from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeReplayJudgeScenario(BaseModel):
    scenario_id: str
    narrative_explanation: str = ''
    confidence_adjustment: float = 0.0
    review_hints: list[str] = Field(default_factory=list)


class RuntimeReplayJudgePack(BaseModel):
    enabled: bool = False
    applied: bool = False
    model: str = ''
    reason: str = ''
    scenario_judgments: list[RuntimeReplayJudgeScenario] = Field(default_factory=list)
    summary: str = ''
