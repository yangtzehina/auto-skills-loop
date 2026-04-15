from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_approval import OpsApprovalState, PriorPilotManualTrialPack

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_prior_manual_trial.py'


def test_run_runtime_prior_manual_trial_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_prior_manual_trial')
    monkeypatch.setattr(module, 'load_ops_approval_state', lambda path: OpsApprovalState())
    monkeypatch.setattr(module, '_load_prior_pilot_report', lambda path: object())
    monkeypatch.setattr(module, 'build_runtime_prior_pilot_exercise_report', lambda **kwargs: type(
        'ExerciseReport',
        (),
        {'generic_promotion_risk': 0, 'top_1_changes': 0, 'verdict': 'ready_for_manual_pilot'},
    )())
    monkeypatch.setattr(
        module,
        'build_prior_pilot_manual_trial_pack',
        lambda **kwargs: PriorPilotManualTrialPack(
            family='hf-trainer',
            summary='ok',
            markdown_summary='# Runtime Prior Manual Trial Pack\n\n- Summary: ok',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_prior_manual_trial.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Prior Manual Trial Pack')
