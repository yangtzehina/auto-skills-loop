from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_test_helpers import invoke_main, load_script_module

from openclaw_skill_create.models.expert_studio import (
    OutcomeOnlyRerankerReport,
    SkillRealizationCandidate,
)
from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services import expert_skill_studio as studio
from openclaw_skill_create.services import (
    build_profile_residual_targets,
    build_residual_gap_report,
    build_program_candidate_review_batch_report,
    build_skill_realization_candidates,
    build_skill_program_authoring_pack,
    build_skill_program_fidelity_report,
    build_skill_program_ir,
    build_skill_task_outcome_report,
    choose_skill_realization_candidate,
    evaluate_negative_case_resistance,
    render_skill_program_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORING_SCRIPT = ROOT / 'scripts' / 'run_skill_program_authoring.py'
REVIEW_SCRIPT = ROOT / 'scripts' / 'run_skill_program_review.py'


def _outcome_only_report(
    *,
    winner: str,
    candidate_ranking: list[str] | None = None,
    status: str = 'pass',
    frontier_comparison_status: str = 'beaten',
    blocking_reason: str = '',
    probe_pass_count: int = 8,
    probe_count: int = 8,
    improved_probe_count: int = 2,
    probe_mode: str = 'probe_expanded_v4',
) -> OutcomeOnlyRerankerReport:
    return OutcomeOnlyRerankerReport(
        skill_name='decision-loop-stress-test',
        probe_mode=probe_mode,
        candidate_ranking=candidate_ranking or [winner],
        winner=winner,
        frontier_comparison_status=frontier_comparison_status,
        blocking_reason=blocking_reason,
        probe_pass_count=probe_pass_count,
        probe_count=probe_count,
        improved_probe_count=improved_probe_count,
        status=status,
    )


def test_known_game_design_profile_builds_skill_program_ir():
    program = build_skill_program_ir(
        skill_name='decision-loop-stress-test',
        task='Stress a decision loop across first hour, midgame, and mastery pressure.',
    )

    assert program is not None
    assert program.workflow_surface == 'execution_spine'
    assert len(program.execution_spine) >= 6
    assert program.execution_spine[0].label == 'Define the Current Loop Shape'
    assert 'Reinforcement Check' in program.output_schema


def test_profile_residual_targets_freeze_frontier_v3_priorities():
    concept = build_profile_residual_targets('concept-to-mvp-pack')
    decision = build_profile_residual_targets('decision-loop-stress-test')
    simulation = build_profile_residual_targets('simulation-resource-loop-design')

    assert concept.target_metrics['expert_pitfall_cluster_recall'] == 0.90
    assert concept.target_metrics['output_field_guidance_coverage'] == 0.85
    assert concept.allowed_sections == [
        'Quality Checks',
        'Failure Patterns and Fixes',
        'Output Format',
    ]
    assert decision.target_metrics['decision_pressure_score'] == 0.98
    assert 'Default Workflow' in decision.allowed_sections
    assert decision.target_metrics['compression_without_loss'] == 0.80
    assert decision.target_metrics['task_outcome_with_skill_average'] == 0.92
    assert decision.target_metrics['outcome_only_probe_pass_count'] == 8.0
    assert decision.target_metrics['outcome_only_improved_probe_count'] == 2.0
    assert decision.target_metrics['repair_specificity_score'] == 0.90
    assert decision.target_metrics['probe_evidence_density'] == 0.85
    assert decision.target_metrics['collapse_witness_coverage'] == 0.90
    assert simulation.target_metrics['generic_surface_leakage'] == 0.05
    assert simulation.target_metrics['generic_skeleton_ratio'] == 0.20
    assert 'Analysis Blocks' in simulation.allowed_sections


def test_decision_loop_probe_expanded_specs_include_future_adversarial_set():
    specs = studio._decision_loop_outcome_probe_specs(mode='probe_expanded_v4')

    assert len(specs) == 8
    probe_ids = {item['probe_id'] for item in specs}
    assert {
        'decision.solved-state-numeric-only-repair',
        'decision.variation-without-read-change',
        'decision.reinforcement-without-habit-mapping',
        'decision.stop-condition-without-collapse-witness',
    } <= probe_ids


def test_decision_loop_probe_expanded_upgrade_requires_two_improved_probes():
    matched_only = _outcome_only_report(
        winner='decision-loop-stress-test:collapse_first_v2:1',
        probe_mode='probe_expanded_v4',
        frontier_comparison_status='matched',
        probe_pass_count=8,
        probe_count=8,
        improved_probe_count=0,
    )
    improved = _outcome_only_report(
        winner='decision-loop-stress-test:collapse_first_v2:1',
        probe_mode='probe_expanded_v4',
        frontier_comparison_status='beaten',
        probe_pass_count=8,
        probe_count=8,
        improved_probe_count=2,
    )

    assert studio._decision_loop_probe_expanded_v4_ready(matched_only) is False
    assert studio._decision_loop_probe_expanded_v4_ready(improved) is True


def test_program_authoring_pack_surfaces_known_and_unknown_candidates():
    pack = build_skill_program_authoring_pack()
    batch = build_program_candidate_review_batch_report(pack)

    assert pack.candidate_program_count >= 8
    assert {
        'concept-to-mvp-pack',
        'decision-loop-stress-test',
        'simulation-resource-loop-design',
    } <= set(pack.ready_for_review)
    assert 'research-memo-synthesis' in pack.needs_human_authoring
    assert batch.pass_count == 3
    assert batch.fail_count >= 1


def test_negative_case_resistance_rejects_generic_shell_failures():
    resistance, generic_rejection, regressions = evaluate_negative_case_resistance()

    assert resistance >= 0.80
    assert generic_rejection >= 1.0
    assert regressions == 0


def test_program_fidelity_passes_for_rendered_known_profile():
    request = SkillCreateRequestV6(task='Stress a decision loop across first hour, midgame, and mastery pressure.')
    skill_md = render_skill_program_markdown(
        skill_name='decision-loop-stress-test',
        description='Stress-test a decision loop.',
        task=request.task,
        references=[],
        scripts=[],
    )
    report = build_skill_program_fidelity_report(
        request=request,
        skill_plan=SkillPlan(skill_name='decision-loop-stress-test', skill_archetype='methodology_guidance'),
        artifacts=Artifacts(files=[ArtifactFile(path='SKILL.md', content=skill_md or '', content_type='text/markdown')]),
    )

    assert report.status == 'pass'
    assert report.execution_move_recall >= 0.85
    assert report.execution_move_order_alignment >= 0.80


def test_realization_candidates_support_pairwise_promotion_for_known_profile():
    program, realization_spec, candidates = build_skill_realization_candidates(
        skill_name='concept-to-mvp-pack',
        description='Turn a concept into a falsifiable MVP pack.',
        task='Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.',
        references=[],
        scripts=[],
    )
    winner, pairwise_report, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='concept-to-mvp-pack',
        task='Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.',
        candidates=candidates,
    )
    assert program.workflow_surface == 'execution_spine'
    assert realization_spec.workflow_surface == 'execution_spine'
    assert len(candidates) >= 4
    assert {item.realization_strategy for item in candidates} >= {
        'proof_first',
        'cut_first',
        'package_ready',
        'failure_pass',
    }
    assert all(
        item.strategy_profile.get('active_frontier_version') == studio.build_active_frontier_version()
        for item in candidates
    )
    assert all(item.strategy_profile.get('allowed_sections') for item in candidates)
    assert {item.strategy_profile.get('target_focus') for item in candidates} <= {'quality_checks', 'failure_repairs', 'output_format', ''}
    assert sum(
        1 for item in candidates
        if item.strategy_profile.get('compression_stage') == 'post'
    ) <= 2
    assert winner.candidate_id in {item.candidate_id for item in candidates}
    assert pairwise_report.winner == winner.candidate_id
    assert pairwise_report.candidate_separation_status == 'pass'
    assert promotion_decision.force_non_regression_status in {'pass', 'fail'}
    assert promotion_decision.coverage_non_regression_status in {'pass', 'fail'}
    assert promotion_decision.compactness_non_regression_status in {'pass', 'fail'}
    assert monotonic_report is not None
    assert monotonic_report.frontier_dominance_status in {'pass', 'fail'}
    assert promotion_decision.promotion_status in {'promote', 'hold'}


