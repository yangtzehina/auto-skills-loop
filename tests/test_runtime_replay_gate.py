from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_replay import (
    build_runtime_replay_gate_result,
    load_runtime_replay_baseline,
    write_runtime_replay_baseline,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / 'fixtures' / 'runtime_replay'
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'


def test_build_runtime_replay_gate_result_matches_default_baseline():
    gate = build_runtime_replay_gate_result(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    assert gate.passed is True
    assert gate.summary == (
        'Runtime replay drift gate complete: scenarios=3 '
        'manifest_failed=0 drifted=0 missing_baseline=0 extra_baseline=0'
    )
    assert len(gate.scenario_results) == 3


def test_build_runtime_replay_gate_result_surfaces_baseline_drift(tmp_path: Path):
    baseline_path = tmp_path / 'baseline_report.json'
    baseline = load_runtime_replay_baseline(BASELINE_PATH)
    payload = baseline.model_dump(mode='json')
    payload['scenario_baselines'][0]['actual_final_followup_action'] = 'derive_child'
    baseline_path.write_text(json.dumps(payload), encoding='utf-8')

    gate = build_runtime_replay_gate_result(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=baseline_path,
    )

    assert gate.passed is False
    assert gate.scenario_results[0].baseline_matched is False
    assert gate.scenario_results[0].drift_messages
    assert 'actual_final_followup_action drifted' in gate.scenario_results[0].drift_messages[0]


def test_write_runtime_replay_baseline_writes_snapshot(tmp_path: Path):
    baseline_path = tmp_path / 'baseline_report.json'

    baseline = write_runtime_replay_baseline(
        baseline_path,
        fixtures_root=FIXTURE_ROOT,
    )

    assert baseline_path.exists() is True
    loaded = load_runtime_replay_baseline(baseline_path)
    assert loaded.model_dump(mode='json') == baseline.model_dump(mode='json')
