from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.simulation import build_simulation_suite_report


def _usage() -> str:
    return (
        'Usage: python scripts/run_simulation_suite.py '
        '--mode <quick|full|runtime-intake|runtime-batch|create-queue|prior-gate|smoke-chain|source-curation> '
        '[--format json|markdown] [--scenario NAME ...] [--fixture-root PATH]'
    )


def _parse_args(argv: list[str]) -> tuple[str, str, Path | None, list[str]]:
    mode = ''
    output_format = 'json'
    fixture_root = None
    scenarios: list[str] = []
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--mode':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--mode requires a value')
            mode = argv[idx]
        elif arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg == '--fixture-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--fixture-root requires a value')
            fixture_root = Path(argv[idx]).expanduser()
        elif arg == '--scenario':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--scenario requires a value')
            scenarios.append(argv[idx])
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    if not mode:
        raise ValueError('--mode is required')
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return mode, output_format, fixture_root, scenarios


def main(argv: list[str]) -> int:
    try:
        mode, output_format, fixture_root, scenarios = _parse_args(argv)
        report = build_simulation_suite_report(
            mode=mode,
            fixture_root=fixture_root,
            scenario_names=scenarios,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False))

    if report.invalid_fixture_count:
        return 2
    if report.drifted_count:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
