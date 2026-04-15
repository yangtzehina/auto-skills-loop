from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.expert_dna_authoring import (  # noqa: E402
    DEFAULT_EXPERT_DNA_GOLDEN_ROOT,
    build_expert_dna_authoring_pack,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_expert_dna_authoring.py '
        '[--format json|markdown] [--golden-root PATH] [--output-root PATH]'
    )


def _parse_args(argv: list[str]) -> tuple[str, Path, Path | None]:
    output_format = 'json'
    golden_root = DEFAULT_EXPERT_DNA_GOLDEN_ROOT
    output_root = None
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
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
    return output_format, golden_root, output_root


def main(argv: list[str]) -> int:
    try:
        output_format, golden_root, output_root = _parse_args(argv)
        report = build_expert_dna_authoring_pack(golden_root=golden_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    payload = json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False)
    if output_root is not None:
        target = output_root / 'evals' / 'expert_dna_authoring.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + '\n', encoding='utf-8')
    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
