from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.diagnostics import Diagnostics, ValidationResult
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.review import RepairSuggestion, SkillQualityReview
from openclaw_skill_create.services.repair import run_repair


def make_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='sample-python-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=['repo_findings']),
            PlannedFile(path='references/usage.md', purpose='details', source_basis=['repo_findings.docs']),
        ],
    )


def test_run_repair_fixes_frontmatter_and_reference_navigation():
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='# sample-python-skill\n\nBody only.\n',
                content_type='text/markdown',
            ),
            ArtifactFile(
                path='references/usage.md',
                content='details',
            ),
        ]
    )
    diagnostics = Diagnostics(
        validation=ValidationResult(
            frontmatter_valid=False,
            skill_md_within_budget=True,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=['references/usage.md'],
            unsupported_claims_found=False,
            repairable_issue_types=['invalid_frontmatter', 'unreferenced_reference'],
        )
    )

    result = run_repair(
        artifacts=artifacts,
        diagnostics=diagnostics,
        skill_plan=make_skill_plan(),
        skill_name='sample-python-skill',
        description='Repo-aware skill for sample-python-skill',
        max_skill_md_lines=300,
    )

    repaired = next(file for file in result.repaired_artifacts.files if file.path == 'SKILL.md')
    assert result.applied is True
    assert repaired.content.startswith('---\nname: sample-python-skill\ndescription: Repo-aware skill for sample-python-skill\n---')
    assert '`references/usage.md`' in repaired.content
    assert repaired.status == 'repaired'


def test_run_repair_drops_unexpected_files_and_trims_budget():
    long_body = '\n'.join(f'line {i}' for i in range(50))
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='---\nname: x\ndescription: y\n---\n\n' + long_body + '\n', content_type='text/markdown'),
            ArtifactFile(path='junk.tmp', content='remove me'),
        ]
    )
    diagnostics = Diagnostics(
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=False,
            planned_files_present=True,
            unnecessary_files_present=True,
            unreferenced_reference_files=[],
            unsupported_claims_found=False,
            repairable_issue_types=['skill_md_over_budget', 'unexpected_file'],
        )
    )

    result = run_repair(
        artifacts=artifacts,
        diagnostics=diagnostics,
        skill_plan=SkillPlan(skill_name='x', files_to_create=[PlannedFile(path='SKILL.md', purpose='entry', source_basis=[])]),
        skill_name='x',
        description='Repo-aware skill for x',
        max_skill_md_lines=10,
    )

    paths = {file.path for file in result.repaired_artifacts.files}
    repaired = next(file for file in result.repaired_artifacts.files if file.path == 'SKILL.md')
    assert 'junk.tmp' not in paths
    assert len(repaired.content.splitlines()) <= 10


def test_run_repair_consumes_structured_review_suggestions():
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='---\nname: sample-python-skill\ndescription: Repo-aware skill for sample-python-skill\n---\n\n# sample-python-skill\n',
                content_type='text/markdown',
            ),
            ArtifactFile(
                path='references/usage.md',
                content='# Usage\n\nReview `references/usage.md` for implementation-specific details.\n',
                content_type='text/markdown',
            ),
        ]
    )
    diagnostics = Diagnostics(
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=True,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=[],
            unsupported_claims_found=False,
            repairable_issue_types=[],
        )
    )

    result = run_repair(
        artifacts=artifacts,
        diagnostics=diagnostics,
        skill_plan=make_skill_plan(),
        skill_name='sample-python-skill',
        description='Repo-aware skill for sample-python-skill',
        max_skill_md_lines=300,
        quality_review=SkillQualityReview(
            skill_name='sample-python-skill',
            repair_suggestions=[
                RepairSuggestion(
                    issue_type='reference_structure_incomplete',
                    instruction='Strengthen repo-grounded reference coverage.',
                    target_paths=['references/usage.md'],
                    priority=80,
                )
            ],
        ),
    )

    repaired = next(file for file in result.repaired_artifacts.files if file.path == 'references/usage.md')
    assert result.applied is True
    assert '## Overview' in repaired.content
    assert '## Key points' in repaired.content


def test_run_repair_description_only_scope_only_updates_frontmatter():
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='---\nname: sample-python-skill\ndescription: Old description\n---\n\n# sample-python-skill\n\nBody stays put.\n',
                content_type='text/markdown',
            ),
            ArtifactFile(
                path='references/usage.md',
                content='placeholder details',
                content_type='text/markdown',
            ),
        ]
    )
    diagnostics = Diagnostics(
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=True,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=['references/usage.md'],
            unsupported_claims_found=False,
            repairable_issue_types=['pattern_description_missing_capability_trigger'],
        )
    )

    result = run_repair(
        artifacts=artifacts,
        diagnostics=diagnostics,
        skill_plan=make_skill_plan(),
        skill_name='sample-python-skill',
        description='Repo-aware skill for sample-python-skill',
        max_skill_md_lines=300,
        quality_review=SkillQualityReview(
            skill_name='sample-python-skill',
            repair_suggestions=[
                RepairSuggestion(
                    issue_type='pattern_description_missing_capability_trigger',
                    instruction='Tighten the description so retrieval and triggering align.',
                    target_paths=['SKILL.md'],
                    priority=90,
                    repair_scope='description_only',
                )
            ],
        ),
    )

    repaired_skill = next(file for file in result.repaired_artifacts.files if file.path == 'SKILL.md')
    repaired_reference = next(file for file in result.repaired_artifacts.files if file.path == 'references/usage.md')
    assert result.applied is True
    assert 'description: Repo-aware skill for sample-python-skill' in repaired_skill.content
    assert repaired_reference.content == 'placeholder details'
