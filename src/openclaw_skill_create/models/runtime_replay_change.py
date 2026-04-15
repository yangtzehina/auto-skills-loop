from __future__ import annotations

from pydantic import BaseModel, Field

from .runtime_replay_review import RuntimeReplayReviewResult


class RuntimeReplayChangeScenario(BaseModel):
    scenario_id: str
    classification: str = 'passed'
    headline: str = ''
    issues: list[str] = Field(default_factory=list)


class RuntimeReplayChangePack(BaseModel):
    fixture_root: str
    baseline_path: str
    review: RuntimeReplayReviewResult
    recommended_action: str = 'keep_baseline'
    decision_reason: str = ''
    write_baseline_recommended: bool = False
    baseline_refresh_command: str = ''
    affected_scenarios: list[str] = Field(default_factory=list)
    drifted_scenarios: list[str] = Field(default_factory=list)
    blocking_scenarios: list[str] = Field(default_factory=list)
    scenario_changes: list[RuntimeReplayChangeScenario] = Field(default_factory=list)
    passed: bool = False
    summary: str = ''
    markdown_summary: str = ''
