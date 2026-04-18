from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.public_source_verification import PublicSourcePromotionPack
from openclaw_skill_create.models.runtime_governance import (
    RuntimeCreateSeedProposal,
    RuntimeCreateSeedProposalPack,
    RuntimeOpsDecisionPack,
    RuntimePriorPilotExerciseReport,
    RuntimePriorPilotProfile,
    RuntimePriorPilotReport,
)
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.models.verify import OpsRoundbookReport, VerifyReport

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_ops_roundbook.py'


def test_run_ops_roundbook_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_ops_roundbook')
    monkeypatch.setattr(module, 'build_verify_report', lambda **kwargs: VerifyReport(mode='quick', overall_status='pass'))
    monkeypatch.setattr(
        module,
        'build_runtime_create_seed_proposal_pack',
        lambda **kwargs: RuntimeCreateSeedProposalPack(
            runs_processed=3,
            proposals=[
                RuntimeCreateSeedProposal(
                    candidate_key='hf-trainer-gaps',
                    suggested_title='HF Trainer Gaps',
                    suggested_description='Cover resume gaps.',
                    preview_request=SkillCreateRequestV6(task='cover resume gaps'),
                    recommended_decision='review',
                )
            ],
        ),
    )
    monkeypatch.setattr(
        module,
        '_load_prior_pilot_report',
        lambda path: RuntimePriorPilotReport(
            profiles=[
                RuntimePriorPilotProfile(
                    family='hf-trainer',
                    recommended_status='pilot',
                    allowed_families=['hf-trainer'],
                )
            ],
            allowed_families=['hf-trainer'],
        ),
    )
    monkeypatch.setattr(
        module,
        'build_runtime_prior_pilot_exercise_report',
        lambda **kwargs: RuntimePriorPilotExerciseReport(
            family='hf-trainer',
            verdict='ready_for_manual_pilot',
        ),
    )
    monkeypatch.setattr(module, 'load_public_source_curation_round_report', lambda path: object())
    monkeypatch.setattr(
        module,
        'build_public_source_promotion_pack',
        lambda **kwargs: PublicSourcePromotionPack(
            repo_full_name='alirezarezvani/claude-skills',
            verdict='ready_for_manual_promotion',
        ),
    )
    monkeypatch.setattr(
        module,
        'build_runtime_ops_decision_pack',
        lambda **kwargs: RuntimeOpsDecisionPack(
            decisions_pending=['create-seed:hf-trainer-gaps:review'],
        ),
    )
    monkeypatch.setattr(
        module,
        'build_ops_roundbook_report',
        lambda **kwargs: OpsRoundbookReport(
            verify_report=VerifyReport(mode='quick', overall_status='pass'),
            runtime_ops_decision_pack=RuntimeOpsDecisionPack(decisions_pending=['create-seed:hf-trainer-gaps:review']),
            prior_pilot_exercise=RuntimePriorPilotExerciseReport(family='hf-trainer', verdict='ready_for_manual_pilot'),
            source_promotion_pack=PublicSourcePromotionPack(
                repo_full_name='alirezarezvani/claude-skills',
                verdict='ready_for_manual_promotion',
            ),
            verification_status='pass',
            pending_create_seed_decisions=['hf-trainer-gaps'],
            pending_prior_pilot_decisions=['hf-trainer'],
            pending_source_promotion_decisions=['alirezarezvani/claude-skills'],
            overall_readiness='caution',
            summary='ok',
            markdown_summary='# Ops Roundbook\n\n- verification_status=pass',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_ops_roundbook.py', '--mode', 'quick', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Ops Roundbook')


def test_run_ops_roundbook_cli_reports_stage_failure(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_ops_roundbook_stage_failure')
    monkeypatch.setattr(
        module,
        'build_verify_report',
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError('comparison timed out')),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_ops_roundbook.py', '--mode', 'quick', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 1
    assert stdout == ''
    assert 'roundbook_stage=build_verify_report RuntimeError: comparison timed out' in stderr


def test_run_ops_roundbook_cli_supports_json(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_ops_roundbook_json')
    verify_report = VerifyReport(
        mode='quick',
        overall_status='pass',
        commands=[
            {
                'label': 'comparison',
                'command': ['python', 'scripts/run_skill_create_comparison.py'],
                'exit_code': 0,
                'stdout': 'x' * 5000,
                'stderr': '',
            }
        ],
        summary='ok',
        markdown_summary='# Verify\n\n- overall_status=pass',
    )
    monkeypatch.setattr(module, 'build_verify_report', lambda **kwargs: verify_report)
    monkeypatch.setattr(
        module,
        'build_runtime_create_seed_proposal_pack',
        lambda **kwargs: RuntimeCreateSeedProposalPack(
            runs_processed=3,
            proposals=[
                RuntimeCreateSeedProposal(
                    candidate_key='hf-trainer-gaps',
                    suggested_title='HF Trainer Gaps',
                    suggested_description='Cover resume gaps.',
                    preview_request=SkillCreateRequestV6(task='cover resume gaps'),
                    recommended_decision='review',
                )
            ],
        ),
    )
    monkeypatch.setattr(
        module,
        '_load_prior_pilot_report',
        lambda path: RuntimePriorPilotReport(
            profiles=[
                RuntimePriorPilotProfile(
                    family='hf-trainer',
                    recommended_status='pilot',
                    allowed_families=['hf-trainer'],
                )
            ],
            allowed_families=['hf-trainer'],
        ),
    )
    monkeypatch.setattr(
        module,
        'build_runtime_prior_pilot_exercise_report',
        lambda **kwargs: RuntimePriorPilotExerciseReport(
            family='hf-trainer',
            verdict='ready_for_manual_pilot',
        ),
    )
    monkeypatch.setattr(module, 'load_public_source_curation_round_report', lambda path: object())
    monkeypatch.setattr(
        module,
        'build_public_source_promotion_pack',
        lambda **kwargs: PublicSourcePromotionPack(
            repo_full_name='alirezarezvani/claude-skills',
            verdict='ready_for_manual_promotion',
        ),
    )
    monkeypatch.setattr(
        module,
        'build_runtime_ops_decision_pack',
        lambda **kwargs: RuntimeOpsDecisionPack(
            decisions_pending=['create-seed:hf-trainer-gaps:review'],
        ),
    )
    monkeypatch.setattr(
        module,
        'build_ops_roundbook_report',
        lambda **kwargs: OpsRoundbookReport(
            verify_report=verify_report,
            runtime_ops_decision_pack=RuntimeOpsDecisionPack(decisions_pending=['create-seed:hf-trainer-gaps:review']),
            prior_pilot_exercise=RuntimePriorPilotExerciseReport(family='hf-trainer', verdict='ready_for_manual_pilot'),
            source_promotion_pack=PublicSourcePromotionPack(
                repo_full_name='alirezarezvani/claude-skills',
                verdict='ready_for_manual_promotion',
            ),
            verification_status='pass',
            pending_create_seed_decisions=['hf-trainer-gaps'],
            pending_prior_pilot_decisions=['hf-trainer'],
            pending_source_promotion_decisions=['alirezarezvani/claude-skills'],
            overall_readiness='ready',
            summary='ok',
            markdown_summary='# Ops Roundbook\n\n- verification_status=pass',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_ops_roundbook.py', '--mode', 'quick', '--format', 'json'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['overall_readiness'] == 'ready'
    assert payload['verification_status'] == 'pass'
    assert payload['verify_report']['overall_status'] == 'pass'
    assert payload['verify_report']['skill_create_comparison_report'] is None
    assert len(payload['verify_report']['commands'][0]['stdout']) < 5000
