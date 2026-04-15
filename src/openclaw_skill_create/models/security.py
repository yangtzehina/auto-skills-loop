from __future__ import annotations

from pydantic import BaseModel, Field


class SecurityAuditFinding(BaseModel):
    category: str
    severity: str
    paths: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    reason: str = ""
    blocking: bool = False


class SecurityAuditReport(BaseModel):
    rating: str = "LOW"
    trust_tier: int = 1
    findings: list[SecurityAuditFinding] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
    recommended_action: str = "proceed"
    blocking_findings_count: int = 0
    top_security_categories: list[str] = Field(default_factory=list)
