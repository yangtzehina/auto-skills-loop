from __future__ import annotations

import json
import re
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.domain_expertise import SkillDomainExpertiseReport
from .body_quality import split_frontmatter
from .domain_specificity import (
    _artifact_content,
    _contains_anchor,
    _extract_section,
    profile_for_skill,
    resolve_domain_anchors,
)


ACTION_MARKERS = (
    "audit",
    "align",
    "choose",
    "check",
    "compare",
    "convert",
    "define",
    "design",
    "draw",
    "explain",
    "frame",
    "identify",
    "include",
    "list",
    "make",
    "map",
    "name",
    "produce",
    "separate",
    "set",
    "test",
    "trace",
    "turn",
    "verify",
    "write",
)

JUDGMENT_MARKERS = (
    "accepted",
    "align",
    "avoid",
    "bar",
    "because",
    "check",
    "concrete",
    "fail",
    "guardrail",
    "enough",
    "must",
    "present",
    "quality",
    "risk",
    "same direction",
    "specific",
    "tradeoff",
    "useful",
    "verify",
    "visible",
    "why",
)

GENERIC_EXPERTISE_MARKERS = (
    "concrete decision or output target",
    "main tradeoff constraint or evaluation lens",
    "explicit workflow step with observable evidence",
    "generic answer before it reaches the user",
    "task-specific result",
    "task-specific slot",
)


def _lines_with_anchor(section: str, anchor: str) -> list[str]:
    return [line.strip() for line in section.splitlines() if _contains_anchor(line, anchor)]


def _anchor_has_marker(section: str, anchor: str, markers: tuple[str, ...]) -> bool:
    for line in _lines_with_anchor(section, anchor):
        normalized = line.lower()
        if any(marker in normalized for marker in markers):
            return True
    return False


def _coverage(anchors: list[str], hits: list[str]) -> float:
    return round(len(hits) / max(1, len(anchors)), 4)


def _task_phrase_echo_ratio(*, task: str, body: str) -> float:
    words = [word.lower() for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", task or "")]
    if len(words) < 4:
        return 0.0
    phrases: list[str] = []
    for size in (6, 5, 4):
        for index in range(0, max(0, len(words) - size + 1)):
            phrase = " ".join(words[index:index + size])
            if phrase not in phrases:
                phrases.append(phrase)
    body_normalized = " ".join(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", body.lower()))
    if not phrases:
        return 0.0
    return round(sum(1 for phrase in phrases if phrase in body_normalized) / len(phrases), 4)


def build_skill_domain_expertise_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
) -> SkillDomainExpertiseReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillDomainExpertiseReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["domain_expertise_status=pass", "domain_expertise_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    anchors, known_profile = resolve_domain_anchors(skill_name=skill_name, task=task)
    workflow_text = _extract_section(body, ("workflow", "process", "steps"))
    output_text = _extract_section(body, ("output format", "output template", "deliverable", "output"))
    quality_text = _extract_section(body, ("quality checks", "quality bar", "acceptance", "checks"))
    pitfall_text = _extract_section(
        body,
        (
            "common pitfalls",
            "failure patterns and fixes",
            "failure patterns",
            "pitfalls",
            "failure modes",
            "anti-patterns",
            "mistakes",
        ),
    )

    action_hits = [
        anchor
        for anchor in anchors
        if _anchor_has_marker(workflow_text, anchor, ACTION_MARKERS)
    ]
    judgment_hits = [
        anchor
        for anchor in anchors
        if _anchor_has_marker(quality_text, anchor, JUDGMENT_MARKERS)
    ]
    output_hits = [anchor for anchor in anchors if _contains_anchor(output_text, anchor)]
    pitfall_hits = [anchor for anchor in anchors if _contains_anchor(pitfall_text, anchor)]

    action_coverage = _coverage(anchors, action_hits)
    judgment_coverage = _coverage(anchors, judgment_hits)
    output_coverage = _coverage(anchors, output_hits)
    pitfall_coverage = _coverage(anchors, pitfall_hits)
    move_coverage = round(
        (action_coverage * 0.35)
        + (judgment_coverage * 0.25)
        + (output_coverage * 0.25)
        + (pitfall_coverage * 0.15),
        4,
    )
    prompt_phrase_echo = _task_phrase_echo_ratio(task=task, body=body)
    generic_hits = sum(1 for marker in GENERIC_EXPERTISE_MARKERS if marker in body.lower())
    generic_ratio = round(generic_hits / max(1, generic_hits + len(action_hits) + len(judgment_hits) + len(output_hits)), 4)

    missing_action = [anchor for anchor in anchors if anchor not in action_hits]
    missing_judgment = [anchor for anchor in anchors if anchor not in judgment_hits]
    missing_output = [anchor for anchor in anchors if anchor not in output_hits]
    missing_pitfall = [anchor for anchor in anchors if anchor not in pitfall_hits]

    blocking: list[str] = []
    warnings: list[str] = []
    if not anchors or len(anchors) < 3:
        warnings.append("insufficient_domain_anchors")
    if known_profile:
        if action_coverage < 0.60:
            blocking.append("domain_actions_missing")
        if output_coverage < 0.40:
            blocking.append("domain_output_fields_missing")
        if judgment_coverage < 0.30:
            blocking.append("domain_judgment_checks_missing")
        if pitfall_coverage < 0.25:
            blocking.append("domain_pitfalls_missing")
        if move_coverage < 0.55:
            blocking.append("domain_moves_underdeveloped")
    else:
        if action_coverage < 0.50:
            warnings.append("domain_actions_missing")
        if output_coverage < 0.40:
            warnings.append("domain_output_fields_missing")
        if judgment_coverage < 0.25:
            warnings.append("domain_judgment_checks_missing")
        if move_coverage < 0.45:
            warnings.append("domain_moves_underdeveloped")
    if generic_ratio >= 0.25 and move_coverage < 0.75:
        if known_profile:
            blocking.append("generic_domain_move_shell")
        else:
            warnings.append("generic_domain_move_shell")
    if prompt_phrase_echo >= 0.25 and move_coverage < 0.75:
        warnings.append("prompt_phrase_echo")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillDomainExpertiseReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        domain_anchors=anchors,
        action_anchor_coverage=action_coverage,
        judgment_anchor_coverage=judgment_coverage,
        output_anchor_coverage=output_coverage,
        pitfall_anchor_coverage=pitfall_coverage,
        domain_move_coverage=move_coverage,
        prompt_phrase_echo_ratio=prompt_phrase_echo,
        generic_expertise_shell_ratio=generic_ratio,
        missing_action_anchors=missing_action,
        missing_judgment_anchors=missing_judgment,
        missing_output_anchors=missing_output,
        missing_pitfall_anchors=missing_pitfall,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"domain_expertise_status={status}",
            f"domain_move_coverage={move_coverage:.2f}",
            f"action_anchor_coverage={action_coverage:.2f}",
            f"judgment_anchor_coverage={judgment_coverage:.2f}",
            f"output_anchor_coverage={output_coverage:.2f}",
            f"pitfall_anchor_coverage={pitfall_coverage:.2f}",
            f"prompt_phrase_echo_ratio={prompt_phrase_echo:.2f}",
        ],
    )


def domain_expertise_artifact(report: SkillDomainExpertiseReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/domain_expertise.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["domain_expertise"],
        status="new",
    )
