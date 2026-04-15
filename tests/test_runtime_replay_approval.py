from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_replay_approval import build_runtime_replay_approval_pack

from .runtime_test_helpers import FIXTURE_ROOT, copy_replay_scenario
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'


def test_runtime_replay_approval_pack_rejects_refresh_when_no_change():
    approval = build_runtime_replay_approval_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    assert approval.passed is True
    assert approval.current_recommended_action == 'keep_baseline'
    assert approval.approval_decision == 'reject_refresh'
    assert approval.allow_baseline_refresh is False
    assert approval.suggested_command == ''
    assert approval.pending_approval_summary.startswith('No baseline refresh is needed')


def test_runtime_replay_approval_pack_allows_refresh_for_drift_only(tmp_path: Path):
    baseline_path = tmp_path / 'baseline_report.json'
    payload = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    payload['scenario_baselines'][0]['actual_final_quality_score'] = 0.25
    baseline_path.write_text(json.dumps(payload), encoding='utf-8')

    approval = build_runtime_replay_approval_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=baseline_path,
    )

    assert approval.passed is True
    assert approval.current_recommended_action == 'refresh_baseline'
    assert approval.approval_decision == 'approve_refresh'
    assert approval.allow_baseline_refresh is True
    assert '--write-baseline' in approval.suggested_command
    assert 'Only baseline drift remains' in approval.pending_approval_summary


def test_runtime_replay_approval_pack_forces_investigation_on_manifest_failure(tmp_path: Path):
    fixtures_root = copy_replay_scenario(tmp_path, 'success_streak', fixtures_root=FIXTURE_ROOT)
    manifest_path = fixtures_root / 'success_streak' / 'manifest.json'
    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    payload['expected_actions'] = ['patch_current', 'patch_current', 'patch_current']
    manifest_path.write_text(json.dumps(payload), encoding='utf-8')

    approval = build_runtime_replay_approval_pack(
        fixtures_root=fixtures_root,
        baseline_path=BASELINE_PATH,
        scenario_names=['success_streak'],
    )

    assert approval.passed is False
    assert approval.current_recommended_action == 'investigate'
    assert approval.approval_decision == 'investigate_first'
    assert approval.allow_baseline_refresh is False
    assert 'run_runtime_replay_review.py' in approval.suggested_command
    assert 'blocked' in approval.pending_approval_summary
