from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
DEFAULT_CREATE_SEED_SOURCE = ROOT / 'tests' / 'fixtures' / 'runtime_create_queue' / 'no_skill_cluster' / 'manifest.json'
DEFAULT_PRIOR_SOURCE = ROOT / 'tests' / 'fixtures' / 'simulation' / 'prior_gate' / 'allowlisted_family_only' / 'input' / 'spec.json'
DEFAULT_ROUND_REPORT = ROOT / 'tests' / 'fixtures' / 'public_source_curation' / 'latest_round_report.json'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.online import SkillSourceCandidate
from openclaw_skill_create.models.runtime_governance import RuntimePriorPilotReport, RuntimePriorRolloutReport
from openclaw_skill_create.services.ops_approval import DEFAULT_APPROVAL_MANIFEST, load_ops_approval_state
from openclaw_skill_create.services.public_source_curation import load_public_source_curation_round_report
from openclaw_skill_create.services.runtime_governance import (
    build_runtime_create_seed_proposal_pack,
    build_runtime_ops_decision_pack,
    build_runtime_prior_gate_report,
    build_runtime_prior_pilot_report,
    build_runtime_prior_rollout_report,
)
from openclaw_skill_create.services.verify import build_verify_report, render_verify_report_markdown


def _usage() -> str:
    return (
        'Usage: python scripts/run_verify_report.py '
        '--mode <quick|full> [--format json|markdown] [--include-live-curation] [--approval-manifest PATH]'
    )


def _load_json_object(path: Path) -> dict[str, object]:
    target = path.expanduser().resolve()
    if not target.exists() or not target.is_file():
        raise ValueError(f'Not a file: {target}')
    try:
        payload = json.loads(target.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON input: {exc.msg}') from exc
    if not isinstance(payload, dict):
        raise ValueError(f'JSON input must be an object: {target}')
    return payload


def _load_prior_pilot_report(path: Path) -> RuntimePriorPilotReport:
    payload = _load_json_object(path)
    if 'profiles' in payload:
        return RuntimePriorPilotReport.model_validate(payload)
    if 'families' in payload:
        rollout_report = RuntimePriorRolloutReport.model_validate(payload)
        return build_runtime_prior_pilot_report(
            rollout_report=rollout_report,
            runtime_effectiveness_min_runs=5,
        )
    catalog = [
        SkillSourceCandidate.model_validate(item)
        for item in list(payload.get('catalog') or [])
    ]
    runtime_effectiveness_min_runs = int(payload.get('runtime_effectiveness_min_runs', 5) or 5)
    gate_report = build_runtime_prior_gate_report(
        catalog=catalog,
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        task_samples=list(payload.get('task_samples') or []),
        runtime_effectiveness_min_runs=runtime_effectiveness_min_runs,
        runtime_effectiveness_allowed_families=list(payload.get('runtime_effectiveness_allowed_families') or []) or None,
    )
    rollout_report = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        rollout_min_runs=int(payload.get('rollout_min_runs', runtime_effectiveness_min_runs) or runtime_effectiveness_min_runs),
    )
    return build_runtime_prior_pilot_report(
        rollout_report=rollout_report,
        runtime_effectiveness_min_runs=runtime_effectiveness_min_runs,
    )


def _parse_args(argv: list[str]) -> tuple[str, str, bool, Path]:
    mode = ''
    output_format = 'json'
    include_live_curation = False
    approval_manifest = DEFAULT_APPROVAL_MANIFEST
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--mode':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--mode requires a value')
            mode = argv[idx]
        elif arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg == '--include-live-curation':
            include_live_curation = True
        elif arg == '--approval-manifest':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--approval-manifest requires a value')
            approval_manifest = Path(argv[idx]).expanduser()
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    if mode not in {'quick', 'full'}:
        raise ValueError(f'Unsupported mode: {mode or "<missing>"}')
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return mode, output_format, include_live_curation, approval_manifest


def main(argv: list[str]) -> int:
    try:
        mode, output_format, include_live_curation, approval_manifest_path = _parse_args(argv)
        approval_state = load_ops_approval_state(approval_manifest_path)
        verify_report = build_verify_report(
            mode=mode,
            include_live_curation=include_live_curation,
        )
        create_seed_pack = build_runtime_create_seed_proposal_pack(
            source_path=DEFAULT_CREATE_SEED_SOURCE,
            policy=OpenSpaceObservationPolicy(enabled=False),
        )
        prior_pilot_report = _load_prior_pilot_report(DEFAULT_PRIOR_SOURCE)
        round_report = load_public_source_curation_round_report(DEFAULT_ROUND_REPORT)
        decision_pack = build_runtime_ops_decision_pack(
            create_seed_pack=create_seed_pack,
            prior_pilot_report=prior_pilot_report,
            source_curation_round=round_report,
            verify_report=verify_report,
            approval_state=approval_state,
        )
        verify_report = verify_report.model_copy(
            update={
                'decision_statuses': {
                    'pending': list(decision_pack.decisions_pending or []),
                    'approved_not_applied': list(decision_pack.approved_not_applied or []),
                    'applied': list(decision_pack.applied or []),
                },
                'decision_status_summary': {
                    'pending': len(list(decision_pack.decisions_pending or [])),
                    'approved_not_applied': len(list(decision_pack.approved_not_applied or [])),
                    'applied': len(list(decision_pack.applied or [])),
                },
            }
        )
        verify_report.markdown_summary = render_verify_report_markdown(verify_report)
    except (ValueError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    if output_format == 'markdown':
        print(verify_report.markdown_summary)
    else:
        print(json.dumps(verify_report.model_dump(mode='json'), indent=2, ensure_ascii=False))
    if verify_report.overall_status == 'fail':
        return 1
    if verify_report.overall_status == 'warn':
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
