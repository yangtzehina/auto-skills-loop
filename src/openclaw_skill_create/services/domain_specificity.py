from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.domain_specificity import SkillDomainSpecificityReport
from .body_quality import split_frontmatter


@dataclass(frozen=True)
class DomainProfile:
    skill_name: str
    label: str
    anchors: tuple[str, ...]


GAME_DESIGN_DOMAIN_PROFILES: dict[str, DomainProfile] = {
    "concept-to-mvp-pack": DomainProfile(
        skill_name="concept-to-mvp-pack",
        label="concept to MVP pack",
        anchors=(
            "validation question",
            "smallest honest loop",
            "feature cut",
            "content scope",
            "out-of-scope",
            "mvp pack",
        ),
    ),
    "decision-loop-stress-test": DomainProfile(
        skill_name="decision-loop-stress-test",
        label="decision loop stress test",
        anchors=(
            "first hour",
            "midgame",
            "lategame",
            "solved state",
            "variation quality",
            "reinforcement",
            "decision loop",
        ),
    ),
    "simulation-resource-loop-design": DomainProfile(
        skill_name="simulation-resource-loop-design",
        label="simulation resource loop design",
        anchors=(
            "variable web",
            "pressure relationships",
            "positive loop",
            "negative loop",
            "failure recovery",
            "resource loop",
            "emotional fantasy",
        ),
    ),
}

GENERIC_TEMPLATE_MARKERS = (
    "name the real job",
    "identify the operating context",
    "build the working frame",
    "run the method",
    "produce the artifact",
    "run the guardrail pass",
    "choose 3-5 criteria",
    "turn abstract goals into concrete checks",
)

STOPWORDS = {
    "about",
    "agent",
    "also",
    "and",
    "artifact",
    "check",
    "checks",
    "create",
    "design",
    "for",
    "format",
    "from",
    "game",
    "guidance",
    "including",
    "into",
    "method",
    "methodology",
    "output",
    "pack",
    "quality",
    "skill",
    "skills",
    "task",
    "template",
    "that",
    "the",
    "this",
    "to",
    "use",
    "when",
    "with",
    "workflow",
}


def _artifact_content(artifacts: Artifacts, path: str) -> str:
    for file in list(artifacts.files or []):
        if file.path == path:
            return file.content or ""
    return ""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _contains_anchor(text: str, anchor: str) -> bool:
    haystack = _normalize(text)
    needle = _normalize(anchor)
    if not needle:
        return False
    if needle in haystack:
        return True
    tokens = [token for token in needle.split() if token]
    return bool(tokens) and all(token in haystack for token in tokens)


def _extract_section(body: str, heading_aliases: tuple[str, ...]) -> str:
    lines = body.splitlines()
    capture = False
    in_fence = False
    capture_level = 0
    captured: list[str] = []
    aliases = tuple(_normalize(alias) for alias in heading_aliases)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if capture:
                captured.append(line)
            in_fence = not in_fence
            continue
        if stripped.startswith("#") and not in_fence:
            level = len(stripped) - len(stripped.lstrip("#"))
            heading = _normalize(stripped.lstrip("#").strip())
            if capture and heading and level <= capture_level:
                break
            if capture:
                captured.append(line)
                continue
            capture = any(alias in heading for alias in aliases)
            if capture:
                capture_level = level
            continue
        if capture:
            captured.append(line)
    return "\n".join(captured).strip()


def profile_for_skill(*, skill_name: str, task: str = "") -> DomainProfile | None:
    normalized_name = str(skill_name or "").strip().lower()
    if normalized_name in GAME_DESIGN_DOMAIN_PROFILES:
        return GAME_DESIGN_DOMAIN_PROFILES[normalized_name]
    task_lower = str(task or "").lower()
    for key, profile in GAME_DESIGN_DOMAIN_PROFILES.items():
        if key in task_lower:
            return profile
    return None


def extract_task_domain_anchors(task: str, *, limit: int = 6) -> list[str]:
    task_text = str(task or "")
    anchors: list[str] = []
    for quoted in re.findall(r"`([^`]{3,60})`|\"([^\"]{3,60})\"|'([^']{3,60})'", task_text):
        value = next((item for item in quoted if item), "")
        if value and value.lower() not in STOPWORDS and value not in anchors:
            anchors.append(value.strip())
    for value in re.findall(r"\b[a-zA-Z][a-zA-Z]+(?:-[a-zA-Z][a-zA-Z]+)+\b", task_text):
        text = value.replace("-", " ").strip().lower()
        if text not in anchors:
            anchors.append(text)
    words = [word.lower() for word in re.findall(r"[a-zA-Z][a-zA-Z]{3,}", task_text)]
    candidates: list[str] = []
    for size in (3, 2):
        for index in range(0, max(0, len(words) - size + 1)):
            phrase_words = words[index:index + size]
            if any(word in STOPWORDS for word in phrase_words):
                continue
            phrase = " ".join(phrase_words)
            if phrase not in candidates:
                candidates.append(phrase)
    for phrase in candidates:
        if phrase not in anchors:
            anchors.append(phrase)
        if len(anchors) >= limit:
            break
    return anchors[:limit]