def test_residual_gap_report_fails_for_known_frontier_weaknesses():
    concept_report = build_residual_gap_report(
        skill_name='concept-to-mvp-pack',
        metrics={
            'expert_pitfall_cluster_recall': 0.75,
            'output_field_guidance_coverage': 0.75,
            'generic_surface_leakage': 0.20,
            'decision_pressure_score': 0.9467,
            'cut_sharpness_score': 1.0,
            'boundary_rule_coverage': 0.8,
            'domain_move_coverage': 1.0,
            'section_depth_score': 0.97,
            'task_outcome_with_skill_average': 0.9398,
        },
    )
    decision_report = build_residual_gap_report(
        skill_name='decision-loop-stress-test',
        metrics={
            'decision_pressure_score': 0.8154,
            'section_force_distinctness': 0.81,
            'compression_without_loss': 0.7333,
            'failure_repair_force': 1.0,
            'stop_condition_coverage': 1.0,
            'domain_move_coverage': 0.9285,
            'section_depth_score': 0.9008,
            'task_outcome_with_skill_average': 0.90,
            'outcome_only_probe_pass_count': 4,
            'outcome_only_improved_probe_count': 0,
            'repair_specificity_score': 0.82,
            'probe_evidence_density': 0.72,
            'collapse_witness_coverage': 0.70,
        },
    )
    simulation_report = build_residual_gap_report(
        skill_name='simulation-resource-loop-design',
        metrics={
            'generic_surface_leakage': 0.0556,
            'redundancy_ratio': 0.041,
            'generic_skeleton_ratio': 0.24,
            'failure_repair_force': 1.0,
            'section_force_distinctness': 1.0,
            'boundary_rule_coverage': 0.2,
            'domain_move_coverage': 1.0,
            'section_depth_score': 1.0,
            'task_outcome_with_skill_average': 0.963,
        },
    )

    assert concept_report.status == 'fail'
    assert concept_report.quality_check_target_status == 'fail'
    assert concept_report.leakage_target_status == 'fail'
    assert concept_report.target_focus in {'failure_repairs', 'output_format'}

    assert decision_report.status == 'fail'
    assert decision_report.pressure_target_status == 'fail'
    assert decision_report.false_fix_rejection_status == 'fail'
    assert decision_report.target_focus == 'pressure'

    assert simulation_report.status == 'fail'
    assert simulation_report.leakage_target_status == 'fail'
    assert simulation_report.pressure_target_status == 'pass'
    assert simulation_report.target_focus == 'leakage'


