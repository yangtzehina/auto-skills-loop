from __future__ import annotations

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.plan import SkillPlan
from ..models.repair import RepairResult
from .generator_fallback import (
    fallback_generate_methodology_skill_md_artifact,
    fallback_generate_operation_skill_md_artifact,
    fallback_generate_skill_md_artifact,
)
from .operation_contract import contract_to_artifact, operation_helper_artifact, operation_validation_artifact
from .operation_coverage import build_operation_coverage_report, operation_coverage_artifact
from .repair_rules import (
    build_repaired_eval_content,
    build_repaired_reference_content,
    build_repaired_script_content,
    clone_artifacts,
    drop_unexpected_files,
    find_artifact,
    repair_missing_planned_files,
    repair_reference_navigation,
    repair_skill_md_budget,
    repair_skill_md_frontmatter,
    replace_artifact,
)


def _quality_review_suggestions(quality_review) -> list[object]:
    if quality_review is None:
        return []
    return list(getattr(quality_review, 'repair_suggestions', []) or [])


def _quality_review_issue_types(quality_review) -> list[str]:
    if quality_review is None:
        return []
    issue_types: list[str] = []
    for suggestion in _quality_review_suggestions(quality_review):
        issue_type = getattr(suggestion, 'issue_type', '') or ''
        if issue_type:
            issue_types.append(issue_type)
    return issue_types


def _effective_repair_scope(quality_review) -> str | None:
    scopes = {
        str(getattr(suggestion, 'repair_scope', '') or '').strip()
        for suggestion in _quality_review_suggestions(quality_review)
        if str(getattr(suggestion, 'repair_scope', '') or '').strip()
    }
    if not scopes:
        return None
    if 'derive_child' in scopes:
        return 'derive_child'
    if 'body_patch' in scopes:
        return 'body_patch'
    if 'description_only' in scopes:
        return 'description_only'
    return None


def _repair_empty_resource_files(repaired: Artifacts, *, request=None, skill_plan=None, reuse_decision=None) -> bool:
    changed = False
    for idx, file in enumerate(repaired.files):
        if file.path.startswith('references/') and not (file.content or '').strip():
            repaired.files[idx] = ArtifactFile(
                path=file.path,
                content=build_repaired_reference_content(path=file.path, raw=''),
                content_type='text/markdown',
                generated_from=sorted(set(list(file.generated_from) + ['repair'])),
                status='repaired',
            )
            changed = True
        elif file.path.startswith('scripts/') and not (file.content or '').strip():
            repaired.files[idx] = ArtifactFile(
                path=file.path,
                content=build_repaired_script_content(path=file.path, raw=''),
                content_type='text/plain',
                generated_from=sorted(set(list(file.generated_from) + ['repair'])),
                status='repaired',
            )
            changed = True
        elif (
            file.path.startswith('evals/')
            and file.path.endswith('.json')
            and not (file.content or '').strip()
            and skill_plan is not None
        ):
            repaired.files[idx] = ArtifactFile(
                path=file.path,
                content=build_repaired_eval_content(
                    path=file.path,
                    request=request,
                    skill_plan=skill_plan,
                    reuse_decision=reuse_decision,
                ),
                content_type='application/json',
                generated_from=sorted(set(list(file.generated_from) + ['repair'])),
                status='repaired',
            )
            changed = True
    return changed


def _repair_operation_backed_sync(
    repaired: Artifacts,
    *,
    skill_plan: SkillPlan,
    diagnostics,
) -> bool:
    if str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower() != 'operation_backed':
        return False
    security_audit = getattr(diagnostics, 'security_audit', None)
    security_rating = str(getattr(security_audit, 'rating', 'LOW') or 'LOW').upper()
    if security_rating in {'HIGH', 'REJECT'}:
        return False

    contract = getattr(skill_plan, 'operation_contract', None)
    if contract is None:
        return False

    changed = False
    references = sorted(file.path for file in repaired.files if file.path.startswith('references/'))
    scripts = sorted(file.path for file in repaired.files if file.path.startswith('scripts/'))
    skill_md = fallback_generate_operation_skill_md_artifact(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        description=f'Repo-aware skill for {getattr(skill_plan, "skill_name", "generated-skill")}',
        contract=contract,
        references=references,
        scripts=scripts,
    )
    existing_skill_md = find_artifact(repaired, 'SKILL.md')
    if existing_skill_md is None or existing_skill_md.content != skill_md.content:
        replace_artifact(repaired, skill_md)
        changed = True

    contract_artifact = contract_to_artifact(contract)
    existing_contract = find_artifact(repaired, contract_artifact.path)
    if existing_contract is None or existing_contract.content != contract_artifact.content:
        replace_artifact(repaired, contract_artifact)
        changed = True

    validation_artifact = operation_validation_artifact(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        skill_archetype='operation_backed',
        contract=contract,
    )
    existing_validation = find_artifact(repaired, validation_artifact.path)
    if existing_validation is None or existing_validation.content != validation_artifact.content:
        replace_artifact(repaired, validation_artifact)
        changed = True

    coverage_report = build_operation_coverage_report(
        skill_plan=skill_plan,
        artifacts=repaired,
        diagnostics=diagnostics,
    )
    coverage_artifact = operation_coverage_artifact(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        report=coverage_report,
    )
    existing_coverage = find_artifact(repaired, coverage_artifact.path)
    if existing_coverage is None or existing_coverage.content != coverage_artifact.content:
        replace_artifact(repaired, coverage_artifact)
        changed = True

    backend_kind = str(getattr(contract, 'backend_kind', 'python_backend') or 'python_backend')
    if backend_kind != 'repo_native_cli':
        helper_artifact = operation_helper_artifact(
            skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
            contract=contract,
            path='scripts/operation_helper.py',
        )
        existing_helper = find_artifact(repaired, helper_artifact.path)
        if existing_helper is None or existing_helper.content != helper_artifact.content:
            replace_artifact(repaired, helper_artifact)
            changed = True
    return changed


