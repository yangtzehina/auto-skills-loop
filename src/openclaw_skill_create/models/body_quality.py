from __future__ import annotations

from pydantic import BaseModel, Field


class SkillBodyQualityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    passed: bool = True
    body_lines: int = 0
    body_chars: int = 0
    heading_count: int = 0
    bullet_count: int = 0
    numbered_step_count: int = 0
    description_chars: int = 0
    description_body_ratio: float = 0.0
    prompt_echo_ratio: float = 0.0
    required_sections_present: list[str] = Field(default_factory=list)
    missing_required_sections: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class SkillSelfReviewReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    can_guide_agent: bool = True
    prompt_transformed: bool = True
    description_stuffing: bool = False
    missing_materials: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
