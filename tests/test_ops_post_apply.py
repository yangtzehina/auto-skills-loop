from __future__ import annotations

from pathlib import Path

import openclaw_skill_create.services.ops_post_apply as ops_post_apply
from openclaw_skill_create.models.ops_approval import (
    CreateSeedApprovalDecision,
    OpsApprovalState,
    PriorPilotApprovalDecision,
    SourcePromotionApprovalDecision,
)
from openclaw_skill_create.models.runtime_governance import (
    RuntimeCreateSeedProposal,
    RuntimeCreateSeedProposalPack,
    RuntimePriorPilotProfile,
    RuntimePriorPilotReport,
)
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.ops_approval import apply_ops_approval_state
from openclaw_skill_create.services.ops_post_apply import (
    build_create_seed_launch_report,
    build_create_seed_package_review_report,
    build_ops_refill_report,
    build_prior_pilot_retrieval_trial_report,
    build_prior_pilot_trial_observation_report,
    build_source_promotion_post_apply_report,
)
from openclaw_skill_create.services.public_source_curation import load_public_source_curation_round_report

from .runtime_test_helpers import PUBLIC_SOURCE_CURATION_ROUND_REPORT, SIMULATION_FIXTURE_ROOT


def _pilot_report() -> RuntimePriorPilotReport:
    return RuntimePriorPilotReport(
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
            ),
            RuntimePriorPilotProfile(
                family='deep-research',
                recommended_status='hold',
                allowed_families=[],
                request_overrides_preview={
                    'enable_runtime_effectiveness_prior': False,
                    'runtime_effectiveness_min_runs': 5,
                    'runtime_effectiveness_allowed_families': [],
                },
                generic_promotion_risk=0,
            ),
        ],
        allowed_families=['hf-trainer'],
    )


def _create_seed_pack() -> RuntimeCreateSeedProposalPack:
    return RuntimeCreateSeedProposalPack(
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


def test_build_create_seed_launch_report_marks_applied_launch_ready(tmp_path: Path):
    approval_state = OpsApprovalState(
        create_seed=[
            CreateSeedApprovalDecision(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                decision='approved',
            )
        ]
    )
    create_seed_pack = _create_seed_pack()

    apply_ops_approval_state(
        create_seed_pack=create_seed_pack,
        prior_pilot_report=RuntimePriorPilotReport(),
        source_promotion_packs=[],
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=tmp_path / 'online_discovery.py',
    )

    report = build_create_seed_launch_report(
        create_seed_pack=create_seed_pack,
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        output_root=tmp_path / 'manual-rounds',
    )

    assert report.decision_status == 'applied'
    assert report.artifact_exists is True
    assert report.launch_ready is True
    assert 'manual-rounds' in report.suggested_output_root


def test_build_create_seed_package_review_report_reads_persisted_manual_round(tmp_path: Path):
    candidate_key = 'missing-fits-calibration-and-astropy-verification-workflow'
    output_root = tmp_path / 'manual-rounds' / candidate_key
    (output_root / 'evals').mkdir(parents=True, exist_ok=True)
    (output_root / 'evals' / 'review.json').write_text(
        '{"fully_correct": true, "confidence": 0.9, "requirement_results": [{"satisfied": true}, {"satisfied": true}], "repair_suggestions": []}',
        encoding='utf-8',
    )
    (output_root / 'evals' / 'report.json').write_text(
        '{"overall_score": 0.81}',
        encoding='utf-8',
    )
    run_summary = tmp_path / f'{candidate_key}-run-summary.json'
    run_summary.write_text(
        f'{{"output_root": "{output_root}"}}',
        encoding='utf-8',
    )

    report = build_create_seed_package_review_report(
        candidate_key=candidate_key,
        run_summary_path=run_summary,
    )

    assert report.review_exists is True
    assert report.report_exists is True
    assert report.fully_correct is True
    assert report.requirements_satisfied == 2
    assert report.verdict == 'ready_for_manual_use'


def test_build_create_seed_package_review_report_prefers_current_snapshot_run_summary(monkeypatch, tmp_path: Path):
    candidate_key = 'missing-fits-calibration-and-astropy-verification-workflow'
    monkeypatch.setattr(ops_post_apply, 'ROOT', tmp_path)

    older_output_root = tmp_path / '.generated-skills' / 'manual_rounds_run_20260413' / candidate_key
    (older_output_root / 'evals').mkdir(parents=True, exist_ok=True)
    (older_output_root / 'evals' / 'review.json').write_text(
        '{"fully_correct": true, "confidence": 0.8, "requirement_results": [{"satisfied": true}], "repair_suggestions": []}',
        encoding='utf-8',
    )
    (older_output_root / 'evals' / 'report.json').write_text(
        '{"overall_score": 0.75}',
        encoding='utf-8',
    )
    older_summary = tmp_path / '.generated-skills' / 'manual_rounds_run_20260413' / f'{candidate_key}-run-summary.json'
    older_summary.parent.mkdir(parents=True, exist_ok=True)
    older_summary.write_text(f'{{"output_root": "{older_output_root}"}}', encoding='utf-8')

    latest_output_root = tmp_path / '.generated-skills' / 'manual_rounds_run_20260414' / 'fits-calibration-astropy-followup-local-v2'
    (latest_output_root / 'evals').mkdir(parents=True, exist_ok=True)
    (latest_output_root / 'evals' / 'review.json').write_text(
        '{"fully_correct": true, "confidence": 0.99, "requirement_results": [{"satisfied": true}, {"satisfied": true}], "repair_suggestions": []}',
        encoding='utf-8',
    )
    (latest_output_root / 'evals' / 'report.json').write_text(
        '{"overall_score": 0.9922}',
        encoding='utf-8',
    )
    latest_summary = tmp_path / '.generated-skills' / 'manual_rounds_run_20260414' / 'fits-calibration-astropy-followup-local-v2-run-summary.json'
    latest_summary.parent.mkdir(parents=True, exist_ok=True)
    latest_summary.write_text(f'{{"output_root": "{latest_output_root}"}}', encoding='utf-8')

    snapshot = tmp_path / '.generated-skills' / 'ops_artifacts' / 'create_seed' / 'fits-calibration-astropy-followup-local-v2-package-review-current.json'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        f'{{"candidate_key": "{candidate_key}", "run_summary_path": "{latest_summary}"}}',
        encoding='utf-8',
    )

    report = build_create_seed_package_review_report(candidate_key=candidate_key)

    assert report.run_summary_path == str(latest_summary.resolve())
    assert report.overall_score == 0.9922
    assert report.requirements_satisfied == 2


