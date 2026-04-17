from __future__ import annotations

from pydantic import BaseModel, Field

from .body_quality import SkillBodyQualityReport, SkillSelfReviewReport
from .domain_expertise import SkillDomainExpertiseReport
from .domain_specificity import SkillDomainSpecificityReport
from .depth_quality import SkillDepthQualityReport
from .editorial_quality import SkillEditorialQualityReport
from .expert_dna import ExpertDNAAuthoringPack, SkillMoveQualityReport, SkillUsefulnessEvalReport
from .expert_studio import (
    MonotonicImprovementReport,
    PairwiseEditorialReport,
    SkillEditorialForceReport,
    ProgramCandidateReviewBatchReport,
    SkillProgramAuthoringPack,
    SkillProgramFidelityReport,
    SkillPromotionDecision,
    SkillTaskOutcomeReport,
)
from .expert_structure import SkillExpertStructureReport
from .style_diversity import SkillStyleDiversityReport
from .workflow_form import SkillWorkflowFormReport


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
    force_boundary_rule_coverage: float = 0.0
    depth_gap_count: int = 0
    editorial_quality_status: str = "unknown"
    decision_pressure_score: float = 0.0
    action_density_score: float = 0.0
    redundancy_ratio: float = 0.0
    output_executability_score: float = 0.0
    failure_correction_score: float = 0.0
    compression_score: float = 0.0
    expert_cut_alignment: float = 0.0
    editorial_gap_count: int = 0
    style_diversity_status: str = "unknown"
    shared_opening_phrase_ratio: float = 0.0
    shared_step_label_ratio: float = 0.0
    shared_boilerplate_sentence_ratio: float = 0.0
    fixed_renderer_phrase_count: int = 0
    profile_specific_label_coverage: float = 0.0
    domain_rhythm_score: float = 0.0
    style_gap_count: int = 0
    move_quality_status: str = "unknown"
    expert_move_recall: float = 0.0
    expert_move_precision: float = 0.0
    decision_rule_coverage: float = 0.0
    cut_rule_coverage: float = 0.0
    output_field_semantics_coverage: float = 0.0
    failure_repair_coverage: float = 0.0
    numbered_workflow_spine_present: bool = False
    voice_rule_alignment: float = 0.0
    cross_case_move_overlap: float = 0.0
    move_quality_gap_count: int = 0
    workflow_form_status: str = "unknown"
    workflow_surface: str = "unknown"
    numbered_spine_count: int = 0
    imperative_move_recall: float = 0.0
    named_block_dominance_ratio: float = 0.0
    workflow_heading_alignment: float = 0.0
    output_block_separation: bool = True
    structural_block_count: int = 0
    workflow_form_gap_count: int = 0
    realization_candidate_count: int = 0
    pairwise_editorial_status: str = "unknown"
    pairwise_decision_pressure_delta: float = 0.0
    pairwise_cut_sharpness_delta: float = 0.0
    pairwise_failure_repair_clarity_delta: float = 0.0
    pairwise_output_executability_delta: float = 0.0
    pairwise_redundancy_delta: float = 0.0
    pairwise_style_convergence_delta: float = 0.0
    pairwise_promotion_status: str = "unknown"
    pairwise_promotion_reason: str = ""
    candidate_separation_status: str = "unknown"
    candidate_separation_score: float = 0.0
    best_balance_comparison_status: str = "unknown"
    best_coverage_comparison_status: str = "unknown"
    active_frontier_status: str = "unknown"
    force_non_regression_status: str = "unknown"
    coverage_non_regression_status: str = "unknown"
    compactness_non_regression_status: str = "unknown"
    frontier_dominance_status: str = "unknown"
    compression_gain_status: str = "unknown"
    current_best_comparison_status: str = "unknown"
    primary_force_win_count: int = 0
    promotion_hold_reason: str = ""
    stable_but_no_breakthrough: bool = False
    quality_check_target_status: str = "unknown"
    pressure_target_status: str = "unknown"
    leakage_target_status: str = "unknown"
    false_fix_rejection_status: str = "unknown"
    residual_gap_count: int = 0
    legacy_delta_summary: list[str] = Field(default_factory=list)
    candidate_strategy_matrix: list[dict[str, str]] = Field(default_factory=list)
    editorial_force_status: str = "unknown"
    cut_sharpness_score: float = 0.0
    failure_repair_force: float = 0.0
    boundary_rule_coverage: float = 0.0
    stop_condition_coverage: float = 0.0
    anti_filler_score: float = 0.0
    section_force_distinctness: float = 0.0
    section_rhythm_distinctness: float = 0.0
    opening_distinctness: float = 0.0
    compression_without_loss: float = 0.0
    generic_surface_leakage: float = 0.0
    editorial_force_gap_count: int = 0
    program_fidelity_status: str = "unknown"
    execution_move_recall: float = 0.0
    execution_move_order_alignment: float = 0.0
    decision_rule_fidelity: float = 0.0
    cut_rule_fidelity: float = 0.0
    failure_repair_fidelity: float = 0.0
    output_schema_fidelity: float = 0.0
    workflow_surface_fidelity: float = 0.0
    style_strategy_fidelity: float = 0.0
    program_fidelity_gap_count: int = 0
    task_outcome_status: str = "unknown"
    task_outcome_pass_count: int = 0
    task_outcome_probe_count: int = 0
    task_outcome_with_skill_average: float = 0.0
    task_outcome_gap_count: int = 0
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
    editorial_quality: SkillEditorialQualityReport | None = None
    style_diversity: SkillStyleDiversityReport | None = None
    move_quality: SkillMoveQualityReport | None = None
    workflow_form: SkillWorkflowFormReport | None = None
    pairwise_editorial: PairwiseEditorialReport | None = None
    promotion_decision: SkillPromotionDecision | None = None
    monotonic_improvement: MonotonicImprovementReport | None = None
    editorial_force: SkillEditorialForceReport | None = None
    program_fidelity: SkillProgramFidelityReport | None = None
    task_outcome: SkillTaskOutcomeReport | None = None
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
    expert_dna_authoring_pack: ExpertDNAAuthoringPack | None = None
    skill_program_authoring_pack: SkillProgramAuthoringPack | None = None
    program_candidate_review_batch: ProgramCandidateReviewBatchReport | None = None
    skill_usefulness_eval_report: SkillUsefulnessEvalReport | None = None
    skill_task_outcome_report: SkillTaskOutcomeReport | None = None
    dna_authoring_status: str = "pass"
    candidate_dna_count: int = 0
    program_authoring_status: str = "pass"
    candidate_program_count: int = 0
    usefulness_eval_status: str = "pass"
    usefulness_gap_count: int = 0
    task_outcome_status: str = "pass"
    task_outcome_gap_count: int = 0
    expert_structure_gap_count: int = 0
    depth_quality_gap_count: int = 0
    editorial_gap_count: int = 0
    style_gap_count: int = 0
    move_quality_gap_count: int = 0
    workflow_form_gap_count: int = 0
    editorial_force_gap_count: int = 0
    pairwise_promotion_gap_count: int = 0
    program_fidelity_gap_count: int = 0
    candidate_separation_gap_count: int = 0
    best_balance_not_beaten_count: int = 0
    best_coverage_not_beaten_count: int = 0
    current_best_not_beaten_count: int = 0
    promotion_hold_count: int = 0
    force_non_regression_status: str = "pass"
    coverage_non_regression_status: str = "pass"
    compactness_non_regression_status: str = "pass"
    frontier_dominance_status: str = "pass"
    compression_gain_status: str = "pass"
    stable_but_no_breakthrough_count: int = 0
    active_frontier_status: str = "pass"
    residual_gap_count: int = 0
    generic_shell_gap_count: int = 0
    pairwise_similarity_gap_count: int = 0
    negative_case_resistance: float = 1.0
    generic_shell_rejection: float = 1.0
    program_regression_count: int = 0
    gap_count: int = 0
    overall_status: str = "pass"
    summary: str = ""
    markdown_summary: str = ""
