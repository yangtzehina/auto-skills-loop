from __future__ import annotations

import json
from typing import Any

from ..models.request import SkillCreateRequestV6


DEFAULT_EXTRACTOR_SYSTEM_PROMPT = """You are the extractor stage of a repo-aware skill synthesizer.
Your task is to convert repo-grounded signals into structured RepoFindings.

Rules:
- Stay repo-grounded. Do not invent commands, workflows, files, or capabilities.
- Prefer scripts/config/tests/examples/CI over README claims when conflicts exist.
- Extract only what is useful for building a reusable skill.
- Do not produce SkillPlan or artifacts.
- Keep outputs concise, factual, and implementation-oriented.
"""


def _safe_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_extractor_messages(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    signal_bundle: Any,
) -> list[dict[str, Any]]:
    """Build a provider-agnostic message list for extractor LLM calls.

    This stage should summarize repo-grounded signals into RepoFindings only.
    """
    request_payload = request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request)
    repo_payload = repo_context.model_dump(mode="json") if hasattr(repo_context, "model_dump") else str(repo_context)
    signal_payload = signal_bundle.model_dump(mode="json") if hasattr(signal_bundle, "model_dump") else str(signal_bundle)

    user_prompt = f"""
Convert the following repo-grounded material into structured RepoFindings.

[request]
{_safe_dump(request_payload)}

[repo_context]
{_safe_dump(repo_payload)}

[signal_bundle]
{_safe_dump(signal_payload)}

Return JSON only.
Expected shape:
{{
  "repos": [
    {{
      "repo_path": "...",
      "summary": "...",
      "detected_stack": ["..."],
      "entrypoints": [],
      "scripts": [],
      "docs": [],
      "configs": [],
      "workflows": [],
      "triggers": [],
      "candidate_resources": {{
        "references": [],
        "scripts": []
      }},
      "risks": []
    }}
  ],
  "cross_repo_signals": [],
  "overall_recommendation": "..."
}}
""".strip()

    return [
        {"role": "system", "content": DEFAULT_EXTRACTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
