from __future__ import annotations

import json

from openclaw_skill_create.models.online import SkillReuseDecision
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.generator import run_generator


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


def test_run_generator_returns_artifacts():
    request = SkillCreateRequestV6(task='generate', enable_llm_skill_md=False)
    artifacts = run_generator(
        request=request,
        repo_context={'files': []},
        repo_findings={'repos': []},
        skill_plan=make_plan(),
    )

    assert artifacts.files
    assert artifacts.files[0].path == 'SKILL.md'


def test_run_generator_returns_eval_artifacts_when_planned():
    plan = SkillPlan(
        skill_name='sample-python-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='Top-level skill entry', source_basis=['repo_findings']),
            PlannedFile(path='evals/trigger_eval.json', purpose='trigger checks', source_basis=[]),
            PlannedFile(path='evals/output_eval.json', purpose='output checks', source_basis=[]),
            PlannedFile(path='evals/benchmark.json', purpose='benchmark checks', source_basis=[]),
        ],
    )
    request = SkillCreateRequestV6(task='generate', enable_llm_skill_md=False, enable_eval_scaffold=True)
    artifacts = run_generator(
        request=request,
        repo_context={'files': []},
        repo_findings={'repos': []},
        skill_plan=plan,
        reuse_decision=SkillReuseDecision(mode='generate_fresh'),
    )

    contents = {file.path: file.content for file in artifacts.files}
    assert 'evals/trigger_eval.json' in contents
    assert 'evals/output_eval.json' in contents
    assert 'evals/benchmark.json' in contents
    assert json.loads(contents['evals/output_eval.json'])['skill_name'] == 'sample-python-skill'
