from __future__ import annotations

from typing import Any, Optional

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.requirements import SkillRequirement
from ..models.review import RepairSuggestion, RequirementResult, SkillQualityReview
from .body_quality import build_skill_body_quality_report, build_skill_self_review_report
from .depth_quality import build_skill_depth_quality_report
from .editorial_quality import build_skill_editorial_quality_report
from .domain_expertise import build_skill_domain_expertise_report
from .domain_specificity import build_skill_domain_specificity_report
from .expert_structure import build_skill_expert_structure_report
from .move_quality import build_skill_move_quality_report
from .operation_coverage import load_operation_coverage_report
from .style_diversity import build_skill_style_diversity_report


SCRIPT_PLACEHOLDER_MARKERS = (
    'placeholder helper script generated from planned candidate resource.',
    'todo: implement',
    'notimplementederror',
)

REFERENCE_PLACEHOLDER_MARKERS = (
    'reference placeholder derived from planned candidate resource.',
    'review `',
)


def _artifact_map(artifacts: Artifacts) -> dict[str, ArtifactFile]:
    return {file.path: file for file in artifacts.files}


def _collect_requirements(*, repo_findings: Any, skill_plan: Any) -> list[SkillRequirement]:
    plan_requirements = list(getattr(skill_plan, 'requirements', []) or [])
    if plan_requirements:
        return plan_requirements
    return list(getattr(repo_findings, 'requirements', []) or [])


def _file_has_substance(path: str, content: str) -> bool:
    stripped = (content or '').strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    if path.startswith('references/'):
        if '## overview' not in lowered and len(stripped.splitlines()) < 4:
            return False
        return not any(marker in lowered for marker in REFERENCE_PLACEHOLDER_MARKERS)
    if path.startswith('scripts/'):
        return not any(marker in lowered for marker in SCRIPT_PLACEHOLDER_MARKERS)
    if path == 'agents/openai.yaml':
        return 'interface:' in lowered
    if path == '_meta.json':
        return stripped.startswith('{') and 'requirements' in lowered
    if path == 'SKILL.md':
        return stripped.startswith('---\n') and len(stripped.splitlines()) >= 5
    return True


def _requirement_result(requirement: SkillRequirement, *, artifacts: Artifacts) -> RequirementResult:
    files = _artifact_map(artifacts)
    missing_artifacts: list[str] = []
    satisfied_targets: list[str] = []

    for path in list(requirement.satisfied_by or []):
        file = files.get(path)
        if file is None:
            missing_artifacts.append(path)
            continue
        if _file_has_substance(path, file.content or ''):
            satisfied_targets.append(path)
        else:
            missing_artifacts.append(path)

    primary_targets = [path for path in list(requirement.satisfied_by or []) if path != 'SKILL.md']
    if primary_targets:
        satisfied = any(path in satisfied_targets for path in primary_targets)
    else:
        satisfied = bool(satisfied_targets)
    if satisfied:
        rationale = f"Covered by {', '.join(satisfied_targets[:2])}."
    elif missing_artifacts:
        rationale = f"Missing substantive coverage in {', '.join(missing_artifacts[:2])}."
    else:
        rationale = 'No planned artifacts were mapped to this requirement.'

    return RequirementResult(
        requirement_id=requirement.requirement_id,
        statement=requirement.statement,
        satisfied=satisfied,
        evidence_paths=list(requirement.evidence_paths or []),
        satisfied_by=satisfied_targets,
        rationale=rationale,
        missing_artifacts=missing_artifacts,
    )


