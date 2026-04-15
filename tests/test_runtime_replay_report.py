from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_replay import build_runtime_replay_report


FIXTURE_ROOT = Path(__file__).resolve().parent / 'fixtures' / 'runtime_replay'


def test_build_runtime_replay_report_passes_against_default_fixtures():
    report = build_runtime_replay_report(fixtures_root=FIXTURE_ROOT)

    assert report.passed is True
    assert len(report.scenario_reports) == 3
    assert report.summary == 'Runtime replay report complete: scenarios=3 passed=3 failed=0'


def test_build_runtime_replay_report_can_filter_single_scenario():
    report = build_runtime_replay_report(
        fixtures_root=FIXTURE_ROOT,
        scenario_names=['stable_gap_streak'],
    )

    assert report.passed is True
    assert len(report.scenario_reports) == 1
    scenario = report.scenario_reports[0]
    assert scenario.scenario_id == 'stable_gap_streak'
    assert scenario.actual_final_followup_action == 'derive_child'


def test_build_runtime_replay_report_surfaces_manifest_mismatch(tmp_path: Path):
    scenario_root = tmp_path / 'runtime_replay' / 'success_streak'
    run_root = scenario_root / 'runs'
    run_root.mkdir(parents=True)

    source_root = FIXTURE_ROOT / 'success_streak'
    manifest = json.loads((source_root / 'manifest.json').read_text(encoding='utf-8'))
    manifest['expected_actions'] = ['patch_current', 'patch_current', 'patch_current']
    (scenario_root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    for run_file in (source_root / 'runs').glob('*.json'):
        (run_root / run_file.name).write_text(run_file.read_text(encoding='utf-8'), encoding='utf-8')

    report = build_runtime_replay_report(fixtures_root=tmp_path / 'runtime_replay')

    assert report.passed is False
    assert len(report.scenario_reports) == 1
    scenario = report.scenario_reports[0]
    assert scenario.passed is False
    assert scenario.mismatches
    assert 'expected_actions' in scenario.mismatches[0]
