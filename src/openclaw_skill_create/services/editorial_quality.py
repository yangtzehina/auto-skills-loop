from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.editorial_quality import ExpertEditorialProfile, SkillEditorialQualityReport
from .body_quality import split_frontmatter
from .domain_specificity import _artifact_content, _contains_anchor, _extract_section
from .expert_structure import expert_profile_for_skill


EXPERT_EDITORIAL_PROFILES: dict[str, ExpertEditorialProfile] = {
    "concept-to-mvp-pack": ExpertEditorialProfile(
        skill_name="concept-to-mvp-pack",
        decision_terms=[
            "validation question",
            "can fail",
            "smallest honest loop",
            "playable",
            "feature cut",
            "minimum content",
            "out of scope",
            "prototype first",
            "success criteria",
        ],
        cut_terms=[
            "cut",
            "defer",
            "out of scope",
            "scope creep",
            "not a mini vertical slice",
            "testability",
        ],
        output_terms=[
            "core question",
            "input",
            "system response",
            "feedback",
            "repeat trigger",
            "must have",
            "cut for now",
            "build recommendation",
        ],
        failure_terms=[
            "fake mvp",
            "scope creep",
            "content-heavy validation",
            "premature meta systems",
            "success criteria missing",
        ],
    ),
    "decision-loop-stress-test": ExpertEditorialProfile(
        skill_name="decision-loop-stress-test",
        decision_terms=[
            "first-hour",
            "midgame",
            "late-game",
            "solved state",
            "dominant strategy",
            "variation quality",
            "reinforcement",
            "structural fixes",
        ],
        cut_terms=[
            "not greenlighting",
            "not mvp scope",
            "not detailed numeric balancing",
            "surface excitement",
            "content padding",
        ],
        output_terms=[
            "core decision",
            "feedback structure",
            "first-hour performance",
            "midgame performance",
            "late-game performance",
            "dominant strategy",
            "variation quality",
            "reinforcement recommendations",
        ],
        failure_terms=[
            "novelty-only start",
            "midgame autopilot",
            "progression without new problems",
            "variety without strategic consequence",
            "mastery removes the game",
        ],
    ),
    "simulation-resource-loop-design": ExpertEditorialProfile(
        skill_name="simulation-resource-loop-design",
        decision_terms=[
            "variable web",
            "player-facing",
            "pressure relationships",
            "tradeoff",
            "positive loops",
            "negative loops",
            "failure recovery",
            "emotional fantasy",
        ],
        cut_terms=[
            "not just one simple currency",
            "not isolated meters",
            "decorative resources",
            "one dominant currency",
            "few strong tensions",
        ],
        output_terms=[
            "enables",
            "restricts",
            "gain sources",
            "loss sources",
            "pressure relationships",
            "positive loops",
            "negative counter loops",
            "failure and recovery",
            "emotional fantasy",
        ],
        failure_terms=[
            "decorative resources",
            "no real tradeoff",
            "one dominant currency",
            "positive-loop runaway",
            "punishment without agency",
            "fantasy-system mismatch",
        ],
    ),
}

ACTION_TERMS = {
    "ask", "cut", "choose", "define", "separate", "test", "validate", "name", "write",
    "mark", "remove", "flag", "confirm", "map", "identify", "trace", "check", "recommend",
    "convert", "compare", "pressure", "reject", "keep", "defer", "output",
}
FILLER_TERMS = {
    "generic", "domain-specific", "methodology shell", "another agent", "raw design material",
    "high quality", "robust", "comprehensive", "useful", "clear and concise",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _recall(items: list[str], text: str) -> tuple[float, list[str]]:
    missing = [item for item in items if not _contains_anchor(text, item)]
    return round((len(items) - len(missing)) / max(1, len(items)), 4), missing


def expert_editorial_profile_for_skill(*, skill_name: str, task: str = "") -> ExpertEditorialProfile | None:
    normalized = str(skill_name or "").strip().lower()
    if normalized in EXPERT_EDITORIAL_PROFILES:
        return EXPERT_EDITORIAL_PROFILES[normalized]
    structure_profile = expert_profile_for_skill(skill_name=skill_name, task=task)
    if structure_profile is not None:
        return EXPERT_EDITORIAL_PROFILES.get(structure_profile.skill_name)
    return None


def _bullet_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in str(text or "").splitlines()
        if line.strip().startswith(("- ", "* ", "+ "))
    ]


