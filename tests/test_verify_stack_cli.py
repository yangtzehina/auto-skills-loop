from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_verify_stack.py'


class _Completed:
    def __init__(self, returncode: int, *, stdout: str = '', stderr: str = ''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_verify_stack_cli_supports_quick(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_stack')
    monkeypatch.setattr(
        module.subprocess,
        'run',
        lambda *args, **kwargs: _Completed(0, stdout='ok'),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_verify_stack.py', '--mode', 'quick'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['mode'] == 'quick'
    assert payload['summary'] == 'Verify stack complete: commands=2 failed=0'


def test_run_verify_stack_cli_returns_nonzero_when_one_command_fails(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_stack_fail')
    calls = {'count': 0}

    def fake_run(*args, **kwargs):
        calls['count'] += 1
        return _Completed(1 if calls['count'] == 2 else 0, stdout='ok')

    monkeypatch.setattr(module.subprocess, 'run', fake_run)

    code, stdout, stderr = invoke_main(
        module,
        ['run_verify_stack.py', '--mode', 'full', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 1
    assert stderr == ''
    assert stdout.startswith('# Verify Stack')


def test_run_verify_stack_cli_rejects_bad_mode(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_stack_bad')

    code, stdout, stderr = invoke_main(
        module,
        ['run_verify_stack.py', '--mode', 'nope'],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported mode' in stderr
