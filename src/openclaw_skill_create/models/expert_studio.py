from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertTaskProbe(BaseModel):
    probe_id: str
    task: str = ""
    decision_terms: list[str] = Field(default_factory=list)
    cut_terms: list[str] = Field(default_factory=list)
    failure_terms: list[str] = Field(default_factory=list)
    repair_terms: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    anti_generic_terms: list[str] = Field(default_factory=list)


class ExpertRewritePair(BaseModel):
    skill_name: str
    weak_shell: str
    expert_revision: str
    revision_reason: str = ""


class ExpertFailureCase(BaseModel):
    skill_name: str
    failure_id: str
    bad_output: str
    failure_type: str
    why_it_fails: str = ""
    repair_direction: str = ""


class ExpertSkillCorpusEntry(BaseModel):
    skill_name: str
    domain_family: str = "methodology_guidance"
    task_brief: str = ""
    expert_skill_markdown: str = ""
    expert_notes: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    task_probes: list[ExpertTaskProbe] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    rewrite_pairs: list[ExpertRewritePair] = Field(default_factory=list)
    failure_cases: list[ExpertFailureCase] = Field(default_factory=list)


class ExecutionMove(BaseModel):
    step_id: str
    label: str
    purpose: str = ""
    decision: str = ""
    action: str = ""
    output: str = ""
    failure_signal: str = ""
    fix: str = ""
    must_include_terms: list[str] = Field(default_factory=list)
    avoid_terms: list[str] = Field(default_factory=list)


class AnalysisBlock(BaseModel):
    name: str
    when_used: str = ""
    questions: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)


class SkillProgramIR(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    workflow_surface: str = "execution_spine"
    opening_strategy: str = ""
    execution_spine: list[ExecutionMove] = Field(default_factory=list)
    analysis_blocks: list[AnalysisBlock] = Field(default_factory=list)
    decision_rules: list[str] = Field(default_factory=list)
    cut_rules: list[str] = Field(default_factory=list)
    failure_repairs: list[str] = Field(default_factory=list)
    output_schema: dict[str, list[str]] = Field(default_factory=dict)
    style_profile: list[str] = Field(default_factory=list)
    voice_constraints: list[str] = Field(default_factory=list)
    source_skill_name: str = ""
    source_confidence: str = "checked_in"
    summary: list[str] = Field(default_factory=list)


class SkillProgramAuthoringCandidate(BaseModel):
    skill_name: str
    task_brief: str = ""
    candidate_program: SkillProgramIR
    source_confidence: str = "needs_human_authoring"
    backlog_categories: list[str] = Field(default_factory=list)
    missing_expert_evidence: list[str] = Field(default_factory=list)
    stable_move_sequence: bool = False
    ready_for_review: bool = False
    confidence: str = "needs_human_authoring"
    summary: list[str] = Field(default_factory=list)


class SkillProgramAuthoringPack(BaseModel):
    schema_version: str = "1.0.0"
    candidates: list[SkillProgramAuthoringCandidate] = Field(default_factory=list)
    ready_for_review: list[str] = Field(default_factory=list)
    needs_human_authoring: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)
    backlog_counts: dict[str, int] = Field(default_factory=dict)
    candidate_program_count: int = 0
    summary: str = ""
    markdown_summary: str = ""


class ProgramCandidateReviewReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    review_status: str = "fail"
    candidate_confidence: str = "needs_human_authoring"
    workflow_surface: str = "unknown"
    execution_move_count: int = 0
    analysis_block_count: int = 0
    output_field_count: int = 0
    checklist: dict[str, bool] = Field(default_factory=dict)
    blocking_issues: list[str] = Field(default_factory=list)
    approved_for_release_gate: bool = False
    summary: list[str] = Field(default_factory=list)
    markdown_summary: str = ""


class ProgramCandidateReviewBatchReport(BaseModel):
    schema_version: str = "1.0.0"
    reports: list[ProgramCandidateReviewReport] = Field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    approved_for_release_gate_count: int = 0
    summary: str = ""
    markdown_summary: str = ""


class SkillProgramFidelityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    execution_move_recall: float = 0.0
    execution_move_order_alignment: float = 0.0
    decision_rule_fidelity: float = 0.0
    cut_rule_fidelity: float = 0.0
    failure_repair_fidelity: float = 0.0
    output_schema_fidelity: float = 0.0
    workflow_surface_fidelity: float = 0.0
    style_strategy_fidelity: float = 0.0
    missing_execution_moves: list[str] = Field(default_factory=list)
    missing_output_fields: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class SkillTaskOutcomeProbeResult(BaseModel):
    skill_name: str
    probe_id: str
    task: str = ""
    with_skill_score: float = 0.0
    baseline_score: float = 0.0
    expert_reference_score: float = 0.0
    decision_specificity: float = 0.0
    cut_strength: float = 0.0
    failure_detection: float = 0.0
    repair_usefulness: float = 0.0
    output_fillability: float = 0.0
    generic_advice_leakage: float = 0.0
    gap_issues: list[str] = Field(default_factory=list)
    status: str = "pass"


class SkillTaskOutcomeProfileResult(BaseModel):
    skill_name: str
    status: str = "pass"
    probe_results: list[SkillTaskOutcomeProbeResult] = Field(default_factory=list)
    probe_count: int = 0
    pass_count: int = 0
    with_skill_average: float = 0.0
    baseline_average: float = 0.0
    expert_reference_average: float = 0.0
    gap_issues: list[str] = Field(default_factory=list)


class SkillTaskOutcomeReport(BaseModel):
    schema_version: str = "1.0.0"
    status: str = "pass"
    profile_results: list[SkillTaskOutcomeProfileResult] = Field(default_factory=list)
    probe_count: int = 0
    task_outcome_gap_count: int = 0
    with_skill_average: float = 0.0
    baseline_average: float = 0.0
    expert_reference_average: float = 0.0
    summary: str = ""
    markdown_summary: str = ""
