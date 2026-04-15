from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_cycle import run_runtime_cycle

from .runtime_test_helpers import invoke_main, load_script_module, sample_run_record


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_cycle.py'


def test_runtime_cycle_cli_reads_file_input(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_cycle')
    payload_path = tmp_path / 'run_record.json'
    record = sample_run_record(
        run_id='run-cycle-cli',
        task_id='task-cycle-cli',
        task_summary='Exercise runtime cycle CLI.',
        execution_result='failed',
        steps_triggered=['run scripts/build.py'],
        user_corrections=[],
    )
    payload_path.write_text(json.dumps(record.model_dump(mode='json')), encoding='utf-8')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(module, ['run_runtime_cycle.py', str(payload_path)], monkeypatch)

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['analysis']['run_id'] == 'run-cycle-cli'
    assert payload['followup']['action'] == 'patch_current'
    assert payload['followup']['repair_suggestions'][0]['issue_type'] == 'script_placeholder_heavy'


def test_runtime_cycle_cli_reads_stdin_input(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_cycle')
    record = sample_run_record(
        run_id='run-cycle-cli',
        task_id='task-cycle-cli',
        task_summary='Exercise runtime cycle CLI.',
        execution_result='failed',
        steps_triggered=['run scripts/build.py'],
        user_corrections=[],
    )
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_cycle.py', '-'],
        monkeypatch,
        stdin_text=json.dumps(record.model_dump(mode='json')),
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['task_id'] == 'task-cycle-cli'
    assert payload['followup']['action'] == 'patch_current'


def test_runtime_cycle_cli_matches_service_output(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_cycle')
    record = sample_run_record(
        run_id='run-cycle-cli',
        task_id='task-cycle-cli',
        task_summary='Exercise runtime cycle CLI.',
        execution_result='failed',
        steps_triggered=['run scripts/build.py'],
        user_corrections=[],
    )
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(record.model_dump(mode='json')), encoding='utf-8')
    policy = OpenSpaceObservationPolicy(enabled=False)
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: policy)

    code, stdout, stderr = invoke_main(module, ['run_runtime_cycle.py', str(payload_path)], monkeypatch)
    expected = run_runtime_cycle(record, policy)

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_cycle_cli_rejects_invalid_json(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_cycle')
    payload_path = tmp_path / 'broken.json'
    payload_path.write_text('{bad json', encoding='utf-8')

    code, stdout, stderr = invoke_main(module, ['run_runtime_cycle.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Invalid JSON input' in stderr


def test_runtime_cycle_cli_rejects_missing_required_fields(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_cycle')
    payload_path = tmp_path / 'missing.json'
    payload_path.write_text('{}', encoding='utf-8')

    code, stdout, stderr = invoke_main(module, ['run_runtime_cycle.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Invalid SkillRunRecord payload' in stderr


def test_runtime_cycle_cli_keeps_cycle_output_when_helper_fails(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_cycle')
    record = sample_run_record(
        run_id='run-cycle-cli',
        task_id='task-cycle-cli',
        task_summary='Exercise runtime cycle CLI.',
        execution_result='failed',
        steps_triggered=['run scripts/build.py'],
        user_corrections=[],
    )
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(record.model_dump(mode='json')), encoding='utf-8')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(
            enabled=True,
            openspace_python=sys.executable,
            db_path=str(tmp_path / 'openspace.db'),
        ),
    )

    def fake_run(args, **kwargs):
        return SimpleNamespace(returncode=1, stdout='', stderr='boom')

    monkeypatch.setattr('openclaw_skill_create.services.runtime_analysis.subprocess.run', fake_run)

    code, stdout, stderr = invoke_main(module, ['run_runtime_cycle.py', str(payload_path)], monkeypatch)

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['followup']['action'] == 'patch_current'
    assert 'store_persistence=failed' in payload['analysis']['summary']
