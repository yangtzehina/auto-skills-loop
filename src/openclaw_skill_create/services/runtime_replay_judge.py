from __future__ import annotations

import json
from typing import Any, Callable, Optional

from ..models.runtime_replay_change import RuntimeReplayChangePack
from ..models.runtime_replay_judge import RuntimeReplayJudgePack, RuntimeReplayJudgeScenario


LLMRunner = Callable[[list[dict[str, Any]], Optional[str]], str]


def _extract_json_payload(raw: str) -> dict[str, Any]:
    text = str(raw or '').strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError('runtime replay judge payload must be a JSON object')
    return payload


def build_runtime_replay_judge_pack(
    change_pack: RuntimeReplayChangePack,
    *,
    enabled: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
) -> RuntimeReplayJudgePack:
    if not enabled:
        return RuntimeReplayJudgePack(enabled=False, applied=False, reason='Runtime replay judge disabled', summary='Runtime replay judge disabled.')

    candidate_scenarios = [
        scenario
        for scenario in list(change_pack.scenario_changes)
        if scenario.classification in {'drifted', 'blocking'}
    ]
    if not candidate_scenarios:
        return RuntimeReplayJudgePack(
            enabled=True,
            applied=False,
            model=str(model or ''),
            reason='No drifted or blocking scenarios required judge review',
            summary='Runtime replay judge skipped: no drifted or blocking scenarios.',
        )
    if llm_runner is None:
        return RuntimeReplayJudgePack(
            enabled=True,
            applied=False,
            model=str(model or ''),
            reason='No llm_runner was provided for the guarded runtime judge',
            summary='Runtime replay judge skipped: no llm_runner was provided.',
        )

    try:
        judgments: list[RuntimeReplayJudgeScenario] = []
        for scenario in candidate_scenarios:
            messages = [
                {
                    'role': 'system',
                    'content': (
                        'Return compact JSON with keys narrative_explanation, '
                        'confidence_adjustment, and review_hints.'
                    ),
                },
                {
                    'role': 'user',
                    'content': json.dumps(
                        {
                            'scenario_id': scenario.scenario_id,
                            'classification': scenario.classification,
                            'headline': scenario.headline,
                            'issues': list(scenario.issues),
                            'recommended_action': change_pack.recommended_action,
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
            raw = llm_runner(messages, model)
            payload = _extract_json_payload(raw)
            judgments.append(
                RuntimeReplayJudgeScenario(
                    scenario_id=scenario.scenario_id,
                    narrative_explanation=str(payload.get('narrative_explanation') or '').strip(),
                    confidence_adjustment=float(payload.get('confidence_adjustment', 0.0) or 0.0),
                    review_hints=[str(item).strip() for item in list(payload.get('review_hints') or []) if str(item).strip()],
                )
            )
        return RuntimeReplayJudgePack(
            enabled=True,
            applied=True,
            model=str(model or ''),
            reason='Runtime replay judge applied supplemental explanations to candidate scenarios.',
            scenario_judgments=judgments,
            summary=f'Runtime replay judge complete: scenarios={len(judgments)}',
        )
    except Exception as exc:  # pragma: no cover - defensive guardrail
        return RuntimeReplayJudgePack(
            enabled=True,
            applied=False,
            model=str(model or ''),
            reason=f'Runtime replay judge failed: {exc}',
            summary='Runtime replay judge fell back to deterministic-only output.',
        )
