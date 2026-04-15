from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from ..models.orchestrator import ExecutionTimings
from ..models.observation import OpenSpaceObservationPolicy
from ..models.persistence import PersistencePolicy
from ..models.request import SkillCreateRequestV6
from ..models.response import SkillCreateResponseV6
from .observation import observe_with_openspace
from .evaluation_runner import run_evaluations
from .extractor import run_extractor
from .generator import run_generator
from .online_discovery import (
    build_skill_blueprints,
    default_discovery_providers,
    decide_skill_reuse,
    discover_online_skills,
)
from .operation_coverage import build_operation_coverage_report
from .persistence import (
    artifacts_with_body_quality,
    artifacts_with_depth_quality,
    artifacts_with_editorial_quality,
    artifacts_with_domain_expertise,
    artifacts_with_domain_specificity,
    artifacts_with_evaluation_report,
    artifacts_with_expert_structure,
    artifacts_with_move_quality,
    artifacts_with_operation_coverage,
    artifacts_with_quality_review,
    artifacts_with_security_audit,
    artifacts_with_self_review,
    artifacts_with_style_diversity,
    persist_artifacts,
)
from .planner import run_planner
from .preloader import preload_repo_context
from .repair import run_repair
from .review import run_skill_quality_review
from .runtime_hook import run_runtime_hook
from .runtime_usage import build_runtime_effectiveness_lookup
from .validator import run_validator


LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def now_ms() -> int:
    return int(time.time() * 1000)


def make_timings() -> ExecutionTimings:
    return ExecutionTimings(started_at_ms=now_ms())


def finish_timings(timings: ExecutionTimings) -> ExecutionTimings:
    timings.finished_at_ms = now_ms()
    return timings


BLOCKING_REPAIRABLE_ISSUES = {
    "invalid_frontmatter",
    "skill_md_over_budget",
    "missing_planned_file",
    "empty_reference_file",
    "empty_script_file",
    "empty_eval_scaffold",
    "reference_structure_incomplete",
    "reference_placeholder_heavy",
    "script_placeholder_heavy",
    "script_non_code_like",
    "script_wrapper_like",
    "invalid_eval_scaffold",
    "pattern_description_missing_capability_trigger",
    "pattern_reference_link_missing",
    "pattern_reference_placeholder_heavy",
    "operation_contract_missing",
    "operation_contract_invalid",
    "operation_surface_incomplete",
    "operation_json_contract_mismatch",
    "operation_mutating_missing_safeguards",
    "operation_session_model_missing",
    "operation_coverage_missing",
    "operation_coverage_invalid",
    "operation_coverage_followup_mismatch",
    "body_too_thin",
    "missing_workflow",
    "missing_output_template",
    "missing_pitfalls",
    "methodology_section_missing",
    "prompt_echo",
    "description_stuffing",
    "self_review_failed",
    "missing_domain_anchors",
    "generic_methodology_shell",
    "high_cross_case_similarity",
    "body_prompt_echo",
    "domain_workflow_missing",
    "domain_output_missing",
    "domain_actions_missing",
    "domain_output_fields_missing",
    "domain_judgment_checks_missing",
    "domain_pitfalls_missing",
    "domain_moves_underdeveloped",
    "generic_domain_move_shell",
    "expert_headings_missing",
    "expert_action_clusters_missing",
    "expert_output_fields_missing",
    "expert_quality_checks_missing",
    "generic_expert_skeleton",
    "high_generated_heading_overlap",
    "high_generated_line_jaccard",
    "shallow_workflow_steps",
    "missing_decision_probes",
    "weak_output_field_guidance",
    "thin_failure_patterns",
    "missing_worked_examples",
    "low_expert_depth_recall",
    "low_decision_pressure",
    "excessive_explanatory_bulk",
    "weak_output_executability",
    "thin_failure_corrections",
    "high_redundancy",
    "missing_expert_cut_moves",
    "expert_move_recall_low",
    "expert_move_precision_low",
    "decision_rules_missing",
    "output_field_semantics_missing",
    "failure_repair_missing",
    "numbered_workflow_spine_missing",
    "high_cross_case_move_overlap",
}



