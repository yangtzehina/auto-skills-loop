from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional

from ..models.artifacts import ArtifactFile
from ..models.lineage import SkillLineageManifest
from .operation_contract import contract_to_artifact, operation_helper_artifact
from .runtime_lineage import build_updated_lineage_manifest, find_parent_lineage_manifest


MAX_SCRIPT_CHARS = 4000
MAX_REFERENCE_CHARS = 6000
MAX_REFERENCE_BODY_LINES = 40
MAX_REFERENCE_KEY_POINTS = 6
MAX_SNIPPET_LINES = 12
MAX_SCRIPT_LINES = 200
SCRIPT_SUFFIX_HINTS = {
    '.py', '.sh', '.bash', '.zsh', '.js', '.ts', '.tsx', '.jsx', '.rb', '.php', '.pl', '.go', '.rs'
}
STRONG_SCRIPT_TOKENS = (
    '#!',
    'import ',
    'from ',
    'def ',
    'class ',
    'if __name__ ==',
    'print(',
    'echo ',
    'set -e',
    'function ',
    'const ',
    'let ',
    'var ',
    'export ',
    'package main',
    'fn main',
)
MARKDOWN_MARKERS = (
    '# ',
    '## ',
    '### ',
    '- ',
    '* ',
    '1. ',
    'usage:',
    'example:',
    'examples:',
    'notes:',
    'preview:',
    'summary:',
)
WRAPPER_MARKERS = (
    '## overview',
    '## key points',
    '## snippet',
    '- source repo:',
    '- source file:',
    'reference placeholder derived from planned candidate resource.',
    'placeholder helper script generated from planned candidate resource.',
)


def _selected_files(repo_context: Any) -> list[dict[str, Any]]:
    if isinstance(repo_context, dict):
        return list(repo_context.get('selected_files', []) or [])
    return list(getattr(repo_context, 'selected_files', []) or [])


def _find_source(repo_context: Any, path: str) -> Optional[dict[str, Any]]:
    for item in _selected_files(repo_context):
        if item.get('path') == path:
            return item
    target_name = Path(path).name.lower()
    for item in _selected_files(repo_context):
        source_path = item.get('path', '')
        if Path(source_path).name.lower() == target_name:
            return item
    return None


def _read_source_text(item: dict[str, Any], max_chars: int) -> str:
    absolute_path = item.get('absolute_path')
    if absolute_path:
        try:
            text = Path(absolute_path).read_text(encoding='utf-8', errors='ignore')
            return text[:max_chars]
        except Exception:
            pass
    return (item.get('preview') or '')[:max_chars]


def _reference_title(path: str) -> str:
    stem = Path(path).stem.replace('_', ' ').replace('-', ' ').strip()
    return stem.title() or 'Reference'


def _clean_reference_lines(raw: str) -> list[str]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    if lines and lines[0].startswith('#'):
        lines = lines[1:]
    return lines[:MAX_REFERENCE_BODY_LINES]


def _build_reference_overview(path: str, lines: list[str]) -> str:
    if lines:
        return lines[0]
    return f'This reference summarizes planned resource `{path}`.'


def _build_reference_key_points(lines: list[str]) -> list[str]:
    points = []
    for line in lines:
        normalized = line.lstrip('-*0123456789. ').strip()
        if not normalized:
            continue
        if normalized.startswith('```'):
            continue
        points.append(normalized)
        if len(points) >= MAX_REFERENCE_KEY_POINTS:
            break
    return points


def _build_reference_snippet(lines: list[str]) -> str:
    snippet_lines = []
    for line in lines[:MAX_SNIPPET_LINES]:
        snippet_lines.append(line)
    return '\n'.join(snippet_lines).strip()


def _normalize_reference_content(path: str, raw: str, source: Optional[dict[str, Any]]) -> str:
    title = _reference_title(path)
    repo_path = source.get('repo_path') if source else None
    lines = _clean_reference_lines(raw)
    overview = _build_reference_overview(path, lines)
    key_points = _build_reference_key_points(lines)
    snippet = _build_reference_snippet(lines)

    blocks = [f'# {title}', '']
    if repo_path:
        blocks.append(f'- Source repo: `{repo_path}`')
    blocks.append(f'- Source file: `{path}`')
    blocks.append('')
    blocks.append('## Overview')
    blocks.append('')
    blocks.append(overview)
    blocks.append('')
    blocks.append('## Key points')
    blocks.append('')

    if key_points:
        for point in key_points:
            blocks.append(f'- {point}')
    else:
        blocks.append('- Reference placeholder derived from planned candidate resource.')

    if snippet:
        blocks.append('')
        blocks.append('## Snippet')
        blocks.append('')
        blocks.append('```text')
        blocks.append(snippet)
        blocks.append('```')

    return '\n'.join(blocks).rstrip() + '\n'