def _repair_methodology_body(
    repaired: Artifacts,
    *,
    skill_plan: SkillPlan,
    request=None,
) -> bool:
    if str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower() != 'methodology_guidance':
        return False
    references = sorted(file.path for file in repaired.files if file.path.startswith('references/'))
    scripts = sorted(file.path for file in repaired.files if file.path.startswith('scripts/'))
    skill_md = fallback_generate_methodology_skill_md_artifact(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        description=f'Create structured methodology guidance for {getattr(skill_plan, "skill_name", "generated-skill")}. Use when Codex needs workflow, output template, and pitfalls for this decision task.',
        task=str(getattr(request, 'task', '') or getattr(skill_plan, 'objective', '') or ''),
        references=references,
        scripts=scripts,
    )
    existing = find_artifact(repaired, 'SKILL.md')
    if existing is not None and existing.content == skill_md.content:
        return False
    replace_artifact(repaired, skill_md)
    return True


def _repair_guidance_body(
    repaired: Artifacts,
    *,
    skill_plan: SkillPlan,
    description: str,
) -> bool:
    if str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower() != 'guidance':
        return False
    references = sorted(file.path for file in repaired.files if file.path.startswith('references/'))
    scripts = sorted(file.path for file in repaired.files if file.path.startswith('scripts/'))
    skill_md = fallback_generate_skill_md_artifact(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        description=description,
        references=references,
        scripts=scripts,
    )
    existing = find_artifact(repaired, 'SKILL.md')
    if existing is not None and existing.content == skill_md.content:
        return False
    replace_artifact(repaired, skill_md)
    return True


def _repair_reference_quality_issues(repaired: Artifacts, repairable_issue_types: list[str]) -> bool:
    should_repair = (
        'reference_structure_incomplete' in repairable_issue_types
        or 'reference_placeholder_heavy' in repairable_issue_types
    )
    if not should_repair:
        return False

    changed = False
    for idx, file in enumerate(repaired.files):
        if not file.path.startswith('references/'):
            continue
        repaired_content = build_repaired_reference_content(path=file.path, raw=file.content or '')
        if repaired_content == file.content:
            continue
        repaired.files[idx] = ArtifactFile(
            path=file.path,
            content=repaired_content,
            content_type='text/markdown',
            generated_from=sorted(set(list(file.generated_from) + ['repair'])),
            status='repaired',
        )
        changed = True
    return changed


def _repair_script_quality_issues(repaired: Artifacts, repairable_issue_types: list[str]) -> bool:
    should_repair = (
        'script_placeholder_heavy' in repairable_issue_types
        or 'script_non_code_like' in repairable_issue_types
        or 'script_wrapper_like' in repairable_issue_types
    )
    if not should_repair:
        return False

    changed = False
    for idx, file in enumerate(repaired.files):
        if not file.path.startswith('scripts/'):
            continue
        repaired_content = build_repaired_script_content(path=file.path, raw=file.content or '')
        if repaired_content == file.content:
            continue
        repaired.files[idx] = ArtifactFile(
            path=file.path,
            content=repaired_content,
            content_type=file.content_type,
            generated_from=sorted(set(list(file.generated_from) + ['repair'])),
            status='repaired',
        )
        changed = True
    return changed


def _repair_eval_quality_issues(
    repaired: Artifacts,
    repairable_issue_types: list[str],
    *,
    request=None,
    skill_plan: SkillPlan | None = None,
    reuse_decision=None,
) -> bool:
    should_repair = (
        'empty_eval_scaffold' in repairable_issue_types
        or 'invalid_eval_scaffold' in repairable_issue_types
    )
    if not should_repair or skill_plan is None:
        return False

    changed = False
    for idx, file in enumerate(repaired.files):
        if not (file.path.startswith('evals/') and file.path.endswith('.json')):
            continue
        repaired_content = build_repaired_eval_content(
            path=file.path,
            request=request,
            skill_plan=skill_plan,
            reuse_decision=reuse_decision,
        )
        if repaired_content == file.content:
            continue
        repaired.files[idx] = ArtifactFile(
            path=file.path,
            content=repaired_content,
            content_type='application/json',
            generated_from=sorted(set(list(file.generated_from) + ['repair'])),
            status='repaired',
        )
        changed = True
    return changed


