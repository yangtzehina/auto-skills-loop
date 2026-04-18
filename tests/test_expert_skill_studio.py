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
    probe_witness_summary: list[str] | None = None,
    matched_probe_ids: list[str] | None = None,
    improved_probe_ids: list[str] | None = None,
    blocked_probe_ids: list[str] | None = None,
    repair_evidence_lines: list[str] | None = None,
    collapse_evidence_lines: list[str] | None = None,
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
        probe_witness_summary=probe_witness_summary or ['decision.fake-repair-by-content=blocked'],
        matched_probe_ids=matched_probe_ids or ['decision.midgame-autopilot'],
        improved_probe_ids=improved_probe_ids or ['decision.stop-condition-without-collapse-witness'],
        blocked_probe_ids=blocked_probe_ids or ['decision.fake-repair-by-content'],
        repair_evidence_lines=repair_evidence_lines or ['repair recommendation: reject not just numeric tuning; make a structural fix'],
        collapse_evidence_lines=collapse_evidence_lines or ['name the collapse witness before the stop condition label'],
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
    assert decision.target_metrics['repair_specificity_score'] == 0.90
    assert decision.target_metrics['probe_evidence_density'] == 0.85
    assert decision.target_metrics['collapse_witness_coverage'] == 0.90
    assert simulation.target_metrics['generic_surface_leakage'] == 0.05
    assert simulation.target_metrics['generic_skeleton_ratio'] == 0.20
    assert 'Analysis Blocks' in simulation.allowed_sections


def test_decision_loop_probe_expanded_specs_include_future_adversarial_set():
    specs = studio._decision_loop_outcome_probe_specs(mode='probe_expanded_v4')
    specs_v7 = studio._decision_loop_outcome_probe_specs(mode='probe_expanded_v7')
    specs_v8 = studio._decision_loop_outcome_probe_specs(mode='probe_expanded_v8')
    specs_v9 = studio._decision_loop_outcome_probe_specs(mode='probe_expanded_v9')

    assert len(specs) == 8
    assert len(specs_v7) == 8
    assert len(specs_v8) == 8
    assert len(specs_v9) == 8
    probe_ids = {item['probe_id'] for item in specs}
    probe_ids_v7 = {item['probe_id'] for item in specs_v7}
    probe_ids_v8 = {item['probe_id'] for item in specs_v8}
    probe_ids_v9 = {item['probe_id'] for item in specs_v9}
    assert {
        'decision.solved-state-numeric-only-repair',
        'decision.variation-without-read-change',
        'decision.reinforcement-without-habit-mapping',
        'decision.stop-condition-without-collapse-witness',
    } <= probe_ids
    assert probe_ids == probe_ids_v7
    assert probe_ids == probe_ids_v8
    assert probe_ids == probe_ids_v9


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


def test_decision_loop_candidates_surface_stronger_probe_evidence():
    _, _, candidates = build_skill_realization_candidates(
        skill_name='decision-loop-stress-test',
        description='Stress-test a decision loop.',
        task='Stress a decision loop across first hour, midgame, and mastery pressure.',
        references=[],
        scripts=[],
    )

    assert candidates
    assert all('old answer' in item.rendered_markdown.lower() for item in candidates)
    assert all('reward loop' in item.rendered_markdown.lower() for item in candidates)
    assert all('same consequence' in item.rendered_markdown.lower() for item in candidates)
    assert all('decision landscape' in item.rendered_markdown.lower() for item in candidates)


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
            frontier_comparison_status='blocked',
            blocking_reason='outcome_only_reranker_blocked_by_probe_failures',
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
    assert promotion_decision.stable_but_no_breakthrough is False
    assert promotion_decision.reason == 'outcome_only_reranker_blocked_by_probe_failures'
    assert promotion_decision.outcome_only_reranker_status == 'fail'
    assert promotion_decision.outcome_only_frontier_comparison_status == 'blocked'
    assert promotion_decision.outcome_only_probe_pass_count == 3
    assert promotion_decision.outcome_only_blocking_reason == 'outcome_only_reranker_blocked_by_probe_failures'
    assert promotion_decision.outcome_only_probe_mode == 'probe_expanded_v4'
    assert promotion_decision.outcome_only_blocked_probe_ids == ['decision.fake-repair-by-content']
    assert promotion_decision.outcome_only_matched_probe_ids == ['decision.midgame-autopilot']
    assert promotion_decision.outcome_only_improved_probe_ids == ['decision.stop-condition-without-collapse-witness']
    assert promotion_decision.outcome_only_probe_witness_summary
    assert promotion_decision.outcome_only_repair_evidence_lines
    assert promotion_decision.outcome_only_collapse_evidence_lines
    assert monotonic_report.promotion_reason == 'breakthrough'


