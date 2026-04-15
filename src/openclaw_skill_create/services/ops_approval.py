from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models.ops_approval import (
    CreateSeedApprovalDecision,
    CreateSeedHandoffArtifact,
    CreateSeedManualRoundPack,
    OpsApprovalApplyReport,
    OpsApprovalState,
    PriorPilotApprovalDecision,
    PriorPilotManualTrialPack,
    PriorPilotOverrideArtifact,
    SourcePromotionApprovalDecision,
)
from ..models.public_source_verification import PublicSourcePromotionPack
from ..models.runtime_governance import (
    RuntimeCreateSeedProposal,
    RuntimeCreateSeedProposalPack,
    RuntimePriorPilotProfile,
    RuntimePriorPilotReport,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_APPROVAL_MANIFEST = ROOT / 'scripts' / 'ops_approval_manifest.json'
DEFAULT_OPS_ARTIFACT_ROOT = ROOT / '.generated-skills' / 'ops_artifacts'
DEFAULT_COLLECTIONS_FILE = ROOT / 'src' / 'openclaw_skill_create' / 'services' / 'online_discovery.py'
SCIENTIFIC_FIXTURE_REPO = ROOT / 'tests' / 'fixtures' / 'scientific_reuse_eval_repo'


def _slug(value: str) -> str:
    text = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or '').strip())
    while '--' in text:
        text = text.replace('--', '-')
    return text.strip('-') or 'item'


def load_ops_approval_state(path: Optional[Path] = None) -> OpsApprovalState:
    target = Path(path or DEFAULT_APPROVAL_MANIFEST).expanduser()
    if not target.exists() or not target.is_file():
        return OpsApprovalState()
    raw = target.read_text(encoding='utf-8').strip()
    if not raw:
        return OpsApprovalState()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid approval manifest: {exc.msg}') from exc
    if not isinstance(payload, dict):
        raise ValueError('Approval manifest must be a JSON object')
    return OpsApprovalState.model_validate(payload)


def _find_create_seed_decision(approval_state: OpsApprovalState, candidate_key: str) -> CreateSeedApprovalDecision:
    return next(
        (
            item
            for item in list(approval_state.create_seed or [])
            if item.candidate_key == candidate_key
        ),
        CreateSeedApprovalDecision(candidate_key=candidate_key),
    )


def _find_prior_pilot_decision(approval_state: OpsApprovalState, family: str) -> PriorPilotApprovalDecision:
    return next(
        (
            item
            for item in list(approval_state.prior_pilot or [])
            if item.family == family
        ),
        PriorPilotApprovalDecision(family=family),
    )


def _find_source_promotion_decision(
    approval_state: OpsApprovalState,
    repo_full_name: str,
) -> SourcePromotionApprovalDecision:
    return next(
        (
            item
            for item in list(approval_state.source_promotion or [])
            if item.repo_full_name == repo_full_name
        ),
        SourcePromotionApprovalDecision(repo_full_name=repo_full_name),
    )


def create_seed_handoff_path(candidate_key: str, artifact_root: Optional[Path] = None) -> Path:
    root = Path(artifact_root or DEFAULT_OPS_ARTIFACT_ROOT).expanduser().resolve()
    return root / 'create_seed' / f'{_slug(candidate_key)}.json'


def prior_pilot_profile_path(family: str, artifact_root: Optional[Path] = None) -> Path:
    root = Path(artifact_root or DEFAULT_OPS_ARTIFACT_ROOT).expanduser().resolve()
    return root / 'prior_pilot' / f'{_slug(family)}.json'


def source_promotion_is_applied(
    repo_full_name: str,
    *,
    collections_file: Optional[Path] = None,
) -> bool:
    target = Path(collections_file or DEFAULT_COLLECTIONS_FILE).expanduser().resolve()
    if not target.exists() or not target.is_file():
        return False
    return f"'{repo_full_name}'" in target.read_text(encoding='utf-8')


def apply_approval_to_create_seed_proposal(
    proposal: RuntimeCreateSeedProposal,
    *,
    approval_state: OpsApprovalState,
    artifact_root: Optional[Path] = None,
) -> RuntimeCreateSeedProposal:
    decision = _find_create_seed_decision(approval_state, proposal.candidate_key)
    artifact_path = create_seed_handoff_path(proposal.candidate_key, artifact_root=artifact_root)
    if decision.decision == 'approved':
        status = 'applied' if artifact_path.exists() else 'approved_not_applied'
    else:
        status = 'pending'
    return proposal.model_copy(
        update={
            'approval_decision': decision.decision,
            'decision_status': status,
            'handoff_artifact_path': str(artifact_path) if decision.decision == 'approved' else '',
        }
    )