def test_pairwise_promotion_holds_when_primary_force_regresses(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:collapse_first:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='collapse_first',
            strategy_profile={
                'opening_frame': 'Collapse frame',
                'section_order': 'Overview > Default Workflow > Quality Checks',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'collapse_detection',
                'step_frame': 'collapse_probe',
                'output_focus': 'Collapse Point,Break Point',
                'quality_tone': 'collapse',
                'quality_mode': 'collapse_gate',
                'failure_style': 'collapse_signals',
                'failure_mode': 'collapse_signals',
            },
            rendered_markdown='# collapse-first',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:stop_condition_first:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='stop_condition_first',
            strategy_profile={
                'opening_frame': 'Stop frame',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Output Format:4',
                'workflow_mode': 'stop_condition_priority',
                'step_frame': 'stop_condition_probe',
                'output_focus': 'Stop Condition,Solved State Risk',
                'quality_tone': 'stop-first',
                'quality_mode': 'stop_condition_gate',
                'failure_style': 'solved_state',
                'failure_mode': 'solved_state',
            },
            rendered_markdown='# stop-condition',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:fake_fix_rejection:3',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='fake_fix_rejection',
            strategy_profile={
                'opening_frame': 'False fix frame',
                'section_order': 'Overview > Failure Patterns and Fixes > Default Workflow',
                'sentence_budget_profile': 'Failure Patterns and Fixes:5',
                'workflow_mode': 'false_fix_rejection',
                'step_frame': 'false_fix_gate',
                'output_focus': 'False Fix Rejection,Repair Recommendation',
                'quality_tone': 'false-fix',
                'quality_mode': 'false_fix_gate',
                'failure_style': 'false_fix',
                'failure_mode': 'false_fix',
            },
            rendered_markdown='# fake-fix',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:pressure_audit:4',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='pressure_audit',
            strategy_profile={
                'opening_frame': 'Audit frame',
                'section_order': 'Overview > Decision Rules > Default Workflow',
                'sentence_budget_profile': 'Decision Rules:4',
                'workflow_mode': 'pressure_audit',
                'step_frame': 'pressure_audit',
                'output_focus': 'Pressure Audit,Variation Audit',
                'quality_tone': 'audit',
                'quality_mode': 'pressure_audit',
                'failure_style': 'wrong_behavior',
                'failure_mode': 'wrong_behavior',
            },
            rendered_markdown='# pressure-audit',
        ),
    ]

    candidate_metrics = {
        '# collapse-first': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.90,
                'cut_sharpness_score': 0.90,
                'failure_repair_force': 0.90,
                'stop_condition_coverage': 0.90,
                'output_executability_score': 0.90,
                'section_force_distinctness': 0.90,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.85})(),
            'score': 0.90,
        },
        '# stop-condition': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.88,
                'cut_sharpness_score': 0.86,
                'failure_repair_force': 0.89,
                'stop_condition_coverage': 0.88,
                'output_executability_score': 0.87,
                'section_force_distinctness': 0.83,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.04})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.88})(),
            'score': 0.88,
        },
        '# fake-fix': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.87,
                'cut_sharpness_score': 0.85,
                'failure_repair_force': 0.88,
                'stop_condition_coverage': 0.92,
                'output_executability_score': 0.86,
                'section_force_distinctness': 0.86,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.03})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.87})(),
            'score': 0.87,
        },
        '# pressure-audit': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.86,
                'cut_sharpness_score': 0.84,
                'failure_repair_force': 0.87,
                'stop_condition_coverage': 0.90,
                'output_executability_score': 0.85,
                'section_force_distinctness': 0.84,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.02})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.89})(),
            'score': 0.86,
        },
    }

    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: candidate_metrics[kwargs['markdown']])
    monkeypatch.setattr(
        studio,
        '_build_outcome_only_reranker_report',
        lambda **kwargs: _outcome_only_report(
            winner='decision-loop-stress-test:collapse_first:1',
            candidate_ranking=[
                'decision-loop-stress-test:collapse_first:1',
                'decision-loop-stress-test:stop_condition_first:2',
                'decision-loop-stress-test:fake_fix_rejection:3',
                'decision-loop-stress-test:pressure_audit:4',
            ],
        ),
    )
    monkeypatch.setattr(
        studio,
        '_current_best_editorial_metrics',
        lambda skill_name, task: {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.93,
                'cut_sharpness_score': 0.90,
                'failure_repair_force': 0.90,
                'stop_condition_coverage': 0.90,
                'output_executability_score': 0.90,
                'section_force_distinctness': 0.82,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.82})(),
            'score': 0.91,
        },
    )

    winner, pairwise_report, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress loop',
        candidates=candidates,
    )

    assert winner is not None
    assert pairwise_report.candidate_separation_status == 'pass'
    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.force_non_regression_status == 'fail'
    assert promotion_decision.promotion_hold_reason.startswith('hold_due_to_force_regression')
    assert monotonic_report.promotion_reason == 'hold_due_to_force_regression'


