from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ..models.operation_backed_ops import (
    OperationBackedBacklogReport,
    OperationBackedStatusEntry,
    OperationBackedStatusReport,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OPERATION_BACKED_ARTIFACT_ROOT = ROOT / '.generated-skills' / 'ops_artifacts' / 'operation_backed'


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in list(values or []):
        text = str(value or '').strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


def _entry_label(entry: OperationBackedStatusEntry) -> str:
    return entry.skill_name or entry.skill_id or Path(str(entry.source_path or '')).stem


def _load_entry(path: Path) -> OperationBackedStatusEntry | None:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    payload['source_path'] = str(path)
    try:
        entry = OperationBackedStatusEntry.model_validate(payload)
    except Exception:
        return None
    if entry.skill_archetype != 'operation_backed':
        return None
    return entry


def load_operation_backed_status_entries(
    *,
    artifact_root: Path | None = None,
) -> list[OperationBackedStatusEntry]:
    root = Path(artifact_root or DEFAULT_OPERATION_BACKED_ARTIFACT_ROOT).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []
    entries = [_load_entry(path) for path in sorted(root.glob('*.json'))]
    filtered = [item for item in entries if item is not None]
    return sorted(filtered, key=lambda item: (_entry_label(item), item.source_path))


def render_operation_backed_status_markdown(report: OperationBackedStatusReport) -> str:
    lines = [
        '# Operation-Backed Status',
        '',
        f'- total_operation_backed_skills={report.total_operation_backed_skills}',
        f'- archetype_counts={report.archetype_counts}',
        f'- operation_validation_status_counts={report.operation_validation_status_counts}',
        f'- recommended_followup_counts={report.recommended_followup_counts}',
        f'- actionable_count={report.actionable_count}',
        f'- hold_count={report.hold_count}',
        f'- recent_coverage_gap_types={report.recent_coverage_gap_types or ["(none)"]}',
        f'- Summary: {report.summary}',
        '',
        '## Entries',
    ]
    if not report.entries:
        lines.append('- None')
        return '\n'.join(lines).strip()
    for entry in report.entries:
        lines.append(f'- `{_entry_label(entry)}`')
        lines.append(f'  - operation_validation_status={entry.operation_validation_status}')
        lines.append(f'  - recommended_followup={entry.recommended_followup}')
        lines.append(f'  - security_rating={entry.security_rating}')
        lines.append(f'  - actionable={entry.actionable}')
        if entry.coverage_gap_summary:
            lines.append(f'  - coverage_gap_summary={entry.coverage_gap_summary}')
        if entry.repo_path:
            lines.append(f'  - repo_path={entry.repo_path}')
    return '\n'.join(lines).strip()


def build_operation_backed_status_report(
    *,
    artifact_root: Path | None = None,
) -> OperationBackedStatusReport:
    entries = load_operation_backed_status_entries(artifact_root=artifact_root)
    archetype_counts = Counter(entry.skill_archetype for entry in entries)
    validation_counts = Counter(entry.operation_validation_status for entry in entries)
    followup_counts = Counter(entry.recommended_followup for entry in entries)
    recent_gap_types = _ordered_unique(
        [gap for entry in entries for gap in list(entry.coverage_gap_summary or [])]
    )
    report = OperationBackedStatusReport(
        entries=entries,
        total_operation_backed_skills=len(entries),
        archetype_counts=dict(archetype_counts),
        operation_validation_status_counts=dict(validation_counts),
        recommended_followup_counts=dict(followup_counts),
        hold_count=sum(1 for entry in entries if entry.recommended_followup == 'hold'),
        actionable_count=sum(1 for entry in entries if entry.actionable),
        recent_coverage_gap_types=recent_gap_types,
        summary=(
            f'Operation-backed steady-state status complete: entries={len(entries)} '
            f'actionable={sum(1 for entry in entries if entry.actionable)} '
            f'hold={sum(1 for entry in entries if entry.recommended_followup == "hold")}'
        ),
    )
    report.markdown_summary = render_operation_backed_status_markdown(report)
    return report


def render_operation_backed_backlog_markdown(report: OperationBackedBacklogReport) -> str:
    lines = [
        '# Operation-Backed Backlog',
        '',
        f'- summary_counts={report.summary_counts}',
        f'- actionable_count={report.actionable_count}',
        f'- Summary: {report.summary}',
        '',
        '## Patch Current Candidates',
    ]
    if not report.patch_current_candidates:
        lines.append('- None')
    else:
        for item in report.patch_current_candidates:
            lines.append(f'- {item}')
    lines.extend(['', '## Derive Child Candidates'])
    if not report.derive_child_candidates:
        lines.append('- None')
    else:
        for item in report.derive_child_candidates:
            lines.append(f'- {item}')
    lines.extend(['', '## Hold Candidates'])
    if not report.hold_candidates:
        lines.append('- None')
    else:
        for item in report.hold_candidates:
            lines.append(f'- {item}')
    return '\n'.join(lines).strip()


def build_operation_backed_backlog_report(
    *,
    artifact_root: Path | None = None,
    status_report: OperationBackedStatusReport | None = None,
) -> OperationBackedBacklogReport:
    status = status_report or build_operation_backed_status_report(artifact_root=artifact_root)
    patch_current_candidates = [_entry_label(entry) for entry in status.entries if entry.recommended_followup == 'patch_current']
    derive_child_candidates = [_entry_label(entry) for entry in status.entries if entry.recommended_followup == 'derive_child']
    hold_candidates = [_entry_label(entry) for entry in status.entries if entry.recommended_followup == 'hold']
    report = OperationBackedBacklogReport(
        entries=list(status.entries or []),
        summary_counts=dict(status.recommended_followup_counts),
        patch_current_candidates=patch_current_candidates,
        derive_child_candidates=derive_child_candidates,
        hold_candidates=hold_candidates,
        actionable_count=len(patch_current_candidates) + len(derive_child_candidates),
        summary=(
            f'Operation-backed backlog complete: patch_current={len(patch_current_candidates)} '
            f'derive_child={len(derive_child_candidates)} hold={len(hold_candidates)}'
        ),
    )
    report.markdown_summary = render_operation_backed_backlog_markdown(report)
    return report
