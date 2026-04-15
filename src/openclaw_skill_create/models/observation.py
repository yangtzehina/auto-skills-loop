from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


DEFAULT_OPENSPACE_PYTHON = (
    os.environ.get('AUTO_SKILLS_LOOP_OPENSPACE_PYTHON')
    or os.environ.get('SKILL_CREATE_OPENSPACE_PYTHON')
    or ''
).strip()
DEFAULT_OPENSPACE_DB_PATH = (
    os.environ.get('AUTO_SKILLS_LOOP_OPENSPACE_DB_PATH')
    or os.environ.get('SKILL_CREATE_OPENSPACE_DB_PATH')
    or ''
).strip() or None


class OpenSpaceObservationPolicy(BaseModel):
    enabled: bool = False
    openspace_python: str = DEFAULT_OPENSPACE_PYTHON
    db_path: Optional[str] = DEFAULT_OPENSPACE_DB_PATH
    timeout_seconds: int = 45
    analyzed_by: str = 'auto-skills-loop.observe-only'