def test_pairwise_promotion_holds_when_candidates_only_change_opening(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id=f'concept-to-mvp-pack:variant:{index}',
            skill_name='concept-to-mvp-pack',
            program_id='concept-to-mvp-pack:execution_spine',
            realization_strategy=f'variant_{index}',
            strategy_profile={
                'opening_frame': f'Opening {index}',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'validation_pressure',
                'step_frame': 'proof_gate',
                'output_focus': 'Core Validation Question,Smallest Honest Loop',
                'quality_tone': 'proof-first',
                'quality_mode': 'proof_gate',
                'failure_style': 'redesign_trigger',
                'failure_mode': 'kill_or_fix',
            },
            rendered_markdown=f'# variant {index}',
        )
        for index in range(1, 5)
    ]
    metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 0.90,
            'cut_sharpness_score': 0.91,
            'failure_repair_force': 0.88,
            'boundary_rule_coverage': 0.30,
            'output_executability_score': 0.90,
            'section_force_distinctness': 0.82,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.84})(),
        'score': 0.90,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: None)

    _, pairwise_report, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='concept-to-mvp-pack',
        task='mvp',
        candidates=candidates,
    )

    assert pairwise_report.candidate_separation_status == 'fail'
    assert pairwise_report.candidate_separation_score < 0.78
    assert promotion_decision.promotion_status == 'hold'
    assert monotonic_report is not None


