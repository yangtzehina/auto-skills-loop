from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .ops_approval import DecisionStatus
from .request import SkillCreateRequestV6
from .public_source_verification import PublicSourcePromotionPack
from .runtime import RuntimeCreateCandidate, RuntimeSemanticSummary, SkillRunRecord
from .runtime_handoff import RuntimeHandoffEnvelope, RuntimeHandoffNormalized
from .runtime_hook import RuntimeHookResult
from .runtime_usage import RuntimeUsageSkillReport


class RuntimeGovernanceBundle(BaseModel):
    run_record: SkillRunRecord
    runtime_hook: RuntimeHookResult
    usage_snapshots: list[RuntimeUsageSkillReport] = Field(default_factory=list)
    create_candidates: list[RuntimeCreateCandidate] = Field(default_factory=list)
    semantic_summary: RuntimeSemanticSummary | None = None
    summary: str = ''


class RuntimeGovernanceIntakeResult(BaseModel):
    handoff: RuntimeHandoffEnvelope
    normalized: RuntimeHandoffNormalized
    runtime_hook: RuntimeHookResult
    governance_bundle: RuntimeGovernanceBundle
    semantic_summary: RuntimeSemanticSummary | None = None
    summary: str = ''


class RuntimeGovernanceBatchSkillReport(BaseModel):
    skill_id: str
    skill_name: str = ''
    skill_archetype: str = 'guidance'
    quality_score: float = 0.0
    recent_actions: list[str] = Field(default_factory=list)
    recent_run_ids: list[str] = Field(default_factory=list)
    latest_recommended_action: str = 'no_change'
    operation_validation_status: str = ''
    coverage_gap_summary: list[str] = Field(default_factory=list)
    parent_skill_ids: list[str] = Field(default_factory=list)
    lineage_version: int = 0
    latest_lineage_event: str = ''


class RuntimeGovernanceBatchReport(BaseModel):
    runs_processed: int = 0
    per_run: list[RuntimeGovernanceBundle] = Field(default_factory=list)
    per_skill: list[RuntimeGovernanceBatchSkillReport] = Field(default_factory=list)
    create_candidates: list[RuntimeCreateCandidate] = Field(default_factory=list)
    semantic_summaries: list[RuntimeSemanticSummary] = Field(default_factory=list)
    action_counts: dict[str, int] = Field(default_factory=dict)
    approval_counts: dict[str, int] = Field(default_factory=dict)
    judge_applied_count: int = 0
    summary: str = ''
    markdown_summary: str = ''


class RuntimeCreateQueueEntry(BaseModel):
    candidate_key: str
    task_summaries: list[str] = Field(default_factory=list)
    requirement_gaps: list[str] = Field(default_factory=list)
    source_run_ids: list[str] = Field(default_factory=list)
    occurrence_count: int = 0
    latest_confidence: float = 0.0
    recommended_status: str = 'defer'


class RuntimeCreateQueueReport(BaseModel):
    runs_processed: int = 0
    entries: list[RuntimeCreateQueueEntry] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class RuntimeCreateReviewEntry(BaseModel):
    candidate_key: str
    candidate_brief: str = ''
    representative_task_summaries: list[str] = Field(default_factory=list)
    distilled_requirement_gaps: list[str] = Field(default_factory=list)
    suggested_title: str = ''
    suggested_description: str = ''
    recommended_next_action: str = 'defer'
    occurrence_count: int = 0
    source_run_ids: list[str] = Field(default_factory=list)


class RuntimeCreateReviewPack(BaseModel):
    runs_processed: int = 0
    entries: list[RuntimeCreateReviewEntry] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class RuntimeCreateSeedProposal(BaseModel):
    candidate_key: str
    suggested_title: str = ''
    suggested_description: str = ''
    representative_task_summaries: list[str] = Field(default_factory=list)
    distilled_requirement_gaps: list[str] = Field(default_factory=list)
    preview_request: SkillCreateRequestV6
    recommended_decision: str = 'defer'
    source_run_ids: list[str] = Field(default_factory=list)
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    handoff_artifact_path: str = ''


class RuntimeCreateSeedProposalPack(BaseModel):
    runs_processed: int = 0
    proposals: list[RuntimeCreateSeedProposal] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class RuntimeOpsDecisionPack(BaseModel):
    create_seed_candidates: list[RuntimeCreateSeedProposal] = Field(default_factory=list)
    prior_pilot_candidates: list[RuntimePriorPilotProfile] = Field(default_factory=list)
    source_promotion_candidates: list[PublicSourcePromotionPack] = Field(default_factory=list)
    decisions_pending: list[str] = Field(default_factory=list)
    approved_not_applied: list[str] = Field(default_factory=list)
    applied: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class RuntimePriorEligibleSkill(BaseModel):
    skill_id: str = ''
    skill_name: str = ''
    quality_score: float = 0.0
    run_count: int = 0
    runtime_prior_delta: float = 0.0
    eligible: bool = False


class RuntimePriorTaskImpact(BaseModel):
    task: str
    baseline_top_candidate: str = ''
    prior_top_candidate: str = ''
    changed_top_1: bool = False
    generic_promoted: bool = False
    prior_applied: bool = False
    summary: str = ''


class RuntimePriorGateReport(BaseModel):
    eligible_skills: list[RuntimePriorEligibleSkill] = Field(default_factory=list)
    task_impacts: list[RuntimePriorTaskImpact] = Field(default_factory=list)
    eligibility_summary: dict[str, int] = Field(default_factory=dict)
    ranking_impact_summary: dict[str, int] = Field(default_factory=dict)
    summary: str = ''
    markdown_summary: str = ''


class RuntimePriorRolloutFamilyReport(BaseModel):
    family: str
    eligible: bool = False
    sample_count: int = 0
    quality_band: str = 'low'
    generic_promotion_risk: int = 0
    recommended_rollout_status: str = 'hold'
    recommended_scope: list[str] = Field(default_factory=list)
    runtime_prior_delta: float = 0.0


class RuntimePriorRolloutReport(BaseModel):
    families: list[RuntimePriorRolloutFamilyReport] = Field(default_factory=list)
    recommended_scope: list[str] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class RuntimePriorPilotProfile(BaseModel):
    family: str
    recommended_status: str = 'hold'
    allowed_families: list[str] = Field(default_factory=list)
    request_overrides_preview: dict[str, Any] = Field(default_factory=dict)
    generic_promotion_risk: int = 0
    sample_count: int = 0
    quality_band: str = 'low'
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    profile_artifact_path: str = ''


class RuntimePriorPilotReport(BaseModel):
    profiles: list[RuntimePriorPilotProfile] = Field(default_factory=list)
    allowed_families: list[str] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class RuntimePriorPilotExerciseReport(BaseModel):
    family: str
    request_overrides: dict[str, Any] = Field(default_factory=dict)
    scenarios_run: list[str] = Field(default_factory=list)
    top_1_changes: int = 0
    generic_promotion_risk: int = 0
    matched_count: int = 0
    drifted_count: int = 0
    invalid_fixture_count: int = 0
    verdict: str = 'hold'
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    profile_artifact_path: str = ''
    summary: str = ''
    markdown_summary: str = ''
