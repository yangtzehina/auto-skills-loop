from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_test_helpers import load_script_module

from openclaw_skill_create.services.skill_create_comparison import build_skill_create_comparison_report


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'run_skill_create_comparison.py'


def test_skill_create_comparison_uses_golden_baselines_without_hermes():
    report = build_skill_create_comparison_report(include_hermes=False)

    assert report.overall_status == 'pass'
    assert report.gap_count == 0
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
    assert report.dna_authoring_status == 'pass'
    assert report.candidate_dna_count >= 8
    assert report.usefulness_eval_status == 'pass'
    assert report.usefulness_gap_count == 0


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

    assert exit_code == 0
    sidecar = tmp_path / 'evals' / 'hermes_comparison.json'
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text(encoding='utf-8'))
    assert payload['overall_status'] == 'pass'
    assert payload['comparison_independence_status'] == 'golden_only'
    assert payload['depth_quality_gap_count'] == 0
    assert payload['editorial_gap_count'] == 0
    assert payload['style_gap_count'] == 0
    assert payload['move_quality_gap_count'] == 0
    assert payload['dna_authoring_status'] == 'pass'
    assert payload['usefulness_eval_status'] == 'pass'
