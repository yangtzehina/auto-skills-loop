from __future__ import annotations

import json

from openclaw_skill_create.models.online import SkillSourceCandidate
from openclaw_skill_create.services.ops_approval import load_ops_approval_state
from openclaw_skill_create.services.runtime_governance import (
    build_runtime_prior_gate_report,
    build_runtime_prior_pilot_exercise_report,
    build_runtime_prior_pilot_report,
    build_runtime_prior_rollout_report,
)

from .runtime_test_helpers import OPS_APPROVAL_MANIFEST, SIMULATION_FIXTURE_ROOT


def test_build_runtime_prior_pilot_exercise_report_marks_hf_trainer_ready():
    payload = json.loads(
        (SIMULATION_FIXTURE_ROOT / 'prior_gate' / 'allowlisted_family_only' / 'input' / 'spec.json').read_text(encoding='utf-8')
    )
    gate_report = build_runtime_prior_gate_report(
        catalog=[SkillSourceCandidate.model_validate(item) for item in list(payload.get('catalog') or [])],
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        task_samples=list(payload.get('task_samples') or []),
        runtime_effectiveness_min_runs=int(payload.get('runtime_effectiveness_min_runs', 5) or 5),
        runtime_effectiveness_allowed_families=list(payload.get('runtime_effectiveness_allowed_families') or []) or None,
    )
    rollout_report = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        rollout_min_runs=5,
    )
    pilot_report = build_runtime_prior_pilot_report(
        rollout_report=rollout_report,
        runtime_effectiveness_min_runs=5,
    )

    report = build_runtime_prior_pilot_exercise_report(
        pilot_report=pilot_report,
        family='hf-trainer',
        fixture_root=SIMULATION_FIXTURE_ROOT,
        scenario_names=['hf_trainer_pilot_ready', 'allowlisted_family_only'],
        approval_state=load_ops_approval_state(OPS_APPROVAL_MANIFEST),
    )

    assert report.family == 'hf-trainer'
    assert report.verdict == 'ready_for_manual_pilot'
    assert report.approval_decision == 'approved'
    assert report.decision_status == 'applied'
    assert report.generic_promotion_risk == 0
    assert 'hf_trainer_pilot_ready' in report.scenarios_run


def test_build_runtime_prior_pilot_exercise_report_holds_deep_research_on_generic_risk():
    payload = json.loads(
        (
            SIMULATION_FIXTURE_ROOT
            / 'prior_gate'
            / 'deep_research_hold_generic_risk'
            / 'input'
            / 'spec.json'
        ).read_text(encoding='utf-8')
    )
    gate_report = build_runtime_prior_gate_report(
        catalog=[SkillSourceCandidate.model_validate(item) for item in list(payload.get('catalog') or [])],
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        task_samples=list(payload.get('task_samples') or []),
        runtime_effectiveness_min_runs=int(payload.get('runtime_effectiveness_min_runs', 5) or 5),
        runtime_effectiveness_allowed_families=list(payload.get('runtime_effectiveness_allowed_families') or []) or None,
    )
    rollout_report = build_runtime_prior_rollout_report(
        gate_report=gate_report,
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        rollout_min_runs=5,
    )
    pilot_report = build_runtime_prior_pilot_report(
        rollout_report=rollout_report,
        runtime_effectiveness_min_runs=5,
    )

    report = build_runtime_prior_pilot_exercise_report(
        pilot_report=pilot_report,
        family='deep-research',
        fixture_root=SIMULATION_FIXTURE_ROOT,
        scenario_names=['deep_research_hold_generic_risk'],
        approval_state=load_ops_approval_state(OPS_APPROVAL_MANIFEST),
    )

    assert report.family == 'deep-research'
    assert report.verdict == 'hold'
    assert report.decision_status == 'pending'
    assert report.generic_promotion_risk == 1
    assert report.top_1_changes == 1
    assert report.scenarios_run == ['deep_research_hold_generic_risk']
