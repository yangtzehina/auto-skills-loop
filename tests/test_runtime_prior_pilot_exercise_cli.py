from __future__ import annotations

from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_prior_pilot_exercise.py'


def test_run_runtime_prior_pilot_exercise_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_prior_pilot_exercise')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_prior_pilot_exercise.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Prior Pilot Exercise')
    assert 'ready_for_manual_pilot' in stdout
