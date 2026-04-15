from __future__ import annotations

from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    requirement_id: str
    statement: str
    evidence_paths: list[str] = Field(default_factory=list)
    source_kind: str = "repo"
    priority: int = 50
    satisfied_by: list[str] = Field(default_factory=list)
