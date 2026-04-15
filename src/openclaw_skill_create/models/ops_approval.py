from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .request import SkillCreateRequestV6


ApprovalDecision = Literal['approved', 'deferred', 'rejected']
DecisionStatus = Literal['pending', 'approved_not_applied', 'applied']


class CreateSeedApprovalDecision(BaseModel):
    candidate_key: str
    decision: ApprovalDecision = 'deferred'
    notes: str = ''


class PriorPilotApprovalDecision(BaseModel):
    family: str
    decision: ApprovalDecision = 'deferred'
    notes: str = ''


class SourcePromotionApprovalDecision(BaseModel):
    repo_full_name: str
    decision: ApprovalDecision = 'deferred'
    notes: str = ''


class OpsApprovalState(BaseModel):
    create_seed: list[CreateSeedApprovalDecision] = Field(default_factory=list)
    prior_pilot: list[PriorPilotApprovalDecision] = Field(default_factory=list)
    source_promotion: list[SourcePromotionApprovalDecision] = Field(default_factory=list)


class CreateSeedHandoffArtifact(BaseModel):
    candidate_key: str
    suggested_title: str = ''
    suggested_description: str = ''
    representative_task_summaries: list[str] = Field(default_factory=list)
    requirement_gaps: list[str] = Field(default_factory=list)
    preview_request: SkillCreateRequestV6
    source_run_ids: list[str] = Field(default_factory=list)
    artifact_path: str = ''
    summary: str = ''


class CreateSeedManualRoundPack(BaseModel):
    candidate_key: str
    approval_decision: str = 'deferred'
    status: DecisionStatus = 'pending'
    handoff_artifact_path: str = ''
    suggested_title: str = ''
    suggested_description: str = ''
    representative_task_summaries: list[str] = Field(default_factory=list)
    requirement_gaps: list[str] = Field(default_factory=list)
    preview_request: SkillCreateRequestV6
    recommended_fixture_inputs: list[str] = Field(default_factory=list)
    launch_checklist: list[str] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class PriorPilotOverrideArtifact(BaseModel):
    family: str
    request_overrides: dict[str, object] = Field(default_factory=dict)
    generic_promotion_risk: int = 0
    artifact_path: str = ''
    summary: str = ''


class PriorPilotManualTrialPack(BaseModel):
    family: str
    approval_decision: str = 'deferred'
    status: DecisionStatus = 'pending'
    profile_artifact_path: str = ''
    request_overrides: dict[str, object] = Field(default_factory=dict)
    recommended_trial_tasks: list[str] = Field(default_factory=list)
    expected_safe_signals: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    verdict: str = 'hold'
    summary: str = ''
    markdown_summary: str = ''


class OpsApprovalApplyReport(BaseModel):
    approval_state: OpsApprovalState
    create_seed_handoffs: list[CreateSeedHandoffArtifact] = Field(default_factory=list)
    prior_pilot_profiles: list[PriorPilotOverrideArtifact] = Field(default_factory=list)
    applied_source_promotions: list[str] = Field(default_factory=list)
    skipped_source_promotions: list[str] = Field(default_factory=list)
    decision_status_summary: dict[str, int] = Field(default_factory=dict)
    summary: str = ''
    markdown_summary: str = ''
