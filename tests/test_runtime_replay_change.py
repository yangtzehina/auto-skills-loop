from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_replay_change import build_runtime_replay_change_pack

from .runtime_test_helpers import FIXTURE_ROOT, copy_replay_scenario
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'


def test_build_runtime_replay_change_pack_passes_when_no_changes():
    change_pack = build_runtime_replay_change_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    assert change_pack.passed is True
    assert change_pack.recommended_action == 'keep_baseline'
    assert change_pack.write_baseline_recommended is False
    assert change_pack.affected_scenarios == []


def test_build_runtime_replay_change_pack_recommends_baseline_refresh_for_drift(tmp_path: Path):
    baseline_path = tmp_path / 'baseline_report.json'
    payload = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    payload['scenario_baselines'][0]['actual_final_quality_score'] = 0.25
    baseline_path.write_text(json.dumps(payload), encoding='utf-8')

    change_pack = build_runtime_replay_change_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=baseline_path,
    )

    assert change_pack.passed is False
    assert change_pack.recommended_action == 'refresh_baseline'
    assert change_pack.write_baseline_recommended is True
    assert change_pack.drifted_scenarios
    assert '--write-baseline' in change_pack.baseline_refresh_command


def test_build_runtime_replay_change_pack_recommends_investigation_for_manifest_failure(tmp_path: Path):
    fixtures_root = copy_replay_scenario(tmp_path, 'success_streak', fixtures_root=FIXTURE_ROOT)
    manifest_path = fixtures_root / 'success_streak' / 'manifest.json'
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    payload['expected_actions'] = ['patch_current', 'patch_current', 'patch_current']
    manifest_path.write_text(json.dumps(payload), encoding='utf-8')

    change_pack = build_runtime_replay_change_pack(
        fixtures_root=fixtures_root,
        baseline_path=BASELINE_PATH,
        scenario_names=['success_streak'],
    )

    assert change_pack.passed is False
    assert change_pack.recommended_action == 'investigate'
    assert change_pack.write_baseline_recommended is False
    assert 'success_streak' in change_pack.blocking_scenarios
