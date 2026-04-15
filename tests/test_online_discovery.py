from __future__ import annotations

from urllib.error import HTTPError

from openclaw_skill_create.models.online import (
    SkillBlueprint,
    SkillBlueprintArtifact,
    SkillDependency,
    SkillInterfaceMetadata,
    SkillProvenance,
    SkillReuseDecision,
    SkillSourceCandidate,
)
from openclaw_skill_create.services.online_discovery import (
    FETCH_TEXT_CACHE,
    GitHubCollectionDiscoveryProvider,
    GitHubRepoSearchDiscoveryProvider,
    JsonManifestDiscoveryProvider,
    StaticCatalogDiscoveryProvider,
    build_skill_blueprint,
    default_discovery_providers,
    decide_skill_reuse,
    discover_online_skills,
    score_skill_candidate,
)


def make_candidate(
    *,
    candidate_id: str,
    name: str,
    description: str,
    score: float = 0.0,
    trigger_phrases: list[str] | None = None,
    tags: list[str] | None = None,
    repo_full_name: str = 'example/skills',
    skill_path: str | None = None,
) -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id=candidate_id,
        name=name,
        description=description,
        trigger_phrases=trigger_phrases or [name.replace('-', ' ')],
        tags=tags or [name.split('-')[0]],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name=repo_full_name,
            ref='main',
            skill_path=skill_path or f'skills/{name}',
            skill_url=f'https://github.com/{repo_full_name}/blob/main/{skill_path or f"skills/{name}"}/SKILL.md',
        ),
        score=score,
    )


def test_discover_online_skills_prefers_notion_capture_for_capture_task():
    ranked = discover_online_skills(
        task='Capture this architecture decision into Notion as a wiki page and FAQ entry',
        repo_context={'selected_files': []},
        limit=3,
    )

    assert ranked
    assert ranked[0].name == 'notion-knowledge-capture'
    assert ranked[0].score > 0
    assert ranked[0].matched_signals


def test_discover_online_skills_runtime_prior_only_applies_to_allowed_families():
    ranked = discover_online_skills(
        task='Fix the Hugging Face trainer resume workflow',
        repo_context={'selected_files': []},
        catalog=[
            make_candidate(
                candidate_id='hf-trainer',
                name='hf-trainer',
                description='Handle Hugging Face trainer workflows.',
                trigger_phrases=['hugging face trainer'],
                tags=['huggingface', 'trainer'],
                repo_full_name='example/hf',
            ),
            make_candidate(
                candidate_id='deep-research',
                name='deep-research',
                description='General research workflow.',
                trigger_phrases=['deep research'],
                tags=['research', 'workflow'],
                repo_full_name='example/research',
            ),
        ],
        runtime_effectiveness_lookup={
            'hf-trainer': {
                'skill_id': 'hf-trainer__v2_deadbeef',
                'skill_name': 'hf-trainer',
                'quality_score': 0.9,
                'run_count': 7,
            },
            'deep-research': {
                'skill_id': 'deep-research__v3_deadbeef',
                'skill_name': 'deep-research',
                'quality_score': 0.98,
                'run_count': 12,
            },
        },
        enable_runtime_effectiveness_prior=True,
        runtime_effectiveness_min_runs=5,
        runtime_effectiveness_allowed_families=['hf-trainer'],
        limit=2,
    )

    assert ranked[0].name == 'hf-trainer'
    deep_research = next(item for item in ranked if item.name == 'deep-research')
    assert ranked[0].runtime_prior_delta > 0.0
    assert deep_research.runtime_prior_delta == 0.0


