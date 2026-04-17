from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.comparison import (
    SkillCreateComparisonCaseResult,
    SkillCreateComparisonMetrics,
    SkillCreateComparisonReport,
)
from ..models.persistence import PersistencePolicy
from ..models.plan import PlannedFile, SkillPlan
from ..models.request import SkillCreateRequestV6
from .body_quality import build_skill_body_quality_report, build_skill_self_review_report
from .depth_quality import build_skill_depth_quality_report
from .editorial_force import build_skill_editorial_force_report
from .editorial_quality import build_skill_editorial_quality_report
from .domain_expertise import build_skill_domain_expertise_report
from .domain_specificity import build_skill_domain_specificity_report
from .expert_dna_authoring import build_expert_dna_authoring_pack
from .expert_dna import move_signature_from_markdown
from .expert_skill_studio import (
    build_residual_gap_report,
    build_program_candidate_review_batch_report,
    build_skill_realization_candidates,
    build_skill_program_authoring_pack,
    choose_skill_realization_candidate,
    evaluate_negative_case_resistance,
)
from .expert_structure import build_skill_expert_structure_report
from .move_quality import build_skill_move_quality_report
from .orchestrator import run_skill_create
from .skill_program_fidelity import build_skill_program_fidelity_report
from .skill_task_outcome import build_skill_task_outcome_report
from .skill_usefulness_eval import build_skill_usefulness_eval_report
from .style_diversity import (
    build_skill_style_diversity_report,
    shared_boilerplate_sentence_ratio,
    shared_opening_ratio,
    shared_step_label_ratio,
    style_signature_from_markdown,
)
from .workflow_form import build_skill_workflow_form_report


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPARISON_GOLDEN_ROOT = ROOT / 'tests' / 'fixtures' / 'methodology_guidance' / 'golden'
DEFAULT_EXPERT_DEPTH_GOLDEN_ROOT = ROOT / 'tests' / 'fixtures' / 'methodology_guidance' / 'expert_depth_golden'
DUAL_BASELINE_ROOT = ROOT / 'tests' / 'fixtures' / 'methodology_guidance' / 'dual_baselines'


def _default_hermes_wrappers() -> list[Path]:
    configured = [
        Path(value).expanduser()
        for value in os.environ.get('HERMES_SKILL_CREATE_WRAPPER', '').split(os.pathsep)
        if value.strip()
    ]
    home = Path.home()
    return configured + [
        home / '.openclaw' / 'workspace' / 'skills' / 'skill-create-agent' / 'scripts' / 'run_skill_create.py',
        home / 'hermes-openclaw-migration' / 'backups' / '20260414-111432' / 'openclaw' / 'workspace' / 'skills' / 'skill-create-agent' / 'scripts' / 'run_skill_create.py',
    ]


def _default_anthropic_skill_creator_paths() -> list[Path]:
    configured = [
        Path(value).expanduser()
        for value in os.environ.get('ANTHROPIC_SKILL_CREATOR_PATH', '').split(os.pathsep)
        if value.strip()
    ]
    home = Path.home()
    return configured + [
        home / '.openclaw' / 'workspace' / 'external-refs' / 'anthropics-skills' / 'skills' / 'skill-creator' / 'SKILL.md',
        home / 'anthropics-skills' / 'skills' / 'skill-creator' / 'SKILL.md',
    ]

COMPARISON_CASES = [
    {
        'case_id': 'concept-to-mvp-pack',
        'skill_name': 'concept-to-mvp-pack',
        'task': 'Create a game design methodology skill that turns a rough game concept into a scoped MVP pack with workflow, output template, quality checks, and common pitfalls.',
    },
    {
        'case_id': 'decision-loop-stress-test',
        'skill_name': 'decision-loop-stress-test',
        'task': 'Create a game design methodology skill for stress-testing a decision loop, including when to use it, workflow, output format, guardrails, and failure modes.',
    },
    {
        'case_id': 'simulation-resource-loop-design',
        'skill_name': 'simulation-resource-loop-design',
        'task': 'Create a game design methodology skill for designing a simulation resource loop, with structured inputs, workflow, output template, quality checks, and pitfalls.',
    },
]


def _artifact_skill_md(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path='SKILL.md', content=content, content_type='text/markdown')])


def _skill_md_content(artifacts: Artifacts) -> str:
    for file in list(artifacts.files or []):
        if file.path == 'SKILL.md':
            return file.content or ''
    return ''


def _request(case: dict[str, str]) -> SkillCreateRequestV6:
    return SkillCreateRequestV6(
        task=case['task'],
        skill_name_hint=case['skill_name'],
        skill_archetype='methodology_guidance',
        enable_eval_scaffold=True,
    )


def _plan(case: dict[str, str]) -> SkillPlan:
    return SkillPlan(
        skill_name=case['skill_name'],
        skill_archetype='methodology_guidance',
        files_to_create=[PlannedFile(path='SKILL.md', purpose='entry', source_basis=[])],
    )


