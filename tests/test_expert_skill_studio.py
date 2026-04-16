from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_test_helpers import invoke_main, load_script_module

from openclaw_skill_create.models.expert_studio import SkillRealizationCandidate
from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.plan import SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services import expert_skill_studio as studio
from openclaw_skill_create.services import (
    build_program_candidate_review_batch_report,
    build_skill_realization_candidates,
    build_skill_program_authoring_pack,
    build_skill_program_fidelity_report,
    build_skill_program_ir,
    build_skill_task_outcome_report,
    choose_skill_realization_candidate,
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


def test_realization_candidates_support_pairwise_promotion_for_known_profile():
    program, realization_spec, candidates = build_skill_realization_candidates(
        skill_name='concept-to-mvp-pack',
        description='Turn a concept into a falsifiable MVP pack.',
        task='Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.',
        references=[],
        scripts=[],
    )
    winner, pairwise_report, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='concept-to-mvp-pack',
        task='Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.',
        candidates=candidates,
    )
    assert program.workflow_surface == 'execution_spine'
    assert realization_spec.workflow_surface == 'execution_spine'
    assert len(candidates) >= 4
    assert {item.realization_strategy for item in candidates} >= {
        'proof_first',
        'cut_first',
        'package_ready',
        'failure_pass',
    }
    assert sum(
        1 for item in candidates
        if item.strategy_profile.get('compression_stage') == 'post'
    ) <= 2
    assert winner.candidate_id in {item.candidate_id for item in candidates}
    assert pairwise_report.winner == winner.candidate_id
    assert pairwise_report.candidate_separation_status == 'pass'
    assert promotion_decision.force_non_regression_status in {'pass', 'fail'}
    assert promotion_decision.coverage_non_regression_status in {'pass', 'fail'}
    assert promotion_decision.compactness_non_regression_status in {'pass', 'fail'}
    assert monotonic_report is not None
    assert monotonic_report.frontier_dominance_status in {'pass', 'fail'}
    assert promotion_decision.promotion_status in {'promote', 'hold'}


def test_pairwise_promotion_holds_when_primary_force_regresses(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:pressure_first:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='pressure_first',
            strategy_profile={
                'opening_frame': 'Pressure frame',
                'section_order': 'Overview > Default Workflow > Quality Checks',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'pressure_first',
                'step_frame': 'pressure_probe',
                'output_focus': 'Pressure Map,Break Point',
                'quality_tone': 'pressure',
                'quality_mode': 'pressure_gate',
                'failure_style': 'collapse_signals',
                'failure_mode': 'collapse_signals',
            },
            rendered_markdown='# pressure',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:repair_first:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='repair_first',
            strategy_profile={
                'opening_frame': 'Repair frame',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Output Format:4',
                'workflow_mode': 'repair_priority',
                'step_frame': 'repair_commit',
                'output_focus': 'Repair Recommendation,Variation Audit',
                'quality_tone': 'repair',
                'quality_mode': 'repair_gate',
                'failure_style': 'repair_moves',
                'failure_mode': 'repair_moves',
            },
            rendered_markdown='# repair',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:collapse_first:3',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='collapse_first',
            strategy_profile={
                'opening_frame': 'Collapse frame',
                'section_order': 'Overview > Failure Patterns and Fixes > Default Workflow',
                'sentence_budget_profile': 'Failure Patterns and Fixes:5',
                'workflow_mode': 'collapse_detection',
                'step_frame': 'collapse_probe',
                'output_focus': 'Collapse Point,Solved State Risk',
                'quality_tone': 'collapse',
                'quality_mode': 'collapse_gate',
                'failure_style': 'solved_state',
                'failure_mode': 'solved_state',
            },
            rendered_markdown='# collapse',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:reinforcement_audit:4',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='reinforcement_audit',
            strategy_profile={
                'opening_frame': 'Reinforcement frame',
                'section_order': 'Overview > Decision Rules > Default Workflow',
                'sentence_budget_profile': 'Decision Rules:4',
                'workflow_mode': 'reinforcement_audit',
                'step_frame': 'reinforcement_probe',
                'output_focus': 'Reinforcement Check,Variation Audit',
                'quality_tone': 'reinforcement',
                'quality_mode': 'reinforcement_gate',
                'failure_style': 'wrong_behavior',
                'failure_mode': 'wrong_behavior',
            },
            rendered_markdown='# reinforcement',
        ),
    ]

    candidate_metrics = {
        '# pressure': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.90,
                'cut_sharpness_score': 0.90,
                'failure_repair_force': 0.90,
                'stop_condition_coverage': 0.90,
                'output_executability_score': 0.90,
                'section_force_distinctness': 0.90,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.85})(),
            'score': 0.90,
        },
        '# repair': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.88,
                'cut_sharpness_score': 0.86,
                'failure_repair_force': 0.89,
                'stop_condition_coverage': 0.88,
                'output_executability_score': 0.87,
                'section_force_distinctness': 0.83,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.04})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.88})(),
            'score': 0.88,
        },
        '# collapse': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.87,
                'cut_sharpness_score': 0.85,
                'failure_repair_force': 0.88,
                'stop_condition_coverage': 0.92,
                'output_executability_score': 0.86,
                'section_force_distinctness': 0.86,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.03})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.87})(),
            'score': 0.87,
        },
        '# reinforcement': {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.86,
                'cut_sharpness_score': 0.84,
                'failure_repair_force': 0.87,
                'stop_condition_coverage': 0.90,
                'output_executability_score': 0.85,
                'section_force_distinctness': 0.84,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.02})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.89})(),
            'score': 0.86,
        },
    }

    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: candidate_metrics[kwargs['markdown']])
    monkeypatch.setattr(
        studio,
        '_current_best_editorial_metrics',
        lambda skill_name, task: {
            'editorial_force': type('Force', (), {
                'decision_pressure_score': 0.93,
                'cut_sharpness_score': 0.90,
                'failure_repair_force': 0.90,
                'stop_condition_coverage': 0.90,
                'output_executability_score': 0.90,
                'section_force_distinctness': 0.82,
            })(),
            'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
            'style': type('Style', (), {'domain_rhythm_score': 0.82})(),
            'score': 0.91,
        },
    )

    winner, pairwise_report, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress loop',
        candidates=candidates,
    )

    assert winner is not None
    assert pairwise_report.candidate_separation_status == 'pass'
    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.force_non_regression_status == 'fail'
    assert promotion_decision.promotion_hold_reason.startswith('hold_due_to_force_regression')
    assert monotonic_report.promotion_reason == 'hold_due_to_force_regression'


