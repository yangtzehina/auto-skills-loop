from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.online import SkillSourceCandidate
from openclaw_skill_create.services.runtime_governance import build_runtime_prior_gate_report


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_prior_gate.py '
        '[--format json|markdown] <prior_gate_spec.json|->'
    )


def _load_spec(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON input: {exc.msg}') from exc
    if not isinstance(payload, dict):
        raise ValueError('Prior gate spec must be a JSON object')
    return payload


def _read_input(source: str) -> dict[str, object]:
    if source == '-':
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError('Missing JSON input on stdin')
        return _load_spec(raw)
    input_path = Path(source).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f'Not a file: {input_path}')
    raw = input_path.read_text(encoding='utf-8')
    if not raw.strip():
        raise ValueError(f'Input file is empty: {input_path}')
    return _load_spec(raw)


def _parse_args(argv: list[str]) -> tuple[str, str]:
    output_format = 'json'
    source = None
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            if source is not None:
                raise ValueError('Only one input source may be provided')
            source = arg
        idx += 1
    if source is None:
        raise ValueError(_usage())
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return source, output_format


def main(argv: list[str]) -> int:
    try:
        source, output_format = _parse_args(argv)
        payload = _read_input(source)
        catalog = [
            SkillSourceCandidate.model_validate(item)
            for item in list(payload.get('catalog') or [])
        ]
    except (ValueError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        if not str(exc).startswith('Usage:'):
            print(_usage(), file=sys.stderr)
        return 2

    report = build_runtime_prior_gate_report(
        catalog=catalog,
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        task_samples=list(payload.get('task_samples') or []),
        runtime_effectiveness_min_runs=int(payload.get('runtime_effectiveness_min_runs', 5) or 5),
        runtime_effectiveness_allowed_families=list(payload.get('runtime_effectiveness_allowed_families') or []) or None,
    )
    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
