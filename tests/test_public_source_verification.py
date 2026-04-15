from __future__ import annotations

from openclaw_skill_create.models.online import SkillProvenance, SkillSourceCandidate
from openclaw_skill_create.models.public_source_verification import PublicSourceCandidateConfig
from openclaw_skill_create.services.public_source_verification import verify_public_source_candidates


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


class _FakeProvider:
    def __init__(self, *, collections, max_candidates, max_candidates_per_collection):
        seed = collections[0]
        self.repo_full_name = seed['repo_full_name']

    def list_candidates(self):
        mapping = {
            'example/accept': [
                _candidate('astropy', 'example/accept'),
                _candidate('pymatgen', 'example/accept'),
                _candidate('xarray-astro', 'example/accept'),
                _candidate('fits-summary', 'example/accept'),
            ],
            'example/reject': [
                _candidate('keyword-research', 'example/reject'),
            ],
            'example/manual': [
                _candidate('deep-research', 'example/manual'),
                _candidate('implementation-planning', 'example/manual'),
                _candidate('astropy', 'example/manual'),
                _candidate('fits-summary', 'example/manual'),
            ],
        }
        return mapping[self.repo_full_name]


def test_verify_public_source_candidates_classifies_accept_reject_and_manual_review():
    configs = [
        PublicSourceCandidateConfig(
            repo_full_name='example/accept',
            root_paths=['skills'],
            verification_task='Find astronomy skills.',
        ),
        PublicSourceCandidateConfig(
            repo_full_name='example/reject',
            root_paths=['skills'],
            verification_task='Find SEO skills.',
        ),
        PublicSourceCandidateConfig(
            repo_full_name='example/manual',
            root_paths=['skills'],
            verification_task='Find planning and research skills.',
        ),
    ]

    def existing_candidates(_task: str):
        return [
            _candidate('deep-research', 'existing/research'),
            _candidate('implementation-planning', 'existing/planning'),
            _candidate('keyword-research', 'existing/seo'),
        ]

    report = verify_public_source_candidates(
        candidate_configs=configs,
        provider_factory=_FakeProvider,
        existing_candidates_resolver=existing_candidates,
    )

    verdicts = {item.repo_full_name: item.verdict for item in report.candidates}
    assert verdicts['example/accept'] == 'accept'
    assert verdicts['example/reject'] == 'reject'
    assert verdicts['example/manual'] == 'manual_review'
    assert report.accepted_repos == ['example/accept']
    assert report.promoted_repos == ['example/accept']

    accept_result = next(item for item in report.candidates if item.repo_full_name == 'example/accept')
    manual_result = next(item for item in report.candidates if item.repo_full_name == 'example/manual')
    reject_result = next(item for item in report.candidates if item.repo_full_name == 'example/reject')

    assert accept_result.smoke_required is True
    assert accept_result.selected_for_default is True
    assert manual_result.smoke_required is False
    assert manual_result.selected_for_default is False
    assert reject_result.selected_for_default is False
