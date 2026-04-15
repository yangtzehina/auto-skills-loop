from __future__ import annotations

from pydantic import BaseModel

from .artifacts import Artifacts


class RepairResult(BaseModel):
    applied: bool = False
    repaired_artifacts: Artifacts
    reason: str = ""