def test_build_skill_blueprint_extracts_artifacts_and_interface_metadata():
    candidate = make_candidate(
        candidate_id='example-demo',
        name='demo-skill',
        description='Demo skill for structured capture and helper scripts',
    )

    def fake_fetch(url: str) -> str:
        if url.endswith('/SKILL.md'):
            return (
                '---\n'
                'name: demo-skill\n'
                'description: Demo skill for structured capture and helper scripts\n'
                '---\n\n'
                '# Demo Skill\n\n'
                '1. Read `references/overview.md`\n'
                '2. Run `scripts/run_capture.py`\n\n'
                'See [Overview](references/overview.md) and [Helper](scripts/run_capture.py).\n'
            )
        if url.endswith('/agents/openai.yaml'):
            return (
                'interface:\n'
                '  display_name: "Demo Skill"\n'
                '  short_description: "Load demo skill rules"\n'
                '  default_prompt: "Use $demo-skill before capture."\n'
                '\n'
                'dependencies:\n'
                '  tools:\n'
                '    - type: "mcp"\n'
                '      value: "notion"\n'
                '      description: "Notion MCP server"\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    blueprint = build_skill_blueprint(candidate, fetch_text=fake_fetch)

    paths = [artifact.path for artifact in blueprint.artifacts]
    assert blueprint.name == 'demo-skill'
    assert 'SKILL.md' in paths
    assert 'references/overview.md' in paths
    assert 'scripts/run_capture.py' in paths
    assert 'agents/openai.yaml' in paths
    assert blueprint.interface.display_name == 'Demo Skill'
    assert blueprint.dependencies[0].value == 'notion'
    assert blueprint.workflow_summary


def test_decide_skill_reuse_prefers_adapt_for_strong_match():
    candidate = make_candidate(
        candidate_id='official-notion',
        name='notion-knowledge-capture',
        description='Capture conversations into structured Notion pages',
        score=0.72,
    )
    blueprint = SkillBlueprint(
        blueprint_id='official-notion__blueprint',
        name='notion-knowledge-capture',
        description='Capture conversations into structured Notion pages',
        artifacts=[
            SkillBlueprintArtifact(path='SKILL.md', artifact_type='skill'),
            SkillBlueprintArtifact(path='references/database.md', artifact_type='reference'),
            SkillBlueprintArtifact(path='agents/openai.yaml', artifact_type='agent-config'),
        ],
        interface=SkillInterfaceMetadata(display_name='Notion Capture'),
        dependencies=[SkillDependency(kind='mcp', value='notion')],
        provenance=candidate.provenance,
    )

    decision = decide_skill_reuse(
        task='Turn this design review into a Notion decision record',
        candidates=[candidate],
        blueprints=[blueprint],
    )

    assert decision.mode == 'adapt_existing'
    assert decision.selected_candidate_ids == ['official-notion']
    assert decision.selected_blueprint_ids == ['official-notion__blueprint']
    assert decision.coverage_score > candidate.score


def test_decide_skill_reuse_prefers_compose_for_two_partial_matches():
    candidate_a = make_candidate(
        candidate_id='research',
        name='deep-research',
        description='Deep research orchestration',
        score=0.41,
    )
    candidate_b = make_candidate(
        candidate_id='planning',
        name='kiro-skill',
        description='Requirements and planning workflow',
        score=0.39,
    )

    decision = decide_skill_reuse(
        task='Research the problem space and turn it into a structured implementation plan',
        candidates=[candidate_a, candidate_b],
        blueprints=[],
    )

    assert decision.mode == 'compose_existing'
    assert decision.selected_candidate_ids == ['research', 'planning']


def test_decide_skill_reuse_falls_back_to_generate_fresh_for_weak_match():
    candidate = make_candidate(
        candidate_id='weak-match',
        name='gastown',
        description='Gas Town CLI operations',
        score=0.12,
    )

    decision = decide_skill_reuse(
        task='Create a repo-grounded skill for extracting coding conventions from a Python project',
        candidates=[candidate],
        blueprints=[],
    )

    assert decision.mode == 'generate_fresh'


def test_discover_online_skills_supports_provider_injection_with_json_manifest():
    manifest_candidate = {
        'candidate_id': 'manifest-docs',
        'name': 'docs-capture',
        'description': 'Capture docs into a team wiki',
        'trigger_phrases': ['docs capture', 'wiki'],
        'tags': ['docs', 'wiki'],
        'provenance': {
            'source_type': 'community',
            'ecosystem': 'codex',
            'repo_full_name': 'example/skills',
            'ref': 'main',
            'skill_path': 'skills/docs-capture',
            'skill_url': 'https://github.com/example/skills/blob/main/skills/docs-capture/SKILL.md',
        },
    }

    def fake_fetch(url: str) -> str:
        assert url == 'https://example.com/catalog.json'
        return '[' + __import__('json').dumps(manifest_candidate) + ']'

    ranked = discover_online_skills(
        task='Capture docs into a wiki',
        repo_context={'selected_files': []},
        providers=default_discovery_providers(manifest_urls=['https://example.com/catalog.json']),
        fetch_text=fake_fetch,
        limit=2,
    )

    assert any(item.name == 'docs-capture' for item in ranked)


def test_json_manifest_provider_accepts_object_payload_and_fills_candidate_id():
    manifest_payload = {
        'version': '1.0.0',
        'candidates': [
            {
                'name': 'governance-sync',
                'description': 'Capture governance decisions into structured pages',
                'trigger_phrases': ['governance sync'],
                'tags': ['governance'],
                'provenance': {
                    'source_type': 'community',
                    'ecosystem': 'codex',
                    'repo_full_name': 'example/team-skills',
                    'ref': 'main',
                    'skill_path': 'skills/governance-sync',
                    'skill_url': 'https://github.com/example/team-skills/blob/main/skills/governance-sync/SKILL.md',
                },
            }
        ],
    }

    provider = JsonManifestDiscoveryProvider(['https://example.com/team-catalog.json'])
    candidates = provider.list_candidates(fetch_text=lambda _url: __import__('json').dumps(manifest_payload))

    assert len(candidates) == 1
    assert candidates[0].candidate_id == 'manifest-0'
    assert candidates[0].name == 'governance-sync'


def test_discover_online_skills_supports_live_github_repo_search_provider():
    def fake_fetch(url: str) -> str:
        if url.startswith('https://api.github.com/search/repositories'):
            return __import__('json').dumps(
                {
                    'items': [
                        {
                            'name': 'notion-lifeos-skill',
                            'full_name': 'example/notion-lifeos-skill',
                            'description': 'Notion capture skill for Codex',
                            'private': False,
                            'fork': False,
                            'archived': False,
                            'disabled': False,
                            'default_branch': 'main',
                            'topics': ['codex', 'skill', 'notion'],
                            'license': {'spdx_id': 'MIT'},
                        },
                        {
                            'name': 'random-repo',
                            'full_name': 'example/random-repo',
                            'description': 'Misc files',
                            'private': False,
                            'fork': False,
                            'archived': True,
                            'disabled': False,
                            'default_branch': 'main',
                            'topics': [],
                        },
                    ]
                }
            )
        if url == 'https://api.github.com/repos/example/notion-lifeos-skill/contents?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/notion-lifeos-skill/main/SKILL.md',
                        'html_url': 'https://github.com/example/notion-lifeos-skill/blob/main/SKILL.md',
                    },
                    {'name': 'references', 'path': 'references', 'type': 'dir'},
                    {'name': 'scripts', 'path': 'scripts', 'type': 'dir'},
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/notion-lifeos-skill/main/SKILL.md':
            return (
                '---\n'
                'name: notion-lifeos-skill\n'
                'description: Capture decisions and notes into structured Notion pages. Use when Codex needs a reusable Notion capture workflow.\n'
                '---\n\n'
                '# Notion LifeOS Skill\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    ranked = discover_online_skills(
        task='Capture a design review into Notion and keep the workflow reusable',
        repo_context={'selected_files': []},
        providers=[GitHubRepoSearchDiscoveryProvider(task='Capture a design review into Notion and keep the workflow reusable')],
        fetch_text=fake_fetch,
        limit=3,
    )

    assert ranked
    assert ranked[0].name == 'notion-lifeos-skill'
    assert ranked[0].provenance.repo_full_name == 'example/notion-lifeos-skill'
    assert ranked[0].provenance.skill_path == ''


