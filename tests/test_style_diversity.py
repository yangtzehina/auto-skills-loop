from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.generator_fallback import fallback_generate_methodology_skill_md
from openclaw_skill_create.services.review import run_skill_quality_review
from openclaw_skill_create.services.style_diversity import build_skill_style_diversity_report
from openclaw_skill_create.services.validator_rules import run_rule_validation


class EmptyFindings:
    requirements = []


def _request(skill_name: str, task: str | None = None) -> SkillCreateRequestV6:
    return SkillCreateRequestV6(
        task=task or f'Create a game design methodology skill for {skill_name}.',
        skill_name_hint=skill_name,
        skill_archetype='methodology_guidance',
    )


def _plan(skill_name: str) -> SkillPlan:
    return SkillPlan(skill_name=skill_name, skill_archetype='methodology_guidance')


def _artifacts(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path='SKILL.md', content=content, content_type='text/markdown')])


def test_style_diversity_passes_profile_shaped_game_design_skill():
    request = _request('concept-to-mvp-pack')
    plan = _plan('concept-to-mvp-pack')
    content = fallback_generate_methodology_skill_md(
        skill_name='concept-to-mvp-pack',
        description='Turn a rough game concept into a scoped MVP pack.',
        task=request.task,
        references=[],
        scripts=[],
    )

    report = build_skill_style_diversity_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'pass'
    assert report.profile_specific_label_coverage >= 0.70
    assert report.fixed_renderer_phrase_count == 0


def test_style_diversity_rejects_universal_editorial_renderer_shell():
    request = _request('decision-loop-stress-test')
    plan = _plan('decision-loop-stress-test')
    content = """---
name: decision-loop-stress-test
description: Stress-test a decision loop.
---

# decision-loop-stress-test

Use this skill to turn a rough game-design request into a sharp, execution-facing decision artifact.

## Overview

Convert the prompt into concrete design judgments: what to test, what to cut, what to output, and what failure would mean.

## Default Workflow

### 1. Test the First-Hour Hook

- Do: Name the first hour decision loop and repeat trigger.
- Ask: Does the first hour create pressure?
- Output: First-hour hook: <fill in>
- Cut / Watch for: Avoid surface variation.
"""

    report = build_skill_style_diversity_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'fail'
    assert 'fixed_renderer_boilerplate' in report.blocking_issues
    assert 'profile_specific_labels_missing' in report.blocking_issues


def test_style_diversity_pairwise_shared_opening_and_labels_fail_known_profiles():
    request = _request('simulation-resource-loop-design')
    plan = _plan('simulation-resource-loop-design')
    content = fallback_generate_methodology_skill_md(
        skill_name='simulation-resource-loop-design',
        description='Design a simulation resource loop.',
        task=request.task,
        references=[],
        scripts=[],
    )

    report = build_skill_style_diversity_report(
        request=request,
        skill_plan=plan,
        artifacts=_artifacts(content),
        shared_opening_phrase_ratio=0.92,
        shared_step_label_ratio_value=0.80,
    )

    assert report.status == 'fail'
    assert 'shared_opening_phrase' in report.blocking_issues
    assert 'shared_step_labels' in report.blocking_issues


def test_style_diversity_failure_blocks_fully_correct():
    request = _request('concept-to-mvp-pack')
    plan = _plan('concept-to-mvp-pack')
    content = """---
name: concept-to-mvp-pack
description: Turn a rough game concept into a scoped MVP pack.
---

# concept-to-mvp-pack

Use this skill to turn a rough game-design request into a sharp, execution-facing decision artifact.

## Overview

Convert the prompt into concrete design judgments: what to test, what to cut, what to output, and what failure would mean.

## When to Use
- Use when an agent needs a method.

## When Not to Use
- Do not use when no decision is needed.

## Inputs
- Game idea and constraints.

## Default Workflow

### 1. Define the Core Validation Question
- Do: Name the validation question.
- Ask: Does the question matter?
- Output: Core validation question.
- Cut / Watch for: Avoid scope creep.

## Output Format
- Core Validation Question:

## Quality Checks
- Check that the validation question can fail.

## Common Pitfalls
- Scope creep.
"""
    artifacts = _artifacts(content)

    diagnostics = run_rule_validation(
        request=request,
        repo_findings=EmptyFindings(),
        skill_plan=plan,
        artifacts=artifacts,
    )
    review = run_skill_quality_review(
        repo_findings=EmptyFindings(),
        skill_plan=plan,
        artifacts=artifacts,
        diagnostics=diagnostics,
    )

    assert diagnostics.style_diversity is not None
    assert diagnostics.style_diversity.status == 'fail'
    assert review.fully_correct is False
    assert review.style_diversity_status == 'fail'


def test_unknown_methodology_style_warns_not_release_ready():
    request = _request(
        'research-memo-synthesis',
        'Create a writing methodology skill for research memo synthesis using `claim`, `source contrast`, and `decision implication`.',
    )
    plan = _plan('research-memo-synthesis')
    content = fallback_generate_methodology_skill_md(
        skill_name='research-memo-synthesis',
        description='Synthesize a research memo.',
        task=request.task,
        references=[],
        scripts=[],
    )

    report = build_skill_style_diversity_report(request=request, skill_plan=plan, artifacts=_artifacts(content))

    assert report.status == 'warn'
    assert 'expert_style_profile_missing' in report.warning_issues
