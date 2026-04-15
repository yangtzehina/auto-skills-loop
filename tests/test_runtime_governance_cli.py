from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_governance import build_runtime_governance_bundle

from .runtime_test_helpers import invoke_main, load_script_module, sample_run_record, write_run_record


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_governance_bundle.py'


def test_runtime_governance_bundle_cli_matches_service_output(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_bundle')
    record = sample_run_record(run_id='run-bundle-cli', task_id='task-bundle-cli')
    payload_path = write_run_record(tmp_path, record)
    policy = OpenSpaceObservationPolicy(enabled=False)
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: policy)

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_bundle.py', str(payload_path)],
        monkeypatch,
    )
    expected = build_runtime_governance_bundle(run_record=record, policy=policy)

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_governance_bundle_cli_reads_stdin(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_bundle')
    record = sample_run_record(run_id='run-bundle-stdin', task_id='task-bundle-stdin')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_bundle.py', '-'],
        monkeypatch,
        stdin_text=json.dumps(record.model_dump(mode='json')),
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['run_record']['run_id'] == 'run-bundle-stdin'


def test_runtime_governance_bundle_cli_rejects_invalid_input(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_bundle')
    bad_payload = tmp_path / 'broken.json'
    bad_payload.write_text('{bad json', encoding='utf-8')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_bundle.py', str(bad_payload)],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Invalid JSON input' in stderr
