from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


ALLOWED_OPERATION_BACKED_FOLLOWUPS = {'no_change', 'patch_current', 'derive_child', 'hold'}


def _normalize_followup(value: Any) -> str:
    normalized = str(value or 'no_change').strip().lower()
    if normalized in ALLOWED_OPERATION_BACKED_FOLLOWUPS:
        return normalized
    return 'no_change'


def _normalize_string_list(values: Any) -> list[str]:
    result: list[str] = []
    for value in list(values or []):
        text = str(value or '').strip()
        if text:
            result.append(text)
    return result


class OperationBackedStatusEntry(BaseModel):
    skill_id: str = ''
    skill_name: str = ''
    skill_archetype: str = 'operation_backed'
    operation_validation_status: str = 'not_applicable'
    recommended_followup: str = 'no_change'
    coverage_gap_summary: list[str] = Field(default_factory=list)
    security_rating: str = 'LOW'
    actionable: bool = False
    repo_path: str = ''
    notes: str = ''
    source_path: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.skill_id = str(self.skill_id or '').strip()
        self.skill_name = str(self.skill_name or '').strip()
        self.skill_archetype = str(self.skill_archetype or 'operation_backed').strip().lower() or 'operation_backed'
        self.operation_validation_status = str(self.operation_validation_status or 'not_applicable').strip().lower() or 'not_applicable'
        self.recommended_followup = _normalize_followup(self.recommended_followup)
        self.coverage_gap_summary = _normalize_string_list(self.coverage_gap_summary)
        self.security_rating = str(self.security_rating or 'LOW').strip().upper() or 'LOW'
        self.repo_path = str(self.repo_path or '').strip()
        self.notes = str(self.notes or '').strip()
        self.source_path = str(self.source_path or '').strip()
        self.actionable = self.recommended_followup in {'patch_current', 'derive_child'}


class OperationBackedStatusReport(BaseModel):
    entries: list[OperationBackedStatusEntry] = Field(default_factory=list)
    total_operation_backed_skills: int = 0
    archetype_counts: dict[str, int] = Field(default_factory=dict)
    operation_validation_status_counts: dict[str, int] = Field(default_factory=dict)
    recommended_followup_counts: dict[str, int] = Field(default_factory=dict)
    hold_count: int = 0
    actionable_count: int = 0
    recent_coverage_gap_types: list[str] = Field(default_factory=list)
    summary: str = ''
    markdown_summary: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.entries = [
            item if isinstance(item, OperationBackedStatusEntry) else OperationBackedStatusEntry.model_validate(item)
            for item in list(self.entries or [])
        ]
        self.total_operation_backed_skills = int(self.total_operation_backed_skills or 0)
        self.archetype_counts = {str(key): int(value or 0) for key, value in dict(self.archetype_counts or {}).items()}
        self.operation_validation_status_counts = {
            str(key): int(value or 0) for key, value in dict(self.operation_validation_status_counts or {}).items()
        }
        self.recommended_followup_counts = {
            str(key): int(value or 0) for key, value in dict(self.recommended_followup_counts or {}).items()
        }
        self.hold_count = int(self.hold_count or 0)
        self.actionable_count = int(self.actionable_count or 0)
        self.recent_coverage_gap_types = _normalize_string_list(self.recent_coverage_gap_types)
        self.summary = str(self.summary or '').strip()
        self.markdown_summary = str(self.markdown_summary or '').strip()


class OperationBackedBacklogReport(BaseModel):
    entries: list[OperationBackedStatusEntry] = Field(default_factory=list)
    summary_counts: dict[str, int] = Field(default_factory=dict)
    patch_current_candidates: list[str] = Field(default_factory=list)
    derive_child_candidates: list[str] = Field(default_factory=list)
    hold_candidates: list[str] = Field(default_factory=list)
    actionable_count: int = 0
    summary: str = ''
    markdown_summary: str = ''

    def model_post_init(self, __context: Any) -> None:
        self.entries = [
            item if isinstance(item, OperationBackedStatusEntry) else OperationBackedStatusEntry.model_validate(item)
            for item in list(self.entries or [])
        ]
        self.summary_counts = {str(key): int(value or 0) for key, value in dict(self.summary_counts or {}).items()}
        self.patch_current_candidates = _normalize_string_list(self.patch_current_candidates)
        self.derive_child_candidates = _normalize_string_list(self.derive_child_candidates)
        self.hold_candidates = _normalize_string_list(self.hold_candidates)
        self.actionable_count = int(self.actionable_count or 0)
        self.summary = str(self.summary or '').strip()
        self.markdown_summary = str(self.markdown_summary or '').strip()
