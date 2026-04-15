from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
DEFAULT_CREATE_SEED_SOURCE = ROOT / 'tests' / 'fixtures' / 'runtime_create_queue' / 'no_skill_cluster' / 'manifest.json'
DEFAULT_CANDIDATE_KEY = 'missing-fits-calibration-and-astropy-verification-workflow'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.ops_approval import (
    DEFAULT_APPROVAL_MANIFEST,
    DEFAULT_OPS_ARTIFACT_ROOT,
    build_create_seed_manual_round_pack,
    load_ops_approval_state,
)
from openclaw_skill_create.services.runtime_governance import build_runtime_create_seed_proposal_pack


def _usage() -> str:
    return (
        'Usage: python scripts/run_create_seed_round_pack.py '
        '[--candidate-key NAME] [--create-seed-source PATH] [--approval-manifest PATH] '
        '[--artifact-root PATH] [--format json|markdown]'
    )


def _parse_args(argv: list[str]) -> tuple[str, Path, Path, Path, str]:
    candidate_key = DEFAULT_CANDIDATE_KEY
    create_seed_source = DEFAULT_CREATE_SEED_SOURCE
    approval_manifest = DEFAULT_APPROVAL_MANIFEST
    artifact_root = DEFAULT_OPS_ARTIFACT_ROOT
    output_format = 'json'
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--candidate-key':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--candidate-key requires a value')
            candidate_key = argv[idx]
        elif arg == '--create-seed-source':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--create-seed-source requires a value')
            create_seed_source = Path(argv[idx]).expanduser()
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
    return candidate_key, create_seed_source, approval_manifest, artifact_root, output_format


def main(argv: list[str]) -> int:
    try:
        candidate_key, create_seed_source, approval_manifest, artifact_root, output_format = _parse_args(argv)
        approval_state = load_ops_approval_state(approval_manifest)
        create_seed_pack = build_runtime_create_seed_proposal_pack(
            source_path=create_seed_source,
            policy=OpenSpaceObservationPolicy(enabled=False),
        )
        pack = build_create_seed_manual_round_pack(
            create_seed_pack=create_seed_pack,
            approval_state=approval_state,
            candidate_key=candidate_key,
            artifact_root=artifact_root,
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
