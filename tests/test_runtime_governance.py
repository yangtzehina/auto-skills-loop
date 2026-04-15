from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.runtime import SkillRunAnalysis
from openclaw_skill_create.models.runtime_cycle import RuntimeCycleResult
from openclaw_skill_create.models.runtime_followup import RuntimeFollowupResult
from openclaw_skill_create.models.runtime_hook import RuntimeHookResult
from openclaw_skill_create.models.runtime_usage import RuntimeUsageReport, RuntimeUsageSkillReport
from openclaw_skill_create.services.runtime_governance import (
    build_runtime_governance_batch_report,
    build_runtime_governance_bundle,
)

from .runtime_test_helpers import sample_run_record, write_run_manifest, write_run_record


def test_build_runtime_governance_bundle_skips_usage_when_store_unavailable():
    record = sample_run_record(
        run_id='run-governance-1',
        task_id='task-governance-1',
        failure_points=[],
        user_corrections=[],
        execution_result='success',
    )

    result = build_runtime_governance_bundle(
        run_record=record,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert result.runtime_hook.applied is True
    assert result.usage_snapshots == []
    assert result.create_candidates == []
    assert 'usage_snapshots=0' in result.summary
    assert 'usage_skipped=1' in result.summary


def test_build_runtime_governance_bundle_collects_usage_snapshots(monkeypatch):
    record = sample_run_record(run_id='run-governance-2', task_id='task-governance-2')

    def fake_build_runtime_usage_report(*, policy, skill_id=None):
        return RuntimeUsageReport(
            applied=True,
            skill_reports=[
                RuntimeUsageSkillReport(
                    skill_id=skill_id or 'demo-skill__v0_abcd1234',
                    skill_name='demo-skill',
                    quality_score=0.8,
                    recent_run_ids=['run-a', 'run-b'],
                    recent_actions=['no_change', 'patch_current'],
                    latest_recommended_action='patch_current',
                    lineage_version=3,
                    latest_lineage_event='patch_current',
                )
            ],
            summary='ok',
        )

    monkeypatch.setattr(
        'openclaw_skill_create.services.runtime_governance.build_runtime_usage_report',
        fake_build_runtime_usage_report,
    )

    result = build_runtime_governance_bundle(
        run_record=record,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert len(result.usage_snapshots) == 1
    assert result.usage_snapshots[0].skill_id == 'demo-skill__v0_abcd1234'
    assert result.usage_snapshots[0].lineage_version == 3
    assert result.usage_snapshots[0].latest_lineage_event == 'patch_current'
    assert 'usage_snapshots=1' in result.summary


def test_build_runtime_governance_bundle_attaches_semantic_summary():
    record = sample_run_record(
        run_id='run-governance-semantic',
        task_id='task-governance-semantic',
        task_summary='Validate astronomy runtime evidence.',
        execution_result='partial',
        steps_triggered=['load fits'],
        failure_points=['Missing FITS calibration and astropy verification workflow.'],
        user_corrections=[],
    )

    result = build_runtime_governance_bundle(
        run_record=record,
        policy=OpenSpaceObservationPolicy(enabled=False),
        session_evidence={
            'run_id': record.run_id,
            'task_id': record.task_id,
            'turn_trace': [
                {
                    'skill_id': 'demo-skill__v0_abcd1234',
                    'skill_name': 'demo-skill',
                    'step': 'load fits',
                    'phase': 'prepare',
                    'tool': 'python',
                    'status': 'success',
                }
            ],
            'phase_markers': ['prepare'],
            'tool_summary': ['python'],
            'failure_points': record.failure_points,
            'user_corrections': record.user_corrections,
        },
    )

    assert result.semantic_summary is not None
    assert result.semantic_summary.task_summary == 'Validate astronomy runtime evidence.'
    assert result.semantic_summary.what_helped
    assert 'semantic_summary=yes' in result.summary


def test_build_runtime_governance_batch_report_carries_lineage_fields(monkeypatch, tmp_path: Path):
    record = sample_run_record(
        run_id='run-batch-lineage',
        task_id='task-batch-lineage',
        failure_points=[],
        user_corrections=[],
        execution_result='success',
    )
    record_path = write_run_record(tmp_path, record)

    def fake_build_runtime_usage_report(*, policy, skill_id=None):
        return RuntimeUsageReport(
            applied=True,
            skill_reports=[
                RuntimeUsageSkillReport(
                    skill_id=skill_id or 'demo-skill__v0_abcd1234',
                    skill_name='demo-skill',
                    quality_score=0.92,
                    recent_run_ids=['run-batch-lineage'],
                    recent_actions=['no_change'],
                    latest_recommended_action='no_change',
                    lineage_version=5,
                    latest_lineage_event='derive_child',
                )
            ],
            summary='ok',
        )

    monkeypatch.setattr(
        'openclaw_skill_create.services.runtime_governance.build_runtime_usage_report',
        fake_build_runtime_usage_report,
    )

    report = build_runtime_governance_batch_report(
        source_path=record_path.parent,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert report.per_skill[0].lineage_version == 5
    assert report.per_skill[0].latest_lineage_event == 'derive_child'


def test_build_runtime_governance_batch_report_supports_manifest_and_skill_filter(tmp_path: Path):
    record_a = sample_run_record(
        run_id='run-batch-a',
        task_id='task-batch-a',
        failure_points=[],
        user_corrections=[],
        execution_result='success',
    )
    record_b = sample_run_record(
        run_id='run-batch-b',
        task_id='task-batch-b',
        failure_points=['The run scripts/build.py step used the wrong command.'],
        user_corrections=[],
        execution_result='failed',
    )

    path_a = write_run_record(tmp_path, record_a)
    path_b = write_run_record(tmp_path, record_b)
    manifest_path = write_run_manifest(tmp_path, [path_a, path_b])

    report = build_runtime_governance_batch_report(
        source_path=manifest_path,
        policy=OpenSpaceObservationPolicy(enabled=False),
        skill_id='demo-skill__v0_abcd1234',
    )

    assert report.runs_processed == 2
    assert report.per_run
    assert report.per_skill
    assert report.per_skill[0].skill_id == 'demo-skill__v0_abcd1234'
    assert set(report.action_counts)
    assert set(report.approval_counts)
    assert report.markdown_summary.startswith('# Runtime Governance Batch Report')


def test_build_runtime_governance_bundle_surfaces_create_candidates(monkeypatch):
    record = sample_run_record(
        run_id='run-governance-create',
        task_id='task-governance-create',
        execution_result='failed',
        steps_triggered=[],
        failure_points=['Missing FITS calibration and astropy verification workflow.'],
        user_corrections=['Need a dedicated FITS calibration workflow for astronomy reductions.'],
    )
    record.skills_used[0]['applied'] = False

    monkeypatch.setattr(
        'openclaw_skill_create.services.runtime_governance.run_runtime_hook',
        lambda **kwargs: RuntimeHookResult(
            applied=True,
            runtime_cycle=RuntimeCycleResult(
                run_id='run-governance-create',
                task_id='task-governance-create',
                analysis=SkillRunAnalysis(
                    run_id='run-governance-create',
                    task_id='task-governance-create',
                    create_candidates=[
                        {
                            'candidate_id': 'create-fits-workflow',
                            'task_summary': 'Build a FITS calibration skill.',
                            'reason': 'No existing skill applied cleanly.',
                            'requirement_gaps': ['Missing FITS calibration and astropy verification workflow.'],
                            'source_run_ids': ['run-governance-create'],
                        }
                    ],
                ),
                followup=RuntimeFollowupResult(action='no_change', noop=True),
                summary='ok',
            ),
            summary='ok',
        ),
    )

    result = build_runtime_governance_bundle(run_record=record, policy=OpenSpaceObservationPolicy(enabled=False))

    assert len(result.create_candidates) == 1
    assert result.create_candidates[0].candidate_id == 'create-fits-workflow'