def test_github_collection_provider_discovers_known_collection_repo():
    def fake_fetch(url: str) -> str:
        if url == 'https://api.github.com/repos/example/research-skills':
            return __import__('json').dumps(
                {
                    'full_name': 'example/research-skills',
                    'description': 'Collection of AI research skills',
                    'private': False,
                    'fork': False,
                    'archived': False,
                    'disabled': False,
                    'default_branch': 'main',
                    'topics': ['skills', 'research', 'codex'],
                    'license': {'spdx_id': 'MIT'},
                }
            )
        if url == 'https://api.github.com/repos/example/research-skills/contents?ref=main':
            return __import__('json').dumps(
                [
                    {'name': '0-autoresearch-skill', 'path': '0-autoresearch-skill', 'type': 'dir'},
                    {'name': '14-agents', 'path': '14-agents', 'type': 'dir'},
                ]
            )
        if url == 'https://api.github.com/repos/example/research-skills/contents/0-autoresearch-skill?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': '0-autoresearch-skill/SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/research-skills/main/0-autoresearch-skill/SKILL.md',
                        'html_url': 'https://github.com/example/research-skills/blob/main/0-autoresearch-skill/SKILL.md',
                    }
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/research-skills/main/0-autoresearch-skill/SKILL.md':
            return (
                '---\n'
                'name: autoresearch-skill\n'
                'description: Run deep research and synthesize findings into reusable plans. Use when Codex needs literature review or research planning.\n'
                '---\n\n'
                '# Autoresearch Skill\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/research-skills',
                'ecosystem': 'ai-research',
                'root_paths': [''],
            }
        ],
        max_candidates=1,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'autoresearch-skill'
    assert candidates[0].provenance.repo_full_name == 'example/research-skills'
    assert candidates[0].provenance.ecosystem == 'ai-research'


def test_github_collection_provider_supports_nested_skills_root_paths():
    def fake_fetch(url: str) -> str:
        if url == 'https://api.github.com/repos/example/nested-skills':
            return __import__('json').dumps(
                {
                    'full_name': 'example/nested-skills',
                    'name': 'nested-skills',
                    'description': 'Collection with bundled skills root',
                    'private': False,
                    'fork': False,
                    'archived': False,
                    'disabled': False,
                    'default_branch': 'main',
                    'topics': ['skills'],
                    'license': {'spdx_id': 'MIT'},
                }
            )
        if url == 'https://api.github.com/repos/example/nested-skills/contents/bundled/skills?ref=main':
            return __import__('json').dumps(
                [
                    {'name': 'capture-docs', 'path': 'bundled/skills/capture-docs', 'type': 'dir'},
                ]
            )
        if url == 'https://api.github.com/repos/example/nested-skills/contents/bundled/skills/capture-docs?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'bundled/skills/capture-docs/SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/nested-skills/main/bundled/skills/capture-docs/SKILL.md',
                        'html_url': 'https://github.com/example/nested-skills/blob/main/bundled/skills/capture-docs/SKILL.md',
                    }
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/nested-skills/main/bundled/skills/capture-docs/SKILL.md':
            return (
                '---\n'
                'name: capture-docs\n'
                'description: Capture docs into a reusable wiki workflow.\n'
                '---\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/nested-skills',
                'ecosystem': 'codex',
                'root_paths': ['bundled/skills'],
            }
        ],
        max_candidates=1,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'capture-docs'
    assert candidates[0].provenance.skill_path == 'bundled/skills/capture-docs'


def test_github_collection_provider_reaches_leaf_skills_inside_large_category_trees():
    def fake_fetch(url: str) -> str:
        if url == 'https://api.github.com/repos/example/category-heavy':
            return __import__('json').dumps(
                {
                    'full_name': 'example/category-heavy',
                    'name': 'category-heavy',
                    'description': 'Collection organized by many subject categories',
                    'private': False,
                    'fork': False,
                    'archived': False,
                    'disabled': False,
                    'default_branch': 'main',
                    'topics': ['skills'],
                    'license': {'spdx_id': 'MIT'},
                }
            )
        if url == 'https://api.github.com/repos/example/category-heavy/contents/skills?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': f'{index:02d}-discipline',
                        'path': f'skills/{index:02d}-discipline',
                        'type': 'dir',
                    }
                    for index in range(30)
                ]
            )
        if url == 'https://api.github.com/repos/example/category-heavy/contents/skills/00-discipline?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'paper-review',
                        'path': 'skills/00-discipline/paper-review',
                        'type': 'dir',
                    }
                ]
            )
        if url == 'https://api.github.com/repos/example/category-heavy/contents/skills/00-discipline/paper-review?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'skills/00-discipline/paper-review/SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/category-heavy/main/skills/00-discipline/paper-review/SKILL.md',
                        'html_url': 'https://github.com/example/category-heavy/blob/main/skills/00-discipline/paper-review/SKILL.md',
                    }
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/category-heavy/main/skills/00-discipline/paper-review/SKILL.md':
            return (
                '---\n'
                'name: paper-review\n'
                'description: Review academic papers and synthesize research findings.\n'
                '---\n'
            )
        if url.startswith('https://api.github.com/repos/example/category-heavy/contents/skills/'):
            return __import__('json').dumps([])
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/category-heavy',
                'ecosystem': 'ai-research',
                'root_paths': ['skills'],
            }
        ],
        max_candidates=1,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'paper-review'
    assert candidates[0].provenance.skill_path == 'skills/00-discipline/paper-review'


def test_github_collection_provider_supports_root_level_skill_directories_via_prefixes():
    def fake_fetch(url: str) -> str:
        if url == 'https://api.github.com/repos/example/root-skill-repo':
            return __import__('json').dumps(
                {
                    'full_name': 'example/root-skill-repo',
                    'name': 'root-skill-repo',
                    'description': 'Root-level skill directories',
                    'private': False,
                    'fork': False,
                    'archived': False,
                    'disabled': False,
                    'default_branch': 'main',
                    'topics': ['skills'],
                    'license': {'spdx_id': 'MIT'},
                }
            )
        if url == 'https://api.github.com/repos/example/root-skill-repo/contents?ref=main':
            return __import__('json').dumps(
                [
                    {'name': 'amazon-competitor-analysis', 'path': 'amazon-competitor-analysis', 'type': 'dir'},
                    {'name': 'docs', 'path': 'docs', 'type': 'dir'},
                ]
            )
        if url == 'https://api.github.com/repos/example/root-skill-repo/contents/amazon-competitor-analysis?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'amazon-competitor-analysis/SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/root-skill-repo/main/amazon-competitor-analysis/SKILL.md',
                        'html_url': 'https://github.com/example/root-skill-repo/blob/main/amazon-competitor-analysis/SKILL.md',
                    }
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/root-skill-repo/main/amazon-competitor-analysis/SKILL.md':
            return (
                '---\n'
                'name: amazon-competitor-analysis\n'
                'description: Analyze Amazon competitors and identify pricing and positioning gaps.\n'
                '---\n'
            )
        if url.startswith('https://api.github.com/repos/example/root-skill-repo/contents/docs'):
            return __import__('json').dumps([])
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/root-skill-repo',
                'ecosystem': 'codex',
                'root_paths': [''],
                'root_dir_prefixes': ['amazon-'],
            }
        ],
        max_candidates=1,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'amazon-competitor-analysis'
    assert candidates[0].provenance.skill_path == 'amazon-competitor-analysis'


