from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.online import (
    SkillBlueprint,
    SkillBlueprintArtifact,
    SkillInterfaceMetadata,
    SkillProvenance,
    SkillSourceCandidate,
)
from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.evaluation_runner import run_evaluations
from openclaw_skill_create.services.orchestrator import run_skill_create


def _fixture_repo() -> Path:
    return Path(__file__).resolve().parent / 'fixtures' / 'online_reuse_eval_repo'


def _load_artifacts(root: Path) -> Artifacts:
    files: list[ArtifactFile] = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        files.append(
            ArtifactFile(
                path=relative,
                content=path.read_text(encoding='utf-8'),
                content_type='application/json' if path.suffix == '.json' else 'text/plain',
                generated_from=['disk'],
                status='existing',
            )
        )
    return Artifacts(files=files)


def _online_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-notion-governance',
        name='notion-governance-capture',
        description='Capture architecture decisions into structured Notion pages with governance-aware templates and sync steps.',
        trigger_phrases=['notion', 'architecture decision', 'decision record', 'governance sync'],
        tags=['notion', 'governance', 'capture', 'decision-log'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/notion-governance-capture',
            ref='main',
            skill_path='skills/notion-governance-capture',
            skill_url='https://github.com/example/notion-governance-capture/blob/main/skills/notion-governance-capture/SKILL.md',
            source_license='MIT',
            source_attribution='example/notion-governance-capture',
        ),
        score=0.78,
        matched_signals=['notion', 'decision', 'governance'],
    )


def _online_blueprint() -> SkillBlueprint:
    provenance = _online_candidate().provenance
    return SkillBlueprint(
        blueprint_id='fixture-notion-governance__blueprint',
        name='notion-governance-capture',
        description='Capture architecture decisions into structured Notion pages with governance-aware templates and sync steps.',
        trigger_summary='Use when a repo-backed decision needs to become a durable Notion record.',
        workflow_summary=[
            'Read the repo decision workflow and schema before generating the skill',
            'Include sync helpers, references, and agent metadata in the package',
        ],
        artifacts=[
            SkillBlueprintArtifact(path='references/notion_schema.md', artifact_type='reference', purpose='Schema notes for Notion database mapping'),
            SkillBlueprintArtifact(path='scripts/sync_notion.py', artifact_type='script', purpose='Deterministic helper for publishing decision pages'),
            SkillBlueprintArtifact(path='agents/openai.yaml', artifact_type='agent-config', purpose='Agent metadata for the generated skill'),
            SkillBlueprintArtifact(path='_meta.json', artifact_type='metadata', purpose='Generation metadata with source provenance'),
        ],
        interface=SkillInterfaceMetadata(
            display_name='Governance Sync',
            short_description='Capture repo decisions into Notion with templates and sync helpers',
            default_prompt='Use $governance-sync-skill before publishing architecture decisions.',
        ),
        tags=['notion', 'governance', 'decision-log'],
        provenance=provenance,
        notes=['Fixture blueprint for smoke coverage'],
    )


def _seo_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-keyword-research',
        name='keyword-research',
        description='Research search demand and cluster keywords for SEO content strategy.',
        trigger_phrases=['keyword research', 'seo keywords', 'search intent'],
        tags=['seo', 'keyword', 'search', 'content'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/seo-geo-skills',
            ref='main',
            skill_path='research/keyword-research',
            skill_url='https://github.com/example/seo-geo-skills/blob/main/research/keyword-research/SKILL.md',
            source_license='MIT',
            source_attribution='example/seo-geo-skills',
        ),
        score=0.84,
        matched_signals=['seo', 'keyword', 'research'],
    )


