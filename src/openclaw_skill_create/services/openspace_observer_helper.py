from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def map_skill_type_to_category(skill_type: str) -> str:
    normalized = (skill_type or '').strip().lower()
    if normalized in {'library-api-reference', 'reference'}:
        return 'reference'
    if normalized in {'tool-guide', 'tool_guide'}:
        return 'tool_guide'
    return 'workflow'


def _benchmark_score(evaluation_report: dict[str, Any], benchmark_name: str) -> float | None:
    for item in list(evaluation_report.get('benchmark_results') or []):
        if not isinstance(item, dict):
            continue
        if item.get('name') != benchmark_name:
            continue
        score = item.get('score')
        if score is None:
            return None
        try:
            return float(score)
        except (TypeError, ValueError):
            return None
    return None


def build_change_summary(payload: dict[str, Any], *, existing: bool) -> str:
    severity = payload.get('severity', 'unknown')
    timings = payload.get('timings') or {}
    diagnostics = payload.get('diagnostics') or {}
    evaluation_report = payload.get('evaluation_report') or {}
    skill_plan = payload.get('skill_plan') or {}
    validation = diagnostics.get('validation') or {}
    security_audit = diagnostics.get('security_audit') or {}
    issues = list(validation.get('repairable_issue_types') or []) + list(validation.get('non_repairable_issue_types') or [])
    summary = 'Observed skill-create-v6 initial capture' if not existing else 'Observed skill-create-v6 overwrite'
    summary += f' (severity={severity})'
    if timings.get('repair_applied'):
        summary += ', after deterministic repair'
    if evaluation_report.get('overall_score') is not None:
        summary += f", eval={float(evaluation_report['overall_score']):.2f}"
    task_alignment = _benchmark_score(evaluation_report, 'task_alignment')
    if task_alignment is not None:
        summary += f", task_alignment={task_alignment:.2f}"
    if issues:
        summary += f"; issues={','.join(sorted(dict.fromkeys(issues))[:4])}"
    if security_audit.get('rating'):
        summary += f", security={security_audit['rating']}"
        if security_audit.get('top_security_categories'):
            summary += f"; security_categories={','.join(list(security_audit['top_security_categories'])[:3])}"
    if skill_plan.get('skill_archetype'):
        summary += f", archetype={skill_plan['skill_archetype']}"
        operation_contract = skill_plan.get('operation_contract') or {}
        operation_groups = list(operation_contract.get('operations') or [])
        if operation_groups:
            operation_count = sum(len(list(group.get('operations') or [])) for group in operation_groups if isinstance(group, dict))
            summary += f"; operation_count={operation_count}"
    quality_review = payload.get('quality_review') or {}
    if quality_review.get('operation_validation_status'):
        summary += f", operation_validation={quality_review['operation_validation_status']}"
    if quality_review.get('recommended_followup'):
        summary += f", recommended_followup={quality_review['recommended_followup']}"
    return summary