def apply_approval_to_prior_pilot_profile(
    profile: RuntimePriorPilotProfile,
    *,
    approval_state: OpsApprovalState,
    artifact_root: Optional[Path] = None,
) -> RuntimePriorPilotProfile:
    decision = _find_prior_pilot_decision(approval_state, profile.family)
    artifact_path = prior_pilot_profile_path(profile.family, artifact_root=artifact_root)
    if decision.decision == 'approved':
        status = 'applied' if artifact_path.exists() else 'approved_not_applied'
    else:
        status = 'pending'
    return profile.model_copy(
        update={
            'approval_decision': decision.decision,
            'decision_status': status,
            'profile_artifact_path': str(artifact_path) if decision.decision == 'approved' else '',
        }
    )


def apply_approval_to_source_promotion_pack(
    pack: PublicSourcePromotionPack,
    *,
    approval_state: OpsApprovalState,
    collections_file: Optional[Path] = None,
) -> PublicSourcePromotionPack:
    decision = _find_source_promotion_decision(approval_state, pack.repo_full_name)
    applied = source_promotion_is_applied(pack.repo_full_name, collections_file=collections_file)
    if decision.decision == 'approved':
        status = 'applied' if applied else 'approved_not_applied'
    else:
        status = 'pending'
    return pack.model_copy(
        update={
            'approval_decision': decision.decision,
            'decision_status': status,
        }
    )


def summarize_decision_statuses(
    *,
    create_seed_candidates: list[RuntimeCreateSeedProposal],
    prior_pilot_candidates: list[RuntimePriorPilotProfile],
    source_promotion_candidates: list[PublicSourcePromotionPack],
) -> dict[str, list[str]]:
    summary = {
        'pending': [],
        'approved_not_applied': [],
        'applied': [],
    }
    for item in list(create_seed_candidates or []):
        summary[item.decision_status].append(f'create-seed:{item.candidate_key}')
    for item in list(prior_pilot_candidates or []):
        summary[item.decision_status].append(f'prior-pilot:{item.family}')
    for item in list(source_promotion_candidates or []):
        summary[item.decision_status].append(f'source-promotion:{item.repo_full_name}')
    return summary


def build_create_seed_handoff_artifact(
    proposal: RuntimeCreateSeedProposal,
    *,
    artifact_root: Optional[Path] = None,
) -> CreateSeedHandoffArtifact:
    artifact_path = create_seed_handoff_path(proposal.candidate_key, artifact_root=artifact_root)
    return CreateSeedHandoffArtifact(
        candidate_key=proposal.candidate_key,
        suggested_title=proposal.suggested_title,
        suggested_description=proposal.suggested_description,
        representative_task_summaries=list(proposal.representative_task_summaries or []),
        requirement_gaps=list(proposal.distilled_requirement_gaps or []),
        preview_request=proposal.preview_request.model_copy(deep=True),
        source_run_ids=list(proposal.source_run_ids or []),
        artifact_path=str(artifact_path),
        summary=(
            f'Create-seed handoff artifact ready for `{proposal.candidate_key}` at {artifact_path}'
        ),
    )


def build_prior_pilot_override_artifact(
    profile: RuntimePriorPilotProfile,
    *,
    artifact_root: Optional[Path] = None,
) -> PriorPilotOverrideArtifact:
    artifact_path = prior_pilot_profile_path(profile.family, artifact_root=artifact_root)
    return PriorPilotOverrideArtifact(
        family=profile.family,
        request_overrides=dict(profile.request_overrides_preview or {}),
        generic_promotion_risk=int(profile.generic_promotion_risk or 0),
        artifact_path=str(artifact_path),
        summary=f'Prior pilot override artifact ready for `{profile.family}` at {artifact_path}',
    )


def _seed_fixture_inputs(proposal: RuntimeCreateSeedProposal) -> list[str]:
    inputs: list[str] = []
    if any(
        token in str(proposal.candidate_key or '').lower()
        for token in ('fits', 'astropy', 'astronomy')
    ):
        inputs.append(str(SCIENTIFIC_FIXTURE_REPO))
    for item in list(proposal.representative_task_summaries or [])[:2]:
        if item and item not in inputs:
            inputs.append(item)
    for item in list(proposal.distilled_requirement_gaps or [])[:2]:
        text = f'Requirement gap: {item}'
        if item and text not in inputs:
            inputs.append(text)
    return inputs