def _heading_count(text: str) -> int:
    return len(re.findall(r"(?m)^\s{0,3}#{1,6}\s+", str(text or "")))


def _redundancy_ratio(body: str) -> float:
    lines = [
        _normalize(re.sub(r"^[-*+]\s*", "", line.strip()))
        for line in str(body or "").splitlines()
        if line.strip().startswith(("- ", "* ", "+ "))
    ]
    meaningful = [
        re.sub(r"^(do|ask|output|cut watch for|good|weak|symptom|cause|correction)\s+", "", line).strip()
        for line in lines
    ]
    meaningful = [line for line in meaningful if len(line) >= 18]
    if not meaningful:
        return 0.0
    counts = Counter(meaningful)
    duplicate_count = sum(count - 1 for count in counts.values() if count > 1)
    filler_count = sum(1 for line in meaningful if any(term in line for term in FILLER_TERMS))
    return round((duplicate_count + filler_count) / max(1, len(meaningful)), 4)


def _action_density_score(body: str) -> float:
    bullets = _bullet_lines(body)
    if not bullets:
        return 0.0
    hits = 0
    for line in bullets:
        normalized = _normalize(line)
        if any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in ACTION_TERMS):
            hits += 1
    return round(hits / max(1, len(bullets)), 4)


def _decision_pressure_score(*, workflow_text: str, profile: ExpertEditorialProfile | None) -> tuple[float, list[str]]:
    normalized = _normalize(workflow_text)
    structural_hits = 0
    structural_hits += len(re.findall(r"\bask\b", normalized))
    structural_hits += len(
        re.findall(
            r"\b(question|if|must|do not|not|cut|watch for|reject|fail|failure|defer|dangerous|required|enough|"
            r"tradeoff|tension|dominant|collapse|risk|weak|strong|meaningful|optimize|punish|pressure)\b",
            normalized,
        )
    )
    structural_score = min(1.0, structural_hits / 18.0)
    if profile is None:
        return round(structural_score, 4), []
    recall, missing = _recall(profile.decision_terms + profile.cut_terms, workflow_text)
    return round((0.40 * recall) + (0.60 * structural_score), 4), missing


def _output_executability_score(*, output_text: str, profile: ExpertEditorialProfile | None) -> tuple[float, list[str]]:
    lines = [line.strip() for line in str(output_text or "").splitlines() if line.strip()]
    fillable_count = sum(1 for line in lines if re.search(r"(:\s*(<|$)|<[^>]+>|write|good:|weak:)", line.lower()))
    good_weak_count = sum(1 for line in lines if re.search(r"\b(good|weak|write|field)\b", line.lower()))
    structural_score = min(1.0, (fillable_count / 10.0) + (good_weak_count / 18.0))
    if profile is None:
        return round(structural_score, 4), []
    recall, missing = _recall(profile.output_terms, output_text)
    return round((0.55 * recall) + (0.45 * structural_score), 4), missing


def _failure_correction_score(*, pitfall_text: str, profile: ExpertEditorialProfile | None) -> tuple[float, list[str]]:
    normalized = _normalize(pitfall_text)
    triad_score = min(
        1.0,
        (
            len(re.findall(r"\bsymptom\b", normalized))
            + len(re.findall(r"\bcause\b", normalized))
            + len(re.findall(r"\bcorrection\b", normalized))
        )
        / 9.0,
    )
    heading_score = min(1.0, len(re.findall(r"(?m)^###\s+", pitfall_text)) / 4.0)
    structural_score = max(triad_score, heading_score)
    if profile is None:
        return round(structural_score, 4), []
    recall, missing = _recall(profile.failure_terms, pitfall_text)
    return round((0.50 * recall) + (0.50 * structural_score), 4), missing


