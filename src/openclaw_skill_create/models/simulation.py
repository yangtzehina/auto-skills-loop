from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SimulationScenarioResult(BaseModel):
    family: str
    scenario_id: str
    status: str = 'matched'
    expected_projection: dict[str, Any] = Field(default_factory=dict)
    actual_projection: dict[str, Any] = Field(default_factory=dict)
    diff_summary: list[str] = Field(default_factory=list)
    error_kind: str = ''
    summary: str = ''


class SimulationSuiteReport(BaseModel):
    mode: str
    fixture_root: str
    scenario_results: list[SimulationScenarioResult] = Field(default_factory=list)
    matched_count: int = 0
    drifted_count: int = 0
    invalid_fixture_count: int = 0
    summary: str = ''
    markdown_summary: str = ''
