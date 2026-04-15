from __future__ import annotations

from pydantic import BaseModel, Field


class TriggerEvalCase(BaseModel):
    case_id: str
    query: str
    expected_trigger: bool
    rationale: str = ""


class TriggerEvalSpec(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    description: str = ""
    cases: list[TriggerEvalCase] = Field(default_factory=list)


class OutputEvalCase(BaseModel):
    case_id: str
    query: str
    baseline_variant: str = "without_skill"
    expected_behavior: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)


class OutputEvalSpec(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    baseline_variants: list[str] = Field(default_factory=lambda: ["with_skill", "without_skill"])
    cases: list[OutputEvalCase] = Field(default_factory=list)


class BenchmarkDimension(BaseModel):
    name: str
    description: str


class BenchmarkEvalSpec(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    comparison_target: str = "without_skill"
    dimensions: list[BenchmarkDimension] = Field(default_factory=list)


class TriggerEvalCaseResult(BaseModel):
    case_id: str
    expected_trigger: bool
    predicted_trigger: bool
    score: float = 0.0
    passed: bool
    matched_terms: list[str] = Field(default_factory=list)


class OutputEvalCaseResult(BaseModel):
    case_id: str
    baseline_variant: str = "without_skill"
    score: float = 0.0
    passed: bool
    satisfied_behavior: list[str] = Field(default_factory=list)
    missing_behavior: list[str] = Field(default_factory=list)
    satisfied_criteria: list[str] = Field(default_factory=list)
    missing_criteria: list[str] = Field(default_factory=list)


class BenchmarkDimensionResult(BaseModel):
    name: str
    score: float = 0.0
    rationale: str = ""


class EvaluationRunReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    trigger_results: list[TriggerEvalCaseResult] = Field(default_factory=list)
    output_results: list[OutputEvalCaseResult] = Field(default_factory=list)
    benchmark_results: list[BenchmarkDimensionResult] = Field(default_factory=list)
    overall_score: float = 0.0
    summary: list[str] = Field(default_factory=list)
