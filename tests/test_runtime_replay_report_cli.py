from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from openclaw_skill_create.services.runtime_replay import build_runtime_replay_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'runtime_replay'
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_replay_report.py'


def _load_script_module():
    spec = importlib.util.spec_from_file_location('skill_create_run_runtime_replay_report', SCRIPT_PATH)
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


def test_runtime_replay_report_cli_matches_service_output():
    module = _load_script_module()

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_report.py', '--scenario', 'stable_gap_streak'],
    )
    expected = build_runtime_replay_report(
        fixtures_root=FIXTURE_ROOT,
        scenario_names=['stable_gap_streak'],
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_replay_report_cli_returns_nonzero_for_mismatch(tmp_path: Path):
    module = _load_script_module()
    scenario_root = tmp_path / 'runtime_replay' / 'success_streak'
    run_root = scenario_root / 'runs'
    run_root.mkdir(parents=True)

    source_root = FIXTURE_ROOT / 'success_streak'
    manifest = json.loads((source_root / 'manifest.json').read_text(encoding='utf-8'))
    manifest['expected_final_followup_action'] = 'derive_child'
    (scenario_root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    for run_file in (source_root / 'runs').glob('*.json'):
        (run_root / run_file.name).write_text(run_file.read_text(encoding='utf-8'), encoding='utf-8')

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_report.py', '--fixtures-root', str(tmp_path / 'runtime_replay')],
    )

    payload = json.loads(stdout)
    assert code == 1
    assert stderr == ''
    assert payload['passed'] is False
    assert payload['scenario_reports'][0]['mismatches']


def test_runtime_replay_report_cli_rejects_unknown_scenario():
    module = _load_script_module()

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_report.py', '--scenario', 'does-not-exist'],
    )

    assert code == 2
    assert stdout == ''
    assert 'Unknown runtime replay scenario' in stderr