def _seo_blueprint() -> SkillBlueprint:
    provenance = _seo_candidate().provenance
    return SkillBlueprint(
        blueprint_id='fixture-keyword-research__blueprint',
        name='keyword-research',
        description='Research search demand and cluster keywords for SEO content strategy.',
        trigger_summary='Use when a team needs keyword clustering, search intent mapping, and SEO-oriented content planning.',
        workflow_summary=[
            'Collect seed terms and search intents before drafting output',
            'Cluster keywords into reusable content opportunities and landing page groups',
        ],
        artifacts=[
            SkillBlueprintArtifact(path='references/keyword_clustering.md', artifact_type='reference', purpose='Keyword clustering workflow and examples'),
            SkillBlueprintArtifact(path='references/intent_matrix.md', artifact_type='reference', purpose='Search intent mapping template'),
            SkillBlueprintArtifact(path='agents/openai.yaml', artifact_type='agent-config', purpose='Agent metadata for the generated skill'),
            SkillBlueprintArtifact(path='_meta.json', artifact_type='metadata', purpose='Generation metadata with source provenance'),
        ],
        interface=SkillInterfaceMetadata(
            display_name='Keyword Research',
            short_description='Cluster SEO keywords into reusable content opportunities',
            default_prompt='Use $keyword-research before planning SEO landing pages.',
        ),
        tags=['seo', 'keyword', 'search-intent'],
        provenance=provenance,
        notes=['Fixture blueprint for SEO smoke coverage'],
    )


def _huggingface_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-huggingface-vision-trainer',
        name='huggingface-vision-trainer',
        description='Train and evaluate computer vision models with Hugging Face datasets, trainers, and experiment tracking.',
        trigger_phrases=['hugging face vision trainer', 'vision model training', 'huggingface dataset training'],
        tags=['huggingface', 'vision', 'trainer', 'datasets', 'tracking'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='huggingface/skills',
            ref='main',
            skill_path='skills/huggingface-vision-trainer',
            skill_url='https://github.com/huggingface/skills/blob/main/skills/huggingface-vision-trainer/SKILL.md',
            source_license='Apache-2.0',
            source_attribution='huggingface/skills',
        ),
        score=0.86,
        matched_signals=['huggingface', 'vision', 'trainer', 'datasets'],
    )


def _huggingface_blueprint() -> SkillBlueprint:
    provenance = _huggingface_candidate().provenance
    return SkillBlueprint(
        blueprint_id='fixture-huggingface-vision-trainer__blueprint',
        name='huggingface-vision-trainer',
        description='Train and evaluate computer vision models with Hugging Face datasets, trainers, and experiment tracking.',
        trigger_summary='Use when a repo needs Hugging Face dataset loading, trainer setup, experiment tracking, and evaluation for a vision model workflow.',
        workflow_summary=[
            'Load datasets and task-specific preprocessing before trainer setup',
            'Configure trainer, tracking, and evaluation metrics before shipping the generated skill',
        ],
        artifacts=[
            SkillBlueprintArtifact(path='references/vision_training.md', artifact_type='reference', purpose='Vision fine-tuning workflow and model selection notes'),
            SkillBlueprintArtifact(path='references/dataset_tracking.md', artifact_type='reference', purpose='Dataset loading and experiment tracking checklist'),
            SkillBlueprintArtifact(path='scripts/train_vision_model.py', artifact_type='script', purpose='Deterministic helper for training and evaluation orchestration'),
            SkillBlueprintArtifact(path='agents/openai.yaml', artifact_type='agent-config', purpose='Agent metadata for the generated skill'),
            SkillBlueprintArtifact(path='_meta.json', artifact_type='metadata', purpose='Generation metadata with source provenance'),
        ],
        interface=SkillInterfaceMetadata(
            display_name='Hugging Face Vision Trainer',
            short_description='Fine-tune and evaluate vision models with datasets, trainers, and tracking',
            default_prompt='Use $huggingface-vision-trainer before building a Hugging Face vision training workflow.',
        ),
        tags=['huggingface', 'vision', 'trainer', 'datasets', 'tracking'],
        provenance=provenance,
        notes=['Fixture blueprint for Hugging Face smoke coverage'],
    )


