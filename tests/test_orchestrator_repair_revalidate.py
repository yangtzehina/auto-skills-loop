from __future__ import annotations

from dataclasses import dataclass

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.diagnostics import Diagnostics, ValidationResult
from openclaw_skill_create.models.evaluation import (
    BenchmarkDimensionResult,
    EvaluationRunReport,
    TriggerEvalCaseResult,
)
from openclaw_skill_create.models.findings import RepoFindings
from openclaw_skill_create.models.online import SkillBlueprint, SkillProvenance, SkillSourceCandidate
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.orchestrator import derive_validation_severity, run_skill_create


def make_repo_findings() -> RepoFindings:
    return RepoFindings(
        repos=[],
        cross_repo_signals=[],
        overall_recommendation="good candidate for skill generation",
    )


def make_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name="sample-python-skill",
        skill_type="mixed",
        objective="Generate a repo-aware skill",
        why_this_shape="integration repair test",
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


def make_eval_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name="sample-python-skill",
        skill_type="mixed",
        objective="Generate a repo-aware skill with eval scaffolds",
        why_this_shape="integration repair eval test",
        files_to_create=[
            PlannedFile(path="SKILL.md", purpose="Top-level skill entry", source_basis=["repo_findings"]),
            PlannedFile(path="evals/trigger_eval.json", purpose="Trigger evaluation", source_basis=["request"]),
            PlannedFile(path="evals/output_eval.json", purpose="Output evaluation", source_basis=["request"]),
            PlannedFile(path="evals/benchmark.json", purpose="Benchmark evaluation", source_basis=["request"]),
        ],
        files_to_update=[],
        files_to_keep=[],
        generation_order=["SKILL.md", "evals/trigger_eval.json", "evals/output_eval.json", "evals/benchmark.json"],
    )


def make_online_candidate() -> SkillSourceCandidate:
    return SkillSourceCandidate(
        candidate_id='openai-notion',
        name='notion-knowledge-capture',
        description='Capture conversations into structured Notion pages',
        provenance=SkillProvenance(
            source_type='official',
            ecosystem='codex',
            repo_full_name='openai/skills',
            ref='main',
            skill_path='skills/.curated/notion-knowledge-capture',
            skill_url='https://github.com/openai/skills/blob/main/skills/.curated/notion-knowledge-capture/SKILL.md',
        ),
        score=0.7,
    )


def make_online_blueprint() -> SkillBlueprint:
    return SkillBlueprint(
        blueprint_id='openai-notion__blueprint',
        name='notion-knowledge-capture',
        description='Capture conversations into structured Notion pages',
        provenance=make_online_candidate().provenance,
    )


def make_invalid_artifacts() -> Artifacts:
    return Artifacts(
        files=[
            ArtifactFile(
                path="SKILL.md",
                content=(
                    "# sample-python-skill\n\n"
                    "This file is missing frontmatter entirely.\n"
                ),
                content_type="text/markdown",
                generated_from=["skill_plan", "repo_findings", "llm"],
                status="new",
            )
        ]
    )


def make_repaired_artifacts() -> Artifacts:
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
                generated_from=["skill_plan", "repo_findings", "repair"],
                status="updated",
            )
        ]
    )


def make_invalid_eval_artifacts() -> Artifacts:
    return Artifacts(
        files=[
            ArtifactFile(
                path="SKILL.md",
                content=(
                    "---\n"
                    "name: sample-python-skill\n"
                    "description: Repo-aware skill for sample-python-skill. Use when Codex needs to capture repo workflows.\n"
                    "---\n\n"
                    "# sample-python-skill\n"
                ),
                content_type="text/markdown",
                generated_from=["skill_plan", "repo_findings"],
                status="new",
            ),
            ArtifactFile(
                path="evals/trigger_eval.json",
                content="{}",
                content_type="application/json",
                generated_from=["skill_plan"],
                status="new",
            ),
            ArtifactFile(
                path="evals/output_eval.json",
                content="",
                content_type="application/json",
                generated_from=["skill_plan"],
                status="new",
            ),
            ArtifactFile(
                path="evals/benchmark.json",
                content='{"skill_name":"sample-python-skill","dimensions":[]}\n',
                content_type="application/json",
                generated_from=["skill_plan"],
                status="new",
            ),
        ]
    )