def build_execution_note(payload: dict[str, Any]) -> str:
    task = payload.get('task', '')
    severity = payload.get('severity', 'unknown')
    skill_plan = payload.get('skill_plan') or {}
    objective = skill_plan.get('objective', '')
    diagnostics = payload.get('diagnostics') or {}
    evaluation_report = payload.get('evaluation_report') or {}
    persistence = payload.get('persistence') or {}
    validation = diagnostics.get('validation') or {}
    security_audit = diagnostics.get('security_audit') or {}
    notes = [
        f'skill-create-v6 observation for task: {task}',
        f'severity={severity}',
    ]
    if objective:
        notes.append(f'objective={objective}')
    if skill_plan.get('skill_archetype'):
        notes.append(f"skill_archetype={skill_plan['skill_archetype']}")
        operation_contract = skill_plan.get('operation_contract') or {}
        if operation_contract:
            notes.append(
                'operation_contract='
                f"{operation_contract.get('backend_kind', 'python_backend')}/"
                f"{operation_contract.get('session_model', 'stateless')}/"
                f"{operation_contract.get('mutability', 'read_only')}"
            )
    quality_review = payload.get('quality_review') or {}
    if quality_review.get('operation_validation_status'):
        notes.append(f"operation_validation_status={quality_review['operation_validation_status']}")
    if quality_review.get('coverage_gap_summary'):
        notes.append(f"coverage_gap_summary={','.join(list(quality_review.get('coverage_gap_summary') or [])[:4])}")
    if quality_review.get('recommended_followup'):
        notes.append(f"recommended_followup={quality_review['recommended_followup']}")
    summary = validation.get('summary') or []
    if summary:
        notes.append(f'validation_summary={"; ".join(summary[:3])}')
    if security_audit.get('rating'):
        notes.append(
            'security_audit='
            f"{security_audit.get('rating')}@tier{security_audit.get('trust_tier', 1)}"
        )
        top_categories = list(security_audit.get('top_security_categories') or [])
        if top_categories:
            notes.append(f"security_categories={','.join(top_categories[:3])}")
    if evaluation_report.get('overall_score') is not None:
        notes.append(f"evaluation_score={float(evaluation_report['overall_score']):.2f}")
    task_alignment = _benchmark_score(evaluation_report, 'task_alignment')
    if task_alignment is not None:
        notes.append(f"task_alignment={task_alignment:.2f}")
    if persistence.get('evaluation_report_path'):
        notes.append(f"evaluation_report_path={persistence['evaluation_report_path']}")
    if persistence.get('security_audit_path'):
        notes.append(f"security_audit_path={persistence['security_audit_path']}")
    return ' | '.join(notes)


def _add_all_diff(snapshot: dict[str, str], *, compute_unified_diff) -> str:
    parts: list[str] = []
    for name, text in sorted(snapshot.items()):
        diff = compute_unified_diff('', text, filename=name)
        if diff:
            parts.append(diff)
    return '\n'.join(parts)


def _snapshot_diff(old_snapshot: dict[str, str], new_snapshot: dict[str, str], *, compute_unified_diff) -> str:
    parts: list[str] = []
    for name in sorted(set(old_snapshot) | set(new_snapshot)):
        diff = compute_unified_diff(old_snapshot.get(name, ''), new_snapshot.get(name, ''), filename=name)
        if diff:
            parts.append(diff)
    return '\n'.join(parts)


