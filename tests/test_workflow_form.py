from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.expert_dna import render_expert_dna_skill_md
from openclaw_skill_create.services.orchestrator import derive_validation_severity
from openclaw_skill_create.services.review import run_skill_quality_review
from openclaw_skill_create.services.validator import run_validator
from openclaw_skill_create.services.workflow_form import build_skill_workflow_form_report


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


def test_workflow_form_passes_execution_spine_profile():
    content = render_expert_dna_skill_md(
        skill_name='decision-loop-stress-test',
        description='Stress-test a game decision loop.',
        task='Create a decision-loop-stress-test skill.',
        references=[],
        scripts=[],
    )
    assert content is not None

    report = build_skill_workflow_form_report(
        request=_request('decision-loop-stress-test'),
        skill_plan=_plan('decision-loop-stress-test'),
        artifacts=_artifacts(content),
    )

    assert report.status == 'pass'
    assert report.workflow_surface == 'execution_spine'
    assert report.numbered_spine_count >= 5
    assert report.imperative_move_recall >= 0.85
    assert report.named_block_dominance_ratio == 0.0
    assert report.output_block_separation is True


def test_workflow_form_rejects_named_blocks_replacing_execution_spine():
    content = """---
name: concept-to-mvp-pack
description: Shape a concept into an MVP pack.
---

# concept-to-mvp-pack

## Default Workflow
### Core Validation Question
- Decision: What can fail?
### Smallest Honest Loop
- Decision: What is playable now?
### Feature Cut
- Decision: What gets cut?
### Minimum Content Package
- Decision: What content proves the loop?
### Out of Scope
- Decision: What stays out?

## Output Format
```markdown
## Core Validation Question
## Smallest Honest Loop
## Feature Cut
```
"""

    report = build_skill_workflow_form_report(
        request=_request('concept-to-mvp-pack'),
        skill_plan=_plan('concept-to-mvp-pack'),
        artifacts=_artifacts(content),
    )

    assert report.status == 'fail'
    assert 'numbered_workflow_spine_missing' in report.blocking_issues
    assert 'workflow_named_blocks_dominate' in report.blocking_issues
    assert 'output_blocks_mixed_into_workflow' in report.blocking_issues


def test_workflow_form_rejects_decision_loop_without_phase_execution_order():
    content = """---
name: decision-loop-stress-test
description: Stress-test a game decision loop.
---

# decision-loop-stress-test

## Default Workflow

1. **Current Loop Shape**
   - Decision: What is the loop?
   - Do: Describe it.
   - Output: Loop summary.
   - Failure Signal: Too vague.
   - Fix: Rewrite it.
2. **Loop Inputs**
   - Decision: What inputs exist?
   - Do: List them.
   - Output: Input summary.
   - Failure Signal: Too vague.
   - Fix: Rewrite it.
3. **Loop Rewards**
   - Decision: What rewards exist?
   - Do: List them.
   - Output: Reward summary.
   - Failure Signal: Too vague.
   - Fix: Rewrite it.
4. **Loop Risks**
   - Decision: What risks exist?
   - Do: List them.
   - Output: Risk summary.
   - Failure Signal: Too vague.
   - Fix: Rewrite it.
5. **Loop Notes**
   - Decision: What else matters?
   - Do: Summarize it.
   - Output: Notes.
   - Failure Signal: Too vague.
   - Fix: Rewrite it.

## Output Format
- Current Loop Shape:
"""

    report = build_skill_workflow_form_report(
        request=_request('decision-loop-stress-test'),
        skill_plan=_plan('decision-loop-stress-test'),
        artifacts=_artifacts(content),
    )

    assert report.status == 'fail'
    assert 'imperative_workflow_moves_missing' in report.blocking_issues


def test_workflow_form_passes_hybrid_resource_profile_with_analysis_blocks():
    content = render_expert_dna_skill_md(
        skill_name='simulation-resource-loop-design',
        description='Design a simulation resource loop.',
        task='Create a simulation-resource-loop-design skill.',
        references=[],
        scripts=[],
    )
    assert content is not None

    report = build_skill_workflow_form_report(
        request=_request('simulation-resource-loop-design'),
        skill_plan=_plan('simulation-resource-loop-design'),
        artifacts=_artifacts(content),
    )

    assert report.status == 'pass'
    assert report.workflow_surface == 'hybrid'
    assert report.numbered_spine_count >= 5
    assert report.structural_block_count >= 3
    assert 'Variable Web' in report.structural_blocks


def test_workflow_form_failure_blocks_fully_correct():
    content = """---
name: concept-to-mvp-pack
description: Shape a concept into an MVP pack.
---

# concept-to-mvp-pack

## Overview
Mention validation question, smallest honest loop, feature cut, content scope, out-of-scope, and MVP package.

## Default Workflow
### Core Validation Question
- Decision: validation question can fail.
### Smallest Honest Loop
- Decision: smallest honest loop is playable.
### Feature Cut
- Decision: feature cut removes attractive work.

## Output Format
- Core Validation Question:
- Smallest Honest Loop:
- Feature Cut:

## Common Pitfalls
- Scope creep.
"""
    diagnostics = run_validator(
        request=_request('concept-to-mvp-pack'),
        repo_findings={},
        skill_plan=_plan('concept-to-mvp-pack'),
        artifacts=_artifacts(content),
    )
    review = run_skill_quality_review(
        repo_findings={},
        skill_plan=_plan('concept-to-mvp-pack'),
        artifacts=_artifacts(content),
        diagnostics=diagnostics,
    )

    assert diagnostics.workflow_form is not None
    assert diagnostics.workflow_form.status == 'fail'
    assert derive_validation_severity(diagnostics) == 'fail'
    assert review.fully_correct is False
    assert review.workflow_form_status == 'fail'
