from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDomainExpertiseReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    domain_anchors: list[str] = Field(default_factory=list)
    action_anchor_coverage: float = 1.0
    judgment_anchor_coverage: float = 1.0
    output_anchor_coverage: float = 1.0
    pitfall_anchor_coverage: float = 1.0
    domain_move_coverage: float = 1.0
    prompt_phrase_echo_ratio: float = 0.0
    generic_expertise_shell_ratio: float = 0.0
    missing_action_anchors: list[str] = Field(default_factory=list)
    missing_judgment_anchors: list[str] = Field(default_factory=list)
    missing_output_anchors: list[str] = Field(default_factory=list)
    missing_pitfall_anchors: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
