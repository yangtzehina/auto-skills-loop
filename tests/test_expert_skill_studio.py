from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_test_helpers import invoke_main, load_script_module

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services import (
    build_program_candidate_review_batch_report,
    build_skill_program_authoring_pack,
    build_skill_program_fidelity_report,
    build_skill_program_ir,
    build_skill_task_outcome_report,
    evaluate_negative_case_resistance,
    render_skill_program_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORING_SCRIPT = ROOT / 'scripts' / 'run_skill_program_authoring.py'
REVIEW_SCRIPT = ROOT / 'scripts' / 'run_skill_program_review.py'


def test_known_game_design_profile_builds_skill_program_ir():
    program = build_skill_program_ir(
        skill_name='decision-loop-stress-test',
        task='Stress a decision loop across first hour, midgame, and mastery pressure.',
    )

    assert program is not None
    assert program.workflow_surface == 'execution_spine'
    assert len(program.execution_spine) >= 6
    assert program.execution_spine[0].label == 'Define the Current Loop Shape'
    assert 'Reinforcement Check' in program.output_schema


def test_program_authoring_pack_surfaces_known_and_unknown_candidates():
    pack = build_skill_program_authoring_pack()
    batch = build_program_candidate_review_batch_report(pack)

    assert pack.candidate_program_count >= 8
    assert {
        'concept-to-mvp-pack',
        'decision-loop-stress-test',
        'simulation-resource-loop-design',
    } <= set(pack.ready_for_review)
    assert 'research-memo-synthesis' in pack.needs_human_authoring
    assert batch.pass_count == 3
    assert batch.fail_count >= 1


def test_negative_case_resistance_rejects_generic_shell_failures():
    resistance, generic_rejection, regressions = evaluate_negative_case_resistance()

    assert resistance >= 0.80
    assert generic_rejection >= 1.0
    assert regressions == 0


def test_program_fidelity_passes_for_rendered_known_profile():
    request = SkillCreateRequestV6(task='Stress a decision loop across first hour, midgame, and mastery pressure.')
    skill_md = render_skill_program_markdown(
        skill_name='decision-loop-stress-test',
        description='Stress-test a decision loop.',
        task=request.task,
        references=[],
        scripts=[],
    )
    report = build_skill_program_fidelity_report(
        request=request,
        skill_plan=SkillPlan(skill_name='decision-loop-stress-test', skill_archetype='methodology_guidance'),
        artifacts=Artifacts(files=[ArtifactFile(path='SKILL.md', content=skill_md or '', content_type='text/markdown')]),
    )

    assert report.status == 'pass'
    assert report.execution_move_recall >= 0.85
    assert report.execution_move_order_alignment >= 0.80


def test_task_outcome_passes_for_known_profile_and_skips_unknown_without_probes():
    skill_md = render_skill_program_markdown(
        skill_name='concept-to-mvp-pack',
        description='Package a falsifiable MVP.',
        task='Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.',
        references=[],
        scripts=[],
    )
    known_report = build_skill_task_outcome_report(
        generated_skill_markdown_by_name={'concept-to-mvp-pack': skill_md or ''},
        skill_names=['concept-to-mvp-pack'],
    )
    skipped_report = build_skill_task_outcome_report(
        generated_skill_markdown_by_name={'demo-skill': '# Demo\n'},
        skill_names=['demo-skill'],
    )

    assert known_report.status == 'pass'
    assert known_report.task_outcome_gap_count == 0
    assert skipped_report.status == 'pass'
    assert skipped_report.probe_count == 0


def test_skill_program_authoring_cli_supports_markdown(monkeypatch):
    module = load_script_module(AUTHORING_SCRIPT, 'auto_skills_loop_run_skill_program_authoring')
    code, stdout, stderr = invoke_main(
        module,
        ['run_skill_program_authoring.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Skill Program Authoring Pack')
    assert 'concept-to-mvp-pack' in stdout


def test_skill_program_review_cli_reads_authoring_pack(monkeypatch, tmp_path: Path):
    module = load_script_module(REVIEW_SCRIPT, 'auto_skills_loop_run_skill_program_review')
    pack_path = tmp_path / 'program_pack.json'
    pack_path.write_text(
        json.dumps(build_skill_program_authoring_pack().model_dump(mode='json'), indent=2),
        encoding='utf-8',
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_skill_program_review.py', '--authoring-pack', str(pack_path), '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Skill Program Review Batch')
    assert 'approved_for_release_gate_count=0' in stdout


def test_skill_program_authoring_output_root_writes_sidecar(monkeypatch, tmp_path: Path):
    module = load_script_module(AUTHORING_SCRIPT, 'auto_skills_loop_run_skill_program_authoring_sidecar')
    code, stdout, stderr = invoke_main(
        module,
        ['run_skill_program_authoring.py', '--output-root', str(tmp_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['candidate_program_count'] >= 8
    assert (tmp_path / 'evals' / 'skill_program_authoring.json').exists()