def test_smoke_chain_online_eval_fixture(tmp_path: Path):
    request = SkillCreateRequestV6(
        task='Capture architecture decisions into Notion with repo-aware governance workflow and evaluation coverage',
        repo_paths=[str(_fixture_repo())],
        skill_name_hint='fixture-governance-skill',
        enable_llm_extractor=False,
        enable_llm_planner=False,
        enable_llm_skill_md=False,
        enable_online_skill_discovery=True,
        enable_live_online_search=False,
        online_skill_candidates=[_online_candidate()],
        online_skill_blueprints=[_online_blueprint()],
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        output_root=str(tmp_path / 'generated'),
        persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
        fail_fast_on_validation_fail=False,
    )

    assert response.severity == 'pass'
    assert response.request_echo.enable_eval_scaffold is True
    assert response.repo_findings is not None
    assert response.repo_findings.repos
    repo = response.repo_findings.repos[0]
    assert repo.docs
    assert repo.scripts
    assert repo.configs
    assert repo.workflows

    assert response.skill_plan is not None
    assert response.skill_plan.requirements
    planned_paths = {item.path for item in response.skill_plan.files_to_create}
    assert 'evals/trigger_eval.json' in planned_paths
    assert 'agents/openai.yaml' in planned_paths
    assert '_meta.json' in planned_paths

    assert response.artifacts is not None
    artifact_paths = {item.path for item in response.artifacts.files}
    assert 'evals/trigger_eval.json' in artifact_paths
    assert 'evals/output_eval.json' in artifact_paths
    assert 'evals/benchmark.json' in artifact_paths
    assert 'evals/report.json' in artifact_paths
    assert 'evals/review.json' in artifact_paths
    assert 'agents/openai.yaml' in artifact_paths
    assert '_meta.json' in artifact_paths

    assert response.evaluation_report is not None
    assert response.quality_review is not None
    assert response.evaluation_report.overall_score > 0.5
    assert response.evaluation_report.trigger_results
    assert response.evaluation_report.output_results
    assert response.quality_review.requirement_results

    assert response.persistence is not None
    assert response.persistence['applied'] is True
    output_dir = Path(response.persistence['output_root'])
    assert (output_dir / 'evals' / 'report.json').exists()
    assert (output_dir / 'evals' / 'review.json').exists()
    saved_report = json.loads((output_dir / 'evals' / 'report.json').read_text(encoding='utf-8'))
    assert saved_report['skill_name'] == 'fixture-governance-skill'
    saved_review = json.loads((output_dir / 'evals' / 'review.json').read_text(encoding='utf-8'))
    assert saved_review['skill_name'] == 'fixture-governance-skill'
    assert (output_dir / 'SKILL.md').exists()
    assert (output_dir / 'evals' / 'trigger_eval.json').exists()
    assert (output_dir / 'agents' / 'openai.yaml').exists()

    persisted_report = run_evaluations(artifacts=_load_artifacts(output_dir))
    assert persisted_report is not None
    assert persisted_report.skill_name == 'fixture-governance-skill'
    assert persisted_report.overall_score == response.evaluation_report.overall_score
    assert persisted_report.overall_score > 0.5


def test_smoke_chain_domain_online_eval_fixture(tmp_path: Path):
    request = SkillCreateRequestV6(
        task='Do SEO keyword research and cluster terms into a reusable landing page strategy with evaluation coverage',
        repo_paths=[str(_fixture_repo())],
        skill_name_hint='fixture-keyword-research-skill',
        enable_llm_extractor=False,
        enable_llm_planner=False,
        enable_llm_skill_md=False,
        enable_online_skill_discovery=True,
        enable_live_online_search=False,
        online_skill_candidates=[_seo_candidate()],
        online_skill_blueprints=[_seo_blueprint()],
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        output_root=str(tmp_path / 'generated'),
        persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
        fail_fast_on_validation_fail=False,
    )

    assert response.severity == 'pass'
    assert response.request_echo.enable_eval_scaffold is True
    assert response.reuse_decision is not None
    assert response.reuse_decision.mode == 'adapt_existing'
    assert response.reuse_decision.selected_candidate_ids == ['fixture-keyword-research']
    assert response.reuse_decision.selected_blueprint_ids == ['fixture-keyword-research__blueprint']

    assert response.skill_plan is not None
    planned_paths = {item.path for item in response.skill_plan.files_to_create}
    assert 'references/keyword_clustering.md' in planned_paths
    assert 'references/intent_matrix.md' in planned_paths
    assert 'agents/openai.yaml' in planned_paths
    assert '_meta.json' in planned_paths
    assert 'evals/trigger_eval.json' in planned_paths

    assert response.artifacts is not None
    artifact_paths = {item.path for item in response.artifacts.files}
    assert 'references/keyword_clustering.md' in artifact_paths
    assert 'references/intent_matrix.md' in artifact_paths
    assert 'agents/openai.yaml' in artifact_paths
    assert '_meta.json' in artifact_paths
    assert 'evals/report.json' in artifact_paths
    assert 'evals/review.json' in artifact_paths

    assert response.evaluation_report is not None
    assert response.quality_review is not None
    assert response.evaluation_report.overall_score > 0.5
    assert response.evaluation_report.trigger_results
    assert response.evaluation_report.output_results

    assert response.persistence is not None
    output_dir = Path(response.persistence['output_root'])
    assert (output_dir / 'evals' / 'report.json').exists()
    saved_report = json.loads((output_dir / 'evals' / 'report.json').read_text(encoding='utf-8'))
    assert saved_report['skill_name'] == 'fixture-keyword-research-skill'

    persisted_report = run_evaluations(artifacts=_load_artifacts(output_dir))
    assert persisted_report is not None
    assert persisted_report.skill_name == 'fixture-keyword-research-skill'
    assert persisted_report.overall_score == response.evaluation_report.overall_score
    assert persisted_report.overall_score > 0.5


