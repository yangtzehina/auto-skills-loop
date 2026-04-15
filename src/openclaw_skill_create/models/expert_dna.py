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


class CandidateExpertSkillDNA(BaseModel):
    skill_name: str
    task_brief: str = ""
    candidate_dna: ExpertSkillDNA
    extracted_workflow_moves: list[str] = Field(default_factory=list)
    output_field_map: dict[str, str] = Field(default_factory=dict)
    decision_rules: list[str] = Field(default_factory=list)
    cut_rules: list[str] = Field(default_factory=list)
    failure_repair_rules: list[str] = Field(default_factory=list)
    evidence_sources: list[str] = Field(default_factory=list)
    missing_expert_evidence: list[str] = Field(default_factory=list)
    stable_move_sequence: bool = False
    needs_human_golden: bool = True
    confidence: str = "needs_human_authoring"
    checked_in_move_recall: float = 0.0
    summary: list[str] = Field(default_factory=list)


class ExpertDNAAuthoringPack(BaseModel):
    schema_version: str = "1.0.0"
    candidates: list[CandidateExpertSkillDNA] = Field(default_factory=list)
    ready_for_review: list[str] = Field(default_factory=list)
    needs_human_authoring: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)
    candidate_dna_count: int = 0
    summary: str = ""
    markdown_summary: str = ""


class ExpertDNAReviewReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    review_status: str = "fail"
    candidate_confidence: str = "needs_human_authoring"
    workflow_move_count: int = 0
    output_field_count: int = 0
    decision_rule_count: int = 0
    failure_repair_count: int = 0
    checklist: dict[str, bool] = Field(default_factory=dict)
    blocking_issues: list[str] = Field(default_factory=list)
    approved_for_release_gate: bool = False
    summary: list[str] = Field(default_factory=list)
    markdown_summary: str = ""


class ExpertDNAReviewBatchReport(BaseModel):
    schema_version: str = "1.0.0"
    reports: list[ExpertDNAReviewReport] = Field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    approved_for_release_gate_count: int = 0
    summary: str = ""
    markdown_summary: str = ""


class SkillUsefulnessProbeResult(BaseModel):
    skill_name: str
    probe_id: str
    task: str = ""
    with_skill_score: float = 0.0
    baseline_score: float = 0.0
    expert_reference_score: float = 0.0
    decision_specificity: float = 0.0
    output_field_completeness: float = 0.0
    cut_failure_detection: float = 0.0
    repair_usefulness: float = 0.0
    generic_advice_leakage: float = 0.0
    gap_issues: list[str] = Field(default_factory=list)
    status: str = "pass"


class SkillUsefulnessEvalReport(BaseModel):
    schema_version: str = "1.0.0"
    status: str = "pass"
    probe_results: list[SkillUsefulnessProbeResult] = Field(default_factory=list)
    probe_count: int = 0
    usefulness_gap_count: int = 0
    with_skill_average: float = 0.0
    baseline_average: float = 0.0
    expert_reference_average: float = 0.0
    summary: str = ""
    markdown_summary: str = ""