def test_github_collection_provider_treats_nested_root_paths_as_non_root_depth():
    def fake_fetch(url: str) -> str:
        if url == 'https://api.github.com/repos/example/categorized-repo':
            return __import__('json').dumps(
                {
                    'full_name': 'example/categorized-repo',
                    'name': 'categorized-repo',
                    'description': 'Category roots with skill directories beneath them',
                    'private': False,
                    'fork': False,
                    'archived': False,
                    'disabled': False,
                    'default_branch': 'main',
                    'topics': ['skills'],
                    'license': {'spdx_id': 'MIT'},
                }
            )
        if url == 'https://api.github.com/repos/example/categorized-repo/contents/research?ref=main':
            return __import__('json').dumps(
                [
                    {'name': 'keyword-research', 'path': 'research/keyword-research', 'type': 'dir'},
                ]
            )
        if url == 'https://api.github.com/repos/example/categorized-repo/contents/research/keyword-research?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'research/keyword-research/SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/categorized-repo/main/research/keyword-research/SKILL.md',
                        'html_url': 'https://github.com/example/categorized-repo/blob/main/research/keyword-research/SKILL.md',
                    }
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/categorized-repo/main/research/keyword-research/SKILL.md':
            return (
                '---\n'
                'name: keyword-research\n'
                'description: Research search demand and cluster keywords.\n'
                '---\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/categorized-repo',
                'ecosystem': 'codex',
                'root_paths': ['research'],
            }
        ],
        max_candidates=1,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'keyword-research'
    assert candidates[0].provenance.skill_path == 'research/keyword-research'


def test_discover_online_skills_dedupes_same_named_candidates_across_repos():
    ranked = discover_online_skills(
        task='Run deep research and synthesize findings into a structured plan',
        repo_context={'selected_files': []},
        catalog=[
            make_candidate(
                candidate_id='deep-research-a',
                name='deep-research',
                description='Deep research orchestration with evidence collection and planning',
            ),
            SkillSourceCandidate(
                candidate_id='deep-research-b',
                name='deep-research',
                description='Deep research workflow with evidence collection and planning',
                trigger_phrases=['deep research'],
                tags=['research', 'planning'],
                provenance=SkillProvenance(
                    source_type='official',
                    ecosystem='codex',
                    repo_full_name='official/deep-research',
                    ref='main',
                    skill_path='skills/deep-research',
                    skill_url='https://github.com/official/deep-research/blob/main/skills/deep-research/SKILL.md',
                ),
            ),
        ],
        limit=5,
    )

    assert len(ranked) == 1
    assert ranked[0].provenance.repo_full_name == 'official/deep-research'


def test_discover_online_skills_prefers_amazon_domain_skill_over_generic_research():
    ranked = discover_online_skills(
        task='Analyze Amazon competitors, reviews, pricing gaps, and listing positioning for a new FBA product',
        repo_context={'selected_files': []},
        catalog=[
            make_candidate(
                candidate_id='amazon-competitor-analysis',
                name='amazon-competitor-analysis',
                description='Analyze Amazon competitors and identify pricing, review, and positioning gaps.',
                trigger_phrases=['amazon competitor analysis'],
                tags=['amazon', 'competitor', 'pricing', 'reviews', 'fba'],
                repo_full_name='example/amazon-skills',
                skill_path='amazon-competitor-analysis',
            ),
            make_candidate(
                candidate_id='deep-research',
                name='deep-research',
                description='Deep research orchestration workflow with evidence collection and reporting.',
                trigger_phrases=['deep research'],
                tags=['research', 'analysis', 'evidence'],
                repo_full_name='example/research-skills',
            ),
            make_candidate(
                candidate_id='orchestration',
                name='orchestration',
                description='Multi-agent orchestration for complex tasks with workers and subtasks.',
                trigger_phrases=['task orchestration'],
                tags=['workflow', 'multi-agent', 'workers'],
                repo_full_name='example/workflow-skills',
            ),
        ],
        limit=3,
    )

    assert ranked
    assert ranked[0].name == 'amazon-competitor-analysis'
    assert ranked[0].score > 0.3
    assert all(item.name != 'orchestration' for item in ranked)


def test_discover_online_skills_prefers_keyword_research_over_generic_research():
    ranked = discover_online_skills(
        task='Do SEO keyword research and cluster terms for a new landing page strategy',
        repo_context={'selected_files': []},
        catalog=[
            make_candidate(
                candidate_id='keyword-research',
                name='keyword-research',
                description='Research search demand and cluster keywords for SEO content strategy.',
                trigger_phrases=['keyword research'],
                tags=['seo', 'keyword', 'search', 'content', 'clustering'],
                repo_full_name='example/seo-geo-skills',
                skill_path='research/keyword-research',
            ),
            make_candidate(
                candidate_id='deep-research',
                name='deep-research',
                description='Deep research orchestration workflow with evidence collection and reporting.',
                trigger_phrases=['deep research'],
                tags=['research', 'analysis', 'evidence'],
                repo_full_name='example/research-skills',
            ),
            make_candidate(
                candidate_id='content-quality-auditor',
                name='content-quality-auditor',
                description='Audit content quality, E-E-A-T signals, and editorial consistency.',
                trigger_phrases=['content quality audit'],
                tags=['seo', 'content', 'audit'],
                repo_full_name='example/seo-geo-skills',
                skill_path='cross-cutting/content-quality-auditor',
            ),
        ],
        limit=3,
    )

    assert ranked
    assert ranked[0].name == 'keyword-research'
    assert ranked[0].score > 0.45
    assert len(ranked) == 2
    assert ranked[1].name == 'deep-research'
    assert ranked[0].score > ranked[1].score


