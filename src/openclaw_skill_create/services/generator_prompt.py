from __future__ import annotations

import json
from typing import Any

from ..models.request import SkillCreateRequestV6


DEFAULT_SKILL_MD_SYSTEM_PROMPT = """You generate only the SKILL.md artifact for a repo-aware skill synthesizer.

Rules:
- Follow the SkillPlan strictly. Do not expand scope.
- Output Markdown body content only; the caller controls artifact wrapping.
- Frontmatter must contain only: name, description.
- Keep SKILL.md concise and route detailed material into references/*.
- Do not invent commands, tools, workflows, or capabilities not grounded in findings/plan.
- Do not generate README-style repository documentation.
"""


def _safe_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_skill_md_messages(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    repo_findings: Any,
    skill_plan: Any,
) -> list[dict[str, Any]]:
    request_payload = request.model_dump(mode='json') if hasattr(request, 'model_dump') else str(request)
    repo_payload = repo_context.model_dump(mode='json') if hasattr(repo_context, 'model_dump') else str(repo_context)
    findings_payload = repo_findings.model_dump(mode='json') if hasattr(repo_findings, 'model_dump') else str(repo_findings)
    plan_payload = skill_plan.model_dump(mode='json') if hasattr(skill_plan, 'model_dump') else str(skill_plan)

    user_prompt = f"""
Generate the full SKILL.md markdown for this skill.

[request]
{_safe_dump(request_payload)}

[repo_context]
{_safe_dump(repo_payload)}

[repo_findings]
{_safe_dump(findings_payload)}

[skill_plan]
{_safe_dump(plan_payload)}

Requirements:
1. Include YAML frontmatter with only name and description.
2. Explain when to use the skill.
3. Give only top-level workflow guidance.
4. Reference references/* and scripts/* when they exist in the plan.
5. Keep it concise and skill-oriented.

Return markdown only.
""".strip()

    return [
        {"role": "system", "content": DEFAULT_SKILL_MD_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