async def _observe(payload: dict[str, Any]) -> dict[str, Any]:
    from openspace.skill_engine.patch import collect_skill_snapshot, compute_unified_diff
    from openspace.skill_engine.registry import write_skill_id
    from openspace.skill_engine.store import SkillStore
    from openspace.skill_engine.types import (
        ExecutionAnalysis,
        SkillCategory,
        SkillJudgment,
        SkillLineage,
        SkillOrigin,
        SkillRecord,
    )

    persistence = payload.get('persistence') or {}
    skill_plan = payload.get('skill_plan') or {}
    evaluation_report = payload.get('evaluation_report') or {}
    skill_dir = Path(persistence['output_root']).expanduser().resolve()
    skill_md = skill_dir / 'SKILL.md'
    if not skill_md.exists():
        return {
            'applied': False,
            'reason': f'SKILL.md not found in {skill_dir}',
            'mode': 'observe-only',
        }

    raw_skill_md = skill_md.read_text(encoding='utf-8')
    name = skill_plan.get('skill_name') or skill_dir.name
    description = skill_plan.get('objective') or f'Repo-aware skill for {name}'
    skill_type = skill_plan.get('skill_type') or 'mixed'
    category = SkillCategory(map_skill_type_to_category(skill_type))

    now = datetime.now()
    snapshot = collect_skill_snapshot(skill_dir)
    db_path = payload.get('db_path')
    db_path_obj = Path(db_path).expanduser().resolve() if db_path else None
    if db_path_obj is not None:
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)
    store = SkillStore(db_path=db_path_obj)

    try:
        existing = store.load_record_by_path(str(skill_dir))
        if existing and existing.lineage.content_snapshot == snapshot:
            record = existing
            event = 'analysis-only'
            write_skill_id(skill_dir, existing.skill_id)
        elif existing:
            generation = existing.lineage.generation + 1
            new_id = f'{name}__v{generation}_{uuid.uuid4().hex[:8]}'
            record = SkillRecord(
                skill_id=new_id,
                name=name,
                description=description,
                path=str(skill_md),
                is_active=True,
                category=existing.category,
                tags=list(existing.tags),
                visibility=existing.visibility,
                creator_id=existing.creator_id,
                lineage=SkillLineage(
                    origin=SkillOrigin.FIXED,
                    generation=generation,
                    parent_skill_ids=[existing.skill_id],
                    source_task_id=payload.get('task_id'),
                    change_summary=build_change_summary(payload, existing=True),
                    content_diff=_snapshot_diff(existing.lineage.content_snapshot or {}, snapshot, compute_unified_diff=compute_unified_diff),
                    content_snapshot=snapshot,
                    created_at=now,
                    created_by=payload.get('analyzed_by', ''),
                ),
                tool_dependencies=list(existing.tool_dependencies),
                critical_tools=list(existing.critical_tools),
            )
            await store.evolve_skill(record, [existing.skill_id])
            write_skill_id(skill_dir, new_id)
            event = 'versioned'
        else:
            new_id = f'{name}__v0_{uuid.uuid4().hex[:8]}'
            record = SkillRecord(
                skill_id=new_id,
                name=name,
                description=description,
                path=str(skill_md),
                is_active=True,
                category=category,
                tags=sorted({'skill-create-v6', skill_type}),
                lineage=SkillLineage(
                    origin=SkillOrigin.CAPTURED,
                    generation=0,
                    parent_skill_ids=[],
                    source_task_id=payload.get('task_id'),
                    change_summary=build_change_summary(payload, existing=False),
                    content_diff=_add_all_diff(snapshot, compute_unified_diff=compute_unified_diff),
                    content_snapshot=snapshot,
                    created_at=now,
                    created_by=payload.get('analyzed_by', ''),
                ),
            )
            await store.save_record(record)
            write_skill_id(skill_dir, new_id)
            event = 'created'

        analysis = ExecutionAnalysis(
            task_id=payload.get('task_id', f'skill-create-v6:{uuid.uuid4()}'),
            timestamp=now,
            task_completed=(payload.get('severity') != 'fail'),
            execution_note=build_execution_note(payload),
            tool_issues=[],
            skill_judgments=[
                SkillJudgment(
                    skill_id=record.skill_id,
                    skill_applied=True,
                    note=f"observe-only via skill-create-v6; severity={payload.get('severity', 'unknown')}",
                )
            ],
            evolution_suggestions=[],
            analyzed_by=payload.get('analyzed_by', 'skill-create-v6.observe-only'),
            analyzed_at=now,
        )
        await store.record_analysis(analysis)

        return {
            'applied': True,
            'mode': 'observe-only',
            'event': event,
            'skill_id': record.skill_id,
            'skill_name': record.name,
            'generation': record.lineage.generation,
            'origin': record.lineage.origin.value,
            'analysis_task_id': analysis.task_id,
            'db_path': str(store.db_path),
            'output_root': str(skill_dir),
            'evaluation_score': evaluation_report.get('overall_score'),
            'evaluation_task_alignment': _benchmark_score(evaluation_report, 'task_alignment'),
            'evaluation_report_path': persistence.get('evaluation_report_path'),
        }
    finally:
        store.close()


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or '{}')
        result = asyncio.run(_observe(payload))
    except Exception as exc:  # pragma: no cover - defensive helper boundary
        result = {
            'applied': False,
            'mode': 'observe-only',
            'reason': str(exc),
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
