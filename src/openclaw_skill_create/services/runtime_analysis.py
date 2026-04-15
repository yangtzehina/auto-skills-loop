from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from ..models.observation import OpenSpaceObservationPolicy
from ..models.request import SkillCreateRequestV6
from ..models.review import RepairSuggestion
from ..models.runtime import (
    EvolutionPlan,
    RuntimeCreateCandidate,
    RuntimeSessionEvidence,
    SkillRunAnalysis,
    SkillRunRecord,
)


HELPER_MODULE = 'openclaw_skill_create.services.openspace_runtime_helper'
SRC_ROOT = Path(__file__).resolve().parents[2]
GAP_KEYWORDS = (
    'missing',
    'lack',
    'lacks',
    'needed',
    'needs',
    'need',
    'should',
    'requires',
    'require',
    'required',
    'gap',
    'not covered',
    'not mention',
    'did not mention',
    'didn\'t mention',
)
SIMPLE_GAP_KEYWORDS = (
    'file',
    'placeholder',
    'todo',
    'stub',
    'frontmatter',
    'metadata',
    '.skill_id',
)
SCRIPT_HINTS = ('script', '.py', '.sh', '.js', '.ts', 'bash', 'python')
EVAL_HINTS = ('eval', 'benchmark', 'trigger_eval', 'output_eval')
PATH_PATTERN = re.compile(r'((?:references|scripts|evals)/[A-Za-z0-9_./-]+|[A-Za-z0-9_./-]+\.(?:py|sh|js|ts|md|json|yaml|yml))')
TRACE_FAILURE_STATUSES = {'failed', 'corrected'}
TRACE_HELPFUL_STATUSES = {'success', 'partial'}
NO_SKILL_HISTORY_ID = '__no_skill__'
OPERATION_HOLD_KEYWORDS = ('write', 'writes', 'delete', 'install', 'download', 'persist', 'save', 'mutate')
OPERATION_SESSION_KEYWORDS = ('session', 'login', 'connect', 'interactive', 'repl')
OPERATION_JSON_KEYWORDS = ('json', '--json', 'structured')
OPERATION_CONFIRMATION_KEYWORDS = ('confirm', 'confirmation', '--force', '-y', 'side effect')


def runtime_analysis_ready(policy: Optional[OpenSpaceObservationPolicy]) -> tuple[bool, str]:
    if policy is None or not policy.enabled:
        return False, 'OpenSpace runtime analysis disabled'
    openspace_python = str(policy.openspace_python or '').strip()
    if not openspace_python:
        return False, 'OpenSpace python not configured'
    if not Path(openspace_python).exists():
        return False, f'OpenSpace python not found: {policy.openspace_python}'
    return True, 'ready'


