from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.expert_dna import (
    EXPERT_SKILL_DNA_PROFILES,
    build_domain_move_plan,
    render_expert_dna_skill_md,
)
from openclaw_skill_create.services.generator_fallback import fallback_generate_methodology_skill_md
from openclaw_skill_create.services.move_quality import build_skill_move_quality_report
from openclaw_skill_create.services.orchestrator import derive_validation_severity
from openclaw_skill_create.services.review import run_skill_quality_review
from openclaw_skill_create.services.validator import run_validator


def _artifacts(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path='SKILL.md', content=content, content_type='text/markdown')])


def _plan(skill_name: str) -> SkillPlan:
    return SkillPlan(
        skill_name=skill_name,
        skill_archetype='methodology_guidance',
        files_to_create=[PlannedFile(path='SKILL.md', purpose='entry')],
    )


def _request(skill_name: str) -> SkillCreateRequestV6:
    return SkillCreateRequestV6(
        task=f'Create a game design methodology skill for {skill_name}.',
        skill_name_hint=skill_name,
        skill_archetype='methodology_guidance',
    )


def test_expert_dna_profiles_load_and_build_move_plans():
    assert {
        'concept-to-mvp-pack',
        'decision-loop-stress-test',
        'simulation-resource-loop-design',
    } <= set(EXPERT_SKILL_DNA_PROFILES)

    for skill_name, dna in EXPERT_SKILL_DNA_PROFILES.items():
        plan = build_domain_move_plan(skill_name=skill_name, task=f'Create {skill_name}.')
        assert plan is not None
        assert plan.dna.skill_name == skill_name
        assert len(plan.dna.workflow_moves) == len(dna.workflow_moves)
        assert plan.dna.workflow_moves[0].decision_probe
        assert plan.dna.workflow_moves[0].repair_move


def test_expert_dna_renderer_creates_numbered_execution_spine():
    content = render_expert_dna_skill_md(
        skill_name='decision-loop-stress-test',
        description='Stress-test a game decision loop.',
        task='Create a decision-loop-stress-test skill.',
        references=[],
        scripts=[],
    )

    assert content is not None
    assert '## Default Workflow' in content
    assert '1. **Define the Current Loop Shape**' in content
    assert '- Decision:' in content
    assert '- Do:' in content
    assert '- Output:' in content
    assert '- Failure Signal:' in content
    assert '- Fix:' in content


def test_move_quality_passes_rendered_known_profile():
    content = render_expert_dna_skill_md(
        skill_name='simulation-resource-loop-design',
        description='Design a simulation resource loop.',
        task='Create a simulation-resource-loop-design skill.',
        references=[],
        scripts=[],
    )
    assert content is not None

    report = build_skill_move_quality_report(
        request=_request('simulation-resource-loop-design'),
        skill_plan=_plan('simulation-resource-loop-design'),
        artifacts=_artifacts(content),
    )

    assert report.status == 'pass'
    assert report.expert_move_recall >= 0.85
    assert report.expert_move_precision >= 0.70
    assert report.numbered_workflow_spine_present is True
    assert report.output_field_semantics_coverage >= 0.75
    assert report.failure_repair_coverage >= 0.75


def test_move_quality_rejects_anchor_heading_shell_without_decision_failure_repair():
    content = """---
name: concept-to-mvp-pack
description: Shape a concept into an MVP pack.
---

# concept-to-mvp-pack

## Overview
Mention validation question, smallest honest loop, feature cut, content scope, out-of-scope, and MVP package.

## Default Workflow
### Define the Core Validation Question
- Mention validation question.
### Identify the Minimum Honest Loop
- Mention smallest honest loop.
### Separate Must-Haves from Supports
- Mention feature cut.

## Output Format
- Core Validation Question:
- Smallest Honest Loop:
- Feature Cut:

## Common Pitfalls
- Scope creep.
"""

    report = build_skill_move_quality_report(
        request=_request('concept-to-mvp-pack'),
        skill_plan=_plan('concept-to-mvp-pack'),
        artifacts=_artifacts(content),
    )

    assert report.status == 'fail'
    assert 'numbered_workflow_spine_missing' in report.blocking_issues
    assert 'failure_repair_missing' in report.blocking_issues


def test_move_quality_rejects_high_cross_case_move_overlap():
    content = render_expert_dna_skill_md(
        skill_name='concept-to-mvp-pack',
        description='Shape a concept into an MVP pack.',
        task='Create a concept-to-mvp-pack skill.',
        references=[],
        scripts=[],
    )
    assert content is not None

    report = build_skill_move_quality_report(
        request=_request('concept-to-mvp-pack'),
        skill_plan=_plan('concept-to-mvp-pack'),
        artifacts=_artifacts(content),
        cross_case_move_overlap=0.55,
    )

    assert report.status == 'fail'
    assert 'high_cross_case_move_overlap' in report.blocking_issues


def test_unknown_methodology_move_quality_warn_blocks_fully_correct():
    request = SkillCreateRequestV6(
        task='Create a research memo synthesis methodology skill.',
        skill_name_hint='research-memo-synthesis',
        skill_archetype='methodology_guidance',
    )
    plan = _plan('research-memo-synthesis')
    content = fallback_generate_methodology_skill_md(
        skill_name='research-memo-synthesis',
        description='Synthesize research memos.',
        task=request.task,
        references=[],
        scripts=[],
    )

    diagnostics = run_validator(request=request, repo_findings={}, skill_plan=plan, artifacts=_artifacts(content))
    review = run_skill_quality_review(
        repo_findings={},
        skill_plan=plan,
        artifacts=_artifacts(content),
        diagnostics=diagnostics,
    )

    assert diagnostics.move_quality is not None
    assert diagnostics.move_quality.status == 'warn'
    assert 'expert_dna_profile_missing' in diagnostics.move_quality.warning_issues
    assert derive_validation_severity(diagnostics) == 'pass'
    assert review.fully_correct is False
    assert review.move_quality_status == 'warn'
