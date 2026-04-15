from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Callable, Iterable, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..models.online import (
    SkillBlueprint,
    SkillBlueprintArtifact,
    SkillBlueprintSection,
    SkillDependency,
    SkillInterfaceMetadata,
    SkillProvenance,
    SkillReuseDecision,
    SkillSourceCandidate,
)


FetchText = Callable[[str], str]


class DiscoveryProvider(Protocol):
    provider_name: str

    def list_candidates(self, *, fetch_text: FetchText | None = None) -> list[SkillSourceCandidate]:
        ...


STOPWORDS = {
    'a',
    'an',
    'and',
    'are',
    'as',
    'at',
    'be',
    'by',
    'for',
    'from',
    'how',
    'i',
    'in',
    'into',
    'is',
    'it',
    'me',
    'my',
    'of',
    'on',
    'or',
    'our',
    'page',
    'repo',
    'repository',
    'skill',
    'system',
    'task',
    'that',
    'the',
    'this',
    'to',
    'use',
    'user',
    'when',
    'with',
}

GITHUB_API_HEADERS = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'openclaw-skill-create-v6',
}

GITHUB_HTML_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (compatible; openclaw-skill-create-v6/1.0)',
}

FETCH_TEXT_CACHE: dict[str, str] = {}

DISCOVERY_DIR_BLACKLIST = {
    '.git',
    '.github',
    '.venv',
    '__pycache__',
    'assets',
    'build',
    'dist',
    'docs',
    'examples',
    'node_modules',
    'references',
    'scripts',
    'test',
    'tests',
    'vendor',
}


REMOTE_SKILL_CATALOG: tuple[SkillSourceCandidate, ...] = (
    SkillSourceCandidate(
        candidate_id='openai-figma-use',
        name='figma-use',
        description='Mandatory prerequisite before use_figma MCP calls for Figma write operations, design-system work, variables, and component automation.',
        trigger_phrases=['figma', 'use_figma', 'design system', 'variables', 'components', 'tokens'],
        tags=['figma', 'design', 'mcp', 'components', 'variables'],
        dependencies=[SkillDependency(kind='mcp', value='figma', description='Figma MCP server')],
        provenance=SkillProvenance(
            source_type='official',
            ecosystem='codex',
            repo_full_name='openai/skills',
            skill_path='skills/.curated/figma-use',
            skill_url='https://github.com/openai/skills/blob/main/skills/.curated/figma-use/SKILL.md',
            source_license='Per-skill LICENSE.txt',
            source_attribution='OpenAI curated skills',
        ),
    ),
    SkillSourceCandidate(
        candidate_id='openai-notion-knowledge-capture',
        name='notion-knowledge-capture',
        description='Capture conversations and decisions into structured Notion pages with templates, database schemas, and linking workflows.',
        trigger_phrases=['notion', 'knowledge capture', 'decision record', 'wiki', 'faq', 'meeting notes'],
        tags=['notion', 'knowledge-base', 'documentation', 'decision-log', 'capture'],
        dependencies=[SkillDependency(kind='mcp', value='notion', description='Notion MCP server')],
        provenance=SkillProvenance(
            source_type='official',
            ecosystem='codex',
            repo_full_name='openai/skills',
            skill_path='skills/.curated/notion-knowledge-capture',
            skill_url='https://github.com/openai/skills/blob/main/skills/.curated/notion-knowledge-capture/SKILL.md',
            source_license='Per-skill LICENSE.txt',
            source_attribution='OpenAI curated skills',
        ),
    ),
    SkillSourceCandidate(
        candidate_id='feiskyer-deep-research',
        name='deep-research',
        description='Deep research orchestration workflow that decomposes research goals into parallel subtasks and aggregates polished reports.',
        trigger_phrases=['deep research', 'research', 'competitor analysis', 'industry analysis', 'multi-agent research'],
        tags=['research', 'orchestration', 'parallel', 'reporting'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='feiskyer/codex-settings',
            skill_path='skills/deep-research',
            skill_url='https://github.com/feiskyer/codex-settings/blob/main/skills/deep-research/SKILL.md',
            source_license='MIT',
            source_attribution='feiskyer/codex-settings',
        ),
    ),
    SkillSourceCandidate(
        candidate_id='feiskyer-spec-kit-skill',
        name='spec-kit-skill',
        description='Constitution-based spec-driven development workflow for requirements, planning, tasks, analysis, and implementation.',
        trigger_phrases=['spec-kit', 'speckit', 'constitution', 'specify', '.specify'],
        tags=['planning', 'spec-driven', 'requirements', 'constitution'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='feiskyer/codex-settings',
            skill_path='skills/spec-kit-skill',
            skill_url='https://github.com/feiskyer/codex-settings/blob/main/skills/spec-kit-skill/SKILL.md',
            source_license='MIT',
            source_attribution='feiskyer/codex-settings',
        ),
    ),
    SkillSourceCandidate(
        candidate_id='feiskyer-kiro-skill',
        name='kiro-skill',
        description='Interactive feature development workflow from rough idea through requirements, design, and task plans.',
        trigger_phrases=['kiro', '.kiro/specs', 'requirements', 'design document', 'implementation plan'],
        tags=['planning', 'requirements', 'design', 'tasks'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='feiskyer/codex-settings',
            skill_path='skills/kiro-skill',
            skill_url='https://github.com/feiskyer/codex-settings/blob/main/skills/kiro-skill/SKILL.md',
            source_license='MIT',
            source_attribution='feiskyer/codex-settings',
        ),
    ),
    SkillSourceCandidate(
        candidate_id='nskills-orchestration',
        name='orchestration',
        description='Multi-agent orchestration for complex tasks with task decomposition, dependency tracking, and worker prompts.',
        trigger_phrases=['orchestration', 'parallel work', 'multi-agent', 'coordination', 'subtasks'],
        tags=['orchestration', 'multi-agent', 'parallel', 'workflow'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='agent-skills',
            repo_full_name='numman-ali/n-skills',
            skill_path='skills/workflow/orchestration/skills/orchestration',
            skill_url='https://github.com/numman-ali/n-skills/blob/main/skills/workflow/orchestration/skills/orchestration/SKILL.md',
            source_license='Apache-2.0',
            source_attribution='numman-ali/n-skills',
        ),
    ),
    SkillSourceCandidate(
        candidate_id='nskills-gastown',
        name='gastown',
        description='Operational manual for the Gas Town multi-agent system including setup, workflows, and command execution patterns.',
        trigger_phrases=['gastown', 'gas town', 'gt', 'convoys', 'polecats', 'beads'],
        tags=['tools', 'multi-agent', 'operations', 'cli'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='agent-skills',
            repo_full_name='numman-ali/n-skills',
            skill_path='skills/tools/gastown/skills/gastown',
            skill_url='https://github.com/numman-ali/n-skills/blob/main/skills/tools/gastown/skills/gastown/SKILL.md',
            source_license='Apache-2.0',
            source_attribution='numman-ali/n-skills',
        ),
    ),
)

