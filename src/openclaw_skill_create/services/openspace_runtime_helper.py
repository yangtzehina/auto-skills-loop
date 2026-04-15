from __future__ import annotations

import asyncio
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.runtime import SkillRunRecord
from .runtime_analysis import (
    analyze_skill_run_deterministically,
    decode_runtime_judgment_note,
    encode_runtime_judgment_note,
)


def _skill_dir_from_path(skill_path: str) -> Path | None:
    raw = (skill_path or '').strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if path.name.lower() == 'skill.md':
        return path.parent
    return path


def _read_skill_id_sidecar(skill_dir: Path | None) -> str:
    if skill_dir is None:
        return ''
    id_file = skill_dir / '.skill_id'
    if not id_file.exists():
        return ''
    try:
        return id_file.read_text(encoding='utf-8').strip()
    except OSError:
        return ''


def build_runtime_execution_note(run_record: SkillRunRecord, analysis_payload: dict[str, Any]) -> str:
    notes = [
        f'runtime task_id={run_record.task_id}',
        f'execution_result={run_record.execution_result}',
        f'skills={len(run_record.skills_used)}',
    ]
    if run_record.task_summary:
        notes.append(f'task_summary={run_record.task_summary}')
    if analysis_payload.get('summary'):
        notes.append(f"summary={analysis_payload['summary']}")
    return ' | '.join(notes)


def _load_recent_skill_history(store: Any, skill_id: str) -> list[dict[str, Any]]:
    if not skill_id or not hasattr(store, 'load_analyses'):
        return []
    try:
        analyses = list(store.load_analyses(skill_id=skill_id, limit=9) or [])
    except TypeError:
        analyses = list(store.load_analyses(skill_id, 9) or [])
    except Exception:
        return []

    history: list[dict[str, Any]] = []
    for analysis in analyses:
        judgment = None
        if hasattr(analysis, 'get_judgment'):
            judgment = analysis.get_judgment(skill_id)
        if judgment is None:
            for candidate in list(getattr(analysis, 'skill_judgments', []) or []):
                if getattr(candidate, 'skill_id', '') == skill_id:
                    judgment = candidate
                    break
        if judgment is None:
            continue
        payload = decode_runtime_judgment_note(getattr(judgment, 'note', ''))
        if not payload:
            continue
        payload.setdefault('run_id', getattr(analysis, 'task_id', ''))
        history.append(payload)
    return history


