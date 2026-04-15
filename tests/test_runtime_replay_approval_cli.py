from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_replay_approval import build_runtime_replay_approval_pack

from .runtime_test_helpers import FIXTURE_ROOT, invoke_main, load_script_module
ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_replay_approval_pack.py'


def test_runtime_replay_approval_pack_cli_matches_service_output():
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_replay_approval_pack')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_replay_approval_pack.py', '--baseline', str(BASELINE_PATH)],
        monkeypatch=None,
    )
    expected = build_runtime_replay_approval_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_replay_approval_pack_cli_supports_markdown_output():
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_replay_approval_pack')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_replay_approval_pack.py', '--baseline', str(BASELINE_PATH), '--format', 'markdown'],
        monkeypatch=None,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Replay Approval Pack')
    assert 'Approval decision: `reject_refresh`' in stdout


def test_runtime_replay_approval_pack_cli_returns_nonzero_for_investigate(tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_replay_approval_pack')
    scenario_root = tmp_path / 'runtime_replay' / 'success_streak'
    run_root = scenario_root / 'runs'
    run_root.mkdir(parents=True)
    source_root = FIXTURE_ROOT / 'success_streak'
    manifest = json.loads((source_root / 'manifest.json').read_text(encoding='utf-8'))
    manifest['expected_actions'] = ['patch_current', 'patch_current', 'patch_current']
    (scenario_root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    for run_file in (source_root / 'runs').glob('*.json'):
        (run_root / run_file.name).write_text(run_file.read_text(encoding='utf-8'), encoding='utf-8')

    code, stdout, stderr = invoke_main(
        module,
        [
            'run_runtime_replay_approval_pack.py',
            '--fixtures-root',
            str(tmp_path / 'runtime_replay'),
            '--baseline',
            str(BASELINE_PATH),
        ],
        monkeypatch=None,
    )

    parsed = json.loads(stdout)
    assert code == 1
    assert stderr == ''
    assert parsed['approval_decision'] == 'investigate_first'
    assert parsed['allow_baseline_refresh'] is False


def test_runtime_replay_approval_pack_cli_rejects_bad_format():
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_replay_approval_pack')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_replay_approval_pack.py', '--format', 'html'],
        monkeypatch=None,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported format' in stderr
