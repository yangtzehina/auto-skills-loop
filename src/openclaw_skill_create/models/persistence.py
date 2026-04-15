from __future__ import annotations

from pydantic import BaseModel


class PersistencePolicy(BaseModel):
    dry_run: bool = True
    overwrite: bool = False
    backup_on_update: bool = True
    persist_evaluation_report: bool = False
