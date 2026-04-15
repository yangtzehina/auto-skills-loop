from __future__ import annotations

import sys
from types import SimpleNamespace

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.runtime import EvolutionPlan, SkillRunAnalysis, SkillRunRecord
from openclaw_skill_create.services import runtime_cycle as mod
from openclaw_skill_create.services.runtime_cycle import run_runtime_cycle


def _patch_run_record() -> SkillRunRecord:
    return SkillRunRecord(
        run_id='run-cycle-patch',
        task_id='task-cycle-patch',
        task_summary='Exercise runtime cycle.',
        execution_result='failed',
        skills_used=[
            {
                'skill_id': 'demo-skill__v0_abcd1234',
                'skill_name': 'demo-skill',
                'skill_path': '/tmp/demo-skill',
                'selected': True,
                'applied': True,
                'steps_triggered': ['run scripts/build.py'],
            }
        ],
        failure_points=['The run scripts/build.py step used the wrong command.'],
        repo_paths=['/tmp/repo'],
    )


def test_run_runtime_cycle_returns_analysis_and_followup_for_patch():
    result = run_runtime_cycle(
        _patch_run_record(),
        OpenSpaceObservationPolicy(enabled=False),
    )

    assert result.run_id == 'run-cycle-patch'
    assert result.analysis.skills_analyzed[0]['recommended_action'] == 'patch_current'
    assert result.followup.action == 'patch_current'
    assert result.followup.repair_suggestions[0].issue_type == 'script_placeholder_heavy'
    assert 'store_persistence=skipped' in result.summary


def test_run_runtime_cycle_uses_analysis_for_derive_followup(monkeypatch):
    def fake_analyze_skill_run(run_record, policy, session_evidence=None):
        return SkillRunAnalysis(
            run_id=run_record.run_id,
            task_id=run_record.task_id,
            evolution_plans=[
                EvolutionPlan(
                    run_id=run_record.run_id,
                    skill_id='hf-trainer__v1_abcd1234',
                    action='derive_child',
                    summary='Derive a child trainer workflow.',
                    requirement_gaps=['Missing distributed resume step.'],
                )
            ],
            summary='fake analysis',
        )

    monkeypatch.setattr(mod, 'analyze_skill_run', fake_analyze_skill_run)

    result = run_runtime_cycle(
        SkillRunRecord(
            run_id='run-cycle-derive',
            task_id='task-cycle-derive',
            task_summary='Create a derived trainer skill.',
            skills_used=[],
            repo_paths=['/tmp/repo'],
        ),
        OpenSpaceObservationPolicy(enabled=False),
        skill_name_hint='hf-trainer-specialized',
    )

    assert result.followup.action == 'derive_child'
    assert result.followup.skill_create_request is not None
    assert result.followup.skill_create_request.skill_name_hint == 'hf-trainer-specialized-derived'
    assert result.followup.skill_create_request.repo_paths == ['/tmp/repo']
    assert 'Create a derived trainer skill.' in result.followup.skill_create_request.task


def test_run_runtime_cycle_keeps_result_when_helper_fails(monkeypatch):
    def fake_run(args, **kwargs):
        return SimpleNamespace(returncode=1, stdout='', stderr='boom')

    monkeypatch.setattr('openclaw_skill_create.services.runtime_analysis.subprocess.run', fake_run)

    result = run_runtime_cycle(
        _patch_run_record(),
        OpenSpaceObservationPolicy(enabled=True, openspace_python=sys.executable),
    )

    assert result.followup.action == 'patch_current'
    assert 'store_persistence=failed' in result.analysis.summary
    assert 'store_persistence=failed' in result.summary
