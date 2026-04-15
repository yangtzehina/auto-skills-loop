from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.runtime_hook import RuntimeHookResult
from openclaw_skill_create.services.runtime_hook import run_runtime_hook

from .runtime_test_helpers import invoke_main, load_script_module, sample_run_record


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_hook.py'


def test_runtime_hook_cli_reads_file_input(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_hook')
    record = sample_run_record(run_id='run-hook-cli', task_id='task-hook-cli')
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(record.model_dump(mode='json')), encoding='utf-8')
    policy = OpenSpaceObservationPolicy(enabled=False)
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: policy)

    code, stdout, stderr = invoke_main(module, ['run_runtime_hook.py', str(payload_path)], monkeypatch)
    expected = run_runtime_hook(run_record=record, policy=policy)

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_hook_cli_reads_stdin_input(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_hook')
    record = sample_run_record(run_id='run-hook-cli', task_id='task-hook-cli')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_hook.py', '-'],
        monkeypatch,
        stdin_text=json.dumps(record.model_dump(mode='json')),
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['runtime_cycle']['run_id'] == 'run-hook-cli'
    assert payload['approval_pack']['approval_decision'] == 'reject_refresh'


def test_runtime_hook_cli_forwards_options(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_hook')
    record = sample_run_record(run_id='run-hook-cli', task_id='task-hook-cli')
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(record.model_dump(mode='json')), encoding='utf-8')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    captured: dict[str, object] = {}

    def fake_run_runtime_hook(**kwargs):
        captured.update(kwargs)
        return RuntimeHookResult(applied=True, summary='hook ok')

    monkeypatch.setattr(module, 'run_runtime_hook', fake_run_runtime_hook)
    baseline_path = tmp_path / 'baseline_report.json'

    code, stdout, stderr = invoke_main(
        module,
        [
            'run_runtime_hook.py',
            '--baseline',
            str(baseline_path),
            '--scenario',
            'success_streak',
            '--scenario',
            'misleading_streak',
            '--enable-judge',
            '--judge-model',
            'gpt-test',
            str(payload_path),
        ],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['summary'] == 'hook ok'
    assert captured['run_record'].run_id == 'run-hook-cli'
    assert captured['baseline_path'] == baseline_path
    assert captured['scenario_names'] == ['success_streak', 'misleading_streak']
    assert captured['enable_llm_judge'] is True
    assert captured['model'] == 'gpt-test'


def test_runtime_hook_cli_rejects_invalid_json(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_hook')
    payload_path = tmp_path / 'broken.json'
    payload_path.write_text('{bad json', encoding='utf-8')

    code, stdout, stderr = invoke_main(module, ['run_runtime_hook.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Invalid JSON input' in stderr


def test_runtime_hook_cli_rejects_missing_required_fields(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_hook')
    payload_path = tmp_path / 'missing.json'
    payload_path.write_text('{}', encoding='utf-8')

    code, stdout, stderr = invoke_main(module, ['run_runtime_hook.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Invalid SkillRunRecord payload' in stderr


def test_runtime_hook_cli_rejects_unknown_option(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_hook')

    code, stdout, stderr = invoke_main(module, ['run_runtime_hook.py', '--wat'], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Unknown option' in stderr
