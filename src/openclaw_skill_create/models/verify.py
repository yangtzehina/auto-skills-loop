from __future__ import annotations

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
    overall_readiness: str = 'ready'
    summary: str = ''
    markdown_summary: str = ''
