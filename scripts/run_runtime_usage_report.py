from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.observation import default_observation_policy
from openclaw_skill_create.services.runtime_usage import build_runtime_usage_report


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_usage_report.py '
        '[--skill-id ID] [--format json|markdown]'
    )


def _parse_args(argv: list[str]) -> dict[str, object]:
    skill_id = None
    output_format = 'json'

    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--skill-id':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--skill-id requires a value')
            skill_id = argv[idx]
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
        'skill_id': skill_id,
        'output_format': output_format,
    }


def main(argv: list[str]) -> int:
    try:
        options = _parse_args(argv)
        output_format = options.pop('output_format')
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    policy = default_observation_policy(auto_enable=True)
    report = build_runtime_usage_report(policy=policy, **options)
    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
