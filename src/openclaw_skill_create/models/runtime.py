from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .review import RepairSuggestion


ALLOWED_EXECUTION_RESULTS = {'success', 'partial', 'failed'}
ALLOWED_RUNTIME_ACTIONS = {'patch_current', 'derive_child', 'hold', 'no_change'}
ALLOWED_TRACE_STATUSES = {'success', 'partial', 'failed', 'corrected', 'skipped', 'unknown'}


def _normalize_string_list(values: Any) -> list[str]:
    result: list[str] = []
    for value in list(values or []):
        text = str(value or '').strip()
        if text:
            result.append(text)
    return result


def _normalize_execution_result(value: Any) -> str:
    normalized = str(value or 'success').strip().lower()
    if normalized in ALLOWED_EXECUTION_RESULTS:
        return normalized
    return 'success'


def _normalize_runtime_action(value: Any) -> str:
    normalized = str(value or 'no_change').strip().lower()
    if normalized in ALLOWED_RUNTIME_ACTIONS:
        return normalized
    return 'no_change'


def _normalize_trace_status(value: Any) -> str:
    normalized = str(value or 'unknown').strip().lower()
    if normalized in ALLOWED_TRACE_STATUSES:
        return normalized
    return 'unknown'


def _normalize_skill_usage_entry(value: Any) -> dict[str, Any]:
    item = dict(value or {})
    return {
        'skill_id': str(item.get('skill_id') or '').strip(),
        'skill_name': str(item.get('skill_name') or '').strip(),
        'skill_path': str(item.get('skill_path') or '').strip(),
        'selected': bool(item.get('selected', False)),
        'applied': bool(item.get('applied', False)),
        'steps_triggered': _normalize_string_list(item.get('steps_triggered')),
        'notes': str(item.get('notes') or '').strip(),
        'skill_archetype': str(item.get('skill_archetype') or 'guidance').strip().lower() or 'guidance',
        'operation_contract': dict(item.get('operation_contract') or {}),
        'operation_validation_status': str(item.get('operation_validation_status') or '').strip().lower(),
        'coverage_gap_summary': _normalize_string_list(item.get('coverage_gap_summary')),
    }


def _normalize_step_trace_entry(value: Any) -> dict[str, Any]:
    item = dict(value or {})
    return {
        'skill_id': str(item.get('skill_id') or '').strip(),
        'skill_name': str(item.get('skill_name') or '').strip(),
        'step': str(item.get('step') or '').strip(),
        'phase': str(item.get('phase') or '').strip(),
        'tool': str(item.get('tool') or '').strip(),
        'status': _normalize_trace_status(item.get('status')),
        'notes': str(item.get('notes') or '').strip(),
    }


def _normalize_runtime_create_candidate(value: Any) -> dict[str, Any]:
    item = dict(value or {})
    return {
        'candidate_id': str(item.get('candidate_id') or '').strip(),
        'candidate_kind': str(item.get('candidate_kind') or 'no_skill').strip().lower() or 'no_skill',
        'task_summary': str(item.get('task_summary') or '').strip(),
        'reason': str(item.get('reason') or '').strip(),
        'requirement_gaps': _normalize_string_list(item.get('requirement_gaps')),
        'source_run_ids': _normalize_string_list(item.get('source_run_ids')),
        'confidence': float(item.get('confidence', 0.0) or 0.0),
    }


