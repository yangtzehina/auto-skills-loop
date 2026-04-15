from __future__ import annotations

import json
from typing import Any

from ..models.request import SkillCreateRequestV6


DEFAULT_PLANNER_SYSTEM_PROMPT = """You are the planner stage of a repo-aware skill synthesizer.
Convert repo findings and a planning seed into a compact SkillPlan.

Rules:
- Stay within the planning boundary. Do not generate file content.
- Prefer fewer, stronger files over bloated file sets.
- Keep SKILL.md concise and push detail into references/* when needed.
- Use skill_archetype="methodology_guidance" for framework, decision-loop, game-design, simulation, or output-template skills that need a real workflow body.
- Only plan files that are grounded in repo findings or existing skill structure.
- Preserve merge safety for rewrite/update scenarios.
"""


def _safe_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_planner_messages(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    repo_findings: Any,
    planning_seed: Any,
) -> list[dict[str, Any]]:
    request_payload = request.model_dump(mode='json') if hasattr(request, 'model_dump') else str(request)
    repo_payload = repo_context.model_dump(mode='json') if hasattr(repo_context, 'model_dump') else str(repo_context)
    findings_payload = repo_findings.model_dump(mode='json') if hasattr(repo_findings, 'model_dump') else str(repo_findings)
    seed_payload = planning_seed.model_dump(mode='json') if hasattr(planning_seed, 'model_dump') else str(planning_seed)

    user_prompt = f"""
Produce a structured SkillPlan from the following grounded inputs.

[request]
{_safe_dump(request_payload)}

[repo_context]
{_safe_dump(repo_payload)}

[repo_findings]
{_safe_dump(findings_payload)}

[planning_seed]
{_safe_dump(seed_payload)}

Return JSON only.
Expected shape:
{{
  "skill_name": "...",
  "skill_type": "mixed",
  "skill_archetype": "guidance|operation_backed|methodology_guidance",
  "objective": "...",
  "why_this_shape": "...",
  "files_to_create": [{{"path": "...", "purpose": "...", "source_basis": ["..."]}}],
  "files_to_update": [],
  "files_to_keep": [],
  "merge_strategy": {{
    "mode": "preserve-and-merge",
    "preserve_existing_files": true,
    "replace_conflicting_sections": true
  }},
  "content_budget": {{
    "skill_md_max_lines": 300,
    "reference_file_targets": {{}},
    "prefer_script_over_inline_code": true
  }},
  "generation_order": ["SKILL.md"]
}}
""".strip()

    return [
        {"role": "system", "content": DEFAULT_PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
