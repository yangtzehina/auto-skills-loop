from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .operation import OperationContract
from .requirements import SkillRequirement


class MergeStrategy(BaseModel):
    mode: str = "preserve-and-merge"
    preserve_existing_files: bool = True
    replace_conflicting_sections: bool = True


class ContentBudget(BaseModel):
    skill_md_max_lines: int = 300
    reference_file_targets: dict[str, int] = Field(default_factory=dict)
    prefer_script_over_inline_code: bool = True


class PlannedFile(BaseModel):
    path: str
    purpose: str
    source_basis: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)


class PlanningSeed(BaseModel):
    suggested_skill_name: str = "generated-skill"
    suggested_skill_type: str = "mixed"
    suggested_skill_archetype: str = "guidance"
    candidate_files: list[PlannedFile] = Field(default_factory=list)
    requirements: list[SkillRequirement] = Field(default_factory=list)
    operation_contract: Optional[OperationContract] = None
    rationale: list[str] = Field(default_factory=list)
    generation_order: list[str] = Field(default_factory=list)


class SkillPlan(BaseModel):
    skill_name: str
    skill_type: str = "mixed"
    skill_archetype: str = "guidance"
    objective: str = ""
    why_this_shape: str = ""
    requirements: list[SkillRequirement] = Field(default_factory=list)
    operation_contract: Optional[OperationContract] = None
    files_to_create: list[PlannedFile] = Field(default_factory=list)
    files_to_update: list[PlannedFile] = Field(default_factory=list)
    files_to_keep: list[PlannedFile] = Field(default_factory=list)
    merge_strategy: MergeStrategy = Field(default_factory=MergeStrategy)
    content_budget: ContentBudget = Field(default_factory=ContentBudget)
    generation_order: list[str] = Field(default_factory=list)
