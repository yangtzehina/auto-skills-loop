from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_test_helpers import load_script_module

from openclaw_skill_create.services.skill_create_comparison import build_skill_create_comparison_report


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'run_skill_create_comparison.py'


def test_skill_create_comparison_uses_golden_baselines_without_hermes():
    report = build_skill_create_comparison_report(include_hermes=False)

    assert report.overall_status in {'breakthrough', 'stable_but_no_breakthrough', 'fail'}
    assert report.gap_count >= 0
    assert len(report.cases) == 3
    assert report.comparison_independence_status == 'golden_only'
    assert report.reference_role == 'quality_baseline'
    assert all(item.auto_metrics.body_quality_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.self_review_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.domain_specificity_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.domain_expertise_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.depth_quality_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.editorial_quality_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.style_diversity_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.move_quality_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.editorial_force_status in {'pass', 'warn'} for item in report.cases)
    assert all(item.auto_metrics.pairwise_promotion_status in {'promote', 'hold'} for item in report.cases)
    assert all(item.auto_metrics.realization_candidate_count >= 2 for item in report.cases)
    assert all(item.auto_metrics.domain_move_coverage >= 0.55 for item in report.cases)
    assert all(item.auto_metrics.expert_depth_recall >= 0.70 for item in report.cases)
    assert all(item.auto_metrics.section_depth_score >= 0.65 for item in report.cases)
    assert all(item.auto_metrics.decision_pressure_score >= 0.70 for item in report.cases)
    assert all(item.auto_metrics.output_executability_score >= 0.70 for item in report.cases)
    assert all(item.auto_metrics.profile_specific_label_coverage >= 0.70 for item in report.cases)
    assert all(item.auto_metrics.shared_opening_phrase_ratio <= 0.35 for item in report.cases)
    assert all(item.auto_metrics.shared_step_label_ratio <= 0.55 for item in report.cases)
    assert all(item.auto_metrics.expert_move_recall >= 0.85 for item in report.cases)
    assert all(item.auto_metrics.decision_rule_coverage >= 0.75 for item in report.cases)
    assert all(item.auto_metrics.output_field_semantics_coverage >= 0.75 for item in report.cases)
    assert all(item.auto_metrics.failure_repair_coverage >= 0.75 for item in report.cases)
    assert all(item.auto_metrics.numbered_workflow_spine_present for item in report.cases)
    assert all(item.auto_metrics.program_fidelity_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.execution_move_recall >= 0.85 for item in report.cases)
    assert all(item.auto_metrics.execution_move_order_alignment >= 0.80 for item in report.cases)
    assert all(item.auto_metrics.task_outcome_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.cut_sharpness_score >= 0.70 for item in report.cases)
    assert all(item.auto_metrics.failure_repair_force >= 0.70 for item in report.cases)
    assert all(item.auto_metrics.section_rhythm_distinctness >= 0.70 for item in report.cases)
    assert all(item.auto_metrics.compression_without_loss >= 0.65 for item in report.cases)
    assert report.dna_authoring_status == 'pass'
    assert report.candidate_dna_count >= 8
    assert report.program_authoring_status == 'pass'
    assert report.candidate_program_count >= 8
    assert report.usefulness_eval_status == 'pass'
    assert report.usefulness_gap_count == 0
    assert report.task_outcome_status == 'pass'
    assert report.task_outcome_gap_count == 0
    assert report.editorial_force_gap_count >= 0
    assert report.candidate_separation_gap_count == 0
    assert report.coverage_non_regression_status in {'pass', 'fail'}
    assert report.compactness_non_regression_status in {'pass', 'fail'}
    assert report.frontier_dominance_status in {'pass', 'fail'}
    assert report.active_frontier_status in {'pass', 'fail'}
    assert report.best_balance_not_beaten_count >= 0
    assert report.best_coverage_not_beaten_count >= 0
    assert report.current_best_not_beaten_count >= 0
    assert report.promotion_hold_count >= 0
    assert report.residual_gap_count >= 0
    assert report.force_non_regression_status == 'pass'
    assert report.pairwise_promotion_gap_count >= 0
    assert report.program_fidelity_gap_count == 0
    assert report.negative_case_resistance >= 0.80
    assert report.program_regression_count == 0
    assert all(item.auto_metrics.candidate_separation_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.force_non_regression_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.coverage_non_regression_status in {'pass', 'fail'} for item in report.cases)
    assert all(item.auto_metrics.compactness_non_regression_status in {'pass', 'fail'} for item in report.cases)
    assert all(item.auto_metrics.current_best_comparison_status in {'beaten', 'not_beaten', 'missing_current_best'} for item in report.cases)
    assert all(item.auto_metrics.best_balance_comparison_status in {'beaten', 'not_beaten'} for item in report.cases)
    assert all(item.auto_metrics.best_coverage_comparison_status in {'beaten', 'not_beaten'} for item in report.cases)
    assert all(item.auto_metrics.active_frontier_status in {'matched', 'beaten', 'regressed'} for item in report.cases)
    assert all(item.auto_metrics.quality_check_target_status in {'pass', 'fail', 'unknown'} for item in report.cases)
    assert all(item.auto_metrics.pressure_target_status in {'pass', 'fail', 'unknown'} for item in report.cases)
    assert all(item.auto_metrics.leakage_target_status in {'pass', 'fail', 'unknown'} for item in report.cases)
    assert all(item.auto_metrics.false_fix_rejection_status in {'pass', 'fail', 'unknown'} for item in report.cases)
    assert all(item.auto_metrics.residual_gap_count >= 0 for item in report.cases)
    assert all(len(item.auto_metrics.candidate_strategy_matrix) >= 4 for item in report.cases)
    decision_case = next(item for item in report.cases if item.skill_name == 'decision-loop-stress-test')
    assert isinstance(decision_case.auto_metrics.outcome_only_probe_witness_summary, list)
    assert isinstance(decision_case.auto_metrics.outcome_only_blocked_probe_ids, list)
    assert isinstance(decision_case.auto_metrics.outcome_only_repair_evidence_lines, list)
    assert isinstance(decision_case.auto_metrics.outcome_only_collapse_evidence_lines, list)
    assert '- auto_outcome_only_probe_witness_summary=' in report.markdown_summary
    assert '- auto_outcome_only_repair_evidence_lines=' in report.markdown_summary
    if report.overall_status == 'stable_but_no_breakthrough':
        assert report.gap_count == 0
        assert report.stable_but_no_breakthrough_count >= 1
    if report.overall_status == 'fail':
        assert (
            report.editorial_force_gap_count > 0
            or report.current_best_not_beaten_count > 0
            or report.best_balance_not_beaten_count > 0
            or report.best_coverage_not_beaten_count > 0
            or report.promotion_hold_count > 0
            or report.pairwise_promotion_gap_count > 0
            or report.coverage_non_regression_status == 'fail'
            or report.compactness_non_regression_status == 'fail'
            or report.frontier_dominance_status == 'fail'
        )
        assert any(item.auto_metrics.editorial_force_status in {'warn', 'fail'} for item in report.cases)
    if report.overall_status == 'breakthrough':
        assert report.gap_count == 0
    elif report.overall_status == 'fail':
        assert report.gap_count >= 1


