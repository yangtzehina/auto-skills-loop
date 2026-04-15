from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .request import SkillCreateRequestV6
from .review import RepairSuggestion
from .runtime import EvolutionPlan


class RuntimeFollowupResult(BaseModel):
    action: str = 'no_change'
    selected_plan: Optional[EvolutionPlan] = None
    repair_suggestions: list[RepairSuggestion] = Field(default_factory=list)
    skill_create_request: Optional[SkillCreateRequestV6] = None
    noop: bool = False
    summary: str = ''
