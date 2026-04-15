from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_governance import build_runtime_governance_batch_report

from .runtime_test_helpers import invoke_main, load_script_module, sample_run_record, write_run_record


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_governance_batch.py'


def test_runtime_governance_batch_cli_matches_service_output(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_batch')
    record = sample_run_record(run_id='run-batch-cli', task_id='task-batch-cli')
    write_run_record(tmp_path, record)
    policy = OpenSpaceObservationPolicy(enabled=False)
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: policy)

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_batch.py', str(tmp_path)],
        monkeypatch,
    )
    expected = build_runtime_governance_batch_report(source_path=tmp_path, policy=policy)

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_governance_batch_cli_supports_markdown(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_batch')
    record = sample_run_record(run_id='run-batch-md', task_id='task-batch-md')
    write_run_record(tmp_path, record)
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_batch.py', '--format', 'markdown', str(tmp_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Governance Batch Report')


def test_runtime_governance_batch_cli_rejects_bad_format(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_batch')
    record = sample_run_record(run_id='run-batch-badfmt', task_id='task-batch-badfmt')
    write_run_record(tmp_path, record)

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_batch.py', '--format', 'html', str(tmp_path)],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported format' in stderr
