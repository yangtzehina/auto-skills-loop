from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.diagnostics import Diagnostics, ValidationResult
from openclaw_skill_create.models.findings import RepoFindings
from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.models.runtime import SkillRunAnalysis, SkillRunRecord
from openclaw_skill_create.models.runtime_cycle import RuntimeCycleResult
from openclaw_skill_create.models.runtime_followup import RuntimeFollowupResult
from openclaw_skill_create.models.runtime_hook import RuntimeHookResult
from openclaw_skill_create.models.runtime_replay_approval import RuntimeReplayApprovalPack
from openclaw_skill_create.models.runtime_replay_change import RuntimeReplayChangePack
from openclaw_skill_create.models.runtime_replay_review import RuntimeReplayReviewResult
from openclaw_skill_create.services.orchestrator import run_skill_create
from openclaw_skill_create.services.runtime_hook import run_runtime_hook


def _make_repo_findings() -> RepoFindings:
    return RepoFindings(repos=[], cross_repo_signals=[], overall_recommendation='ok')


def _make_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='demo-skill',
        files_to_create=[PlannedFile(path='SKILL.md', purpose='entry')],
    )


def _make_artifacts() -> Artifacts:
    return Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='---\nname: demo-skill\ndescription: demo\n---\n',
            )
        ]
    )


def _make_diagnostics() -> Diagnostics:
    return Diagnostics(validation=ValidationResult(summary=['ok']))


