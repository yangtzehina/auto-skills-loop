from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from ..models.runtime import RuntimeSemanticSummary, RuntimeSessionEvidence, SkillRunRecord
from ..models.runtime_handoff import RuntimeHandoffEnvelope, RuntimeHandoffNormalized, RuntimeHandoffOptions


def _normalize_handoff_payload(value: Any) -> dict[str, Any]:
    payload = dict(value or {})
    if 'skills_used' not in payload and 'skills' in payload:
        payload['skills_used'] = payload.pop('skills')
    if 'execution_result' not in payload and 'result' in payload:
        payload['execution_result'] = payload.pop('result')
    if 'repo_paths' not in payload and 'repositories' in payload:
        payload['repo_paths'] = payload.pop('repositories')
    return payload


def load_runtime_handoff_input(raw: str) -> RuntimeHandoffEnvelope:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON input: {exc.msg}') from exc
    try:
        return RuntimeHandoffEnvelope.model_validate(_normalize_handoff_payload(payload))
    except ValidationError as exc:
        raise ValueError(f'Invalid RuntimeHandoffEnvelope payload: {exc}') from exc


def normalize_runtime_handoff(value: RuntimeHandoffEnvelope | dict[str, Any]) -> RuntimeHandoffNormalized:
    envelope = (
        value if isinstance(value, RuntimeHandoffEnvelope) else RuntimeHandoffEnvelope.model_validate(_normalize_handoff_payload(value))
    )
    options = envelope.runtime_options
    if options.judge_model and not options.enable_llm_judge:
        raise ValueError('runtime_options.judge_model requires enable_llm_judge=true')
    turn_trace = list(envelope.turn_trace or [])
    phase_markers: list[str] = []
    tool_summary: list[str] = []
    for item in turn_trace:
        phase = str(item.get('phase') or '').strip()
        tool = str(item.get('tool') or '').strip()
        if phase and phase not in phase_markers:
            phase_markers.append(phase)
        if tool and tool not in tool_summary:
            tool_summary.append(tool)
    record = SkillRunRecord(
        run_id=envelope.run_id,
        task_id=envelope.task_id,
        task_summary=envelope.task_summary,
        skills_used=list(envelope.skills_used),
        execution_result=envelope.execution_result,
        failure_points=list(envelope.failure_points),
        user_corrections=list(envelope.user_corrections),
        output_summary=envelope.output_summary,
        repo_paths=list(envelope.repo_paths),
        step_trace=turn_trace,
        phase_markers=phase_markers,
        tool_summary=tool_summary,
        completed_at=envelope.completed_at,
    )
    session_evidence = None
    semantic_summary = None
    if turn_trace:
        session_evidence = RuntimeSessionEvidence(
            run_id=record.run_id,
            task_id=record.task_id,
            turn_trace=turn_trace,
            phase_markers=phase_markers,
            tool_summary=tool_summary,
            failure_points=record.failure_points,
            user_corrections=record.user_corrections,
            output_summary=record.output_summary,
        )
        semantic_summary = RuntimeSemanticSummary(
            run_id=record.run_id,
            task_id=record.task_id,
            task_summary=record.task_summary or record.task_id,
            concise_summary=(
                f'Runtime handoff captured {len(turn_trace)} trace step(s) for '
                f'{record.execution_result} execution.'
            ),
            notable_steps=[
                str(item.get('step') or '').strip()
                for item in turn_trace
                if str(item.get('step') or '').strip()
            ][:5],
            what_helped=[
                str(item.get('step') or '').strip()
                for item in turn_trace
                if str(item.get('status') or '').strip().lower() in {'success', 'partial'}
                and str(item.get('step') or '').strip()
            ][:5],
            what_misled=[
                str(item.get('step') or '').strip()
                for item in turn_trace
                if str(item.get('status') or '').strip().lower() in {'failed', 'corrected'}
                and str(item.get('step') or '').strip()
            ][:5],
            repeated_gaps=list(record.failure_points or [])[:3] + list(record.user_corrections or [])[:3],
            missing_capabilities=list(record.failure_points or [])[:3] + list(record.user_corrections or [])[:3],
            confidence=0.6 if turn_trace else 0.0,
            evidence_coverage=1.0 if turn_trace else 0.0,
        )
    return RuntimeHandoffNormalized(
        skill_run_record=record,
        runtime_session_evidence=session_evidence,
        runtime_semantic_summary=semantic_summary,
        runtime_options=RuntimeHandoffOptions.model_validate(options.model_dump(mode='json')),
        summary=(
            f'Runtime handoff normalized: '
            f'run_id={record.run_id}; skills={len(record.skills_used)}; '
            f'trace_steps={len(turn_trace)}; '
            f'judge={"enabled" if options.enable_llm_judge else "disabled"}'
        ),
    )
