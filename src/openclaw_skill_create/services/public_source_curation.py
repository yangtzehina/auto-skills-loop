from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from ..models.public_source_verification import (
    PublicSourceCandidateConfig,
    PublicSourceCurationRoundReport,
    PublicSourcePromotionPack,
)
from ..models.ops_approval import OpsApprovalState
from .ops_approval import apply_approval_to_source_promotion_pack
from .public_source_verification import verify_public_source_candidates
from .simulation import build_simulation_suite_report

ROOT = Path(__file__).resolve().parents[3]


def render_public_source_curation_round_markdown(report: PublicSourceCurationRoundReport) -> str:
    lines = [
        '# Public Source Curation Round',
        '',
        f'- Summary: {report.summary}',
        f'- rehearsal_passed={report.rehearsal_passed}',
        f'- live_applied={report.live_applied}',
        f'- promoted_repos={report.promoted_repos}',
    ]
    live_report = report.live_report
    if live_report is not None:
        lines.extend(
            [
                '',
                '## Live Verification',
                f'- accepted={len(live_report.accepted_repos or [])}',
                f'- rejected={len(live_report.rejected_repos or [])}',
                f'- manual_review={len(live_report.manual_review_repos or [])}',
            ]
        )
    return '\n'.join(lines).strip()


def build_public_source_curation_round(
    *,
    candidate_configs: Iterable[PublicSourceCandidateConfig],
    fixture_root: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    provider_factory: Optional[Callable[..., Any]] = None,
    existing_candidates_resolver: Optional[Callable[[str], list[Any]]] = None,
) -> PublicSourceCurationRoundReport:
    rehearsal = build_simulation_suite_report(
        mode='source-curation',
        fixture_root=fixture_root,
        scenario_names=scenario_names,
    )
    rehearsal_passed = rehearsal.drifted_count == 0 and rehearsal.invalid_fixture_count == 0
    if not rehearsal_passed:
        report = PublicSourceCurationRoundReport(
            rehearsal_matched_count=rehearsal.matched_count,
            rehearsal_drifted_count=rehearsal.drifted_count,
            rehearsal_invalid_fixture_count=rehearsal.invalid_fixture_count,
            rehearsal_passed=False,
            live_applied=False,
            promoted_repos=[],
            summary=(
                f'Public source curation round skipped live verification: '
                f'rehearsal matched={rehearsal.matched_count} '
                f'drifted={rehearsal.drifted_count} invalid_fixture={rehearsal.invalid_fixture_count}'
            ),
        )
        report.markdown_summary = render_public_source_curation_round_markdown(report)
        return report

    live_report = verify_public_source_candidates(
        candidate_configs=candidate_configs,
        provider_factory=provider_factory,
        existing_candidates_resolver=existing_candidates_resolver,
    )
    report = PublicSourceCurationRoundReport(
        rehearsal_matched_count=rehearsal.matched_count,
        rehearsal_drifted_count=rehearsal.drifted_count,
        rehearsal_invalid_fixture_count=rehearsal.invalid_fixture_count,
        rehearsal_passed=True,
        live_applied=True,
        live_report=live_report,
        promoted_repos=list(live_report.promoted_repos or []),
        summary=(
            f'Public source curation round complete: '
            f'rehearsal_matched={rehearsal.matched_count} '
            f'accepted={len(live_report.accepted_repos or [])} '
            f'promoted={len(live_report.promoted_repos or [])}'
        ),
    )
    report.markdown_summary = render_public_source_curation_round_markdown(report)
    return report


