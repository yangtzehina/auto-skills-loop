from __future__ import annotations

from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.planner_llm import synthesize_skill_plan
from openclaw_skill_create.services.planner_rules import build_planning_seed


class DummyRepoContext:
    def model_dump(self, mode: str = 'json'):
        return {'selected_files': [{'path': 'scripts/run_analysis.py'}]}


class DummyRepoFindings:
    def model_dump(self, mode: str = 'json'):
        return {
            'repos': [
                {
                    'repo_path': '/tmp/repo',
                    'summary': 'Python repo with one script and some docs',
                    'detected_stack': ['python'],
                }
            ],
            'cross_repo_signals': [],
            'overall_recommendation': 'Good candidate for a skill',
        }


def test_planner_llm_returns_skill_plan_model():
    request = SkillCreateRequestV6(
        task='plan skill',
        enable_llm_planner=True,
        skill_name_hint='sample-python-skill',
    )
    repo_context = DummyRepoContext()
    repo_findings = DummyRepoFindings()
    planning_seed = build_planning_seed(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
    )

    def fake_runner(messages, model):
        assert messages
        return '''
        {
          "skill_name": "sample-python-skill",
          "skill_type": "mixed",
          "objective": "Generate a repo-aware skill from grounded findings",
          "why_this_shape": "The repo has at least one reusable script and clear workflow hints.",
          "files_to_create": [
            {
              "path": "SKILL.md",
              "purpose": "Top-level skill instructions and routing guidance",
              "source_basis": ["repo_findings.workflows", "repo_findings.triggers"]
            }
          ],
          "files_to_update": [],
          "files_to_keep": [],
          "merge_strategy": {
            "mode": "preserve-and-merge",
            "preserve_existing_files": true,
            "replace_conflicting_sections": true
          },
          "content_budget": {
            "skill_md_max_lines": 300,
            "reference_file_targets": {},
            "prefer_script_over_inline_code": true
          },
          "generation_order": ["SKILL.md"]
        }
        '''

    plan = synthesize_skill_plan(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        planning_seed=planning_seed,
        llm_runner=fake_runner,
        model='codex-vip/gpt-5.4',
    )

    assert plan.skill_name == 'sample-python-skill'
    assert plan.files_to_create[0].path == 'SKILL.md'
