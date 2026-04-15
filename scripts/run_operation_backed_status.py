from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.operation_backed_ops import (  # noqa: E402
    DEFAULT_OPERATION_BACKED_ARTIFACT_ROOT,
    build_operation_backed_status_report,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_operation_backed_status.py '
        '[--format json|markdown] [--artifact-root PATH]'
    )


def _parse_args(argv: list[str]) -> tuple[str, Path]:
    output_format = 'json'
    artifact_root = DEFAULT_OPERATION_BACKED_ARTIFACT_ROOT
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg == '--artifact-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--artifact-root requires a value')
            artifact_root = Path(argv[idx]).expanduser()
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return output_format, artifact_root


def main(argv: list[str]) -> int:
    try:
        output_format, artifact_root = _parse_args(argv)
        report = build_operation_backed_status_report(artifact_root=artifact_root)
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
