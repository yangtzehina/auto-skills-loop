from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, Field

from .body_quality import SkillBodyQualityReport, SkillSelfReviewReport
from .domain_expertise import SkillDomainExpertiseReport
from .domain_specificity import SkillDomainSpecificityReport
from .depth_quality import SkillDepthQualityReport
from .expert_structure import SkillExpertStructureReport
from .security import SecurityAuditReport


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
    notes: list[str] = Field(default_factory=list)
