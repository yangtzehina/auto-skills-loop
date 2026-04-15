from __future__ import annotations

from ..models.diagnostics import Diagnostics
from .security_audit import run_security_audit
from .validator_rules import run_rule_validation


def _merge_security_audit(*, diagnostics: Diagnostics, security_audit) -> Diagnostics:
    diagnostics.security_audit = security_audit
    summary = list(getattr(security_audit, "summary", []) or [])
    findings = list(getattr(security_audit, "findings", []) or [])

    if summary:
        warnings = list(getattr(diagnostics, "warnings", []) or [])
        for item in summary:
            if item not in warnings:
                warnings.append(item)
        diagnostics.warnings = warnings

    validation = diagnostics.validation
    validation_summary = list(getattr(validation, "summary", []) or [])
    non_repairable = list(getattr(validation, "non_repairable_issue_types", []) or [])

    for finding in findings:
        note = (
            f"Security audit [{finding.severity.upper()}] {finding.category}: "
            f"{finding.reason} ({', '.join(finding.paths[:2])})"
        )
        if note not in validation_summary:
            validation_summary.append(note)
        issue_type = f"security_{finding.category}"
        if issue_type not in non_repairable:
            non_repairable.append(issue_type)

    rating = str(getattr(security_audit, "rating", "LOW") or "LOW").upper()
    if rating != "LOW":
        top_level = f"security_audit_{rating.lower()}"
        if top_level not in non_repairable:
            non_repairable.append(top_level)

    validation.summary = validation_summary
    validation.non_repairable_issue_types = sorted(set(non_repairable))
    validation.failure_reasons = list(validation.summary)

    notes = list(getattr(diagnostics, "notes", []) or [])
    security_note = (
        "Security audit: "
        f"rating={rating}; trust_tier={getattr(security_audit, 'trust_tier', 1)}; "
        f"blocking_findings={getattr(security_audit, 'blocking_findings_count', 0)}; "
        f"recommended_action={getattr(security_audit, 'recommended_action', 'proceed')}; "
        f"top_categories={list(getattr(security_audit, 'top_security_categories', []) or [])}"
    )
    if security_note not in notes:
        notes.append(security_note)
    diagnostics.notes = notes
    return diagnostics


def run_validator(
    *,
    request,
    repo_findings,
    skill_plan,
    artifacts,
    extracted_patterns=None,
) -> Diagnostics:
    diagnostics = run_rule_validation(
        request=request,
        repo_findings=repo_findings,
        skill_plan=skill_plan,
        artifacts=artifacts,
        extracted_patterns=extracted_patterns,
    )
    security_audit = run_security_audit(
        request=request,
        repo_findings=repo_findings,
        skill_plan=skill_plan,
        artifacts=artifacts,
        extracted_patterns=extracted_patterns,
    )
    return _merge_security_audit(diagnostics=diagnostics, security_audit=security_audit)
