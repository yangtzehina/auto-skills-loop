from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertStyleProfile(BaseModel):
    skill_name: str
    opening_frame: str = ""
    workflow_label_set: list[str] = Field(default_factory=list)
    signature_moves: list[str] = Field(default_factory=list)
    section_rhythm: list[str] = Field(default_factory=list)
    forbidden_boilerplate: list[str] = Field(default_factory=list)


class SkillStyleDiversityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    shared_opening_phrase_ratio: float = 0.0
    shared_step_label_ratio: float = 0.0
    shared_boilerplate_sentence_ratio: float = 0.0
    fixed_renderer_phrase_count: int = 0
    profile_specific_label_coverage: float = 0.0
    domain_rhythm_score: float = 0.0
    workflow_labels: list[str] = Field(default_factory=list)
    missing_profile_labels: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
