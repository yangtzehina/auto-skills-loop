from __future__ import annotations

import json
import re
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.expert_structure import ExpertSkillProfile, SkillExpertStructureReport
from .body_quality import split_frontmatter
from .domain_specificity import _artifact_content, _contains_anchor, _extract_section, profile_for_skill


GENERIC_SKELETON_HEADINGS = {
    "overview",
    "when to use",
    "when not to use",
    "inputs",
    "workflow",
    "output format",
    "goal",
    "domain frame",
    "method result",
    "tradeoffs",
    "quality checks",
    "common pitfalls",
}


EXPERT_SKILL_PROFILES: dict[str, ExpertSkillProfile] = {
    "concept-to-mvp-pack": ExpertSkillProfile(
        skill_name="concept-to-mvp-pack",
        required_headings=[
            "Core Principle",
            "Default Workflow",
            "Define the Core Validation Question",
            "Identify the Minimum Honest Loop",
            "Separate Must-Haves from Supports",
            "Define the Minimum Content Package",
            "Define What Is Out of Scope",
            "Assemble the MVP Pack",
            "Run the Failure Pass",
        ],
        domain_actions=[
            "validation question",
            "smallest honest loop",
            "feature cut",
            "content scope",
            "out-of-scope",
            "mvp pack",
            "core support cut",
            "minimum content package",
        ],
        output_fields=[
            "Core Validation Question",
            "Smallest Honest Loop",
            "Feature Cut",
            "Minimum Content Package",
            "Out of Scope",
            "MVP Pack",
        ],
        pitfall_clusters=[
            "vertical slice",
            "scope creep",
            "mood instead of loop",
            "content hiding uncertainty",
        ],
        quality_checks=[
            "validation question can fail",
            "smallest honest loop is playable",
            "feature cut removes attractive work",
            "out-of-scope list blocks creep",
        ],
    ),
    "decision-loop-stress-test": ExpertSkillProfile(
        skill_name="decision-loop-stress-test",
        required_headings=[
            "Core Principle",
            "Default Workflow",
            "Define the Current Loop Shape",
            "Test the First-Hour Hook",
            "Test Midgame Sustainability",
            "Test Late-Game Expansion or Mutation",
            "Look for Solved States",
            "Audit Variation Quality",
            "Audit Reinforcement",
        ],
        domain_actions=[
            "decision loop",
            "first hour",
            "midgame",
            "lategame",
            "solved state",
            "variation quality",
            "reinforcement",
            "dominant strategy",
        ],
        output_fields=[
            "Current Loop Shape",
            "First-Hour Hook",
            "Midgame Sustainability",
            "Late-Game Evolution",
            "Solved State Risk",
            "Variation Quality",
            "Reinforcement Check",
        ],
        pitfall_clusters=[
            "cosmetic options",
            "dominant strategy",
            "surface variation",
            "rewarding autopilot",
        ],
        quality_checks=[
            "first hour midgame and lategame differ",
            "variation changes decisions",
            "solved state is concrete",
            "reinforcement teaches intended behavior",
        ],
    ),
    "simulation-resource-loop-design": ExpertSkillProfile(
        skill_name="simulation-resource-loop-design",
        required_headings=[
            "Core Principle",
            "Default Workflow",
            "List the Core Resources or Pressures",
            "Define Each Variable's Role",
            "Map the Pressure Relationships",
            "Identify the Primary Decision Tensions",
            "Design the Main Feedback Loops",
            "Design Failure and Recovery",
            "Align the Loop with the Emotional Fantasy",
        ],
        domain_actions=[
            "variable web",
            "pressure relationships",
            "positive loop",
            "negative loop",
            "failure recovery",
            "resource loop",
            "emotional fantasy",
            "primary decision tensions",
        ],
        output_fields=[
            "Variable Web",
            "Pressure Relationships",
            "Positive Loop",
            "Negative Loop",
            "Failure Recovery",
            "Resource Loop",
            "Emotional Fantasy",
        ],
        pitfall_clusters=[
            "variable web sprawl",
            "runaway snowball",
            "death spiral",
            "hidden pressure relationships",
            "emotionless resource loop",
        ],
        quality_checks=[
            "pressure is visible before commitment",
            "recovery keeps a cost",
            "one resource can bypass the intended tension web",
            "emotional fantasy still matches the pressure math",
        ],
    ),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _headings(body: str) -> list[str]:
    headings: list[str] = []
    in_fence = False
    for line in body.splitlines():
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


def _numbered_spine_labels(body: str) -> list[str]:
    labels: list[str] = []
    in_fence = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"\s*\d+\.\s+(?:\*\*)?([^*\n]+?)(?:\*\*)?\s*$", line)
        if match:
            label = match.group(1).strip()
            if label:
                labels.append(label)
    return labels


def _recall(items: list[str], text: str) -> tuple[float, list[str]]:
    missing = [item for item in items if not _contains_anchor(text, item)]
    return round((len(items) - len(missing)) / max(1, len(items)), 4), missing