def render_create_seed_manual_round_pack_markdown(pack: CreateSeedManualRoundPack) -> str:
    lines = [
        '# Create Seed Manual Round Pack',
        '',
        f'- candidate_key={pack.candidate_key}',
        f'- approval_decision={pack.approval_decision}',
        f'- status={pack.status}',
        f'- handoff_artifact_path={pack.handoff_artifact_path or "(not materialized)"}',
        f'- Summary: {pack.summary}',
        '',
        '## Recommended Fixture Inputs',
    ]
    if not pack.recommended_fixture_inputs:
        lines.append('- None')
    else:
        for item in pack.recommended_fixture_inputs:
            lines.append(f'- {item}')
    lines.extend(['', '## Launch Checklist'])
    if not pack.launch_checklist:
        lines.append('- None')
    else:
        for item in pack.launch_checklist:
            lines.append(f'- {item}')
    lines.extend(['', '## Preview Request'])
    lines.append(f'- skill_name_hint={pack.preview_request.skill_name_hint}')
    lines.append(f'- task={pack.preview_request.task}')
    return '\n'.join(lines).strip()


def build_create_seed_manual_round_pack(
    *,
    create_seed_pack: RuntimeCreateSeedProposalPack,
    approval_state: OpsApprovalState,
    candidate_key: str = 'missing-fits-calibration-and-astropy-verification-workflow',
    artifact_root: Optional[Path] = None,
) -> CreateSeedManualRoundPack:
    target_key = str(candidate_key or '').strip()
    proposal = next(
        (item for item in list(create_seed_pack.proposals or []) if item.candidate_key == target_key),
        None,
    )
    if proposal is None:
        raise ValueError(f'Create-seed proposal not found: {target_key}')
    approved_proposal = apply_approval_to_create_seed_proposal(
        proposal,
        approval_state=approval_state,
        artifact_root=artifact_root,
    )
    launch_checklist = [
        'Confirm the approval manifest still marks this create-seed candidate as approved before launching a manual round.',
        'Review the preview SkillCreateRequestV6 payload and representative FITS/Astropy task summaries.',
        'Use the recommended fixture inputs to sanity-check the manual round before any real generator run.',
        'After the manual round, rerun verify and ops roundbook so the decision loop stays closed.',
    ]
    pack = CreateSeedManualRoundPack(
        candidate_key=approved_proposal.candidate_key,
        approval_decision=approved_proposal.approval_decision,
        status=approved_proposal.decision_status,
        handoff_artifact_path=approved_proposal.handoff_artifact_path,
        suggested_title=approved_proposal.suggested_title,
        suggested_description=approved_proposal.suggested_description,
        representative_task_summaries=list(approved_proposal.representative_task_summaries or []),
        requirement_gaps=list(approved_proposal.distilled_requirement_gaps or []),
        preview_request=approved_proposal.preview_request.model_copy(deep=True),
        recommended_fixture_inputs=_seed_fixture_inputs(approved_proposal),
        launch_checklist=launch_checklist,
        summary=(
            f'Create-seed manual round pack ready: '
            f'candidate={approved_proposal.candidate_key} status={approved_proposal.decision_status}'
        ),
    )
    pack.markdown_summary = render_create_seed_manual_round_pack_markdown(pack)
    return pack


def _trial_tasks_for_family(family: str) -> list[str]:
    normalized = str(family or '').strip().lower()
    if normalized == 'hf-trainer':
        return [
            'Fix the Hugging Face trainer resume workflow for interrupted checkpoints.',
            'Debug trainer evaluation resume logic without letting generic research helpers take top-1.',
            'Validate that the allowlisted hf-trainer prior improves retrieval without changing unrelated families.',
        ]
    return [f'Run one focused opt-in prior trial for `{family}` with the allowlist override enabled.']


def render_prior_pilot_manual_trial_markdown(pack: PriorPilotManualTrialPack) -> str:
    lines = [
        '# Runtime Prior Manual Trial Pack',
        '',
        f'- family={pack.family}',
        f'- approval_decision={pack.approval_decision}',
        f'- status={pack.status}',
        f'- verdict={pack.verdict}',
        f'- profile_artifact_path={pack.profile_artifact_path or "(not materialized)"}',
        f'- Summary: {pack.summary}',
        '',
        '## Recommended Trial Tasks',
    ]
    if not pack.recommended_trial_tasks:
        lines.append('- None')
    else:
        for item in pack.recommended_trial_tasks:
            lines.append(f'- {item}')
    lines.extend(['', '## Expected Safe Signals'])
    if not pack.expected_safe_signals:
        lines.append('- None')
    else:
        for item in pack.expected_safe_signals:
            lines.append(f'- {item}')
    lines.extend(['', '## Rollback Steps'])
    if not pack.rollback_steps:
        lines.append('- None')
    else:
        for item in pack.rollback_steps:
            lines.append(f'- {item}')
    lines.extend(['', '## Request Overrides', f'- {pack.request_overrides}'])
    return '\n'.join(lines).strip()