KNOWN_SKILL_COLLECTIONS: tuple[dict[str, Any], ...] = (
    {
        'repo_full_name': 'openai/skills',
        'ecosystem': 'codex',
        'root_paths': ['skills'],
        'priority': 10,
    },
    {
        'repo_full_name': 'feiskyer/codex-settings',
        'ecosystem': 'codex',
        'root_paths': ['skills'],
        'priority': 30,
    },
    {
        'repo_full_name': 'numman-ali/n-skills',
        'ecosystem': 'agent-skills',
        'root_paths': ['skills'],
        'priority': 30,
    },
    {
        'repo_full_name': 'Orchestra-Research/AI-Research-SKILLs',
        'ecosystem': 'ai-research',
        'root_paths': [''],
        'priority': 40,
    },
    {
        'repo_full_name': 'foryourhealth111-pixel/Vibe-Skills',
        'ecosystem': 'codex',
        'root_paths': ['bundled/skills'],
        'priority': 35,
    },
    {
        'repo_full_name': 'xjtulyc/awesome-rosetta-skills',
        'ecosystem': 'ai-research',
        'root_paths': ['skills'],
        'priority': 40,
    },
    {
        'repo_full_name': 'cnfjlhj/ai-collab-playbook',
        'ecosystem': 'codex',
        'root_paths': ['skills/full'],
        'priority': 20,
    },
    {
        'repo_full_name': 'nexscope-ai/Amazon-Skills',
        'ecosystem': 'codex',
        'root_paths': [''],
        'root_dir_prefixes': ['amazon-', 'tariff-'],
        'priority': 20,
    },
    {
        'repo_full_name': 'aaron-he-zhu/seo-geo-claude-skills',
        'ecosystem': 'codex',
        'root_paths': ['research', 'build', 'optimize', 'monitor', 'cross-cutting'],
        'priority': 20,
    },
    {
        'repo_full_name': 'huggingface/skills',
        'ecosystem': 'codex',
        'root_paths': ['skills', 'hf-mcp/skills'],
        'priority': 10,
    },
    {
        'repo_full_name': 'K-Dense-AI/claude-scientific-skills',
        'ecosystem': 'claude',
        'root_paths': [''],
        'priority': 30,
    },
    {
        'repo_full_name': 'alirezarezvani/claude-skills',
        'ecosystem': 'claude',
        'root_paths': ['skills', '.claude/skills', ''],
        'priority': 35,
    },

)

SEMANTIC_TOKEN_GROUPS: tuple[set[str], ...] = (
    {'research', 'analysis', 'evidence', 'investigation', 'literature'},
    {'plan', 'planning', 'milestone', 'milestones', 'task', 'tasks', 'requirements', 'implementation', 'roadmap'},
    {'evaluate', 'evaluation', 'eval', 'benchmark', 'judge', 'judging', 'scoring'},
    {'capture', 'document', 'documentation', 'record', 'records', 'notes', 'wiki', 'notion', 'sync'},
    {'orchestrate', 'orchestration', 'multi-agent', 'multiagent', 'parallel', 'worker', 'workers'},
)


class StaticCatalogDiscoveryProvider:
    provider_name = 'static-catalog'

    def __init__(self, catalog: Iterable[SkillSourceCandidate]):
        self._catalog = list(catalog)

    def list_candidates(self, *, fetch_text: FetchText | None = None) -> list[SkillSourceCandidate]:
        return [candidate.model_copy() for candidate in self._catalog]


class JsonManifestDiscoveryProvider:
    provider_name = 'json-manifest'

    def __init__(self, manifest_urls: Iterable[str]):
        self._manifest_urls = list(manifest_urls)

    def list_candidates(self, *, fetch_text: FetchText | None = None) -> list[SkillSourceCandidate]:
        fetch_text = fetch_text or default_fetch_text
        discovered: list[SkillSourceCandidate] = []
        for manifest_url in self._manifest_urls:
            raw = fetch_text(manifest_url)
            payload = json.loads(raw)
            for index, item in enumerate(payload if isinstance(payload, list) else payload.get('candidates', [])):
                candidate_payload = dict(item)
                candidate_payload.setdefault('candidate_id', f'manifest-{index}')
                candidate = SkillSourceCandidate.model_validate(candidate_payload)
                discovered.append(candidate)
        return discovered


class GitHubCollectionDiscoveryProvider:
    provider_name = 'github-collections'

    def __init__(
        self,
        *,
        collections: Optional[Iterable[dict[str, Any]]] = None,
        max_candidates: int = 16,
        max_candidates_per_collection: int = 4,
    ):
        raw_collections = list(collections or KNOWN_SKILL_COLLECTIONS)
        self._collections = _sort_collection_seeds(raw_collections)
        self._max_candidates = max_candidates
        self._max_candidates_per_collection = max(1, max_candidates_per_collection)

    def list_candidates(self, *, fetch_text: FetchText | None = None) -> list[SkillSourceCandidate]:
        fetch_text = fetch_text or default_fetch_text
        discovered: list[SkillSourceCandidate] = []
        seen_candidates: set[str] = set()

        for seed in self._collections:
            if len(discovered) >= self._max_candidates:
                break
            repo_full_name = str(seed.get('repo_full_name', '') or '').strip()
            if not repo_full_name:
                continue
            repo_payload = _fetch_repo_metadata(repo_full_name, fetch_text=fetch_text)
            if not repo_payload:
                continue
            entries = _discover_repo_skill_entries(
                repo_payload,
                fetch_text=fetch_text,
                max_skills=min(
                    self._max_candidates_per_collection,
                    max(1, self._max_candidates - len(discovered)),
                ),
                root_paths=seed.get('root_paths') or [''],
                root_dir_prefixes=seed.get('root_dir_prefixes') or [],
            )
            for entry in entries:
                candidate = _make_live_candidate(entry, fetch_text=fetch_text)
                if candidate is None:
                    continue
                key = f'{candidate.provenance.repo_full_name}::{candidate.provenance.skill_path or "."}'
                if key in seen_candidates:
                    continue
                seen_candidates.add(key)
                ecosystem = seed.get('ecosystem')
                if ecosystem:
                    candidate = candidate.model_copy(
                        update={
                            'provenance': candidate.provenance.model_copy(
                                update={'ecosystem': ecosystem}
                            )
                        }
                    )
                discovered.append(candidate)
                if len(discovered) >= self._max_candidates:
                    break

        return discovered


