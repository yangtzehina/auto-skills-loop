from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.verify import VerifyCommandResult
from openclaw_skill_create.services.verify import _run_in_process_main, _run_tests_command

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_verify_report.py'


def _command_result(label: str, exit_code: int = 0, *, stdout: str = "", stderr: str = "") -> VerifyCommandResult:
    return VerifyCommandResult(
        label=label,
        command=["python3", f"scripts/{label}.py"],
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_run_verify_report_cli_supports_quick(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_report')
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify._run_tests_command',
        lambda: _command_result('run_tests', 0, stdout='passed=434 failed=0'),
    )
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify._run_simulation_command',
        lambda *, mode: _command_result('run_simulation_suite', 0, stdout=f'mode={mode}\nmatched=28\ndrifted=0\ninvalid_fixture=0'),
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
    assert payload['breakthrough_status'] in {'pass', 'breakthrough', 'stable_but_no_breakthrough', 'fail'}


def test_run_verify_report_cli_warns_when_live_curation_fails(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_verify_report_warn')
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify._run_tests_command',
        lambda: _command_result('run_tests', 0, stdout='passed=434 failed=0'),
    )
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify._run_simulation_command',
        lambda *, mode: _command_result('run_simulation_suite', 0, stdout=f'mode={mode}\nmatched=28\ndrifted=0\ninvalid_fixture=0'),
    )
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify.subprocess.run',
        lambda *args, **kwargs: type('Completed', (), {'returncode': 1, 'stdout': 'live', 'stderr': ''})(),
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
        'openclaw_skill_create.services.verify._run_tests_command',
        lambda: _command_result('run_tests', 0, stdout='passed=434 failed=0'),
    )
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify._run_simulation_command',
        lambda *, mode: _command_result('run_simulation_suite', 0, stdout=f'mode={mode}\nmatched=28\ndrifted=0\ninvalid_fixture=0'),
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


def test_run_in_process_main_supports_zero_arg_main(tmp_path: Path):
    script_path = tmp_path / 'zero_arg_main.py'
    script_path.write_text(
        "def main():\n"
        "    print('passed=434 failed=0')\n"
        "    return 0\n",
        encoding='utf-8',
    )

    result = _run_in_process_main(
        label='run_tests',
        cmd=['python3', 'scripts/run_tests.py'],
        script_path=script_path,
        argv=['run_tests.py'],
    )

    assert result.exit_code == 0
    assert result.stdout == 'passed=434 failed=0'
    assert result.stderr == ''


def test_run_tests_command_recovers_from_timeout_summary(monkeypatch):
    monkeypatch.setattr(
        'openclaw_skill_create.services.verify._prefer_in_process_verify_commands',
        lambda: False,
    )

    def _timeout(*args, **kwargs):
        raise TimeoutError  # pragma: no cover

    monkeypatch.setattr(
        'openclaw_skill_create.services.verify.subprocess.run',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            __import__('subprocess').TimeoutExpired(
                cmd=['python3', 'scripts/run_tests.py'],
                timeout=90,
                output='ok test_demo demo\npassed=435 failed=0\n',
                stderr='',
            )
        ),
    )

    result = _run_tests_command()

    assert result.exit_code == 0
    assert 'passed=435 failed=0' in result.stdout
    assert 'run_tests_timeout_recovered_from_summary=true' in result.stderr
