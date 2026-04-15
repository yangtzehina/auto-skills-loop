from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_test_helpers import invoke_main, load_script_module

from openclaw_skill_create.services.expert_dna import render_expert_dna_skill_md
from openclaw_skill_create.services.expert_dna_authoring import (
    build_expert_dna_authoring_candidate,
    build_expert_dna_authoring_pack,
    build_expert_dna_review_batch_report,
    build_expert_dna_review_report,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORING_SCRIPT = ROOT / 'scripts' / 'run_expert_dna_authoring.py'
REVIEW_SCRIPT = ROOT / 'scripts' / 'run_expert_dna_review.py'


def test_known_game_design_golden_generates_ready_candidate():
    candidate = build_expert_dna_authoring_candidate(
        skill_name='concept-to-mvp-pack',
        task_brief='Create a concept-to-mvp-pack methodology skill.',
    )

    assert candidate.confidence == 'ready_for_review'
    assert candidate.checked_in_move_recall >= 0.85
    assert candidate.missing_expert_evidence == []
    assert candidate.stable_move_sequence is True


def test_generic_shell_cannot_be_ready_for_review():
    shell = """---
name: concept-to-mvp-pack
description: Generic methodology.
---

# concept-to-mvp-pack

Use this skill to turn a request into a concrete decision artifact.

## Overview
Use domain-specific decisions and avoid generic shell.

## Workflow
- Think about the context.
"""
    candidate = build_expert_dna_authoring_candidate(
        skill_name='new-methodology-skill',
        task_brief='Create a new methodology skill.',
        generated_skill_md=shell,
    )

    assert candidate.confidence == 'reject'
    assert 'expert_golden' in candidate.missing_expert_evidence
    assert candidate.stable_move_sequence is False


def test_unknown_methodology_needs_human_authoring_without_golden():
    candidate = build_expert_dna_authoring_candidate(
        skill_name='research-memo-synthesis',
        task_brief='Create a research memo synthesis methodology skill.',
    )

    assert candidate.confidence == 'needs_human_authoring'
    assert candidate.needs_human_golden is True
    assert 'checked_in_expert_profile' in candidate.missing_expert_evidence


def test_review_pass_does_not_auto_enable_release_gate():
    candidate = build_expert_dna_authoring_candidate(
        skill_name='decision-loop-stress-test',
        task_brief='Create a decision-loop-stress-test methodology skill.',
    )
    report = build_expert_dna_review_report(candidate)

    assert report.review_status == 'pass'
    assert report.approved_for_release_gate is False
    assert report.blocking_issues == []


def test_review_fails_candidate_missing_core_material():
    candidate = build_expert_dna_authoring_candidate(
        skill_name='research-memo-synthesis',
        task_brief='Create a research memo synthesis methodology skill.',
    )
    candidate.candidate_dna.workflow_moves = []
    report = build_expert_dna_review_report(candidate)

    assert report.review_status == 'fail'
    assert 'has_workflow_moves' in report.blocking_issues
    assert report.approved_for_release_gate is False


def test_default_authoring_pack_surfaces_unknown_candidates():
    pack = build_expert_dna_authoring_pack()

    assert pack.candidate_dna_count >= 8
    assert {
        'concept-to-mvp-pack',
        'decision-loop-stress-test',
        'simulation-resource-loop-design',
    } <= set(pack.ready_for_review)
    assert 'research-memo-synthesis' in pack.needs_human_authoring


def test_review_batch_counts_pass_and_fail():
    pack = build_expert_dna_authoring_pack()
    batch = build_expert_dna_review_batch_report(pack)

    assert batch.pass_count == 3
    assert batch.fail_count >= 1
    assert batch.approved_for_release_gate_count == 0


def test_expert_dna_authoring_cli_supports_markdown(monkeypatch):
    module = load_script_module(AUTHORING_SCRIPT, 'skill_create_run_expert_dna_authoring')
    code, stdout, stderr = invoke_main(
        module,
        ['run_expert_dna_authoring.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Expert DNA Authoring Pack')
    assert 'concept-to-mvp-pack' in stdout


def test_expert_dna_review_cli_reads_authoring_pack(monkeypatch, tmp_path: Path):
    module = load_script_module(REVIEW_SCRIPT, 'skill_create_run_expert_dna_review')
    pack_path = tmp_path / 'pack.json'
    pack_path.write_text(
        json.dumps(build_expert_dna_authoring_pack().model_dump(mode='json'), indent=2),
        encoding='utf-8',
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_expert_dna_review.py', '--authoring-pack', str(pack_path), '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Expert DNA Review Batch')
    assert 'approved_for_release_gate_count=0' in stdout


def test_authoring_output_root_writes_sidecar(monkeypatch, tmp_path: Path):
    module = load_script_module(AUTHORING_SCRIPT, 'skill_create_run_expert_dna_authoring_sidecar')
    code, stdout, stderr = invoke_main(
        module,
        ['run_expert_dna_authoring.py', '--output-root', str(tmp_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['candidate_dna_count'] >= 8
    assert (tmp_path / 'evals' / 'expert_dna_authoring.json').exists()
