from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import ValidationError

from ..models.runtime import EvolutionPlan, SkillRunAnalysis
from ..models.runtime_followup import RuntimeFollowupResult
from .runtime_analysis import (
    evolution_plan_to_repair_suggestions,
    evolution_plan_to_skill_create_request,
)


def _load_followup_payload(value: Any) -> tuple[str, SkillRunAnalysis | EvolutionPlan]:
    if isinstance(value, SkillRunAnalysis):
        return 'analysis', value
    if isinstance(value, EvolutionPlan):
        return 'plan', value
    if not isinstance(value, dict):
        raise ValueError('Runtime follow-up input must be a JSON object')

    try:
        return 'analysis', SkillRunAnalysis.model_validate(value)
    except ValidationError:
        pass

    try:
        return 'plan', EvolutionPlan.model_validate(value)
    except ValidationError as exc:
        raise ValueError(f'Input is neither SkillRunAnalysis nor EvolutionPlan: {exc}') from exc


def load_runtime_followup_input(raw: str) -> tuple[str, SkillRunAnalysis | EvolutionPlan]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON input: {exc.msg}') from exc
    return _load_followup_payload(payload)


def select_runtime_followup_plan(
    analysis: SkillRunAnalysis,
    *,
    plan_index: Optional[int] = None,
) -> EvolutionPlan | None:
    plans = list(analysis.evolution_plans or [])
    if not plans:
        return None
    if plan_index is not None:
        if plan_index < 0 or plan_index >= len(plans):
            raise ValueError(f'plan_index out of range: {plan_index}')
        return plans[plan_index]
    for plan in plans:
        if plan.action in {'patch_current', 'derive_child'}:
            return plan
    for plan in plans:
        if plan.action == 'hold':
            return plan
    return plans[0]


def build_runtime_followup_result(
    value: SkillRunAnalysis | EvolutionPlan | dict[str, Any],
    *,
    plan_index: Optional[int] = None,
    task_summary: Optional[str] = None,
    repo_paths: Optional[list[str]] = None,
    skill_name_hint: Optional[str] = None,
) -> RuntimeFollowupResult:
    payload_kind, payload = _load_followup_payload(value)
    selected_plan: EvolutionPlan | None
    if payload_kind == 'analysis':
        selected_plan = select_runtime_followup_plan(payload, plan_index=plan_index)
    else:
        selected_plan = payload

    if selected_plan is None:
        return RuntimeFollowupResult(
            action='no_change',
            selected_plan=None,
            noop=True,
            summary='No runtime evolution plans were available to consume.',
        )

    if selected_plan.action == 'patch_current':
        suggestions = evolution_plan_to_repair_suggestions(selected_plan)
        return RuntimeFollowupResult(
            action='patch_current',
            selected_plan=selected_plan,
            repair_suggestions=suggestions,
            summary=f'Produced {len(suggestions)} repair suggestion(s) from runtime follow-up.',
        )

    if selected_plan.action == 'derive_child':
        request = evolution_plan_to_skill_create_request(
            selected_plan,
            task_summary=task_summary,
            repo_paths=repo_paths,
            skill_name_hint=skill_name_hint,
        )
        return RuntimeFollowupResult(
            action='derive_child',
            selected_plan=selected_plan,
            skill_create_request=request,
            summary='Produced a SkillCreateRequestV6 from the runtime evolution plan.',
        )

    if selected_plan.action == 'hold':
        return RuntimeFollowupResult(
            action='hold',
            selected_plan=selected_plan,
            noop=True,
            summary=selected_plan.summary or selected_plan.reason or 'Runtime follow-up is on hold pending contract or safety alignment.',
        )

    return RuntimeFollowupResult(
        action='no_change',
        selected_plan=selected_plan,
        noop=True,
        summary=selected_plan.summary or selected_plan.reason or 'No runtime follow-up is required.',
    )
