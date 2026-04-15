from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..models.runtime_replay_approval import (
    RuntimeReplayApprovalPack,
    RuntimeReplayApprovalScenario,
)
from .runtime_replay_change import build_runtime_replay_change_pack


def render_runtime_replay_approval_markdown(approval: RuntimeReplayApprovalPack) -> str:
    status_text = 'passed' if approval.passed else 'action_required'
    lines = [
        '# Runtime Replay Approval Pack',
        '',
        f'- Status: {status_text}',
        f'- Current recommended action: `{approval.current_recommended_action}`',
        f'- Approval decision: `{approval.approval_decision}`',
        f'- Allow baseline refresh: {"yes" if approval.allow_baseline_refresh else "no"}',
        f'- Pending approval summary: {approval.pending_approval_summary}',
        f'- Summary: {approval.summary}',
        '',
        '## Approval Review',
    ]
    for scenario in list(approval.scenario_approvals):
        lines.append(f'- `{scenario.scenario_id}` [{scenario.approval_state}]: {scenario.headline}')
        for issue in list(scenario.issues):
            lines.append(f'  - {issue}')
    if approval.suggested_command:
        lines.extend(['', '## Suggested Command', f'`{approval.suggested_command}`'])
    return '\n'.join(lines).strip()


def build_runtime_replay_approval_pack(
    *,
    fixtures_root: Optional[Path] = None,
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> RuntimeReplayApprovalPack:
    change_pack = build_runtime_replay_change_pack(
        fixtures_root=fixtures_root,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
    )
    scenario_approvals = [
        RuntimeReplayApprovalScenario(
            scenario_id=scenario.scenario_id,
            approval_state=(
                'investigate_first'
                if scenario.classification == 'blocking'
                else 'pending_refresh'
                if scenario.classification == 'drifted'
                else 'unchanged'
            ),
            headline=scenario.headline,
            issues=list(scenario.issues),
        )
        for scenario in list(change_pack.scenario_changes)
    ]

    if change_pack.recommended_action == 'investigate':
        approval_decision = 'investigate_first'
        allow_baseline_refresh = False
        suggested_command = 'PYTHONPATH=src python3 scripts/run_runtime_replay_review.py --format markdown'
        pending_approval_summary = 'Baseline refresh is blocked until manifest or baseline coverage issues are resolved.'
        passed = False
    elif change_pack.recommended_action == 'refresh_baseline':
        approval_decision = 'approve_refresh'
        allow_baseline_refresh = True
        suggested_command = change_pack.baseline_refresh_command
        pending_approval_summary = 'Only baseline drift remains. Refresh the snapshot after confirming the new behavior is intentional.'
        passed = True
    else:
        approval_decision = 'reject_refresh'
        allow_baseline_refresh = False
        suggested_command = ''
        pending_approval_summary = 'No baseline refresh is needed because the current replay behavior already matches the approved snapshot.'
        passed = True

    approval = RuntimeReplayApprovalPack(
        fixture_root=change_pack.fixture_root,
        baseline_path=change_pack.baseline_path,
        change_pack=change_pack,
        current_recommended_action=change_pack.recommended_action,
        approval_decision=approval_decision,
        allow_baseline_refresh=allow_baseline_refresh,
        suggested_command=suggested_command,
        pending_approval_summary=pending_approval_summary,
        affected_scenarios=list(change_pack.affected_scenarios),
        drifted_scenarios=list(change_pack.drifted_scenarios),
        blocking_scenarios=list(change_pack.blocking_scenarios),
        scenario_approvals=scenario_approvals,
        passed=passed,
        summary=(
            f'Runtime replay approval pack complete: approval_decision={approval_decision} '
            f'allow_refresh={"yes" if allow_baseline_refresh else "no"} '
            f'affected={len(change_pack.affected_scenarios)}'
        ),
    )
    approval.markdown_summary = render_runtime_replay_approval_markdown(approval)
    return approval
