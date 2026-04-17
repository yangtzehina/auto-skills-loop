from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_verify_report.py'


class _Completed:
    def __init__(self, returncode: int, *, stdout: str = '', stderr: str = ''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_verify_report_cli_supports_quick(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_report')
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify.subprocess.run',
        lambda *args, **kwargs: _Completed(0, stdout='ok'),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_verify_report.py', '--mode', 'quick'],
        monkeypatch,
    )

    assert code in {0, 1}
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['overall_status'] in {'pass', 'warn', 'fail'}
    assert payload['editorial_force_status'] in {'pass', 'warn', 'fail'}
    assert payload['editorial_force_non_regression'] == 'pass'
    assert payload['pairwise_promotion_status'] in {'pass', 'hold', 'fail'}
    assert payload['promotion_hold_count'] >= 0
    assert payload['coverage_non_regression_status'] in {'pass', 'fail'}
    assert payload['compactness_non_regression_status'] in {'pass', 'fail'}
    assert payload['frontier_dominance_status'] in {'pass', 'fail'}
    assert payload['active_frontier_status'] in {'pass', 'fail'}
    assert payload['program_fidelity_status'] == 'pass'
    assert payload['candidate_separation_gap_count'] == 0
    assert payload['best_balance_not_beaten_count'] >= 0
    assert payload['best_coverage_not_beaten_count'] >= 0
    assert payload['current_best_not_beaten_count'] >= 0
    assert payload['residual_gap_count'] >= 0
    assert payload['task_outcome_status'] == 'pass'
    assert payload['program_authoring_status'] == 'pass'
    assert payload['breakthrough_status'] in {'pass', 'stable_but_no_breakthrough', 'fail'}


def test_run_verify_report_cli_warns_when_live_curation_fails(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_report_warn')
    calls = {'count': 0}

    def fake_run(*args, **kwargs):
        calls['count'] += 1
        return _Completed(1 if calls['count'] == 3 else 0, stdout='ok')

    monkeypatch.setattr(
        'openclaw_skill_create.services.verify.subprocess.run',
        fake_run,
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_verify_report.py', '--mode', 'full', '--include-live-curation', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 1
    assert stderr == ''
    assert stdout.startswith('# Verify Report')


def test_run_verify_report_markdown_includes_decision_statuses(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_report_markdown')
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify.subprocess.run',
        lambda *args, **kwargs: _Completed(0, stdout='ok'),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_verify_report.py', '--mode', 'quick', '--format', 'markdown'],
        monkeypatch,
    )

    assert code in {0, 1}
    assert stderr == ''
    assert '## Decision Statuses' in stdout
    assert '`pending`' in stdout
    assert '## Operation-Backed Summary' in stdout
    assert '`no_change`' in stdout
    assert '- editorial_force_status=' in stdout
    assert '- editorial_force_non_regression=pass' in stdout
    assert '- pairwise_promotion_status=' in stdout
    assert '- promotion_hold_count=' in stdout
    assert '- coverage_non_regression_status=' in stdout
    assert '- compactness_non_regression_status=' in stdout
    assert '- frontier_dominance_status=' in stdout
    assert '- active_frontier_status=' in stdout
    assert '- program_fidelity_status=pass' in stdout
    assert '- candidate_separation_gap_count=0' in stdout
    assert '- best_balance_not_beaten_count=' in stdout
    assert '- best_coverage_not_beaten_count=' in stdout
    assert '- current_best_not_beaten_count=' in stdout
    assert '- residual_gap_count=' in stdout
    assert '- task_outcome_status=pass' in stdout
    assert '- breakthrough_status=' in stdout
