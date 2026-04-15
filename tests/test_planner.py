from __future__ import annotations

from openclaw_skill_create.models.findings import CandidateResources, RepoFinding, RepoFindings
from openclaw_skill_create.models.online import (
    SkillBlueprint,
    SkillBlueprintArtifact,
    SkillInterfaceMetadata,
    SkillProvenance,
    SkillReuseDecision,
)
from openclaw_skill_create.models.patterns import (
    AggregatedHints,
    ExtractedSkillPatterns,
    ExtractionContext,
    SkillPattern,
    PatternApplicability,
    PatternDownstreamHints,
    PatternFileShape,
    PatternSummary,
)
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.models.requirements import SkillRequirement
from openclaw_skill_create.services.planner import run_planner


class DummyRepoFindings:
    repos = []


def make_extracted_patterns() -> ExtractedSkillPatterns:
    return ExtractedSkillPatterns(
        pattern_set_id='esp_test_planner_001',
        extraction=ExtractionContext(
            run_id='run-test',
            created_at='2026-03-25T13:00:00+08:00',
            extractor_version='test',
        ),
        summary=PatternSummary(
            recommended_defaults={'skill_md_max_lines': '220'}
        ),
        aggregated_hints=AggregatedHints(
            planner_defaults=['Prefer SKILL.md + references/ over a monolithic SKILL.md']
        ),
        patterns=[
            SkillPattern(
                pattern_id='pat_reference_split_v1',
                pattern_type='reference-split',
                status='accepted',
                title='Split long detail into references',
                applicability=PatternApplicability(priority=80),
                file_shape=PatternFileShape(
                    required_files=['SKILL.md'],
                    optional_files=['references/overview.md'],
                    content_budget_hint=220,
                ),
                downstream_hints=PatternDownstreamHints(
                    planner_actions=['add references/*.md candidates when detail grows']
                ),
                confidence=0.9,
            )
        ],
    )


def make_online_blueprint() -> SkillBlueprint:
    return SkillBlueprint(
        blueprint_id='openai-notion__blueprint',
        name='notion-knowledge-capture',
        description='Capture conversations into structured Notion pages',
        workflow_summary=['Clarify what to capture', 'Create or update the destination page'],
        artifacts=[
            SkillBlueprintArtifact(path='SKILL.md', artifact_type='skill'),
            SkillBlueprintArtifact(path='references/team-wiki-database.md', artifact_type='reference'),
            SkillBlueprintArtifact(path='agents/openai.yaml', artifact_type='agent-config'),
            SkillBlueprintArtifact(path='_meta.json', artifact_type='metadata'),
        ],
        interface=SkillInterfaceMetadata(display_name='Notion Knowledge Capture'),
        provenance=SkillProvenance(
            source_type='official',
            ecosystem='codex',
            repo_full_name='openai/skills',
            ref='main',
            skill_path='skills/.curated/notion-knowledge-capture',
            skill_url='https://github.com/openai/skills/blob/main/skills/.curated/notion-knowledge-capture/SKILL.md',
        ),
    )


def test_run_planner_uses_fallback_when_llm_disabled():
    request = SkillCreateRequestV6(task='plan', enable_llm_planner=False)
    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=DummyRepoFindings(),
    )

    assert plan.skill_name == 'generated-skill'
    assert plan.files_to_create


def test_run_planner_fallback_includes_candidate_resources():
    request = SkillCreateRequestV6(task='plan', enable_llm_planner=False, skill_name_hint='sample-python-skill')
    repo_findings = RepoFindings(
        repos=[
            RepoFinding(
                repo_path='/tmp/repo',
                summary='Demo repo',
                candidate_resources=CandidateResources(
                    references=['references/usage.md'],
                    scripts=['scripts/run_analysis.py'],
                ),
            )
        ]
    )
    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=repo_findings,
    )

    paths = [file.path for file in plan.files_to_create]
    assert 'references/usage.md' in paths
    assert 'scripts/run_analysis.py' in paths


def test_run_planner_consumes_extracted_patterns_for_files_and_budget():
    request = SkillCreateRequestV6(task='plan', enable_llm_planner=False, skill_name_hint='sample-python-skill')

    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=DummyRepoFindings(),
        extracted_patterns=make_extracted_patterns(),
    )

    paths = [file.path for file in plan.files_to_create]
    assert 'references/overview.md' in paths
    assert plan.content_budget.skill_md_max_lines == 220
    assert 'esp_test_planner_001' in plan.why_this_shape
    assert 'Planner default:' in plan.why_this_shape


