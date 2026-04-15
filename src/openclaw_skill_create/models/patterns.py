from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExampleSnippet(BaseModel):
    case_id: str
    prompt_excerpt: str = ""
    outcome_excerpt: str = ""
    note: str = ""


class PatternApplicability(BaseModel):
    use_when: list[str] = Field(default_factory=list)
    avoid_when: list[str] = Field(default_factory=list)
    required_repo_signals: list[str] = Field(default_factory=list)
    negative_repo_signals: list[str] = Field(default_factory=list)
    request_modes: list[str] = Field(default_factory=list)
    priority: int = 50


class PatternEvidence(BaseModel):
    source_case_ids: list[str] = Field(default_factory=list)
    occurrence_count: int = 0
    success_rate: Optional[float] = None
    example_snippets: list[ExampleSnippet] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)


class PatternFileShape(BaseModel):
    required_files: list[str] = Field(default_factory=list)
    optional_files: list[str] = Field(default_factory=list)
    extraction_targets: list[str] = Field(default_factory=list)
    script_strategy: str = "prefer-deterministic-script-for-fragile-repetition"
    content_budget_hint: Optional[int] = None


class PatternContentHints(BaseModel):
    must_include: list[str] = Field(default_factory=list)
    should_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    references_to_read: list[str] = Field(default_factory=list)
    example_phrasings: list[str] = Field(default_factory=list)


class PatternDownstreamHints(BaseModel):
    planner_actions: list[str] = Field(default_factory=list)
    generator_actions: list[str] = Field(default_factory=list)
    validator_checks: list[str] = Field(default_factory=list)
    repair_recipes: list[str] = Field(default_factory=list)


class SkillPattern(BaseModel):
    pattern_id: str
    pattern_type: str
    status: str = "candidate"
    title: str
    summary: str = ""
    applicability: PatternApplicability = Field(default_factory=PatternApplicability)
    evidence: PatternEvidence = Field(default_factory=PatternEvidence)
    file_shape: Optional[PatternFileShape] = None
    content_hints: Optional[PatternContentHints] = None
    downstream_hints: PatternDownstreamHints = Field(default_factory=PatternDownstreamHints)
    confidence: float = 0.0
    support: int = 0
    tags: list[str] = Field(default_factory=list)
    supersedes_pattern_id: Optional[str] = None


class ExtractionScope(BaseModel):
    domain: str = "skill-create"
    target_kind: str = "AgentSkill"
    target_name: Optional[str] = None
    request_modes: list[str] = Field(default_factory=list)
    repo_paths: list[str] = Field(default_factory=list)
    existing_skill_path: Optional[str] = None


class ExtractionContext(BaseModel):
    run_id: str
    created_at: str
    extractor_version: str
    source_case_ids: list[str] = Field(default_factory=list)
    source_case_count: int = 0
    source_pattern_set_ids: list[str] = Field(default_factory=list)
    repo_snapshot_refs: list[str] = Field(default_factory=list)
    llm_model: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class PatternSummary(BaseModel):
    goals: list[str] = Field(default_factory=list)
    common_constraints: list[str] = Field(default_factory=list)
    dominant_skill_types: list[str] = Field(default_factory=list)
    recommended_defaults: dict[str, str] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)


class AggregatedHints(BaseModel):
    planner_defaults: list[str] = Field(default_factory=list)
    generator_defaults: list[str] = Field(default_factory=list)
    validator_defaults: list[str] = Field(default_factory=list)
    repair_defaults: list[str] = Field(default_factory=list)


class PatternQuality(BaseModel):
    confidence: str = "medium"
    coverage_score: Optional[float] = None
    consistency_score: Optional[float] = None
    review_status: str = "draft"
    reviewer_notes: list[str] = Field(default_factory=list)


class MemoryCandidate(BaseModel):
    title: str
    content: str
    category: str = "pattern"
    importance: str = "medium"


class PatternWriteback(BaseModel):
    should_persist_patterns: bool = False
    should_store_case_deltas: bool = False
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list)


class ExtractedSkillPatterns(BaseModel):
    schema_version: str = "1.0.0"
    pattern_set_id: str
    scope: ExtractionScope = Field(default_factory=ExtractionScope)
    extraction: ExtractionContext
    summary: PatternSummary = Field(default_factory=PatternSummary)
    patterns: list[SkillPattern] = Field(default_factory=list)
    aggregated_hints: AggregatedHints = Field(default_factory=AggregatedHints)
    quality: PatternQuality = Field(default_factory=PatternQuality)
    writeback: Optional[PatternWriteback] = None
    examples: list[ExampleSnippet] = Field(default_factory=list)
