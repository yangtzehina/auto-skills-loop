from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.external_eval_export import (  # noqa: E402
    build_external_eval_export_bundle,
)


def _usage() -> str:
    return (
        "Usage: python scripts/run_external_eval_export.py "
        "--targets <promptfoo,openai> [--format json|markdown] [--output-root PATH]"
    )


def _parse_args(argv: list[str]) -> tuple[list[str], str, Path | None]:
    targets: list[str] = []
    output_format = "json"
    output_root = None
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--targets":
            idx += 1
            if idx >= len(argv):
                raise ValueError("--targets requires a value")
            targets = [item.strip() for item in argv[idx].split(",") if item.strip()]
        elif arg == "--format":
            idx += 1
            if idx >= len(argv):
                raise ValueError("--format requires a value")
            output_format = argv[idx]
        elif arg == "--output-root":
            idx += 1
            if idx >= len(argv):
                raise ValueError("--output-root requires a value")
            output_root = Path(argv[idx]).expanduser()
        elif arg.startswith("--"):
            raise ValueError(f"Unknown option: {arg}")
        else:
            raise ValueError(f"Unexpected positional argument: {arg}")
        idx += 1
    if not targets:
        raise ValueError("--targets requires at least one target")
    if output_format not in {"json", "markdown"}:
        raise ValueError(f"Unsupported format: {output_format}")
    return targets, output_format, output_root


def main(argv: list[str]) -> int:
    try:
        targets, output_format, output_root = _parse_args(argv)
        bundle = build_external_eval_export_bundle(targets=targets, output_root=output_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    if output_format == "markdown":
        print(bundle.markdown_summary)
    else:
        print(json.dumps(bundle.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
