from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_approval import (
    CreateSeedApprovalDecision,
    OpsApprovalState,
    PriorPilotApprovalDecision,
    SourcePromotionApprovalDecision,
)
from openclaw_skill_create.models.public_source_verification import PublicSourcePromotionPack
from openclaw_skill_create.models.runtime_governance import (
    RuntimeCreateSeedProposal,
    RuntimeCreateSeedProposalPack,
    RuntimePriorPilotProfile,
    RuntimePriorPilotReport,
)
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.ops_approval import (
    apply_ops_approval_state,
    build_create_seed_manual_round_pack,
    build_prior_pilot_manual_trial_pack,
    load_ops_approval_state,
)


def test_load_ops_approval_state_returns_deferred_defaults_when_manifest_missing(tmp_path: Path):
    state = load_ops_approval_state(tmp_path / 'missing-approval.json')

    assert state.create_seed == []
    assert state.prior_pilot == []
    assert state.source_promotion == []


def test_apply_ops_approval_state_materializes_artifacts_and_applies_source_promotion(tmp_path: Path):
    approval_state = OpsApprovalState(
        create_seed=[
            CreateSeedApprovalDecision(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                decision='approved',
            )
        ],
        prior_pilot=[
            PriorPilotApprovalDecision(
                family='hf-trainer',
                decision='approved',
            )
        ],
        source_promotion=[
            SourcePromotionApprovalDecision(
                repo_full_name='alirezarezvani/claude-skills',
                decision='approved',
            )
        ],
    )
    create_seed_pack = RuntimeCreateSeedProposalPack(
        runs_processed=3,
        proposals=[
            RuntimeCreateSeedProposal(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                suggested_title='Missing FITS Calibration And Astropy Verification Workflow',
                suggested_description='Missing FITS calibration and astropy verification workflow.',
                preview_request=SkillCreateRequestV6(task='Missing FITS calibration and astropy verification workflow.'),
                recommended_decision='review',
            )
        ],
    )
    prior_pilot_report = RuntimePriorPilotReport(
        profiles=[
            RuntimePriorPilotProfile(
                family='hf-trainer',
                recommended_status='pilot',
                allowed_families=['hf-trainer'],
                request_overrides_preview={
                    'enable_runtime_effectiveness_prior': True,
                    'runtime_effectiveness_min_runs': 5,
                    'runtime_effectiveness_allowed_families': ['hf-trainer'],
                },
            )
        ],
        allowed_families=['hf-trainer'],
    )
    source_promotion_packs = [
        PublicSourcePromotionPack(
            repo_full_name='alirezarezvani/claude-skills',
            promotion_candidate=True,
            requirements_satisfied=True,
            required_ranking_regressions=[],
            required_smoke=[],
            missing_requirements=[],
            seed_patch_preview={
                'seed': {
                    'repo_full_name': 'alirezarezvani/claude-skills',
                    'ecosystem': 'claude',
                    'root_paths': ['skills', '.claude/skills', ''],
                    'priority': 35,
                }
            },
            verdict='ready_for_manual_promotion',
        )
    ]
    collections_file = tmp_path / 'online_discovery.py'
    collections_file.write_text(
        "from typing import Any\n\nKNOWN_SKILL_COLLECTIONS: tuple[dict[str, Any], ...] = (\n)\n\nSEMANTIC_TOKEN_GROUPS = ()\n",
        encoding='utf-8',
    )

    report = apply_ops_approval_state(
        create_seed_pack=create_seed_pack,
        prior_pilot_report=prior_pilot_report,
        source_promotion_packs=source_promotion_packs,
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=collections_file,
    )

    assert len(report.create_seed_handoffs) == 1
    assert Path(report.create_seed_handoffs[0].artifact_path).exists()
    assert len(report.prior_pilot_profiles) == 1
    assert Path(report.prior_pilot_profiles[0].artifact_path).exists()
    assert report.applied_source_promotions == ['alirezarezvani/claude-skills']
    assert "'alirezarezvani/claude-skills'" in collections_file.read_text(encoding='utf-8')


