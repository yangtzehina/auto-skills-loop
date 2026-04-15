from __future__ import annotations

import json
from typing import Any, Callable, Optional

from ..models.findings import RepoFindings
from ..models.request import SkillCreateRequestV6
from ..utils.errors import ExtractionError
from .extractor_prompt import build_extractor_messages


LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def parse_repo_findings_payload(payload: str) -> dict[str, Any]:
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"extractor_llm returned invalid JSON: {exc}") from exc


def parse_repo_findings_model(data: dict[str, Any]) -> RepoFindings:
    try:
        return RepoFindings.model_validate(data)
    except Exception as exc:
        raise ExtractionError(f"extractor_llm payload does not match RepoFindings: {exc}") from exc


def synthesize_repo_findings_from_signals(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    signal_bundle: Any,
    llm_runner: LLMRunner,
    model: str | None = None,
    response_parser: Callable[[dict[str, Any]], Any] | None = None,
) -> Any:
    """Run the extractor LLM stage.

    The function is intentionally provider-agnostic:
    - llm_runner handles the model call
    - response_parser optionally upgrades the parsed dict into RepoFindings
    """
    if llm_runner is None:
        raise ExtractionError("extractor_llm requires llm_runner")

    messages = build_extractor_messages(
        request=request,
        repo_context=repo_context,
        signal_bundle=signal_bundle,
    )

    try:
        raw = llm_runner(messages, model)
    except Exception as exc:  # pragma: no cover - wrapper path
        raise ExtractionError(f"extractor_llm call failed: {exc}") from exc

    parsed = parse_repo_findings_payload(raw)

    if response_parser is not None:
        try:
            return response_parser(parsed)
        except Exception as exc:  # pragma: no cover - parser integration path
            raise ExtractionError(f"extractor_llm response parsing failed: {exc}") from exc

    return parse_repo_findings_model(parsed)
