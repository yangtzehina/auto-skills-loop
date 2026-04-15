from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeUsageSkillReport(BaseModel):
    skill_id: str
    skill_name: str = ''
    quality_score: float = 0.0
    usage_stats: dict[str, int] = Field(default_factory=dict)
    recent_run_ids: list[str] = Field(default_factory=list)
    recent_actions: list[str] = Field(default_factory=list)
    parent_skill_ids: list[str] = Field(default_factory=list)
    latest_recommended_action: str = 'no_change'
    lineage_version: int = 0
    latest_lineage_event: str = ''


class RuntimeUsageReport(BaseModel):
    applied: bool = False
    reason: str = ''
    db_path: str = ''
    skill_reports: list[RuntimeUsageSkillReport] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''
