from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_approval import OpsApprovalState
from openclaw_skill_create.models.ops_post_apply import PriorPilotRetrievalTrialReport

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_prior_retrieval_trial.py'


def test_run_runtime_prior_retrieval_trial_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_prior_retrieval_trial')
    monkeypatch.setattr(module, 'load_ops_approval_state', lambda path: OpsApprovalState())
    monkeypatch.setattr(module, '_load_prior_pilot_report', lambda path: object())
    monkeypatch.setattr(
        module,
        'build_prior_pilot_retrieval_trial_report',
        lambda **kwargs: PriorPilotRetrievalTrialReport(
            family='hf-trainer',
            summary='ok',
            markdown_summary='# Prior Pilot Retrieval Trial\n\n- Summary: ok',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_prior_retrieval_trial.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Prior Pilot Retrieval Trial')