def test_pairwise_promotion_holds_when_candidates_only_change_opening(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id=f'concept-to-mvp-pack:variant:{index}',
            skill_name='concept-to-mvp-pack',
            program_id='concept-to-mvp-pack:execution_spine',
            realization_strategy=f'variant_{index}',
            strategy_profile={
                'opening_frame': f'Opening {index}',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'validation_pressure',
                'step_frame': 'proof_gate',
                'output_focus': 'Core Validation Question,Smallest Honest Loop',
                'quality_tone': 'proof-first',
                'quality_mode': 'proof_gate',
                'failure_style': 'redesign_trigger',
                'failure_mode': 'kill_or_fix',
            },
            rendered_markdown=f'# variant {index}',
        )
        for index in range(1, 5)
    ]
    metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 0.90,
            'cut_sharpness_score': 0.91,
            'failure_repair_force': 0.88,
            'boundary_rule_coverage': 0.30,
            'output_executability_score': 0.90,
            'section_force_distinctness': 0.82,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.05})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.84})(),
        'score': 0.90,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: None)

    _, pairwise_report, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='concept-to-mvp-pack',
        task='mvp',
        candidates=candidates,
    )

    assert pairwise_report.candidate_separation_status == 'fail'
    assert pairwise_report.candidate_separation_score < 0.78
    assert promotion_decision.promotion_status == 'hold'
    assert monotonic_report is not None


def test_monotonic_promotion_holds_when_only_stable_without_breakthrough(monkeypatch):
    candidates = [
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:pressure_first:1',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='pressure_first',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'Pressure frame',
                'section_order': 'Overview > Default Workflow > Output Format',
                'sentence_budget_profile': 'Default Workflow:5',
                'workflow_mode': 'pressure_first',
                'step_frame': 'pressure_probe',
                'output_focus': 'Pressure Map,Break Point,Repair Recommendation',
                'quality_tone': 'pressure',
                'quality_mode': 'pressure_gate',
                'failure_style': 'collapse_signals',
                'failure_mode': 'collapse_signals',
            },
            rendered_markdown='# proof',
        ),
        SkillRealizationCandidate(
            candidate_id='decision-loop-stress-test:repair_first:2',
            skill_name='decision-loop-stress-test',
            program_id='decision-loop-stress-test:execution_spine',
            realization_strategy='repair_first',
            strategy_profile={
                'compression_stage': 'pre',
                'opening_frame': 'Repair frame',
                'section_order': 'Overview > Output Format > Default Workflow',
                'sentence_budget_profile': 'Output Format:4',
                'workflow_mode': 'repair_priority',
                'step_frame': 'repair_commit',
                'output_focus': 'Repair Recommendation,Pressure Map,Variation Audit',
                'quality_tone': 'repair',
                'quality_mode': 'repair_gate',
                'failure_style': 'repair_moves',
                'failure_mode': 'repair_moves',
            },
            rendered_markdown='# repair',
        ),
    ]
    metrics = {
        'editorial_force': type('Force', (), {
            'decision_pressure_score': 0.8154,
            'cut_sharpness_score': 1.0,
            'failure_repair_force': 0.89,
            'boundary_rule_coverage': 0.25,
            'stop_condition_coverage': 1.0,
            'output_executability_score': 0.92,
            'section_force_distinctness': 0.81,
            'compression_without_loss': 0.7369,
        })(),
        'editorial': type('Editorial', (), {'redundancy_ratio': 0.08})(),
        'style': type('Style', (), {'domain_rhythm_score': 0.86})(),
        'domain_move_coverage': 0.7571,
        'section_depth_score': 0.9008,
        'task_outcome_with_skill_average': 0.8611,
        'redundancy_ratio': 0.0584,
        'shared_opening_phrase_ratio': 0.0,
        'cross_case_similarity': 0.25,
        'compression_without_loss': 0.7369,
        'score': 0.95,
    }
    monkeypatch.setattr(studio, '_candidate_editorial_metrics', lambda **kwargs: metrics)
    monkeypatch.setattr(studio, '_current_best_editorial_metrics', lambda skill_name, task: {'score': 0.90})

    _, _, promotion_decision, monotonic_report = choose_skill_realization_candidate(
        skill_name='decision-loop-stress-test',
        task='stress a core loop',
        candidates=candidates,
    )

    assert promotion_decision.promotion_status == 'hold'
    assert promotion_decision.stable_but_no_breakthrough is True
    assert promotion_decision.reason == 'stable_but_no_breakthrough'
    assert monotonic_report.promotion_reason == 'hold_due_to_no_primary_win'


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
