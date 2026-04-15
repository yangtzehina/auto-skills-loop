from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.ops_post_apply import (  # noqa: E402
    build_create_seed_package_review_report,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_create_seed_package_review.py '
        '[--candidate-key NAME] [--run-summary PATH] [--format json|markdown]'
    )


def _parse_args(argv: list[str]) -> tuple[str, Path | None, str]:
    candidate_key = 'missing-fits-calibration-and-astropy-verification-workflow'
    run_summary = None
    output_format = 'json'
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--candidate-key':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--candidate-key requires a value')
            candidate_key = argv[idx]
        elif arg == '--run-summary':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--run-summary requires a value')
            run_summary = Path(argv[idx]).expanduser()
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
    return candidate_key, run_summary, output_format


def main(argv: list[str]) -> int:
    try:
        candidate_key, run_summary, output_format = _parse_args(argv)
        report = build_create_seed_package_review_report(
            candidate_key=candidate_key,
            run_summary_path=run_summary,
        )
    except ValueError as exc:
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
