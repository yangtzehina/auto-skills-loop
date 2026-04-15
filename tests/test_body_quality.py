from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.body_quality import (
    build_skill_body_quality_report,
    build_skill_self_review_report,
)
from openclaw_skill_create.services.orchestrator import derive_validation_severity
from openclaw_skill_create.services.validator import run_validator


def _artifacts(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path='SKILL.md', content=content, content_type='text/markdown')])


def test_body_quality_rejects_hollow_skill_md():
    request = SkillCreateRequestV6(
        task='Create a methodology skill with workflow, output template, and pitfalls.',
        skill_name_hint='thin-skill',
        skill_archetype='methodology_guidance',
    )
    plan = SkillPlan(
        skill_name='thin-skill',
        skill_archetype='methodology_guidance',
        files_to_create=[PlannedFile(path='SKILL.md', purpose='entry')],
    )
    content = (
        '---\nname: thin-skill\ndescription: Create a methodology skill with workflow, output template, and pitfalls.\n---\n\n'
        '# thin-skill\n\nUse this skill when needed.\n'
    )
    report = build_skill_body_quality_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'fail'
    assert 'body_too_thin' in report.blocking_issues
    assert 'missing_workflow' in report.blocking_issues
    assert 'missing_output_template' in report.blocking_issues


def test_body_quality_detects_description_stuffing_and_prompt_echo():
    task = ' '.join([f'game design workflow output template pitfall concept mvp loop {idx}' for idx in range(20)])
    description = task + ' ' + task
    content = f'---\nname: stuffed\ndescription: {description}\n---\n\n# Stuffed\n\nUse this skill when needed.\n'
    request = SkillCreateRequestV6(task=task, skill_name_hint='stuffed', skill_archetype='methodology_guidance')
    plan = SkillPlan(skill_name='stuffed', skill_archetype='methodology_guidance')

    report = build_skill_body_quality_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert 'description_stuffing' in report.blocking_issues
    assert 'prompt_echo' in report.blocking_issues


def test_methodology_body_quality_passes_complete_skill():
    from openclaw_skill_create.services.generator_fallback import fallback_generate_methodology_skill_md

    request = SkillCreateRequestV6(
        task='Create a game design methodology skill for concept to MVP packaging.',
        skill_name_hint='concept-to-mvp-pack',
        skill_archetype='methodology_guidance',
    )
    plan = SkillPlan(skill_name='concept-to-mvp-pack', skill_archetype='methodology_guidance')
    content = fallback_generate_methodology_skill_md(
        skill_name='concept-to-mvp-pack',
        description='Shape a concept into an MVP pack. Use when Codex needs methodology guidance.',
        task=request.task,
        references=[],
        scripts=[],
    )
    body_quality = build_skill_body_quality_report(request=request, skill_plan=plan, artifacts=_artifacts(content))
    self_review = build_skill_self_review_report(
        request=request,
        skill_plan=plan,
        artifacts=_artifacts(content),
        body_quality=body_quality,
    )

    assert body_quality.status == 'pass'
    assert self_review.status == 'pass'
    assert body_quality.missing_required_sections == []


def test_validator_blocks_hollow_methodology_skill():
    request = SkillCreateRequestV6(
        task='Create a methodology skill with workflow, output template, and pitfalls.',
        skill_name_hint='thin-skill',
        skill_archetype='methodology_guidance',
    )
    plan = SkillPlan(
        skill_name='thin-skill',
        skill_archetype='methodology_guidance',
        files_to_create=[PlannedFile(path='SKILL.md', purpose='entry')],
    )
    diagnostics = run_validator(
        request=request,
        repo_findings={},
        skill_plan=plan,
        artifacts=_artifacts(
            '---\nname: thin-skill\ndescription: Create a methodology skill with workflow, output template, and pitfalls.\n---\n\n# thin-skill\n\nUse this skill when needed.\n'
        ),
    )

    assert diagnostics.body_quality is not None
    assert diagnostics.self_review is not None
    assert derive_validation_severity(diagnostics) == 'fail'
    assert 'body_too_thin' in diagnostics.validation.repairable_issue_types
