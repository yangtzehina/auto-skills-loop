from __future__ import annotations

from pydantic import BaseModel, Field


class ExpertTaskProbe(BaseModel):
    probe_id: str
    task: str = ""
    decision_terms: list[str] = Field(default_factory=list)
    cut_terms: list[str] = Field(default_factory=list)
    failure_terms: list[str] = Field(default_factory=list)
    repair_terms: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    anti_generic_terms: list[str] = Field(default_factory=list)


class ExpertRewritePair(BaseModel):
    skill_name: str
    weak_shell: str
    expert_revision: str
    revision_reason: str = ""


class ExpertFailureCase(BaseModel):
    skill_name: str
    failure_id: str
    bad_output: str
    failure_type: str
    why_it_fails: str = ""
    repair_direction: str = ""


class ExpertSectionCorpusEntry(BaseModel):
    skill_name: str
    section_name: str
    expert_excerpt: str = ""
    section_purpose: str = ""
    judgment_moves: list[str] = Field(default_factory=list)
    cut_moves: list[str] = Field(default_factory=list)
    repair_moves: list[str] = Field(default_factory=list)


class ExpertSkillCorpusEntry(BaseModel):
    skill_name: str
    domain_family: str = "methodology_guidance"
    task_brief: str = ""
    expert_skill_markdown: str = ""
    expert_notes: list[str] = Field(default_factory=list)
    section_corpus: list[ExpertSectionCorpusEntry] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    task_probes: list[ExpertTaskProbe] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    rewrite_pairs: list[ExpertRewritePair] = Field(default_factory=list)
    failure_cases: list[ExpertFailureCase] = Field(default_factory=list)


class ExecutionMove(BaseModel):
    step_id: str
    label: str
    purpose: str = ""
    decision: str = ""
    action: str = ""
    output: str = ""
    failure_signal: str = ""
    fix: str = ""
    must_include_terms: list[str] = Field(default_factory=list)
    avoid_terms: list[str] = Field(default_factory=list)


class AnalysisBlock(BaseModel):
    name: str
    when_used: str = ""
    questions: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)


