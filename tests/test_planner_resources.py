from __future__ import annotations

from openclaw_skill_create.models.findings import CandidateResources, RepoFinding, RepoFindings
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.planner_rules import build_planning_seed, fallback_skill_plan_from_seed


def test_build_planning_seed_consumes_candidate_resources():
    request = SkillCreateRequestV6(task='plan', skill_name_hint='repo-aware-skill')
    findings = RepoFindings(
        repos=[
            RepoFinding(
                repo_path='/tmp/repo',
                summary='Demo repo',
                candidate_resources=CandidateResources(
                    references=['references/usage.md'],
                    scripts=['scripts/run_analysis.py'],
                ),
            )
        ],
        overall_recommendation='Good candidate for skill generation',
    )

    seed = build_planning_seed(
        request=request,
        repo_context={'selected_files': []},
        repo_findings=findings,
    )

    paths = [file.path for file in seed.candidate_files]
    assert 'SKILL.md' in paths
    assert 'references/usage.md' in paths
    assert 'scripts/run_analysis.py' in paths
    assert any('candidate_resources.references' in r for r in seed.rationale)
    assert any('candidate_resources.scripts' in r for r in seed.rationale)


def test_fallback_skill_plan_keeps_candidate_resource_files():
    request = SkillCreateRequestV6(task='plan', skill_name_hint='repo-aware-skill')
    findings = RepoFindings(
        repos=[
            RepoFinding(
                repo_path='/tmp/repo',
                summary='Demo repo',
                candidate_resources=CandidateResources(
                    references=['references/usage.md'],
                    scripts=['scripts/run_analysis.py'],
                ),
            )
        ]
    )

    seed = build_planning_seed(
        request=request,
        repo_context={'selected_files': []},
        repo_findings=findings,
    )
    plan = fallback_skill_plan_from_seed(seed)

    paths = [file.path for file in plan.files_to_create]
    assert 'references/usage.md' in paths
    assert 'scripts/run_analysis.py' in paths