def run_repair(
    *,
    artifacts: Artifacts,
    diagnostics,
    skill_plan: SkillPlan,
    skill_name: str,
    description: str,
    max_skill_md_lines: int,
    request=None,
    reuse_decision=None,
    quality_review=None,
) -> RepairResult:
    repaired = clone_artifacts(artifacts)
    changed = False
    scoped_repair = _effective_repair_scope(quality_review)
    if scoped_repair == 'derive_child':
        return RepairResult(
            applied=False,
            repaired_artifacts=repaired,
            reason='scoped repair skipped: derive_child requested',
        )
    repairable_issue_types = sorted(
        set(list(getattr(diagnostics.validation, 'repairable_issue_types', []) or []) + _quality_review_issue_types(quality_review))
    )

    if scoped_repair != 'description_only':
        changed = _repair_operation_backed_sync(
            repaired,
            skill_plan=skill_plan,
            diagnostics=diagnostics,
        ) or changed
        body_issue_types = {
            'body_too_thin',
            'missing_workflow',
            'missing_output_template',
            'missing_pitfalls',
            'methodology_section_missing',
            'prompt_echo',
            'description_stuffing',
            'self_review_failed',
            'missing_domain_anchors',
            'generic_methodology_shell',
            'high_cross_case_similarity',
            'body_prompt_echo',
            'domain_workflow_missing',
            'domain_output_missing',
            'domain_actions_missing',
            'domain_output_fields_missing',
            'domain_judgment_checks_missing',
            'domain_pitfalls_missing',
            'domain_moves_underdeveloped',
            'generic_domain_move_shell',
            'expert_headings_missing',
            'expert_action_clusters_missing',
            'expert_output_fields_missing',
            'expert_quality_checks_missing',
            'generic_expert_skeleton',
            'high_generated_heading_overlap',
            'high_generated_line_jaccard',
            'shallow_workflow_steps',
            'missing_decision_probes',
            'weak_output_field_guidance',
            'thin_failure_patterns',
            'missing_worked_examples',
            'low_expert_depth_recall',
        }
        if body_issue_types & set(repairable_issue_types):
            changed = _repair_methodology_body(
                repaired,
                skill_plan=skill_plan,
                request=request,
            ) or changed
            changed = _repair_guidance_body(
                repaired,
                skill_plan=skill_plan,
                description=description,
            ) or changed
        repair_missing_planned_files(
            artifacts=repaired,
            skill_plan=skill_plan,
            request=request,
            reuse_decision=reuse_decision,
        )
        if len(repaired.files) != len(artifacts.files):
            changed = True

        changed = _repair_empty_resource_files(
            repaired,
            request=request,
            skill_plan=skill_plan,
            reuse_decision=reuse_decision,
        ) or changed
        changed = _repair_reference_quality_issues(
            repaired,
            repairable_issue_types,
        ) or changed
        changed = _repair_script_quality_issues(
            repaired,
            repairable_issue_types,
        ) or changed
        changed = _repair_eval_quality_issues(
            repaired,
            repairable_issue_types,
            request=request,
            skill_plan=skill_plan,
            reuse_decision=reuse_decision,
        ) or changed

        if diagnostics.validation.unnecessary_files_present:
            before = len(repaired.files)
            drop_unexpected_files(artifacts=repaired, skill_plan=skill_plan)
            changed = changed or (len(repaired.files) != before)

    skill_md = find_artifact(repaired, 'SKILL.md')
    if skill_md is None:
        skill_md = ArtifactFile(
            path='SKILL.md',
            content='',
            content_type='text/markdown',
            generated_from=['repair'],
            status='repaired',
        )
        replace_artifact(repaired, skill_md)
        changed = True

    content = skill_md.content or ''

    if scoped_repair == 'description_only':
        repaired_content = repair_skill_md_frontmatter(
            content=content,
            skill_name=skill_name,
            description=description,
        )
        if repaired_content != content:
            content = repaired_content
            changed = True
    elif not diagnostics.validation.frontmatter_valid:
        content = repair_skill_md_frontmatter(
            content=content,
            skill_name=skill_name,
            description=description,
        )
        changed = True

    if scoped_repair != 'description_only' and diagnostics.validation.unreferenced_reference_files:
        content = repair_reference_navigation(
            skill_md_content=content,
            artifacts=repaired,
        )
        changed = True

    if scoped_repair != 'description_only' and not diagnostics.validation.skill_md_within_budget:
        content = repair_skill_md_budget(content=content, max_lines=max_skill_md_lines)
        changed = True

    if content != skill_md.content:
        skill_md = ArtifactFile(
            path=skill_md.path,
            content=content,
            content_type=skill_md.content_type,
            generated_from=sorted(set(list(skill_md.generated_from) + ['repair'])),
            status='repaired',
        )
        replace_artifact(repaired, skill_md)

    return RepairResult(
        applied=changed,
        repaired_artifacts=repaired,
        reason=(
            f'scoped deterministic repair applied ({scoped_repair})'
            if changed and scoped_repair
            else 'deterministic repair applied'
            if changed
            else 'no deterministic repair needed'
        ),
    )
