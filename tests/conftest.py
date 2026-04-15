from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def make_tmp_repo(tmp_path: Path) -> Path:
    (tmp_path / 'README.md').write_text('# Demo\n\nRepo intro\n', encoding='utf-8')
    (tmp_path / 'scripts').mkdir(exist_ok=True)
    (tmp_path / 'scripts' / 'run.py').write_text('print("hi")\n', encoding='utf-8')
    (tmp_path / '.github').mkdir(exist_ok=True)
    (tmp_path / '.github' / 'workflows').mkdir(exist_ok=True)
    (tmp_path / '.github' / 'workflows' / 'ci.yml').write_text('name: ci\n', encoding='utf-8')
    return tmp_path