def test_monotonic_promotion_holds_when_only_stable_without_breakthrough(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:collapse_first:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='collapse_first',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'Collapse frame',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'collapse_detection',
                'step_frame': 'collapse_probe',
                'output_focus': 'Collapse Point,Break Point,Repair Recommendation',
                'quality_tone': 'collapse',
                'quality_mode': 'collapse_gate',
                'failure_style': 'collapse_signals',
                'failure_mode': 'collapse_signals',
            },
            rendered_markdown='# proof',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:fake_fix_rejection:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='fake_fix_rejection',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'False fix frame',
                'section_order': 'Overview > Output Format > Default Workflow',
                'sentence_budget_profile': 'Output Format:4',
                'workflow_mode': 'false_fix_rejection',
                'step_frame': 'false_fix_gate',
                'output_focus': 'Repair Recommendation,False Fix Rejection,Variation Audit',
                'quality_tone': 'false-fix',
                'quality_mode': 'false_fix_gate',
                'failure_style': 'false_fix',
                'failure_mode': 'false_fix',
            },
            rendered_markdown='# repair',
        ),
    ]
    metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 0.8154,
            'cut_sharpness_score': 1.0,
            'failure_repair_force': 0.89,
            'boundary_rule_coverage': 0.25,
            'stop_condition_coverage': 1.0,
            'output_executability_score': 0.92,
            'section_force_distinctness': 0.81,
            'compression_without_loss': 0.7369,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.08})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.86})(),
        'domain_move_coverage': 0.7571,
        'section_depth_score': 0.9008,
        'task_outcome_with_skill_average': 0.8611,
        'redundancy_ratio': 0.0584,
        'shared_opening_phrase_ratio': 0.0,
        'cross_case_similarity': 0.25,
        'compression_without_loss': 0.7369,
        'score': 0.95,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: {'score': 0.90})
    monkeypatch.setattr(
        studio,
        '_build_outcome_only_reranker_report',
        lambda **kwargs: _outcome_only_report(
            winner='decision-loop-stress-test:collapse_first:1',
            candidate_ranking=[
                'decision-loop-stress-test:collapse_first:1',
                'decision-loop-stress-test:fake_fix_rejection:2',
            ],
        ),
    )

    _, _, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress a core loop',
        candidates=candidates,
    )

    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.stable_but_no_breakthrough is False
    assert promotion_decision.reason == 'hold_due_to_force_regression'
    assert promotion_decision.pressure_target_status == 'fail'
    assert promotion_decision.residual_gap_count >= 1
    assert monotonic_report.promotion_reason == 'hold_due_to_force_regression'


