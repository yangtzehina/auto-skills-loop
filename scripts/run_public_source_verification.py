from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
DEFAULT_CONFIG = ROOT / 'scripts' / 'public_source_candidates.json'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.public_source_verification import PublicSourceCandidateConfig
from openclaw_skill_create.services.public_source_verification import verify_public_source_candidates


def _usage() -> str:
    return 'Usage: python scripts/run_public_source_verification.py [--config PATH]'


def _load_configs(config_path: Path) -> list[PublicSourceCandidateConfig]:
    if not config_path.exists() or not config_path.is_file():
        raise ValueError(f'Not a file: {config_path}')
    try:
        payload = json.loads(config_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON config: {exc.msg}') from exc
    if isinstance(payload, dict):
        raw_items = payload.get('candidates') or []
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raise ValueError('Config must be a JSON array or object with a candidates list')

    configs: list[PublicSourceCandidateConfig] = []
    for item in raw_items:
        try:
            configs.append(PublicSourceCandidateConfig.model_validate(item))
        except ValidationError as exc:
            raise ValueError(f'Invalid candidate config: {exc}') from exc
    return configs


def _parse_args(argv: list[str]) -> Path:
    config_path = DEFAULT_CONFIG
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--config':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--config requires a value')
            config_path = Path(argv[idx]).expanduser()
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    return config_path


def main(argv: list[str]) -> int:
    try:
        config_path = _parse_args(argv)
        configs = _load_configs(config_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    report = verify_public_source_candidates(candidate_configs=configs)
    print(json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
