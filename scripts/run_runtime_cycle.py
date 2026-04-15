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
from openclaw_skill_create.services.runtime_cycle import run_runtime_cycle


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_cycle.py '
        '[--plan-index N] [--task-summary TEXT] [--skill-name-hint TEXT] [--repo-path PATH]... '
        '<run_record.json|->'
    )


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


def _parse_args(argv: list[str]) -> tuple[str, dict[str, object]]:
    plan_index = None
    task_summary = None
    skill_name_hint = None
    repo_paths: list[str] = []
    source = None

    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--plan-index':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--plan-index requires a value')
            try:
                plan_index = int(argv[idx])
            except ValueError as exc:
                raise ValueError('--plan-index must be an integer') from exc
        elif arg == '--task-summary':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--task-summary requires a value')
            task_summary = argv[idx]
        elif arg == '--skill-name-hint':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--skill-name-hint requires a value')
            skill_name_hint = argv[idx]
        elif arg == '--repo-path':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--repo-path requires a value')
            repo_paths.append(argv[idx])
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            if source is not None:
                raise ValueError('Only one input source may be provided')
            source = arg
        idx += 1

    if source is None:
        raise ValueError(_usage())

    return source, {
        'plan_index': plan_index,
        'task_summary': task_summary,
        'repo_paths': repo_paths if repo_paths else None,
        'skill_name_hint': skill_name_hint,
    }


def main(argv: list[str]) -> int:
    try:
        source, options = _parse_args(argv)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        if not str(exc).startswith('Usage:'):
            print(_usage(), file=sys.stderr)
        return 2

    try:
        run_record = _read_input(source)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    policy = default_observation_policy(auto_enable=True)
    result = run_runtime_cycle(run_record, policy, **options)
    print(json.dumps(result.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
