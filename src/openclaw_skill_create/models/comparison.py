from __future__ import annotations

from pydantic import BaseModel, Field

from .body_quality import SkillBodyQualityReport, SkillSelfReviewReport


class SkillCreateComparisonMetrics(BaseModel):
    body_lines: int = 0
    body_chars: int = 0
    heading_count: int = 0
    bullet_count: int = 0
    numbered_step_count: int = 0
    required_sections_present: list[str] = Field(default_factory=list)
    missing_required_sections: list[str] = Field(default_factory=list)
    prompt_echo_ratio: float = 0.0
    description_body_ratio: float = 0.0
    body_quality_status: str = "unknown"
    self_review_status: str = "unknown"
    fully_correct: bool = False
    severity: str = ""


class SkillCreateComparisonCaseResult(BaseModel):
    case_id: str
    skill_name: str
    auto_metrics: SkillCreateComparisonMetrics = Field(default_factory=SkillCreateComparisonMetrics)
    golden_metrics: SkillCreateComparisonMetrics = Field(default_factory=SkillCreateComparisonMetrics)
    hermes_metrics: SkillCreateComparisonMetrics | None = None
    body_quality: SkillBodyQualityReport | None = None
    self_review: SkillSelfReviewReport | None = None
    gap_issues: list[str] = Field(default_factory=list)
    status: str = "matched"
    summary: str = ""


class SkillCreateComparisonReport(BaseModel):
    schema_version: str = "1.0.0"
    cases: list[SkillCreateComparisonCaseResult] = Field(default_factory=list)
    include_hermes: bool = False
    hermes_available: bool = False
    hermes_errors: list[str] = Field(default_factory=list)
    gap_count: int = 0
    overall_status: str = "pass"
    summary: str = ""
    markdown_summary: str = ""