def resolve_domain_anchors(*, skill_name: str, task: str) -> tuple[list[str], bool]:
    profile = profile_for_skill(skill_name=skill_name, task=task)
    if profile is not None:
        return list(profile.anchors), True
    return extract_task_domain_anchors(task, limit=6), False


def build_skill_domain_specificity_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    cross_case_similarity: float = 0.0,
) -> SkillDomainSpecificityReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillDomainSpecificityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["domain_specificity_status=pass", "domain_specificity_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    anchors, known_profile = resolve_domain_anchors(skill_name=skill_name, task=task)
    body_text = body
    workflow_text = _extract_section(body, ("workflow", "process", "steps"))
    output_text = _extract_section(body, ("output format", "output template", "deliverable", "output"))
    description = frontmatter.get("description", "")
    overview_text = _extract_section(body, ("overview", "summary", "purpose"))

    covered = [anchor for anchor in anchors if _contains_anchor(body_text, anchor)]
    workflow_hits = [anchor for anchor in anchors if _contains_anchor(workflow_text, anchor)]
    output_hits = [anchor for anchor in anchors if _contains_anchor(output_text, anchor)]
    missing = [anchor for anchor in anchors if anchor not in covered]
    anchor_count = max(1, len(anchors))
    coverage = round(len(covered) / anchor_count, 4)
    workflow_coverage = round(len(workflow_hits) / anchor_count, 4)
    output_coverage = round(len(output_hits) / anchor_count, 4)

    generic_hits = sum(1 for marker in GENERIC_TEMPLATE_MARKERS if marker in body.lower())
    generic_ratio = round(generic_hits / max(1, generic_hits + len(covered)), 4)

    task_tokens = sorted(set(token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", task)))
    body_lower = body.lower()
    prompt_echo = round(
        sum(1 for token in task_tokens if token in body_lower) / max(1, len(task_tokens)),
        4,
    )

    blocking: list[str] = []
    warnings: list[str] = []
    if not anchors:
        warnings.append("missing_domain_anchors")
    elif known_profile and coverage < 0.70:
        blocking.append("missing_domain_anchors")
    elif not known_profile and coverage < 0.70:
        warnings.append("missing_domain_anchors")
    if known_profile and workflow_coverage < 0.35:
        blocking.append("domain_workflow_missing")
    elif not known_profile and workflow_coverage == 0.0:
        warnings.append("domain_workflow_missing")
    if known_profile and output_coverage < 0.20:
        blocking.append("domain_output_missing")
    if generic_ratio >= 0.35 and coverage < 0.85:
        if known_profile:
            blocking.append("generic_methodology_shell")
        else:
            warnings.append("generic_methodology_shell")
    if cross_case_similarity >= 0.82:
        blocking.append("high_cross_case_similarity")
    if prompt_echo >= 0.80 and len(overview_text) > 80 and task.lower().strip(". ") in overview_text.lower():
        blocking.append("body_prompt_echo")
    if prompt_echo >= 0.90 and description.lower().strip(". ") in body_lower and coverage < 0.85:
        blocking.append("body_prompt_echo")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillDomainSpecificityReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        domain_anchor_coverage=coverage,
        domain_anchors=anchors,
        covered_domain_anchors=covered,
        missing_domain_anchors=missing,
        workflow_anchor_coverage=workflow_coverage,
        output_anchor_coverage=output_coverage,
        generic_template_ratio=generic_ratio,
        cross_case_similarity=round(float(cross_case_similarity or 0.0), 4),
        prompt_echo_in_body=prompt_echo,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"domain_specificity_status={status}",
            f"domain_anchor_coverage={coverage:.2f}",
            f"workflow_anchor_coverage={workflow_coverage:.2f}",
            f"output_anchor_coverage={output_coverage:.2f}",
            f"generic_template_ratio={generic_ratio:.2f}",
            f"prompt_echo_in_body={prompt_echo:.2f}",
        ],
    )


def domain_specificity_artifact(report: SkillDomainSpecificityReport) -> ArtifactFile:
    import json

    return ArtifactFile(
        path="evals/domain_specificity.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["domain_specificity"],
        status="new",
    )
