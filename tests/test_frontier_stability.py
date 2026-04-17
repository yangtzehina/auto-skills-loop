from __future__ import annotations

from pathlib import Path

from tests.runtime_test_helpers import invoke_main, load_script_module

from openclaw_skill_create.models.comparison import (
    SkillCreateComparisonCaseResult,
    SkillCreateComparisonMetrics,
    SkillCreateComparisonReport,
)
from openclaw_skill_create.services.expert_skill_studio import build_active_frontier_version
from openclaw_skill_create.services.frontier_stability import build_frontier_stability_report


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_frontier_stability_report.py"


def _comparison_case(
    skill_name: str,
    *,
    decision_pressure_score: float,
    task_outcome_with_skill_average: float,
    redundancy_ratio: float,
    generic_surface_leakage: float = 0.0,
    pairwise_promotion_status: str = "hold",
    residual_gap_count: int = 0,
    active_frontier_status: str = "matched",
) -> SkillCreateComparisonCaseResult:
    return SkillCreateComparisonCaseResult(
        case_id=skill_name,
        skill_name=skill_name,
        auto_metrics=SkillCreateComparisonMetrics(
            decision_pressure_score=decision_pressure_score,
            task_outcome_with_skill_average=task_outcome_with_skill_average,
            redundancy_ratio=redundancy_ratio,
            generic_surface_leakage=generic_surface_leakage,
            pairwise_promotion_status=pairwise_promotion_status,
            residual_gap_count=residual_gap_count,
            active_frontier_status=active_frontier_status,
        ),
    )


def _comparison_report(
    *,
    overall_status: str = "stable_but_no_breakthrough",
    gap_count: int = 0,
    active_frontier_status: str = "pass",
    force_non_regression_status: str = "pass",
    coverage_non_regression_status: str = "pass",
    compactness_non_regression_status: str = "pass",
    cases: list[SkillCreateComparisonCaseResult] | None = None,
) -> SkillCreateComparisonReport:
    return SkillCreateComparisonReport(
        overall_status=overall_status,
        gap_count=gap_count,
        active_frontier_status=active_frontier_status,
        force_non_regression_status=force_non_regression_status,
        coverage_non_regression_status=coverage_non_regression_status,
        compactness_non_regression_status=compactness_non_regression_status,
        cases=cases or [],
    )


def test_frontier_stability_report_marks_stable_frontier(monkeypatch):
    run_counter = {"count": 0}

    def fake_build_skill_create_comparison_report(*, include_hermes: bool = False):
        run_counter["count"] += 1
        drift = 0.002 * run_counter["count"]
        return _comparison_report(
            cases=[
                _comparison_case(
                    "concept-to-mvp-pack",
                    decision_pressure_score=0.9467,
                    task_outcome_with_skill_average=0.9398 + drift,
                    redundancy_ratio=0.05,
                ),
                _comparison_case(
                    "decision-loop-stress-test",
                    decision_pressure_score=0.9692,
                    task_outcome_with_skill_average=0.8981 + drift,
                    redundancy_ratio=0.01,
                    residual_gap_count=2,
                ),
                _comparison_case(
                    "simulation-resource-loop-design",
                    decision_pressure_score=0.9385,
                    task_outcome_with_skill_average=1.0,
                    redundancy_ratio=0.0141,
                ),
            ]
        )

    monkeypatch.setattr(
        "openclaw_skill_create.services.frontier_stability.build_skill_create_comparison_report",
        fake_build_skill_create_comparison_report,
    )

    report = build_frontier_stability_report()

    assert report.status == "pass"
    assert report.frontier_state == "stable_frontier"
    assert report.run_count == 10
    assert report.pass_count == 10
    assert report.fail_count == 0
    assert report.frontier_regression_count == 0
    assert {item.skill_name for item in report.profile_summaries} == {
        "concept-to-mvp-pack",
        "decision-loop-stress-test",
        "simulation-resource-loop-design",
    }


def test_frontier_stability_report_fails_on_regression(monkeypatch):
    run_counter = {"count": 0}

    def fake_build_skill_create_comparison_report(*, include_hermes: bool = False):
        run_counter["count"] += 1
        if run_counter["count"] == 3:
            return _comparison_report(
                overall_status="fail",
                gap_count=1,
                active_frontier_status="fail",
                force_non_regression_status="fail",
                cases=[
                    _comparison_case(
                        "decision-loop-stress-test",
                        decision_pressure_score=0.90,
                        task_outcome_with_skill_average=0.84,
                        redundancy_ratio=0.05,
                        residual_gap_count=1,
                        active_frontier_status="fail",
                    )
                ],
            )
        return _comparison_report(
            cases=[
                _comparison_case(
                    "decision-loop-stress-test",
                    decision_pressure_score=0.9692,
                    task_outcome_with_skill_average=0.8981,
                    redundancy_ratio=0.01,
                )
            ]
        )

    monkeypatch.setattr(
        "openclaw_skill_create.services.frontier_stability.build_skill_create_comparison_report",
        fake_build_skill_create_comparison_report,
    )

    report = build_frontier_stability_report(runs=5)

    assert report.status == "fail"
    assert report.frontier_state == "frontier_regressed"
    assert report.fail_count == 1
    assert report.frontier_regression_count == 1


def test_run_frontier_stability_report_cli(monkeypatch):
    module = load_script_module(SCRIPT_PATH, "skill_create_run_frontier_stability_report")

    code, stdout, stderr = invoke_main(
        module,
        ["run_frontier_stability_report.py", "--runs", "1", "--format", "json"],
        monkeypatch,
    )

    assert code in {0, 1}
    assert stderr == ""
    assert f'"frontier_version": "{build_active_frontier_version()}"' in stdout
