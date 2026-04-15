from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeReplayReviewScenario(BaseModel):
    scenario_id: str
    status: str = 'passed'
    headline: str = ''
    issues: list[str] = Field(default_factory=list)


class RuntimeReplayReviewResult(BaseModel):
    fixture_root: str
    baseline_path: str
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    extra_baseline_scenarios: list[str] = Field(default_factory=list)
    scenario_reviews: list[RuntimeReplayReviewScenario] = Field(default_factory=list)
    passed: bool = False
    summary: str = ''
    markdown_summary: str = ''
