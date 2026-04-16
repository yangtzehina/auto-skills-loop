from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, Field

from .body_quality import SkillBodyQualityReport, SkillSelfReviewReport
from .domain_expertise import SkillDomainExpertiseReport
from .domain_specificity import SkillDomainSpecificityReport
from .depth_quality import SkillDepthQualityReport
from .editorial_quality import SkillEditorialQualityReport
from .expert_dna import SkillMoveQualityReport
from .expert_studio import (
    ExpertEvidenceGapReport,
    MonotonicImprovementReport,
    PairwiseEditorialReport,
    SkillEditorialForceReport,
    SkillProgramFidelityReport,
    SkillPromotionDecision,
    SkillRealizationCandidate,
    SkillRealizationSpec,
    SkillTaskOutcomeReport,
)
from .expert_structure import SkillExpertStructureReport
from .security import SecurityAuditReport
from .style_diversity import SkillStyleDiversityReport
from .workflow_form import SkillWorkflowFormReport


class ValidationResult(BaseModel):
    frontmatter_valid: bool = True
    skill_md_within_budget: bool = True
    planned_files_present: bool = True
    unnecessary_files_present: bool = False
    unreferenced_reference_files: list[str] = Field(default_factory=list)
    unsupported_claims_found: bool = False
    summary: list[str] = Field(default_factory=list)
    repairable_issue_types: list[str] = Field(default_factory=list)
    non_repairable_issue_types: list[str] = Field(default_factory=list)
    failure_reasons: list[str] = Field(default_factory=list)
    repair_recommended: bool = False


class Diagnostics(BaseModel):
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    validation: ValidationResult = Field(default_factory=ValidationResult)
    security_audit: Optional[SecurityAuditReport] = None
    body_quality: Optional[SkillBodyQualityReport] = None
    self_review: Optional[SkillSelfReviewReport] = None
    domain_specificity: Optional[SkillDomainSpecificityReport] = None
    domain_expertise: Optional[SkillDomainExpertiseReport] = None
    expert_structure: Optional[SkillExpertStructureReport] = None
    depth_quality: Optional[SkillDepthQualityReport] = None
    editorial_quality: Optional[SkillEditorialQualityReport] = None
    style_diversity: Optional[SkillStyleDiversityReport] = None
    move_quality: Optional[SkillMoveQualityReport] = None
    workflow_form: Optional[SkillWorkflowFormReport] = None
    realization_spec: Optional[SkillRealizationSpec] = None
    realization_candidates: list[SkillRealizationCandidate] = Field(default_factory=list)
    pairwise_editorial: Optional[PairwiseEditorialReport] = None
    promotion_decision: Optional[SkillPromotionDecision] = None
    monotonic_improvement: Optional[MonotonicImprovementReport] = None
    editorial_force: Optional[SkillEditorialForceReport] = None
    program_fidelity: Optional[SkillProgramFidelityReport] = None
    task_outcome: Optional[SkillTaskOutcomeReport] = None
    expert_evidence_gap: Optional[ExpertEvidenceGapReport] = None
    notes: list[str] = Field(default_factory=list)
