from __future__ import annotations

from openclaw_skill_create.services.public_source_curation import (
    build_public_source_promotion_pack,
    load_public_source_curation_round_report,
)
from openclaw_skill_create.services.ops_approval import load_ops_approval_state

from .runtime_test_helpers import OPS_APPROVAL_MANIFEST, PUBLIC_SOURCE_CURATION_ROUND_REPORT


def test_build_public_source_promotion_pack_marks_claude_skills_ready():
    round_report = load_public_source_curation_round_report(PUBLIC_SOURCE_CURATION_ROUND_REPORT)

    pack = build_public_source_promotion_pack(
        round_report=round_report,
        repo_full_name='alirezarezvani/claude-skills',
        approval_state=load_ops_approval_state(OPS_APPROVAL_MANIFEST),
    )

    assert pack.verdict == 'ready_for_manual_promotion'
    assert pack.promotion_candidate is True
    assert pack.requirements_satisfied is True
    assert pack.approval_decision == 'approved'
    assert pack.decision_status == 'applied'
    assert pack.missing_requirements == []
    assert any('SEO specialists' in item for item in pack.required_ranking_regressions)
    assert pack.seed_patch_preview['seed']['repo_full_name'] == 'alirezarezvani/claude-skills'
