from __future__ import annotations

from typing import Any, Optional

from ..models.runtime import RuntimeSemanticSummary, RuntimeSessionEvidence, SkillRunAnalysis, SkillRunRecord


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in list(values or []):
        text = str(value or '').strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


def _stringify_step(value: Any, *, skill_name: str = '') -> str:
    step = str(value or '').strip()
    label = str(skill_name or '').strip()
    if step and label:
        return f'{label}: {step}'
    return step or label


def _semantic_evidence_coverage(
    *,
    run_record: SkillRunRecord,
    session_evidence: Optional[RuntimeSessionEvidence],
) -> float:
    signals = 0
    total = 3
    if session_evidence is not None and session_evidence.turn_trace:
        signals += 1
    elif run_record.step_trace:
        signals += 1
    if (session_evidence is not None and session_evidence.phase_markers) or run_record.phase_markers:
        signals += 1
    if (session_evidence is not None and session_evidence.tool_summary) or run_record.tool_summary:
        signals += 1
    return round(signals / total, 4)


def build_runtime_semantic_summary(
    *,
    run_record: SkillRunRecord,
    analysis: SkillRunAnalysis,
    session_evidence: Optional[RuntimeSessionEvidence] = None,
) -> RuntimeSemanticSummary | None:
    has_rich_evidence = bool(
        (session_evidence is not None and (session_evidence.turn_trace or session_evidence.phase_markers or session_evidence.tool_summary))
        or run_record.step_trace
        or run_record.phase_markers
        or run_record.tool_summary
    )
    if not has_rich_evidence:
        return None

    helped = _ordered_unique(
        [
            _stringify_step(item.get('most_valuable_step'), skill_name=item.get('skill_name', ''))
            for item in list(analysis.skills_analyzed or [])
            if str(item.get('most_valuable_step') or '').strip()
        ]
    )
    misled = _ordered_unique(
        [
            _stringify_step(item.get('misleading_step'), skill_name=item.get('skill_name', ''))
            for item in list(analysis.skills_analyzed or [])
            if str(item.get('misleading_step') or '').strip()
        ]
    )
    repeated_gaps = _ordered_unique(
        [
            gap
            for candidate in list(analysis.create_candidates or [])
            for gap in list(candidate.requirement_gaps or [])
        ]
        + [
            gap
            for item in list(analysis.skills_analyzed or [])
            for gap in list(item.get('missing_steps') or [])
        ]
    )
    notable_steps = _ordered_unique(
        [value.split(': ', 1)[-1] for value in helped + misled if value]
    )[:8]
    confidence_values = [
        float(item.get('confidence', 0.0) or 0.0)
        for item in list(analysis.skills_analyzed or [])
    ]
    confidence = round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0
    evidence_coverage = _semantic_evidence_coverage(
        run_record=run_record,
        session_evidence=session_evidence,
    )
    concise_summary = (
        f'Runtime evidence for `{run_record.task_summary or run_record.task_id}` '
        f'shows helped={len(helped)} misled={len(misled)} repeated_gaps={len(repeated_gaps)}.'
    )

    return RuntimeSemanticSummary(
        run_id=run_record.run_id,
        task_id=run_record.task_id,
        task_summary=run_record.task_summary or run_record.task_id,
        concise_summary=concise_summary,
        notable_steps=notable_steps,
        what_helped=helped,
        what_misled=misled,
        repeated_gaps=repeated_gaps[:5],
        missing_capabilities=repeated_gaps[:5],
        confidence=confidence,
        evidence_coverage=evidence_coverage,
    )
