from __future__ import annotations

import tempfile
from pathlib import Path

from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.orchestrator import run_skill_create


def seed_demo_repo(root: Path) -> None:
    (root / 'README.md').write_text('# Demo\n\nRepo intro\n', encoding='utf-8')
    (root / 'scripts').mkdir(parents=True, exist_ok=True)
    (root / 'scripts' / 'run.py').write_text('print("hi")\n', encoding='utf-8')
    (root / '.github' / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / '.github' / 'workflows' / 'ci.yml').write_text('name: ci\n', encoding='utf-8')


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='skill-create-v6-smoke-') as tmp:
        repo_root = Path(tmp) / 'demo-repo'
        repo_root.mkdir(parents=True, exist_ok=True)
        seed_demo_repo(repo_root)

        request = SkillCreateRequestV6(
            task='build a repo-aware skill',
            repo_paths=[str(repo_root)],
            skill_name_hint='example-skill',
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

        repo = response.repo_findings.repos[0] if response.repo_findings and response.repo_findings.repos else None
        print('severity:', response.severity)
        print('repo_path:', repo.repo_path if repo else 'missing')
        print('repo_docs:', repo.docs if repo else [])
        print('repo_scripts:', repo.scripts if repo else [])
        print('skill_plan:', response.skill_plan.skill_name if response.skill_plan else 'missing')
        print('artifacts:', [f.path for f in (response.artifacts.files if response.artifacts else [])])
        print('diagnostics:', response.diagnostics.validation.summary if response.diagnostics else [])
        print('persistence:', response.persistence)
        print('timings_finished_at_ms:', response.timings.finished_at_ms)


if __name__ == '__main__':
    main()
