from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from ..models.online import SkillSourceCandidate
from ..models.public_source_verification import (
    PublicSourceCandidateConfig,
    PublicSourceVerificationReport,
    PublicSourceVerificationResult,
)
from .online_discovery import GitHubCollectionDiscoveryProvider, discover_online_skills


def _family_key(candidate: SkillSourceCandidate) -> str:
    return (candidate.name or candidate.candidate_id or '').strip().lower()


def _make_seed(config: PublicSourceCandidateConfig) -> dict[str, Any]:
    return {
        'repo_full_name': config.repo_full_name,
        'ecosystem': config.ecosystem,
        'root_paths': list(config.root_paths or []),
        'priority': config.priority,
    }


def _overlap_assessment(
    *,
    candidates: list[SkillSourceCandidate],
    existing_candidates: list[SkillSourceCandidate],
    repo_full_name: str,
) -> str:
    family_keys = {_family_key(item) for item in candidates if _family_key(item)}
    if not family_keys:
        return 'none'
    baseline_keys = {
        _family_key(item)
        for item in existing_candidates
        if item.provenance.repo_full_name != repo_full_name and _family_key(item)
    }
    overlap = len(family_keys & baseline_keys)
    ratio = overlap / max(len(family_keys), 1)
    if ratio >= 0.6:
        return 'high'
    if ratio >= 0.25:
        return 'medium'
    return 'low'


def verify_public_source_candidates(
    *,
    candidate_configs: Iterable[PublicSourceCandidateConfig],
    provider_factory: Optional[Callable[..., Any]] = None,
    existing_candidates_resolver: Optional[Callable[[str], list[SkillSourceCandidate]]] = None,
) -> PublicSourceVerificationReport:
    provider_factory = provider_factory or GitHubCollectionDiscoveryProvider

    def default_existing_candidates(task: str) -> list[SkillSourceCandidate]:
        return discover_online_skills(
            task=task,
            repo_context={'selected_files': []},
            providers=[
                GitHubCollectionDiscoveryProvider(
                    max_candidates=8,
                    max_candidates_per_collection=2,
                )
            ],
            limit=6,
        )

    existing_candidates_resolver = existing_candidates_resolver or default_existing_candidates
    existing_candidates_cache: dict[str, list[SkillSourceCandidate]] = {}

    results: list[PublicSourceVerificationResult] = []
    for config in list(candidate_configs):
        provider = provider_factory(
            collections=[_make_seed(config)],
            max_candidates=8,
            max_candidates_per_collection=6,
        )
        try:
            candidates = list(provider.list_candidates())
        except Exception as exc:
            candidates = []
            verdict = 'manual_review'
            reason = f'Verification failed: {exc}'
            overlap = 'none'
            structure_supported = False
        else:
            structure_supported = bool(candidates)
            verification_task = config.verification_task
            if verification_task not in existing_candidates_cache:
                existing_candidates_cache[verification_task] = existing_candidates_resolver(verification_task)
            overlap = _overlap_assessment(
                candidates=candidates,
                existing_candidates=existing_candidates_cache[verification_task],
                repo_full_name=config.repo_full_name,
            )
            if len(candidates) < 4:
                verdict = 'reject'
                reason = f'Only discovered {len(candidates)} candidate(s)'
            elif overlap == 'high':
                verdict = 'reject'
                reason = 'High overlap with existing seeded families'
            elif overlap == 'medium':
                verdict = 'manual_review'
                reason = 'Moderate overlap with existing seeded families'
            elif not structure_supported:
                verdict = 'reject'
                reason = 'Repository structure is not supported by current seed rules'
            else:
                verdict = 'accept'
                reason = 'Discovered enough low-overlap candidates with supported structure'

        results.append(
            PublicSourceVerificationResult(
                repo_full_name=config.repo_full_name,
                ecosystem=config.ecosystem,
                root_paths=list(config.root_paths or []),
                priority=config.priority,
                verification_task=config.verification_task,
                notes=config.notes,
                candidate_count=len(candidates),
                sample_skill_names=[item.name for item in candidates[:6]],
                overlap_assessment=overlap,
                structure_supported=structure_supported,
                verdict=verdict,
                reason=reason,
                smoke_required=(verdict == 'accept'),
            )
        )

    promoted_repos = [
        item.repo_full_name
        for item in sorted(
            (result for result in results if result.verdict == 'accept'),
            key=lambda item: (int(item.priority or 100), item.repo_full_name),
        )[:1]
    ]
    for item in results:
        item.selected_for_default = item.repo_full_name in promoted_repos
    report = PublicSourceVerificationReport(
        candidates=results,
        accepted_repos=[item.repo_full_name for item in results if item.verdict == 'accept'],
        rejected_repos=[item.repo_full_name for item in results if item.verdict == 'reject'],
        manual_review_repos=[item.repo_full_name for item in results if item.verdict == 'manual_review'],
        promoted_repos=promoted_repos,
        summary=(
            f'Public source verification complete: '
            f'accept={sum(1 for item in results if item.verdict == "accept")} '
            f'reject={sum(1 for item in results if item.verdict == "reject")} '
            f'manual_review={sum(1 for item in results if item.verdict == "manual_review")} '
            f'promoted={len(promoted_repos)}'
        ),
    )
    return report
