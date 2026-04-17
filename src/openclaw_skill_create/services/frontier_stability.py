from __future__ import annotations

from statistics import mean

from ..models.comparison import SkillCreateComparisonCaseResult, SkillCreateComparisonReport
from ..models.frontier_stability import (
    FrontierStabilityProfileRun,
    FrontierStabilityProfileSummary,
    FrontierStabilityReport,
    FrontierStabilityRun,
)
from .expert_skill_studio import build_active_frontier_version
from .skill_create_comparison import build_skill_create_comparison_report


DEFAULT_FRONTIER_STABILITY_RUNS = 10
_PRESSURE_SPREAD_LIMIT = 0.03
_OUTCOME_SPREAD_LIMIT = 0.03
_REDUNDANCY_SPREAD_LIMIT = 0.02
_ACTIVE_BREAKTHROUGH_SKILL = "decision-loop-stress-test"


def _profile_run(case: SkillCreateComparisonCaseResult) -> FrontierStabilityProfileRun:
    metrics = case.auto_metrics
    return FrontierStabilityProfileRun(
        skill_name=case.skill_name,
        decision_pressure_score=round(float(metrics.decision_pressure_score or 0.0), 4),
        task_outcome_with_skill_average=round(float(metrics.task_outcome_with_skill_average or 0.0), 4),
        redundancy_ratio=round(float(metrics.redundancy_ratio or 0.0), 4),
        generic_surface_leakage=round(float(metrics.generic_surface_leakage or 0.0), 4),
        pairwise_promotion_status=str(metrics.pairwise_promotion_status or "unknown"),
        residual_gap_count=int(metrics.residual_gap_count or 0),
        active_frontier_status=str(metrics.active_frontier_status or "unknown"),
    )


def _run_summary(run_index: int, report: SkillCreateComparisonReport) -> FrontierStabilityRun:
    overall_status = str(report.overall_status or "pass")
    frontier_regressed = any(
        value != "pass"
        for value in (
            str(report.force_non_regression_status or "pass"),
            str(report.coverage_non_regression_status or "pass"),
            str(report.compactness_non_regression_status or "pass"),
        )
    ) or int(report.gap_count or 0) > 0 or str(report.active_frontier_status or "pass") == "fail"
    return FrontierStabilityRun(
        run_index=run_index,
        overall_status=overall_status,
        gap_count=int(report.gap_count or 0),
        active_frontier_status=str(report.active_frontier_status or "pass"),
        force_non_regression_status=str(report.force_non_regression_status or "pass"),
        coverage_non_regression_status=str(report.coverage_non_regression_status or "pass"),
        compactness_non_regression_status=str(report.compactness_non_regression_status or "pass"),
        frontier_regressed=frontier_regressed,
        profile_runs=[_profile_run(case) for case in list(report.cases or [])],
        summary=[
            f"run_index={run_index}",
            f"overall_status={overall_status}",
            f"gap_count={int(report.gap_count or 0)}",
            f"active_frontier_status={str(report.active_frontier_status or 'pass')}",
            f"force_non_regression_status={str(report.force_non_regression_status or 'pass')}",
            f"coverage_non_regression_status={str(report.coverage_non_regression_status or 'pass')}",
            f"compactness_non_regression_status={str(report.compactness_non_regression_status or 'pass')}",
        ],
    )


def _spread(values: list[float]) -> tuple[float, float, float]:
    items = [round(float(value or 0.0), 4) for value in list(values or [])]
    if not items:
        return 0.0, 0.0, 0.0
    return min(items), max(items), round(max(items) - min(items), 4)


def _profile_summary(profile_runs: list[FrontierStabilityProfileRun]) -> FrontierStabilityProfileSummary:
    skill_name = profile_runs[0].skill_name if profile_runs else ""
    pressure_values = [item.decision_pressure_score for item in profile_runs]
    outcome_values = [item.task_outcome_with_skill_average for item in profile_runs]
    redundancy_values = [item.redundancy_ratio for item in profile_runs]
    leakage_values = [item.generic_surface_leakage for item in profile_runs]
    pressure_min, pressure_max, pressure_spread = _spread(pressure_values)
    outcome_min, outcome_max, outcome_spread = _spread(outcome_values)
    redundancy_min, redundancy_max, redundancy_spread = _spread(redundancy_values)
    leakage_min, leakage_max, leakage_spread = _spread(leakage_values)
    statuses = [str(item.pairwise_promotion_status or "unknown") for item in profile_runs]
    residuals = [int(item.residual_gap_count or 0) for item in profile_runs]
    frontier_statuses = [str(item.active_frontier_status or "unknown") for item in profile_runs]
    stable_active_target_gap = (
        skill_name == _ACTIVE_BREAKTHROUGH_SKILL
        and all(value in {"pass", "matched", "beaten"} for value in frontier_statuses)
        and all(value in {"hold", "promote"} for value in statuses)
    )
    status = "pass"
    if (
        pressure_spread > _PRESSURE_SPREAD_LIMIT
        or outcome_spread > _OUTCOME_SPREAD_LIMIT
        or redundancy_spread > _REDUNDANCY_SPREAD_LIMIT
        or (any(value > 0 for value in residuals) and not stable_active_target_gap)
        or any(value == "fail" for value in frontier_statuses)
    ):
        status = "fail"
    return FrontierStabilityProfileSummary(
        skill_name=skill_name,
        decision_pressure_score_min=pressure_min,
        decision_pressure_score_max=pressure_max,
        decision_pressure_score_spread=pressure_spread,
        task_outcome_with_skill_average_min=outcome_min,
        task_outcome_with_skill_average_max=outcome_max,
        task_outcome_with_skill_average_spread=outcome_spread,
        redundancy_ratio_min=redundancy_min,
        redundancy_ratio_max=redundancy_max,
        redundancy_ratio_spread=redundancy_spread,
        generic_surface_leakage_min=leakage_min,
        generic_surface_leakage_max=leakage_max,
        generic_surface_leakage_spread=leakage_spread,
        pairwise_promotion_statuses=statuses,
        residual_gap_counts=residuals,
        status=status,
        summary=[
            f"skill_name={skill_name}",
            f"decision_pressure_score_spread={pressure_spread:.4f}",
            f"task_outcome_with_skill_average_spread={outcome_spread:.4f}",
            f"redundancy_ratio_spread={redundancy_spread:.4f}",
            f"generic_surface_leakage_spread={leakage_spread:.4f}",
            f"pairwise_promotion_statuses={statuses}",
            f"residual_gap_counts={residuals}",
            f"status={status}",
        ],
    )