def _extract_fenced_code(raw: str) -> str:
    match = re.search(r"```[A-Za-z0-9_+-]*\n(.*?)\n```", raw, flags=re.DOTALL)
    if not match:
        return ''
    return match.group(1).strip('\n')


def _looks_like_markdown_or_notes(raw: str) -> bool:
    stripped = raw.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if any(marker in lower for marker in WRAPPER_MARKERS):
        return True
    if '```' in stripped:
        return True
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if not lines:
        return False
    sample = lines[:8]
    markdown_like = sum(
        1
        for line in sample
        if any(line.lower().startswith(marker) for marker in MARKDOWN_MARKERS)
    )
    return markdown_like >= max(2, len(sample) // 2)


def _looks_like_script_text(path: str, raw: str) -> bool:
    stripped = raw.strip()
    if not stripped:
        return False

    lower = stripped.lower()
    if stripped.startswith('#!'):
        return True
    if lower.startswith('python ') or lower.startswith('bash '):
        return False
    if Path(path).suffix.lower() == '.py':
        try:
            compile(raw, path, 'exec')
            return True
        except SyntaxError:
            return False
        except Exception:
            return True
    if Path(path).suffix.lower() in SCRIPT_SUFFIX_HINTS:
        if any(token in stripped for token in STRONG_SCRIPT_TOKENS):
            return True
        if '() {' in stripped or '{\n' in stripped or '= lambda ' in stripped:
            return True
        if _looks_like_markdown_or_notes(raw):
            return False
        if any(token in stripped for token in ('=', '(', ')', '{', '}', '$', ';')):
            return True
    if any(token in stripped for token in STRONG_SCRIPT_TOKENS):
        return True
    return False


def _looks_like_wrapper_text(raw: str) -> bool:
    stripped = raw.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if any(marker in lower for marker in WRAPPER_MARKERS):
        return True
    if '```' in stripped:
        return True
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(lines) >= 2 and lines[0].startswith('# ') and lines[1].startswith('- '):
        return True
    return False


def _normalize_script_content(path: str, raw: str) -> str:
    stripped = raw.strip()
    if stripped:
        fenced = _extract_fenced_code(raw)
        if fenced and _looks_like_script_text(path, fenced):
            content = fenced
        elif _looks_like_script_text(path, raw) and not _looks_like_wrapper_text(raw):
            content = raw
        else:
            content = ''

        if content:
            lines = content.splitlines()
            if len(lines) > MAX_SCRIPT_LINES:
                content = '\n'.join(lines[:MAX_SCRIPT_LINES])
            return content if content.endswith('\n') else content + '\n'

    filename = Path(path).name
    return (
        f'# {filename}\n'
        '# Placeholder helper script generated from planned candidate resource.\n'
    )


def generate_reference_artifacts(*, repo_context: Any, skill_plan: Any) -> list[ArtifactFile]:
    artifacts: list[ArtifactFile] = []
    files = getattr(skill_plan, 'files_to_create', []) or []
    operation_contract = getattr(skill_plan, 'operation_contract', None)
    for planned in files:
        path = getattr(planned, 'path', '')
        if not path.startswith('references/'):
            continue
        if path == 'references/operations/contract.json' and operation_contract is not None:
            artifacts.append(contract_to_artifact(operation_contract))
            continue
        source = _find_source(repo_context, path)
        raw = _read_source_text(source, MAX_REFERENCE_CHARS) if source else ''
        content = _normalize_reference_content(path, raw, source)
        artifacts.append(
            ArtifactFile(
                path=path,
                content=content,
                content_type='text/markdown',
                generated_from=['skill_plan', 'repo_context'],
                status='new',
            )
        )
    return artifacts


def generate_script_artifacts(*, repo_context: Any, skill_plan: Any) -> list[ArtifactFile]:
    artifacts: list[ArtifactFile] = []
    files = getattr(skill_plan, 'files_to_create', []) or []
    operation_contract = getattr(skill_plan, 'operation_contract', None)
    skill_name = getattr(skill_plan, 'skill_name', 'generated-skill')
    for planned in files:
        path = getattr(planned, 'path', '')
        if not path.startswith('scripts/'):
            continue
        if path == 'scripts/operation_helper.py' and operation_contract is not None:
            artifacts.append(operation_helper_artifact(skill_name=skill_name, contract=operation_contract, path=path))
            continue
        source = _find_source(repo_context, path)
        raw = _read_source_text(source, MAX_SCRIPT_CHARS) if source else ''
        content = _normalize_script_content(path, raw)
        artifacts.append(
            ArtifactFile(
                path=path,
                content=content,
                content_type='text/plain',
                generated_from=['skill_plan', 'repo_context'],
                status='new',
            )
        )
    return artifacts


def _generate_openai_yaml_content(*, request: Any, skill_plan: Any) -> str:
    skill_name = getattr(skill_plan, 'skill_name', 'generated-skill')
    interface = None
    blueprints = list(getattr(request, 'online_skill_blueprints', []) or [])
    if blueprints:
        interface = getattr(blueprints[0], 'interface', None)

    display_name = getattr(interface, 'display_name', None) or skill_name
    short_description = (
        getattr(interface, 'short_description', None)
        or f'Load the repo-aware workflow for {skill_name}'
    )
    default_prompt = (
        getattr(interface, 'default_prompt', None)
        or f'Use ${skill_name} and follow its repo-aware workflow before acting.'
    )

    lines = [
        'interface:',
        f'  display_name: "{display_name}"',
        f'  short_description: "{short_description}"',
        f'  default_prompt: "{default_prompt}"',
        '',
        'dependencies:',
        '  tools: []',
    ]
    return '\n'.join(lines) + '\n'


def _slugify_skill_name(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', str(value or '').strip().lower()).strip('-')
    return slug or 'generated-skill'


def _parse_skill_version(skill_id: str | None) -> int:
    raw = str(skill_id or '').strip()
    match = re.search(r'__v(\d+)_', raw)
    if not match:
        return 0
    return int(match.group(1))


def _lineage_version(*, request: Any) -> int:
    runtime_plan = getattr(request, 'runtime_evolution_plan', None)
    parent_skill_id = getattr(request, 'parent_skill_id', None) or getattr(runtime_plan, 'parent_skill_id', None)
    parent_manifest = find_parent_lineage_manifest(
        parent_skill_id=parent_skill_id,
        repo_paths=list(getattr(request, 'repo_paths', []) or []),
    )
    if parent_manifest is not None:
        parent_version = int(parent_manifest.version or 0)
    else:
        parent_version = _parse_skill_version(parent_skill_id)
    action = str(getattr(runtime_plan, 'action', '') or '').strip()
    if action == 'patch_current':
        return parent_version + 1
    if action == 'derive_child':
        return 0
    return 0 if not parent_skill_id else parent_version


def _lineage_quality_score(*, request: Any) -> float:
    runtime_plan = getattr(request, 'runtime_evolution_plan', None)
    if runtime_plan is None:
        return 0.0
    suggestions = list(getattr(runtime_plan, 'repair_suggestions', []) or [])
    if suggestions and str(getattr(runtime_plan, 'action', '') or '') == 'patch_current':
        return 0.0
    return 0.0


def _build_lineage_manifest(*, request: Any, skill_plan: Any, payload: dict[str, Any]) -> SkillLineageManifest:
    runtime_plan = getattr(request, 'runtime_evolution_plan', None)
    parent_skill_id = getattr(request, 'parent_skill_id', None) or getattr(runtime_plan, 'parent_skill_id', None)
    parent_manifest = find_parent_lineage_manifest(
        parent_skill_id=parent_skill_id,
        repo_paths=list(getattr(request, 'repo_paths', []) or []),
    )
    version = _lineage_version(request=request)
    signature_payload = {
        'skill_name': getattr(skill_plan, 'skill_name', 'generated-skill'),
        'skill_type': getattr(skill_plan, 'skill_type', 'mixed'),
        'requirements': payload.get('requirements', []),
        'online_blueprint_sources': payload.get('online_blueprint_sources', []),
        'parent_skill_id': parent_skill_id,
        'runtime_action': getattr(runtime_plan, 'action', None),
        'runtime_reason': getattr(runtime_plan, 'reason', None),
    }
    content_sha = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    ).hexdigest()[:12]
    skill_id = f'{_slugify_skill_name(getattr(skill_plan, "skill_name", "generated-skill"))}__v{version}_{content_sha[:8]}'
    event = 'generated'
    if runtime_plan is not None:
        event = str(getattr(runtime_plan, 'action', '') or '').strip() or 'generated'
    return build_updated_lineage_manifest(
        skill_id=skill_id,
        version=version,
        parent_skill_id=parent_skill_id,
        content_sha=content_sha,
        quality_score=_lineage_quality_score(request=request),
        event=event,
        summary=(
            getattr(runtime_plan, 'summary', '')
            or getattr(runtime_plan, 'reason', '')
            or f'Initialized lineage manifest for {getattr(skill_plan, "skill_name", "generated-skill")}.'
        ),
        existing_manifest=parent_manifest,
        append_history=(event == 'patch_current' and parent_manifest is not None),
    )


def _generate_meta_json_content(*, request: Any, skill_plan: Any) -> str:
    provenance = []
    for blueprint in list(getattr(request, 'online_skill_blueprints', []) or [])[:3]:
        source = getattr(getattr(blueprint, 'provenance', None), 'skill_url', None)
        if source:
            provenance.append(source)

    payload = {
        'skill_name': getattr(skill_plan, 'skill_name', 'generated-skill'),
        'skill_type': getattr(skill_plan, 'skill_type', 'mixed'),
        'skill_archetype': getattr(skill_plan, 'skill_archetype', 'guidance'),
        'generated_by': 'skill-create-v6',
        'repo_grounded': bool(getattr(request, 'repo_paths', []) or []),
        'eval_scaffold_enabled': bool(getattr(request, 'enable_eval_scaffold', False)),
        'online_blueprint_sources': provenance,
        'requirements': [
            {
                'requirement_id': getattr(requirement, 'requirement_id', ''),
                'statement': getattr(requirement, 'statement', ''),
                'evidence_paths': list(getattr(requirement, 'evidence_paths', []) or []),
                'source_kind': getattr(requirement, 'source_kind', 'repo'),
                'priority': int(getattr(requirement, 'priority', 50) or 50),
                'satisfied_by': list(getattr(requirement, 'satisfied_by', []) or []),
            }
            for requirement in list(getattr(skill_plan, 'requirements', []) or [])[:12]
        ],
    }
    operation_contract = getattr(skill_plan, 'operation_contract', None)
    if operation_contract is not None:
        payload['operation_contract'] = {
            'backend_kind': getattr(operation_contract, 'backend_kind', 'python_backend'),
            'supports_json': bool(getattr(operation_contract, 'supports_json', False)),
            'session_model': getattr(operation_contract, 'session_model', 'stateless'),
            'mutability': getattr(operation_contract, 'mutability', 'read_only'),
            'entrypoint_hint': getattr(operation_contract, 'entrypoint_hint', None),
            'operation_groups': [
                {
                    'name': getattr(group, 'name', ''),
                    'operation_names': [getattr(item, 'name', '') for item in list(getattr(group, 'operations', []) or [])],
                }
                for group in list(getattr(operation_contract, 'operations', []) or [])
            ],
            'safety_profile': getattr(operation_contract, 'safety_profile', None).model_dump(mode='json')
            if getattr(operation_contract, 'safety_profile', None) is not None
            else {},
        }
    parent_skill_id = getattr(request, 'parent_skill_id', None)
    if parent_skill_id:
        payload['parent_skill_id'] = parent_skill_id

    runtime_plan = getattr(request, 'runtime_evolution_plan', None)
    if runtime_plan is not None:
        payload['runtime_evolution_plan'] = {
            'skill_id': getattr(runtime_plan, 'skill_id', ''),
            'action': getattr(runtime_plan, 'action', 'no_change'),
            'parent_skill_id': getattr(runtime_plan, 'parent_skill_id', None),
            'reason': getattr(runtime_plan, 'reason', ''),
            'requirement_gaps': list(getattr(runtime_plan, 'requirement_gaps', []) or []),
            'summary': getattr(runtime_plan, 'summary', ''),
        }
    lineage = _build_lineage_manifest(request=request, skill_plan=skill_plan, payload=payload)
    payload['lineage'] = lineage.model_dump(mode='json')
    return json.dumps(payload, indent=2, ensure_ascii=False) + '\n'


def generate_metadata_artifacts(*, request: Any, skill_plan: Any) -> list[ArtifactFile]:
    artifacts: list[ArtifactFile] = []
    files = getattr(skill_plan, 'files_to_create', []) or []
    for planned in files:
        path = getattr(planned, 'path', '')
        if path == 'agents/openai.yaml':
            content = _generate_openai_yaml_content(request=request, skill_plan=skill_plan)
            content_type = 'text/yaml'
        elif path == '_meta.json':
            content = _generate_meta_json_content(request=request, skill_plan=skill_plan)
            content_type = 'application/json'
        else:
            continue

        artifacts.append(
            ArtifactFile(
                path=path,
                content=content,
                content_type=content_type,
                generated_from=['skill_plan', 'online_skill_blueprints'],
                status='new',
            )
        )
    return artifacts