def test_build_prior_pilot_trial_observation_report_marks_applied_trial_ready(tmp_path: Path):
    approval_state = OpsApprovalState(
        prior_pilot=[PriorPilotApprovalDecision(family='hf-trainer', decision='approved')]
    )
    pilot_report = _pilot_report()

    apply_ops_approval_state(
        create_seed_pack=RuntimeCreateSeedProposalPack(),
        prior_pilot_report=pilot_report,
        source_promotion_packs=[],
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=tmp_path / 'online_discovery.py',
    )

    report = build_prior_pilot_trial_observation_report(
        pilot_report=pilot_report,
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        fixture_root=SIMULATION_FIXTURE_ROOT,
    )

    assert report.decision_status == 'applied'
    assert report.artifact_exists is True
    assert report.trial_ready is True
    assert report.drifted_count == 0
    assert report.generic_promotion_risk == 0
    assert 'hf_trainer_pilot_ready' in report.scenarios_run


def test_build_prior_pilot_retrieval_trial_report_uses_real_repo_context(tmp_path: Path):
    approval_state = OpsApprovalState(
        prior_pilot=[PriorPilotApprovalDecision(family='hf-trainer', decision='approved')]
    )
    pilot_report = _pilot_report()

    apply_ops_approval_state(
        create_seed_pack=RuntimeCreateSeedProposalPack(),
        prior_pilot_report=pilot_report,
        source_promotion_packs=[],
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=tmp_path / 'online_discovery.py',
    )

    report = build_prior_pilot_retrieval_trial_report(
        pilot_report=pilot_report,
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
    )

    assert report.decision_status == 'applied'
    assert report.repo_path.endswith('tests/fixtures/hf_prior_trial_repo')
    assert report.selected_files_count > 0
    assert report.pilot_top_candidate == 'hf-trainer'
    assert report.generic_promotion_risk == 0
    assert report.verdict == 'ready_for_manual_trial'


def test_build_source_promotion_post_apply_report_marks_applied_source_stable(tmp_path: Path):
    round_report = load_public_source_curation_round_report(PUBLIC_SOURCE_CURATION_ROUND_REPORT)
    approval_state = OpsApprovalState(
        source_promotion=[
            SourcePromotionApprovalDecision(
                repo_full_name='alirezarezvani/claude-skills',
                decision='approved',
            )
        ]
    )
    collections_file = tmp_path / 'online_discovery.py'
    collections_file.write_text(
        "KNOWN_SKILL_COLLECTIONS = (\n    {'repo_full_name': 'alirezarezvani/claude-skills'},\n)\n",
        encoding='utf-8',
    )

    report = build_source_promotion_post_apply_report(
        round_report=round_report,
        approval_state=approval_state,
        collections_file=collections_file,
        fixture_root=SIMULATION_FIXTURE_ROOT,
    )

    assert report.decision_status == 'applied'
    assert report.collections_applied is True
    assert report.monitor_status == 'stable'
    assert report.drifted_count == 0
    assert report.matched_count == 1


def test_build_ops_refill_report_surfaces_next_hold_family_after_applied_round(tmp_path: Path):
    approval_state = OpsApprovalState(
        create_seed=[
            CreateSeedApprovalDecision(
                candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
                decision='approved',
            )
        ],
        prior_pilot=[PriorPilotApprovalDecision(family='hf-trainer', decision='approved')],
        source_promotion=[
            SourcePromotionApprovalDecision(
                repo_full_name='alirezarezvani/claude-skills',
                decision='approved',
            )
        ],
    )
    create_seed_pack = _create_seed_pack()
    pilot_report = _pilot_report()
    round_report = load_public_source_curation_round_report(PUBLIC_SOURCE_CURATION_ROUND_REPORT)
    collections_file = tmp_path / 'online_discovery.py'
    collections_file.write_text(
        "KNOWN_SKILL_COLLECTIONS = (\n    {'repo_full_name': 'alirezarezvani/claude-skills'},\n)\n",
        encoding='utf-8',
    )
    apply_ops_approval_state(
        create_seed_pack=create_seed_pack,
        prior_pilot_report=pilot_report,
        source_promotion_packs=[],
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=collections_file,
    )

    report = build_ops_refill_report(
        create_seed_pack=create_seed_pack,
        prior_pilot_report=pilot_report,
        round_report=round_report,
        approval_state=approval_state,
        artifact_root=tmp_path / 'ops-artifacts',
        collections_file=collections_file,
    )

    assert report.next_create_seed_candidate == ''
    assert report.next_prior_family_on_hold == 'deep-research'
    assert report.next_source_round_status == 'wait_for_post_apply_stability_before_next_live_round'
    assert report.applied_source_promotions == ['alirezarezvani/claude-skills']
