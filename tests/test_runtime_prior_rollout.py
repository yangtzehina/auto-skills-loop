from __future__ import annotations

from openclaw_skill_create.models.runtime_governance import (
    RuntimePriorEligibleSkill,
    RuntimePriorGateReport,
)
from openclaw_skill_create.services.runtime_governance import (
    build_runtime_prior_pilot_report,
    build_runtime_prior_rollout_report,
)


def test_build_runtime_prior_rollout_report_marks_high_confidence_family_eligible():
    gate_report = RuntimePriorGateReport(
        eligible_skills=[
            RuntimePriorEligibleSkill(
                skill_id='hf-trainer__v2_deadbeef',
                skill_name='hf-trainer',
                quality_score=0.9,
                run_count=9,
                runtime_prior_delta=0.048,
                eligible=True,
            )
        ],
        ranking_impact_summary={'generic_promoted_count': 0},
    )

    report = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup={},
        rollout_min_runs=5,
    )

    assert report.families[0].recommended_rollout_status == 'eligible'
    assert report.recommended_scope == ['hf-trainer']


def test_build_runtime_prior_rollout_report_holds_on_generic_risk():
    gate_report = RuntimePriorGateReport(
        eligible_skills=[
            RuntimePriorEligibleSkill(
                skill_id='deep-research__v3_deadbeef',
                skill_name='deep-research',
                quality_score=0.95,
                run_count=10,
                runtime_prior_delta=0.054,
                eligible=True,
            )
        ],
        ranking_impact_summary={'generic_promoted_count': 1},
    )

    report = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup={},
        rollout_min_runs=5,
    )

    assert report.families[0].recommended_rollout_status == 'hold'
    assert report.recommended_scope == []


def test_build_runtime_prior_rollout_report_holds_deep_research_when_product_brief_task_promotes_generic():
    gate_report = RuntimePriorGateReport(
        eligible_skills=[
            RuntimePriorEligibleSkill(
                skill_id='deep-research__v4_deadbeef',
                skill_name='deep-research',
                quality_score=1.0,
                run_count=10,
                runtime_prior_delta=0.06,
                eligible=True,
            ),
            RuntimePriorEligibleSkill(
                skill_id='user-interview-synthesis__v1_deadbeef',
                skill_name='user-interview-synthesis',
                quality_score=0.2,
                run_count=10,
                runtime_prior_delta=-0.036,
                eligible=True,
            ),
        ],
        ranking_impact_summary={'generic_promoted_count': 1},
    )

    report = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup={},
        rollout_min_runs=5,
    )

    by_family = {item.family: item for item in report.families}
    assert by_family['deep-research'].recommended_rollout_status == 'hold'
    assert by_family['deep-research'].generic_promotion_risk == 1
    assert report.recommended_scope == []


def test_build_runtime_prior_rollout_report_holds_when_samples_are_low():
    gate_report = RuntimePriorGateReport(
        eligible_skills=[
            RuntimePriorEligibleSkill(
                skill_id='seo-optimizer__v1_deadbeef',
                skill_name='seo-optimizer',
                quality_score=0.82,
                run_count=3,
                runtime_prior_delta=0.0,
                eligible=False,
            )
        ],
        ranking_impact_summary={'generic_promoted_count': 0},
    )

    report = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup={},
        rollout_min_runs=5,
    )

    assert report.families[0].recommended_rollout_status == 'hold'


def test_build_runtime_prior_pilot_report_builds_allowlist_preview():
    gate_report = RuntimePriorGateReport(
        eligible_skills=[
            RuntimePriorEligibleSkill(
                skill_id='hf-trainer__v2_deadbeef',
                skill_name='hf-trainer',
                quality_score=0.9,
                run_count=9,
                runtime_prior_delta=0.048,
                eligible=True,
            )
        ],
        ranking_impact_summary={'generic_promoted_count': 0},
    )
    rollout = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup={},
        rollout_min_runs=5,
    )

    report = build_runtime_prior_pilot_report(
        rollout_report=rollout,
        runtime_effectiveness_min_runs=5,
    )

    assert report.allowed_families == ['hf-trainer']
    assert report.profiles[0].request_overrides_preview['enable_runtime_effectiveness_prior'] is True
    assert report.profiles[0].request_overrides_preview['runtime_effectiveness_allowed_families'] == ['hf-trainer']
