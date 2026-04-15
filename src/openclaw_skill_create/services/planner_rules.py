from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.plan import ContentBudget, PlannedFile, PlanningSeed, SkillPlan
from ..models.requirements import SkillRequirement
from .operation_contract import build_operation_contract


MAX_PATTERN_ACTIONS = 6
MAX_PATTERN_REQUIRED_FILES = 12
MAX_PATTERN_OPTIONAL_FILES = 12


def _iter_repo_findings(repo_findings: Any) -> list[Any]:
    repos = getattr(repo_findings, 'repos', None)
    if repos is not None:
        return list(repos)
    if isinstance(repo_findings, dict):
        return list(repo_findings.get('repos', []) or [])
    return []


def _get_candidate_resources(repo: Any) -> tuple[list[str], list[str]]:
    resources = getattr(repo, 'candidate_resources', None)
    if resources is None and isinstance(repo, dict):
        resources = repo.get('candidate_resources', {})

    if hasattr(resources, 'references'):
        references = list(resources.references)
    elif isinstance(resources, dict):
        references = list(resources.get('references', []) or [])
    else:
        references = []

    if hasattr(resources, 'scripts'):
        scripts = list(resources.scripts)
    elif isinstance(resources, dict):
        scripts = list(resources.get('scripts', []) or [])
    else:
        scripts = []

    return references, scripts


def _iter_requirements(repo_findings: Any) -> list[SkillRequirement]:
    requirements = getattr(repo_findings, 'requirements', None)
    if requirements is not None:
        return list(requirements)
    if isinstance(repo_findings, dict):
        return list(repo_findings.get('requirements', []) or [])
    return []


def _iter_patterns(extracted_patterns: Any) -> list[Any]:
    if extracted_patterns is None:
        return []
    patterns = getattr(extracted_patterns, 'patterns', None)
    if patterns is not None:
        return list(patterns)
    if isinstance(extracted_patterns, dict):
        return list(extracted_patterns.get('patterns', []) or [])
    return []


def _get_pattern_attr(obj: Any, key: str, default=None):
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _accepted_patterns(extracted_patterns: Any) -> list[Any]:
    ranked = []
    for pattern in _iter_patterns(extracted_patterns):
        status = (_get_pattern_attr(pattern, 'status', 'candidate') or 'candidate').lower()
        if status not in {'accepted', 'candidate'}:
            continue
        applicability = _get_pattern_attr(pattern, 'applicability', None)
        priority = _get_pattern_attr(applicability, 'priority', 50) or 50
        confidence = _get_pattern_attr(pattern, 'confidence', 0.0) or 0.0
        ranked.append((priority, confidence, pattern))
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    return [pattern for _, _, pattern in ranked]


def _normalize_candidate_path(path: str) -> str:
    if not path or path == 'SKILL.md':
        return 'SKILL.md'
    lowered = path.lower()
    if (
        lowered.startswith('references/')
        or lowered.startswith('scripts/')
        or lowered.startswith('agents/')
        or lowered.startswith('evals/')
        or lowered.startswith('evaluations/')
    ):
        return path
    if lowered.endswith('.json'):
        return path
    filename = path.split('/')[-1]
    if lowered.endswith(('.md', '.markdown', '.mdx')):
        return f'references/{filename}'
    return f'scripts/{filename}'


def _append_candidate_file(
    candidate_files: list[PlannedFile],
    generation_order: list[str],
    seen_paths: set[str],
    *,
    path: str,
    purpose: str,
    source_basis: list[str],
    requirement_ids: list[str] | None = None,
) -> None:
    normalized = _normalize_candidate_path(path)
    if normalized in seen_paths:
        return
    seen_paths.add(normalized)
    candidate_files.append(
        PlannedFile(
            path=normalized,
            purpose=purpose,
            source_basis=source_basis,
            requirement_ids=list(requirement_ids or []),
        )
    )
    if normalized not in generation_order:
        generation_order.append(normalized)


def _extract_pattern_budget(extracted_patterns: Any) -> int | None:
    if extracted_patterns is None:
        return None

    recommended_defaults = _get_pattern_attr(_get_pattern_attr(extracted_patterns, 'summary', None), 'recommended_defaults', {})
    if isinstance(recommended_defaults, dict):
        raw = recommended_defaults.get('skill_md_max_lines')
        if raw is not None:
            try:
                value = int(raw)
                if value > 0:
                    return value
            except (TypeError, ValueError):
                pass

    budget_hints = []
    for pattern in _accepted_patterns(extracted_patterns):
        file_shape = _get_pattern_attr(pattern, 'file_shape', None)
        hint = _get_pattern_attr(file_shape, 'content_budget_hint', None)
        if hint is not None:
            try:
                budget_hints.append(int(hint))
            except (TypeError, ValueError):
                continue
    if budget_hints:
        return min(budget_hints)
    return None