def _normalize_skill_analysis_entry(value: Any) -> dict[str, Any]:
    item = dict(value or {})
    return {
        'skill_id': str(item.get('skill_id') or '').strip(),
        'skill_name': str(item.get('skill_name') or '').strip(),
        'skill_archetype': str(item.get('skill_archetype') or 'guidance').strip().lower() or 'guidance',
        'helped': bool(item.get('helped', False)),
        'most_valuable_step': str(item.get('most_valuable_step') or '').strip(),
        'misleading_step': str(item.get('misleading_step') or '').strip(),
        'missing_steps': _normalize_string_list(item.get('missing_steps')),
        'run_quality_score': float(item.get('run_quality_score', 0.0) or 0.0),
        'recommended_action': _normalize_runtime_action(item.get('recommended_action')),
        'confidence': float(item.get('confidence', 0.0) or 0.0),
        'rationale': str(item.get('rationale') or '').strip(),
        'quality_score': float(item.get('quality_score', 0.0) or 0.0),
        'usage_stats': dict(item.get('usage_stats') or {}),
        'recent_run_ids': _normalize_string_list(item.get('recent_run_ids')),
        'parent_skill_ids': _normalize_string_list(item.get('parent_skill_ids')),
        'operation_validation_status': str(item.get('operation_validation_status') or '').strip().lower(),
        'coverage_gap_summary': _normalize_string_list(item.get('coverage_gap_summary')),
        'recommended_followup': str(item.get('recommended_followup') or '').strip().lower(),
    }


class RuntimeTurnTrace(BaseModel):
    skill_id: str = ''
    skill_name: str = ''
    step: str = ''
    phase: str = ''
    tool: str = ''
    status: str = 'unknown'
    notes: str = ''

    def model_post_init(self, __context: Any) -> None:
        normalized = _normalize_step_trace_entry(self.model_dump(mode='python'))
        self.skill_id = normalized['skill_id']
        self.skill_name = normalized['skill_name']
        self.step = normalized['step']
        self.phase = normalized['phase']
        self.tool = normalized['tool']
        self.status = normalized['status']
        self.notes = normalized['notes']


class RuntimeSessionEvidence(BaseModel):
    run_id: str
    task_id: str
    turn_trace: list[RuntimeTurnTrace] = Field(default_factory=list)
    phase_markers: list[str] = Field(default_factory=list)
    tool_summary: list[str] = Field(default_factory=list)
    failure_points: list[str] = Field(default_factory=list)
    user_corrections: list[str] = Field(default_factory=list)
    output_summary: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.run_id = str(self.run_id or '').strip()
        self.task_id = str(self.task_id or '').strip()
        self.turn_trace = [
            item if isinstance(item, RuntimeTurnTrace) else RuntimeTurnTrace.model_validate(item)
            for item in list(self.turn_trace or [])
        ]
        self.phase_markers = _normalize_string_list(self.phase_markers)
        self.tool_summary = _normalize_string_list(self.tool_summary)
        self.failure_points = _normalize_string_list(self.failure_points)
        self.user_corrections = _normalize_string_list(self.user_corrections)
        self.output_summary = str(self.output_summary or '').strip()


class RuntimeSemanticSummary(BaseModel):
    run_id: str
    task_id: str
    task_summary: str = ''
    concise_summary: str = ''
    notable_steps: list[str] = Field(default_factory=list)
    what_helped: list[str] = Field(default_factory=list)
    what_misled: list[str] = Field(default_factory=list)
    repeated_gaps: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence_coverage: float = 0.0

    def model_post_init(self, __context: Any) -> None:
        self.run_id = str(self.run_id or '').strip()
        self.task_id = str(self.task_id or '').strip()
        self.task_summary = str(self.task_summary or '').strip()
        self.concise_summary = str(self.concise_summary or '').strip()
        self.notable_steps = _normalize_string_list(self.notable_steps)
        self.what_helped = _normalize_string_list(self.what_helped)
        self.what_misled = _normalize_string_list(self.what_misled)
        self.repeated_gaps = _normalize_string_list(self.repeated_gaps)
        self.missing_capabilities = _normalize_string_list(self.missing_capabilities)
        self.confidence = float(self.confidence or 0.0)
        self.evidence_coverage = float(self.evidence_coverage or 0.0)


class RuntimeCreateCandidate(BaseModel):
    candidate_id: str
    candidate_kind: str = 'no_skill'
    task_summary: str = ''
    reason: str = ''
    requirement_gaps: list[str] = Field(default_factory=list)
    source_run_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    def model_post_init(self, __context: Any) -> None:
        normalized = _normalize_runtime_create_candidate(self.model_dump(mode='python'))
        self.candidate_id = normalized['candidate_id']
        self.candidate_kind = normalized['candidate_kind']
        self.task_summary = normalized['task_summary']
        self.reason = normalized['reason']
        self.requirement_gaps = normalized['requirement_gaps']
        self.source_run_ids = normalized['source_run_ids']
        self.confidence = normalized['confidence']


