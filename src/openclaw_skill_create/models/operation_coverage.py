from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


ALLOWED_OPERATION_GAP_TYPES = {
    'missing_operation',
    'missing_operation_group',
    'missing_json_surface',
    'missing_session_model',
    'missing_mutating_safeguards',
    'contract_surface_drift',
}
ALLOWED_OPERATION_FOLLOWUPS = {'patch_current', 'derive_child', 'hold', 'no_change'}


def _normalize_gap_type(value: Any) -> str:
    normalized = str(value or 'contract_surface_drift').strip().lower()
    if normalized in ALLOWED_OPERATION_GAP_TYPES:
        return normalized
    return 'contract_surface_drift'


def _normalize_followup(value: Any) -> str:
    normalized = str(value or 'no_change').strip().lower()
    if normalized in ALLOWED_OPERATION_FOLLOWUPS:
        return normalized
    return 'no_change'


class OperationCoverageGap(BaseModel):
    gap_type: str = 'contract_surface_drift'
    operation_group: str = ''
    operation_name: str = ''
    reason: str = ''
    recommended_action: str = 'patch_current'

    def model_post_init(self, __context: Any) -> None:
        self.gap_type = _normalize_gap_type(self.gap_type)
        self.operation_group = str(self.operation_group or '').strip()
        self.operation_name = str(self.operation_name or '').strip()
        self.reason = str(self.reason or '').strip()
        self.recommended_action = _normalize_followup(self.recommended_action)


class OperationCoverageReport(BaseModel):
    skill_archetype: str = 'guidance'
    operation_count: int = 0
    covered_operations: list[str] = Field(default_factory=list)
    missing_operations: list[str] = Field(default_factory=list)
    gap_summary: list[OperationCoverageGap] = Field(default_factory=list)
    validation_status: str = 'not_applicable'
    security_alignment: str = 'not_applicable'
    recommended_followup: str = 'no_change'

    def model_post_init(self, __context: Any) -> None:
        self.skill_archetype = str(self.skill_archetype or 'guidance').strip().lower() or 'guidance'
        self.operation_count = int(self.operation_count or 0)
        self.covered_operations = [
            str(item or '').strip()
            for item in list(self.covered_operations or [])
            if str(item or '').strip()
        ]
        self.missing_operations = [
            str(item or '').strip()
            for item in list(self.missing_operations or [])
            if str(item or '').strip()
        ]
        self.gap_summary = [
            item if isinstance(item, OperationCoverageGap) else OperationCoverageGap.model_validate(item)
            for item in list(self.gap_summary or [])
        ]
        self.validation_status = str(self.validation_status or 'not_applicable').strip().lower() or 'not_applicable'
        self.security_alignment = str(self.security_alignment or 'not_applicable').strip().lower() or 'not_applicable'
        self.recommended_followup = _normalize_followup(self.recommended_followup)