def _iter_online_blueprints(online_skill_blueprints: Any) -> list[Any]:
    if online_skill_blueprints is None:
        return []
    if isinstance(online_skill_blueprints, list):
        return list(online_skill_blueprints)
    return list(getattr(online_skill_blueprints, 'items', []) or [])


def _collect_blueprint_rationale(online_skill_blueprints: Any, reuse_decision: Any) -> list[str]:
    if not online_skill_blueprints:
        return []

    rationale: list[str] = []
    for blueprint in _iter_online_blueprints(online_skill_blueprints)[:3]:
        provenance = _get_pattern_attr(blueprint, 'provenance', None)
        repo_full_name = _get_pattern_attr(provenance, 'repo_full_name', '')
        if repo_full_name:
            rationale.append(
                f'Online skill blueprint available: {_get_pattern_attr(blueprint, "name", "skill")} from {repo_full_name}'
            )

    if reuse_decision is not None:
        mode = _get_pattern_attr(reuse_decision, 'mode', '')
        if mode:
            rationale.append(f'Online reuse decision: {mode}')
        for note in list(_get_pattern_attr(reuse_decision, 'rationale', []) or [])[:2]:
            rationale.append(f'Reuse rationale: {note}')

    return rationale


def _append_blueprint_artifacts(
    *,
    candidate_files: list[PlannedFile],
    generation_order: list[str],
    seen_paths: set[str],
    online_skill_blueprints: Any,
) -> None:
    for blueprint in _iter_online_blueprints(online_skill_blueprints):
        blueprint_name = _get_pattern_attr(blueprint, 'name', 'online-skill')
        artifacts = list(_get_pattern_attr(blueprint, 'artifacts', []) or [])
        for artifact in artifacts:
            path = _get_pattern_attr(artifact, 'path', '')
            if not path or path == 'SKILL.md':
                continue
            if not (
                path.startswith('references/')
                or path.startswith('scripts/')
                or path.startswith('agents/')
                or path.endswith('.json')
            ):
                continue
            purpose = _get_pattern_attr(artifact, 'purpose', '') or f'Blueprint artifact from {blueprint_name}'
            _append_candidate_file(
                candidate_files,
                generation_order,
                seen_paths,
                path=path,
                purpose=purpose,
                source_basis=[f'online_skill_blueprints.{blueprint_name}.artifacts'],
            )


def _append_eval_artifacts(
    *,
    candidate_files: list[PlannedFile],
    generation_order: list[str],
    seen_paths: set[str],
) -> None:
    for path, purpose in (
        ('evals/trigger_eval.json', 'Trigger evaluation scaffold for should-trigger and should-not-trigger cases'),
        ('evals/output_eval.json', 'Output evaluation scaffold for with-skill vs baseline comparisons'),
        ('evals/benchmark.json', 'Benchmark dimensions for evaluating generated skill quality'),
    ):
        _append_candidate_file(
            candidate_files,
            generation_order,
            seen_paths,
            path=path,
            purpose=purpose,
            source_basis=['evaluation_scaffold'],
        )


def _match_requirement_targets(requirement: SkillRequirement, candidate_files: list[PlannedFile]) -> list[str]:
    paths = [file.path for file in candidate_files]
    reference_paths = [path for path in paths if path.startswith('references/')]
    script_paths = [path for path in paths if path.startswith('scripts/')]
    evidence_names = {
        Path(path).name.lower()
        for path in list(requirement.evidence_paths or [])
        if path
    }

    targets: list[str] = []
    if requirement.source_kind == 'script':
        for path in script_paths:
            if Path(path).name.lower() in evidence_names:
                targets.append(path)
        if not targets and script_paths:
            targets.append(script_paths[0])
    elif requirement.source_kind == 'doc':
        for path in reference_paths:
            if Path(path).name.lower() in evidence_names:
                targets.append(path)
        if not targets and reference_paths:
            targets.append(reference_paths[0])
    elif requirement.source_kind == 'config':
        if '_meta.json' in paths:
            targets.append('_meta.json')
        if reference_paths:
            targets.append(reference_paths[0])
    elif requirement.source_kind == 'workflow':
        if script_paths:
            targets.append(script_paths[0])
        if reference_paths:
            targets.append(reference_paths[0])
    elif requirement.source_kind == 'entrypoint':
        if script_paths:
            targets.append(script_paths[0])
    if 'SKILL.md' in paths:
        targets.append('SKILL.md')

    deduped: list[str] = []
    seen: set[str] = set()
    for path in targets:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped[:3]