class SkillRunRecord(BaseModel):
    run_id: str
    task_id: str
    task_summary: str = ''
    skills_used: list[dict[str, Any]] = Field(default_factory=list)
    execution_result: str = 'success'
    failure_points: list[str] = Field(default_factory=list)
    user_corrections: list[str] = Field(default_factory=list)
    output_summary: str = ''
    repo_paths: list[str] = Field(default_factory=list)
    step_trace: list[dict[str, Any]] = Field(default_factory=list)
    phase_markers: list[str] = Field(default_factory=list)
    tool_summary: list[str] = Field(default_factory=list)
    completed_at: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.task_summary = str(self.task_summary or '').strip()
        self.execution_result = _normalize_execution_result(self.execution_result)
        self.failure_points = _normalize_string_list(self.failure_points)
        self.user_corrections = _normalize_string_list(self.user_corrections)
        self.repo_paths = _normalize_string_list(self.repo_paths)
        self.step_trace = [_normalize_step_trace_entry(item) for item in list(self.step_trace or [])]
        self.phase_markers = _normalize_string_list(self.phase_markers)
        self.tool_summary = _normalize_string_list(self.tool_summary)
        self.completed_at = str(self.completed_at or '').strip()
        self.output_summary = str(self.output_summary or '').strip()
        self.skills_used = [_normalize_skill_usage_entry(item) for item in list(self.skills_used or [])]


class EvolutionPlan(BaseModel):
    run_id: str
    skill_id: str
    action: str = 'no_change'
    skill_archetype: str = 'guidance'
    parent_skill_id: str | None = None
    reason: str = ''
    repair_suggestions: list[RepairSuggestion] = Field(default_factory=list)
    requirement_gaps: list[str] = Field(default_factory=list)
    coverage_gap_types: list[str] = Field(default_factory=list)
    operation_group: str = ''
    operation_name: str = ''
    operation_validation_status: str = ''
    recommended_followup: str = ''
    summary: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.action = _normalize_runtime_action(self.action)
        self.skill_archetype = str(self.skill_archetype or 'guidance').strip().lower() or 'guidance'
        self.parent_skill_id = str(self.parent_skill_id or '').strip() or None
        self.reason = str(self.reason or '').strip()
        self.requirement_gaps = _normalize_string_list(self.requirement_gaps)
        self.coverage_gap_types = _normalize_string_list(self.coverage_gap_types)
        self.operation_group = str(self.operation_group or '').strip()
        self.operation_name = str(self.operation_name or '').strip()
        self.operation_validation_status = str(self.operation_validation_status or '').strip().lower()
        self.recommended_followup = str(self.recommended_followup or '').strip().lower()
        self.summary = str(self.summary or '').strip()
        self.repair_suggestions = [
            suggestion
            if isinstance(suggestion, RepairSuggestion)
            else RepairSuggestion.model_validate(suggestion)
            for suggestion in list(self.repair_suggestions or [])
        ]


class SkillRunAnalysis(BaseModel):
    run_id: str
    task_id: str
    execution_result: str = 'success'
    skills_analyzed: list[dict[str, Any]] = Field(default_factory=list)
    evolution_plans: list[EvolutionPlan] = Field(default_factory=list)
    create_candidates: list[RuntimeCreateCandidate] = Field(default_factory=list)
    summary: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.execution_result = _normalize_execution_result(self.execution_result)
        self.skills_analyzed = [
            _normalize_skill_analysis_entry(item)
            for item in list(self.skills_analyzed or [])
        ]
        self.evolution_plans = [
            plan if isinstance(plan, EvolutionPlan) else EvolutionPlan.model_validate(plan)
            for plan in list(self.evolution_plans or [])
        ]
        self.create_candidates = [
            item if isinstance(item, RuntimeCreateCandidate) else RuntimeCreateCandidate.model_validate(item)
            for item in list(self.create_candidates or [])
        ]
        self.summary = str(self.summary or '').strip()
