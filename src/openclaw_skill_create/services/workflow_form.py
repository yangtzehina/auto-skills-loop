from __future__ import annotations

import json
import re
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.workflow_form import SkillWorkflowFormReport
from .body_quality import split_frontmatter
from .domain_specificity import _artifact_content, _contains_anchor, _extract_section
from .expert_dna import expert_skill_dna_for_skill


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _numbered_moves(workflow_text: str) -> list[str]:
    moves: list[str] = []
    for line in str(workflow_text or "").splitlines():
        match = re.match(r"\s*\d+\.\s+(?:\*\*)?([^*\n]+?)(?:\*\*)?\s*$", line)
        if match:
            value = match.group(1).strip()
            if value:
                moves.append(value)
    return moves


def _named_workflow_blocks(workflow_text: str) -> list[str]:
    blocks: list[str] = []
    in_fence = False
    for line in str(workflow_text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        if re.match(r"^\d+\.", heading):
            continue
        if heading:
            blocks.append(heading)
    return blocks


def _section_headings(section_text: str) -> list[str]:
    headings: list[str] = []
    in_fence = False
    for line in str(section_text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        if heading:
            headings.append(heading)
    return headings


def _recall(expected: list[str], text: str) -> float:
    if not expected:
        return 1.0
    hits = sum(1 for item in expected if _contains_anchor(text, item))
    return round(hits / max(1, len(expected)), 4)


def _output_block_separation(*, named_blocks: list[str], output_fields: list[str]) -> bool:
    if not named_blocks or not output_fields:
        return True
    normalized_blocks = {_normalize(item) for item in named_blocks}
    for field in output_fields:
        normalized_field = _normalize(field)
        if normalized_field and normalized_field in normalized_blocks:
            return False
    return True


def build_skill_workflow_form_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
) -> SkillWorkflowFormReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillWorkflowFormReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["workflow_form_status=pass", "workflow_form_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    dna = expert_skill_dna_for_skill(skill_name=skill_name, task=task)
    if dna is None:
        return SkillWorkflowFormReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="warn",
            profile_available=False,
            workflow_surface="unknown",
            warning_issues=["expert_workflow_surface_profile_missing"],
            summary=["workflow_form_status=warn", "expert_workflow_surface_profile_missing"],
        )

    workflow_surface = str(getattr(dna, "workflow_surface", "") or "execution_spine").strip().lower()
    workflow_text = _extract_section(body, ("default workflow", "workflow", "process", "steps"))
    output_text = _extract_section(body, ("output format", "output", "deliverable"))
    analysis_text = _extract_section(body, ("analysis blocks", "analysis block", "map blocks"))
    numbered_moves = _numbered_moves(workflow_text)
    named_blocks = _named_workflow_blocks(workflow_text)
    structural_blocks = _section_headings(analysis_text)
    numbered_count = len(numbered_moves)
    named_count = len(named_blocks)
    named_dominance = round(named_count / max(1, numbered_count + named_count), 4)
    expected_moves = [move.name for move in list(dna.workflow_moves or [])]
    imperative_recall = _recall(expected_moves, "\n".join(numbered_moves))
    heading_alignment = _recall(expected_moves, workflow_text)
    output_separation = _output_block_separation(named_blocks=named_blocks, output_fields=list(dna.output_fields or []))

    required_numbered = min(5, len(expected_moves))
    blocking: list[str] = []
    warnings: list[str] = []
    if workflow_surface == "execution_spine":
        if numbered_count < required_numbered:
            blocking.append("numbered_workflow_spine_missing")
        if imperative_recall < 0.85:
            blocking.append("imperative_workflow_moves_missing")
        if named_dominance > 0.35:
            blocking.append("workflow_named_blocks_dominate")
        if not output_separation:
            blocking.append("output_blocks_mixed_into_workflow")
    elif workflow_surface == "hybrid":
        if numbered_count < required_numbered:
            blocking.append("numbered_map_sequence_missing")
        if imperative_recall < 0.75:
            blocking.append("imperative_workflow_moves_missing")
        if len(structural_blocks) < 3:
            blocking.append("structural_analysis_blocks_missing")
        if named_dominance > 0.50:
            warnings.append("workflow_named_blocks_heavy")
    elif workflow_surface == "analytical_map":
        if named_count < 3:
            blocking.append("analytical_blocks_missing")
        if numbered_count and imperative_recall < 0.50:
            warnings.append("weak_execution_support")
    else:
        warnings.append("unknown_workflow_surface")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillWorkflowFormReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        profile_available=True,
        workflow_surface=workflow_surface,
        numbered_spine_count=numbered_count,
        imperative_move_recall=imperative_recall,
        named_block_dominance_ratio=named_dominance,
        workflow_heading_alignment=heading_alignment,
        output_block_separation=output_separation,
        structural_block_count=len(structural_blocks),
        workflow_numbered_moves=numbered_moves,
        workflow_named_blocks=named_blocks,
        structural_blocks=structural_blocks,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"workflow_form_status={status}",
            f"workflow_surface={workflow_surface}",
            f"numbered_spine_count={numbered_count}",
            f"imperative_move_recall={imperative_recall:.2f}",
            f"named_block_dominance_ratio={named_dominance:.2f}",
            f"workflow_heading_alignment={heading_alignment:.2f}",
            f"output_block_separation={output_separation}",
            f"structural_block_count={len(structural_blocks)}",
        ],
    )


def workflow_form_artifact(report: SkillWorkflowFormReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/workflow_form.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["workflow_form"],
        status="new",
    )