def test_discover_online_skills_prefers_huggingface_domain_skill_over_generic_research():
    ranked = discover_online_skills(
        task='Fine-tune and evaluate a vision model on Hugging Face with dataset loading, trainer configuration, and experiment tracking',
        repo_context={'selected_files': []},
        catalog=[
            make_candidate(
                candidate_id='huggingface-vision-trainer',
                name='huggingface-vision-trainer',
                description='Train and evaluate computer vision models with Hugging Face datasets, trainers, and experiment tracking.',
                trigger_phrases=['hugging face vision trainer'],
                tags=['huggingface', 'vision', 'trainer', 'datasets', 'tracking'],
                repo_full_name='huggingface/skills',
                skill_path='skills/huggingface-vision-trainer',
            ),
            make_candidate(
                candidate_id='deep-research',
                name='deep-research',
                description='Deep research orchestration workflow with evidence collection and reporting.',
                trigger_phrases=['deep research'],
                tags=['research', 'analysis', 'evidence'],
                repo_full_name='example/research-skills',
            ),
            make_candidate(
                candidate_id='orchestration',
                name='orchestration',
                description='Multi-agent orchestration for complex tasks with workers and subtasks.',
                trigger_phrases=['task orchestration'],
                tags=['workflow', 'multi-agent', 'workers'],
                repo_full_name='example/workflow-skills',
            ),
        ],
        limit=3,
    )

    assert ranked
    assert ranked[0].name == 'huggingface-vision-trainer'
    assert ranked[0].score > 0.35
    assert all(item.name != 'orchestration' for item in ranked)


def test_discover_online_skills_prefers_scientific_domain_skill_over_generic_research():
    ranked = discover_online_skills(
        task='Create an astronomy data-analysis skill around Astropy workflows, coordinate transforms, and FITS handling',
        repo_context={'selected_files': []},
        catalog=[
            make_candidate(
                candidate_id='scientific-astropy',
                name='astropy',
                description='Astropy-powered astronomy workflows for FITS files, coordinate transforms, tables, and scientific analysis.',
                trigger_phrases=['astropy astronomy workflow'],
                tags=['astropy', 'astronomy', 'fits', 'coordinates', 'analysis'],
                repo_full_name='K-Dense-AI/claude-scientific-skills',
                skill_path='scientific-skills/astropy',
            ),
            make_candidate(
                candidate_id='deep-research',
                name='deep-research',
                description='Deep research orchestration workflow with evidence collection and reporting.',
                trigger_phrases=['deep research'],
                tags=['research', 'analysis', 'evidence'],
                repo_full_name='example/research-skills',
            ),
            make_candidate(
                candidate_id='orchestration',
                name='orchestration',
                description='Multi-agent orchestration for complex tasks with workers and subtasks.',
                trigger_phrases=['task orchestration'],
                tags=['workflow', 'multi-agent', 'workers'],
                repo_full_name='example/workflow-skills',
            ),
        ],
        limit=3,
    )

    assert ranked
    assert ranked[0].name == 'astropy'
    assert ranked[0].score > 0.35
    assert all(item.name != 'orchestration' for item in ranked)


def test_default_discovery_providers_include_github_collections_when_live():
    providers = default_discovery_providers(include_live=True, task='research and planning')

    assert any(isinstance(provider, GitHubCollectionDiscoveryProvider) for provider in providers)


def test_github_collection_provider_falls_back_to_html_when_api_rate_limited():
    def fake_fetch(url: str) -> str:
        if url == 'https://api.github.com/repos/example/html-fallback':
            raise HTTPError(url, 403, 'rate limit exceeded', None, None)
        if url == 'https://github.com/example/html-fallback':
            return (
                '<meta name="description" content="HTML fallback skill collection">\n'
                '"defaultBranch":"main"\n'
            )
        if url == 'https://api.github.com/repos/example/html-fallback/contents/skills?ref=main':
            raise HTTPError(url, 403, 'rate limit exceeded', None, None)
        if url == 'https://github.com/example/html-fallback/tree/main/skills':
            return (
                '<a href="/example/html-fallback/tree/main/skills/research-skill">research-skill</a>\n'
            )
        if url == 'https://api.github.com/repos/example/html-fallback/contents/skills/research-skill?ref=main':
            raise HTTPError(url, 403, 'rate limit exceeded', None, None)
        if url == 'https://github.com/example/html-fallback/tree/main/skills/research-skill':
            return (
                '<a href="/example/html-fallback/blob/main/skills/research-skill/SKILL.md">SKILL.md</a>\n'
            )
        if url == 'https://raw.githubusercontent.com/example/html-fallback/main/skills/research-skill/SKILL.md':
            return (
                '---\n'
                'name: research-skill\n'
                'description: Run research and synthesize results into reusable guidance.\n'
                '---\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/html-fallback',
                'ecosystem': 'codex',
                'root_paths': ['skills'],
            }
        ],
        max_candidates=1,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'research-skill'
    assert candidates[0].provenance.repo_full_name == 'example/html-fallback'


def test_github_collection_provider_discovers_multiple_collections_via_html_fallback_under_rate_limit():
    api_failures = {'count': 0}

    def fake_fetch(url: str) -> str:
        if url in {
            'https://api.github.com/repos/example/html-fallback-alpha',
            'https://api.github.com/repos/example/html-fallback-beta',
            'https://api.github.com/repos/example/html-fallback-alpha/contents/skills?ref=main',
            'https://api.github.com/repos/example/html-fallback-beta/contents/library/skills?ref=main',
            'https://api.github.com/repos/example/html-fallback-alpha/contents/skills/research-alpha?ref=main',
            'https://api.github.com/repos/example/html-fallback-beta/contents/library/skills/hf-beta?ref=main',
        }:
            api_failures['count'] += 1
            raise HTTPError(url, 403, 'rate limit exceeded', None, None)
        if url == 'https://github.com/example/html-fallback-alpha':
            return (
                '<meta name="description" content="Alpha collection under rate limit">\n'
                '"defaultBranch":"main"\n'
            )
        if url == 'https://github.com/example/html-fallback-beta':
            return (
                '<meta name="description" content="Beta collection under rate limit">\n'
                '"defaultBranch":"main"\n'
            )
        if url == 'https://github.com/example/html-fallback-alpha/tree/main/skills':
            return '<a href="/example/html-fallback-alpha/tree/main/skills/research-alpha">research-alpha</a>\n'
        if url == 'https://github.com/example/html-fallback-beta/tree/main/library/skills':
            return '<a href="/example/html-fallback-beta/tree/main/library/skills/hf-beta">hf-beta</a>\n'
        if url == 'https://github.com/example/html-fallback-alpha/tree/main/skills/research-alpha':
            return '<a href="/example/html-fallback-alpha/blob/main/skills/research-alpha/SKILL.md">SKILL.md</a>\n'
        if url == 'https://github.com/example/html-fallback-beta/tree/main/library/skills/hf-beta':
            return '<a href="/example/html-fallback-beta/blob/main/library/skills/hf-beta/SKILL.md">SKILL.md</a>\n'
        if url == 'https://raw.githubusercontent.com/example/html-fallback-alpha/main/skills/research-alpha/SKILL.md':
            return (
                '---\n'
                'name: research-alpha\n'
                'description: Research alpha workflows and synthesize findings into reusable plans.\n'
                '---\n'
            )
        if url == 'https://raw.githubusercontent.com/example/html-fallback-beta/main/library/skills/hf-beta/SKILL.md':
            return (
                '---\n'
                'name: hf-beta\n'
                'description: Train and evaluate Hugging Face models with datasets, trainers, and tracking.\n'
                '---\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/html-fallback-alpha',
                'ecosystem': 'ai-research',
                'root_paths': ['skills'],
            },
            {
                'repo_full_name': 'example/html-fallback-beta',
                'ecosystem': 'codex',
                'root_paths': ['library/skills'],
            },
        ],
        max_candidates=4,
        max_candidates_per_collection=2,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert {candidate.name for candidate in candidates} == {'research-alpha', 'hf-beta'}
    assert {candidate.provenance.repo_full_name for candidate in candidates} == {
        'example/html-fallback-alpha',
        'example/html-fallback-beta',
    }
    assert api_failures['count'] >= 6


