from __future__ import annotations

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.runtime_governance import RuntimePriorPilotProfile, RuntimePriorPilotReport
from openclaw_skill_create.services.ops_approval import load_ops_approval_state
from openclaw_skill_create.services.public_source_curation import load_public_source_curation_round_report
from openclaw_skill_create.services.runtime_governance import (
    build_runtime_create_seed_proposal_pack,
    build_runtime_ops_decision_pack,
)

from .runtime_test_helpers import CREATE_QUEUE_FIXTURE_ROOT, OPS_APPROVAL_MANIFEST, PUBLIC_SOURCE_CURATION_ROUND_REPORT


def test_build_runtime_ops_decision_pack_collects_current_candidates():
    create_seed_pack = build_runtime_create_seed_proposal_pack(
        source_path=CREATE_QUEUE_FIXTURE_ROOT / 'no_skill_cluster' / 'manifest.json',
        policy=OpenSpaceObservationPolicy(enabled=False),
    )
    prior_pilot_report = RuntimePriorPilotReport(
        profiles=[
            RuntimePriorPilotProfile(
                family='hf-trainer',
                recommended_status='pilot',
                allowed_families=['hf-trainer'],
                request_overrides_preview={
                    'enable_runtime_effectiveness_prior': True,
                    'runtime_effectiveness_allowed_families': ['hf-trainer'],
                },
            )
        ],
        allowed_families=['hf-trainer'],
    )
    round_report = load_public_source_curation_round_report(PUBLIC_SOURCE_CURATION_ROUND_REPORT)
    approval_state = load_ops_approval_state(OPS_APPROVAL_MANIFEST)

    pack = build_runtime_ops_decision_pack(
        create_seed_pack=create_seed_pack,
        prior_pilot_report=prior_pilot_report,
        source_curation_round=round_report,
        approval_state=approval_state,
    )

    assert pack.create_seed_candidates
    assert pack.create_seed_candidates[0].approval_decision == 'approved'
    assert pack.create_seed_candidates[0].decision_status == 'applied'
    assert pack.prior_pilot_candidates[0].family == 'hf-trainer'
    assert pack.prior_pilot_candidates[0].decision_status == 'applied'
    assert pack.source_promotion_candidates[0].repo_full_name == 'alirezarezvani/claude-skills'
    assert pack.source_promotion_candidates[0].decision_status == 'applied'
    assert pack.decisions_pending == []
    assert any(item.startswith('create-seed:') for item in pack.applied)
    assert any(item.startswith('prior-pilot:hf-trainer') for item in pack.applied)
    assert any(item.startswith('source-promotion:alirezarezvani/claude-skills') for item in pack.applied)
