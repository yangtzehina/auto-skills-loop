from __future__ import annotations

from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_public_source_promotion_pack.py'


def test_run_public_source_promotion_pack_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_public_source_promotion_pack')

    code, stdout, stderr = invoke_main(
        module,
        ['run_public_source_promotion_pack.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Public Source Promotion Pack')
    assert 'ready_for_manual_promotion' in stdout