def _resolve_skill_usage(store: Any, usage: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    resolved = dict(usage)
    skill_dir = _skill_dir_from_path(resolved.get('skill_path', ''))
    record = None

    if skill_dir is not None and hasattr(store, 'load_record_by_path'):
        try:
            record = store.load_record_by_path(str(skill_dir))
        except Exception:
            record = None

    skill_id = str(resolved.get('skill_id') or '').strip()
    if not skill_id:
        skill_id = _read_skill_id_sidecar(skill_dir)
    if not skill_id and record is not None:
        skill_id = str(getattr(record, 'skill_id', '') or '').strip()
    resolved['skill_id'] = skill_id

    parent_skill_ids: list[str] = []
    if skill_id and hasattr(store, 'load_record'):
        try:
            record_by_id = store.load_record(skill_id)
        except Exception:
            record_by_id = None
        if record_by_id is not None:
            record = record_by_id

    lineage = getattr(record, 'lineage', None)
    if lineage is not None:
        parent_skill_ids = list(getattr(lineage, 'parent_skill_ids', []) or [])
    return resolved, parent_skill_ids


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _analyze_runtime_payload(
    payload: dict[str, Any],
    *,
    store_factory: Any = None,
    execution_analysis_cls: Any = None,
    skill_judgment_cls: Any = None,
    evolution_suggestion_cls: Any = None,
    evolution_type_enum: Any = None,
) -> dict[str, Any]:
    if store_factory is None:
        from openspace.skill_engine.store import SkillStore as store_factory
    if execution_analysis_cls is None or skill_judgment_cls is None:
        from openspace.skill_engine.types import (
            ExecutionAnalysis as execution_analysis_cls,
            SkillJudgment as skill_judgment_cls,
        )
    if evolution_suggestion_cls is None or evolution_type_enum is None:
        from openspace.skill_engine.types import (
            EvolutionSuggestion as evolution_suggestion_cls,
            EvolutionType as evolution_type_enum,
        )

    run_record = SkillRunRecord.model_validate(payload.get('run_record') or {})
    db_path = payload.get('db_path')
    db_path_obj = Path(db_path).expanduser().resolve() if db_path else None
    if db_path_obj is not None:
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    store = None
    try:
        store = store_factory(db_path=db_path_obj)
    except TypeError:
        store = store_factory(db_path_obj)

    try:
        recent_skill_history: dict[str, list[dict[str, Any]]] = {}
        parent_skill_ids: dict[str, list[str]] = {}
        resolved_skills: list[dict[str, Any]] = []
        recent_skill_history['__no_skill__'] = _load_recent_skill_history(store, '__no_skill__')
        for usage in list(run_record.skills_used):
            resolved, parents = _resolve_skill_usage(store, usage)
            resolved_skills.append(resolved)
            skill_id = resolved.get('skill_id', '')
            if skill_id:
                recent_skill_history[skill_id] = _load_recent_skill_history(store, skill_id)
                parent_skill_ids[skill_id] = parents

        normalized_record = SkillRunRecord(
            run_id=run_record.run_id,
            task_id=run_record.task_id,
            task_summary=run_record.task_summary,
            skills_used=resolved_skills,
            execution_result=run_record.execution_result,
            failure_points=run_record.failure_points,
            user_corrections=run_record.user_corrections,
            output_summary=run_record.output_summary,
            repo_paths=run_record.repo_paths,
            step_trace=run_record.step_trace,
            phase_markers=run_record.phase_markers,
            tool_summary=run_record.tool_summary,
            completed_at=run_record.completed_at,
        )
        analysis = analyze_skill_run_deterministically(
            normalized_record,
            recent_skill_history=recent_skill_history,
            parent_skill_ids=parent_skill_ids,
        )

        judgments = []
        for item in list(analysis.skills_analyzed):
            skill_id = str(item.get('skill_id') or '').strip()
            if not skill_id:
                continue
            skill_usage = next(
                (usage for usage in normalized_record.skills_used if usage.get('skill_id') == skill_id),
                {},
            )
            judgments.append(
                skill_judgment_cls(
                    skill_id=skill_id,
                    skill_applied=bool(skill_usage.get('applied', False)),
                    note=encode_runtime_judgment_note(item),
                )
            )
        if analysis.create_candidates and not any(
            bool(skill.get('applied', False))
            for skill in list(normalized_record.skills_used or [])
        ):
            judgments.append(
                skill_judgment_cls(
                    skill_id='__no_skill__',
                    skill_applied=False,
                    note=encode_runtime_judgment_note(
                        {
                            'run_id': normalized_record.run_id,
                            'helped': False,
                            'run_quality_score': 0.0,
                            'recommended_action': 'no_change',
                            'most_valuable_step': '',
                            'misleading_step': '',
                            'missing_steps': list(analysis.create_candidates[0].requirement_gaps),
                            'quality_score': 0.0,
                            'usage_stats': {},
                            'recent_run_ids': list(analysis.create_candidates[0].source_run_ids),
                            'parent_skill_ids': [],
                        }
                    ),
                )
            )

        evolution_suggestions = []
        for plan in list(analysis.evolution_plans):
            if plan.action == 'patch_current':
                evolution_suggestions.append(
                    evolution_suggestion_cls(
                        evolution_type=evolution_type_enum.FIX,
                        target_skill_ids=[plan.skill_id],
                        direction=plan.summary or plan.reason,
                    )
                )
            elif plan.action == 'derive_child':
                evolution_suggestions.append(
                    evolution_suggestion_cls(
                        evolution_type=evolution_type_enum.DERIVED,
                        target_skill_ids=[plan.skill_id],
                        direction=plan.summary or plan.reason,
                    )
                )

        execution_analysis = execution_analysis_cls(
            task_id=run_record.task_id,
            timestamp=datetime.now(),
            task_completed=(run_record.execution_result == 'success'),
            execution_note=build_runtime_execution_note(
                normalized_record,
                analysis.model_dump(mode='json'),
            ),
            tool_issues=[],
            skill_judgments=judgments,
            evolution_suggestions=evolution_suggestions,
            analyzed_by=payload.get('analyzed_by', 'skill-create-v6.runtime-analysis'),
            analyzed_at=datetime.now(),
        )
        await _maybe_await(store.record_analysis(execution_analysis))

        return {
            'applied': True,
            'mode': 'runtime-analysis',
            'analysis': analysis.model_dump(mode='json'),
            'db_path': str(getattr(store, 'db_path', db_path_obj or '')),
        }
    finally:
        if store is not None and hasattr(store, 'close'):
            store.close()


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or '{}')
        result = asyncio.run(_analyze_runtime_payload(payload))
    except Exception as exc:  # pragma: no cover - defensive helper boundary
        result = {
            'applied': False,
            'mode': 'runtime-analysis',
            'reason': str(exc),
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
