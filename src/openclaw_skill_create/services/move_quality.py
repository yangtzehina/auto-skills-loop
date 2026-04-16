from __future__ import annotations

import json
import re
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.expert_dna import ExpertSkillDNA, SkillMoveQualityReport
from .body_quality import split_frontmatter
from .domain_specificity import _artifact_content, _contains_anchor, _extract_section
from .expert_dna import expert_skill_dna_for_skill


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _recall(items: list[str], text: str) -> tuple[float, list[str]]:
    missing = [item for item in list(items or []) if not _contains_anchor(text, item)]
    return round((len(items) - len(missing)) / max(1, len(items)), 4), missing


def _numbered_moves(workflow_text: str) -> list[str]:
    moves: list[str] = []
    for line in str(workflow_text or "").splitlines():
        match = re.match(r"\s*\d+\.\s+(?:\*\*)?([^*\n]+?)(?:\*\*)?\s*$", line)
        if match:
            value = _normalize(match.group(1))
            if value:
                moves.append(value)
    return moves


def _named_workflow_block_count(workflow_text: str) -> int:
    count = 0
    in_fence = False
    for line in str(workflow_text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        if heading and not re.match(r"^\d+\.", heading):
            count += 1
    return count


def _workflow_step_support_counts(workflow_text: str) -> list[int]:
    counts: list[int] = []
    current = -1
    for raw in str(workflow_text or "").splitlines():
        if re.match(r"\s*\d+\.\s+(?:\*\*)?([^*\n]+?)(?:\*\*)?\s*$", raw):
            if current >= 0:
                counts.append(current)
            current = 0
            continue
        if current < 0:
            continue
        stripped = raw.strip()
        if re.match(r"^-\s+[^:]{2,}:\s+.+$", stripped):
            current += 1
    if current >= 0:
        counts.append(current)
    return counts


def _move_precision(*, dna: ExpertSkillDNA, detected_moves: list[str]) -> tuple[float, list[str]]:
    expected = [_normalize(move.name) for move in list(dna.workflow_moves or [])]
    if not detected_moves:
        return 0.0, []
    matched = [move for move in detected_moves if any(move == item or move in item or item in move for item in expected)]
    return round(len(matched) / max(1, len(detected_moves)), 4), matched


def _numbered_spine_present(*, workflow_text: str, dna: ExpertSkillDNA) -> bool:
    detected = _numbered_moves(workflow_text)
    if len(detected) < min(5, len(list(dna.workflow_moves or []))):
        return False
    support_counts = _workflow_step_support_counts(workflow_text)
    if not support_counts:
        return False
    rich_steps = sum(1 for count in support_counts if count >= 4)
    if rich_steps / max(1, len(support_counts)) < 0.80:
        return False
    workflow_surface = str(getattr(dna, "workflow_surface", "") or "execution_spine").strip().lower()
    if workflow_surface == "execution_spine":
        named_count = _named_workflow_block_count(workflow_text)
        if named_count / max(1, named_count + len(detected)) > 0.35:
            return False
    return True


def _output_semantics_score(*, output_text: str, dna: ExpertSkillDNA) -> tuple[float, list[str]]:
    field_recall, missing_fields = _recall(list(dna.output_fields or []), output_text)
    normalized = _normalize(output_text)
    good_weak_score = 1.0 if "good" in normalized and "weak" in normalized and "write" in normalized else 0.0
    return round((0.75 * field_recall) + (0.25 * good_weak_score), 4), missing_fields


def _failure_repair_score(*, pitfall_text: str, dna: ExpertSkillDNA) -> tuple[float, list[str]]:
    failure_recall, missing_failures = _recall(list(dna.failure_patterns or []), pitfall_text)
    repair_recall, missing_repairs = _recall(list(dna.repair_moves or []), pitfall_text)
    normalized = _normalize(pitfall_text)
    correction_score = 1.0 if "correction" in normalized and "symptom" in normalized and "cause" in normalized else 0.0
    score = round((0.45 * failure_recall) + (0.40 * repair_recall) + (0.15 * correction_score), 4)
    return score, missing_failures + missing_repairs


def build_skill_move_quality_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    cross_case_move_overlap: float = 0.0,
) -> SkillMoveQualityReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillMoveQualityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["move_quality_status=pass", "move_quality_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    dna = expert_skill_dna_for_skill(skill_name=skill_name, task=task)
    if dna is None:
        return SkillMoveQualityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="warn",
            profile_available=False,
            warning_issues=["expert_dna_profile_missing"],
            summary=["move_quality_status=warn", "expert_dna_profile_missing"],
        )

    workflow_text = _extract_section(body, ("default workflow", "workflow", "process", "steps"))
    output_text = _extract_section(body, ("output format", "output", "deliverable"))
    pitfall_text = _extract_section(body, ("common pitfalls", "failure patterns", "pitfalls"))
    detected_moves = _numbered_moves(workflow_text)
    workflow_move_terms = [move.name for move in list(dna.workflow_moves or [])]
    expert_move_recall, missing_moves = _recall(workflow_move_terms, workflow_text)
    expert_move_precision, _ = _move_precision(dna=dna, detected_moves=detected_moves)
    decision_rule_coverage, missing_decision_rules = _recall(list(dna.decision_rules or []), body)
    cut_rule_coverage, missing_cut_rules = _recall(list(dna.cut_rules or []), body)
    output_field_semantics_coverage, missing_output_fields = _output_semantics_score(output_text=output_text, dna=dna)
    failure_repair_coverage, missing_failure_repairs = _failure_repair_score(pitfall_text=pitfall_text, dna=dna)
    voice_rule_alignment, missing_voice_rules = _recall(list(dna.voice_rules or []), body)
    numbered_spine = _numbered_spine_present(workflow_text=workflow_text, dna=dna)
    overlap = round(float(cross_case_move_overlap or 0.0), 4)

    blocking: list[str] = []
    if expert_move_recall < 0.85:
        blocking.append("expert_move_recall_low")
    if expert_move_precision < 0.70:
        blocking.append("expert_move_precision_low")
    if decision_rule_coverage < 0.75:
        blocking.append("decision_rules_missing")
    if output_field_semantics_coverage < 0.75:
        blocking.append("output_field_semantics_missing")
    if failure_repair_coverage < 0.75:
        blocking.append("failure_repair_missing")
    if not numbered_spine:
        blocking.append("numbered_workflow_spine_missing")
    if overlap >= 0.35:
        blocking.append("high_cross_case_move_overlap")

    warnings: list[str] = []
    if cut_rule_coverage < 0.75:
        warnings.append("cut_rules_undercovered")
    if voice_rule_alignment < 0.70:
        warnings.append("voice_rule_alignment_weak")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillMoveQualityReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        profile_available=True,
        expert_move_recall=expert_move_recall,
        expert_move_precision=expert_move_precision,
        decision_rule_coverage=decision_rule_coverage,
        cut_rule_coverage=cut_rule_coverage,
        output_field_semantics_coverage=output_field_semantics_coverage,
        failure_repair_coverage=failure_repair_coverage,
        numbered_workflow_spine_present=numbered_spine,
        voice_rule_alignment=voice_rule_alignment,
        cross_case_move_overlap=overlap,
        detected_moves=detected_moves,
        missing_workflow_moves=missing_moves,
        missing_decision_rules=missing_decision_rules,
        missing_cut_rules=missing_cut_rules,
        missing_output_fields=missing_output_fields,
        missing_failure_repairs=missing_failure_repairs,
        missing_voice_rules=missing_voice_rules,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"move_quality_status={status}",
            f"expert_move_recall={expert_move_recall:.2f}",
            f"expert_move_precision={expert_move_precision:.2f}",
            f"decision_rule_coverage={decision_rule_coverage:.2f}",
            f"cut_rule_coverage={cut_rule_coverage:.2f}",
            f"output_field_semantics_coverage={output_field_semantics_coverage:.2f}",
            f"failure_repair_coverage={failure_repair_coverage:.2f}",
            f"numbered_workflow_spine_present={numbered_spine}",
            f"voice_rule_alignment={voice_rule_alignment:.2f}",
            f"cross_case_move_overlap={overlap:.2f}",
        ],
    )


def move_quality_artifact(report: SkillMoveQualityReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/move_quality.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["move_quality"],
        status="new",
    )
