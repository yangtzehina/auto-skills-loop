from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_governance import build_runtime_create_review_pack

from .runtime_test_helpers import CREATE_QUEUE_FIXTURE_ROOT, sample_run_record, write_run_manifest, write_run_record


def test_build_runtime_create_review_pack_promotes_no_skill_cluster():
    pack = build_runtime_create_review_pack(
        source_path=CREATE_QUEUE_FIXTURE_ROOT / 'no_skill_cluster' / 'manifest.json',
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert pack.runs_processed == 3
    assert len(pack.entries) == 1
    entry = pack.entries[0]
    assert entry.recommended_next_action == 'review'
    assert entry.occurrence_count == 3
    assert entry.suggested_title
    assert entry.suggested_description


def test_build_runtime_create_review_pack_keeps_simple_gaps_out(tmp_path: Path):
    run_paths = []
    for idx in range(1, 4):
        record = sample_run_record(
            run_id=f'run-simple-gap-{idx}',
            task_id='task-simple-gap',
            task_summary='Fix metadata placeholder references.',
            execution_result='failed',
            steps_triggered=[],
            failure_points=['Missing metadata placeholder file.'],
            user_corrections=['Metadata placeholder still missing.'],
        )
        record.skills_used[0]['applied'] = False
        run_paths.append(write_run_record(tmp_path, record, name=f'run_{idx}.json'))
    manifest_path = write_run_manifest(tmp_path, run_paths)

    pack = build_runtime_create_review_pack(
        source_path=manifest_path,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert pack.entries == []