def derive_validation_severity(diagnostics) -> str:
    validation = diagnostics.validation
    repairable_issue_types = set(getattr(validation, "repairable_issue_types", []) or [])
    security_audit = getattr(diagnostics, "security_audit", None)
    security_rating = str(getattr(security_audit, "rating", "LOW") or "LOW").upper()

    if security_rating in {"HIGH", "REJECT"}:
        return "fail"

    if (
        not validation.frontmatter_valid
        or not validation.skill_md_within_budget
        or not validation.planned_files_present
        or bool(repairable_issue_types & BLOCKING_REPAIRABLE_ISSUES)
    ):
        return "fail"

    if (
        validation.unnecessary_files_present
        or bool(validation.unreferenced_reference_files)
        or validation.unsupported_claims_found
        or bool(repairable_issue_types)
        or security_rating == "MEDIUM"
    ):
        return "warn"

    return "pass"


def should_attempt_repair(
    *,
    request: SkillCreateRequestV6,
    severity: str,
    diagnostics,
    attempts: int,
) -> bool:
    if not getattr(request, "enable_repair", True):
        return False
    security_audit = getattr(diagnostics, "security_audit", None)
    security_rating = str(getattr(security_audit, "rating", "LOW") or "LOW").upper()
    if security_rating in {"HIGH", "REJECT"}:
        return False
    if severity != "fail":
        return False
    if attempts >= getattr(request, "max_repair_attempts", 1):
        return False
    if not getattr(diagnostics.validation, "repairable_issue_types", []):
        return False
    return True


def _collect_issue_types(diagnostics) -> list[str]:
    validation = diagnostics.validation
    return sorted(
        set(
            list(getattr(validation, "repairable_issue_types", []) or [])
            + list(getattr(validation, "non_repairable_issue_types", []) or [])
        )
    )


def _append_diagnostic_note(diagnostics, note: str) -> None:
    if diagnostics is None or not note:
        return
    notes = list(getattr(diagnostics, "notes", []) or [])
    if note not in notes:
        notes.append(note)
        diagnostics.notes = notes


def _benchmark_score(evaluation_report, benchmark_name: str) -> float | None:
    for item in list(getattr(evaluation_report, "benchmark_results", []) or []):
        if getattr(item, "name", None) != benchmark_name:
            continue
        score = getattr(item, "score", None)
        if score is None:
            return None
        try:
            return float(score)
        except (TypeError, ValueError):
            return None
    return None


def _describe_issue_transition(before_issues: list[str], after_issues: list[str]) -> str:
    before = set(before_issues)
    after = set(after_issues)
    resolved = sorted(before - after)
    added = sorted(after - before)
    persistent = sorted(before & after)

    parts = [
        f"repairable/non-repairable issues {len(before_issues)} -> {len(after_issues)}",
    ]
    if resolved:
        parts.append(f"resolved={resolved}")
    if persistent:
        parts.append(f"remaining={persistent}")
    if added:
        parts.append(f"new={added}")
    return "; ".join(parts)


