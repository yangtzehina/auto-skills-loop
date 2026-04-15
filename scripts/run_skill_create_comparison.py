from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.skill_create_comparison import (  # noqa: E402
    build_skill_create_comparison_report,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_skill_create_comparison.py '
        '[--format json|markdown] [--include-hermes] [--golden-root PATH] [--output-root PATH]'
    )


def _parse_args(argv: list[str]) -> tuple[str, bool, Path | None, Path | None]:
    output_format = 'json'
    include_hermes = False
    golden_root = None
    output_root = None
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg == '--include-hermes':
            include_hermes = True
        elif arg == '--golden-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--golden-root requires a value')
            golden_root = Path(argv[idx]).expanduser()
        elif arg == '--output-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--output-root requires a value')
            output_root = Path(argv[idx]).expanduser()
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return output_format, include_hermes, golden_root, output_root


def main(argv: list[str]) -> int:
    try:
        output_format, include_hermes, golden_root, output_root = _parse_args(argv)
        report = build_skill_create_comparison_report(
            include_hermes=include_hermes,
            golden_root=golden_root,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    payload = json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False)
    if output_root is not None:
        target = output_root / 'evals' / 'hermes_comparison.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + '\n', encoding='utf-8')
    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(payload)
    return 1 if report.overall_status == 'fail' else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
