from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..models.lineage import SkillLineageHistoryEntry, SkillLineageManifest


def _normalize_skill_dir(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    raw = Path(value).expanduser()
    if raw.name == 'SKILL.md':
        raw = raw.parent
    if raw.name == '_meta.json':
        raw = raw.parent
    return raw


def _lineage_meta_path(value: str | Path | None) -> Path | None:
    skill_dir = _normalize_skill_dir(value)
    if skill_dir is None:
        return None
    return skill_dir / '_meta.json'


def load_lineage_manifest(value: str | Path | None) -> SkillLineageManifest | None:
    meta_path = _lineage_meta_path(value)
    if meta_path is None or not meta_path.exists() or not meta_path.is_file():
        return None
    try:
        payload = json.loads(meta_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    lineage = payload.get('lineage')
    if not isinstance(lineage, dict):
        return None
    try:
        return SkillLineageManifest.model_validate(lineage)
    except Exception:
        return None


def find_parent_lineage_manifest(*, parent_skill_id: str | None, repo_paths: list[str] | None) -> SkillLineageManifest | None:
    wanted = str(parent_skill_id or '').strip()
    discovered: list[SkillLineageManifest] = []
    for raw in list(repo_paths or []):
        manifest = load_lineage_manifest(raw)
        if manifest is None:
            continue
        if wanted and manifest.skill_id == wanted:
            return manifest
        discovered.append(manifest)
    if len(discovered) == 1 and not wanted:
        return discovered[0]
    return None


def latest_lineage_details(value: str | Path | None) -> tuple[int, str]:
    manifest = load_lineage_manifest(value)
    if manifest is None:
        return 0, ''
    latest = manifest.history[-1] if manifest.history else SkillLineageHistoryEntry()
    return manifest.version, latest.event


def build_updated_lineage_manifest(
    *,
    skill_id: str,
    version: int,
    parent_skill_id: str | None,
    content_sha: str,
    quality_score: float,
    event: str,
    summary: str,
    existing_manifest: Optional[SkillLineageManifest] = None,
    append_history: bool = False,
) -> SkillLineageManifest:
    history_entry = SkillLineageHistoryEntry(
        event=event,
        skill_id=skill_id,
        version=version,
        parent_skill_id=parent_skill_id,
        content_sha=content_sha,
        quality_score=quality_score,
        summary=summary,
    )
    history: list[SkillLineageHistoryEntry]
    if append_history and existing_manifest is not None:
        history = list(existing_manifest.history or []) + [history_entry]
    else:
        history = [history_entry]
    return SkillLineageManifest(
        skill_id=skill_id,
        version=version,
        parent_skill_id=parent_skill_id,
        content_sha=content_sha,
        quality_score=quality_score,
        history=history,
    )
