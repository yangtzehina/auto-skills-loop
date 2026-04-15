from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SkillDependency(BaseModel):
    kind: str = "tool"
    value: str
    description: str = ""


class SkillProvenance(BaseModel):
    source_type: str = "community"
    ecosystem: str = "codex"
    repo_full_name: str
    ref: str = "main"
    skill_path: str
    skill_url: str
    source_license: Optional[str] = None
    source_attribution: Optional[str] = None


class SkillSourceCandidate(BaseModel):
    candidate_id: str
    name: str
    description: str
    trigger_phrases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    dependencies: list[SkillDependency] = Field(default_factory=list)
    provenance: SkillProvenance
    score: float = 0.0
    base_score: float = 0.0
    runtime_prior_delta: float = 0.0
    adjusted_score: float = 0.0
    matched_signals: list[str] = Field(default_factory=list)


class SkillBlueprintArtifact(BaseModel):
    path: str
    artifact_type: str
    purpose: str = ""
    required: bool = True
    source_url: Optional[str] = None


class SkillBlueprintSection(BaseModel):
    heading: str
    summary: str = ""


class SkillInterfaceMetadata(BaseModel):
    display_name: Optional[str] = None
    short_description: Optional[str] = None
    default_prompt: Optional[str] = None


class SkillBlueprint(BaseModel):
    blueprint_id: str
    name: str
    description: str
    trigger_summary: str = ""
    workflow_summary: list[str] = Field(default_factory=list)
    sections: list[SkillBlueprintSection] = Field(default_factory=list)
    artifacts: list[SkillBlueprintArtifact] = Field(default_factory=list)
    dependencies: list[SkillDependency] = Field(default_factory=list)
    interface: SkillInterfaceMetadata = Field(default_factory=SkillInterfaceMetadata)
    tags: list[str] = Field(default_factory=list)
    provenance: SkillProvenance
    notes: list[str] = Field(default_factory=list)


class SkillReuseDecision(BaseModel):
    mode: str = "generate_fresh"
    selected_candidate_ids: list[str] = Field(default_factory=list)
    selected_blueprint_ids: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    coverage_score: float = 0.0
    gaps: list[str] = Field(default_factory=list)
