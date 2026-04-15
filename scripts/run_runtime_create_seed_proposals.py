from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.observation import default_observation_policy
from openclaw_skill_create.services.runtime_governance import build_runtime_create_seed_proposal_pack


def _usage() -> str:
    return (
        'Usage: python scripts/run_runtime_create_seed_proposals.py '
        '[--baseline PATH] [--scenario NAME]... [--enable-judge] [--judge-model NAME] '
        '[--format json|markdown] <runs_dir|manifest.json>'
    )


def _parse_args(argv: list[str]) -> tuple[Path, dict[str, object]]:
    baseline_path = None
    scenario_names: list[str] = []
    enable_judge = False
    judge_model = None
    output_format = 'json'
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
        elif arg == '--format':
            idx += 1
            if idx >= len(argv):
                raise ValueError('--format requires a value')
            output_format = argv[idx]
        elif arg.startswith('--'):
            raise ValueError(f'Unknown option: {arg}')
        else:
            if source is not None:
                raise ValueError('Only one source path may be provided')
            source = Path(arg).expanduser()
        idx += 1

    if source is None:
        raise ValueError(_usage())
    if output_format not in {'json', 'markdown'}:
        raise ValueError(f'Unsupported format: {output_format}')
    return source, {
        'baseline_path': baseline_path,
        'scenario_names': scenario_names or None,
        'enable_llm_judge': enable_judge,
        'model': judge_model,
        'output_format': output_format,
    }


def main(argv: list[str]) -> int:
    try:
        source_path, options = _parse_args(argv)
        output_format = str(options.pop('output_format'))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        if not str(exc).startswith('Usage:'):
            print(_usage(), file=sys.stderr)
        return 2

    policy = default_observation_policy(auto_enable=True)
    try:
        pack = build_runtime_create_seed_proposal_pack(
            source_path=source_path,
            policy=policy,
            **options,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if output_format == 'markdown':
        print(pack.markdown_summary)
    else:
        print(json.dumps(pack.model_dump(mode='json'), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
