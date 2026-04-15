from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.runtime_handoff import (
    load_runtime_handoff_input,
    normalize_runtime_handoff,
)


def _usage() -> str:
    return 'Usage: python scripts/run_runtime_handoff_normalize.py <handoff.json|->'


def _read_input(source: str) -> str:
    if source == '-':
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError('Missing JSON input on stdin')
        return raw

    input_path = Path(source).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f'Not a file: {input_path}')
    raw = input_path.read_text(encoding='utf-8')
    if not raw.strip():
        raise ValueError(f'Input file is empty: {input_path}')
    return raw


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(_usage(), file=sys.stderr)
        return 2

    try:
        raw = _read_input(argv[1])
        envelope = load_runtime_handoff_input(raw)
        normalized = normalize_runtime_handoff(envelope)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(normalized.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
