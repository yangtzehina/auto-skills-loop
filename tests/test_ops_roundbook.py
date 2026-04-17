from __future__ import annotations

from openclaw_skill_create.models.comparison import (
    SkillCreateComparisonCaseResult,
    SkillCreateComparisonMetrics,
    SkillCreateComparisonReport,
)
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
from openclaw_skill_create.services.verify import build_ops_roundbook_report, render_ops_roundbook_markdown


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
    assert report.editorial_force_status == 'pass'
    assert report.editorial_force_non_regression == 'pass'
    assert report.pairwise_promotion_status == 'pass'
    assert report.promotion_hold_count == 0
    assert report.coverage_non_regression_status == 'pass'
    assert report.compactness_non_regression_status == 'pass'
    assert report.frontier_dominance_status == 'pass'
    assert report.active_frontier_status == 'pass'
    assert report.candidate_separation_gap_count == 0
    assert report.best_balance_not_beaten_count == 0
    assert report.best_coverage_not_beaten_count == 0
    assert report.current_best_not_beaten_count == 0
    assert report.residual_gap_count == 0
    assert report.program_authoring_status == 'pass'
    assert report.task_outcome_status == 'pass'
    assert report.breakthrough_status == 'pass'
    assert report.overall_readiness == 'caution'


def test_render_ops_roundbook_markdown_includes_decision_loop_outcome_only():
    comparison_report = SkillCreateComparisonReport(
        cases=[
            SkillCreateComparisonCaseResult(
                case_id='decision-loop-stress-test',
                skill_name='decision-loop-stress-test',
                auto_metrics=SkillCreateComparisonMetrics(
                    outcome_only_reranker_status='fail',
                    outcome_only_probe_mode='probe_expanded_v4',
                    outcome_only_frontier_comparison_status='matched',
                    outcome_only_probe_pass_count=7,
                    outcome_only_probe_count=8,
                    outcome_only_improved_probe_count=5,
                    outcome_only_matched_probe_count=2,
                    outcome_only_blocked_probe_count=1,
                    outcome_only_repair_specificity_score=0.75,
                    outcome_only_probe_evidence_density=0.875,
                    outcome_only_collapse_witness_coverage=1.0,
                    false_fix_rejection_status='fail',
                    outcome_only_blocked_probe_ids=['decision.variation-without-read-change'],
                    outcome_only_matched_probe_ids=['decision.midgame-autopilot'],
                    outcome_only_improved_probe_ids=['decision.fake-repair-by-content'],
                    outcome_only_probe_witness_summary=['decision.variation-without-read-change=blocked'],
                    outcome_only_repair_evidence_lines=['repair recommendation: not just numeric tuning'],
                    outcome_only_collapse_evidence_lines=['collapse witness appears before the stop condition label'],
                ),
            )
        ]
    )
    report = build_ops_roundbook_report(
        verify_report=VerifyReport(
            mode='quick',
            overall_status='pass',
            skill_create_comparison_report=comparison_report,
        ),
        runtime_ops_decision_pack=RuntimeOpsDecisionPack(),
        prior_pilot_exercise=RuntimePriorPilotExerciseReport(family='decision-loop'),
        source_promotion_pack=PublicSourcePromotionPack(repo_full_name='example/repo'),
    )

    markdown = render_ops_roundbook_markdown(report)

    assert '## Decision-Loop Outcome-Only' in markdown
    assert '- blocked_probe_ids=' in markdown
    assert '- repair_evidence_lines=' in markdown
    assert '- collapse_evidence_lines=' in markdown