def render_frontier_stability_markdown(report: FrontierStabilityReport) -> str:
    lines = [
        "# Frontier Stability Report",
        "",
        f"- frontier_version={report.frontier_version}",
        f"- run_count={report.run_count}",
        f"- pass_count={report.pass_count}",
        f"- fail_count={report.fail_count}",
        f"- frontier_regression_count={report.frontier_regression_count}",
        f"- frontier_state={report.frontier_state}",
        f"- status={report.status}",
        f"- summary={report.summary}",
        "",
        "## Profile Summaries",
    ]
    for profile in list(report.profile_summaries or []):
        lines.append(f"- `{profile.skill_name}` status={profile.status}")
        lines.append(
            "  "
            + ", ".join(
                [
                    f"decision_pressure_spread={profile.decision_pressure_score_spread:.4f}",
                    f"task_outcome_spread={profile.task_outcome_with_skill_average_spread:.4f}",
                    f"redundancy_spread={profile.redundancy_ratio_spread:.4f}",
                    f"leakage_spread={profile.generic_surface_leakage_spread:.4f}",
                    f"pairwise_promotion_statuses={profile.pairwise_promotion_statuses}",
                    f"residual_gap_counts={profile.residual_gap_counts}",
                ]
            )
        )
    lines.extend(["", "## Runs"])
    for run in list(report.runs or []):
        lines.append(
            f"- run={run.run_index} overall_status={run.overall_status} "
            f"gap_count={run.gap_count} active_frontier_status={run.active_frontier_status} "
            f"force={run.force_non_regression_status} coverage={run.coverage_non_regression_status} "
            f"compactness={run.compactness_non_regression_status}"
        )
    return "\n".join(lines).strip()


def build_frontier_stability_report(*, runs: int = DEFAULT_FRONTIER_STABILITY_RUNS) -> FrontierStabilityReport:
    if int(runs or 0) <= 0:
        raise ValueError("runs must be greater than 0")

    run_reports: list[FrontierStabilityRun] = []
    for index in range(1, int(runs) + 1):
        comparison = build_skill_create_comparison_report(include_hermes=False)
        run_reports.append(_run_summary(index, comparison))

    pass_count = sum(
        1
        for run in run_reports
        if (
            run.overall_status in {"breakthrough", "stable_but_no_breakthrough"}
            and run.gap_count == 0
            and run.active_frontier_status in {"pass", "matched", "beaten"}
            and run.force_non_regression_status == "pass"
            and run.coverage_non_regression_status == "pass"
            and run.compactness_non_regression_status == "pass"
        )
    )
    fail_count = len(run_reports) - pass_count
    frontier_regression_count = sum(1 for run in run_reports if run.frontier_regressed)

    profile_summary_map: dict[str, list[FrontierStabilityProfileRun]] = {}
    for run in list(run_reports):
        for profile in list(run.profile_runs or []):
            profile_summary_map.setdefault(profile.skill_name, []).append(profile)
    profile_summaries = [
        _profile_summary(profile_summary_map[skill_name])
        for skill_name in sorted(profile_summary_map)
    ]

    metric_variance_summary: dict[str, dict[str, float]] = {}
    for item in list(profile_summaries or []):
        profile_runs = profile_summary_map[item.skill_name]
        metric_variance_summary[item.skill_name] = {
            "decision_pressure_score_spread": item.decision_pressure_score_spread,
            "task_outcome_with_skill_average_spread": item.task_outcome_with_skill_average_spread,
            "redundancy_ratio_spread": item.redundancy_ratio_spread,
            "generic_surface_leakage_spread": item.generic_surface_leakage_spread,
            "mean_task_outcome_with_skill_average": round(
                mean(run.task_outcome_with_skill_average for run in profile_runs),
                4,
            ),
        }

    status = "pass"
    if fail_count > 0 or frontier_regression_count > 0 or any(item.status != "pass" for item in list(profile_summaries or [])):
        status = "fail"
    frontier_state = "stable_frontier" if status == "pass" else "frontier_regressed"
    report = FrontierStabilityReport(
        frontier_version=build_active_frontier_version(),
        run_count=int(runs),
        pass_count=pass_count,
        fail_count=fail_count,
        frontier_regression_count=frontier_regression_count,
        frontier_state=frontier_state,
        metric_variance_summary=metric_variance_summary,
        runs=run_reports,
        profile_summaries=profile_summaries,
        status=status,
        summary=(
            f"Frontier stability complete: runs={runs} pass_count={pass_count} "
            f"fail_count={fail_count} frontier_regressions={frontier_regression_count} "
            f"frontier_state={frontier_state}"
        ),
    )
    report.markdown_summary = render_frontier_stability_markdown(report)
    return report