def load_public_source_curation_round_report(path: Path) -> PublicSourceCurationRoundReport:
    target = path.expanduser().resolve()
    if not target.exists() or not target.is_file():
        raise ValueError(f'Not a file: {target}')
    try:
        payload = json.loads(target.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON report: {exc.msg}') from exc
    return PublicSourceCurationRoundReport.model_validate(payload)


def _promotion_regression_requirements(repo_full_name: str, verification_task: str) -> list[str]:
    task = str(verification_task or '').strip().lower()
    requirements: list[str] = []
    if 'seo' in task:
        requirements.append('Protect SEO specialists from generic research/workflow candidates.')
    if 'amazon' in task:
        requirements.append('Protect Amazon specialists from generic research/workflow candidates.')
    if 'business' in task:
        requirements.append('Protect business workflow specialists from generic research/workflow candidates.')
    if not requirements:
        requirements.append(
            f'Protect domain-specific skills from `{repo_full_name}` against generic research/workflow candidates.'
        )
    return requirements


def _promotion_missing_requirements(
    repo_full_name: str,
    required_ranking_regressions: list[str],
    required_smoke: list[str],
) -> list[str]:
    if repo_full_name != 'alirezarezvani/claude-skills':
        return []
    missing: list[str] = []
    online_discovery_tests = (ROOT / 'tests' / 'test_online_discovery.py').read_text(encoding='utf-8')
    if 'test_score_skill_candidate_prefers_claude_skills_domain_candidate_for_amazon_seo_tasks' not in online_discovery_tests:
        missing.append(required_ranking_regressions[0])
    if len(required_ranking_regressions) > 1 and 'test_score_skill_candidate_prefers_claude_skills_domain_candidate_for_amazon_seo_tasks' not in online_discovery_tests:
        missing.append(required_ranking_regressions[1])
    if len(required_ranking_regressions) > 2 and 'test_score_skill_candidate_prefers_claude_skills_domain_candidate_for_business_workflow_tasks' not in online_discovery_tests:
        missing.append(required_ranking_regressions[2])
    if required_smoke:
        smoke_expected = ROOT / 'tests' / 'fixtures' / 'simulation' / 'smoke_chain' / 'online_reuse_claude_skills_business_adapt' / 'expected' / 'result.json'
        if not smoke_expected.exists():
            missing.extend(required_smoke)
    return missing


def render_public_source_promotion_pack_markdown(pack: PublicSourcePromotionPack) -> str:
    lines = [
        '# Public Source Promotion Pack',
        '',
        f'- Repo: {pack.repo_full_name}',
        f'- Verdict: {pack.verdict}',
        f'- requirements_satisfied={pack.requirements_satisfied}',
        f'- approval_decision={pack.approval_decision}',
        f'- decision_status={pack.decision_status}',
        f'- promotion_candidate={pack.promotion_candidate}',
        f'- candidate_count={pack.candidate_count}',
        f'- overlap_assessment={pack.overlap_assessment}',
        f'- Summary: {pack.summary}',
        '',
        '## Required Ranking Regressions',
    ]
    if not pack.required_ranking_regressions:
        lines.append('- No additional ranking regressions are required.')
    else:
        for item in pack.required_ranking_regressions:
            lines.append(f'- {item}')
    lines.extend(['', '## Required Smoke'])
    if not pack.required_smoke:
        lines.append('- No additional smoke coverage is required yet.')
    else:
        for item in pack.required_smoke:
            lines.append(f'- {item}')
    lines.extend(['', '## Missing Requirements'])
    if not pack.missing_requirements:
        lines.append('- None')
    else:
        for item in pack.missing_requirements:
            lines.append(f'- {item}')
    lines.extend(['', '## Seed Patch Preview', f'- {pack.seed_patch_preview}'])
    return '\n'.join(lines).strip()


def build_public_source_promotion_pack(
    *,
    round_report: PublicSourceCurationRoundReport,
    repo_full_name: str = 'alirezarezvani/claude-skills',
    approval_state: Optional[OpsApprovalState] = None,
    collections_file: Optional[Path] = None,
) -> PublicSourcePromotionPack:
    live_report = round_report.live_report
    live_candidate = None
    if live_report is not None:
        live_candidate = next(
            (item for item in list(live_report.candidates or []) if item.repo_full_name == repo_full_name),
            None,
        )
    promotion_candidate = bool(
        round_report.rehearsal_passed
        and live_candidate is not None
        and live_candidate.verdict == 'accept'
        and repo_full_name in list(round_report.promoted_repos or [])
    )
    required_ranking_regressions = (
        _promotion_regression_requirements(repo_full_name, live_candidate.verification_task)
        if live_candidate is not None
        else [f'Protect promoted skills from `{repo_full_name}` with domain-specific ranking coverage.']
    )
    required_smoke = (
        [f'Add one domain smoke covering discovery -> ranking -> reuse -> eval scaffold for `{repo_full_name}`.']
        if live_candidate is not None and live_candidate.smoke_required
        else []
    )
    missing_requirements = _promotion_missing_requirements(
        repo_full_name,
        required_ranking_regressions=required_ranking_regressions,
        required_smoke=required_smoke,
    )
    seed_patch_preview = {
        'target_constant': 'KNOWN_SKILL_COLLECTIONS',
        'operation': 'append_if_manually_approved',
        'seed': {
            'repo_full_name': repo_full_name,
            'ecosystem': live_candidate.ecosystem if live_candidate is not None else 'claude',
            'root_paths': list(live_candidate.root_paths or []) if live_candidate is not None else ['skills', '.claude/skills', ''],
            'priority': int(live_candidate.priority or 100) if live_candidate is not None else 35,
        },
    }
    pack = PublicSourcePromotionPack(
        repo_full_name=repo_full_name,
        promotion_candidate=promotion_candidate,
        requirements_satisfied=bool(promotion_candidate and not missing_requirements),
        candidate_count=int(live_candidate.candidate_count or 0) if live_candidate is not None else 0,
        overlap_assessment=str(live_candidate.overlap_assessment or 'none') if live_candidate is not None else 'none',
        reason=str(live_candidate.reason or '') if live_candidate is not None else 'No matching live candidate was found.',
        required_ranking_regressions=required_ranking_regressions,
        required_smoke=required_smoke,
        missing_requirements=missing_requirements,
        seed_patch_preview=seed_patch_preview,
        verdict='ready_for_manual_promotion' if promotion_candidate and not missing_requirements else 'hold',
        summary=(
            f'Public source promotion pack complete: repo={repo_full_name} '
            f'promotion_candidate={promotion_candidate} rehearsal_passed={round_report.rehearsal_passed} '
            f'missing_requirements={len(missing_requirements)}'
        ),
    )
    pack = apply_approval_to_source_promotion_pack(
        pack,
        approval_state=approval_state or OpsApprovalState(),
        collections_file=collections_file,
    )
    pack.markdown_summary = render_public_source_promotion_pack_markdown(pack)
    return pack
