from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
DEFAULT_PRIOR_SOURCE = ROOT / 'tests' / 'fixtures' / 'simulation' / 'prior_gate' / 'hf_trainer_pilot_ready' / 'input' / 'spec.json'
DEFAULT_FAMILY = 'hf-trainer'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.online import SkillSourceCandidate
from openclaw_skill_create.models.runtime_governance import RuntimePriorPilotReport, RuntimePriorRolloutReport
from openclaw_skill_create.services.ops_approval import (
    DEFAULT_APPROVAL_MANIFEST,
    DEFAULT_OPS_ARTIFACT_ROOT,
    build_prior_pilot_manual_trial_pack,
    load_ops_approval_state,
)
from openclaw_skill_create.services.runtime_governance import (
    build_runtime_prior_gate_report,
    build_runtime_prior_pilot_exercise_report,
    build_runtime_prior_pilot_report,
    build_runtime_prior_rollout_report,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_prior_manual_trial.py '
        '[--prior-source PATH] [--family NAME] [--approval-manifest PATH] [--artifact-root PATH] '
        '[--scenario NAME ...] [--format json|markdown]'
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


def _parse_args(argv: list[str]) -> tuple[Path, str, Path, Path, list[str], str]:
    prior_source = DEFAULT_PRIOR_SOURCE
    family = DEFAULT_FAMILY
    approval_manifest = DEFAULT_APPROVAL_MANIFEST
    artifact_root = DEFAULT_OPS_ARTIFACT_ROOT
    scenario_names: list[str] = []
    output_format = 'json'
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--prior-source':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--prior-source requires a value')
            prior_source = Path(argv[idx]).expanduser()
        elif arg == '--family':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--family requires a value')
            family = argv[idx]
        elif arg == '--approval-manifest':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--approval-manifest requires a value')
            approval_manifest = Path(argv[idx]).expanduser()
        elif arg == '--artifact-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--artifact-root requires a value')
            artifact_root = Path(argv[idx]).expanduser()
        elif arg == '--scenario':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--scenario requires a value')
            scenario_names.append(argv[idx])
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
    return prior_source, family, approval_manifest, artifact_root, scenario_names, output_format


def main(argv: list[str]) -> int:
    try:
        prior_source, family, approval_manifest, artifact_root, scenario_names, output_format = _parse_args(argv)
        approval_state = load_ops_approval_state(approval_manifest)
        pilot_report = _load_prior_pilot_report(prior_source)
        exercise_report = build_runtime_prior_pilot_exercise_report(
            pilot_report=pilot_report,
            family=family,
            approval_state=approval_state,
            artifact_root=artifact_root,
            scenario_names=list(scenario_names or ['hf_trainer_pilot_ready', 'allowlisted_family_only']),
        )
        pack = build_prior_pilot_manual_trial_pack(
            pilot_report=pilot_report,
            family=family,
            approval_state=approval_state,
            artifact_root=artifact_root,
            generic_promotion_risk=exercise_report.generic_promotion_risk,
            top_1_changes=exercise_report.top_1_changes,
            exercise_verdict=exercise_report.verdict,
        )
    except (ValueError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    if output_format == 'markdown':
        print(pack.markdown_summary)
    else:
        print(json.dumps(pack.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
