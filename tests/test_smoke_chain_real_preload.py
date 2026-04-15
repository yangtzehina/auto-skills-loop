from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.orchestrator import run_skill_create


def test_smoke_chain_with_real_preload(tmp_path: Path):
    (tmp_path / 'README.md').write_text('# Demo\n\nRepo intro\n', encoding='utf-8')
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts' / 'run.py').write_text('print("hi")\n', encoding='utf-8')
    (tmp_path / '.github').mkdir()
    (tmp_path / '.github' / 'workflows').mkdir()
    (tmp_path / '.github' / 'workflows' / 'ci.yml').write_text('name: ci\n', encoding='utf-8')

    request = SkillCreateRequestV6(
        task='build a repo-aware skill',
        repo_paths=[str(tmp_path)],
        skill_name_hint='example-skill',
        enable_llm_extractor=False,
        enable_llm_planner=False,
        enable_llm_skill_md=False,
    )

    response = run_skill_create(
        request,
        persistence_policy=PersistencePolicy(),
        fail_fast_on_validation_fail=False,
    )

    assert response.repo_findings is not None
    assert response.repo_findings.repos
    assert response.repo_findings.requirements
    repo = response.repo_findings.repos[0]
    assert repo.docs
    assert repo.scripts
    assert response.skill_plan is not None
    assert response.skill_plan.requirements
    assert response.artifacts is not None
    assert response.quality_review is not None
