from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.request import SkillCreateRequestV6


TEXT_EXTENSIONS = {
    '.md', '.txt', '.py', '.sh', '.json', '.yaml', '.yml', '.toml', '.ini',
    '.cfg', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.kt',
    '.swift', '.rb', '.php', '.c', '.cc', '.cpp', '.h', '.hpp', '.cs',
    '.sql', '.html', '.css', '.xml'
}

DOC_NAMES = {'readme.md', 'skill.md', 'agents.md'}
SCRIPT_EXTENSIONS = {'.py', '.sh', '.js', '.ts', '.rb', '.php'}
CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'}
MAX_FILES_PER_REPO = 200
MAX_PREVIEW_CHARS = 400


def _safe_preview(path: Path) -> str:
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''
    return text[:MAX_PREVIEW_CHARS]


def _categorize_path(path: Path) -> list[str]:
    tags: list[str] = []
    name = path.name.lower()
    suffix = path.suffix.lower()

    if name in DOC_NAMES or suffix == '.md':
        tags.append('doc')
    if suffix in SCRIPT_EXTENSIONS:
        tags.append('script')
    if suffix in CONFIG_EXTENSIONS:
        tags.append('config')
    if '.github/workflows/' in path.as_posix() or name in {'docker-compose.yml', 'docker-compose.yaml', 'makefile'}:
        tags.append('workflow')
    return tags


def _scan_repo(repo_path: str) -> dict[str, Any]:
    root = Path(repo_path).expanduser()
    if not root.exists() or not root.is_dir():
        return {
            'repo_path': str(root),
            'exists': False,
            'selected_files': [],
            'notes': [f'repo path not found: {root}'],
        }

    selected_files: list[dict[str, Any]] = []
    notes: list[str] = []
    count = 0

    for path in sorted(root.rglob('*')):
        if count >= MAX_FILES_PER_REPO:
            notes.append(f'truncated after {MAX_FILES_PER_REPO} files')
            break
        if not path.is_file():
            continue
        rel_path = path.relative_to(root)
        if any(part.startswith('.') and part not in {'.github'} for part in rel_path.parts):
            continue
        if 'node_modules' in rel_path.parts or '__pycache__' in rel_path.parts:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name.lower() not in DOC_NAMES:
            continue

        rel = rel_path.as_posix()
        selected_files.append(
            {
                'path': rel,
                'absolute_path': str(path),
                'size_bytes': path.stat().st_size,
                'tags': _categorize_path(path),
                'preview': _safe_preview(path),
            }
        )
        count += 1

    return {
        'repo_path': str(root),
        'exists': True,
        'selected_files': selected_files,
        'notes': notes,
    }


def preload_repo_context(request: SkillCreateRequestV6) -> dict[str, Any]:
    repo_paths = list(getattr(request, 'repo_paths', []) or [])
    scanned = [_scan_repo(repo_path) for repo_path in repo_paths]

    selected_files: list[dict[str, Any]] = []
    notes: list[str] = []
    for repo in scanned:
        notes.extend(repo.get('notes', []))
        for file in repo.get('selected_files', []):
            enriched = dict(file)
            enriched['repo_path'] = repo['repo_path']
            selected_files.append(enriched)

    return {
        'repo_paths': repo_paths,
        'repos': scanned,
        'selected_files': selected_files,
        'notes': notes,
    }
