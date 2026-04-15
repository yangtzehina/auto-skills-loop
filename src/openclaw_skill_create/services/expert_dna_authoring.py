from __future__ import annotations

import re
from pathlib import Path

from ..models.expert_dna import (
    CandidateExpertSkillDNA,
    ExpertDNAAuthoringPack,
    ExpertDNAReviewBatchReport,
    ExpertDNAReviewReport,
    ExpertSkillDNA,
    ExpertWorkflowMove,
)
from .expert_dna import EXPERT_SKILL_DNA_PROFILES, expert_skill_dna_for_skill


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXPERT_DNA_GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "expert_depth_golden"


DEFAULT_AUTHORING_CASES: list[dict[str, str]] = [
    {
        "skill_name": "concept-to-mvp-pack",
        "task": "Create a game design methodology skill for packaging a rough concept into a falsifiable MVP.",
    },
    {
        "skill_name": "decision-loop-stress-test",
        "task": "Create a methodology skill for stress-testing a game decision loop across player mastery phases.",
    },
    {
        "skill_name": "simulation-resource-loop-design",
        "task": "Create a methodology skill for designing visible simulation resource pressure loops.",
    },
    {
        "skill_name": "go-to-market-decision-brief",
        "task": "Create a methodology skill for writing a go-to-market decision brief.",
    },
    {
        "skill_name": "agent-skill-abuse-review",
        "task": "Create a methodology skill for reviewing agent skills for abuse and security risk.",
    },
    {
        "skill_name": "messy-dataset-analysis-plan",
        "task": "Create a methodology skill for planning messy dataset analysis.",
    },
    {
        "skill_name": "architecture-tradeoff-review",
        "task": "Create a methodology skill for reviewing architecture tradeoffs.",
    },
    {
        "skill_name": "research-memo-synthesis",
        "task": "Create a methodology skill for synthesizing a research memo.",
    },
]


