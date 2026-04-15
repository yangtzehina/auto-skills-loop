from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from ..models.runtime_usage import RuntimeUsageReport, RuntimeUsageSkillReport
from .runtime_analysis import decode_runtime_judgment_note
from .runtime_lineage import latest_lineage_details


def _normalize_action(value: Any) -> str:
    text = str(value or '').strip().lower()
    return text or 'no_change'


def _normalize_run_id(value: Any) -> str:
    return str(value or '').strip()


def _record_name(record: Any, skill_id: str) -> str:
    for attr in ('name', 'skill_name', 'title'):
        value = str(getattr(record, attr, '') or '').strip()
        if value:
            return value
    return skill_id.split('__', 1)[0] if skill_id else ''


def _record_skill_path(record: Any) -> str:
    for attr in ('path', 'skill_path'):
        value = str(getattr(record, attr, '') or '').strip()
        if value:
            return value
    return ''


def _lineage_parents(record: Any) -> list[str]:
    lineage = getattr(record, 'lineage', None)
    if lineage is None:
        return []
    return [str(item).strip() for item in list(getattr(lineage, 'parent_skill_ids', []) or []) if str(item).strip()]


def _load_records(store: Any) -> list[Any]:
    for attr in ('list_records', 'load_records'):
        if not hasattr(store, attr):
            continue
        try:
            result = getattr(store, attr)()
        except TypeError:
            continue
        return list(result or [])
    return []


def _load_analyses_for_skill(store: Any, skill_id: str, limit: int = 10) -> list[Any]:
    if not hasattr(store, 'load_analyses'):
        return []
    try:
        return list(store.load_analyses(skill_id=skill_id, limit=limit) or [])
    except TypeError:
        try:
            return list(store.load_analyses(skill_id, limit) or [])
        except Exception:
            return []
    except Exception:
        return []


def _judgment_payload(analysis: Any, skill_id: str) -> dict[str, Any]:
    judgment = None
    if hasattr(analysis, 'get_judgment'):
        judgment = analysis.get_judgment(skill_id)
    if judgment is None:
        for candidate in list(getattr(analysis, 'skill_judgments', []) or []):
            if str(getattr(candidate, 'skill_id', '') or '').strip() == skill_id:
                judgment = candidate
                break
    if judgment is None:
        return {}
    return decode_runtime_judgment_note(getattr(judgment, 'note', ''))


async def _build_runtime_usage_payload(payload: dict[str, Any], *, store_factory: Any = None) -> dict[str, Any]:
    if store_factory is None:
        from openspace.skill_engine.store import SkillStore as store_factory

    requested_skill_id = str(payload.get('skill_id') or '').strip()
    db_path = payload.get('db_path')
    db_path_obj = Path(db_path).expanduser().resolve() if db_path else None
    if db_path_obj is not None:
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    store = None
    try:
        try:
            store = store_factory(db_path=db_path_obj)
        except TypeError:
            store = store_factory(db_path_obj)

        records = _load_records(store)
        reports: list[RuntimeUsageSkillReport] = []
        for record in list(records or []):
            skill_id = str(getattr(record, 'skill_id', '') or '').strip()
            if not skill_id:
                continue
            if requested_skill_id and skill_id != requested_skill_id:
                continue

            analyses = _load_analyses_for_skill(store, skill_id, 10)
            judgments = []
            for analysis in list(analyses):
                judgment = _judgment_payload(analysis, skill_id)
                if judgment:
                    judgments.append(judgment)

            if not judgments:
                continue

            latest = judgments[0]
            lineage_version, latest_lineage_event = latest_lineage_details(_record_skill_path(record))
            reports.append(
                RuntimeUsageSkillReport(
                    skill_id=skill_id,
                    skill_name=_record_name(record, skill_id),
                    quality_score=round(float(latest.get('quality_score', 0.0) or 0.0), 4),
                    usage_stats=dict(latest.get('usage_stats') or {}),
                    recent_run_ids=[_normalize_run_id(item) for item in list(latest.get('recent_run_ids') or []) if _normalize_run_id(item)],
                    recent_actions=[
                        _normalize_action(item.get('recommended_action'))
                        for item in list(judgments)
                        if _normalize_action(item.get('recommended_action'))
                    ],
                    parent_skill_ids=_lineage_parents(record) or [str(item).strip() for item in list(latest.get('parent_skill_ids') or []) if str(item).strip()],
                    latest_recommended_action=_normalize_action(latest.get('recommended_action')),
                    lineage_version=lineage_version,
                    latest_lineage_event=latest_lineage_event,
                )
            )

        reports.sort(key=lambda item: (-item.quality_score, item.skill_name or item.skill_id))
        result = RuntimeUsageReport(
            applied=True,
            db_path=str(getattr(store, 'db_path', db_path_obj or '')),
            skill_reports=reports,
            summary=(
                f'Runtime usage report complete: skills={len(reports)}'
                + (f' filtered_skill={requested_skill_id}' if requested_skill_id else '')
            ),
        )
        return result.model_dump(mode='json')
    finally:
        if store is not None and hasattr(store, 'close'):
            store.close()


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or '{}')
        result = asyncio.run(_build_runtime_usage_payload(payload))
    except Exception as exc:  # pragma: no cover - defensive helper boundary
        result = RuntimeUsageReport(
            applied=False,
            reason=str(exc),
            summary=f'Runtime usage report skipped: {exc}',
        ).model_dump(mode='json')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
