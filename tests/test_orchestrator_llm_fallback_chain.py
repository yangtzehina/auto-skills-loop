from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.diagnostics import Diagnostics, ValidationResult
from openclaw_skill_create.models.findings import RepoFindings
from openclaw_skill_create.models.patterns import ExtractedSkillPatterns, ExtractionContext
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.orchestrator import run_skill_create


def make_repo_findings() -> RepoFindings:
    return RepoFindings(
        repos=[],
        cross_repo_signals=[],
        overall_recommendation="fallback extractor findings",
    )


def make_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name="sample-python-skill",
        skill_type="mixed",
        objective="Generate a repo-aware skill",
        why_this_shape="fallback planner path",
        files_to_create=[
            PlannedFile(
                path="SKILL.md",
                purpose="Top-level skill entry",
                source_basis=["repo_findings"],
            )
        ],
        files_to_update=[],
        files_to_keep=[],
        generation_order=["SKILL.md"],
    )


def make_artifacts() -> Artifacts:
    return Artifacts(
        files=[
            ArtifactFile(
                path="SKILL.md",
                content=(
                    "---\n"
                    "name: sample-python-skill\n"
                    "description: Repo-aware skill for sample-python-skill\n"
                    "---\n\n"
                    "# sample-python-skill\n\n"
                    "Use this skill when the repo-grounded workflow matches the task.\n"
                ),
                content_type="text/markdown",
                generated_from=["skill_plan", "repo_findings"],
                status="new",
            )
        ]
    )


def make_pass_diagnostics() -> Diagnostics:
    return Diagnostics(
        warnings=[],
        errors=[],
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=True,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=[],
            unsupported_claims_found=False,
            repairable_issue_types=[],
            non_repairable_issue_types=[],
            failure_reasons=[],
            repair_recommended=False,
        ),
        notes=[],
    )


def make_patterns() -> ExtractedSkillPatterns:
    return ExtractedSkillPatterns(
        pattern_set_id='esp_orchestrator_001',
        extraction=ExtractionContext(
            run_id='run-test-orchestrator',
            created_at='2026-03-25T13:00:00+08:00',
            extractor_version='test',
        ),
    )


def preload_repo_context(_request):
    return {
        "repo_paths": [],
        "selected_files": [{"path": "scripts/run_analysis.py"}],
        "notes": [],
    }


def persist_artifacts(**kwargs):
    return {
        "applied": False,
        "reason": "test stub",
        "severity": kwargs["severity"],
        "file_count": len(kwargs["artifacts"].files),
    }


def test_orchestrator_full_fallback_chain_survives_llm_runner_failures(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_artifacts())
    monkeypatch.setattr(mod, "run_validator", lambda **kwargs: make_pass_diagnostics())

    request = SkillCreateRequestV6(
        task="build skill",
        enable_llm_extractor=True,
        enable_llm_planner=True,
        enable_llm_skill_md=True,
        extracted_patterns=make_patterns(),
    )

    def bad_runner(messages, model):
        raise RuntimeError("upstream llm failure")

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        extractor_llm_runner=bad_runner,
        planner_llm_runner=bad_runner,
        generator_llm_runner=bad_runner,
    )

    assert response.severity == "pass"
    assert response.repo_findings is not None
    assert response.extracted_patterns is not None
    assert response.extracted_patterns.pattern_set_id == 'esp_orchestrator_001'
    assert response.skill_plan is not None
    assert response.artifacts is not None
    assert response.diagnostics is not None
    assert response.persistence is not None
    assert response.persistence["severity"] == "pass"
    assert response.artifacts.files[0].path == "SKILL.md"


def test_orchestrator_extract_mode_short_circuits_after_extractor(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())

    planner_called = {"value": False}
    generator_called = {"value": False}
    validator_called = {"value": False}

    def planner_stub(**kwargs):
        planner_called["value"] = True
        return make_skill_plan()

    def generator_stub(**kwargs):
        generator_called["value"] = True
        return make_artifacts()

    def validator_stub(**kwargs):
        validator_called["value"] = True
        return make_pass_diagnostics()

    monkeypatch.setattr(mod, "run_planner", planner_stub)
    monkeypatch.setattr(mod, "run_generator", generator_stub)
    monkeypatch.setattr(mod, "run_validator", validator_stub)

    request = SkillCreateRequestV6(
        task="extract only",
        mode="extract",
        extracted_patterns=make_patterns(),
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
    )

    assert response.severity == "pass"
    assert response.repo_findings is not None
    assert response.extracted_patterns is not None
    assert response.skill_plan is None
    assert response.artifacts is None
    assert response.diagnostics is None

    assert planner_called["value"] is False
    assert generator_called["value"] is False
    assert validator_called["value"] is False


def test_orchestrator_plan_mode_short_circuits_after_planner(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())

    generator_called = {"value": False}
    validator_called = {"value": False}

    def generator_stub(**kwargs):
        generator_called["value"] = True
        return make_artifacts()

    def validator_stub(**kwargs):
        validator_called["value"] = True
        return make_pass_diagnostics()

    monkeypatch.setattr(mod, "run_generator", generator_stub)
    monkeypatch.setattr(mod, "run_validator", validator_stub)

    request = SkillCreateRequestV6(
        task="plan only",
        output_mode="plan",
        extracted_patterns=make_patterns(),
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
    )

    assert response.severity == "pass"
    assert response.repo_findings is not None
    assert response.extracted_patterns is not None
    assert response.skill_plan is not None
    assert response.artifacts is None
    assert response.diagnostics is None

    assert generator_called["value"] is False
    assert validator_called["value"] is False