def build_prior_pilot_manual_trial_pack(
    *,
    pilot_report: RuntimePriorPilotReport,
    family: str = 'hf-trainer',
    approval_state: OpsApprovalState,
    artifact_root: Optional[Path] = None,
    generic_promotion_risk: int = 0,
    top_1_changes: int = 0,
    exercise_verdict: str = 'hold',
) -> PriorPilotManualTrialPack:
    target_family = str(family or '').strip()
    profile = next(
        (item for item in list(pilot_report.profiles or []) if item.family == target_family),
        None,
    )
    if profile is None:
        raise ValueError(f'Prior pilot profile not found: {target_family}')
    approved_profile = apply_approval_to_prior_pilot_profile(
        profile,
        approval_state=approval_state,
        artifact_root=artifact_root,
    )
    expected_safe_signals = [
        'Only the allowlisted family receives a runtime effectiveness prior.',
        f'generic_promotion_risk stays at 0 (current={int(generic_promotion_risk or 0)}).',
        f'top_1_changes stays bounded and explainable across checked-in scenarios (current={int(top_1_changes or 0)}).',
    ]
    rollback_steps = [
        'Stop passing enable_runtime_effectiveness_prior=true in the request overrides.',
        "Clear runtime_effectiveness_allowed_families so discovery falls back to the default no-prior path.",
        'Rerun verify and ops roundbook to confirm the pilot is no longer active.',
    ]
    verdict = 'hold'
    if (
        approved_profile.approval_decision == 'approved'
        and exercise_verdict == 'ready_for_manual_pilot'
        and int(generic_promotion_risk or 0) == 0
    ):
        verdict = 'ready_for_manual_trial'
    pack = PriorPilotManualTrialPack(
        family=approved_profile.family,
        approval_decision=approved_profile.approval_decision,
        status=approved_profile.decision_status,
        profile_artifact_path=approved_profile.profile_artifact_path,
        request_overrides=dict(approved_profile.request_overrides_preview or {}),
        recommended_trial_tasks=_trial_tasks_for_family(approved_profile.family),
        expected_safe_signals=expected_safe_signals,
        rollback_steps=rollback_steps,
        verdict=verdict,
        summary=(
            f'Runtime prior manual trial pack ready: '
            f'family={approved_profile.family} status={approved_profile.decision_status} verdict={verdict}'
        ),
    )
    pack.markdown_summary = render_prior_pilot_manual_trial_markdown(pack)
    return pack


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def _format_seed_snippet(seed: dict[str, object]) -> str:
    lines = [
        '    {',
        f"        'repo_full_name': {seed.get('repo_full_name')!r},",
        f"        'ecosystem': {seed.get('ecosystem', 'codex')!r},",
        f"        'root_paths': {list(seed.get('root_paths') or [])!r},",
    ]
    if seed.get('root_dir_prefixes'):
        lines.append(f"        'root_dir_prefixes': {list(seed.get('root_dir_prefixes') or [])!r},")
    lines.append(f"        'priority': {int(seed.get('priority', 100) or 100)},")
    lines.append('    },')
    return '\n'.join(lines) + '\n'


def apply_source_promotion_seed(
    *,
    pack: PublicSourcePromotionPack,
    collections_file: Optional[Path] = None,
) -> bool:
    target = Path(collections_file or DEFAULT_COLLECTIONS_FILE).expanduser().resolve()
    if not target.exists() or not target.is_file():
        raise ValueError(f'Collections file not found: {target}')
    if source_promotion_is_applied(pack.repo_full_name, collections_file=target):
        return False
    text = target.read_text(encoding='utf-8')
    marker = 'KNOWN_SKILL_COLLECTIONS: tuple[dict[str, Any], ...] = (\n'
    start = text.find(marker)
    if start < 0:
        raise ValueError(f'Could not locate KNOWN_SKILL_COLLECTIONS in {target}')
    insert_at = text.find('\n)\n\nSEMANTIC_TOKEN_GROUPS', start)
    if insert_at < 0:
        raise ValueError(f'Could not locate end of KNOWN_SKILL_COLLECTIONS in {target}')
    updated = text[:insert_at] + _format_seed_snippet(dict(pack.seed_patch_preview.get('seed') or {})) + text[insert_at:]
    target.write_text(updated, encoding='utf-8')
    return True


