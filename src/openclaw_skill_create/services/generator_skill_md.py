from __future__ import annotations

from typing import Any, Callable, Optional

from ..models.artifacts import ArtifactFile
from ..models.request import SkillCreateRequestV6
from ..utils.errors import SkillCreateError
from .generator_fallback import (
    fallback_generate_operation_skill_md_artifact,
    fallback_generate_skill_md_artifact,
)
from .generator_prompt import build_skill_md_messages
from .skill_description import build_trigger_aware_skill_description


class GenerationError(SkillCreateError):
    pass


LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def collect_reference_paths(skill_plan: Any) -> list[str]:
    files = getattr(skill_plan, 'files_to_create', []) or []
    return [f.path for f in files if getattr(f, 'path', '').startswith('references/')]


def collect_script_paths(skill_plan: Any) -> list[str]:
    files = getattr(skill_plan, 'files_to_create', []) or []
    return [f.path for f in files if getattr(f, 'path', '').startswith('scripts/')]


def generate_skill_md_artifact(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    repo_findings: Any,
    skill_plan: Any,
    llm_runner: LLMRunner | None = None,
    model: str | None = None,
) -> ArtifactFile:
    skill_name = getattr(skill_plan, 'skill_name', 'generated-skill')
    skill_archetype = str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower()
    contract = getattr(skill_plan, 'operation_contract', None)
    description = build_trigger_aware_skill_description(
        skill_name=skill_name,
        task=getattr(request, 'task', '') or '',
    )
    references = collect_reference_paths(skill_plan)
    scripts = collect_script_paths(skill_plan)

    if skill_archetype == 'operation_backed' and contract is not None:
        return fallback_generate_operation_skill_md_artifact(
            skill_name=skill_name,
            description=description,
            contract=contract,
            references=references,
            scripts=scripts,
        )

    use_llm = getattr(request, 'enable_llm_skill_md', False)
    if not use_llm or llm_runner is None:
        return fallback_generate_skill_md_artifact(
            skill_name=skill_name,
            description=description,
            references=references,
            scripts=scripts,
        )

    messages = build_skill_md_messages(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        skill_plan=skill_plan,
    )

    try:
        content = llm_runner(messages, model)
    except Exception:
        return fallback_generate_skill_md_artifact(
            skill_name=skill_name,
            description=description,
            references=references,
            scripts=scripts,
        )

    if not isinstance(content, str) or not content.strip():
        raise GenerationError('generator_skill_md returned empty content')

    return ArtifactFile(
        path='SKILL.md',
        content=content.strip() + '\n',
        content_type='text/markdown',
        generated_from=['skill_plan', 'repo_findings', 'llm'],
        status='new',
    )
