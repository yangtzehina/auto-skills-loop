from __future__ import annotations

from .comparison import SkillCreateComparisonReport
from .operation_backed_ops import OperationBackedBacklogReport
from .public_source_verification import PublicSourcePromotionPack
from .runtime_governance import RuntimeOpsDecisionPack, RuntimePriorPilotExerciseReport
from pydantic import BaseModel, Field


class VerifyCommandResult(BaseModel):
    label: str
    command: list[str] = Field(default_factory=list)
    exit_code: int = 0
    stdout: str = ''
    stderr: str = ''


class VerifyReport(BaseModel):
    mode: str
    include_live_curation: bool = False
    commands: list[VerifyCommandResult] = Field(default_factory=list)
    decision_statuses: dict[str, list[str]] = Field(default_factory=dict)
    decision_status_summary: dict[str, int] = Field(default_factory=dict)
    operation_backed_status_counts: dict[str, int] = Field(default_factory=dict)
    operation_backed_actionable_count: int = 0
    operation_backed_hold_count: int = 0
    methodology_body_quality_status: str = 'pass'
    self_review_fail_count: int = 0
    domain_specificity_status: str = 'pass'
    domain_specificity_fail_count: int = 0
    generic_shell_gap_count: int = 0
    domain_expertise_status: str = 'pass'
    domain_expertise_fail_count: int = 0
    domain_expertise_warn_count: int = 0
    expert_structure_status: str = 'pass'
    expert_structure_fail_count: int = 0
    expert_structure_warn_count: int = 0
    expert_structure_gap_count: int = 0
    depth_quality_status: str = 'pass'
    depth_quality_fail_count: int = 0
    depth_quality_warn_count: int = 0
    depth_quality_gap_count: int = 0
    editorial_quality_status: str = 'pass'
    editorial_quality_fail_count: int = 0
    editorial_quality_warn_count: int = 0
    editorial_gap_count: int = 0
    style_diversity_status: str = 'pass'
    style_diversity_fail_count: int = 0
    style_diversity_warn_count: int = 0
    style_gap_count: int = 0
    move_quality_status: str = 'pass'
    move_quality_fail_count: int = 0
    move_quality_warn_count: int = 0
    move_quality_gap_count: int = 0
    dna_authoring_status: str = 'pass'
    candidate_dna_count: int = 0
    usefulness_eval_status: str = 'pass'
    usefulness_gap_count: int = 0
    pairwise_similarity_gap_count: int = 0
    hermes_comparison_gap_count: int = 0
    skill_create_comparison_report: SkillCreateComparisonReport | None = None
    overall_status: str = 'pass'
    summary: str = ''
    markdown_summary: str = ''


class OpsRoundbookReport(BaseModel):
    verification_status: str = 'pass'
    verify_report: VerifyReport
    runtime_ops_decision_pack: RuntimeOpsDecisionPack
    prior_pilot_exercise: RuntimePriorPilotExerciseReport
    source_promotion_pack: PublicSourcePromotionPack
    pending_create_seed_decisions: list[str] = Field(default_factory=list)
    pending_prior_pilot_decisions: list[str] = Field(default_factory=list)
    pending_source_promotion_decisions: list[str] = Field(default_factory=list)
    approved_not_applied_create_seed_decisions: list[str] = Field(default_factory=list)
    approved_not_applied_prior_pilot_decisions: list[str] = Field(default_factory=list)
    approved_not_applied_source_promotion_decisions: list[str] = Field(default_factory=list)
    applied_create_seed_decisions: list[str] = Field(default_factory=list)
    applied_prior_pilot_decisions: list[str] = Field(default_factory=list)
    applied_source_promotion_decisions: list[str] = Field(default_factory=list)
    next_create_seed_candidate: str = ''
    next_prior_family_on_hold: str = ''
    next_source_round_status: str = ''
    operation_backed_backlog_report: OperationBackedBacklogReport | None = None
    operation_backed_patch_current_candidates: list[str] = Field(default_factory=list)
    operation_backed_derive_child_candidates: list[str] = Field(default_factory=list)
    operation_backed_hold_candidates: list[str] = Field(default_factory=list)
    methodology_body_quality_status: str = 'pass'
    self_review_fail_count: int = 0
    domain_specificity_status: str = 'pass'
    domain_specificity_fail_count: int = 0
    generic_shell_gap_count: int = 0
    domain_expertise_status: str = 'pass'
    domain_expertise_fail_count: int = 0
    domain_expertise_warn_count: int = 0
    expert_structure_status: str = 'pass'
    expert_structure_fail_count: int = 0
    expert_structure_warn_count: int = 0
    expert_structure_gap_count: int = 0
    depth_quality_status: str = 'pass'
    depth_quality_fail_count: int = 0
    depth_quality_warn_count: int = 0
    depth_quality_gap_count: int = 0
    editorial_quality_status: str = 'pass'
    editorial_quality_fail_count: int = 0
    editorial_quality_warn_count: int = 0
    editorial_gap_count: int = 0
    style_diversity_status: str = 'pass'
    style_diversity_fail_count: int = 0
    style_diversity_warn_count: int = 0
    style_gap_count: int = 0
    move_quality_status: str = 'pass'
    move_quality_fail_count: int = 0
    move_quality_warn_count: int = 0
    move_quality_gap_count: int = 0
    dna_authoring_status: str = 'pass'
    candidate_dna_count: int = 0
    usefulness_eval_status: str = 'pass'
    usefulness_gap_count: int = 0
    pairwise_similarity_gap_count: int = 0
    hermes_comparison_gap_count: int = 0
    overall_readiness: str = 'ready'
    summary: str = ''
    markdown_summary: str = ''