def test_run_planner_consumes_online_blueprints_for_files_and_rationale():
    request = SkillCreateRequestV6(task='capture decisions into notion', enable_llm_planner=False, skill_name_hint='notion-capture-skill')

    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=DummyRepoFindings(),
        online_skill_blueprints=[make_online_blueprint()],
        reuse_decision=SkillReuseDecision(
            mode='adapt_existing',
            rationale=['Top candidate has strong task overlap'],
        ),
    )

    paths = [file.path for file in plan.files_to_create]
    assert 'references/team-wiki-database.md' in paths
    assert 'agents/openai.yaml' in paths
    assert '_meta.json' in paths
    assert 'Online skill blueprint available' in plan.why_this_shape
    assert 'Online reuse decision: adapt_existing' in plan.why_this_shape


def test_run_planner_adds_eval_scaffold_files_when_enabled():
    request = SkillCreateRequestV6(task='capture decisions into notion', enable_llm_planner=False, enable_eval_scaffold=True)

    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=DummyRepoFindings(),
    )

    paths = [file.path for file in plan.files_to_create]
    assert 'evals/trigger_eval.json' in paths
    assert 'evals/output_eval.json' in paths
    assert 'evals/benchmark.json' in paths


def test_run_planner_maps_repo_requirements_into_files():
    request = SkillCreateRequestV6(task='build a repo-aware skill', enable_llm_planner=False, skill_name_hint='repo-grounded-skill')
    repo_findings = RepoFindings(
        requirements=[
            SkillRequirement(
                requirement_id='script-runner',
                statement='Provide a deterministic helper aligned with `scripts/run_analysis.py`.',
                evidence_paths=['scripts/run_analysis.py'],
                source_kind='script',
                priority=80,
            ),
            SkillRequirement(
                requirement_id='docs-guide',
                statement='Carry the repo guidance from `README.md` into the generated skill references and instructions.',
                evidence_paths=['README.md'],
                source_kind='doc',
                priority=70,
            ),
        ],
        repos=[
            RepoFinding(
                repo_path='/tmp/repo',
                summary='Demo repo',
                candidate_resources=CandidateResources(
                    references=['README.md'],
                    scripts=['scripts/run_analysis.py'],
                ),
            )
        ],
    )

    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=repo_findings,
    )

    assert plan.requirements
    requirement_map = {item.requirement_id: item for item in plan.requirements}
    assert 'scripts/run_analysis.py' in requirement_map['script-runner'].satisfied_by
    assert 'SKILL.md' in requirement_map['script-runner'].satisfied_by
    assert 'references/README.md' in requirement_map['docs-guide'].satisfied_by

    planned = {item.path: item for item in plan.files_to_create}
    assert 'script-runner' in planned['scripts/run_analysis.py'].requirement_ids
    assert 'docs-guide' in planned['references/README.md'].requirement_ids


def test_run_planner_uses_llm_when_enabled():
    request = SkillCreateRequestV6(task='plan', enable_llm_planner=True, skill_name_hint='sample-python-skill')

    def fake_runner(messages, model):
        return '''
        {
          "skill_name": "sample-python-skill",
          "skill_type": "mixed",
          "objective": "Plan a grounded skill",
          "why_this_shape": "LLM planner path",
          "files_to_create": [
            {
              "path": "SKILL.md",
              "purpose": "Top-level instructions",
              "source_basis": ["repo_findings"]
            }
          ],
          "files_to_update": [],
          "files_to_keep": [],
          "merge_strategy": {
            "mode": "preserve-and-merge",
            "preserve_existing_files": true,
            "replace_conflicting_sections": true
          },
          "content_budget": {
            "skill_md_max_lines": 300,
            "reference_file_targets": {},
            "prefer_script_over_inline_code": true
          },
          "generation_order": ["SKILL.md"]
        }
        '''

    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=DummyRepoFindings(),
        llm_runner=fake_runner,
    )

    assert plan.skill_name == 'sample-python-skill'
    assert plan.why_this_shape == 'LLM planner path'


def test_run_planner_falls_back_on_llm_error():
    request = SkillCreateRequestV6(task='plan', enable_llm_planner=True)

    def bad_runner(messages, model):
        raise RuntimeError('planner upstream failure')

    plan = run_planner(
        request=request,
        repo_context={'files': []},
        repo_findings=DummyRepoFindings(),
        llm_runner=bad_runner,
    )

    assert plan.skill_name == 'generated-skill'
