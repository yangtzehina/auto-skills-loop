from __future__ import annotations

from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.orchestrator import run_skill_create


def main() -> None:
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

    print("severity:", response.severity)
    print("repo_findings:", "ok" if response.repo_findings is not None else "missing")
    print("skill_plan:", response.skill_plan.skill_name if response.skill_plan else "missing")
    print("artifacts:", [f.path for f in (response.artifacts.files if response.artifacts else [])])
    print("diagnostics:", response.diagnostics.validation.summary if response.diagnostics else [])
    print("persistence:", response.persistence)
    print("timings_finished_at_ms:", response.timings.finished_at_ms)


if __name__ == "__main__":
    main()
