from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertSkillProfile(BaseModel):
    skill_name: str
    required_headings: list[str] = Field(default_factory=list)
    domain_actions: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    pitfall_clusters: list[str] = Field(default_factory=list)
    quality_checks: list[str] = Field(default_factory=list)


class SkillExpertStructureReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    expert_heading_recall: float = 0.0
    expert_action_cluster_recall: float = 0.0
    expert_output_field_recall: float = 0.0
    expert_pitfall_cluster_recall: float = 0.0
    expert_quality_check_recall: float = 0.0
    generated_vs_generated_heading_overlap: float = 0.0
    generated_vs_generated_line_jaccard: float = 0.0
    generic_skeleton_ratio: float = 0.0
    missing_expert_headings: list[str] = Field(default_factory=list)
    missing_action_clusters: list[str] = Field(default_factory=list)
    missing_output_fields: list[str] = Field(default_factory=list)
    missing_pitfall_clusters: list[str] = Field(default_factory=list)
    missing_quality_checks: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
