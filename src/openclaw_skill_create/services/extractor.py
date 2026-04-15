from __future__ import annotations

from typing import Any, Callable, Optional

from ..models.request import SkillCreateRequestV6
from ..utils.errors import ExtractionError
from .extractor_llm import synthesize_repo_findings_from_signals
from .extractor_rules import (
    enrich_repo_findings_from_context,
    extract_signal_bundle,
    fallback_repo_findings_from_signals,
)


ResponseParser = Callable[[dict[str, Any]], Any]
LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def run_extractor(
    *,
    request: SkillCreateRequestV6,
    repo_context: Any,
    llm_runner: LLMRunner | None = None,
    response_parser: ResponseParser | None = None,
    model: str | None = None,
) -> Any:
    """Run extractor with deterministic-first fallback behavior.

    Flow:
    1. Rules extract a signal bundle from repo context.
    2. If enable_llm_extractor is on, try LLM synthesis.
    3. On any LLM failure, fall back to deterministic findings synthesis.
    """
    try:
        signal_bundle = extract_signal_bundle(
            request=request,
            repo_context=repo_context,
        )
    except Exception as exc:
        raise ExtractionError(f"extract_signal_bundle failed: {exc}") from exc

    use_llm = getattr(request, "enable_llm_extractor", False)
    if not use_llm:
        return enrich_repo_findings_from_context(
            repo_context=repo_context,
            repo_findings=fallback_repo_findings_from_signals(signal_bundle),
        )

    if llm_runner is None:
        return enrich_repo_findings_from_context(
            repo_context=repo_context,
            repo_findings=fallback_repo_findings_from_signals(signal_bundle),
        )

    try:
        return enrich_repo_findings_from_context(
            repo_context=repo_context,
            repo_findings=synthesize_repo_findings_from_signals(
                request=request,
                repo_context=repo_context,
                signal_bundle=signal_bundle,
                llm_runner=llm_runner,
                model=model,
                response_parser=response_parser,
            ),
        )
    except Exception:
        return enrich_repo_findings_from_context(
            repo_context=repo_context,
            repo_findings=fallback_repo_findings_from_signals(signal_bundle),
        )