def _assign_requirement_targets(
    requirements: list[SkillRequirement],
    candidate_files: list[PlannedFile],
) -> tuple[list[SkillRequirement], dict[str, list[str]]]:
    mapped: list[SkillRequirement] = []
    by_path: dict[str, list[str]] = {}
    for requirement in requirements:
        targets = _match_requirement_targets(requirement, candidate_files)
        mapped_requirement = requirement.model_copy(update={'satisfied_by': targets})
        mapped.append(mapped_requirement)
        for path in targets:
            by_path.setdefault(path, []).append(requirement.requirement_id)
    return mapped, by_path


def _collect_pattern_rationale(extracted_patterns: Any) -> list[str]:
    if extracted_patterns is None:
        return []

    rationale: list[str] = []
    pattern_set_id = _get_pattern_attr(extracted_patterns, 'pattern_set_id', '')
    if pattern_set_id:
        rationale.append(f'Pattern-aware planning seeded from extracted_patterns:{pattern_set_id}')

    aggregated_hints = _get_pattern_attr(extracted_patterns, 'aggregated_hints', None)
    planner_defaults = list(_get_pattern_attr(aggregated_hints, 'planner_defaults', []) or [])
    for hint in planner_defaults[:3]:
        rationale.append(f'Planner default: {hint}')

    action_count = 0
    for pattern in _accepted_patterns(extracted_patterns):
        title = _get_pattern_attr(pattern, 'title', _get_pattern_attr(pattern, 'pattern_id', 'pattern'))
        downstream_hints = _get_pattern_attr(pattern, 'downstream_hints', None)
        for action in list(_get_pattern_attr(downstream_hints, 'planner_actions', []) or []):
            rationale.append(f'Pattern action ({title}): {action}')
            action_count += 1
            if action_count >= MAX_PATTERN_ACTIONS:
                return rationale
    return rationale


