from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.runtime import RuntimeCreateCandidate
from openclaw_skill_create.models.runtime_governance import RuntimeGovernanceBatchReport
from openclaw_skill_create.services.runtime_governance import build_runtime_create_queue_report

from .runtime_test_helpers import CREATE_QUEUE_FIXTURE_ROOT


def test_build_runtime_create_queue_report_aggregates_no_skill_cluster():
    report = build_runtime_create_queue_report(
        source_path=CREATE_QUEUE_FIXTURE_ROOT / 'no_skill_cluster' / 'manifest.json',
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert report.runs_processed == 3
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.recommended_status == 'review'
    assert entry.occurrence_count == 3
    assert entry.source_run_ids[-1] == 'run-no-skill-03'
    assert 'fits-calibration' in entry.candidate_key


def test_build_runtime_create_queue_report_filters_simple_gaps(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        'openclaw_skill_create.services.runtime_governance.build_runtime_governance_batch_report',
        lambda **kwargs: RuntimeGovernanceBatchReport(
            runs_processed=1,
            create_candidates=[
                RuntimeCreateCandidate(
                    candidate_id='create-placeholder',
                    task_summary='Fix placeholder metadata.',
                    reason='No existing skill applied cleanly.',
                    requirement_gaps=['Missing metadata placeholder file.'],
                    source_run_ids=['run-placeholder-1'],
                    confidence=0.82,
                )
            ],
        ),
    )

    report = build_runtime_create_queue_report(
        source_path=tmp_path,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert report.entries == []


def test_build_runtime_create_queue_report_skips_operation_backed_followup_candidates(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        'openclaw_skill_create.services.runtime_governance.build_runtime_governance_batch_report',
        lambda **kwargs: RuntimeGovernanceBatchReport(
            runs_processed=1,
            create_candidates=[
                RuntimeCreateCandidate(
                    candidate_id='backend-only-patchable',
                    candidate_kind='existing_skill_followup',
                    task_summary='Add JSON output coverage to the existing backend helper.',
                    reason='Existing operation-backed skill is missing JSON surface coverage.',
                    requirement_gaps=['missing_json_surface'],
                    source_run_ids=['run-operation-1'],
                    confidence=0.88,
                )
            ],
        ),
    )

    report = build_runtime_create_queue_report(
        source_path=tmp_path,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert report.entries == []