def test_outcome_only_reranker_blocks_promotion_without_frontier_win(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:collapse_first:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='collapse_first',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'Collapse frame',
                'section_order': 'Overview > Default Workflow > Quality Checks',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'collapse_detection',
                'step_frame': 'collapse_probe',
                'output_focus': 'Collapse Point,Break Point',
                'quality_tone': 'collapse',
                'quality_mode': 'collapse_gate',
                'failure_style': 'collapse_signals',
                'failure_mode': 'collapse_signals',
            },
            rendered_markdown='# collapse',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:fake_fix_rejection:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='fake_fix_rejection',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'False fix frame',
                'section_order': 'Overview > Quality Checks > Failure Patterns and Fixes',
                'sentence_budget_profile': 'Quality Checks:4',
                'workflow_mode': 'false_fix_rejection',
                'step_frame': 'false_fix_gate',
                'output_focus': 'False Fix Rejection,Repair Recommendation',
                'quality_tone': 'false-fix',
                'quality_mode': 'false_fix_gate',
                'failure_style': 'false_fix',
                'failure_mode': 'false_fix',
            },
            rendered_markdown='# false-fix',
        ),
    ]
    strong_metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 0.99,
            'cut_sharpness_score': 1.0,
            'failure_repair_force': 1.0,
            'stop_condition_coverage': 1.0,
            'output_executability_score': 0.95,
            'section_force_distinctness': 0.90,
            'compression_without_loss': 0.81,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.03})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.90})(),
        'domain_move_coverage': 0.95,
        'section_depth_score': 0.92,
        'task_outcome_with_skill_average': 0.93,
        'shared_opening_phrase_ratio': 0.0,
        'cross_case_similarity': 0.22,
        'compression_without_loss': 0.81,
        'score': 0.99,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: strong_metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: {'score': 0.95})
    monkeypatch.setattr(
        studio,
        '_compare_to_dual_baselines',
        lambda **kwargs: studio.MonotonicImprovementReport(
            skill_name='decision-loop-stress-test',
            active_frontier_status='beaten',
            best_balance_comparison_status='beaten',
            best_coverage_comparison_status='beaten',
            force_non_regression_status='pass',
            coverage_non_regression_status='pass',
            compactness_non_regression_status='pass',
            frontier_dominance_status='pass',
            compression_gain_status='pass',
            promotion_status='promote',
            promotion_reason='breakthrough',
            primary_force_win_count=2,
        ),
    )
    monkeypatch.setattr(
        studio,
        '_residual_gap_report',
        lambda skill_name, metrics: studio.ResidualGapReport(
            skill_name=skill_name,
            quality_check_target_status='unknown',
            pressure_target_status='pass',
            leakage_target_status='unknown',
            false_fix_rejection_status='pass',
            residual_gap_count=0,
            status='pass',
        ),
    )
    monkeypatch.setattr(
        studio,
        '_build_outcome_only_reranker_report',
        lambda **kwargs: _outcome_only_report(
            winner='decision-loop-stress-test:collapse_first:1',
            candidate_ranking=[
                'decision-loop-stress-test:collapse_first:1',
                'decision-loop-stress-test:fake_fix_rejection:2',
            ],
            status='fail',
            probe_mode='probe_expanded_v4',
            frontier_comparison_status='matched',
            blocking_reason='outcome_only_reranker_not_better_than_frontier',
            probe_pass_count=3,
            probe_count=8,
            improved_probe_count=0,
        ),
    )

    _, _, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress a core loop',
        candidates=candidates,
    )

    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.stable_but_no_breakthrough is True
    assert promotion_decision.reason == 'stable_but_no_breakthrough'
    assert promotion_decision.outcome_only_reranker_status == 'fail'
    assert promotion_decision.outcome_only_frontier_comparison_status == 'matched'
    assert promotion_decision.outcome_only_probe_pass_count == 3
    assert promotion_decision.outcome_only_blocking_reason == 'outcome_only_reranker_not_better_than_frontier'
    assert promotion_decision.outcome_only_probe_mode == 'probe_expanded_v4'
    assert monotonic_report.promotion_reason == 'breakthrough'


