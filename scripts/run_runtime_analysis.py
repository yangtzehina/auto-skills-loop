from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.runtime import SkillRunRecord
from openclaw_skill_create.services.observation import default_observation_policy
from openclaw_skill_create.services.runtime_analysis import analyze_skill_run


def _load_run_record(raw: str) -> SkillRunRecord:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON input: {exc.msg}') from exc

    try:
        return SkillRunRecord.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f'Invalid SkillRunRecord payload: {exc}') from exc


def _read_input(source: str) -> SkillRunRecord:
    if source == '-':
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError('Missing JSON input on stdin')
        return _load_run_record(raw)

    input_path = Path(source).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f'Not a file: {input_path}')
    try:
        raw = input_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ValueError(f'Failed to read input file: {input_path}') from exc
    if not raw.strip():
        raise ValueError(f'Input file is empty: {input_path}')
    return _load_run_record(raw)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('Usage: python scripts/run_runtime_analysis.py <run_record.json|->', file=sys.stderr)
        return 2

    try:
        run_record = _read_input(argv[1])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    policy = default_observation_policy(auto_enable=True)
    analysis = analyze_skill_run(run_record, policy)
    print(json.dumps(analysis.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
