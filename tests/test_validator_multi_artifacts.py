from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.patterns import (
    AggregatedHints,
    ExtractedSkillPatterns,
    ExtractionContext,
    PatternApplicability,
    PatternDownstreamHints,
    SkillPattern,
)
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.services.validator import run_validator


def _make_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='demo',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='references/usage.md', purpose='reference', source_basis=[]),
            PlannedFile(path='scripts/run.py', purpose='script', source_basis=[]),
        ],
    )


def _make_eval_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='demo',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='evals/trigger_eval.json', purpose='trigger eval', source_basis=[]),
            PlannedFile(path='evals/output_eval.json', purpose='output eval', source_basis=[]),
            PlannedFile(path='evals/benchmark.json', purpose='benchmark eval', source_basis=[]),
        ],
    )


def _make_patterns() -> ExtractedSkillPatterns:
    return ExtractedSkillPatterns(
        pattern_set_id='esp_test_validator_001',
        extraction=ExtractionContext(
            run_id='run-test-validator',
            created_at='2026-03-25T13:00:00+08:00',
            extractor_version='test',
        ),
        aggregated_hints=AggregatedHints(
            validator_defaults=['Check frontmatter quality beyond mere presence']
        ),
        patterns=[
            SkillPattern(
                pattern_id='pat_trigger_description_v1',
                pattern_type='trigger-description',
                status='accepted',
                title='Description should include capability and trigger',
                applicability=PatternApplicability(priority=90),
                downstream_hints=PatternDownstreamHints(
                    validator_checks=['description_mentions_capability_and_trigger']
                ),
                confidence=0.9,
            ),
            SkillPattern(
                pattern_id='pat_reference_split_v1',
                pattern_type='reference-split',
                status='accepted',
                title='Reference files should be linked and non-placeholder',
                applicability=PatternApplicability(priority=80),
                downstream_hints=PatternDownstreamHints(
                    validator_checks=[
                        'reference_files_are_linked_from_skill_md',
                        'reference_file_is_not_placeholder_heavy',
                    ]
                ),
                confidence=0.8,
            ),
        ],
    )


def test_validator_detects_empty_reference_and_script_files():
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='---\nname: demo\ndescription: demo\n---\n', content_type='text/markdown'),
            ArtifactFile(path='references/usage.md', content=''),
            ArtifactFile(path='scripts/run.py', content=''),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_skill_plan(),
        artifacts=artifacts,
    )

    assert 'empty_reference_file' in diagnostics.validation.repairable_issue_types
    assert 'empty_script_file' in diagnostics.validation.repairable_issue_types
    assert any('Empty reference file: references/usage.md' == item for item in diagnostics.validation.summary)
    assert any('Empty script file: scripts/run.py' == item for item in diagnostics.validation.summary)


def test_validator_detects_invalid_eval_scaffold_files():
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='---\nname: demo\ndescription: demo\n---\n', content_type='text/markdown'),
            ArtifactFile(path='evals/trigger_eval.json', content='{}', content_type='application/json'),
            ArtifactFile(path='evals/output_eval.json', content='', content_type='application/json'),
            ArtifactFile(
                path='evals/benchmark.json',
                content='{"skill_name":"demo","dimensions":[]}',
                content_type='application/json',
            ),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_eval_skill_plan(),
        artifacts=artifacts,
    )

    assert 'invalid_eval_scaffold' in diagnostics.validation.repairable_issue_types
    assert 'empty_eval_scaffold' in diagnostics.validation.repairable_issue_types
    assert any(
        'Invalid eval scaffold: evals/trigger_eval.json' == item
        for item in diagnostics.validation.summary
    )
    assert any(
        'Empty eval scaffold file: evals/output_eval.json' == item
        for item in diagnostics.validation.summary
    )
    assert any(
        note == "Validator eval diagnostics: empty=['evals/output_eval.json']; invalid=['evals/trigger_eval.json']"
        for note in diagnostics.notes
    )


def test_validator_detects_reference_structure_and_placeholder_issues():
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='---\nname: demo\ndescription: demo\n---\n\nSee `references/usage.md`.', content_type='text/markdown'),
            ArtifactFile(
                path='references/usage.md',
                content='# Usage\n\nReference placeholder generated by repair.\n',
                content_type='text/markdown',
            ),
            ArtifactFile(path='scripts/run.py', content='print("hi")\n'),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_skill_plan(),
        artifacts=artifacts,
    )

    assert 'reference_structure_incomplete' in diagnostics.validation.repairable_issue_types
    assert 'reference_placeholder_heavy' in diagnostics.validation.repairable_issue_types
    assert any('Reference structure incomplete: references/usage.md' == item for item in diagnostics.validation.summary)
    assert any('Reference placeholder heavy: references/usage.md' == item for item in diagnostics.validation.summary)


