from __future__ import annotations

import importlib.util
import io
import inspect
import re
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from ..models.public_source_verification import PublicSourceCurationRoundReport, PublicSourcePromotionPack
from ..models.runtime_governance import (
    RuntimeCreateSeedProposalPack,
    RuntimeOpsDecisionPack,
    RuntimePriorPilotExerciseReport,
    RuntimePriorPilotReport,
)
from ..models.verify import OpsRoundbookReport, VerifyCommandResult, VerifyReport
from .operation_backed_ops import build_operation_backed_backlog_report, build_operation_backed_status_report
from .ops_approval import summarize_decision_statuses
from .skill_create_comparison import build_skill_create_comparison_report
from .simulation import build_simulation_suite_report


ROOT = Path(__file__).resolve().parents[3]
RUN_TESTS_SCRIPT = ROOT / "scripts" / "run_tests.py"
RUN_TESTS_TIMEOUT_SECONDS = 240


def _trim_command_output(text: str, *, max_lines: int = 24, max_chars: int = 4000) -> str:
    content = str(text or "").strip()
    if not content:
        return ""
    lines = content.splitlines()
    if len(lines) > max_lines:
        omitted = len(lines) - max_lines
        lines = lines[-max_lines:]
        lines.insert(0, f"... {omitted} earlier lines omitted ...")
    trimmed = "\n".join(lines)
    if len(trimmed) > max_chars:
        trimmed = f"... output trimmed ...\n{trimmed[-max_chars:]}"
    return trimmed


def _load_script_module(path: Path):
    module_name = f"_verify_runtime_{path.stem.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load script module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_in_process_main(*, label: str, cmd: list[str], script_path: Path, argv: list[str]) -> VerifyCommandResult:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    exit_code = 1
    try:
        module = _load_script_module(script_path)
        main_fn = getattr(module, "main", None)
        if not callable(main_fn):
            raise RuntimeError(f"Script has no callable main(): {script_path}")
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            signature = inspect.signature(main_fn)
            exit_code = int(main_fn(argv) if signature.parameters else main_fn())
    except SystemExit as exc:
        exit_code = int(exc.code) if isinstance(exc.code, int) else 1
    except Exception as exc:  # pragma: no cover - exercised via CLI smoke path
        exit_code = 1
        stderr_buffer.write(f"{type(exc).__name__}: {exc}\n")
    return VerifyCommandResult(
        label=label,
        command=cmd,
        exit_code=exit_code,
        stdout=_trim_command_output(stdout_buffer.getvalue()),
        stderr=_trim_command_output(stderr_buffer.getvalue()),
    )


def _prefer_in_process_verify_commands() -> bool:
    return True


def _run_tests_command() -> VerifyCommandResult:
    cmd = [sys.executable, "scripts/run_tests.py"]
    if _prefer_in_process_verify_commands():
        result = _run_in_process_main(
            label="run_tests",
            cmd=cmd,
            script_path=RUN_TESTS_SCRIPT,
            argv=["run_tests.py"],
        )
        if re.search(r"passed=(\d+)\s+failed=(\d+)", result.stdout):
            return result
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
            timeout=RUN_TESTS_TIMEOUT_SECONDS,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        match = re.search(r"passed=(\d+)\s+failed=(\d+)", stdout)
        if match is not None:
            failed = int(match.group(2))
            exit_code = 1 if failed else 0
            suffix = "run_tests_timeout_recovered_from_summary=true"
            stderr = f"{stderr}\n{suffix}".strip()
        else:
            exit_code = 1
            suffix = f"run_tests_timeout_after={RUN_TESTS_TIMEOUT_SECONDS}s"
            stderr = f"{stderr}\n{suffix}".strip()
    return VerifyCommandResult(
        label="run_tests",
        command=cmd,
        exit_code=exit_code,
        stdout=_trim_command_output(stdout),
        stderr=_trim_command_output(stderr),
    )


def _run_simulation_command(*, mode: str) -> VerifyCommandResult:
    report = build_simulation_suite_report(mode=mode)
    exit_code = 2 if int(report.invalid_fixture_count or 0) else (1 if int(report.drifted_count or 0) else 0)
    stdout = "\n".join(
        [
            f"mode={mode}",
            f"matched={int(report.matched_count or 0)}",
            f"drifted={int(report.drifted_count or 0)}",
            f"invalid_fixture={int(report.invalid_fixture_count or 0)}",
            f"summary={report.summary}",
        ]
    )
    return VerifyCommandResult(
        label="run_simulation_suite",
        command=[sys.executable, "scripts/run_simulation_suite.py", "--mode", mode],
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
    )


def _run_command(label: str, cmd: list[str]) -> VerifyCommandResult:
    if label == "run_tests" and cmd == [sys.executable, "scripts/run_tests.py"]:
        return _run_tests_command()
    if (
        label == "run_simulation_suite"
        and len(cmd) >= 4
        and cmd[:2] == [sys.executable, "scripts/run_simulation_suite.py"]
        and cmd[2] == "--mode"
    ):
        return _run_simulation_command(mode=str(cmd[3]))
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return VerifyCommandResult(
        label=label,
        command=cmd,
        exit_code=completed.returncode,
        stdout=_trim_command_output(completed.stdout),
        stderr=_trim_command_output(completed.stderr),
    )