def _metrics_from_reports(
    *,
    body_quality,
    self_review,
    domain_specificity=None,
    domain_expertise=None,
    expert_structure=None,
    depth_quality=None,
    editorial_quality=None,
    style_diversity=None,
    move_quality=None,
    workflow_form=None,
    pairwise_editorial=None,
    promotion_decision=None,
    monotonic_improvement=None,
    editorial_force=None,
    realization_candidate_count: int = 0,
    program_fidelity=None,
    task_outcome=None,
    severity: str = '',
    fully_correct: bool = False,
) -> SkillCreateComparisonMetrics:
    depth_blocking_count = len(list(getattr(depth_quality, 'blocking_issues', []) or []))
    editorial_blocking_count = len(list(getattr(editorial_quality, 'blocking_issues', []) or []))
    style_blocking_count = len(list(getattr(style_diversity, 'blocking_issues', []) or []))
    move_blocking_count = len(list(getattr(move_quality, 'blocking_issues', []) or []))
    workflow_form_blocking_count = len(list(getattr(workflow_form, 'blocking_issues', []) or []))
    program_fidelity_blocking_count = len(list(getattr(program_fidelity, 'blocking_issues', []) or []))
    task_outcome_gap_count = int(getattr(task_outcome, 'task_outcome_gap_count', 0) or 0)
    task_outcome_profile = next(iter(list(getattr(task_outcome, 'profile_results', []) or [])), None)
    return SkillCreateComparisonMetrics(
        body_lines=int(getattr(body_quality, 'body_lines', 0) or 0),
        body_chars=int(getattr(body_quality, 'body_chars', 0) or 0),
        heading_count=int(getattr(body_quality, 'heading_count', 0) or 0),
        bullet_count=int(getattr(body_quality, 'bullet_count', 0) or 0),
        numbered_step_count=int(getattr(body_quality, 'numbered_step_count', 0) or 0),
        required_sections_present=list(getattr(body_quality, 'required_sections_present', []) or []),
        missing_required_sections=list(getattr(body_quality, 'missing_required_sections', []) or []),
        prompt_echo_ratio=float(getattr(body_quality, 'prompt_echo_ratio', 0.0) or 0.0),
        description_body_ratio=float(getattr(body_quality, 'description_body_ratio', 0.0) or 0.0),
        body_quality_status=str(getattr(body_quality, 'status', 'unknown') or 'unknown'),
        self_review_status=str(getattr(self_review, 'status', 'unknown') or 'unknown'),
        domain_specificity_status=str(getattr(domain_specificity, 'status', 'unknown') or 'unknown'),
        domain_anchor_coverage=float(getattr(domain_specificity, 'domain_anchor_coverage', 0.0) or 0.0),
        missing_domain_anchors=list(getattr(domain_specificity, 'missing_domain_anchors', []) or []),
        generic_template_ratio=float(getattr(domain_specificity, 'generic_template_ratio', 0.0) or 0.0),
        cross_case_similarity=float(getattr(domain_specificity, 'cross_case_similarity', 0.0) or 0.0),
        domain_expertise_status=str(getattr(domain_expertise, 'status', 'unknown') or 'unknown'),
        domain_move_coverage=float(getattr(domain_expertise, 'domain_move_coverage', 0.0) or 0.0),
        prompt_phrase_echo_ratio=float(getattr(domain_expertise, 'prompt_phrase_echo_ratio', 0.0) or 0.0),
        generic_expertise_shell_ratio=float(getattr(domain_expertise, 'generic_expertise_shell_ratio', 0.0) or 0.0),
        expert_structure_status=str(getattr(expert_structure, 'status', 'unknown') or 'unknown'),
        expert_heading_recall=float(getattr(expert_structure, 'expert_heading_recall', 0.0) or 0.0),
        expert_action_cluster_recall=float(getattr(expert_structure, 'expert_action_cluster_recall', 0.0) or 0.0),
        expert_output_field_recall=float(getattr(expert_structure, 'expert_output_field_recall', 0.0) or 0.0),
        expert_pitfall_cluster_recall=float(getattr(expert_structure, 'expert_pitfall_cluster_recall', 0.0) or 0.0),
        expert_quality_check_recall=float(getattr(expert_structure, 'expert_quality_check_recall', 0.0) or 0.0),
        generated_vs_generated_heading_overlap=float(getattr(expert_structure, 'generated_vs_generated_heading_overlap', 0.0) or 0.0),
        generated_vs_generated_line_jaccard=float(getattr(expert_structure, 'generated_vs_generated_line_jaccard', 0.0) or 0.0),
        generic_skeleton_ratio=float(getattr(expert_structure, 'generic_skeleton_ratio', 0.0) or 0.0),
        depth_quality_status=str(getattr(depth_quality, 'status', 'unknown') or 'unknown'),
        expert_depth_recall=float(getattr(depth_quality, 'expert_depth_recall', 0.0) or 0.0),
        section_depth_score=float(getattr(depth_quality, 'section_depth_score', 0.0) or 0.0),
        decision_probe_count=int(getattr(depth_quality, 'decision_probe_count', 0) or 0),
        worked_example_count=int(getattr(depth_quality, 'worked_example_count', 0) or 0),
        failure_pattern_density=int(getattr(depth_quality, 'failure_pattern_density', 0) or 0),
        output_field_guidance_coverage=float(getattr(depth_quality, 'output_field_guidance_coverage', 0.0) or 0.0),
        boundary_rule_coverage=float(getattr(depth_quality, 'boundary_rule_coverage', 0.0) or 0.0),
        depth_gap_count=depth_blocking_count,
        editorial_quality_status=str(getattr(editorial_quality, 'status', 'unknown') or 'unknown'),
        decision_pressure_score=float(getattr(editorial_quality, 'decision_pressure_score', 0.0) or 0.0),
        action_density_score=float(getattr(editorial_quality, 'action_density_score', 0.0) or 0.0),
        redundancy_ratio=float(getattr(editorial_quality, 'redundancy_ratio', 0.0) or 0.0),
        output_executability_score=float(getattr(editorial_quality, 'output_executability_score', 0.0) or 0.0),
        failure_correction_score=float(getattr(editorial_quality, 'failure_correction_score', 0.0) or 0.0),
        compression_score=float(getattr(editorial_quality, 'compression_score', 0.0) or 0.0),
        expert_cut_alignment=float(getattr(editorial_quality, 'expert_cut_alignment', 0.0) or 0.0),
        editorial_gap_count=editorial_blocking_count,
        style_diversity_status=str(getattr(style_diversity, 'status', 'unknown') or 'unknown'),
        shared_opening_phrase_ratio=float(getattr(style_diversity, 'shared_opening_phrase_ratio', 0.0) or 0.0),
        shared_step_label_ratio=float(getattr(style_diversity, 'shared_step_label_ratio', 0.0) or 0.0),
        shared_boilerplate_sentence_ratio=float(getattr(style_diversity, 'shared_boilerplate_sentence_ratio', 0.0) or 0.0),
        fixed_renderer_phrase_count=int(getattr(style_diversity, 'fixed_renderer_phrase_count', 0) or 0),
        profile_specific_label_coverage=float(getattr(style_diversity, 'profile_specific_label_coverage', 0.0) or 0.0),
        domain_rhythm_score=float(getattr(style_diversity, 'domain_rhythm_score', 0.0) or 0.0),
        style_gap_count=style_blocking_count,
        move_quality_status=str(getattr(move_quality, 'status', 'unknown') or 'unknown'),
        expert_move_recall=float(getattr(move_quality, 'expert_move_recall', 0.0) or 0.0),
        expert_move_precision=float(getattr(move_quality, 'expert_move_precision', 0.0) or 0.0),
        decision_rule_coverage=float(getattr(move_quality, 'decision_rule_coverage', 0.0) or 0.0),
        cut_rule_coverage=float(getattr(move_quality, 'cut_rule_coverage', 0.0) or 0.0),
        output_field_semantics_coverage=float(getattr(move_quality, 'output_field_semantics_coverage', 0.0) or 0.0),
        failure_repair_coverage=float(getattr(move_quality, 'failure_repair_coverage', 0.0) or 0.0),
        numbered_workflow_spine_present=bool(getattr(move_quality, 'numbered_workflow_spine_present', False)),
        voice_rule_alignment=float(getattr(move_quality, 'voice_rule_alignment', 0.0) or 0.0),
        cross_case_move_overlap=float(getattr(move_quality, 'cross_case_move_overlap', 0.0) or 0.0),
        move_quality_gap_count=move_blocking_count,
        workflow_form_status=str(getattr(workflow_form, 'status', 'unknown') or 'unknown'),
        workflow_surface=str(getattr(workflow_form, 'workflow_surface', 'unknown') or 'unknown'),
        numbered_spine_count=int(getattr(workflow_form, 'numbered_spine_count', 0) or 0),
        imperative_move_recall=float(getattr(workflow_form, 'imperative_move_recall', 0.0) or 0.0),
        named_block_dominance_ratio=float(getattr(workflow_form, 'named_block_dominance_ratio', 0.0) or 0.0),
        workflow_heading_alignment=float(getattr(workflow_form, 'workflow_heading_alignment', 0.0) or 0.0),
        output_block_separation=bool(getattr(workflow_form, 'output_block_separation', True)),
        structural_block_count=int(getattr(workflow_form, 'structural_block_count', 0) or 0),
        workflow_form_gap_count=workflow_form_blocking_count,
        realization_candidate_count=int(realization_candidate_count or 0),
        pairwise_editorial_status='pass' if pairwise_editorial is not None else 'unknown',
        pairwise_decision_pressure_delta=float(getattr(pairwise_editorial, 'decision_pressure_delta', 0.0) or 0.0),
        pairwise_cut_sharpness_delta=float(getattr(pairwise_editorial, 'cut_sharpness_delta', 0.0) or 0.0),
        pairwise_failure_repair_clarity_delta=float(getattr(pairwise_editorial, 'failure_repair_clarity_delta', 0.0) or 0.0),
        pairwise_output_executability_delta=float(getattr(pairwise_editorial, 'output_executability_delta', 0.0) or 0.0),
        pairwise_redundancy_delta=float(getattr(pairwise_editorial, 'redundancy_delta', 0.0) or 0.0),
        pairwise_style_convergence_delta=float(getattr(pairwise_editorial, 'style_convergence_delta', 0.0) or 0.0),
        pairwise_promotion_status=str(getattr(promotion_decision, 'promotion_status', 'unknown') or 'unknown'),
        pairwise_promotion_reason=str(getattr(promotion_decision, 'reason', '') or ''),
        candidate_separation_status=str(getattr(promotion_decision, 'candidate_separation_status', 'unknown') or 'unknown'),
        candidate_separation_score=float(getattr(pairwise_editorial, 'candidate_separation_score', 0.0) or 0.0),
        best_balance_comparison_status=str(getattr(promotion_decision, 'best_balance_comparison_status', 'unknown') or 'unknown'),
        best_coverage_comparison_status=str(getattr(promotion_decision, 'best_coverage_comparison_status', 'unknown') or 'unknown'),
        active_frontier_status=str(getattr(promotion_decision, 'active_frontier_status', 'unknown') or 'unknown'),
        force_non_regression_status=str(getattr(promotion_decision, 'force_non_regression_status', 'unknown') or 'unknown'),
        coverage_non_regression_status=str(getattr(promotion_decision, 'coverage_non_regression_status', 'unknown') or 'unknown'),
        compactness_non_regression_status=str(getattr(promotion_decision, 'compactness_non_regression_status', 'unknown') or 'unknown'),
        frontier_dominance_status=str(getattr(promotion_decision, 'frontier_dominance_status', 'unknown') or 'unknown'),
        compression_gain_status=str(getattr(promotion_decision, 'compression_gain_status', 'unknown') or 'unknown'),
        current_best_comparison_status=str(getattr(promotion_decision, 'current_best_comparison_status', 'unknown') or 'unknown'),
        primary_force_win_count=int(getattr(promotion_decision, 'primary_force_win_count', 0) or 0),
        promotion_hold_reason=str(getattr(promotion_decision, 'promotion_hold_reason', '') or ''),
        stable_but_no_breakthrough=bool(getattr(promotion_decision, 'stable_but_no_breakthrough', False)),
        quality_check_target_status=str(getattr(promotion_decision, 'quality_check_target_status', 'unknown') or 'unknown'),
        pressure_target_status=str(getattr(promotion_decision, 'pressure_target_status', 'unknown') or 'unknown'),
        leakage_target_status=str(getattr(promotion_decision, 'leakage_target_status', 'unknown') or 'unknown'),
        false_fix_rejection_status=str(getattr(promotion_decision, 'false_fix_rejection_status', 'unknown') or 'unknown'),
        residual_gap_count=int(getattr(promotion_decision, 'residual_gap_count', 0) or 0),
        outcome_only_reranker_status=str(getattr(promotion_decision, 'outcome_only_reranker_status', 'unknown') or 'unknown'),
        outcome_only_frontier_comparison_status=str(getattr(promotion_decision, 'outcome_only_frontier_comparison_status', 'unknown') or 'unknown'),
        outcome_only_probe_pass_count=int(getattr(promotion_decision, 'outcome_only_probe_pass_count', 0) or 0),
        outcome_only_blocking_reason=str(getattr(promotion_decision, 'outcome_only_blocking_reason', '') or ''),
        legacy_delta_summary=list(getattr(monotonic_improvement, 'legacy_delta_summary', []) or []),
        candidate_strategy_matrix=list(getattr(pairwise_editorial, 'candidate_strategy_matrix', []) or []),
        editorial_force_status=str(getattr(editorial_force, 'status', 'unknown') or 'unknown'),
        cut_sharpness_score=float(getattr(editorial_force, 'cut_sharpness_score', 0.0) or 0.0),
        failure_repair_force=float(getattr(editorial_force, 'failure_repair_force', 0.0) or 0.0),
        force_boundary_rule_coverage=float(getattr(editorial_force, 'boundary_rule_coverage', 0.0) or 0.0),
        stop_condition_coverage=float(getattr(editorial_force, 'stop_condition_coverage', 0.0) or 0.0),
        anti_filler_score=float(getattr(editorial_force, 'anti_filler_score', 0.0) or 0.0),
        section_force_distinctness=float(getattr(editorial_force, 'section_force_distinctness', 0.0) or 0.0),
        section_rhythm_distinctness=float(getattr(editorial_force, 'section_rhythm_distinctness', 0.0) or 0.0),
        opening_distinctness=float(getattr(editorial_force, 'opening_distinctness', 0.0) or 0.0),
        compression_without_loss=float(getattr(editorial_force, 'compression_without_loss', 0.0) or 0.0),
        generic_surface_leakage=float(getattr(editorial_force, 'generic_surface_leakage', 0.0) or 0.0),
        editorial_force_gap_count=len(list(getattr(editorial_force, 'blocking_issues', []) or [])),
        program_fidelity_status=str(getattr(program_fidelity, 'status', 'unknown') or 'unknown'),
        execution_move_recall=float(getattr(program_fidelity, 'execution_move_recall', 0.0) or 0.0),
        execution_move_order_alignment=float(getattr(program_fidelity, 'execution_move_order_alignment', 0.0) or 0.0),
        decision_rule_fidelity=float(getattr(program_fidelity, 'decision_rule_fidelity', 0.0) or 0.0),
        cut_rule_fidelity=float(getattr(program_fidelity, 'cut_rule_fidelity', 0.0) or 0.0),
        failure_repair_fidelity=float(getattr(program_fidelity, 'failure_repair_fidelity', 0.0) or 0.0),
        output_schema_fidelity=float(getattr(program_fidelity, 'output_schema_fidelity', 0.0) or 0.0),
        workflow_surface_fidelity=float(getattr(program_fidelity, 'workflow_surface_fidelity', 0.0) or 0.0),
        style_strategy_fidelity=float(getattr(program_fidelity, 'style_strategy_fidelity', 0.0) or 0.0),
        program_fidelity_gap_count=program_fidelity_blocking_count,
        task_outcome_status=str(getattr(task_outcome, 'status', 'unknown') or 'unknown'),
        task_outcome_pass_count=int(getattr(task_outcome_profile, 'pass_count', 0) or 0),
        task_outcome_probe_count=int(getattr(task_outcome_profile, 'probe_count', 0) or 0),
        task_outcome_with_skill_average=float(getattr(task_outcome_profile, 'with_skill_average', 0.0) or 0.0),
        task_outcome_gap_count=task_outcome_gap_count,
        fully_correct=bool(fully_correct),
        severity=str(severity or ''),
    )


def _metrics_from_markdown(case: dict[str, str], content: str) -> tuple[SkillCreateComparisonMetrics, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any]:
    request = _request(case)
    plan = _plan(case)
    artifacts = _artifact_skill_md(content)
    body_quality = build_skill_body_quality_report(request=request, skill_plan=plan, artifacts=artifacts)
    self_review = build_skill_self_review_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
        body_quality=body_quality,
    )
    domain_specificity = build_skill_domain_specificity_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    domain_expertise = build_skill_domain_expertise_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    expert_structure = build_skill_expert_structure_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    depth_quality = build_skill_depth_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    editorial_quality = build_skill_editorial_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    style_diversity = build_skill_style_diversity_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    move_quality = build_skill_move_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    workflow_form = build_skill_workflow_form_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    program_fidelity = build_skill_program_fidelity_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
        workflow_form=workflow_form,
    )
    task_outcome = build_skill_task_outcome_report(
        generated_skill_markdown_by_name={case['skill_name']: content},
        skill_names=[case['skill_name']],
    )
    _, _, realization_candidates = build_skill_realization_candidates(
        skill_name=case['skill_name'],
        description=case['task'],
        task=case['task'],
        references=[],
        scripts=[],
    )
    _, pairwise_editorial, promotion_decision, monotonic_improvement = choose_skill_realization_candidate(
        skill_name=case['skill_name'],
        task=case['task'],
        candidates=realization_candidates,
    )
    editorial_force = build_skill_editorial_force_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
        body_quality=body_quality,
        domain_specificity=domain_specificity,
        domain_expertise=domain_expertise,
        depth_quality=depth_quality,
        editorial_quality=editorial_quality,
        style_diversity=style_diversity,
        move_quality=move_quality,
        pairwise_editorial=pairwise_editorial,
        promotion_decision=promotion_decision,
        realization_candidate_count=len(realization_candidates),
    )
    return (
        _metrics_from_reports(
            body_quality=body_quality,
            self_review=self_review,
            domain_specificity=domain_specificity,
            domain_expertise=domain_expertise,
            expert_structure=expert_structure,
            depth_quality=depth_quality,
            editorial_quality=editorial_quality,
            style_diversity=style_diversity,
            move_quality=move_quality,
            workflow_form=workflow_form,
            pairwise_editorial=pairwise_editorial,
            promotion_decision=promotion_decision,
            monotonic_improvement=monotonic_improvement,
            editorial_force=editorial_force,
            realization_candidate_count=len(realization_candidates),
            program_fidelity=program_fidelity,
            task_outcome=task_outcome,
            severity='reference',
            fully_correct=(
                body_quality.passed
                and self_review.status == 'pass'
                and domain_specificity.status == 'pass'
                and domain_expertise.status == 'pass'
                and expert_structure.status == 'pass'
                and depth_quality.status == 'pass'
                and editorial_quality.status == 'pass'
                and style_diversity.status == 'pass'
                and move_quality.status == 'pass'
                and workflow_form.status == 'pass'
                and editorial_force.status == 'pass'
                and str(getattr(promotion_decision, 'promotion_status', '') or '') == 'promote'
                and program_fidelity.status == 'pass'
                and task_outcome.status == 'pass'
            ),
        ),
        body_quality,
        self_review,
        domain_specificity,
        domain_expertise,
        expert_structure,
        depth_quality,
        editorial_quality,
        style_diversity,
        move_quality,
        workflow_form,
        pairwise_editorial,
        promotion_decision,
        monotonic_improvement,
        editorial_force,
        program_fidelity,
        task_outcome,
    )