def test_smoke_chain_huggingface_online_eval_fixture(tmp_path: Path):
    request = SkillCreateRequestV6(
        task='Fine-tune and evaluate a vision model on Hugging Face with dataset loading, trainer configuration, experiment tracking, and evaluation coverage',
        repo_paths=[str(_fixture_repo())],
        skill_name_hint='fixture-huggingface-vision-trainer-skill',
        enable_llm_extractor=False,
        enable_llm_planner=False,
        enable_llm_skill_md=False,
        enable_online_skill_discovery=True,
        enable_live_online_search=False,
        online_skill_candidates=[_huggingface_candidate()],
        online_skill_blueprints=[_huggingface_blueprint()],
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        output_root=str(tmp_path / 'generated'),
        persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
        fail_fast_on_validation_fail=False,
    )

    assert response.severity == 'pass'
    assert response.request_echo.enable_eval_scaffold is True
    assert response.reuse_decision is not None
    assert response.reuse_decision.mode == 'adapt_existing'
    assert response.reuse_decision.selected_candidate_ids == ['fixture-huggingface-vision-trainer']
    assert response.reuse_decision.selected_blueprint_ids == ['fixture-huggingface-vision-trainer__blueprint']

    assert response.skill_plan is not None
    planned_paths = {item.path for item in response.skill_plan.files_to_create}
    assert 'references/vision_training.md' in planned_paths
    assert 'references/dataset_tracking.md' in planned_paths
    assert 'scripts/train_vision_model.py' in planned_paths
    assert 'agents/openai.yaml' in planned_paths
    assert '_meta.json' in planned_paths
    assert 'evals/trigger_eval.json' in planned_paths
    assert 'evals/output_eval.json' in planned_paths
    assert 'evals/benchmark.json' in planned_paths

    assert response.artifacts is not None
    artifact_paths = {item.path for item in response.artifacts.files}
    assert 'references/vision_training.md' in artifact_paths
    assert 'references/dataset_tracking.md' in artifact_paths
    assert 'scripts/train_vision_model.py' in artifact_paths
    assert 'agents/openai.yaml' in artifact_paths
    assert '_meta.json' in artifact_paths
    assert 'evals/report.json' in artifact_paths
    assert 'evals/review.json' in artifact_paths

    assert response.evaluation_report is not None
    assert response.quality_review is not None
    assert response.evaluation_report.overall_score > 0.5
    assert response.evaluation_report.trigger_results
    assert response.evaluation_report.output_results
    assert {item.name for item in response.evaluation_report.benchmark_results} >= {
        'trigger_accuracy',
        'artifact_completeness',
        'task_alignment',
        'adaptation_quality',
    }

    assert response.persistence is not None
    output_dir = Path(response.persistence['output_root'])
    assert (output_dir / 'evals' / 'report.json').exists()
    saved_report = json.loads((output_dir / 'evals' / 'report.json').read_text(encoding='utf-8'))
    assert saved_report['skill_name'] == 'fixture-huggingface-vision-trainer-skill'

    persisted_report = run_evaluations(artifacts=_load_artifacts(output_dir))
    assert persisted_report is not None
    assert persisted_report.skill_name == 'fixture-huggingface-vision-trainer-skill'
    assert persisted_report.overall_score == response.evaluation_report.overall_score
    assert persisted_report.model_dump() == response.evaluation_report.model_dump()
