from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models.ops_approval import OpsApprovalState
from ..models.ops_post_apply import (
    CreateSeedLaunchReport,
    CreateSeedPackageReviewReport,
    OpsRefillReport,
    PriorPilotRetrievalTrialReport,
    PriorPilotTrialObservationReport,
    SourcePromotionPostApplyReport,
)
from ..models.online import SkillSourceCandidate
from ..models.request import SkillCreateRequestV6
from ..models.public_source_verification import PublicSourceCurationRoundReport
from ..models.runtime_governance import (
    RuntimeCreateSeedProposalPack,
    RuntimePriorPilotReport,
)
from .online_discovery import StaticCatalogDiscoveryProvider, discover_online_skills
from .preloader import preload_repo_context
from .runtime_governance import build_runtime_prior_gate_report, build_runtime_prior_pilot_exercise_report
from .ops_approval import (
    DEFAULT_COLLECTIONS_FILE,
    DEFAULT_OPS_ARTIFACT_ROOT,
    apply_approval_to_create_seed_proposal,
    apply_approval_to_prior_pilot_profile,
    build_create_seed_manual_round_pack,
    build_prior_pilot_manual_trial_pack,
    source_promotion_is_applied,
)
from .public_source_curation import build_public_source_promotion_pack
from .simulation import build_simulation_suite_report


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANUAL_ROUND_OUTPUT_ROOT = ROOT / '.generated-skills' / 'manual_rounds'
DEFAULT_HF_PRIOR_TRIAL_REPO = ROOT / 'tests' / 'fixtures' / 'hf_prior_trial_repo'
DEFAULT_HF_PRIOR_SPEC = ROOT / 'tests' / 'fixtures' / 'simulation' / 'prior_gate' / 'hf_trainer_pilot_ready' / 'input' / 'spec.json'


def _slug(value: str) -> str:
    text = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or '').strip())
    while '--' in text:
        text = text.replace('--', '-')
    return text.strip('-') or 'item'


def render_create_seed_launch_report_markdown(report: CreateSeedLaunchReport) -> str:
    lines = [
        '# Create Seed Launch Report',
        '',
        f'- candidate_key={report.candidate_key}',
        f'- approval_decision={report.approval_decision}',
        f'- decision_status={report.decision_status}',
        f'- artifact_exists={report.artifact_exists}',
        f'- launch_ready={report.launch_ready}',
        f'- handoff_artifact_path={report.handoff_artifact_path or "(not materialized)"}',
        f'- suggested_output_root={report.suggested_output_root or "(not set)"}',
        f'- Summary: {report.summary}',
        '',
        '## Recommended Fixture Inputs',
    ]
    if not report.recommended_fixture_inputs:
        lines.append('- None')
    else:
        for item in report.recommended_fixture_inputs:
            lines.append(f'- {item}')
    lines.extend(['', '## Launch Checklist'])
    if not report.launch_checklist:
        lines.append('- None')
    else:
        for item in report.launch_checklist:
            lines.append(f'- {item}')
    lines.extend(['', '## Preview Request'])
    lines.append(f'- skill_name_hint={report.preview_request.skill_name_hint}')
    lines.append(f'- task={report.preview_request.task}')
    lines.extend(['', '## Next Step'])
    lines.append(f'- {report.next_step_hint}')
    return '\n'.join(lines).strip()


