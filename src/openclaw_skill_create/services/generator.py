from __future__ import annotations

from typing import Any, Callable, Optional

from ..models.artifacts import Artifacts
from ..models.request import SkillCreateRequestV6
from .evaluation_scaffold import generate_eval_artifacts
from .generator_resources import (
    generate_metadata_artifacts,
    generate_reference_artifacts,
    generate_script_artifacts,
)
from .generator_skill_md import generate_skill_md_artifact


LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def run_generator(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    repo_findings: Any,
    skill_plan: Any,
    reuse_decision: Any = None,
    llm_runner: LLMRunner | None = None,
    model: str | None = None,
) -> Artifacts:
    skill_md = generate_skill_md_artifact(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        skill_plan=skill_plan,
        llm_runner=llm_runner,
        model=model,
    )
    files = [skill_md]
    files.extend(generate_reference_artifacts(repo_context=repo_context, skill_plan=skill_plan))
    files.extend(generate_script_artifacts(repo_context=repo_context, skill_plan=skill_plan))
    files.extend(generate_metadata_artifacts(request=request, skill_plan=skill_plan))
    files.extend(generate_eval_artifacts(request=request, skill_plan=skill_plan, reuse_decision=reuse_decision))
    return Artifacts(files=files)