def test_github_collection_provider_prioritizes_high_value_seeds_before_broad_collections():
    requested_urls: list[str] = []

    def fake_fetch(url: str) -> str:
        requested_urls.append(url)
        if url.startswith('https://api.github.com/repos/example/low-priority-broad'):
            raise AssertionError('low-priority collection should not be scanned after the candidate cap is reached')
        if url == 'https://api.github.com/repos/example/high-priority-domain':
            return __import__('json').dumps(
                {
                    'full_name': 'example/high-priority-domain',
                    'name': 'high-priority-domain',
                    'description': 'High-value domain collection',
                    'private': False,
                    'fork': False,
                    'archived': False,
                    'disabled': False,
                    'default_branch': 'main',
                    'topics': ['skills'],
                    'license': {'spdx_id': 'MIT'},
                }
            )
        if url == 'https://api.github.com/repos/example/high-priority-domain/contents/skills?ref=main':
            return __import__('json').dumps(
                [
                    {'name': 'hf-trainer', 'path': 'skills/hf-trainer', 'type': 'dir'},
                ]
            )
        if url == 'https://api.github.com/repos/example/high-priority-domain/contents/skills/hf-trainer?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'skills/hf-trainer/SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/high-priority-domain/main/skills/hf-trainer/SKILL.md',
                        'html_url': 'https://github.com/example/high-priority-domain/blob/main/skills/hf-trainer/SKILL.md',
                    }
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/high-priority-domain/main/skills/hf-trainer/SKILL.md':
            return (
                '---\n'
                'name: hf-trainer\n'
                'description: Train Hugging Face models with datasets, trainers, and evaluation.\n'
                '---\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubCollectionDiscoveryProvider(
        collections=[
            {
                'repo_full_name': 'example/low-priority-broad',
                'ecosystem': 'ai-research',
                'root_paths': ['skills'],
                'priority': 90,
            },
            {
                'repo_full_name': 'example/high-priority-domain',
                'ecosystem': 'codex',
                'root_paths': ['skills'],
                'priority': 10,
            },
        ],
        max_candidates=1,
        max_candidates_per_collection=1,
    )
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'hf-trainer'
    assert candidates[0].provenance.repo_full_name == 'example/high-priority-domain'
    assert any('example/high-priority-domain' in url for url in requested_urls)
    assert not any('example/low-priority-broad' in url for url in requested_urls)


def test_default_fetch_text_uses_cache_for_github_hosts(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'cached-body'

    calls = {'count': 0}

    def fake_urlopen(_request, timeout=20):
        calls['count'] += 1
        return FakeResponse()

    FETCH_TEXT_CACHE.clear()
    monkeypatch.setattr('openclaw_skill_create.services.online_discovery.urlopen', fake_urlopen)

    from openclaw_skill_create.services.online_discovery import default_fetch_text

    assert default_fetch_text('https://github.com/example/repo') == 'cached-body'
    assert default_fetch_text('https://github.com/example/repo') == 'cached-body'
    assert calls['count'] == 1


def test_github_repo_search_provider_falls_back_to_html_search_results():
    def fake_fetch(url: str) -> str:
        if url.startswith('https://api.github.com/search/repositories'):
            raise HTTPError(url, 403, 'rate limit exceeded', None, None)
        if url.startswith('https://github.com/search?q=') and url.endswith('&type=repositories'):
            return (
                '<script type="application/json" data-target="react-app.embeddedData">'
                '{"payload":{"results":['
                '{"archived":false,"public":true,"hl_trunc_description":"Capture docs into a wiki for Codex","topics":["codex","skill","docs"],'
                '"repo":{"repository":{"name":"docs-skill","owner_login":"example"}}}'
                ']}}</script>'
            )
        if url == 'https://api.github.com/repos/example/docs-skill/contents?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/docs-skill/main/SKILL.md',
                        'html_url': 'https://github.com/example/docs-skill/blob/main/SKILL.md',
                    }
                ]
            )
        if url == 'https://raw.githubusercontent.com/example/docs-skill/main/SKILL.md':
            return (
                '---\n'
                'name: docs-skill\n'
                'description: Capture docs into a reusable wiki workflow.\n'
                '---\n'
            )
        raise AssertionError(f'unexpected url: {url}')

    provider = GitHubRepoSearchDiscoveryProvider(task='Capture docs')
    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len(candidates) == 1
    assert candidates[0].name == 'docs-skill'
    assert candidates[0].provenance.repo_full_name == 'example/docs-skill'


