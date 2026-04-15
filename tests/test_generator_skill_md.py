from __future__ import annotations

from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.generator_skill_md import generate_skill_md_artifact


def make_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='sample-python-skill',
        files_to_create=[
            PlannedFile(
                path='SKILL.md',
                purpose='Top-level skill entry',
                source_basis=['repo_findings'],
            ),
            PlannedFile(
                path='references/workflows.md',
                purpose='Detailed workflow notes',
                source_basis=['repo_findings.workflows'],
            ),
            PlannedFile(
                path='scripts/run_analysis.py',
                purpose='Reusable helper script',
                source_basis=['repo_findings.scripts'],
            ),
        ],
    )


def test_generate_skill_md_artifact_uses_fallback_when_llm_disabled():
    request = SkillCreateRequestV6(
        task='Build a repo-grounded skill for calibrating astronomical FITS frames with Astropy.',
        enable_llm_skill_md=False,
    )
    artifact = generate_skill_md_artifact(
        request=request,
        repo_context={'files': []},
        repo_findings={'repos': []},
        skill_plan=make_plan(),
    )

    assert artifact.path == 'SKILL.md'
    assert 'use when' in artifact.content.lower()
    assert 'fits frames with astropy' in artifact.content.lower()
    assert '`references/workflows.md`' in artifact.content
    assert '`scripts/run_analysis.py`' in artifact.content


def test_generate_skill_md_artifact_uses_llm_when_enabled():
    request = SkillCreateRequestV6(task='generate', enable_llm_skill_md=True)

    def fake_runner(messages, model):
        return '''
---
name: sample-python-skill
description: Repo-aware skill for sample-python-skill
---

# sample-python-skill

Use this skill when the repo-grounded workflow matches the task.

## References

- See `references/workflows.md` for more detail.
'''

    artifact = generate_skill_md_artifact(
        request=request,
        repo_context={'files': []},
        repo_findings={'repos': []},
        skill_plan=make_plan(),
        llm_runner=fake_runner,
        model='codex-vip/gpt-5.4',
    )

    assert artifact.path == 'SKILL.md'
    assert artifact.generated_from[-1] == 'llm'
    assert 'name: sample-python-skill' in artifact.content


def test_generate_skill_md_artifact_fallback_description_is_trigger_aware():
    request = SkillCreateRequestV6(
        task='Build a repo-grounded skill for calibrating astronomical FITS frames with Astropy, tracking bias and flat-field reduction notes.',
        enable_llm_skill_md=False,
    )
    artifact = generate_skill_md_artifact(
        request=request,
        repo_context={'files': []},
        repo_findings={'repos': []},
        skill_plan=make_plan(),
    )

    assert 'description:' in artifact.content
    assert 'use when a repo-backed task needs' in artifact.content.lower()
    assert 'calibrating astronomical fits frames with astropy' in artifact.content.lower()