def _requirement_suggestion(requirement: SkillRequirement, result: RequirementResult) -> Optional[RepairSuggestion]:
    if result.satisfied:
        return None
    if result.missing_artifacts:
        return RepairSuggestion(
            issue_type='missing_planned_file',
            instruction=f"Add or restore artifacts covering requirement: {requirement.statement}",
            target_paths=result.missing_artifacts,
            priority=requirement.priority,
            repair_scope='body_patch',
        )
    target_paths = list(requirement.satisfied_by or [])
    if requirement.source_kind in {'doc', 'config'}:
        target_paths = [path for path in target_paths if path.startswith('references/')] or target_paths
        return RepairSuggestion(
            issue_type='reference_structure_incomplete',
            instruction=f"Strengthen repo-grounded reference coverage for requirement: {requirement.statement}",
            target_paths=target_paths,
            priority=requirement.priority,
            repair_scope='body_patch',
        )
    if requirement.source_kind in {'script', 'workflow', 'entrypoint'}:
        target_paths = [path for path in target_paths if path.startswith('scripts/')] or target_paths
        return RepairSuggestion(
            issue_type='script_placeholder_heavy',
            instruction=f"Strengthen deterministic helper coverage for requirement: {requirement.statement}",
            target_paths=target_paths,
            priority=requirement.priority,
            repair_scope='body_patch',
        )
    return None


def _repair_scope_for_issue(issue_type: str, instruction: str) -> str:
    normalized = f'{issue_type} {instruction}'.lower()
    if any(token in normalized for token in ('derive', 'specialization', 'specialisation', 'domain split', 'stable gap')):
        return 'derive_child'
    if any(token in normalized for token in ('trigger', 'alignment', 'selection', 'description')):
        return 'description_only'
    return 'body_patch'


def _diagnostic_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    validation = getattr(diagnostics, 'validation', None)
    if validation is None:
        return []
    issue_types = list(getattr(validation, 'repairable_issue_types', []) or [])
    reasons = list(getattr(validation, 'failure_reasons', []) or [])
    suggestions: list[RepairSuggestion] = []
    for index, issue_type in enumerate(issue_types):
        instruction = reasons[index] if index < len(reasons) else f'Address validation issue: {issue_type}'
        suggestions.append(
            RepairSuggestion(
                issue_type=issue_type,
                instruction=instruction,
                target_paths=[],
                priority=80,
                repair_scope=_repair_scope_for_issue(issue_type, instruction),
            )
        )
    return suggestions