class SkillProgramIR(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    workflow_surface: str = "execution_spine"
    opening_strategy: str = ""
    execution_spine: list[ExecutionMove] = Field(default_factory=list)
    analysis_blocks: list[AnalysisBlock] = Field(default_factory=list)
    decision_rules: list[str] = Field(default_factory=list)
    cut_rules: list[str] = Field(default_factory=list)
    failure_repairs: list[str] = Field(default_factory=list)
    output_schema: dict[str, list[str]] = Field(default_factory=dict)
    style_profile: list[str] = Field(default_factory=list)
    voice_constraints: list[str] = Field(default_factory=list)
    source_skill_name: str = ""
    source_confidence: str = "checked_in"
    summary: list[str] = Field(default_factory=list)


class SectionRealizationSpec(BaseModel):
    section_name: str
    rhetorical_purpose: str = ""
    allowed_surface_forms: list[str] = Field(default_factory=list)
    sentence_budget: int = 3
    required_judgment_moves: list[str] = Field(default_factory=list)
    forbidden_filler_patterns: list[str] = Field(default_factory=list)
    section_form: str = "compact"
    primary_force_focus: str = ""
    emphasis_level: str = "balanced"


class SkillRealizationSpec(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    workflow_surface: str = "execution_spine"
    opening_frame: str = ""
    section_order: list[str] = Field(default_factory=list)
    section_rhythm: list[str] = Field(default_factory=list)
    compression_policy: str = "balanced"
    voice_profile: list[str] = Field(default_factory=list)
    boilerplate_forbidden: list[str] = Field(default_factory=list)
    strategy_family: str = "default"
    strategy_tags: list[str] = Field(default_factory=list)
    sections: list[SectionRealizationSpec] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class SkillRealizationCandidate(BaseModel):
    schema_version: str = "1.0.0"
    candidate_id: str
    skill_name: str
    program_id: str
    realization_strategy: str = ""
    strategy_family: str = "default"
    strategy_profile: dict[str, str] = Field(default_factory=dict)
    rendered_markdown: str = ""
    diagnostic_summary: list[str] = Field(default_factory=list)


class ProfileBaselineSnapshot(BaseModel):
    label: str
    primary_force_metrics: dict[str, float] = Field(default_factory=dict)
    coverage_metrics: dict[str, float] = Field(default_factory=dict)
    compactness_metrics: dict[str, float] = Field(default_factory=dict)
    target_metrics: dict[str, float] = Field(default_factory=dict)
    summary: list[str] = Field(default_factory=list)


class ProfileBaselineBundle(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    active_frontier_version: str = ""
    best_balance_snapshot: ProfileBaselineSnapshot
    best_coverage_snapshot: ProfileBaselineSnapshot
    legacy_balance_snapshot: ProfileBaselineSnapshot | None = None
    legacy_coverage_snapshot: ProfileBaselineSnapshot | None = None
    force_floor: dict[str, float] = Field(default_factory=dict)
    coverage_floor: dict[str, float] = Field(default_factory=dict)
    compactness_ceiling: dict[str, float] = Field(default_factory=dict)
    tolerance: dict[str, float] = Field(default_factory=dict)
    summary: list[str] = Field(default_factory=list)


class ProfileResidualTargets(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    target_metrics: dict[str, float] = Field(default_factory=dict)
    allowed_sections: list[str] = Field(default_factory=list)
    protected_metrics: dict[str, float] = Field(default_factory=dict)
    summary: list[str] = Field(default_factory=list)


class ResidualGapReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str
    target_focus: str = ""
    quality_check_target_status: str = "pass"
    pressure_target_status: str = "pass"
    leakage_target_status: str = "pass"
    false_fix_rejection_status: str = "pass"
    residual_gap_count: int = 0
    status: str = "pass"
    summary: list[str] = Field(default_factory=list)


class OutcomeOnlyProbeScore(BaseModel):
    schema_version: str = "1.0.0"
    candidate_id: str = ""
    probe_id: str = ""
    win_status: str = "hold"
    pressure_delta: float = 0.0
    false_fix_delta: float = 0.0
    compression_delta: float = 0.0
    candidate_score: float = 0.0
    frontier_score: float = 0.0
    summary: list[str] = Field(default_factory=list)


class OutcomeOnlyRerankerReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    probe_mode: str = "frontier_v3"
    candidate_ranking: list[str] = Field(default_factory=list)
    winner: str = ""
    frontier_comparison_status: str = "unknown"
    blocking_reason: str = ""
    probe_pass_count: int = 0
    probe_count: int = 0
    improved_probe_count: int = 0
    matched_probe_count: int = 0
    blocked_probe_count: int = 0
    repair_specificity_score: float = 0.0
    probe_evidence_density: float = 0.0
    collapse_witness_coverage: float = 0.0
    probe_witness_summary: list[str] = Field(default_factory=list)
    matched_probe_ids: list[str] = Field(default_factory=list)
    improved_probe_ids: list[str] = Field(default_factory=list)
    blocked_probe_ids: list[str] = Field(default_factory=list)
    repair_evidence_lines: list[str] = Field(default_factory=list)
    collapse_evidence_lines: list[str] = Field(default_factory=list)
    probe_scores: list[OutcomeOnlyProbeScore] = Field(default_factory=list)
    status: str = "unknown"
    summary: list[str] = Field(default_factory=list)


class SectionCompressionPlan(BaseModel):
    section_name: str
    max_sentence_budget: int = 3
    protected_terms: list[str] = Field(default_factory=list)
    forbidden_removals: list[str] = Field(default_factory=list)
    compression_rules: list[str] = Field(default_factory=list)


class SectionCompressionResult(BaseModel):
    section_name: str
    removed_redundant_lines: int = 0
    opening_rewrite_applied: bool = False
    filler_removed_count: int = 0
    protected_terms_preserved: bool = True


class SkillProgramAuthoringCandidate(BaseModel):
    skill_name: str
    task_brief: str = ""
    candidate_program: SkillProgramIR
    source_confidence: str = "needs_human_authoring"
    backlog_categories: list[str] = Field(default_factory=list)
    missing_expert_evidence: list[str] = Field(default_factory=list)
    stable_move_sequence: bool = False
    ready_for_review: bool = False
    confidence: str = "needs_human_authoring"
    summary: list[str] = Field(default_factory=list)


class SkillProgramAuthoringPack(BaseModel):
    schema_version: str = "1.0.0"
    candidates: list[SkillProgramAuthoringCandidate] = Field(default_factory=list)
    ready_for_review: list[str] = Field(default_factory=list)
    needs_human_authoring: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)
    backlog_counts: dict[str, int] = Field(default_factory=dict)
    candidate_program_count: int = 0
    summary: str = ""
    markdown_summary: str = ""


class ProgramCandidateReviewReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    review_status: str = "fail"
    candidate_confidence: str = "needs_human_authoring"
    workflow_surface: str = "unknown"
    execution_move_count: int = 0
    analysis_block_count: int = 0
    output_field_count: int = 0
    checklist: dict[str, bool] = Field(default_factory=dict)
    blocking_issues: list[str] = Field(default_factory=list)
    approved_for_release_gate: bool = False
    summary: list[str] = Field(default_factory=list)
    markdown_summary: str = ""


class ProgramCandidateReviewBatchReport(BaseModel):
    schema_version: str = "1.0.0"
    reports: list[ProgramCandidateReviewReport] = Field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    approved_for_release_gate_count: int = 0
    summary: str = ""
    markdown_summary: str = ""


class PairwiseEditorialReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    winner: str = ""
    loser: str = ""
    decision_pressure_delta: float = 0.0
    cut_sharpness_delta: float = 0.0
    failure_repair_clarity_delta: float = 0.0
    output_executability_delta: float = 0.0
    redundancy_delta: float = 0.0
    style_convergence_delta: float = 0.0
    candidate_separation_status: str = "unknown"
    candidate_separation_score: float = 0.0
    force_non_regression_status: str = "unknown"
    current_best_comparison_status: str = "unknown"
    primary_force_win_count: int = 0
    promotion_hold_reason: str = ""
    candidate_strategy_matrix: list[dict[str, str]] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class SkillPromotionDecision(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    candidate_id: str = ""
    current_best_id: str = ""
    promotion_status: str = "hold"
    reason: str = ""
    best_balance_comparison_status: str = "unknown"
    best_coverage_comparison_status: str = "unknown"
    candidate_separation_status: str = "unknown"
    force_non_regression_status: str = "unknown"
    coverage_non_regression_status: str = "unknown"
    compactness_non_regression_status: str = "unknown"
    frontier_dominance_status: str = "unknown"
    compression_gain_status: str = "unknown"
    current_best_comparison_status: str = "unknown"
    active_frontier_status: str = "unknown"
    primary_force_win_count: int = 0
    promotion_hold_reason: str = ""
    stable_but_no_breakthrough: bool = False
    quality_check_target_status: str = "unknown"
    pressure_target_status: str = "unknown"
    leakage_target_status: str = "unknown"
    false_fix_rejection_status: str = "unknown"
    residual_gap_count: int = 0
    outcome_only_reranker_status: str = "unknown"
    outcome_only_frontier_comparison_status: str = "unknown"
    outcome_only_probe_pass_count: int = 0
    outcome_only_blocking_reason: str = ""
    summary: list[str] = Field(default_factory=list)


class MonotonicImprovementReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    best_balance_comparison_status: str = "unknown"
    best_coverage_comparison_status: str = "unknown"
    force_non_regression_status: str = "unknown"
    coverage_non_regression_status: str = "unknown"
    compactness_non_regression_status: str = "unknown"
    frontier_dominance_status: str = "unknown"
    compression_gain_status: str = "unknown"
    active_frontier_status: str = "unknown"
    promotion_status: str = "hold"
    promotion_reason: str = ""
    primary_force_win_count: int = 0
    protected_regressions: list[str] = Field(default_factory=list)
    compactness_gains: list[str] = Field(default_factory=list)
    legacy_delta_summary: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class SkillEditorialForceReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    decision_pressure_score: float = 0.0
    cut_sharpness_score: float = 0.0
    failure_repair_force: float = 0.0
    boundary_rule_coverage: float = 0.0
    stop_condition_coverage: float = 0.0
    output_executability_score: float = 0.0
    anti_filler_score: float = 0.0
    section_force_distinctness: float = 0.0
    section_rhythm_distinctness: float = 0.0
    opening_distinctness: float = 0.0
    compression_without_loss: float = 0.0
    generic_surface_leakage: float = 0.0
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    primary_force_metrics: dict[str, float] = Field(default_factory=dict)
    summary: list[str] = Field(default_factory=list)


class SkillProgramFidelityReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    skill_archetype: str = "guidance"
    status: str = "pass"
    profile_available: bool = False
    execution_move_recall: float = 0.0
    execution_move_order_alignment: float = 0.0
    decision_rule_fidelity: float = 0.0
    cut_rule_fidelity: float = 0.0
    failure_repair_fidelity: float = 0.0
    output_schema_fidelity: float = 0.0
    workflow_surface_fidelity: float = 0.0
    style_strategy_fidelity: float = 0.0
    missing_execution_moves: list[str] = Field(default_factory=list)
    missing_output_fields: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warning_issues: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)


class SkillTaskOutcomeProbeResult(BaseModel):
    skill_name: str
    probe_id: str
    task: str = ""
    with_skill_score: float = 0.0
    baseline_score: float = 0.0
    expert_reference_score: float = 0.0
    decision_specificity: float = 0.0
    cut_strength: float = 0.0
    failure_detection: float = 0.0
    repair_usefulness: float = 0.0
    output_fillability: float = 0.0
    generic_advice_leakage: float = 0.0
    gap_issues: list[str] = Field(default_factory=list)
    status: str = "pass"


class SkillTaskOutcomeProfileResult(BaseModel):
    skill_name: str
    status: str = "pass"
    probe_results: list[SkillTaskOutcomeProbeResult] = Field(default_factory=list)
    probe_count: int = 0
    pass_count: int = 0
    with_skill_average: float = 0.0
    baseline_average: float = 0.0
    expert_reference_average: float = 0.0
    gap_issues: list[str] = Field(default_factory=list)


class SkillTaskOutcomeReport(BaseModel):
    schema_version: str = "1.0.0"
    status: str = "pass"
    profile_results: list[SkillTaskOutcomeProfileResult] = Field(default_factory=list)
    probe_count: int = 0
    task_outcome_gap_count: int = 0
    with_skill_average: float = 0.0
    baseline_average: float = 0.0
    expert_reference_average: float = 0.0
    summary: str = ""
    markdown_summary: str = ""


class ExpertEvidenceGapReport(BaseModel):
    schema_version: str = "1.0.0"
    skill_name: str = ""
    status: str = "pass"
    missing_expert_golden: bool = False
    missing_section_corpus: bool = False
    missing_probe_outputs: bool = False
    unstable_move_sequence: bool = False
    unstable_program_shape: bool = False
    generic_realization_candidate: bool = False
    backlog_categories: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
