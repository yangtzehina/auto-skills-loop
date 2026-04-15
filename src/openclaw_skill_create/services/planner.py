from __future__ import annotations

from typing import Any, Callable, Optional

from ..models.request import SkillCreateRequestV6
from .planner_llm import synthesize_skill_plan
from .planner_rules import build_planning_seed, fallback_skill_plan_from_seed


ResponseParser = Callable[[dict[str, Any]], Any]
LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def run_planner(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    repo_findings: Any,
    extracted_patterns: Any = None,
    online_skill_blueprints: Any = None,
    reuse_decision: Any = None,
    llm_runner: LLMRunner | None = None,
    response_parser: ResponseParser | None = None,
    model: str | None = None,
) -> Any:
    planning_seed = build_planning_seed(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        extracted_patterns=extracted_patterns,
        online_skill_blueprints=online_skill_blueprints,
        reuse_decision=reuse_decision,
    )

    use_llm = getattr(request, 'enable_llm_planner', False)
    if not use_llm:
        return fallback_skill_plan_from_seed(planning_seed)

    if llm_runner is None:
        return fallback_skill_plan_from_seed(planning_seed)

    try:
        return synthesize_skill_plan(
            request=request,
            repo_context=repo_context,
            repo_findings=repo_findings,
            planning_seed=planning_seed,
            llm_runner=llm_runner,
            model=model,
            response_parser=response_parser,
        )
    except Exception:
        return fallback_skill_plan_from_seed(planning_seed)
