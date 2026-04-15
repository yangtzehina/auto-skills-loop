from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.expert_dna import ExpertDNAAuthoringPack  # noqa: E402
from openclaw_skill_create.services.expert_dna_authoring import (  # noqa: E402
    build_expert_dna_authoring_pack,
    build_expert_dna_review_batch_report,
)


def _usage() -> str:
    return (
        'Usage: python scripts/run_expert_dna_review.py '
        '[--format json|markdown] [--authoring-pack PATH] [--output-root PATH]'
    )


def _parse_args(argv: list[str]) -> tuple[str, Path | None, Path | None]:
    output_format = 'json'
    authoring_pack = None
    output_root = None
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg == '--authoring-pack':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--authoring-pack requires a value')
            authoring_pack = Path(argv[idx]).expanduser()
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
    return output_format, authoring_pack, output_root


def _load_pack(path: Path | None) -> ExpertDNAAuthoringPack:
    if path is None:
        return build_expert_dna_authoring_pack()
    if not path.exists() or not path.is_file():
        raise ValueError(f'Not a file: {path}')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON input: {exc.msg}') from exc
    return ExpertDNAAuthoringPack.model_validate(payload)


def main(argv: list[str]) -> int:
    try:
        output_format, authoring_pack_path, output_root = _parse_args(argv)
        report = build_expert_dna_review_batch_report(_load_pack(authoring_pack_path))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    payload = json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False)
    if output_root is not None:
        target = output_root / 'evals' / 'expert_dna_review.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + '\n', encoding='utf-8')
    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
