from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.online import (
    SkillBlueprint,
    SkillBlueprintArtifact,
    SkillProvenance,
    SkillSourceCandidate,
)
from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.evaluation_runner import run_evaluations
from openclaw_skill_create.services.orchestrator import run_skill_create


def _fixture_repo() -> Path:
    return Path(__file__).resolve().parent / 'fixtures' / 'compose_reuse_eval_repo'


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


def _research_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-deep-research',
        name='deep-research',
        description='Deep research orchestration for exploring a problem space and collecting evidence.',
        trigger_phrases=['deep research', 'problem space', 'collect evidence'],
        tags=['research', 'evidence', 'orchestration'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/research-skills',
            ref='main',
            skill_path='skills/deep-research',
            skill_url='https://github.com/example/research-skills/blob/main/skills/deep-research/SKILL.md',
        ),
        score=0.41,
        matched_signals=['research', 'problem', 'evidence'],
    )


def _planning_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='fixture-implementation-planning',
        name='implementation-planning',
        description='Turn findings into implementation plans, milestones, and task breakdowns.',
        trigger_phrases=['implementation plan', 'milestones', 'task breakdown'],
        tags=['planning', 'milestones', 'tasks'],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name='example/planning-skills',
            ref='main',
            skill_path='skills/implementation-planning',
            skill_url='https://github.com/example/planning-skills/blob/main/skills/implementation-planning/SKILL.md',
        ),
        score=0.39,
        matched_signals=['implementation', 'plan', 'tasks'],
    )


def _research_blueprint() -> SkillBlueprint:
    return SkillBlueprint(
        blueprint_id='fixture-deep-research__blueprint',
        name='deep-research',
        description='Deep research orchestration for exploring a problem space and collecting evidence.',
        workflow_summary=['Map the problem space', 'Gather sources and summarize findings'],
        artifacts=[
            SkillBlueprintArtifact(path='references/research_strategy.md', artifact_type='reference', purpose='Research framing and source checklist'),
            SkillBlueprintArtifact(path='scripts/gather_sources.py', artifact_type='script', purpose='Helper for source collection'),
        ],
        provenance=_research_candidate().provenance,
        tags=['research', 'evidence'],
    )


def _planning_blueprint() -> SkillBlueprint:
    return SkillBlueprint(
        blueprint_id='fixture-implementation-planning__blueprint',
        name='implementation-planning',
        description='Turn findings into implementation plans, milestones, and task breakdowns.',
        workflow_summary=['Convert research into milestones', 'Generate tasks and validation plan'],
        artifacts=[
            SkillBlueprintArtifact(path='references/design_template.md', artifact_type='reference', purpose='Reusable design template'),
            SkillBlueprintArtifact(path='references/task_breakdown.md', artifact_type='reference', purpose='Task breakdown template'),
            SkillBlueprintArtifact(path='_meta.json', artifact_type='metadata', purpose='Generation provenance'),
        ],
        provenance=_planning_candidate().provenance,
        tags=['planning', 'milestones', 'tasks'],
    )


def test_smoke_chain_compose_online_eval_fixture(tmp_path: Path):
    request = SkillCreateRequestV6(
        task='Research the problem space and turn it into a structured implementation plan with reusable task templates and evaluation coverage',
        repo_paths=[str(_fixture_repo())],
        skill_name_hint='compose-reuse-skill',
        enable_llm_extractor=False,
        enable_llm_planner=False,
        enable_llm_skill_md=False,
        enable_online_skill_discovery=True,
        enable_live_online_search=False,
        online_skill_candidates=[_research_candidate(), _planning_candidate()],
        online_skill_blueprints=[_research_blueprint(), _planning_blueprint()],
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
    assert response.reuse_decision is not None
    assert response.reuse_decision.mode == 'compose_existing'
    assert response.reuse_decision.selected_candidate_ids == [
        'fixture-deep-research',
        'fixture-implementation-planning',
    ]

    assert response.skill_plan is not None
    planned_paths = {item.path for item in response.skill_plan.files_to_create}
    assert 'references/research_strategy.md' in planned_paths
    assert 'scripts/gather_sources.py' in planned_paths
    assert 'references/design_template.md' in planned_paths
    assert 'references/task_breakdown.md' in planned_paths
    assert 'evals/benchmark.json' in planned_paths

    assert response.artifacts is not None
    artifact_paths = {item.path for item in response.artifacts.files}
    assert 'references/research_strategy.md' in artifact_paths
    assert 'references/design_template.md' in artifact_paths
    assert 'scripts/gather_sources.py' in artifact_paths
    assert 'evals/report.json' in artifact_paths
    assert 'evals/review.json' in artifact_paths
    assert '_meta.json' in artifact_paths

    assert response.evaluation_report is not None
    assert response.quality_review is not None
    assert response.evaluation_report.overall_score > 0.5
    assert {item.name for item in response.evaluation_report.benchmark_results} >= {
        'trigger_accuracy',
        'artifact_completeness',
        'adaptation_quality',
    }

    assert response.persistence is not None
    output_dir = Path(response.persistence['output_root'])
    assert (output_dir / 'evals' / 'benchmark.json').exists()
    saved_report = json.loads((output_dir / 'evals' / 'report.json').read_text(encoding='utf-8'))
    assert saved_report['skill_name'] == 'compose-reuse-skill'

    persisted_report = run_evaluations(artifacts=_load_artifacts(output_dir))
    assert persisted_report is not None
    assert persisted_report.skill_name == 'compose-reuse-skill'
    assert persisted_report.overall_score == response.evaluation_report.overall_score
    assert persisted_report.overall_score > 0.5
