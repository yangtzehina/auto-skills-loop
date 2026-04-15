from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.style_diversity import ExpertStyleProfile, SkillStyleDiversityReport
from .body_quality import split_frontmatter
from .domain_specificity import _artifact_content, _contains_anchor, _extract_section, profile_for_skill
from .expert_structure import expert_profile_for_skill


FIXED_RENDERER_PHRASES = (
    "use this skill to turn a rough game-design request into a sharp, execution-facing decision artifact",
    "convert the prompt into concrete design judgments",
    "ask:",
    "cut / watch for:",
    "field guidance:",
)

OPENING_STOPWORDS = {
    "a",
    "an",
    "and",
    "before",
    "into",
    "it",
    "skill",
    "the",
    "this",
    "to",
    "turn",
    "use",
    "with",
}


EXPERT_STYLE_PROFILES: dict[str, ExpertStyleProfile] = {
    "concept-to-mvp-pack": ExpertStyleProfile(
        skill_name="concept-to-mvp-pack",
        opening_frame="Use this skill to decide what the first playable proof must test, keep, cut, and package.",
        workflow_label_set=["test", "keep", "cut", "package"],
        signature_moves=[
            "validation question can fail",
            "smallest honest loop",
            "feature cut",
            "out-of-scope",
            "scope creep",
        ],
        section_rhythm=["proof first", "build target", "scope boundary"],
        forbidden_boilerplate=list(FIXED_RENDERER_PHRASES),
    ),
    "decision-loop-stress-test": ExpertStyleProfile(
        skill_name="decision-loop-stress-test",
        opening_frame="Use this skill to stress a game loop across first-hour, midgame, and mastery pressure before adding content.",
        workflow_label_set=["stress", "watch", "break", "reinforce"],
        signature_moves=[
            "first hour",
            "midgame",
            "lategame",
            "solved state",
            "dominant strategy",
            "variation quality",
            "reinforcement",
        ],
        section_rhythm=["phase pressure", "collapse point", "structural fix"],
        forbidden_boilerplate=list(FIXED_RENDERER_PHRASES),
    ),
    "simulation-resource-loop-design": ExpertStyleProfile(
        skill_name="simulation-resource-loop-design",
        opening_frame="Use this skill to map resource pressure into visible choices, feedback loops, recovery, and fantasy alignment.",
        workflow_label_set=["map", "tension", "loop", "correct"],
        signature_moves=[
            "variable web",
            "pressure relationships",
            "positive loop",
            "negative loop",
            "failure recovery",
            "emotional fantasy",
        ],
        section_rhythm=["system map", "pressure rhythm", "recovery cost"],
        forbidden_boilerplate=list(FIXED_RENDERER_PHRASES),
    ),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/]+", " ", str(text or "").lower())).strip()


def expert_style_profile_for_skill(*, skill_name: str, task: str = "") -> ExpertStyleProfile | None:
    normalized = str(skill_name or "").strip().lower()
    if normalized in EXPERT_STYLE_PROFILES:
        return EXPERT_STYLE_PROFILES[normalized]
    structure_profile = expert_profile_for_skill(skill_name=skill_name, task=task)
    if structure_profile is not None:
        return EXPERT_STYLE_PROFILES.get(structure_profile.skill_name)
    domain_profile = profile_for_skill(skill_name=skill_name, task=task)
    if domain_profile is not None:
        return EXPERT_STYLE_PROFILES.get(domain_profile.skill_name)
    return None


def _body_opening(body: str) -> str:
    seen_title = False
    paragraph: list[str] = []
    in_fence = False
    for line in str(body or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("#"):
            if not seen_title:
                seen_title = True
                continue
            if paragraph:
                break
            continue
        if not seen_title:
            continue
        if stripped:
            paragraph.append(stripped)
        elif paragraph:
            break
    return " ".join(paragraph).strip()


def _workflow_labels(workflow_text: str) -> list[str]:
    numbered_labels: list[str] = []
    for line in str(workflow_text or "").splitlines():
        numbered = re.match(r"\s*\d+\.\s+(?:\*\*)?([^*\n]+?)(?:\*\*)?\s*$", line)
        if not numbered:
            continue
        label = _normalize(numbered.group(1))
        if label and label not in numbered_labels:
            numbered_labels.append(label)
    if numbered_labels:
        return numbered_labels

    labels: list[str] = []
    for line in str(workflow_text or "").splitlines():
        match = re.match(r"\s*[-*+]\s+([^:\n]{2,48}):", line)
        if not match:
            continue
        label = _normalize(match.group(1))
        if label and label not in labels:
            labels.append(label)
    return labels


def _boilerplate_sentences(body: str) -> list[str]:
    sentences: list[str] = []
    for line in str(body or "").splitlines():
        stripped = re.sub(r"^\s*[-*+]\s*", "", line.strip())
        if len(stripped) < 28:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", stripped):
            normalized = _normalize(sentence)
            if len(normalized) >= 24 and normalized not in sentences:
                sentences.append(normalized)
    return sentences


def style_signature_from_markdown(content: str) -> dict[str, Any]:
    _, body = split_frontmatter(content)
    workflow_text = _extract_section(body, ("workflow", "default workflow", "process", "steps"))
    return {
        "opening": _normalize(_body_opening(body)),
        "workflow_labels": _workflow_labels(workflow_text),
        "boilerplate_sentences": _boilerplate_sentences(body),
    }


def _recall(items: list[str], text: str) -> tuple[float, list[str]]:
    missing = [item for item in items if not _contains_anchor(text, item)]
    return round((len(items) - len(missing)) / max(1, len(items)), 4), missing


def _fixed_phrase_count(body: str, profile: ExpertStyleProfile | None) -> int:
    lowered = str(body or "").lower()
    phrases = list(getattr(profile, "forbidden_boilerplate", []) or FIXED_RENDERER_PHRASES)
    count = 0
    for phrase in phrases:
        normalized_phrase = _normalize(phrase)
        if normalized_phrase in {"do", "ask", "output", "cut / watch for", "field guidance"}:
            pattern = re.escape(str(phrase).rstrip(":"))
            if re.search(rf"(?mi)^\s*[-*+]\s+{pattern}\s*:", str(body or "")):
                count += 1
            continue
        if normalized_phrase and normalized_phrase in _normalize(lowered):
            count += 1
    return count


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", _normalize(text))
        if token not in OPENING_STOPWORDS and len(token) > 2
    }