def build_create_seed_launch_report(
    *,
    create_seed_pack: RuntimeCreateSeedProposalPack,
    approval_state: OpsApprovalState,
    candidate_key: str = 'missing-fits-calibration-and-astropy-verification-workflow',
    artifact_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
) -> CreateSeedLaunchReport:
    round_pack = build_create_seed_manual_round_pack(
        create_seed_pack=create_seed_pack,
        approval_state=approval_state,
        candidate_key=candidate_key,
        artifact_root=artifact_root,
    )
    artifact_path = Path(str(round_pack.handoff_artifact_path or '')).expanduser() if round_pack.handoff_artifact_path else None
    artifact_exists = bool(artifact_path is not None and artifact_path.exists())
    suggested_output_root = Path(output_root or DEFAULT_MANUAL_ROUND_OUTPUT_ROOT).expanduser().resolve() / _slug(round_pack.candidate_key)
    launch_ready = round_pack.status == 'applied' and artifact_exists
    report = CreateSeedLaunchReport(
        candidate_key=round_pack.candidate_key,
        approval_decision=round_pack.approval_decision,
        decision_status=round_pack.status,
        handoff_artifact_path=round_pack.handoff_artifact_path,
        artifact_exists=artifact_exists,
        launch_ready=launch_ready,
        preview_request=round_pack.preview_request.model_copy(deep=True),
        recommended_fixture_inputs=list(round_pack.recommended_fixture_inputs or []),
        launch_checklist=list(round_pack.launch_checklist or []),
        suggested_output_root=str(suggested_output_root),
        next_step_hint=(
            'Use the handoff artifact and preview request as the explicit input for a human-started skill-create round.'
            if launch_ready
            else 'Keep the create-seed candidate approved and materialized before attempting a manual round.'
        ),
        summary=(
            f'Create-seed launch report ready: candidate={round_pack.candidate_key} '
            f'status={round_pack.status} launch_ready={launch_ready}'
        ),
    )
    report.markdown_summary = render_create_seed_launch_report_markdown(report)
    return report


def _find_latest_create_seed_run_summary(candidate_key: str) -> Optional[Path]:
    snapshot_root = ROOT / '.generated-skills' / 'ops_artifacts' / 'create_seed'
    snapshot_matches = sorted(snapshot_root.glob('*package-review*.json'), key=lambda item: item.stat().st_mtime)
    for snapshot_path in reversed(snapshot_matches):
        try:
            payload = json.loads(snapshot_path.read_text(encoding='utf-8'))
        except Exception:
            continue
        if str(payload.get('candidate_key') or '').strip() != candidate_key:
            continue
        run_summary_path = str(payload.get('run_summary_path') or '').strip()
        if not run_summary_path:
            continue
        candidate = Path(run_summary_path).expanduser().resolve()
        if candidate.exists():
            return candidate
    root = ROOT / '.generated-skills'
    matches = sorted(root.glob(f'manual_rounds*/{candidate_key}-run-summary.json'))
    return matches[-1] if matches else None


def render_create_seed_package_review_markdown(report: CreateSeedPackageReviewReport) -> str:
    lines = [
        '# Create Seed Package Review',
        '',
        f'- candidate_key={report.candidate_key}',
        f'- run_summary_path={report.run_summary_path or "(missing)"}',
        f'- output_root={report.output_root or "(missing)"}',
        f'- review_exists={report.review_exists}',
        f'- report_exists={report.report_exists}',
        f'- fully_correct={report.fully_correct}',
        f'- overall_score={report.overall_score:.4f}',
        f'- confidence={report.confidence:.4f}',
        f'- requirements_satisfied={report.requirements_satisfied}/{report.requirements_total}',
        f'- repair_suggestions_count={report.repair_suggestions_count}',
        f'- verdict={report.verdict}',
        f'- Summary: {report.summary}',
    ]
    return '\n'.join(lines).strip()


