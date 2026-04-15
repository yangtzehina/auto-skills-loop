from __future__ import annotations

from pydantic import BaseModel, Field

from .ops_approval import DecisionStatus
from .request import SkillCreateRequestV6


class CreateSeedLaunchReport(BaseModel):
    candidate_key: str
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    handoff_artifact_path: str = ''
    artifact_exists: bool = False
    launch_ready: bool = False
    preview_request: SkillCreateRequestV6
    recommended_fixture_inputs: list[str] = Field(default_factory=list)
    launch_checklist: list[str] = Field(default_factory=list)
    suggested_output_root: str = ''
    next_step_hint: str = ''
    summary: str = ''
    markdown_summary: str = ''


class CreateSeedPackageReviewReport(BaseModel):
    candidate_key: str
    run_summary_path: str = ''
    output_root: str = ''
    review_path: str = ''
    report_path: str = ''
    review_exists: bool = False
    report_exists: bool = False
    fully_correct: bool = False
    overall_score: float = 0.0
    confidence: float = 0.0
    requirements_satisfied: int = 0
    requirements_total: int = 0
    repair_suggestions_count: int = 0
    verdict: str = 'missing'
    summary: str = ''
    markdown_summary: str = ''


class PriorPilotTrialObservationReport(BaseModel):
    family: str
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    profile_artifact_path: str = ''
    artifact_exists: bool = False
    request_overrides: dict[str, object] = Field(default_factory=dict)
    recommended_trial_tasks: list[str] = Field(default_factory=list)
    expected_safe_signals: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    scenarios_run: list[str] = Field(default_factory=list)
    matched_count: int = 0
    drifted_count: int = 0
    invalid_fixture_count: int = 0
    top_1_changes: int = 0
    generic_promotion_risk: int = 0
    trial_ready: bool = False
    next_step_hint: str = ''
    summary: str = ''
    markdown_summary: str = ''


class PriorPilotRetrievalTrialReport(BaseModel):
    family: str
    repo_path: str = ''
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    selected_files_count: int = 0
    baseline_top_candidate: str = ''
    pilot_top_candidate: str = ''
    baseline_prior_applied: bool = False
    pilot_prior_applied: bool = False
    generic_promotion_risk: int = 0
    eligible_families: list[str] = Field(default_factory=list)
    request_overrides: dict[str, object] = Field(default_factory=dict)
    verdict: str = 'hold'
    summary: str = ''
    markdown_summary: str = ''


class SourcePromotionPostApplyReport(BaseModel):
    repo_full_name: str
    approval_decision: str = 'deferred'
    decision_status: DecisionStatus = 'pending'
    collections_applied: bool = False
    requirements_satisfied: bool = False
    rehearsal_passed: bool = False
    live_applied: bool = False
    promoted_repos: list[str] = Field(default_factory=list)
    required_ranking_regressions: list[str] = Field(default_factory=list)
    required_smoke: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    scenarios_run: list[str] = Field(default_factory=list)
    matched_count: int = 0
    drifted_count: int = 0
    invalid_fixture_count: int = 0
    monitor_status: str = 'not_applied'
    next_step_hint: str = ''
    summary: str = ''
    markdown_summary: str = ''


class OpsRefillReport(BaseModel):
    next_create_seed_candidate: str = ''
    next_prior_family_on_hold: str = ''
    next_source_round_status: str = ''
    create_seed_candidates_considered: list[str] = Field(default_factory=list)
    prior_families_on_hold: list[str] = Field(default_factory=list)
    applied_create_seed_candidates: list[str] = Field(default_factory=list)
    applied_prior_families: list[str] = Field(default_factory=list)
    applied_source_promotions: list[str] = Field(default_factory=list)
    source_promoted_repos: list[str] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''
