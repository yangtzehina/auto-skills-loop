from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .artifacts import Artifacts
from .diagnostics import Diagnostics
from .evaluation import EvaluationRunReport
from .findings import RepoFindings
from .online import SkillBlueprint, SkillReuseDecision, SkillSourceCandidate
from .orchestrator import ExecutionTimings
from .patterns import ExtractedSkillPatterns
from .plan import SkillPlan
from .review import SkillQualityReview
from .request import SkillCreateRequestV6


class SkillCreateResponseV6(BaseModel):
    request_id: str
    version: str = "v6"
    severity: str
    request_echo: SkillCreateRequestV6
    repo_findings: Optional[RepoFindings] = None
    extracted_patterns: Optional[ExtractedSkillPatterns] = None
    online_skill_candidates: list[SkillSourceCandidate] = Field(default_factory=list)
    online_skill_blueprints: list[SkillBlueprint] = Field(default_factory=list)
    reuse_decision: Optional[SkillReuseDecision] = None
    skill_plan: Optional[SkillPlan] = None
    artifacts: Optional[Artifacts] = None
    diagnostics: Optional[Diagnostics] = None
    evaluation_report: Optional[EvaluationRunReport] = None
    quality_review: Optional[SkillQualityReview] = None
    persistence: Optional[dict[str, Any]] = None
    observation: Optional[dict[str, Any]] = None
    timings: ExecutionTimings = Field(default_factory=lambda: ExecutionTimings(started_at_ms=0))