def _make_run_record() -> SkillRunRecord:
    return SkillRunRecord(
        run_id='run-hook',
        task_id='task-hook',
        task_summary='Exercise runtime hook.',
        execution_result='failed',
        skills_used=[
            {
                'skill_id': 'demo-skill__v0_test',
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


def _make_hook_result() -> RuntimeHookResult:
    review = RuntimeReplayReviewResult(
        fixture_root='/tmp/runtime_replay',
        baseline_path='/tmp/runtime_replay/baseline_report.json',
        total_scenarios=1,
        passed_scenarios=1,
        failed_scenarios=0,
        passed=True,
        summary='review ok',
    )
    change_pack = RuntimeReplayChangePack(
        fixture_root=review.fixture_root,
        baseline_path=review.baseline_path,
        review=review,
        recommended_action='keep_baseline',
        passed=True,
        summary='change ok',
    )
    approval_pack = RuntimeReplayApprovalPack(
        fixture_root=review.fixture_root,
        baseline_path=review.baseline_path,
        change_pack=change_pack,
        current_recommended_action='keep_baseline',
        approval_decision='reject_refresh',
        allow_baseline_refresh=False,
        passed=True,
        summary='approval ok',
    )
    return RuntimeHookResult(
        applied=True,
        runtime_cycle=RuntimeCycleResult(
            run_id='run-hook',
            task_id='task-hook',
            analysis=SkillRunAnalysis(run_id='run-hook', task_id='task-hook', skills_analyzed=[], evolution_plans=[]),
            followup=RuntimeFollowupResult(action='patch_current', noop=False, summary='patch current'),
            summary='cycle ok',
        ),
        replay_review=review,
        change_pack=change_pack,
        approval_pack=approval_pack,
        summary='hook ok',
    )


def test_run_runtime_hook_returns_runtime_envelope():
    result = run_runtime_hook(
        run_record=_make_run_record(),
        policy=OpenSpaceObservationPolicy(enabled=False),
        scenario_names=['success_streak'],
    )

    assert result.applied is True
    assert result.runtime_cycle is not None
    assert result.runtime_cycle.followup.action == 'patch_current'
    assert result.replay_review is not None
    assert result.change_pack is not None
    assert result.approval_pack is not None
    assert result.judge_pack is None


def test_orchestrator_does_not_call_runtime_hook_when_disabled(monkeypatch, tmp_path: Path):
    from openclaw_skill_create.services import orchestrator as mod

    output_dir = tmp_path / 'demo-skill'
    output_dir.mkdir()
    monkeypatch.setattr(mod, 'run_extractor', lambda **kwargs: _make_repo_findings())
    monkeypatch.setattr(mod, 'run_planner', lambda **kwargs: _make_skill_plan())
    monkeypatch.setattr(mod, 'run_generator', lambda **kwargs: _make_artifacts())
    monkeypatch.setattr(mod, 'run_validator', lambda **kwargs: _make_diagnostics())

    def fail_runtime_hook(**kwargs):
        raise AssertionError('runtime hook should not be called when disabled')

    response = run_skill_create(
        SkillCreateRequestV6(task='build skill'),
        persist_artifacts_fn=lambda **kwargs: {
            'applied': True,
            'written_files': [str(output_dir / 'SKILL.md')],
            'output_root': str(output_dir),
            'severity': kwargs['severity'],
        },
        observe_with_openspace_fn=lambda **kwargs: {'applied': False, 'reason': 'skip'},
        run_runtime_hook_fn=fail_runtime_hook,
        observation_policy=OpenSpaceObservationPolicy(enabled=False),
        repair_fn=lambda **kwargs: None,
    )

    assert response.observation == {'applied': False, 'reason': 'skip'}
    assert all('Runtime hook:' not in note for note in response.diagnostics.notes)


def test_orchestrator_runtime_hook_adds_observation_and_note_when_enabled(monkeypatch, tmp_path: Path):
    from openclaw_skill_create.services import orchestrator as mod

    output_dir = tmp_path / 'demo-skill'
    output_dir.mkdir()
    monkeypatch.setattr(mod, 'run_extractor', lambda **kwargs: _make_repo_findings())
    monkeypatch.setattr(mod, 'run_planner', lambda **kwargs: _make_skill_plan())
    monkeypatch.setattr(mod, 'run_generator', lambda **kwargs: _make_artifacts())
    monkeypatch.setattr(mod, 'run_validator', lambda **kwargs: _make_diagnostics())

    captured: dict[str, object] = {}

    def runtime_hook_stub(**kwargs):
        captured.update(kwargs)
        return _make_hook_result()

    fake_llm_runner = lambda messages, model: '{}'

    response = run_skill_create(
        SkillCreateRequestV6(
            task='build skill',
            enable_runtime_hook=True,
            runtime_run_record=_make_run_record(),
            runtime_hook_scenarios=['success_streak'],
            enable_runtime_llm_judge=True,
            runtime_judge_model='gpt-test',
        ),
        persist_artifacts_fn=lambda **kwargs: {
            'applied': True,
            'written_files': [str(output_dir / 'SKILL.md')],
            'output_root': str(output_dir),
            'severity': kwargs['severity'],
        },
        observe_with_openspace_fn=lambda **kwargs: {'applied': False, 'reason': 'skip'},
        run_runtime_hook_fn=runtime_hook_stub,
        observation_policy=OpenSpaceObservationPolicy(enabled=False),
        repair_fn=lambda **kwargs: None,
        runtime_judge_llm_runner=fake_llm_runner,
    )

    assert captured['run_record'].run_id == 'run-hook'
    assert captured['scenario_names'] == ['success_streak']
    assert captured['enable_llm_judge'] is True
    assert captured['model'] == 'gpt-test'
    assert captured['llm_runner'] is fake_llm_runner
    assert response.observation is not None
    assert response.observation['applied'] is False
    assert response.observation['runtime_hook']['applied'] is True
    assert any('Runtime hook: followup_action=patch_current' in note for note in response.diagnostics.notes)


def test_orchestrator_runtime_hook_skips_cleanly_without_run_record(monkeypatch, tmp_path: Path):
    from openclaw_skill_create.services import orchestrator as mod

    output_dir = tmp_path / 'demo-skill'
    output_dir.mkdir()
    monkeypatch.setattr(mod, 'run_extractor', lambda **kwargs: _make_repo_findings())
    monkeypatch.setattr(mod, 'run_planner', lambda **kwargs: _make_skill_plan())
    monkeypatch.setattr(mod, 'run_generator', lambda **kwargs: _make_artifacts())
    monkeypatch.setattr(mod, 'run_validator', lambda **kwargs: _make_diagnostics())

    def fail_runtime_hook(**kwargs):
        raise AssertionError('runtime hook should not be called without runtime_run_record')

    response = run_skill_create(
        SkillCreateRequestV6(
            task='build skill',
            enable_runtime_hook=True,
        ),
        persist_artifacts_fn=lambda **kwargs: {
            'applied': True,
            'written_files': [str(output_dir / 'SKILL.md')],
            'output_root': str(output_dir),
            'severity': kwargs['severity'],
        },
        observe_with_openspace_fn=lambda **kwargs: {'applied': True, 'event': 'created'},
        run_runtime_hook_fn=fail_runtime_hook,
        observation_policy=OpenSpaceObservationPolicy(enabled=False),
        repair_fn=lambda **kwargs: None,
    )

    assert response.observation == {'applied': True, 'event': 'created'}
    assert all('Runtime hook:' not in note for note in response.diagnostics.notes)