def build_create_seed_package_review_report(
    *,
    candidate_key: str = 'missing-fits-calibration-and-astropy-verification-workflow',
    run_summary_path: Optional[Path] = None,
) -> CreateSeedPackageReviewReport:
    summary_path = Path(run_summary_path).expanduser().resolve() if run_summary_path else _find_latest_create_seed_run_summary(candidate_key)
    if summary_path is None or not summary_path.exists():
        report = CreateSeedPackageReviewReport(
            candidate_key=candidate_key,
            verdict='missing',
            summary=f'Create-seed package review missing: no run summary found for {candidate_key}',
        )
        report.markdown_summary = render_create_seed_package_review_markdown(report)
        return report

    payload = json.loads(summary_path.read_text(encoding='utf-8'))
    output_root = Path(str(payload.get('output_root') or '')).expanduser().resolve()
    review_path = output_root / 'evals' / 'review.json'
    report_path = output_root / 'evals' / 'report.json'
    review_payload = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else {}
    report_payload = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    requirement_results = list(review_payload.get('requirement_results') or [])
    requirements_satisfied = sum(1 for item in requirement_results if item.get('satisfied'))
    requirements_total = len(requirement_results)
    repair_suggestions_count = len(list(review_payload.get('repair_suggestions') or []))
    fully_correct = bool(review_payload.get('fully_correct'))
    overall_score = float(report_payload.get('overall_score') or 0.0)
    confidence = float(review_payload.get('confidence') or 0.0)
    verdict = (
        'ready_for_manual_use'
        if review_path.exists() and report_path.exists() and fully_correct and repair_suggestions_count == 0
        else 'needs_revision'
    )
    report = CreateSeedPackageReviewReport(
        candidate_key=candidate_key,
        run_summary_path=str(summary_path),
        output_root=str(output_root),
        review_path=str(review_path),
        report_path=str(report_path),
        review_exists=review_path.exists(),
        report_exists=report_path.exists(),
        fully_correct=fully_correct,
        overall_score=overall_score,
        confidence=confidence,
        requirements_satisfied=requirements_satisfied,
        requirements_total=requirements_total,
        repair_suggestions_count=repair_suggestions_count,
        verdict=verdict,
        summary=(
            f'Create-seed package review complete: candidate={candidate_key} '
            f'verdict={verdict} requirements={requirements_satisfied}/{requirements_total}'
        ),
    )
    report.markdown_summary = render_create_seed_package_review_markdown(report)
    return report


def render_prior_pilot_trial_observation_markdown(report: PriorPilotTrialObservationReport) -> str:
    lines = [
        '# Runtime Prior Trial Observation',
        '',
        f'- family={report.family}',
        f'- approval_decision={report.approval_decision}',
        f'- decision_status={report.decision_status}',
        f'- artifact_exists={report.artifact_exists}',
        f'- trial_ready={report.trial_ready}',
        f'- profile_artifact_path={report.profile_artifact_path or "(not materialized)"}',
        f'- matched={report.matched_count} drifted={report.drifted_count} invalid_fixture={report.invalid_fixture_count}',
        f'- top_1_changes={report.top_1_changes}',
        f'- generic_promotion_risk={report.generic_promotion_risk}',
        f'- Summary: {report.summary}',
        '',
        '## Scenarios',
    ]
    if not report.scenarios_run:
        lines.append('- None')
    else:
        for item in report.scenarios_run:
            lines.append(f'- {item}')
    lines.extend(['', '## Recommended Trial Tasks'])
    if not report.recommended_trial_tasks:
        lines.append('- None')
    else:
        for item in report.recommended_trial_tasks:
            lines.append(f'- {item}')
    lines.extend(['', '## Expected Safe Signals'])
    if not report.expected_safe_signals:
        lines.append('- None')
    else:
        for item in report.expected_safe_signals:
            lines.append(f'- {item}')
    lines.extend(['', '## Rollback Steps'])
    if not report.rollback_steps:
        lines.append('- None')
    else:
        for item in report.rollback_steps:
            lines.append(f'- {item}')
    lines.extend(['', '## Next Step'])
    lines.append(f'- {report.next_step_hint}')
    return '\n'.join(lines).strip()