def test_outcome_only_reranker_allows_stable_match_without_breakthrough(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:collapse_first_v2:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='collapse_first_v2',
            strategy_profile={},
            rendered_markdown='# collapse',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:pressure_audit_v2:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='pressure_audit_v2',
            strategy_profile={},
            rendered_markdown='# audit',
        ),
    ]
    strong_metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 1.0,
            'cut_sharpness_score': 1.0,
            'failure_repair_force': 1.0,
            'stop_condition_coverage': 1.0,
            'output_executability_score': 0.95,
            'section_force_distinctness': 0.90,
            'compression_without_loss': 0.83,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.03})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.90})(),
        'domain_move_coverage': 0.95,
        'section_depth_score': 0.97,
        'task_outcome_with_skill_average': 0.98,
        'shared_opening_phrase_ratio': 0.0,
        'cross_case_similarity': 0.22,
        'compression_without_loss': 0.83,
        'score': 0.99,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: strong_metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: {'score': 0.98})
    monkeypatch.setattr(
        studio,
        '_candidate_separation_report',
        lambda candidates: ('pass', 0.95, [{'candidate_id': item.candidate_id} for item in candidates]),
    )
    monkeypatch.setattr(
        studio,
        '_compare_to_dual_baselines',
        lambda **kwargs: studio.MonotonicImprovementReport(
            skill_name='decision-loop-stress-test',
            active_frontier_status='matched',
            best_balance_comparison_status='not_beaten',
            best_coverage_comparison_status='not_beaten',
            force_non_regression_status='pass',
            coverage_non_regression_status='pass',
            compactness_non_regression_status='pass',
            frontier_dominance_status='pass',
            compression_gain_status='pass',
            promotion_status='hold',
            promotion_reason='hold_due_to_no_primary_win',
            primary_force_win_count=0,
        ),
    )
    monkeypatch.setattr(
        studio,
        '_residual_gap_report',
        lambda skill_name, metrics: studio.ResidualGapReport(
            skill_name=skill_name,
            target_focus='none',
            quality_check_target_status='pass',
            pressure_target_status='pass',
            leakage_target_status='pass',
            false_fix_rejection_status='pass',
            residual_gap_count=0,
            status='pass',
        ),
    )
    monkeypatch.setattr(
        studio,
        '_build_outcome_only_reranker_report',
        lambda **kwargs: _outcome_only_report(
            winner='decision-loop-stress-test:collapse_first_v2:1',
            candidate_ranking=['decision-loop-stress-test:collapse_first_v2:1'],
            status='pass',
            probe_mode='probe_expanded_v4',
            frontier_comparison_status='matched',
            blocking_reason='outcome_only_reranker_matches_but_improvements_below_threshold',
            probe_pass_count=8,
            probe_count=8,
            improved_probe_count=1,
            blocked_probe_ids=[],
            matched_probe_ids=['decision.midgame-autopilot'],
            improved_probe_ids=['decision.fake-repair-by-content'],
        ),
    )

    _, _, promotion_decision, _ = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress a core loop',
        candidates=candidates,
    )

    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.stable_but_no_breakthrough is True
    assert promotion_decision.reason == 'stable_but_no_breakthrough'
    assert promotion_decision.outcome_only_frontier_comparison_status == 'matched'
    assert promotion_decision.outcome_only_blocked_probe_count == 0


def test_decision_loop_outcome_breakthrough_can_promote_without_primary_force_win(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:collapse_first_v2:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='collapse_first_v2',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'Collapse frame',
                'section_order': 'Overview > Default Workflow > Quality Checks',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'collapse_detection',
                'step_frame': 'collapse_probe_v2',
                'output_focus': 'Collapse Point,Break Point',
                'quality_tone': 'collapse',
                'quality_mode': 'collapse_gate',
                'failure_style': 'collapse_signals',
                'failure_mode': 'collapse_signals',
            },
            rendered_markdown='# collapse',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:fake_fix_rejection_v2:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='fake_fix_rejection_v2',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'False fix frame',
                'section_order': 'Overview > Quality Checks > Failure Patterns and Fixes',
                'sentence_budget_profile': 'Quality Checks:4',
                'workflow_mode': 'false_fix_rejection',
                'step_frame': 'false_fix_gate_v2',
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
            'decision_pressure_score': 1.0,
            'cut_sharpness_score': 1.0,
            'failure_repair_force': 1.0,
            'stop_condition_coverage': 1.0,
            'output_executability_score': 0.95,
            'section_force_distinctness': 1.0,
            'compression_without_loss': 0.83,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.04})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.90})(),
        'domain_move_coverage': 0.95,
        'section_depth_score': 0.97,
        'task_outcome_with_skill_average': 0.98,
        'shared_opening_phrase_ratio': 0.0,
        'cross_case_similarity': 0.23,
        'compression_without_loss': 0.83,
        'score': 1.02,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: strong_metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: {'score': 1.01})
    monkeypatch.setattr(
        studio,
        '_compare_to_dual_baselines',
        lambda **kwargs: studio.MonotonicImprovementReport(
            skill_name='decision-loop-stress-test',
            active_frontier_status='matched',
            best_balance_comparison_status='not_beaten',
            best_coverage_comparison_status='not_beaten',
            force_non_regression_status='pass',
            coverage_non_regression_status='pass',
            compactness_non_regression_status='pass',
            frontier_dominance_status='pass',
            compression_gain_status='neutral',
            promotion_status='hold',
            promotion_reason='hold_due_to_no_primary_win',
            primary_force_win_count=0,
        ),
    )
    monkeypatch.setattr(
        studio,
        '_residual_gap_report',
        lambda skill_name, metrics: studio.ResidualGapReport(
            skill_name=skill_name,
            target_focus='none',
            quality_check_target_status='pass',
            pressure_target_status='pass',
            leakage_target_status='pass',
            false_fix_rejection_status='pass',
            residual_gap_count=0,
            status='pass',
        ),
    )
    monkeypatch.setattr(
        studio,
        '_build_outcome_only_reranker_report',
        lambda **kwargs: _outcome_only_report(
            winner='decision-loop-stress-test:collapse_first_v2:1',
            candidate_ranking=[
                'decision-loop-stress-test:collapse_first_v2:1',
                'decision-loop-stress-test:fake_fix_rejection_v2:2',
            ],
            status='pass',
            probe_mode='probe_expanded_v4',
            frontier_comparison_status='beaten',
            blocking_reason='',
            probe_pass_count=8,
            probe_count=8,
            improved_probe_count=6,
            blocked_probe_ids=[],
            matched_probe_ids=['decision.midgame-autopilot'],
            improved_probe_ids=[
                'decision.fake-repair-by-content',
                'decision.variation-without-read-change',
            ],
        ),
    )

    _, _, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress a core loop',
        candidates=candidates,
    )

    assert promotion_decision.promotion_status == 'promote'
    assert promotion_decision.reason == 'breakthrough'
    assert promotion_decision.stable_but_no_breakthrough is False
    assert promotion_decision.current_best_comparison_status == 'beaten'
    assert promotion_decision.active_frontier_status == 'beaten'
    assert promotion_decision.outcome_only_frontier_comparison_status == 'beaten'
    assert promotion_decision.outcome_only_probe_pass_count == 8
    assert promotion_decision.outcome_only_improved_probe_count == 6
    assert monotonic_report.promotion_reason == 'hold_due_to_no_primary_win'


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