def test_score_skill_candidate_prefers_direct_overlap_over_loose_semantic_match():
    docs_candidate = SkillSourceCandidate(
        candidate_id='docs-capture',
        name='docs-capture',
        description='Capture docs into a reusable wiki workflow',
        trigger_phrases=['docs capture', 'wiki workflow'],
        tags=['docs', 'wiki'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/docs-capture',
            ref='main',
            skill_path='skills/docs-capture',
            skill_url='https://github.com/example/docs-capture/blob/main/skills/docs-capture/SKILL.md',
        ),
    )
    generic_candidate = SkillSourceCandidate(
        candidate_id='agent-debug',
        name='agent-introspection-debugging',
        description='Debug agent behavior with traces, logs, and workflow documentation',
        trigger_phrases=['agent debugging'],
        tags=['debugging', 'documentation'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/agent-debug',
            ref='main',
            skill_path='skills/agent-debug',
            skill_url='https://github.com/example/agent-debug/blob/main/skills/agent-debug/SKILL.md',
        ),
    )

    docs_score, _docs_matched = score_skill_candidate(
        task='Capture docs into a wiki and reusable workflow',
        repo_context={'selected_files': []},
        candidate=docs_candidate,
    )
    generic_score, generic_matched = score_skill_candidate(
        task='Capture docs into a wiki and reusable workflow',
        repo_context={'selected_files': []},
        candidate=generic_candidate,
    )

    assert docs_score > generic_score
    assert generic_score < 0.2


def test_score_skill_candidate_applies_runtime_effectiveness_prior_when_enabled():
    candidate = SkillSourceCandidate(
        candidate_id='hf-trainer',
        name='hf-trainer',
        description='Handle Hugging Face trainer workflows and checkpoint resumes.',
        trigger_phrases=['hugging face trainer', 'trainer resume'],
        tags=['huggingface', 'trainer'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/hf-trainer',
            ref='main',
            skill_path='skills/hf-trainer',
            skill_url='https://github.com/example/hf-trainer/blob/main/skills/hf-trainer/SKILL.md',
        ),
    )

    baseline_score, _ = score_skill_candidate(
        task='Fix the Hugging Face trainer resume workflow',
        repo_context={'selected_files': []},
        candidate=candidate,
    )
    boosted_score, boosted_matched = score_skill_candidate(
        task='Fix the Hugging Face trainer resume workflow',
        repo_context={'selected_files': []},
        candidate=candidate,
        runtime_effectiveness_lookup={
            'hf-trainer': {
                'skill_id': 'hf-trainer__v2_deadbeef',
                'skill_name': 'hf-trainer',
                'quality_score': 0.9,
                'run_count': 7,
            }
        },
        runtime_effectiveness_min_runs=5,
    )
    unchanged_low_sample, _ = score_skill_candidate(
        task='Fix the Hugging Face trainer resume workflow',
        repo_context={'selected_files': []},
        candidate=candidate,
        runtime_effectiveness_lookup={
            'hf-trainer': {
                'skill_id': 'hf-trainer__v2_deadbeef',
                'skill_name': 'hf-trainer',
                'quality_score': 0.9,
                'run_count': 2,
            }
        },
        runtime_effectiveness_min_runs=5,
    )

    assert boosted_score > baseline_score
    assert unchanged_low_sample == baseline_score
    assert any(signal.startswith('runtime-prior:+') for signal in boosted_matched)


def test_score_skill_candidate_runtime_prior_allowlist_only_boosts_hf_trainer():
    hf_candidate = SkillSourceCandidate(
        candidate_id='hf-trainer',
        name='hf-trainer',
        description='Handle Hugging Face trainer workflows and checkpoint resumes.',
        trigger_phrases=['hugging face trainer', 'trainer resume'],
        tags=['huggingface', 'trainer'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/hf-trainer',
            ref='main',
            skill_path='skills/hf-trainer',
            skill_url='https://github.com/example/hf-trainer/blob/main/skills/hf-trainer/SKILL.md',
        ),
    )
    generic_candidate = SkillSourceCandidate(
        candidate_id='deep-research',
        name='deep-research',
        description='General deep research workflow.',
        trigger_phrases=['deep research'],
        tags=['research', 'workflow'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/deep-research',
            ref='main',
            skill_path='skills/deep-research',
            skill_url='https://github.com/example/deep-research/blob/main/skills/deep-research/SKILL.md',
        ),
    )

    hf_score, hf_matched = score_skill_candidate(
        task='Resume the Hugging Face trainer checkpoint and fix evaluation resume logic',
        repo_context={'selected_files': []},
        candidate=hf_candidate,
        runtime_effectiveness_lookup={
            'hf-trainer': {
                'skill_id': 'hf-trainer__v2_deadbeef',
                'skill_name': 'hf-trainer',
                'quality_score': 0.91,
                'run_count': 8,
            },
            'deep-research': {
                'skill_id': 'deep-research__v4_deadbeef',
                'skill_name': 'deep-research',
                'quality_score': 0.99,
                'run_count': 12,
            },
        },
        runtime_effectiveness_min_runs=5,
        runtime_effectiveness_allowed_families=['hf-trainer'],
    )
    generic_score, generic_matched = score_skill_candidate(
        task='Resume the Hugging Face trainer checkpoint and fix evaluation resume logic',
        repo_context={'selected_files': []},
        candidate=generic_candidate,
        runtime_effectiveness_lookup={
            'hf-trainer': {
                'skill_id': 'hf-trainer__v2_deadbeef',
                'skill_name': 'hf-trainer',
                'quality_score': 0.91,
                'run_count': 8,
            },
            'deep-research': {
                'skill_id': 'deep-research__v4_deadbeef',
                'skill_name': 'deep-research',
                'quality_score': 0.99,
                'run_count': 12,
            },
        },
        runtime_effectiveness_min_runs=5,
        runtime_effectiveness_allowed_families=['hf-trainer'],
    )

    baseline_hf_score, _ = score_skill_candidate(
        task='Resume the Hugging Face trainer checkpoint and fix evaluation resume logic',
        repo_context={'selected_files': []},
        candidate=hf_candidate,
    )
    baseline_generic_score, _ = score_skill_candidate(
        task='Resume the Hugging Face trainer checkpoint and fix evaluation resume logic',
        repo_context={'selected_files': []},
        candidate=generic_candidate,
    )

    assert hf_score > baseline_hf_score
    assert generic_score == baseline_generic_score
    assert any(signal.startswith('runtime-prior:+') for signal in hf_matched)
    assert not any(signal.startswith('runtime-prior:+') for signal in generic_matched)