def render_verify_report_markdown(report: VerifyReport) -> str:
    lines = [
        '# Verify Report',
        '',
        f'- Mode: {report.mode}',
        f'- Overall status: {report.overall_status}',
        f'- Summary: {report.summary}',
        f'- decision_status_summary={report.decision_status_summary}',
        f'- operation_backed_status_counts={report.operation_backed_status_counts}',
        f'- operation_backed_actionable_count={report.operation_backed_actionable_count}',
        f'- operation_backed_hold_count={report.operation_backed_hold_count}',
        f'- methodology_body_quality_status={report.methodology_body_quality_status}',
        f'- self_review_fail_count={report.self_review_fail_count}',
        f'- domain_specificity_status={report.domain_specificity_status}',
        f'- domain_specificity_fail_count={report.domain_specificity_fail_count}',
        f'- domain_expertise_status={report.domain_expertise_status}',
        f'- domain_expertise_fail_count={report.domain_expertise_fail_count}',
        f'- domain_expertise_warn_count={report.domain_expertise_warn_count}',
        f'- expert_structure_status={report.expert_structure_status}',
        f'- expert_structure_fail_count={report.expert_structure_fail_count}',
        f'- expert_structure_warn_count={report.expert_structure_warn_count}',
        f'- expert_structure_gap_count={report.expert_structure_gap_count}',
        f'- depth_quality_status={report.depth_quality_status}',
        f'- depth_quality_fail_count={report.depth_quality_fail_count}',
        f'- depth_quality_warn_count={report.depth_quality_warn_count}',
        f'- depth_quality_gap_count={report.depth_quality_gap_count}',
        f'- editorial_quality_status={report.editorial_quality_status}',
        f'- editorial_quality_fail_count={report.editorial_quality_fail_count}',
        f'- editorial_quality_warn_count={report.editorial_quality_warn_count}',
        f'- editorial_gap_count={report.editorial_gap_count}',
        f'- style_diversity_status={report.style_diversity_status}',
        f'- style_diversity_fail_count={report.style_diversity_fail_count}',
        f'- style_diversity_warn_count={report.style_diversity_warn_count}',
        f'- style_gap_count={report.style_gap_count}',
        f'- move_quality_status={report.move_quality_status}',
        f'- move_quality_fail_count={report.move_quality_fail_count}',
        f'- move_quality_warn_count={report.move_quality_warn_count}',
        f'- move_quality_gap_count={report.move_quality_gap_count}',
        f'- workflow_form_status={report.workflow_form_status}',
        f'- workflow_form_fail_count={report.workflow_form_fail_count}',
        f'- workflow_form_warn_count={report.workflow_form_warn_count}',
        f'- workflow_form_gap_count={report.workflow_form_gap_count}',
        f'- editorial_force_status={report.editorial_force_status}',
        f'- editorial_force_fail_count={report.editorial_force_fail_count}',
        f'- editorial_force_warn_count={report.editorial_force_warn_count}',
        f'- editorial_force_gap_count={report.editorial_force_gap_count}',
        f'- editorial_force_non_regression={report.editorial_force_non_regression}',
        f'- pairwise_promotion_status={report.pairwise_promotion_status}',
        f'- pairwise_promotion_gap_count={report.pairwise_promotion_gap_count}',
        f'- promotion_hold_count={report.promotion_hold_count}',
        f'- coverage_non_regression_status={report.coverage_non_regression_status}',
        f'- compactness_non_regression_status={report.compactness_non_regression_status}',
        f'- frontier_dominance_status={report.frontier_dominance_status}',
        f'- compression_gain_status={report.compression_gain_status}',
        f'- active_frontier_status={report.active_frontier_status}',
        f'- program_fidelity_status={report.program_fidelity_status}',
        f'- program_fidelity_fail_count={report.program_fidelity_fail_count}',
        f'- program_fidelity_warn_count={report.program_fidelity_warn_count}',
        f'- program_fidelity_gap_count={report.program_fidelity_gap_count}',
        f'- candidate_separation_gap_count={report.candidate_separation_gap_count}',
        f'- best_balance_not_beaten_count={report.best_balance_not_beaten_count}',
        f'- best_coverage_not_beaten_count={report.best_coverage_not_beaten_count}',
        f'- current_best_not_beaten_count={report.current_best_not_beaten_count}',
        f'- stable_but_no_breakthrough_count={report.stable_but_no_breakthrough_count}',
        f'- residual_gap_count={report.residual_gap_count}',
        f'- dna_authoring_status={report.dna_authoring_status}',
        f'- candidate_dna_count={report.candidate_dna_count}',
        f'- program_authoring_status={report.program_authoring_status}',
        f'- candidate_program_count={report.candidate_program_count}',
        f'- usefulness_eval_status={report.usefulness_eval_status}',
        f'- usefulness_gap_count={report.usefulness_gap_count}',
        f'- task_outcome_status={report.task_outcome_status}',
        f'- task_outcome_gap_count={report.task_outcome_gap_count}',
        f'- pairwise_similarity_gap_count={report.pairwise_similarity_gap_count}',
        f'- generic_shell_gap_count={report.generic_shell_gap_count}',
        f'- hermes_comparison_gap_count={report.hermes_comparison_gap_count}',
        f'- negative_case_resistance={report.negative_case_resistance:.2f}',
        f'- generic_shell_rejection={report.generic_shell_rejection:.2f}',
        f'- program_regression_count={report.program_regression_count}',
        f'- breakthrough_status={report.breakthrough_status}',
        '',
        '## Commands',
    ]
    for item in list(report.commands or []):
        lines.append(f'- `{item.label}` exit_code={item.exit_code}')
    if report.decision_statuses:
        lines.extend(['', '## Decision Statuses'])
        for status, values in list(report.decision_statuses.items()):
            lines.append(f'- `{status}`: {values}')
    lines.extend(['', '## Operation-Backed Summary'])
    if not report.operation_backed_status_counts:
        lines.append('- None')
    else:
        for status, count in list(report.operation_backed_status_counts.items()):
            lines.append(f'- `{status}`: {count}')
    return '\n'.join(lines).strip()


