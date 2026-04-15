from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import SIMULATION_FIXTURE_ROOT, copy_tree, invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_simulation_suite.py'


def test_run_simulation_suite_cli_supports_quick_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_simulation_suite_quick')

    code, stdout, stderr = invoke_main(
        module,
        ['run_simulation_suite.py', '--mode', 'quick', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Simulation Suite Report')
    assert 'partial_trace_no_change' in stdout


def test_run_simulation_suite_cli_supports_full_json(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_simulation_suite_full')

    code, stdout, stderr = invoke_main(
        module,
        ['run_simulation_suite.py', '--mode', 'full'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['mode'] == 'full'
    assert payload['matched_count'] == 28


def test_run_simulation_suite_cli_rejects_bad_mode(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_simulation_suite_bad_mode')

    code, stdout, stderr = invoke_main(
        module,
        ['run_simulation_suite.py', '--mode', 'nope'],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported mode' in stderr


def test_run_simulation_suite_cli_returns_nonzero_for_drift(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_simulation_suite_drift')
    fixture_root = copy_tree(tmp_path, SIMULATION_FIXTURE_ROOT)
    expected_path = (
        fixture_root
        / 'runtime_intake'
        / 'partial_trace_no_change'
        / 'expected'
        / 'result.json'
    )
    payload = json.loads(expected_path.read_text(encoding='utf-8'))
    payload['runtime_followup_action'] = 'patch_current'
    expected_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    code, stdout, stderr = invoke_main(
        module,
        [
            'run_simulation_suite.py',
            '--mode',
            'runtime-intake',
            '--scenario',
            'partial_trace_no_change',
            '--fixture-root',
            str(fixture_root),
        ],
        monkeypatch,
    )

    assert code == 1
    assert stderr == ''
    assert json.loads(stdout)['drifted_count'] == 1


def test_run_simulation_suite_cli_returns_nonzero_for_invalid_fixture(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_simulation_suite_invalid')
    fixture_root = copy_tree(tmp_path, SIMULATION_FIXTURE_ROOT)
    expected_path = (
        fixture_root
        / 'prior_gate'
        / 'eligible_domain_safe'
        / 'expected'
        / 'result.json'
    )
    expected_path.unlink()

    code, stdout, stderr = invoke_main(
        module,
        [
            'run_simulation_suite.py',
            '--mode',
            'prior-gate',
            '--scenario',
            'eligible_domain_safe',
            '--fixture-root',
            str(fixture_root),
        ],
        monkeypatch,
    )

    assert code == 2
    assert stderr == ''
    assert json.loads(stdout)['invalid_fixture_count'] == 1
