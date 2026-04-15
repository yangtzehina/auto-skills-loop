from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.online import SkillBlueprint, SkillInterfaceMetadata, SkillProvenance
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.requirements import SkillRequirement
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.models.runtime import EvolutionPlan
from openclaw_skill_create.services.generator_resources import (
    generate_metadata_artifacts,
    generate_reference_artifacts,
    generate_script_artifacts,
)


def make_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='sample-python-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='references/workflows.md', purpose='details', source_basis=[]),
            PlannedFile(path='scripts/run_analysis.py', purpose='script', source_basis=[]),
        ],
    )


def test_generate_reference_artifacts_uses_structured_sections():
    repo_context = {
        'selected_files': [
            {
                'path': 'references/workflows.md',
                'preview': '# Workflow details\n\nDo A then B.\n\nUse CI before release.',
                'repo_path': '/tmp/repo',
            }
        ]
    }
    artifacts = generate_reference_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert artifacts[0].path == 'references/workflows.md'
    assert artifacts[0].content.startswith('# Workflows')
    assert '- Source repo: `/tmp/repo`' in artifacts[0].content
    assert '- Source file: `references/workflows.md`' in artifacts[0].content
    assert '## Overview' in artifacts[0].content
    assert '## Key points' in artifacts[0].content
    assert '## Snippet' in artifacts[0].content
    assert '- Do A then B.' in artifacts[0].content
    assert 'Use CI before release.' in artifacts[0].content


def test_generate_reference_artifacts_falls_back_to_structured_placeholder():
    repo_context = {'selected_files': [{'path': 'references/workflows.md', 'preview': ''}]}
    artifacts = generate_reference_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert '## Overview' in artifacts[0].content
    assert '## Key points' in artifacts[0].content
    assert 'Reference placeholder derived from planned candidate resource.' in artifacts[0].content


def test_generate_script_artifacts_preserves_real_script_preview_verbatim():
    repo_context = {
        'selected_files': [
            {
                'path': 'scripts/run_analysis.py',
                'preview': 'def main():\n    print("hi")\n\n\nif __name__ == "__main__":\n    main()\n',
            }
        ]
    }
    artifacts = generate_script_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert artifacts[0].path == 'scripts/run_analysis.py'
    assert artifacts[0].content == 'def main():\n    print("hi")\n\n\nif __name__ == "__main__":\n    main()\n'


def test_generate_script_artifacts_extracts_fenced_code_from_wrapped_preview():
    repo_context = {
        'selected_files': [
            {
                'path': 'scripts/run_analysis.py',
                'preview': (
                    '# Script preview\n\n'
                    '- Source file: `scripts/run_analysis.py`\n\n'
                    '```python\n'
                    'import sys\n'
                    'print(sys.argv[1])\n'
                    '```\n'
                ),
            }
        ]
    }
    artifacts = generate_script_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert artifacts[0].content == 'import sys\nprint(sys.argv[1])\n'


def test_generate_script_artifacts_rejects_obvious_wrapper_preview():
    repo_context = {
        'selected_files': [
            {
                'path': 'scripts/run_analysis.py',
                'preview': (
                    '# Run Analysis\n\n'
                    '- Source file: `scripts/run_analysis.py`\n\n'
                    '## Overview\n\n'
                    'This helper script runs the analysis pipeline.\n'
                ),
            }
        ]
    }
    artifacts = generate_script_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert '# run_analysis.py' in artifacts[0].content
    assert 'Placeholder helper script generated from planned candidate resource.' in artifacts[0].content


def test_generate_script_artifacts_rejects_markdown_notes_preview():
    repo_context = {
        'selected_files': [
            {
                'path': 'scripts/run_analysis.py',
                'preview': (
                    '# Usage\n\n'
                    '- Run the analysis script locally\n'
                    '- Check the generated report before sharing\n'
                ),
            }
        ]
    }
    artifacts = generate_script_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert artifacts[0].content.startswith('# run_analysis.py\n')
    assert 'Placeholder helper script generated from planned candidate resource.' in artifacts[0].content
    assert '- Run the analysis script locally' not in artifacts[0].content


def test_generate_script_artifacts_prefers_full_source_file_over_preview(tmp_path):
    script_path = tmp_path / 'run_analysis.py'
    script_path.write_text('def main():\n    return 1\n', encoding='utf-8')
    repo_context = {
        'selected_files': [
            {
                'path': 'scripts/run_analysis.py',
                'absolute_path': str(script_path),
                'preview': '# Preview\n\nNot the actual script.',
            }
        ]
    }
    artifacts = generate_script_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert artifacts[0].content == 'def main():\n    return 1\n'


def test_generate_script_artifacts_falls_back_to_placeholder_when_empty():
    repo_context = {
        'selected_files': [
            {'path': 'scripts/run_analysis.py', 'preview': ''}
        ]
    }
    artifacts = generate_script_artifacts(repo_context=repo_context, skill_plan=make_plan())
    assert len(artifacts) == 1
    assert '# run_analysis.py' in artifacts[0].content
    assert 'Placeholder helper script generated from planned candidate resource.' in artifacts[0].content