def _body_quality_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    body_quality = getattr(diagnostics, 'body_quality', None)
    self_review = getattr(diagnostics, 'self_review', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(body_quality, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Rewrite SKILL.md body so the generated skill is directly usable: {issue}',
                target_paths=['SKILL.md'],
                priority=95,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(self_review, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type='self_review_failed',
                instruction=f'Read back and strengthen SKILL.md body before treating the skill as complete: {issue}',
                target_paths=['SKILL.md'],
                priority=90,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _domain_specificity_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    domain_specificity = getattr(diagnostics, 'domain_specificity', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(domain_specificity, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Rewrite SKILL.md with domain-specific workflow, output fields, checks, and pitfalls: {issue}',
                target_paths=['SKILL.md'],
                priority=98,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(domain_specificity, 'warning_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Strengthen domain-specific anchors before treating the skill as complete: {issue}',
                target_paths=['SKILL.md'],
                priority=88,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _domain_expertise_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    domain_expertise = getattr(diagnostics, 'domain_expertise', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(domain_expertise, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Rewrite SKILL.md so domain anchors become actions, judgments, output fields, and pitfalls: {issue}',
                target_paths=['SKILL.md'],
                priority=99,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(domain_expertise, 'warning_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Strengthen domain moves before treating this methodology skill as release-ready: {issue}',
                target_paths=['SKILL.md'],
                priority=89,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _expert_structure_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    expert_structure = getattr(diagnostics, 'expert_structure', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(expert_structure, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Rewrite SKILL.md around expert domain headings, action clusters, output fields, and pitfalls: {issue}',
                target_paths=['SKILL.md'],
                priority=100,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(expert_structure, 'warning_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Mark this methodology skill as not release-ready until expert structure is available or stronger: {issue}',
                target_paths=['SKILL.md'],
                priority=87,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _depth_quality_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    depth_quality = getattr(diagnostics, 'depth_quality', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(depth_quality, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Rewrite SKILL.md so workflow steps include probes, output guidance, failure signals, examples, and expert depth: {issue}',
                target_paths=['SKILL.md'],
                priority=101,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(depth_quality, 'warning_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Strengthen methodology depth before treating this skill as release-ready: {issue}',
                target_paths=['SKILL.md'],
                priority=86,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _editorial_quality_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    editorial_quality = getattr(diagnostics, 'editorial_quality', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(editorial_quality, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Edit SKILL.md down to sharper decisions, executable fields, and failure corrections: {issue}',
                target_paths=['SKILL.md'],
                priority=102,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(editorial_quality, 'warning_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Mark this methodology skill as not release-ready until editorial quality is stronger: {issue}',
                target_paths=['SKILL.md'],
                priority=85,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _style_diversity_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    style_diversity = getattr(diagnostics, 'style_diversity', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(style_diversity, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Rewrite SKILL.md so methodology style, opening, and workflow labels are shaped by the specific domain: {issue}',
                target_paths=['SKILL.md'],
                priority=103,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(style_diversity, 'warning_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Mark this methodology skill as not release-ready until style diversity is stronger: {issue}',
                target_paths=['SKILL.md'],
                priority=84,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _move_quality_suggestions(diagnostics: Any) -> list[RepairSuggestion]:
    if diagnostics is None:
        return []
    move_quality = getattr(diagnostics, 'move_quality', None)
    suggestions: list[RepairSuggestion] = []
    for issue in list(getattr(move_quality, 'blocking_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Regenerate the methodology skill from Expert Skill DNA so workflow moves, outputs, and repair moves are preserved: {issue}',
                target_paths=['SKILL.md'],
                priority=106,
                repair_scope='body_patch',
            )
        )
    for issue in list(getattr(move_quality, 'warning_issues', []) or []):
        suggestions.append(
            RepairSuggestion(
                issue_type=str(issue),
                instruction=f'Mark this methodology skill as not release-ready until Expert Skill DNA coverage is stronger: {issue}',
                target_paths=['SKILL.md'],
                priority=86,
                repair_scope='body_patch',
            )
        )
    return suggestions


def _security_summary(diagnostics: Any) -> tuple[str | None, int, list[str]]:
    security_audit = getattr(diagnostics, 'security_audit', None) if diagnostics is not None else None
    if security_audit is None:
        return None, 0, []
    rating = str(getattr(security_audit, 'rating', '') or '').upper() or None
    blocking = int(getattr(security_audit, 'blocking_findings_count', 0) or 0)
    categories = list(getattr(security_audit, 'top_security_categories', []) or [])
    return rating, blocking, categories


def _dedupe_suggestions(suggestions: list[RepairSuggestion]) -> list[RepairSuggestion]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    ordered: list[RepairSuggestion] = []
    for suggestion in sorted(suggestions, key=lambda item: (-item.priority, item.issue_type)):
        key = (suggestion.issue_type, tuple(suggestion.target_paths))
        if key in seen:
            continue
        seen.add(key)
        ordered.append(suggestion)
    return ordered


def review_to_artifact(review: SkillQualityReview) -> ArtifactFile:
    import json

    return ArtifactFile(
        path='evals/review.json',
        content=json.dumps(review.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['quality_review'],
        status='new',
    )


def run_skill_quality_review(
    *,
    repo_findings: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    diagnostics: Any = None,
    evaluation_report: Any = None,
) -> SkillQualityReview:
    requirements = _collect_requirements(repo_findings=repo_findings, skill_plan=skill_plan)
    requirement_results = [_requirement_result(requirement, artifacts=artifacts) for requirement in requirements]

    requirement_suggestions = [
        suggestion
        for requirement, result in zip(requirements, requirement_results)
        for suggestion in [_requirement_suggestion(requirement, result)]
        if suggestion is not None
    ]
    suggestions = _dedupe_suggestions(
        requirement_suggestions
        + _diagnostic_suggestions(diagnostics)
        + _body_quality_suggestions(diagnostics)
        + _domain_specificity_suggestions(diagnostics)
        + _domain_expertise_suggestions(diagnostics)
        + _expert_structure_suggestions(diagnostics)
        + _depth_quality_suggestions(diagnostics)
        + _editorial_quality_suggestions(diagnostics)
        + _style_diversity_suggestions(diagnostics)
        + _move_quality_suggestions(diagnostics)
    )

    missing_evidence = sorted(
        {
            path
            for requirement in requirements
            if not requirement.evidence_paths
            for path in [requirement.requirement_id]
        }
    )
    requirement_score = (
        sum(1.0 for item in requirement_results if item.satisfied) / len(requirement_results)
        if requirement_results
        else 1.0
    )
    evaluation_score = float(getattr(evaluation_report, 'overall_score', 0.0) or 0.0)
    confidence = round((0.55 * requirement_score) + (0.45 * evaluation_score), 4)
    security_rating, security_blocking, security_categories = _security_summary(diagnostics)
    body_quality = getattr(diagnostics, 'body_quality', None) if diagnostics is not None else None
    self_review = getattr(diagnostics, 'self_review', None) if diagnostics is not None else None
    domain_specificity = getattr(diagnostics, 'domain_specificity', None) if diagnostics is not None else None
    domain_expertise = getattr(diagnostics, 'domain_expertise', None) if diagnostics is not None else None
    expert_structure = getattr(diagnostics, 'expert_structure', None) if diagnostics is not None else None
    depth_quality = getattr(diagnostics, 'depth_quality', None) if diagnostics is not None else None
    editorial_quality = getattr(diagnostics, 'editorial_quality', None) if diagnostics is not None else None
    style_diversity = getattr(diagnostics, 'style_diversity', None) if diagnostics is not None else None
    move_quality = getattr(diagnostics, 'move_quality', None) if diagnostics is not None else None
    if body_quality is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        body_quality = build_skill_body_quality_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    if self_review is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        self_review = build_skill_self_review_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
            body_quality=body_quality,
        )
    if domain_specificity is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        domain_specificity = build_skill_domain_specificity_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    if domain_expertise is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        domain_expertise = build_skill_domain_expertise_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    if expert_structure is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        expert_structure = build_skill_expert_structure_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    if depth_quality is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        depth_quality = build_skill_depth_quality_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    if editorial_quality is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        editorial_quality = build_skill_editorial_quality_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    if style_diversity is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        style_diversity = build_skill_style_diversity_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    if move_quality is None:
        request_proxy = type('RequestProxy', (), {'task': getattr(skill_plan, 'objective', '') or ''})()
        move_quality = build_skill_move_quality_report(
            request=request_proxy,
            skill_plan=skill_plan,
            artifacts=artifacts,
        )
    body_quality_status = str(getattr(body_quality, 'status', 'not_applicable') or 'not_applicable')
    body_quality_passed = bool(getattr(body_quality, 'passed', True)) if body_quality is not None else True
    body_quality_issues = list(getattr(body_quality, 'issues', []) or []) if body_quality is not None else []
    self_review_status = str(getattr(self_review, 'status', 'not_applicable') or 'not_applicable')
    self_review_passed = self_review_status in {'not_applicable', 'pass'}
    domain_specificity_status = str(getattr(domain_specificity, 'status', 'not_applicable') or 'not_applicable')
    domain_specificity_passed = domain_specificity_status in {'not_applicable', 'pass'}
    domain_specificity_issues = (
        list(getattr(domain_specificity, 'blocking_issues', []) or [])
        + list(getattr(domain_specificity, 'warning_issues', []) or [])
        if domain_specificity is not None
        else []
    )
    domain_expertise_status = str(getattr(domain_expertise, 'status', 'not_applicable') or 'not_applicable')
    domain_expertise_passed = domain_expertise_status in {'not_applicable', 'pass'}
    domain_expertise_issues = (
        list(getattr(domain_expertise, 'blocking_issues', []) or [])
        + list(getattr(domain_expertise, 'warning_issues', []) or [])
        if domain_expertise is not None
        else []
    )
    expert_structure_status = str(getattr(expert_structure, 'status', 'not_applicable') or 'not_applicable')
    expert_structure_passed = expert_structure_status in {'not_applicable', 'pass'}
    expert_structure_issues = (
        list(getattr(expert_structure, 'blocking_issues', []) or [])
        + list(getattr(expert_structure, 'warning_issues', []) or [])
        if expert_structure is not None
        else []
    )
    depth_quality_status = str(getattr(depth_quality, 'status', 'not_applicable') or 'not_applicable')
    depth_quality_passed = depth_quality_status in {'not_applicable', 'pass'}
    depth_quality_issues = (
        list(getattr(depth_quality, 'blocking_issues', []) or [])
        + list(getattr(depth_quality, 'warning_issues', []) or [])
        if depth_quality is not None
        else []
    )
    editorial_quality_status = str(getattr(editorial_quality, 'status', 'not_applicable') or 'not_applicable')
    editorial_quality_passed = editorial_quality_status in {'not_applicable', 'pass'}
    editorial_quality_issues = (
        list(getattr(editorial_quality, 'blocking_issues', []) or [])
        + list(getattr(editorial_quality, 'warning_issues', []) or [])
        if editorial_quality is not None
        else []
    )
    style_diversity_status = str(getattr(style_diversity, 'status', 'not_applicable') or 'not_applicable')
    style_diversity_passed = style_diversity_status in {'not_applicable', 'pass'}
    style_diversity_issues = (
        list(getattr(style_diversity, 'blocking_issues', []) or [])
        + list(getattr(style_diversity, 'warning_issues', []) or [])
        if style_diversity is not None
        else []
    )
    move_quality_status = str(getattr(move_quality, 'status', 'not_applicable') or 'not_applicable')
    move_quality_passed = move_quality_status in {'not_applicable', 'pass'}
    move_quality_issues = (
        list(getattr(move_quality, 'blocking_issues', []) or [])
        + list(getattr(move_quality, 'warning_issues', []) or [])
        if move_quality is not None
        else []
    )
    skill_archetype = str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower()
    operation_contract = getattr(skill_plan, 'operation_contract', None)
    operation_groups = [getattr(group, 'name', '') for group in list(getattr(operation_contract, 'operations', []) or []) if getattr(group, 'name', '')]
    operation_count = sum(len(list(getattr(group, 'operations', []) or [])) for group in list(getattr(operation_contract, 'operations', []) or []))
    operation_validation_status = 'not_applicable'
    coverage_gap_summary: list[str] = []
    recommended_followup = 'no_change'
    if skill_archetype == 'operation_backed':
        operation_coverage = load_operation_coverage_report(artifacts)
        if operation_coverage is not None:
            operation_validation_status = operation_coverage.validation_status
            coverage_gap_summary = [item.gap_type for item in list(operation_coverage.gap_summary or [])]
            recommended_followup = operation_coverage.recommended_followup
        else:
            issue_types = list(getattr(getattr(diagnostics, 'validation', None), 'repairable_issue_types', []) or []) if diagnostics is not None else []
            contract_issue_types = [item for item in issue_types if item.startswith('operation_')]
            if contract_issue_types:
                operation_validation_status = 'needs_attention'
                coverage_gap_summary = contract_issue_types
                recommended_followup = 'patch_current'
            else:
                operation_validation_status = 'validated'
    fully_correct = (
        not missing_evidence
        and not suggestions
        and (security_rating in {None, 'LOW'})
        and body_quality_passed
        and self_review_passed
        and domain_specificity_passed
        and domain_expertise_passed
        and expert_structure_passed
        and depth_quality_passed
        and editorial_quality_passed
        and style_diversity_passed
        and move_quality_passed
        and requirement_score >= 0.99
        and (evaluation_score >= 0.75 if evaluation_report is not None else True)
    )

    summary = [
        f"requirements_satisfied={sum(1 for item in requirement_results if item.satisfied)}/{len(requirement_results)}"
        if requirement_results
        else 'requirements_skipped',
        f"repair_suggestions={len(suggestions)}",
        f"confidence={confidence:.2f}",
    ]
    if evaluation_report is not None:
        summary.append(f"overall_score={evaluation_score:.2f}")
    if security_rating is not None:
        summary.append(f"security_rating={security_rating}")
        summary.append(f"security_blocking_findings={security_blocking}")
        if security_categories:
            summary.append(f"security_categories={','.join(security_categories)}")
    if body_quality is not None:
        summary.append(f"body_quality_status={body_quality_status}")
        summary.append(f"body_quality_issues={','.join(body_quality_issues[:6]) or 'none'}")
    if self_review is not None:
        summary.append(f"self_review_status={self_review_status}")
    if domain_specificity is not None:
        summary.append(f"domain_specificity_status={domain_specificity_status}")
        summary.append(f"domain_specificity_issues={','.join(domain_specificity_issues[:6]) or 'none'}")
    if domain_expertise is not None:
        summary.append(f"domain_expertise_status={domain_expertise_status}")
        summary.append(f"domain_expertise_issues={','.join(domain_expertise_issues[:6]) or 'none'}")
    if expert_structure is not None:
        summary.append(f"expert_structure_status={expert_structure_status}")
        summary.append(f"expert_structure_issues={','.join(expert_structure_issues[:6]) or 'none'}")
    if depth_quality is not None:
        summary.append(f"depth_quality_status={depth_quality_status}")
        summary.append(f"depth_quality_issues={','.join(depth_quality_issues[:6]) or 'none'}")
    if editorial_quality is not None:
        summary.append(f"editorial_quality_status={editorial_quality_status}")
        summary.append(f"editorial_quality_issues={','.join(editorial_quality_issues[:6]) or 'none'}")
    if style_diversity is not None:
        summary.append(f"style_diversity_status={style_diversity_status}")
        summary.append(f"style_diversity_issues={','.join(style_diversity_issues[:6]) or 'none'}")
    if move_quality is not None:
        summary.append(f"move_quality_status={move_quality_status}")
        summary.append(f"move_quality_issues={','.join(move_quality_issues[:6]) or 'none'}")
    if skill_archetype == 'operation_backed':
        summary.append(f"skill_archetype={skill_archetype}")
        summary.append(f"operation_count={operation_count}")
        if operation_groups:
            summary.append(f"operation_groups={','.join(operation_groups)}")
        summary.append(f"operation_validation_status={operation_validation_status}")
        summary.append(f"recommended_followup={recommended_followup}")
        if coverage_gap_summary:
            summary.append(f"coverage_gap_summary={','.join(coverage_gap_summary[:4])}")

    return SkillQualityReview(
        skill_name=getattr(skill_plan, 'skill_name', '') or getattr(evaluation_report, 'skill_name', 'generated-skill'),
        skill_archetype=skill_archetype,
        fully_correct=fully_correct,
        requirement_results=requirement_results,
        repair_suggestions=suggestions,
        missing_evidence=missing_evidence,
        confidence=confidence,
        operation_count=operation_count,
        operation_groups=operation_groups,
        operation_validation_status=operation_validation_status,
        coverage_gap_summary=coverage_gap_summary,
        recommended_followup=recommended_followup,
        body_quality_status=body_quality_status,
        body_quality_issues=body_quality_issues,
        self_review_status=self_review_status,
        domain_specificity_status=domain_specificity_status,
        domain_specificity_issues=domain_specificity_issues,
        domain_expertise_status=domain_expertise_status,
        domain_expertise_issues=domain_expertise_issues,
        expert_structure_status=expert_structure_status,
        expert_structure_issues=expert_structure_issues,
        depth_quality_status=depth_quality_status,
        depth_quality_issues=depth_quality_issues,
        editorial_quality_status=editorial_quality_status,
        editorial_quality_issues=editorial_quality_issues,
        style_diversity_status=style_diversity_status,
        style_diversity_issues=style_diversity_issues,
        move_quality_status=move_quality_status,
        move_quality_issues=move_quality_issues,
        summary=summary,
    )
