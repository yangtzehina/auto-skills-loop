from __future__ import annotations

from pydantic import BaseModel, Field


class FrontierStabilityProfileRun(BaseModel):
    skill_name: str
    decision_pressure_score: float = 0.0
    task_outcome_with_skill_average: float = 0.0
    redundancy_ratio: float = 0.0
    generic_surface_leakage: float = 0.0
    pairwise_promotion_status: str = "unknown"
    residual_gap_count: int = 0
    active_frontier_status: str = "unknown"


class FrontierStabilityRun(BaseModel):
    run_index: int
    overall_status: str = "pass"
    gap_count: int = 0
    active_frontier_status: str = "pass"
    force_non_regression_status: str = "pass"
    coverage_non_regression_status: str = "pass"
    compactness_non_regression_status: str = "pass"
    frontier_regressed: bool = False
    profile_runs: list[FrontierStabilityProfileRun] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class FrontierStabilityProfileSummary(BaseModel):
    skill_name: str
    decision_pressure_score_min: float = 0.0
    decision_pressure_score_max: float = 0.0
    decision_pressure_score_spread: float = 0.0
    task_outcome_with_skill_average_min: float = 0.0
    task_outcome_with_skill_average_max: float = 0.0
    task_outcome_with_skill_average_spread: float = 0.0
    redundancy_ratio_min: float = 0.0
    redundancy_ratio_max: float = 0.0
    redundancy_ratio_spread: float = 0.0
    generic_surface_leakage_min: float = 0.0
    generic_surface_leakage_max: float = 0.0
    generic_surface_leakage_spread: float = 0.0
    pairwise_promotion_statuses: list[str] = Field(default_factory=list)
    residual_gap_counts: list[int] = Field(default_factory=list)
    status: str = "pass"
    summary: list[str] = Field(default_factory=list)


class FrontierStabilityReport(BaseModel):
    schema_version: str = "1.0.0"
    frontier_version: str = "frontier_v3"
    run_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    frontier_regression_count: int = 0
    frontier_state: str = "stable_frontier"
    metric_variance_summary: dict[str, dict[str, float]] = Field(default_factory=dict)
    runs: list[FrontierStabilityRun] = Field(default_factory=list)
    profile_summaries: list[FrontierStabilityProfileSummary] = Field(default_factory=list)
    status: str = "pass"
    summary: str = ""
    markdown_summary: str = ""
