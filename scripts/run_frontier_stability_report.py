from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.services.frontier_stability import build_frontier_stability_report  # noqa: E402


def _usage() -> str:
    return (
        "Usage: python scripts/run_frontier_stability_report.py "
        "[--runs N] [--format json|markdown]"
    )


def _parse_args(argv: list[str]) -> tuple[int, str]:
    runs = 5
    output_format = "json"
    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--runs":
            idx += 1
            if idx >= len(argv):
                raise ValueError("--runs requires a value")
            runs = int(argv[idx])
        elif arg == "--format":
            idx += 1
            if idx >= len(argv):
                raise ValueError("--format requires a value")
            output_format = argv[idx]
        elif arg.startswith("--"):
            raise ValueError(f"Unknown option: {arg}")
        else:
            raise ValueError(f"Unexpected positional argument: {arg}")
        idx += 1
    if output_format not in {"json", "markdown"}:
        raise ValueError(f"Unsupported format: {output_format}")
    return runs, output_format


def main(argv: list[str]) -> int:
    try:
        runs, output_format = _parse_args(argv)
        report = build_frontier_stability_report(runs=runs)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2
    if output_format == "markdown":
        print(report.markdown_summary)
    else:
        print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
