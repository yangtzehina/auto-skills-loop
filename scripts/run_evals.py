from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.services.evaluation_runner import run_evaluations


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == '.md':
        return 'text/markdown'
    if suffix in {'.json'}:
        return 'application/json'
    if suffix in {'.yaml', '.yml'}:
        return 'application/yaml'
    return 'text/plain'


def load_artifacts(skill_dir: Path) -> Artifacts:
    files: list[ArtifactFile] = []
    for path in sorted(skill_dir.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir).as_posix()
        if relative.startswith('.git/') or relative.startswith('__pycache__/'):
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        files.append(
            ArtifactFile(
                path=relative,
                content=content,
                content_type=_content_type(path),
                generated_from=['disk'],
                status='existing',
            )
        )
    return Artifacts(files=files)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('Usage: python scripts/run_evals.py /path/to/generated-skill', file=sys.stderr)
        return 2

    skill_dir = Path(argv[1]).expanduser().resolve()
    if not skill_dir.exists() or not skill_dir.is_dir():
        print(f'Not a directory: {skill_dir}', file=sys.stderr)
        return 2

    report = run_evaluations(artifacts=load_artifacts(skill_dir))
    if report is None:
        print(json.dumps({'error': 'No eval specs found'}, indent=2))
        return 1

    print(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
