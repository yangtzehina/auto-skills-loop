from __future__ import annotations

import json
from typing import Any, Callable, Optional

from ..models.plan import SkillPlan
from ..models.request import SkillCreateRequestV6
from ..utils.errors import SkillCreateError
from .planner_prompt import build_planner_messages


class PlanningError(SkillCreateError):
    pass


LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def parse_skill_plan_payload(payload: str) -> dict[str, Any]:
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PlanningError(f"planner_llm returned invalid JSON: {exc}") from exc


def parse_skill_plan_model(data: dict[str, Any]) -> SkillPlan:
    try:
        return SkillPlan.model_validate(data)
    except Exception as exc:
        raise PlanningError(f"planner_llm payload does not match SkillPlan: {exc}") from exc


def synthesize_skill_plan(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    repo_findings: Any,
    planning_seed: Any,
    llm_runner: LLMRunner,
    model: str | None = None,
    response_parser: Callable[[dict[str, Any]], Any] | None = None,
) -> Any:
    if llm_runner is None:
        raise PlanningError("planner_llm requires llm_runner")

    messages = build_planner_messages(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        planning_seed=planning_seed,
    )

    try:
        raw = llm_runner(messages, model)
    except Exception as exc:
        raise PlanningError(f"planner_llm call failed: {exc}") from exc

    parsed = parse_skill_plan_payload(raw)

    if response_parser is not None:
        try:
            return response_parser(parsed)
        except Exception as exc:
            raise PlanningError(f"planner_llm response parsing failed: {exc}") from exc

    return parse_skill_plan_model(parsed)