def build_prior_pilot_trial_observation_report(
    *,
    pilot_report: RuntimePriorPilotReport,
    approval_state: OpsApprovalState,
    family: str = 'hf-trainer',
    artifact_root: Optional[Path] = None,
    fixture_root: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> PriorPilotTrialObservationReport:
    scenario_names = list(scenario_names or ['hf_trainer_pilot_ready', 'allowlisted_family_only'])
    exercise_report = build_runtime_prior_pilot_exercise_report(
        pilot_report=pilot_report,
        family=family,
        fixture_root=fixture_root,
        scenario_names=scenario_names,
        approval_state=approval_state,
        artifact_root=artifact_root,
    )
    profile = next(
        (item for item in list(pilot_report.profiles or []) if item.family == family),
        None,
    )
    if profile is None:
        raise ValueError(f'Prior pilot profile not found: {family}')
    approved_profile = apply_approval_to_prior_pilot_profile(
        profile,
        approval_state=approval_state,
        artifact_root=artifact_root,
    )
    manual_pack = build_prior_pilot_manual_trial_pack(
        pilot_report=pilot_report,
        family=family,
        approval_state=approval_state,
        artifact_root=artifact_root,
        generic_promotion_risk=int(approved_profile.generic_promotion_risk or 0),
        top_1_changes=0,
        exercise_verdict='ready_for_manual_pilot' if exercise_report.drifted_count == 0 and exercise_report.invalid_fixture_count == 0 else 'hold',
    )
    artifact_path = Path(str(manual_pack.profile_artifact_path or '')).expanduser() if manual_pack.profile_artifact_path else None
    artifact_exists = bool(artifact_path is not None and artifact_path.exists())
    trial_ready = (
        manual_pack.status == 'applied'
        and artifact_exists
        and exercise_report.drifted_count == 0
        and exercise_report.invalid_fixture_count == 0
        and int(exercise_report.generic_promotion_risk or 0) == 0
    )
    report = PriorPilotTrialObservationReport(
        family=manual_pack.family,
        approval_decision=manual_pack.approval_decision,
        decision_status=manual_pack.status,
        profile_artifact_path=manual_pack.profile_artifact_path,
        artifact_exists=artifact_exists,
        request_overrides=dict(manual_pack.request_overrides or {}),
        recommended_trial_tasks=list(manual_pack.recommended_trial_tasks or []),
        expected_safe_signals=list(manual_pack.expected_safe_signals or []),
        rollback_steps=list(manual_pack.rollback_steps or []),
        scenarios_run=list(exercise_report.scenarios_run or scenario_names),
        matched_count=exercise_report.matched_count,
        drifted_count=exercise_report.drifted_count,
        invalid_fixture_count=exercise_report.invalid_fixture_count,
        top_1_changes=exercise_report.top_1_changes,
        generic_promotion_risk=int(exercise_report.generic_promotion_risk or 0),
        trial_ready=trial_ready,
        next_step_hint=(
            'Run a human-owned allowlisted hf-trainer trial and keep the override strictly opt-in.'
            if trial_ready
            else 'Do not widen the prior pilot yet; keep the family on a controlled allowlist until the observation report is clean.'
        ),
        summary=(
            f'Prior trial observation complete: family={family} '
            f'status={manual_pack.status} matched={exercise_report.matched_count} '
            f'drifted={exercise_report.drifted_count} invalid_fixture={exercise_report.invalid_fixture_count}'
        ),
    )
    report.markdown_summary = render_prior_pilot_trial_observation_markdown(report)
    return report


def render_prior_pilot_retrieval_trial_markdown(report: PriorPilotRetrievalTrialReport) -> str:
    lines = [
        '# Prior Pilot Retrieval Trial',
        '',
        f'- family={report.family}',
        f'- repo_path={report.repo_path or "(missing)"}',
        f'- approval_decision={report.approval_decision}',
        f'- decision_status={report.decision_status}',
        f'- selected_files_count={report.selected_files_count}',
        f'- baseline_top_candidate={report.baseline_top_candidate or "(none)"}',
        f'- pilot_top_candidate={report.pilot_top_candidate or "(none)"}',
        f'- baseline_prior_applied={report.baseline_prior_applied}',
        f'- pilot_prior_applied={report.pilot_prior_applied}',
        f'- generic_promotion_risk={report.generic_promotion_risk}',
        f'- eligible_families={report.eligible_families}',
        f'- verdict={report.verdict}',
        f'- Summary: {report.summary}',
        '',
        '## Request Overrides',
        f'- {report.request_overrides}',
    ]
    return '\n'.join(lines).strip()


def build_prior_pilot_retrieval_trial_report(
    *,
    pilot_report: RuntimePriorPilotReport,
    approval_state: OpsApprovalState,
    family: str = 'hf-trainer',
    repo_path: Optional[Path] = None,
    spec_path: Optional[Path] = None,
    artifact_root: Optional[Path] = None,
) -> PriorPilotRetrievalTrialReport:
    manual_pack = build_prior_pilot_manual_trial_pack(
        pilot_report=pilot_report,
        family=family,
        approval_state=approval_state,
        artifact_root=artifact_root,
        generic_promotion_risk=0,
        top_1_changes=0,
        exercise_verdict='ready_for_manual_pilot',
    )
    resolved_repo = Path(repo_path or DEFAULT_HF_PRIOR_TRIAL_REPO).expanduser().resolve()
    resolved_spec = Path(spec_path or DEFAULT_HF_PRIOR_SPEC).expanduser().resolve()
    spec_payload = json.loads(resolved_spec.read_text(encoding='utf-8'))
    catalog = [SkillSourceCandidate.model_validate(item) for item in list(spec_payload.get('catalog') or [])]
    lookup = dict(spec_payload.get('runtime_effectiveness_lookup') or {})
    task = str((list(spec_payload.get('task_samples') or [{}])[0]).get('task') or '').strip()
    repo_context = preload_repo_context(
        SkillCreateRequestV6(
            task=task or 'Run an allowlisted hf-trainer retrieval trial.',
            repo_paths=[str(resolved_repo)],
        )
    )
    baseline_report = build_runtime_prior_gate_report(
        catalog=catalog,
        runtime_effectiveness_lookup=lookup,
        task_samples=[{'task': task, 'repo_context': repo_context}],
        runtime_effectiveness_min_runs=int(manual_pack.request_overrides.get('runtime_effectiveness_min_runs', 5) or 5),
        runtime_effectiveness_allowed_families=None,
    )
    pilot_gate_report = build_runtime_prior_gate_report(
        catalog=catalog,
        runtime_effectiveness_lookup=lookup,
        task_samples=[{'task': task, 'repo_context': repo_context}],
        runtime_effectiveness_min_runs=int(manual_pack.request_overrides.get('runtime_effectiveness_min_runs', 5) or 5),
        runtime_effectiveness_allowed_families=list(manual_pack.request_overrides.get('runtime_effectiveness_allowed_families') or []),
    )
    baseline_ranked = discover_online_skills(
        task=task,
        repo_context=repo_context,
        catalog=catalog,
        limit=5,
    )
    pilot_ranked = discover_online_skills(
        task=task,
        repo_context=repo_context,
        catalog=catalog,
        limit=5,
        runtime_effectiveness_lookup=lookup,
        enable_runtime_effectiveness_prior=True,
        runtime_effectiveness_min_runs=int(manual_pack.request_overrides.get('runtime_effectiveness_min_runs', 5) or 5),
        runtime_effectiveness_allowed_families=list(manual_pack.request_overrides.get('runtime_effectiveness_allowed_families') or []),
    )
    baseline_top = baseline_ranked[0] if baseline_ranked else None
    pilot_top = pilot_ranked[0] if pilot_ranked else None
    eligible_families = [item.skill_name for item in pilot_gate_report.eligible_skills if item.eligible]
    generic_promotion_risk = int(pilot_gate_report.ranking_impact_summary.get('generic_promoted_count', 0) or 0)
    pilot_prior_applied = any(abs(float(getattr(candidate, 'runtime_prior_delta', 0.0) or 0.0)) > 0.0 for candidate in list(pilot_ranked or []))
    verdict = (
        'ready_for_manual_trial'
        if manual_pack.status == 'applied'
        and pilot_top is not None
        and pilot_top.name == family
        and generic_promotion_risk == 0
        else 'hold'
    )
    report = PriorPilotRetrievalTrialReport(
        family=family,
        repo_path=str(resolved_repo),
        approval_decision=manual_pack.approval_decision,
        decision_status=manual_pack.status,
        selected_files_count=len(list(repo_context.get('selected_files') or [])),
        baseline_top_candidate=baseline_top.name if baseline_top is not None else '',
        pilot_top_candidate=pilot_top.name if pilot_top is not None else '',
        baseline_prior_applied=False,
        pilot_prior_applied=pilot_prior_applied,
        generic_promotion_risk=generic_promotion_risk,
        eligible_families=eligible_families,
        request_overrides=dict(manual_pack.request_overrides or {}),
        verdict=verdict,
        summary=(
            f'Prior retrieval trial complete: family={family} '
            f'baseline_top={baseline_top.name if baseline_top is not None else "n/a"} '
            f'pilot_top={pilot_top.name if pilot_top is not None else "n/a"} '
            f'verdict={verdict}'
        ),
    )
    report.markdown_summary = render_prior_pilot_retrieval_trial_markdown(report)
    return report


def render_source_promotion_post_apply_markdown(report: SourcePromotionPostApplyReport) -> str:
    lines = [
        '# Source Promotion Post-Apply Monitor',
        '',
        f'- repo_full_name={report.repo_full_name}',
        f'- approval_decision={report.approval_decision}',
        f'- decision_status={report.decision_status}',
        f'- collections_applied={report.collections_applied}',
        f'- requirements_satisfied={report.requirements_satisfied}',
        f'- rehearsal_passed={report.rehearsal_passed}',
        f'- live_applied={report.live_applied}',
        f'- monitor_status={report.monitor_status}',
        f'- matched={report.matched_count} drifted={report.drifted_count} invalid_fixture={report.invalid_fixture_count}',
        f'- Summary: {report.summary}',
        '',
        '## Scenarios',
    ]
    if not report.scenarios_run:
        lines.append('- None')
    else:
        for item in report.scenarios_run:
            lines.append(f'- {item}')
    lines.extend(['', '## Missing Requirements'])
    if not report.missing_requirements:
        lines.append('- None')
    else:
        for item in report.missing_requirements:
            lines.append(f'- {item}')
    lines.extend(['', '## Next Step'])
    lines.append(f'- {report.next_step_hint}')
    return '\n'.join(lines).strip()


def build_source_promotion_post_apply_report(
    *,
    round_report: PublicSourceCurationRoundReport,
    approval_state: OpsApprovalState,
    repo_full_name: str = 'alirezarezvani/claude-skills',
    collections_file: Optional[Path] = None,
    fixture_root: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> SourcePromotionPostApplyReport:
    pack = build_public_source_promotion_pack(
        round_report=round_report,
        repo_full_name=repo_full_name,
        approval_state=approval_state,
        collections_file=collections_file,
    )
    scenario_names = list(scenario_names or ['online_reuse_claude_skills_business_adapt'])
    smoke_report = build_simulation_suite_report(
        mode='smoke-chain',
        fixture_root=fixture_root,
        scenario_names=scenario_names,
    )
    collections_applied = source_promotion_is_applied(
        repo_full_name,
        collections_file=collections_file or DEFAULT_COLLECTIONS_FILE,
    )
    if pack.decision_status != 'applied':
        monitor_status = 'not_applied'
    elif smoke_report.drifted_count or smoke_report.invalid_fixture_count:
        monitor_status = 'needs_attention'
    else:
        monitor_status = 'stable'
    report = SourcePromotionPostApplyReport(
        repo_full_name=repo_full_name,
        approval_decision=pack.approval_decision,
        decision_status=pack.decision_status,
        collections_applied=collections_applied,
        requirements_satisfied=pack.requirements_satisfied,
        rehearsal_passed=bool(round_report.rehearsal_passed),
        live_applied=bool(round_report.live_applied),
        promoted_repos=list(round_report.promoted_repos or []),
        required_ranking_regressions=list(pack.required_ranking_regressions or []),
        required_smoke=list(pack.required_smoke or []),
        missing_requirements=list(pack.missing_requirements or []),
        scenarios_run=scenario_names,
        matched_count=smoke_report.matched_count,
        drifted_count=smoke_report.drifted_count,
        invalid_fixture_count=smoke_report.invalid_fixture_count,
        monitor_status=monitor_status,
        next_step_hint=(
            'Keep the promoted source under normal verification and wait for another live round only after this applied source stays stable.'
            if monitor_status == 'stable'
            else 'Do not widen source promotion until the post-apply monitor is clean.'
        ),
        summary=(
            f'Source promotion post-apply monitor complete: repo={repo_full_name} '
            f'decision_status={pack.decision_status} monitor_status={monitor_status}'
        ),
    )
    report.markdown_summary = render_source_promotion_post_apply_markdown(report)
    return report


def render_ops_refill_report_markdown(report: OpsRefillReport) -> str:
    lines = [
        '# Ops Refill Report',
        '',
        f'- next_create_seed_candidate={report.next_create_seed_candidate or "(none)"}',
        f'- next_prior_family_on_hold={report.next_prior_family_on_hold or "(none)"}',
        f'- next_source_round_status={report.next_source_round_status or "(none)"}',
        f'- Summary: {report.summary}',
        '',
        '## Applied Decisions',
    ]
    if not (
        report.applied_create_seed_candidates
        or report.applied_prior_families
        or report.applied_source_promotions
    ):
        lines.append('- None')
    else:
        for item in report.applied_create_seed_candidates:
            lines.append(f'- create-seed:{item}')
        for item in report.applied_prior_families:
            lines.append(f'- prior-pilot:{item}')
        for item in report.applied_source_promotions:
            lines.append(f'- source-promotion:{item}')
    lines.extend(['', '## Prior Families On Hold'])
    if not report.prior_families_on_hold:
        lines.append('- None')
    else:
        for item in report.prior_families_on_hold:
            lines.append(f'- {item}')
    return '\n'.join(lines).strip()


def build_ops_refill_report(
    *,
    create_seed_pack: RuntimeCreateSeedProposalPack,
    prior_pilot_report: RuntimePriorPilotReport,
    round_report: PublicSourceCurationRoundReport,
    approval_state: OpsApprovalState,
    artifact_root: Optional[Path] = None,
    collections_file: Optional[Path] = None,
) -> OpsRefillReport:
    create_seed_candidates = [
        apply_approval_to_create_seed_proposal(item, approval_state=approval_state, artifact_root=artifact_root)
        for item in list(create_seed_pack.proposals or [])
        if item.recommended_decision in {'review', 'defer'}
    ]
    prior_candidates = [
        apply_approval_to_prior_pilot_profile(item, approval_state=approval_state, artifact_root=artifact_root)
        for item in list(prior_pilot_report.profiles or [])
        if item.recommended_status in {'pilot', 'eligible', 'hold'}
    ]
    next_create_seed_candidate = next(
        (item.candidate_key for item in create_seed_candidates if item.decision_status != 'applied'),
        '',
    )
    next_prior_family_on_hold = next(
        (item.family for item in prior_candidates if item.recommended_status == 'hold'),
        '',
    )
    source_pack = build_public_source_promotion_pack(
        round_report=round_report,
        repo_full_name='alirezarezvani/claude-skills',
        approval_state=approval_state,
        collections_file=collections_file,
    )
    if source_pack.decision_status in {'pending', 'approved_not_applied'}:
        next_source_round_status = 'wait_for_current_source_promotion_resolution'
    elif source_pack.decision_status == 'applied':
        next_source_round_status = 'wait_for_post_apply_stability_before_next_live_round'
    elif round_report.rehearsal_passed:
        next_source_round_status = 'ready_for_next_live_round_when_new_candidates_exist'
    else:
        next_source_round_status = 'rehearsal_required_before_next_live_round'
    report = OpsRefillReport(
        next_create_seed_candidate=next_create_seed_candidate,
        next_prior_family_on_hold=next_prior_family_on_hold,
        next_source_round_status=next_source_round_status,
        create_seed_candidates_considered=[item.candidate_key for item in create_seed_candidates],
        prior_families_on_hold=[item.family for item in prior_candidates if item.recommended_status == 'hold'],
        applied_create_seed_candidates=[item.candidate_key for item in create_seed_candidates if item.decision_status == 'applied'],
        applied_prior_families=[item.family for item in prior_candidates if item.decision_status == 'applied'],
        applied_source_promotions=[source_pack.repo_full_name] if source_pack.decision_status == 'applied' else [],
        source_promoted_repos=list(round_report.promoted_repos or []),
        summary=(
            f'Ops refill report complete: next_create_seed={next_create_seed_candidate or "none"} '
            f'next_prior_hold={next_prior_family_on_hold or "none"} '
            f'next_source_round_status={next_source_round_status}'
        ),
    )
    report.markdown_summary = render_ops_refill_report_markdown(report)
    return report