def run_skill_create(
    request: SkillCreateRequestV6,
    *,
    preload_repo_context_fn=None,
    persist_artifacts_fn=None,
    repair_fn=None,
    observe_with_openspace_fn=None,
    run_runtime_hook_fn=None,
    output_root: Optional[str] = None,
    persistence_policy: Optional[PersistencePolicy] = None,
    observation_policy: Optional[OpenSpaceObservationPolicy] = None,
    fail_fast_on_validation_fail: bool = False,
    extractor_llm_runner: Optional[LLMRunner] = None,
    planner_llm_runner: Optional[LLMRunner] = None,
    generator_llm_runner: Optional[LLMRunner] = None,
    extractor_model: Optional[str] = None,
    planner_model: Optional[str] = None,
    generator_model: Optional[str] = None,
    runtime_judge_llm_runner: Optional[LLMRunner] = None,
) -> SkillCreateResponseV6:
    request_id = str(uuid.uuid4())
    timings = make_timings()
    effective_request = request
    effective_persistence_policy = persistence_policy or PersistencePolicy()

    preload_repo_context_fn = preload_repo_context_fn or preload_repo_context
    persist_artifacts_fn = persist_artifacts_fn or persist_artifacts
    repair_fn = repair_fn or run_repair
    observe_with_openspace_fn = observe_with_openspace_fn or observe_with_openspace
    run_runtime_hook_fn = run_runtime_hook_fn or run_runtime_hook

    repo_context = preload_repo_context_fn(request)
    extracted_patterns = getattr(request, 'extracted_patterns', None)
    online_skill_candidates = list(getattr(request, 'online_skill_candidates', []) or [])
    online_skill_blueprints = list(getattr(request, 'online_skill_blueprints', []) or [])
    reuse_decision = None
    evaluation_report = None
    quality_review = None

    if getattr(request, 'enable_online_skill_discovery', False):
        if not online_skill_candidates:
            runtime_effectiveness_lookup = None
            if getattr(request, 'enable_runtime_effectiveness_prior', False):
                runtime_effectiveness_lookup = build_runtime_effectiveness_lookup(
                    policy=observation_policy,
                )
            online_skill_candidates = discover_online_skills(
                task=request.task,
                repo_context=repo_context,
                providers=default_discovery_providers(
                    manifest_urls=getattr(request, 'online_skill_manifest_urls', []) or [],
                    task=request.task,
                    include_live=getattr(request, 'enable_live_online_search', True),
                ),
                limit=getattr(request, 'online_skill_limit', 5),
                runtime_effectiveness_lookup=runtime_effectiveness_lookup,
                enable_runtime_effectiveness_prior=getattr(request, 'enable_runtime_effectiveness_prior', False),
                runtime_effectiveness_min_runs=getattr(request, 'runtime_effectiveness_min_runs', 5),
                runtime_effectiveness_allowed_families=getattr(request, 'runtime_effectiveness_allowed_families', None),
            )
        if not online_skill_blueprints and online_skill_candidates:
            online_skill_blueprints = build_skill_blueprints(
                online_skill_candidates,
                limit=getattr(request, 'online_skill_limit', 5),
            )
        reuse_decision = decide_skill_reuse(
            task=request.task,
            candidates=online_skill_candidates,
            blueprints=online_skill_blueprints,
        )

    if online_skill_candidates or online_skill_blueprints:
        effective_request = request.model_copy(
            update={
                'online_skill_candidates': online_skill_candidates,
                'online_skill_blueprints': online_skill_blueprints,
                'enable_eval_scaffold': bool(
                    getattr(request, 'enable_eval_scaffold', False)
                    or online_skill_candidates
                    or online_skill_blueprints
                ),
            }
        )

    timings.extractor_started_at_ms = now_ms()
    repo_findings = run_extractor(
        request=effective_request,
        repo_context=repo_context,
        llm_runner=extractor_llm_runner,
        model=extractor_model,
    )
    timings.extractor_finished_at_ms = now_ms()

    if getattr(request, "mode", "synthesize") == "extract":
        return SkillCreateResponseV6(
            request_id=request_id,
            version=request.version,
            severity="pass",
            request_echo=effective_request,
            repo_findings=repo_findings,
            extracted_patterns=extracted_patterns,
            online_skill_candidates=online_skill_candidates,
            online_skill_blueprints=online_skill_blueprints,
            reuse_decision=reuse_decision,
            skill_plan=None,
            artifacts=None,
            diagnostics=None,
            evaluation_report=None,
            quality_review=None,
            persistence=None,
            timings=finish_timings(timings),
        )

    timings.planner_started_at_ms = now_ms()
    skill_plan = run_planner(
        request=effective_request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        extracted_patterns=extracted_patterns,
        online_skill_blueprints=online_skill_blueprints,
        reuse_decision=reuse_decision,
        llm_runner=planner_llm_runner,
        model=planner_model,
    )
    timings.planner_finished_at_ms = now_ms()

    if getattr(request, "output_mode", None) == "plan":
        return SkillCreateResponseV6(
            request_id=request_id,
            version=request.version,
            severity="pass",
            request_echo=effective_request,
            repo_findings=repo_findings,
            extracted_patterns=extracted_patterns,
            online_skill_candidates=online_skill_candidates,
            online_skill_blueprints=online_skill_blueprints,
            reuse_decision=reuse_decision,
            skill_plan=skill_plan,
            artifacts=None,
            diagnostics=None,
            evaluation_report=None,
            quality_review=None,
            persistence=None,
            timings=finish_timings(timings),
        )

    timings.generator_started_at_ms = now_ms()
    artifacts = run_generator(
        request=effective_request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        skill_plan=skill_plan,
        reuse_decision=reuse_decision,
        llm_runner=generator_llm_runner,
        model=generator_model,
    )
    timings.generator_finished_at_ms = now_ms()

    timings.validator_started_at_ms = now_ms()
    diagnostics = run_validator(
        request=effective_request,
        repo_findings=repo_findings,
        skill_plan=skill_plan,
        artifacts=artifacts,
        extracted_patterns=extracted_patterns,
    )
    timings.validator_finished_at_ms = now_ms()

    severity = derive_validation_severity(diagnostics)
    evaluation_report = run_evaluations(artifacts=artifacts) if artifacts is not None else None
    quality_review = run_skill_quality_review(
        repo_findings=repo_findings,
        skill_plan=skill_plan,
        artifacts=artifacts,
        diagnostics=diagnostics,
        evaluation_report=evaluation_report,
    )
    if diagnostics is not None and quality_review is not None:
        if getattr(request, 'enable_runtime_effectiveness_prior', False) and online_skill_candidates:
            adjusted = [
                candidate
                for candidate in list(online_skill_candidates or [])
                if abs(float(getattr(candidate, 'runtime_prior_delta', 0.0) or 0.0)) > 0.0
            ]
            if adjusted:
                allowed_families = list(getattr(request, 'runtime_effectiveness_allowed_families', None) or [])
                family_note = f'; allowed_families={allowed_families}' if allowed_families else ''
                details = ', '.join(
                    (
                        f'{candidate.name}: base_score={candidate.base_score:.2f}, '
                        f'runtime_prior_delta={candidate.runtime_prior_delta:+.2f}, '
                        f'adjusted_score={candidate.adjusted_score:.2f}'
                    )
                    for candidate in adjusted[:3]
                )
                _append_diagnostic_note(
                    diagnostics,
                    f'Runtime effectiveness prior{family_note}: {details}',
                )
        _append_diagnostic_note(
            diagnostics,
            (
                "Quality review: "
                f"fully_correct={quality_review.fully_correct}; "
                f"requirements_satisfied={sum(1 for item in quality_review.requirement_results if item.satisfied)}/{len(quality_review.requirement_results)}; "
                f"repair_suggestions={len(quality_review.repair_suggestions)}; "
                f"confidence={quality_review.confidence:.2f}"
            ),
        )

    repair_attempts = 0
    while repair_fn is not None and should_attempt_repair(
        request=request,
        severity=severity,
        diagnostics=diagnostics,
        attempts=repair_attempts,
    ):
        timings.repair_attempted = True
        repair_attempts += 1
        pre_repair_issues = _collect_issue_types(diagnostics)

        repair_result = repair_fn(
            artifacts=artifacts,
            diagnostics=diagnostics,
            skill_plan=skill_plan,
            skill_name=skill_plan.skill_name,
            description=f"Repo-aware skill for {skill_plan.skill_name}",
            max_skill_md_lines=skill_plan.content_budget.skill_md_max_lines,
            request=effective_request,
            reuse_decision=reuse_decision,
            quality_review=quality_review,
        )

        if not getattr(repair_result, "applied", False):
            _append_diagnostic_note(
                diagnostics,
                f"Repair attempt {repair_attempts} made no changes: {getattr(repair_result, 'reason', '') or 'repair returned applied=False'}",
            )
            break

        timings.repair_applied = True
        timings.repair_iteration_count = repair_attempts
        artifacts = repair_result.repaired_artifacts

        timings.validator_started_at_ms = now_ms()
        diagnostics = run_validator(
            request=effective_request,
            repo_findings=repo_findings,
            skill_plan=skill_plan,
            artifacts=artifacts,
            extracted_patterns=extracted_patterns,
        )
        timings.validator_finished_at_ms = now_ms()

        post_repair_issues = _collect_issue_types(diagnostics)
        _append_diagnostic_note(
            diagnostics,
            f"Repair attempt {repair_attempts}: {_describe_issue_transition(pre_repair_issues, post_repair_issues)}",
        )

        severity = derive_validation_severity(diagnostics)
        evaluation_report = run_evaluations(artifacts=artifacts) if artifacts is not None else None
        quality_review = run_skill_quality_review(
            repo_findings=repo_findings,
            skill_plan=skill_plan,
            artifacts=artifacts,
            diagnostics=diagnostics,
            evaluation_report=evaluation_report,
        )

    if (
        repair_attempts >= getattr(request, "max_repair_attempts", 1)
        and severity == "fail"
        and diagnostics is not None
    ):
        _append_diagnostic_note(
            diagnostics,
            f"Repair stopped after reaching max_repair_attempts={getattr(request, 'max_repair_attempts', 1)}; remaining issues={_collect_issue_types(diagnostics)}",
        )

    if severity != "fail" and artifacts is not None:
        timings.eval_runner_started_at_ms = now_ms()
        evaluation_report = run_evaluations(artifacts=artifacts)
        timings.eval_runner_finished_at_ms = now_ms()
        quality_review = run_skill_quality_review(
            repo_findings=repo_findings,
            skill_plan=skill_plan,
            artifacts=artifacts,
            diagnostics=diagnostics,
            evaluation_report=evaluation_report,
        )
        if evaluation_report is not None and diagnostics is not None:
            note_parts = [
                "Evaluation runner: "
                f"overall_score={evaluation_report.overall_score:.2f}",
            ]
            task_alignment = _benchmark_score(evaluation_report, "task_alignment")
            if task_alignment is not None:
                note_parts.append(f"task_alignment={task_alignment:.2f}")
            adaptation_quality = _benchmark_score(evaluation_report, "adaptation_quality")
            if adaptation_quality is not None:
                note_parts.append(f"adaptation_quality={adaptation_quality:.2f}")
            note_parts.extend(
                [
                    f"trigger_cases={len(evaluation_report.trigger_results)}",
                    f"output_cases={len(evaluation_report.output_results)}",
                ]
            )
            _append_diagnostic_note(
                diagnostics,
                "; ".join(note_parts),
            )
        if quality_review is not None and diagnostics is not None:
            _append_diagnostic_note(
                diagnostics,
                (
                    "Quality review: "
                    f"fully_correct={quality_review.fully_correct}; "
                    f"requirements_satisfied={sum(1 for item in quality_review.requirement_results if item.satisfied)}/{len(quality_review.requirement_results)}; "
                    f"repair_suggestions={len(quality_review.repair_suggestions)}; "
                    f"confidence={quality_review.confidence:.2f}"
                ),
            )
        artifacts = artifacts_with_evaluation_report(
            artifacts=artifacts,
            evaluation_report=evaluation_report,
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_quality_review(
            artifacts=artifacts,
            quality_review=quality_review,
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_body_quality(
            artifacts=artifacts,
            body_quality=getattr(diagnostics, "body_quality", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_self_review(
            artifacts=artifacts,
            self_review=getattr(diagnostics, "self_review", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_domain_specificity(
            artifacts=artifacts,
            domain_specificity=getattr(diagnostics, "domain_specificity", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_domain_expertise(
            artifacts=artifacts,
            domain_expertise=getattr(diagnostics, "domain_expertise", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_expert_structure(
            artifacts=artifacts,
            expert_structure=getattr(diagnostics, "expert_structure", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_depth_quality(
            artifacts=artifacts,
            depth_quality=getattr(diagnostics, "depth_quality", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_editorial_quality(
            artifacts=artifacts,
            editorial_quality=getattr(diagnostics, "editorial_quality", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_style_diversity(
            artifacts=artifacts,
            style_diversity=getattr(diagnostics, "style_diversity", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_move_quality(
            artifacts=artifacts,
            move_quality=getattr(diagnostics, "move_quality", None),
            policy=effective_persistence_policy,
        )

    if artifacts is not None and diagnostics is not None:
        artifacts = artifacts_with_body_quality(
            artifacts=artifacts,
            body_quality=getattr(diagnostics, "body_quality", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_self_review(
            artifacts=artifacts,
            self_review=getattr(diagnostics, "self_review", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_domain_specificity(
            artifacts=artifacts,
            domain_specificity=getattr(diagnostics, "domain_specificity", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_domain_expertise(
            artifacts=artifacts,
            domain_expertise=getattr(diagnostics, "domain_expertise", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_expert_structure(
            artifacts=artifacts,
            expert_structure=getattr(diagnostics, "expert_structure", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_depth_quality(
            artifacts=artifacts,
            depth_quality=getattr(diagnostics, "depth_quality", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_editorial_quality(
            artifacts=artifacts,
            editorial_quality=getattr(diagnostics, "editorial_quality", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_style_diversity(
            artifacts=artifacts,
            style_diversity=getattr(diagnostics, "style_diversity", None),
            policy=effective_persistence_policy,
        )
        artifacts = artifacts_with_move_quality(
            artifacts=artifacts,
            move_quality=getattr(diagnostics, "move_quality", None),
            policy=effective_persistence_policy,
        )
        operation_coverage = None
        if str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower() == 'operation_backed':
            operation_coverage = build_operation_coverage_report(
                skill_plan=skill_plan,
                artifacts=artifacts,
                diagnostics=diagnostics,
            )
            artifacts = artifacts_with_operation_coverage(
                artifacts=artifacts,
                operation_coverage=operation_coverage,
                policy=effective_persistence_policy,
            )
        artifacts = artifacts_with_security_audit(
            artifacts=artifacts,
            security_audit=getattr(diagnostics, "security_audit", None),
            policy=effective_persistence_policy,
        )

    if fail_fast_on_validation_fail and severity == "fail":
        persistence = None
    else:
        persistence = persist_artifacts_fn(
            artifacts=artifacts,
            skill_plan=skill_plan,
            output_root=output_root,
            severity=severity,
            policy=effective_persistence_policy,
        )

    observation = None
    if observe_with_openspace_fn is not None and observation_policy is not None:
        observation = observe_with_openspace_fn(
            request=request,
            request_id=request_id,
            severity=severity,
            skill_plan=skill_plan,
            artifacts=artifacts,
            diagnostics=diagnostics,
            evaluation_report=evaluation_report,
            persistence=persistence,
            timings=timings,
            policy=observation_policy,
        )
    if getattr(request, 'enable_runtime_hook', False) and getattr(request, 'runtime_run_record', None) is not None:
        try:
            runtime_hook_result = run_runtime_hook_fn(
                run_record=request.runtime_run_record,
                policy=observation_policy,
                baseline_path=(
                    Path(request.runtime_hook_baseline_path).expanduser()
                    if getattr(request, 'runtime_hook_baseline_path', None)
                    else None
                ),
                scenario_names=list(getattr(request, 'runtime_hook_scenarios', []) or []) or None,
                enable_llm_judge=bool(getattr(request, 'enable_runtime_llm_judge', False)),
                llm_runner=runtime_judge_llm_runner,
                model=getattr(request, 'runtime_judge_model', None),
            )
            observation = dict(observation or {})
            observation['runtime_hook'] = runtime_hook_result.model_dump(mode='json')
            if diagnostics is not None:
                followup_action = (
                    runtime_hook_result.runtime_cycle.followup.action
                    if runtime_hook_result.runtime_cycle is not None
                    else 'n/a'
                )
                change_action = (
                    runtime_hook_result.change_pack.recommended_action
                    if runtime_hook_result.change_pack is not None
                    else 'n/a'
                )
                approval = (
                    runtime_hook_result.approval_pack.approval_decision
                    if runtime_hook_result.approval_pack is not None
                    else 'n/a'
                )
                judge_state = 'disabled'
                if getattr(request, 'enable_runtime_llm_judge', False):
                    judge_state = (
                        'applied'
                        if runtime_hook_result.judge_pack is not None and runtime_hook_result.judge_pack.applied
                        else 'skipped'
                    )
                _append_diagnostic_note(
                    diagnostics,
                    (
                        'Runtime hook: '
                        f'followup_action={followup_action}; '
                        f'change_pack={change_action}; '
                        f'approval={approval}; '
                        f'judge={judge_state}'
                    ),
                )
        except Exception as exc:  # pragma: no cover - defensive optional hook
            if diagnostics is not None:
                _append_diagnostic_note(
                    diagnostics,
                    f'Runtime hook skipped: {exc}',
                )

    return SkillCreateResponseV6(
        request_id=request_id,
        version=request.version,
        severity=severity,
        request_echo=effective_request,
        repo_findings=repo_findings,
        extracted_patterns=extracted_patterns,
        online_skill_candidates=online_skill_candidates,
        online_skill_blueprints=online_skill_blueprints,
        reuse_decision=reuse_decision,
        skill_plan=skill_plan,
        artifacts=artifacts,
        diagnostics=diagnostics,
        evaluation_report=evaluation_report,
        quality_review=quality_review,
        persistence=persistence,
        observation=observation,
        timings=finish_timings(timings),
    )
