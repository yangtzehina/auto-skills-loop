from __future__ import annotations

from pydantic import BaseModel, Field


class ExternalEvalCriterion(BaseModel):
    criterion_id: str
    label: str
    description: str = ""
    mode: str = "rubric"


class ExternalEvalProbe(BaseModel):
    probe_id: str
    skill_name: str
    task: str = ""
    probe_family: str = "residual"
    criteria: list[str] = Field(default_factory=list)
    expected_signals: list[str] = Field(default_factory=list)
    pass_expectation: str = "pass"


class ExternalEvalProfile(BaseModel):
    skill_name: str
    active_frontier_version: str = ""
    current_frontier_metrics: dict[str, float] = Field(default_factory=dict)
    residual_targets: dict[str, float] = Field(default_factory=dict)
    expected_signals: list[str] = Field(default_factory=list)
    probe_ids: list[str] = Field(default_factory=list)


class NormalizedEvalSuite(BaseModel):
    schema_version: str = "1.0.0"
    suite_version: str = ""
    profiles: list[ExternalEvalProfile] = Field(default_factory=list)
    probes: list[ExternalEvalProbe] = Field(default_factory=list)
    criteria: list[ExternalEvalCriterion] = Field(default_factory=list)
    current_frontier_metrics: dict[str, dict[str, float]] = Field(default_factory=dict)
    expected_signals: dict[str, list[str]] = Field(default_factory=dict)
    summary: list[str] = Field(default_factory=list)


class ExternalEvalExportBundle(BaseModel):
    schema_version: str = "1.0.0"
    normalized_eval_suite_path: str = ""
    promptfoo_config_path: str = ""
    promptfoo_cases_path: str = ""
    openai_evals_suite_path: str = ""
    generated_targets: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
    markdown_summary: str = ""
