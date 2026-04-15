from __future__ import annotations

from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_ops_decision_pack.py'


def test_run_runtime_ops_decision_pack_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_ops_decision_pack')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_ops_decision_pack.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Ops Decision Pack')
    assert 'hf-trainer' in stdout
    assert 'alirezarezvani/claude-skills' in stdout
