from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_handoff_normalize.py'


def test_runtime_handoff_cli_reads_file_input(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_handoff_normalize')
    payload = tmp_path / 'handoff.json'
    payload.write_text(
        json.dumps(
            {
                'task_id': 'task-handoff-cli',
                'skills': [{'skill_id': 'demo-skill__v0_abcd1234', 'skill_name': 'demo-skill'}],
            }
        ),
        encoding='utf-8',
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_handoff_normalize.py', str(payload)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['skill_run_record']['task_id'] == 'task-handoff-cli'


def test_runtime_handoff_cli_reads_stdin(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_handoff_normalize')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_handoff_normalize.py', '-'],
        monkeypatch,
        stdin_text=json.dumps({'task_id': 'task-handoff-stdin', 'skills_used': []}),
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['runtime_options']['enable_llm_judge'] is False


def test_runtime_handoff_cli_rejects_invalid_runtime_options(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_handoff_normalize')
    payload = tmp_path / 'handoff.json'
    payload.write_text(
        json.dumps(
            {
                'task_id': 'task-handoff-bad',
                'runtime_options': {'judge_model': 'gpt-test'},
            }
        ),
        encoding='utf-8',
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_handoff_normalize.py', str(payload)],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'judge_model requires enable_llm_judge=true' in stderr
