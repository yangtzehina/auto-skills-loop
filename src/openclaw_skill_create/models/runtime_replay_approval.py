from __future__ import annotations

from pydantic import BaseModel, Field

from .runtime_replay_change import RuntimeReplayChangePack


class RuntimeReplayApprovalScenario(BaseModel):
    scenario_id: str
    approval_state: str = 'unchanged'
    headline: str = ''
    issues: list[str] = Field(default_factory=list)


class RuntimeReplayApprovalPack(BaseModel):
    fixture_root: str
    baseline_path: str
    change_pack: RuntimeReplayChangePack
    current_recommended_action: str = 'keep_baseline'
    approval_decision: str = 'reject_refresh'
    allow_baseline_refresh: bool = False
    suggested_command: str = ''
    pending_approval_summary: str = ''
    affected_scenarios: list[str] = Field(default_factory=list)
    drifted_scenarios: list[str] = Field(default_factory=list)
    blocking_scenarios: list[str] = Field(default_factory=list)
    scenario_approvals: list[RuntimeReplayApprovalScenario] = Field(default_factory=list)
    passed: bool = False
    summary: str = ''
    markdown_summary: str = ''
