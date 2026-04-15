from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .ops_approval import DecisionStatus


class PublicSourceCandidateConfig(BaseModel):
    repo_full_name: str
    ecosystem: str = 'codex'
    root_paths: list[str] = Field(default_factory=list)
    priority: int = 100
    verification_task: str = ''
    notes: str = ''


class PublicSourceVerificationResult(BaseModel):
    repo_full_name: str
    ecosystem: str = 'codex'
    root_paths: list[str] = Field(default_factory=list)
    priority: int = 100
    verification_task: str = ''
    notes: str = ''
    candidate_count: int = 0
    sample_skill_names: list[str] = Field(default_factory=list)
    overlap_assessment: str = 'none'
    structure_supported: bool = False
    verdict: str = 'manual_review'
    reason: str = ''
    smoke_required: bool = False
    selected_for_default: bool = False


class PublicSourceVerificationReport(BaseModel):
    candidates: list[PublicSourceVerificationResult] = Field(default_factory=list)
    accepted_repos: list[str] = Field(default_factory=list)
    rejected_repos: list[str] = Field(default_factory=list)
    manual_review_repos: list[str] = Field(default_factory=list)
    promoted_repos: list[str] = Field(default_factory=list)
    summary: str = ''


class PublicSourceCurationRoundReport(BaseModel):
    rehearsal_matched_count: int = 0
    rehearsal_drifted_count: int = 0
    rehearsal_invalid_fixture_count: int = 0
    rehearsal_passed: bool = False
    live_applied: bool = False
    live_report: PublicSourceVerificationReport | None = None
    promoted_repos: list[str] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''


class PublicSourcePromotionPack(BaseModel):
    repo_full_name: str
    promotion_candidate: bool = False
    requirements_satisfied: bool = False
    candidate_count: int = 0
    overlap_assessment: str = 'none'
    reason: str = ''
    required_ranking_regressions: list[str] = Field(default_factory=list)
    required_smoke: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    seed_patch_preview: dict[str, Any] = Field(default_factory=dict)
    verdict: str = 'hold'
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    summary: str = ''
    markdown_summary: str = ''
