from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.domain_expertise import build_skill_domain_expertise_report
from openclaw_skill_create.services.domain_specificity import build_skill_domain_specificity_report
from openclaw_skill_create.services.generator_fallback import fallback_generate_methodology_skill_md
from openclaw_skill_create.services.orchestrator import derive_validation_severity
from openclaw_skill_create.services.review import run_skill_quality_review
from openclaw_skill_create.services.validator import run_validator


def _artifacts(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path='SKILL.md', content=content, content_type='text/markdown')])


def _methodology_plan(skill_name: str) -> SkillPlan:
    return SkillPlan(
        skill_name=skill_name,
        skill_archetype='methodology_guidance',
        files_to_create=[PlannedFile(path='SKILL.md', purpose='entry')],
    )


def _methodology_shell(*, name: str, overview: str, workflow: str, output: str) -> str:
    return f"""---
name: {name}
description: Methodology guidance for {name}.
---

# {name}

## Overview
{overview}

## When to Use
- Use when the task needs a repeatable method.
- Use when the output needs structured decisions.
- Use when an agent needs checks before finalizing.
- Use when tradeoffs must be made explicit.

## When Not to Use
- Do not use for a one-line answer.
- Do not use when the domain has no decision surface.
- Do not use when the user already supplied the final artifact.
- Do not use when only a code formatter is needed.

## Inputs
- Goal: the concrete outcome to produce.
- Context: the constraints, audience, and source material.
- Evidence: examples, notes, and existing drafts.
- Boundaries: what must stay out of scope.

## Workflow
{workflow}

## Output Format
{output}

## Quality Checks
- Check that the method answers the actual user problem.
- Check that the output exposes assumptions before decisions.
- Check that each section includes a concrete next action.
- Check that the final result can be used without hidden context.
- Check that unresolved risks are named plainly.
- Check that the artifact avoids generic filler.

## Common Pitfalls
- Repeating the prompt instead of transforming it.
- Filling the template without making domain decisions.
- Treating all constraints as equal.
- Skipping edge cases because the outline looks complete.
- Hiding tradeoffs in vague prose.
- Shipping a polished shell with no usable method.
"""


def test_domain_specificity_passes_known_game_design_anchors():
    request = SkillCreateRequestV6(
        task='Create a game design methodology skill for concept-to-mvp-pack.',
        skill_name_hint='concept-to-mvp-pack',
        skill_archetype='methodology_guidance',
    )
    plan = _methodology_plan('concept-to-mvp-pack')
    content = fallback_generate_methodology_skill_md(
        skill_name='concept-to-mvp-pack',
        description='Shape a concept into an MVP pack.',
        task=request.task,
        references=[],
        scripts=[],
    )

    report = build_skill_domain_specificity_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'pass'
    assert report.domain_anchor_coverage >= 0.70
    assert report.workflow_anchor_coverage >= 0.35
    assert report.output_anchor_coverage >= 0.20
    assert report.missing_domain_anchors == []


def test_domain_specificity_rejects_generic_methodology_shell():
    request = SkillCreateRequestV6(
        task='Create a concept-to-mvp-pack skill for game design.',
        skill_name_hint='concept-to-mvp-pack',
        skill_archetype='methodology_guidance',
    )
    plan = _methodology_plan('concept-to-mvp-pack')
    content = _methodology_shell(
        name='concept-to-mvp-pack',
        overview='Use this skill to organize a project into a practical method with checks and a final artifact.',
        workflow='\n'.join(
            [
                '1. Name the real job and write the operating context.',
                '2. Identify the operating context and constraints.',
                '3. Build the working frame from the available notes.',
                '4. Run the method against the current draft.',
                '5. Produce the artifact with concise recommendations.',
                '6. Run the guardrail pass before final delivery.',
            ]
        ),
        output='\n'.join(
            [
                '- Context summary',
                '- Decision list',
                '- Open risks',
                '- Recommended next action',
                '- Final handoff note',
            ]
        ),
    )

    report = build_skill_domain_specificity_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'fail'
    assert 'missing_domain_anchors' in report.blocking_issues


def test_domain_specificity_requires_workflow_anchors_not_just_overview_echo():
    request = SkillCreateRequestV6(
        task='Create a concept-to-mvp-pack skill with validation question, smallest honest loop, feature cut, content scope, out-of-scope, and mvp pack decisions.',
        skill_name_hint='concept-to-mvp-pack',
        skill_archetype='methodology_guidance',
    )
    plan = _methodology_plan('concept-to-mvp-pack')
    anchors = 'validation question, smallest honest loop, feature cut, content scope, out-of-scope, and mvp pack'
    content = _methodology_shell(
        name='concept-to-mvp-pack',
        overview=f'This method mentions {anchors} in the overview only.',
        workflow='\n'.join(
            [
                '1. Read the task and list the known facts.',
                '2. Pick the strongest option from the notes.',
                '3. Remove anything that does not fit the plan.',
                '4. Write a concise recommendation.',
                '5. Check assumptions before final delivery.',
                '6. Ask for missing context only if blocked.',
            ]
        ),
        output='\n'.join(
            [
                f'- Domain terms: {anchors}',
                '- Decision summary',
                '- Risk list',
                '- Next action',
                '- Final checklist',
            ]
        ),
    )

    report = build_skill_domain_specificity_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'fail'
    assert 'domain_workflow_missing' in report.blocking_issues


