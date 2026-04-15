from __future__ import annotations

from openclaw_skill_create.models.runtime import RuntimeSessionEvidence, SkillRunAnalysis
from openclaw_skill_create.services.runtime_semantic import build_runtime_semantic_summary

from .runtime_test_helpers import sample_run_record


def test_build_runtime_semantic_summary_returns_none_without_rich_evidence():
    record = sample_run_record(
        run_id='run-semantic-none',
        task_id='task-semantic-none',
        steps_triggered=['load dataset'],
        failure_points=[],
        user_corrections=[],
        execution_result='success',
    )
    record.step_trace = []
    record.phase_markers = []
    record.tool_summary = []
    analysis = SkillRunAnalysis(
        run_id=record.run_id,
        task_id=record.task_id,
        skills_analyzed=[
            {
                'skill_id': 'demo-skill__v0_abcd1234',
                'skill_name': 'demo-skill',
                'helped': True,
                'most_valuable_step': 'load dataset',
                'run_quality_score': 1.0,
                'recommended_action': 'no_change',
                'confidence': 0.8,
            }
        ],
    )

    assert build_runtime_semantic_summary(run_record=record, analysis=analysis) is None


def test_build_runtime_semantic_summary_uses_analysis_and_evidence():
    record = sample_run_record(
        run_id='run-semantic-evidence',
        task_id='task-semantic-evidence',
        task_summary='Repair the astronomy reduction workflow.',
        steps_triggered=['load fits', 'verify astropy headers'],
        failure_points=['Missing FITS calibration and astropy verification workflow.'],
        user_corrections=['Need a dedicated FITS calibration workflow for astronomy reductions.'],
        execution_result='partial',
    )
    evidence = RuntimeSessionEvidence(
        run_id=record.run_id,
        task_id=record.task_id,
        turn_trace=[
            {
                'skill_id': 'astro-skill__v1_deadbeef',
                'skill_name': 'astro-skill',
                'step': 'load fits',
                'phase': 'prepare',
                'tool': 'python',
                'status': 'success',
            },
            {
                'skill_id': 'astro-skill__v1_deadbeef',
                'skill_name': 'astro-skill',
                'step': 'verify astropy headers',
                'phase': 'validate',
                'tool': 'python',
                'status': 'failed',
            },
        ],
        phase_markers=['prepare', 'validate'],
        tool_summary=['python'],
        failure_points=record.failure_points,
        user_corrections=record.user_corrections,
    )
    analysis = SkillRunAnalysis(
        run_id=record.run_id,
        task_id=record.task_id,
        skills_analyzed=[
            {
                'skill_id': 'astro-skill__v1_deadbeef',
                'skill_name': 'astro-skill',
                'helped': False,
                'most_valuable_step': 'load fits',
                'misleading_step': 'verify astropy headers',
                'missing_steps': ['Missing FITS calibration and astropy verification workflow.'],
                'run_quality_score': 0.6,
                'recommended_action': 'patch_current',
                'confidence': 0.85,
            }
        ],
        create_candidates=[
            {
                'candidate_id': 'create-fits-workflow',
                'task_summary': 'Build a FITS calibration skill.',
                'reason': 'No clean existing skill covered the astronomy reduction workflow.',
                'requirement_gaps': ['Need a dedicated FITS calibration workflow for astronomy reductions.'],
                'source_run_ids': [record.run_id],
                'confidence': 0.82,
            }
        ],
    )

    summary = build_runtime_semantic_summary(
        run_record=record,
        analysis=analysis,
        session_evidence=evidence,
    )

    assert summary is not None
    assert summary.task_summary == 'Repair the astronomy reduction workflow.'
    assert 'astro-skill: load fits' in summary.what_helped
    assert 'astro-skill: verify astropy headers' in summary.what_misled
    assert summary.repeated_gaps
    assert summary.evidence_coverage == 1.0
