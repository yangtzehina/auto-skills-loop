from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertDepthProfile(BaseModel):
    skill_name: str
    depth_terms: list[str] = Field(default_factory=list)
    decision_probes: list[str] = Field(default_factory=list)
    output_guidance_terms: list[str] = Field(default_factory=list)
    boundary_rules: list[str] = Field(default_factory=list)
    failure_patterns: list[str] = Field(default_factory=list)
    quality_rubric_terms: list[str] = Field(default_factory=list)


class SkillDepthQualityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    section_depth_score: float = 0.0
    expert_depth_recall: float = 0.0
    decision_probe_count: int = 0
    worked_example_count: int = 0
    failure_pattern_density: int = 0
    output_field_guidance_coverage: float = 0.0
    boundary_rule_coverage: float = 0.0
    thin_section_count: int = 0
    missing_depth_terms: list[str] = Field(default_factory=list)
    missing_output_guidance_terms: list[str] = Field(default_factory=list)
    missing_boundary_rules: list[str] = Field(default_factory=list)
    missing_failure_patterns: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