def test_score_skill_candidate_prefers_claude_skills_domain_candidate_for_amazon_seo_tasks():
    claude_candidate = SkillSourceCandidate(
        candidate_id='amazon-keyword-optimizer',
        name='amazon-keyword-optimizer',
        description='Optimize Amazon listing keywords and SEO coverage.',
        trigger_phrases=['amazon seo', 'listing keywords'],
        tags=['amazon', 'seo', 'listing'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='claude',
            repo_full_name='alirezarezvani/claude-skills',
            ref='main',
            skill_path='skills/amazon-keyword-optimizer',
            skill_url='https://github.com/alirezarezvani/claude-skills/blob/main/skills/amazon-keyword-optimizer/SKILL.md',
        ),
    )
    generic_candidate = SkillSourceCandidate(
        candidate_id='deep-research',
        name='deep-research',
        description='General deep research workflow.',
        trigger_phrases=['deep research'],
        tags=['research', 'workflow'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/deep-research',
            ref='main',
            skill_path='skills/deep-research',
            skill_url='https://github.com/example/deep-research/blob/main/skills/deep-research/SKILL.md',
        ),
    )

    claude_score, _ = score_skill_candidate(
        task='Refresh Amazon SEO keyword coverage and improve listing ranking',
        repo_context={'selected_files': []},
        candidate=claude_candidate,
    )
    generic_score, _ = score_skill_candidate(
        task='Refresh Amazon SEO keyword coverage and improve listing ranking',
        repo_context={'selected_files': []},
        candidate=generic_candidate,
    )

    assert claude_score > generic_score


def test_score_skill_candidate_prefers_claude_skills_domain_candidate_for_business_workflow_tasks():
    claude_candidate = SkillSourceCandidate(
        candidate_id='business-workflow-optimizer',
        name='business-workflow-optimizer',
        description='Optimize business workflows, SOPs, and operational handoff loops.',
        trigger_phrases=['business workflow', 'operations handoff', 'sop optimization'],
        tags=['business', 'workflow', 'operations'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='claude',
            repo_full_name='alirezarezvani/claude-skills',
            ref='main',
            skill_path='skills/business-workflow-optimizer',
            skill_url='https://github.com/alirezarezvani/claude-skills/blob/main/skills/business-workflow-optimizer/SKILL.md',
        ),
    )
    generic_candidate = SkillSourceCandidate(
        candidate_id='deep-research',
        name='deep-research',
        description='General deep research workflow.',
        trigger_phrases=['deep research'],
        tags=['research', 'workflow'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/deep-research',
            ref='main',
            skill_path='skills/deep-research',
            skill_url='https://github.com/example/deep-research/blob/main/skills/deep-research/SKILL.md',
        ),
    )

    claude_score, _ = score_skill_candidate(
        task='Audit the business workflow handoff and tighten the SOP for operations review',
        repo_context={'selected_files': []},
        candidate=claude_candidate,
    )
    generic_score, _ = score_skill_candidate(
        task='Audit the business workflow handoff and tighten the SOP for operations review',
        repo_context={'selected_files': []},
        candidate=generic_candidate,
    )

    assert claude_score > generic_score


def test_github_repo_search_provider_limits_candidates_per_repo():
    provider = GitHubRepoSearchDiscoveryProvider(task='Capture docs', max_repos=4, max_candidates=6, max_candidates_per_repo=2)

    def fake_fetch(url: str) -> str:
        if url.startswith('https://api.github.com/search/repositories'):
            return __import__('json').dumps(
                {
                    'items': [
                        {
                            'name': 'mega-skills',
                            'full_name': 'example/mega-skills',
                            'description': 'Skill collection',
                            'private': False,
                            'fork': False,
                            'archived': False,
                            'disabled': False,
                            'default_branch': 'main',
                            'topics': ['codex', 'skills'],
                        },
                        {
                            'name': 'docs-skills',
                            'full_name': 'example/docs-skills',
                            'description': 'Docs skill collection',
                            'private': False,
                            'fork': False,
                            'archived': False,
                            'disabled': False,
                            'default_branch': 'main',
                            'topics': ['codex', 'skills'],
                        },
                    ]
                }
            )
        if url == 'https://api.github.com/repos/example/mega-skills/contents?ref=main':
            return __import__('json').dumps(
                [
                    {'name': 'skills', 'path': 'skills', 'type': 'dir'},
                ]
            )
        if url == 'https://api.github.com/repos/example/mega-skills/contents/skills?ref=main':
            return __import__('json').dumps(
                [
                    {'name': 'one', 'path': 'skills/one', 'type': 'dir'},
                    {'name': 'two', 'path': 'skills/two', 'type': 'dir'},
                    {'name': 'three', 'path': 'skills/three', 'type': 'dir'},
                ]
            )
        if url in {
            'https://api.github.com/repos/example/mega-skills/contents/skills/one?ref=main',
            'https://api.github.com/repos/example/mega-skills/contents/skills/two?ref=main',
            'https://api.github.com/repos/example/mega-skills/contents/skills/three?ref=main',
        }:
            skill_name = url.split('/contents/', 1)[1].split('?ref=', 1)[0].rsplit('/', 1)[-1]
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': f'skills/{skill_name}/SKILL.md',
                        'type': 'file',
                        'download_url': f'https://raw.githubusercontent.com/example/mega-skills/main/skills/{skill_name}/SKILL.md',
                        'html_url': f'https://github.com/example/mega-skills/blob/main/skills/{skill_name}/SKILL.md',
                    }
                ]
            )
        if url == 'https://api.github.com/repos/example/docs-skills/contents?ref=main':
            return __import__('json').dumps(
                [
                    {
                        'name': 'SKILL.md',
                        'path': 'SKILL.md',
                        'type': 'file',
                        'download_url': 'https://raw.githubusercontent.com/example/docs-skills/main/SKILL.md',
                        'html_url': 'https://github.com/example/docs-skills/blob/main/SKILL.md',
                    }
                ]
            )
        if url.startswith('https://raw.githubusercontent.com/example/mega-skills/main/skills/'):
            skill_name = url.rsplit('/', 1)[-2]
            return f'---\\nname: {skill_name}\\ndescription: Example {skill_name} skill\\n---\\n'
        if url == 'https://raw.githubusercontent.com/example/docs-skills/main/SKILL.md':
            return '---\\nname: docs-skill\\ndescription: Capture docs into a reusable wiki workflow\\n---\\n'
        raise AssertionError(f'unexpected url: {url}')

    candidates = provider.list_candidates(fetch_text=fake_fetch)

    assert len([item for item in candidates if item.provenance.repo_full_name == 'example/mega-skills']) == 2
