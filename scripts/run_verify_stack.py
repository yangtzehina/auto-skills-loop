from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _usage() -> str:
    return 'Usage: python scripts/run_verify_stack.py --mode <quick|full> [--format json|markdown]'


def _parse_args(argv: list[str]) -> tuple[str, str]:
    mode = ''
    output_format = 'json'
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
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    if mode not in {'quick', 'full'}:
        raise ValueError(f'Unsupported mode: {mode or "<missing>"}')
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return mode, output_format


def _run_command(label: str, cmd: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        'label': label,
        'command': cmd,
        'exit_code': completed.returncode,
        'stdout': completed.stdout,
        'stderr': completed.stderr,
    }


def _render_markdown(report: dict[str, object]) -> str:
    lines = [
        '# Verify Stack',
        '',
        f'- Mode: {report["mode"]}',
        f'- Summary: {report["summary"]}',
        '',
        '## Commands',
    ]
    for item in list(report.get('commands') or []):
        lines.append(f'- `{item["label"]}` exit_code={item["exit_code"]}')
    return '\n'.join(lines).strip()


def main(argv: list[str]) -> int:
    try:
        mode, output_format = _parse_args(argv)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    commands = [
        _run_command(
            'run_tests',
            [sys.executable, 'scripts/run_tests.py'],
        ),
        _run_command(
            'run_simulation_suite',
            [sys.executable, 'scripts/run_simulation_suite.py', '--mode', mode],
        ),
    ]
    failed = [item for item in commands if int(item['exit_code']) != 0]
    report = {
        'mode': mode,
        'commands': commands,
        'summary': (
            f'Verify stack complete: commands={len(commands)} failed={len(failed)}'
        ),
    }
    if output_format == 'markdown':
        print(_render_markdown(report))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
