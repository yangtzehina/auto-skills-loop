from __future__ import annotations

from openclaw_skill_create.models.online import SkillProvenance, SkillSourceCandidate
from openclaw_skill_create.services.runtime_governance import build_runtime_prior_gate_report


def _candidate(name: str, *, tags: list[str], repo_full_name: str) -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id=name,
        name=name,
        description=f'{name} workflow',
        trigger_phrases=[name.replace('-', ' ')],
        tags=tags,
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name=repo_full_name,
            ref='main',
            skill_path=f'skills/{name}',
            skill_url=f'https://github.com/{repo_full_name}/blob/main/skills/{name}/SKILL.md',
        ),
    )


def test_build_runtime_prior_gate_report_surfaces_eligibility_and_no_generic_promotion():
    report = build_runtime_prior_gate_report(
        catalog=[
            _candidate('huggingface-vision-trainer', tags=['huggingface', 'vision', 'trainer'], repo_full_name='example/hf'),
            _candidate('deep-research', tags=['research', 'workflow'], repo_full_name='example/research'),
        ],
        runtime_effectiveness_lookup={
            'huggingface-vision-trainer': {
                'skill_id': 'huggingface-vision-trainer__v2_deadbeef',
                'skill_name': 'huggingface-vision-trainer',
                'quality_score': 0.9,
                'run_count': 7,
            }
        },
        task_samples=[
            {
                'task': 'Fine-tune and evaluate a Hugging Face vision model with trainer configuration and datasets',
                'repo_context': {'selected_files': []},
            }
        ],
        runtime_effectiveness_min_runs=5,
    )

    assert report.eligibility_summary['eligible_count'] == 1
    assert report.ranking_impact_summary['generic_promoted_count'] == 0
    assert report.task_impacts[0].prior_applied is True


def test_build_runtime_prior_gate_report_flags_generic_promotion():
    report = build_runtime_prior_gate_report(
        catalog=[
            _candidate('deep-research', tags=['research', 'workflow'], repo_full_name='example/research'),
        ],
        runtime_effectiveness_lookup={
            'deep-research': {
                'skill_id': 'deep-research__v3_deadbeef',
                'skill_name': 'deep-research',
                'quality_score': 0.95,
                'run_count': 8,
            }
        },
        task_samples=[
            {
                'task': 'Research a general product space and assemble a reusable plan',
                'repo_context': {'selected_files': []},
            }
        ],
        runtime_effectiveness_min_runs=5,
    )

    assert report.ranking_impact_summary['prior_applied_count'] == 1
    assert report.task_impacts[0].prior_top_candidate == 'deep-research'


def test_build_runtime_prior_gate_report_respects_allowed_families():
    report = build_runtime_prior_gate_report(
        catalog=[
            _candidate('hf-trainer', tags=['huggingface', 'trainer'], repo_full_name='example/hf'),
            _candidate('deep-research', tags=['research', 'workflow'], repo_full_name='example/research'),
        ],
        runtime_effectiveness_lookup={
            'hf-trainer': {
                'skill_id': 'hf-trainer__v2_deadbeef',
                'skill_name': 'hf-trainer',
                'quality_score': 0.9,
                'run_count': 7,
            },
            'deep-research': {
                'skill_id': 'deep-research__v3_deadbeef',
                'skill_name': 'deep-research',
                'quality_score': 0.97,
                'run_count': 10,
            },
        },
        task_samples=[
            {
                'task': 'Fix the Hugging Face trainer resume workflow',
                'repo_context': {'selected_files': []},
            }
        ],
        runtime_effectiveness_min_runs=5,
        runtime_effectiveness_allowed_families=['hf-trainer'],
    )

    by_name = {item.skill_name: item for item in report.eligible_skills}
    assert by_name['hf-trainer'].eligible is True
    assert by_name['deep-research'].eligible is False
    assert by_name['deep-research'].runtime_prior_delta == 0.0


def test_build_runtime_prior_gate_report_flags_deep_research_generic_promotion_on_product_brief_task():
    report = build_runtime_prior_gate_report(
        catalog=[
            _candidate('user-interview-synthesis', tags=['research', 'interviews', 'product'], repo_full_name='example/product-research'),
            _candidate('deep-research', tags=['research', 'workflow'], repo_full_name='example/research'),
        ],
        runtime_effectiveness_lookup={
            'user-interview-synthesis': {
                'skill_id': 'user-interview-synthesis__v1_deadbeef',
                'skill_name': 'user-interview-synthesis',
                'quality_score': 0.2,
                'run_count': 10,
            },
            'deep-research': {
                'skill_id': 'deep-research__v4_deadbeef',
                'skill_name': 'deep-research',
                'quality_score': 1.0,
                'run_count': 10,
            },
        },
        task_samples=[
            {
                'task': 'Draft a product research brief with competitive landscape notes',
                'repo_context': {'selected_files': []},
            }
        ],
        runtime_effectiveness_min_runs=5,
    )

    assert report.ranking_impact_summary['top_1_changed_count'] == 1
    assert report.ranking_impact_summary['generic_promoted_count'] == 1
    assert report.task_impacts[0].baseline_top_candidate == 'user-interview-synthesis'
    assert report.task_impacts[0].prior_top_candidate == 'deep-research'
    assert report.task_impacts[0].generic_promoted is True
