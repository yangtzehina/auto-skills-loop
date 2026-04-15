from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from openclaw_skill_create.services.runtime_replay_review import build_runtime_replay_review


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'runtime_replay'
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_replay_review.py'


def _load_script_module():
    spec = importlib.util.spec_from_file_location('skill_create_run_runtime_replay_review', SCRIPT_PATH)
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


def test_runtime_replay_review_cli_matches_service_output():
    module = _load_script_module()

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_review.py', '--baseline', str(BASELINE_PATH)],
    )
    expected = build_runtime_replay_review(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_replay_review_cli_supports_markdown_output():
    module = _load_script_module()

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_review.py', '--baseline', str(BASELINE_PATH), '--format', 'markdown'],
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Replay Review')
    assert '`success_streak` [passed]' in stdout


def test_runtime_replay_review_cli_rejects_bad_format():
    module = _load_script_module()

    code, stdout, stderr = _invoke_main(
        module,
        ['run_runtime_replay_review.py', '--format', 'html'],
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported format' in stderr
