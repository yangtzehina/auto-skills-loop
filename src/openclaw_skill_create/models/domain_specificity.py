from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDomainSpecificityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    domain_anchor_coverage: float = 1.0
    domain_anchors: list[str] = Field(default_factory=list)
    covered_domain_anchors: list[str] = Field(default_factory=list)
    missing_domain_anchors: list[str] = Field(default_factory=list)
    workflow_anchor_coverage: float = 1.0
    output_anchor_coverage: float = 1.0
    generic_template_ratio: float = 0.0
    cross_case_similarity: float = 0.0
    prompt_echo_in_body: float = 0.0
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
