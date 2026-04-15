from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
DEFAULT_ROUND_REPORT = ROOT / 'tests' / 'fixtures' / 'public_source_curation' / 'latest_round_report.json'
DEFAULT_REPO = 'alirezarezvani/claude-skills'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.ops_approval import DEFAULT_APPROVAL_MANIFEST, DEFAULT_COLLECTIONS_FILE, load_ops_approval_state
from openclaw_skill_create.services.ops_post_apply import build_source_promotion_post_apply_report
from openclaw_skill_create.services.public_source_curation import load_public_source_curation_round_report


def _usage() -> str:
    return (
        'Usage: python scripts/run_source_post_apply_monitor.py '
        '[--round-report PATH] [--repo NAME] [--approval-manifest PATH] [--collections-file PATH] '
        '[--scenario NAME ...] [--format json|markdown]'
    )


def _parse_args(argv: list[str]) -> tuple[Path, str, Path, Path, list[str], str]:
    round_report = DEFAULT_ROUND_REPORT
    repo_full_name = DEFAULT_REPO
    approval_manifest = DEFAULT_APPROVAL_MANIFEST
    collections_file = DEFAULT_COLLECTIONS_FILE
    scenario_names: list[str] = []
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
        elif arg == '--collections-file':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--collections-file requires a value')
            collections_file = Path(argv[idx]).expanduser()
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
    return round_report, repo_full_name, approval_manifest, collections_file, scenario_names, output_format


def main(argv: list[str]) -> int:
    try:
        round_report_path, repo_full_name, approval_manifest, collections_file, scenario_names, output_format = _parse_args(argv)
        approval_state = load_ops_approval_state(approval_manifest)
        round_report = load_public_source_curation_round_report(round_report_path)
        report = build_source_promotion_post_apply_report(
            round_report=round_report,
            approval_state=approval_state,
            repo_full_name=repo_full_name,
            collections_file=collections_file,
            scenario_names=list(scenario_names or ['online_reuse_claude_skills_business_adapt']),
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
