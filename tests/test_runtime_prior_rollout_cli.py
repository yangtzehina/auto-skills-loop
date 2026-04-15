from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import SIMULATION_FIXTURE_ROOT, invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_prior_rollout.py'
PILOT_SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_prior_pilot.py'


def test_runtime_prior_rollout_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_prior_rollout')

    code, stdout, stderr = invoke_main(
        module,
        [
            'run_runtime_prior_rollout.py',
            '--format',
            'markdown',
            str(SIMULATION_FIXTURE_ROOT / 'prior_gate' / 'eligible_domain_safe' / 'input' / 'spec.json'),
        ],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Prior Rollout Report')
    assert 'hf-trainer' in stdout


def test_runtime_prior_rollout_cli_rejects_bad_format(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_prior_rollout_bad')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_prior_rollout.py', '--format', 'yaml', '-'],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported format: yaml' in stderr


def test_runtime_prior_pilot_cli_supports_markdown(monkeypatch):
    module = load_script_module(PILOT_SCRIPT_PATH, 'skill_create_run_runtime_prior_pilot')

    code, stdout, stderr = invoke_main(
        module,
        [
            'run_runtime_prior_pilot.py',
            '--format',
            'markdown',
            str(SIMULATION_FIXTURE_ROOT / 'prior_gate' / 'eligible_domain_safe' / 'input' / 'spec.json'),
        ],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Prior Pilot Report')
    assert 'hf-trainer' in stdout
