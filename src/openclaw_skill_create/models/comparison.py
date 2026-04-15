from __future__ import annotations

from pydantic import BaseModel, Field

from .body_quality import SkillBodyQualityReport, SkillSelfReviewReport
from .domain_expertise import SkillDomainExpertiseReport
from .domain_specificity import SkillDomainSpecificityReport
from .depth_quality import SkillDepthQualityReport
from .expert_structure import SkillExpertStructureReport


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
    domain_specificity_status: str = "unknown"
    domain_anchor_coverage: float = 0.0
    missing_domain_anchors: list[str] = Field(default_factory=list)
    generic_template_ratio: float = 0.0
    cross_case_similarity: float = 0.0
    domain_expertise_status: str = "unknown"
    domain_move_coverage: float = 0.0
    prompt_phrase_echo_ratio: float = 0.0
    generic_expertise_shell_ratio: float = 0.0
    expert_structure_status: str = "unknown"
    expert_heading_recall: float = 0.0
    expert_action_cluster_recall: float = 0.0
    expert_output_field_recall: float = 0.0
    expert_pitfall_cluster_recall: float = 0.0
    expert_quality_check_recall: float = 0.0
    generated_vs_generated_heading_overlap: float = 0.0
    generated_vs_generated_line_jaccard: float = 0.0
    generic_skeleton_ratio: float = 0.0
    depth_quality_status: str = "unknown"
    expert_depth_recall: float = 0.0
    section_depth_score: float = 0.0
    decision_probe_count: int = 0
    worked_example_count: int = 0
    failure_pattern_density: int = 0
    output_field_guidance_coverage: float = 0.0
    boundary_rule_coverage: float = 0.0
    depth_gap_count: int = 0
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
    domain_specificity: SkillDomainSpecificityReport | None = None
    domain_expertise: SkillDomainExpertiseReport | None = None
    expert_structure: SkillExpertStructureReport | None = None
    depth_quality: SkillDepthQualityReport | None = None
    gap_issues: list[str] = Field(default_factory=list)
    status: str = "matched"
    summary: str = ""


class SkillCreateComparisonReport(BaseModel):
    schema_version: str = "1.0.0"
    cases: list[SkillCreateComparisonCaseResult] = Field(default_factory=list)
    include_hermes: bool = False
    hermes_available: bool = False
    hermes_execution_status: str = "not_requested"
    hermes_error_count: int = 0
    hermes_errors: list[str] = Field(default_factory=list)
    comparison_source: str = "golden"
    comparison_independence_status: str = "golden_only"
    reference_role: str = "quality_baseline"
    anthropic_reference_available: bool = False
    anthropic_reference_metrics: SkillCreateComparisonMetrics | None = None
    anthropic_reference_summary: list[str] = Field(default_factory=list)
    expert_structure_gap_count: int = 0
    depth_quality_gap_count: int = 0
    generic_shell_gap_count: int = 0
    pairwise_similarity_gap_count: int = 0
    gap_count: int = 0
    overall_status: str = "pass"
    summary: str = ""
    markdown_summary: str = ""
