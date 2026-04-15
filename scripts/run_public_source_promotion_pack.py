from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
DEFAULT_ROUND_REPORT = ROOT / 'tests' / 'fixtures' / 'public_source_curation' / 'latest_round_report.json'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.ops_approval import DEFAULT_APPROVAL_MANIFEST, load_ops_approval_state
from openclaw_skill_create.services.public_source_curation import (
    build_public_source_promotion_pack,
    load_public_source_curation_round_report,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_public_source_promotion_pack.py '
        '[--round-report PATH] [--repo FULL_NAME] [--approval-manifest PATH] [--format json|markdown]'
    )


def _parse_args(argv: list[str]) -> tuple[Path, str, Path, str]:
    round_report = DEFAULT_ROUND_REPORT
    repo_full_name = 'alirezarezvani/claude-skills'
    approval_manifest = DEFAULT_APPROVAL_MANIFEST
    output_format = 'json'
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--round-report':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--round-report requires a value')
            round_report = Path(argv[idx]).expanduser()
        elif arg == '--repo':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--repo requires a value')
            repo_full_name = argv[idx]
        elif arg == '--approval-manifest':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--approval-manifest requires a value')
            approval_manifest = Path(argv[idx]).expanduser()
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
    return round_report, repo_full_name, approval_manifest, output_format


def main(argv: list[str]) -> int:
    try:
        round_report_path, repo_full_name, approval_manifest_path, output_format = _parse_args(argv)
        round_report = load_public_source_curation_round_report(round_report_path)
        approval_state = load_ops_approval_state(approval_manifest_path)
        pack = build_public_source_promotion_pack(
            round_report=round_report,
            repo_full_name=repo_full_name,
            approval_state=approval_state,
        )
    except (ValueError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        if not str(exc).startswith('Usage:'):
            print(_usage(), file=sys.stderr)
        return 2

    if output_format == 'markdown':
        print(pack.markdown_summary)
    else:
        print(json.dumps(pack.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