def make_fail_diagnostics() -> Diagnostics:
    return Diagnostics(
        warnings=["SKILL.md frontmatter is invalid"],
        errors=[],
        validation=ValidationResult(
            frontmatter_valid=False,
            skill_md_within_budget=True,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=[],
            unsupported_claims_found=False,
            repairable_issue_types=["invalid_frontmatter"],
            non_repairable_issue_types=[],
            failure_reasons=["SKILL.md frontmatter is invalid"],
            repair_recommended=True,
        ),
        notes=[],
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


def make_over_budget_diagnostics() -> Diagnostics:
    return Diagnostics(
        warnings=['SKILL.md exceeds configured line budget'],
        errors=[],
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=False,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=[],
            unsupported_claims_found=False,
            repairable_issue_types=['skill_md_over_budget'],
            non_repairable_issue_types=[],
            failure_reasons=['SKILL.md exceeds configured line budget'],
            repair_recommended=True,
        ),
        notes=[],
    )



def make_script_quality_diagnostics() -> Diagnostics:
    return Diagnostics(
        warnings=['Script non-code-like: scripts/run.py', 'Script wrapper-like: scripts/run.py'],
        errors=[],
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=True,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=[],
            unsupported_claims_found=False,
            repairable_issue_types=['script_non_code_like', 'script_wrapper_like'],
            non_repairable_issue_types=[],
            failure_reasons=['Script non-code-like: scripts/run.py', 'Script wrapper-like: scripts/run.py'],
            repair_recommended=True,
        ),
        notes=[],
    )


def make_invalid_eval_diagnostics() -> Diagnostics:
    return Diagnostics(
        warnings=['Invalid eval scaffold: evals/trigger_eval.json'],
        errors=[],
        validation=ValidationResult(
            frontmatter_valid=True,
            skill_md_within_budget=True,
            planned_files_present=True,
            unnecessary_files_present=False,
            unreferenced_reference_files=[],
            unsupported_claims_found=False,
            repairable_issue_types=['invalid_eval_scaffold'],
            non_repairable_issue_types=[],
            failure_reasons=['Invalid eval scaffold: evals/trigger_eval.json'],
            repair_recommended=True,
        ),
        notes=[],
    )


