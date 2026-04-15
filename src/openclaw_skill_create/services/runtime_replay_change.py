from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..models.runtime_replay_change import RuntimeReplayChangePack, RuntimeReplayChangeScenario
from ..models.runtime_replay_review import RuntimeReplayReviewResult, RuntimeReplayReviewScenario
from .runtime_replay import DEFAULT_RUNTIME_REPLAY_BASELINE, DEFAULT_RUNTIME_REPLAY_FIXTURES
from .runtime_replay_review import build_runtime_replay_review


def _classify_review_scenario(scenario: RuntimeReplayReviewScenario) -> str:
    if scenario.status in {'manifest_failed', 'missing_baseline'}:
        return 'blocking'
    if scenario.status == 'drifted':
        return 'drifted'
    return 'passed'


def _render_write_baseline_command(
    *,
    fixtures_root: Optional[Path] = None,
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> str:
    parts = ['PYTHONPATH=src', 'python3', 'scripts/run_runtime_replay_gate.py', '--write-baseline']
    if fixtures_root is not None and Path(fixtures_root).expanduser().resolve() != DEFAULT_RUNTIME_REPLAY_FIXTURES.resolve():
        parts.extend(['--fixtures-root', str(Path(fixtures_root).expanduser())])
    if baseline_path is not None and Path(baseline_path).expanduser().resolve() != DEFAULT_RUNTIME_REPLAY_BASELINE.resolve():
        parts.extend(['--baseline', str(Path(baseline_path).expanduser())])
    for scenario_name in list(scenario_names or []):
        parts.extend(['--scenario', scenario_name])
    return ' '.join(parts)


def render_runtime_replay_change_pack_markdown(change_pack: RuntimeReplayChangePack) -> str:
    status_text = 'passed' if change_pack.passed else 'action_required'
    lines = [
        '# Runtime Replay Change Pack',
        '',
        f'- Status: {status_text}',
        f'- Recommended action: `{change_pack.recommended_action}`',
        f'- Should run `--write-baseline`: {"yes" if change_pack.write_baseline_recommended else "no"}',
        f'- Reason: {change_pack.decision_reason}',
        f'- Summary: {change_pack.summary}',
        '',
        '## Scenario Changes',
    ]

    for scenario in list(change_pack.scenario_changes):
        lines.append(f'- `{scenario.scenario_id}` [{scenario.classification}]: {scenario.headline}')
        for issue in list(scenario.issues):
            lines.append(f'  - {issue}')

    if change_pack.blocking_scenarios:
        lines.extend(['', '## Blocking Scenarios'])
        for scenario_id in list(change_pack.blocking_scenarios):
            lines.append(f'- `{scenario_id}`')

    if change_pack.drifted_scenarios:
        lines.extend(['', '## Drifted Scenarios'])
        for scenario_id in list(change_pack.drifted_scenarios):
            lines.append(f'- `{scenario_id}`')

    if change_pack.write_baseline_recommended:
        lines.extend(
            [
                '',
                '## Suggested Command',
                f'`{change_pack.baseline_refresh_command}`',
            ]
        )

    if change_pack.review.extra_baseline_scenarios:
        lines.extend(['', '## Extra Baseline Scenarios'])
        for scenario_id in list(change_pack.review.extra_baseline_scenarios):
            lines.append(f'- `{scenario_id}` exists in the baseline snapshot but not in the current replay selection.')

    return '\n'.join(lines).strip()


def build_runtime_replay_change_pack(
    *,
    fixtures_root: Optional[Path] = None,
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> RuntimeReplayChangePack:
    review = build_runtime_replay_review(
        fixtures_root=fixtures_root,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
    )
    scenario_changes = [
        RuntimeReplayChangeScenario(
            scenario_id=scenario.scenario_id,
            classification=_classify_review_scenario(scenario),
            headline=scenario.headline,
            issues=list(scenario.issues),
        )
        for scenario in list(review.scenario_reviews)
    ]
    drifted_scenarios = [
        scenario.scenario_id
        for scenario in list(scenario_changes)
        if scenario.classification == 'drifted'
    ]
    blocking_scenarios = [
        scenario.scenario_id
        for scenario in list(scenario_changes)
        if scenario.classification == 'blocking'
    ] + list(review.extra_baseline_scenarios)
    affected_scenarios = list(dict.fromkeys(drifted_scenarios + blocking_scenarios))

    if blocking_scenarios:
        recommended_action = 'investigate'
        decision_reason = 'Resolve manifest or baseline coverage issues before refreshing the baseline snapshot.'
        write_baseline_recommended = False
    elif drifted_scenarios:
        recommended_action = 'refresh_baseline'
        decision_reason = 'Only baseline drift remains; refresh the snapshot once the new behavior is confirmed intentional.'
        write_baseline_recommended = True
    else:
        recommended_action = 'keep_baseline'
        decision_reason = 'No behavior drift or blocking replay issue was detected.'
        write_baseline_recommended = False

    baseline_refresh_command = _render_write_baseline_command(
        fixtures_root=fixtures_root,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
    )
    change_pack = RuntimeReplayChangePack(
        fixture_root=review.fixture_root,
        baseline_path=review.baseline_path,
        review=review,
        recommended_action=recommended_action,
        decision_reason=decision_reason,
        write_baseline_recommended=write_baseline_recommended,
        baseline_refresh_command=baseline_refresh_command,
        affected_scenarios=affected_scenarios,
        drifted_scenarios=drifted_scenarios,
        blocking_scenarios=blocking_scenarios,
        scenario_changes=scenario_changes,
        passed=recommended_action == 'keep_baseline',
        summary=(
            f'Runtime replay change pack complete: recommended_action={recommended_action} '
            f'affected={len(affected_scenarios)} drifted={len(drifted_scenarios)} '
            f'blocking={len(blocking_scenarios)} write_baseline={"yes" if write_baseline_recommended else "no"}'
        ),
    )
    change_pack.markdown_summary = render_runtime_replay_change_pack_markdown(change_pack)
    return change_pack