def apply_ops_approval_state(
    *,
    create_seed_pack: RuntimeCreateSeedProposalPack,
    prior_pilot_report: RuntimePriorPilotReport,
    source_promotion_packs: list[PublicSourcePromotionPack],
    approval_state: OpsApprovalState,
    artifact_root: Optional[Path] = None,
    collections_file: Optional[Path] = None,
) -> OpsApprovalApplyReport:
    handoffs: list[CreateSeedHandoffArtifact] = []
    pilot_profiles: list[PriorPilotOverrideArtifact] = []
    applied_source_promotions: list[str] = []
    skipped_source_promotions: list[str] = []

    for proposal in list(create_seed_pack.proposals or []):
        decision = _find_create_seed_decision(approval_state, proposal.candidate_key)
        if decision.decision != 'approved':
            continue
        artifact = build_create_seed_handoff_artifact(proposal, artifact_root=artifact_root)
        _write_json(Path(artifact.artifact_path), artifact.model_dump(mode='json'))
        handoffs.append(artifact)

    for profile in list(prior_pilot_report.profiles or []):
        decision = _find_prior_pilot_decision(approval_state, profile.family)
        if decision.decision != 'approved':
            continue
        artifact = build_prior_pilot_override_artifact(profile, artifact_root=artifact_root)
        _write_json(Path(artifact.artifact_path), artifact.model_dump(mode='json'))
        pilot_profiles.append(artifact)

    updated_source_packs: list[PublicSourcePromotionPack] = []
    for pack in list(source_promotion_packs or []):
        decision = _find_source_promotion_decision(approval_state, pack.repo_full_name)
        if decision.decision != 'approved':
            updated_source_packs.append(pack)
            continue
        if (
            pack.verdict != 'ready_for_manual_promotion'
            or not bool(pack.requirements_satisfied)
            or list(pack.missing_requirements or [])
        ):
            skipped_source_promotions.append(pack.repo_full_name)
            updated_source_packs.append(pack)
            continue
        changed = apply_source_promotion_seed(pack=pack, collections_file=collections_file)
        if changed:
            applied_source_promotions.append(pack.repo_full_name)
        updated_source_packs.append(pack)

    create_seed_candidates = [
        apply_approval_to_create_seed_proposal(item, approval_state=approval_state, artifact_root=artifact_root)
        for item in list(create_seed_pack.proposals or [])
        if item.recommended_decision in {'review', 'defer'}
    ]
    prior_pilot_candidates = [
        apply_approval_to_prior_pilot_profile(item, approval_state=approval_state, artifact_root=artifact_root)
        for item in list(prior_pilot_report.profiles or [])
        if item.recommended_status in {'pilot', 'eligible'}
    ]
    source_candidates = [
        apply_approval_to_source_promotion_pack(item, approval_state=approval_state, collections_file=collections_file)
        for item in list(updated_source_packs or [])
    ]
    status_groups = summarize_decision_statuses(
        create_seed_candidates=create_seed_candidates,
        prior_pilot_candidates=prior_pilot_candidates,
        source_promotion_candidates=source_candidates,
    )
    decision_status_summary = {
        key: len(list(value or []))
        for key, value in status_groups.items()
    }
    report = OpsApprovalApplyReport(
        approval_state=approval_state,
        create_seed_handoffs=handoffs,
        prior_pilot_profiles=pilot_profiles,
        applied_source_promotions=applied_source_promotions,
        skipped_source_promotions=skipped_source_promotions,
        decision_status_summary=decision_status_summary,
        summary=(
            f'Ops approval apply complete: '
            f'create_seed_handoffs={len(handoffs)} '
            f'prior_pilot_profiles={len(pilot_profiles)} '
            f'applied_source_promotions={len(applied_source_promotions)} '
            f'skipped_source_promotions={len(skipped_source_promotions)}'
        ),
    )
    report.markdown_summary = (
        '# Ops Approval Apply Report\n\n'
        f'- Summary: {report.summary}\n'
        f'- applied_source_promotions={report.applied_source_promotions}\n'
        f'- skipped_source_promotions={report.skipped_source_promotions}\n'
        f'- decision_status_summary={report.decision_status_summary}'
    )
    return report
