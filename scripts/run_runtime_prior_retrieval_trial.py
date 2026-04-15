from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.online import SkillSourceCandidate  # noqa: E402
from openclaw_skill_create.models.runtime_governance import RuntimePriorPilotReport, RuntimePriorRolloutReport  # noqa: E402
from openclaw_skill_create.services.ops_approval import DEFAULT_APPROVAL_MANIFEST, load_ops_approval_state  # noqa: E402
from openclaw_skill_create.services.ops_post_apply import build_prior_pilot_retrieval_trial_report  # noqa: E402
from openclaw_skill_create.services.runtime_governance import (  # noqa: E402
    build_runtime_prior_gate_report,
    build_runtime_prior_pilot_report,
    build_runtime_prior_rollout_report,
)


DEFAULT_SPEC = ROOT / 'tests' / 'fixtures' / 'simulation' / 'prior_gate' / 'hf_trainer_pilot_ready' / 'input' / 'spec.json'
DEFAULT_REPO = ROOT / 'tests' / 'fixtures' / 'hf_prior_trial_repo'


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_prior_retrieval_trial.py '
        '[--approval-manifest PATH] [--family NAME] [--repo-path PATH] [--prior-source PATH] '
        '[--format json|markdown]'
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


def _parse_args(argv: list[str]) -> tuple[Path, str, Path, Path, str]:
    approval_manifest = DEFAULT_APPROVAL_MANIFEST
    family = 'hf-trainer'
    repo_path = DEFAULT_REPO
    prior_source = DEFAULT_SPEC
    output_format = 'json'
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--approval-manifest':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--approval-manifest requires a value')
            approval_manifest = Path(argv[idx]).expanduser()
        elif arg == '--family':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--family requires a value')
            family = argv[idx]
        elif arg == '--repo-path':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--repo-path requires a value')
            repo_path = Path(argv[idx]).expanduser()
        elif arg == '--prior-source':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--prior-source requires a value')
            prior_source = Path(argv[idx]).expanduser()
        elif arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return approval_manifest, family, repo_path, prior_source, output_format


def main(argv: list[str]) -> int:
    try:
        approval_manifest, family, repo_path, prior_source, output_format = _parse_args(argv)
        approval_state = load_ops_approval_state(approval_manifest)
        pilot_report = _load_prior_pilot_report(prior_source)
        report = build_prior_pilot_retrieval_trial_report(
            pilot_report=pilot_report,
            approval_state=approval_state,
            family=family,
            repo_path=repo_path,
            spec_path=prior_source,
        )
    except (ValueError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
