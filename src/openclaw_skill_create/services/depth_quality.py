from __future__ import annotations

import json
import re
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.depth_quality import ExpertDepthProfile, SkillDepthQualityReport
from .body_quality import split_frontmatter
from .domain_specificity import _artifact_content, _contains_anchor, _extract_section
from .expert_structure import expert_profile_for_skill


EXPERT_DEPTH_PROFILES: dict[str, ExpertDepthProfile] = {
    "concept-to-mvp-pack": ExpertDepthProfile(
        skill_name="concept-to-mvp-pack",
        depth_terms=[
            "validation question",
            "central design hypothesis",
            "smallest honest loop",
            "player input",
            "system response",
            "visible feedback",
            "repeat trigger",
            "core supportive later cut",
            "minimum content package",
            "required systems",
            "out of scope",
            "success criteria",
            "first playable",
            "prototype first",
        ],
        decision_probes=[
            "what exactly is the MVP trying to validate",
            "what would count as validated",
            "how much content is enough",
            "what to prototype first",
        ],
        output_guidance_terms=[
            "validation goal",
            "minimum honest loop",
            "core features",
            "minimum content scope",
            "required systems",
            "explicitly out of scope",
            "main production risks",
            "build recommendation",
        ],
        boundary_rules=[
            "not a dream expanding skill",
            "kill list",
            "cut aggressively",
            "do not fake the entire game",
            "scope creep",
        ],
        failure_patterns=[
            "fake MVP",
            "scope creep",
            "content-heavy validation",
            "premature meta systems",
            "success criteria missing",
        ],
        quality_rubric_terms=[
            "testability",
            "execution-ready scope",
            "keep the loop honest",
            "prefer testability over impressiveness",
        ],
    ),
    "decision-loop-stress-test": ExpertDepthProfile(
        skill_name="decision-loop-stress-test",
        depth_terms=[
            "current loop shape",
            "uncertainty",
            "resources or states move",
            "first-hour hook",
            "cause-and-effect chain",
            "midgame sustainability",
            "compounding tradeoffs",
            "late-game expansion",
            "solved states",
            "dominant strategy",
            "variation quality",
            "decision variation",
            "reinforcement recommendations",
        ],
        decision_probes=[
            "does this loop hold up beyond the pitch",
            "why would the player still care",
            "what prevents the game from flattening",
            "can the player figure out the answer",
        ],
        output_guidance_terms=[
            "loop under test",
            "first-hour performance",
            "midgame performance",
            "late-game performance",
            "solved-state risks",
            "variation quality",
            "reinforcement recommendations",
        ],
        boundary_rules=[
            "not about greenlighting the theme",
            "not MVP scope cutting",
            "not detailed numeric balancing",
            "decision quality",
        ],
        failure_patterns=[
            "novelty-only start",
            "midgame autopilot",
            "progression without new problems",
            "variety without strategic consequence",
            "mastery removes the game",
        ],
        quality_rubric_terms=[
            "where collapse happens",
            "structural fixes",
            "healthy mastery",
            "decision quality",
        ],
    ),
    "simulation-resource-loop-design": ExpertDepthProfile(
        skill_name="simulation-resource-loop-design",
        depth_terms=[
            "interacting pressures",
            "time money energy reputation relationships",
            "pressure relationships",
            "resource web",
            "variable role",
            "conversion",
            "amplification",
            "decay",
            "threshold",
            "feedback loop",
            "primary decision tensions",
            "positive loops",
            "negative loops",
            "counter-pressure",
            "failure recovery",
            "emotional fantasy",
        ],
        decision_probes=[
            "what choices hurt in an interesting way",
            "what can the player never maximize all at once",
            "how does the player notice it early",
            "what the player is really chasing",
        ],
        output_guidance_terms=[
            "core resources pressures",
            "pressure relationships",
            "primary decision tensions",
            "positive loops",
            "negative counter loops",
            "failure and recovery",
            "emotional fantasy alignment",
            "design recommendations",
        ],
        boundary_rules=[
            "not just one simple currency",
            "not mostly content writing",
            "only include it if it changes player behavior",
            "not isolated meters",
            "few strong tensions",
        ],
        failure_patterns=[
            "decorative resources",
            "no real tradeoff",
            "one dominant currency",
            "positive-loop runaway",
            "punishment without agency",
            "fantasy-system mismatch",
        ],
        quality_rubric_terms=[
            "player-facing tradeoffs",
            "pressure web",
            "aspiration and consequence",
            "emotional or structural backlash",
        ],
    ),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def expert_depth_profile_for_skill(*, skill_name: str, task: str = "") -> ExpertDepthProfile | None:
    normalized = str(skill_name or "").strip().lower()
    if normalized in EXPERT_DEPTH_PROFILES:
        return EXPERT_DEPTH_PROFILES[normalized]
    structure_profile = expert_profile_for_skill(skill_name=skill_name, task=task)
    if structure_profile is not None:
        return EXPERT_DEPTH_PROFILES.get(structure_profile.skill_name)
    return None


def _recall(items: list[str], text: str) -> tuple[float, list[str]]:
    missing = [item for item in items if not _contains_anchor(text, item)]
    return round((len(items) - len(missing)) / max(1, len(items)), 4), missing


def _line_count(text: str) -> int:
    return len([line for line in str(text or "").splitlines() if line.strip()])


def _thin_sections(*sections: str) -> int:
    return sum(1 for section in sections if _line_count(section) < 8)


def _decision_probe_count(body: str) -> int:
    question_count = len(re.findall(r"\?", body))
    explicit_probe_count = len(
        re.findall(
            r"\b(ask|check|probe|test|validate|what|why|how|whether)\b",
            _normalize(body),
        )
    )
    return min(12, question_count + (explicit_probe_count // 8))


def _worked_example_count(body: str) -> int:
    normalized = _normalize(body)
    return len(re.findall(r"\b(example|examples|for example|worked example|micro example|sample)\b", normalized))


def _failure_pattern_density(pitfall_text: str) -> int:
    heading_count = len(re.findall(r"(?m)^###\s+", pitfall_text))
    explicit_count = len(
        re.findall(
            r"\b(symptom|cause|correction|failure|pitfall|risk|collapse|creep|autopilot|runaway|death spiral|mismatch)\b",
            _normalize(pitfall_text),
        )
    )
    return heading_count + min(8, explicit_count // 2)


def _section_depth_score(
    *,
    workflow_text: str,
    output_text: str,
    pitfall_text: str,
    quality_text: str,
    decision_probe_count: int,
    worked_example_count: int,
    failure_pattern_density: int,
    output_guidance_coverage: float,
    boundary_rule_coverage: float,
) -> float:
    components = [
        min(1.0, _line_count(workflow_text) / 45.0),
        min(1.0, _line_count(output_text) / 28.0),
        min(1.0, _line_count(pitfall_text) / 20.0),
        min(1.0, _line_count(quality_text) / 10.0),
        min(1.0, decision_probe_count / 4.0),
        1.0 if worked_example_count >= 1 else 0.0,
        min(1.0, failure_pattern_density / 4.0),
        min(1.0, output_guidance_coverage),
        min(1.0, boundary_rule_coverage),
    ]
    return round(sum(components) / len(components), 4)


def build_skill_depth_quality_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
) -> SkillDepthQualityReport:
    skill_md = _artifact_content(artifacts, "SKILL.md")
    frontmatter, body = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, "skill_name", "") or frontmatter.get("name", "") or "")
    skill_archetype = str(getattr(skill_plan, "skill_archetype", "guidance") or "guidance").strip().lower()
    if skill_archetype != "methodology_guidance":
        return SkillDepthQualityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="pass",
            summary=["depth_quality_status=pass", "depth_quality_skipped=non_methodology"],
        )

    task = str(getattr(request, "task", "") or "")
    profile = expert_depth_profile_for_skill(skill_name=skill_name, task=task)
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
            _extract_section(body, ("common failure patterns", "failure modes", "failure patterns")),
        ]
    )
    quality_text = _extract_section(body, ("quality checks", "quality bar", "acceptance", "checks"))
    boundary_text = "\n".join(
        [
            _extract_section(body, ("when not to use", "boundaries", "boundary rules", "out of scope")),
            workflow_text,
            pitfall_text,
        ]
    )

    decision_probe_count = _decision_probe_count(workflow_text or body)
    worked_example_count = _worked_example_count(body)
    failure_pattern_density = _failure_pattern_density(pitfall_text)
    thin_section_count = _thin_sections(workflow_text, output_text, pitfall_text, quality_text)

    if profile is None:
        section_depth_score = _section_depth_score(
            workflow_text=workflow_text,
            output_text=output_text,
            pitfall_text=pitfall_text,
            quality_text=quality_text,
            decision_probe_count=decision_probe_count,
            worked_example_count=worked_example_count,
            failure_pattern_density=failure_pattern_density,
            output_guidance_coverage=0.0,
            boundary_rule_coverage=0.0,
        )
        warnings = ["expert_depth_profile_missing"]
        if section_depth_score < 0.55:
            warnings.append("methodology_depth_uncertain")
        return SkillDepthQualityReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status="warn",
            profile_available=False,
            section_depth_score=section_depth_score,
            decision_probe_count=decision_probe_count,
            worked_example_count=worked_example_count,
            failure_pattern_density=failure_pattern_density,
            thin_section_count=thin_section_count,
            warning_issues=warnings,
            summary=[
                "depth_quality_status=warn",
                "expert_depth_profile_available=false",
                f"section_depth_score={section_depth_score:.2f}",
            ],
        )

    expert_depth_recall, missing_depth_terms = _recall(profile.depth_terms + profile.quality_rubric_terms, body)
    output_field_guidance_coverage, missing_output_guidance = _recall(profile.output_guidance_terms, output_text)
    boundary_rule_coverage, missing_boundary_rules = _recall(profile.boundary_rules, boundary_text)
    failure_recall, missing_failure_patterns = _recall(profile.failure_patterns, pitfall_text)
    probe_recall, _ = _recall(profile.decision_probes, workflow_text or body)
    section_depth_score = _section_depth_score(
        workflow_text=workflow_text,
        output_text=output_text,
        pitfall_text=pitfall_text,
        quality_text=quality_text,
        decision_probe_count=decision_probe_count,
        worked_example_count=worked_example_count,
        failure_pattern_density=failure_pattern_density,
        output_guidance_coverage=output_field_guidance_coverage,
        boundary_rule_coverage=boundary_rule_coverage,
    )

    blocking: list[str] = []
    warnings: list[str] = []
    if expert_depth_recall < 0.70:
        blocking.append("low_expert_depth_recall")
    if section_depth_score < 0.65:
        blocking.append("shallow_workflow_steps")
    if decision_probe_count < 4 and probe_recall < 0.35:
        blocking.append("missing_decision_probes")
    if worked_example_count < 1 and expert_depth_recall < 0.95:
        blocking.append("missing_worked_examples")
    if failure_pattern_density < 4 or failure_recall < 0.55:
        blocking.append("thin_failure_patterns")
    if output_field_guidance_coverage < 0.70:
        blocking.append("weak_output_field_guidance")
    if boundary_rule_coverage < 0.20 and section_depth_score < 0.75:
        warnings.append("boundary_rules_thin")
    if thin_section_count >= 2:
        blocking.append("shallow_workflow_steps")

    status = "fail" if blocking else ("warn" if warnings else "pass")
    return SkillDepthQualityReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        profile_available=True,
        section_depth_score=section_depth_score,
        expert_depth_recall=expert_depth_recall,
        decision_probe_count=decision_probe_count,
        worked_example_count=worked_example_count,
        failure_pattern_density=failure_pattern_density,
        output_field_guidance_coverage=output_field_guidance_coverage,
        boundary_rule_coverage=boundary_rule_coverage,
        thin_section_count=thin_section_count,
        missing_depth_terms=missing_depth_terms,
        missing_output_guidance_terms=missing_output_guidance,
        missing_boundary_rules=missing_boundary_rules,
        missing_failure_patterns=missing_failure_patterns,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        summary=[
            f"depth_quality_status={status}",
            f"section_depth_score={section_depth_score:.2f}",
            f"expert_depth_recall={expert_depth_recall:.2f}",
            f"decision_probe_count={decision_probe_count}",
            f"worked_example_count={worked_example_count}",
            f"failure_pattern_density={failure_pattern_density}",
            f"output_field_guidance_coverage={output_field_guidance_coverage:.2f}",
            f"boundary_rule_coverage={boundary_rule_coverage:.2f}",
        ],
    )


def depth_quality_artifact(report: SkillDepthQualityReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/depth_quality.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["depth_quality"],
        status="new",
    )