def default_fetch_text(url: str) -> str:
    if url in FETCH_TEXT_CACHE:
        return FETCH_TEXT_CACHE[url]
    headers = GITHUB_API_HEADERS if 'api.github.com' in url else GITHUB_HTML_HEADERS
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        text = response.read().decode('utf-8')
    if any(host in url for host in ('api.github.com', 'github.com', 'raw.githubusercontent.com')):
        FETCH_TEXT_CACHE[url] = text
    return text


def _fetch_json(url: str, *, fetch_text: FetchText | None = None) -> Any:
    fetch_text = fetch_text or default_fetch_text
    return json.loads(fetch_text(url))


def _build_repo_search_queries(task: str) -> list[str]:
    tokens = _unique(_normalize_tokens(task))[:4]
    token_query = ' '.join(tokens)
    queries = [
        f'{token_query} codex skill'.strip(),
        f'{token_query} agent skill'.strip(),
        f'{token_query} openclaw skill'.strip(),
        'codex skill',
    ]
    return _unique(query for query in queries if query.strip())


def _repo_is_skill_relevant(repo_payload: dict[str, Any]) -> bool:
    if repo_payload.get('private') or repo_payload.get('fork') or repo_payload.get('archived') or repo_payload.get('disabled'):
        return False

    text = ' '.join(
        [
            str(repo_payload.get('name', '')),
            str(repo_payload.get('full_name', '')),
            str(repo_payload.get('description', '')),
            ' '.join(repo_payload.get('topics', []) or []),
        ]
    ).lower()
    return any(token in text for token in ('skill', 'skills', 'codex', 'openclaw', 'claude', 'agent', 'mcp'))


def _repo_contents_url(repo_full_name: str, *, path: str = '', ref: str = 'main') -> str:
    encoded_path = urllib.parse.quote(path, safe='/')
    if encoded_path:
        return f'https://api.github.com/repos/{repo_full_name}/contents/{encoded_path}?ref={urllib.parse.quote(ref)}'
    return f'https://api.github.com/repos/{repo_full_name}/contents?ref={urllib.parse.quote(ref)}'


def _repo_metadata_url(repo_full_name: str) -> str:
    return f'https://api.github.com/repos/{repo_full_name}'


def _repo_html_url(repo_full_name: str, *, ref: str = 'main', path: str = '') -> str:
    base = f'https://github.com/{repo_full_name}/tree/{urllib.parse.quote(ref)}'
    encoded_path = urllib.parse.quote(path, safe='/')
    if encoded_path:
        return f'{base}/{encoded_path}'
    return base


def _repo_home_html_url(repo_full_name: str) -> str:
    return f'https://github.com/{repo_full_name}'


def _list_repo_contents(
    repo_full_name: str,
    *,
    path: str = '',
    ref: str = 'main',
    fetch_text: FetchText | None = None,
) -> list[dict[str, Any]]:
    try:
        payload = _fetch_json(_repo_contents_url(repo_full_name, path=path, ref=ref), fetch_text=fetch_text)
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        return _list_repo_contents_via_html(repo_full_name, path=path, ref=ref, fetch_text=fetch_text)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _fetch_repo_metadata(repo_full_name: str, *, fetch_text: FetchText | None = None) -> dict[str, Any]:
    try:
        payload = _fetch_json(_repo_metadata_url(repo_full_name), fetch_text=fetch_text)
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        return _fetch_repo_metadata_via_html(repo_full_name, fetch_text=fetch_text)
    return payload if isinstance(payload, dict) else {}


def _is_collection_category(path_segment: str) -> bool:
    return bool(re.match(r'^\d+[-_][a-z0-9._-]+$', (path_segment or '').lower()))


def _list_repo_contents_via_html(
    repo_full_name: str,
    *,
    path: str = '',
    ref: str = 'main',
    fetch_text: FetchText | None = None,
) -> list[dict[str, Any]]:
    fetch_text = fetch_text or default_fetch_text
    try:
        html = fetch_text(_repo_html_url(repo_full_name, ref=ref, path=path))
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        return []

    current_path = (path or '').strip('/')
    dir_pattern = re.compile(
        rf'href="/{re.escape(repo_full_name)}/tree/{re.escape(ref)}/([^"#?]+)"'
    )
    file_pattern = re.compile(
        rf'href="/{re.escape(repo_full_name)}/blob/{re.escape(ref)}/([^"#?]+)"'
    )

    entries: dict[tuple[str, str], dict[str, Any]] = {}

    def register(match_path: str, entry_type: str) -> None:
        decoded = urllib.parse.unquote(match_path)
        if current_path:
            prefix = current_path + '/'
            if not decoded.startswith(prefix):
                return
            remainder = decoded[len(prefix) :]
        else:
            remainder = decoded
        if not remainder:
            return
        child_name = remainder.split('/', 1)[0]
        child_path = f'{current_path}/{child_name}' if current_path else child_name
        key = (entry_type, child_path)
        if key in entries:
            return
        entry: dict[str, Any] = {
            'name': child_name,
            'path': child_path,
            'type': entry_type,
            'html_url': (
                f'https://github.com/{repo_full_name}/tree/{ref}/{child_path}'
                if entry_type == 'dir'
                else f'https://github.com/{repo_full_name}/blob/{ref}/{child_path}'
            ),
        }
        if entry_type == 'file':
            entry['download_url'] = f'https://raw.githubusercontent.com/{repo_full_name}/{ref}/{child_path}'
        entries[key] = entry

    for match in dir_pattern.findall(html):
        register(match, 'dir')
    for match in file_pattern.findall(html):
        register(match, 'file')

    return list(entries.values())


def _fetch_repo_metadata_via_html(repo_full_name: str, *, fetch_text: FetchText | None = None) -> dict[str, Any]:
    fetch_text = fetch_text or default_fetch_text
    try:
        html = fetch_text(_repo_home_html_url(repo_full_name))
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        return {}

    description_match = re.search(r'<meta name="description" content="([^"]+)"', html)
    branch_match = re.search(r'"defaultBranch":"([^"]+)"', html)
    return {
        'full_name': repo_full_name,
        'name': repo_full_name.split('/', 1)[-1],
        'description': description_match.group(1).strip() if description_match else '',
        'default_branch': branch_match.group(1).strip() if branch_match else 'main',
        'private': False,
        'fork': False,
        'archived': False,
        'disabled': False,
        'topics': [],
        'license': {},
    }