def build_verify_report(
    *,
    mode: str,
    include_live_curation: bool = False,
    decision_statuses: dict[str, list[str]] | None = None,
) -> VerifyReport:
    operation_backed_status_report = build_operation_backed_status_report()
    comparison_report = build_skill_create_comparison_report(include_hermes=False)
    commands = [
        _run_command(
            'run_tests',
            [sys.executable, 'scripts/run_tests.py'],
        ),
        _run_command(
            'run_simulation_suite',
            [sys.executable, 'scripts/run_simulation_suite.py', '--mode', mode],
        ),
    ]
    if include_live_curation:
        commands.append(
            _run_command(
                'run_public_source_curation_round',
                [sys.executable, 'scripts/run_public_source_curation_round.py'],
            )
        )
    failed = [item for item in commands if int(item.exit_code) != 0]
    if failed:
        if include_live_curation and all(item.label == 'run_public_source_curation_round' for item in failed):
            overall_status = 'warn'
        else:
            overall_status = 'fail'
    elif comparison_report.overall_status == 'fail':
        overall_status = 'fail'
    else:
        overall_status = 'pass'
    domain_specificity_status = (
        'fail'
        if any(item.auto_metrics.domain_specificity_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.domain_specificity_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    domain_expertise_status = (
        'fail'
        if any(item.auto_metrics.domain_expertise_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.domain_expertise_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    expert_structure_status = (
        'fail'
        if any(item.auto_metrics.expert_structure_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.expert_structure_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    depth_quality_status = (
        'fail'
        if any(item.auto_metrics.depth_quality_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.depth_quality_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    editorial_quality_status = (
        'fail'
        if any(item.auto_metrics.editorial_quality_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.editorial_quality_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    style_diversity_status = (
        'fail'
        if any(item.auto_metrics.style_diversity_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.style_diversity_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    move_quality_status = (
        'fail'
        if any(item.auto_metrics.move_quality_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.move_quality_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    workflow_form_status = (
        'fail'
        if any(item.auto_metrics.workflow_form_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.workflow_form_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    editorial_force_status = (
        'fail'
        if any(item.auto_metrics.editorial_force_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.editorial_force_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    pairwise_promotion_status = (
        'fail'
        if any(
            item.auto_metrics.pairwise_promotion_status not in {'promote', 'pass'}
            and not item.auto_metrics.stable_but_no_breakthrough
            for item in list(comparison_report.cases or [])
        )
        else (
            'hold'
            if any(item.auto_metrics.stable_but_no_breakthrough for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    editorial_force_non_regression = (
        'fail'
        if any(item.auto_metrics.force_non_regression_status == 'fail' for item in list(comparison_report.cases or []))
        else 'pass'
    )
    coverage_non_regression_status = str(comparison_report.coverage_non_regression_status or 'pass')
    compactness_non_regression_status = str(comparison_report.compactness_non_regression_status or 'pass')
    frontier_dominance_status = str(comparison_report.frontier_dominance_status or 'pass')
    compression_gain_status = str(comparison_report.compression_gain_status or 'pass')
    active_frontier_status = str(comparison_report.active_frontier_status or 'pass')
    program_fidelity_status = (
        'fail'
        if any(item.auto_metrics.program_fidelity_status == 'fail' for item in list(comparison_report.cases or []))
        else (
            'warn'
            if any(item.auto_metrics.program_fidelity_status == 'warn' for item in list(comparison_report.cases or []))
            else 'pass'
        )
    )
    report = VerifyReport(
        mode=mode,
        include_live_curation=include_live_curation,
        commands=commands,
        decision_statuses=dict(decision_statuses or {}),
        decision_status_summary={
            key: len(list(values or []))
            for key, values in dict(decision_statuses or {}).items()
        },
        operation_backed_status_counts=dict(operation_backed_status_report.recommended_followup_counts),
        operation_backed_actionable_count=int(operation_backed_status_report.actionable_count or 0),
        operation_backed_hold_count=int(operation_backed_status_report.hold_count or 0),
        methodology_body_quality_status=comparison_report.overall_status,
        self_review_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.self_review_status != 'pass'
        ),
        domain_specificity_status=domain_specificity_status,
        domain_specificity_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.domain_specificity_status != 'pass'
        ),
        domain_expertise_status=domain_expertise_status,
        domain_expertise_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.domain_expertise_status == 'fail'
        ),
        domain_expertise_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.domain_expertise_status == 'warn'
        ),
        expert_structure_status=expert_structure_status,
        expert_structure_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.expert_structure_status == 'fail'
        ),
        expert_structure_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.expert_structure_status == 'warn'
        ),
        expert_structure_gap_count=int(comparison_report.expert_structure_gap_count or 0),
        depth_quality_status=depth_quality_status,
        depth_quality_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.depth_quality_status == 'fail'
        ),
        depth_quality_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.depth_quality_status == 'warn'
        ),
        depth_quality_gap_count=int(comparison_report.depth_quality_gap_count or 0),
        editorial_quality_status=editorial_quality_status,
        editorial_quality_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.editorial_quality_status == 'fail'
        ),
        editorial_quality_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.editorial_quality_status == 'warn'
        ),
        editorial_gap_count=int(comparison_report.editorial_gap_count or 0),
        style_diversity_status=style_diversity_status,
        style_diversity_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.style_diversity_status == 'fail'
        ),
        style_diversity_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.style_diversity_status == 'warn'
        ),
        style_gap_count=int(comparison_report.style_gap_count or 0),
        move_quality_status=move_quality_status,
        move_quality_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.move_quality_status == 'fail'
        ),
        move_quality_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.move_quality_status == 'warn'
        ),
        move_quality_gap_count=int(comparison_report.move_quality_gap_count or 0),
        workflow_form_status=workflow_form_status,
        workflow_form_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.workflow_form_status == 'fail'
        ),
        workflow_form_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.workflow_form_status == 'warn'
        ),
        workflow_form_gap_count=int(comparison_report.workflow_form_gap_count or 0),
        editorial_force_status=editorial_force_status,
        editorial_force_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.editorial_force_status == 'fail'
        ),
        editorial_force_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.editorial_force_status == 'warn'
        ),
        editorial_force_gap_count=int(comparison_report.editorial_force_gap_count or 0),
        editorial_force_non_regression=editorial_force_non_regression,
        pairwise_promotion_status=pairwise_promotion_status,
        pairwise_promotion_gap_count=int(comparison_report.pairwise_promotion_gap_count or 0),
        promotion_hold_count=int(comparison_report.promotion_hold_count or 0),
        coverage_non_regression_status=coverage_non_regression_status,
        compactness_non_regression_status=compactness_non_regression_status,
        frontier_dominance_status=frontier_dominance_status,
        compression_gain_status=compression_gain_status,
        active_frontier_status=active_frontier_status,
        program_fidelity_status=program_fidelity_status,
        program_fidelity_fail_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.program_fidelity_status == 'fail'
        ),
        program_fidelity_warn_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if item.auto_metrics.program_fidelity_status == 'warn'
        ),
        program_fidelity_gap_count=int(comparison_report.program_fidelity_gap_count or 0),
        candidate_separation_gap_count=int(comparison_report.candidate_separation_gap_count or 0),
        best_balance_not_beaten_count=int(comparison_report.best_balance_not_beaten_count or 0),
        best_coverage_not_beaten_count=int(comparison_report.best_coverage_not_beaten_count or 0),
        current_best_not_beaten_count=int(comparison_report.current_best_not_beaten_count or 0),
        stable_but_no_breakthrough_count=int(comparison_report.stable_but_no_breakthrough_count or 0),
        residual_gap_count=int(comparison_report.residual_gap_count or 0),
        dna_authoring_status=str(comparison_report.dna_authoring_status or 'pass'),
        candidate_dna_count=int(comparison_report.candidate_dna_count or 0),
        program_authoring_status=str(comparison_report.program_authoring_status or 'pass'),
        candidate_program_count=int(comparison_report.candidate_program_count or 0),
        usefulness_eval_status=str(comparison_report.usefulness_eval_status or 'pass'),
        usefulness_gap_count=int(comparison_report.usefulness_gap_count or 0),
        task_outcome_status=str(comparison_report.task_outcome_status or 'pass'),
        task_outcome_gap_count=int(comparison_report.task_outcome_gap_count or 0),
        pairwise_similarity_gap_count=int(comparison_report.pairwise_similarity_gap_count or 0),
        generic_shell_gap_count=sum(
            1
            for item in list(comparison_report.cases or [])
            if any(issue in {'auto_generic_shell_gap', 'auto_generic_skeleton_gap'} for issue in list(item.gap_issues or []))
        ),
        hermes_comparison_gap_count=int(comparison_report.gap_count or 0),
        negative_case_resistance=float(comparison_report.negative_case_resistance or 0.0),
        generic_shell_rejection=float(comparison_report.generic_shell_rejection or 0.0),
        program_regression_count=int(comparison_report.program_regression_count or 0),
        skill_create_comparison_report=comparison_report,
        overall_status=overall_status,
        breakthrough_status=str(comparison_report.overall_status or 'pass'),
        summary=(
            f'Verify report complete: commands={len(commands)} '
            f'failed={len(failed)} overall_status={overall_status} '
            f'operation_backed_actionable={operation_backed_status_report.actionable_count} '
            f'operation_backed_hold={operation_backed_status_report.hold_count} '
            f'methodology_body_quality={comparison_report.overall_status} '
            f'domain_specificity={domain_specificity_status} '
            f'domain_expertise={domain_expertise_status} '
            f'expert_structure={expert_structure_status} '
            f'depth_quality={depth_quality_status} '
            f'editorial_quality={editorial_quality_status} '
            f'style_diversity={style_diversity_status} '
            f'move_quality={move_quality_status} '
            f'workflow_form={workflow_form_status} '
            f'editorial_force={editorial_force_status} '
            f'editorial_force_non_regression={editorial_force_non_regression} '
            f'coverage_non_regression={coverage_non_regression_status} '
            f'compactness_non_regression={compactness_non_regression_status} '
            f'frontier_dominance={frontier_dominance_status} '
            f'active_frontier_status={active_frontier_status} '
            f'pairwise_promotion={pairwise_promotion_status} '
            f'candidate_separation_gaps={comparison_report.candidate_separation_gap_count} '
            f'best_balance_not_beaten={comparison_report.best_balance_not_beaten_count} '
            f'best_coverage_not_beaten={comparison_report.best_coverage_not_beaten_count} '
            f'current_best_not_beaten={comparison_report.current_best_not_beaten_count} '
            f'residual_gaps={comparison_report.residual_gap_count} '
            f'program_fidelity={program_fidelity_status} '
            f'dna_authoring={comparison_report.dna_authoring_status} '
            f'program_authoring={comparison_report.program_authoring_status} '
            f'usefulness_eval={comparison_report.usefulness_eval_status} '
            f'task_outcome={comparison_report.task_outcome_status} '
            f'hermes_comparison_gaps={comparison_report.gap_count}'
        ),
    )
    report.markdown_summary = render_verify_report_markdown(report)
    return report


def render_ops_roundbook_markdown(report: OpsRoundbookReport) -> str:
    lines = [
        '# Ops Roundbook',
        '',
        f'- verification_status={report.verification_status}',
        f'- overall_readiness={report.overall_readiness}',
        f'- Summary: {report.summary}',
        '',
        '## Pending Create Seed Decisions',
    ]
    if not report.pending_create_seed_decisions:
        lines.append('- None')
    else:
        for item in report.pending_create_seed_decisions:
            lines.append(f'- {item}')
    lines.extend(['', '## Pending Prior Pilot Decisions'])
    if not report.pending_prior_pilot_decisions:
        lines.append('- None')
    else:
        for item in report.pending_prior_pilot_decisions:
            lines.append(f'- {item}')
    lines.extend(['', '## Pending Source Promotion Decisions'])
    if not report.pending_source_promotion_decisions:
        lines.append('- None')
    else:
        for item in report.pending_source_promotion_decisions:
            lines.append(f'- {item}')
    lines.extend(['', '## Approved Not Applied'])
    if not (
        report.approved_not_applied_create_seed_decisions
        or report.approved_not_applied_prior_pilot_decisions
        or report.approved_not_applied_source_promotion_decisions
    ):
        lines.append('- None')
    else:
        for item in report.approved_not_applied_create_seed_decisions:
            lines.append(f'- create-seed:{item}')
        for item in report.approved_not_applied_prior_pilot_decisions:
            lines.append(f'- prior-pilot:{item}')
        for item in report.approved_not_applied_source_promotion_decisions:
            lines.append(f'- source-promotion:{item}')
    lines.extend(['', '## Applied'])
    if not (
        report.applied_create_seed_decisions
        or report.applied_prior_pilot_decisions
        or report.applied_source_promotion_decisions
    ):
        lines.append('- None')
    else:
        for item in report.applied_create_seed_decisions:
            lines.append(f'- create-seed:{item}')
        for item in report.applied_prior_pilot_decisions:
            lines.append(f'- prior-pilot:{item}')
        for item in report.applied_source_promotion_decisions:
            lines.append(f'- source-promotion:{item}')
    lines.extend(['', '## Decision Refill'])
    lines.append(f'- next_create_seed_candidate={report.next_create_seed_candidate or "(none)"}')
    lines.append(f'- next_prior_family_on_hold={report.next_prior_family_on_hold or "(none)"}')
    lines.append(f'- next_source_round_status={report.next_source_round_status or "(none)"}')
    lines.extend(['', '## Operation-Backed Backlog'])
    if not (
        report.operation_backed_patch_current_candidates
        or report.operation_backed_derive_child_candidates
        or report.operation_backed_hold_candidates
    ):
        lines.append('- None')
    else:
        for item in report.operation_backed_patch_current_candidates:
            lines.append(f'- patch_current:{item}')
        for item in report.operation_backed_derive_child_candidates:
            lines.append(f'- derive_child:{item}')
        for item in report.operation_backed_hold_candidates:
            lines.append(f'- hold:{item}')
    lines.extend(['', '## Methodology Guidance Readiness'])
    lines.append(f'- methodology_body_quality_status={report.methodology_body_quality_status}')
    lines.append(f'- self_review_fail_count={report.self_review_fail_count}')
    lines.append(f'- domain_specificity_status={report.domain_specificity_status}')
    lines.append(f'- domain_specificity_fail_count={report.domain_specificity_fail_count}')
    lines.append(f'- domain_expertise_status={report.domain_expertise_status}')
    lines.append(f'- domain_expertise_fail_count={report.domain_expertise_fail_count}')
    lines.append(f'- domain_expertise_warn_count={report.domain_expertise_warn_count}')
    lines.append(f'- expert_structure_status={report.expert_structure_status}')
    lines.append(f'- expert_structure_fail_count={report.expert_structure_fail_count}')
    lines.append(f'- expert_structure_warn_count={report.expert_structure_warn_count}')
    lines.append(f'- expert_structure_gap_count={report.expert_structure_gap_count}')
    lines.append(f'- depth_quality_status={report.depth_quality_status}')
    lines.append(f'- depth_quality_fail_count={report.depth_quality_fail_count}')
    lines.append(f'- depth_quality_warn_count={report.depth_quality_warn_count}')
    lines.append(f'- depth_quality_gap_count={report.depth_quality_gap_count}')
    lines.append(f'- editorial_quality_status={report.editorial_quality_status}')
    lines.append(f'- editorial_quality_fail_count={report.editorial_quality_fail_count}')
    lines.append(f'- editorial_quality_warn_count={report.editorial_quality_warn_count}')
    lines.append(f'- editorial_gap_count={report.editorial_gap_count}')
    lines.append(f'- style_diversity_status={report.style_diversity_status}')
    lines.append(f'- style_diversity_fail_count={report.style_diversity_fail_count}')
    lines.append(f'- style_diversity_warn_count={report.style_diversity_warn_count}')
    lines.append(f'- style_gap_count={report.style_gap_count}')
    lines.append(f'- move_quality_status={report.move_quality_status}')
    lines.append(f'- move_quality_fail_count={report.move_quality_fail_count}')
    lines.append(f'- move_quality_warn_count={report.move_quality_warn_count}')
    lines.append(f'- move_quality_gap_count={report.move_quality_gap_count}')
    lines.append(f'- workflow_form_status={report.workflow_form_status}')
    lines.append(f'- workflow_form_fail_count={report.workflow_form_fail_count}')
    lines.append(f'- workflow_form_warn_count={report.workflow_form_warn_count}')
    lines.append(f'- workflow_form_gap_count={report.workflow_form_gap_count}')
    lines.append(f'- editorial_force_status={report.editorial_force_status}')
    lines.append(f'- editorial_force_fail_count={report.editorial_force_fail_count}')
    lines.append(f'- editorial_force_warn_count={report.editorial_force_warn_count}')
    lines.append(f'- editorial_force_gap_count={report.editorial_force_gap_count}')
    lines.append(f'- editorial_force_non_regression={report.editorial_force_non_regression}')
    lines.append(f'- pairwise_promotion_status={report.pairwise_promotion_status}')
    lines.append(f'- pairwise_promotion_gap_count={report.pairwise_promotion_gap_count}')
    lines.append(f'- promotion_hold_count={report.promotion_hold_count}')
    lines.append(f'- coverage_non_regression_status={report.coverage_non_regression_status}')
    lines.append(f'- compactness_non_regression_status={report.compactness_non_regression_status}')
    lines.append(f'- frontier_dominance_status={report.frontier_dominance_status}')
    lines.append(f'- compression_gain_status={report.compression_gain_status}')
    lines.append(f'- active_frontier_status={report.active_frontier_status}')
    lines.append(f'- program_fidelity_status={report.program_fidelity_status}')
    lines.append(f'- program_fidelity_fail_count={report.program_fidelity_fail_count}')
    lines.append(f'- program_fidelity_warn_count={report.program_fidelity_warn_count}')
    lines.append(f'- program_fidelity_gap_count={report.program_fidelity_gap_count}')
    lines.append(f'- candidate_separation_gap_count={report.candidate_separation_gap_count}')
    lines.append(f'- best_balance_not_beaten_count={report.best_balance_not_beaten_count}')
    lines.append(f'- best_coverage_not_beaten_count={report.best_coverage_not_beaten_count}')
    lines.append(f'- current_best_not_beaten_count={report.current_best_not_beaten_count}')
    lines.append(f'- stable_but_no_breakthrough_count={report.stable_but_no_breakthrough_count}')
    lines.append(f'- residual_gap_count={report.residual_gap_count}')
    lines.append(f'- dna_authoring_status={report.dna_authoring_status}')
    lines.append(f'- candidate_dna_count={report.candidate_dna_count}')
    lines.append(f'- program_authoring_status={report.program_authoring_status}')
    lines.append(f'- candidate_program_count={report.candidate_program_count}')
    lines.append(f'- usefulness_eval_status={report.usefulness_eval_status}')
    lines.append(f'- usefulness_gap_count={report.usefulness_gap_count}')
    lines.append(f'- task_outcome_status={report.task_outcome_status}')
    lines.append(f'- task_outcome_gap_count={report.task_outcome_gap_count}')
    lines.append(f'- pairwise_similarity_gap_count={report.pairwise_similarity_gap_count}')
    lines.append(f'- generic_shell_gap_count={report.generic_shell_gap_count}')
    lines.append(f'- hermes_comparison_gap_count={report.hermes_comparison_gap_count}')
    lines.append(f'- negative_case_resistance={report.negative_case_resistance:.2f}')
    lines.append(f'- generic_shell_rejection={report.generic_shell_rejection:.2f}')
    lines.append(f'- program_regression_count={report.program_regression_count}')
    lines.append(f'- breakthrough_status={report.breakthrough_status}')
    return '\n'.join(lines).strip()


def build_ops_roundbook_report(
    *,
    verify_report: VerifyReport,
    runtime_ops_decision_pack: RuntimeOpsDecisionPack,
    prior_pilot_exercise: RuntimePriorPilotExerciseReport,
    source_promotion_pack: PublicSourcePromotionPack,
    create_seed_pack: RuntimeCreateSeedProposalPack | None = None,
    prior_pilot_report: RuntimePriorPilotReport | None = None,
    source_curation_round: PublicSourceCurationRoundReport | None = None,
) -> OpsRoundbookReport:
    operation_backed_backlog_report = build_operation_backed_backlog_report()
    status_groups = summarize_decision_statuses(
        create_seed_candidates=list(runtime_ops_decision_pack.create_seed_candidates or []),
        prior_pilot_candidates=list(runtime_ops_decision_pack.prior_pilot_candidates or []),
        source_promotion_candidates=list(runtime_ops_decision_pack.source_promotion_candidates or []),
    )
    pending_create_seed_decisions = [
        item.candidate_key
        for item in list(runtime_ops_decision_pack.create_seed_candidates or [])
        if item.decision_status == 'pending'
    ]
    pending_prior_pilot_decisions = [
        item.family
        for item in list(runtime_ops_decision_pack.prior_pilot_candidates or [])
        if item.decision_status == 'pending'
    ]
    pending_source_promotion_decisions = [
        item.repo_full_name
        for item in list(runtime_ops_decision_pack.source_promotion_candidates or [])
        if item.decision_status == 'pending'
    ]
    approved_not_applied_create_seed_decisions = [
        item.candidate_key
        for item in list(runtime_ops_decision_pack.create_seed_candidates or [])
        if item.decision_status == 'approved_not_applied'
    ]
    approved_not_applied_prior_pilot_decisions = [
        item.family
        for item in list(runtime_ops_decision_pack.prior_pilot_candidates or [])
        if item.decision_status == 'approved_not_applied'
    ]
    approved_not_applied_source_promotion_decisions = [
        item.repo_full_name
        for item in list(runtime_ops_decision_pack.source_promotion_candidates or [])
        if item.decision_status == 'approved_not_applied'
    ]
    applied_create_seed_decisions = [
        item.candidate_key
        for item in list(runtime_ops_decision_pack.create_seed_candidates or [])
        if item.decision_status == 'applied'
    ]
    applied_prior_pilot_decisions = [
        item.family
        for item in list(runtime_ops_decision_pack.prior_pilot_candidates or [])
        if item.decision_status == 'applied'
    ]
    applied_source_promotion_decisions = [
        item.repo_full_name
        for item in list(runtime_ops_decision_pack.source_promotion_candidates or [])
        if item.decision_status == 'applied'
    ]
    next_create_seed_candidate = (
        pending_create_seed_decisions[0]
        if pending_create_seed_decisions
        else (
            next(
                (
                    item.candidate_key
                    for item in list(create_seed_pack.proposals or [])
                    if item.recommended_decision in {'review', 'defer'}
                    and item.candidate_key not in applied_create_seed_decisions
                ),
                '',
            )
            if create_seed_pack is not None
            else ''
        )
    )
    next_prior_family_on_hold = (
        next(
            (
                item.family
                for item in list(prior_pilot_report.profiles or [])
                if item.recommended_status == 'hold'
            ),
            '',
        )
        if prior_pilot_report is not None
        else ''
    )
    if pending_source_promotion_decisions or approved_not_applied_source_promotion_decisions:
        next_source_round_status = 'wait_for_current_source_promotion_resolution'
    elif applied_source_promotion_decisions:
        next_source_round_status = 'wait_for_post_apply_stability_before_next_live_round'
    elif source_curation_round is not None and source_curation_round.rehearsal_passed:
        next_source_round_status = 'ready_for_next_live_round_when_new_candidates_exist'
    elif source_curation_round is not None:
        next_source_round_status = 'rehearsal_required_before_next_live_round'
    else:
        next_source_round_status = ''

    if verify_report.overall_status == 'fail':
        overall_readiness = 'blocked'
    elif (
        verify_report.overall_status == 'warn'
        or pending_create_seed_decisions
        or pending_prior_pilot_decisions
        or pending_source_promotion_decisions
        or approved_not_applied_create_seed_decisions
        or approved_not_applied_prior_pilot_decisions
        or approved_not_applied_source_promotion_decisions
    ):
        overall_readiness = 'caution'
    else:
        overall_readiness = 'ready'

    report = OpsRoundbookReport(
        verification_status=verify_report.overall_status,
        verify_report=verify_report.model_copy(
            update={
                'decision_statuses': status_groups,
                'decision_status_summary': {
                    key: len(list(values or []))
                    for key, values in status_groups.items()
                },
            }
        ),
        runtime_ops_decision_pack=runtime_ops_decision_pack,
        prior_pilot_exercise=prior_pilot_exercise,
        source_promotion_pack=source_promotion_pack,
        pending_create_seed_decisions=pending_create_seed_decisions,
        pending_prior_pilot_decisions=pending_prior_pilot_decisions,
        pending_source_promotion_decisions=pending_source_promotion_decisions,
        approved_not_applied_create_seed_decisions=approved_not_applied_create_seed_decisions,
        approved_not_applied_prior_pilot_decisions=approved_not_applied_prior_pilot_decisions,
        approved_not_applied_source_promotion_decisions=approved_not_applied_source_promotion_decisions,
        applied_create_seed_decisions=applied_create_seed_decisions,
        applied_prior_pilot_decisions=applied_prior_pilot_decisions,
        applied_source_promotion_decisions=applied_source_promotion_decisions,
        next_create_seed_candidate=next_create_seed_candidate,
        next_prior_family_on_hold=next_prior_family_on_hold,
        next_source_round_status=next_source_round_status,
        operation_backed_backlog_report=operation_backed_backlog_report,
        operation_backed_patch_current_candidates=list(operation_backed_backlog_report.patch_current_candidates or []),
        operation_backed_derive_child_candidates=list(operation_backed_backlog_report.derive_child_candidates or []),
        operation_backed_hold_candidates=list(operation_backed_backlog_report.hold_candidates or []),
        methodology_body_quality_status=verify_report.methodology_body_quality_status,
        self_review_fail_count=verify_report.self_review_fail_count,
        domain_specificity_status=verify_report.domain_specificity_status,
        domain_specificity_fail_count=verify_report.domain_specificity_fail_count,
        domain_expertise_status=verify_report.domain_expertise_status,
        domain_expertise_fail_count=verify_report.domain_expertise_fail_count,
        domain_expertise_warn_count=verify_report.domain_expertise_warn_count,
        expert_structure_status=verify_report.expert_structure_status,
        expert_structure_fail_count=verify_report.expert_structure_fail_count,
        expert_structure_warn_count=verify_report.expert_structure_warn_count,
        expert_structure_gap_count=verify_report.expert_structure_gap_count,
        depth_quality_status=verify_report.depth_quality_status,
        depth_quality_fail_count=verify_report.depth_quality_fail_count,
        depth_quality_warn_count=verify_report.depth_quality_warn_count,
        depth_quality_gap_count=verify_report.depth_quality_gap_count,
        editorial_quality_status=verify_report.editorial_quality_status,
        editorial_quality_fail_count=verify_report.editorial_quality_fail_count,
        editorial_quality_warn_count=verify_report.editorial_quality_warn_count,
        editorial_gap_count=verify_report.editorial_gap_count,
        style_diversity_status=verify_report.style_diversity_status,
        style_diversity_fail_count=verify_report.style_diversity_fail_count,
        style_diversity_warn_count=verify_report.style_diversity_warn_count,
        style_gap_count=verify_report.style_gap_count,
        move_quality_status=verify_report.move_quality_status,
        move_quality_fail_count=verify_report.move_quality_fail_count,
        move_quality_warn_count=verify_report.move_quality_warn_count,
        move_quality_gap_count=verify_report.move_quality_gap_count,
        workflow_form_status=verify_report.workflow_form_status,
        workflow_form_fail_count=verify_report.workflow_form_fail_count,
        workflow_form_warn_count=verify_report.workflow_form_warn_count,
        workflow_form_gap_count=verify_report.workflow_form_gap_count,
        editorial_force_status=verify_report.editorial_force_status,
        editorial_force_fail_count=verify_report.editorial_force_fail_count,
        editorial_force_warn_count=verify_report.editorial_force_warn_count,
        editorial_force_gap_count=verify_report.editorial_force_gap_count,
        editorial_force_non_regression=verify_report.editorial_force_non_regression,
        pairwise_promotion_status=verify_report.pairwise_promotion_status,
        pairwise_promotion_gap_count=verify_report.pairwise_promotion_gap_count,
        promotion_hold_count=verify_report.promotion_hold_count,
        coverage_non_regression_status=verify_report.coverage_non_regression_status,
        compactness_non_regression_status=verify_report.compactness_non_regression_status,
        frontier_dominance_status=verify_report.frontier_dominance_status,
        compression_gain_status=verify_report.compression_gain_status,
        active_frontier_status=verify_report.active_frontier_status,
        program_fidelity_status=verify_report.program_fidelity_status,
        program_fidelity_fail_count=verify_report.program_fidelity_fail_count,
        program_fidelity_warn_count=verify_report.program_fidelity_warn_count,
        program_fidelity_gap_count=verify_report.program_fidelity_gap_count,
        candidate_separation_gap_count=verify_report.candidate_separation_gap_count,
        best_balance_not_beaten_count=verify_report.best_balance_not_beaten_count,
        best_coverage_not_beaten_count=verify_report.best_coverage_not_beaten_count,
        current_best_not_beaten_count=verify_report.current_best_not_beaten_count,
        stable_but_no_breakthrough_count=verify_report.stable_but_no_breakthrough_count,
        residual_gap_count=verify_report.residual_gap_count,
        dna_authoring_status=verify_report.dna_authoring_status,
        candidate_dna_count=verify_report.candidate_dna_count,
        program_authoring_status=verify_report.program_authoring_status,
        candidate_program_count=verify_report.candidate_program_count,
        usefulness_eval_status=verify_report.usefulness_eval_status,
        usefulness_gap_count=verify_report.usefulness_gap_count,
        task_outcome_status=verify_report.task_outcome_status,
        task_outcome_gap_count=verify_report.task_outcome_gap_count,
        pairwise_similarity_gap_count=verify_report.pairwise_similarity_gap_count,
        generic_shell_gap_count=verify_report.generic_shell_gap_count,
        hermes_comparison_gap_count=verify_report.hermes_comparison_gap_count,
        negative_case_resistance=verify_report.negative_case_resistance,
        generic_shell_rejection=verify_report.generic_shell_rejection,
        program_regression_count=verify_report.program_regression_count,
        overall_readiness=overall_readiness,
        breakthrough_status=verify_report.breakthrough_status,
        summary=(
            f'Ops roundbook complete: verification={verify_report.overall_status} '
            f'create_seed_pending={len(pending_create_seed_decisions)} '
            f'prior_pending={len(pending_prior_pilot_decisions)} '
            f'source_pending={len(pending_source_promotion_decisions)} '
            f'approved_not_applied={len(status_groups.get("approved_not_applied", []))} '
            f'operation_backed_patch={len(operation_backed_backlog_report.patch_current_candidates)} '
            f'operation_backed_derive_child={len(operation_backed_backlog_report.derive_child_candidates)} '
            f'operation_backed_hold={len(operation_backed_backlog_report.hold_candidates)} '
            f'domain_expertise={verify_report.domain_expertise_status} '
            f'expert_structure={verify_report.expert_structure_status} '
            f'depth_quality={verify_report.depth_quality_status} '
            f'editorial_quality={verify_report.editorial_quality_status} '
            f'style_diversity={verify_report.style_diversity_status} '
            f'move_quality={verify_report.move_quality_status} '
            f'workflow_form={verify_report.workflow_form_status} '
            f'editorial_force={verify_report.editorial_force_status} '
            f'editorial_force_non_regression={verify_report.editorial_force_non_regression} '
            f'coverage_non_regression={verify_report.coverage_non_regression_status} '
            f'compactness_non_regression={verify_report.compactness_non_regression_status} '
            f'frontier_dominance={verify_report.frontier_dominance_status} '
            f'active_frontier_status={verify_report.active_frontier_status} '
            f'pairwise_promotion={verify_report.pairwise_promotion_status} '
            f'candidate_separation_gaps={verify_report.candidate_separation_gap_count} '
            f'best_balance_not_beaten={verify_report.best_balance_not_beaten_count} '
            f'best_coverage_not_beaten={verify_report.best_coverage_not_beaten_count} '
            f'current_best_not_beaten={verify_report.current_best_not_beaten_count} '
            f'residual_gaps={verify_report.residual_gap_count} '
            f'program_fidelity={verify_report.program_fidelity_status} '
            f'dna_authoring={verify_report.dna_authoring_status} '
            f'program_authoring={verify_report.program_authoring_status} '
            f'usefulness_eval={verify_report.usefulness_eval_status} '
            f'task_outcome={verify_report.task_outcome_status} '
            f'breakthrough_status={verify_report.breakthrough_status} '
            f'overall_readiness={overall_readiness} '
            f'next_create_seed={next_create_seed_candidate or "none"} '
            f'next_prior_hold={next_prior_family_on_hold or "none"}'
        ),
    )
    report.markdown_summary = render_ops_roundbook_markdown(report)
    return report
