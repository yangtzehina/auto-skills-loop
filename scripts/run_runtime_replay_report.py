from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.runtime_replay import build_runtime_replay_report


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_replay_report.py '
        '[--fixtures-root PATH] [--scenario NAME]...'
    )


def _parse_args(argv: list[str]) -> dict[str, object]:
    fixtures_root = None
    scenario_names: list[str] = []

    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--fixtures-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--fixtures-root requires a value')
            fixtures_root = Path(argv[idx]).expanduser()
        elif arg == '--scenario':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--scenario requires a value')
            scenario_names.append(argv[idx])
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1

    return {
        'fixtures_root': fixtures_root,
        'scenario_names': scenario_names or None,
    }


def main(argv: list[str]) -> int:
    try:
        options = _parse_args(argv)
        report = build_runtime_replay_report(**options)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    print(json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0 if report.passed else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
