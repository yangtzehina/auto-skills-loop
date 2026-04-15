from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_cycle import replay_runtime_runs

from .runtime_test_helpers import FIXTURE_ROOT, load_replay_scenario


def _assert_replay_scenario(name: str, monkeypatch) -> None:
    def fail_if_subprocess_used(*args, **kwargs):
        raise AssertionError('runtime replay should not invoke subprocess-backed OpenSpace analysis')

    monkeypatch.setattr('openclaw_skill_create.services.runtime_analysis.subprocess.run', fail_if_subprocess_used)

    manifest, runs = load_replay_scenario(name, fixtures_root=FIXTURE_ROOT)
    results = replay_runtime_runs(runs)

    expected_actions = list(manifest['expected_actions'])
    actual_actions = [
        result.analysis.skills_analyzed[0]['recommended_action']
        for result in results
    ]
    assert actual_actions == expected_actions

    final_result = results[-1]
    final_item = final_result.analysis.skills_analyzed[0]
    assert final_result.followup.action == manifest['expected_final_followup_action']
    assert final_item['quality_score'] == manifest['expected_final_quality_score']
    assert final_item['usage_stats'] == manifest['expected_final_usage_stats']
    assert final_item['recent_run_ids'] == manifest['expected_final_recent_run_ids']
    assert final_result.followup.selected_plan is not None
    assert final_result.followup.selected_plan.requirement_gaps == manifest['expected_final_requirement_gaps']

    scenario_id = manifest['scenario_id']
    if scenario_id == 'success_streak':
        assert final_result.followup.noop is True
        assert final_result.followup.repair_suggestions == []
        assert final_result.followup.skill_create_request is None
    elif scenario_id == 'misleading_streak':
        assert final_result.followup.action == 'patch_current'
        assert final_result.followup.noop is False
        assert final_result.followup.repair_suggestions
        assert final_result.followup.skill_create_request is None
    elif scenario_id == 'stable_gap_streak':
        assert final_result.followup.action == 'derive_child'
        assert final_result.followup.noop is False
        assert final_result.followup.repair_suggestions == []
        assert final_result.followup.skill_create_request is not None
    else:  # pragma: no cover - defensive fixture guard
        raise AssertionError(f'Unknown replay scenario: {scenario_id}')


def test_runtime_replay_success_streak(monkeypatch):
    _assert_replay_scenario('success_streak', monkeypatch)


def test_runtime_replay_misleading_streak(monkeypatch):
    _assert_replay_scenario('misleading_streak', monkeypatch)


def test_runtime_replay_stable_gap_streak(monkeypatch):
    _assert_replay_scenario('stable_gap_streak', monkeypatch)