def test_apply_ops_approval_state_status_summary_ignores_non_actionable_hold_profiles(tmp_path: Path):
    create_seed_pack = RuntimeCreateSeedProposalPack(
        runs_processed=3,
        proposals=[
            RuntimeCreateSeedProposal(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                suggested_title='Missing FITS Calibration And Astropy Verification Workflow',
                suggested_description='Missing FITS calibration and astropy verification workflow.',
                preview_request=SkillCreateRequestV6(task='Missing FITS calibration and astropy verification workflow.'),
                recommended_decision='review',
            )
        ],
    )
    prior_pilot_report = RuntimePriorPilotReport(
        profiles=[
            RuntimePriorPilotProfile(
                family='hf-trainer',
                recommended_status='pilot',
                allowed_families=['hf-trainer'],
                request_overrides_preview={
                    'enable_runtime_effectiveness_prior': True,
                    'runtime_effectiveness_min_runs': 5,
                    'runtime_effectiveness_allowed_families': ['hf-trainer'],
                },
            ),
            RuntimePriorPilotProfile(
                family='deep-research',
                recommended_status='hold',
                allowed_families=[],
            ),
        ],
        allowed_families=['hf-trainer'],
    )
    source_promotion_packs = [
        PublicSourcePromotionPack(
            repo_full_name='alirezarezvani/claude-skills',
            promotion_candidate=True,
            requirements_satisfied=True,
            required_ranking_regressions=[],
            required_smoke=[],
            missing_requirements=[],
            seed_patch_preview={
                'seed': {
                    'repo_full_name': 'alirezarezvani/claude-skills',
                    'ecosystem': 'claude',
                    'root_paths': ['skills', '.claude/skills', ''],
                    'priority': 35,
                }
            },
            verdict='ready_for_manual_promotion',
        )
    ]

    report = apply_ops_approval_state(
        create_seed_pack=create_seed_pack,
        prior_pilot_report=prior_pilot_report,
        source_promotion_packs=source_promotion_packs,
        approval_state=OpsApprovalState(),
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=tmp_path / 'online_discovery.py',
    )

    assert report.decision_status_summary == {
        'pending': 3,
        'approved_not_applied': 0,
        'applied': 0,
    }


def test_build_create_seed_manual_round_pack_uses_approved_handoff_and_scientific_fixture(tmp_path: Path):
    approval_state = OpsApprovalState(
        create_seed=[
            CreateSeedApprovalDecision(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                decision='approved',
            )
        ]
    )
    create_seed_pack = RuntimeCreateSeedProposalPack(
        runs_processed=3,
        proposals=[
            RuntimeCreateSeedProposal(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                suggested_title='Missing FITS Calibration And Astropy Verification Workflow',
                suggested_description='Missing FITS calibration and astropy verification workflow.',
                representative_task_summaries=['Handle astronomy FITS calibration edge cases.'],
                distilled_requirement_gaps=['Need a dedicated FITS calibration workflow for astronomy reductions.'],
                preview_request=SkillCreateRequestV6(task='Missing FITS calibration and astropy verification workflow.'),
                recommended_decision='review',
            )
        ],
    )
    apply_ops_approval_state(
        create_seed_pack=create_seed_pack,
        prior_pilot_report=RuntimePriorPilotReport(),
        source_promotion_packs=[],
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=tmp_path / 'online_discovery.py',
    )

    pack = build_create_seed_manual_round_pack(
        create_seed_pack=create_seed_pack,
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
    )

    assert pack.approval_decision == 'approved'
    assert pack.status == 'applied'
    assert Path(pack.handoff_artifact_path).exists()
    assert any('scientific_reuse_eval_repo' in item for item in pack.recommended_fixture_inputs)
    assert any('manual round' in item.lower() for item in pack.launch_checklist)


def test_build_prior_pilot_manual_trial_pack_requires_approved_allowlist(tmp_path: Path):
    pilot_report = RuntimePriorPilotReport(
        profiles=[
            RuntimePriorPilotProfile(
                family='hf-trainer',
                recommended_status='pilot',
                allowed_families=['hf-trainer'],
                request_overrides_preview={
                    'enable_runtime_effectiveness_prior': True,
                    'runtime_effectiveness_min_runs': 5,
                    'runtime_effectiveness_allowed_families': ['hf-trainer'],
                },
                generic_promotion_risk=0,
            )
        ],
        allowed_families=['hf-trainer'],
    )

    deferred_pack = build_prior_pilot_manual_trial_pack(
        pilot_report=pilot_report,
        family='hf-trainer',
        approval_state=OpsApprovalState(),
        exercise_verdict='ready_for_manual_pilot',
        generic_promotion_risk=0,
        top_1_changes=0,
    )
    assert deferred_pack.status == 'pending'
    assert deferred_pack.verdict == 'hold'

    approved_pack = build_prior_pilot_manual_trial_pack(
        pilot_report=pilot_report,
        family='hf-trainer',
        approval_state=OpsApprovalState(
            prior_pilot=[PriorPilotApprovalDecision(family='hf-trainer', decision='approved')]
        ),
        artifact_root=tmp_path / 'ops-artifacts',
        exercise_verdict='ready_for_manual_pilot',
        generic_promotion_risk=0,
        top_1_changes=0,
    )
    assert approved_pack.approval_decision == 'approved'
    assert approved_pack.status == 'approved_not_applied'
    assert approved_pack.verdict == 'ready_for_manual_trial'
    assert approved_pack.request_overrides['runtime_effectiveness_allowed_families'] == ['hf-trainer']
