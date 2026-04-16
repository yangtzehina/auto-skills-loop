from __future__ import annotations

from pydantic import BaseModel, Field


class SkillWorkflowFormReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    workflow_surface: str = "not_applicable"
    numbered_spine_count: int = 0
    imperative_move_recall: float = 0.0
    named_block_dominance_ratio: float = 0.0
    workflow_heading_alignment: float = 0.0
    output_block_separation: bool = True
    structural_block_count: int = 0
    workflow_numbered_moves: list[str] = Field(default_factory=list)
    workflow_named_blocks: list[str] = Field(default_factory=list)
    structural_blocks: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