def make_eval_report_with_benchmarks() -> EvaluationRunReport:
    return EvaluationRunReport(
        skill_name="sample-python-skill",
        trigger_results=[
            TriggerEvalCaseResult(
                case_id="capture-notes",
                expected_trigger=True,
                predicted_trigger=True,
                score=1.0,
                passed=True,
                matched_terms=["capture", "notes"],
            )
        ],
        output_results=[],
        benchmark_results=[
            BenchmarkDimensionResult(
                name="task_alignment",
                score=0.88,
                rationale="Domain-specific workflow stays focused on the requested task.",
            ),
            BenchmarkDimensionResult(
                name="adaptation_quality",
                score=0.91,
                rationale="Artifacts adapt public references into repo-ready steps.",
            ),
        ],
        overall_score=0.89,
        summary=["Synthetic evaluation report for orchestrator note coverage."],
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


@dataclass
class RepairResult:
    applied: bool
    repaired_artifacts: Artifacts


def test_orchestrator_repair_then_revalidate(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_invalid_artifacts())

    validator_calls = {"count": 0}

    def validator_stub(**kwargs):
        validator_calls["count"] += 1
        if validator_calls["count"] == 1:
            return make_fail_diagnostics()
        return make_pass_diagnostics()

    monkeypatch.setattr(mod, "run_validator", validator_stub)

    def repair_stub(**kwargs):
        return RepairResult(
            applied=True,
            repaired_artifacts=make_repaired_artifacts(),
        )

    request = SkillCreateRequestV6(
        task="build skill",
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        repair_fn=repair_stub,
    )

    assert validator_calls["count"] == 2
    assert response.severity == "pass"
    assert response.artifacts is not None
    assert response.diagnostics is not None
    assert response.artifacts.files[0].status == "updated"
    assert response.timings.repair_attempted is True
    assert response.timings.repair_applied is True
    assert response.timings.repair_iteration_count == 1
    assert response.diagnostics is not None
    assert any(
        "Repair attempt 1: repairable/non-repairable issues 1 -> 0" in note
        for note in response.diagnostics.notes
    )


def test_orchestrator_honors_multiple_repair_attempts(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_invalid_artifacts())

    validator_calls = {"count": 0}

    def validator_stub(**kwargs):
        validator_calls["count"] += 1
        if validator_calls["count"] < 3:
            return make_fail_diagnostics()
        return make_pass_diagnostics()

    monkeypatch.setattr(mod, "run_validator", validator_stub)

    repair_calls = {"count": 0}

    def repair_stub(**kwargs):
        repair_calls["count"] += 1
        return RepairResult(
            applied=True,
            repaired_artifacts=make_repaired_artifacts(),
        )

    request = SkillCreateRequestV6(
        task="build skill",
        enable_repair=True,
        max_repair_attempts=2,
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        repair_fn=repair_stub,
    )

    assert repair_calls["count"] == 2
    assert validator_calls["count"] == 3
    assert response.severity == "pass"
    assert response.timings.repair_attempted is True
    assert response.timings.repair_applied is True
    assert response.timings.repair_iteration_count == 2


def test_orchestrator_surfaces_online_discovery_context(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_repaired_artifacts())
    monkeypatch.setattr(mod, "run_validator", lambda **kwargs: make_pass_diagnostics())

    request = SkillCreateRequestV6(
        task="capture conversations into notion",
        online_skill_candidates=[make_online_candidate()],
        online_skill_blueprints=[make_online_blueprint()],
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        repair_fn=None,
    )

    assert response.online_skill_candidates
    assert response.online_skill_candidates[0].name == 'notion-knowledge-capture'
    assert response.online_skill_blueprints
    assert response.online_skill_blueprints[0].blueprint_id == 'openai-notion__blueprint'
    assert response.diagnostics is not None


def test_orchestrator_auto_enables_eval_scaffold_when_online_context_present(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    captured = {}

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())

    def planner_stub(**kwargs):
        captured['enable_eval_scaffold'] = kwargs['request'].enable_eval_scaffold
        return make_skill_plan()

    monkeypatch.setattr(mod, "run_planner", planner_stub)
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_repaired_artifacts())
    monkeypatch.setattr(mod, "run_validator", lambda **kwargs: make_pass_diagnostics())

    request = SkillCreateRequestV6(
        task="capture conversations into notion",
        enable_online_skill_discovery=True,
        online_skill_candidates=[make_online_candidate()],
        online_skill_blueprints=[make_online_blueprint()],
    )

    run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        repair_fn=None,
    )

    assert captured['enable_eval_scaffold'] is True


def test_validation_severity_fails_on_invalid_eval_scaffold():
    assert derive_validation_severity(make_invalid_eval_diagnostics()) == 'fail'


def test_orchestrator_repairs_invalid_eval_scaffolds(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_eval_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_invalid_eval_artifacts())
    monkeypatch.setattr(mod, "run_evaluations", lambda **kwargs: make_eval_report_with_benchmarks())

    response = run_skill_create(
        SkillCreateRequestV6(
            task="capture notes into notion",
            enable_eval_scaffold=True,
            enable_repair=True,
            max_repair_attempts=1,
        ),
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
    )

    assert response.severity == "pass"
    assert response.timings.repair_attempted is True
    assert response.timings.repair_applied is True
    assert response.timings.eval_runner_started_at_ms is not None
    assert response.timings.eval_runner_finished_at_ms is not None
    assert response.artifacts is not None
    assert response.evaluation_report is not None
    assert response.evaluation_report.trigger_results
    trigger_eval = next(file for file in response.artifacts.files if file.path == "evals/trigger_eval.json")
    assert '"cases"' in trigger_eval.content
    assert response.diagnostics is not None
    resolved_note = next(note for note in response.diagnostics.notes if note.startswith('Repair attempt 1:'))
    assert 'empty_eval_scaffold' in resolved_note
    assert 'invalid_eval_scaffold' in resolved_note
    assert any(
        note.startswith('Evaluation runner: overall_score=0.89; task_alignment=0.88; adaptation_quality=0.91')
        for note in response.diagnostics.notes
    )


