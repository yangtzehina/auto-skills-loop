from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.runtime_replay_review import build_runtime_replay_review


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_replay_review.py '
        '[--fixtures-root PATH] [--baseline PATH] [--scenario NAME]... [--format json|markdown]'
    )


def _parse_args(argv: list[str]) -> dict[str, object]:
    fixtures_root = None
    baseline_path = None
    scenario_names: list[str] = []
    output_format = 'json'

    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--fixtures-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--fixtures-root requires a value')
            fixtures_root = Path(argv[idx]).expanduser()
        elif arg == '--baseline':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--baseline requires a value')
            baseline_path = Path(argv[idx]).expanduser()
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

    return {
        'fixtures_root': fixtures_root,
        'baseline_path': baseline_path,
        'scenario_names': scenario_names or None,
        'output_format': output_format,
    }


def main(argv: list[str]) -> int:
    try:
        options = _parse_args(argv)
        output_format = options.pop('output_format')
        review = build_runtime_replay_review(**options)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    if output_format == 'markdown':
        print(review.markdown_summary)
    else:
        print(json.dumps(review.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0 if review.passed else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