def test_outcome_only_reranker_counts_frontier_equivalent_evidence_as_matched(monkeypatch):
    candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:collapse_first_v2:1',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='collapse_first_v2',
        strategy_profile={},
        rendered_markdown=(
            "# Decision Loop\n\n"
            "- Name the collapse witness, stop condition, and break point before phase explanation.\n"
            "- Reject any repair recommendation that is not just numeric tuning and demand a structural fix.\n"
        ),
    )
    monkeypatch.setattr(studio, '_current_best_markdown', lambda skill_name: candidate.rendered_markdown)
    monkeypatch.setattr(
        studio,
        '_decision_loop_outcome_probe_specs',
        lambda mode='probe_expanded_v4': [
            {
                'probe_id': 'decision.frontier-equivalent',
                'pressure_terms': ['collapse witness', 'stop condition'],
                'false_fix_terms': ['not just numeric tuning', 'structural fix'],
            }
        ],
    )

    def _metrics(**kwargs):
        return {
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'editorial_force': type('Force', (), {})(),
        }

    monkeypatch.setattr(studio, '_candidate_editorial_metrics', _metrics)

    report = studio._build_outcome_only_reranker_report(
        skill_name='decision-loop-stress-test',
        scored_candidates=[(candidate, {'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})()})],
        probe_mode='probe_expanded_v4',
    )

    assert report is not None
    assert report.status == 'pass'
    assert report.frontier_comparison_status == 'matched'
    assert report.matched_probe_ids == ['decision.frontier-equivalent']
    assert report.blocked_probe_ids == []


def test_outcome_only_reranker_counts_stronger_witness_bundle_as_improved(monkeypatch):
    frontier_markdown = (
        "# Frontier\n\n"
        "- Reject fake variation if it keeps the same dominant line or the same read.\n"
        "- Map the wrong habit to the right habit and name the intended behavior shift.\n"
        "- Reject repairs that are not just numeric tuning and still leave the same dominant line alive.\n"
    )
    candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:pressure_audit_v2:1',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='pressure_audit_v2',
        strategy_profile={},
        rendered_markdown=(
            "# Candidate\n\n"
            "- Reject fake variation if it keeps the same dominant line, the same read, or the same consequence, because the old answer still works until a new answer is required.\n"
            "- Map the wrong habit to the right habit, name the intended behavior and the behavior shift, say which reward loop currently trains the wrong behavior, and say what replacement behavior must become optimal.\n"
            "- Reject repairs that are not just numeric tuning when they keep the same dominant line, the same read, the same consequence structure, and the same decision landscape.\n"
        ),
    )
    monkeypatch.setattr(studio, '_current_best_markdown', lambda skill_name: frontier_markdown)

    def _metrics(**kwargs):
        return {
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'editorial_force': type('Force', (), {})(),
        }

    monkeypatch.setattr(studio, '_candidate_editorial_metrics', _metrics)

    report = studio._build_outcome_only_reranker_report(
        skill_name='decision-loop-stress-test',
        scored_candidates=[(candidate, {'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})()})],
        probe_mode='probe_expanded_v4',
    )

    assert report is not None
    assert {
        'decision.variation-without-read-change',
        'decision.reinforcement-without-habit-mapping',
        'decision.solved-state-numeric-only-repair',
    } <= set(report.improved_probe_ids)


def test_outcome_only_reranker_counts_stronger_section_bundle_as_improved_in_v7(monkeypatch):
    frontier_markdown = (
        "# Frontier\n\n"
        "## Default Workflow\n\n"
        "- Demand a repair recommendation with a structural fix that changes read, tradeoff, or consequence, names what old answer stops working, what new answer becomes correct, and which reward loop currently trains the wrong habit.\n\n"
        "## Quality Checks\n\n"
        "- Check whether variation changes read, tradeoff, or consequence instead of just renaming content.\n"
        "- Check whether reinforcement explicitly maps the wrong habit to the right habit the loop should train.\n"
        "- Check whether solved-state repair changes the decision landscape instead of leaving the same read, tradeoff, or consequence alive.\n\n"
        "## Common Pitfalls: Collapse Patterns and Repairs\n\n"
        "### Variety Without Strategic Consequence\n"
        "- Correction: Keep only the variants that force a new read, tradeoff, or consequence.\n"
    )
    candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:fake_fix_rejection_v2:1',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='fake_fix_rejection_v2',
        strategy_profile={},
        rendered_markdown=(
            "# Candidate\n\n"
            "## Default Workflow\n\n"
            "- Demand a structural fix that names the dominant line, what old answer stops working, what new answer becomes correct, and what reward, information, or cost changed to cause that shift.\n"
            "- Map the wrong habit to the right habit, say which reward loop currently trains the wrong habit, say what player behavior must disappear, and say what replacement behavior must become optimal.\n"
            "- Reject repairs that are not just numeric tuning when they keep the same dominant line, the same read, the same consequence structure, and the same decision landscape.\n\n"
            "## Quality Checks\n\n"
            "- Hard fail variation named but same dominant line, same read, or same consequence under a new label.\n"
            "- Hard fail habit mapping named but reward loop unchanged.\n"
            "- Hard fail solved-state repair named but decision landscape unchanged.\n"
            "- Hard fail numeric-only, content-only, pacing-only, or throughput-only fixes.\n\n"
            "## Common Pitfalls: Collapse Patterns and Repairs\n\n"
            "### Variety Without Strategic Consequence\n"
            "- Fake version: fake variation keeps the same dominant line and the same read.\n"
            "- Structural replacement: change reward, information, or cost so the old answer stops working and a new answer becomes correct.\n"
            "### Wrong Behavior Training\n"
            "- Fake version: fake reinforcement loop keeps rewarding the same safe behavior.\n"
            "- Structural replacement: name the reward loop currently training the wrong habit and make the replacement behavior become optimal.\n"
            "### Numeric-Only Repair\n"
            "- Fake version: numeric-only fake fix keeps the same dominant line, the same read, and the same consequence structure alive.\n"
            "- Structural replacement: change the decision landscape first so the old answer stops working.\n"
        ),
    )
    monkeypatch.setattr(studio, '_current_best_markdown', lambda skill_name: frontier_markdown)
    original_probe_specs = studio._decision_loop_outcome_probe_specs

    def _filtered_probe_specs(*, mode: str = 'probe_expanded_v4'):
        if mode != 'probe_expanded_v7':
            return list(original_probe_specs(mode=mode))
        return [
            {
                'probe_id': 'decision.variation-without-read-change',
                'pressure_terms': ['dominant line', 'old answer stops working', 'new answer becomes correct', 'read'],
                'false_fix_terms': ['structural replacement', 'reward, information, or cost', 'same consequence'],
            },
            {
                'probe_id': 'decision.reinforcement-without-habit-mapping',
                'pressure_terms': ['wrong habit', 'right habit', 'reward loop currently trains', 'behavior'],
                'false_fix_terms': ['structural replacement', 'replacement behavior', 'reward loop unchanged'],
            },
            {
                'probe_id': 'decision.solved-state-numeric-only-repair',
                'pressure_terms': ['not just numeric tuning', 'same dominant line', 'same read', 'decision landscape'],
                'false_fix_terms': ['structural replacement', 'numeric-only fake fix', 'decision landscape unchanged'],
            },
        ]

    monkeypatch.setattr(studio, '_decision_loop_outcome_probe_specs', _filtered_probe_specs)

    def _metrics(**kwargs):
        return {
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'editorial_force': type('Force', (), {})(),
        }

    monkeypatch.setattr(studio, '_candidate_editorial_metrics', _metrics)

    report = studio._build_outcome_only_reranker_report(
        skill_name='decision-loop-stress-test',
        scored_candidates=[(candidate, {'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})()})],
        probe_mode='probe_expanded_v7',
    )

    assert report is not None
    assert report.frontier_comparison_status == 'beaten'
    assert {
        'decision.variation-without-read-change',
        'decision.reinforcement-without-habit-mapping',
        'decision.solved-state-numeric-only-repair',
    } <= set(report.improved_probe_ids)


def test_outcome_only_reranker_counts_frontier_equivalent_section_bundle_as_matched_in_v7(monkeypatch):
    candidate_markdown = (
        "# Candidate\n\n"
        "## Default Workflow\n\n"
        "- Demand a structural fix that names the dominant line, what old answer stops working, what new answer becomes correct, and what reward, information, or cost changed to cause that shift.\n"
        "- Map the wrong habit to the right habit, say which reward loop currently trains the wrong habit, say what player behavior must disappear, and say what replacement behavior must become optimal.\n"
        "- Reject repairs that are not just numeric tuning when they keep the same dominant line, the same read, the same consequence structure, and the same decision landscape.\n\n"
        "## Quality Checks\n\n"
        "- Hard fail variation named but same dominant line, same read, or same consequence under a new label.\n"
        "- Hard fail habit mapping named but reward loop unchanged.\n"
        "- Hard fail solved-state repair named but decision landscape unchanged.\n"
        "- Hard fail numeric-only, content-only, pacing-only, or throughput-only fixes.\n\n"
        "## Common Pitfalls: Collapse Patterns and Repairs\n\n"
        "### Variety Without Strategic Consequence\n"
        "- Fake version: fake variation keeps the same dominant line and the same read.\n"
        "- Structural replacement: change reward, information, or cost so the old answer stops working and a new answer becomes correct.\n"
        "### Wrong Behavior Training\n"
        "- Fake version: fake reinforcement loop keeps rewarding the same safe behavior.\n"
        "- Structural replacement: name the reward loop currently training the wrong habit and make the replacement behavior become optimal.\n"
        "### Numeric-Only Repair\n"
        "- Fake version: numeric-only fake fix keeps the same dominant line, the same read, and the same consequence structure alive.\n"
        "- Structural replacement: change the decision landscape first so the old answer stops working.\n"
    )
    candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:pressure_audit_v2:1',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='pressure_audit_v2',
        strategy_profile={},
        rendered_markdown=candidate_markdown,
    )
    monkeypatch.setattr(studio, '_current_best_markdown', lambda skill_name: candidate_markdown)
    original_probe_specs = studio._decision_loop_outcome_probe_specs

    def _filtered_probe_specs(*, mode: str = 'probe_expanded_v4'):
        if mode != 'probe_expanded_v7':
            return list(original_probe_specs(mode=mode))
        return [
            {
                'probe_id': 'decision.variation-without-read-change',
                'pressure_terms': ['dominant line', 'old answer stops working', 'new answer becomes correct', 'read'],
                'false_fix_terms': ['structural replacement', 'reward, information, or cost', 'same consequence'],
            },
            {
                'probe_id': 'decision.reinforcement-without-habit-mapping',
                'pressure_terms': ['wrong habit', 'right habit', 'reward loop currently trains', 'behavior'],
                'false_fix_terms': ['structural replacement', 'replacement behavior', 'reward loop unchanged'],
            },
            {
                'probe_id': 'decision.solved-state-numeric-only-repair',
                'pressure_terms': ['not just numeric tuning', 'same dominant line', 'same read', 'decision landscape'],
                'false_fix_terms': ['structural replacement', 'numeric-only fake fix', 'decision landscape unchanged'],
            },
        ]

    monkeypatch.setattr(studio, '_decision_loop_outcome_probe_specs', _filtered_probe_specs)

    def _metrics(**kwargs):
        return {
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'editorial_force': type('Force', (), {})(),
        }

    monkeypatch.setattr(studio, '_candidate_editorial_metrics', _metrics)

    report = studio._build_outcome_only_reranker_report(
        skill_name='decision-loop-stress-test',
        scored_candidates=[(candidate, {'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})()})],
        probe_mode='probe_expanded_v7',
    )

    assert report is not None
    assert report.status == 'pass'
    assert report.frontier_comparison_status == 'matched'
    assert report.blocked_probe_ids == []
    assert report.improved_probe_ids == []


def test_outcome_only_reranker_requires_stronger_v8_section_bundle_for_improvement(monkeypatch):
    frontier_markdown = (
        "# Frontier\n\n"
        "## Default Workflow\n\n"
        "- Demand a structural fix that names the dominant line, what old answer stops working, what new answer becomes correct, and what reward, information, or cost changed to cause that shift.\n"
        "- Map the wrong habit to the right habit, say which reward loop currently trains the wrong habit, say what player behavior must disappear, and say what replacement behavior must become optimal.\n"
        "- Reject repairs that are not just numeric tuning when they keep the same dominant line, the same read, the same consequence structure, and the same decision landscape.\n\n"
        "## Quality Checks\n\n"
        "- Hard fail variation named but same dominant line, same read, or same consequence under a new label.\n"
        "- Hard fail habit mapping named but reward loop unchanged.\n"
        "- Hard fail solved-state repair named but decision landscape unchanged.\n"
        "- Hard fail numeric-only, content-only, pacing-only, or throughput-only fixes.\n\n"
        "## Common Pitfalls: Collapse Patterns and Repairs\n\n"
        "### Variety Without Strategic Consequence\n"
        "- Fake version: fake variation keeps the same dominant line and the same read.\n"
        "- Structural replacement: change reward, information, or cost so the old answer stops working and a new answer becomes correct.\n"
        "### Wrong Behavior Training\n"
        "- Fake version: fake reinforcement loop keeps rewarding the same safe behavior.\n"
        "- Structural replacement: name the reward loop currently training the wrong habit and make the replacement behavior become optimal.\n"
        "### Numeric-Only Repair\n"
        "- Fake version: numeric-only fake fix keeps the same dominant line, the same read, and the same consequence structure alive.\n"
        "- Structural replacement: change the decision landscape first so the old answer stops working.\n"
    )
    candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:pressure_audit_v2:1',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='pressure_audit_v2',
        strategy_profile={},
        rendered_markdown=(
            "# Candidate\n\n"
            "## Default Workflow\n\n"
            "- Demand a structural fix that names the dominant line, what old answer stops working because of the reward, information, or cost shift, what new answer becomes correct because of that shift, and what reward, information, or cost shift kills the old answer.\n"
            "- Map the wrong habit to the right habit, say which reward loop currently trains the wrong habit, say what player behavior must disappear, say what replacement behavior must become optimal, say what replacement reward logic makes the right habit profitable, and say when the wrong habit stops paying.\n"
            "- Reject repairs that are not just numeric tuning when they keep the same dominant line still winning, the same read still solving, the same consequence structure still paying out, and the decision landscape unchanged before balance values are tuned.\n\n"
            "## Quality Checks\n\n"
            "- Hard fail variation named but same dominant line, same read, or same consequence under a new label.\n"
            "- Hard fail the same dominant line still winning, the same read under a new label, or the same consequence under a new label.\n"
            "- Hard fail habit mapping named but reward loop unchanged, the wrong habit still pays, or replacement behavior never becomes optimal.\n"
            "- Hard fail solved-state repair named but decision landscape unchanged before balance values are tuned, or the same consequence structure still pays out.\n"
            "- Hard fail numeric-only, content-only, pacing-only, or throughput-only fixes.\n\n"
            "## Common Pitfalls: Collapse Patterns and Repairs\n\n"
            "### Variety Without Strategic Consequence\n"
            "- Fake version: fake variation keeps the same dominant line still winning and the same answer survives under a new label.\n"
            "- Structural replacement: change reward, information, or cost so the old answer stops working because the shift kills the old answer and a new answer becomes correct.\n"
            "### Wrong Behavior Training\n"
            "- Fake version: fake reinforcement loop keeps rewarding the same safe behavior, the wrong habit still pays, and the reward logic never changes.\n"
            "- Structural replacement: rewrite the replacement reward logic so the right habit becomes the profitable answer and the replacement behavior becomes optimal because of the new pressure.\n"
            "### Numeric-Only Repair\n"
            "- Fake version: numeric-only fake fix keeps the same dominant line still winning and the same consequence structure still paying out.\n"
            "- Structural replacement: change the decision landscape first so the old answer stops working before balance values are tuned.\n"
        ),
    )
    monkeypatch.setattr(studio, '_current_best_markdown', lambda skill_name: frontier_markdown)

    original_probe_specs = studio._decision_loop_outcome_probe_specs

    def _filtered_probe_specs(*, mode: str = 'probe_expanded_v4'):
        if mode != 'probe_expanded_v8':
            return list(original_probe_specs(mode=mode))
        return [
            {
                'probe_id': 'decision.variation-without-read-change',
                'pressure_terms': [
                    'dominant line',
                    'old answer stops working because',
                    'new answer becomes correct because',
                    'reward, information, or cost shift kills the old answer',
                ],
                'false_fix_terms': [
                    'same dominant line still wins',
                    'same answer survives under a new label',
                    'structural replacement',
                ],
            },
            {
                'probe_id': 'decision.reinforcement-without-habit-mapping',
                'pressure_terms': [
                    'wrong habit',
                    'right habit',
                    'reward loop currently trains',
                    'replacement reward logic',
                ],
                'false_fix_terms': [
                    'wrong habit still pays',
                    'replacement behavior becomes optimal',
                    'structural replacement',
                ],
            },
            {
                'probe_id': 'decision.solved-state-numeric-only-repair',
                'pressure_terms': [
                    'not just numeric tuning',
                    'same dominant line still wins',
                    'same read still solves',
                    'decision landscape',
                ],
                'false_fix_terms': [
                    'same consequence structure still pays out',
                    'decision landscape unchanged before balance values are tuned',
                    'structural replacement',
                ],
            },
        ]

    monkeypatch.setattr(studio, '_decision_loop_outcome_probe_specs', _filtered_probe_specs)
    monkeypatch.setattr(
        studio,
        '_candidate_editorial_metrics',
        lambda **kwargs: {
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'editorial_force': type('Force', (), {})(),
        },
    )

    report = studio._build_outcome_only_reranker_report(
        skill_name='decision-loop-stress-test',
        scored_candidates=[(candidate, {'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})()})],
        probe_mode='probe_expanded_v8',
    )

    assert report is not None
    assert report.frontier_comparison_status == 'beaten'
    assert {
        'decision.variation-without-read-change',
        'decision.reinforcement-without-habit-mapping',
        'decision.solved-state-numeric-only-repair',
    } <= set(report.improved_probe_ids)


def test_outcome_only_reranker_requires_stronger_v9_section_bundle_for_improvement(monkeypatch):
    frontier_markdown = (
        "# Frontier\n\n"
        "## Default Workflow\n\n"
        "- Demand a structural fix that names the dominant line, what old answer stops working because of the reward, information, or cost shift, what new answer becomes correct because of that shift, and what reward, information, or cost shift kills the old answer.\n"
        "- Map the wrong habit to the right habit, say which reward loop currently trains the wrong habit, say what player behavior must disappear, and say what replacement behavior must become optimal.\n"
        "- Reject repairs that are not just numeric tuning when they keep the same dominant line still winning, the same read still solving, the same consequence structure still paying out, and the decision landscape unchanged before balance values are tuned.\n\n"
        "## Quality Checks\n\n"
        "- Hard fail variation named but same dominant line, same read, or same consequence under a new label.\n"
        "- Hard fail habit mapping named but reward loop unchanged.\n"
        "- Hard fail solved-state repair named but decision landscape unchanged before balance values are tuned.\n"
        "- Hard fail numeric-only, content-only, pacing-only, or throughput-only fixes.\n\n"
        "## Common Pitfalls: Collapse Patterns and Repairs\n\n"
        "### Variety Without Strategic Consequence\n"
        "- Fake version: fake variation keeps the same dominant line still wins under a new label and the same answer survives under a new label.\n"
        "- Structural replacement: change reward, information, or cost so the old answer stops working because the shift kills the old answer.\n"
        "### Wrong Behavior Training\n"
        "- Fake version: fake reinforcement loop keeps rewarding the same safe behavior and the wrong habit still pays.\n"
        "- Structural replacement: rewrite the replacement reward logic so the right habit becomes the profitable answer.\n"
        "### Numeric-Only Repair\n"
        "- Fake version: numeric-only fake fix keeps the same dominant line still winning and the same consequence structure still paying out.\n"
        "- Structural replacement: change the decision landscape first so the old answer stops working before balance values are tuned.\n"
    )
    candidate = SkillRealizationCandidate(
        candidate_id='decision-loop-stress-test:pressure_audit_v2:1',
        skill_name='decision-loop-stress-test',
        program_id='decision-loop-stress-test:execution_spine',
        realization_strategy='pressure_audit_v2',
        strategy_profile={},
        rendered_markdown=(
            "# Candidate\n\n"
            "## Default Workflow\n\n"
            "- Demand a structural fix that names the dominant line, what old answer stops working because of the reward, information, or cost shift, what new answer becomes correct because of that shift, what reward, information, or cost changed to cause that shift, and what reward, information, or cost shift causes that change.\n"
        "- Map the wrong habit to the right habit, say which reward loop currently trains the wrong habit, name the behavior shift, say what player behavior must disappear, say what replacement behavior must become optimal, say what replacement behavior becomes optimal because of the replacement reward logic, and say what reward, information, or cost shift causes that behavior shift.\n"
            "- Reject repairs that are not just numeric tuning when they keep the same dominant line still winning, the same read still solving, the same consequence structure still paying out, and the decision landscape unchanged before balance values are tuned; demand a fix that changes the decision landscape before balance values are tuned and makes the old answer stop working before balance values are tuned.\n\n"
            "## Quality Checks\n\n"
            "- Hard fail variation named but same dominant line, same read, or same consequence under a new label.\n"
            "- Hard fail the same dominant line still wins under a new label, the same answer survives under a new label, the same read under a new label, or the same consequence under a new label.\n"
            "- Hard fail habit mapping named but reward loop unchanged, the wrong habit still pays, replacement behavior never becomes optimal, or the replacement reward logic never changes.\n"
            "- Hard fail solved-state repair named but decision landscape unchanged before balance values are tuned, the same consequence structure still paying out, the old answer still working, or the new answer never becoming correct.\n"
            "- Hard fail numeric-only, content-only, pacing-only, or throughput-only fixes.\n\n"
            "## Common Pitfalls: Collapse Patterns and Repairs\n\n"
            "### Variety Without Strategic Consequence\n"
            "- Fake version: fake variation keeps the same dominant line still wins under a new label and the same answer survives under a new label.\n"
            "- Structural replacement: change reward, information, or cost so the old answer stops working because the shift kills the old answer, a new answer becomes required, and a new answer becomes correct because of the new pressure.\n"
            "### Wrong Behavior Training\n"
            "- Fake version: fake reinforcement loop keeps rewarding the same safe behavior, the wrong habit still pays, and the reward loop currently trains the wrong habit.\n"
            "- Structural replacement: rewrite the replacement reward logic so the right habit becomes the profitable answer, say what player behavior must disappear, say what replacement behavior must become optimal, make the replacement behavior becomes optimal because of the new pressure, and make the wrong habit stop paying.\n"
            "### Numeric-Only Repair\n"
            "- Fake version: numeric-only fake fix keeps the same dominant line still wins, the same read still solves, and the same consequence structure still pays out.\n"
            "- Structural replacement: change the decision landscape first so the old answer stops working before balance values are tuned and the new answer becomes correct after the decision landscape changes.\n"
        ),
    )
    monkeypatch.setattr(studio, '_current_best_markdown', lambda skill_name: frontier_markdown)
    original_probe_specs = studio._decision_loop_outcome_probe_specs

    def _filtered_probe_specs(*, mode: str = 'probe_expanded_v4'):
        if mode != 'probe_expanded_v9':
            return list(original_probe_specs(mode=mode))
        return [
            {
                'probe_id': 'decision.variation-without-read-change',
                'pressure_terms': [
                    'dominant line',
                    'old answer stops working because',
                    'new answer becomes correct because',
                    'reward, information, or cost changed to cause that shift',
                ],
                'false_fix_terms': [
                    'same dominant line still wins under a new label',
                    'same read under a new label',
                    'structural replacement',
                ],
            },
            {
                'probe_id': 'decision.reinforcement-without-habit-mapping',
                'pressure_terms': [
                    'wrong habit',
                    'right habit',
                    'reward loop currently trains',
                    'behavior shift',
                ],
                'false_fix_terms': [
                    'wrong habit still pays',
                    'replacement reward logic never changes',
                    'structural replacement',
                ],
            },
            {
                'probe_id': 'decision.solved-state-numeric-only-repair',
                'pressure_terms': [
                    'not just numeric tuning',
                    'same dominant line still wins',
                    'same read still solves',
                    'decision landscape changes before balance values are tuned',
                ],
                'false_fix_terms': [
                    'same consequence structure still pays out',
                    'old answer stops working before balance values are tuned',
                    'structural replacement',
                ],
            },
        ]

    monkeypatch.setattr(studio, '_decision_loop_outcome_probe_specs', _filtered_probe_specs)
    monkeypatch.setattr(
        studio,
        '_candidate_editorial_metrics',
        lambda **kwargs: {
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'editorial_force': type('Force', (), {})(),
        },
    )

    report = studio._build_outcome_only_reranker_report(
        skill_name='decision-loop-stress-test',
        scored_candidates=[(candidate, {'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})()})],
        probe_mode='probe_expanded_v9',
    )

    assert report is not None
    assert report.frontier_comparison_status == 'beaten'
    assert {
        'decision.variation-without-read-change',
        'decision.reinforcement-without-habit-mapping',
        'decision.solved-state-numeric-only-repair',
    } <= set(report.improved_probe_ids)


def test_decision_loop_promotion_requires_both_v8_and_v9_gates(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:pressure_audit_v2:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='pressure_audit_v2',
            strategy_profile={},
            rendered_markdown='# audit',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:fake_fix_rejection_v2:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='fake_fix_rejection_v2',
            strategy_profile={},
            rendered_markdown='# false-fix',
        ),
    ]
    strong_metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 1.0,
            'cut_sharpness_score': 1.0,
            'failure_repair_force': 1.0,
            'stop_condition_coverage': 1.0,
            'output_executability_score': 0.95,
            'section_force_distinctness': 1.0,
            'compression_without_loss': 0.83,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.04})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.90})(),
        'domain_move_coverage': 0.95,
        'section_depth_score': 0.97,
        'task_outcome_with_skill_average': 0.98,
        'shared_opening_phrase_ratio': 0.0,
        'cross_case_similarity': 0.23,
        'compression_without_loss': 0.83,
        'score': 1.02,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: strong_metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: {'score': 1.01})
    monkeypatch.setattr(
        studio,
        '_candidate_separation_report',
        lambda candidates: ('pass', 0.95, [{'candidate_id': item.candidate_id} for item in candidates]),
    )
    monkeypatch.setattr(
        studio,
        '_compare_to_dual_baselines',
        lambda **kwargs: studio.MonotonicImprovementReport(
            skill_name='decision-loop-stress-test',
            active_frontier_status='matched',
            best_balance_comparison_status='not_beaten',
            best_coverage_comparison_status='not_beaten',
            force_non_regression_status='pass',
            coverage_non_regression_status='pass',
            compactness_non_regression_status='pass',
            frontier_dominance_status='pass',
            compression_gain_status='neutral',
            promotion_status='hold',
            promotion_reason='hold_due_to_no_primary_win',
            primary_force_win_count=0,
        ),
    )
    monkeypatch.setattr(
        studio,
        '_residual_gap_report',
        lambda skill_name, metrics: studio.ResidualGapReport(
            skill_name=skill_name,
            target_focus='none',
            quality_check_target_status='pass',
            pressure_target_status='pass',
            leakage_target_status='pass',
            false_fix_rejection_status='pass',
            residual_gap_count=0,
            status='pass',
        ),
    )

    def _report_for_mode(**kwargs):
        probe_mode = kwargs.get('probe_mode')
        if probe_mode == 'probe_expanded_v8':
            return _outcome_only_report(
                winner='decision-loop-stress-test:pressure_audit_v2:1',
                candidate_ranking=[
                    'decision-loop-stress-test:pressure_audit_v2:1',
                    'decision-loop-stress-test:fake_fix_rejection_v2:2',
                ],
                status='pass',
                probe_mode='probe_expanded_v8',
                frontier_comparison_status='beaten',
                probe_pass_count=8,
                probe_count=8,
                improved_probe_count=2,
                blocked_probe_ids=[],
                matched_probe_ids=[],
                improved_probe_ids=[
                    'decision.variation-without-read-change',
                    'decision.reinforcement-without-habit-mapping',
                ],
            )
        return _outcome_only_report(
            winner='decision-loop-stress-test:pressure_audit_v2:1',
            candidate_ranking=[
                'decision-loop-stress-test:pressure_audit_v2:1',
                'decision-loop-stress-test:fake_fix_rejection_v2:2',
            ],
            status='pass',
            probe_mode='probe_expanded_v9',
            frontier_comparison_status='matched',
            blocking_reason='outcome_only_reranker_matches_but_improvements_below_threshold',
            probe_pass_count=8,
            probe_count=8,
            improved_probe_count=1,
            blocked_probe_ids=[],
            matched_probe_ids=['decision.midgame-autopilot'],
            improved_probe_ids=['decision.variation-without-read-change'],
        )

    monkeypatch.setattr(studio, '_build_outcome_only_reranker_report', _report_for_mode)

    _, _, promotion_decision, _ = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress a core loop',
        candidates=candidates,
    )

    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.reason == 'stable_but_no_breakthrough'
    assert promotion_decision.stable_but_no_breakthrough is True
    assert promotion_decision.outcome_only_probe_mode == 'probe_expanded_v9'
    assert promotion_decision.outcome_only_frontier_comparison_status == 'matched'


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