def test_orchestrator_stops_after_max_repair_attempts_and_keeps_failure_context(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_invalid_artifacts())

    validator_calls = {"count": 0}

    def validator_stub(**kwargs):
        validator_calls["count"] += 1
        return make_fail_diagnostics()

    monkeypatch.setattr(mod, "run_validator", validator_stub)

    repair_calls = {"count": 0}

    def repair_stub(**kwargs):
        repair_calls["count"] += 1
        return RepairResult(
            applied=True,
            repaired_artifacts=make_repaired_artifacts(),
        )

    request = SkillCreateRequestV6(
        task="build skill",
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        repair_fn=repair_stub,
    )

    assert response.severity == "fail"
    assert repair_calls["count"] == 1
    assert validator_calls["count"] == 2
    assert response.timings.repair_attempted is True
    assert response.timings.repair_applied is True
    assert response.timings.repair_iteration_count == 1
    assert response.diagnostics is not None
    assert any(
        "Repair attempt 1: repairable/non-repairable issues 1 -> 1; remaining=['invalid_frontmatter']" == note
        for note in response.diagnostics.notes
    )
    assert any(
        "Repair stopped after reaching max_repair_attempts=1; remaining issues=['invalid_frontmatter']" == note
        for note in response.diagnostics.notes
    )


def test_orchestrator_reports_new_issue_branch_after_repair(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_invalid_artifacts())

    validator_calls = {"count": 0}

    def validator_stub(**kwargs):
        validator_calls["count"] += 1
        if validator_calls["count"] == 1:
            return make_fail_diagnostics()
        return make_over_budget_diagnostics()

    monkeypatch.setattr(mod, "run_validator", validator_stub)

    def repair_stub(**kwargs):
        return RepairResult(
            applied=True,
            repaired_artifacts=make_repaired_artifacts(),
        )

    request = SkillCreateRequestV6(
        task="build skill",
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        repair_fn=repair_stub,
    )

    assert response.severity == "fail"
    assert validator_calls["count"] == 2
    assert response.diagnostics is not None
    assert any(
        note == "Repair attempt 1: repairable/non-repairable issues 1 -> 1; resolved=['invalid_frontmatter']; new=['skill_md_over_budget']"
        for note in response.diagnostics.notes
    )
    assert any(
        note == "Repair stopped after reaching max_repair_attempts=1; remaining issues=['skill_md_over_budget']"
        for note in response.diagnostics.notes
    )


def test_orchestrator_repairs_script_quality_failures_even_without_skill_md_errors(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_repaired_artifacts())

    validator_calls = {"count": 0}

    def validator_stub(**kwargs):
        validator_calls["count"] += 1
        if validator_calls["count"] == 1:
            return make_script_quality_diagnostics()
        return make_pass_diagnostics()

    monkeypatch.setattr(mod, "run_validator", validator_stub)

    repair_calls = {"count": 0}

    def repair_stub(**kwargs):
        repair_calls["count"] += 1
        return RepairResult(
            applied=True,
            repaired_artifacts=make_repaired_artifacts(),
        )

    request = SkillCreateRequestV6(
        task="build skill",
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_artifacts,
        repair_fn=repair_stub,
    )

    assert repair_calls["count"] == 1
    assert validator_calls["count"] == 2
    assert response.severity == "pass"
    assert response.timings.repair_attempted is True
    assert response.timings.repair_applied is True
    assert response.diagnostics is not None
    assert any(
        "Repair attempt 1: repairable/non-repairable issues 2 -> 0" in note
        for note in response.diagnostics.notes
    )



def test_orchestrator_skips_persistence_when_fail_fast_and_still_failing(monkeypatch):
    from openclaw_skill_create.services import orchestrator as mod

    monkeypatch.setattr(mod, "run_extractor", lambda **kwargs: make_repo_findings())
    monkeypatch.setattr(mod, "run_planner", lambda **kwargs: make_skill_plan())
    monkeypatch.setattr(mod, "run_generator", lambda **kwargs: make_invalid_artifacts())
    monkeypatch.setattr(mod, "run_validator", lambda **kwargs: make_fail_diagnostics())

    def repair_stub(**kwargs):
        return RepairResult(
            applied=False,
            repaired_artifacts=make_invalid_artifacts(),
        )

    persist_called = {"value": False}

    def persist_stub(**kwargs):
        persist_called["value"] = True
        return {"applied": False}

    request = SkillCreateRequestV6(
        task="build skill",
        enable_repair=True,
        max_repair_attempts=1,
    )

    response = run_skill_create(
        request,
        preload_repo_context_fn=preload_repo_context,
        persist_artifacts_fn=persist_stub,
        repair_fn=repair_stub,
        fail_fast_on_validation_fail=True,
    )

    assert response.severity == "fail"
    assert response.persistence is None
    assert persist_called["value"] is False
    assert response.timings.repair_attempted is True
