from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from openclaw_skill_create.services.runtime_replay import build_runtime_replay_gate_result


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'runtime_replay'
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_replay_gate.py'


def _load_script_module():
    spec = importlib.util.spec_from_file_location('skill_create_run_runtime_replay_gate', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _invoke_main(module, argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = module.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def test_runtime_replay_gate_cli_matches_service_output():
    module = _load_script_module()

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_gate.py', '--baseline', str(BASELINE_PATH)],
    )
    expected = build_runtime_replay_gate_result(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_replay_gate_cli_returns_nonzero_for_drift(tmp_path: Path):
    module = _load_script_module()
    baseline_path = tmp_path / 'baseline_report.json'
    payload = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    payload['scenario_baselines'][1]['actual_final_quality_score'] = 0.25
    baseline_path.write_text(json.dumps(payload), encoding='utf-8')

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_gate.py', '--baseline', str(baseline_path)],
    )

    parsed = json.loads(stdout)
    assert code == 1
    assert stderr == ''
    assert parsed['passed'] is False
    assert parsed['scenario_results'][1]['drift_messages']


def test_runtime_replay_gate_cli_can_write_baseline(tmp_path: Path):
    module = _load_script_module()
    baseline_path = tmp_path / 'generated_baseline.json'

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_gate.py', '--baseline', str(baseline_path), '--write-baseline'],
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert baseline_path.exists() is True
    assert payload['summary'] == 'Runtime replay baseline complete: scenarios=3'


def test_runtime_replay_gate_cli_rejects_unknown_option():
    module = _load_script_module()

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_gate.py', '--wat'],
    )

    assert code == 2
    assert stdout == ''
    assert 'Unknown option' in stderr
