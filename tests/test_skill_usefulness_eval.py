from __future__ import annotations

from openclaw_skill_create.services.expert_dna import render_expert_dna_skill_md
from openclaw_skill_create.services.skill_usefulness_eval import build_skill_usefulness_eval_report


def test_usefulness_eval_passes_known_expert_dna_outputs():
    generated = {
        name: render_expert_dna_skill_md(
            skill_name=name,
            description=f'Use {name}.',
            task=f'Create {name}.',
            references=[],
            scripts=[],
        )
        or ''
        for name in [
            'concept-to-mvp-pack',
            'decision-loop-stress-test',
            'simulation-resource-loop-design',
        ]
    }

    report = build_skill_usefulness_eval_report(generated_skill_markdown_by_name=generated)

    assert report.status == 'pass'
    assert report.probe_count == 6
    assert report.usefulness_gap_count == 0
    assert report.with_skill_average > report.baseline_average + 0.30


def test_usefulness_eval_rejects_generic_advice_leakage():
    generic = """# concept-to-mvp-pack

## Overview
Consider various factors and think about best practices at a high level.

## Output Format
- A general summary.
"""

    report = build_skill_usefulness_eval_report(
        generated_skill_markdown_by_name={'concept-to-mvp-pack': generic},
        skill_names=['concept-to-mvp-pack'],
    )

    assert report.status == 'fail'
    assert report.usefulness_gap_count > 0
    assert any('generic_advice_leakage' in result.gap_issues for result in report.probe_results)


def test_comparison_report_includes_authoring_and_usefulness():
    from openclaw_skill_create.services.skill_create_comparison import build_skill_create_comparison_report

    report = build_skill_create_comparison_report(include_hermes=False)

    assert report.dna_authoring_status == 'pass'
    assert report.candidate_dna_count >= 8
    assert report.expert_dna_authoring_pack is not None
    assert report.skill_usefulness_eval_report is not None
    assert report.usefulness_eval_status == 'pass'
    assert report.usefulness_gap_count == 0
