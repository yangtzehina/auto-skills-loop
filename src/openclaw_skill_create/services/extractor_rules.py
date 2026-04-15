from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..models.findings import CandidateResources, RepoFinding, RepoFindings
from ..models.requirements import SkillRequirement


REQUIREMENT_PRIORITY_BY_KIND = {
    'entrypoint': 90,
    'workflow': 85,
    'script': 80,
    'config': 75,
    'doc': 70,
}

ENTRYPOINT_NAMES = {
    'main',
    'app',
    'server',
    'cli',
    'index',
    'run',
    'start',
}


def extract_signal_bundle(*, request: Any, repo_context: Any) -> dict[str, Any]:
    selected_files = list(repo_context.get('selected_files', []) or [])
    script_paths = [item['path'] for item in selected_files if 'script' in item.get('tags', [])]
    doc_paths = [item['path'] for item in selected_files if 'doc' in item.get('tags', [])]
    workflow_paths = [item['path'] for item in selected_files if 'workflow' in item.get('tags', [])]
    config_paths = [item['path'] for item in selected_files if 'config' in item.get('tags', [])]

    return {
        'request_task': getattr(request, 'task', ''),
        'repo_context': repo_context,
        'signals': [
            {'kind': 'scripts', 'count': len(script_paths), 'paths': script_paths[:20]},
            {'kind': 'docs', 'count': len(doc_paths), 'paths': doc_paths[:20]},
            {'kind': 'workflows', 'count': len(workflow_paths), 'paths': workflow_paths[:20]},
            {'kind': 'configs', 'count': len(config_paths), 'paths': config_paths[:20]},
        ],
    }


def fallback_repo_findings_from_signals(signal_bundle: Any) -> RepoFindings:
    repo_context = signal_bundle.get('repo_context', {})
    repos = []
    requirements: list[SkillRequirement] = []
    for repo in repo_context.get('repos', []) or []:
        selected_files = repo.get('selected_files', []) or []
        entrypoints = [{'path': item['path']} for item in selected_files if _looks_like_entrypoint(item.get('path', ''))]
        docs = [{'path': item['path']} for item in selected_files if 'doc' in item.get('tags', [])]
        scripts = [{'path': item['path']} for item in selected_files if 'script' in item.get('tags', [])]
        configs = [{'path': item['path']} for item in selected_files if 'config' in item.get('tags', [])]
        workflows = [{'path': item['path']} for item in selected_files if 'workflow' in item.get('tags', [])]
        previews = [item.get('preview', '') for item in selected_files[:5] if item.get('preview')]
        summary = ' | '.join(previews)[:240]
        repos.append(
            RepoFinding(
                repo_path=repo['repo_path'],
                summary=summary or 'Fallback extractor summary from scanned files',
                detected_stack=sorted({item['path'].split('.')[-1] for item in selected_files if '.' in item['path']}),
                entrypoints=entrypoints,
                scripts=scripts,
                docs=docs,
                configs=configs,
                workflows=workflows,
                candidate_resources=CandidateResources(
                    references=[item['path'] for item in docs[:10]],
                    scripts=[item['path'] for item in scripts[:10]],
                ),
                risks=list(repo.get('notes', []) or []),
            )
        )
        requirements.extend(_requirements_from_selected_files(selected_files))

    return RepoFindings(
        repos=repos,
        cross_repo_signals=signal_bundle.get('signals', []),
        requirements=_dedupe_requirements(requirements),
        overall_recommendation='fallback extractor findings',
    )


def enrich_repo_findings_from_context(*, repo_context: Any, repo_findings: RepoFindings) -> RepoFindings:
    repo_map = {
        item.get('repo_path', ''): item
        for item in list((repo_context or {}).get('repos', []) or [])
        if item.get('repo_path')
    }
    enriched_repos: list[RepoFinding] = []
    derived_requirements: list[SkillRequirement] = []

    for repo in list(getattr(repo_findings, 'repos', []) or []):
        scanned = repo_map.get(repo.repo_path, {})
        selected_files = list(scanned.get('selected_files', []) or [])
        derived_entrypoints = [{'path': item.get('path', '')} for item in selected_files if _looks_like_entrypoint(item.get('path', ''))]
        if not repo.entrypoints and derived_entrypoints:
            repo = repo.model_copy(update={'entrypoints': derived_entrypoints})
        enriched_repos.append(repo)
        derived_requirements.extend(_requirements_from_selected_files(selected_files))

    requirements = list(getattr(repo_findings, 'requirements', []) or [])
    if not requirements and derived_requirements:
        requirements = _dedupe_requirements(derived_requirements)

    return repo_findings.model_copy(
        update={
            'repos': enriched_repos,
            'requirements': requirements,
        }
    )


def _looks_like_entrypoint(path: str) -> bool:
    if not path:
        return False
    pure = Path(path)
    stem = pure.stem.lower()
    if pure.parent.as_posix() in {'.', ''} and stem in ENTRYPOINT_NAMES:
        return True
    lowered = pure.as_posix().lower()
    return lowered.startswith('src/main.') or lowered.startswith('app/main.') or lowered.startswith('bin/')


def _statement_for_requirement(source_kind: str, path: str) -> str:
    if source_kind == 'entrypoint':
        return f'Explain how the primary repo entrypoint `{path}` anchors the generated skill workflow.'
    if source_kind == 'script':
        return f'Provide a deterministic helper or usage guidance aligned with `{path}`.'
    if source_kind == 'config':
        return f'Preserve configuration or schema details from `{path}` in the generated skill.'
    if source_kind == 'workflow':
        return f'Reflect the automation and execution flow defined in `{path}`.'
    return f'Carry the repo guidance from `{path}` into the generated skill references and instructions.'


def _requirement_id(source_kind: str, path: str) -> str:
    normalized = re.sub(r'[^a-z0-9]+', '-', f'{source_kind}-{path}'.lower()).strip('-')
    return normalized or f'{source_kind}-requirement'


def _requirements_from_selected_files(selected_files: list[dict[str, Any]]) -> list[SkillRequirement]:
    requirements: list[SkillRequirement] = []
    for item in selected_files:
        path = item.get('path', '')
        tags = set(item.get('tags', []) or [])
        source_kind = None
        if _looks_like_entrypoint(path):
            source_kind = 'entrypoint'
        elif 'workflow' in tags:
            source_kind = 'workflow'
        elif 'script' in tags:
            source_kind = 'script'
        elif 'config' in tags:
            source_kind = 'config'
        elif 'doc' in tags:
            source_kind = 'doc'
        if source_kind is None:
            continue
        requirements.append(
            SkillRequirement(
                requirement_id=_requirement_id(source_kind, path),
                statement=_statement_for_requirement(source_kind, path),
                evidence_paths=[path],
                source_kind=source_kind,
                priority=REQUIREMENT_PRIORITY_BY_KIND.get(source_kind, 50),
            )
        )
    requirements.sort(key=lambda item: (-item.priority, item.requirement_id))
    return _dedupe_requirements(requirements)


def _dedupe_requirements(requirements: list[SkillRequirement]) -> list[SkillRequirement]:
    seen: set[str] = set()
    ordered: list[SkillRequirement] = []
    for requirement in requirements:
        if requirement.requirement_id in seen:
            continue
        seen.add(requirement.requirement_id)
        ordered.append(requirement)
    return ordered
