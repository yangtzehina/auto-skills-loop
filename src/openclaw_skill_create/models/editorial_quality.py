from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertEditorialProfile(BaseModel):
    skill_name: str
    decision_terms: list[str] = Field(default_factory=list)
    cut_terms: list[str] = Field(default_factory=list)
    output_terms: list[str] = Field(default_factory=list)
    failure_terms: list[str] = Field(default_factory=list)


class SkillEditorialQualityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    decision_pressure_score: float = 0.0
    action_density_score: float = 0.0
    redundancy_ratio: float = 0.0
    output_executability_score: float = 0.0
    failure_correction_score: float = 0.0
    compression_score: float = 0.0
    expert_cut_alignment: float = 0.0
    missing_decision_terms: list[str] = Field(default_factory=list)
    missing_cut_terms: list[str] = Field(default_factory=list)
    missing_output_terms: list[str] = Field(default_factory=list)
    missing_failure_terms: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