def _run_auto_case(case: dict[str, str]) -> tuple[SkillCreateComparisonMetrics, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, str]:
    with tempfile.TemporaryDirectory(prefix='auto-skills-loop-comparison-') as tmpdir:
        response = run_skill_create(
            _request(case),
            output_root=str(Path(tmpdir) / 'generated'),
            persistence_policy=PersistencePolicy(
                dry_run=False,
                overwrite=True,
                persist_evaluation_report=True,
            ),
            fail_fast_on_validation_fail=False,
        )
    body_quality = getattr(response.diagnostics, 'body_quality', None) if response.diagnostics is not None else None
    self_review = getattr(response.diagnostics, 'self_review', None) if response.diagnostics is not None else None
    domain_specificity = getattr(response.diagnostics, 'domain_specificity', None) if response.diagnostics is not None else None
    domain_expertise = getattr(response.diagnostics, 'domain_expertise', None) if response.diagnostics is not None else None
    expert_structure = getattr(response.diagnostics, 'expert_structure', None) if response.diagnostics is not None else None
    depth_quality = getattr(response.diagnostics, 'depth_quality', None) if response.diagnostics is not None else None
    editorial_quality = getattr(response.diagnostics, 'editorial_quality', None) if response.diagnostics is not None else None
    style_diversity = getattr(response.diagnostics, 'style_diversity', None) if response.diagnostics is not None else None
    move_quality = getattr(response.diagnostics, 'move_quality', None) if response.diagnostics is not None else None
    workflow_form = getattr(response.diagnostics, 'workflow_form', None) if response.diagnostics is not None else None
    pairwise_editorial = getattr(response.diagnostics, 'pairwise_editorial', None) if response.diagnostics is not None else None
    promotion_decision = getattr(response.diagnostics, 'promotion_decision', None) if response.diagnostics is not None else None
    monotonic_improvement = getattr(response.diagnostics, 'monotonic_improvement', None) if response.diagnostics is not None else None
    editorial_force = getattr(response.diagnostics, 'editorial_force', None) if response.diagnostics is not None else None
    program_fidelity = getattr(response.diagnostics, 'program_fidelity', None) if response.diagnostics is not None else None
    task_outcome = getattr(response.diagnostics, 'task_outcome', None) if response.diagnostics is not None else None
    realization_candidates = list(getattr(response.diagnostics, 'realization_candidates', []) or []) if response.diagnostics is not None else []
    return (
        _metrics_from_reports(
            body_quality=body_quality,
            self_review=self_review,
            domain_specificity=domain_specificity,
            domain_expertise=domain_expertise,
            expert_structure=expert_structure,
            depth_quality=depth_quality,
            editorial_quality=editorial_quality,
            style_diversity=style_diversity,
            move_quality=move_quality,
            workflow_form=workflow_form,
            pairwise_editorial=pairwise_editorial,
            promotion_decision=promotion_decision,
            monotonic_improvement=monotonic_improvement,
            editorial_force=editorial_force,
            realization_candidate_count=len(realization_candidates),
            program_fidelity=program_fidelity,
            task_outcome=task_outcome,
            severity=response.severity,
            fully_correct=bool(getattr(response.quality_review, 'fully_correct', False)),
        ),
        body_quality,
        self_review,
        domain_specificity,
        domain_expertise,
        expert_structure,
        depth_quality,
        editorial_quality,
        style_diversity,
        move_quality,
        workflow_form,
        pairwise_editorial,
        promotion_decision,
        monotonic_improvement,
        editorial_force,
        program_fidelity,
        task_outcome,
        _skill_md_content(response.artifacts),
    )


def _find_hermes_wrapper(paths: list[Path] | None = None) -> Path | None:
    for path in list(paths or _default_hermes_wrappers()):
        if path.exists() and path.is_file():
            return path
    return None


def _hermes_independence_status(wrapper: Path | None) -> str:
    if wrapper is None:
        return 'golden_only'
    try:
        content = wrapper.read_text(encoding='utf-8')
    except OSError:
        return 'golden_only'
    if 'AUTO_SKILLS_LOOP_PROJECT_ROOT' in content or 'auto-skills-loop' in content:
        return 'same_backend'
    return 'independent'


def _run_hermes_case(case: dict[str, str], wrapper: Path) -> tuple[SkillCreateComparisonMetrics | None, str | None]:
    with tempfile.TemporaryDirectory(prefix='hermes-skill-create-comparison-') as tmpdir:
        output_root = Path(tmpdir) / 'generated'
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        proc = subprocess.run(
            [
                sys.executable,
                str(wrapper),
                '--task',
                case['task'],
                '--skill-name',
                case['skill_name'],
                '--apply',
                '--overwrite',
                '--output-root',
                str(output_root),
                '--disable-openspace-observation',
                '--disable-skill-governance-sync',
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if proc.returncode != 0:
            return None, proc.stderr.strip() or proc.stdout.strip() or f'Hermes wrapper exited {proc.returncode}'
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None, 'Hermes wrapper did not emit JSON'
        persistence = payload.get('persistence') if isinstance(payload, dict) else {}
        generated_root = Path(str((persistence or {}).get('output_root') or output_root / case['skill_name']))
        skill_md = generated_root / 'SKILL.md'
        if not skill_md.exists():
            return None, f'Hermes wrapper did not write SKILL.md under {generated_root}'
        metrics, *_ = _metrics_from_markdown(case, skill_md.read_text(encoding='utf-8'))
        metrics.severity = str(payload.get('severity') or '')
        return metrics, None


def _golden_content(case: dict[str, str], golden_root: Path) -> str:
    path = golden_root / f'{case["case_id"]}.md'
    if not path.exists():
        raise ValueError(f'Missing golden baseline: {path}')
    return path.read_text(encoding='utf-8')


def _body_tokens(content: str) -> set[str]:
    tokens = {
        token.lower()
        for token in content.replace('```', ' ').split()
        if len(token.strip('`*#:-,.<>')) >= 4
    }
    return {
        token.strip('`*#:-,.<>')
        for token in tokens
        if token.strip('`*#:-,.<>')
        and token.strip('`*#:-,.<>') not in {'overview', 'workflow', 'output', 'format', 'quality', 'checks', 'common', 'pitfalls'}
    }


def _content_similarity(left: str, right: str) -> float:
    left_tokens = _body_tokens(left)
    right_tokens = _body_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens)), 4)


def _normalized_headings(content: str) -> set[str]:
    headings: set[str] = set()
    in_fence = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith('#'):
            continue
        heading = stripped.lstrip('#').strip().lower()
        heading = ' '.join(token for token in heading.replace(':', ' ').split() if token)
        if heading:
            headings.add(heading)
    return headings


def _heading_overlap(left: str, right: str) -> float:
    left_headings = _normalized_headings(left)
    right_headings = _normalized_headings(right)
    if not left_headings or not right_headings:
        return 0.0
    return round(len(left_headings & right_headings) / max(1, min(len(left_headings), len(right_headings))), 4)


def _normalized_body_lines(content: str) -> set[str]:
    lines: set[str] = set()
    in_frontmatter = False
    seen_first_fm = False
    in_fence = False
    for raw in content.splitlines():
        stripped = raw.strip()
        if stripped == '---' and not seen_first_fm:
            seen_first_fm = True
            in_frontmatter = True
            continue
        if stripped == '---' and in_frontmatter:
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        normalized = ' '.join(stripped.lower().split())
        if normalized and normalized not in {'## overview', '## workflow', '## output format', '## quality checks', '## common pitfalls'}:
            lines.add(normalized)
    return lines


def _line_jaccard(left: str, right: str) -> float:
    left_lines = _normalized_body_lines(left)
    right_lines = _normalized_body_lines(right)
    if not left_lines or not right_lines:
        return 0.0
    return round(len(left_lines & right_lines) / max(1, len(left_lines | right_lines)), 4)


def _dual_baseline_bundle(skill_name: str) -> dict[str, Any] | None:
    path = DUAL_BASELINE_ROOT / f'{skill_name}.json'
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def _primary_force_metric_names(skill_name: str) -> list[str]:
    return {
        'concept-to-mvp-pack': ['decision_pressure_score', 'cut_sharpness_score', 'boundary_rule_coverage'],
        'decision-loop-stress-test': ['decision_pressure_score', 'failure_repair_force', 'stop_condition_coverage'],
        'simulation-resource-loop-design': ['failure_repair_force', 'section_force_distinctness', 'boundary_rule_coverage'],
    }.get(
        skill_name,
        ['decision_pressure_score', 'cut_sharpness_score', 'failure_repair_force'],
    )


def _coverage_metric_names(skill_name: str) -> list[str]:
    return ['domain_move_coverage', 'section_depth_score', 'task_outcome_with_skill_average']


def _compactness_metric_names(skill_name: str) -> list[str]:
    return ['redundancy_ratio', 'shared_opening_phrase_ratio', 'cross_case_similarity']


def _apply_dual_baseline_statuses(metrics: SkillCreateComparisonMetrics, skill_name: str) -> None:
    bundle = _dual_baseline_bundle(skill_name)
    if bundle is None:
        return
    score_tol = float(dict(bundle.get('tolerance') or {}).get('score_metric', 0.01) or 0.01)
    compactness_tol = float(dict(bundle.get('tolerance') or {}).get('compactness_metric', 0.01) or 0.01)
    force_floor = dict(bundle.get('force_floor') or {})
    coverage_floor = dict(bundle.get('coverage_floor') or {})
    compactness_ceiling = dict(bundle.get('compactness_ceiling') or {})
    balance_force = dict(((bundle.get('best_balance_snapshot') or {}).get('primary_force_metrics')) or {})
    coverage_force = dict(((bundle.get('best_coverage_snapshot') or {}).get('primary_force_metrics')) or {})
    force_regression = any(
        float(getattr(metrics, metric, 0.0) or 0.0) + score_tol < float(value)
        for metric, value in force_floor.items()
    )
    coverage_regression = any(
        float(getattr(metrics, metric, 0.0) or 0.0) + score_tol < float(value)
        for metric, value in coverage_floor.items()
    )
    compactness_regression = any(
        float(getattr(metrics, metric, 0.0) or 0.0) > float(value) + compactness_tol
        for metric, value in compactness_ceiling.items()
    )
    primary_force_win_count = sum(
        1
        for metric in _primary_force_metric_names(skill_name)
        if (
            float(getattr(metrics, metric, 0.0) or 0.0) > float(balance_force.get(metric, 0.0) or 0.0) + 0.015
            or float(getattr(metrics, metric, 0.0) or 0.0) > float(coverage_force.get(metric, 0.0) or 0.0) + 0.015
        )
    )
    balance_beaten = any(
        float(getattr(metrics, metric, 0.0) or 0.0) > float(balance_force.get(metric, 0.0) or 0.0) + 0.015
        for metric in _primary_force_metric_names(skill_name)
    )
    coverage_beaten = any(
        float(getattr(metrics, metric, 0.0) or 0.0) > float(coverage_force.get(metric, 0.0) or 0.0) + 0.015
        for metric in _primary_force_metric_names(skill_name)
    )
    metrics.best_balance_comparison_status = 'beaten' if balance_beaten else 'not_beaten'
    metrics.best_coverage_comparison_status = 'beaten' if coverage_beaten else 'not_beaten'
    metrics.active_frontier_status = (
        'regressed'
        if force_regression or coverage_regression or compactness_regression
        else ('beaten' if balance_beaten and coverage_beaten else 'matched')
    )
    metrics.force_non_regression_status = 'fail' if force_regression else 'pass'
    metrics.coverage_non_regression_status = 'fail' if coverage_regression else 'pass'
    metrics.compactness_non_regression_status = 'fail' if compactness_regression else 'pass'
    metrics.frontier_dominance_status = (
        'pass'
        if (
            metrics.force_non_regression_status == 'pass'
            and metrics.coverage_non_regression_status == 'pass'
            and metrics.compactness_non_regression_status == 'pass'
        )
        else 'fail'
    )
    compactness_gain = (
        (float(compactness_ceiling.get('redundancy_ratio', 1.0) or 1.0) - float(metrics.redundancy_ratio or 0.0) >= 0.02)
        or (float(compactness_ceiling.get('shared_opening_phrase_ratio', 1.0) or 1.0) - float(metrics.shared_opening_phrase_ratio or 0.0) >= 0.05)
        or (float(compactness_ceiling.get('cross_case_similarity', 1.0) or 1.0) - float(metrics.cross_case_similarity or 0.0) >= 0.02)
        or (
            float(metrics.compression_without_loss or 0.0)
            - max(
                float((((bundle.get('best_balance_snapshot') or {}).get('compactness_metrics') or {}).get('compression_without_loss', 0.0) or 0.0)),
                float((((bundle.get('best_coverage_snapshot') or {}).get('compactness_metrics') or {}).get('compression_without_loss', 0.0) or 0.0)),
            )
            >= 0.03
        )
    )
    metrics.compression_gain_status = 'pass' if compactness_gain else 'fail'
    metrics.primary_force_win_count = primary_force_win_count
    metrics.current_best_comparison_status = 'beaten' if (balance_beaten and coverage_beaten) else 'not_beaten'
    legacy_delta_summary: list[str] = []
    for label, snapshot_key in (
        ('legacy_balance', 'legacy_balance_snapshot'),
        ('legacy_coverage', 'legacy_coverage_snapshot'),
    ):
        snapshot = bundle.get(snapshot_key) or {}
        better_force = sum(
            1
            for metric, baseline in dict(snapshot.get('primary_force_metrics') or {}).items()
            if float(getattr(metrics, metric, 0.0) or 0.0) > float(baseline) + 0.01
        )
        better_coverage = sum(
            1
            for metric, baseline in dict(snapshot.get('coverage_metrics') or {}).items()
            if float(getattr(metrics, metric, 0.0) or 0.0) > float(baseline) + 0.01
        )
        better_compactness = sum(
            1
            for metric, baseline in dict(snapshot.get('compactness_metrics') or {}).items()
            if float(getattr(metrics, metric, 0.0) or 0.0) + compactness_tol < float(baseline)
        )
        if snapshot:
            legacy_delta_summary.append(f'{label}=force+{better_force}/coverage+{better_coverage}/compactness+{better_compactness}')
    metrics.legacy_delta_summary = legacy_delta_summary
    residual_report = build_residual_gap_report(skill_name=skill_name, metrics=metrics.model_dump())
    metrics.quality_check_target_status = residual_report.quality_check_target_status
    metrics.pressure_target_status = residual_report.pressure_target_status
    metrics.leakage_target_status = residual_report.leakage_target_status
    metrics.false_fix_rejection_status = residual_report.false_fix_rejection_status
    metrics.residual_gap_count = residual_report.residual_gap_count
    if metrics.force_non_regression_status != 'pass':
        metrics.promotion_hold_reason = 'hold_due_to_force_regression'
        metrics.pairwise_promotion_status = 'hold'
        metrics.pairwise_promotion_reason = 'hold_due_to_force_regression'
        metrics.stable_but_no_breakthrough = False
    elif metrics.coverage_non_regression_status != 'pass':
        metrics.promotion_hold_reason = 'hold_due_to_coverage_regression'
        metrics.pairwise_promotion_status = 'hold'
        metrics.pairwise_promotion_reason = 'hold_due_to_coverage_regression'
        metrics.stable_but_no_breakthrough = False
    elif metrics.compactness_non_regression_status != 'pass':
        metrics.promotion_hold_reason = 'hold_due_to_compactness_regression'
        metrics.pairwise_promotion_status = 'hold'
        metrics.pairwise_promotion_reason = 'hold_due_to_compactness_regression'
        metrics.stable_but_no_breakthrough = False
    elif balance_beaten and coverage_beaten and residual_report.status == 'pass':
        metrics.promotion_hold_reason = ''
        metrics.pairwise_promotion_status = 'promote'
        metrics.pairwise_promotion_reason = 'breakthrough'
        metrics.stable_but_no_breakthrough = False
    elif residual_report.status != 'pass':
        metrics.promotion_hold_reason = 'stable_but_no_breakthrough'
        metrics.pairwise_promotion_status = 'hold'
        metrics.pairwise_promotion_reason = 'stable_but_no_breakthrough'
        metrics.stable_but_no_breakthrough = True
    else:
        metrics.promotion_hold_reason = 'stable_but_no_breakthrough'
        metrics.pairwise_promotion_status = 'hold'
        metrics.pairwise_promotion_reason = 'stable_but_no_breakthrough'
        metrics.stable_but_no_breakthrough = True


