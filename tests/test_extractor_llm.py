from __future__ import annotations

from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.extractor_llm import synthesize_repo_findings_from_signals


class DummyRepoContext:
    def model_dump(self, mode: str = "json"):
        return {
            "selected_files": [
                {"path": "scripts/run_analysis.py", "kind": "script"},
                {"path": "docs/api.md", "kind": "doc"},
            ]
        }


class DummySignalBundle:
    def model_dump(self, mode: str = "json"):
        return {
            "scripts": ["scripts/run_analysis.py"],
            "docs": ["docs/api.md"],
            "workflows": ["run-analysis"],
        }


def test_extractor_llm_returns_repo_findings_model():
    request = SkillCreateRequestV6(task="extract repo findings", enable_llm_extractor=True)

    def fake_runner(messages, model):
        assert messages
        return """
        {
          "repos": [
            {
              "repo_path": "/tmp/sample_repo",
              "summary": "Small Python repo with reusable script and docs.",
              "detected_stack": ["python"],
              "entrypoints": [],
              "scripts": [],
              "docs": [],
              "configs": [],
              "workflows": [],
              "triggers": [],
              "candidate_resources": {
                "references": ["references/workflows.md"],
                "scripts": ["scripts/run_analysis.py"]
              },
              "risks": []
            }
          ],
          "cross_repo_signals": [],
          "overall_recommendation": "Good candidate for a repo-aware skill."
        }
        """

    findings = synthesize_repo_findings_from_signals(
        request=request,
        repo_context=DummyRepoContext(),
        signal_bundle=DummySignalBundle(),
        llm_runner=fake_runner,
        model="codex-vip/gpt-5.4",
    )

    assert findings.repos
    assert findings.repos[0].repo_path == "/tmp/sample_repo"
    assert findings.repos[0].candidate_resources.scripts == ["scripts/run_analysis.py"]
    assert findings.overall_recommendation
