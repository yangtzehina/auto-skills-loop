from __future__ import annotations

import json
import math
import re

from ..models.artifacts import ArtifactFile
from ..models.expert_studio import (
    ExpertTaskProbe,
    SkillTaskOutcomeProbeResult,
    SkillTaskOutcomeProfileResult,
    SkillTaskOutcomeReport,
)
from .expert_skill_studio import expert_corpus_entry_for_skill


GENERIC_ADVICE_TERMS = {
    "consider",
    "think about",
    "explore options",
    "various factors",
    "best practices",
    "high level",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _coverage(content: str, terms: list[str]) -> float:
    if not terms:
        return 1.0
    normalized = _normalize(content)
    normalized_tokens = set(normalized.split())
    hits = 0
    for term in terms:
        normalized_term = _normalize(term)
        if not normalized_term:
            continue
        if normalized_term in normalized:
            hits += 1
            continue
        tokens = [token for token in normalized_term.split() if len(token) >= 3]
        if not tokens:
            continue
        overlap = sum(1 for token in tokens if token in normalized_tokens)
        if overlap >= max(1, math.ceil(len(tokens) * 0.6)):
            hits += 1
    return round(hits / max(1, len(terms)), 4)


def _score_probe(*, skill_name: str, probe: ExpertTaskProbe, skill_md: str) -> SkillTaskOutcomeProbeResult:
    decision_specificity = _coverage(skill_md, list(probe.decision_terms or []))
    cut_strength = _coverage(skill_md, list(probe.cut_terms or []))
    failure_detection = _coverage(skill_md, list(probe.failure_terms or []))
    repair_usefulness = _coverage(skill_md, list(probe.repair_terms or []))
    output_fillability = _coverage(skill_md, list(probe.output_fields or []))
    leakage_hits = sum(1 for term in GENERIC_ADVICE_TERMS if term in skill_md.lower())
    generic_advice_leakage = round(min(1.0, leakage_hits / 4), 4)
    with_skill_score = round(
        (
            decision_specificity
            + cut_strength
            + failure_detection
            + repair_usefulness
            + output_fillability
            + (1.0 - generic_advice_leakage)
        )
        / 6,
        4,
    )
    baseline_score = 0.26
    expert_reference_score = 0.93
    gaps: list[str] = []
    if with_skill_score <= baseline_score + 0.15:
        gaps.append("skill_not_better_than_baseline")
    if decision_specificity < 0.55:
        gaps.append("weak_decision_specificity")
    if cut_strength < 0.34:
        gaps.append("weak_cut_strength")
    if failure_detection < 0.34:
        gaps.append("weak_failure_detection")
    if repair_usefulness < 0.34:
        gaps.append("weak_repair_usefulness")
    if output_fillability < 0.70:
        gaps.append("weak_output_fillability")
    if generic_advice_leakage > 0.25:
        gaps.append("generic_advice_leakage")
    blocking = {
        issue
        for issue in gaps
        if issue in {
            "skill_not_better_than_baseline",
            "weak_decision_specificity",
            "weak_output_fillability",
            "generic_advice_leakage",
        }
    }
    return SkillTaskOutcomeProbeResult(
        skill_name=skill_name,
        probe_id=probe.probe_id,
        task=probe.task,
        with_skill_score=with_skill_score,
        baseline_score=baseline_score,
        expert_reference_score=expert_reference_score,
        decision_specificity=decision_specificity,
        cut_strength=cut_strength,
        failure_detection=failure_detection,
        repair_usefulness=repair_usefulness,
        output_fillability=output_fillability,
        generic_advice_leakage=generic_advice_leakage,
        gap_issues=gaps,
        status="fail" if blocking else "pass",
    )


def build_skill_task_outcome_report(
    *,
    generated_skill_markdown_by_name: dict[str, str] | None = None,
    skill_names: list[str] | None = None,
) -> SkillTaskOutcomeReport:
    generated = dict(generated_skill_markdown_by_name or {})
    names = list(skill_names or generated.keys() or [])
    profile_results: list[SkillTaskOutcomeProfileResult] = []
    for skill_name in names:
        corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
        if corpus is None or not corpus.task_probes or not str(corpus.expert_skill_markdown or "").strip():
            continue
        skill_md = generated.get(skill_name) or corpus.expert_skill_markdown
        probe_results = [_score_probe(skill_name=skill_name, probe=probe, skill_md=skill_md) for probe in corpus.task_probes]
        pass_count = sum(1 for result in probe_results if result.status == "pass")
        required_pass_count = max(2, (len(probe_results) * 2 + 2) // 3)
        gap_issues: list[str] = []
        if pass_count < required_pass_count:
            gap_issues.append("probe_pass_rate_low")
        if any("generic_advice_leakage" in result.gap_issues for result in probe_results):
            gap_issues.append("generic_advice_leakage")
        with_skill_average = round(sum(item.with_skill_score for item in probe_results) / max(1, len(probe_results)), 4)
        baseline_average = round(sum(item.baseline_score for item in probe_results) / max(1, len(probe_results)), 4)
        expert_reference_average = round(sum(item.expert_reference_score for item in probe_results) / max(1, len(probe_results)), 4)
        if with_skill_average <= baseline_average + 0.15:
            gap_issues.append("skill_not_better_than_baseline")
        profile_results.append(
            SkillTaskOutcomeProfileResult(
                skill_name=skill_name,
                status="pass" if not gap_issues else "fail",
                probe_results=probe_results,
                probe_count=len(probe_results),
                pass_count=pass_count,
                with_skill_average=with_skill_average,
                baseline_average=baseline_average,
                expert_reference_average=expert_reference_average,
                gap_issues=gap_issues,
            )
        )
    probe_count = sum(item.probe_count for item in profile_results)
    gap_count = sum(len(item.gap_issues) for item in profile_results)
    with_avg = round(sum(item.with_skill_average for item in profile_results) / max(1, len(profile_results)), 4)
    baseline_avg = round(sum(item.baseline_average for item in profile_results) / max(1, len(profile_results)), 4)
    expert_avg = round(sum(item.expert_reference_average for item in profile_results) / max(1, len(profile_results)), 4)
    status = "pass" if not profile_results else ("pass" if all(item.status == "pass" for item in profile_results) else "fail")
    report = SkillTaskOutcomeReport(
        status=status,
        profile_results=profile_results,
        probe_count=probe_count,
        task_outcome_gap_count=gap_count,
        with_skill_average=with_avg,
        baseline_average=baseline_avg,
        expert_reference_average=expert_avg,
        summary=(
            f"Task outcome eval complete: profiles={len(profile_results)} probes={probe_count} gaps={gap_count} "
            f"with_skill_average={with_avg:.2f} baseline_average={baseline_avg:.2f}"
            if profile_results
            else "Task outcome eval skipped: no checked-in expert probes for this skill."
        ),
    )
    lines = [
        "# Skill Task Outcome Eval",
        "",
        f"- status={report.status}",
        f"- probe_count={report.probe_count}",
        f"- task_outcome_gap_count={report.task_outcome_gap_count}",
        f"- with_skill_average={report.with_skill_average:.2f}",
        f"- baseline_average={report.baseline_average:.2f}",
        f"- expert_reference_average={report.expert_reference_average:.2f}",
        f"- Summary: {report.summary}",
    ]
    for item in report.profile_results:
        lines.extend(
            [
                "",
                f"## {item.skill_name}",
                f"- status={item.status}",
                f"- pass_count={item.pass_count}/{item.probe_count}",
                f"- gap_issues={', '.join(item.gap_issues) or 'none'}",
            ]
        )
    report.markdown_summary = "\n".join(lines) + "\n"
    return report


def task_outcome_artifact(report: SkillTaskOutcomeReport) -> ArtifactFile:
    return ArtifactFile(
        path="evals/task_outcome.json",
        content=json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["task_outcome"],
        status="new",
    )