def _extract_json_line(raw_stdout: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith('{') and line.endswith('}'):
            return json.loads(line)
    raise ValueError('No JSON payload found in helper stdout')


def _normalize_text(value: Any) -> str:
    return re.sub(r'\s+', ' ', str(value or '').strip().lower())


def _step_tokens(step: str) -> list[str]:
    normalized = _normalize_text(step)
    parts = re.split(r'[^a-z0-9]+', normalized)
    return [part for part in parts if len(part) >= 4]


def _text_mentions_step(step: str, text: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_step = _normalize_text(step)
    if normalized_step and normalized_step in normalized_text:
        return True
    tokens = _step_tokens(step)
    if not tokens:
        return False
    hits = sum(1 for token in tokens if token in normalized_text)
    return hits >= min(2, len(tokens))


def _line_targets_skill(line: str, *, skill_usage: dict[str, Any], total_skills: int) -> bool:
    if total_skills <= 1:
        return True
    normalized_line = _normalize_text(line)
    for field in ('skill_id', 'skill_name'):
        value = _normalize_text(skill_usage.get(field, ''))
        if value and value in normalized_line:
            return True
    for step in list(skill_usage.get('steps_triggered') or []):
        if _text_mentions_step(step, line):
            return True
    return False


def _extract_gap_lines(
    *,
    run_record: SkillRunRecord,
    skill_usage: dict[str, Any],
    total_skills: int,
) -> list[str]:
    gaps: list[str] = []
    for line in list(run_record.failure_points) + list(run_record.user_corrections):
        normalized = _normalize_text(line)
        if not any(keyword in normalized for keyword in GAP_KEYWORDS):
            continue
        if _line_targets_skill(line, skill_usage=skill_usage, total_skills=total_skills):
            gaps.append(line)
    return gaps


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in list(values or []):
        text = str(value or '').strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


def _matching_trace_entries(
    *,
    run_record: SkillRunRecord,
    session_evidence: Optional[RuntimeSessionEvidence],
    skill_usage: dict[str, Any],
    total_skills: int,
) -> list[dict[str, Any]]:
    skill_id = _normalize_text(skill_usage.get('skill_id', ''))
    skill_name = _normalize_text(skill_usage.get('skill_name', ''))
    steps_triggered = list(skill_usage.get('steps_triggered') or [])
    matched: list[dict[str, Any]] = []

    trace_source = list(run_record.step_trace or [])
    if session_evidence is not None and session_evidence.turn_trace:
        trace_source = [item.model_dump(mode='python') for item in list(session_evidence.turn_trace or [])]

    for entry in trace_source:
        entry_skill_id = _normalize_text(entry.get('skill_id', ''))
        entry_skill_name = _normalize_text(entry.get('skill_name', ''))
        entry_step = str(entry.get('step') or '').strip()

        if skill_id and entry_skill_id == skill_id:
            matched.append(entry)
            continue
        if skill_name and entry_skill_name == skill_name:
            matched.append(entry)
            continue
        if entry_step and any(
            _text_mentions_step(entry_step, step) or _text_mentions_step(step, entry_step)
            for step in steps_triggered
        ):
            matched.append(entry)
            continue
        if total_skills <= 1 and entry_step and not entry_skill_id and not entry_skill_name:
            matched.append(entry)

    return matched


def _observed_steps(
    *,
    skill_usage: dict[str, Any],
    trace_entries: list[dict[str, Any]],
) -> list[str]:
    trace_steps = [str(entry.get('step') or '').strip() for entry in list(trace_entries or [])]
    return _ordered_unique(list(skill_usage.get('steps_triggered') or []) + trace_steps)


def _flagged_steps(
    skill_usage: dict[str, Any],
    notes: list[str],
    *,
    trace_entries: Optional[list[dict[str, Any]]] = None,
) -> list[str]:
    flagged: list[str] = []
    for entry in list(trace_entries or []):
        step = str(entry.get('step') or '').strip()
        if not step:
            continue
        if str(entry.get('status') or '').strip().lower() in TRACE_FAILURE_STATUSES and step not in flagged:
            flagged.append(step)
    for step in _observed_steps(skill_usage=skill_usage, trace_entries=list(trace_entries or [])):
        if any(_text_mentions_step(step, note) for note in notes):
            if step not in flagged:
                flagged.append(step)
    return flagged


def _select_most_valuable_step(
    *,
    steps_observed: list[str],
    trace_entries: list[dict[str, Any]],
    notes: list[str],
) -> str:
    for entry in list(trace_entries or []):
        step = str(entry.get('step') or '').strip()
        status = str(entry.get('status') or '').strip().lower()
        if not step or status not in TRACE_HELPFUL_STATUSES:
            continue
        if not any(_text_mentions_step(step, line) for line in notes):
            return step
    for step in list(steps_observed or []):
        if not any(_text_mentions_step(step, line) for line in notes):
            return step
    return ''


def _extract_target_paths(*, skill_usage: dict[str, Any], missing_steps: list[str], misleading_step: str) -> list[str]:
    candidates: list[str] = []
    for value in list(skill_usage.get('steps_triggered') or []) + missing_steps + [misleading_step, skill_usage.get('notes', '')]:
        for match in PATH_PATTERN.findall(str(value or '')):
            cleaned = match.strip().strip('.,;:()[]{}')
            if cleaned:
                candidates.append(cleaned)
    deduped: list[str] = []
    for value in candidates:
        if value not in deduped:
            deduped.append(value)
    return deduped[:6]


def _operation_groups(skill_usage: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    contract = dict(skill_usage.get('operation_contract') or {})
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for raw_group in list(contract.get('operations') or []):
        if not isinstance(raw_group, dict):
            continue
        group_name = str(raw_group.get('name') or '').strip() or 'operations'
        operations = [
            dict(item)
            for item in list(raw_group.get('operations') or [])
            if isinstance(item, dict) and str(item.get('name') or '').strip()
        ]
        if operations:
            groups.append((group_name, operations))
    return groups


def _operation_gap_hints(
    *,
    skill_usage: dict[str, Any],
    missing_steps: list[str],
    misleading_step: str,
    notes: list[str] | None = None,
) -> list[dict[str, Any]]:
    skill_archetype = str(skill_usage.get('skill_archetype') or 'guidance').strip().lower()
    if skill_archetype != 'operation_backed':
        return []

    contract = dict(skill_usage.get('operation_contract') or {})
    surface_text = _normalize_text(
        ' '.join(
            list(missing_steps or [])
            + [misleading_step]
            + list(notes or [])
            + [str(skill_usage.get('notes') or '')]
        )
    )
    hints: list[dict[str, Any]] = []
    observed_steps = {
        _normalize_text(step)
        for step in list(skill_usage.get('steps_triggered') or [])
        if _normalize_text(step)
    }

    mutability = str(contract.get('mutability') or 'read_only').strip().lower()
    if mutability == 'read_only' and any(keyword in surface_text for keyword in OPERATION_HOLD_KEYWORDS):
        return [
            {
                'gap_type': 'contract_surface_drift',
                'reason': 'Runtime evidence suggests mutating behavior even though the operation contract is read-only.',
                'recommended_action': 'hold',
            }
        ]

    if bool(contract.get('supports_json')) and any(keyword in surface_text for keyword in OPERATION_JSON_KEYWORDS):
        hints.append(
            {
                'gap_type': 'missing_json_surface',
                'reason': 'Runtime evidence asked for a JSON surface that the current skill surface did not make clear.',
                'recommended_action': 'patch_current',
            }
        )

    if str(contract.get('session_model') or 'stateless').strip().lower() == 'session_required' and any(
        keyword in surface_text for keyword in OPERATION_SESSION_KEYWORDS
    ):
        hints.append(
            {
                'gap_type': 'missing_session_model',
                'reason': 'Runtime evidence referenced a session lifecycle that the current skill surface did not explain.',
                'recommended_action': 'patch_current',
            }
        )

    safety_profile = dict(contract.get('safety_profile') or {})
    if (
        mutability in {'mixed', 'mutating'}
        and bool(safety_profile.get('confirmation_required'))
        and any(keyword in surface_text for keyword in OPERATION_CONFIRMATION_KEYWORDS)
    ):
        hints.append(
            {
                'gap_type': 'missing_mutating_safeguards',
                'reason': 'Mutating operation coverage needs stronger confirmation, precondition, or side-effect guidance.',
                'recommended_action': 'patch_current',
            }
        )

    matched_groups: dict[str, list[str]] = {}
    for group_name, operations in _operation_groups(skill_usage):
        for operation in operations:
            operation_name = str(operation.get('name') or '').strip()
            summary = str(operation.get('summary') or '').strip()
            if _text_mentions_step(operation_name, surface_text) or (summary and _text_mentions_step(summary, surface_text)):
                matched_groups.setdefault(group_name, []).append(operation_name)

    for group_name, operations in _operation_groups(skill_usage):
        matched_names = matched_groups.get(group_name, [])
        if not matched_names:
            continue
        missing_operation_names = [
            operation_name
            for operation_name in matched_names
            if _normalize_text(operation_name) not in observed_steps
        ]
        if not missing_operation_names:
            continue
        operation_names = [str(item.get('name') or '').strip() for item in operations if str(item.get('name') or '').strip()]
        if len(missing_operation_names) >= len(operation_names) and len(operation_names) > 1:
            hints.append(
                {
                    'gap_type': 'missing_operation_group',
                    'operation_group': group_name,
                    'reason': f'Runtime evidence points at an uncovered operation group `{group_name}`.',
                    'recommended_action': 'derive_child',
                }
            )
            continue
        for operation_name in missing_operation_names:
            hints.append(
                {
                    'gap_type': 'missing_operation',
                    'operation_group': group_name,
                    'operation_name': operation_name,
                    'reason': f'Runtime evidence points at an uncovered operation `{operation_name}`.',
                    'recommended_action': 'derive_child',
                }
            )

    if misleading_step and not hints:
        hints.append(
            {
                'gap_type': 'contract_surface_drift',
                'reason': 'Runtime evidence suggests the current operation-backed instructions drifted from the declared contract surface.',
                'recommended_action': 'patch_current',
            }
        )
    return hints


def _infer_repair_issue_type(*, target_paths: list[str], skill_usage: dict[str, Any], misleading_step: str, missing_steps: list[str]) -> str:
    combined = ' '.join(target_paths + list(skill_usage.get('steps_triggered') or []) + missing_steps + [misleading_step, skill_usage.get('notes', '')]).lower()
    if any(path.startswith('scripts/') for path in target_paths) or any(hint in combined for hint in SCRIPT_HINTS):
        return 'script_placeholder_heavy'
    if any(path.startswith('evals/') for path in target_paths) or any(hint in combined for hint in EVAL_HINTS):
        return 'invalid_eval_scaffold'
    return 'reference_structure_incomplete'


def _is_simple_gap(line: str) -> bool:
    normalized = _normalize_text(line)
    return any(keyword in normalized for keyword in SIMPLE_GAP_KEYWORDS)


def _history_window(entries: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(entries) <= limit:
        return list(entries)
    return list(entries[-limit:])


def _build_patch_suggestions(
    *,
    skill_usage: dict[str, Any],
    misleading_step: str,
    missing_steps: list[str],
    skill_archetype: str = 'guidance',
) -> list[RepairSuggestion]:
    target_paths = _extract_target_paths(
        skill_usage=skill_usage,
        missing_steps=missing_steps,
        misleading_step=misleading_step,
    )
    if skill_archetype == 'operation_backed':
        target_paths = _ordered_unique(
            target_paths
            + ['SKILL.md', 'references/operations/contract.json', 'evals/operation_validation.json', 'evals/operation_coverage.json']
            + (
                ['scripts/operation_helper.py']
                if str(dict(skill_usage.get('operation_contract') or {}).get('backend_kind') or 'python_backend') != 'repo_native_cli'
                else []
            )
        )
    issue_type = _infer_repair_issue_type(
        target_paths=target_paths,
        skill_usage=skill_usage,
        misleading_step=misleading_step,
        missing_steps=missing_steps,
    )
    repair_scope = 'body_patch' if target_paths or missing_steps else 'description_only'
    instruction = (
        f'Patch the current skill so the runtime step `{misleading_step}` stops misleading downstream execution.'
        if misleading_step
        else 'Patch the current skill to address repeated runtime misalignment.'
    )
    if missing_steps:
        instruction += f' Cover these missing runtime gaps: {", ".join(missing_steps[:3])}.'
    return [
        RepairSuggestion(
            issue_type=issue_type,
            instruction=instruction,
            target_paths=target_paths,
            priority=90 if misleading_step else 80,
            repair_scope=repair_scope,
        )
    ]


def _gap_cluster_from_history(
    history: list[dict[str, Any]],
    current_gaps: list[str],
) -> tuple[str, int]:
    gap_cluster: dict[str, int] = {}
    gap_examples: dict[str, str] = {}
    for gap in current_gaps:
        normalized = _normalize_text(gap)
        if not normalized:
            continue
        gap_cluster[normalized] = gap_cluster.get(normalized, 0) + 1
        gap_examples.setdefault(normalized, gap)
    for item in history:
        for gap in list(item.get('missing_steps') or []):
            normalized = _normalize_text(gap)
            if not normalized:
                continue
            gap_cluster[normalized] = gap_cluster.get(normalized, 0) + 1
            gap_examples.setdefault(normalized, gap)

    repeated_gap = ''
    repeated_gap_count = 0
    for normalized, count in gap_cluster.items():
        if count > repeated_gap_count and not _is_simple_gap(gap_examples.get(normalized, normalized)):
            repeated_gap = gap_examples.get(normalized, normalized)
            repeated_gap_count = count
    return repeated_gap, repeated_gap_count


def _extract_global_gap_lines(run_record: SkillRunRecord) -> list[str]:
    gaps: list[str] = []
    for line in list(run_record.failure_points) + list(run_record.user_corrections):
        normalized = _normalize_text(line)
        if normalized and any(keyword in normalized for keyword in GAP_KEYWORDS):
            gaps.append(line)
    return gaps


def _build_runtime_create_candidate(
    *,
    run_record: SkillRunRecord,
    repeated_gap: str,
    repeated_gap_count: int,
    current_gaps: list[str],
    history: list[dict[str, Any]],
) -> RuntimeCreateCandidate:
    candidate_key = re.sub(r'[^a-z0-9]+', '-', _normalize_text(repeated_gap or run_record.task_id)).strip('-')
    source_run_ids = [
        str(item.get('run_id') or '').strip()
        for item in _history_window(history, 4)
        if str(item.get('run_id') or '').strip()
    ]
    if run_record.run_id not in source_run_ids:
        source_run_ids.append(run_record.run_id)
    gaps = _ordered_unique(current_gaps or ([repeated_gap] if repeated_gap else []))
    return RuntimeCreateCandidate(
        candidate_id=f'create-{candidate_key or "runtime-gap"}',
        candidate_kind='no_skill',
        task_summary=run_record.task_summary or run_record.task_id,
        reason=(
            f'No existing skill applied cleanly and runtime evidence repeated the same gap '
            f'{repeated_gap_count} time(s): {repeated_gap}'
        ),
        requirement_gaps=gaps[:5],
        source_run_ids=source_run_ids[-5:],
        confidence=0.82 if repeated_gap_count >= 3 else 0.7,
    )


def _enrich_record_with_session_evidence(
    record: SkillRunRecord,
    session_evidence: Optional[RuntimeSessionEvidence | dict[str, Any]],
) -> tuple[SkillRunRecord, Optional[RuntimeSessionEvidence]]:
    if session_evidence is None:
        return record, None
    evidence = (
        session_evidence
        if isinstance(session_evidence, RuntimeSessionEvidence)
        else RuntimeSessionEvidence.model_validate(session_evidence)
    )
    enriched = record.model_copy(
        update={
            'step_trace': [item.model_dump(mode='python') for item in list(evidence.turn_trace or [])] or list(record.step_trace or []),
            'phase_markers': list(evidence.phase_markers or []) or list(record.phase_markers or []),
            'tool_summary': list(evidence.tool_summary or []) or list(record.tool_summary or []),
        }
    )
    return enriched, evidence


def encode_runtime_judgment_note(skill_analysis: dict[str, Any]) -> str:
    payload = {
        'run_id': skill_analysis.get('run_id', ''),
        'skill_archetype': skill_analysis.get('skill_archetype', 'guidance'),
        'helped': bool(skill_analysis.get('helped', False)),
        'run_quality_score': float(skill_analysis.get('run_quality_score', 0.0) or 0.0),
        'recommended_action': skill_analysis.get('recommended_action', 'no_change'),
        'recommended_followup': skill_analysis.get('recommended_followup', 'no_change'),
        'most_valuable_step': skill_analysis.get('most_valuable_step', ''),
        'misleading_step': skill_analysis.get('misleading_step', ''),
        'missing_steps': list(skill_analysis.get('missing_steps', []) or []),
        'coverage_gap_summary': list(skill_analysis.get('coverage_gap_summary', []) or []),
        'operation_validation_status': skill_analysis.get('operation_validation_status', ''),
        'quality_score': float(skill_analysis.get('quality_score', 0.0) or 0.0),
        'usage_stats': dict(skill_analysis.get('usage_stats') or {}),
        'recent_run_ids': list(skill_analysis.get('recent_run_ids', []) or []),
        'parent_skill_ids': list(skill_analysis.get('parent_skill_ids', []) or []),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def decode_runtime_judgment_note(note: str) -> dict[str, Any]:
    raw = (note or '').strip()
    if not raw.startswith('{'):
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def analyze_skill_run_deterministically(
    run_record: SkillRunRecord | dict[str, Any],
    *,
    session_evidence: Optional[RuntimeSessionEvidence | dict[str, Any]] = None,
    recent_skill_history: Optional[dict[str, list[dict[str, Any]]]] = None,
    parent_skill_ids: Optional[dict[str, list[str]]] = None,
) -> SkillRunAnalysis:
    record = (
        run_record
        if isinstance(run_record, SkillRunRecord)
        else SkillRunRecord.model_validate(run_record)
    )
    record, evidence = _enrich_record_with_session_evidence(record, session_evidence)
    recent_skill_history = recent_skill_history or {}
    parent_skill_ids = parent_skill_ids or {}
    analyzed: list[dict[str, Any]] = []
    plans: list[EvolutionPlan] = []
    create_candidates: list[RuntimeCreateCandidate] = []
    total_skills = max(len(record.skills_used), 1)
    notes = list(record.failure_points) + list(record.user_corrections)
    applied_skill_count = 0
    phase_markers = list(evidence.phase_markers or []) if evidence is not None and evidence.phase_markers else list(record.phase_markers or [])
    tool_summary = list(evidence.tool_summary or []) if evidence is not None and evidence.tool_summary else list(record.tool_summary or [])

    for skill_usage in list(record.skills_used):
        skill_id = skill_usage.get('skill_id', '')
        history = _history_window(list(recent_skill_history.get(skill_id, []) or []), 9)
        trace_entries = _matching_trace_entries(
            run_record=record,
            session_evidence=evidence,
            skill_usage=skill_usage,
            total_skills=total_skills,
        )
        steps_triggered = _observed_steps(skill_usage=skill_usage, trace_entries=trace_entries)
        flagged = _flagged_steps(skill_usage, notes, trace_entries=trace_entries)
        misleading_step = flagged[0] if flagged else ''
        missing_steps = _extract_gap_lines(
            run_record=record,
            skill_usage=skill_usage,
            total_skills=total_skills,
        )
        applied = bool(skill_usage.get('applied', False))
        selected = bool(skill_usage.get('selected', False))
        if applied:
            applied_skill_count += 1
        helped = (
            applied
            and record.execution_result in {'success', 'partial'}
            and bool(steps_triggered)
            and not misleading_step
        )

        if applied and misleading_step:
            run_quality_score = 0.0
        elif helped and record.execution_result == 'success':
            run_quality_score = 1.0
        elif helped and record.execution_result == 'partial':
            run_quality_score = 0.6
        elif selected and not applied:
            run_quality_score = 0.25
        elif applied:
            run_quality_score = 0.0
        else:
            run_quality_score = 0.25 if selected else 0.0

        most_valuable_step = _select_most_valuable_step(
            steps_observed=steps_triggered,
            trace_entries=trace_entries,
            notes=notes,
        )

        recent_five = _history_window(history, 4)
        recent_zero_count = sum(
            1
            for item in recent_five
            if float(item.get('run_quality_score', 0.0) or 0.0) == 0.0
        )
        if run_quality_score == 0.0:
            recent_zero_count += 1

        repeated_gap, repeated_gap_count = _gap_cluster_from_history(recent_five, missing_steps)
        skill_archetype = str(skill_usage.get('skill_archetype') or 'guidance').strip().lower() or 'guidance'
        operation_gaps = _operation_gap_hints(
            skill_usage=skill_usage,
            missing_steps=missing_steps,
            misleading_step=misleading_step,
            notes=notes,
        )
        coverage_gap_types = _ordered_unique([str(item.get('gap_type') or '').strip() for item in operation_gaps])
        operation_validation_status = str(skill_usage.get('operation_validation_status') or '').strip().lower()

        if any(item.get('recommended_action') == 'hold' for item in operation_gaps):
            recommended_action = 'hold'
        elif any(item.get('recommended_action') == 'derive_child' for item in operation_gaps):
            recommended_action = 'derive_child'
        elif any(item.get('recommended_action') == 'patch_current' for item in operation_gaps):
            recommended_action = 'patch_current'
        elif (applied and misleading_step) or recent_zero_count >= 2:
            recommended_action = 'patch_current'
        elif repeated_gap and repeated_gap_count >= 3:
            recommended_action = 'derive_child'
        else:
            recommended_action = 'no_change'

        confidence = 0.85 if recommended_action != 'no_change' else 0.7
        if selected and not applied:
            confidence = 0.6
        rationale_parts = [
            f'execution_result={record.execution_result}',
            f'applied={applied}',
            f'selected={selected}',
            f'steps={len(steps_triggered)}',
            f'flagged_steps={len(flagged)}',
        ]
        if trace_entries:
            rationale_parts.append(f'trace_steps={len(trace_entries)}')
        if phase_markers:
            rationale_parts.append(f'phases={len(phase_markers)}')
        if tool_summary:
            rationale_parts.append(f'tools={len(tool_summary)}')
        if missing_steps:
            rationale_parts.append(f'missing_steps={len(missing_steps)}')
        if repeated_gap_count:
            rationale_parts.append(f'repeated_gap_count={repeated_gap_count}')
        if coverage_gap_types:
            rationale_parts.append(f'operation_gaps={coverage_gap_types}')
        rationale = '; '.join(rationale_parts)

        history_with_current = history + [
            {
                'run_id': record.run_id,
                'run_quality_score': run_quality_score,
                'recommended_action': recommended_action,
                'missing_steps': list(missing_steps),
            }
        ]
        quality_window = _history_window(history_with_current, 10)
        quality_score = round(
            sum(float(item.get('run_quality_score', 0.0) or 0.0) for item in quality_window) / len(quality_window),
            4,
        ) if quality_window else 0.0
        usage_stats = {
            'run_count': len(history_with_current),
            'helped_count': sum(
                1
                for item in quality_window
                if float(item.get('run_quality_score', 0.0) or 0.0) >= 0.6
            ),
            'misled_count': sum(
                1
                for item in quality_window
                if float(item.get('run_quality_score', 0.0) or 0.0) == 0.0
            ),
            'patch_count': sum(
                1
                for item in quality_window
                if str(item.get('recommended_action') or '') == 'patch_current'
            ),
            'derive_count': sum(
                1
                for item in quality_window
                if str(item.get('recommended_action') or '') == 'derive_child'
            ),
        }
        recent_run_ids = [
            str(item.get('run_id') or '').strip()
            for item in _history_window(history_with_current, 5)
            if str(item.get('run_id') or '').strip()
        ]
        current_parent_ids = list(parent_skill_ids.get(skill_id, []) or [])

        skill_analysis = {
            'run_id': record.run_id,
            'skill_id': skill_id,
            'skill_name': skill_usage.get('skill_name', ''),
            'skill_archetype': skill_archetype,
            'helped': helped,
            'most_valuable_step': most_valuable_step,
            'misleading_step': misleading_step,
            'missing_steps': missing_steps,
            'run_quality_score': run_quality_score,
            'recommended_action': recommended_action,
            'confidence': confidence,
            'rationale': rationale,
            'quality_score': quality_score,
            'usage_stats': usage_stats,
            'recent_run_ids': recent_run_ids,
            'parent_skill_ids': current_parent_ids,
            'operation_validation_status': operation_validation_status,
            'coverage_gap_summary': coverage_gap_types,
            'recommended_followup': recommended_action,
        }
        analyzed.append(skill_analysis)

        if recommended_action == 'patch_current':
            repair_suggestions = _build_patch_suggestions(
                skill_usage=skill_usage,
                misleading_step=misleading_step,
                missing_steps=missing_steps,
                skill_archetype=skill_archetype,
            )
            plans.append(
                EvolutionPlan(
                    run_id=record.run_id,
                    skill_id=skill_id,
                    action='patch_current',
                    skill_archetype=skill_archetype,
                    parent_skill_id=skill_id or None,
                    reason=(
                        f'Runtime analysis marked `{misleading_step}` as misleading.'
                        if misleading_step
                        else 'Runtime analysis observed repeated low-quality runs for this skill.'
                    ),
                    repair_suggestions=repair_suggestions,
                    requirement_gaps=missing_steps,
                    coverage_gap_types=coverage_gap_types,
                    operation_group=str(operation_gaps[0].get('operation_group') or '') if operation_gaps else '',
                    operation_name=str(operation_gaps[0].get('operation_name') or '') if operation_gaps else '',
                    operation_validation_status=operation_validation_status,
                    recommended_followup='patch_current',
                    summary='Patch the current skill to address runtime misalignment.',
                )
            )
        elif recommended_action == 'derive_child':
            plans.append(
                EvolutionPlan(
                    run_id=record.run_id,
                    skill_id=skill_id,
                    action='derive_child',
                    skill_archetype=skill_archetype,
                    parent_skill_id=skill_id or None,
                    reason=(
                        str(operation_gaps[0].get('reason') or '').strip()
                        if operation_gaps
                        else f'Recurring runtime gap suggests a stable specialization need: {repeated_gap}'
                    ),
                    requirement_gaps=missing_steps or ([repeated_gap] if repeated_gap else []),
                    coverage_gap_types=coverage_gap_types,
                    operation_group=str(operation_gaps[0].get('operation_group') or '') if operation_gaps else '',
                    operation_name=str(operation_gaps[0].get('operation_name') or '') if operation_gaps else '',
                    operation_validation_status=operation_validation_status,
                    recommended_followup='derive_child',
                    summary='Derive a child skill to cover repeated domain-specific gaps.',
                )
            )
        elif recommended_action == 'hold':
            plans.append(
                EvolutionPlan(
                    run_id=record.run_id,
                    skill_id=skill_id,
                    action='hold',
                    skill_archetype=skill_archetype,
                    parent_skill_id=skill_id or None,
                    reason=(operation_gaps[0].get('reason') if operation_gaps else 'Runtime evidence requires a manual hold.'),
                    requirement_gaps=missing_steps,
                    coverage_gap_types=coverage_gap_types,
                    operation_group=str(operation_gaps[0].get('operation_group') or '') if operation_gaps else '',
                    operation_name=str(operation_gaps[0].get('operation_name') or '') if operation_gaps else '',
                    operation_validation_status=operation_validation_status,
                    recommended_followup='hold',
                    summary='Hold follow-up until contract or safety alignment improves.',
                )
            )
        else:
            plans.append(
                EvolutionPlan(
                    run_id=record.run_id,
                    skill_id=skill_id,
                    action='no_change',
                    skill_archetype=skill_archetype,
                    parent_skill_id=skill_id or None,
                    reason='Runtime evidence does not justify patch or derive actions.',
                    coverage_gap_types=coverage_gap_types,
                    operation_validation_status=operation_validation_status,
                    recommended_followup='no_change',
                    summary='No runtime evolution change is recommended.',
                )
            )

    helped_count = sum(1 for item in analyzed if item.get('helped'))
    misled_count = sum(1 for item in analyzed if item.get('recommended_action') == 'patch_current')
    if applied_skill_count == 0:
        no_skill_history = _history_window(list(recent_skill_history.get(NO_SKILL_HISTORY_ID, []) or []), 4)
        global_gaps = [line for line in _extract_global_gap_lines(record) if not _is_simple_gap(line)]
        repeated_gap, repeated_gap_count = _gap_cluster_from_history(no_skill_history, global_gaps)
        if repeated_gap and repeated_gap_count >= 3:
            create_candidates.append(
                _build_runtime_create_candidate(
                    run_record=record,
                    repeated_gap=repeated_gap,
                    repeated_gap_count=repeated_gap_count,
                    current_gaps=global_gaps,
                    history=no_skill_history,
                )
            )

    summary = (
        f'Runtime analysis complete: skills={len(analyzed)}, helped={helped_count}, '
        f'patch={misled_count}, create_candidates={len(create_candidates)}'
    )
    return SkillRunAnalysis(
        run_id=record.run_id,
        task_id=record.task_id,
        execution_result=record.execution_result,
        skills_analyzed=analyzed,
        evolution_plans=plans,
        create_candidates=create_candidates,
        summary=summary,
    )


def analyze_skill_run(
    run_record: SkillRunRecord | dict[str, Any],
    policy: Optional[OpenSpaceObservationPolicy],
    *,
    session_evidence: Optional[RuntimeSessionEvidence | dict[str, Any]] = None,
) -> SkillRunAnalysis:
    record = (
        run_record
        if isinstance(run_record, SkillRunRecord)
        else SkillRunRecord.model_validate(run_record)
    )
    record, normalized_evidence = _enrich_record_with_session_evidence(record, session_evidence)
    fallback = analyze_skill_run_deterministically(record, session_evidence=normalized_evidence)
    ready, reason = runtime_analysis_ready(policy)
    if not ready:
        fallback.summary = f'{fallback.summary} | store_persistence=skipped ({reason})'
        return fallback

    assert policy is not None
    payload = {
        'run_record': record.model_dump(mode='json'),
        'db_path': policy.db_path,
        'analyzed_by': policy.analyzed_by.replace('observe-only', 'runtime-analysis'),
    }
    env = os.environ.copy()
    existing_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(SRC_ROOT) if not existing_pythonpath else f'{SRC_ROOT}:{existing_pythonpath}'

    completed = subprocess.run(
        [policy.openspace_python, '-m', HELPER_MODULE],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        env=env,
        timeout=policy.timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        fallback.summary = f'{fallback.summary} | store_persistence=failed (helper exit {completed.returncode})'
        return fallback
    try:
        result = _extract_json_line(completed.stdout)
        analysis_payload = result.get('analysis') or result
        analysis = SkillRunAnalysis.model_validate(analysis_payload)
        if result.get('applied') is False and result.get('reason'):
            analysis.summary = f'{analysis.summary} | store_persistence=failed ({result["reason"]})'
        return analysis
    except Exception as exc:  # pragma: no cover - defensive helper boundary
        fallback.summary = f'{fallback.summary} | store_persistence=failed ({exc})'
        return fallback


def evolution_plan_to_repair_suggestions(plan: EvolutionPlan | dict[str, Any]) -> list[RepairSuggestion]:
    normalized = plan if isinstance(plan, EvolutionPlan) else EvolutionPlan.model_validate(plan)
    if normalized.action != 'patch_current':
        return []
    if normalized.repair_suggestions:
        return list(normalized.repair_suggestions)
    return [
        RepairSuggestion(
            issue_type='reference_structure_incomplete',
            instruction=normalized.reason or 'Patch the current skill based on runtime analysis.',
            target_paths=[],
            priority=80,
            repair_scope='body_patch',
        )
    ]


def evolution_plan_to_skill_create_request(
    plan: EvolutionPlan | dict[str, Any],
    *,
    task_summary: Optional[str] = None,
    repo_paths: Optional[list[str]] = None,
    skill_name_hint: Optional[str] = None,
) -> SkillCreateRequestV6:
    normalized = plan if isinstance(plan, EvolutionPlan) else EvolutionPlan.model_validate(plan)
    base_name = skill_name_hint or normalized.skill_id.split('__', 1)[0] or normalized.skill_id
    request_task = str(task_summary or '').strip()
    provided_task_summary = bool(request_task)
    if not request_task:
        request_task = (
            normalized.summary
            or normalized.reason
            or f'Follow up on runtime evolution plan for {normalized.skill_id}.'
        )
    if normalized.summary and (provided_task_summary or normalized.summary != request_task):
        request_task = f'{request_task}\n\nRuntime evolution goal: {normalized.summary}'
    if normalized.requirement_gaps:
        request_task += f'\nRequirement gaps: {", ".join(normalized.requirement_gaps[:5])}'
    if normalized.reason:
        request_task += f'\nReason: {normalized.reason}'
    return SkillCreateRequestV6(
        task=request_task.strip(),
        repo_paths=list(repo_paths or []),
        skill_name_hint=f'{base_name}-derived' if normalized.action == 'derive_child' else base_name,
        enable_eval_scaffold=True,
        enable_repair=True,
        parent_skill_id=normalized.parent_skill_id or normalized.skill_id,
        runtime_evolution_plan=normalized,
    )
