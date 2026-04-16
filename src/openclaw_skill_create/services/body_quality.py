from __future__ import annotations

import re
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.body_quality import SkillBodyQualityReport, SkillSelfReviewReport


REQUIRED_METHODOLOGY_SECTIONS = [
    "overview",
    "when_to_use",
    "when_not_to_use",
    "inputs",
    "workflow",
    "output_format",
    "quality_checks",
    "common_pitfalls",
]

SECTION_ALIASES = {
    "overview": ("overview", "summary", "purpose", "introduction"),
    "when_to_use": ("when to use", "when this skill applies", "trigger"),
    "when_not_to_use": ("when not to use", "do not use", "out of scope"),
    "inputs": ("inputs", "input", "before you start"),
    "workflow": ("workflow", "process", "steps", "procedure"),
    "output_format": ("output format", "output template", "template", "deliverable"),
    "quality_checks": ("quality checks", "quality bar", "acceptance", "review checks"),
    "common_pitfalls": (
        "common pitfalls",
        "pitfalls",
        "failure patterns and fixes",
        "failure patterns",
        "failure modes",
        "anti-patterns",
        "mistakes",
    ),
}

PROMPT_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{3,}")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
NUMBERED_RE = re.compile(r"^\s*\d+[\.)]\s+")


def _artifact_content(artifacts: Artifacts, path: str) -> str:
    for file in list(artifacts.files or []):
        if file.path == path:
            return file.content or ""
    return ""


def split_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        return {}, content
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return {}, content
    frontmatter: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip()
    return frontmatter, parts[2]


def _body_nonempty_lines(body: str) -> list[str]:
    return [line.strip() for line in body.splitlines() if line.strip()]


def _heading_texts(lines: list[str]) -> list[str]:
    headings: list[str] = []
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            headings.append(match.group(1).strip().lower())
    return headings


def _section_hits(headings: list[str]) -> list[str]:
    present: list[str] = []
    haystack = "\n".join(headings)
    for section, aliases in SECTION_ALIASES.items():
        if any(alias in haystack for alias in aliases):
            present.append(section)
    return present


def _prompt_echo_ratio(*, task: str, description: str) -> float:
    tokens = sorted(set(token.lower() for token in PROMPT_TOKEN_RE.findall(task or "")))
    if not tokens:
        return 0.0
    lowered_description = (description or "").lower()
    hits = sum(1 for token in tokens if token in lowered_description)
    return round(hits / len(tokens), 4)


def build_skill_body_quality_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
) -> SkillBodyQualityReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    description = frontmatter.get("description", "")
    body_lines = _body_nonempty_lines(body)
    headings = _heading_texts(body.splitlines())
    bullets = sum(1 for line in body_lines if line.startswith(("- ", "* ", "+ ")))
    numbered = sum(1 for line in body_lines if NUMBERED_RE.match(line))
    body_chars = len(body.strip())
    description_chars = len(description.strip())
    ratio = round(description_chars / max(1, body_chars), 4)
    prompt_ratio = _prompt_echo_ratio(task=str(getattr(request, "task", "") or ""), description=description)
    present_sections = _section_hits(headings)
    missing_required = [
        section
        for section in REQUIRED_METHODOLOGY_SECTIONS
        if section not in present_sections
    ] if skill_archetype == "methodology_guidance" else []

    issues: list[str] = []
    blocking: list[str] = []

    if skill_archetype == "methodology_guidance":
        if len(body_lines) < 35 or body_chars < 1400 or len(headings) < 6:
            blocking.append("body_too_thin")
        for section in missing_required:
            if section == "workflow":
                blocking.append("missing_workflow")
            elif section == "output_format":
                blocking.append("missing_output_template")
            elif section == "common_pitfalls":
                blocking.append("missing_pitfalls")
            else:
                blocking.append(f"missing_{section}")
        if bullets + numbered < 8:
            blocking.append("body_too_thin")
    else:
        if len(body_lines) < 4 or body_chars < 160:
            blocking.append("body_too_thin")

    if description_chars > 500 and body_chars < 800 and ratio > 0.75:
        blocking.append("description_stuffing")
    if prompt_ratio >= 0.35 and body_chars < 800 and description_chars > body_chars:
        blocking.append("prompt_echo")

    issues = sorted(set(blocking))
    status = "fail" if blocking else "pass"
    return SkillBodyQualityReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        passed=status == "pass",
        body_lines=len(body_lines),
        body_chars=body_chars,
        heading_count=len(headings),
        bullet_count=bullets,
        numbered_step_count=numbered,
        description_chars=description_chars,
        description_body_ratio=ratio,
        prompt_echo_ratio=prompt_ratio,
        required_sections_present=present_sections,
        missing_required_sections=missing_required,
        issues=issues,
        blocking_issues=sorted(set(blocking)),
        summary=[
            f"body_quality_status={status}",
            f"body_lines={len(body_lines)}",
            f"body_chars={body_chars}",
            f"headings={len(headings)}",
            f"description_body_ratio={ratio:.2f}",
            f"prompt_echo_ratio={prompt_ratio:.2f}",
        ],
    )


def build_skill_self_review_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    body_quality: SkillBodyQualityReport,
) -> SkillSelfReviewReport:
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    missing_materials = list(body_quality.missing_required_sections or [])
    description_stuffing = "description_stuffing" in body_quality.issues
    prompt_transformed = not description_stuffing and "prompt_echo" not in body_quality.issues
    if skill_archetype == "methodology_guidance":
        prompt_transformed = prompt_transformed and not missing_materials
    can_guide_agent = bool(body_quality.passed and prompt_transformed)
    blocking = []
    if not body_quality.passed:
        blocking.extend(list(body_quality.blocking_issues or []))
    if not prompt_transformed:
        blocking.append("prompt_not_transformed")
    if not can_guide_agent:
        blocking.append("not_directly_usable")
    status = "fail" if blocking else "pass"
    return SkillSelfReviewReport(
        skill_name=body_quality.skill_name,
        skill_archetype=skill_archetype,
        status=status,
        can_guide_agent=can_guide_agent,
        prompt_transformed=prompt_transformed,
        description_stuffing=description_stuffing,
        missing_materials=sorted(set(missing_materials)),
        blocking_issues=sorted(set(blocking)),
        summary=[
            f"self_review_status={status}",
            f"can_guide_agent={can_guide_agent}",
            f"prompt_transformed={prompt_transformed}",
            f"description_stuffing={description_stuffing}",
        ],
    )


def body_quality_artifact(report: SkillBodyQualityReport) -> ArtifactFile:
    import json

    return ArtifactFile(
        path="evals/body_quality.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["body_quality"],
        status="new",
    )


def self_review_artifact(report: SkillSelfReviewReport) -> ArtifactFile:
    import json

    return ArtifactFile(
        path="evals/self_review.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["self_review"],
        status="new",
    )
