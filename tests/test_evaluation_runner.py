from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.online import SkillReuseDecision
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.evaluation_runner import run_evaluations
from openclaw_skill_create.services.evaluation_scaffold import generate_eval_artifacts


def test_run_evaluations_scores_generated_skill_package():
    skill_plan = SkillPlan(
        skill_name='notion-capture-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='references/workflow.md', purpose='reference', source_basis=[]),
            PlannedFile(path='scripts/capture.py', purpose='script', source_basis=[]),
            PlannedFile(path='evals/trigger_eval.json', purpose='trigger eval', source_basis=[]),
            PlannedFile(path='evals/output_eval.json', purpose='output eval', source_basis=[]),
            PlannedFile(path='evals/benchmark.json', purpose='benchmark eval', source_basis=[]),
        ],
    )
    request = SkillCreateRequestV6(
        task='Capture architecture decisions into Notion with a reusable workflow',
        enable_eval_scaffold=True,
    )
    eval_artifacts = generate_eval_artifacts(
        request=request,
        skill_plan=skill_plan,
        reuse_decision=SkillReuseDecision(mode='adapt_existing', rationale=['Strong blueprint match']),
    )
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content=(
                    '---\n'
                    'name: notion-capture-skill\n'
                    'description: Capture architecture decisions into Notion. Use when Codex needs a reusable capture workflow for repo-backed knowledge.\n'
                    '---\n\n'
                    '# Notion Capture Skill\n\n'
                    'See `references/workflow.md` for the detailed flow.\n'
                ),
                content_type='text/markdown',
                generated_from=['repo_findings', 'skill_plan'],
            ),
            ArtifactFile(
                path='references/workflow.md',
                content='## Overview\n\nFollow the capture workflow.\n\n## Key points\n\n- Preserve repo context\n',
                content_type='text/markdown',
                generated_from=['repo_findings'],
            ),
            ArtifactFile(
                path='scripts/capture.py',
                content='def main() -> int:\n    return 0\n',
                content_type='text/plain',
                generated_from=['repo_findings'],
            ),
            *eval_artifacts,
        ]
    )

    report = run_evaluations(artifacts=artifacts)

    assert report is not None
    assert report.skill_name == 'notion-capture-skill'
    assert report.trigger_results
    assert all(item.passed for item in report.trigger_results)
    assert report.output_results
    assert report.output_results[0].passed is True
    assert {item.name for item in report.benchmark_results} >= {
        'trigger_accuracy',
        'task_alignment',
        'repo_grounding',
        'artifact_completeness',
        'maintainability',
        'adaptation_quality',
    }
    assert report.overall_score > 0.6


def test_run_evaluations_returns_none_when_no_eval_specs_exist():
    report = run_evaluations(
        artifacts=Artifacts(
            files=[
                ArtifactFile(
                    path='SKILL.md',
                    content='---\nname: demo\ndescription: Demo. Use when Codex needs demo help.\n---\n',
                    content_type='text/markdown',
                )
            ]
        )
    )

    assert report is None


def test_run_evaluations_does_not_trigger_on_negated_skill_name_reference():
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content=(
                    '---\n'
                    'name: keyword-research-skill\n'
                    'description: Research search demand and cluster keywords for SEO strategy. Use when Codex needs keyword research help.\n'
                    '---\n\n'
                    '# Keyword Research Skill\n'
                ),
                content_type='text/markdown',
                generated_from=['skill_plan'],
            ),
            ArtifactFile(
                path='evals/trigger_eval.json',
                content=(
                    '{\n'
                    '  "skill_name": "keyword-research-skill",\n'
                    '  "cases": [\n'
                    '    {\n'
                    '      "case_id": "trigger-negative-1",\n'
                    '      "query": "Fix an unrelated CSS spacing bug without using keyword-research-skill",\n'
                    '      "expected_trigger": false,\n'
                    '      "rationale": "Out of scope"\n'
                    '    }\n'
                    '  ]\n'
                    '}\n'
                ),
                content_type='application/json',
                generated_from=['request'],
            ),
        ]
    )

    report = run_evaluations(artifacts=artifacts)

    assert report is not None
    assert len(report.trigger_results) == 1
    assert report.trigger_results[0].predicted_trigger is False
    assert report.trigger_results[0].passed is True


def test_run_evaluations_reports_task_alignment_for_domain_specific_skill():
    skill_plan = SkillPlan(
        skill_name='keyword-research-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='references/keyword_clustering.md', purpose='reference', source_basis=[]),
            PlannedFile(path='evals/trigger_eval.json', purpose='trigger eval', source_basis=[]),
            PlannedFile(path='evals/output_eval.json', purpose='output eval', source_basis=[]),
            PlannedFile(path='evals/benchmark.json', purpose='benchmark eval', source_basis=[]),
        ],
    )
    request = SkillCreateRequestV6(
        task='Do SEO keyword research and cluster terms for a new landing page strategy',
        enable_eval_scaffold=True,
    )
    eval_artifacts = generate_eval_artifacts(
        request=request,
        skill_plan=skill_plan,
        reuse_decision=SkillReuseDecision(mode='adapt_existing', rationale=['Strong blueprint match']),
    )
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content=(
                    '---\n'
                    'name: keyword-research-skill\n'
                    'description: Research search demand and cluster keywords for SEO strategy. Use when Codex needs keyword research and landing page clustering.\n'
                    '---\n\n'
                    '# Keyword Research Skill\n\n'
                    'See `references/keyword_clustering.md` for the workflow.\n'
                ),
                content_type='text/markdown',
                generated_from=['repo_findings', 'skill_plan'],
            ),
            ArtifactFile(
                path='references/keyword_clustering.md',
                content='## Cluster terms\n',
                content_type='text/markdown',
                generated_from=['repo_findings'],
            ),
            *eval_artifacts,
        ]
    )

    report = run_evaluations(artifacts=artifacts)

    assert report is not None
    by_name = {item.name: item for item in report.benchmark_results}
    assert 'task_alignment' in by_name
    assert by_name['task_alignment'].score > 0.6