def test_skill_create_comparison_cli_writes_sidecar(tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_skill_create_comparison')
    exit_code = module.main(
        [
            'run_skill_create_comparison.py',
            '--format',
            'json',
            '--output-root',
            str(tmp_path),
        ]
    )

    assert exit_code in {0, 1}
    sidecar = tmp_path / 'evals' / 'hermes_comparison.json'
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text(encoding='utf-8'))
    assert payload['overall_status'] in {'breakthrough', 'stable_but_no_breakthrough', 'fail'}
    assert payload['comparison_independence_status'] == 'golden_only'
    assert payload['depth_quality_gap_count'] == 0
    assert payload['editorial_gap_count'] == 0
    assert payload['style_gap_count'] == 0
    assert payload['move_quality_gap_count'] == 0
    assert payload['editorial_force_gap_count'] >= 0
    assert payload['candidate_separation_gap_count'] == 0
    assert payload['force_non_regression_status'] == 'pass'
    assert payload['coverage_non_regression_status'] in {'pass', 'fail'}
    assert payload['compactness_non_regression_status'] in {'pass', 'fail'}
    assert payload['frontier_dominance_status'] in {'pass', 'fail'}
    assert payload['active_frontier_status'] in {'pass', 'fail'}
    assert payload['pairwise_promotion_gap_count'] >= 0
    assert payload['program_fidelity_gap_count'] == 0
    assert payload['residual_gap_count'] >= 0
    assert payload['dna_authoring_status'] == 'pass'
    assert payload['program_authoring_status'] == 'pass'
    assert payload['usefulness_eval_status'] == 'pass'
    assert payload['task_outcome_status'] == 'pass'
