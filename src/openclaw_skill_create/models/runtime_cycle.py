from __future__ import annotations

from pydantic import BaseModel

from .runtime import SkillRunAnalysis
from .runtime_followup import RuntimeFollowupResult


class RuntimeCycleResult(BaseModel):
    run_id: str
    task_id: str
    analysis: SkillRunAnalysis
    followup: RuntimeFollowupResult
    summary: str = ''
