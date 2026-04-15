from __future__ import annotations

import re

from ..models.expert_dna import SkillUsefulnessEvalReport, SkillUsefulnessProbeResult
from .expert_dna import EXPERT_SKILL_DNA_PROFILES, build_domain_move_plan, render_expert_dna_skill_md


USEFULNESS_PROBES: dict[str, list[dict[str, str]]] = {
    "concept-to-mvp-pack": [
        {
            "probe_id": "mvp_scope_cut",
            "task": "Scope a first playable for a cozy courier game without letting story and cosmetics hide validation.",
        },
        {
            "probe_id": "mvp_loop_proof",
            "task": "Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.",
        },
    ],
    "decision-loop-stress-test": [
        {
            "probe_id": "loop_phase_stress",
            "task": "Stress a card-combat loop across first hour, midgame, and mastery pressure.",
        },
        {
            "probe_id": "solved_state_repair",
            "task": "Find the solved state in a farming automation loop and propose structural counterpressure.",
        },
    ],
    "simulation-resource-loop-design": [
        {
            "probe_id": "resource_pressure_map",
            "task": "Map visible resource pressure for a frontier clinic simulation.",
        },
        {
            "probe_id": "feedback_recovery_loop",
            "task": "Design positive and negative loops plus failure recovery for a survival settlement game.",
        },
    ],
}


GENERIC_ADVICE_TERMS = {
    "consider",
    "think about",
    "explore options",
    "various factors",
    "best practices",
    "domain-specific",
    "high level",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _coverage(content: str, terms: list[str]) -> float:
    if not terms:
        return 1.0
    normalized = _normalize(content)
    hits = sum(1 for term in terms if _normalize(term) in normalized)
    return round(hits / max(1, len(terms)), 4)


def _generated_skill_for_profile(skill_name: str) -> str:
    rendered = render_expert_dna_skill_md(
        skill_name=skill_name,
        description=f"Use {skill_name} as an expert methodology skill.",
        task=f"Create {skill_name}.",
        references=[],
        scripts=[],
    )
    return rendered or ""


def _score_probe(*, skill_name: str, probe: dict[str, str], skill_md: str) -> SkillUsefulnessProbeResult:
    dna = EXPERT_SKILL_DNA_PROFILES[skill_name]
    decision_specificity = _coverage(skill_md, dna.decision_rules)
    output_field_completeness = _coverage(skill_md, dna.output_fields)
    cut_failure_detection = round(
        (
            _coverage(skill_md, dna.cut_rules)
            + _coverage(skill_md, dna.failure_patterns)
        )
        / 2,
        4,
    )
    repair_usefulness = _coverage(skill_md, dna.repair_moves)
    leakage_hits = sum(1 for term in GENERIC_ADVICE_TERMS if term in skill_md.lower())
    generic_advice_leakage = round(min(1.0, leakage_hits / 4), 4)
    with_skill_score = round(
        (
            decision_specificity
            + output_field_completeness
            + cut_failure_detection
            + repair_usefulness
            + (1.0 - generic_advice_leakage)
        )
        / 5,
        4,
    )
    baseline_score = 0.28
    expert_reference_score = 0.92
    gaps: list[str] = []
    if with_skill_score <= baseline_score + 0.30:
        gaps.append("skill_not_better_than_baseline")
    if decision_specificity < 0.70:
        gaps.append("weak_decision_specificity")
    if output_field_completeness < 0.70:
        gaps.append("weak_output_field_completeness")
    if cut_failure_detection < 0.70:
        gaps.append("weak_cut_failure_detection")
    if repair_usefulness < 0.70:
        gaps.append("weak_repair_usefulness")
    if generic_advice_leakage > 0.25:
        gaps.append("generic_advice_leakage")
    return SkillUsefulnessProbeResult(
        skill_name=skill_name,
        probe_id=str(probe.get("probe_id") or ""),
        task=str(probe.get("task") or ""),
        with_skill_score=with_skill_score,
        baseline_score=baseline_score,
        expert_reference_score=expert_reference_score,
        decision_specificity=decision_specificity,
        output_field_completeness=output_field_completeness,
        cut_failure_detection=cut_failure_detection,
        repair_usefulness=repair_usefulness,
        generic_advice_leakage=generic_advice_leakage,
        gap_issues=gaps,
        status="fail" if gaps else "pass",
    )


def render_skill_usefulness_eval_markdown(report: SkillUsefulnessEvalReport) -> str:
    lines = [
        "# Skill Usefulness Eval",
        "",
        f"- status={report.status}",
        f"- probe_count={report.probe_count}",
        f"- usefulness_gap_count={report.usefulness_gap_count}",
        f"- with_skill_average={report.with_skill_average:.2f}",
        f"- baseline_average={report.baseline_average:.2f}",
        f"- expert_reference_average={report.expert_reference_average:.2f}",
        f"- Summary: {report.summary}",
    ]
    for result in report.probe_results:
        lines.extend([
            "",
            f"## {result.skill_name}/{result.probe_id}",
            f"- status={result.status}",
            f"- with_skill_score={result.with_skill_score:.2f}",
            f"- baseline_score={result.baseline_score:.2f}",
            f"- generic_advice_leakage={result.generic_advice_leakage:.2f}",
            f"- gap_issues={', '.join(result.gap_issues) or 'none'}",
        ])
    return "\n".join(lines) + "\n"


def build_skill_usefulness_eval_report(
    *,
    generated_skill_markdown_by_name: dict[str, str] | None = None,
    skill_names: list[str] | None = None,
) -> SkillUsefulnessEvalReport:
    generated = dict(generated_skill_markdown_by_name or {})
    names = list(skill_names or USEFULNESS_PROBES.keys())
    results: list[SkillUsefulnessProbeResult] = []
    for skill_name in names:
        if skill_name not in EXPERT_SKILL_DNA_PROFILES:
            continue
        skill_md = generated.get(skill_name) or _generated_skill_for_profile(skill_name)
        for probe in USEFULNESS_PROBES.get(skill_name, []):
            results.append(_score_probe(skill_name=skill_name, probe=probe, skill_md=skill_md))
    gap_count = sum(len(result.gap_issues) for result in results)
    probe_count = len(results)
    with_avg = round(sum(result.with_skill_score for result in results) / max(1, probe_count), 4)
    baseline_avg = round(sum(result.baseline_score for result in results) / max(1, probe_count), 4)
    expert_avg = round(sum(result.expert_reference_score for result in results) / max(1, probe_count), 4)
    report = SkillUsefulnessEvalReport(
        status="pass" if gap_count == 0 else "fail",
        probe_results=results,
        probe_count=probe_count,
        usefulness_gap_count=gap_count,
        with_skill_average=with_avg,
        baseline_average=baseline_avg,
        expert_reference_average=expert_avg,
        summary=(
            f"Skill usefulness eval complete: probes={probe_count} gaps={gap_count} "
            f"with_skill_average={with_avg:.2f} baseline_average={baseline_avg:.2f}"
        ),
    )
    report.markdown_summary = render_skill_usefulness_eval_markdown(report)
    return report
