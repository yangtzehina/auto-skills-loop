from __future__ import annotations

from pydantic import BaseModel, Field

ALLOWED_REPAIR_SCOPES = {'description_only', 'body_patch', 'derive_child'}


def _normalize_repair_scope(value: str) -> str:
    normalized = str(value or 'body_patch').strip().lower()
    if normalized in ALLOWED_REPAIR_SCOPES:
        return normalized
    return 'body_patch'


class RequirementResult(BaseModel):
    requirement_id: str
    statement: str
    satisfied: bool = False
    evidence_paths: list[str] = Field(default_factory=list)
    satisfied_by: list[str] = Field(default_factory=list)
    rationale: str = ""
    missing_artifacts: list[str] = Field(default_factory=list)


class RepairSuggestion(BaseModel):
    issue_type: str
    instruction: str
    target_paths: list[str] = Field(default_factory=list)
    priority: int = 50
    repair_scope: str = 'body_patch'

    def model_post_init(self, __context) -> None:
        self.issue_type = str(self.issue_type or '').strip()
        self.instruction = str(self.instruction or '').strip()
        self.target_paths = [str(path or '').strip() for path in list(self.target_paths or []) if str(path or '').strip()]
        self.priority = int(self.priority or 0)
        self.repair_scope = _normalize_repair_scope(self.repair_scope)


class SkillQualityReview(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    skill_archetype: str = "guidance"
    fully_correct: bool = False
    requirement_results: list[RequirementResult] = Field(default_factory=list)
    repair_suggestions: list[RepairSuggestion] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    operation_count: int = 0
    operation_groups: list[str] = Field(default_factory=list)
    operation_validation_status: str = "not_applicable"
    coverage_gap_summary: list[str] = Field(default_factory=list)
    recommended_followup: str = "no_change"
    body_quality_status: str = "not_applicable"
    body_quality_issues: list[str] = Field(default_factory=list)
    self_review_status: str = "not_applicable"
    domain_specificity_status: str = "not_applicable"
    domain_specificity_issues: list[str] = Field(default_factory=list)
    domain_expertise_status: str = "not_applicable"
    domain_expertise_issues: list[str] = Field(default_factory=list)
    expert_structure_status: str = "not_applicable"
    expert_structure_issues: list[str] = Field(default_factory=list)
    depth_quality_status: str = "not_applicable"
    depth_quality_issues: list[str] = Field(default_factory=list)
    editorial_quality_status: str = "not_applicable"
    editorial_quality_issues: list[str] = Field(default_factory=list)
    style_diversity_status: str = "not_applicable"
    style_diversity_issues: list[str] = Field(default_factory=list)
    move_quality_status: str = "not_applicable"
    move_quality_issues: list[str] = Field(default_factory=list)
    workflow_form_status: str = "not_applicable"
    workflow_form_issues: list[str] = Field(default_factory=list)
    editorial_force_status: str = "not_applicable"
    editorial_force_issues: list[str] = Field(default_factory=list)
    pairwise_promotion_status: str = "not_applicable"
    pairwise_promotion_reason: str = ""
    program_fidelity_status: str = "not_applicable"
    program_fidelity_issues: list[str] = Field(default_factory=list)
    task_outcome_status: str = "not_applicable"
    task_outcome_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
