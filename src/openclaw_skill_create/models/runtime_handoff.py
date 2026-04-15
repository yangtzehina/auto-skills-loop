from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from .runtime import RuntimeSemanticSummary, RuntimeSessionEvidence, SkillRunRecord


def _normalize_string_list(values: Any) -> list[str]:
    result: list[str] = []
    for value in list(values or []):
        text = str(value or '').strip()
        if text:
            result.append(text)
    return result


def _normalize_runtime_options(payload: Any) -> dict[str, Any]:
    item = dict(payload or {})
    return {
        'baseline_path': str(item.get('baseline_path') or '').strip(),
        'scenario_names': _normalize_string_list(item.get('scenario_names')),
        'enable_llm_judge': bool(item.get('enable_llm_judge', False)),
        'judge_model': str(item.get('judge_model') or '').strip(),
    }


def _normalize_handoff_skill_usage(value: Any, *, execution_result: str) -> dict[str, Any]:
    item = dict(value or {})
    steps_triggered = _normalize_string_list(item.get('steps_triggered'))
    selected = item.get('selected')
    applied = item.get('applied')
    return {
        'skill_id': str(item.get('skill_id') or '').strip(),
        'skill_name': str(item.get('skill_name') or '').strip(),
        'skill_path': str(item.get('skill_path') or '').strip(),
        'selected': True if selected is None else bool(selected),
        'applied': (
            bool(steps_triggered) or execution_result in {'success', 'partial'}
            if applied is None
            else bool(applied)
        ),
        'steps_triggered': steps_triggered,
        'notes': str(item.get('notes') or '').strip(),
    }


def _normalize_handoff_turn_trace(value: Any) -> dict[str, Any]:
    item = dict(value or {})
    return {
        'skill_id': str(item.get('skill_id') or '').strip(),
        'skill_name': str(item.get('skill_name') or '').strip(),
        'step': str(item.get('step') or '').strip(),
        'phase': str(item.get('phase') or '').strip(),
        'tool': str(item.get('tool') or '').strip(),
        'status': str(item.get('status') or 'unknown').strip().lower() or 'unknown',
        'notes': str(item.get('notes') or '').strip(),
    }


class RuntimeHandoffOptions(BaseModel):
    baseline_path: str = ''
    scenario_names: list[str] = Field(default_factory=list)
    enable_llm_judge: bool = False
    judge_model: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.baseline_path = str(self.baseline_path or '').strip()
        self.scenario_names = _normalize_string_list(self.scenario_names)
        self.judge_model = str(self.judge_model or '').strip()


class RuntimeHandoffEnvelope(BaseModel):
    run_id: str = ''
    task_id: str
    task_summary: str = ''
    skills_used: list[dict[str, Any]] = Field(default_factory=list)
    execution_result: str = 'success'
    failure_points: list[str] = Field(default_factory=list)
    user_corrections: list[str] = Field(default_factory=list)
    output_summary: str = ''
    repo_paths: list[str] = Field(default_factory=list)
    turn_trace: list[dict[str, Any]] = Field(default_factory=list)
    completed_at: str = ''
    runtime_options: RuntimeHandoffOptions = Field(default_factory=RuntimeHandoffOptions)

    def model_post_init(self, __context: Any) -> None:
        task_id = str(self.task_id or '').strip()
        self.task_id = task_id
        self.task_summary = str(self.task_summary or '').strip() or task_id
        self.execution_result = str(self.execution_result or 'success').strip().lower() or 'success'
        self.failure_points = _normalize_string_list(self.failure_points)
        self.user_corrections = _normalize_string_list(self.user_corrections)
        self.output_summary = str(self.output_summary or '').strip()
        self.repo_paths = _normalize_string_list(self.repo_paths)
        self.turn_trace = [_normalize_handoff_turn_trace(item) for item in list(self.turn_trace or [])]
        self.completed_at = str(self.completed_at or '').strip()
        if not self.run_id:
            base = re.sub(r'[^a-zA-Z0-9._-]+', '-', task_id or 'runtime-handoff').strip('-')
            self.run_id = f'hand-off-{base or "runtime"}'
        else:
            self.run_id = str(self.run_id).strip()
        self.skills_used = [
            _normalize_handoff_skill_usage(item, execution_result=self.execution_result)
            for item in list(self.skills_used or [])
        ]
        if not isinstance(self.runtime_options, RuntimeHandoffOptions):
            self.runtime_options = RuntimeHandoffOptions.model_validate(self.runtime_options)


class RuntimeHandoffNormalized(BaseModel):
    skill_run_record: SkillRunRecord
    runtime_session_evidence: RuntimeSessionEvidence | None = None
    runtime_semantic_summary: RuntimeSemanticSummary | None = None
    runtime_options: RuntimeHandoffOptions
    summary: str = ''
