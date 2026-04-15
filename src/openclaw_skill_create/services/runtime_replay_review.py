from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..models.runtime_replay import RuntimeReplayGateResult, RuntimeReplayGateScenarioResult
from ..models.runtime_replay_review import RuntimeReplayReviewResult, RuntimeReplayReviewScenario
from .runtime_replay import build_runtime_replay_gate_result


def _scenario_status(result: RuntimeReplayGateScenarioResult) -> str:
    if not result.manifest_passed:
        return 'manifest_failed'
    if not result.baseline_present:
        return 'missing_baseline'
    if not result.baseline_matched:
        return 'drifted'
    return 'passed'


def _scenario_headline(result: RuntimeReplayGateScenarioResult) -> str:
    status = _scenario_status(result)
    if status == 'manifest_failed':
        return 'Manifest expectations no longer match the replayed behavior.'
    if status == 'missing_baseline':
        return 'A baseline snapshot is missing for this replay scenario.'
    if status == 'drifted':
        return 'Current replay behavior drifted from the checked-in baseline.'
    return 'Replay behavior matches both the manifest and the checked-in baseline.'


def render_runtime_replay_review_markdown(review: RuntimeReplayReviewResult) -> str:
    status_text = 'passed' if review.passed else 'failed'
    lines = [
        '# Runtime Replay Review',
        '',
        f'- Status: {status_text}',
        f'- Summary: {review.summary}',
        f'- Fixture root: `{review.fixture_root}`',
        f'- Baseline: `{review.baseline_path}`',
        '',
        '## Scenario Reviews',
    ]

    for scenario in list(review.scenario_reviews):
        lines.append(f'- `{scenario.scenario_id}` [{scenario.status}]: {scenario.headline}')
        for issue in list(scenario.issues):
            lines.append(f'  - {issue}')

    if review.extra_baseline_scenarios:
        lines.extend(
            [
                '',
                '## Extra Baseline Scenarios',
            ]
        )
        for scenario_id in list(review.extra_baseline_scenarios):
            lines.append(f'- `{scenario_id}` exists in the baseline snapshot but not in the current replay run.')

    return '\n'.join(lines).strip()


def build_runtime_replay_review(
    *,
    fixtures_root: Optional[Path] = None,
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> RuntimeReplayReviewResult:
    gate = build_runtime_replay_gate_result(
        fixtures_root=fixtures_root,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
    )
    scenario_reviews = [
        RuntimeReplayReviewScenario(
            scenario_id=result.scenario_id,
            status=_scenario_status(result),
            headline=_scenario_headline(result),
            issues=list(result.current.mismatches) + list(result.drift_messages),
        )
        for result in list(gate.scenario_results)
    ]
    passed_scenarios = sum(1 for item in scenario_reviews if item.status == 'passed')
    failed_scenarios = len(scenario_reviews) - passed_scenarios
    review = RuntimeReplayReviewResult(
        fixture_root=gate.fixture_root,
        baseline_path=gate.baseline_path,
        total_scenarios=len(scenario_reviews),
        passed_scenarios=passed_scenarios,
        failed_scenarios=failed_scenarios,
        extra_baseline_scenarios=list(gate.extra_baseline_scenarios),
        scenario_reviews=scenario_reviews,
        passed=gate.passed,
        summary=(
            f'Runtime replay review complete: scenarios={len(scenario_reviews)} '
            f'passed={passed_scenarios} failed={failed_scenarios} '
            f'extra_baseline={len(gate.extra_baseline_scenarios)}'
        ),
    )
    review.markdown_summary = render_runtime_replay_review_markdown(review)
    return review
