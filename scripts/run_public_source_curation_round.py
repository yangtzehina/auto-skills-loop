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
from openclaw_skill_create.services.public_source_curation import build_public_source_curation_round


def _usage() -> str:
    return (
        'Usage: python scripts/run_public_source_curation_round.py '
        '[--config PATH] [--format json|markdown] [--fixture-root PATH] [--scenario NAME]...'
    )


def _load_configs(config_path: Path) -> list[PublicSourceCandidateConfig]:
    if not config_path.exists() or not config_path.is_file():
        raise ValueError(f'Not a file: {config_path}')
    try:
        payload = json.loads(config_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON config: {exc.msg}') from exc
    raw_items = payload.get('candidates') if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        raise ValueError('Config must be a JSON array or object with a candidates list')
    return [PublicSourceCandidateConfig.model_validate(item) for item in raw_items]


def _parse_args(argv: list[str]) -> tuple[Path, str, Path | None, list[str]]:
    config_path = DEFAULT_CONFIG
    output_format = 'json'
    fixture_root = None
    scenario_names: list[str] = []
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == '--config':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--config requires a value')
            config_path = Path(argv[idx]).expanduser()
        elif arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg == '--fixture-root':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--fixture-root requires a value')
            fixture_root = Path(argv[idx]).expanduser()
        elif arg == '--scenario':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--scenario requires a value')
            scenario_names.append(argv[idx])
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            raise ValueError(f'Unexpected positional argument: {arg}')
        idx += 1
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return config_path, output_format, fixture_root, scenario_names


def main(argv: list[str]) -> int:
    try:
        config_path, output_format, fixture_root, scenario_names = _parse_args(argv)
        configs = _load_configs(config_path)
    except (ValueError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    report = build_public_source_curation_round(
        candidate_configs=configs,
        fixture_root=fixture_root,
        scenario_names=scenario_names or None,
    )
    if output_format == 'markdown':
        print(report.markdown_summary)
    else:
        print(json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