def _opening_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if _normalize(left) == _normalize(right):
        return 1.0
    left_tokens = _content_tokens(left)
    right_tokens = _content_tokens(right)
    if not left_tokens or not right_tokens:
        return round(SequenceMatcher(None, left, right).ratio(), 4)
    return round(len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens)), 4)


def shared_opening_ratio(left: str, right: str) -> float:
    return _opening_similarity(_normalize(left), _normalize(right))


def shared_step_label_ratio(left: list[str], right: list[str]) -> float:
    left_set = {_normalize(item) for item in list(left or []) if _normalize(item)}
    right_set = {_normalize(item) for item in list(right or []) if _normalize(item)}
    if not left_set or not right_set:
        return 0.0
    return round(len(left_set & right_set) / max(1, len(left_set | right_set)), 4)


def shared_boilerplate_sentence_ratio(left: list[str], right: list[str]) -> float:
    left_set = {_normalize(item) for item in list(left or []) if _normalize(item)}
    right_set = {_normalize(item) for item in list(right or []) if _normalize(item)}
    if not left_set or not right_set:
        return 0.0
    return round(len(left_set & right_set) / max(1, min(len(left_set), len(right_set))), 4)


def build_skill_style_diversity_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    shared_opening_phrase_ratio: float = 0.0,
    shared_step_label_ratio_value: float = 0.0,
    shared_boilerplate_sentence_ratio_value: float = 0.0,
) -> SkillStyleDiversityReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillStyleDiversityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["style_diversity_status=pass", "style_diversity_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    workflow_text = _extract_section(body, ("workflow", "default workflow", "process", "steps"))
    workflow_labels = _workflow_labels(workflow_text)
    label_text = f"{' '.join(workflow_labels)} {workflow_text}"
    fixed_count = _fixed_phrase_count(body, profile)
    label_coverage, missing_labels = _recall(list(getattr(profile, "workflow_label_set", []) or []), label_text) if profile else (0.0, [])
    signature_recall, _ = _recall(list(getattr(profile, "signature_moves", []) or []), body) if profile else (0.0, [])
    rhythm_score = round((0.60 * label_coverage) + (0.40 * signature_recall), 4) if profile else 0.0

    shared_opening = round(float(shared_opening_phrase_ratio or 0.0), 4)
    shared_labels = round(float(shared_step_label_ratio_value or 0.0), 4)
    shared_boilerplate = round(float(shared_boilerplate_sentence_ratio_value or 0.0), 4)

    blocking: list[str] = []
    warnings: list[str] = []
    if profile is None:
        warnings.append("expert_style_profile_missing")
        if fixed_count >= 3:
            warnings.append("fixed_renderer_boilerplate")
    else:
        if shared_opening > 0.35:
            blocking.append("shared_opening_phrase")
        if shared_labels > 0.55:
            blocking.append("shared_step_labels")
        if shared_boilerplate > 0.35:
            blocking.append("shared_boilerplate_sentences")
        if label_coverage < 0.70:
            blocking.append("profile_specific_labels_missing")
        if fixed_count >= 3:
            blocking.append("fixed_renderer_boilerplate")
        elif fixed_count > 0:
            warnings.append("fixed_renderer_phrase_present")
        if rhythm_score < 0.70:
            blocking.append("weak_domain_rhythm")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillStyleDiversityReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        profile_available=profile is not None,
        shared_opening_phrase_ratio=shared_opening,
        shared_step_label_ratio=shared_labels,
        shared_boilerplate_sentence_ratio=shared_boilerplate,
        fixed_renderer_phrase_count=fixed_count,
        profile_specific_label_coverage=label_coverage,
        domain_rhythm_score=rhythm_score,
        workflow_labels=workflow_labels,
        missing_profile_labels=missing_labels,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"style_diversity_status={status}",
            f"shared_opening_phrase_ratio={shared_opening:.2f}",
            f"shared_step_label_ratio={shared_labels:.2f}",
            f"shared_boilerplate_sentence_ratio={shared_boilerplate:.2f}",
            f"fixed_renderer_phrase_count={fixed_count}",
            f"profile_specific_label_coverage={label_coverage:.2f}",
            f"domain_rhythm_score={rhythm_score:.2f}",
        ],
    )


def style_diversity_artifact(report: SkillStyleDiversityReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/style_diversity.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["style_diversity"],
        status="new",
    )
