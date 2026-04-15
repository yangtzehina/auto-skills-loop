from __future__ import annotations

import json
from pathlib import Path


def load_schema(repo_root: Path) -> dict:
    schema_path = repo_root / "config" / "notion_schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    schema = load_schema(repo_root)
    print(f"Loaded schema with {len(schema.get('properties', {}))} properties")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
