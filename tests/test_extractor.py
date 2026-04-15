from __future__ import annotations

from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.extractor import run_extractor


def test_run_extractor_uses_fallback_when_llm_disabled():
    request = SkillCreateRequestV6(task="extract", enable_llm_extractor=False)
    result = run_extractor(
        request=request,
        repo_context={
            "repos": [
                {
                    "repo_path": "/tmp/repo",
                    "selected_files": [
                        {"path": "README.md", "tags": ["doc"], "preview": "# Demo"},
                        {"path": "scripts/run.py", "tags": ["script"], "preview": "print('hi')"},
                    ],
                }
            ]
        },
    )

    assert result.overall_recommendation == "fallback extractor findings"
    assert result.requirements
    assert {item.source_kind for item in result.requirements} >= {"doc", "script"}


def test_run_extractor_uses_llm_when_enabled():
    request = SkillCreateRequestV6(task="extract", enable_llm_extractor=True)

    def fake_runner(messages, model):
        return """
        {
          "repos": [
            {
              "repo_path": "/tmp/repo",
              "summary": "Repo summary",
              "detected_stack": ["python"],
              "entrypoints": [],
              "scripts": [],
              "docs": [],
              "configs": [],
              "workflows": [],
              "triggers": [],
              "candidate_resources": {"references": [], "scripts": []},
              "risks": []
            }
          ],
          "cross_repo_signals": [],
          "overall_recommendation": "Use llm findings"
        }
        """

    result = run_extractor(
        request=request,
        repo_context={
            "repos": [
                {
                    "repo_path": "/tmp/repo",
                    "selected_files": [
                        {"path": "README.md", "tags": ["doc"], "preview": "# Demo"},
                        {"path": "scripts/run.py", "tags": ["script"], "preview": "print('hi')"},
                    ],
                }
            ]
        },
        llm_runner=fake_runner,
    )

    assert result.overall_recommendation == "Use llm findings"
    assert result.repos[0].repo_path == "/tmp/repo"
    assert result.requirements


def test_run_extractor_falls_back_on_llm_error():
    request = SkillCreateRequestV6(task="extract", enable_llm_extractor=True)

    def bad_runner(messages, model):
        raise RuntimeError("upstream failure")

    result = run_extractor(
        request=request,
        repo_context={
            "repos": [
                {
                    "repo_path": "/tmp/repo",
                    "selected_files": [
                        {"path": "README.md", "tags": ["doc"], "preview": "# Demo"},
                    ],
                }
            ]
        },
        llm_runner=bad_runner,
    )

    assert result.overall_recommendation == "fallback extractor findings"
    assert result.requirements[0].evidence_paths == ["README.md"]
