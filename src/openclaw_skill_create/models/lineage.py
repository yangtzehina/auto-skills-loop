from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SkillLineageHistoryEntry(BaseModel):
    event: str = 'generated'
    skill_id: str = ''
    version: int = 0
    parent_skill_id: str | None = None
    content_sha: str = ''
    quality_score: float = 0.0
    summary: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.event = str(self.event or 'generated').strip() or 'generated'
        self.skill_id = str(self.skill_id or '').strip()
        self.version = max(int(self.version or 0), 0)
        self.parent_skill_id = str(self.parent_skill_id or '').strip() or None
        self.content_sha = str(self.content_sha or '').strip()
        self.quality_score = float(self.quality_score or 0.0)
        self.summary = str(self.summary or '').strip()


class SkillLineageManifest(BaseModel):
    skill_id: str
    version: int = 0
    parent_skill_id: str | None = None
    content_sha: str = ''
    quality_score: float = 0.0
    history: list[SkillLineageHistoryEntry] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        self.skill_id = str(self.skill_id or '').strip()
        self.version = max(int(self.version or 0), 0)
        self.parent_skill_id = str(self.parent_skill_id or '').strip() or None
        self.content_sha = str(self.content_sha or '').strip()
        self.quality_score = float(self.quality_score or 0.0)
        self.history = [
            item if isinstance(item, SkillLineageHistoryEntry) else SkillLineageHistoryEntry.model_validate(item)
            for item in list(self.history or [])
        ]
