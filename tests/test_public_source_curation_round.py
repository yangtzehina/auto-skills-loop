from __future__ import annotations

from openclaw_skill_create.models.online import SkillProvenance, SkillSourceCandidate
from openclaw_skill_create.models.public_source_verification import PublicSourceCandidateConfig
from openclaw_skill_create.models.simulation import SimulationSuiteReport
from openclaw_skill_create.services.public_source_curation import build_public_source_curation_round


def _candidate(name: str, repo_full_name: str) -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id=f'{repo_full_name.replace("/", "-")}-{name}',
        name=name,
        description=f'{name} workflow',
        trigger_phrases=[name],
        tags=[name],
        provenance=SkillProvenance(
            source_type='community',
            ecosystem='codex',
            repo_full_name=repo_full_name,
            ref='main',
            skill_path=f'skills/{name}',
            skill_url=f'https://github.com/{repo_full_name}/blob/main/skills/{name}/SKILL.md',
        ),
    )


class _AcceptProvider:
    def __init__(self, *, collections, max_candidates, max_candidates_per_collection):
        seed = collections[0]
        self.repo_full_name = seed['repo_full_name']

    def list_candidates(self):
        return [
            _candidate('astropy', self.repo_full_name),
            _candidate('pymatgen', self.repo_full_name),
            _candidate('xarray-astro', self.repo_full_name),
            _candidate('fits-summary', self.repo_full_name),
        ]


def test_build_public_source_curation_round_runs_live_after_rehearsal(monkeypatch):
    monkeypatch.setattr(
        'openclaw_skill_create.services.public_source_curation.build_simulation_suite_report',
        lambda **kwargs: SimulationSuiteReport(
            mode='source-curation',
            fixture_root='fixtures',
            matched_count=3,
            drifted_count=0,
            invalid_fixture_count=0,
            summary='ok',
        ),
    )

    report = build_public_source_curation_round(
        candidate_configs=[
            PublicSourceCandidateConfig(
                repo_full_name='example/accept',
                root_paths=['skills'],
                verification_task='Find astronomy skills.',
            )
        ],
        provider_factory=_AcceptProvider,
        existing_candidates_resolver=lambda task: [],
    )

    assert report.rehearsal_passed is True
    assert report.live_applied is True
    assert report.promoted_repos == ['example/accept']


def test_build_public_source_curation_round_skips_live_when_rehearsal_drifts(monkeypatch):
    monkeypatch.setattr(
        'openclaw_skill_create.services.public_source_curation.build_simulation_suite_report',
        lambda **kwargs: SimulationSuiteReport(
            mode='source-curation',
            fixture_root='fixtures',
            matched_count=1,
            drifted_count=1,
            invalid_fixture_count=0,
            summary='drift',
        ),
    )

    report = build_public_source_curation_round(
        candidate_configs=[
            PublicSourceCandidateConfig(
                repo_full_name='example/accept',
                root_paths=['skills'],
                verification_task='Find astronomy skills.',
            )
        ],
    )

    assert report.rehearsal_passed is False
    assert report.live_applied is False
    assert report.live_report is None
