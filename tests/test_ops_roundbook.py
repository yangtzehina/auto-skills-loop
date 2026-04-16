from __future__ import annotations

from openclaw_skill_create.models.operation_backed_ops import OperationBackedBacklogReport
from openclaw_skill_create.models.public_source_verification import PublicSourceCurationRoundReport, PublicSourcePromotionPack
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.models.runtime_governance import (
    RuntimeCreateSeedProposalPack,
    RuntimeCreateSeedProposal,
    RuntimeOpsDecisionPack,
    RuntimePriorPilotExerciseReport,
    RuntimePriorPilotProfile,
    RuntimePriorPilotReport,
)
from openclaw_skill_create.models.verify import VerifyReport
from openclaw_skill_create.services.verify import build_ops_roundbook_report


def test_build_ops_roundbook_report_marks_pending_manual_work_as_caution():
    create_seed_pack = RuntimeCreateSeedProposalPack(
        proposals=[
            RuntimeCreateSeedProposal(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                preview_request=SkillCreateRequestV6(task='placeholder'),
            )
        ]
    )
    prior_pilot_report = RuntimePriorPilotReport(
        profiles=[
            RuntimePriorPilotProfile(
                family='hf-trainer',
                recommended_status='pilot',
                allowed_families=['hf-trainer'],
                request_overrides_preview={'enable_runtime_effectiveness_prior': True},
            ),
            RuntimePriorPilotProfile(
                family='deep-research',
                recommended_status='hold',
                allowed_families=[],
            ),
        ],
        allowed_families=['hf-trainer'],
    )
    report = build_ops_roundbook_report(
        verify_report=VerifyReport(mode='quick', overall_status='pass'),
        runtime_ops_decision_pack=RuntimeOpsDecisionPack(
            create_seed_candidates=[
                RuntimeCreateSeedProposal(
                    candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                    preview_request=SkillCreateRequestV6(task='placeholder'),
                )
            ],
            prior_pilot_candidates=[
                RuntimePriorPilotProfile(
                    family='hf-trainer',
                    recommended_status='pilot',
                    allowed_families=['hf-trainer'],
                    request_overrides_preview={'enable_runtime_effectiveness_prior': True},
                )
            ],
            source_promotion_candidates=[
                PublicSourcePromotionPack(
                    repo_full_name='alirezarezvani/claude-skills',
                    verdict='ready_for_manual_promotion',
                )
            ],
        ),
        prior_pilot_exercise=RuntimePriorPilotExerciseReport(
            family='hf-trainer',
            verdict='ready_for_manual_pilot',
        ),
        source_promotion_pack=PublicSourcePromotionPack(
            repo_full_name='alirezarezvani/claude-skills',
            verdict='ready_for_manual_promotion',
        ),
        create_seed_pack=create_seed_pack,
        prior_pilot_report=prior_pilot_report,
        source_curation_round=PublicSourceCurationRoundReport(rehearsal_passed=True),
    )

    assert report.verification_status == 'pass'
    assert report.pending_create_seed_decisions == ['missing-fits-calibration-and-astropy-verification-workflow']
    assert report.pending_prior_pilot_decisions == ['hf-trainer']
    assert report.pending_source_promotion_decisions == ['alirezarezvani/claude-skills']
    assert report.next_create_seed_candidate == 'missing-fits-calibration-and-astropy-verification-workflow'
    assert report.next_prior_family_on_hold == 'deep-research'
    assert report.next_source_round_status == 'wait_for_current_source_promotion_resolution'
    assert report.operation_backed_backlog_report is not None
    assert isinstance(report.operation_backed_backlog_report, OperationBackedBacklogReport)
    assert report.operation_backed_patch_current_candidates == []
    assert report.operation_backed_derive_child_candidates == []
    assert report.operation_backed_hold_candidates == []
    assert report.program_fidelity_status == 'pass'
    assert report.program_authoring_status == 'pass'
    assert report.task_outcome_status == 'pass'
    assert report.overall_readiness == 'caution'