def build_planning_seed(
    *,
    request: Any,
    repo_context: Any,
    repo_findings: Any,
    extracted_patterns: Any = None,
    online_skill_blueprints: Any = None,
    reuse_decision: Any = None,
) -> PlanningSeed:
    skill_name = getattr(request, 'skill_name_hint', None) or 'generated-skill'
    operation_contract = build_operation_contract(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        skill_name=skill_name,
    )
    skill_archetype = 'operation_backed' if operation_contract is not None else 'guidance'
    candidate_files: list[PlannedFile] = [
        PlannedFile(
            path='SKILL.md',
            purpose='Top-level skill instructions and routing guidance',
            source_basis=['repo_findings.workflows', 'repo_findings.triggers'],
        )
    ]
    rationale = ['Deterministic planning seed from repo findings']
    rationale.extend(_collect_pattern_rationale(extracted_patterns))
    rationale.extend(_collect_blueprint_rationale(online_skill_blueprints, reuse_decision))
    generation_order = ['SKILL.md']
    seen_paths = {'SKILL.md'}

    reference_targets: set[str] = set()
    script_targets: set[str] = set()
    requirements = _iter_requirements(repo_findings)

    for repo in _iter_repo_findings(repo_findings):
        references, scripts = _get_candidate_resources(repo)
        reference_targets.update(path for path in references if path and path != 'SKILL.md')
        script_targets.update(path for path in scripts if path and path != 'SKILL.md')

    for path in sorted(reference_targets):
        _append_candidate_file(
            candidate_files,
            generation_order,
            seen_paths,
            path=path,
            purpose='Detailed reference material extracted from repo candidate resources',
            source_basis=['repo_findings.candidate_resources.references'],
        )

    for path in sorted(script_targets):
        _append_candidate_file(
            candidate_files,
            generation_order,
            seen_paths,
            path=path,
            purpose='Reusable helper script selected from repo candidate resources',
            source_basis=['repo_findings.candidate_resources.scripts'],
        )

    if reference_targets:
        rationale.append('Added references/* targets from candidate_resources.references')
    if script_targets:
        rationale.append('Added scripts/* targets from candidate_resources.scripts')

    _append_blueprint_artifacts(
        candidate_files=candidate_files,
        generation_order=generation_order,
        seen_paths=seen_paths,
        online_skill_blueprints=online_skill_blueprints,
    )
    if online_skill_blueprints:
        rationale.append('Added online blueprint artifacts for reuse-aware planning')

    enable_eval_scaffold = bool(getattr(request, 'enable_eval_scaffold', False))
    if enable_eval_scaffold:
        _append_eval_artifacts(
            candidate_files=candidate_files,
            generation_order=generation_order,
            seen_paths=seen_paths,
        )
        rationale.append('Added evaluation scaffold artifacts for trigger/output benchmark checks')

    accepted_patterns = _accepted_patterns(extracted_patterns)
    required_added = 0
    optional_added = 0
    for pattern in accepted_patterns:
        title = _get_pattern_attr(pattern, 'title', _get_pattern_attr(pattern, 'pattern_id', 'pattern'))
        file_shape = _get_pattern_attr(pattern, 'file_shape', None)
        for path in list(_get_pattern_attr(file_shape, 'required_files', []) or []):
            if path == 'SKILL.md':
                continue
            _append_candidate_file(
                candidate_files,
                generation_order,
                seen_paths,
                path=path,
                purpose=f'Pattern-required artifact from {title}',
                source_basis=[f'extracted_patterns.patterns.{_get_pattern_attr(pattern, "pattern_id", title)}.file_shape.required_files'],
            )
            required_added += 1
            if required_added >= MAX_PATTERN_REQUIRED_FILES:
                break
        for path in list(_get_pattern_attr(file_shape, 'optional_files', []) or []):
            if path == 'SKILL.md':
                continue
            _append_candidate_file(
                candidate_files,
                generation_order,
                seen_paths,
                path=path,
                purpose=f'Pattern-optional artifact from {title}',
                source_basis=[f'extracted_patterns.patterns.{_get_pattern_attr(pattern, "pattern_id", title)}.file_shape.optional_files'],
            )
            optional_added += 1
            if optional_added >= MAX_PATTERN_OPTIONAL_FILES:
                break

    budget = ContentBudget()
    extracted_budget = _extract_pattern_budget(extracted_patterns)
    if extracted_budget is not None:
        budget.skill_md_max_lines = extracted_budget
        rationale.append(f'Applied pattern-derived SKILL.md budget={extracted_budget}')

    mapped_requirements, requirement_paths = _assign_requirement_targets(requirements, candidate_files)
    if mapped_requirements:
        rationale.append(f'Mapped {len(mapped_requirements)} repo-grounded requirements into planned artifacts')
        for file in candidate_files:
            requirement_ids = list(requirement_paths.get(file.path, []) or [])
            if requirement_ids:
                file.requirement_ids = requirement_ids

    if operation_contract is not None:
        rationale.append(
            'Operation-backed planning selected from stable repo operation surface '
            f'(backend_kind={operation_contract.backend_kind}; session_model={operation_contract.session_model})'
        )
        _append_candidate_file(
            candidate_files,
            generation_order,
            seen_paths,
            path='references/operations/contract.json',
            purpose='Machine-readable operation contract derived from the repo operation surface',
            source_basis=['operation_contract'],
        )
        _append_candidate_file(
            candidate_files,
            generation_order,
            seen_paths,
            path='evals/operation_validation.json',
            purpose='Operation-backed validation scaffold derived from the operation contract',
            source_basis=['operation_contract'],
        )
        _append_candidate_file(
            candidate_files,
            generation_order,
            seen_paths,
            path='evals/operation_coverage.json',
            purpose='Operation-backed coverage report derived from the operation contract and generated surface',
            source_basis=['operation_contract'],
        )
        if operation_contract.backend_kind != 'repo_native_cli':
            _append_candidate_file(
                candidate_files,
                generation_order,
                seen_paths,
                path='scripts/operation_helper.py',
                purpose='Thin helper exposing the detected operation surface without packaging a new CLI',
                source_basis=['operation_contract'],
            )
            rationale.append('Added thin operation helper because the repo exposes a backend surface without a stable native CLI')

    return PlanningSeed(
        suggested_skill_name=skill_name,
        suggested_skill_type='tool-guide' if operation_contract is not None else 'mixed',
        suggested_skill_archetype=skill_archetype,
        candidate_files=candidate_files,
        requirements=mapped_requirements,
        operation_contract=operation_contract,
        rationale=rationale,
        generation_order=generation_order,
    )


def fallback_skill_plan_from_seed(seed: PlanningSeed) -> SkillPlan:
    why_this_shape = 'Fallback planner used deterministic seed output.'
    if seed.rationale:
        why_this_shape = ' | '.join([why_this_shape] + seed.rationale[:6])

    budget = ContentBudget()
    for line in seed.rationale:
        marker = 'Applied pattern-derived SKILL.md budget='
        if line.startswith(marker):
            try:
                budget.skill_md_max_lines = int(line.split('=', 1)[1])
            except (TypeError, ValueError):
                pass
            break

    return SkillPlan(
        skill_name=seed.suggested_skill_name,
        skill_type=seed.suggested_skill_type,
        skill_archetype=seed.suggested_skill_archetype,
        objective='Generate a repo-aware skill from grounded findings',
        why_this_shape=why_this_shape,
        requirements=seed.requirements,
        operation_contract=seed.operation_contract,
        files_to_create=seed.candidate_files,
        files_to_update=[],
        files_to_keep=[],
        content_budget=budget,
        generation_order=seed.generation_order or [f.path for f in seed.candidate_files],
    )
