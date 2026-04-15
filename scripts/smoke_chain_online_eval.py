from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openclaw_skill_create.models.online import (
    SkillBlueprint,
    SkillBlueprintArtifact,
    SkillInterfaceMetadata,
    SkillProvenance,
    SkillSourceCandidate,
)
from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.orchestrator import run_skill_create


def fixture_repo() -> Path:
    return ROOT / 'tests' / 'fixtures' / 'online_reuse_eval_repo'


def online_candidate() -> SkillSourceCandidate:
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


def online_blueprint() -> SkillBlueprint:
    provenance = online_candidate().provenance
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
            default_prompt='Use $governance-smoke-skill before publishing architecture decisions.',
        ),
        tags=['notion', 'governance', 'decision-log'],
        provenance=provenance,
        notes=['Fixture blueprint for smoke coverage'],
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='skill-create-v6-online-eval-') as tmp:
        temp_root = Path(tmp)
        output_root = temp_root / 'generated'
        request = SkillCreateRequestV6(
            task='Capture architecture decisions into Notion with repo-aware governance workflow and evaluation coverage',
            repo_paths=[str(fixture_repo())],
            skill_name_hint='governance-smoke-skill',
            enable_llm_extractor=False,
            enable_llm_planner=False,
            enable_llm_skill_md=False,
            enable_online_skill_discovery=True,
            enable_live_online_search=False,
            online_skill_candidates=[online_candidate()],
            online_skill_blueprints=[online_blueprint()],
            enable_repair=True,
            max_repair_attempts=1,
        )

        response = run_skill_create(
            request,
            output_root=str(output_root),
            persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
            fail_fast_on_validation_fail=False,
        )

        print('severity:', response.severity)
        print('repo_paths:', request.repo_paths)
        print('planned_files:', [item.path for item in (response.skill_plan.files_to_create if response.skill_plan else [])])
        print('artifacts:', [item.path for item in (response.artifacts.files if response.artifacts else [])])
        print('evaluation_summary:', response.evaluation_report.summary if response.evaluation_report else [])
        print('persisted_output:', response.persistence['output_root'] if response.persistence else 'missing')
        if response.persistence and response.persistence.get('output_root'):
            report_path = Path(response.persistence['output_root']) / 'evals' / 'report.json'
            print('saved_eval_report:', report_path.exists())

        if response.persistence and response.persistence.get('output_root'):
            completed = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'run_evals.py'), response.persistence['output_root']],
                capture_output=True,
                text=True,
                check=False,
            )
            print('run_evals_exit:', completed.returncode)
            stdout = completed.stdout.strip()
            if stdout:
                try:
                    payload = json.loads(stdout)
                    print('run_evals_score:', payload.get('overall_score'))
                    print('run_evals_summary:', payload.get('summary'))
                except json.JSONDecodeError:
                    print('run_evals_stdout:', stdout[:500])


if __name__ == '__main__':
    main()
