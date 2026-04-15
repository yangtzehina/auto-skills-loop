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
from openclaw_skill_create.services.runtime_governance import build_runtime_governance_bundle


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_governance_bundle.py '
        '[--baseline PATH] [--scenario NAME]... [--enable-judge] [--judge-model NAME] '
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
    raw = input_path.read_text(encoding='utf-8')
    if not raw.strip():
        raise ValueError(f'Input file is empty: {input_path}')
    return _load_run_record(raw)


def _parse_args(argv: list[str]) -> tuple[str, dict[str, object]]:
    baseline_path = None
    scenario_names: list[str] = []
    enable_judge = False
    judge_model = None
    source = None

    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--baseline':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--baseline requires a value')
            baseline_path = Path(argv[idx]).expanduser()
        elif arg == '--scenario':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--scenario requires a value')
            scenario_names.append(argv[idx])
        elif arg == '--enable-judge':
            enable_judge = True
        elif arg == '--judge-model':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--judge-model requires a value')
            judge_model = argv[idx]
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
        'baseline_path': baseline_path,
        'scenario_names': scenario_names or None,
        'enable_llm_judge': enable_judge,
        'model': judge_model,
    }


def main(argv: list[str]) -> int:
    try:
        source, options = _parse_args(argv)
        run_record = _read_input(source)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        if not str(exc).startswith('Usage:'):
            print(_usage(), file=sys.stderr)
        return 2

    policy = default_observation_policy(auto_enable=True)
    result = build_runtime_governance_bundle(run_record=run_record, policy=policy, **options)
    print(json.dumps(result.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