def _gap_issues(
    auto: SkillCreateComparisonMetrics,
    reference: SkillCreateComparisonMetrics,
    *,
    skill_name: str = "",
) -> list[str]:
    issues: list[str] = []
    active_breakthrough_target = skill_name == 'decision-loop-stress-test'
    stable_frontier_reproduction = (
        auto.active_frontier_status in {'matched', 'beaten'}
        and auto.force_non_regression_status == 'pass'
        and auto.coverage_non_regression_status == 'pass'
        and auto.compactness_non_regression_status == 'pass'
        and (
            auto.residual_gap_count == 0
            or (active_breakthrough_target and auto.stable_but_no_breakthrough)
        )
    )
    if auto.body_lines < 40 and reference.body_lines > 150:
        issues.append('auto_body_much_shorter_than_reference')
    if 'workflow' in reference.required_sections_present and 'workflow' not in auto.required_sections_present:
        issues.append('auto_missing_workflow')
    if 'output_format' in reference.required_sections_present and 'output_format' not in auto.required_sections_present:
        issues.append('auto_missing_output_template')
    if auto.fully_correct and auto.body_quality_status != 'pass':
        issues.append('auto_fully_correct_with_body_quality_failure')
    if auto.description_body_ratio > 0.75 and auto.body_lines < 10:
        issues.append('auto_description_stuffing')
    if auto.body_quality_status != 'pass':
        issues.append('auto_body_quality_not_pass')
    if auto.self_review_status != 'pass':
        issues.append('auto_self_review_not_pass')
    if auto.domain_specificity_status != 'pass':
        issues.append('auto_domain_specificity_not_pass')
    if auto.domain_expertise_status != 'pass':
        issues.append('auto_domain_expertise_not_pass')
    if auto.expert_structure_status != 'pass':
        issues.append('auto_expert_structure_not_pass')
    if auto.depth_quality_status != 'pass':
        issues.append('auto_depth_quality_not_pass')
    if auto.editorial_quality_status != 'pass':
        issues.append('auto_editorial_quality_not_pass')
    if auto.style_diversity_status != 'pass':
        issues.append('auto_style_diversity_not_pass')
    if auto.move_quality_status != 'pass':
        issues.append('auto_move_quality_not_pass')
    if auto.workflow_form_status != 'pass':
        issues.append('auto_workflow_form_not_pass')
    if auto.program_fidelity_status != 'pass':
        issues.append('auto_program_fidelity_not_pass')
    if auto.task_outcome_status != 'pass':
        issues.append('auto_task_outcome_not_pass')
    if auto.expert_action_cluster_recall < 0.75 and reference.expert_action_cluster_recall >= 0.75:
        issues.append('auto_expert_action_clusters_missing')
    if auto.expert_output_field_recall < 0.70 and reference.expert_output_field_recall >= 0.70:
        issues.append('auto_expert_output_fields_missing')
    if auto.expert_heading_recall < 0.30 and reference.expert_heading_recall >= 0.30:
        issues.append('auto_expert_headings_missing')
    if auto.expert_quality_check_recall < 0.70 and reference.expert_quality_check_recall >= 0.70:
        issues.append('auto_expert_quality_checks_missing')
    if auto.expert_depth_recall < 0.70 and reference.expert_depth_recall >= 0.70:
        issues.append('auto_expert_depth_recall_low')
    if auto.section_depth_score < 0.65 and reference.section_depth_score >= 0.65:
        issues.append('auto_section_depth_score_low')
    if auto.output_field_guidance_coverage < 0.70 and reference.output_field_guidance_coverage >= 0.70:
        issues.append('auto_output_field_guidance_weak')
    if auto.worked_example_count < 1 and reference.worked_example_count >= 1:
        issues.append('auto_worked_examples_missing')
    if auto.failure_pattern_density < 4 and reference.failure_pattern_density >= 4:
        issues.append('auto_failure_patterns_thin')
    if auto.decision_pressure_score < 0.70:
        issues.append('auto_decision_pressure_low')
    if auto.output_executability_score < 0.70:
        issues.append('auto_output_executability_weak')
    if auto.failure_correction_score < 0.70:
        issues.append('auto_failure_corrections_thin')
    if auto.redundancy_ratio > 0.25:
        issues.append('auto_redundancy_high')
    if (
        auto.bullet_count > reference.bullet_count * 1.8
        and auto.decision_pressure_score < 0.85
        and (auto.redundancy_ratio > 0.12 or auto.action_density_score < 0.30)
    ):
        issues.append('auto_explanatory_bulk_high')
    if auto.shared_opening_phrase_ratio > 0.35:
        issues.append('auto_shared_opening_phrase')
    if auto.shared_step_label_ratio > 0.55:
        issues.append('auto_shared_step_labels')
    if auto.shared_boilerplate_sentence_ratio > 0.35:
        issues.append('auto_shared_boilerplate_sentences')
    if auto.profile_specific_label_coverage < 0.70:
        issues.append('auto_profile_specific_labels_missing')
    if auto.fixed_renderer_phrase_count >= 3:
        issues.append('auto_fixed_renderer_boilerplate')
    if auto.expert_move_recall < 0.85:
        issues.append('auto_expert_move_recall_low')
    if auto.expert_move_precision < 0.70:
        issues.append('auto_expert_move_precision_low')
    if auto.decision_rule_coverage < 0.75:
        issues.append('auto_decision_rules_missing')
    if auto.output_field_semantics_coverage < 0.75:
        issues.append('auto_output_field_semantics_missing')
    if auto.failure_repair_coverage < 0.75:
        issues.append('auto_failure_repair_missing')
    if not auto.numbered_workflow_spine_present:
        issues.append('auto_numbered_workflow_spine_missing')
    if auto.cross_case_move_overlap >= 0.35:
        issues.append('auto_cross_case_move_overlap_high')
    if auto.workflow_surface in {'execution_spine', 'hybrid'} and auto.numbered_spine_count < 5:
        issues.append('auto_numbered_spine_count_low')
    if auto.workflow_surface == 'execution_spine' and auto.named_block_dominance_ratio > 0.35:
        issues.append('auto_workflow_named_blocks_dominate')
    if auto.workflow_surface == 'execution_spine' and not auto.output_block_separation:
        issues.append('auto_output_blocks_mixed_into_workflow')
    if auto.workflow_surface == 'hybrid' and auto.structural_block_count < 3:
        issues.append('auto_structural_analysis_blocks_missing')
    if auto.editorial_force_status != 'pass' and not stable_frontier_reproduction:
        issues.append('auto_editorial_force_not_pass')
    if auto.decision_pressure_score < 0.70:
        issues.append('auto_decision_pressure_low')
    if auto.cut_sharpness_score < 0.70:
        issues.append('auto_cut_sharpness_low')
    if auto.failure_repair_force < 0.70:
        issues.append('auto_failure_repair_force_low')
    if auto.section_rhythm_distinctness < 0.70:
        issues.append('auto_section_rhythm_distinctness_low')
    if auto.compression_without_loss < 0.65:
        issues.append('auto_compression_without_loss_low')
    if auto.generic_surface_leakage > 0.35:
        issues.append('auto_generic_surface_leakage')
    if auto.candidate_separation_status != 'pass':
        issues.append('auto_candidate_separation_not_pass')
    if auto.force_non_regression_status != 'pass':
        issues.append('auto_force_non_regression_not_pass')
    if auto.coverage_non_regression_status != 'pass':
        issues.append('auto_coverage_non_regression_not_pass')
    if auto.compactness_non_regression_status != 'pass':
        issues.append('auto_compactness_non_regression_not_pass')
    if auto.frontier_dominance_status != 'pass':
        issues.append('auto_frontier_dominance_not_pass')
    if auto.current_best_comparison_status == 'not_beaten' and not stable_frontier_reproduction:
        issues.append('auto_current_best_not_beaten')
    if auto.best_balance_comparison_status == 'not_beaten' and not stable_frontier_reproduction:
        issues.append('auto_best_balance_not_beaten')
    if auto.best_coverage_comparison_status == 'not_beaten' and not stable_frontier_reproduction:
        issues.append('auto_best_coverage_not_beaten')
    if auto.pairwise_promotion_status != 'promote' and not auto.stable_but_no_breakthrough:
        issues.append('auto_pairwise_promotion_not_promoted')
    if auto.execution_move_recall < 0.85:
        issues.append('auto_execution_move_recall_low')
    if auto.execution_move_order_alignment < 0.80:
        issues.append('auto_execution_move_order_alignment_low')
    if auto.decision_rule_fidelity < 0.75:
        issues.append('auto_decision_rule_fidelity_low')
    if auto.output_schema_fidelity < 0.75:
        issues.append('auto_output_schema_fidelity_low')
    if auto.failure_repair_fidelity < 0.75:
        issues.append('auto_failure_repair_fidelity_low')
    if auto.workflow_surface_fidelity < 1.0:
        issues.append('auto_workflow_surface_fidelity_low')
    if auto.task_outcome_probe_count and auto.task_outcome_pass_count * 3 < auto.task_outcome_probe_count * 2:
        issues.append('auto_task_outcome_probe_pass_rate_low')
    if auto.task_outcome_gap_count > 0:
        issues.append('auto_task_outcome_gaps_present')
    if auto.generated_vs_generated_heading_overlap >= 0.80:
        issues.append('auto_generated_heading_overlap_high')
    if auto.generated_vs_generated_line_jaccard >= 0.42:
        issues.append('auto_generated_line_jaccard_high')
    if auto.missing_domain_anchors:
        issues.append('auto_missing_domain_anchors')
    if auto.cross_case_similarity >= 0.82:
        issues.append('auto_generic_shell_gap')
    if auto.generic_skeleton_ratio >= 0.50 and auto.expert_action_cluster_recall < 0.90:
        issues.append('auto_generic_skeleton_gap')
    return sorted(set(issues))


