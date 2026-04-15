from __future__ import annotations

from openclaw_skill_create.models.runtime import EvolutionPlan, SkillRunAnalysis
from openclaw_skill_create.services.runtime_followup import (
    build_runtime_followup_result,
    select_runtime_followup_plan,
)


def test_select_runtime_followup_plan_prefers_first_actionable():
    analysis = SkillRunAnalysis(
        run_id='run-1',
        task_id='task-1',
        evolution_plans=[
            EvolutionPlan(run_id='run-1', skill_id='skill-a', action='no_change', summary='Nothing to do.'),
            EvolutionPlan(run_id='run-1', skill_id='skill-b', action='patch_current', summary='Patch the current skill.'),
            EvolutionPlan(run_id='run-1', skill_id='skill-c', action='derive_child', summary='Derive a child skill.'),
        ],
    )

    plan = select_runtime_followup_plan(analysis)

    assert plan is not None
    assert plan.skill_id == 'skill-b'


def test_build_runtime_followup_result_returns_patch_suggestions():
    result = build_runtime_followup_result(
        EvolutionPlan(
            run_id='run-patch',
            skill_id='skill-patch',
            action='patch_current',
            summary='Patch the current skill.',
            repair_suggestions=[
                {
                    'issue_type': 'script_placeholder_heavy',
                    'instruction': 'Repair the runtime script guidance.',
                    'target_paths': ['scripts/build.py'],
                    'priority': 90,
                }
            ],
        )
    )

    assert result.action == 'patch_current'
    assert result.noop is False
    assert result.skill_create_request is None
    assert result.repair_suggestions[0].issue_type == 'script_placeholder_heavy'
    assert result.repair_suggestions[0].repair_scope == 'body_patch'


def test_build_runtime_followup_result_returns_derive_request_with_defaults():
    result = build_runtime_followup_result(
        EvolutionPlan(
            run_id='run-derive',
            skill_id='hf-trainer__v1_abcd1234',
            action='derive_child',
            summary='Derive a child skill for trainer resume workflows.',
            reason='Recurring trainer resume gaps were observed.',
            requirement_gaps=['Missing Hugging Face trainer resume step.'],
        )
    )

    assert result.action == 'derive_child'
    assert result.noop is False
    assert result.repair_suggestions == []
    assert result.skill_create_request is not None
    assert result.skill_create_request.parent_skill_id == 'hf-trainer__v1_abcd1234'
    assert result.skill_create_request.task.count('Derive a child skill for trainer resume workflows.') == 1


def test_build_runtime_followup_result_returns_noop_for_no_change():
    result = build_runtime_followup_result(
        EvolutionPlan(
            run_id='run-noop',
            skill_id='skill-noop',
            action='no_change',
            summary='No runtime follow-up is required.',
        )
    )

    assert result.action == 'no_change'
    assert result.noop is True
    assert result.selected_plan is not None
    assert result.repair_suggestions == []
    assert result.skill_create_request is None


def test_build_runtime_followup_result_returns_noop_when_analysis_has_no_plans():
    result = build_runtime_followup_result(
        SkillRunAnalysis(run_id='run-empty', task_id='task-empty', evolution_plans=[])
    )

    assert result.action == 'no_change'
    assert result.noop is True
    assert result.selected_plan is None
    assert 'No runtime evolution plans were available' in result.summary


def test_build_runtime_followup_result_honors_plan_index_and_request_overrides():
    analysis = SkillRunAnalysis(
        run_id='run-2',
        task_id='task-2',
        evolution_plans=[
            EvolutionPlan(run_id='run-2', skill_id='skill-a', action='patch_current', summary='Patch A.'),
            EvolutionPlan(
                run_id='run-2',
                skill_id='skill-b',
                action='derive_child',
                summary='Derive B.',
                requirement_gaps=['Missing repo-specific validator step.'],
            ),
        ],
    )

    result = build_runtime_followup_result(
        analysis,
        plan_index=1,
        task_summary='Create a more specialized child skill.',
        repo_paths=['/tmp/repo'],
        skill_name_hint='specialized-b',
    )

    assert result.action == 'derive_child'
    assert result.selected_plan is not None
    assert result.selected_plan.skill_id == 'skill-b'
    assert result.skill_create_request is not None
    assert result.skill_create_request.skill_name_hint == 'specialized-b-derived'
    assert result.skill_create_request.repo_paths == ['/tmp/repo']
    assert 'Create a more specialized child skill.' in result.skill_create_request.task