GENERIC_SHELL_PHRASES = {
    "use this skill to turn",
    "concrete decision artifact",
    "domain-specific decisions",
    "another agent should be able",
    "avoid generic shell",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _split_terms(text: str) -> list[str]:
    stop = {
        "create",
        "methodology",
        "skill",
        "using",
        "with",
        "into",
        "from",
        "that",
        "this",
        "brief",
        "review",
        "plan",
        "design",
    }
    terms: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", str(text or "")):
        normalized = token.strip("-").lower()
        if normalized and normalized not in stop and normalized not in terms:
            terms.append(normalized)
    return terms[:8]


def _headings(content: str) -> list[str]:
    headings: list[str] = []
    in_fence = False
    for raw in str(content or "").splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        if heading and heading.lower() not in {"overview", "workflow", "output format", "quality checks", "common pitfalls"}:
            headings.append(heading)
    return headings


def _looks_like_generic_shell(content: str) -> bool:
    normalized = _normalize(content)
    phrase_hits = sum(1 for phrase in GENERIC_SHELL_PHRASES if phrase in normalized)
    has_numbered_decisions = bool(re.search(r"^\s*\d+\.\s+\*\*.+\*\*", str(content or ""), flags=re.MULTILINE))
    has_failure_fix = "failure signal" in normalized and "fix" in normalized
    return phrase_hits >= 2 and not (has_numbered_decisions and has_failure_fix)


def _golden_for_skill(skill_name: str, golden_root: Path = DEFAULT_EXPERT_DNA_GOLDEN_ROOT) -> str:
    path = golden_root / f"{skill_name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _derived_candidate_dna(*, skill_name: str, task_brief: str, generated_skill_md: str, expert_reference_md: str) -> ExpertSkillDNA:
    headings = _headings(expert_reference_md) or _headings(generated_skill_md)
    terms = _split_terms(" ".join([task_brief, expert_reference_md, generated_skill_md]))
    move_names = [heading for heading in headings if len(heading.split()) >= 2][:6]
    if not move_names:
        move_names = [f"Work through {term.replace('-', ' ')}" for term in terms[:4]]
    moves = [
        ExpertWorkflowMove(
            name=name,
            purpose=f"Clarify the {name.lower()} judgment.",
            decision_probe=f"What decision must the {name.lower()} step make?",
            action=f"Turn evidence about {name.lower()} into an explicit choice.",
            output_fragment=f"{name}: decision, evidence, risk, and next action.",
            failure_signal=f"The {name.lower()} step stays descriptive instead of making a judgment.",
            repair_move=f"Rewrite {name.lower()} as a decision with evidence and a correction.",
            must_include_terms=terms[:5],
        )
        for name in move_names
    ]
    output_fields = move_names[:6] or [term.replace("-", " ").title() for term in terms[:5]]
    return ExpertSkillDNA(
        skill_name=skill_name,
        core_thesis=f"{skill_name} needs an expert move sequence, not a generic methodology shell.",
        workflow_moves=moves,
        output_fields=output_fields,
        decision_rules=[f"{term.replace('-', ' ')} decision is explicit" for term in terms[:6]],
        cut_rules=["remove generic advice that does not change the decision"],
        failure_patterns=["Generic Advice Leakage", "Missing Decision", "Weak Repair"],
        repair_moves=["replace description with a decision, evidence, and correction"],
        voice_rules=["specific", "evidence-based", "decision-facing"],
        numbered_spine=[_normalize(name) for name in move_names],
    )


def _checked_in_move_recall(candidate: ExpertSkillDNA, checked_in: ExpertSkillDNA | None) -> float:
    if checked_in is None or not checked_in.workflow_moves:
        return 0.0
    candidate_moves = {_normalize(move.name) for move in candidate.workflow_moves}
    expected_moves = {_normalize(move.name) for move in checked_in.workflow_moves}
    return round(len(candidate_moves & expected_moves) / max(1, len(expected_moves)), 4)


def build_expert_dna_authoring_candidate(
    *,
    skill_name: str,
    task_brief: str = "",
    generated_skill_md: str = "",
    expert_reference_md: str = "",
    design_notes: str = "",
    golden_root: Path = DEFAULT_EXPERT_DNA_GOLDEN_ROOT,
) -> CandidateExpertSkillDNA:
    checked_in = expert_skill_dna_for_skill(skill_name=skill_name, task=task_brief)
    reference = expert_reference_md or _golden_for_skill(skill_name, golden_root=golden_root)
    evidence_sources: list[str] = []
    if reference:
        evidence_sources.append("expert_golden")
    if generated_skill_md:
        evidence_sources.append("generated_skill")
    if design_notes:
        evidence_sources.append("design_notes")
    if checked_in is not None:
        evidence_sources.append("checked_in_profile")
    if checked_in is not None and reference:
        candidate = checked_in.model_copy(deep=True)
        confidence = "ready_for_review"
        missing_evidence: list[str] = []
        stable_sequence = True
    elif _looks_like_generic_shell(generated_skill_md):
        candidate = _derived_candidate_dna(
            skill_name=skill_name,
            task_brief=task_brief,
            generated_skill_md=generated_skill_md,
            expert_reference_md=reference,
        )
        confidence = "reject"
        missing_evidence = ["expert_golden", "stable_domain_move_sequence"]
        stable_sequence = False
    else:
        candidate = _derived_candidate_dna(
            skill_name=skill_name,
            task_brief=task_brief,
            generated_skill_md=generated_skill_md,
            expert_reference_md=reference,
        )
        confidence = "needs_human_authoring"
        missing_evidence = []
        if not reference:
            missing_evidence.append("expert_golden")
        if checked_in is None:
            missing_evidence.append("checked_in_expert_profile")
        stable_sequence = bool(reference and len(candidate.workflow_moves) >= 4)
    failure_repair_rules = [
        f"{pattern} -> {candidate.repair_moves[index % len(candidate.repair_moves)] if candidate.repair_moves else 'repair explicitly'}"
        for index, pattern in enumerate(candidate.failure_patterns)
    ]
    return CandidateExpertSkillDNA(
        skill_name=skill_name,
        task_brief=task_brief,
        candidate_dna=candidate,
        extracted_workflow_moves=[move.name for move in candidate.workflow_moves],
        output_field_map={field: f"{field}: decision, evidence, and action" for field in candidate.output_fields},
        decision_rules=list(candidate.decision_rules),
        cut_rules=list(candidate.cut_rules),
        failure_repair_rules=failure_repair_rules,
        evidence_sources=evidence_sources,
        missing_expert_evidence=missing_evidence,
        stable_move_sequence=stable_sequence,
        needs_human_golden=("expert_golden" in missing_evidence),
        confidence=confidence,
        checked_in_move_recall=_checked_in_move_recall(candidate, checked_in),
        summary=[
            f"confidence={confidence}",
            f"workflow_moves={len(candidate.workflow_moves)}",
            f"missing_expert_evidence={','.join(missing_evidence) or 'none'}",
        ],
    )


def render_expert_dna_authoring_pack_markdown(pack: ExpertDNAAuthoringPack) -> str:
    lines = [
        "# Expert DNA Authoring Pack",
        "",
        f"- candidate_dna_count={pack.candidate_dna_count}",
        f"- ready_for_review={len(pack.ready_for_review)}",
        f"- needs_human_authoring={len(pack.needs_human_authoring)}",
        f"- rejected={len(pack.rejected)}",
        f"- Summary: {pack.summary}",
    ]
    for candidate in pack.candidates:
        lines.extend([
            "",
            f"## {candidate.skill_name}",
            f"- confidence={candidate.confidence}",
            f"- stable_move_sequence={candidate.stable_move_sequence}",
            f"- checked_in_move_recall={candidate.checked_in_move_recall:.2f}",
            f"- evidence_sources={', '.join(candidate.evidence_sources) or 'none'}",
            f"- missing_expert_evidence={', '.join(candidate.missing_expert_evidence) or 'none'}",
            f"- moves={', '.join(candidate.extracted_workflow_moves[:8]) or 'none'}",
        ])
    return "\n".join(lines) + "\n"


def build_expert_dna_authoring_pack(
    *,
    cases: list[dict[str, str]] | None = None,
    golden_root: Path = DEFAULT_EXPERT_DNA_GOLDEN_ROOT,
) -> ExpertDNAAuthoringPack:
    candidates = [
        build_expert_dna_authoring_candidate(
            skill_name=str(case.get("skill_name") or ""),
            task_brief=str(case.get("task") or ""),
            generated_skill_md=str(case.get("generated_skill_md") or ""),
            expert_reference_md=str(case.get("expert_reference_md") or ""),
            design_notes=str(case.get("design_notes") or ""),
            golden_root=golden_root,
        )
        for case in list(cases or DEFAULT_AUTHORING_CASES)
    ]
    ready = [candidate.skill_name for candidate in candidates if candidate.confidence == "ready_for_review"]
    needs_human = [candidate.skill_name for candidate in candidates if candidate.confidence == "needs_human_authoring"]
    rejected = [candidate.skill_name for candidate in candidates if candidate.confidence == "reject"]
    pack = ExpertDNAAuthoringPack(
        candidates=candidates,
        ready_for_review=ready,
        needs_human_authoring=needs_human,
        rejected=rejected,
        candidate_dna_count=len(candidates),
        summary=(
            f"Expert DNA authoring complete: candidates={len(candidates)} "
            f"ready_for_review={len(ready)} needs_human_authoring={len(needs_human)} rejected={len(rejected)}"
        ),
    )
    pack.markdown_summary = render_expert_dna_authoring_pack_markdown(pack)
    return pack


def build_expert_dna_review_report(candidate: CandidateExpertSkillDNA) -> ExpertDNAReviewReport:
    dna = candidate.candidate_dna
    failure_repair_count = len(candidate.failure_repair_rules)
    checklist = {
        "has_workflow_moves": len(dna.workflow_moves) >= 4,
        "has_output_fields": len(dna.output_fields) >= 3,
        "has_decision_rules": len(dna.decision_rules) >= 3,
        "has_failure_repairs": failure_repair_count >= 2,
        "has_expert_evidence": not candidate.missing_expert_evidence,
        "stable_move_sequence": candidate.stable_move_sequence,
        "ready_for_review": candidate.confidence == "ready_for_review",
    }
    blocking = [name for name, passed in checklist.items() if not passed]
    status = "pass" if not blocking else "fail"
    report = ExpertDNAReviewReport(
        skill_name=candidate.skill_name,
        review_status=status,
        candidate_confidence=candidate.confidence,
        workflow_move_count=len(dna.workflow_moves),
        output_field_count=len(dna.output_fields),
        decision_rule_count=len(dna.decision_rules),
        failure_repair_count=failure_repair_count,
        checklist=checklist,
        blocking_issues=blocking,
        approved_for_release_gate=False,
        summary=[
            f"review_status={status}",
            "approved_for_release_gate=false",
            "candidate DNA must be checked in explicitly before it can affect fully_correct",
        ],
    )
    report.markdown_summary = render_expert_dna_review_markdown(report)
    return report


def build_expert_dna_review_batch_report(pack: ExpertDNAAuthoringPack) -> ExpertDNAReviewBatchReport:
    reports = [build_expert_dna_review_report(candidate) for candidate in pack.candidates]
    pass_count = sum(1 for report in reports if report.review_status == "pass")
    fail_count = len(reports) - pass_count
    batch = ExpertDNAReviewBatchReport(
        reports=reports,
        pass_count=pass_count,
        fail_count=fail_count,
        approved_for_release_gate_count=sum(1 for report in reports if report.approved_for_release_gate),
        summary=f"Expert DNA review complete: reports={len(reports)} pass={pass_count} fail={fail_count} auto_enabled=0",
    )
    batch.markdown_summary = render_expert_dna_review_batch_markdown(batch)
    return batch


def render_expert_dna_review_markdown(report: ExpertDNAReviewReport) -> str:
    lines = [
        "# Expert DNA Review",
        "",
        f"- skill_name={report.skill_name}",
        f"- review_status={report.review_status}",
        f"- candidate_confidence={report.candidate_confidence}",
        f"- approved_for_release_gate={report.approved_for_release_gate}",
        f"- blocking_issues={', '.join(report.blocking_issues) or 'none'}",
    ]
    return "\n".join(lines) + "\n"


def render_expert_dna_review_batch_markdown(batch: ExpertDNAReviewBatchReport) -> str:
    lines = [
        "# Expert DNA Review Batch",
        "",
        f"- pass_count={batch.pass_count}",
        f"- fail_count={batch.fail_count}",
        f"- approved_for_release_gate_count={batch.approved_for_release_gate_count}",
        f"- Summary: {batch.summary}",
    ]
    for report in batch.reports:
        lines.extend([
            "",
            f"## {report.skill_name}",
            f"- review_status={report.review_status}",
            f"- candidate_confidence={report.candidate_confidence}",
            f"- blocking_issues={', '.join(report.blocking_issues) or 'none'}",
        ])
    return "\n".join(lines) + "\n"
