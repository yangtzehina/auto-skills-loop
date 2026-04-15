from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertWorkflowMove(BaseModel):
    name: str
    purpose: str = ""
    decision_probe: str = ""
    action: str = ""
    output_fragment: str = ""
    failure_signal: str = ""
    repair_move: str = ""
    must_include_terms: list[str] = Field(default_factory=list)
    avoid_terms: list[str] = Field(default_factory=list)


class ExpertSkillDNA(BaseModel):
    skill_name: str
    core_thesis: str = ""
    workflow_moves: list[ExpertWorkflowMove] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    decision_rules: list[str] = Field(default_factory=list)
    cut_rules: list[str] = Field(default_factory=list)
    failure_patterns: list[str] = Field(default_factory=list)
    repair_moves: list[str] = Field(default_factory=list)
    voice_rules: list[str] = Field(default_factory=list)
    numbered_spine: list[str] = Field(default_factory=list)


class DomainMovePlan(BaseModel):
    skill_name: str
    opening_frame: str = ""
    overview: str = ""
    when_to_use: list[str] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    dna: ExpertSkillDNA


class SkillMoveQualityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    expert_move_recall: float = 0.0
    expert_move_precision: float = 0.0
    decision_rule_coverage: float = 0.0
    cut_rule_coverage: float = 0.0
    output_field_semantics_coverage: float = 0.0
    failure_repair_coverage: float = 0.0
    numbered_workflow_spine_present: bool = False
    voice_rule_alignment: float = 0.0
    cross_case_move_overlap: float = 0.0
    detected_moves: list[str] = Field(default_factory=list)
    missing_workflow_moves: list[str] = Field(default_factory=list)
    missing_decision_rules: list[str] = Field(default_factory=list)
    missing_cut_rules: list[str] = Field(default_factory=list)
    missing_output_fields: list[str] = Field(default_factory=list)
    missing_failure_repairs: list[str] = Field(default_factory=list)
    missing_voice_rules: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
