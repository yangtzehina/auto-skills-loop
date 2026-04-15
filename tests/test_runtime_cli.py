from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_analysis import analyze_skill_run

from .runtime_test_helpers import invoke_main, load_script_module, sample_run_record

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_analysis.py'


def test_runtime_cli_reads_file_input(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_analysis')
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(sample_run_record().model_dump(mode='json')), encoding='utf-8')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(module, ['run_runtime_analysis.py', str(payload_path)], monkeypatch)

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['run_id'] == 'run-cli-1'
    assert payload['skills_analyzed'][0]['recommended_action'] == 'patch_current'


def test_runtime_cli_reads_stdin_input(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_analysis')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_analysis.py', '-'],
        monkeypatch,
        stdin_text=json.dumps(sample_run_record().model_dump(mode='json')),
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['task_id'] == 'task-cli-1'
    assert payload['skills_analyzed'][0]['skill_id'] == 'demo-skill__v0_abcd1234'


def test_runtime_cli_rejects_invalid_json(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_analysis')
    payload_path = tmp_path / 'broken.json'
    payload_path.write_text('{bad json', encoding='utf-8')

    code, stdout, stderr = invoke_main(module, ['run_runtime_analysis.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Invalid JSON input' in stderr


def test_runtime_cli_rejects_missing_required_fields(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_analysis')
    payload_path = tmp_path / 'missing.json'
    payload_path.write_text('{}', encoding='utf-8')

    code, stdout, stderr = invoke_main(module, ['run_runtime_analysis.py', str(payload_path)], monkeypatch)

    assert code == 2
    assert stdout == ''
    assert 'Invalid SkillRunRecord payload' in stderr


def test_runtime_cli_matches_service_output(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_analysis')
    record = sample_run_record()
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(record.model_dump(mode='json')), encoding='utf-8')
    policy = OpenSpaceObservationPolicy(enabled=False)
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: policy)

    code, stdout, stderr = invoke_main(module, ['run_runtime_analysis.py', str(payload_path)], monkeypatch)
    expected = analyze_skill_run(record, policy)

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_cli_returns_analysis_when_policy_disabled(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_analysis')
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(sample_run_record().model_dump(mode='json')), encoding='utf-8')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(module, ['run_runtime_analysis.py', str(payload_path)], monkeypatch)

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert 'store_persistence=skipped' in payload['summary']


def test_runtime_cli_returns_analysis_when_helper_fails(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_analysis')
    payload_path = tmp_path / 'run_record.json'
    payload_path.write_text(json.dumps(sample_run_record().model_dump(mode='json')), encoding='utf-8')
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

    code, stdout, stderr = invoke_main(module, ['run_runtime_analysis.py', str(payload_path)], monkeypatch)

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert 'store_persistence=failed' in payload['summary']
