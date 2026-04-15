from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_approval import OpsApprovalState
from openclaw_skill_create.models.ops_post_apply import PriorPilotTrialObservationReport

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_prior_trial_report.py'


def test_run_runtime_prior_trial_report_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_prior_trial_report')
    monkeypatch.setattr(module, 'load_ops_approval_state', lambda path: OpsApprovalState())
    monkeypatch.setattr(module, '_load_prior_pilot_report', lambda path: object())
    monkeypatch.setattr(
        module,
        'build_prior_pilot_trial_observation_report',
        lambda **kwargs: PriorPilotTrialObservationReport(
            family='hf-trainer',
            summary='ok',
            markdown_summary='# Runtime Prior Trial Observation\n\n- Summary: ok',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_prior_trial_report.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Prior Trial Observation')
