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
from openclaw_skill_create.services.online_discovery import StaticCatalogDiscoveryProvider
from openclaw_skill_create.services.orchestrator import run_skill_create


def _fixture_repo() -> Path:
    return Path(__file__).resolve().parent / 'fixtures' / 'scientific_reuse_eval_repo'


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


def _scientific_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-scientific-astropy',
        name='astropy',
        description='Astropy-powered astronomy workflows for FITS handling, coordinate transforms, and scientific observation analysis.',
        trigger_phrases=['astropy astronomy workflow', 'fits handling', 'coordinate transforms'],
        tags=['astropy', 'astronomy', 'fits', 'coordinates', 'analysis'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='claude',
            repo_full_name='K-Dense-AI/claude-scientific-skills',
            ref='main',
            skill_path='scientific-skills/astropy',
            skill_url='https://github.com/K-Dense-AI/claude-scientific-skills/blob/main/scientific-skills/astropy/SKILL.md',
            source_license='MIT',
            source_attribution='K-Dense-AI/claude-scientific-skills',
        ),
    )


def _generic_research_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-deep-research',
        name='deep-research',
        description='Deep research orchestration for literature review and multi-step evidence gathering.',
        trigger_phrases=['deep research', 'literature review'],
        tags=['research', 'orchestration', 'evidence'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/research-skills',
            ref='main',
            skill_path='skills/deep-research',
            skill_url='https://github.com/example/research-skills/blob/main/skills/deep-research/SKILL.md',
        ),
    )


def _orchestration_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-orchestration',
        name='orchestration',
        description='Coordinate worker subtasks and consolidate findings for generic research workflows.',
        trigger_phrases=['orchestration', 'parallel work'],
        tags=['orchestration', 'parallel', 'workflow'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='agent-skills',
            repo_full_name='example/orchestration-skills',
            ref='main',
            skill_path='skills/orchestration',
            skill_url='https://github.com/example/orchestration-skills/blob/main/skills/orchestration/SKILL.md',
        ),
    )


def _scientific_blueprint() -> SkillBlueprint:
    provenance = _scientific_candidate().provenance
    return SkillBlueprint(
        blueprint_id='fixture-scientific-astropy__blueprint',
        name='astropy',
        description='Astropy-powered astronomy workflows for FITS handling, coordinate transforms, and scientific observation analysis.',
        trigger_summary='Use when a repo needs astronomy-specific FITS handling, calibration notes, and coordinate transforms.',
        workflow_summary=[
            'Load observation docs, configs, and scripts before drafting the generated skill',
            'Preserve FITS handling, calibration, and astronomy-specific validation steps in the generated package',
        ],
        artifacts=[
            SkillBlueprintArtifact(path='references/astropy_pipeline.md', artifact_type='reference', purpose='Astropy workflow and calibration checklist'),
            SkillBlueprintArtifact(path='references/fits_validation.md', artifact_type='reference', purpose='FITS validation and coordinate transform notes'),
            SkillBlueprintArtifact(path='scripts/process_fits.py', artifact_type='script', purpose='Deterministic helper for FITS preprocessing'),
            SkillBlueprintArtifact(path='agents/openai.yaml', artifact_type='agent-config', purpose='Agent metadata for the generated skill'),
            SkillBlueprintArtifact(path='_meta.json', artifact_type='metadata', purpose='Generation metadata with source provenance'),
        ],
        interface=SkillInterfaceMetadata(
            display_name='Astropy Workflow',
            short_description='Handle FITS observations and astronomy coordinate transforms',
            default_prompt='Use $astropy before building astronomy-specific analysis workflows.',
        ),
        tags=['astropy', 'astronomy', 'fits', 'coordinates'],
        provenance=provenance,
        notes=['Fixture blueprint for scientific smoke coverage'],
    )


def test_smoke_chain_scientific_online_eval_fixture(monkeypatch, tmp_path: Path):
    request = SkillCreateRequestV6(
        task='Create an astronomy data-analysis skill around Astropy workflows, coordinate transforms, FITS handling, and evaluation coverage',
        repo_paths=[str(_fixture_repo())],
        skill_name_hint='fixture-astropy-skill',
        enable_llm_extractor=False,
        enable_llm_planner=False,
        enable_llm_skill_md=False,
        enable_online_skill_discovery=True,
        enable_live_online_search=False,
        enable_repair=True,
        max_repair_attempts=1,
    )

    candidates = [_generic_research_candidate(), _orchestration_candidate(), _scientific_candidate()]

    monkeypatch.setattr(
        'openclaw_skill_create.services.orchestrator.default_discovery_providers',
        lambda **kwargs: [StaticCatalogDiscoveryProvider(candidates)],
    )

    def fake_build_skill_blueprints(ranked_candidates, *, limit=5):
        assert ranked_candidates[0].candidate_id == 'fixture-scientific-astropy'
        return [_scientific_blueprint()]

    monkeypatch.setattr(
        'openclaw_skill_create.services.orchestrator.build_skill_blueprints',
        fake_build_skill_blueprints,
    )

    response = run_skill_create(
        request,
        output_root=str(tmp_path / 'generated'),
        persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
        fail_fast_on_validation_fail=False,
    )

    assert response.severity == 'pass'
    assert response.online_skill_candidates
    assert response.online_skill_candidates[0].candidate_id == 'fixture-scientific-astropy'
    assert response.reuse_decision is not None
    assert response.reuse_decision.mode == 'adapt_existing'
    assert response.reuse_decision.selected_candidate_ids == ['fixture-scientific-astropy']
    assert response.reuse_decision.selected_blueprint_ids == ['fixture-scientific-astropy__blueprint']

    assert response.skill_plan is not None
    planned_paths = {item.path for item in response.skill_plan.files_to_create}
    assert 'references/astropy_pipeline.md' in planned_paths
    assert 'scripts/process_fits.py' in planned_paths
    assert 'evals/report.json' in {item.path for item in response.artifacts.files}

    assert response.persistence is not None
    output_dir = Path(response.persistence['output_root'])
    saved_report = json.loads((output_dir / 'evals' / 'report.json').read_text(encoding='utf-8'))
    assert saved_report['skill_name'] == 'fixture-astropy-skill'

    persisted_report = run_evaluations(artifacts=_load_artifacts(output_dir))
    assert persisted_report is not None
    assert response.evaluation_report is not None
    assert persisted_report.skill_name == 'fixture-astropy-skill'
    assert persisted_report.overall_score == response.evaluation_report.overall_score