def test_outcome_only_reranker_collects_probe_witnesses(monkeypatch):
    candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:collapse_first_v2:1',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='collapse_first_v2',
        strategy_profile={},
        rendered_markdown=(
            "# Decision Loop\n\n"
            "- First hour novelty can hide a weak decision if the collapse signal never arrives.\n"
            "- Name the stop condition and collapse witness before phase explanation.\n"
            "- Reject any fix that only adds more content or softer compensation.\n"
            "- A structural fix must change the decision problem and wrong habit.\n"
        ),
    )
    frontier_candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:frontier',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='frontier',
        strategy_profile={},
        rendered_markdown="# Frontier\n- Stop condition.\n",
    )

    monkeypatch.setattr(studio, '_current_best_markdown', lambda skill_name: frontier_candidate.rendered_markdown)

    def _metrics(**kwargs):
        markdown = kwargs['markdown']
        redundancy_ratio = 0.03 if 'collapse witness' in markdown else 0.05
        return {
            'editorial': type('Editorial', (), {'redundancy_ratio': redundancy_ratio})(),
            'editorial_force': type('Force', (), {})(),
        }

    monkeypatch.setattr(studio, '_candidate_editorial_metrics', _metrics)

    report = studio._build_outcome_only_reranker_report(
        skill_name='decision-loop-stress-test',
        scored_candidates=[(candidate, {'editorial': type('Editorial', (), {'redundancy_ratio': 0.03})()})],
        probe_mode='probe_expanded_v4',
    )

    assert report is not None
    assert report.probe_mode == 'probe_expanded_v4'
    assert report.probe_count == 8
    assert report.probe_witness_summary
    assert report.repair_evidence_lines
    assert report.collapse_evidence_lines
    assert report.repair_specificity_score > 0.0
    assert report.collapse_witness_coverage > 0.0
    assert set(report.improved_probe_ids) | set(report.matched_probe_ids) | set(report.blocked_probe_ids)


