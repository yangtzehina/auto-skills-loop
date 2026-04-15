from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.runtime import SkillRunRecord
from openclaw_skill_create.services.runtime_cycle import replay_runtime_runs


FIXTURE_ROOT = Path(__file__).resolve().parent / 'fixtures' / 'runtime_trace_replay'


def _load_trace_scenario(name: str) -> tuple[dict[str, object], list[SkillRunRecord]]:
    scenario_root = FIXTURE_ROOT / name
    manifest = json.loads((scenario_root / 'manifest.json').read_text(encoding='utf-8'))
    runs = [
        SkillRunRecord.model_validate(
            json.loads((scenario_root / relative_path).read_text(encoding='utf-8'))
        )
        for relative_path in list(manifest.get('run_files') or [])
    ]
    return manifest, runs


def test_runtime_trace_replay_uses_richer_trace_for_step_selection(monkeypatch):
    def fail_if_subprocess_used(*args, **kwargs):
        raise AssertionError('runtime trace replay should not invoke subprocess-backed OpenSpace analysis')

    monkeypatch.setattr('openclaw_skill_create.services.runtime_analysis.subprocess.run', fail_if_subprocess_used)

    manifest, runs = _load_trace_scenario('trace_precision_streak')
    results = replay_runtime_runs(runs)

    actual_actions = [
        result.analysis.skills_analyzed[0]['recommended_action']
        for result in results
    ]
    most_valuable_steps = [
        result.analysis.skills_analyzed[0]['most_valuable_step']
        for result in results
    ]
    misleading_steps = [
        result.analysis.skills_analyzed[0]['misleading_step']
        for result in results
    ]

    assert actual_actions == manifest['expected_actions']
    assert most_valuable_steps == manifest['expected_most_valuable_steps']
    assert misleading_steps == manifest['expected_misleading_steps']

    final_result = results[-1]
    final_item = final_result.analysis.skills_analyzed[0]
    assert final_result.followup.action == manifest['expected_final_followup_action']
    assert final_item['quality_score'] == manifest['expected_final_quality_score']
    assert final_item['usage_stats'] == manifest['expected_final_usage_stats']
    assert final_item['recent_run_ids'] == manifest['expected_final_recent_run_ids']
    assert final_result.followup.selected_plan is not None
    assert final_result.followup.selected_plan.requirement_gaps == manifest['expected_final_requirement_gaps']
