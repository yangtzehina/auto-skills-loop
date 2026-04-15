from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from openclaw_skill_create.models.runtime import EvolutionPlan, SkillRunAnalysis
from openclaw_skill_create.services.runtime_followup import build_runtime_followup_result


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_followup.py'


def _load_script_module():
    spec = importlib.util.spec_from_file_location('skill_create_run_runtime_followup', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _invoke_main(module, argv: list[str], monkeypatch, *, stdin_text: str = '') -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(sys, 'stdin', io.StringIO(stdin_text))
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = module.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _sample_analysis() -> SkillRunAnalysis:
    return SkillRunAnalysis(
        run_id='run-cli-followup',
        task_id='task-cli-followup',
        evolution_plans=[
            EvolutionPlan(run_id='run-cli-followup', skill_id='skill-noop', action='no_change', summary='No-op first.'),
            EvolutionPlan(
                run_id='run-cli-followup',
                skill_id='skill-patch',
                action='patch_current',
                summary='Patch the current skill.',
                repair_suggestions=[
                    {
                        'issue_type': 'reference_structure_incomplete',
                        'instruction': 'Repair the reference guidance.',
                        'target_paths': ['references/usage.md'],
                        'priority': 80,
                    }
                ],
            ),
        ],
    )


def test_runtime_followup_cli_reads_analysis_file_and_selects_actionable(monkeypatch, tmp_path: Path):
    module = _load_script_module()
    payload_path = tmp_path / 'analysis.json'
    analysis = _sample_analysis()
    payload_path.write_text(json.dumps(analysis.model_dump(mode='json')), encoding='utf-8')

    code, stdout, stderr = _invoke_main(module, ['run_runtime_followup.py', str(payload_path)], monkeypatch)

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['action'] == 'patch_current'
    assert payload['selected_plan']['skill_id'] == 'skill-patch'
    assert payload['repair_suggestions'][0]['issue_type'] == 'reference_structure_incomplete'


def test_runtime_followup_cli_reads_plan_from_stdin_and_builds_request(monkeypatch):
    module = _load_script_module()
    plan = EvolutionPlan(
        run_id='run-derive',
        skill_id='skill-derive',
        action='derive_child',
        summary='Derive a child skill for repo-specific validation.',
        requirement_gaps=['Missing repo-specific validator step.'],
    )

    code, stdout, stderr = _invoke_main(
        module,
        [
            'run_runtime_followup.py',
            '--task-summary',
            'Create the derived validator skill.',
            '--skill-name-hint',
            'repo-validator',
            '--repo-path',
            '/tmp/repo',
            '-',
        ],
        monkeypatch,
        stdin_text=json.dumps(plan.model_dump(mode='json')),
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['action'] == 'derive_child'
    assert payload['skill_create_request']['skill_name_hint'] == 'repo-validator-derived'
    assert payload['skill_create_request']['repo_paths'] == ['/tmp/repo']
    assert 'Create the derived validator skill.' in payload['skill_create_request']['task']


def test_runtime_followup_cli_rejects_invalid_json(monkeypatch, tmp_path: Path):
    module = _load_script_module()
    payload_path = tmp_path / 'broken.json'
    payload_path.write_text('{bad json', encoding='utf-8')

    code, stdout, stderr = _invoke_main(module, ['run_runtime_followup.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Invalid JSON input' in stderr


def test_runtime_followup_cli_rejects_unknown_payload(monkeypatch, tmp_path: Path):
    module = _load_script_module()
    payload_path = tmp_path / 'unknown.json'
    payload_path.write_text(json.dumps({'hello': 'world'}), encoding='utf-8')

    code, stdout, stderr = _invoke_main(module, ['run_runtime_followup.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Input is neither SkillRunAnalysis nor EvolutionPlan' in stderr


def test_runtime_followup_cli_honors_plan_index(monkeypatch, tmp_path: Path):
    module = _load_script_module()
    payload_path = tmp_path / 'analysis.json'
    analysis = SkillRunAnalysis(
        run_id='run-idx',
        task_id='task-idx',
        evolution_plans=[
            EvolutionPlan(run_id='run-idx', skill_id='skill-a', action='patch_current', summary='Patch A.'),
            EvolutionPlan(run_id='run-idx', skill_id='skill-b', action='no_change', summary='No change B.'),
        ],
    )
    payload_path.write_text(json.dumps(analysis.model_dump(mode='json')), encoding='utf-8')

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_followup.py', '--plan-index', '1', str(payload_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['action'] == 'no_change'
    assert payload['noop'] is True
    assert payload['selected_plan']['skill_id'] == 'skill-b'


def test_runtime_followup_cli_matches_service_output(monkeypatch, tmp_path: Path):
    module = _load_script_module()
    payload_path = tmp_path / 'analysis.json'
    analysis = _sample_analysis()
    payload_path.write_text(json.dumps(analysis.model_dump(mode='json')), encoding='utf-8')

    code, stdout, stderr = _invoke_main(module, ['run_runtime_followup.py', str(payload_path)], monkeypatch)
    expected = build_runtime_followup_result(analysis)

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')
