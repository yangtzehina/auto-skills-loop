from __future__ import annotations

from pydantic import BaseModel, Field

from .requirements import SkillRequirement


class CandidateResources(BaseModel):
    references: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)


class RepoFinding(BaseModel):
    repo_path: str
    summary: str = ""
    detected_stack: list[str] = Field(default_factory=list)
    entrypoints: list[dict] = Field(default_factory=list)
    scripts: list[dict] = Field(default_factory=list)
    docs: list[dict] = Field(default_factory=list)
    configs: list[dict] = Field(default_factory=list)
    workflows: list[dict] = Field(default_factory=list)
    triggers: list[dict] = Field(default_factory=list)
    candidate_resources: CandidateResources = Field(default_factory=CandidateResources)
    risks: list[str] = Field(default_factory=list)


class RepoFindings(BaseModel):
    repos: list[RepoFinding] = Field(default_factory=list)
    cross_repo_signals: list[dict] = Field(default_factory=list)
    requirements: list[SkillRequirement] = Field(default_factory=list)
    overall_recommendation: str = ""
