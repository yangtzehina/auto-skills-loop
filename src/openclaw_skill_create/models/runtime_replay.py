from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RuntimeReplayScenarioReport(BaseModel):
    scenario_id: str
    description: str = ''
    run_count: int = 0
    expected_actions: list[str] = Field(default_factory=list)
    actual_actions: list[str] = Field(default_factory=list)
    expected_final_followup_action: str = ''
    actual_final_followup_action: str = ''
    expected_final_quality_score: float = 0.0
    actual_final_quality_score: float = 0.0
    expected_final_usage_stats: dict[str, int] = Field(default_factory=dict)
    actual_final_usage_stats: dict[str, int] = Field(default_factory=dict)
    expected_final_recent_run_ids: list[str] = Field(default_factory=list)
    actual_final_recent_run_ids: list[str] = Field(default_factory=list)
    expected_final_requirement_gaps: list[str] = Field(default_factory=list)
    actual_final_requirement_gaps: list[str] = Field(default_factory=list)
    passed: bool = False
    mismatches: list[str] = Field(default_factory=list)


class RuntimeReplayReport(BaseModel):
    fixture_root: str
    scenario_reports: list[RuntimeReplayScenarioReport] = Field(default_factory=list)
    passed: bool = False
    summary: str = ''


class RuntimeReplayScenarioBaseline(BaseModel):
    scenario_id: str
    actual_actions: list[str] = Field(default_factory=list)
    actual_final_followup_action: str = ''
    actual_final_quality_score: float = 0.0
    actual_final_usage_stats: dict[str, int] = Field(default_factory=dict)
    actual_final_recent_run_ids: list[str] = Field(default_factory=list)
    actual_final_requirement_gaps: list[str] = Field(default_factory=list)


class RuntimeReplayBaseline(BaseModel):
    scenario_baselines: list[RuntimeReplayScenarioBaseline] = Field(default_factory=list)
    summary: str = ''


class RuntimeReplayGateScenarioResult(BaseModel):
    scenario_id: str
    manifest_passed: bool = False
    baseline_present: bool = False
    baseline_matched: bool = False
    passed: bool = False
    drift_messages: list[str] = Field(default_factory=list)
    current: RuntimeReplayScenarioReport
    baseline: Optional[RuntimeReplayScenarioBaseline] = None


class RuntimeReplayGateResult(BaseModel):
    fixture_root: str
    baseline_path: str
    report: RuntimeReplayReport
    baseline: RuntimeReplayBaseline
    scenario_results: list[RuntimeReplayGateScenarioResult] = Field(default_factory=list)
    extra_baseline_scenarios: list[str] = Field(default_factory=list)
    passed: bool = False
    summary: str = ''
