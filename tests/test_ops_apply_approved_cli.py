from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_approval import OpsApprovalApplyReport, OpsApprovalState

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_ops_apply_approved.py'


def test_run_ops_apply_approved_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_ops_apply_approved')
    monkeypatch.setattr(module, 'load_ops_approval_state', lambda path: OpsApprovalState())
    monkeypatch.setattr(module, 'build_runtime_create_seed_proposal_pack', lambda **kwargs: object())
    monkeypatch.setattr(module, '_load_prior_pilot_report', lambda path: object())
    monkeypatch.setattr(module, 'load_public_source_curation_round_report', lambda path: type('Round', (), {'promoted_repos': []})())
    monkeypatch.setattr(module, 'apply_ops_approval_state', lambda **kwargs: OpsApprovalApplyReport(
        approval_state=OpsApprovalState(),
        summary='ok',
        markdown_summary='# Ops Approval Apply Report\n\n- Summary: ok',
    ))

    code, stdout, stderr = invoke_main(
        module,
        ['run_ops_apply_approved.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Ops Approval Apply Report')
