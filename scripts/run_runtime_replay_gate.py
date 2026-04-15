from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.runtime_replay import (
    DEFAULT_RUNTIME_REPLAY_BASELINE,
    build_runtime_replay_gate_result,
    write_runtime_replay_baseline,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_replay_gate.py '
        '[--fixtures-root PATH] [--baseline PATH] [--scenario NAME]... [--write-baseline]'
    )


def _parse_args(argv: list[str]) -> dict[str, object]:
    fixtures_root = None
    baseline_path = DEFAULT_RUNTIME_REPLAY_BASELINE
    scenario_names: list[str] = []
    write_baseline = False

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
        elif arg == '--write-baseline':
            write_baseline = True
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1

    return {
        'fixtures_root': fixtures_root,
        'baseline_path': baseline_path,
        'scenario_names': scenario_names or None,
        'write_baseline': write_baseline,
    }


def main(argv: list[str]) -> int:
    try:
        options = _parse_args(argv)
        fixtures_root = options['fixtures_root']
        baseline_path = options['baseline_path']
        scenario_names = options['scenario_names']
        if options['write_baseline']:
            baseline = write_runtime_replay_baseline(
                baseline_path,
                fixtures_root=fixtures_root,
                scenario_names=scenario_names,
            )
            print(json.dumps(baseline.model_dump(mode='json'), indent=2, ensure_ascii=False))
            return 0

        gate = build_runtime_replay_gate_result(
            fixtures_root=fixtures_root,
            baseline_path=baseline_path,
            scenario_names=scenario_names,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    print(json.dumps(gate.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0 if gate.passed else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
