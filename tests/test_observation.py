from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.diagnostics import Diagnostics, ValidationResult
from openclaw_skill_create.models.evaluation import EvaluationRunReport
from openclaw_skill_create.models.findings import RepoFindings
from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.observation import (
    default_observation_policy,
    observe_with_openspace,
)
from openclaw_skill_create.services.openspace_observer_helper import (
    build_change_summary,
    map_skill_type_to_category,
)
from openclaw_skill_create.services.orchestrator import run_skill_create


def test_default_observation_policy_auto_enables_when_python_exists():
    policy = default_observation_policy(auto_enable=True)
    assert isinstance(policy, OpenSpaceObservationPolicy)
    assert policy.enabled in {True, False}


def test_observe_with_openspace_skips_when_disabled(tmp_path: Path):
    result = observe_with_openspace(
        request=SkillCreateRequestV6(task='build skill'),
        request_id='req-1',
        severity='pass',
        skill_plan=None,
        artifacts=None,
        diagnostics=None,
        evaluation_report=None,
        persistence={
            'applied': True,
            'written_files': [str(tmp_path / 'demo' / 'SKILL.md')],
            'output_root': str(tmp_path / 'demo'),
        },
        timings=None,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert result['applied'] is False
    assert result['reason'] == 'OpenSpace observation disabled'


def test_observe_with_openspace_invokes_helper(monkeypatch, tmp_path: Path):
    skill_dir = tmp_path / 'demo-skill'
    skill_dir.mkdir()

    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        captured['args'] = args
        captured['kwargs'] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout='{"applied": true, "event": "created", "skill_id": "demo-skill__v0_deadbeef"}\n',
            stderr='',
        )

    monkeypatch.setattr('openclaw_skill_create.services.observation.subprocess.run', fake_run)

    result = observe_with_openspace(
        request=SkillCreateRequestV6(task='build skill', repo_paths=['/tmp/repo']),
        request_id='req-2',
        severity='pass',
        skill_plan=SkillPlan(skill_name='demo-skill', files_to_create=[PlannedFile(path='SKILL.md', purpose='entry')]),
        artifacts=Artifacts(files=[ArtifactFile(path='SKILL.md', content='demo')]),
        diagnostics=Diagnostics(validation=ValidationResult(summary=['looks good'])),
        evaluation_report=EvaluationRunReport(skill_name='demo-skill', overall_score=0.93, summary=['strong']),
        persistence={
            'applied': True,
            'written_files': [str(skill_dir / 'SKILL.md')],
            'output_root': str(skill_dir),
            'evaluation_report_path': str(skill_dir / 'evals' / 'report.json'),
        },
        timings=None,
        policy=OpenSpaceObservationPolicy(enabled=True, openspace_python=sys.executable, db_path=str(tmp_path / 'openspace.db')),
    )

    assert result['applied'] is True
    assert captured['args'] == [sys.executable, '-m', 'openclaw_skill_create.services.openspace_observer_helper']
    env = captured['kwargs']['env']
    assert 'PYTHONPATH' in env
    assert str(Path(__file__).resolve().parents[1] / 'src') in env['PYTHONPATH']
    assert '"request_id": "req-2"' in captured['kwargs']['input']
    assert '"overall_score": 0.93' in captured['kwargs']['input']
    assert '"evaluation_report_path":' in captured['kwargs']['input']


def test_observation_helper_summary_helpers():
    payload = {
        'severity': 'warn',
        'timings': {'repair_applied': True},
        'evaluation_report': {
            'overall_score': 0.88,
            'benchmark_results': [{'name': 'task_alignment', 'score': 0.73}],
        },
        'diagnostics': {
            'validation': {
                'repairable_issue_types': ['invalid_frontmatter'],
                'non_repairable_issue_types': ['custom-warning'],
            },
            'security_audit': {
                'rating': 'HIGH',
                'trust_tier': 5,
                'top_security_categories': ['runtime_download_install'],
            },
        },
    }
    assert map_skill_type_to_category('library-api-reference') == 'reference'
    summary = build_change_summary(payload, existing=False)
    assert 'severity=warn' in summary
    assert 'deterministic repair' in summary
    assert 'eval=0.88' in summary
    assert 'task_alignment=0.73' in summary
    assert 'invalid_frontmatter' in summary
    assert 'security=HIGH' in summary


def test_orchestrator_emits_observation_result(monkeypatch, tmp_path: Path):
    from openclaw_skill_create.services import orchestrator as mod

    output_dir = tmp_path / 'demo-skill'
    output_dir.mkdir()

    monkeypatch.setattr(mod, 'run_extractor', lambda **kwargs: RepoFindings(repos=[], cross_repo_signals=[], overall_recommendation='ok'))
    monkeypatch.setattr(
        mod,
        'run_planner',
        lambda **kwargs: SkillPlan(
            skill_name='demo-skill',
            files_to_create=[PlannedFile(path='SKILL.md', purpose='entry')],
        ),
    )
    monkeypatch.setattr(
        mod,
        'run_generator',
        lambda **kwargs: Artifacts(files=[ArtifactFile(path='SKILL.md', content='---\nname: demo-skill\ndescription: demo\n---\n')]),
    )
    monkeypatch.setattr(
        mod,
        'run_validator',
        lambda **kwargs: Diagnostics(validation=ValidationResult(summary=['ok'])),
    )

    observed: dict[str, object] = {}

    def observe_stub(**kwargs):
        observed.update(kwargs)
        return {'applied': True, 'event': 'created', 'skill_id': 'demo-skill__v0_test'}

    response = run_skill_create(
        SkillCreateRequestV6(task='build skill'),
        persist_artifacts_fn=lambda **kwargs: {
            'applied': True,
            'written_files': [str(output_dir / 'SKILL.md')],
            'output_root': str(output_dir),
            'severity': kwargs['severity'],
        },
        observe_with_openspace_fn=observe_stub,
        observation_policy=OpenSpaceObservationPolicy(enabled=True, openspace_python=sys.executable),
        repair_fn=lambda **kwargs: None,
    )

    assert response.observation == {'applied': True, 'event': 'created', 'skill_id': 'demo-skill__v0_test'}
    assert observed['request_id'] == response.request_id
    assert observed['policy'].enabled is True