def _search_repositories_via_html(
    query: str,
    *,
    fetch_text: FetchText | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    fetch_text = fetch_text or default_fetch_text
    url = f'https://github.com/search?q={urllib.parse.quote(query)}&type=repositories'
    try:
        html = fetch_text(url)
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        return []

    embedded_match = re.search(
        r'<script type="application/json" data-target="react-app\.embeddedData">(.*?)</script>',
        html,
        re.S,
    )
    if not embedded_match:
        return []

    try:
        payload = json.loads(embedded_match.group(1))
    except json.JSONDecodeError:
        return []

    results = (((payload or {}).get('payload') or {}).get('results') or [])
    repos: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        repository = (((item.get('repo') or {}).get('repository')) or {})
        owner = repository.get('owner_login')
        name = repository.get('name')
        if not owner or not name:
            continue
        repos.append(
            {
                'name': name,
                'full_name': f'{owner}/{name}',
                'description': re.sub(r'<[^>]+>', '', item.get('hl_trunc_description') or ''),
                'private': not bool(item.get('public', True)),
                'fork': False,
                'archived': bool(item.get('archived')),
                'disabled': False,
                'default_branch': 'main',
                'topics': list(item.get('topics') or []),
                'license': {},
            }
        )
        if len(repos) >= max(limit, 1):
            break
    return repos


def _should_descend_repo_dir(*, parent_path: str, child_name: str, child_path: str, depth: int) -> bool:
    lowered_name = child_name.lower()
    lowered_path = child_path.lower()
    parent_parts = [part.lower() for part in parent_path.split('/') if part]
    if lowered_name in DISCOVERY_DIR_BLACKLIST:
        return False
    if depth >= 5:
        return False
    if parent_path in {'.codex', '.openclaw'} and lowered_name == 'skills':
        return True
    if any(_is_collection_category(part) for part in parent_parts):
        return True
    if lowered_name in {'workflow', 'workflows', 'tools', '.curated', 'curated', 'collections', 'library'}:
        return True
    if (
        parent_path.startswith('skills')
        or parent_path.startswith('.codex/skills')
        or parent_path.startswith('.openclaw/skills')
        or parent_path.endswith('/skills')
        or '/skills/' in parent_path
    ):
        return True
    if depth == 0:
        return (
            lowered_name in {'skills', '.codex', 'codex', 'openclaw', 'claude', '.openclaw', 'agents'}
            or 'skill' in lowered_name
            or _is_collection_category(lowered_name)
        )
    return 'skill' in lowered_path


def _discover_repo_skill_entries(
    repo_payload: dict[str, Any],
    *,
    fetch_text: FetchText | None = None,
    max_dirs: int = 24,
    max_skills: int = 8,
    root_paths: Optional[Iterable[str]] = None,
    root_dir_prefixes: Optional[Iterable[str]] = None,
) -> list[dict[str, Any]]:
    repo_full_name = repo_payload.get('full_name', '')
    ref = repo_payload.get('default_branch', 'main') or 'main'
    queue: list[tuple[str, int]] = [
        (
            (path or '').strip('/'),
            len([part for part in (path or '').strip('/').split('/') if part]),
        )
        for path in list(root_paths or [''])
    ] or [('', 0)]
    visited: set[str] = set()
    discovered: list[dict[str, Any]] = []
    trusted_root_paths = {
        (path or '').strip('/')
        for path in list(root_paths or [''])
        if (path or '').strip('/')
    }

    while queue and len(visited) < max_dirs and len(discovered) < max_skills:
        current_path, depth = queue.pop(0)
        if current_path in visited:
            continue
        visited.add(current_path)

        entries = _list_repo_contents(repo_full_name, path=current_path, ref=ref, fetch_text=fetch_text)
        if not entries:
            continue

        for entry in entries:
            if entry.get('type') == 'file' and entry.get('name') == 'SKILL.md':
                discovered.append(
                    {
                        'skill_path': current_path,
                        'skill_file': entry,
                        'repo': repo_payload,
                    }
                )
                if len(discovered) >= max_skills:
                    break

        if len(discovered) >= max_skills:
            break

        child_dirs: list[tuple[str, int]] = []
        for entry in entries:
            if entry.get('type') != 'dir':
                continue
            child_name = entry.get('name', '')
            child_path = entry.get('path', '')
            should_descend = _should_descend_repo_dir(
                parent_path=current_path,
                child_name=child_name,
                child_path=child_path,
                depth=depth,
            )
            if not should_descend and depth == 0:
                lowered_name = child_name.lower()
                should_descend = any(
                    lowered_name.startswith((prefix or '').strip().lower())
                    for prefix in (root_dir_prefixes or [])
                    if (prefix or '').strip()
                )
            if (
                not should_descend
                and current_path in trusted_root_paths
                and child_name.lower() not in DISCOVERY_DIR_BLACKLIST
                and depth < 5
            ):
                should_descend = True
            if should_descend:
                child_dirs.append((child_path, depth + 1))
        if child_dirs:
            # Prefer descending into the current branch before scanning every sibling
            # so large categorized collections can still surface leaf skills within
            # the traversal budget.
            queue = child_dirs + queue

    return discovered


def _collection_priority(seed: dict[str, Any]) -> int:
    priority = seed.get('priority', 100)
    try:
        return int(priority)
    except (TypeError, ValueError):
        return 100


def _sort_collection_seeds(collections: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = list(enumerate(collections))
    indexed.sort(key=lambda item: (_collection_priority(item[1]), item[0]))
    return [seed for _index, seed in indexed]


def _derive_trigger_phrases(*, name: str, description: str) -> list[str]:
    phrases = [name, name.replace('-', ' ')]
    lowered = description.lower()
    if 'use when' in lowered:
        snippet = description[lowered.index('use when') :].split('.', 1)[0].strip()
        if snippet:
            phrases.append(snippet)
    return _unique(phrase for phrase in phrases if phrase)


def _derive_candidate_tags(*, repo_payload: dict[str, Any], skill_path: str, name: str) -> list[str]:
    raw = ' '.join(
        [
            name,
            skill_path.replace('/', ' '),
            repo_payload.get('name', ''),
            ' '.join(repo_payload.get('topics', []) or []),
        ]
    )
    return _unique(_normalize_tokens(raw))[:8]


def _make_live_candidate(entry: dict[str, Any], *, fetch_text: FetchText | None = None) -> SkillSourceCandidate | None:
    repo_payload = entry.get('repo', {}) or {}
    repo_full_name = repo_payload.get('full_name', '')
    skill_path = entry.get('skill_path', '') or ''
    skill_file = entry.get('skill_file', {}) or {}
    ref = repo_payload.get('default_branch', 'main') or 'main'

    download_url = skill_file.get('download_url') or ''
    try:
        raw_skill = (fetch_text or default_fetch_text)(download_url) if download_url else ''
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        raw_skill = ''

    frontmatter, _body = _parse_frontmatter(raw_skill)
    fallback_name = skill_path.rsplit('/', 1)[-1] if skill_path else repo_payload.get('name', 'discovered-skill')
    name = frontmatter.get('name') or fallback_name
    description = frontmatter.get('description') or repo_payload.get('description') or f'Live discovered skill from {repo_full_name}'
    skill_url = skill_file.get('html_url') or _github_blob_url(repo_full_name, ref=ref, skill_path=skill_path, filename='SKILL.md')
    candidate_key = f"{repo_full_name}::{skill_path or '.'}"

    return SkillSourceCandidate(
        candidate_id=re.sub(r'[^a-zA-Z0-9._-]+', '-', candidate_key),
        name=name,
        description=description,
        trigger_phrases=_derive_trigger_phrases(name=name, description=description),
        tags=_derive_candidate_tags(repo_payload=repo_payload, skill_path=skill_path, name=name),
        provenance=SkillProvenance(
            source_type='official' if repo_full_name == 'openai/skills' else 'community',
            ecosystem='codex',
            repo_full_name=repo_full_name,
            ref=ref,
            skill_path=skill_path,
            skill_url=skill_url,
            source_license=((repo_payload.get('license') or {}).get('spdx_id') or '').strip() or None,
            source_attribution=repo_full_name or None,
        ),
    )


class GitHubRepoSearchDiscoveryProvider:
    provider_name = 'github-repo-search'

    def __init__(
        self,
        *,
        task: str,
        max_repos: int = 6,
        max_candidates: int = 8,
        max_candidates_per_repo: int = 3,
    ):
        self._task = task
        self._max_repos = max_repos
        self._max_candidates = max_candidates
        self._max_candidates_per_repo = max(1, max_candidates_per_repo)

    def list_candidates(self, *, fetch_text: FetchText | None = None) -> list[SkillSourceCandidate]:
        fetch_text = fetch_text or default_fetch_text
        repos: list[dict[str, Any]] = []
        seen_repos: set[str] = set()

        for query in _build_repo_search_queries(self._task):
            url = (
                'https://api.github.com/search/repositories'
                f'?q={urllib.parse.quote(query)}&per_page={max(self._max_repos, 1)}&sort=stars&order=desc'
            )
            try:
                payload = _fetch_json(url, fetch_text=fetch_text)
                query_repos = list(payload.get('items', []) or [])
            except (HTTPError, URLError, ValueError, TimeoutError, OSError):
                query_repos = _search_repositories_via_html(query, fetch_text=fetch_text, limit=self._max_repos)
            for repo in query_repos:
                full_name = repo.get('full_name', '')
                if not full_name or full_name in seen_repos:
                    continue
                if not _repo_is_skill_relevant(repo):
                    continue
                seen_repos.add(full_name)
                repos.append(repo)
                if len(repos) >= self._max_repos:
                    break
            if len(repos) >= self._max_repos:
                break

        discovered: list[SkillSourceCandidate] = []
        seen_candidates: set[str] = set()
        for repo in repos:
            entries = _discover_repo_skill_entries(
                repo,
                fetch_text=fetch_text,
                max_skills=min(
                    self._max_candidates_per_repo,
                    max(1, self._max_candidates - len(discovered)),
                ),
            )
            for entry in entries:
                candidate = _make_live_candidate(entry, fetch_text=fetch_text)
                if candidate is None:
                    continue
                key = f'{candidate.provenance.repo_full_name}::{candidate.provenance.skill_path or "."}'
                if key in seen_candidates:
                    continue
                seen_candidates.add(key)
                discovered.append(candidate)
                if len(discovered) >= self._max_candidates:
                    return discovered

        return discovered


def _normalize_tokens(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r'[a-z0-9][a-z0-9_+-]{1,}', text.lower())
    return [token for token in tokens if token not in STOPWORDS]


def _expand_semantic_tokens(tokens: Iterable[str]) -> set[str]:
    expanded = set(tokens)
    for token in list(expanded):
        for group in SEMANTIC_TOKEN_GROUPS:
            if token in group:
                expanded.update(group)
    return expanded


def _repo_signals(repo_context: Any) -> list[str]:
    selected_files: Iterable[dict[str, Any]]
    if isinstance(repo_context, dict):
        selected_files = repo_context.get('selected_files', []) or []
    else:
        selected_files = getattr(repo_context, 'selected_files', []) or []

    signals: list[str] = []
    for item in selected_files:
        path = item.get('path', '')
        preview = item.get('preview', '')
        signals.extend(_normalize_tokens(path))
        signals.extend(_normalize_tokens(preview))
        if len(signals) >= 80:
            break
    return signals[:80]


def _candidate_corpus(candidate: SkillSourceCandidate) -> list[str]:
    parts = [candidate.name, candidate.description]
    parts.extend(candidate.trigger_phrases)
    parts.extend(candidate.tags)
    return _normalize_tokens(' '.join(parts))


def _candidate_family_key(candidate: SkillSourceCandidate) -> str:
    normalized = re.sub(r'[^a-z0-9]+', '-', (candidate.name or '').lower()).strip('-')
    return normalized or candidate.candidate_id


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _candidate_runtime_lookup_keys(candidate: SkillSourceCandidate) -> list[str]:
    keys = [
        _candidate_family_key(candidate),
        str(candidate.name or '').strip().lower(),
        str(candidate.provenance.skill_path or '').strip().lower().rsplit('/', 1)[-1],
    ]
    ordered: list[str] = []
    for value in keys:
        text = str(value or '').strip().lower()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


def _candidate_runtime_family_aliases(candidate: SkillSourceCandidate) -> list[str]:
    aliases = [
        _candidate_family_key(candidate),
        str(candidate.name or '').strip().lower(),
        str(candidate.provenance.skill_path or '').strip().lower().rsplit('/', 1)[-1],
    ]
    return _unique(str(item or '').strip().lower() for item in aliases if str(item or '').strip())


def _normalize_runtime_family_allowlist(values: Optional[list[str]]) -> list[str]:
    normalized: list[str] = []
    for value in list(values or []):
        text = re.sub(r'[^a-z0-9]+', '-', str(value or '').strip().lower()).strip('-')
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _runtime_prior_for_candidate(
    *,
    candidate: SkillSourceCandidate,
    runtime_effectiveness_lookup: Optional[dict[str, dict[str, Any]]],
    runtime_effectiveness_min_runs: int,
    runtime_effectiveness_allowed_families: Optional[list[str]] = None,
) -> tuple[float, dict[str, Any] | None]:
    if not runtime_effectiveness_lookup:
        return 0.0, None
    allowed_families = _normalize_runtime_family_allowlist(runtime_effectiveness_allowed_families)
    if allowed_families:
        aliases = set(_candidate_runtime_family_aliases(candidate))
        if not aliases.intersection(allowed_families):
            return 0.0, None
    for key in _candidate_runtime_lookup_keys(candidate):
        payload = runtime_effectiveness_lookup.get(key)
        if payload is None:
            continue
        run_count = int(payload.get('run_count', 0) or 0)
        if run_count < max(int(runtime_effectiveness_min_runs or 0), 0):
            return 0.0, payload
        quality_score = float(payload.get('quality_score', 0.0) or 0.0)
        delta = max(-0.06, min(0.06, (quality_score - 0.5) * 0.12))
        return delta, payload
    return 0.0, None


def _score_skill_candidate_breakdown(
    *,
    task: str,
    repo_context: Any,
    candidate: SkillSourceCandidate,
    runtime_effectiveness_lookup: Optional[dict[str, dict[str, Any]]] = None,
    runtime_effectiveness_min_runs: int = 5,
    runtime_effectiveness_allowed_families: Optional[list[str]] = None,
) -> tuple[float, list[str], float, float]:
    base_task_tokens = set(_normalize_tokens(task))
    base_repo_tokens = set(_repo_signals(repo_context))
    semantic_task_tokens = _expand_semantic_tokens(base_task_tokens) - base_task_tokens
    semantic_repo_tokens = _expand_semantic_tokens(base_repo_tokens) - base_repo_tokens
    candidate_tokens = set(_candidate_corpus(candidate))

    if not candidate_tokens:
        return 0.0, [], 0.0, 0.0

    task_overlap = base_task_tokens & candidate_tokens
    repo_overlap = base_repo_tokens & candidate_tokens
    semantic_task_overlap = semantic_task_tokens & candidate_tokens
    semantic_repo_overlap = semantic_repo_tokens & candidate_tokens
    direct_phrase_hits = [
        phrase
        for phrase in candidate.trigger_phrases
        if phrase and phrase.lower() in task.lower()
    ]

    score = 0.0
    if base_task_tokens:
        score += 0.62 * (len(task_overlap) / max(len(base_task_tokens), 1))
        score += 0.1 * (len(semantic_task_overlap) / max(len(base_task_tokens), 1))
    if base_repo_tokens:
        score += 0.14 * (len(repo_overlap) / max(len(base_repo_tokens), 1))
        score += 0.04 * (len(semantic_repo_overlap) / max(len(base_repo_tokens), 1))
    if direct_phrase_hits:
        score += 0.15
    if candidate.provenance.source_type == 'official':
        score += 0.02

    if not task_overlap and not direct_phrase_hits and len(semantic_task_overlap) < 2:
        score *= 0.2

    base_score = min(score, 1.0)
    runtime_prior_delta, prior_payload = _runtime_prior_for_candidate(
        candidate=candidate,
        runtime_effectiveness_lookup=runtime_effectiveness_lookup,
        runtime_effectiveness_min_runs=runtime_effectiveness_min_runs,
        runtime_effectiveness_allowed_families=runtime_effectiveness_allowed_families,
    )
    adjusted_score = min(max(base_score + runtime_prior_delta, 0.0), 1.0)

    matched = _unique(
        list(task_overlap)[:6]
        + [f'semantic:{token}' for token in list(semantic_task_overlap)[:3]]
        + [f'phrase:{phrase}' for phrase in direct_phrase_hits[:3]]
        + [f'repo:{token}' for token in list(repo_overlap)[:3]]
        + [f'repo-semantic:{token}' for token in list(semantic_repo_overlap)[:2]]
    )
    if prior_payload is not None and runtime_prior_delta != 0.0:
        matched.extend(
            [
                f'runtime-prior:{runtime_prior_delta:+.3f}',
                f'runtime-quality:{float(prior_payload.get("quality_score", 0.0) or 0.0):.2f}',
                f'runtime-runs:{int(prior_payload.get("run_count", 0) or 0)}',
            ]
        )
    return adjusted_score, matched, base_score, runtime_prior_delta


def score_skill_candidate(
    *,
    task: str,
    repo_context: Any,
    candidate: SkillSourceCandidate,
    runtime_effectiveness_lookup: Optional[dict[str, dict[str, Any]]] = None,
    runtime_effectiveness_min_runs: int = 5,
    runtime_effectiveness_allowed_families: Optional[list[str]] = None,
) -> tuple[float, list[str]]:
    adjusted_score, matched, _base_score, _runtime_prior_delta = _score_skill_candidate_breakdown(
        task=task,
        repo_context=repo_context,
        candidate=candidate,
        runtime_effectiveness_lookup=runtime_effectiveness_lookup,
        runtime_effectiveness_min_runs=runtime_effectiveness_min_runs,
        runtime_effectiveness_allowed_families=runtime_effectiveness_allowed_families,
    )
    return adjusted_score, matched


def discover_online_skills(
    *,
    task: str,
    repo_context: Any,
    catalog: Optional[Iterable[SkillSourceCandidate]] = None,
    providers: Optional[Iterable[DiscoveryProvider]] = None,
    fetch_text: FetchText | None = None,
    limit: int = 5,
    runtime_effectiveness_lookup: Optional[dict[str, dict[str, Any]]] = None,
    enable_runtime_effectiveness_prior: bool = False,
    runtime_effectiveness_min_runs: int = 5,
    runtime_effectiveness_allowed_families: Optional[list[str]] = None,
) -> list[SkillSourceCandidate]:
    if providers is not None:
        candidates: list[SkillSourceCandidate] = []
        for provider in providers:
            candidates.extend(provider.list_candidates(fetch_text=fetch_text))
    else:
        candidates = list(catalog or REMOTE_SKILL_CATALOG)
    ranked_by_identity: dict[str, SkillSourceCandidate] = {}
    for candidate in candidates:
        score, matched, base_score, runtime_prior_delta = _score_skill_candidate_breakdown(
            task=task,
            repo_context=repo_context,
            candidate=candidate,
            runtime_effectiveness_lookup=runtime_effectiveness_lookup if enable_runtime_effectiveness_prior else None,
            runtime_effectiveness_min_runs=runtime_effectiveness_min_runs,
            runtime_effectiveness_allowed_families=runtime_effectiveness_allowed_families if enable_runtime_effectiveness_prior else None,
        )
        if score <= 0.08 or not matched:
            continue
        enriched = candidate.model_copy(
            update={
                'score': round(score, 4),
                'base_score': round(base_score, 4),
                'runtime_prior_delta': round(runtime_prior_delta, 4),
                'adjusted_score': round(score, 4),
                'matched_signals': matched,
            }
        )
        identity = f'{enriched.provenance.repo_full_name}::{enriched.provenance.skill_path or "."}'
        incumbent = ranked_by_identity.get(identity)
        if incumbent is None or enriched.score > incumbent.score:
            ranked_by_identity[identity] = enriched
    ranked_by_family: dict[str, SkillSourceCandidate] = {}
    for candidate in ranked_by_identity.values():
        family_key = _candidate_family_key(candidate)
        incumbent = ranked_by_family.get(family_key)
        if (
            incumbent is None
            or candidate.score > incumbent.score
            or (
                candidate.score == incumbent.score
                and candidate.provenance.source_type == 'official'
                and incumbent.provenance.source_type != 'official'
            )
        ):
            ranked_by_family[family_key] = candidate
    ranked = list(ranked_by_family.values())
    ranked.sort(key=lambda item: (-item.score, item.name))
    return ranked[:max(limit, 1)]


def default_discovery_providers(
    *,
    manifest_urls: Optional[Iterable[str]] = None,
    task: str = '',
    include_live: bool = False,
) -> list[DiscoveryProvider]:
    providers: list[DiscoveryProvider] = [StaticCatalogDiscoveryProvider(REMOTE_SKILL_CATALOG)]
    if include_live:
        providers.append(GitHubCollectionDiscoveryProvider())
        providers.append(GitHubRepoSearchDiscoveryProvider(task=task))
    urls = list(manifest_urls or [])
    if urls:
        providers.append(JsonManifestDiscoveryProvider(urls))
    return providers


def _github_blob_url(repo_full_name: str, *, ref: str, skill_path: str, filename: str) -> str:
    base = f'https://github.com/{repo_full_name}/blob/{ref}'
    if skill_path:
        return f'{base}/{skill_path}/{filename}'
    return f'{base}/{filename}'


def _github_raw_url(provenance: SkillProvenance, relative_path: str) -> str:
    base = f'https://raw.githubusercontent.com/{provenance.repo_full_name}/{provenance.ref}'
    if provenance.skill_path:
        return f'{base}/{provenance.skill_path}/{relative_path}'
    return f'{base}/{relative_path}'


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith('---\n'):
        return {}, text
    parts = text.split('---\n', 2)
    if len(parts) < 3:
        return {}, text
    raw = parts[1].splitlines()
    frontmatter: dict[str, str] = {}
    for line in raw:
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter, parts[2]


def _extract_sections(body: str) -> list[SkillBlueprintSection]:
    sections: list[SkillBlueprintSection] = []
    current_heading: Optional[str] = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_lines
        if current_heading is None:
            current_lines = []
            return
        summary = ' '.join(line.strip() for line in current_lines[:3] if line.strip())[:220]
        sections.append(SkillBlueprintSection(heading=current_heading, summary=summary))
        current_lines = []

    for line in body.splitlines():
        if line.startswith('#'):
            flush()
            current_heading = line.lstrip('#').strip()
            continue
        if current_heading is not None and len(current_lines) < 6:
            current_lines.append(line)
    flush()
    return sections[:12]


def _extract_workflow_summary(body: str) -> list[str]:
    steps: list[str] = []
    in_code_block = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if re.match(r'^\d+\.\s+', stripped) or stripped.startswith('- '):
            step = re.sub(r'^\d+\.\s+|^-\s+', '', stripped).strip()
            if step:
                steps.append(step)
        if len(steps) >= 8:
            break
    return steps


def _extract_artifact_paths(body: str) -> list[str]:
    paths = set(re.findall(r'(references/[A-Za-z0-9_./-]+|scripts/[A-Za-z0-9_./-]+|agents/openai\.yaml|_meta\.json|evals/[A-Za-z0-9_./-]+|evaluations/[A-Za-z0-9_./-]+)', body))
    return sorted(paths)


def _artifact_type(path: str) -> str:
    if path == 'SKILL.md':
        return 'skill'
    if path.startswith('references/'):
        return 'reference'
    if path.startswith('scripts/'):
        return 'script'
    if path.startswith('agents/'):
        return 'agent-config'
    if path.endswith('.json'):
        return 'metadata'
    return 'support'


def _artifact_purpose(path: str) -> str:
    if path.startswith('references/'):
        return 'Detailed reference material loaded on demand'
    if path.startswith('scripts/'):
        return 'Deterministic helper script or automation entrypoint'
    if path == 'agents/openai.yaml':
        return 'Agent UI and dependency metadata'
    if path.endswith('.json'):
        return 'Structured metadata or evaluation scaffold'
    return 'Skill support artifact'


def _parse_openai_yaml(text: str) -> tuple[SkillInterfaceMetadata, list[SkillDependency]]:
    interface = SkillInterfaceMetadata()
    dependencies: list[SkillDependency] = []

    display_name = re.search(r'display_name:\s*"([^"]+)"', text)
    short_description = re.search(r'short_description:\s*"([^"]+)"', text)
    default_prompt = re.search(r'default_prompt:\s*"([^"]+)"', text)
    if display_name:
        interface.display_name = display_name.group(1)
    if short_description:
        interface.short_description = short_description.group(1)
    if default_prompt:
        interface.default_prompt = default_prompt.group(1)

    tool_blocks = re.findall(
        r'-\s+type:\s*"([^"]+)"\s+value:\s*"([^"]+)"(?:\s+description:\s*"([^"]*)")?',
        text,
        flags=re.MULTILINE,
    )
    for kind, value, description in tool_blocks:
        dependencies.append(
            SkillDependency(
                kind=kind,
                value=value,
                description=description or '',
            )
        )

    return interface, dependencies


def _fallback_blueprint(candidate: SkillSourceCandidate, note: str = '') -> SkillBlueprint:
    notes = [note] if note else []
    return SkillBlueprint(
        blueprint_id=f'{candidate.candidate_id}__fallback',
        name=candidate.name,
        description=candidate.description,
        trigger_summary=candidate.description,
        workflow_summary=[],
        sections=[],
        artifacts=[
            SkillBlueprintArtifact(
                path='SKILL.md',
                artifact_type='skill',
                purpose='Top-level skill instructions',
                source_url=_github_raw_url(candidate.provenance, 'SKILL.md'),
            )
        ],
        dependencies=list(candidate.dependencies),
        interface=SkillInterfaceMetadata(),
        tags=list(candidate.tags),
        provenance=candidate.provenance,
        notes=notes,
    )


def build_skill_blueprint(
    candidate: SkillSourceCandidate,
    *,
    fetch_text: FetchText | None = None,
) -> SkillBlueprint:
    fetch_text = fetch_text or default_fetch_text
    skill_md_url = _github_raw_url(candidate.provenance, 'SKILL.md')

    try:
        skill_md_text = fetch_text(skill_md_url)
    except Exception as exc:
        return _fallback_blueprint(candidate, note=f'Failed to fetch source SKILL.md: {exc}')

    frontmatter, body = _parse_frontmatter(skill_md_text)
    name = frontmatter.get('name') or candidate.name
    description = frontmatter.get('description') or candidate.description
    sections = _extract_sections(body)
    workflow_summary = _extract_workflow_summary(body)
    artifact_paths = ['SKILL.md']
    artifact_paths.extend(_extract_artifact_paths(body))

    interface = SkillInterfaceMetadata()
    dependencies = list(candidate.dependencies)
    notes: list[str] = []

    openai_yaml_url = _github_raw_url(candidate.provenance, 'agents/openai.yaml')
    try:
        openai_yaml = fetch_text(openai_yaml_url)
    except (HTTPError, URLError, ValueError, TimeoutError, OSError):
        openai_yaml = ''
    if openai_yaml:
        interface, parsed_deps = _parse_openai_yaml(openai_yaml)
        if parsed_deps:
            dependencies = parsed_deps
        artifact_paths.append('agents/openai.yaml')
        notes.append('Loaded agents/openai.yaml for interface/dependency hints')

    artifacts = [
        SkillBlueprintArtifact(
            path=path,
            artifact_type=_artifact_type(path),
            purpose=_artifact_purpose(path),
            source_url=_github_raw_url(candidate.provenance, path),
        )
        for path in _unique(artifact_paths)
    ]

    return SkillBlueprint(
        blueprint_id=f'{candidate.candidate_id}__blueprint',
        name=name,
        description=description,
        trigger_summary=description,
        workflow_summary=workflow_summary,
        sections=sections,
        artifacts=artifacts,
        dependencies=dependencies,
        interface=interface,
        tags=list(candidate.tags),
        provenance=candidate.provenance,
        notes=notes,
    )


def build_skill_blueprints(
    candidates: Iterable[SkillSourceCandidate],
    *,
    fetch_text: FetchText | None = None,
    limit: int | None = None,
) -> list[SkillBlueprint]:
    blueprints: list[SkillBlueprint] = []
    for idx, candidate in enumerate(candidates):
        if limit is not None and idx >= limit:
            break
        blueprints.append(build_skill_blueprint(candidate, fetch_text=fetch_text))
    return blueprints


def _combined_candidate_tokens(candidates: Iterable[SkillSourceCandidate]) -> set[str]:
    combined: set[str] = set()
    for candidate in candidates:
        combined.update(_candidate_corpus(candidate))
    return combined


def decide_skill_reuse(
    *,
    task: str,
    candidates: list[SkillSourceCandidate],
    blueprints: Optional[list[SkillBlueprint]] = None,
) -> SkillReuseDecision:
    blueprints = blueprints or []
    blueprint_by_name = {blueprint.name: blueprint for blueprint in blueprints}
    blueprint_by_candidate = {
        blueprint.provenance.skill_path: blueprint for blueprint in blueprints
    }

    if not candidates:
        return SkillReuseDecision(
            mode='generate_fresh',
            rationale=['No matching online skill candidates were found'],
            coverage_score=0.0,
            gaps=_normalize_tokens(task)[:6],
        )

    ranked = sorted(candidates, key=lambda item: (-item.score, item.name))
    top = ranked[0]
    top_blueprint = blueprint_by_candidate.get(top.provenance.skill_path) or blueprint_by_name.get(top.name)
    top_artifact_count = len(top_blueprint.artifacts) if top_blueprint is not None else 1

    task_tokens = set(_normalize_tokens(task))
    if top.score >= 0.58 or (top.score >= 0.46 and top_artifact_count >= 3):
        chosen = [top]
        combined_tokens = _combined_candidate_tokens(chosen)
        gaps = sorted(task_tokens - combined_tokens)[:6]
        return SkillReuseDecision(
            mode='adapt_existing',
            selected_candidate_ids=[top.candidate_id],
            selected_blueprint_ids=[top_blueprint.blueprint_id] if top_blueprint is not None else [],
            rationale=[
                f'Top candidate `{top.name}` has strong task overlap score={top.score:.2f}',
                f'Blueprint richness={top_artifact_count} artifacts suggests a reusable baseline',
            ],
            coverage_score=round(min(1.0, top.score + 0.12), 4),
            gaps=gaps,
        )

    if len(ranked) >= 2 and ranked[0].score >= 0.28 and ranked[1].score >= 0.28:
        chosen = ranked[:2]
        combined_tokens = _combined_candidate_tokens(chosen)
        gaps = sorted(task_tokens - combined_tokens)[:6]
        selected_blueprint_ids = []
        for candidate in chosen:
            blueprint = blueprint_by_candidate.get(candidate.provenance.skill_path) or blueprint_by_name.get(candidate.name)
            if blueprint is not None:
                selected_blueprint_ids.append(blueprint.blueprint_id)
        return SkillReuseDecision(
            mode='compose_existing',
            selected_candidate_ids=[item.candidate_id for item in chosen],
            selected_blueprint_ids=selected_blueprint_ids,
            rationale=[
                f'No single candidate dominates; composing `{chosen[0].name}` + `{chosen[1].name}` covers more of the task',
                'Partial matches are strong enough to seed a combined blueprint rather than starting from scratch',
            ],
            coverage_score=round(min(1.0, sum(item.score for item in chosen) / len(chosen) + 0.1), 4),
            gaps=gaps,
        )

    combined_tokens = _combined_candidate_tokens([top])
    gaps = sorted(task_tokens - combined_tokens)[:6]
    return SkillReuseDecision(
        mode='generate_fresh',
        selected_candidate_ids=[top.candidate_id],
        selected_blueprint_ids=[top_blueprint.blueprint_id] if top_blueprint is not None else [],
        rationale=[
            f'Best candidate `{top.name}` is informative but not complete enough to adapt directly',
            'Use the discovered skill as inspiration while generating a repo-grounded skill from scratch',
        ],
        coverage_score=round(top.score, 4),
        gaps=gaps,
    )
