from __future__ import annotations

from typing import Optional

from ..models.observation import OpenSpaceObservationPolicy
from ..models.runtime import RuntimeSessionEvidence, SkillRunRecord
from ..models.runtime_cycle import RuntimeCycleResult
from .runtime_analysis import (
    NO_SKILL_HISTORY_ID,
    _extract_global_gap_lines,
    analyze_skill_run,
    analyze_skill_run_deterministically,
)
from .runtime_followup import build_runtime_followup_result


def run_runtime_cycle(
    run_record: SkillRunRecord,
    policy: Optional[OpenSpaceObservationPolicy],
    *,
    session_evidence: Optional[RuntimeSessionEvidence] = None,
    plan_index: Optional[int] = None,
    task_summary: Optional[str] = None,
    repo_paths: Optional[list[str]] = None,
    skill_name_hint: Optional[str] = None,
) -> RuntimeCycleResult:
    analysis = analyze_skill_run(run_record, policy, session_evidence=session_evidence)
    followup = build_runtime_followup_result(
        analysis,
        plan_index=plan_index,
        task_summary=task_summary or run_record.task_summary,
        repo_paths=repo_paths if repo_paths is not None else run_record.repo_paths,
        skill_name_hint=skill_name_hint,
    )
    return RuntimeCycleResult(
        run_id=analysis.run_id,
        task_id=analysis.task_id,
        analysis=analysis,
        followup=followup,
        summary=f'Runtime cycle complete: action={followup.action}; {analysis.summary}',
    )


def replay_runtime_runs(
    run_records: list[SkillRunRecord],
    *,
    skill_name_hint: Optional[str] = None,
) -> list[RuntimeCycleResult]:
    recent_skill_history: dict[str, list[dict[str, object]]] = {}
    results: list[RuntimeCycleResult] = []

    for value in list(run_records or []):
        record = value if isinstance(value, SkillRunRecord) else SkillRunRecord.model_validate(value)
        analysis = analyze_skill_run_deterministically(
            record,
            recent_skill_history=recent_skill_history,
        )
        followup = build_runtime_followup_result(
            analysis,
            task_summary=record.task_summary,
            repo_paths=record.repo_paths,
            skill_name_hint=skill_name_hint,
        )
        results.append(
            RuntimeCycleResult(
                run_id=analysis.run_id,
                task_id=analysis.task_id,
                analysis=analysis,
                followup=followup,
                summary=f'Runtime replay cycle complete: action={followup.action}; {analysis.summary}',
            )
        )

        for item in list(analysis.skills_analyzed or []):
            skill_id = str(item.get('skill_id') or '').strip()
            if not skill_id:
                continue
            history = list(recent_skill_history.get(skill_id, []) or [])
            history.append(
                {
                    'run_id': analysis.run_id,
                    'run_quality_score': float(item.get('run_quality_score', 0.0) or 0.0),
                    'recommended_action': str(item.get('recommended_action') or 'no_change'),
                    'missing_steps': list(item.get('missing_steps') or []),
                }
            )
            recent_skill_history[skill_id] = history[-10:]

        if not any(bool(skill.get('applied', False)) for skill in list(record.skills_used or [])):
            no_skill_history = list(recent_skill_history.get(NO_SKILL_HISTORY_ID, []) or [])
            global_gaps = list(analysis.create_candidates[0].requirement_gaps) if analysis.create_candidates else _extract_global_gap_lines(record)
            if global_gaps:
                no_skill_history.append(
                    {
                        'run_id': analysis.run_id,
                        'run_quality_score': 0.0,
                        'recommended_action': 'no_change',
                        'missing_steps': list(global_gaps),
                    }
                )
            recent_skill_history[NO_SKILL_HISTORY_ID] = no_skill_history[-10:]

    return results
