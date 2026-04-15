from __future__ import annotations

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_governance import build_runtime_create_seed_proposal_pack

from .runtime_test_helpers import CREATE_QUEUE_FIXTURE_ROOT


def test_build_runtime_create_seed_proposal_pack_emits_preview_requests():
    pack = build_runtime_create_seed_proposal_pack(
        source_path=CREATE_QUEUE_FIXTURE_ROOT / 'no_skill_cluster' / 'manifest.json',
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert pack.runs_processed == 3
    assert len(pack.proposals) == 1
    proposal = pack.proposals[0]
    assert proposal.recommended_decision == 'review'
    assert proposal.preview_request.skill_name_hint
    assert proposal.preview_request.enable_online_skill_discovery is True
    assert proposal.preview_request.enable_eval_scaffold is True

