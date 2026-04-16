from __future__ import annotations

import json
import re
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.expert_studio import SkillProgramFidelityReport
from .body_quality import split_frontmatter
from .domain_specificity import _artifact_content, _contains_anchor, _extract_section
from .expert_skill_studio import build_skill_program_ir, expert_corpus_entry_for_skill
from .workflow_form import build_skill_workflow_form_report


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _coverage(items: list[str], text: str) -> tuple[float, list[str]]:
    if not items:
        return 1.0, []
    missing = [item for item in items if not _contains_anchor(text, item)]
    score = round((len(items) - len(missing)) / max(1, len(items)), 4)
    return score, missing


def _detect_numbered_moves(workflow_text: str) -> list[str]:
    moves: list[str] = []
    for raw in str(workflow_text or "").splitlines():
        match = re.match(r"\s*\d+\.\s+(?:\*\*)?([^*\n]+?)(?:\*\*)?\s*$", raw)
        if match:
            value = _normalize(match.group(1))
            if value:
                moves.append(value)
    return moves


def _order_alignment(expected: list[str], detected: list[str]) -> float:
    if not expected:
        return 1.0
    if not detected:
        return 0.0
    positions: list[int] = []
    for item in expected:
        normalized = _normalize(item)
        match = next((idx for idx, value in enumerate(detected) if value == normalized or value in normalized or normalized in value), None)
        if match is not None:
            positions.append(match)
    if not positions:
        return 0.0
    in_order = sum(1 for left, right in zip(positions, positions[1:]) if right >= left)
    return round((1 + in_order) / max(1, len(expected)), 4)


def build_skill_program_fidelity_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    workflow_form: Any | None = None,
) -> SkillProgramFidelityReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillProgramFidelityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            profile_available=False,
            summary=["program_fidelity_status=pass", "program_fidelity_skipped=non_methodology"],
        )

    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    if corpus is None or not str(corpus.expert_skill_markdown or "").strip():
        return SkillProgramFidelityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            profile_available=False,
            summary=[
                "program_fidelity_status=pass",
                "program_fidelity_skipped=missing_checked_in_expert_program",
            ],
        )

    task = str(getattr(request, "task", "") or "")
    program = build_skill_program_ir(skill_name=skill_name, task=task)
    if program is None:
        return SkillProgramFidelityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="warn",
            profile_available=False,
            warning_issues=["expert_program_missing"],
            summary=["program_fidelity_status=warn", "expert_program_missing"],
        )

    workflow_text = _extract_section(body, ("default workflow", "workflow", "process", "steps"))
    output_text = _extract_section(body, ("output format", "output", "deliverable"))
    pitfall_text = _extract_section(body, ("common pitfalls", "failure patterns", "pitfalls"))
    detected_moves = _detect_numbered_moves(workflow_text)
    expected_moves = [move.label for move in list(program.execution_spine or [])]
    execution_move_recall, missing_execution_moves = _coverage(expected_moves, workflow_text)
    execution_move_order_alignment = _order_alignment(expected_moves, detected_moves)
    decision_rule_fidelity, _ = _coverage(list(program.decision_rules or []), body)
    cut_rule_fidelity, _ = _coverage(list(program.cut_rules or []), body)
    failure_repair_fidelity, _ = _coverage(list(program.failure_repairs or []), pitfall_text)
    output_schema_fidelity, missing_output_fields = _coverage(list(program.output_schema.keys()), output_text)
    if workflow_form is None:
        workflow_form = build_skill_workflow_form_report(request=request, skill_plan=skill_plan, artifacts=artifacts)
    workflow_surface_fidelity = 1.0 if str(getattr(workflow_form, "workflow_surface", "") or "unknown") == program.workflow_surface else 0.0
    style_terms = [program.opening_strategy] + list(program.voice_constraints or []) + list(program.style_profile[:3] or [])
    style_strategy_fidelity, _ = _coverage([item for item in style_terms if item], body)

    blocking: list[str] = []
    if execution_move_recall < 0.85:
        blocking.append("execution_move_recall_low")
    if execution_move_order_alignment < 0.80:
        blocking.append("execution_move_order_alignment_low")
    if decision_rule_fidelity < 0.75:
        blocking.append("decision_rule_fidelity_low")
    if output_schema_fidelity < 0.75:
        blocking.append("output_schema_fidelity_low")
    if failure_repair_fidelity < 0.75:
        blocking.append("failure_repair_fidelity_low")
    if workflow_surface_fidelity < 1.0:
        blocking.append("workflow_surface_fidelity_low")

    warnings: list[str] = []
    if cut_rule_fidelity < 0.75:
        warnings.append("cut_rule_fidelity_low")
    if style_strategy_fidelity < 0.65:
        warnings.append("style_strategy_fidelity_low")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillProgramFidelityReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        profile_available=True,
        execution_move_recall=execution_move_recall,
        execution_move_order_alignment=execution_move_order_alignment,
        decision_rule_fidelity=decision_rule_fidelity,
        cut_rule_fidelity=cut_rule_fidelity,
        failure_repair_fidelity=failure_repair_fidelity,
        output_schema_fidelity=output_schema_fidelity,
        workflow_surface_fidelity=workflow_surface_fidelity,
        style_strategy_fidelity=style_strategy_fidelity,
        missing_execution_moves=missing_execution_moves,
        missing_output_fields=missing_output_fields,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"program_fidelity_status={status}",
            f"execution_move_recall={execution_move_recall:.2f}",
            f"execution_move_order_alignment={execution_move_order_alignment:.2f}",
            f"decision_rule_fidelity={decision_rule_fidelity:.2f}",
            f"cut_rule_fidelity={cut_rule_fidelity:.2f}",
            f"failure_repair_fidelity={failure_repair_fidelity:.2f}",
            f"output_schema_fidelity={output_schema_fidelity:.2f}",
            f"workflow_surface_fidelity={workflow_surface_fidelity:.2f}",
            f"style_strategy_fidelity={style_strategy_fidelity:.2f}",
        ],
    )


def program_fidelity_artifact(report: SkillProgramFidelityReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/program_fidelity.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["program_fidelity"],
        status="new",
    )
