from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.operation_backed_ops import (
    build_operation_backed_backlog_report,
    build_operation_backed_status_report,
)


def _write_snapshot(root: Path, name: str, payload: dict[str, object]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f'{name}.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')


def test_build_operation_backed_status_report_summarizes_entries(tmp_path: Path):
    artifact_root = tmp_path / 'operation_backed'
    _write_snapshot(
        artifact_root,
        'safe',
        {
            'skill_id': 'safe',
            'skill_name': 'safe-cli',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'validated',
            'recommended_followup': 'no_change',
            'coverage_gap_summary': [],
            'security_rating': 'LOW',
        },
    )
    _write_snapshot(
        artifact_root,
        'patch',
        {
            'skill_id': 'patch',
            'skill_name': 'patchable-helper',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'patch_current',
            'coverage_gap_summary': ['missing_json_surface'],
            'security_rating': 'LOW',
        },
    )
    _write_snapshot(
        artifact_root,
        'hold',
        {
            'skill_id': 'hold',
            'skill_name': 'blocked-helper',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'hold',
            'coverage_gap_summary': ['contract_surface_drift'],
            'security_rating': 'HIGH',
        },
    )

    report = build_operation_backed_status_report(artifact_root=artifact_root)

    assert report.total_operation_backed_skills == 3
    assert report.recommended_followup_counts == {'hold': 1, 'no_change': 1, 'patch_current': 1}
    assert report.operation_validation_status_counts == {'needs_attention': 2, 'validated': 1}
    assert report.actionable_count == 1
    assert report.hold_count == 1
    assert report.recent_coverage_gap_types == ['contract_surface_drift', 'missing_json_surface']


def test_build_operation_backed_backlog_report_filters_no_change_entries(tmp_path: Path):
    artifact_root = tmp_path / 'operation_backed'
    _write_snapshot(
        artifact_root,
        'safe',
        {
            'skill_id': 'safe',
            'skill_name': 'safe-cli',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'validated',
            'recommended_followup': 'no_change',
            'coverage_gap_summary': [],
            'security_rating': 'LOW',
        },
    )
    _write_snapshot(
        artifact_root,
        'patch',
        {
            'skill_id': 'patch',
            'skill_name': 'patchable-helper',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'patch_current',
            'coverage_gap_summary': ['missing_json_surface'],
            'security_rating': 'LOW',
        },
    )
    _write_snapshot(
        artifact_root,
        'derive',
        {
            'skill_id': 'derive',
            'skill_name': 'child-derivation',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'derive_child',
            'coverage_gap_summary': ['missing_operation_group'],
            'security_rating': 'LOW',
        },
    )
    _write_snapshot(
        artifact_root,
        'hold',
        {
            'skill_id': 'hold',
            'skill_name': 'blocked-helper',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'hold',
            'coverage_gap_summary': ['contract_surface_drift'],
            'security_rating': 'HIGH',
        },
    )

    report = build_operation_backed_backlog_report(artifact_root=artifact_root)

    assert report.patch_current_candidates == ['patchable-helper']
    assert report.derive_child_candidates == ['child-derivation']
    assert report.hold_candidates == ['blocked-helper']
    assert report.actionable_count == 2
    assert report.summary_counts == {'derive_child': 1, 'hold': 1, 'no_change': 1, 'patch_current': 1}
