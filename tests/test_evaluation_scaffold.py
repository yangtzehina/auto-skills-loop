from __future__ import annotations

import json

from openclaw_skill_create.models.online import SkillReuseDecision
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.evaluation_scaffold import (
    build_benchmark_eval_spec,
    build_output_eval_spec,
    build_trigger_eval_spec,
    generate_eval_artifacts,
)


def make_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='capture-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='evals/trigger_eval.json', purpose='trigger checks', source_basis=[]),
            PlannedFile(path='evals/output_eval.json', purpose='output baseline', source_basis=[]),
            PlannedFile(path='evals/benchmark.json', purpose='benchmark dimensions', source_basis=[]),
        ],
    )


def test_build_trigger_eval_spec_includes_positive_and_negative_cases():
    request = SkillCreateRequestV6(task='Capture a design review decision into Notion', enable_eval_scaffold=True)
    spec = build_trigger_eval_spec(request=request, skill_plan=make_plan())

    assert spec.skill_name == 'capture-skill'
    assert any(case.expected_trigger for case in spec.cases)
    assert any(not case.expected_trigger for case in spec.cases)


def test_build_trigger_eval_spec_prefers_task_description_over_unrelated_blueprint_copy():
    request = SkillCreateRequestV6(
        task='Build a repo-grounded skill for calibrating astronomical FITS frames with Astropy and validating reduced observations.',
        enable_eval_scaffold=True,
        online_skill_blueprints=[
            {
                'blueprint_id': 'bp-1',
                'name': 'notion-capture',
                'description': 'Capture conversations and decisions into structured Notion pages.',
                'trigger_summary': 'Use when recording notes into Notion.',
                'artifacts': [],
                'tags': [],
                'workflow_summary': [],
                'provenance': {
                    'source_type': 'community',
                    'ecosystem': 'codex',
                    'repo_full_name': 'example/notion',
                    'ref': 'main',
                    'skill_path': 'skills/notion',
                    'skill_url': 'https://example.invalid/notion',
                },
            }
        ],
    )
    spec = build_trigger_eval_spec(request=request, skill_plan=make_plan())

    assert 'use when' in spec.description.lower()
    assert 'fits frames with astropy' in spec.description.lower()
    positive_queries = [case.query for case in spec.cases if case.expected_trigger]
    assert all('notion' not in query.lower() for query in positive_queries)


def test_build_output_eval_spec_uses_reuse_decision_to_add_source_blueprint_baseline():
    request = SkillCreateRequestV6(task='Capture a design review decision into Notion', enable_eval_scaffold=True)
    spec = build_output_eval_spec(
        request=request,
        skill_plan=make_plan(),
        reuse_decision=SkillReuseDecision(mode='adapt_existing', rationale=['Strong blueprint match']),
    )

    assert 'source_blueprint' in spec.baseline_variants
    assert spec.cases[0].expected_behavior
    assert spec.cases[0].success_criteria


def test_build_benchmark_eval_spec_adds_adaptation_dimension_when_reusing():
    request = SkillCreateRequestV6(task='Capture a design review decision into Notion', enable_eval_scaffold=True)
    spec = build_benchmark_eval_spec(
        request=request,
        skill_plan=make_plan(),
        reuse_decision=SkillReuseDecision(mode='compose_existing'),
    )

    names = [dimension.name for dimension in spec.dimensions]
    assert 'adaptation_quality' in names
    assert 'task_alignment' in names


def test_generate_eval_artifacts_returns_three_json_files():
    request = SkillCreateRequestV6(task='Capture a design review decision into Notion', enable_eval_scaffold=True)
    artifacts = generate_eval_artifacts(
        request=request,
        skill_plan=make_plan(),
        reuse_decision=SkillReuseDecision(mode='generate_fresh'),
    )

    assert [artifact.path for artifact in artifacts] == [
        'evals/trigger_eval.json',
        'evals/output_eval.json',
        'evals/benchmark.json',
    ]
    for artifact in artifacts:
        payload = json.loads(artifact.content)
        assert payload['skill_name'] == 'capture-skill'