def _compression_score(*, body: str) -> float:
    lines = [line.strip() for line in str(body or "").splitlines() if line.strip()]
    headings = _heading_count(body)
    bullets = len(_bullet_lines(body))
    line_score = 1.0 if len(lines) <= 230 else max(0.0, 1.0 - ((len(lines) - 230) / 80.0))
    heading_score = 1.0 if headings <= 56 else max(0.0, 1.0 - ((headings - 56) / 25.0))
    bullet_score = 1.0 if bullets <= 170 else max(0.0, 1.0 - ((bullets - 170) / 80.0))
    return round((line_score + heading_score + bullet_score) / 3.0, 4)


def build_skill_editorial_quality_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
) -> SkillEditorialQualityReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillEditorialQualityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["editorial_quality_status=pass", "editorial_quality_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    profile = expert_editorial_profile_for_skill(skill_name=skill_name, task=task)
    workflow_text = _extract_section(body, ("workflow", "default workflow", "process", "steps"))
    output_text = "\n".join(
        [
            _extract_section(body, ("output format", "output template", "deliverable")),
            _extract_section(body, ("output field guidance", "field guidance")),
        ]
    )
    pitfall_text = "\n".join(
        [
            _extract_section(body, ("common pitfalls", "pitfalls")),
            _extract_section(body, ("failure patterns", "failure modes", "failure patterns and fixes")),
        ]
    )

    decision_pressure, missing_decision_terms = _decision_pressure_score(workflow_text=workflow_text, profile=profile)
    output_executability, missing_output_terms = _output_executability_score(output_text=output_text, profile=profile)
    failure_correction, missing_failure_terms = _failure_correction_score(pitfall_text=pitfall_text, profile=profile)
    redundancy_ratio = _redundancy_ratio(body)
    action_density = _action_density_score(body)
    compression_score = _compression_score(body=body)
    expert_cut_alignment, missing_cut_terms = _recall(list(getattr(profile, "cut_terms", []) or []), body) if profile else (0.0, [])

    blocking: list[str] = []
    warnings: list[str] = []
    if profile is None:
        warnings.append("expert_editorial_profile_missing")
        if decision_pressure < 0.60 or output_executability < 0.60:
            warnings.append("editorial_quality_uncertain")
    else:
        if decision_pressure < 0.70:
            blocking.append("low_decision_pressure")
        if output_executability < 0.70:
            blocking.append("weak_output_executability")
        if failure_correction < 0.70:
            blocking.append("thin_failure_corrections")
        if expert_cut_alignment < 0.55:
            blocking.append("missing_expert_cut_moves")
    if redundancy_ratio > 0.25:
        blocking.append("high_redundancy")
    if compression_score < 0.75 and decision_pressure < 0.85:
        blocking.append("excessive_explanatory_bulk")
    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillEditorialQualityReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        profile_available=profile is not None,
        decision_pressure_score=decision_pressure,
        action_density_score=action_density,
        redundancy_ratio=redundancy_ratio,
        output_executability_score=output_executability,
        failure_correction_score=failure_correction,
        compression_score=compression_score,
        expert_cut_alignment=expert_cut_alignment,
        missing_decision_terms=missing_decision_terms,
        missing_cut_terms=missing_cut_terms,
        missing_output_terms=missing_output_terms,
        missing_failure_terms=missing_failure_terms,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"editorial_quality_status={status}",
            f"decision_pressure_score={decision_pressure:.2f}",
            f"action_density_score={action_density:.2f}",
            f"redundancy_ratio={redundancy_ratio:.2f}",
            f"output_executability_score={output_executability:.2f}",
            f"failure_correction_score={failure_correction:.2f}",
            f"compression_score={compression_score:.2f}",
            f"expert_cut_alignment={expert_cut_alignment:.2f}",
        ],
    )


def editorial_quality_artifact(report: SkillEditorialQualityReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/editorial_quality.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["editorial_quality"],
        status="new",
    )