def test_validator_detects_script_placeholder_heavy_and_non_code_like_issues():
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='---\nname: demo\ndescription: demo\n---\n', content_type='text/markdown'),
            ArtifactFile(path='references/usage.md', content='## Overview\n\nOk\n\n## Key points\n\n- Ok\n', content_type='text/markdown'),
            ArtifactFile(
                path='scripts/run.py',
                content='# run.py\n# Placeholder helper script generated from planned candidate resource.\n',
                content_type='text/plain',
            ),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_skill_plan(),
        artifacts=artifacts,
    )

    assert 'script_placeholder_heavy' in diagnostics.validation.repairable_issue_types
    assert 'script_non_code_like' in diagnostics.validation.repairable_issue_types
    assert any('Script placeholder heavy: scripts/run.py' == item for item in diagnostics.validation.summary)
    assert any('Script non-code-like: scripts/run.py' == item for item in diagnostics.validation.summary)


def test_validator_detects_script_wrapper_like_issue():
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='---\nname: demo\ndescription: demo\n---\n', content_type='text/markdown'),
            ArtifactFile(path='references/usage.md', content='## Overview\n\nOk\n\n## Key points\n\n- Ok\n', content_type='text/markdown'),
            ArtifactFile(
                path='scripts/run.py',
                content=(
                    '# Run Script\n\n'
                    '- Source file: `scripts/run.py`\n\n'
                    '## Overview\n\n'
                    'This helper script runs the pipeline.\n'
                ),
                content_type='text/plain',
            ),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_skill_plan(),
        artifacts=artifacts,
    )

    assert 'script_wrapper_like' in diagnostics.validation.repairable_issue_types
    assert 'script_non_code_like' in diagnostics.validation.repairable_issue_types
    assert any('Script wrapper-like: scripts/run.py' == item for item in diagnostics.validation.summary)


def test_validator_emits_detailed_notes_for_reference_and_script_issues():
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='---\nname: demo\ndescription: demo\n---\n', content_type='text/markdown'),
            ArtifactFile(
                path='references/usage.md',
                content='# Usage\n\nReference placeholder generated by repair.\n',
                content_type='text/markdown',
            ),
            ArtifactFile(
                path='scripts/run.py',
                content='# run.py\n# Placeholder helper script generated from planned candidate resource.\n',
                content_type='text/plain',
            ),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_skill_plan(),
        artifacts=artifacts,
    )

    assert any(
        note == "Validator reference diagnostics: structure=['references/usage.md']; placeholder=['references/usage.md']"
        for note in diagnostics.notes
    )
    assert any(
        note == "Validator script diagnostics: placeholder=['scripts/run.py']; non_code_like=['scripts/run.py']"
        for note in diagnostics.notes
    )
    assert any(
        note == "Validator repair candidates: ['reference_placeholder_heavy', 'reference_structure_incomplete', 'script_non_code_like', 'script_placeholder_heavy', 'unreferenced_reference']"
        for note in diagnostics.notes
    )


def test_validator_consumes_extracted_patterns_for_description_and_reference_checks():
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='---\nname: demo\ndescription: Skill for docs\n---\n\nNo reference links here.\n',
                content_type='text/markdown',
            ),
            ArtifactFile(
                path='references/usage.md',
                content='# Usage\n\nReference placeholder generated by repair.\n',
                content_type='text/markdown',
            ),
            ArtifactFile(path='scripts/run.py', content='print("hi")\n', content_type='text/plain'),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_skill_plan(),
        artifacts=artifacts,
        extracted_patterns=_make_patterns(),
    )

    assert 'pattern_description_missing_capability_trigger' in diagnostics.validation.repairable_issue_types
    assert 'pattern_reference_link_missing' in diagnostics.validation.repairable_issue_types
    assert 'pattern_reference_placeholder_heavy' in diagnostics.validation.repairable_issue_types
    assert any(
        item == 'Pattern check failed: description should mention both capability and trigger'
        for item in diagnostics.validation.summary
    )
    assert any(
        item == 'Pattern check failed: reference files should be linked from SKILL.md'
        for item in diagnostics.validation.summary
    )
    assert any(
        item == 'Pattern check failed: reference files should not remain placeholder-heavy'
        for item in diagnostics.validation.summary
    )
    assert any(note == 'Validator consumed extracted_patterns=esp_test_validator_001' for note in diagnostics.notes)
    assert any(note.startswith('Validator aggregated defaults:') for note in diagnostics.notes)
    assert any(note.startswith('Pattern-aware validator checks requested:') for note in diagnostics.notes)


def test_validator_passes_pattern_description_check_when_frontmatter_is_trigger_aware():
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content=(
                    '---\n'
                    'name: demo\n'
                    'description: Audit and refine skill entrypoints. Use when Codex needs to review or improve AgentSkill triggering quality.\n'
                    '---\n\n'
                    'See `references/usage.md`.\n'
                ),
                content_type='text/markdown',
            ),
            ArtifactFile(
                path='references/usage.md',
                content='## Overview\n\nOk\n\n## Key points\n\n- Ok\n',
                content_type='text/markdown',
            ),
            ArtifactFile(path='scripts/run.py', content='print("hi")\n', content_type='text/plain'),
        ]
    )

    diagnostics = run_validator(
        request=None,
        repo_findings=None,
        skill_plan=_make_skill_plan(),
        artifacts=artifacts,
        extracted_patterns=_make_patterns(),
    )

    assert 'pattern_description_missing_capability_trigger' not in diagnostics.validation.repairable_issue_types
    assert any(
        note == 'Pattern-aware validator check passed: description_mentions_capability_and_trigger'
        for note in diagnostics.notes
    )
