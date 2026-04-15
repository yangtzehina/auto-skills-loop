from __future__ import annotations

from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.orchestrator import run_skill_create


def test_smoke_chain_full_flow():
    request = SkillCreateRequestV6(
        task="build a repo-aware skill",
        repo_paths=["/tmp/example-repo"],
        skill_name_hint="example-skill",
        enable_llm_extractor=False,
        enable_llm_planner=False,
        enable_llm_skill_md=False,
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        persistence_policy=PersistencePolicy(),
        fail_fast_on_validation_fail=False,
    )

    assert response.repo_findings is not None
    assert response.skill_plan is not None
    assert response.artifacts is not None
    assert response.diagnostics is not None
    assert response.persistence is not None
    assert response.artifacts.files[0].path == "SKILL.md"
    assert response.timings.finished_at_ms is not None
    assert response.severity in {"pass", "warn", "fail"}
