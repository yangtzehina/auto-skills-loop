from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactFile(BaseModel):
    path: str
    content: str
    content_type: str = "text/plain"
    generated_from: list[str] = Field(default_factory=list)
    status: str = "new"


class Artifacts(BaseModel):
    files: list[ArtifactFile] = Field(default_factory=list)
