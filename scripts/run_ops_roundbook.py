from __future__ import annotations

import json
import sys
from pathlib import Path

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
from openclaw_skill_create.services.public_source_curation import (
    build_public_source_promotion_pack,
    load_public_source_curation_round_report,
)
from openclaw_skill_create.services.runtime_governance import (
    build_runtime_create_seed_proposal_pack,
    build_runtime_ops_decision_pack,
    build_runtime_prior_gate_report,
    build_runtime_prior_pilot_exercise_report,
    build_runtime_prior_pilot_report,
    build_runtime_prior_rollout_report,
)
from openclaw_skill_create.services.verify import build_ops_roundbook_report, build_verify_report


def _truncate_text(value: str, *, limit: int = 4000) -> str:
    text = str(value or '')
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n...[truncated {len(text) - limit} chars]"


def _compact_verify_report_payload(payload: dict[str, object]) -> dict[str, object]:
    compact = dict(payload)
    commands = []
    for item in list(compact.get('commands') or []):
        if not isinstance(item, dict):
            commands.append(item)
            continue
        command = dict(item)
        command['stdout'] = _truncate_text(str(command.get('stdout') or ''))
        command['stderr'] = _truncate_text(str(command.get('stderr') or ''))
        commands.append(command)
    compact['commands'] = commands
    compact['skill_create_comparison_report'] = None
    compact['summary'] = _truncate_text(str(compact.get('summary') or ''), limit=2000)
    compact['markdown_summary'] = _truncate_text(str(compact.get('markdown_summary') or ''), limit=4000)
    return compact


def _compact_roundbook_payload(report) -> dict[str, object]:
    payload = report.model_dump(mode='json')
    verify_report = payload.get('verify_report')
    if isinstance(verify_report, dict):
        payload['verify_report'] = _compact_verify_report_payload(verify_report)
    payload['summary'] = _truncate_text(str(payload.get('summary') or ''), limit=2000)
    payload['markdown_summary'] = _truncate_text(str(payload.get('markdown_summary') or ''), limit=4000)
    return payload


def _usage() -> str:
    return (
        'Usage: python scripts/run_ops_roundbook.py '
        '--mode <quick|full> [--format json|markdown] [--include-live-curation] '
        '[--round-report PATH] [--approval-manifest PATH]'
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


def _parse_args(argv: list[str]) -> tuple[str, str, bool, Path, Path]:
    mode = ''
    output_format = 'json'
    include_live_curation = False
    round_report = DEFAULT_ROUND_REPORT
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
        elif arg == '--round-report':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--round-report requires a value')
            round_report = Path(argv[idx]).expanduser()
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
    return mode, output_format, include_live_curation, round_report, approval_manifest


def _run_roundbook_stage(stage: str, builder):
    try:
        return builder()
    except Exception as exc:  # pragma: no cover - exercised via CLI path
        raise RuntimeError(f'roundbook_stage={stage} {type(exc).__name__}: {exc}') from exc


def _build_cli_roundbook_report(
    *,
    mode: str,
    include_live_curation: bool,
    round_report_path: Path,
    approval_manifest_path: Path,
):
    approval_state = _run_roundbook_stage(
        'load_approval_state',
        lambda: load_ops_approval_state(approval_manifest_path),
    )
    verify_report = _run_roundbook_stage(
        'build_verify_report',
        lambda: build_verify_report(mode=mode, include_live_curation=include_live_curation),
    )
    create_seed_pack = _run_roundbook_stage(
        'build_create_seed_pack',
        lambda: build_runtime_create_seed_proposal_pack(
            source_path=DEFAULT_CREATE_SEED_SOURCE,
            policy=OpenSpaceObservationPolicy(enabled=False),
        ),
    )
    prior_pilot_report = _run_roundbook_stage(
        'load_prior_pilot_report',
        lambda: _load_prior_pilot_report(DEFAULT_PRIOR_SOURCE),
    )
    prior_pilot_exercise = _run_roundbook_stage(
        'build_prior_pilot_exercise',
        lambda: build_runtime_prior_pilot_exercise_report(
            pilot_report=prior_pilot_report,
            family='hf-trainer',
            approval_state=approval_state,
        ),
    )
    round_report = _run_roundbook_stage(
        'load_source_round_report',
        lambda: load_public_source_curation_round_report(round_report_path),
    )
    source_promotion_pack = _run_roundbook_stage(
        'build_source_promotion_pack',
        lambda: build_public_source_promotion_pack(
            round_report=round_report,
            repo_full_name='alirezarezvani/claude-skills',
            approval_state=approval_state,
        ),
    )
    decision_pack = _run_roundbook_stage(
        'build_runtime_ops_decision_pack',
        lambda: build_runtime_ops_decision_pack(
            create_seed_pack=create_seed_pack,
            prior_pilot_report=prior_pilot_report,
            source_curation_round=round_report,
            verify_report=verify_report,
            approval_state=approval_state,
        ),
    )
    return _run_roundbook_stage(
        'build_ops_roundbook_report',
        lambda: build_ops_roundbook_report(
            verify_report=verify_report,
            runtime_ops_decision_pack=decision_pack,
            prior_pilot_exercise=prior_pilot_exercise,
            source_promotion_pack=source_promotion_pack,
            create_seed_pack=create_seed_pack,
            prior_pilot_report=prior_pilot_report,
            source_curation_round=round_report,
        ),
    )


def main(argv: list[str]) -> int:
    try:
        mode, output_format, include_live_curation, round_report_path, approval_manifest_path = _parse_args(argv)
        report = _build_cli_roundbook_report(
            mode=mode,
            include_live_curation=include_live_curation,
            round_report_path=round_report_path,
            approval_manifest_path=approval_manifest_path,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(json.dumps(_compact_roundbook_payload(report), indent=2, ensure_ascii=False))
    return 1 if report.overall_readiness == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
