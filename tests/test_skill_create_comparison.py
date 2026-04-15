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
    assert all(item.auto_metrics.body_quality_status == 'pass' for item in report.cases)
    assert all(item.auto_metrics.self_review_status == 'pass' for item in report.cases)


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