def test_promotion_stays_stable_when_residual_targets_do_not_improve(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='concept-to-mvp-pack:proof_first:1',
            skill_name='concept-to-mvp-pack',
            program_id='concept-to-mvp-pack:execution_spine',
            realization_strategy='proof_first',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'proof',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'validation_pressure',
                'step_frame': 'proof_gate',
                'output_focus': 'Core Validation Question,Smallest Honest Loop',
                'quality_tone': 'proof-first',
                'quality_mode': 'proof_gate',
                'failure_style': 'redesign_trigger',
                'failure_mode': 'kill_or_fix',
            },
            rendered_markdown='# proof',
        ),
        SkillRealizationCandidate(
            candidate_id='concept-to-mvp-pack:cut_first:2',
            skill_name='concept-to-mvp-pack',
            program_id='concept-to-mvp-pack:execution_spine',
            realization_strategy='cut_first',
            strategy_profile={
                'compression_stage': 'post',
                'source_candidate_id': 'concept-to-mvp-pack:proof_first:1',
                'opening_frame': 'cut',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Default Workflow:4',
                'workflow_mode': 'scope_cut',
                'step_frame': 'cut_gate',
                'output_focus': 'Out of Scope,Core Validation Question',
                'quality_tone': 'cut-first',
                'quality_mode': 'proof_gate',
                'failure_style': 'scope_creep',
                'failure_mode': 'scope_creep',
            },
            rendered_markdown='# cut',
        ),
    ]
    metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 0.95,
            'cut_sharpness_score': 1.0,
            'failure_repair_force': 1.0,
            'boundary_rule_coverage': 0.8,
            'output_executability_score': 0.95,
            'section_force_distinctness': 0.86,
            'compression_without_loss': 0.80,
            'stop_condition_coverage': 1.0,
            'generic_surface_leakage': 0.20,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.90})(),
        'expert_structure': type('Structure', (), {'expert_quality_check_recall': 0.75})(),
        'domain_expertise': type('Domain', (), {'domain_move_coverage': 1.0})(),
        'depth': type('Depth', (), {'section_depth_score': 0.95})(),
        'task_outcome': type('Outcome', (), {
            'profile_results': [type('Profile', (), {'with_skill_average': 0.9398})()],
        })(),
        'domain_move_coverage': 1.0,
        'section_depth_score': 0.95,
        'task_outcome_with_skill_average': 0.9398,
        'redundancy_ratio': 0.05,
        'shared_opening_phrase_ratio': 0.0,
        'cross_case_similarity': 0.22,
        'compression_without_loss': 0.80,
        'score': 0.99,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: {'score': 0.90})

    _, _, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='concept-to-mvp-pack',
        task='turn a concept into an honest first playable',
        candidates=candidates,
    )

    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.stable_but_no_breakthrough is False
    assert promotion_decision.reason == 'hold_due_to_candidate_separation'
    assert promotion_decision.quality_check_target_status == 'fail'
    assert promotion_decision.leakage_target_status == 'fail'
    assert promotion_decision.residual_gap_count >= 1
    assert monotonic_report.promotion_reason == 'hold_due_to_force_regression'


def test_task_outcome_passes_for_known_profile_and_skips_unknown_without_probes():
    skill_md = render_skill_program_markdown(
        skill_name='concept-to-mvp-pack',
        description='Package a falsifiable MVP.',
        task='Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.',
        references=[],
        scripts=[],
    )
    known_report = build_skill_task_outcome_report(
        generated_skill_markdown_by_name={'concept-to-mvp-pack': skill_md or ''},
        skill_names=['concept-to-mvp-pack'],
    )
    skipped_report = build_skill_task_outcome_report(
        generated_skill_markdown_by_name={'demo-skill': '# Demo\n'},
        skill_names=['demo-skill'],
    )

    assert known_report.status == 'pass'
    assert known_report.task_outcome_gap_count == 0
    assert skipped_report.status == 'pass'
    assert skipped_report.probe_count == 0


def test_skill_program_authoring_cli_supports_markdown(monkeypatch):
    module = load_script_module(AUTHORING_SCRIPT, 'auto_skills_loop_run_skill_program_authoring')
    code, stdout, stderr = invoke_main(
        module,
        ['run_skill_program_authoring.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Skill Program Authoring Pack')
    assert 'concept-to-mvp-pack' in stdout


def test_skill_program_review_cli_reads_authoring_pack(monkeypatch, tmp_path: Path):
    module = load_script_module(REVIEW_SCRIPT, 'auto_skills_loop_run_skill_program_review')
    pack_path = tmp_path / 'program_pack.json'
    pack_path.write_text(
        json.dumps(build_skill_program_authoring_pack().model_dump(mode='json'), indent=2),
        encoding='utf-8',
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_skill_program_review.py', '--authoring-pack', str(pack_path), '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Skill Program Review Batch')
    assert 'approved_for_release_gate_count=0' in stdout


def test_skill_program_authoring_output_root_writes_sidecar(monkeypatch, tmp_path: Path):
    module = load_script_module(AUTHORING_SCRIPT, 'auto_skills_loop_run_skill_program_authoring_sidecar')
    code, stdout, stderr = invoke_main(
        module,
        ['run_skill_program_authoring.py', '--output-root', str(tmp_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['candidate_program_count'] >= 8
    assert (tmp_path / 'evals' / 'skill_program_authoring.json').exists()
