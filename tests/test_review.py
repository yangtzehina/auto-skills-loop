from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.diagnostics import Diagnostics, ValidationResult
from openclaw_skill_create.models.evaluation import EvaluationRunReport
from openclaw_skill_create.models.findings import RepoFindings
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.requirements import SkillRequirement
from openclaw_skill_create.models.security import SecurityAuditReport
from openclaw_skill_create.services.review import run_skill_quality_review


def test_run_skill_quality_review_reports_requirement_results_and_suggestions():
    repo_findings = RepoFindings(
        requirements=[
            SkillRequirement(
                requirement_id='script-runner',
                statement='Provide a deterministic helper aligned with `scripts/run_analysis.py`.',
                evidence_paths=['scripts/run_analysis.py'],
                source_kind='script',
                priority=80,
                satisfied_by=['scripts/run_analysis.py', 'SKILL.md'],
            ),
            SkillRequirement(
                requirement_id='docs-guide',
                statement='Carry the repo guidance from `README.md` into the generated skill references and instructions.',
                evidence_paths=['README.md'],
                source_kind='doc',
                priority=70,
                satisfied_by=['references/README.md', 'SKILL.md'],
            ),
        ]
    )
    skill_plan = SkillPlan(
        skill_name='demo-skill',
        requirements=repo_findings.requirements,
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='references/README.md', purpose='ref', source_basis=[]),
            PlannedFile(path='scripts/run_analysis.py', purpose='script', source_basis=[]),
        ],
    )
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='---\nname: demo-skill\ndescription: Analyze repo workflows. Use when Codex needs repo-grounded guidance.\n---\n\n# Demo\n',
                content_type='text/markdown',
            ),
            ArtifactFile(
                path='references/README.md',
                content='# Readme\n\n- Source file: `references/README.md`\n\n## Overview\n\nRepo guide.\n\n## Key points\n\n- Step one.\n',
                content_type='text/markdown',
            ),
        ]
    )
    diagnostics = Diagnostics(
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=True,
            planned_files_present=True,
            repairable_issue_types=[],
        )
    )

    review = run_skill_quality_review(
        repo_findings=repo_findings,
        skill_plan=skill_plan,
        artifacts=artifacts,
        diagnostics=diagnostics,
        evaluation_report=EvaluationRunReport(skill_name='demo-skill', overall_score=0.82),
    )

    results = {item.requirement_id: item for item in review.requirement_results}
    assert results['docs-guide'].satisfied is True
    assert results['script-runner'].satisfied is False
    assert review.repair_suggestions
    assert review.repair_suggestions[0].issue_type == 'missing_planned_file'
    assert 'scripts/run_analysis.py' in review.repair_suggestions[0].target_paths
    assert review.fully_correct is False


def test_run_skill_quality_review_passes_when_requirements_and_eval_are_strong():
    requirements = [
        SkillRequirement(
            requirement_id='repo-docs',
            statement='Carry the repo guidance from `README.md` into the generated skill references and instructions.',
            evidence_paths=['README.md'],
            source_kind='doc',
            priority=70,
            satisfied_by=['references/README.md', 'SKILL.md'],
        )
    ]
    review = run_skill_quality_review(
        repo_findings=RepoFindings(requirements=requirements),
        skill_plan=SkillPlan(
            skill_name='demo-skill',
            requirements=requirements,
            files_to_create=[
                PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
                PlannedFile(path='references/README.md', purpose='ref', source_basis=[]),
            ],
        ),
        artifacts=Artifacts(
            files=[
                ArtifactFile(
                    path='SKILL.md',
                    content=(
                        '---\nname: demo-skill\ndescription: Capture repo guidance. Use when Codex needs repo-grounded instructions.\n---\n\n'
                        '# Demo\n\n'
                        'Use this skill when the repo guidance applies to the current task.\n\n'
                        '## When to Use\n\n'
                        '- The task needs repo-grounded instructions.\n\n'
                        '## Workflow\n\n'
                        '1. Read `references/README.md` before making repo-specific claims.\n'
                        '2. Apply the relevant workflow in small steps.\n'
                        '3. Report the files or assumptions used.\n\n'
                        '## Output Format\n\n'
                        '- State the workflow path.\n'
                        '- Summarize verification status.\n'
                    ),
                    content_type='text/markdown',
                ),
                ArtifactFile(
                    path='references/README.md',
                    content='# Readme\n\n- Source file: `references/README.md`\n\n## Overview\n\nRepo guide.\n\n## Key points\n\n- Step one.\n',
                    content_type='text/markdown',
                ),
            ]
        ),
        diagnostics=Diagnostics(validation=ValidationResult(frontmatter_valid=True, skill_md_within_budget=True, planned_files_present=True)),
        evaluation_report=EvaluationRunReport(skill_name='demo-skill', overall_score=0.91),
    )

    assert review.fully_correct is True
    assert review.repair_suggestions == []
    assert review.confidence > 0.9


def test_run_skill_quality_review_includes_security_summary_and_not_fully_correct_on_medium_risk():
    review = run_skill_quality_review(
        repo_findings=RepoFindings(requirements=[]),
        skill_plan=SkillPlan(skill_name='demo-skill', files_to_create=[PlannedFile(path='SKILL.md', purpose='entry', source_basis=[])]),
        artifacts=Artifacts(
            files=[
                ArtifactFile(
                    path='SKILL.md',
                    content='---\nname: demo-skill\ndescription: Capture repo guidance. Use when Codex needs repo-grounded instructions.\n---\n\n# Demo\n',
                    content_type='text/markdown',
                )
            ]
        ),
        diagnostics=Diagnostics(
            validation=ValidationResult(frontmatter_valid=True, skill_md_within_budget=True, planned_files_present=True),
            security_audit=SecurityAuditReport(
                rating='MEDIUM',
                trust_tier=4,
                summary=['Security audit rating=MEDIUM; trust_tier=4'],
                recommended_action='caution',
                blocking_findings_count=0,
                top_security_categories=['credential_access'],
            ),
        ),
        evaluation_report=EvaluationRunReport(skill_name='demo-skill', overall_score=0.91),
    )

    assert review.fully_correct is False
    assert 'security_rating=MEDIUM' in review.summary
    assert 'security_blocking_findings=0' in review.summary