def _heading_recall(required: list[str], headings: list[str]) -> tuple[float, list[str]]:
    heading_text = "\n".join(headings)
    return _recall(required, heading_text)


def expert_profile_for_skill(*, skill_name: str, task: str = "") -> ExpertSkillProfile | None:
    normalized = str(skill_name or "").strip().lower()
    if normalized in EXPERT_SKILL_PROFILES:
        return EXPERT_SKILL_PROFILES[normalized]
    profile = profile_for_skill(skill_name=skill_name, task=task)
    if profile is not None:
        return EXPERT_SKILL_PROFILES.get(profile.skill_name)
    return None


def build_skill_expert_structure_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    generated_vs_generated_heading_overlap: float = 0.0,
    generated_vs_generated_line_jaccard: float = 0.0,
) -> SkillExpertStructureReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillExpertStructureReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["expert_structure_status=pass", "expert_structure_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    profile = expert_profile_for_skill(skill_name=skill_name, task=task)
    headings = _headings(body)
    structure_labels = headings + _numbered_spine_labels(body)
    normalized_headings = [_normalize(item) for item in headings]
    generic_count = sum(1 for heading in normalized_headings if heading in GENERIC_SKELETON_HEADINGS)
    generic_ratio = round(generic_count / max(1, len(headings)), 4)

    if profile is None:
        status = "warn"
        return SkillExpertStructureReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status=status,
            profile_available=False,
            generated_vs_generated_heading_overlap=round(float(generated_vs_generated_heading_overlap or 0.0), 4),
            generated_vs_generated_line_jaccard=round(float(generated_vs_generated_line_jaccard or 0.0), 4),
            generic_skeleton_ratio=generic_ratio,
            warning_issues=["expert_profile_missing"],
            summary=[
                f"expert_structure_status={status}",
                "expert_profile_available=false",
                f"generic_skeleton_ratio={generic_ratio:.2f}",
            ],
        )

    workflow_text = _extract_section(body, ("workflow", "default workflow", "process", "steps"))
    output_text = _extract_section(body, ("output format", "output template", "deliverable", "output"))
    pitfall_text = _extract_section(body, ("common pitfalls", "pitfalls", "failure modes", "anti-patterns"))
    quality_text = _extract_section(body, ("quality checks", "quality bar", "acceptance", "checks"))

    heading_recall, missing_headings = _heading_recall(profile.required_headings, structure_labels)
    action_recall, missing_actions = _recall(profile.domain_actions, workflow_text or body)
    output_recall, missing_outputs = _recall(profile.output_fields, output_text)
    pitfall_recall, missing_pitfalls = _recall(profile.pitfall_clusters, pitfall_text)
    quality_recall, missing_quality = _recall(profile.quality_checks, quality_text)

    blocking: list[str] = []
    warnings: list[str] = []
    if action_recall < 0.75:
        blocking.append("expert_action_clusters_missing")
    if output_recall < 0.70:
        blocking.append("expert_output_fields_missing")
    if heading_recall < 0.30:
        blocking.append("expert_headings_missing")
    if pitfall_recall < 0.50:
        warnings.append("expert_pitfall_clusters_thin")
    if quality_recall < 0.70:
        blocking.append("expert_quality_checks_missing")
    if generated_vs_generated_heading_overlap >= 0.80:
        blocking.append("high_generated_heading_overlap")
    if generated_vs_generated_line_jaccard >= 0.42:
        blocking.append("high_generated_line_jaccard")
    if generic_ratio >= 0.50 and action_recall < 0.90:
        blocking.append("generic_expert_skeleton")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillExpertStructureReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        profile_available=True,
        expert_heading_recall=heading_recall,
        expert_action_cluster_recall=action_recall,
        expert_output_field_recall=output_recall,
        expert_pitfall_cluster_recall=pitfall_recall,
        expert_quality_check_recall=quality_recall,
        generated_vs_generated_heading_overlap=round(float(generated_vs_generated_heading_overlap or 0.0), 4),
        generated_vs_generated_line_jaccard=round(float(generated_vs_generated_line_jaccard or 0.0), 4),
        generic_skeleton_ratio=generic_ratio,
        missing_expert_headings=missing_headings,
        missing_action_clusters=missing_actions,
        missing_output_fields=missing_outputs,
        missing_pitfall_clusters=missing_pitfalls,
        missing_quality_checks=missing_quality,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"expert_structure_status={status}",
            f"expert_heading_recall={heading_recall:.2f}",
            f"expert_action_cluster_recall={action_recall:.2f}",
            f"expert_output_field_recall={output_recall:.2f}",
            f"expert_pitfall_cluster_recall={pitfall_recall:.2f}",
            f"expert_quality_check_recall={quality_recall:.2f}",
            f"generic_skeleton_ratio={generic_ratio:.2f}",
        ],
    )


def expert_structure_artifact(report: SkillExpertStructureReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/expert_structure.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["expert_structure"],
        status="new",
    )