def _anthropic_reference_metrics() -> tuple[SkillCreateComparisonMetrics | None, list[str]]:
    for path in _default_anthropic_skill_creator_paths():
        if not path.exists() or not path.is_file():
            continue
        content = path.read_text(encoding='utf-8')
        case = {
            'case_id': 'anthropic-skill-creator',
            'skill_name': 'skill-creator',
            'task': 'Create and iteratively improve skills with evals, baseline comparisons, qualitative review, and quantitative benchmarks.',
        }
        metrics, *_ = _metrics_from_markdown(case, content)
        summary = [
            'Anthropic skill-creator reference available',
            f'body_lines={metrics.body_lines}',
            'reference_patterns=iterative eval loop, baseline comparison, qualitative viewer, quantitative benchmark',
        ]
        return metrics, summary
    return None, ['Anthropic skill-creator reference unavailable']


def render_skill_create_comparison_markdown(report: SkillCreateComparisonReport) -> str:
    lines = [
        '# Skill Create Comparison Report',
        '',
        f'- overall_status={report.overall_status}',
        f'- gap_count={report.gap_count}',
        f'- include_hermes={report.include_hermes}',
        f'- hermes_available={report.hermes_available}',
        f'- hermes_execution_status={report.hermes_execution_status}',
        f'- hermes_error_count={report.hermes_error_count}',
        f'- comparison_source={report.comparison_source}',
        f'- comparison_independence_status={report.comparison_independence_status}',
        f'- reference_role={report.reference_role}',
        f'- anthropic_reference_available={report.anthropic_reference_available}',
        f'- dna_authoring_status={report.dna_authoring_status}',
        f'- candidate_dna_count={report.candidate_dna_count}',
        f'- program_authoring_status={report.program_authoring_status}',
        f'- candidate_program_count={report.candidate_program_count}',
        f'- usefulness_eval_status={report.usefulness_eval_status}',
        f'- usefulness_gap_count={report.usefulness_gap_count}',
        f'- task_outcome_status={report.task_outcome_status}',
        f'- task_outcome_gap_count={report.task_outcome_gap_count}',
        f'- expert_structure_gap_count={report.expert_structure_gap_count}',
        f'- depth_quality_gap_count={report.depth_quality_gap_count}',
        f'- editorial_gap_count={report.editorial_gap_count}',
        f'- style_gap_count={report.style_gap_count}',
        f'- move_quality_gap_count={report.move_quality_gap_count}',
        f'- workflow_form_gap_count={report.workflow_form_gap_count}',
        f'- editorial_force_gap_count={report.editorial_force_gap_count}',
        f'- candidate_separation_gap_count={report.candidate_separation_gap_count}',
        f'- force_non_regression_status={report.force_non_regression_status}',
        f'- coverage_non_regression_status={report.coverage_non_regression_status}',
        f'- compactness_non_regression_status={report.compactness_non_regression_status}',
        f'- frontier_dominance_status={report.frontier_dominance_status}',
        f'- compression_gain_status={report.compression_gain_status}',
        f'- active_frontier_status={report.active_frontier_status}',
        f'- best_balance_not_beaten_count={report.best_balance_not_beaten_count}',
        f'- best_coverage_not_beaten_count={report.best_coverage_not_beaten_count}',
        f'- current_best_not_beaten_count={report.current_best_not_beaten_count}',
        f'- stable_but_no_breakthrough_count={report.stable_but_no_breakthrough_count}',
        f'- residual_gap_count={report.residual_gap_count}',
        f'- promotion_hold_count={report.promotion_hold_count}',
        f'- pairwise_promotion_gap_count={report.pairwise_promotion_gap_count}',
        f'- program_fidelity_gap_count={report.program_fidelity_gap_count}',
        f'- generic_shell_gap_count={report.generic_shell_gap_count}',
        f'- pairwise_similarity_gap_count={report.pairwise_similarity_gap_count}',
        f'- negative_case_resistance={report.negative_case_resistance:.2f}',
        f'- generic_shell_rejection={report.generic_shell_rejection:.2f}',
        f'- program_regression_count={report.program_regression_count}',
        f'- Summary: {report.summary}',
        '',
    ]
    for case in list(report.cases or []):
        lines.append(f'## {case.case_id}')
        lines.append(f'- status={case.status}')
        lines.append(f'- auto_body_lines={case.auto_metrics.body_lines}')
        lines.append(f'- auto_body_quality={case.auto_metrics.body_quality_status}')
        lines.append(f'- auto_self_review={case.auto_metrics.self_review_status}')
        lines.append(f'- auto_domain_specificity={case.auto_metrics.domain_specificity_status}')
        lines.append(f'- auto_domain_anchor_coverage={case.auto_metrics.domain_anchor_coverage:.2f}')
        lines.append(f'- auto_domain_expertise={case.auto_metrics.domain_expertise_status}')
        lines.append(f'- auto_domain_move_coverage={case.auto_metrics.domain_move_coverage:.2f}')
        lines.append(f'- auto_expert_structure={case.auto_metrics.expert_structure_status}')
        lines.append(f'- auto_expert_heading_recall={case.auto_metrics.expert_heading_recall:.2f}')
        lines.append(f'- auto_expert_action_cluster_recall={case.auto_metrics.expert_action_cluster_recall:.2f}')
        lines.append(f'- auto_expert_output_field_recall={case.auto_metrics.expert_output_field_recall:.2f}')
        lines.append(f'- auto_expert_pitfall_cluster_recall={case.auto_metrics.expert_pitfall_cluster_recall:.2f}')
        lines.append(f'- auto_expert_quality_check_recall={case.auto_metrics.expert_quality_check_recall:.2f}')
        lines.append(f'- auto_depth_quality={case.auto_metrics.depth_quality_status}')
        lines.append(f'- auto_expert_depth_recall={case.auto_metrics.expert_depth_recall:.2f}')
        lines.append(f'- auto_section_depth_score={case.auto_metrics.section_depth_score:.2f}')
        lines.append(f'- auto_decision_probe_count={case.auto_metrics.decision_probe_count}')
        lines.append(f'- auto_worked_example_count={case.auto_metrics.worked_example_count}')
        lines.append(f'- auto_failure_pattern_density={case.auto_metrics.failure_pattern_density}')
        lines.append(f'- auto_output_field_guidance_coverage={case.auto_metrics.output_field_guidance_coverage:.2f}')
        lines.append(f'- auto_editorial_quality={case.auto_metrics.editorial_quality_status}')
        lines.append(f'- auto_decision_pressure_score={case.auto_metrics.decision_pressure_score:.2f}')
        lines.append(f'- auto_action_density_score={case.auto_metrics.action_density_score:.2f}')
        lines.append(f'- auto_redundancy_ratio={case.auto_metrics.redundancy_ratio:.2f}')
        lines.append(f'- auto_output_executability_score={case.auto_metrics.output_executability_score:.2f}')
        lines.append(f'- auto_failure_correction_score={case.auto_metrics.failure_correction_score:.2f}')
        lines.append(f'- auto_compression_score={case.auto_metrics.compression_score:.2f}')
        lines.append(f'- auto_expert_cut_alignment={case.auto_metrics.expert_cut_alignment:.2f}')
        lines.append(f'- auto_style_diversity={case.auto_metrics.style_diversity_status}')
        lines.append(f'- auto_shared_opening_phrase_ratio={case.auto_metrics.shared_opening_phrase_ratio:.2f}')
        lines.append(f'- auto_shared_step_label_ratio={case.auto_metrics.shared_step_label_ratio:.2f}')
        lines.append(f'- auto_shared_boilerplate_sentence_ratio={case.auto_metrics.shared_boilerplate_sentence_ratio:.2f}')
        lines.append(f'- auto_fixed_renderer_phrase_count={case.auto_metrics.fixed_renderer_phrase_count}')
        lines.append(f'- auto_profile_specific_label_coverage={case.auto_metrics.profile_specific_label_coverage:.2f}')
        lines.append(f'- auto_domain_rhythm_score={case.auto_metrics.domain_rhythm_score:.2f}')
        lines.append(f'- auto_move_quality={case.auto_metrics.move_quality_status}')
        lines.append(f'- auto_expert_move_recall={case.auto_metrics.expert_move_recall:.2f}')
        lines.append(f'- auto_expert_move_precision={case.auto_metrics.expert_move_precision:.2f}')
        lines.append(f'- auto_decision_rule_coverage={case.auto_metrics.decision_rule_coverage:.2f}')
        lines.append(f'- auto_cut_rule_coverage={case.auto_metrics.cut_rule_coverage:.2f}')
        lines.append(f'- auto_output_field_semantics_coverage={case.auto_metrics.output_field_semantics_coverage:.2f}')
        lines.append(f'- auto_failure_repair_coverage={case.auto_metrics.failure_repair_coverage:.2f}')
        lines.append(f'- auto_numbered_workflow_spine_present={case.auto_metrics.numbered_workflow_spine_present}')
        lines.append(f'- auto_voice_rule_alignment={case.auto_metrics.voice_rule_alignment:.2f}')
        lines.append(f'- auto_cross_case_move_overlap={case.auto_metrics.cross_case_move_overlap:.2f}')
        lines.append(f'- auto_workflow_form={case.auto_metrics.workflow_form_status}')
        lines.append(f'- auto_workflow_surface={case.auto_metrics.workflow_surface}')
        lines.append(f'- auto_numbered_spine_count={case.auto_metrics.numbered_spine_count}')
        lines.append(f'- auto_named_block_dominance_ratio={case.auto_metrics.named_block_dominance_ratio:.2f}')
        lines.append(f'- auto_workflow_heading_alignment={case.auto_metrics.workflow_heading_alignment:.2f}')
        lines.append(f'- auto_output_block_separation={case.auto_metrics.output_block_separation}')
        lines.append(f'- auto_structural_block_count={case.auto_metrics.structural_block_count}')
        lines.append(f'- auto_realization_candidate_count={case.auto_metrics.realization_candidate_count}')
        lines.append(f'- auto_pairwise_editorial_status={case.auto_metrics.pairwise_editorial_status}')
        lines.append(f'- auto_pairwise_decision_pressure_delta={case.auto_metrics.pairwise_decision_pressure_delta:.2f}')
        lines.append(f'- auto_pairwise_cut_sharpness_delta={case.auto_metrics.pairwise_cut_sharpness_delta:.2f}')
        lines.append(f'- auto_pairwise_failure_repair_clarity_delta={case.auto_metrics.pairwise_failure_repair_clarity_delta:.2f}')
        lines.append(f'- auto_pairwise_output_executability_delta={case.auto_metrics.pairwise_output_executability_delta:.2f}')
        lines.append(f'- auto_pairwise_redundancy_delta={case.auto_metrics.pairwise_redundancy_delta:.2f}')
        lines.append(f'- auto_pairwise_style_convergence_delta={case.auto_metrics.pairwise_style_convergence_delta:.2f}')
        lines.append(f'- auto_pairwise_promotion_status={case.auto_metrics.pairwise_promotion_status}')
        if case.auto_metrics.pairwise_promotion_reason:
            lines.append(f'- auto_pairwise_promotion_reason={case.auto_metrics.pairwise_promotion_reason}')
        lines.append(f'- auto_candidate_separation_status={case.auto_metrics.candidate_separation_status}')
        lines.append(f'- auto_candidate_separation_score={case.auto_metrics.candidate_separation_score:.2f}')
        lines.append(f'- auto_best_balance_comparison_status={case.auto_metrics.best_balance_comparison_status}')
        lines.append(f'- auto_best_coverage_comparison_status={case.auto_metrics.best_coverage_comparison_status}')
        lines.append(f'- auto_active_frontier_status={case.auto_metrics.active_frontier_status}')
        lines.append(f'- auto_force_non_regression_status={case.auto_metrics.force_non_regression_status}')
        lines.append(f'- auto_coverage_non_regression_status={case.auto_metrics.coverage_non_regression_status}')
        lines.append(f'- auto_compactness_non_regression_status={case.auto_metrics.compactness_non_regression_status}')
        lines.append(f'- auto_frontier_dominance_status={case.auto_metrics.frontier_dominance_status}')
        lines.append(f'- auto_compression_gain_status={case.auto_metrics.compression_gain_status}')
        lines.append(f'- auto_current_best_comparison_status={case.auto_metrics.current_best_comparison_status}')
        lines.append(f'- auto_primary_force_win_count={case.auto_metrics.primary_force_win_count}')
        lines.append(f'- auto_stable_but_no_breakthrough={case.auto_metrics.stable_but_no_breakthrough}')
        lines.append(f'- auto_quality_check_target_status={case.auto_metrics.quality_check_target_status}')
        lines.append(f'- auto_pressure_target_status={case.auto_metrics.pressure_target_status}')
        lines.append(f'- auto_leakage_target_status={case.auto_metrics.leakage_target_status}')
        lines.append(f'- auto_false_fix_rejection_status={case.auto_metrics.false_fix_rejection_status}')
        lines.append(f'- auto_outcome_only_reranker_status={case.auto_metrics.outcome_only_reranker_status}')
        lines.append(f'- auto_outcome_only_frontier_comparison_status={case.auto_metrics.outcome_only_frontier_comparison_status}')
        lines.append(f'- auto_outcome_only_probe_pass_count={case.auto_metrics.outcome_only_probe_pass_count}')
        if case.auto_metrics.outcome_only_blocking_reason:
            lines.append(f'- auto_outcome_only_blocking_reason={case.auto_metrics.outcome_only_blocking_reason}')
        lines.append(f'- auto_residual_gap_count={case.auto_metrics.residual_gap_count}')
        if case.auto_metrics.promotion_hold_reason:
            lines.append(f'- auto_promotion_hold_reason={case.auto_metrics.promotion_hold_reason}')
        if case.auto_metrics.legacy_delta_summary:
            lines.append(f'- auto_legacy_delta_summary={case.auto_metrics.legacy_delta_summary}')
        lines.append(f'- auto_editorial_force={case.auto_metrics.editorial_force_status}')
        lines.append(f'- auto_cut_sharpness_score={case.auto_metrics.cut_sharpness_score:.2f}')
        lines.append(f'- auto_failure_repair_force={case.auto_metrics.failure_repair_force:.2f}')
        lines.append(f'- auto_force_boundary_rule_coverage={case.auto_metrics.force_boundary_rule_coverage:.2f}')
        lines.append(f'- auto_stop_condition_coverage={case.auto_metrics.stop_condition_coverage:.2f}')
        lines.append(f'- auto_anti_filler_score={case.auto_metrics.anti_filler_score:.2f}')
        lines.append(f'- auto_section_force_distinctness={case.auto_metrics.section_force_distinctness:.2f}')
        lines.append(f'- auto_section_rhythm_distinctness={case.auto_metrics.section_rhythm_distinctness:.2f}')
        lines.append(f'- auto_opening_distinctness={case.auto_metrics.opening_distinctness:.2f}')
        lines.append(f'- auto_compression_without_loss={case.auto_metrics.compression_without_loss:.2f}')
        lines.append(f'- auto_generic_surface_leakage={case.auto_metrics.generic_surface_leakage:.2f}')
        if case.auto_metrics.candidate_strategy_matrix:
            lines.append(f'- auto_candidate_strategy_matrix={case.auto_metrics.candidate_strategy_matrix}')
        lines.append(f'- auto_program_fidelity={case.auto_metrics.program_fidelity_status}')
        lines.append(f'- auto_execution_move_recall={case.auto_metrics.execution_move_recall:.2f}')
        lines.append(f'- auto_execution_move_order_alignment={case.auto_metrics.execution_move_order_alignment:.2f}')
        lines.append(f'- auto_decision_rule_fidelity={case.auto_metrics.decision_rule_fidelity:.2f}')
        lines.append(f'- auto_cut_rule_fidelity={case.auto_metrics.cut_rule_fidelity:.2f}')
        lines.append(f'- auto_failure_repair_fidelity={case.auto_metrics.failure_repair_fidelity:.2f}')
        lines.append(f'- auto_output_schema_fidelity={case.auto_metrics.output_schema_fidelity:.2f}')
        lines.append(f'- auto_workflow_surface_fidelity={case.auto_metrics.workflow_surface_fidelity:.2f}')
        lines.append(f'- auto_style_strategy_fidelity={case.auto_metrics.style_strategy_fidelity:.2f}')
        lines.append(f'- auto_task_outcome={case.auto_metrics.task_outcome_status}')
        lines.append(f'- auto_task_outcome_pass_count={case.auto_metrics.task_outcome_pass_count}/{case.auto_metrics.task_outcome_probe_count}')
        lines.append(f'- auto_task_outcome_with_skill_average={case.auto_metrics.task_outcome_with_skill_average:.2f}')
        lines.append(f'- auto_generated_heading_overlap={case.auto_metrics.generated_vs_generated_heading_overlap:.2f}')
        lines.append(f'- auto_generated_line_jaccard={case.auto_metrics.generated_vs_generated_line_jaccard:.2f}')
        lines.append(f'- auto_generic_skeleton_ratio={case.auto_metrics.generic_skeleton_ratio:.2f}')
        lines.append(f'- auto_prompt_phrase_echo_ratio={case.auto_metrics.prompt_phrase_echo_ratio:.2f}')
        if case.auto_metrics.missing_domain_anchors:
            lines.append(f'- missing_domain_anchors={case.auto_metrics.missing_domain_anchors}')
        if case.auto_metrics.cross_case_similarity:
            lines.append(f'- cross_case_similarity={case.auto_metrics.cross_case_similarity:.2f}')
        lines.append(f'- golden_body_lines={case.golden_metrics.body_lines}')
        if case.hermes_metrics is not None:
            lines.append(f'- hermes_body_lines={case.hermes_metrics.body_lines}')
        if case.gap_issues:
            lines.append(f'- gap_issues={case.gap_issues}')
        lines.append('')
    if report.hermes_errors:
        lines.append('## Hermes Errors')
        for item in report.hermes_errors:
            lines.append(f'- {item}')
    if report.anthropic_reference_summary:
        lines.extend(['', '## Anthropic Skill-Creator Reference'])
        for item in report.anthropic_reference_summary:
            lines.append(f'- {item}')
    if report.expert_dna_authoring_pack is not None:
        lines.extend(['', '## Expert DNA Authoring'])
        lines.append(f'- ready_for_review={len(report.expert_dna_authoring_pack.ready_for_review)}')
        lines.append(f'- needs_human_authoring={len(report.expert_dna_authoring_pack.needs_human_authoring)}')
        lines.append(f'- rejected={len(report.expert_dna_authoring_pack.rejected)}')
    if report.skill_program_authoring_pack is not None:
        lines.extend(['', '## Skill Program Authoring'])
        lines.append(f'- ready_for_review={len(report.skill_program_authoring_pack.ready_for_review)}')
        lines.append(f'- needs_human_authoring={len(report.skill_program_authoring_pack.needs_human_authoring)}')
        lines.append(f'- rejected={len(report.skill_program_authoring_pack.rejected)}')
        lines.append(f'- backlog_counts={report.skill_program_authoring_pack.backlog_counts}')
    if report.skill_usefulness_eval_report is not None:
        lines.extend(['', '## Skill Usefulness Eval'])
        lines.append(f'- status={report.skill_usefulness_eval_report.status}')
        lines.append(f'- probe_count={report.skill_usefulness_eval_report.probe_count}')
        lines.append(f'- usefulness_gap_count={report.skill_usefulness_eval_report.usefulness_gap_count}')
        lines.append(f'- with_skill_average={report.skill_usefulness_eval_report.with_skill_average:.2f}')
    if report.skill_task_outcome_report is not None:
        lines.extend(['', '## Skill Task Outcome'])
        lines.append(f'- status={report.skill_task_outcome_report.status}')
        lines.append(f'- probe_count={report.skill_task_outcome_report.probe_count}')
        lines.append(f'- task_outcome_gap_count={report.skill_task_outcome_report.task_outcome_gap_count}')
        lines.append(f'- with_skill_average={report.skill_task_outcome_report.with_skill_average:.2f}')
    return '\n'.join(lines).strip()