def test_domain_specificity_warning_blocks_fully_correct_but_not_validation_pass():
    request = SkillCreateRequestV6(
        task='Audit an operations handoff workflow and package the business review steps into a reusable skill with evaluation coverage',
        skill_name_hint='simulation-business-workflow-skill',
        skill_archetype='methodology_guidance',
    )
    plan = _methodology_plan('simulation-business-workflow-skill')
    domain_terms = 'audit operations handoff, package business review, business review steps, audit operations, operations handoff, package business'
    content = _methodology_shell(
        name='simulation-business-workflow-skill',
        overview=f'This business workflow method covers {domain_terms}.',
        workflow='\n'.join(
            [
                '1. Read the source notes and collect the constraints.',
                '2. Identify the current handoff owner and target reader.',
                '3. Group the evidence into decision points.',
                '4. Convert the notes into a reusable checklist.',
                '5. Add evaluation coverage for the final artifact.',
                '6. Review the final package for missing assumptions.',
            ]
        ),
        output='\n'.join(
            [
                f'- Domain terms: {domain_terms}',
                '- Review checklist',
                '- Evaluation coverage',
                '- Risks and follow-up',
                '- Final reusable handoff',
            ]
        ),
    )

    diagnostics = run_validator(request=request, repo_findings={}, skill_plan=plan, artifacts=_artifacts(content))
    review = run_skill_quality_review(
        repo_findings={},
        skill_plan=plan,
        artifacts=_artifacts(content),
        diagnostics=diagnostics,
    )

    assert diagnostics.domain_specificity is not None
    assert diagnostics.domain_specificity.status == 'warn'
    assert 'domain_workflow_missing' in diagnostics.domain_specificity.warning_issues
    assert derive_validation_severity(diagnostics) == 'pass'
    assert review.fully_correct is False
    assert review.domain_specificity_status == 'warn'


def test_domain_expertise_passes_known_game_design_moves():
    request = SkillCreateRequestV6(
        task='Create a game design methodology skill for simulation-resource-loop-design.',
        skill_name_hint='simulation-resource-loop-design',
        skill_archetype='methodology_guidance',
    )
    plan = _methodology_plan('simulation-resource-loop-design')
    content = fallback_generate_methodology_skill_md(
        skill_name='simulation-resource-loop-design',
        description='Design a simulation resource loop.',
        task=request.task,
        references=[],
        scripts=[],
    )

    report = build_skill_domain_expertise_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'pass'
    assert report.domain_move_coverage >= 0.55
    assert report.action_anchor_coverage >= 0.60
    assert report.output_anchor_coverage >= 0.40


def test_domain_expertise_rejects_anchor_mentions_without_domain_moves():
    request = SkillCreateRequestV6(
        task='Create a concept-to-mvp-pack skill with validation question, smallest honest loop, feature cut, content scope, out-of-scope, and mvp pack decisions.',
        skill_name_hint='concept-to-mvp-pack',
        skill_archetype='methodology_guidance',
    )
    plan = _methodology_plan('concept-to-mvp-pack')
    anchors = 'validation question, smallest honest loop, feature cut, content scope, out-of-scope, and mvp pack'
    content = _methodology_shell(
        name='concept-to-mvp-pack',
        overview=f'This shell repeats {anchors}.',
        workflow='\n'.join(
            [
                f'1. Mention {anchors} without turning them into actions.',
                '2. Name the real job and identify the operating context.',
                '3. Build the working frame and run the method.',
                '4. Produce the artifact and run the guardrail pass.',
                '5. Choose 3-5 criteria and finalize.',
                '6. Turn abstract goals into concrete checks.',
            ]
        ),
        output='\n'.join(
            [
                f'- Domain terms: {anchors}',
                '- Context summary',
                '- Decision list',
                '- Open risks',
                '- Final handoff note',
            ]
        ),
    )

    report = build_skill_domain_expertise_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'fail'
    assert 'domain_judgment_checks_missing' in report.blocking_issues
    assert 'domain_pitfalls_missing' in report.blocking_issues


def test_domain_expertise_warning_blocks_fully_correct_but_not_validation_pass():
    task = (
        'Create a methodology skill for `target segment`, `positioning claim`, '
        '`channel bet`, and `success signal` planning.'
    )
    request = SkillCreateRequestV6(
        task=task,
        skill_name_hint='go-to-market-decision-brief',
        skill_archetype='methodology_guidance',
    )
    plan = _methodology_plan('go-to-market-decision-brief')
    content = _methodology_shell(
        name='go-to-market-decision-brief',
        overview='This method is for a go-to-market decision brief.',
        workflow='\n'.join(
            [
                '1. Convert target segment into a concrete decision.',
                '2. Use positioning claim to define the main tradeoff.',
                '3. Turn channel bet into an explicit workflow step.',
                '4. Check success signal against launch risk.',
                '5. Produce the decision brief.',
                '6. Mark unresolved assumptions.',
            ]
        ),
        output='\n'.join(
            [
                '- Target segment: <specific buyer or user>',
                '- Positioning claim: <claim to test>',
                '- Channel bet: <distribution path>',
                '- Success signal: <observable evidence>',
                '- Decision brief: <recommendation>',
            ]
        ),
    )

    diagnostics = run_validator(request=request, repo_findings={}, skill_plan=plan, artifacts=_artifacts(content))
    review = run_skill_quality_review(
        repo_findings={},
        skill_plan=plan,
        artifacts=_artifacts(content),
        diagnostics=diagnostics,
    )

    assert diagnostics.domain_expertise is not None
    assert diagnostics.domain_expertise.status == 'warn'
    assert 'domain_judgment_checks_missing' in diagnostics.domain_expertise.warning_issues
    assert derive_validation_severity(diagnostics) == 'pass'
    assert review.fully_correct is False
    assert review.domain_expertise_status == 'warn'
