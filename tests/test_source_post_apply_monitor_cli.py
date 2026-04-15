from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_approval import OpsApprovalState
from openclaw_skill_create.models.ops_post_apply import SourcePromotionPostApplyReport

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_source_post_apply_monitor.py'


def test_run_source_post_apply_monitor_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_source_post_apply_monitor')
    monkeypatch.setattr(module, 'load_ops_approval_state', lambda path: OpsApprovalState())
    monkeypatch.setattr(module, 'load_public_source_curation_round_report', lambda path: object())
    monkeypatch.setattr(
        module,
        'build_source_promotion_post_apply_report',
        lambda **kwargs: SourcePromotionPostApplyReport(
            repo_full_name='alirezarezvani/claude-skills',
            summary='ok',
            markdown_summary='# Source Promotion Post-Apply Monitor\n\n- Summary: ok',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_source_post_apply_monitor.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Source Promotion Post-Apply Monitor')