def build_skill_create_comparison_report(
    *,
    include_hermes: bool = False,
    golden_root: Path | None = None,
    hermes_wrappers: list[Path] | None = None,
) -> SkillCreateComparisonReport:
    root = (golden_root or DEFAULT_COMPARISON_GOLDEN_ROOT).expanduser()
    hermes_wrapper = _find_hermes_wrapper(hermes_wrappers) if include_hermes else None
    initial_independence_status = _hermes_independence_status(hermes_wrapper) if include_hermes else 'golden_only'
    hermes_errors: list[str] = []
    case_payloads: list[dict[str, Any]] = []
    for case in COMPARISON_CASES:
        (
            auto_metrics,
            body_quality,
            self_review,
            domain_specificity,
            domain_expertise,
            expert_structure,
            depth_quality,
            editorial_quality,
            style_diversity,
            move_quality,
            workflow_form,
            pairwise_editorial,
            promotion_decision,
            monotonic_improvement,
            editorial_force,
            program_fidelity,
            task_outcome,
            auto_content,
        ) = _run_auto_case(case)
        reference_root = DEFAULT_EXPERT_DEPTH_GOLDEN_ROOT if DEFAULT_EXPERT_DEPTH_GOLDEN_ROOT.exists() else root
        golden_metrics, *_ = _metrics_from_markdown(case, _golden_content(case, reference_root))
        hermes_metrics = None
        if hermes_wrapper is not None:
            hermes_metrics, error = _run_hermes_case(case, hermes_wrapper)
            if error:
                hermes_errors.append(f'{case["case_id"]}: {error}')
        case_payloads.append(
            {
                'case': case,
                'auto_metrics': auto_metrics,
                'golden_metrics': golden_metrics,
                'hermes_metrics': hermes_metrics,
                'body_quality': body_quality,
                'self_review': self_review,
                'domain_specificity': domain_specificity,
                'domain_expertise': domain_expertise,
                'expert_structure': expert_structure,
                'depth_quality': depth_quality,
                'editorial_quality': editorial_quality,
                'style_diversity': style_diversity,
                'move_quality': move_quality,
                'workflow_form': workflow_form,
                'pairwise_editorial': pairwise_editorial,
                'promotion_decision': promotion_decision,
                'monotonic_improvement': monotonic_improvement,
                'editorial_force': editorial_force,
                'program_fidelity': program_fidelity,
                'task_outcome': task_outcome,
                'auto_content': auto_content,
            }
        )

    for payload in case_payloads:
        similarities = [
            _content_similarity(payload['auto_content'], other['auto_content'])
            for other in case_payloads
            if other is not payload
        ]
        max_similarity = max(similarities or [0.0])
        heading_overlaps = [
            _heading_overlap(payload['auto_content'], other['auto_content'])
            for other in case_payloads
            if other is not payload
        ]
        line_jaccards = [
            _line_jaccard(payload['auto_content'], other['auto_content'])
            for other in case_payloads
            if other is not payload
        ]
        max_heading_overlap = max(heading_overlaps or [0.0])
        max_line_jaccard = max(line_jaccards or [0.0])
        signatures = [
            style_signature_from_markdown(other['auto_content'])
            for other in case_payloads
            if other is not payload
        ]
        own_signature = style_signature_from_markdown(payload['auto_content'])
        max_opening = max(
            [shared_opening_ratio(own_signature['opening'], item['opening']) for item in signatures] or [0.0]
        )
        max_label_ratio = max(
            [
                shared_step_label_ratio(own_signature['workflow_labels'], item['workflow_labels'])
                for item in signatures
            ]
            or [0.0]
        )
        max_boilerplate = max(
            [
                shared_boilerplate_sentence_ratio(own_signature['boilerplate_sentences'], item['boilerplate_sentences'])
                for item in signatures
            ]
            or [0.0]
        )
        own_moves = move_signature_from_markdown(payload['auto_content'])
        move_overlaps = []
        for other in case_payloads:
            if other is payload:
                continue
            other_moves = move_signature_from_markdown(other['auto_content'])
            if own_moves and other_moves:
                move_overlaps.append(len(own_moves & other_moves) / max(1, len(own_moves | other_moves)))
        max_move_overlap = round(max(move_overlaps or [0.0]), 4)
        payload['auto_metrics'].cross_case_similarity = max_similarity
        payload['auto_metrics'].generated_vs_generated_heading_overlap = max_heading_overlap
        payload['auto_metrics'].generated_vs_generated_line_jaccard = max_line_jaccard
        payload['style_diversity'] = build_skill_style_diversity_report(
            request=_request(payload['case']),
            skill_plan=_plan(payload['case']),
            artifacts=_artifact_skill_md(payload['auto_content']),
            shared_opening_phrase_ratio=max_opening,
            shared_step_label_ratio_value=max_label_ratio,
            shared_boilerplate_sentence_ratio_value=max_boilerplate,
        )
        payload['auto_metrics'].style_diversity_status = payload['style_diversity'].status
        payload['auto_metrics'].shared_opening_phrase_ratio = payload['style_diversity'].shared_opening_phrase_ratio
        payload['auto_metrics'].shared_step_label_ratio = payload['style_diversity'].shared_step_label_ratio
        payload['auto_metrics'].shared_boilerplate_sentence_ratio = payload['style_diversity'].shared_boilerplate_sentence_ratio
        payload['auto_metrics'].fixed_renderer_phrase_count = payload['style_diversity'].fixed_renderer_phrase_count
        payload['auto_metrics'].profile_specific_label_coverage = payload['style_diversity'].profile_specific_label_coverage
        payload['auto_metrics'].domain_rhythm_score = payload['style_diversity'].domain_rhythm_score
        payload['auto_metrics'].style_gap_count = len(list(payload['style_diversity'].blocking_issues or []))
        payload['move_quality'] = build_skill_move_quality_report(
            request=_request(payload['case']),
            skill_plan=_plan(payload['case']),
            artifacts=_artifact_skill_md(payload['auto_content']),
            cross_case_move_overlap=max_move_overlap,
        )
        payload['auto_metrics'].move_quality_status = payload['move_quality'].status
        payload['auto_metrics'].expert_move_recall = payload['move_quality'].expert_move_recall
        payload['auto_metrics'].expert_move_precision = payload['move_quality'].expert_move_precision
        payload['auto_metrics'].decision_rule_coverage = payload['move_quality'].decision_rule_coverage
        payload['auto_metrics'].cut_rule_coverage = payload['move_quality'].cut_rule_coverage
        payload['auto_metrics'].output_field_semantics_coverage = payload['move_quality'].output_field_semantics_coverage
        payload['auto_metrics'].failure_repair_coverage = payload['move_quality'].failure_repair_coverage
        payload['auto_metrics'].numbered_workflow_spine_present = payload['move_quality'].numbered_workflow_spine_present
        payload['auto_metrics'].voice_rule_alignment = payload['move_quality'].voice_rule_alignment
        payload['auto_metrics'].cross_case_move_overlap = payload['move_quality'].cross_case_move_overlap
        payload['auto_metrics'].move_quality_gap_count = len(list(payload['move_quality'].blocking_issues or []))
        payload['workflow_form'] = build_skill_workflow_form_report(
            request=_request(payload['case']),
            skill_plan=_plan(payload['case']),
            artifacts=_artifact_skill_md(payload['auto_content']),
        )
        payload['auto_metrics'].workflow_form_status = payload['workflow_form'].status
        payload['auto_metrics'].workflow_surface = payload['workflow_form'].workflow_surface
        payload['auto_metrics'].numbered_spine_count = payload['workflow_form'].numbered_spine_count
        payload['auto_metrics'].imperative_move_recall = payload['workflow_form'].imperative_move_recall
        payload['auto_metrics'].named_block_dominance_ratio = payload['workflow_form'].named_block_dominance_ratio
        payload['auto_metrics'].workflow_heading_alignment = payload['workflow_form'].workflow_heading_alignment
        payload['auto_metrics'].output_block_separation = payload['workflow_form'].output_block_separation
        payload['auto_metrics'].structural_block_count = payload['workflow_form'].structural_block_count
        payload['auto_metrics'].workflow_form_gap_count = len(list(payload['workflow_form'].blocking_issues or []))
        payload['program_fidelity'] = build_skill_program_fidelity_report(
            request=_request(payload['case']),
            skill_plan=_plan(payload['case']),
            artifacts=_artifact_skill_md(payload['auto_content']),
            workflow_form=payload['workflow_form'],
        )
        payload['auto_metrics'].program_fidelity_status = payload['program_fidelity'].status
        payload['auto_metrics'].execution_move_recall = payload['program_fidelity'].execution_move_recall
        payload['auto_metrics'].execution_move_order_alignment = payload['program_fidelity'].execution_move_order_alignment
        payload['auto_metrics'].decision_rule_fidelity = payload['program_fidelity'].decision_rule_fidelity
        payload['auto_metrics'].cut_rule_fidelity = payload['program_fidelity'].cut_rule_fidelity
        payload['auto_metrics'].failure_repair_fidelity = payload['program_fidelity'].failure_repair_fidelity
        payload['auto_metrics'].output_schema_fidelity = payload['program_fidelity'].output_schema_fidelity
        payload['auto_metrics'].workflow_surface_fidelity = payload['program_fidelity'].workflow_surface_fidelity
        payload['auto_metrics'].style_strategy_fidelity = payload['program_fidelity'].style_strategy_fidelity
        payload['auto_metrics'].program_fidelity_gap_count = len(list(payload['program_fidelity'].blocking_issues or []))
        payload['task_outcome'] = build_skill_task_outcome_report(
            generated_skill_markdown_by_name={str(payload['case']['skill_name']): payload['auto_content']},
            skill_names=[str(payload['case']['skill_name'])],
        )
        profile_result = next(iter(list(payload['task_outcome'].profile_results or [])), None)
        payload['editorial_force'] = build_skill_editorial_force_report(
            request=_request(payload['case']),
            skill_plan=_plan(payload['case']),
            artifacts=_artifact_skill_md(payload['auto_content']),
            body_quality=payload['body_quality'],
            domain_specificity=payload['domain_specificity'],
            domain_expertise=payload['domain_expertise'],
            depth_quality=payload['depth_quality'],
            editorial_quality=payload['editorial_quality'],
            style_diversity=payload['style_diversity'],
            move_quality=payload['move_quality'],
            pairwise_editorial=payload['pairwise_editorial'],
            promotion_decision=payload['promotion_decision'],
            realization_candidate_count=int(payload['auto_metrics'].realization_candidate_count or 0),
        )
        payload['auto_metrics'].editorial_force_status = payload['editorial_force'].status
        payload['auto_metrics'].cut_sharpness_score = payload['editorial_force'].cut_sharpness_score
        payload['auto_metrics'].failure_repair_force = payload['editorial_force'].failure_repair_force
        payload['auto_metrics'].force_boundary_rule_coverage = payload['editorial_force'].boundary_rule_coverage
        payload['auto_metrics'].stop_condition_coverage = payload['editorial_force'].stop_condition_coverage
        payload['auto_metrics'].anti_filler_score = payload['editorial_force'].anti_filler_score
        payload['auto_metrics'].section_force_distinctness = payload['editorial_force'].section_force_distinctness
        payload['auto_metrics'].section_rhythm_distinctness = payload['editorial_force'].section_rhythm_distinctness
        payload['auto_metrics'].opening_distinctness = payload['editorial_force'].opening_distinctness
        payload['auto_metrics'].compression_without_loss = payload['editorial_force'].compression_without_loss
        payload['auto_metrics'].generic_surface_leakage = payload['editorial_force'].generic_surface_leakage
        payload['auto_metrics'].editorial_force_gap_count = len(list(payload['editorial_force'].blocking_issues or []))
        payload['auto_metrics'].task_outcome_status = payload['task_outcome'].status
        payload['auto_metrics'].task_outcome_pass_count = int(getattr(profile_result, 'pass_count', 0) or 0)
        payload['auto_metrics'].task_outcome_probe_count = int(getattr(profile_result, 'probe_count', 0) or 0)
        payload['auto_metrics'].task_outcome_with_skill_average = float(getattr(profile_result, 'with_skill_average', 0.0) or 0.0)
        payload['auto_metrics'].task_outcome_gap_count = int(payload['task_outcome'].task_outcome_gap_count or 0)
        if payload['domain_specificity'] is not None:
            payload['domain_specificity'].cross_case_similarity = max_similarity
            if max_similarity >= 0.82 and 'high_cross_case_similarity' not in payload['domain_specificity'].blocking_issues:
                payload['domain_specificity'].blocking_issues.append('high_cross_case_similarity')
                payload['domain_specificity'].status = 'fail'
            payload['auto_metrics'].domain_specificity_status = payload['domain_specificity'].status
        if payload['expert_structure'] is not None:
            payload['expert_structure'].generated_vs_generated_heading_overlap = max_heading_overlap
            payload['expert_structure'].generated_vs_generated_line_jaccard = max_line_jaccard
            if max_heading_overlap >= 0.80 and 'high_generated_heading_overlap' not in payload['expert_structure'].blocking_issues:
                payload['expert_structure'].blocking_issues.append('high_generated_heading_overlap')
                payload['expert_structure'].status = 'fail'
            if max_line_jaccard >= 0.42 and 'high_generated_line_jaccard' not in payload['expert_structure'].blocking_issues:
                payload['expert_structure'].blocking_issues.append('high_generated_line_jaccard')
                payload['expert_structure'].status = 'fail'
            payload['auto_metrics'].expert_structure_status = payload['expert_structure'].status
        _apply_dual_baseline_statuses(payload['auto_metrics'], str(payload['case']['skill_name']))

    if not include_hermes:
        hermes_execution_status = 'not_requested'
        comparison_independence_status = 'golden_only'
        comparison_source = 'expert_golden'
        reference_role = 'quality_baseline'
    elif hermes_wrapper is None:
        hermes_execution_status = 'unavailable'
        comparison_independence_status = 'golden_only'
        comparison_source = 'expert_golden'
        reference_role = 'quality_baseline'
    elif hermes_errors:
        hermes_execution_status = 'failed'
        comparison_independence_status = 'golden_only'
        comparison_source = 'expert_golden'
        reference_role = 'quality_baseline'
    else:
        hermes_execution_status = 'passed'
        comparison_independence_status = initial_independence_status
        if comparison_independence_status == 'independent':
            comparison_source = 'hermes'
            reference_role = 'quality_baseline'
        else:
            comparison_source = 'expert_golden'
            reference_role = 'entrypoint_smoke'

    cases: list[SkillCreateComparisonCaseResult] = []
    for payload in case_payloads:
        case = payload['case']
        reference_metrics = (
            payload['hermes_metrics']
            if comparison_source == 'hermes' and payload['hermes_metrics'] is not None
            else payload['golden_metrics']
        )
        gap_issues = _gap_issues(
            payload['auto_metrics'],
            reference_metrics,
            skill_name=str(case['skill_name']),
        )
        status = 'gap' if gap_issues else 'matched'
        cases.append(
            SkillCreateComparisonCaseResult(
                case_id=case['case_id'],
                skill_name=case['skill_name'],
                auto_metrics=payload['auto_metrics'],
                golden_metrics=payload['golden_metrics'],
                hermes_metrics=payload['hermes_metrics'],
                body_quality=payload['body_quality'],
                self_review=payload['self_review'],
                domain_specificity=payload['domain_specificity'],
                domain_expertise=payload['domain_expertise'],
                expert_structure=payload['expert_structure'],
                depth_quality=payload['depth_quality'],
                editorial_quality=payload['editorial_quality'],
                style_diversity=payload['style_diversity'],
                move_quality=payload['move_quality'],
                workflow_form=payload['workflow_form'],
                pairwise_editorial=payload['pairwise_editorial'],
                promotion_decision=payload['promotion_decision'],
                monotonic_improvement=payload['monotonic_improvement'],
                editorial_force=payload['editorial_force'],
                program_fidelity=payload['program_fidelity'],
                task_outcome=payload['task_outcome'],
                gap_issues=gap_issues,
                status=status,
                summary=f'{case["case_id"]}: {status}',
            )
        )
    gap_count = sum(1 for item in cases if item.status == 'gap')
    expert_structure_gap_count = sum(
        1
        for item in cases
        if any(issue.startswith('auto_expert_') for issue in list(item.gap_issues or []))
        or item.auto_metrics.expert_structure_status != 'pass'
    )
    depth_quality_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_depth_quality_not_pass',
                'auto_expert_depth_recall_low',
                'auto_section_depth_score_low',
                'auto_output_field_guidance_weak',
                'auto_worked_examples_missing',
                'auto_failure_patterns_thin',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.depth_quality_status != 'pass'
    )
    editorial_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_editorial_quality_not_pass',
                'auto_decision_pressure_low',
                'auto_output_executability_weak',
                'auto_failure_corrections_thin',
                'auto_redundancy_high',
                'auto_explanatory_bulk_high',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.editorial_quality_status != 'pass'
    )
    style_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_style_diversity_not_pass',
                'auto_shared_opening_phrase',
                'auto_shared_step_labels',
                'auto_shared_boilerplate_sentences',
                'auto_profile_specific_labels_missing',
                'auto_fixed_renderer_boilerplate',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.style_diversity_status != 'pass'
    )
    move_quality_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_move_quality_not_pass',
                'auto_expert_move_recall_low',
                'auto_expert_move_precision_low',
                'auto_decision_rules_missing',
                'auto_output_field_semantics_missing',
                'auto_failure_repair_missing',
                'auto_numbered_workflow_spine_missing',
                'auto_cross_case_move_overlap_high',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.move_quality_status != 'pass'
    )
    workflow_form_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_workflow_form_not_pass',
                'auto_numbered_spine_count_low',
                'auto_workflow_named_blocks_dominate',
                'auto_output_blocks_mixed_into_workflow',
                'auto_structural_analysis_blocks_missing',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.workflow_form_status != 'pass'
    )
    editorial_force_gap_count = sum(
        1
        for item in cases
        if (
            any(
                issue
                in {
                    'auto_editorial_force_not_pass',
                    'auto_cut_sharpness_low',
                    'auto_failure_repair_force_low',
                    'auto_section_rhythm_distinctness_low',
                    'auto_compression_without_loss_low',
                    'auto_generic_surface_leakage',
                }
                for issue in list(item.gap_issues or [])
            )
            or (
                item.auto_metrics.editorial_force_status != 'pass'
                and not (
                    item.skill_name == 'decision-loop-stress-test'
                    and item.auto_metrics.stable_but_no_breakthrough
                    and item.auto_metrics.active_frontier_status in {'matched', 'beaten'}
                    and item.auto_metrics.force_non_regression_status == 'pass'
                    and item.auto_metrics.coverage_non_regression_status == 'pass'
                    and item.auto_metrics.compactness_non_regression_status == 'pass'
                )
            )
        )
    )
    candidate_separation_gap_count = sum(
        1
        for item in cases
        if any(issue in {'auto_candidate_separation_not_pass'} for issue in list(item.gap_issues or []))
        or item.auto_metrics.candidate_separation_status != 'pass'
    )
    best_balance_not_beaten_count = sum(
        1
        for item in cases
        if item.auto_metrics.best_balance_comparison_status == 'not_beaten'
    )
    best_coverage_not_beaten_count = sum(
        1
        for item in cases
        if item.auto_metrics.best_coverage_comparison_status == 'not_beaten'
    )
    current_best_not_beaten_count = sum(
        1
        for item in cases
        if any(issue in {'auto_current_best_not_beaten'} for issue in list(item.gap_issues or []))
        or item.auto_metrics.current_best_comparison_status == 'not_beaten'
    )
    promotion_hold_count = sum(
        1
        for item in cases
        if item.auto_metrics.pairwise_promotion_status != 'promote'
    )
    pairwise_promotion_gap_count = sum(
        1
        for item in cases
        if any(
            issue in {'auto_pairwise_promotion_not_promoted'}
            for issue in list(item.gap_issues or [])
        )
        or (
            item.auto_metrics.pairwise_promotion_status != 'promote'
            and not item.auto_metrics.stable_but_no_breakthrough
        )
    )
    program_fidelity_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_program_fidelity_not_pass',
                'auto_execution_move_recall_low',
                'auto_execution_move_order_alignment_low',
                'auto_decision_rule_fidelity_low',
                'auto_output_schema_fidelity_low',
                'auto_failure_repair_fidelity_low',
                'auto_workflow_surface_fidelity_low',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.program_fidelity_status != 'pass'
    )
    task_outcome_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_task_outcome_not_pass',
                'auto_task_outcome_probe_pass_rate_low',
                'auto_task_outcome_gaps_present',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.task_outcome_status != 'pass'
    )
    force_non_regression_status = (
        'fail'
        if any(item.auto_metrics.force_non_regression_status == 'fail' for item in cases)
        else 'pass'
    )
    coverage_non_regression_status = (
        'fail'
        if any(item.auto_metrics.coverage_non_regression_status == 'fail' for item in cases)
        else 'pass'
    )
    compactness_non_regression_status = (
        'fail'
        if any(item.auto_metrics.compactness_non_regression_status == 'fail' for item in cases)
        else 'pass'
    )
    frontier_dominance_status = (
        'fail'
        if any(item.auto_metrics.frontier_dominance_status == 'fail' for item in cases)
        else 'pass'
    )
    compression_gain_status = (
        'pass'
        if any(item.auto_metrics.compression_gain_status == 'pass' for item in cases)
        else 'fail'
    )
    stable_but_no_breakthrough_count = sum(
        1
        for item in cases
        if item.auto_metrics.stable_but_no_breakthrough
    )
    residual_gap_count = sum(
        int(item.auto_metrics.residual_gap_count or 0)
        for item in cases
        if not (
            item.skill_name == 'decision-loop-stress-test'
            and item.auto_metrics.stable_but_no_breakthrough
            and item.auto_metrics.active_frontier_status in {'matched', 'beaten'}
            and item.auto_metrics.force_non_regression_status == 'pass'
            and item.auto_metrics.coverage_non_regression_status == 'pass'
            and item.auto_metrics.compactness_non_regression_status == 'pass'
        )
    )
    active_frontier_status = (
        'fail'
        if any(item.auto_metrics.active_frontier_status == 'regressed' for item in cases)
        else 'pass'
    )
    generic_shell_gap_count = sum(
        1
        for item in cases
        if any(issue in {'auto_generic_shell_gap', 'auto_generic_skeleton_gap'} for issue in list(item.gap_issues or []))
    )
    pairwise_similarity_gap_count = sum(
        1
        for item in cases
        if any(
            issue in {'auto_generated_heading_overlap_high', 'auto_generated_line_jaccard_high'}
            for issue in list(item.gap_issues or [])
        )
    )
    anthropic_metrics, anthropic_summary = _anthropic_reference_metrics()
    auto_content_by_name = {
        str(payload['case']['skill_name']): str(payload.get('auto_content') or '')
        for payload in case_payloads
    }
    authoring_pack = build_expert_dna_authoring_pack()
    program_authoring_pack = build_skill_program_authoring_pack()
    program_review_batch = build_program_candidate_review_batch_report(program_authoring_pack)
    usefulness_report = build_skill_usefulness_eval_report(
        generated_skill_markdown_by_name=auto_content_by_name,
    )
    task_outcome_report = build_skill_task_outcome_report(
        generated_skill_markdown_by_name=auto_content_by_name,
        skill_names=list(auto_content_by_name.keys()),
    )
    negative_case_resistance, generic_shell_rejection, program_regression_count = evaluate_negative_case_resistance()
    dna_authoring_status = 'pass' if authoring_pack.rejected == [] else 'fail'
    usefulness_eval_status = usefulness_report.status
    program_authoring_status = 'pass' if program_authoring_pack.rejected == [] else 'fail'
    task_outcome_status = task_outcome_report.status
    active_breakthrough_case = next(
        (item for item in cases if item.skill_name == 'decision-loop-stress-test'),
        None,
    )
    guardrail_cases = [item for item in cases if item.skill_name != 'decision-loop-stress-test']
    shared_gate_pass = (
        gap_count == 0
        and usefulness_report.usefulness_gap_count == 0
        and task_outcome_report.task_outcome_gap_count == 0
        and dna_authoring_status == 'pass'
        and program_authoring_status == 'pass'
        and editorial_force_gap_count == 0
        and force_non_regression_status == 'pass'
        and coverage_non_regression_status == 'pass'
        and compactness_non_regression_status == 'pass'
        and frontier_dominance_status == 'pass'
        and active_frontier_status == 'pass'
    )
    guardrails_stable = all(
        item.auto_metrics.force_non_regression_status == 'pass'
        and item.auto_metrics.coverage_non_regression_status == 'pass'
        and item.auto_metrics.compactness_non_regression_status == 'pass'
        and item.auto_metrics.active_frontier_status in {'matched', 'beaten'}
        and int(item.auto_metrics.residual_gap_count or 0) == 0
        for item in guardrail_cases
    )
    decision_loop_breakthrough = bool(
        active_breakthrough_case is not None
        and active_breakthrough_case.auto_metrics.pairwise_promotion_status == 'promote'
        and active_breakthrough_case.auto_metrics.force_non_regression_status == 'pass'
        and active_breakthrough_case.auto_metrics.coverage_non_regression_status == 'pass'
        and active_breakthrough_case.auto_metrics.compactness_non_regression_status == 'pass'
        and active_breakthrough_case.auto_metrics.active_frontier_status == 'beaten'
        and int(active_breakthrough_case.auto_metrics.residual_gap_count or 0) == 0
        and str(active_breakthrough_case.auto_metrics.outcome_only_reranker_status or 'not_applicable')
        in {'pass', 'not_applicable'}
        and str(active_breakthrough_case.auto_metrics.outcome_only_frontier_comparison_status or 'not_applicable')
        in {'beaten', 'not_applicable'}
        and not bool(active_breakthrough_case.auto_metrics.stable_but_no_breakthrough)
    )
    breakthrough_ready = (
        shared_gate_pass
        and editorial_force_gap_count == 0
        and pairwise_promotion_gap_count == 0
        and candidate_separation_gap_count == 0
        and guardrails_stable
        and decision_loop_breakthrough
    )
    stable_but_no_breakthrough = (
        not breakthrough_ready
        and shared_gate_pass
        and editorial_force_gap_count == 0
        and candidate_separation_gap_count == 0
        and guardrails_stable
        and active_breakthrough_case is not None
        and active_breakthrough_case.auto_metrics.force_non_regression_status == 'pass'
        and active_breakthrough_case.auto_metrics.coverage_non_regression_status == 'pass'
        and active_breakthrough_case.auto_metrics.compactness_non_regression_status == 'pass'
        and active_breakthrough_case.auto_metrics.active_frontier_status in {'matched', 'beaten'}
    )
    report = SkillCreateComparisonReport(
        cases=cases,
        include_hermes=include_hermes,
        hermes_available=hermes_wrapper is not None,
        hermes_execution_status=hermes_execution_status,
        hermes_error_count=len(hermes_errors),
        hermes_errors=hermes_errors,
        comparison_source=comparison_source,
        comparison_independence_status=comparison_independence_status,
        reference_role=reference_role,
        anthropic_reference_available=anthropic_metrics is not None,
        anthropic_reference_metrics=anthropic_metrics,
        anthropic_reference_summary=anthropic_summary,
        expert_dna_authoring_pack=authoring_pack,
        skill_program_authoring_pack=program_authoring_pack,
        program_candidate_review_batch=program_review_batch,
        skill_usefulness_eval_report=usefulness_report,
        skill_task_outcome_report=task_outcome_report,
        dna_authoring_status=dna_authoring_status,
        candidate_dna_count=authoring_pack.candidate_dna_count,
        program_authoring_status=program_authoring_status,
        candidate_program_count=program_authoring_pack.candidate_program_count,
        usefulness_eval_status=usefulness_eval_status,
        usefulness_gap_count=usefulness_report.usefulness_gap_count,
        task_outcome_status=task_outcome_status,
        task_outcome_gap_count=task_outcome_report.task_outcome_gap_count,
        expert_structure_gap_count=expert_structure_gap_count,
        depth_quality_gap_count=depth_quality_gap_count,
        editorial_gap_count=editorial_gap_count,
        style_gap_count=style_gap_count,
        move_quality_gap_count=move_quality_gap_count,
        workflow_form_gap_count=workflow_form_gap_count,
        editorial_force_gap_count=editorial_force_gap_count,
        pairwise_promotion_gap_count=pairwise_promotion_gap_count,
        program_fidelity_gap_count=program_fidelity_gap_count,
        candidate_separation_gap_count=candidate_separation_gap_count,
        best_balance_not_beaten_count=best_balance_not_beaten_count,
        best_coverage_not_beaten_count=best_coverage_not_beaten_count,
        current_best_not_beaten_count=current_best_not_beaten_count,
        promotion_hold_count=promotion_hold_count,
        force_non_regression_status=force_non_regression_status,
        coverage_non_regression_status=coverage_non_regression_status,
        compactness_non_regression_status=compactness_non_regression_status,
        frontier_dominance_status=frontier_dominance_status,
        compression_gain_status=compression_gain_status,
        stable_but_no_breakthrough_count=stable_but_no_breakthrough_count,
        active_frontier_status=active_frontier_status,
        residual_gap_count=residual_gap_count,
        generic_shell_gap_count=generic_shell_gap_count,
        pairwise_similarity_gap_count=pairwise_similarity_gap_count,
        negative_case_resistance=negative_case_resistance,
        generic_shell_rejection=generic_shell_rejection,
        program_regression_count=program_regression_count,
        gap_count=gap_count,
        overall_status=(
            'breakthrough'
            if breakthrough_ready
            else (
                'stable_but_no_breakthrough'
                if stable_but_no_breakthrough
                else 'fail'
            )
        ),
        summary=(
            f'Skill create comparison complete: cases={len(cases)} gaps={gap_count} '
            f'comparison_source={comparison_source} '
            f'independence={comparison_independence_status} '
            f'reference_role={reference_role} '
            f'hermes_status={hermes_execution_status} '
            f'move_quality_gaps={move_quality_gap_count} '
            f'workflow_form_gaps={workflow_form_gap_count} '
            f'editorial_force_gaps={editorial_force_gap_count} '
            f'candidate_separation_gaps={candidate_separation_gap_count} '
            f'force_non_regression={force_non_regression_status} '
            f'coverage_non_regression={coverage_non_regression_status} '
            f'compactness_non_regression={compactness_non_regression_status} '
            f'frontier_dominance={frontier_dominance_status} '
            f'active_frontier_status={active_frontier_status} '
            f'best_balance_not_beaten={best_balance_not_beaten_count} '
            f'best_coverage_not_beaten={best_coverage_not_beaten_count} '
            f'current_best_not_beaten={current_best_not_beaten_count} '
            f'residual_gaps={residual_gap_count} '
            f'pairwise_promotion_gaps={pairwise_promotion_gap_count} '
            f'program_fidelity_gaps={program_fidelity_gap_count} '
            f'dna_candidates={authoring_pack.candidate_dna_count} '
            f'program_candidates={program_authoring_pack.candidate_program_count} '
            f'usefulness_gaps={usefulness_report.usefulness_gap_count} '
            f'task_outcome_gaps={task_outcome_report.task_outcome_gap_count}'
        ),
    )
    report.markdown_summary = render_skill_create_comparison_markdown(report)
    return report