def test_generate_metadata_artifacts_seed_openai_yaml_and_meta_json():
    request = SkillCreateRequestV6(
        task='generate',
        repo_paths=['/tmp/repo'],
        online_skill_blueprints=[
            SkillBlueprint(
                blueprint_id='openai-notion__blueprint',
                name='notion-knowledge-capture',
                description='Capture conversations into structured Notion pages',
                interface=SkillInterfaceMetadata(
                    display_name='Notion Knowledge Capture',
                    short_description='Capture conversations into structured Notion pages',
                    default_prompt='Capture this conversation into structured Notion pages.',
                ),
                provenance=SkillProvenance(
                    source_type='official',
                    ecosystem='codex',
                    repo_full_name='openai/skills',
                    ref='main',
                    skill_path='skills/.curated/notion-knowledge-capture',
                    skill_url='https://github.com/openai/skills/blob/main/skills/.curated/notion-knowledge-capture/SKILL.md',
                ),
            )
        ],
    )
    plan = SkillPlan(
        skill_name='notion-capture-skill',
        requirements=[
            SkillRequirement(
                requirement_id='docs-readme',
                statement='Carry the repo guidance from `README.md` into the generated skill references and instructions.',
                evidence_paths=['README.md'],
                source_kind='doc',
                priority=70,
                satisfied_by=['references/README.md', 'SKILL.md'],
            )
        ],
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='agents/openai.yaml', purpose='ui metadata', source_basis=[]),
            PlannedFile(path='_meta.json', purpose='structured metadata', source_basis=[]),
        ],
    )

    artifacts = generate_metadata_artifacts(request=request, skill_plan=plan)
    contents = {artifact.path: artifact.content for artifact in artifacts}
    meta = json.loads(contents['_meta.json'])

    assert 'display_name: "Notion Knowledge Capture"' in contents['agents/openai.yaml']
    assert meta['skill_name'] == 'notion-capture-skill'
    assert meta['repo_grounded'] is True
    assert meta['online_blueprint_sources'] == [
        'https://github.com/openai/skills/blob/main/skills/.curated/notion-knowledge-capture/SKILL.md'
    ]
    assert meta['requirements'][0]['requirement_id'] == 'docs-readme'
    assert meta['requirements'][0]['satisfied_by'] == ['references/README.md', 'SKILL.md']
    assert meta['lineage']['skill_id'].startswith('notion-capture-skill__v0_')
    assert meta['lineage']['history'][0]['event'] == 'generated'


def test_generate_metadata_artifacts_increments_lineage_version_for_patch(tmp_path: Path):
    parent_skill_dir = tmp_path / 'sample-python-skill'
    parent_skill_dir.mkdir()
    (parent_skill_dir / '_meta.json').write_text(
        json.dumps(
            {
                'lineage': {
                    'skill_id': 'sample-python-skill__v2_deadbeef',
                    'version': 2,
                    'parent_skill_id': 'sample-python-skill__v1_cafebabe',
                    'content_sha': 'deadbeef00aa',
                    'quality_score': 0.4,
                    'history': [
                        {
                            'event': 'generated',
                            'skill_id': 'sample-python-skill__v2_deadbeef',
                            'version': 2,
                            'parent_skill_id': 'sample-python-skill__v1_cafebabe',
                            'content_sha': 'deadbeef00aa',
                            'quality_score': 0.4,
                            'summary': 'Parent lineage entry.',
                        }
                    ],
                }
            }
        ),
        encoding='utf-8',
    )

    request = SkillCreateRequestV6(
        task='patch runtime guidance',
        parent_skill_id='sample-python-skill__v2_deadbeef',
        repo_paths=[str(parent_skill_dir)],
        runtime_evolution_plan=EvolutionPlan(
            run_id='run-patch',
            skill_id='sample-python-skill__v2_deadbeef',
            action='patch_current',
            parent_skill_id='sample-python-skill__v2_deadbeef',
            reason='Repeated runtime misalignment.',
            summary='Patch the current skill to address runtime misalignment.',
        ),
    )
    plan = SkillPlan(
        skill_name='sample-python-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='_meta.json', purpose='structured metadata', source_basis=[]),
        ],
    )

    artifacts = generate_metadata_artifacts(request=request, skill_plan=plan)
    meta = json.loads(next(item.content for item in artifacts if item.path == '_meta.json'))

    assert meta['lineage']['parent_skill_id'] == 'sample-python-skill__v2_deadbeef'
    assert meta['lineage']['version'] == 3
    assert len(meta['lineage']['history']) == 2
    assert meta['lineage']['history'][0]['event'] == 'generated'
    assert meta['lineage']['history'][1]['event'] == 'patch_current'
