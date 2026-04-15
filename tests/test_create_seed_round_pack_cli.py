from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_approval import CreateSeedManualRoundPack, OpsApprovalState
from openclaw_skill_create.models.request import SkillCreateRequestV6

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_create_seed_round_pack.py'


def test_run_create_seed_round_pack_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_create_seed_round_pack')
    monkeypatch.setattr(module, 'load_ops_approval_state', lambda path: OpsApprovalState())
    monkeypatch.setattr(module, 'build_runtime_create_seed_proposal_pack', lambda **kwargs: object())
    monkeypatch.setattr(
        module,
        'build_create_seed_manual_round_pack',
        lambda **kwargs: CreateSeedManualRoundPack(
            candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
            preview_request=SkillCreateRequestV6(task='placeholder'),
            summary='ok',
            markdown_summary='# Create Seed Manual Round Pack\n\n- Summary: ok',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_create_seed_round_pack.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Create Seed Manual Round Pack')
