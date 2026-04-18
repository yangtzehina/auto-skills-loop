from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from ..models.expert_dna import ExpertSkillDNA
from ..models.expert_studio import (
    AnalysisBlock,
    ExecutionMove,
    ExpertEvidenceGapReport,
    ExpertFailureCase,
    ExpertRewritePair,
    ExpertSectionCorpusEntry,
    ExpertSkillCorpusEntry,
    ExpertTaskProbe,
    MonotonicImprovementReport,
    OutcomeOnlyProbeScore,
    OutcomeOnlyRerankerReport,
    PairwiseEditorialReport,
    ProfileBaselineBundle,
    ProfileBaselineSnapshot,
    ProfileResidualTargets,
    ProgramCandidateReviewBatchReport,
    ProgramCandidateReviewReport,
    ResidualGapReport,
    SectionCompressionPlan,
    SectionCompressionResult,
    SectionRealizationSpec,
    SkillEditorialForceReport,
    SkillProgramAuthoringCandidate,
    SkillProgramAuthoringPack,
    SkillProgramIR,
    SkillPromotionDecision,
    SkillRealizationCandidate,
    SkillRealizationSpec,
)
from .expert_dna import OUTPUT_FIELD_GUIDANCE, build_domain_move_plan, expert_skill_dna_for_skill
from .expert_dna_authoring import DEFAULT_AUTHORING_CASES, _looks_like_generic_shell, build_expert_dna_authoring_candidate
from .style_diversity import expert_style_profile_for_skill
from .body_quality import split_frontmatter
from .domain_specificity import _extract_section
from .editorial_quality import build_skill_editorial_quality_report
from .editorial_force import build_skill_editorial_force_report
from .move_quality import build_skill_move_quality_report
from .style_diversity import build_skill_style_diversity_report
from .expert_structure import build_skill_expert_structure_report
from ..models.artifacts import ArtifactFile, Artifacts
from ..models.plan import SkillPlan
from ..models.request import SkillCreateRequestV6
from .body_quality import build_skill_body_quality_report
from .domain_specificity import build_skill_domain_specificity_report
from .domain_expertise import build_skill_domain_expertise_report
from .depth_quality import build_skill_depth_quality_report


ROOT = Path(__file__).resolve().parents[3]
EXPERT_DEPTH_GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "expert_depth_golden"
CURRENT_BEST_GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "golden"
DUAL_BASELINE_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "dual_baselines"
FRONTIER_BANK_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "frontier_bank" / "known_profiles"

PROFILE_FRONTMATTER_DESCRIPTIONS: dict[str, str] = {
    "concept-to-mvp-pack": "Proof-driven brief for deciding the first playable, the hard cuts, and the first build target.",
    "decision-loop-stress-test": "Phase-by-phase audit for finding collapse points, dominant routes, and reward-training mistakes.",
    "simulation-resource-loop-design": "Systems brief for visible tradeoffs, counterpressure, costly recovery, and fantasy fit.",
}

PROFILE_QUALITY_GATE_LINES: dict[str, str] = {
    "concept-to-mvp-pack": "Approve the first playable only if the proof, cut, and scope lines are explicit enough to kill or greenlight the build.",
    "decision-loop-stress-test": "Keep the audit on collapse witness, structural repair, dominant strategy, and reinforcement before anyone reaches for extra content.",
    "simulation-resource-loop-design": "Keep the loop readable through visible pressure, costly recovery, and fantasy fit before smoothing the numbers.",
}

PROFILE_QUALITY_CHECK_LINES: dict[str, list[str]] = {
    "concept-to-mvp-pack": [
        "Check whether the validation question can fail in a short playtest.",
        "Check whether the smallest honest loop is playable without future systems or spectacle.",
        "Check whether the feature cut removes attractive work instead of protecting comfort.",
        "Check whether the content scope is just enough to prove the loop.",
        "Check whether the out-of-scope list blocks creep instead of sounding polite.",
        "Check whether the pack keeps a kill list so this does not turn into a dream-expanding skill.",
        "Check whether the MVP pack names the next build and the next playtest signal.",
        "Check whether the build recommendation and success criteria are explicit enough to approve the first playable.",
        "Check whether the pack stays prototype first instead of drifting into a mini vertical slice.",
        "Check whether pass and fail evidence would actually force a redesign instead of just sounding organized.",
        "Check whether a greybox build with stubbed content and placeholder art still answers the validation question.",
    ],
    "decision-loop-stress-test": [
        "Check whether first-hour novelty is masking a weak decision before the loop gets greenlit.",
        "Check whether the decision loop is readable in the first hour before novelty wears off.",
        "Check whether first hour midgame and lategame differ for the right reason instead of throughput-only inflation.",
        "Check whether midgame autopilot is appearing because the loop lost counterpressure and adaptation.",
        "Check whether lategame pressure creates a new decision problem instead of throughput-only mastery.",
        "Check whether solved state is concrete enough to name, trigger, and attack.",
        "Check whether fake variation, shallow reward inflation, or content padding are being mistaken for repair.",
        "Check whether the repair changes pressure inside the decision loop instead of adding softer content or softer compensation.",
        "Check whether the repair recommendation is not just numeric tuning, not just more content, not just phase explanation, and not just pacing cover.",
        "Check whether solved-state repair changes the decision landscape instead of leaving the same read, tradeoff, or consequence alive.",
        "Check whether the variation audit changes read, tradeoff, consequence, or dominant line instead of renaming the same answer.",
        "Check whether reinforcement teaches intended behavior instead of rewarding autopilot, safe throughput, or the wrong habit.",
        "Check whether reinforcement maps wrong habit to right habit, names the intended behavior shift, and rejects throughput-only mastery.",
        "Check whether the stop condition, collapse witness, and break point appear together as the structural witness for repair.",
    ],
    "simulation-resource-loop-design": [
        "Check whether variables have player-facing roles before any balancing work starts.",
        "Check whether pressure relationships create a readable tradeoff instead of hidden bookkeeping.",
        "Check whether positive and negative loops both exist and counterweight each other on purpose.",
        "Check whether failure recovery keeps consequences instead of flattening the system.",
        "Check whether emotional fantasy matches resource math instead of drifting away from the loop.",
        "Check whether one dominant currency can still bypass the intended tension web.",
        "Check whether the feedback loops create rhythm instead of runaway snowball or pure punishment.",
        "Check whether you can reduce currencies until only a few strong tensions remain and every variable changes player behavior.",
        "Check whether the loop is not just one simple currency, not isolated meters, and not mostly content writing.",
        "Check whether recovery avoids a consequence-free reset, makes pressure visible early, and keeps tradeoffs costly.",
        "Check whether you only include a variable if it changes player behavior inside the pressure web.",
    ],
}

PROFILE_FAILURE_ENTRIES: dict[str, list[tuple[str, str, str, str]]] = {
    "concept-to-mvp-pack": [
        (
            "Fake MVP",
            "The core question reads like a slogan and no short session could disprove it.",
            "The pack protected confidence instead of proof.",
            "Rewrite the validation question so one failed playtest would force a redesign.",
        ),
        (
            "Scope Creep",
            "Support systems keep sliding back into the first build as if they were core.",
            "The feature cut was polite instead of explicit.",
            "Cut aggressively, then move the supportive work into out of scope with a clear re-entry condition.",
        ),
        (
            "Content Hiding Uncertainty",
            "The MVP only works if future meta systems, content volume, or presentation arrive first.",
            "The smallest honest loop was never isolated, so content is hiding uncertainty instead of proving the idea.",
            "Do not fake the entire game; reduce the build to the repeatable loop that already produces the intended feeling.",
        ),
        (
            "Mood Instead of Loop",
            "The package sells fantasy, tone, or mood, but it still does not say which repeatable loop proves the concept.",
            "The handoff is carrying aspiration instead of a smallest honest loop.",
            "Rewrite the pack around the repeatable loop, then cut any line that is only mood instead of loop.",
        ),
        (
            "Vertical Slice Drift",
            "The first build quietly grows into a mini vertical slice with polish, onboarding, and support systems doing proof work.",
            "The feature cut stopped protecting the prototype-first boundary and the pack drifted toward a vertical slice.",
            "Return to the proof target, restore the kill list, and keep only the work required to validate the loop.",
        ),
    ],
    "decision-loop-stress-test": [
        (
            "Novelty-Only Start",
            "Early play only works because the premise is fresh, not because the decision is clear.",
            "The first-hour hook never established readable pressure.",
            "Raise the stakes and feedback around the core choice, call the weak decision directly, and do not greenlight a repair that only adds more content.",
        ),
        (
            "Midgame Autopilot",
            "The player keeps repeating the same answer while the game only changes labels or numbers.",
            "Midgame added volume without adding new constraints.",
            "Introduce structural counterpressure that forces adaptation, changes the read, tradeoff, or consequence, makes the old answer stop working, makes a new answer become correct, and maps the wrong habit to the right habit instead of rewarding simple efficiency scaling.",
        ),
        (
            "Progression Without New Problems",
            "Progression adds throughput or spectacle while the underlying choice stays solved.",
            "Expansion arrived without a new pressure problem.",
            "Add a new constraint or pressure relationship before adding more content or reward layers, reject content-only or numeric-only repair, and change the decision landscape instead of polishing the same answer so the old answer stops working and a new answer becomes correct.",
        ),
        (
            "Variety Without Strategic Consequence",
            "The game offers more variants, but they do not change read, tradeoff, or consequence.",
            "Variation was used as surface freshness instead of decision mutation.",
            "Cut cosmetic variation, call fake variation by name, reject any variation that does not change decisions or keeps the same read, same consequence, or dominant line, say what old answer stops working, what new answer becomes required, what reward, information, or cost changed to cause that shift, and what reward, information, or cost shift kills the old answer, and keep only the variants that force a new read, tradeoff, or consequence.",
        ),
        (
            "Mastery Removes the Game",
            "Late play collapses into rote execution or a dominant route.",
            "Mastery widened throughput without creating a new decision problem.",
            "Change the pressure landscape so mastery unlocks new tradeoffs instead of solving the loop forever.",
        ),
        (
            "Wrong Behavior Training",
            "The reward structure favors autopilot even though the design claims expression or adaptation.",
            "Reinforcement was tuned for throughput rather than the intended behavior.",
            "Map the wrong habit to the right habit, name the intended behavior shift, state which reward loop currently trains the wrong behavior, say what player behavior must disappear, say what replacement behavior must become optimal, say what reward, information, or cost shift causes that behavior shift, rewrite the replacement reward logic so the wrong habit stops paying and the right habit becomes the profitable answer, move rewards onto that right habit, and strip reward from throughput-only or safe dominant routines.",
        ),
        (
            "Numeric-Only Repair",
            "The loop identifies a solved state, then proposes softer numbers or reward tuning while the same decision still wins.",
            "The repair changed intensity instead of changing the pressure relationship.",
            "Reject numeric-only or content-only fixes, write a structural repair recommendation, call out when numeric-only tuning keeps the same dominant line still winning, the same read still solving, and the same consequence structure still paying out, and rewrite the fix so the decision landscape changes before balance values are tuned and the old answer stops working before balance values are tuned.",
        ),
        (
            "Stop Condition Without Witness",
            "The audit names a stop condition, but never says what the collapse witness would look like in play.",
            "The review described the phase boundary without naming the observable failure evidence.",
            "Pair the stop condition with the specific collapse witness, break point, and structural witness that should trigger the repair recommendation instead of only naming the phase boundary.",
        ),
    ],
    "simulation-resource-loop-design": [
        (
            "Decorative Resources",
            "The loop lists resources, but they do not create a player-facing tradeoff.",
            "Variables were added for flavor or spreadsheet depth rather than decision pressure.",
            "Reduce currencies and cut decorative resources until each remaining variable changes player behavior.",
        ),
        (
            "No Real Tradeoff",
            "Pressure exists on paper, but the player still has one obviously correct answer.",
            "The pressure relationship never creates a real sacrifice.",
            "Make pressure visible and tighten tradeoffs so the player must give something up.",
        ),
        (
            "One Dominant Currency",
            "A single resource or loop answers every problem.",
            "Counterpressure exists on paper but never bites in play.",
            "Add a brake, opportunity cost, or dependency that the dominant currency cannot bypass.",
        ),
        (
            "Positive-Loop Runaway",
            "Success compounds into snowballing without a meaningful brake.",
            "Positive loops were tuned without a matching negative loop or cap.",
            "Pair the runaway loop with a counterpressure that stays visible during success.",
        ),
        (
            "Punishment Without Agency",
            "Pressure punishes the player, but the recovery path offers no meaningful response or tradeoff.",
            "The loop preserved pain without preserving agency.",
            "Add readable warning, viable responses, and recovery with cost instead of a consequence-free reset or pure punishment.",
        ),
        (
            "Fantasy-System Mismatch",
            "The spreadsheet balances, but the player-facing pressure produces the wrong feeling.",
            "Variables were optimized independently from the intended emotional rhythm.",
            "Rewrite the loop so the visible pressures reinforce the fantasy instead of flattening it.",
        ),
        (
            "Hidden Pressure Relationships",
            "Resources move in the background, but the player cannot read the pressure soon enough to plan around it.",
            "Signals were treated as bookkeeping instead of decision surfaces.",
            "Make pressure visible before the player commits so the cost, risk, or bottleneck can actually shape the next move.",
        ),
        (
            "Cheap Recovery",
            "Recovery resets pressure so cleanly that failure loses most of its cost, memory, or structural consequence.",
            "The loop is protecting comfort instead of preserving the meaning of failure and recovery.",
            "Keep recovery playable, but attach a visible cost, lost position, or delayed opportunity before tuning anything else.",
        ),
    ],
}


def _golden_markdown(skill_name: str) -> str:
    path = EXPERT_DEPTH_GOLDEN_ROOT / f"{skill_name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _current_best_markdown(skill_name: str) -> str:
    path = CURRENT_BEST_GOLDEN_ROOT / f"{skill_name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _dual_baseline_bundle(skill_name: str) -> ProfileBaselineBundle | None:
    path = DUAL_BASELINE_ROOT / f"{skill_name}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return ProfileBaselineBundle.model_validate(payload)


def _active_frontier_version(skill_name: str) -> str:
    bundle = _dual_baseline_bundle(skill_name)
    return str(getattr(bundle, "active_frontier_version", "") or "")


def build_active_frontier_version(skill_name: str | None = None) -> str:
    if skill_name:
        return _active_frontier_version(skill_name) or "frontier_v3"
    versions = [
        _active_frontier_version(name)
        for name in (
            "concept-to-mvp-pack",
            "decision-loop-stress-test",
            "simulation-resource-loop-design",
        )
        if _active_frontier_version(name)
    ]
    if not versions:
        return "frontier_v3"
    return str(Counter(versions).most_common(1)[0][0] or "frontier_v3")


def _frontier_bank_entry(skill_name: str) -> dict[str, Any]:
    path = FRONTIER_BANK_ROOT / f"{skill_name}.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _profile_residual_targets(skill_name: str) -> ProfileResidualTargets:
    targets: dict[str, ProfileResidualTargets] = {
        "concept-to-mvp-pack": ProfileResidualTargets(
            skill_name=skill_name,
            target_metrics={
                "expert_pitfall_cluster_recall": 0.90,
                "output_field_guidance_coverage": 0.85,
            },
            allowed_sections=[
                "Quality Checks",
                "Failure Patterns and Fixes",
                "Output Format",
            ],
            protected_metrics={
                "domain_move_coverage": 1.0,
                "section_depth_score": 0.97,
                "task_outcome_with_skill_average": 0.9398,
                "decision_pressure_score": 0.9467,
                "cut_sharpness_score": 1.0,
                "boundary_rule_coverage": 0.8,
                "generic_surface_leakage": 0.05,
            },
            summary=[
                "target expert_pitfall_cluster_recall >= 0.90",
                "target output_field_guidance_coverage >= 0.85",
            ],
        ),
        "decision-loop-stress-test": ProfileResidualTargets(
            skill_name=skill_name,
            target_metrics={
                "decision_pressure_score": 0.98,
                "compression_without_loss": 0.80,
                "task_outcome_with_skill_average": 0.92,
                "outcome_only_probe_pass_count": 8.0,
                "repair_specificity_score": 0.90,
                "probe_evidence_density": 0.85,
                "collapse_witness_coverage": 0.90,
            },
            allowed_sections=[
                "Overview",
                "Default Workflow",
                "Quality Checks",
                "Failure Patterns and Fixes",
            ],
            protected_metrics={
                "domain_move_coverage": 0.9285,
                "section_depth_score": 0.9008,
                "task_outcome_with_skill_average": 0.90,
                "failure_repair_force": 1.0,
                "stop_condition_coverage": 1.0,
                "section_force_distinctness": 0.84,
            },
            summary=[
                "target decision_pressure_score >= 0.98",
                "target compression_without_loss >= 0.80",
                "target task_outcome_with_skill_average >= 0.92",
                "target outcome_only_probe_pass_count = 8",
                "target repair_specificity_score >= 0.90",
                "target probe_evidence_density >= 0.85",
                "target collapse_witness_coverage >= 0.90",
                "target false_fix_rejection_status = pass",
            ],
        ),
        "simulation-resource-loop-design": ProfileResidualTargets(
            skill_name=skill_name,
            target_metrics={
                "generic_surface_leakage": 0.05,
                "redundancy_ratio": 0.04,
                "generic_skeleton_ratio": 0.20,
            },
            allowed_sections=[
                "Analysis Blocks",
                "Output Format",
                "Failure Patterns and Fixes",
            ],
            protected_metrics={
                "domain_move_coverage": 1.0,
                "section_depth_score": 1.0,
                "task_outcome_with_skill_average": 0.96,
                "failure_repair_force": 1.0,
                "section_force_distinctness": 1.0,
                "boundary_rule_coverage": 0.2,
            },
            summary=[
                "target generic_surface_leakage <= 0.05",
                "target redundancy_ratio <= 0.04",
                "target generic_skeleton_ratio <= 0.20",
            ],
        ),
    }
    return targets.get(skill_name, ProfileResidualTargets(skill_name=skill_name))


def build_profile_residual_targets(skill_name: str) -> ProfileResidualTargets:
    return _profile_residual_targets(skill_name)


def _active_frontier_snapshot(skill_name: str) -> ProfileBaselineSnapshot | None:
    bundle = _dual_baseline_bundle(skill_name)
    if bundle is None:
        return None
    return bundle.best_balance_snapshot


def _raw_metric(metrics: dict[str, Any], name: str) -> float:
    editorial_force = metrics.get("editorial_force")
    editorial = metrics.get("editorial")
    domain_expertise = metrics.get("domain_expertise")
    depth = metrics.get("depth")
    expert_structure = metrics.get("expert_structure")
    task_outcome = metrics.get("task_outcome")
    profile_result = next(iter(list(getattr(task_outcome, "profile_results", []) or [])), None) if task_outcome is not None else None
    mapping = {
        "expert_quality_check_recall": lambda: float(getattr(metrics.get("expert_structure"), "expert_quality_check_recall", 0.0) or 0.0),
        "expert_pitfall_cluster_recall": lambda: float(getattr(expert_structure, "expert_pitfall_cluster_recall", 0.0) or 0.0),
        "generic_surface_leakage": lambda: float(getattr(editorial_force, "generic_surface_leakage", 0.0) or 0.0),
        "decision_pressure_score": lambda: float(getattr(editorial_force, "decision_pressure_score", 0.0) or 0.0),
        "cut_sharpness_score": lambda: float(getattr(editorial_force, "cut_sharpness_score", 0.0) or 0.0),
        "boundary_rule_coverage": lambda: float(getattr(editorial_force, "boundary_rule_coverage", 0.0) or 0.0),
        "section_force_distinctness": lambda: float(getattr(editorial_force, "section_force_distinctness", 0.0) or 0.0),
        "compression_without_loss": lambda: float(getattr(editorial_force, "compression_without_loss", 0.0) or 0.0),
        "redundancy_ratio": lambda: float(getattr(editorial, "redundancy_ratio", 0.0) or 0.0),
        "generic_skeleton_ratio": lambda: float(getattr(expert_structure, "generic_skeleton_ratio", 0.0) or 0.0),
        "failure_repair_force": lambda: float(getattr(editorial_force, "failure_repair_force", 0.0) or 0.0),
        "stop_condition_coverage": lambda: float(getattr(editorial_force, "stop_condition_coverage", 0.0) or 0.0),
        "domain_move_coverage": lambda: float(getattr(domain_expertise, "domain_move_coverage", 0.0) or 0.0),
        "section_depth_score": lambda: float(getattr(depth, "section_depth_score", 0.0) or 0.0),
        "output_field_guidance_coverage": lambda: float(getattr(depth, "output_field_guidance_coverage", 0.0) or 0.0),
        "task_outcome_with_skill_average": lambda: float(getattr(profile_result, "with_skill_average", 0.0) or 0.0),
    }
    if name in metrics:
        return float(metrics.get(name, 0.0) or 0.0)
    getter = mapping.get(name)
    return round(float(getter() if getter is not None else 0.0), 4)


def _residual_gap_report(skill_name: str, metrics: dict[str, Any]) -> ResidualGapReport:
    targets = _profile_residual_targets(skill_name)
    values = {metric: _raw_metric(metrics, metric) for metric in set(targets.target_metrics) | set(targets.protected_metrics)}
    quality_status = "pass"
    pressure_status = "pass"
    leakage_status = "pass"
    false_fix_status = "pass"
    if skill_name == "concept-to-mvp-pack":
        quality_status = (
            "pass"
            if (
                values.get("expert_pitfall_cluster_recall", 0.0) >= targets.target_metrics.get("expert_pitfall_cluster_recall", 0.0)
                and values.get("output_field_guidance_coverage", 0.0) >= targets.target_metrics.get("output_field_guidance_coverage", 0.0)
            )
            else "fail"
        )
        leakage_status = "pass" if values.get("generic_surface_leakage", 1.0) <= targets.protected_metrics.get("generic_surface_leakage", 1.0) else "fail"
        pressure_status = "pass" if values.get("decision_pressure_score", 0.0) >= targets.protected_metrics.get("decision_pressure_score", 0.0) else "fail"
        false_fix_status = (
            "pass"
            if (
                values.get("cut_sharpness_score", _raw_metric(metrics, "cut_sharpness_score")) >= targets.protected_metrics.get("cut_sharpness_score", 0.0)
                and values.get("boundary_rule_coverage", _raw_metric(metrics, "boundary_rule_coverage")) >= targets.protected_metrics.get("boundary_rule_coverage", 0.0)
            )
            else "fail"
        )
    elif skill_name == "decision-loop-stress-test":
        quality_status = "pass"
        pressure_status = (
            "pass"
            if (
                values.get("decision_pressure_score", 0.0) >= targets.target_metrics.get("decision_pressure_score", 0.0)
                and values.get("compression_without_loss", 0.0) >= targets.target_metrics.get("compression_without_loss", 0.0)
                and values.get("task_outcome_with_skill_average", 0.0) >= targets.target_metrics.get("task_outcome_with_skill_average", 0.0)
                and values.get("repair_specificity_score", 0.0) >= targets.target_metrics.get("repair_specificity_score", 0.0)
                and values.get("probe_evidence_density", 0.0) >= targets.target_metrics.get("probe_evidence_density", 0.0)
                and values.get("collapse_witness_coverage", 0.0) >= targets.target_metrics.get("collapse_witness_coverage", 0.0)
            )
            else "fail"
        )
        leakage_status = "pass"
        false_fix_status = (
            "pass"
            if (
                values.get("failure_repair_force", 0.0) >= targets.protected_metrics.get("failure_repair_force", 0.0)
                and values.get("stop_condition_coverage", 0.0) >= targets.protected_metrics.get("stop_condition_coverage", 0.0)
                and values.get("section_force_distinctness", 0.0) >= targets.protected_metrics.get("section_force_distinctness", 0.0)
                and values.get("outcome_only_probe_pass_count", 0.0) >= targets.target_metrics.get("outcome_only_probe_pass_count", 0.0)
            )
            else "fail"
        )
    elif skill_name == "simulation-resource-loop-design":
        quality_status = "pass"
        pressure_status = "pass" if values.get("failure_repair_force", 0.0) >= targets.protected_metrics.get("failure_repair_force", 0.0) else "fail"
        leakage_status = (
            "pass"
            if (
                values.get("generic_surface_leakage", 1.0) <= targets.target_metrics.get("generic_surface_leakage", 1.0)
                and values.get("redundancy_ratio", 1.0) <= targets.target_metrics.get("redundancy_ratio", 1.0)
                and values.get("generic_skeleton_ratio", 1.0) <= targets.target_metrics.get("generic_skeleton_ratio", 1.0)
            )
            else "fail"
        )
        false_fix_status = (
            "pass"
            if (
                values.get("section_force_distinctness", 0.0) >= targets.protected_metrics.get("section_force_distinctness", 0.0)
                and values.get("boundary_rule_coverage", 0.0) >= targets.protected_metrics.get("boundary_rule_coverage", 0.0)
            )
            else "fail"
        )
    gaps = []
    deficits: list[tuple[str, float]] = []
    for metric, threshold in targets.target_metrics.items():
        value = values.get(metric, 0.0)
        if metric in {"generic_surface_leakage", "redundancy_ratio"}:
            gap = max(0.0, value - threshold)
        else:
            gap = max(0.0, threshold - value)
        deficits.append((metric, round(gap, 4)))
    target_focus = ""
    if deficits:
        metric_name, gap_value = max(deficits, key=lambda item: item[1])
        if gap_value > 0:
            target_focus = {
                "expert_quality_check_recall": "quality_checks",
                "expert_pitfall_cluster_recall": "failure_repairs",
                "output_field_guidance_coverage": "output_format",
                "decision_pressure_score": "pressure",
                "section_force_distinctness": "pressure",
                "compression_without_loss": "pressure",
                "task_outcome_with_skill_average": "pressure",
                "outcome_only_probe_pass_count": "pressure",
                "repair_specificity_score": "pressure",
                "probe_evidence_density": "pressure",
                "collapse_witness_coverage": "pressure",
                "generic_surface_leakage": "leakage",
                "redundancy_ratio": "compactness",
                "generic_skeleton_ratio": "compactness",
            }.get(metric_name, metric_name)
    for label, status in (
        ("quality_checks", quality_status),
        ("pressure", pressure_status),
        ("leakage", leakage_status),
        ("false_fix_rejection", false_fix_status),
    ):
        if status != "pass":
            gaps.append(label)
    status = "pass" if not gaps else "fail"
    return ResidualGapReport(
        skill_name=skill_name,
        target_focus=target_focus,
        quality_check_target_status=quality_status,
        pressure_target_status=pressure_status,
        leakage_target_status=leakage_status,
        false_fix_rejection_status=false_fix_status,
        residual_gap_count=len(gaps),
        status=status,
        summary=[
            f"target_focus={target_focus or 'none'}",
            f"quality_check_target_status={quality_status}",
            f"pressure_target_status={pressure_status}",
            f"leakage_target_status={leakage_status}",
            f"false_fix_rejection_status={false_fix_status}",
            f"residual_gap_count={len(gaps)}",
        ],
    )


def build_residual_gap_report(*, skill_name: str, metrics: dict[str, Any]) -> ResidualGapReport:
    return _residual_gap_report(skill_name, metrics)


def _target_focus_for_skill(skill_name: str) -> str:
    snapshot = _active_frontier_snapshot(skill_name)
    if snapshot is None:
        return ""
    metrics: dict[str, Any] = {}
    metrics.update(dict(snapshot.primary_force_metrics or {}))
    metrics.update(dict(snapshot.coverage_metrics or {}))
    metrics.update(dict(snapshot.compactness_metrics or {}))
    metrics.update(dict(snapshot.target_metrics or {}))
    report = _residual_gap_report(skill_name, metrics)
    if report.target_focus:
        return str(report.target_focus)
    return {
        "decision-loop-stress-test": "pressure",
        "concept-to-mvp-pack": "quality_checks",
        "simulation-resource-loop-design": "compactness",
    }.get(skill_name, "")


def _frontier_section_lines(
    *,
    skill_name: str,
    target_focus: str,
    section_name: str,
) -> list[str]:
    bank = _frontier_bank_entry(skill_name)
    if not bank:
        return []
    focus_to_bucket = {
        "pressure": "pressure_best_sections",
        "quality_checks": "quality_checks_best_sections",
        "leakage": "compactness_best_sections",
        "compactness": "compactness_best_sections",
        "false_fix_rejection": "failure_repairs_best_sections",
        "output_format": "output_format_best_sections",
    }
    bucket_names: list[str] = []
    if target_focus:
        bucket = focus_to_bucket.get(target_focus, "")
        if bucket:
            bucket_names.append(bucket)
    section_fallback_buckets = {
        "Quality Checks": "quality_checks_best_sections",
        "Failure Patterns and Fixes": "failure_repairs_best_sections",
        "Output Format": "output_format_best_sections",
    }
    fallback_bucket = section_fallback_buckets.get(section_name, "")
    if fallback_bucket and fallback_bucket not in bucket_names:
        bucket_names.append(fallback_bucket)
    lines: list[str] = []
    for bucket_name in bucket_names:
        section_map = bank.get(bucket_name)
        if not isinstance(section_map, dict):
            continue
        for item in list(section_map.get(section_name) or []):
            text = str(item).strip()
            if text and text not in lines:
                lines.append(text)
    return lines


def _section_corpus(
    skill_name: str,
    expert_markdown: str,
    expert_notes: list[str],
    failure_cases: list[ExpertFailureCase],
) -> list[ExpertSectionCorpusEntry]:
    if not expert_markdown.strip():
        return []
    _, body = split_frontmatter(expert_markdown)
    section_specs = [
        ("Overview", "Frame the skill as a sharp domain method, not a generic planning template."),
        ("Default Workflow", "Carry the primary execution spine and keep the domain moves in explicit order."),
        ("Output Format", "Make the deliverable directly fillable and execution-facing."),
        ("Quality Checks", "Force the hard judgment checks that prevent a soft generic answer."),
        ("Common Pitfalls", "Name failure patterns and corrections sharply enough to fix them."),
    ]
    results: list[ExpertSectionCorpusEntry] = []
    for name, purpose in section_specs:
        excerpt = _extract_section(body, (name.lower(),))
        if not excerpt:
            continue
        lowered = excerpt.lower()
        judgment_moves = [note for note in list(expert_notes or []) if any(token in lowered for token in note.lower().split()[:3])]
        cut_moves = [
            line.strip("- ").strip()
            for line in excerpt.splitlines()
            if "cut" in line.lower() or "out of scope" in line.lower() or "defer" in line.lower()
        ][:6]
        repair_moves = [
            item.repair_direction
            for item in list(failure_cases or [])
            if item.repair_direction and item.failure_type != "generic_shell"
        ][:6]
        results.append(
            ExpertSectionCorpusEntry(
                skill_name=skill_name,
                section_name=name,
                expert_excerpt=excerpt.strip(),
                section_purpose=purpose,
                judgment_moves=judgment_moves,
                cut_moves=cut_moves,
                repair_moves=repair_moves,
            )
        )
    return results


def _probe(
    probe_id: str,
    task: str,
    *,
    decision_terms: list[str],
    cut_terms: list[str],
    failure_terms: list[str],
    repair_terms: list[str],
    output_fields: list[str],
    anti_generic_terms: list[str],
) -> ExpertTaskProbe:
    return ExpertTaskProbe(
        probe_id=probe_id,
        task=task,
        decision_terms=decision_terms,
        cut_terms=cut_terms,
        failure_terms=failure_terms,
        repair_terms=repair_terms,
        output_fields=output_fields,
        anti_generic_terms=anti_generic_terms,
    )


def _rewrite_pair(skill_name: str, weak_shell: str, expert_revision: str, reason: str) -> ExpertRewritePair:
    return ExpertRewritePair(
        skill_name=skill_name,
        weak_shell=weak_shell,
        expert_revision=expert_revision,
        revision_reason=reason,
    )


def _failure_case(skill_name: str, failure_id: str, bad_output: str, failure_type: str, why: str, fix: str) -> ExpertFailureCase:
    return ExpertFailureCase(
        skill_name=skill_name,
        failure_id=failure_id,
        failure_type=failure_type,
        why_it_fails=why,
        repair_direction=fix,
        bad_output=bad_output,
    )


_KNOWN_CORPUS_DATA: dict[str, dict[str, Any]] = {
    "concept-to-mvp-pack": {
        "domain_family": "game-design",
        "task_brief": "Turn a game direction into a falsifiable first-playable MVP package.",
        "opening_strategy": "Lead with proof-first scope cutting, not broad concept expansion.",
        "expert_notes": [
            "Start from the validation question, not from feature enthusiasm.",
            "Use the smallest honest loop as the unit of truth, then cut anything that does not support it.",
            "The pack must end in an execution-facing MVP package, not a broad design overview.",
            "Always include an out-of-scope kill list and a final failure pass.",
        ],
        "anti_patterns": [
            "vertical slice inflation",
            "content hiding uncertainty",
            "scope creep by empathy",
            "mood instead of loop",
        ],
        "task_probes": [
            _probe(
                "mvp_scope_cut",
                "Scope a first playable for a cozy courier game without letting story and cosmetics hide validation.",
                decision_terms=["validation question", "smallest honest loop", "feature cut", "out of scope"],
                cut_terms=["cut", "defer", "out of scope", "kill list"],
                failure_terms=["scope creep", "vertical slice", "content hiding uncertainty"],
                repair_terms=["cut aggressively", "rewrite as playtest proof", "remove decorative scope"],
                output_fields=["Core Validation Question", "Smallest Honest Loop", "Feature Cut", "MVP Pack"],
                anti_generic_terms=["testability", "falsifiable", "playable proof"],
            ),
            _probe(
                "mvp_loop_proof",
                "Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.",
                decision_terms=["core validation question", "smallest honest loop", "minimum content package"],
                cut_terms=["later", "cut for now", "supportive", "out of scope"],
                failure_terms=["fake mvp", "mood instead of loop"],
                repair_terms=["state the repeatable loop", "use kill list"],
                output_fields=["Smallest Honest Loop", "Out of Scope", "Minimum Content Package"],
                anti_generic_terms=["repeat trigger", "system response", "visible feedback"],
            ),
            _probe(
                "mvp_failure_pass",
                "Package a tactics game concept into a first playable and explain what would make the MVP fail.",
                decision_terms=["failure pass", "build recommendation", "playtest signal"],
                cut_terms=["remove supportive systems", "do not overbuild"],
                failure_terms=["cannot fail clearly", "too many systems called core"],
                repair_terms=["rewrite as playtest observation", "shrink the pack"],
                output_fields=["MVP Pack", "Out of Scope", "Build recommendation"],
                anti_generic_terms=["could fail", "playtest signal", "redesign trigger"],
            ),
        ],
        "expected_outputs": [
            "Validation Goal with pass/fail evidence.",
            "Minimum Honest Loop with player input, system response, feedback, and repeat trigger.",
            "Feature Cut table with core/support/defer/cut buckets.",
            "Execution-facing MVP Pack and first playtest signal.",
        ],
        "rewrite_pairs": [
            _rewrite_pair(
                "concept-to-mvp-pack",
                "Use this skill to turn a game idea into a structured plan with goals and tradeoffs.",
                "Force the idea into a validation question, smallest honest loop, feature cut, and out-of-scope kill list.",
                "Replace generic concept planning with proof-first scope cutting.",
            ),
            _rewrite_pair(
                "concept-to-mvp-pack",
                "Describe the MVP and mention a few risks before moving into production planning.",
                "Name what the first playable must prove, what gets cut, what stays out of scope, and what would make the pack fail immediately.",
                "Convert a polite MVP summary into a pressure-tested package decision.",
            ),
        ],
        "failure_cases": [
            _failure_case(
                "concept-to-mvp-pack",
                "generic_shell",
                "# Concept to MVP Pack\n\n## Overview\nThink about what the game could be and list some features to include.\n",
                "generic_shell",
                "It describes planning instead of forcing a falsifiable MVP package.",
                "Rewrite around validation question, smallest honest loop, feature cut, and failure pass.",
            ),
            _failure_case(
                "concept-to-mvp-pack",
                "template_bloat",
                "# Concept to MVP Pack\n\n## Workflow\n1. Understand the context.\n2. Consider options.\n3. Write a summary.\n",
                "template_bloat",
                "It keeps a generic workflow skeleton and never names the actual MVP-cutting moves.",
                "Rebuild the workflow around the concrete MVP move sequence.",
            ),
        ],
    },
    "decision-loop-stress-test": {
        "domain_family": "game-design",
        "task_brief": "Stress test a game decision loop across first-hour, midgame, and mastery phases.",
        "opening_strategy": "Lead with phase stress and collapse-point hunting, not general loop commentary.",
        "expert_notes": [
            "The skill must read like a pressure test across time, not a static loop description.",
            "First hour, midgame, and late game are distinct stress lenses.",
            "Solved state and reinforcement quality are structural, not cosmetic, checks.",
            "Repairs should target decision pressure, not content volume.",
        ],
        "anti_patterns": [
            "loop analysis directory",
            "content instead of pressure repair",
            "variation as surface variety only",
        ],
        "task_probes": [
            _probe(
                "loop_phase_stress",
                "Stress a card-combat loop across first hour, midgame, and mastery pressure.",
                decision_terms=["first-hour hook", "midgame sustainability", "late-game expansion", "solved state"],
                cut_terms=["do not fix with more content", "structural fix", "counterpressure"],
                failure_terms=["repetition", "solved state", "autopilot"],
                repair_terms=["add counterpressure", "reward adaptation", "change decision landscape"],
                output_fields=["First-Hour Performance", "Midgame Performance", "Late-Game Performance", "Solved State Risk"],
                anti_generic_terms=["phase stress", "collapse point", "decision landscape"],
            ),
            _probe(
                "solved_state_repair",
                "Find the solved state in a farming automation loop and propose structural counterpressure.",
                decision_terms=["dominant strategy", "solved state risk", "variation quality"],
                cut_terms=["not more content", "not more cosmetic variation"],
                failure_terms=["dominant option", "flat feedback", "rote execution"],
                repair_terms=["punish repeated safe choices", "reward state-aware adaptation"],
                output_fields=["Solved State Risk", "Variation Quality", "Reinforcement Recommendations"],
                anti_generic_terms=["counterpressure", "state-aware", "autopilot risk"],
            ),
            _probe(
                "reinforcement_audit",
                "Audit whether a tactics loop teaches expressive adaptation or only efficient repetition.",
                decision_terms=["reinforcement check", "what behavior the rewards teach"],
                cut_terms=["avoid shallow reward inflation"],
                failure_terms=["wrong behavior training", "efficiency-only loop"],
                repair_terms=["reward adaptation", "change incentive structure"],
                output_fields=["Reinforcement Check", "Reinforcement Recommendations"],
                anti_generic_terms=["teaches", "reinforces", "behavior"],
            ),
        ],
        "expected_outputs": [
            "Phase-by-phase stress readout from first hour to mastery.",
            "Solved state diagnosis and structural repair direction.",
            "Reinforcement analysis showing what behavior the system trains.",
        ],
        "rewrite_pairs": [
            _rewrite_pair(
                "decision-loop-stress-test",
                "Describe the loop and suggest ways to make it more engaging over time.",
                "Pressure-test the loop across first hour, midgame, late game, solved state, and reinforcement quality.",
                "Turn generic engagement advice into a phase-based stress program.",
            ),
            _rewrite_pair(
                "decision-loop-stress-test",
                "List each phase of the loop and offer a few content ideas where it feels weak.",
                "Find the collapse point in each phase, state the wrong behavior being reinforced, and prescribe a structural repair before adding content.",
                "Turn a tidy loop review into a pressure-and-repair audit.",
            ),
        ],
        "failure_cases": [
            _failure_case(
                "decision-loop-stress-test",
                "analysis_directory",
                "# Decision Loop Stress Test\n\n## Current Loop Shape\n- Describe the loop.\n## Midgame\n- Talk about variety.\n",
                "analysis_directory",
                "It lists loop topics but does not run the player through an explicit stress sequence.",
                "Restore first-hour to late-game numbered stress moves and structural repair checks.",
            ),
            _failure_case(
                "decision-loop-stress-test",
                "content_patch_bias",
                "# Decision Loop Stress Test\n\n## Repair Ideas\n- Add more enemies.\n- Add more upgrades.\n",
                "content_patch_bias",
                "It prescribes content expansion instead of structural pressure repair.",
                "Rewrite fixes around pressure, dominant strategies, and reward training.",
            ),
        ],
    },
    "simulation-resource-loop-design": {
        "domain_family": "game-design",
        "task_brief": "Design a simulation resource loop around visible pressures, tradeoffs, and recovery.",
        "opening_strategy": "Lead with map/tension/loop/correct rather than generic systems design commentary.",
        "expert_notes": [
            "The skill should first map the variable web, then show how pressures create player-facing choices.",
            "Positive and negative loops must be paired; snowballing alone is not a design.",
            "Failure recovery must preserve cost, not erase pressure.",
            "The loop should protect emotional fantasy, not drift into spreadsheet simulation.",
        ],
        "anti_patterns": [
            "spreadsheet loop",
            "hidden-state only design",
            "positive loop without brake",
            "free recovery",
        ],
        "task_probes": [
            _probe(
                "resource_pressure_map",
                "Map visible resource pressure for a frontier clinic simulation.",
                decision_terms=["variable web", "pressure relationships", "primary decision tensions"],
                cut_terms=["cut decorative resources", "keep only strong tensions"],
                failure_terms=["flat loop", "no visible pressure", "hidden simulation state"],
                repair_terms=["make pressure visible", "reduce currencies", "tighten tradeoffs"],
                output_fields=["Variable Web", "Pressure Relationships", "Primary Decision Tensions"],
                anti_generic_terms=["player-facing", "pressure", "tradeoff"],
            ),
            _probe(
                "feedback_recovery_loop",
                "Design positive and negative loops plus failure recovery for a survival settlement game.",
                decision_terms=["positive and negative loops", "failure recovery"],
                cut_terms=["avoid consequence-free reset"],
                failure_terms=["runaway snowballing", "death spiral", "free reset"],
                repair_terms=["add brake", "preserve cost", "keep agency"],
                output_fields=["Positive and Negative Loops", "Failure Recovery"],
                anti_generic_terms=["snowball", "counter-pressure", "lasting cost"],
            ),
            _probe(
                "fantasy_alignment",
                "Check whether a social survival economy supports the intended emotional fantasy.",
                decision_terms=["emotional fantasy alignment", "resource pressure"],
                cut_terms=["remove decorative variables"],
                failure_terms=["spreadsheet feeling", "fantasy mismatch"],
                repair_terms=["reconnect scarcity and aspiration", "show consequence in play"],
                output_fields=["Emotional Fantasy Alignment", "Design Recommendations"],
                anti_generic_terms=["fantasy alignment", "aspiration", "consequence"],
            ),
        ],
        "expected_outputs": [
            "Variable web with player-facing signals and roles.",
            "Pressure relationships and main decision tensions.",
            "Positive/negative loop pair plus failure recovery with cost.",
            "Emotional fantasy alignment and design recommendations.",
        ],
        "rewrite_pairs": [
            _rewrite_pair(
                "simulation-resource-loop-design",
                "Explain how resources interact in a simulation game and note any risks.",
                "Map the variable web, trace pressure relationships, pair loops, and define recovery plus fantasy alignment.",
                "Turn generic systems talk into a visible pressure program.",
            ),
            _rewrite_pair(
                "simulation-resource-loop-design",
                "List the resources, explain the loop, and suggest adding recovery if the game feels too punishing.",
                "Show which pressures the player sees, where tradeoffs bite, how positive and negative loops balance, and how recovery preserves cost instead of erasing it.",
                "Replace broad systems commentary with player-facing tension and recovery discipline.",
            ),
        ],
        "failure_cases": [
            _failure_case(
                "simulation-resource-loop-design",
                "spreadsheet_pressureless",
                "# Simulation Resource Loop Design\n\n## Resources\n- Money\n- Time\n- Energy\n",
                "spreadsheet_pressureless",
                "It lists resources but never turns them into tensions, loops, or recovery structure.",
                "Rebuild around variable roles, pressure relationships, loop pair, and recovery cost.",
            ),
            _failure_case(
                "simulation-resource-loop-design",
                "all_positive_loops",
                "# Simulation Resource Loop Design\n\n## Positive Loop\n- Success generates more success.\n",
                "all_positive_loops",
                "It creates growth without brakes, making the loop unstable and uninteresting.",
                "Pair each compounding loop with counter-pressure and a costly recovery path.",
            ),
        ],
    },
    "go-to-market-decision-brief": {
        "domain_family": "strategy",
        "task_brief": "Write a go-to-market decision brief with explicit channel bets and failure signals.",
        "opening_strategy": "Lead with market choice and risk, not generic launch advice.",
        "expert_notes": [
            "Choose one primary GTM bet and make the rejection criteria explicit.",
            "Output should end in a decision brief, not a laundry list of channels.",
        ],
        "anti_patterns": ["channel laundry list", "generic launch checklist"],
        "task_probes": [
            _probe(
                "gtm_primary_bet",
                "Choose a primary channel bet for a devtools launch.",
                decision_terms=["primary bet", "channel thesis", "evidence threshold"],
                cut_terms=["not every channel", "defer channels"],
                failure_terms=["channel sprawl", "missing rejection criteria"],
                repair_terms=["pick one bet", "state failure signal"],
                output_fields=["Decision Brief", "Primary Channel", "Failure Signals"],
                anti_generic_terms=["channel thesis", "evidence threshold"],
            )
        ],
        "expected_outputs": ["Decision brief with channel thesis, rejection criteria, and next test."],
    },
    "agent-skill-abuse-review": {
        "domain_family": "security",
        "task_brief": "Review an agent skill for abuse risk and blocked behavior.",
        "opening_strategy": "Lead with abuse path, trust boundary, and refusal rule.",
        "expert_notes": [
            "The skill must identify abuse paths, trust boundaries, and refusal conditions.",
            "Repairs should reduce capability misuse rather than add more vague safety prose.",
        ],
        "anti_patterns": ["generic safety disclaimer", "no refusal criteria"],
        "task_probes": [
            _probe(
                "abuse_boundary",
                "Review whether a skill can be repurposed for credential harvesting.",
                decision_terms=["abuse path", "trust boundary", "refusal condition"],
                cut_terms=["remove unsafe capability"],
                failure_terms=["credential access", "prompt injection", "boundary bypass"],
                repair_terms=["scope credentials", "refuse execution", "separate safe helper"],
                output_fields=["Abuse Path", "Refusal Rule", "Repair Direction"],
                anti_generic_terms=["trust boundary", "refusal", "unsafe capability"],
            )
        ],
        "expected_outputs": ["Abuse review with explicit blocked behavior and repair direction."],
    },
    "messy-dataset-analysis-plan": {
        "domain_family": "data",
        "task_brief": "Plan a messy dataset analysis with cleaning assumptions and failure checks.",
        "opening_strategy": "Lead with data trust, not analysis ambition.",
        "expert_notes": [
            "The first move is to classify data quality risk, not jump to modeling.",
            "Output should name cleaning assumptions, bias risks, and stop conditions.",
        ],
        "anti_patterns": ["straight to modeling", "missing data trust check"],
        "task_probes": [
            _probe(
                "dataset_trust",
                "Plan analysis for a multi-source CSV dump with duplicated IDs and missing timestamps.",
                decision_terms=["data trust", "cleaning assumption", "bias risk"],
                cut_terms=["defer modeling", "reject unreliable slice"],
                failure_terms=["silent duplicate bias", "timestamp drift"],
                repair_terms=["dedupe rule", "trust boundary", "stop condition"],
                output_fields=["Data Trust", "Cleaning Plan", "Stop Condition"],
                anti_generic_terms=["dedupe", "bias risk", "stop condition"],
            )
        ],
        "expected_outputs": ["Analysis plan with trust checks, cleaning assumptions, and stop conditions."],
    },
    "architecture-tradeoff-review": {
        "domain_family": "engineering",
        "task_brief": "Review architecture tradeoffs with explicit decision criteria and rejection reasons.",
        "opening_strategy": "Lead with tradeoff lens and irreversible cost, not generic pros/cons.",
        "expert_notes": [
            "A tradeoff review should force a decision, not restate options.",
            "Output should carry rejection reasons and revisit triggers.",
        ],
        "anti_patterns": ["balanced but indecisive summary", "generic pros cons"],
        "task_probes": [
            _probe(
                "tradeoff_forcing",
                "Choose between a queue-based async workflow and a simpler synchronous path for an internal tool.",
                decision_terms=["decision criteria", "rejection reason", "revisit trigger"],
                cut_terms=["reject one path", "avoid false balance"],
                failure_terms=["false balance", "missing irreversible cost"],
                repair_terms=["name winning criterion", "state reject reason"],
                output_fields=["Decision", "Rejected Option", "Revisit Trigger"],
                anti_generic_terms=["tradeoff lens", "irreversible cost", "revisit trigger"],
            )
        ],
        "expected_outputs": ["Tradeoff review with chosen option, rejected option, and revisit trigger."],
    },
    "research-memo-synthesis": {
        "domain_family": "writing",
        "task_brief": "Synthesize a research memo into a decision-facing narrative with evidence tiers.",
        "opening_strategy": "Lead with claim strength and unresolved questions, not summary prose.",
        "expert_notes": [
            "A memo synthesis should rank claims by evidence quality and uncertainty.",
            "Output should separate what is known, what is inferred, and what is still open.",
        ],
        "anti_patterns": ["summary only", "flattened evidence tiers"],
        "task_probes": [
            _probe(
                "memo_claim_tiers",
                "Synthesize a user-research memo into ranked claims and open questions.",
                decision_terms=["claim strength", "evidence tier", "open question"],
                cut_terms=["remove unsupported narrative"],
                failure_terms=["flattened evidence", "unsupported conclusion"],
                repair_terms=["separate observed vs inferred", "restate uncertainty"],
                output_fields=["Ranked Claims", "Evidence Tier", "Open Questions"],
                anti_generic_terms=["observed", "inferred", "uncertain"],
            )
        ],
        "expected_outputs": ["Memo synthesis with ranked claims, evidence tiers, and open questions."],
    },
}


def load_expert_skill_corpus() -> dict[str, ExpertSkillCorpusEntry]:
    corpus: dict[str, ExpertSkillCorpusEntry] = {}
    for skill_name, seed in _KNOWN_CORPUS_DATA.items():
        expert_markdown = _golden_markdown(skill_name)
        failure_cases = list(seed.get("failure_cases") or [])
        corpus[skill_name] = ExpertSkillCorpusEntry(
            skill_name=skill_name,
            domain_family=str(seed.get("domain_family") or "methodology_guidance"),
            task_brief=str(seed.get("task_brief") or ""),
            expert_skill_markdown=expert_markdown,
            expert_notes=list(seed.get("expert_notes") or []),
            section_corpus=_section_corpus(
                skill_name,
                expert_markdown,
                list(seed.get("expert_notes") or []),
                failure_cases,
            ),
            anti_patterns=list(seed.get("anti_patterns") or []),
            task_probes=list(seed.get("task_probes") or []),
            expected_outputs=list(seed.get("expected_outputs") or []),
            rewrite_pairs=list(seed.get("rewrite_pairs") or []),
            failure_cases=failure_cases,
        )
    return corpus


def expert_corpus_entry_for_skill(*, skill_name: str) -> ExpertSkillCorpusEntry | None:
    return load_expert_skill_corpus().get(skill_name)


def _execution_move(step_id: int, move: Any) -> ExecutionMove:
    return ExecutionMove(
        step_id=str(step_id),
        label=str(getattr(move, "name", "") or ""),
        purpose=str(getattr(move, "purpose", "") or ""),
        decision=str(getattr(move, "decision_probe", "") or ""),
        action=str(getattr(move, "action", "") or ""),
        output=str(getattr(move, "output_fragment", "") or ""),
        failure_signal=str(getattr(move, "failure_signal", "") or ""),
        fix=str(getattr(move, "repair_move", "") or ""),
        must_include_terms=list(getattr(move, "must_include_terms", []) or []),
        avoid_terms=list(getattr(move, "avoid_terms", []) or []),
    )


def _analysis_blocks(skill_name: str, workflow_surface: str, output_fields: list[str], expert_notes: list[str]) -> list[AnalysisBlock]:
    if workflow_surface == "execution_spine":
        return []
    if workflow_surface == "hybrid":
        field_groups = [
            ("Variable Web", ["Variable Web", "Variable Roles"]),
            ("Pressure Relationships", ["Pressure Relationships", "Primary Decision Tensions"]),
            ("Feedback Loops", ["Positive and Negative Loops", "Failure Recovery", "Emotional Fantasy Alignment"]),
        ]
    else:
        field_groups = [(field, [field]) for field in output_fields[:6]]
    blocks: list[AnalysisBlock] = []
    notes = list(expert_notes or [])
    for index, (name, fields) in enumerate(field_groups, start=1):
        blocks.append(
            AnalysisBlock(
                name=name,
                when_used=notes[(index - 1) % len(notes)] if notes else f"Use `{name}` to hold the mapped analysis after the workflow makes the decision.",
                questions=[f"What must `{name}` make visible to the user or builder?"],
                output_fields=[field for field in fields if field in output_fields],
            )
        )
    return blocks


def build_skill_program_ir(
    *,
    skill_name: str,
    task: str = "",
    candidate_dna: ExpertSkillDNA | None = None,
) -> SkillProgramIR | None:
    dna = candidate_dna or expert_skill_dna_for_skill(skill_name=skill_name, task=task)
    if dna is None:
        return None
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    plan = build_domain_move_plan(skill_name=skill_name, task=task)
    style_profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    workflow_surface = str(getattr(dna, "workflow_surface", "") or "execution_spine").strip().lower()
    execution_spine = [_execution_move(index, move) for index, move in enumerate(list(dna.workflow_moves or []), start=1)]
    output_schema = {
        field: [
            OUTPUT_FIELD_GUIDANCE.get(dna.skill_name, {}).get(
                field,
                "Write the concrete result with the decision, evidence, and next action clearly enough to use.",
            ),
            f"Good: {field} names the decision, evidence, consequence, and next action clearly enough to act on.",
            f"Weak: {field} stays abstract, repeats the prompt, or leaves the field as a vague summary.",
        ]
        for field in list(dna.output_fields or [])
    }
    failure_repairs = [
        f"{pattern} -> {dna.repair_moves[index % len(dna.repair_moves)] if dna.repair_moves else 'Return to the workflow and make the judgment explicit.'}"
        for index, pattern in enumerate(list(dna.failure_patterns or []))
    ]
    style_profile_items = list(getattr(style_profile, "workflow_label_set", []) or [])
    if corpus is not None:
        style_profile_items = style_profile_items + list(corpus.anti_patterns or [])
    program = SkillProgramIR(
        skill_name=skill_name,
        workflow_surface=workflow_surface,
        opening_strategy=(
            str(_KNOWN_CORPUS_DATA.get(skill_name, {}).get("opening_strategy") or "")
            or str(getattr(plan, "opening_frame", "") or "")
        ),
        execution_spine=execution_spine,
        analysis_blocks=_analysis_blocks(
            skill_name,
            workflow_surface,
            list(dna.output_fields or []),
            list(corpus.expert_notes if corpus is not None else []),
        ),
        decision_rules=list(dna.decision_rules or []),
        cut_rules=list(dna.cut_rules or []),
        failure_repairs=failure_repairs,
        output_schema=output_schema,
        style_profile=style_profile_items,
        voice_constraints=list(dna.voice_rules or []),
        source_skill_name=skill_name,
        source_confidence="checked_in" if candidate_dna is None else "candidate",
        summary=[
            f"workflow_surface={workflow_surface}",
            f"execution_move_count={len(execution_spine)}",
            f"analysis_block_count={len(_analysis_blocks(skill_name, workflow_surface, list(dna.output_fields or []), list(corpus.expert_notes if corpus is not None else [])))}",
        ],
    )
    return program


def _surface_label_profile(skill_name: str) -> dict[str, str]:
    profiles = {
        "concept-to-mvp-pack": {
            "decision": "Prove",
            "action": "Do",
            "output": "Package",
            "failure": "Cut If",
            "fix": "Tighten",
            "write": "Write",
            "good": "Good",
            "weak": "Weak",
            "pitfalls": "Failure Patterns and Fixes",
        },
        "decision-loop-stress-test": {
            "decision": "Stress Test",
            "action": "Watch",
            "output": "Write",
            "failure": "Break If",
            "fix": "Reinforce / Repair",
            "write": "Write",
            "good": "Strong",
            "weak": "Weak",
            "pitfalls": "Collapse Patterns and Repairs",
        },
        "simulation-resource-loop-design": {
            "decision": "Map",
            "action": "Trace",
            "output": "Record",
            "failure": "Watch For",
            "fix": "Correct",
            "write": "Record",
            "good": "Healthy",
            "weak": "Weak",
            "pitfalls": "Loop Failures and Corrections",
        },
    }
    return profiles.get(
        skill_name,
        {
            "decision": "Decision",
            "action": "Do",
            "output": "Output",
            "failure": "Failure Signal",
            "fix": "Fix",
            "write": "Write",
            "good": "Good",
            "weak": "Weak",
            "pitfalls": "Failure Patterns and Fixes",
        },
    )


def build_skill_realization_spec(
    *,
    skill_name: str,
    task: str,
    program: SkillProgramIR,
) -> SkillRealizationSpec:
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    style_profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    section_order = [
        "Overview",
        "Core Principle",
        "When to Use",
        "When Not to Use",
        "Inputs",
        "Default Workflow",
    ]
    if program.workflow_surface == "hybrid":
        section_order.append("Analysis Blocks")
    section_order.extend(
        [
            "Output Format",
            "Decision Rules",
            "Cut Rules",
            "Quality Checks",
            "Failure Patterns and Fixes",
            "Worked Micro-Example",
            "Voice Rules",
        ]
    )
    section_rhythm = list(getattr(style_profile, "section_rhythm", []) or [])
    opening_frame = str(getattr(style_profile, "opening_frame", "") or program.opening_strategy or "")
    sections = [
        SectionRealizationSpec(
            section_name=name,
            rhetorical_purpose=next(
                (entry.section_purpose for entry in list(getattr(corpus, "section_corpus", []) or []) if entry.section_name == name),
                f"Render `{name}` as a domain-facing section instead of a generic methodology block.",
            ),
            allowed_surface_forms=["compact", "direct", "judgment_first"],
            sentence_budget=2 if name in {"Overview", "Core Principle"} else 3,
            required_judgment_moves=next(
                (entry.judgment_moves[:4] for entry in list(getattr(corpus, "section_corpus", []) or []) if entry.section_name == name),
                [],
            ),
            forbidden_filler_patterns=list(getattr(style_profile, "forbidden_boilerplate", []) or []),
        )
        for name in section_order
    ]
    return SkillRealizationSpec(
        skill_name=skill_name,
        workflow_surface=program.workflow_surface,
        opening_frame=opening_frame,
        section_order=section_order,
        section_rhythm=section_rhythm,
        compression_policy="tight" if program.workflow_surface == "execution_spine" else "balanced",
        voice_profile=list(program.voice_constraints or []),
        boilerplate_forbidden=list(getattr(style_profile, "forbidden_boilerplate", []) or []),
        strategy_family="default",
        sections=sections,
        summary=[
            f"workflow_surface={program.workflow_surface}",
            f"section_count={len(section_order)}",
            f"section_rhythm={','.join(section_rhythm) or 'none'}",
        ],
    )


def _ordered_sections(base_order: list[str], preferred_tail: list[str]) -> list[str]:
    head = [item for item in base_order if item not in {
        "Output Format",
        "Decision Rules",
        "Cut Rules",
        "Quality Checks",
        "Failure Patterns and Fixes",
        "Worked Micro-Example",
        "Voice Rules",
    }]
    tail = [item for item in preferred_tail if item in base_order]
    for item in base_order:
        if item not in head and item not in tail:
            tail.append(item)
    ordered: list[str] = []
    for item in head + tail:
        if item not in ordered:
            ordered.append(item)
    return ordered


def _pressure_strategy_family(skill_name: str, workflow_surface: str, base_order: list[str]) -> list[dict[str, Any]]:
    families: dict[str, list[dict[str, Any]]] = {
        "concept-to-mvp-pack": [
            {
                "name": "proof_first",
                "opening_frame": "Decide what the first playable must prove before it grows.",
                "section_order": _ordered_sections(base_order, ["Quality Checks", "Cut Rules", "Output Format", "Failure Patterns and Fixes", "Worked Micro-Example", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 1, "Core Principle": 1, "Default Workflow": 5, "Quality Checks": 4},
                "workflow_mode": "validation_pressure",
                "step_frame": "proof_gate",
                "output_focus": ["Core Validation Question", "Smallest Honest Loop"],
                "quality_tone": "proof-first",
                "quality_mode": "proof_gate",
                "failure_style": "redesign_trigger",
                "failure_mode": "kill_or_fix",
                "strategy_tags": ["proof", "validation", "scope"],
            },
            {
                "name": "cut_first",
                "opening_frame": "Cut scope early, then prove the smallest playable that survives.",
                "section_order": _ordered_sections(base_order, ["Cut Rules", "Quality Checks", "Output Format", "Failure Patterns and Fixes", "Worked Micro-Example", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 1, "Cut Rules": 4, "Default Workflow": 4},
                "workflow_mode": "cut_pressure",
                "step_frame": "scope_gate",
                "output_focus": ["Feature Cut", "Out of Scope", "Minimum Content Package"],
                "quality_tone": "scope_enforcement",
                "quality_mode": "scope_gate",
                "failure_style": "scope_creep",
                "failure_mode": "scope_creep",
                "strategy_tags": ["cut", "scope", "out-of-scope"],
            },
            {
                "name": "package_ready",
                "opening_frame": "Turn the proof into a first-playable package that can actually be built next.",
                "section_order": _ordered_sections(base_order, ["Output Format", "Worked Micro-Example", "Quality Checks", "Cut Rules", "Failure Patterns and Fixes", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 2, "Output Format": 4, "Worked Micro-Example": 3},
                "workflow_mode": "package_readiness",
                "step_frame": "handoff_gate",
                "output_focus": ["MVP Pack", "Build Recommendation", "Minimum Content Package"],
                "quality_tone": "build_ready",
                "quality_mode": "build_gate",
                "failure_style": "pack_failure",
                "failure_mode": "handoff_failure",
                "strategy_tags": ["package", "build", "handoff"],
            },
            {
                "name": "failure_pass",
                "opening_frame": "Prove the first playable, then run a failure pass before approval.",
                "section_order": _ordered_sections(base_order, ["Failure Patterns and Fixes", "Quality Checks", "Output Format", "Cut Rules", "Worked Micro-Example", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 1, "Failure Patterns and Fixes": 5, "Quality Checks": 4},
                "workflow_mode": "failure_pass",
                "step_frame": "failure_pass",
                "output_focus": ["Failure Pass", "Build Recommendation", "Out of Scope"],
                "quality_tone": "failure_pass",
                "quality_mode": "failure_gate",
                "failure_style": "kill_or_fix",
                "failure_mode": "kill_or_fix",
                "strategy_tags": ["failure", "kill", "repair"],
            },
        ],
        "decision-loop-stress-test": [
            {
                "name": "collapse_first_v2",
                "opening_frame": "Find the collapse witness before the loop gets greenlit by novelty, rewards, or pacing cover.",
                "section_order": _ordered_sections(base_order, ["Failure Patterns and Fixes", "Quality Checks", "Decision Rules", "Output Format", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Failure Patterns and Fixes": 5, "Default Workflow": 4},
                "workflow_mode": "collapse_first_v2",
                "step_frame": "collapse_probe_v2",
                "output_focus": ["Collapse Point", "Solved State Risk", "Repair Recommendation"],
                "quality_tone": "collapse",
                "quality_mode": "collapse_gate",
                "failure_style": "solved_state",
                "failure_mode": "solved_state",
                "strategy_tags": ["collapse", "solved-state", "dominance"],
            },
            {
                "name": "stop_condition_first_v2",
                "opening_frame": "Name the stop condition and collapse witness before you explain the phase, the content, or the reward pacing.",
                "section_order": _ordered_sections(base_order, ["Quality Checks", "Failure Patterns and Fixes", "Output Format", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Default Workflow": 5, "Quality Checks": 4},
                "workflow_mode": "stop_condition_first_v2",
                "step_frame": "stop_condition_probe_v2",
                "output_focus": ["Break Point", "Pressure Map", "Repair Recommendation"],
                "quality_tone": "pressure",
                "quality_mode": "pressure_gate",
                "failure_style": "collapse_signals",
                "failure_mode": "collapse_signals",
                "strategy_tags": ["stop-condition", "pressure", "breakpoint"],
            },
            {
                "name": "fake_fix_rejection_v2",
                "opening_frame": "Reject fake fixes early: if the repair is only numeric tuning or more content, it is not a repair yet.",
                "section_order": _ordered_sections(base_order, ["Output Format", "Failure Patterns and Fixes", "Quality Checks", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Output Format": 4, "Failure Patterns and Fixes": 4},
                "workflow_mode": "fake_fix_rejection_v2",
                "step_frame": "false_fix_gate_v2",
                "output_focus": ["Repair Recommendation", "Pressure Map", "Variation Audit"],
                "quality_tone": "repair",
                "quality_mode": "repair_gate",
                "failure_style": "false_fix_rejection",
                "failure_mode": "false_fix_rejection",
                "strategy_tags": ["repair", "structure", "false-fix"],
            },
            {
                "name": "pressure_audit_v2",
                "opening_frame": "Audit the loop for pressure, collapse, and wrong reinforcement before mastery hardens the wrong habit into the only answer.",
                "section_order": _ordered_sections(base_order, ["Decision Rules", "Quality Checks", "Output Format", "Failure Patterns and Fixes", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Decision Rules": 4, "Quality Checks": 4},
                "workflow_mode": "pressure_audit_v2",
                "step_frame": "pressure_audit_v2",
                "output_focus": ["Reinforcement Check", "Variation Audit", "Repair Recommendation"],
                "quality_tone": "pressure",
                "quality_mode": "reinforcement_gate",
                "failure_style": "wrong_behavior",
                "failure_mode": "wrong_behavior",
                "strategy_tags": ["reinforcement", "variation", "mastery"],
            },
        ],
        "simulation-resource-loop-design": [
            {
                "name": "map_first",
                "opening_frame": "Map the pressure web before you balance any single resource in isolation.",
                "section_order": _ordered_sections(base_order, ["Analysis Blocks", "Output Format", "Quality Checks", "Failure Patterns and Fixes", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Analysis Blocks": 5, "Output Format": 3},
                "workflow_mode": "map_first",
                "step_frame": "map_probe",
                "output_focus": ["Variable Web", "Pressure Relationships", "Main Feedback Loops"],
                "quality_tone": "mapping",
                "quality_mode": "mapping_gate",
                "failure_style": "hidden_pressure",
                "failure_mode": "hidden_pressure",
                "strategy_tags": ["map", "web", "visibility"],
            },
            {
                "name": "tension_first",
                "opening_frame": "Force visible tradeoffs before you optimize the system for smoothness.",
                "section_order": _ordered_sections(base_order, ["Quality Checks", "Analysis Blocks", "Output Format", "Failure Patterns and Fixes", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Quality Checks": 4, "Analysis Blocks": 4},
                "workflow_mode": "tension_first",
                "step_frame": "tension_probe",
                "output_focus": ["Primary Decision Tensions", "Pressure Relationships", "Failure and Recovery"],
                "quality_tone": "tension",
                "quality_mode": "tension_gate",
                "failure_style": "no_tradeoff",
                "failure_mode": "no_tradeoff",
                "strategy_tags": ["tension", "tradeoff", "pressure"],
            },
            {
                "name": "loop_balance",
                "opening_frame": "Balance positive and negative loops without letting either side erase the decision game.",
                "section_order": _ordered_sections(base_order, ["Output Format", "Analysis Blocks", "Quality Checks", "Failure Patterns and Fixes", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Output Format": 4, "Quality Checks": 4},
                "workflow_mode": "loop_balance",
                "step_frame": "loop_balance",
                "output_focus": ["Main Feedback Loops", "Failure and Recovery", "Emotional Fantasy Alignment"],
                "quality_tone": "balance",
                "quality_mode": "balance_gate",
                "failure_style": "runaway_loops",
                "failure_mode": "runaway_loops",
                "strategy_tags": ["loops", "balance", "counterweight"],
            },
            {
                "name": "recovery_cost",
                "opening_frame": "Design recovery that preserves cost, clarity, and fantasy instead of flattening the system.",
                "section_order": _ordered_sections(base_order, ["Failure Patterns and Fixes", "Output Format", "Analysis Blocks", "Quality Checks", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Failure Patterns and Fixes": 5, "Output Format": 4},
                "workflow_mode": "recovery_cost",
                "step_frame": "recovery_cost",
                "output_focus": ["Failure and Recovery", "Main Feedback Loops", "Emotional Fantasy Alignment"],
                "quality_tone": "recovery_cost",
                "quality_mode": "recovery_gate",
                "failure_style": "cheap_recovery",
                "failure_mode": "cheap_recovery",
                "strategy_tags": ["recovery", "cost", "fantasy"],
            },
        ],
    }
    default_family = [
        {
            "name": "balanced",
            "opening_frame": "",
            "section_order": list(base_order),
            "sentence_budgets": {},
            "workflow_mode": workflow_surface,
            "step_frame": workflow_surface,
            "output_focus": [],
            "quality_tone": "balanced",
            "quality_mode": "balanced",
            "failure_style": "balanced",
            "failure_mode": "balanced",
            "strategy_tags": [workflow_surface],
        }
    ]
    return families.get(skill_name, default_family)


def _spec_for_strategy(
    *,
    base_spec: SkillRealizationSpec,
    strategy_profile: dict[str, Any],
) -> SkillRealizationSpec:
    budget_overrides = dict(strategy_profile.get("sentence_budgets") or {})
    section_order = list(strategy_profile.get("section_order") or list(base_spec.section_order or []))
    section_map = {section.section_name: section for section in list(base_spec.sections or [])}
    sections: list[SectionRealizationSpec] = []
    for section_name in section_order:
        current = section_map.get(section_name)
        if current is None:
            continue
        sections.append(
            current.model_copy(
                update={
                    "sentence_budget": int(budget_overrides.get(section_name, current.sentence_budget or 3)),
                    "section_form": str(strategy_profile.get("workflow_mode") or current.section_form or "compact"),
                    "primary_force_focus": str(strategy_profile.get("quality_tone") or current.primary_force_focus or ""),
                    "emphasis_level": "high"
                    if section_name in {"Default Workflow", "Output Format", "Quality Checks", "Failure Patterns and Fixes"}
                    else current.emphasis_level,
                }
            )
        )
    return base_spec.model_copy(
        update={
            "opening_frame": str(strategy_profile.get("opening_frame") or base_spec.opening_frame),
            "section_order": section_order,
            "compression_policy": "tight" if "tight" in strategy_profile.get("strategy_tags", []) else base_spec.compression_policy,
            "strategy_family": "pressure_first",
            "strategy_tags": list(strategy_profile.get("strategy_tags") or []),
            "sections": sections,
        }
    )


def _strategy_budget_signature(strategy_profile: dict[str, Any]) -> str:
    budgets = dict(strategy_profile.get("sentence_budgets") or {})
    if not budgets:
        return "default"
    return ",".join(f"{name}:{int(value)}" for name, value in sorted(budgets.items()))


def _artifact_for_markdown(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path="SKILL.md", content=content, content_type="text/markdown")])


def _request_plan(skill_name: str, task: str) -> tuple[SkillCreateRequestV6, SkillPlan]:
    return (
        SkillCreateRequestV6(task=task, skill_name_hint=skill_name, skill_archetype="methodology_guidance"),
        SkillPlan(skill_name=skill_name, skill_archetype="methodology_guidance"),
    )


def _candidate_editorial_metrics(
    *,
    skill_name: str,
    task: str,
    markdown: str,
    realization_candidate_count: int = 0,
) -> dict[str, Any]:
    from .skill_task_outcome import build_skill_task_outcome_report

    request, plan = _request_plan(skill_name, task)
    artifacts = _artifact_for_markdown(markdown)
    body = build_skill_body_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    domain_specificity = build_skill_domain_specificity_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    domain_expertise = build_skill_domain_expertise_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    expert_structure = build_skill_expert_structure_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    depth = build_skill_depth_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    editorial = build_skill_editorial_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    style = build_skill_style_diversity_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    move = build_skill_move_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    task_outcome = build_skill_task_outcome_report(
        generated_skill_markdown_by_name={skill_name: markdown},
        skill_names=[skill_name],
    )
    profile_result = next(iter(list(task_outcome.profile_results or [])), None)
    editorial_force = build_skill_editorial_force_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
        body_quality=body,
        domain_specificity=domain_specificity,
        domain_expertise=domain_expertise,
        depth_quality=depth,
        editorial_quality=editorial,
        style_diversity=style,
        move_quality=move,
        realization_candidate_count=realization_candidate_count,
    )
    score = (
        0.25 * float(getattr(editorial_force, "decision_pressure_score", 0.0) or 0.0)
        + 0.18 * float(getattr(editorial_force, "cut_sharpness_score", 0.0) or 0.0)
        + 0.16 * float(getattr(editorial_force, "failure_repair_force", 0.0) or 0.0)
        + 0.12 * float(getattr(editorial_force, "output_executability_score", 0.0) or 0.0)
        + 0.10 * float(getattr(editorial_force, "boundary_rule_coverage", 0.0) or 0.0)
        + 0.08 * float(getattr(editorial_force, "stop_condition_coverage", 0.0) or 0.0)
        + 0.06 * float(getattr(editorial_force, "section_force_distinctness", 0.0) or 0.0)
        + 0.05 * float(getattr(style, "domain_rhythm_score", 0.0) or 0.0)
        + 0.05 * max(0.0, 1.0 - float(getattr(editorial, "redundancy_ratio", 0.0) or 0.0))
    )
    return {
        "body": body,
        "domain_specificity": domain_specificity,
        "domain_expertise": domain_expertise,
        "expert_structure": expert_structure,
        "depth": depth,
        "editorial": editorial,
        "editorial_force": editorial_force,
        "style": style,
        "move": move,
        "task_outcome": task_outcome,
        "domain_move_coverage": float(getattr(domain_expertise, "domain_move_coverage", 0.0) or 0.0),
        "section_depth_score": float(getattr(depth, "section_depth_score", 0.0) or 0.0),
        "task_outcome_with_skill_average": float(getattr(profile_result, "with_skill_average", 0.0) or 0.0),
        "redundancy_ratio": float(getattr(editorial, "redundancy_ratio", 0.0) or 0.0),
        "shared_opening_phrase_ratio": float(getattr(style, "shared_opening_phrase_ratio", 0.0) or 0.0),
        "cross_case_similarity": 0.0,
        "compression_without_loss": float(getattr(editorial_force, "compression_without_loss", 0.0) or 0.0),
        "expert_quality_check_recall": float(getattr(expert_structure, "expert_quality_check_recall", 0.0) or 0.0),
        "generic_surface_leakage": float(getattr(editorial_force, "generic_surface_leakage", 0.0) or 0.0),
        "decision_pressure_score": float(getattr(editorial_force, "decision_pressure_score", 0.0) or 0.0),
        "section_force_distinctness": float(getattr(editorial_force, "section_force_distinctness", 0.0) or 0.0),
        "failure_repair_force": float(getattr(editorial_force, "failure_repair_force", 0.0) or 0.0),
        "stop_condition_coverage": float(getattr(editorial_force, "stop_condition_coverage", 0.0) or 0.0),
        "cut_sharpness_score": float(getattr(editorial_force, "cut_sharpness_score", 0.0) or 0.0),
        "boundary_rule_coverage": float(getattr(editorial_force, "boundary_rule_coverage", 0.0) or 0.0),
        "score": round(score, 4),
    }


def _section_entries(corpus: ExpertSkillCorpusEntry | None, section_name: str) -> list[ExpertSectionCorpusEntry]:
    if corpus is None:
        return []
    return [
        entry
        for entry in list(getattr(corpus, "section_corpus", []) or [])
        if entry.section_name == section_name
    ]


def _strategy_rewrite_pairs(
    *,
    corpus: ExpertSkillCorpusEntry | None,
    strategy_profile: dict[str, Any],
) -> list[ExpertRewritePair]:
    if corpus is None:
        return []
    tags = {str(item).lower() for item in list(strategy_profile.get("strategy_tags") or [])}
    quality_tone = str(strategy_profile.get("quality_tone") or "").lower()
    results: list[ExpertRewritePair] = []
    for pair in list(getattr(corpus, "rewrite_pairs", []) or []):
        reason = str(pair.revision_reason or "").lower()
        weak = str(pair.weak_shell or "").lower()
        if quality_tone and quality_tone in reason:
            results.append(pair)
            continue
        if any(tag in reason or tag in weak for tag in tags):
            results.append(pair)
    return results[:2]


def _strategy_failure_cases(
    *,
    corpus: ExpertSkillCorpusEntry | None,
    strategy_profile: dict[str, Any],
) -> list[ExpertFailureCase]:
    if corpus is None:
        return []
    failure_mode = str(strategy_profile.get("failure_mode") or "").lower()
    quality_tone = str(strategy_profile.get("quality_tone") or "").lower()
    results: list[ExpertFailureCase] = []
    for failure in list(getattr(corpus, "failure_cases", []) or []):
        failure_type = str(failure.failure_type or "").lower()
        why = str(failure.why_it_fails or "").lower()
        if failure_mode and (failure_mode in failure_type or failure_mode in why):
            results.append(failure)
            continue
        if quality_tone and quality_tone in why:
            results.append(failure)
    if not results:
        results = list(getattr(corpus, "failure_cases", []) or [])
    return results[:2]


def _strategy_primary_moves(
    *,
    corpus: ExpertSkillCorpusEntry | None,
    section_name: str,
    strategy_profile: dict[str, Any],
) -> list[str]:
    tags = {str(item).lower() for item in list(strategy_profile.get("strategy_tags") or [])}
    moves: list[str] = []
    for entry in _section_entries(corpus, section_name):
        for item in list(entry.judgment_moves or []):
            lowered = item.lower()
            if not tags or any(tag in lowered for tag in tags):
                if item not in moves:
                    moves.append(item)
    if moves:
        return moves[:3]
    return [item for entry in _section_entries(corpus, section_name) for item in list(entry.judgment_moves or [])[:2]][:3]


def _section_variant_text(
    *,
    section_name: str,
    strategy: str,
    strategy_profile: dict[str, Any],
    plan: Any,
    program: SkillProgramIR,
    corpus: ExpertSkillCorpusEntry | None,
) -> list[str]:
    skill_name = str(program.skill_name or "")
    output_focus = list(strategy_profile.get("output_focus") or [])
    quality_tone = str(strategy_profile.get("quality_tone") or "")
    failure_style = str(strategy_profile.get("failure_style") or "")
    target_focus = str(strategy_profile.get("target_focus") or "")
    rewrite_pairs = _strategy_rewrite_pairs(corpus=corpus, strategy_profile=strategy_profile)
    failure_cases = _strategy_failure_cases(corpus=corpus, strategy_profile=strategy_profile)
    section_moves = _strategy_primary_moves(corpus=corpus, section_name=section_name, strategy_profile=strategy_profile)
    frontier_lines = _frontier_section_lines(skill_name=program.skill_name, target_focus=target_focus, section_name=section_name)
    if section_name == "Overview":
        overview_lines = {
            ("concept-to-mvp-pack", "proof_first"): "Start with a question that can fail, then shrink the playable until the proof is honest.",
            ("concept-to-mvp-pack", "cut_first"): "Treat scope as suspect until the smallest surviving proof is clear.",
            ("concept-to-mvp-pack", "package_ready"): "Lock the proof first, then shape the smallest build-ready pack around it.",
            ("concept-to-mvp-pack", "failure_pass"): "Approve the first playable only after a failure pass says what would force a redesign in a greybox build with stubbed content.",
            ("decision-loop-stress-test", "collapse_first_v2"): "Find the collapse witness and the break point before you discuss more content, and reject any repair recommendation that is not just numeric tuning, not just more content, still keeps the same dominant line, still keeps the same read or same consequence, still lets the old answer survive, or never explains why the old dominant line stops paying and a new answer becomes correct.",
            ("decision-loop-stress-test", "stop_condition_first_v2"): "Name the stop condition, collapse witness, break point, and structural witness before phase explanation, then reject any repair recommendation that keeps the same dominant line, the same read, the same consequence, lets the old answer keep working, or never names the reward, information, or cost change that makes the new answer become correct.",
            ("decision-loop-stress-test", "fake_fix_rejection_v2"): "Reject fake repairs early: if numeric-only tuning, more content, pacing cover, or throughput-only mastery still keep the same dominant line, the same read, or the same consequence structure alive, or if the old dominant line still pays under the same reward, information, or cost rules, the structural replacement has not started yet.",
            ("decision-loop-stress-test", "pressure_audit_v2"): "Audit what mastery teaches, which reward loop currently trains the wrong habit, what player behavior must disappear, what right habit should replace it, what replacement behavior must become optimal, what replacement reward loop makes that new behavior pay, and whether the repair recommendation is a structural fix that makes the old answer stop working because the old dominant line stops paying.",
            ("simulation-resource-loop-design", "map_first"): "Start by drawing the pressure web; only then judge balance inside it.",
            ("simulation-resource-loop-design", "tension_first"): "Lead with tradeoffs that hurt in visible ways, not with resource lists.",
            ("simulation-resource-loop-design", "loop_balance"): "Balance positive and negative loops so neither side erases the decision game.",
            ("simulation-resource-loop-design", "recovery_cost"): "Recovery should preserve cost, visibility, and fantasy instead of flattening the system.",
        }
        overview = overview_lines.get((program.skill_name, strategy), "")
        if not overview:
            overview = frontier_lines[0] if frontier_lines else str(plan.overview or "").strip()
        return [overview or str(strategy_profile.get("opening_frame") or plan.overview)]
    if section_name == "Core Principle":
        lines = [str(getattr(plan.dna, "core_thesis", "") or "")]
        if quality_tone in {"proof-first", "pressure", "tension"}:
            if section_moves:
                lines.append(f"Keep the section anchored on: {', '.join(section_moves[:2])}.")
            return lines[:2]
        if corpus is not None and corpus.expert_notes:
            lines.append(corpus.expert_notes[min(1, len(corpus.expert_notes) - 1)])
        return lines
    if section_name == "Quality Checks":
        if skill_name == "decision-loop-stress-test" and target_focus == "pressure":
            return [
                "Hard fail any repair recommendation that is not just numeric tuning, not just more content, not just phase explanation, not just pacing cover, not just throughput-only mastery, is only softer compensation, still leaves the old answer working, or still keeps the same dominant line alive.",
                "Hard fail any solved-state repair that keeps the same dominant line still winning, the same read still solving, the same consequence structure still paying out, or the old answer alive inside the same decision landscape before balance values are tuned, and hard fail any numeric-only, content-only, pacing-only, or throughput-only fix.",
                "Hard fail any variation pass that names variation but keeps the same dominant line still winning, lets the same answer survive under a new label, keeps the same read or same consequence under a new label, never says what old answer stops working, what new answer becomes correct, what reward, information, or cost changed to cause that shift, or why the old dominant line still pays.",
                "Hard fail any reinforcement pass that names wrong habit to right habit but never states which reward loop currently trains the wrong behavior, what player behavior must disappear, what replacement behavior must become optimal, what replacement reward logic makes the right habit profitable, what reward, information, or cost shift causes that behavior shift, or why the old behavior still pays.",
                "Hard fail any stop condition that names a break point without naming the collapse witness the player can actually observe.",
            ]
        if frontier_lines:
            return frontier_lines[:2]
        if quality_tone == "pressure":
            lines = ["Force a structural answer before anyone reaches for softer compensation."]
        elif quality_tone == "scope_enforcement":
            lines = ["Cut anything that protects comfort instead of proof."]
        elif quality_tone == "recovery_cost":
            lines = ["Keep recovery meaningful instead of flattening the loop."]
        elif quality_tone == "build_ready":
            lines = ["Only keep checks that make the pack buildable without hidden scope."]
        else:
            lines = []
        if section_moves:
            lines.append(f"Keep the checks anchored on {', '.join(section_moves[:2])}.")
        return lines[:2]
    if section_name == "Failure Patterns and Fixes":
        if skill_name == "decision-loop-stress-test" and target_focus == "pressure":
            strategy_specific = {
                "collapse_first_v2": "Treat any loop without a collapse witness or break point, or any repair recommendation that still keeps the same read, tradeoff, same consequence, dominant line, or old answer alive, or never says why the old dominant line stops paying, as unshippable until the structural fix is explicit.",
                "stop_condition_first_v2": "Treat missing stop conditions, missing collapse witnesses, break point labels with no observable witness, and repair recommendations that keep the old answer working or never name the reward, information, or cost change that makes the new answer become correct as structure failures until the structural witness is explicit.",
                "fake_fix_rejection_v2": "Treat numeric-only tuning, content-only padding, pacing-only relief, reward inflation, and fake variation that keeps the same dominant line still winning, the same read still solving, the same consequence still paying out, the old answer still working, or the old dominant line still paying as false fixes unless the repair recommendation names a structural fix and the structural replacement.",
                "pressure_audit_v2": "Treat reinforcement that leaves the wrong habit alive, keeps the same read or dominant line, never says which reward loop currently trains it, never says what wrong habit stops paying, never says what player behavior must disappear, never says what replacement reward loop makes the right habit profitable, or never names the behavior shift as a failed repair.",
            }.get(strategy, "")
            if strategy_specific:
                return [strategy_specific, *frontier_lines[:1]]
        if frontier_lines:
            return frontier_lines[:1]
        if failure_style == "solved_state":
            return ["Treat solved states and fake variation as structure failures, not balance trivia."]
        if failure_style == "cheap_recovery":
            return ["Treat cheap recovery and invisible pressure as core loop failures, not polish issues."]
        if failure_style == "scope_creep":
            return ["Treat anything that dilutes the proof or hides uncertainty as a failure, not a nice-to-have."]
        if failure_style == "false_fix_rejection":
            return ["Treat repairs that add events, rewards, or content padding without changing pressure as false fixes."]
        if failure_style == "repair_moves":
            return ["Treat repairs that add content without changing pressure as false fixes."]
        if failure_cases:
            return [failure_cases[0].why_it_fails]
        return []
    if section_name == "Output Format" and output_focus:
        if frontier_lines:
            return frontier_lines[:2]
        lines = [f"Lead with `{output_focus[0]}` and keep the rest of the output subordinate to that decision."]
        if len(output_focus) > 1:
            lines.append(f"Secondary emphasis: {', '.join(output_focus[1:3])}.")
        return lines[:2]
    return []


def _strip_guidance_prefix(text: str, label: str) -> str:
    stripped = str(text or "").strip()
    lowered = stripped.lower()
    prefixes = [f"{label.lower()}:", label.lower()]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            stripped = stripped[len(prefix):].strip(" :")
            break
    return stripped or str(text or "").strip()


def _render_quality_checks(
    *,
    skill_name: str,
    strategy_profile: dict[str, Any],
    plan: Any,
    program: SkillProgramIR,
    corpus: ExpertSkillCorpusEntry | None,
) -> list[str]:
    lines = ["## Quality Checks", ""]
    target_focus = str(strategy_profile.get("target_focus") or "")
    frontier_lines = _frontier_section_lines(
        skill_name=skill_name,
        target_focus=target_focus,
        section_name="Quality Checks",
    )
    gate_line = PROFILE_QUALITY_GATE_LINES.get(skill_name, "")
    strategy_name = str(strategy_profile.get("name") or "")
    if gate_line:
        lines.append(f"- Gate: {gate_line}")
    for item in frontier_lines[:2]:
        lines.append(f"- {item}")
    if skill_name == "simulation-resource-loop-design":
        grouped_checks = {
            "Visible Pressure": [
                "Check whether pressure is visible before commitment and early enough for planning.",
                "Check whether pressure relationships create readable tradeoffs instead of hidden bookkeeping.",
            ],
            "Costly Recovery": [
                "Check whether failure recovery keeps a cost instead of collapsing into a flat reset.",
                "Check whether recovery preserves consequence, readability, and fantasy at the same time.",
            ],
            "Dominant Currency Guard": [
                "Check whether one resource can bypass the intended tension web.",
                "Check whether positive and negative loops counterweight each other instead of feeding one dominant route.",
            ],
            "Fantasy Fit": [
                "Check whether emotional fantasy still matches the pressure math.",
                "Check whether every kept variable still changes player behavior inside the pressure web.",
            ],
        }
        for heading, items in grouped_checks.items():
            lines.extend([f"### {heading}"])
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
        return lines
    strategy_specific_check = ""
    if skill_name == "decision-loop-stress-test":
        strategy_specific_check = {
            "collapse_first_v2": "Check whether the first named collapse witness appears before phase explanation, pacing cover, or reward pacing.",
            "stop_condition_first_v2": "Check whether the stop condition names the specific collapse witness instead of only naming the phase boundary.",
            "fake_fix_rejection_v2": "Check whether the repair changes read, tradeoff, or consequence instead of only tuning numbers, widening rewards, widening content, or preserving the same dominant line.",
            "pressure_audit_v2": "Check whether the audit maps the wrong habit to the intended right habit, names the current reward loop, and states what player behavior must disappear instead of only praising faster throughput or keeping the same read.",
        }.get(strategy_name, "")
    for item in PROFILE_QUALITY_CHECK_LINES.get(skill_name, []):
        lines.append(f"- {item}")
    if strategy_specific_check:
        lines.append(f"- {strategy_specific_check}")
    if skill_name == "decision-loop-stress-test":
        lines.extend(
            [
                "- Hard fail variation named but same dominant line, same read, or same consequence under a new label.",
                "- Hard fail the same dominant line still wins under a new label, the same answer survives under a new label, the same read under a new label, or the same consequence under a new label.",
                "- Hard fail variation where reward, information, or cost changed in name only, the old answer still works, the old dominant line still pays, or the new answer never becomes correct.",
                "- Hard fail habit mapping named but reward loop unchanged, the reward loop currently trains the wrong habit, the wrong habit still pays, the replacement reward loop is unnamed, or replacement behavior never becomes optimal.",
                "- Hard fail solved-state repair named but decision landscape unchanged before balance values are tuned, the same dominant line still wins, the same read still solves, the same consequence structure still pays out, the old dominant line stays profitable, the old answer still works, or the new answer never becomes correct.",
            ]
        )
        for item in [
            "Check whether a named stop condition also includes a concrete collapse witness and a break point the player can observe.",
            "Check whether variation does not change decisions, keeps the same dominant line, preserves the same read under a new label, or never says why the old dominant line stops paying and why the new answer becomes correct.",
            "Check whether reinforcement names what reward loop currently trains the wrong behavior, what replacement reward loop makes the right habit profitable, and what replacement behavior must become optimal.",
            "Check whether solved-state repair says numeric-only tuning keeps the same dominant line, the same read, the same consequence structure, and the old dominant line profitable until the decision landscape rule changes.",
            "Check whether every repair recommendation names a structural fix instead of numeric-only tuning, content-only padding, pacing-only relief, or throughput-only mastery.",
        ]:
            lines.append(f"- {item}")
    lines.append("")
    return lines


def _failure_entries(
    *,
    skill_name: str,
    corpus: ExpertSkillCorpusEntry | None,
) -> list[tuple[str, str, str, str]]:
    entries = list(PROFILE_FAILURE_ENTRIES.get(skill_name, []))
    if entries:
        if skill_name == "decision-loop-stress-test":
            return [entry for entry in entries if entry[0] != "Progression Without New Problems" and entry[0] != "Stop Condition Without Witness"][:6]
        if skill_name == "simulation-resource-loop-design":
            return entries[:8]
        return entries[:5]
    if corpus is None:
        return []
    results: list[tuple[str, str, str, str]] = []
    for failure in list(corpus.failure_cases or [])[:6]:
        results.append(
            (
                str(failure.failure_type or "Failure").replace("-", " ").title(),
                str(failure.bad_output or "The output collapses into a generic answer."),
                str(failure.why_it_fails or "The workflow skipped the hard judgment."),
                str(failure.repair_direction or "Return to the workflow and make the decision explicit."),
            )
        )
    return results


def _render_output_fields(
    *,
    program: SkillProgramIR,
    labels: dict[str, str],
    strategy: str,
    strategy_profile: dict[str, Any],
) -> list[str]:
    target_focus = str(strategy_profile.get("target_focus") or "")
    frontier_lines = _frontier_section_lines(
        skill_name=program.skill_name,
        target_focus=target_focus,
        section_name="Output Format",
    )
    output_opening = {
        "concept-to-mvp-pack": "Fill the template so a greybox or cardboard first playable can be greenlit or killed without rereading the pitch deck, wireframe notes, or telemetry plan.",
        "decision-loop-stress-test": "Fill the template so the collapse point, solved state, and repair can be acted on immediately.",
        "simulation-resource-loop-design": "Fill the template so the pressure web, recovery cost, and fantasy fit stay visible in one pass.",
    }.get(program.skill_name, "Fill the template so the next decision is explicit, testable, and ready to act on.")
    if frontier_lines:
        output_opening = frontier_lines[0]
    fence_language = "text" if program.skill_name == "concept-to-mvp-pack" else "markdown"
    lines = ["## Output Format", "", output_opening]
    if program.skill_name == "concept-to-mvp-pack":
        lines.extend(
            [
                "",
                "Keep the field list explicit: validation goal, minimum honest loop, core features, minimum content scope, required systems, explicitly out of scope, main production risks, and build recommendation.",
            ]
        )
    lines.extend(["", f"```{fence_language}"])
    focus = [field for field in list(strategy_profile.get("output_focus") or []) if field in program.output_schema]
    ordered_fields = focus + [field for field in program.output_schema.keys() if field not in focus]
    quality_mode = str(strategy_profile.get("quality_mode") or "")
    concept_aliases = {
        "Core Validation Question": "validation goal with success criteria and failure evidence",
        "Smallest Honest Loop": "minimum honest loop with player input, system response, visible feedback, and repeat trigger",
        "Feature Cut": "core features, support, defer, and cut for now",
        "Minimum Content Package": "minimum content scope, required systems, and the prototype first target",
        "Out of Scope": "explicitly out of scope with re-entry condition",
        "MVP Package": "build recommendation, main production risks, and redesign trigger",
    }
    for field in ordered_fields:
        guidance_lines = program.output_schema.get(field, [])
        lines.append(f"## {field}")
        write_line = _strip_guidance_prefix(guidance_lines[0], labels["write"]) if guidance_lines else "<fill in>"
        if program.skill_name == "concept-to-mvp-pack":
            alias = concept_aliases.get(field, "")
            if alias and alias.lower() not in write_line.lower():
                write_line = f"{write_line.rstrip('.')}; keep the {alias} explicit."
        lines.append(f"- {labels['write']}: {write_line}")
        if program.skill_name == "simulation-resource-loop-design":
            compact_guardrail = {
                "Variable Web": "Keep only variables that change player behavior or reveal visible pressure.",
                "Pressure Relationships": "Show the cost, warning, and tradeoff before the player commits.",
                "Primary Decision Tensions": "Name what the player cannot maximize all at once.",
                "Positive and Negative Loops": "Show what compounds and what brakes it in the same read.",
                "Failure Recovery": "Keep recovery playable, but preserve cost and consequence.",
                "Emotional Fantasy Alignment": "Tie the intended feeling to the actual pressure math.",
            }.get(field, "")
            if compact_guardrail:
                lines.append(f"- Guardrail: {compact_guardrail}")
            lines.append("")
            continue
        if len(guidance_lines) > 1:
            lines.append(f"- {labels['good']}: {_strip_guidance_prefix(guidance_lines[1], labels['good'])}")
        if len(guidance_lines) > 2:
            lines.append(f"- {labels['weak']}: {_strip_guidance_prefix(guidance_lines[2], labels['weak'])}")
        if program.skill_name == "decision-loop-stress-test":
            decision_loop_guardrail = {
                "Solved State Risk": "Name the dominant strategy, the counterpressure, and the move that punishes repeated safe choices.",
                "Variation Quality": "Reject fake variation and keep only changes that alter read, tradeoff, consequence, or adaptation.",
                "Reinforcement Check": "State whether the loop teaches the wrong habit, throughput only, or the intended behavior under pressure.",
                "Reinforcement Recommendations": "Avoid shallow reward inflation; reward state-aware adaptation and change incentive structure instead.",
            }.get(field, "")
            if decision_loop_guardrail:
                lines.append(f"- Guardrail: {decision_loop_guardrail}")
        if field in focus:
            focus_note = {
                "proof_gate": "Make this field strong enough to prove or kill the first playable.",
                "scope_gate": "Make this field sharp enough to remove supportive scope without debate.",
                "build_gate": "Make this field handoff-ready so a builder can act immediately.",
                "pressure_gate": "Make this field sharp enough to expose where the loop breaks.",
                "collapse_gate": "Make this field show the exact collapse point or solved-state risk.",
                "repair_gate": "Make this field point to the structural repair, not extra content.",
                "mapping_gate": "Make this field reveal the pressure web instead of listing resources.",
                "tension_gate": "Make this field state the tradeoff the player can actually feel.",
                "balance_gate": "Make this field show how positive and negative loops stay in tension.",
                "recovery_gate": "Make this field preserve cost and consequence instead of flattening recovery.",
            }.get(quality_mode, "Keep this field sharp enough to drive the next decision.")
            lines.append(f"- Focus: {focus_note}")
        lines.append("")
    lines.extend(["```", ""])
    return lines


def _render_workflow(
    *,
    skill_name: str,
    program: SkillProgramIR,
    labels: dict[str, str],
    strategy: str,
    strategy_profile: dict[str, Any],
) -> list[str]:
    lines = ["## Default Workflow", ""]
    workflow_mode = str(strategy_profile.get("workflow_mode") or "")
    step_frame = str(strategy_profile.get("step_frame") or "")
    target_focus = str(strategy_profile.get("target_focus") or "")
    workflow_orders = {
        "validation_pressure": ["decision", "action", "output", "failure", "fix"],
        "cut_pressure": ["decision", "failure", "action", "output", "fix"],
        "package_readiness": ["decision", "output", "action", "failure", "fix"],
        "failure_pass": ["decision", "failure", "fix", "output", "action"],
        "collapse_first": ["decision", "failure", "action", "fix", "output"],
        "collapse_first_v2": ["decision", "failure", "action", "fix", "output"],
        "stop_condition_first": ["decision", "failure", "action", "output", "fix"],
        "stop_condition_first_v2": ["decision", "failure", "action", "output", "fix"],
        "fake_fix_rejection": ["decision", "fix", "failure", "output", "action"],
        "fake_fix_rejection_v2": ["decision", "fix", "failure", "output", "action"],
        "pressure_audit": ["decision", "action", "output", "fix", "failure"],
        "pressure_audit_v2": ["decision", "action", "output", "fix", "failure"],
        "map_first": ["decision", "action", "output", "failure", "fix"],
        "tension_first": ["decision", "failure", "action", "output", "fix"],
        "loop_balance": ["decision", "action", "output", "fix", "failure"],
        "recovery_cost": ["decision", "failure", "fix", "action", "output"],
    }
    step_openers = {
        "proof_gate": "Push this step until the loop earns the right to stay.",
        "scope_gate": "Use this step to remove anything that only makes the idea feel safer.",
        "handoff_gate": "Use this step to leave the next builder with a concrete pack, not a concept note.",
        "failure_pass": "Use this step to surface what would kill the MVP before more scope sneaks in.",
        "collapse_probe": "Use this step to find where the loop caves in or goes automatic.",
        "collapse_probe_v2": "Use this step to name the collapse witness before novelty, phase explanation, or pacing cover can hide it.",
        "stop_condition_probe": "Use this step to name the stop condition before the phase gets explained away.",
        "stop_condition_probe_v2": "Use this step to name the stop condition, the collapse witness, and the structural witness before the phase gets explained away.",
        "false_fix_gate": "Use this step to reject repairs that only add content, rewards, or softer compensation.",
        "false_fix_gate_v2": "Use this step to reject repairs that only add content, only tune numbers, or only soften failure.",
        "pressure_audit": "Use this step to check what behavior the system is actually teaching under pressure.",
        "pressure_audit_v2": "Use this step to map the wrong habit, the intended right habit, and the pressure that should separate them.",
        "map_probe": "Use this step to map the visible pressure before tuning any single variable.",
        "tension_probe": "Use this step to state the tradeoff before the loop gets smoothed over.",
        "loop_balance": "Use this step to prove the loop has both drive and restraint.",
        "recovery_cost": "Use this step to keep recovery meaningful instead of consequence-free.",
    }
    order = workflow_orders.get(workflow_mode, ["decision", "action", "output", "failure", "fix"])
    render_fields = {
        "decision": lambda move: f"   - {labels['decision']}: {move.decision}",
        "action": lambda move: f"   - {labels['action']}: {move.action}",
        "output": lambda move: f"   - {labels['output']}: {move.output}",
        "failure": lambda move: f"   - {labels['failure']}: {move.failure_signal}",
        "fix": lambda move: f"   - {labels['fix']}: {move.fix}",
    }
    if skill_name == "decision-loop-stress-test" and target_focus == "pressure":
        lines.extend(
            [
                "- Keep the audit on first-hour, midgame, late-game, solved state, dominant strategy, variation quality, reinforcement, and structural fixes.",
                "- Put the collapse signal, collapse witness, stop condition, break point, and structural witness before explanation, then reject surface excitement, first-hour novelty, not just phase explanation, and not just pacing cover.",
                "- Treat not MVP scope cutting and not detailed numeric balancing as guardrails, not excuses for a weak decision.",
                "- Keep weak decision, midgame autopilot, fake variation, shallow reward inflation, the same dominant line, and the same read visible enough to reject them as false fixes in the decision landscape, and state when reward, information, or cost changed in name only while the old answer still works.",
                "- Demand a repair recommendation with a structural fix that is not just numeric tuning, changes read, tradeoff, or consequence, names the dominant line, says what old answer stops working because of the reward, information, or cost shift, what new answer becomes correct because of that shift, what reward, information, or cost changed to cause that shift, why the old dominant line stops paying, how read changes because information changes, how tradeoff changes because cost changes, how consequence changes because reward changes, which reward loop currently trains the wrong habit, what player behavior must disappear, what wrong habit stops paying, what right habit should replace it, what replacement behavior must become optimal, what replacement reward loop makes that replacement behavior pay, and how the decision landscape rule changes before balance values are tuned before you call the loop fixed.",
                "",
            ]
        )
    for index, move in enumerate(program.execution_spine, start=1):
        decision_text = move.decision
        action_text = move.action
        extra_pressure_line = ""
        workflow_opener = step_openers.get(step_frame, "")
        if skill_name == "decision-loop-stress-test":
            if move.label == "Test Late-Game Expansion or Mutation":
                decision_text = "Test whether lategame mastery reveals a deeper problem or solves the game away."
            elif move.label == "Look for Solved States":
                decision_text = "Test which solved state a strong player would repeat until the loop becomes stale."
            elif move.label == "Audit Variation and Reinforcement":
                decision_text = "Test whether variation quality changes read, tradeoff, consequence, or adaptation."
                action_text = "Audit variation quality and reinforcement so the decision loop trains the intended behavior."
            if target_focus == "pressure":
                if move.label in {"Test the First-Hour Hook", "Test Midgame Sustainability"}:
                    decision_text = _append_sentence(decision_text, "Name the stop condition before proposing more content.")
                if move.label == "Test the First-Hour Hook":
                    extra_pressure_line = "   - Check: Reject surface excitement, first-hour novelty, and not greenlighting the loop if the first-hour pressure still hides a weak decision; name the collapse witness before phase explanation or pacing cover."
                elif move.label == "Test Midgame Sustainability":
                    action_text = _append_sentence(action_text, "Name the counterpressure, variation audit, read shift, tradeoff change, consequence change, why the old dominant line stops paying, and adaptation test before content gets added.")
                    extra_pressure_line = "   - Check: Name the dominant strategy, the midgame autopilot risk, the missing counterpressure, and whether the variation audit changes read, tradeoff, or consequence; if the same dominant line still wins, the same answer survives under a new label, the same read under a new label survives, the same consequence under a new label survives, the old answer still works, the new answer never becomes correct, or reward, information, or cost changed in name only while the old dominant line still pays, reject it as fake variation until a reward, information, or cost shift kills the old answer, the old dominant line stops paying, and a new answer becomes correct."
                elif move.label in {"Look for Solved States", "Audit Variation and Reinforcement"}:
                    action_text = _append_sentence(action_text, "Reject any fix that only widens content, only tunes numbers, only softens pacing, or keeps the same dominant line without changing pressure.")
                    if move.label == "Look for Solved States":
                        action_text = _append_sentence(action_text, "Name the landscape rule that changes before balance values are tuned and why numeric-only tuning leaves the old dominant line profitable.")
                        extra_pressure_line = "   - Check: Break the dominant strategy with a structural fix and repair recommendation, reject numeric-only tuning or content-only padding, call out when numeric-only tuning keeps the same dominant line still winning, the same read still solving, the same consequence structure still paying out, the old dominant line still profitable, or the old read still intact, and change the decision landscape rule before balance values are tuned so the old answer stops working before balance values are tuned and a new answer becomes correct."
                    else:
                        action_text = _append_sentence(action_text, "Call out variation that does not change decisions, keeps the same read, preserves the same dominant line, hides the missing behavior shift, or leaves the old dominant line paying under a renamed reward loop.")
                        extra_pressure_line = "   - Check: Reinforce the intended behavior, map wrong habit to right habit, name the behavior shift, say which reward loop currently trains the wrong habit, say what player behavior must disappear, say what replacement behavior must become optimal, say what replacement behavior becomes optimal because of the replacement reward logic, say what replacement reward loop makes the right habit profitable, reject fake variation, reject variation that does not change decisions, keeps the same dominant line still winning, keeps the same read, leaves the old answer working, or leaves the old behavior paying, and reject any repair that only improves throughput."
                elif move.label == "Test Late-Game Expansion or Mutation":
                    extra_pressure_line = "   - Check: Confirm late-game mastery creates a new decision problem instead of pure throughput, pacing cover, reward inflation, or a solved-state witness with no structural response and no right-habit replacement."
        elif skill_name == "simulation-resource-loop-design" and target_focus in {"leakage", "compactness"}:
            workflow_opener = {
                1: "Use this step to map the visible pressure before tuning any single variable.",
                2: "Use this step to give every kept variable a player-facing role.",
                3: "Use this step to expose cause, effect, and warning before commitment.",
                4: "Use this step to name the tradeoff the player cannot optimize away.",
                5: "Use this step to pair compounding force with a visible brake.",
                6: "Use this step to keep recovery costly without making it hopeless.",
                7: "Use this step to make the pressure web reinforce the intended fantasy.",
            }.get(index, workflow_opener)
            if move.label == "Map the Variable Web":
                extra_pressure_line = "   - Check: Confirm the pressure web is not just one simple currency with nicer labels."
        lines.append(f"{index}. **{move.label}**")
        if workflow_opener:
            lines.append(f"   - Frame: {workflow_opener}")
        for key in order:
            if key == "decision":
                lines.append(f"   - {labels['decision']}: {decision_text}")
            elif key == "action":
                lines.append(f"   - {labels['action']}: {action_text}")
            else:
                lines.append(render_fields[key](move))
        if extra_pressure_line:
            lines.append(extra_pressure_line)
        if strategy_profile.get("quality_tone") not in {"pressure", "collapse", "repair", "recovery_cost"} and move.must_include_terms:
            lines.append(f"   - Must include: {', '.join(move.must_include_terms[:5])}.")
        lines.append("")
    return lines


def _render_analysis_blocks(program: SkillProgramIR, strategy_profile: dict[str, Any]) -> list[str]:
    if not program.analysis_blocks:
        return []
    lines = ["## Analysis Blocks", ""]
    quality_tone = str(strategy_profile.get("quality_tone") or "")
    target_focus = str(strategy_profile.get("target_focus") or "")
    frontier_lines = _frontier_section_lines(
        skill_name=program.skill_name,
        target_focus=target_focus,
        section_name="Analysis Blocks",
    )
    for item in frontier_lines[:2]:
        lines.append(f"- {item}")
    lead_prefix = {
        "mapping": "Signal",
        "tension": "Tension",
        "balance": "Loop",
        "recovery_cost": "Recovery",
    }.get(quality_tone, "Focus")
    for block in program.analysis_blocks:
        lines.append(f"### {block.name}")
        lines.append(f"- {lead_prefix}: {block.questions[0] if block.questions else block.when_used}")
        if block.questions:
            for item in block.questions[1:2]:
                prefix = {
                    "tension": "Tradeoff",
                    "recovery_cost": "Cost",
                    "balance": "Counterweight",
                    "mapping": "Signal",
                }.get(quality_tone, "Check")
                lines.append(f"- {prefix}: {item}")
        if block.output_fields:
            lines.append(f"- Output: {', '.join(block.output_fields)}")
        lines.append("")
    return lines


def _render_candidate_markdown(
    *,
    program: SkillProgramIR,
    spec: SkillRealizationSpec,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
    strategy: str,
    strategy_profile: dict[str, Any],
) -> str:
    plan = build_domain_move_plan(skill_name=skill_name, task=task)
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    if plan is None:
        return ""
    labels = _surface_label_profile(skill_name)
    frontmatter_description = (
        PROFILE_FRONTMATTER_DESCRIPTIONS.get(skill_name)
        or (plan.opening_frame or program.opening_strategy or description or "").strip().splitlines()[0].strip()
    )
    lines = [
        "---",
        f"name: {skill_name}",
        f"description: {frontmatter_description}",
        "---",
        "",
        f"# {skill_name}",
        "",
        str(strategy_profile.get("opening_frame") or spec.opening_frame or program.opening_strategy or plan.opening_frame),
        "",
    ]
    for section_name in spec.section_order:
        if section_name == "Overview":
            lines.extend(["## Overview", ""])
            lines.extend(_section_variant_text(section_name=section_name, strategy=strategy, strategy_profile=strategy_profile, plan=plan, program=program, corpus=corpus))
            lines.extend([""])
        elif section_name == "Core Principle":
            lines.extend(["## Core Principle", ""])
            lines.extend(_section_variant_text(section_name=section_name, strategy=strategy, strategy_profile=strategy_profile, plan=plan, program=program, corpus=corpus))
            lines.extend([""])
        elif section_name == "When to Use":
            lines.extend(["## When to Use", ""])
            lines.extend(f"- {item}" for item in plan.when_to_use)
            lines.extend([""])
        elif section_name == "When Not to Use":
            lines.extend(["## When Not to Use", ""])
            lines.extend(f"- {item}" for item in plan.when_not_to_use)
            lines.extend([""])
        elif section_name == "Inputs":
            lines.extend(["## Inputs", ""])
            lines.extend(f"- {item}" for item in plan.inputs)
            lines.extend([""])
        elif section_name == "Default Workflow":
            lines.extend(_render_workflow(skill_name=skill_name, program=program, labels=labels, strategy=strategy, strategy_profile=strategy_profile))
        elif section_name == "Analysis Blocks":
            lines.extend(_render_analysis_blocks(program, strategy_profile))
        elif section_name == "Output Format":
            lines.extend(_render_output_fields(program=program, labels=labels, strategy=strategy, strategy_profile=strategy_profile))
        elif section_name == "Decision Rules":
            lines.extend(["## Decision Rules", ""])
            lines.extend(f"- {item}" for item in program.decision_rules)
            lines.extend([""])
        elif section_name == "Cut Rules":
            lines.extend(["## Cut Rules", ""])
            lines.extend(f"- {item}" for item in program.cut_rules)
            lines.extend([""])
        elif section_name == "Quality Checks":
            lines.extend(
                _render_quality_checks(
                    skill_name=skill_name,
                    strategy_profile=strategy_profile,
                    plan=plan,
                    program=program,
                    corpus=corpus,
                )
            )
        elif section_name == "Failure Patterns and Fixes":
            lines.extend([f"## Common Pitfalls: {labels['pitfalls']}", ""])
            intro_lines = _section_variant_text(section_name=section_name, strategy=strategy, strategy_profile=strategy_profile, plan=plan, program=program, corpus=corpus)
            lines.extend(intro_lines[:1])
            if intro_lines:
                lines.append("")
            pattern_names = [item.split(" -> ", 1)[0] for item in list(program.failure_repairs or [])]
            repair_moves = []
            for item in list(program.failure_repairs or []):
                _, _, fix = item.partition(" -> ")
                if fix and fix not in repair_moves:
                    repair_moves.append(fix)
            profile_preface = {
                "concept-to-mvp-pack": "Use these failure patterns to pressure-test the feature cut, out-of-scope line, and first playable package against scope creep, vertical slice drift, mood instead of loop, and content hiding uncertainty.",
                "decision-loop-stress-test": "Use these failure patterns to pressure-test lategame, variation quality, solved state, and reinforcement before adding content.",
                "simulation-resource-loop-design": "Use these failure patterns to check variable web clarity, pressure relationships, and failure recovery without collapsing into one simple currency, isolated meters, mostly content writing, or anything weaker than a few strong tensions; only include a variable if it changes player behavior.",
            }.get(skill_name, "")
            if profile_preface:
                lines.append(f"- {profile_preface}")
            if pattern_names:
                lines.append(f"- Pattern index: {', '.join(pattern_names)}.")
            if repair_moves:
                lines.append(f"- Repair moves: {', '.join(repair_moves)}.")
            if profile_preface or pattern_names or repair_moves:
                lines.append("")
            for title, symptom, cause, correction in _failure_entries(skill_name=skill_name, corpus=corpus):
                lines.append(f"### {title}")
                lines.append(f"- Symptom: {symptom}")
                lines.append(f"- Cause: {cause}")
                lines.append(f"- Correction: {correction}")
                if skill_name == "decision-loop-stress-test":
                    structural_pairs = {
                        "Variety Without Strategic Consequence": (
                            "Variation named, but the same dominant line still wins, the same answer survives under a new label, the same read survives under a new label, and the same consequence still survives under a new label.",
                            "Change reward, information, or cost so the old answer stops working because that shift kills the old answer, the old dominant line stops paying, a new answer becomes required, and the variation changes read, tradeoff, or consequence.",
                        ),
                        "Wrong Behavior Training": (
                            "A fake reinforcement loop keeps rewarding the same safe behavior, so the wrong habit survives, the wrong habit still pays, the reward loop currently trains the wrong habit, the old behavior still pays, and the review names the right habit without changing the reward logic.",
                            "Name the reward loop currently training the wrong habit, remove reward from that behavior, rewrite the replacement reward logic so the old behavior stops paying, and make the replacement behavior become optimal because the new pressure makes the right habit the profitable answer.",
                        ),
                        "Numeric-Only Repair": (
                            "Numeric-only fake fix: softer numbers still keep the same dominant line still winning, the same read still solving, the same consequence structure still paying out, and the old dominant line still profitable.",
                            "Structural replacement: change the decision landscape rule first so the old answer stops working before balance values are tuned, then tune balance values after the new answer becomes correct.",
                        ),
                    }
                    fake_version, structural_replacement = structural_pairs.get(title, ("", ""))
                    if fake_version:
                        lines.append(f"- Fake version: {fake_version}")
                    if structural_replacement:
                        lines.append(f"- Structural replacement: {structural_replacement}")
                lines.append("")
        elif section_name == "Worked Micro-Example":
            lines.extend(["## Worked Micro-Example", ""])
            if corpus is not None and corpus.expected_outputs:
                lines.extend(f"- {item}" for item in corpus.expected_outputs[:3])
            else:
                lines.append("- Use the workflow to produce a compact decision-facing output with explicit evidence and next action.")
            lines.extend([""])
        elif section_name == "Voice Rules":
            lines.extend(["## Voice Rules", ""])
            lines.extend(f"- {item}" for item in program.voice_constraints)
            lines.extend([""])
    if references:
        lines.extend(["## References", ""])
        lines.extend(f"- See `{path}` for supporting material." for path in references)
        lines.extend([""])
    if scripts:
        lines.extend(["## Helpers", ""])
        lines.extend(f"- Use `{path}` only when it directly supports this workflow." for path in scripts)
        lines.extend([""])
    return "\n".join(lines).rstrip() + "\n"


def build_skill_realization_candidates(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
    candidate_dna: ExpertSkillDNA | None = None,
) -> tuple[SkillProgramIR | None, SkillRealizationSpec | None, list[SkillRealizationCandidate]]:
    program = build_skill_program_ir(skill_name=skill_name, task=task, candidate_dna=candidate_dna)
    if program is None:
        return None, None, []
    spec = build_skill_realization_spec(skill_name=skill_name, task=task, program=program)
    residual_targets = _profile_residual_targets(skill_name)
    target_focus = _target_focus_for_skill(skill_name)
    frontier_bundle = _dual_baseline_bundle(skill_name)
    strategies = _pressure_strategy_family(skill_name, program.workflow_surface, list(spec.section_order or []))
    base_candidates: list[SkillRealizationCandidate] = []
    for index, strategy_profile in enumerate(strategies, start=1):
        strategy = str(strategy_profile.get("name") or f"variant_{index}")
        strategy_profile = dict(strategy_profile)
        strategy_profile["target_focus"] = target_focus
        strategy_profile["allowed_sections"] = ",".join(list(residual_targets.allowed_sections or []))
        strategy_profile["active_frontier_version"] = str(getattr(frontier_bundle, "active_frontier_version", "") or "")
        strategy_spec = _spec_for_strategy(base_spec=spec, strategy_profile=strategy_profile)
        base_candidates.append(
            SkillRealizationCandidate(
                candidate_id=f"{skill_name}:{strategy}:{index}",
                skill_name=skill_name,
                program_id=f"{skill_name}:{program.workflow_surface}",
                realization_strategy=strategy,
                strategy_family=str(strategy_spec.strategy_family or "pressure_first"),
                strategy_profile={
                    "compression_stage": "pre",
                    "opening_frame": str(strategy_profile.get("opening_frame") or ""),
                    "section_order": " > ".join(list(strategy_spec.section_order or [])),
                    "sentence_budget_profile": _strategy_budget_signature(strategy_profile),
                    "workflow_mode": str(strategy_profile.get("workflow_mode") or ""),
                    "step_frame": str(strategy_profile.get("step_frame") or ""),
                    "output_focus": ",".join(list(strategy_profile.get("output_focus") or [])),
                    "quality_tone": str(strategy_profile.get("quality_tone") or ""),
                    "quality_mode": str(strategy_profile.get("quality_mode") or ""),
                    "failure_style": str(strategy_profile.get("failure_style") or ""),
                    "failure_mode": str(strategy_profile.get("failure_mode") or ""),
                    "target_focus": str(strategy_profile.get("target_focus") or ""),
                    "allowed_sections": str(strategy_profile.get("allowed_sections") or ""),
                    "active_frontier_version": str(strategy_profile.get("active_frontier_version") or ""),
                },
                rendered_markdown=_render_candidate_markdown(
                    program=program,
                    spec=strategy_spec,
                    skill_name=skill_name,
                    description=description,
                    task=task,
                    references=references,
                    scripts=scripts,
                    strategy=strategy,
                    strategy_profile=strategy_profile,
                ),
                diagnostic_summary=[
                    f"strategy={strategy}",
                    f"workflow_surface={program.workflow_surface}",
                    f"workflow_mode={strategy_profile.get('workflow_mode', '')}",
                    f"quality_tone={strategy_profile.get('quality_tone', '')}",
                    f"failure_style={strategy_profile.get('failure_style', '')}",
                ],
            )
        )
    scored_base = [
        (
            candidate,
            _candidate_editorial_metrics(
                skill_name=skill_name,
                task=task,
                markdown=candidate.rendered_markdown,
                realization_candidate_count=len(base_candidates),
            ),
        )
        for candidate in base_candidates
    ]
    scored_base.sort(key=lambda item: _coverage_rank_key(skill_name, item[1]), reverse=True)
    compressed_candidates: list[SkillRealizationCandidate] = []
    for candidate, source_metrics in scored_base[:2]:
        compressed_candidate = _compress_candidate_sections(
            skill_name=skill_name,
            candidate=candidate,
            program=program,
        )
        compressed_metrics = _candidate_editorial_metrics(
            skill_name=skill_name,
            task=task,
            markdown=compressed_candidate.rendered_markdown,
            realization_candidate_count=len(base_candidates),
        )
        source_force = _primary_force_values(skill_name, source_metrics.get("editorial_force"))
        compressed_force = _primary_force_values(skill_name, compressed_metrics.get("editorial_force"))
        source_coverage = _coverage_values(source_metrics, skill_name)
        compressed_coverage = _coverage_values(compressed_metrics, skill_name)
        force_regressed = any(
            compressed_force.get(metric, 0.0) + 0.01 < source_force.get(metric, 0.0)
            for metric in _primary_force_metric_names(skill_name)
        )
        coverage_regressed = any(
            compressed_coverage.get(metric, 0.0) + 0.01 < source_coverage.get(metric, 0.0)
            for metric in _coverage_metric_names(skill_name)
        )
        if force_regressed or coverage_regressed:
            continue
        compressed_candidates.append(compressed_candidate)
    return program, spec, base_candidates + compressed_candidates


def _current_best_editorial_metrics(skill_name: str, task: str) -> dict[str, Any] | None:
    current_best = _current_best_markdown(skill_name)
    if not current_best.strip():
        return None
    return _candidate_editorial_metrics(
        skill_name=skill_name,
        task=task,
        markdown=current_best,
    )


def _primary_force_metric_names(skill_name: str) -> list[str]:
    return {
        "concept-to-mvp-pack": [
            "decision_pressure_score",
            "cut_sharpness_score",
            "boundary_rule_coverage",
            "output_executability_score",
        ],
        "decision-loop-stress-test": [
            "decision_pressure_score",
            "cut_sharpness_score",
            "failure_repair_force",
            "stop_condition_coverage",
        ],
        "simulation-resource-loop-design": [
            "decision_pressure_score",
            "failure_repair_force",
            "section_force_distinctness",
            "boundary_rule_coverage",
        ],
    }.get(
        skill_name,
        [
            "decision_pressure_score",
            "cut_sharpness_score",
            "failure_repair_force",
            "output_executability_score",
        ],
    )


def _primary_force_values(skill_name: str, editorial_force: SkillEditorialForceReport | None) -> dict[str, float]:
    if editorial_force is None:
        return {metric: 0.0 for metric in _primary_force_metric_names(skill_name)}
    return {
        metric: round(float(getattr(editorial_force, metric, 0.0) or 0.0), 4)
        for metric in _primary_force_metric_names(skill_name)
    }


def _candidate_rank_key(skill_name: str, metrics: dict[str, Any]) -> tuple[float, ...]:
    editorial_force = metrics.get("editorial_force")
    values = _primary_force_values(skill_name, editorial_force)
    ordered_primary = tuple(round(values.get(metric, 0.0), 4) for metric in _primary_force_metric_names(skill_name))
    return (
        *ordered_primary,
        round(float(getattr(editorial_force, "output_executability_score", 0.0) or 0.0), 4),
        round(float(getattr(editorial_force, "section_force_distinctness", 0.0) or 0.0), 4),
        round(max(0.0, 1.0 - float(getattr(metrics.get("editorial"), "redundancy_ratio", 0.0) or 0.0)), 4),
        round(float(metrics.get("score", 0.0) or 0.0), 4),
    )


def _coverage_metric_names(skill_name: str) -> list[str]:
    return {
        "concept-to-mvp-pack": [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
        "decision-loop-stress-test": [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
        "simulation-resource-loop-design": [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
    }.get(
        skill_name,
        [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
    )


def _compactness_metric_names(skill_name: str) -> list[str]:
    return {
        "concept-to-mvp-pack": [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
        "decision-loop-stress-test": [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
        "simulation-resource-loop-design": [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
    }.get(
        skill_name,
        [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
    )


def _coverage_values(metrics: dict[str, Any], skill_name: str) -> dict[str, float]:
    domain_expertise = metrics.get("domain_expertise")
    depth = metrics.get("depth")
    task_outcome = metrics.get("task_outcome")
    profile_result = next(iter(list(getattr(task_outcome, "profile_results", []) or [])), None) if task_outcome is not None else None
    values: dict[str, float] = {}
    for metric in _coverage_metric_names(skill_name):
        if metric in metrics:
            value = metrics.get(metric, 0.0)
        elif metric == "domain_move_coverage":
            value = getattr(domain_expertise, "domain_move_coverage", 0.0)
        elif metric == "section_depth_score":
            value = getattr(depth, "section_depth_score", 0.0)
        elif metric == "task_outcome_with_skill_average":
            value = getattr(profile_result, "with_skill_average", 0.0)
        else:
            value = 0.0
        values[metric] = round(float(value or 0.0), 4)
    return values


def _compactness_values(metrics: dict[str, Any], skill_name: str) -> dict[str, float]:
    editorial = metrics.get("editorial")
    style = metrics.get("style")
    values: dict[str, float] = {}
    for metric in _compactness_metric_names(skill_name):
        if metric in metrics:
            value = metrics.get(metric, 0.0)
        elif metric == "redundancy_ratio":
            value = getattr(editorial, "redundancy_ratio", 0.0)
        elif metric == "shared_opening_phrase_ratio":
            value = getattr(style, "shared_opening_phrase_ratio", 0.0)
        else:
            value = 0.0
        values[metric] = round(float(value or 0.0), 4)
    return values


def _coverage_rank_key(skill_name: str, metrics: dict[str, Any]) -> tuple[float, ...]:
    force_values = _primary_force_values(skill_name, metrics.get("editorial_force"))
    coverage_values = _coverage_values(metrics, skill_name)
    return (
        *tuple(round(coverage_values.get(metric, 0.0), 4) for metric in _coverage_metric_names(skill_name)),
        *tuple(round(force_values.get(metric, 0.0), 4) for metric in _primary_force_metric_names(skill_name)),
        round(float(getattr(metrics.get("editorial_force"), "compression_without_loss", 0.0) or 0.0), 4),
        round(float(metrics.get("score", 0.0) or 0.0), 4),
    )


def _normalize_probe_text(text: str) -> str:
    return " ".join(str(text or "").lower().replace("-", " ").split())


def _probe_term_coverage(text: str, terms: list[str]) -> float:
    if not terms:
        return 1.0
    normalized = _normalize_probe_text(text)
    hits = 0
    for term in terms:
        token = _normalize_probe_text(term)
        if token and token in normalized:
            hits += 1
    return round(hits / max(1, len(terms)), 4)


def _matching_probe_lines(text: str, *, terms: list[str], limit: int = 6) -> list[str]:
    normalized_terms = [_normalize_probe_text(term) for term in terms if _normalize_probe_text(term)]
    if not normalized_terms:
        return []
    matches: list[str] = []
    seen: set[str] = set()
    for raw_line in str(text or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        normalized_line = _normalize_probe_text(stripped.lstrip("-#* "))
        if any(term in normalized_line for term in normalized_terms):
            clean_line = stripped
            if clean_line not in seen:
                matches.append(clean_line)
                seen.add(clean_line)
        if len(matches) >= limit:
            break
    return matches


def _decision_loop_improvement_signal_groups(probe_id: str) -> list[list[str]]:
    signal_groups = {
        "decision.variation-without-read-change": [
            ["dominant line"],
            ["same read"],
            ["same consequence", "same consequence structure"],
            ["old answer stops working", "new answer becomes correct", "new answer is required"],
            ["same dominant line still wins", "same answer survives under a new label"],
            [
                "reward, information, or cost shift kills the old answer",
                "reward, information, or cost changed to kill the old answer",
            ],
        ],
        "decision.reinforcement-without-habit-mapping": [
            ["wrong habit"],
            ["right habit"],
            ["behavior shift", "replacement behavior", "player behavior must disappear"],
            ["reward loop", "replacement reward logic", "reward logic", "replacement behavior must become optimal"],
            ["wrong habit stops paying", "replacement reward logic"],
            ["right habit becomes the profitable answer", "replacement behavior becomes optimal because"],
        ],
        "decision.solved-state-numeric-only-repair": [
            ["not just numeric tuning"],
            ["same dominant line"],
            ["same read"],
            ["same consequence", "same consequence structure"],
            ["decision landscape"],
            ["same dominant line still wins"],
            ["same read still solves"],
            [
                "decision landscape changes before balance values are tuned",
                "change the decision landscape before balance values are tuned",
            ],
        ],
    }
    return signal_groups.get(probe_id, [])


def _probe_signal_group_hit_count(text: str, signal_groups: list[list[str]]) -> int:
    if not signal_groups:
        return 0
    normalized = _normalize_probe_text(text)
    hits = 0
    for group in signal_groups:
        normalized_group = [_normalize_probe_text(term) for term in group if _normalize_probe_text(term)]
        if any(token in normalized for token in normalized_group):
            hits += 1
    return hits


def _canonical_probe_section_name(section_name: str) -> str:
    heading = str(section_name or "").strip()
    if heading.startswith("Common Pitfalls:"):
        return "Failure Patterns and Fixes"
    return heading


def _markdown_section_bodies(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_section = ""
    for raw_line in str(text or "").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current_section = _canonical_probe_section_name(stripped[3:].strip())
            sections.setdefault(current_section, [])
            continue
        if current_section:
            sections.setdefault(current_section, []).append(raw_line)
    return {
        name: "\n".join(lines).strip()
        for name, lines in sections.items()
    }


def _decision_loop_section_improvement_bundles(
    probe_id: str,
    *,
    mode: str = "probe_expanded_v7",
) -> dict[str, list[list[str]]]:
    bundles_v7 = {
        "decision.variation-without-read-change": {
            "Default Workflow": [
                ["dominant line"],
                ["old answer stops working"],
                ["new answer becomes correct", "new answer is required"],
                ["reward, information, or cost changed", "reward, information, or cost shift"],
                ["old answer stops working because", "new answer becomes correct because"],
            ],
            "Quality Checks": [
                ["variation named but same dominant line"],
                ["same read", "same consequence", "same consequence structure"],
                ["same dominant line still wins", "same answer survives under a new label"],
            ],
            "Failure Patterns and Fixes": [
                ["fake variation"],
                ["structural replacement"],
                ["same dominant line still wins under a new label", "same answer survives under a new label"],
            ],
        },
        "decision.reinforcement-without-habit-mapping": {
            "Default Workflow": [
                ["wrong habit"],
                ["right habit"],
                ["reward loop currently trains"],
                ["behavior shift"],
                ["replacement reward logic", "wrong habit stops paying"],
            ],
            "Quality Checks": [
                ["habit mapping named but reward loop unchanged"],
                ["wrong habit still pays", "replacement behavior never becomes optimal"],
            ],
            "Failure Patterns and Fixes": [
                ["fake reinforcement loop"],
                ["structural replacement"],
                ["replacement reward logic", "wrong habit still pays"],
            ],
        },
        "decision.solved-state-numeric-only-repair": {
            "Default Workflow": [
                ["not just numeric tuning"],
                ["same dominant line"],
                ["same read"],
                ["same consequence structure", "same consequence"],
                ["decision landscape"],
                ["same dominant line still wins", "same read still solves"],
            ],
            "Quality Checks": [
                ["numeric only", "content only", "pacing only", "throughput only"],
                ["decision landscape unchanged"],
                ["same dominant line still wins", "same read still solves", "same consequence structure still pays out"],
            ],
            "Failure Patterns and Fixes": [
                ["numeric only fake fix"],
                ["structural replacement"],
                ["same dominant line still wins", "same consequence structure still pays out"],
            ],
        },
    }
    bundles_v8 = {
        "decision.variation-without-read-change": {
            "Default Workflow": [
                ["dominant line"],
                ["old answer stops working"],
                ["new answer becomes correct", "new answer is required"],
                ["reward, information, or cost changed", "reward, information, or cost shift"],
                ["old answer stops working because", "new answer becomes correct because"],
                ["reward, information, or cost shift kills the old answer", "reward, information, or cost changed to kill the old answer"],
            ],
            "Quality Checks": [
                ["variation named but same dominant line"],
                ["same read", "same consequence", "same consequence structure"],
                ["same dominant line still wins", "same answer survives under a new label"],
                ["same read under a new label", "same consequence under a new label"],
            ],
            "Failure Patterns and Fixes": [
                ["fake variation"],
                ["structural replacement"],
                ["same dominant line still wins under a new label", "same answer survives under a new label"],
                ["reward, information, or cost shift kills the old answer", "new answer becomes correct because"],
            ],
        },
        "decision.reinforcement-without-habit-mapping": {
            "Default Workflow": [
                ["wrong habit"],
                ["right habit"],
                ["reward loop currently trains"],
                ["behavior shift"],
                ["replacement reward logic", "wrong habit stops paying"],
                ["right habit becomes the profitable answer", "replacement behavior becomes optimal because"],
            ],
            "Quality Checks": [
                ["habit mapping named but reward loop unchanged"],
                ["wrong habit still pays", "replacement behavior never becomes optimal"],
                ["reward loop currently trains the wrong habit", "replacement reward logic never changes"],
            ],
            "Failure Patterns and Fixes": [
                ["fake reinforcement loop"],
                ["structural replacement"],
                ["replacement reward logic", "wrong habit still pays"],
                ["right habit becomes the profitable answer", "replacement behavior becomes optimal because"],
            ],
        },
        "decision.solved-state-numeric-only-repair": {
            "Default Workflow": [
                ["not just numeric tuning"],
                ["same dominant line"],
                ["same read"],
                ["same consequence structure", "same consequence"],
                ["decision landscape"],
                ["same dominant line still wins", "same read still solves"],
                [
                    "decision landscape changes before balance values are tuned",
                    "change the decision landscape before balance values are tuned",
                ],
            ],
            "Quality Checks": [
                ["numeric only", "content only", "pacing only", "throughput only"],
                ["decision landscape unchanged"],
                ["same dominant line still wins", "same read still solves", "same consequence structure still pays out"],
                [
                    "decision landscape unchanged before balance values are tuned",
                    "same consequence structure still pays out",
                ],
            ],
            "Failure Patterns and Fixes": [
                ["numeric only fake fix"],
                ["structural replacement"],
                ["same dominant line still wins", "same consequence structure still pays out"],
                [
                    "decision landscape changes before balance values are tuned",
                    "old answer stops working before balance values are tuned",
                ],
            ],
        },
    }
    bundles_v9 = {
        "decision.variation-without-read-change": {
            "Default Workflow": [
                ["dominant line"],
                ["old answer stops working"],
                ["new answer becomes correct", "new answer is required"],
                ["reward, information, or cost changed", "reward, information, or cost shift"],
                ["old answer stops working because", "what old answer stops working"],
                ["new answer becomes correct because", "what new answer becomes correct"],
                [
                    "what reward, information, or cost changed to cause that shift",
                    "reward, information, or cost shift causes that change",
                ],
            ],
            "Quality Checks": [
                ["variation named but same dominant line"],
                ["same read", "same consequence", "same consequence structure"],
                ["same dominant line still wins", "same answer survives under a new label"],
                ["same read under a new label", "same consequence under a new label"],
            ],
            "Failure Patterns and Fixes": [
                ["fake variation"],
                ["structural replacement"],
                ["same dominant line still wins under a new label", "same answer survives under a new label"],
                ["reward, information, or cost shift kills the old answer", "new answer becomes correct because"],
                ["old answer stops working because", "new answer is required"],
            ],
        },
        "decision.reinforcement-without-habit-mapping": {
            "Default Workflow": [
                ["wrong habit"],
                ["right habit"],
                ["reward loop currently trains"],
                ["behavior shift"],
                ["what player behavior must disappear", "wrong habit disappears"],
                ["what replacement behavior must become optimal", "right habit becomes optimal"],
                ["replacement reward logic", "replacement behavior becomes optimal because"],
                [
                    "what reward, information, or cost shift causes that behavior shift",
                    "reward, information, or cost shift causes that behavior shift",
                ],
            ],
            "Quality Checks": [
                ["habit mapping named but reward loop unchanged"],
                ["wrong habit still pays", "replacement behavior never becomes optimal"],
                ["reward loop currently trains the wrong habit", "replacement reward logic never changes"],
            ],
            "Failure Patterns and Fixes": [
                ["fake reinforcement loop"],
                ["structural replacement"],
                ["replacement reward logic", "wrong habit still pays"],
                ["right habit becomes the profitable answer", "replacement behavior becomes optimal because"],
                ["what player behavior must disappear", "what replacement behavior must become optimal"],
            ],
        },
        "decision.solved-state-numeric-only-repair": {
            "Default Workflow": [
                ["not just numeric tuning"],
                ["same dominant line"],
                ["same read"],
                ["same consequence structure", "same consequence"],
                ["decision landscape"],
                ["same dominant line still wins", "same read still solves"],
                [
                    "decision landscape changes before balance values are tuned",
                    "change the decision landscape before balance values are tuned",
                ],
                [
                    "old answer stops working before balance values are tuned",
                    "new answer becomes correct after the decision landscape changes",
                ],
            ],
            "Quality Checks": [
                ["numeric only", "content only", "pacing only", "throughput only"],
                ["decision landscape unchanged"],
                ["same dominant line still wins", "same read still solves", "same consequence structure still pays out"],
                [
                    "decision landscape unchanged before balance values are tuned",
                    "same consequence structure still pays out",
                ],
                ["old answer still works", "new answer never becomes correct"],
            ],
            "Failure Patterns and Fixes": [
                ["numeric only fake fix"],
                ["structural replacement"],
                ["same dominant line still wins", "same consequence structure still pays out"],
                [
                    "decision landscape changes before balance values are tuned",
                    "old answer stops working before balance values are tuned",
                ],
                ["same read still solves", "new answer becomes correct after the landscape shifts"],
            ],
        },
    }
    bundles_v10 = {
        "decision.variation-without-read-change": {
            "Default Workflow": [
                ["dominant line"],
                ["old answer stops working", "old answer stops working because"],
                ["new answer becomes correct", "new answer is required"],
                ["reward, information, or cost changed", "reward, information, or cost shift"],
                ["why the old dominant line stops paying", "old dominant line stops paying"],
                ["read changes because information changes", "tradeoff changes because cost changes", "consequence changes because reward changes"],
            ],
            "Quality Checks": [
                ["variation named but same dominant line"],
                ["same read", "same consequence", "same consequence structure"],
                ["reward, information, or cost changed in name only"],
                ["old answer still works", "new answer never becomes correct"],
            ],
            "Failure Patterns and Fixes": [
                ["fake variation"],
                ["structural replacement"],
                ["old answer still works", "same answer survives under a new label"],
                ["old dominant line stops paying", "new answer becomes correct"],
            ],
        },
        "decision.reinforcement-without-habit-mapping": {
            "Default Workflow": [
                ["wrong habit"],
                ["right habit"],
                ["reward loop currently trains"],
                ["what player behavior must disappear", "wrong habit disappears"],
                ["what replacement behavior must become optimal", "right habit becomes optimal"],
                ["replacement reward loop", "replacement reward logic"],
                ["reward, information, or cost shift causes that behavior shift", "behavior shift"],
            ],
            "Quality Checks": [
                ["habit mapping named but reward loop unchanged"],
                ["wrong habit still pays", "old behavior still pays"],
                ["replacement behavior never becomes optimal", "replacement reward logic never changes"],
            ],
            "Failure Patterns and Fixes": [
                ["fake reinforcement loop"],
                ["structural replacement"],
                ["old behavior still pays", "wrong habit still pays"],
                ["replacement reward loop", "replacement behavior becomes optimal"],
            ],
        },
        "decision.solved-state-numeric-only-repair": {
            "Default Workflow": [
                ["not just numeric tuning"],
                ["same dominant line"],
                ["same read"],
                ["same consequence structure", "same consequence"],
                ["decision landscape"],
                ["decision landscape rule changes before balance values are tuned", "decision landscape changes before balance values are tuned"],
                ["old answer stops working before balance values are tuned", "same dominant line still wins"],
            ],
            "Quality Checks": [
                ["numeric only", "content only", "pacing only", "throughput only"],
                ["decision landscape unchanged"],
                ["same dominant line still wins", "same read still solves"],
                ["same consequence structure still pays out", "old answer still works"],
            ],
            "Failure Patterns and Fixes": [
                ["numeric only fake fix"],
                ["structural replacement"],
                ["same dominant line still wins", "same consequence structure still pays out"],
                ["decision landscape rule changes before balance values are tuned", "old answer stops working before balance values are tuned"],
            ],
        },
    }
    bundle_by_mode = {
        "probe_expanded_v7": bundles_v7,
        "probe_expanded_v8": bundles_v8,
        "probe_expanded_v9": bundles_v9,
        "probe_expanded_v10": bundles_v10,
    }
    return bundle_by_mode.get(mode, {}).get(probe_id, {})


def _probe_section_bundle_hit_count(text: str, section_bundles: dict[str, list[list[str]]]) -> int:
    if not section_bundles:
        return 0
    section_bodies = _markdown_section_bodies(text)
    hits = 0
    for section_name, signal_groups in section_bundles.items():
        section_body = section_bodies.get(section_name, "")
        if (
            section_body
            and _probe_signal_group_hit_count(section_body, signal_groups) == len(signal_groups)
        ):
            hits += 1
    return hits


def _decision_loop_causal_alignment_families(
    probe_id: str,
    *,
    mode: str = "probe_expanded_v10",
) -> dict[str, dict[str, list[list[str]]]]:
    if mode != "probe_expanded_v10":
        return {}
    families = {
        "decision.variation-without-read-change": {
            "old_answer_chain": {
                "Default Workflow": [
                    ["old answer stops working", "old answer stops working because"],
                    ["old dominant line stops paying", "why the old dominant line stops paying"],
                ],
                "Quality Checks": [
                    ["variation named but same dominant line"],
                    ["same read", "same consequence", "same consequence structure"],
                ],
                "Failure Patterns and Fixes": [
                    ["fake variation"],
                    ["old answer still works", "same answer survives under a new label"],
                ],
            },
            "new_answer_chain": {
                "Default Workflow": [
                    ["new answer becomes correct", "new answer is required"],
                    ["reward, information, or cost changed", "reward, information, or cost shift"],
                ],
                "Failure Patterns and Fixes": [
                    ["structural replacement"],
                    ["new answer becomes correct", "new answer becomes required", "new answer is required"],
                ],
            },
            "cause_shift_chain": {
                "Default Workflow": [
                    ["reward, information, or cost changed", "reward, information, or cost shift"],
                    ["read changes because information changes", "tradeoff changes because cost changes", "consequence changes because reward changes"],
                ],
                "Quality Checks": [
                    ["reward, information, or cost changed in name only"],
                    ["old answer still works", "new answer never becomes correct"],
                ],
                "Failure Patterns and Fixes": [
                    ["structural replacement"],
                    ["old dominant line stops paying", "old answer stops working"],
                ],
            },
        },
        "decision.reinforcement-without-habit-mapping": {
            "wrong_habit_chain": {
                "Default Workflow": [
                    ["wrong habit"],
                    ["reward loop currently trains"],
                ],
                "Quality Checks": [
                    ["habit mapping named but reward loop unchanged"],
                    ["wrong habit still pays", "old behavior still pays"],
                ],
                "Failure Patterns and Fixes": [
                    ["fake reinforcement loop"],
                    ["wrong habit still pays", "old behavior still pays"],
                ],
            },
            "right_habit_chain": {
                "Default Workflow": [
                    ["right habit"],
                    ["what replacement behavior must become optimal", "right habit becomes optimal"],
                    ["replacement reward loop", "replacement reward logic"],
                ],
                "Failure Patterns and Fixes": [
                    ["structural replacement"],
                    ["replacement behavior becomes optimal", "right habit becomes the profitable answer"],
                ],
            },
            "behavior_shift_chain": {
                "Default Workflow": [
                    ["reward, information, or cost shift causes that behavior shift", "behavior shift"],
                    ["what player behavior must disappear", "wrong habit disappears"],
                ],
                "Quality Checks": [
                    ["replacement behavior never becomes optimal", "replacement reward logic never changes"],
                ],
                "Failure Patterns and Fixes": [
                    ["structural replacement"],
                    ["replacement reward loop", "replacement reward logic"],
                ],
            },
        },
        "decision.solved-state-numeric-only-repair": {
            "same_solution_chain": {
                "Default Workflow": [
                    ["not just numeric tuning"],
                    ["same dominant line"],
                    ["same read"],
                    ["same consequence structure", "same consequence"],
                ],
                "Quality Checks": [
                    ["same dominant line still wins", "same read still solves"],
                    ["same consequence structure still pays out", "old answer still works"],
                ],
                "Failure Patterns and Fixes": [
                    ["numeric only fake fix"],
                    ["same dominant line still wins", "same consequence structure still pays out"],
                ],
            },
            "landscape_first_chain": {
                "Default Workflow": [
                    ["decision landscape"],
                    ["decision landscape rule changes before balance values are tuned", "decision landscape changes before balance values are tuned"],
                ],
                "Quality Checks": [
                    ["decision landscape unchanged"],
                ],
                "Failure Patterns and Fixes": [
                    ["structural replacement"],
                    ["decision landscape rule changes before balance values are tuned", "old answer stops working before balance values are tuned"],
                ],
            },
            "ordering_chain": {
                "Default Workflow": [
                    ["old answer stops working before balance values are tuned", "decision landscape changes before balance values are tuned"],
                ],
                "Quality Checks": [
                    ["numeric only", "content only", "pacing only", "throughput only"],
                ],
                "Failure Patterns and Fixes": [
                    ["structural replacement"],
                    ["old answer stops working before balance values are tuned"],
                ],
            },
        },
    }
    return families.get(probe_id, {})


def _probe_cross_section_family_hit_count(
    text: str,
    section_families: dict[str, dict[str, list[list[str]]]],
) -> int:
    if not section_families:
        return 0
    section_bodies = _markdown_section_bodies(text)
    hits = 0
    for requirements in section_families.values():
        family_hit = True
        for section_name, signal_groups in requirements.items():
            section_body = section_bodies.get(section_name, "")
            if (
                not section_body
                or _probe_signal_group_hit_count(section_body, signal_groups) != len(signal_groups)
            ):
                family_hit = False
                break
        if family_hit:
            hits += 1
    return hits


def _decision_loop_outcome_probe_specs(*, mode: str = "frontier_v3") -> list[dict[str, Any]]:
    base_specs = [
        {
            "probe_id": "decision.novelty-masks-weak-choice",
            "pressure_terms": [
                "first hour novelty",
                "weak decision",
                "collapse signal",
                "stop condition",
                "surface excitement",
            ],
            "false_fix_terms": [
                "not greenlighting",
                "more content",
                "structural fixes",
                "decision problem",
            ],
        },
        {
            "probe_id": "decision.midgame-autopilot",
            "pressure_terms": [
                "midgame autopilot",
                "dominant strategy",
                "counterpressure",
                "adaptation",
            ],
            "false_fix_terms": [
                "content padding",
                "not detailed numeric balancing",
                "structural fixes",
                "pressure",
            ],
        },
        {
            "probe_id": "decision.fake-repair-by-content",
            "pressure_terms": [
                "collapse signal",
                "solved state",
                "decision landscape",
                "structural fixes",
            ],
            "false_fix_terms": [
                "reject any fix that only",
                "more content",
                "reward inflation",
                "softer compensation",
            ],
        },
        {
            "probe_id": "decision.mastery-throughput-only",
            "pressure_terms": [
                "mastery",
                "throughput",
                "new decision problem",
                "reinforcement",
            ],
            "false_fix_terms": [
                "wrong habit",
                "fake variation",
                "repair",
                "pressure",
            ],
        },
    ]
    if mode not in {"probe_expanded_v4", "probe_expanded_v7", "probe_expanded_v8", "probe_expanded_v9", "probe_expanded_v10"}:
        return base_specs
    expanded_specs = base_specs + [
        {
            "probe_id": "decision.solved-state-numeric-only-repair",
            "pressure_terms": [
                "solved state",
                "collapse witness",
                "repair recommendation",
                "decision landscape",
            ],
            "false_fix_terms": [
                "not just numeric tuning",
                "structural fix",
                "same read",
                "same dominant line",
            ],
        },
        {
            "probe_id": "decision.variation-without-read-change",
            "pressure_terms": [
                "variation audit",
                "read",
                "tradeoff",
                "consequence",
            ],
            "false_fix_terms": [
                "fake variation",
                "does not change decisions",
                "same dominant line",
                "same read",
            ],
        },
        {
            "probe_id": "decision.reinforcement-without-habit-mapping",
            "pressure_terms": [
                "reinforcement",
                "wrong habit",
                "right habit",
                "intended behavior",
            ],
            "false_fix_terms": [
                "throughput only",
                "wrong behavior",
                "wrong habit to right habit",
                "behavior shift",
            ],
        },
        {
            "probe_id": "decision.stop-condition-without-collapse-witness",
            "pressure_terms": [
                "stop condition",
                "collapse witness",
                "break point",
                "solved state risk",
            ],
            "false_fix_terms": [
                "phase explanation",
                "pacing cover",
                "not just more content",
                "structural witness",
            ],
        },
    ]
    if mode in {"probe_expanded_v7", "probe_expanded_v8", "probe_expanded_v9", "probe_expanded_v10"}:
        for spec in expanded_specs:
            probe_id = str(spec.get("probe_id") or "")
            if probe_id == "decision.variation-without-read-change":
                spec["pressure_terms"] = list(spec["pressure_terms"]) + [
                    "old answer stops working because",
                    "new answer becomes correct because",
                    "old dominant line stops paying",
                    "reward, information, or cost changed in name only",
                ]
                spec["false_fix_terms"] = list(spec["false_fix_terms"]) + [
                    "same dominant line still wins",
                    "reward, information, or cost shift kills the old answer",
                    "new answer never becomes correct",
                ]
            elif probe_id == "decision.reinforcement-without-habit-mapping":
                spec["pressure_terms"] = list(spec["pressure_terms"]) + [
                    "reward loop currently trains",
                    "replacement reward logic",
                    "replacement reward loop",
                    "old behavior still pays",
                ]
                spec["false_fix_terms"] = list(spec["false_fix_terms"]) + [
                    "wrong habit stops paying",
                    "right habit becomes the profitable answer",
                    "replacement behavior must become optimal",
                ]
            elif probe_id == "decision.solved-state-numeric-only-repair":
                spec["pressure_terms"] = list(spec["pressure_terms"]) + [
                    "same dominant line still wins",
                    "same read still solves",
                    "old dominant line still profitable",
                ]
                spec["false_fix_terms"] = list(spec["false_fix_terms"]) + [
                    "same consequence structure still pays out",
                    "decision landscape changes before balance values are tuned",
                    "decision landscape rule changes before balance values are tuned",
                ]
    return expanded_specs


def _decision_loop_probe_expanded_ready(
    report: OutcomeOnlyRerankerReport | None,
    *,
    required_probe_count: int = 8,
    required_improved_probe_count: int = 2,
) -> bool:
    if report is None:
        return False
    return (
        report.status == "pass"
        and report.probe_count >= required_probe_count
        and report.probe_pass_count >= required_probe_count
        and report.frontier_comparison_status == "beaten"
        and report.improved_probe_count >= required_improved_probe_count
    )


def _decision_loop_probe_clean_pass(
    report: OutcomeOnlyRerankerReport | None,
    *,
    required_probe_count: int = 8,
) -> bool:
    if report is None:
        return False
    return (
        report.status == "pass"
        and report.probe_count >= required_probe_count
        and report.probe_pass_count >= required_probe_count
        and report.blocked_probe_count == 0
    )


def _decision_loop_probe_expanded_v4_ready(
    report: OutcomeOnlyRerankerReport | None,
    *,
    required_probe_count: int = 8,
    required_improved_probe_count: int = 2,
) -> bool:
    return _decision_loop_probe_expanded_ready(
        report,
        required_probe_count=required_probe_count,
        required_improved_probe_count=required_improved_probe_count,
    )


def _build_outcome_only_reranker_report(
    *,
    skill_name: str,
    scored_candidates: list[tuple[SkillRealizationCandidate, dict[str, Any]]],
    probe_mode: str = "frontier_v3",
) -> OutcomeOnlyRerankerReport | None:
    if skill_name != "decision-loop-stress-test":
        return None
    frontier_markdown = _current_best_markdown(skill_name)
    if not frontier_markdown.strip():
        return OutcomeOnlyRerankerReport(
            skill_name=skill_name,
            probe_mode=probe_mode,
            status="not_applicable",
            frontier_comparison_status="missing_current_best",
            blocking_reason="missing_current_best",
            summary=["outcome_only_reranker_skipped=missing_current_best"],
        )
    frontier_metrics = _candidate_editorial_metrics(
        skill_name=skill_name,
        task="frontier_outcome_only",
        markdown=frontier_markdown,
        realization_candidate_count=0,
    )
    frontier_redundancy = float(getattr(frontier_metrics.get("editorial"), "redundancy_ratio", 0.0) or 0.0)
    frontier_compression = round(max(0.0, 1.0 - frontier_redundancy), 4)
    probe_specs = _decision_loop_outcome_probe_specs(mode=probe_mode)
    ranking_rows: list[tuple[str, int, int, float, float, float, float, float, float]] = []
    winner_probe_scores: list[OutcomeOnlyProbeScore] = []
    winner_matched_probe_ids: list[str] = []
    winner_improved_probe_ids: list[str] = []
    winner_blocked_probe_ids: list[str] = []
    winner_repair_evidence_lines: list[str] = []
    winner_collapse_evidence_lines: list[str] = []
    winner_probe_witness_summary: list[str] = []
    winner_repair_specificity_score = 0.0
    winner_probe_evidence_density = 0.0
    winner_collapse_witness_coverage = 0.0
    for candidate, metrics in scored_candidates:
        candidate_redundancy = float(getattr(metrics.get("editorial"), "redundancy_ratio", 0.0) or 0.0)
        candidate_compression = round(max(0.0, 1.0 - candidate_redundancy), 4)
        probe_scores: list[OutcomeOnlyProbeScore] = []
        pass_count = 0
        improved_probe_count = 0
        matched_probe_ids: list[str] = []
        improved_probe_ids: list[str] = []
        blocked_probe_ids: list[str] = []
        total_candidate_score = 0.0
        total_pressure_delta = 0.0
        total_false_fix_delta = 0.0
        total_compression_delta = 0.0
        for spec in probe_specs:
            candidate_pressure = _probe_term_coverage(candidate.rendered_markdown, list(spec.get("pressure_terms") or []))
            frontier_pressure = _probe_term_coverage(frontier_markdown, list(spec.get("pressure_terms") or []))
            candidate_false_fix = _probe_term_coverage(candidate.rendered_markdown, list(spec.get("false_fix_terms") or []))
            frontier_false_fix = _probe_term_coverage(frontier_markdown, list(spec.get("false_fix_terms") or []))
            probe_id = str(spec.get("probe_id") or "")
            signal_groups = _decision_loop_improvement_signal_groups(probe_id)
            section_bundles = (
                _decision_loop_section_improvement_bundles(probe_id, mode=probe_mode)
                if probe_mode in {"probe_expanded_v7", "probe_expanded_v8", "probe_expanded_v9", "probe_expanded_v10"}
                else {}
            )
            causal_alignment_families = (
                _decision_loop_causal_alignment_families(probe_id, mode=probe_mode)
                if probe_mode == "probe_expanded_v10"
                else {}
            )
            candidate_signal_hits = _probe_signal_group_hit_count(candidate.rendered_markdown, signal_groups)
            frontier_signal_hits = _probe_signal_group_hit_count(frontier_markdown, signal_groups)
            candidate_section_bundle_hits = _probe_section_bundle_hit_count(candidate.rendered_markdown, section_bundles)
            frontier_section_bundle_hits = _probe_section_bundle_hit_count(frontier_markdown, section_bundles)
            candidate_alignment_hits = _probe_cross_section_family_hit_count(candidate.rendered_markdown, causal_alignment_families)
            frontier_alignment_hits = _probe_cross_section_family_hit_count(frontier_markdown, causal_alignment_families)
            candidate_score = round((0.50 * candidate_pressure) + (0.35 * candidate_false_fix) + (0.15 * candidate_compression), 4)
            frontier_score = round((0.50 * frontier_pressure) + (0.35 * frontier_false_fix) + (0.15 * frontier_compression), 4)
            pressure_delta = round(candidate_pressure - frontier_pressure, 4)
            false_fix_delta = round(candidate_false_fix - frontier_false_fix, 4)
            compression_delta = round(candidate_compression - frontier_compression, 4)
            probe_improved_by_score = (
                (
                    candidate_score > frontier_score + 0.02
                    and pressure_delta >= 0.0
                    and false_fix_delta >= 0.0
                )
                or (
                    bool(signal_groups)
                    and candidate_score + 0.02 >= frontier_score
                    and candidate_pressure + 0.01 >= frontier_pressure
                    and candidate_false_fix + 0.01 >= frontier_false_fix
                    and candidate_signal_hits == len(signal_groups)
                    and candidate_signal_hits > frontier_signal_hits
                )
            )
            probe_matched = (
                not probe_improved_by_score
                and candidate_score + 0.02 >= frontier_score
                and candidate_pressure + 0.01 >= frontier_pressure
                and candidate_false_fix + 0.01 >= frontier_false_fix
                and max(candidate_pressure, frontier_pressure) >= 0.50
                and max(candidate_false_fix, frontier_false_fix) >= 0.25
            )
            probe_improved_by_section_bundle = bool(
                probe_mode in {"probe_expanded_v7", "probe_expanded_v8", "probe_expanded_v9"}
                and section_bundles
                and probe_matched
                and candidate_section_bundle_hits == len(section_bundles)
                and candidate_section_bundle_hits > frontier_section_bundle_hits
            )
            probe_improved_by_causal_alignment = bool(
                probe_mode == "probe_expanded_v10"
                and section_bundles
                and causal_alignment_families
                and probe_matched
                and candidate_section_bundle_hits == len(section_bundles)
                and candidate_alignment_hits == len(causal_alignment_families)
                and candidate_alignment_hits > frontier_alignment_hits
            )
            probe_improved = (
                probe_improved_by_score
                or probe_improved_by_section_bundle
                or probe_improved_by_causal_alignment
            )
            if probe_improved and not probe_improved_by_score and probe_improved_by_section_bundle:
                probe_matched = False
            if probe_improved and not probe_improved_by_score and probe_improved_by_causal_alignment:
                probe_matched = False
            win_status = "pass" if (probe_improved or probe_matched) else "hold"
            if win_status == "pass":
                pass_count += 1
            if probe_improved:
                improved_probe_count += 1
                improved_probe_ids.append(probe_id)
            elif probe_matched:
                matched_probe_ids.append(probe_id)
            else:
                blocked_probe_ids.append(probe_id)
            total_candidate_score += candidate_score
            total_pressure_delta += pressure_delta
            total_false_fix_delta += false_fix_delta
            total_compression_delta += compression_delta
            probe_scores.append(
                OutcomeOnlyProbeScore(
                    candidate_id=candidate.candidate_id,
                    probe_id=probe_id,
                    win_status=win_status,
                    pressure_delta=pressure_delta,
                    false_fix_delta=false_fix_delta,
                    compression_delta=compression_delta,
                    candidate_score=candidate_score,
                    frontier_score=frontier_score,
                    summary=[
                        f"candidate_score={candidate_score:.4f}",
                        f"frontier_score={frontier_score:.4f}",
                        f"pressure_delta={pressure_delta:.4f}",
                        f"false_fix_delta={false_fix_delta:.4f}",
                        f"compression_delta={compression_delta:.4f}",
                        (
                            f"signal_hits={candidate_signal_hits}/{len(signal_groups)} "
                            f"frontier_signal_hits={frontier_signal_hits}/{len(signal_groups)}"
                            if signal_groups else
                            "signal_hits=not_applicable"
                        ),
                        (
                            f"section_bundle_hits={candidate_section_bundle_hits}/{len(section_bundles)} "
                            f"frontier_section_bundle_hits={frontier_section_bundle_hits}/{len(section_bundles)}"
                            if section_bundles else
                            "section_bundle_hits=not_applicable"
                        ),
                        (
                            f"causal_alignment_hits={candidate_alignment_hits}/{len(causal_alignment_families)} "
                            f"frontier_causal_alignment_hits={frontier_alignment_hits}/{len(causal_alignment_families)}"
                            if causal_alignment_families else
                            "causal_alignment_hits=not_applicable"
                        ),
                    ],
                )
            )
        ranking_rows.append(
            (
                candidate.candidate_id,
                pass_count,
                improved_probe_count,
                round(total_candidate_score, 4),
                round(total_pressure_delta, 4),
                round(total_false_fix_delta, 4),
                round(total_compression_delta, 4),
                round(float(getattr(metrics.get("editorial_force"), "compression_without_loss", 0.0) or 0.0), 4),
                round(float(getattr(metrics.get("editorial_force"), "decision_pressure_score", 0.0) or 0.0), 4),
            )
        )
        repair_evidence_lines = _matching_probe_lines(
            candidate.rendered_markdown,
            terms=[
                "reject any fix that only",
                "structural fix",
                "wrong habit",
                "right habit",
                "behavior shift",
                "reward loop",
                "replacement behavior",
                "repair recommendation",
                "fake variation",
                "not just numeric tuning",
                "not just more content",
                "same dominant line",
                "same consequence",
                "same consequence structure",
                "old answer stops working",
                "new answer",
                "decision landscape",
                "read, tradeoff, or consequence",
            ],
        )
        collapse_evidence_lines = _matching_probe_lines(
            candidate.rendered_markdown,
            terms=[
                "collapse signal",
                "collapse witness",
                "stop condition",
                "break point",
                "structural witness",
                "solved state risk",
            ],
        )
        repair_specificity_score = _probe_term_coverage(
            candidate.rendered_markdown,
            [
                "reject any fix that only",
                "structural fix",
                "wrong habit",
                "right habit",
                "repair recommendation",
                "read, tradeoff, or consequence",
            ],
        )
        collapse_witness_coverage = _probe_term_coverage(
            candidate.rendered_markdown,
            [
                "collapse signal",
                "collapse witness",
                "stop condition",
                "break point",
            ],
        )
        probe_evidence_density = round(pass_count / max(1, len(probe_specs)), 4)
        probe_witness_summary = [
            f"{probe_id}={'improved' if probe_id in improved_probe_ids else ('matched' if probe_id in matched_probe_ids else 'blocked')}"
            for probe_id in [str(spec.get("probe_id") or "") for spec in probe_specs]
        ]
        if not winner_probe_scores or ranking_rows[-1][1:] > max(
            (row[1:] for row in ranking_rows[:-1]),
            default=(-1, -1, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0),
        ):
            winner_probe_scores = probe_scores
            winner_matched_probe_ids = matched_probe_ids
            winner_improved_probe_ids = improved_probe_ids
            winner_blocked_probe_ids = blocked_probe_ids
            winner_repair_evidence_lines = repair_evidence_lines
            winner_collapse_evidence_lines = collapse_evidence_lines
            winner_probe_witness_summary = probe_witness_summary
            winner_repair_specificity_score = repair_specificity_score
            winner_probe_evidence_density = probe_evidence_density
            winner_collapse_witness_coverage = collapse_witness_coverage
    ranking_rows.sort(key=lambda item: item[1:], reverse=True)
    candidate_ranking = [row[0] for row in ranking_rows]
    winner = candidate_ranking[0] if candidate_ranking else ""
    winner_row = ranking_rows[0] if ranking_rows else ("", 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    all_probes_pass = bool(winner and int(winner_row[1]) == len(probe_specs))
    improved_probe_count = int(winner_row[2]) if winner else 0
    required_improvement_count = 2 if probe_mode in {"probe_expanded_v4", "probe_expanded_v7", "probe_expanded_v8", "probe_expanded_v9", "probe_expanded_v10"} else 1
    frontier_beaten = bool(all_probes_pass and improved_probe_count >= required_improvement_count)
    frontier_matched = bool(all_probes_pass and not frontier_beaten)
    frontier_blocked = not all_probes_pass
    blocking_reason = (
        ""
        if frontier_beaten
        else (
            "outcome_only_reranker_matches_but_improvements_below_threshold"
            if frontier_matched and probe_mode in {"probe_expanded_v4", "probe_expanded_v7", "probe_expanded_v8", "probe_expanded_v9", "probe_expanded_v10"}
            else (
                "outcome_only_reranker_matches_but_does_not_beat_frontier"
                if frontier_matched
                else "outcome_only_reranker_blocked_by_probe_failures"
            )
        )
    )
    return OutcomeOnlyRerankerReport(
        skill_name=skill_name,
        probe_mode=probe_mode,
        candidate_ranking=candidate_ranking,
        winner=winner,
        frontier_comparison_status="beaten" if frontier_beaten else ("matched" if frontier_matched else "blocked"),
        blocking_reason=blocking_reason,
        probe_pass_count=int(winner_row[1]),
        probe_count=len(probe_specs),
        improved_probe_count=improved_probe_count,
        matched_probe_count=len(winner_matched_probe_ids),
        blocked_probe_count=len(winner_blocked_probe_ids),
        repair_specificity_score=winner_repair_specificity_score,
        probe_evidence_density=winner_probe_evidence_density,
        collapse_witness_coverage=winner_collapse_witness_coverage,
        probe_witness_summary=winner_probe_witness_summary,
        matched_probe_ids=winner_matched_probe_ids,
        improved_probe_ids=winner_improved_probe_ids,
        blocked_probe_ids=winner_blocked_probe_ids,
        repair_evidence_lines=winner_repair_evidence_lines,
        collapse_evidence_lines=winner_collapse_evidence_lines,
        probe_scores=winner_probe_scores,
        status="pass" if all_probes_pass else "fail",
        summary=[
            f"winner={winner or 'none'}",
            f"probe_mode={probe_mode}",
            f"probe_pass_count={int(winner_row[1])}/{len(probe_specs)}",
            f"improved_probe_count={improved_probe_count}",
            f"required_improvement_count={required_improvement_count}",
            f"matched_probe_count={len(winner_matched_probe_ids)}",
            f"blocked_probe_count={len(winner_blocked_probe_ids)}",
            f"frontier_comparison_status={'beaten' if frontier_beaten else 'matched'}",
            f"repair_specificity_score={winner_repair_specificity_score:.4f}",
            f"probe_evidence_density={winner_probe_evidence_density:.4f}",
            f"collapse_witness_coverage={winner_collapse_witness_coverage:.4f}",
            f"blocking_reason={blocking_reason or 'none'}",
        ],
    )


def _compressible_section_names(skill_name: str) -> set[str]:
    targets = _profile_residual_targets(skill_name)
    if targets.allowed_sections:
        return set(targets.allowed_sections)
    names = {"Overview", "Output Format", "Quality Checks", "Failure Patterns and Fixes"}
    if skill_name == "simulation-resource-loop-design":
        names.add("Analysis Blocks")
    return names


def _compression_plans(
    *,
    skill_name: str,
    strategy_profile: dict[str, str],
    program: SkillProgramIR,
) -> list[SectionCompressionPlan]:
    common_rules = [
        "merge repeated framing lines",
        "delete repeated generic setup lines",
        "prefer judgment sentences over explanation sentences",
        "keep at most one framing sentence before bullets",
    ]
    output_terms = list(program.output_schema.keys())[:8]
    decision_terms = [move.label for move in list(program.execution_spine or [])[:6]]
    failure_terms = [item.split(" -> ", 1)[0] for item in list(program.failure_repairs or [])[:6]]
    plans = [
        SectionCompressionPlan(
            section_name="Overview",
            max_sentence_budget=1,
            protected_terms=list(output_terms[:2] or decision_terms[:2]),
            forbidden_removals=list(decision_terms[:2]),
            compression_rules=common_rules + ["rewrite opening into a profile-specific one-liner"],
        ),
        SectionCompressionPlan(
            section_name="Output Format",
            max_sentence_budget=1,
            protected_terms=list(output_terms),
            forbidden_removals=list(output_terms),
            compression_rules=common_rules + ["keep field lines and good/weak guidance"],
        ),
        SectionCompressionPlan(
            section_name="Quality Checks",
            max_sentence_budget=1,
            protected_terms=list(decision_terms),
            forbidden_removals=list(decision_terms[:4]),
            compression_rules=common_rules + ["keep failure-trigger checks and stop conditions"],
        ),
        SectionCompressionPlan(
            section_name="Failure Patterns and Fixes",
            max_sentence_budget=1,
            protected_terms=list(failure_terms),
            forbidden_removals=list(failure_terms[:4]),
            compression_rules=common_rules + ["keep symptom/cause/correction structure intact"],
        ),
    ]
    if "Default Workflow" in _compressible_section_names(skill_name):
        plans.append(
            SectionCompressionPlan(
                section_name="Default Workflow",
                max_sentence_budget=1,
                protected_terms=list(decision_terms),
                forbidden_removals=list(decision_terms),
                compression_rules=common_rules + ["preserve numbered workflow spine and decision/failure/fix bullets"],
            )
        )
    if skill_name == "simulation-resource-loop-design":
        plans.append(
            SectionCompressionPlan(
                section_name="Analysis Blocks",
                max_sentence_budget=1,
                protected_terms=["Variable Web", "Pressure Relationships", "Main Feedback Loops", "Failure and Recovery"],
                forbidden_removals=["Variable Web", "Pressure Relationships"],
                compression_rules=common_rules + ["preserve map/tension/loop/recovery structure"],
            )
        )
    return plans


def _parse_markdown_sections(markdown: str) -> tuple[list[str], dict[str, list[str]]]:
    lines = markdown.splitlines()
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    current_name: str | None = None
    buffer: list[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            buffer.append(line)
            continue
        if line.startswith("## ") and not in_fence:
            if current_name is None:
                preamble = list(buffer)
            else:
                sections[current_name] = list(buffer)
            current_name = line[3:].strip()
            buffer = [line]
            continue
        buffer.append(line)
    if current_name is None:
        preamble = list(buffer)
    else:
        sections[current_name] = list(buffer)
    return preamble, sections


def _resolve_section_key(sections: dict[str, list[str]], target_name: str) -> str | None:
    if target_name in sections:
        return target_name
    if target_name == "Failure Patterns and Fixes":
        for key in sections:
            if key.lower().startswith("common pitfalls:"):
                return key
    return None


def _restore_markdown_sections(preamble: list[str], sections: dict[str, list[str]], order: list[str]) -> str:
    output: list[str] = list(preamble)
    if output and output[-1] != "":
        output.append("")
    for name in order:
        lines = list(sections.get(name, []))
        if not lines:
            continue
        if output and output[-1] != "":
            output.append("")
        output.extend(lines)
    return "\n".join(output).rstrip() + "\n"


def _sentence_like_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(("#", "-", "*", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "```", "---")):
        return False
    return True


def _compression_opening(skill_name: str, strategy_profile: dict[str, str]) -> str:
    opening = str(strategy_profile.get("opening_frame") or "").strip()
    if opening:
        return opening
    defaults = {
        "concept-to-mvp-pack": "Prove the smallest honest first playable, cut the rest, and package only what survives.",
        "decision-loop-stress-test": "Pressure-test the decision game until the break point and repair move are explicit.",
        "simulation-resource-loop-design": "Map the pressure web, keep the tradeoffs visible, and preserve recovery cost.",
    }
    return defaults.get(skill_name, "")


def _append_sentence(base: str, extra: str) -> str:
    left = str(base or "").strip()
    right = str(extra or "").strip()
    if not left:
        return right
    if not right:
        return left
    if left.endswith((".", "!", "?")):
        return f"{left} {right}"
    return f"{left}. {right}"


def _compress_section_lines(
    *,
    skill_name: str,
    section_name: str,
    lines: list[str],
    plan: SectionCompressionPlan,
    strategy_profile: dict[str, str],
) -> tuple[list[str], SectionCompressionResult]:
    if not lines:
        return lines, SectionCompressionResult(section_name=section_name)
    result = SectionCompressionResult(section_name=section_name)
    heading = lines[0]
    body_lines = list(lines[1:])
    compressed: list[str] = []
    seen_norm: set[str] = set()
    framing_count = 0
    generic_prefixes = (
        "use this skill to",
        "use this section to",
        "use these checks to",
        "use this step to",
        "lead with",
        "secondary emphasis:",
        "another agent should",
        "avoid generic",
    )
    opening_override = _compression_opening(skill_name, strategy_profile) if section_name == "Overview" else ""
    for raw_line in body_lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if compressed and compressed[-1] != "":
                compressed.append("")
            continue
        lowered = stripped.lower()
        protected = any(term.lower() in lowered for term in list(plan.protected_terms or []))
        forbidden = any(term.lower() in lowered for term in list(plan.forbidden_removals or []))
        if opening_override and _sentence_like_line(stripped):
            compressed.append(opening_override)
            result.opening_rewrite_applied = True
            opening_override = ""
            result.removed_redundant_lines += 1
            continue
        normalized = " ".join(lowered.split())
        if normalized in seen_norm and not protected and not forbidden:
            result.removed_redundant_lines += 1
            continue
        if any(lowered.startswith(prefix) for prefix in generic_prefixes) and not protected and not forbidden:
            result.filler_removed_count += 1
            continue
        if _sentence_like_line(stripped):
            framing_count += 1
            if framing_count > max(1, int(plan.max_sentence_budget or 1)) and not protected and not forbidden:
                result.filler_removed_count += 1
                continue
            if ":" not in stripped and not any(token in lowered for token in ("must", "cut", "fail", "keep", "output", "check", "watch")) and not protected:
                stripped = stripped.rstrip(".") + "."
        compressed.append(stripped if stripped == line else stripped)
        seen_norm.add(normalized)
    if section_name == "Quality Checks":
        prioritized: list[str] = []
        bullet_count = 0
        for item in compressed:
            stripped = item.strip()
            if not stripped:
                continue
            if not stripped.startswith("- "):
                prioritized.append(item)
                continue
            lowered = stripped.lower()
            is_priority = any(
                token in lowered
                for token in (
                    "gate:",
                    "reject",
                    "must",
                    "fail",
                    "pressure",
                    "scope",
                    "out-of-scope",
                    "solved",
                    "autopilot",
                    "recovery",
                    "tradeoff",
                    "build",
                    "playtest",
                    "reward",
                    "decision quality",
                    "numeric balancing",
                    "prototype first",
                    "consequence-free reset",
                )
            )
            if bullet_count < 10 and (is_priority or "check that" not in lowered):
                prioritized.append(item)
                bullet_count += 1
            else:
                result.filler_removed_count += 1
        compressed = prioritized
    elif section_name == "Failure Patterns and Fixes":
        pruned: list[str] = []
        heading_count = 0
        allow_block = True
        max_headings = 5 if skill_name != "simulation-resource-loop-design" else 6
        for item in compressed:
            stripped = item.strip()
            if stripped.startswith("### "):
                heading_count += 1
                allow_block = heading_count <= max_headings
                if not allow_block:
                    result.filler_removed_count += 1
                    continue
            if allow_block:
                pruned.append(item)
            elif stripped:
                result.filler_removed_count += 1
        compressed = pruned
    elif section_name == "Analysis Blocks":
        pruned_blocks: list[str] = []
        for item in compressed:
            stripped = item.strip()
            lowered = stripped.lower()
            if lowered.startswith("- use when:"):
                result.filler_removed_count += 1
                continue
            pruned_blocks.append(item)
        compressed = pruned_blocks
    while compressed and compressed[-1] == "":
        compressed.pop()
    preserved = True
    lowered_joined = "\n".join(item.lower() for item in compressed)
    for term in list(plan.protected_terms or []):
        if term and term.lower() not in lowered_joined:
            preserved = False
            break
    result.protected_terms_preserved = preserved
    final_lines = [heading]
    if compressed:
        final_lines.extend(compressed)
    return final_lines, result


def _compress_candidate_sections(
    *,
    skill_name: str,
    candidate: SkillRealizationCandidate,
    program: SkillProgramIR,
) -> SkillRealizationCandidate:
    preamble, sections = _parse_markdown_sections(candidate.rendered_markdown)
    plans = {
        item.section_name: item
        for item in _compression_plans(skill_name=skill_name, strategy_profile=dict(candidate.strategy_profile or {}), program=program)
        if item.section_name in _compressible_section_names(skill_name)
    }
    compression_results: list[SectionCompressionResult] = []
    for section_name, plan in plans.items():
        section_key = _resolve_section_key(sections, section_name)
        if section_key is None:
            continue
        compressed_lines, result = _compress_section_lines(
            skill_name=skill_name,
            section_name=section_name,
            lines=list(sections[section_key]),
            plan=plan,
            strategy_profile=dict(candidate.strategy_profile or {}),
        )
        sections[section_key] = compressed_lines
        compression_results.append(result)
    markdown = _restore_markdown_sections(preamble, sections, list(sections.keys()))
    profile = dict(candidate.strategy_profile or {})
    profile["compression_stage"] = "post"
    profile["source_candidate_id"] = candidate.candidate_id
    profile["compression_sections"] = ",".join(item.section_name for item in compression_results if item.removed_redundant_lines or item.filler_removed_count or item.opening_rewrite_applied)
    return candidate.model_copy(
        update={
            "candidate_id": f"{candidate.candidate_id}:compressed",
            "strategy_profile": profile,
            "rendered_markdown": markdown,
            "diagnostic_summary": list(candidate.diagnostic_summary or [])
            + [
                "compression_stage=post",
                f"compression_sections={profile.get('compression_sections', '') or 'none'}",
                f"compression_removed_lines={sum(item.removed_redundant_lines for item in compression_results)}",
                f"compression_removed_fillers={sum(item.filler_removed_count for item in compression_results)}",
            ],
        }
    )


def _candidate_separation_report(candidates: list[SkillRealizationCandidate]) -> tuple[str, float, list[dict[str, str]]]:
    pre_candidates = [
        item for item in candidates
        if str(dict(item.strategy_profile or {}).get("compression_stage") or "pre") != "post"
    ]
    source = pre_candidates or candidates
    matrix = [
        {
            "candidate_id": item.candidate_id,
            "strategy": item.realization_strategy,
            **{str(key): str(value) for key, value in dict(item.strategy_profile or {}).items()},
        }
        for item in source
    ]
    if len(matrix) < 2:
        return "fail", 0.0, matrix

    candidate_count = len(matrix)

    def _norm(key: str) -> float:
        values = {str(item.get(key, "") or "") for item in matrix}
        return round((max(0, len(values) - 1) / max(1, candidate_count - 1)), 4)

    opening = _norm("opening_frame")
    section_order = _norm("section_order")
    sentence_budget_profile = _norm("sentence_budget_profile")
    workflow_mode = _norm("workflow_mode")
    step_frame = _norm("step_frame")
    output_focus = _norm("output_focus")
    quality_tone = _norm("quality_tone")
    quality_mode = _norm("quality_mode")
    failure_style = _norm("failure_style")
    failure_mode = _norm("failure_mode")
    score = round(
        0.14 * opening
        + 0.18 * section_order
        + 0.12 * sentence_budget_profile
        + 0.16 * workflow_mode
        + 0.12 * step_frame
        + 0.10 * output_focus
        + 0.06 * quality_tone
        + 0.06 * quality_mode
        + 0.03 * failure_style
        + 0.03 * failure_mode,
        4,
    )
    strong_axes = sum(
        value >= 0.34
        for value in [
            section_order,
            sentence_budget_profile,
            workflow_mode,
            step_frame,
            output_focus,
            quality_mode,
            failure_mode,
        ]
    )
    status = (
        "pass"
        if score >= 0.78
        and strong_axes >= 4
        and section_order > 0.0
        and workflow_mode > 0.0
        and step_frame > 0.0
        else "fail"
    )
    return status, score, matrix


def _compare_to_dual_baselines(
    *,
    skill_name: str,
    winner_metrics: dict[str, Any],
    source_metrics: dict[str, Any] | None,
    bundle: ProfileBaselineBundle | None,
) -> MonotonicImprovementReport:
    if bundle is None:
        return MonotonicImprovementReport(
            skill_name=skill_name,
            active_frontier_status="missing",
            best_balance_comparison_status="missing",
            best_coverage_comparison_status="missing",
            force_non_regression_status="pass",
            coverage_non_regression_status="pass",
            compactness_non_regression_status="pass",
            frontier_dominance_status="pass",
            compression_gain_status="neutral",
            promotion_status="promote",
            promotion_reason="no_dual_baseline_bundle",
            summary=["no dual-baseline bundle available"],
        )

    score_tol = float(dict(bundle.tolerance or {}).get("score_metric", 0.01) or 0.01)
    compactness_tol = float(dict(bundle.tolerance or {}).get("compactness_metric", 0.01) or 0.01)
    winner_force = _primary_force_values(skill_name, winner_metrics.get("editorial_force"))
    winner_coverage = _coverage_values(winner_metrics, skill_name)
    winner_compactness = _compactness_values(winner_metrics, skill_name)

    force_regressions = [
        f"{metric}:{winner_force.get(metric, 0.0):.4f}<{float(value) - score_tol:.4f}"
        for metric, value in dict(bundle.force_floor or {}).items()
        if winner_force.get(metric, 0.0) + score_tol < float(value)
    ]
    coverage_regressions = [
        f"{metric}:{winner_coverage.get(metric, 0.0):.4f}<{float(value) - score_tol:.4f}"
        for metric, value in dict(bundle.coverage_floor or {}).items()
        if winner_coverage.get(metric, 0.0) + score_tol < float(value)
    ]
    compactness_regressions = [
        f"{metric}:{winner_compactness.get(metric, 0.0):.4f}>{float(value) + compactness_tol:.4f}"
        for metric, value in dict(bundle.compactness_ceiling or {}).items()
        if winner_compactness.get(metric, 0.0) > float(value) + compactness_tol
    ]
    force_non_regression_status = "fail" if force_regressions else "pass"
    coverage_non_regression_status = "fail" if coverage_regressions else "pass"
    compactness_non_regression_status = "fail" if compactness_regressions else "pass"

    def _baseline_force_win(snapshot_name: str) -> int:
        snapshot = getattr(bundle, snapshot_name)
        return sum(
            1
            for metric, baseline in dict(snapshot.primary_force_metrics or {}).items()
            if winner_force.get(metric, 0.0) > float(baseline) + 0.015
        )

    best_balance_force_win_count = _baseline_force_win("best_balance_snapshot")
    best_coverage_force_win_count = _baseline_force_win("best_coverage_snapshot")
    primary_force_win_count = max(best_balance_force_win_count, best_coverage_force_win_count)

    best_balance_comparison_status = "beaten" if best_balance_force_win_count >= 1 else "not_beaten"
    best_coverage_comparison_status = "beaten" if best_coverage_force_win_count >= 1 else "not_beaten"
    active_frontier_status = (
        "regressed"
        if (
            force_non_regression_status == "fail"
            or coverage_non_regression_status == "fail"
            or compactness_non_regression_status == "fail"
        )
        else ("beaten" if best_balance_force_win_count >= 1 and best_coverage_force_win_count >= 1 else "matched")
    )
    frontier_dominance_status = (
        "pass"
        if (
            force_non_regression_status == "pass"
            and coverage_non_regression_status == "pass"
            and compactness_non_regression_status == "pass"
        )
        else "fail"
    )

    compactness_gains: list[str] = []
    if source_metrics is not None:
        source_compactness = _compactness_values(source_metrics, skill_name)
        source_compression = round(float(source_metrics.get("compression_without_loss", 0.0) or 0.0), 4)
        winner_compression = round(float(winner_metrics.get("compression_without_loss", 0.0) or 0.0), 4)
        if source_compactness.get("redundancy_ratio", 1.0) - winner_compactness.get("redundancy_ratio", 1.0) >= 0.02:
            compactness_gains.append("redundancy_ratio")
        if source_compactness.get("shared_opening_phrase_ratio", 1.0) - winner_compactness.get("shared_opening_phrase_ratio", 1.0) >= 0.05:
            compactness_gains.append("shared_opening_phrase_ratio")
        if source_compactness.get("cross_case_similarity", 1.0) - winner_compactness.get("cross_case_similarity", 1.0) >= 0.02:
            compactness_gains.append("cross_case_similarity")
        if winner_compression - source_compression >= 0.03:
            compactness_gains.append("compression_without_loss")
    compression_gain_status = (
        "pass"
        if compactness_gains
        else ("neutral" if source_metrics is None else "fail")
    )

    protected_regressions = force_regressions + coverage_regressions + compactness_regressions
    if force_non_regression_status != "pass":
        promotion_status = "hold"
        promotion_reason = "hold_due_to_force_regression"
    elif coverage_non_regression_status != "pass":
        promotion_status = "hold"
        promotion_reason = "hold_due_to_coverage_regression"
    elif compactness_non_regression_status != "pass":
        promotion_status = "hold"
        promotion_reason = "hold_due_to_compactness_regression"
    elif primary_force_win_count >= 1:
        promotion_status = "promote"
        promotion_reason = "breakthrough"
    elif compression_gain_status == "pass":
        promotion_status = "promote"
        promotion_reason = "breakthrough"
    else:
        promotion_status = "hold"
        promotion_reason = "hold_due_to_no_primary_win"

    legacy_delta_summary: list[str] = []
    for label, snapshot in (
        ("legacy_balance", bundle.legacy_balance_snapshot),
        ("legacy_coverage", bundle.legacy_coverage_snapshot),
    ):
        if snapshot is None:
            continue
        better_force = sum(
            1
            for metric, baseline in dict(snapshot.primary_force_metrics or {}).items()
            if winner_force.get(metric, 0.0) > float(baseline) + 0.01
        )
        better_coverage = sum(
            1
            for metric, baseline in dict(snapshot.coverage_metrics or {}).items()
            if winner_coverage.get(metric, 0.0) > float(baseline) + 0.01
        )
        better_compactness = sum(
            1
            for metric, baseline in dict(snapshot.compactness_metrics or {}).items()
            if winner_compactness.get(metric, 0.0) + compactness_tol < float(baseline)
        )
        legacy_delta_summary.append(
            f"{label}=force+{better_force}/coverage+{better_coverage}/compactness+{better_compactness}"
        )

    return MonotonicImprovementReport(
        skill_name=skill_name,
        active_frontier_status=active_frontier_status,
        best_balance_comparison_status=best_balance_comparison_status,
        best_coverage_comparison_status=best_coverage_comparison_status,
        force_non_regression_status=force_non_regression_status,
        coverage_non_regression_status=coverage_non_regression_status,
        compactness_non_regression_status=compactness_non_regression_status,
        frontier_dominance_status=frontier_dominance_status,
        compression_gain_status=compression_gain_status,
        promotion_status=promotion_status,
        promotion_reason=promotion_reason,
        primary_force_win_count=primary_force_win_count,
        protected_regressions=protected_regressions,
        compactness_gains=compactness_gains,
        legacy_delta_summary=legacy_delta_summary,
        summary=[
            f"active_frontier_status={active_frontier_status}",
            f"best_balance_comparison_status={best_balance_comparison_status}",
            f"best_coverage_comparison_status={best_coverage_comparison_status}",
            f"force_non_regression_status={force_non_regression_status}",
            f"coverage_non_regression_status={coverage_non_regression_status}",
            f"compactness_non_regression_status={compactness_non_regression_status}",
            f"compression_gain_status={compression_gain_status}",
            f"primary_force_win_count={primary_force_win_count}",
            f"promotion_reason={promotion_reason}",
            *legacy_delta_summary,
        ],
    )


def choose_skill_realization_candidate(
    *,
    skill_name: str,
    task: str,
    candidates: list[SkillRealizationCandidate],
) -> tuple[SkillRealizationCandidate | None, PairwiseEditorialReport | None, SkillPromotionDecision, MonotonicImprovementReport | None]:
    if not candidates:
        return None, None, SkillPromotionDecision(skill_name=skill_name, promotion_status="hold", reason="no_candidates"), None
    scored = [
        (
            candidate,
            _candidate_editorial_metrics(
                skill_name=skill_name,
                task=task,
                markdown=candidate.rendered_markdown,
                realization_candidate_count=len(candidates),
            ),
        )
        for candidate in candidates
    ]
    scored.sort(key=lambda item: _candidate_rank_key(skill_name, item[1]), reverse=True)
    outcome_probe_mode = "probe_expanded_v10" if skill_name == "decision-loop-stress-test" else "frontier_v3"
    outcome_only_base_report = (
        _build_outcome_only_reranker_report(
            skill_name=skill_name,
            scored_candidates=scored,
            probe_mode="probe_expanded_v9",
        )
        if skill_name == "decision-loop-stress-test"
        else None
    )
    outcome_only_report = _build_outcome_only_reranker_report(
        skill_name=skill_name,
        scored_candidates=scored,
        probe_mode=outcome_probe_mode,
    )
    if outcome_only_report is not None and list(outcome_only_report.candidate_ranking or []):
        ranking_order = {candidate_id: index for index, candidate_id in enumerate(list(outcome_only_report.candidate_ranking or []))}
        scored.sort(
            key=lambda item: (
                ranking_order.get(item[0].candidate_id, len(ranking_order)),
                tuple(-value for value in _candidate_rank_key(skill_name, item[1])),
            )
        )
    winner, winner_metrics = scored[0]
    loser, loser_metrics = scored[1] if len(scored) > 1 else scored[0]
    scored_by_id = {item.candidate_id: metrics for item, metrics in scored}
    candidate_separation_status, candidate_separation_score, candidate_strategy_matrix = _candidate_separation_report(candidates)
    current_best_metrics = _current_best_editorial_metrics(skill_name, task)
    source_candidate_id = str(dict(winner.strategy_profile or {}).get("source_candidate_id") or "")
    source_metrics = scored_by_id.get(source_candidate_id)
    monotonic_report = _compare_to_dual_baselines(
        skill_name=skill_name,
        winner_metrics=winner_metrics,
        source_metrics=source_metrics,
        bundle=_dual_baseline_bundle(skill_name),
    )
    residual_input_metrics = dict(winner_metrics)
    if outcome_only_report is not None:
        residual_input_metrics.update(
            {
                "outcome_only_probe_pass_count": float(getattr(outcome_only_report, "probe_pass_count", 0) or 0),
                "outcome_only_improved_probe_count": float(getattr(outcome_only_report, "improved_probe_count", 0) or 0),
                "repair_specificity_score": float(getattr(outcome_only_report, "repair_specificity_score", 0.0) or 0.0),
                "probe_evidence_density": float(getattr(outcome_only_report, "probe_evidence_density", 0.0) or 0.0),
                "collapse_witness_coverage": float(getattr(outcome_only_report, "collapse_witness_coverage", 0.0) or 0.0),
            }
        )
    residual_gap_report = _residual_gap_report(skill_name, residual_input_metrics)
    force_non_regression_status = monotonic_report.force_non_regression_status
    base_probe_clean_pass = _decision_loop_probe_clean_pass(outcome_only_base_report)
    current_probe_clean_pass = _decision_loop_probe_clean_pass(outcome_only_report)
    base_outcome_breakthrough = _decision_loop_probe_expanded_ready(outcome_only_base_report)
    current_outcome_breakthrough = (
        _decision_loop_probe_expanded_ready(outcome_only_report)
        if outcome_probe_mode == "probe_expanded_v10"
        else True
    )
    outcome_only_ready = (
        base_outcome_breakthrough and current_outcome_breakthrough
        if skill_name == "decision-loop-stress-test"
        else True
    )
    decision_loop_outcome_breakthrough = bool(
        skill_name == "decision-loop-stress-test"
        and candidate_separation_status == "pass"
        and monotonic_report.frontier_dominance_status == "pass"
        and residual_gap_report.status == "pass"
        and outcome_only_report is not None
        and outcome_only_report.status == "pass"
        and outcome_only_report.frontier_comparison_status == "beaten"
        and outcome_only_ready
    )
    current_best_comparison_status = (
        "beaten"
        if monotonic_report.promotion_status == "promote" or decision_loop_outcome_breakthrough
        else "not_beaten"
    )
    primary_force_win_count = int(monotonic_report.primary_force_win_count or 0)
    hold_reason = (
        monotonic_report.promotion_reason
        if monotonic_report.promotion_status != "promote" and not decision_loop_outcome_breakthrough
        else ""
    )
    pairwise = PairwiseEditorialReport(
        skill_name=skill_name,
        winner=winner.candidate_id,
        loser=loser.candidate_id,
        decision_pressure_delta=round(
            float(getattr(winner_metrics["editorial_force"], "decision_pressure_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "decision_pressure_score", 0.0) or 0.0),
            4,
        ),
        cut_sharpness_delta=round(
            float(getattr(winner_metrics["editorial_force"], "cut_sharpness_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "cut_sharpness_score", 0.0) or 0.0),
            4,
        ),
        failure_repair_clarity_delta=round(
            float(getattr(winner_metrics["editorial_force"], "failure_repair_force", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "failure_repair_force", 0.0) or 0.0),
            4,
        ),
        output_executability_delta=round(
            float(getattr(winner_metrics["editorial_force"], "output_executability_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "output_executability_score", 0.0) or 0.0),
            4,
        ),
        redundancy_delta=round(
            float(getattr(loser_metrics["editorial"], "redundancy_ratio", 0.0) or 0.0)
            - float(getattr(winner_metrics["editorial"], "redundancy_ratio", 0.0) or 0.0),
            4,
        ),
        style_convergence_delta=round(
            float(getattr(winner_metrics["style"], "domain_rhythm_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["style"], "domain_rhythm_score", 0.0) or 0.0),
            4,
        ),
        candidate_separation_status=candidate_separation_status,
        candidate_separation_score=candidate_separation_score,
        force_non_regression_status=force_non_regression_status,
        current_best_comparison_status=current_best_comparison_status,
        primary_force_win_count=primary_force_win_count,
        promotion_hold_reason=hold_reason,
        candidate_strategy_matrix=candidate_strategy_matrix,
        summary=[
            f"winner={winner.candidate_id}",
            f"loser={loser.candidate_id}",
            f"candidate_separation_status={candidate_separation_status}",
            f"force_non_regression_status={force_non_regression_status}",
            f"current_best_comparison_status={current_best_comparison_status}",
            f"primary_force_win_count={primary_force_win_count}",
            f"outcome_only_reranker_status={getattr(outcome_only_report, 'status', 'not_applicable')}",
            f"score_delta={winner_metrics['score'] - loser_metrics['score']:.4f}",
        ],
    )
    if current_best_metrics is None:
        promote_without_best = candidate_separation_status == "pass"
        monotonic_if_missing = monotonic_report.model_copy(
            update={
                "promotion_status": "promote" if promote_without_best else "hold",
                "promotion_reason": "no_current_best_snapshot" if promote_without_best else "hold_due_to_candidate_separation",
            }
        )
        return winner, pairwise, SkillPromotionDecision(
            skill_name=skill_name,
            candidate_id=winner.candidate_id,
            current_best_id="missing",
            promotion_status="promote" if promote_without_best else "hold",
            reason="no_current_best_snapshot" if promote_without_best else "hold_due_to_candidate_separation",
            best_balance_comparison_status=monotonic_if_missing.best_balance_comparison_status,
            best_coverage_comparison_status=monotonic_if_missing.best_coverage_comparison_status,
            candidate_separation_status=candidate_separation_status,
            force_non_regression_status="pass",
            coverage_non_regression_status=monotonic_if_missing.coverage_non_regression_status,
            compactness_non_regression_status=monotonic_if_missing.compactness_non_regression_status,
            frontier_dominance_status=monotonic_if_missing.frontier_dominance_status,
            compression_gain_status=monotonic_if_missing.compression_gain_status,
            current_best_comparison_status="missing_current_best",
            active_frontier_status=monotonic_if_missing.active_frontier_status,
            primary_force_win_count=0,
            promotion_hold_reason="" if promote_without_best else "hold_due_to_candidate_separation",
            stable_but_no_breakthrough=not promote_without_best,
            quality_check_target_status=residual_gap_report.quality_check_target_status,
            pressure_target_status=residual_gap_report.pressure_target_status,
            leakage_target_status=residual_gap_report.leakage_target_status,
            false_fix_rejection_status=residual_gap_report.false_fix_rejection_status,
            residual_gap_count=residual_gap_report.residual_gap_count,
            outcome_only_reranker_status=str(getattr(outcome_only_report, "status", "not_applicable") or "not_applicable"),
            outcome_only_probe_mode=str(getattr(outcome_only_report, "probe_mode", "unknown") or "unknown"),
            outcome_only_frontier_comparison_status=str(getattr(outcome_only_report, "frontier_comparison_status", "missing_current_best") or "missing_current_best"),
            outcome_only_probe_pass_count=int(getattr(outcome_only_report, "probe_pass_count", 0) or 0),
            outcome_only_probe_count=int(getattr(outcome_only_report, "probe_count", 0) or 0),
            outcome_only_improved_probe_count=int(getattr(outcome_only_report, "improved_probe_count", 0) or 0),
            outcome_only_matched_probe_count=int(getattr(outcome_only_report, "matched_probe_count", 0) or 0),
            outcome_only_blocked_probe_count=int(getattr(outcome_only_report, "blocked_probe_count", 0) or 0),
            outcome_only_repair_specificity_score=float(getattr(outcome_only_report, "repair_specificity_score", 0.0) or 0.0),
            outcome_only_probe_evidence_density=float(getattr(outcome_only_report, "probe_evidence_density", 0.0) or 0.0),
            outcome_only_collapse_witness_coverage=float(getattr(outcome_only_report, "collapse_witness_coverage", 0.0) or 0.0),
            outcome_only_blocking_reason=str(getattr(outcome_only_report, "blocking_reason", "") or ""),
            outcome_only_probe_witness_summary=list(getattr(outcome_only_report, "probe_witness_summary", []) or []),
            outcome_only_matched_probe_ids=list(getattr(outcome_only_report, "matched_probe_ids", []) or []),
            outcome_only_improved_probe_ids=list(getattr(outcome_only_report, "improved_probe_ids", []) or []),
            outcome_only_blocked_probe_ids=list(getattr(outcome_only_report, "blocked_probe_ids", []) or []),
            outcome_only_repair_evidence_lines=list(getattr(outcome_only_report, "repair_evidence_lines", []) or []),
            outcome_only_collapse_evidence_lines=list(getattr(outcome_only_report, "collapse_evidence_lines", []) or []),
            summary=[
                f"promotion_status={'promote' if promote_without_best else 'hold'}",
                f"reason={'no_current_best_snapshot' if promote_without_best else 'hold_due_to_candidate_separation'}",
                f"candidate_separation_status={candidate_separation_status}",
                *residual_gap_report.summary,
            ],
        ), monotonic_if_missing
    winner_score = float(winner_metrics["score"])
    current_score = float(current_best_metrics["score"])
    promote = (
        candidate_separation_status == "pass"
        and monotonic_report.frontier_dominance_status == "pass"
        and (monotonic_report.promotion_status == "promote" or decision_loop_outcome_breakthrough)
        and residual_gap_report.status == "pass"
        and (
            outcome_only_report is None
            or (
                outcome_only_report.status == "pass"
                and outcome_only_report.frontier_comparison_status == "beaten"
                and outcome_only_ready
            )
        )
    )
    outcome_only_probe_blocked = bool(
        (skill_name == "decision-loop-stress-test" and not base_probe_clean_pass)
        or (
            outcome_only_report is not None
            and (
                (skill_name == "decision-loop-stress-test" and not current_probe_clean_pass)
                or
                outcome_only_report.status != "pass"
                or str(getattr(outcome_only_report, "frontier_comparison_status", "blocked") or "blocked") == "blocked"
                or int(getattr(outcome_only_report, "blocked_probe_count", 0) or 0) > 0
            )
        )
    )
    base_outcome_stable_matched = bool(
        outcome_only_base_report is not None
        and outcome_only_base_report.status == "pass"
        and str(getattr(outcome_only_base_report, "frontier_comparison_status", "blocked") or "blocked") == "matched"
        and int(getattr(outcome_only_base_report, "blocked_probe_count", 0) or 0) == 0
    )
    current_outcome_stable_matched = bool(
        outcome_only_report is not None
        and outcome_only_report.status == "pass"
        and str(getattr(outcome_only_report, "frontier_comparison_status", "blocked") or "blocked") == "matched"
        and int(getattr(outcome_only_report, "blocked_probe_count", 0) or 0) == 0
    )
    outcome_only_stable_matched = bool(
        residual_gap_report.status == "pass"
        and (
            (
                skill_name == "decision-loop-stress-test"
                and base_probe_clean_pass
                and current_probe_clean_pass
                and (base_outcome_stable_matched or current_outcome_stable_matched)
            )
            or (
                skill_name != "decision-loop-stress-test"
                and current_outcome_stable_matched
            )
        )
    )
    stable_but_no_breakthrough = (
        not promote
        and candidate_separation_status == "pass"
        and monotonic_report.frontier_dominance_status == "pass"
        and (
            outcome_only_stable_matched
            or (
                outcome_only_report is None
                and (
                    (monotonic_report.promotion_status != "promote" and monotonic_report.promotion_reason == "hold_due_to_no_primary_win")
                    or residual_gap_report.status != "pass"
                )
            )
        )
    )
    promotion_reason = (
        "breakthrough"
        if promote
        else (
            "hold_due_to_candidate_separation"
            if candidate_separation_status != "pass"
            else (
                "stable_but_no_breakthrough"
                if stable_but_no_breakthrough
                else (
                    str(getattr(outcome_only_report, "blocking_reason", "") or "")
                    if outcome_only_probe_blocked
                    else (
                        "breakthrough"
                        if decision_loop_outcome_breakthrough
                        else monotonic_report.promotion_reason
                    )
                )
            )
        )
    )
    return winner, pairwise, SkillPromotionDecision(
        skill_name=skill_name,
        candidate_id=winner.candidate_id,
        current_best_id=f"{skill_name}:current_best",
        promotion_status="promote" if promote else "hold",
        reason=promotion_reason,
        best_balance_comparison_status=monotonic_report.best_balance_comparison_status,
        best_coverage_comparison_status=monotonic_report.best_coverage_comparison_status,
        candidate_separation_status=candidate_separation_status,
        force_non_regression_status=force_non_regression_status,
        coverage_non_regression_status=monotonic_report.coverage_non_regression_status,
        compactness_non_regression_status=monotonic_report.compactness_non_regression_status,
        frontier_dominance_status=monotonic_report.frontier_dominance_status,
        compression_gain_status=monotonic_report.compression_gain_status,
        current_best_comparison_status=current_best_comparison_status,
        active_frontier_status=(
            "beaten"
            if decision_loop_outcome_breakthrough and monotonic_report.active_frontier_status == "matched"
            else monotonic_report.active_frontier_status
        ),
        primary_force_win_count=primary_force_win_count,
        promotion_hold_reason="" if promote else promotion_reason,
        stable_but_no_breakthrough=stable_but_no_breakthrough,
        quality_check_target_status=residual_gap_report.quality_check_target_status,
        pressure_target_status=residual_gap_report.pressure_target_status,
        leakage_target_status=residual_gap_report.leakage_target_status,
        false_fix_rejection_status=residual_gap_report.false_fix_rejection_status,
        residual_gap_count=residual_gap_report.residual_gap_count,
        outcome_only_reranker_status=str(getattr(outcome_only_report, "status", "not_applicable") or "not_applicable"),
        outcome_only_probe_mode=str(getattr(outcome_only_report, "probe_mode", "unknown") or "unknown"),
        outcome_only_frontier_comparison_status=str(getattr(outcome_only_report, "frontier_comparison_status", "not_applicable") or "not_applicable"),
        outcome_only_probe_pass_count=int(getattr(outcome_only_report, "probe_pass_count", 0) or 0),
        outcome_only_probe_count=int(getattr(outcome_only_report, "probe_count", 0) or 0),
        outcome_only_improved_probe_count=int(getattr(outcome_only_report, "improved_probe_count", 0) or 0),
        outcome_only_matched_probe_count=int(getattr(outcome_only_report, "matched_probe_count", 0) or 0),
        outcome_only_blocked_probe_count=int(getattr(outcome_only_report, "blocked_probe_count", 0) or 0),
        outcome_only_repair_specificity_score=float(getattr(outcome_only_report, "repair_specificity_score", 0.0) or 0.0),
        outcome_only_probe_evidence_density=float(getattr(outcome_only_report, "probe_evidence_density", 0.0) or 0.0),
        outcome_only_collapse_witness_coverage=float(getattr(outcome_only_report, "collapse_witness_coverage", 0.0) or 0.0),
        outcome_only_blocking_reason=str(getattr(outcome_only_report, "blocking_reason", "") or ""),
        outcome_only_probe_witness_summary=list(getattr(outcome_only_report, "probe_witness_summary", []) or []),
        outcome_only_matched_probe_ids=list(getattr(outcome_only_report, "matched_probe_ids", []) or []),
        outcome_only_improved_probe_ids=list(getattr(outcome_only_report, "improved_probe_ids", []) or []),
        outcome_only_blocked_probe_ids=list(getattr(outcome_only_report, "blocked_probe_ids", []) or []),
        outcome_only_repair_evidence_lines=list(getattr(outcome_only_report, "repair_evidence_lines", []) or []),
        outcome_only_collapse_evidence_lines=list(getattr(outcome_only_report, "collapse_evidence_lines", []) or []),
        summary=[
            f"winner_score={winner_score:.4f}",
            f"current_best_score={current_score:.4f}",
            f"candidate_separation_status={candidate_separation_status}",
            f"active_frontier_status={monotonic_report.active_frontier_status}",
            f"force_non_regression_status={force_non_regression_status}",
            f"coverage_non_regression_status={monotonic_report.coverage_non_regression_status}",
            f"compactness_non_regression_status={monotonic_report.compactness_non_regression_status}",
            f"frontier_dominance_status={monotonic_report.frontier_dominance_status}",
            f"compression_gain_status={monotonic_report.compression_gain_status}",
            f"current_best_comparison_status={current_best_comparison_status}",
            f"primary_force_win_count={primary_force_win_count}",
            f"outcome_only_reranker_status={getattr(outcome_only_report, 'status', 'not_applicable')}",
            f"outcome_only_base_probe_mode={getattr(outcome_only_base_report, 'probe_mode', 'not_applicable')}",
            f"outcome_only_base_frontier_comparison_status={getattr(outcome_only_base_report, 'frontier_comparison_status', 'not_applicable')}",
            f"outcome_only_base_probe_pass_count={int(getattr(outcome_only_base_report, 'probe_pass_count', 0) or 0)}",
            f"outcome_only_base_improved_probe_count={int(getattr(outcome_only_base_report, 'improved_probe_count', 0) or 0)}",
            f"outcome_only_probe_mode={getattr(outcome_only_report, 'probe_mode', 'unknown')}",
            f"outcome_only_frontier_comparison_status={getattr(outcome_only_report, 'frontier_comparison_status', 'not_applicable')}",
            f"outcome_only_probe_pass_count={int(getattr(outcome_only_report, 'probe_pass_count', 0) or 0)}",
            f"outcome_only_improved_probe_count={int(getattr(outcome_only_report, 'improved_probe_count', 0) or 0)}",
            f"promotion_status={'promote' if promote else 'hold'}",
            *residual_gap_report.summary,
        ],
    ), monotonic_report


def render_skill_program_markdown(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
    candidate_dna: ExpertSkillDNA | None = None,
) -> str | None:
    _, _, candidates = build_skill_realization_candidates(
        skill_name=skill_name,
        description=description,
        task=task,
        references=references,
        scripts=scripts,
        candidate_dna=candidate_dna,
    )
    winner, _, _, _ = choose_skill_realization_candidate(
        skill_name=skill_name,
        task=task,
        candidates=candidates,
    )
    if winner is None:
        return None
    return winner.rendered_markdown


def build_skill_program_authoring_candidate(
    *,
    skill_name: str,
    task_brief: str = "",
    generated_skill_md: str = "",
    design_notes: str = "",
) -> SkillProgramAuthoringCandidate:
    dna_candidate = build_expert_dna_authoring_candidate(
        skill_name=skill_name,
        task_brief=task_brief,
        generated_skill_md=generated_skill_md,
        design_notes=design_notes,
    )
    program = build_skill_program_ir(
        skill_name=skill_name,
        task=task_brief,
        candidate_dna=dna_candidate.candidate_dna,
    )
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    backlog_categories: list[str] = []
    missing_evidence = list(dna_candidate.missing_expert_evidence or [])
    if corpus is None or not corpus.expert_skill_markdown.strip():
        backlog_categories.append("missing_expert_golden")
        if "expert_golden" not in missing_evidence:
            missing_evidence.append("expert_golden")
    if corpus is None or not list(getattr(corpus, "section_corpus", []) or []):
        backlog_categories.append("missing_section_corpus")
    if corpus is None or not corpus.task_probes:
        backlog_categories.append("missing_probe_outputs")
    if not dna_candidate.stable_move_sequence:
        backlog_categories.append("unstable_move_sequence")
        backlog_categories.append("unstable_program_shape")
    if dna_candidate.confidence == "reject":
        backlog_categories.append("generic_program_candidate")
    if program is None:
        backlog_categories.append("program_ir_missing")
    if generated_skill_md:
        lowered = generated_skill_md.lower()
        if _looks_like_generic_shell(generated_skill_md):
            backlog_categories.append("generic_program_candidate")
        if program is not None:
            move_labels = [move.label for move in list(program.execution_spine or [])]
            move_hits = sum(1 for label in move_labels if label.lower() in lowered)
            output_fields = list(program.output_schema.keys())
            output_hits = sum(1 for field in output_fields if field.lower() in lowered)
            if move_labels and move_hits / max(1, len(move_labels)) < 0.5:
                backlog_categories.append("unstable_move_sequence")
            if output_fields and output_hits / max(1, len(output_fields)) < 0.5:
                backlog_categories.append("generic_program_candidate")
    confidence = "ready_for_review"
    if "generic_program_candidate" in backlog_categories:
        confidence = "reject"
    elif backlog_categories:
        confidence = "needs_human_authoring"
    return SkillProgramAuthoringCandidate(
        skill_name=skill_name,
        task_brief=task_brief,
        candidate_program=program
        or SkillProgramIR(
            skill_name=skill_name,
            workflow_surface=str(getattr(dna_candidate.candidate_dna, "workflow_surface", "execution_spine") or "execution_spine"),
            source_skill_name=skill_name,
            source_confidence="candidate",
        ),
        source_confidence=confidence,
        backlog_categories=sorted(set(backlog_categories)),
        missing_expert_evidence=missing_evidence,
        stable_move_sequence=bool(dna_candidate.stable_move_sequence),
        ready_for_review=(confidence == "ready_for_review"),
        confidence=confidence,
        summary=[
            f"confidence={confidence}",
            f"backlog_categories={','.join(sorted(set(backlog_categories))) or 'none'}",
            f"missing_expert_evidence={','.join(missing_evidence) or 'none'}",
        ],
    )


def render_skill_program_authoring_pack_markdown(pack: SkillProgramAuthoringPack) -> str:
    lines = [
        "# Skill Program Authoring Pack",
        "",
        f"- candidate_program_count={pack.candidate_program_count}",
        f"- ready_for_review={len(pack.ready_for_review)}",
        f"- needs_human_authoring={len(pack.needs_human_authoring)}",
        f"- rejected={len(pack.rejected)}",
        f"- backlog_counts={pack.backlog_counts}",
        f"- Summary: {pack.summary}",
    ]
    for candidate in pack.candidates:
        lines.extend(
            [
                "",
                f"## {candidate.skill_name}",
                f"- confidence={candidate.confidence}",
                f"- workflow_surface={candidate.candidate_program.workflow_surface}",
                f"- stable_move_sequence={candidate.stable_move_sequence}",
                f"- backlog_categories={', '.join(candidate.backlog_categories) or 'none'}",
                f"- missing_expert_evidence={', '.join(candidate.missing_expert_evidence) or 'none'}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_expert_evidence_gap_report(candidate: SkillProgramAuthoringCandidate) -> ExpertEvidenceGapReport:
    backlog = set(candidate.backlog_categories or [])
    status = "fail" if backlog else "pass"
    return ExpertEvidenceGapReport(
        skill_name=candidate.skill_name,
        status=status,
        missing_expert_golden="missing_expert_golden" in backlog,
        missing_section_corpus="missing_section_corpus" in backlog,
        missing_probe_outputs="missing_probe_outputs" in backlog,
        unstable_move_sequence="unstable_move_sequence" in backlog,
        unstable_program_shape="unstable_program_shape" in backlog or "unstable_move_sequence" in backlog,
        generic_realization_candidate="generic_realization_candidate" in backlog,
        backlog_categories=sorted(backlog),
        summary=[
            f"expert_evidence_gap_status={status}",
            f"backlog_categories={','.join(sorted(backlog)) or 'none'}",
        ],
    )


def build_skill_program_authoring_pack(
    *,
    cases: list[dict[str, str]] | None = None,
) -> SkillProgramAuthoringPack:
    candidates = [
        build_skill_program_authoring_candidate(
            skill_name=str(case.get("skill_name") or ""),
            task_brief=str(case.get("task") or ""),
            generated_skill_md=str(case.get("generated_skill_md") or ""),
            design_notes=str(case.get("design_notes") or ""),
        )
        for case in list(cases or DEFAULT_AUTHORING_CASES)
    ]
    ready = [candidate.skill_name for candidate in candidates if candidate.confidence == "ready_for_review"]
    needs_human = [candidate.skill_name for candidate in candidates if candidate.confidence == "needs_human_authoring"]
    rejected = [candidate.skill_name for candidate in candidates if candidate.confidence == "reject"]
    backlog_counts = dict(Counter(category for candidate in candidates for category in candidate.backlog_categories))
    pack = SkillProgramAuthoringPack(
        candidates=candidates,
        ready_for_review=ready,
        needs_human_authoring=needs_human,
        rejected=rejected,
        backlog_counts=backlog_counts,
        candidate_program_count=len(candidates),
        summary=(
            f"Skill program authoring complete: candidates={len(candidates)} ready_for_review={len(ready)} "
            f"needs_human_authoring={len(needs_human)} rejected={len(rejected)}"
        ),
    )
    pack.markdown_summary = render_skill_program_authoring_pack_markdown(pack)
    return pack


def render_program_candidate_review_markdown(report: ProgramCandidateReviewReport) -> str:
    lines = [
        "# Skill Program Review",
        "",
        f"- skill_name={report.skill_name}",
        f"- review_status={report.review_status}",
        f"- candidate_confidence={report.candidate_confidence}",
        f"- workflow_surface={report.workflow_surface}",
        f"- approved_for_release_gate={report.approved_for_release_gate}",
        f"- blocking_issues={', '.join(report.blocking_issues) or 'none'}",
    ]
    return "\n".join(lines) + "\n"


def render_program_candidate_review_batch_markdown(batch: ProgramCandidateReviewBatchReport) -> str:
    lines = [
        "# Skill Program Review Batch",
        "",
        f"- pass_count={batch.pass_count}",
        f"- fail_count={batch.fail_count}",
        f"- approved_for_release_gate_count={batch.approved_for_release_gate_count}",
        f"- Summary: {batch.summary}",
    ]
    for report in batch.reports:
        lines.extend(
            [
                "",
                f"## {report.skill_name}",
                f"- review_status={report.review_status}",
                f"- candidate_confidence={report.candidate_confidence}",
                f"- blocking_issues={', '.join(report.blocking_issues) or 'none'}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_program_candidate_review_report(candidate: SkillProgramAuthoringCandidate) -> ProgramCandidateReviewReport:
    program = candidate.candidate_program
    output_field_count = len(list(program.output_schema.keys()))
    checklist = {
        "has_execution_spine": len(program.execution_spine) >= 4,
        "has_output_schema": output_field_count >= 3,
        "has_decision_rules": len(program.decision_rules) >= 3,
        "has_failure_repairs": len(program.failure_repairs) >= 2,
        "has_expert_evidence": not candidate.missing_expert_evidence,
        "stable_move_sequence": candidate.stable_move_sequence,
        "ready_for_review": candidate.confidence == "ready_for_review",
    }
    if program.workflow_surface == "hybrid":
        checklist["has_analysis_blocks"] = len(program.analysis_blocks) >= 2
    blocking = [name for name, passed in checklist.items() if not passed]
    status = "pass" if not blocking else "fail"
    report = ProgramCandidateReviewReport(
        skill_name=candidate.skill_name,
        review_status=status,
        candidate_confidence=candidate.confidence,
        workflow_surface=program.workflow_surface,
        execution_move_count=len(program.execution_spine),
        analysis_block_count=len(program.analysis_blocks),
        output_field_count=output_field_count,
        checklist=checklist,
        blocking_issues=blocking,
        approved_for_release_gate=False,
        summary=[
            f"review_status={status}",
            "approved_for_release_gate=false",
            "candidate program must be checked in explicitly before it can affect fully_correct",
        ],
    )
    report.markdown_summary = render_program_candidate_review_markdown(report)
    return report


def build_program_candidate_review_batch_report(pack: SkillProgramAuthoringPack) -> ProgramCandidateReviewBatchReport:
    reports = [build_program_candidate_review_report(candidate) for candidate in pack.candidates]
    pass_count = sum(1 for report in reports if report.review_status == "pass")
    fail_count = len(reports) - pass_count
    batch = ProgramCandidateReviewBatchReport(
        reports=reports,
        pass_count=pass_count,
        fail_count=fail_count,
        approved_for_release_gate_count=sum(1 for report in reports if report.approved_for_release_gate),
        summary=(
            f"Skill program review complete: reports={len(reports)} pass={pass_count} "
            f"fail={fail_count} auto_enabled=0"
        ),
    )
    batch.markdown_summary = render_program_candidate_review_batch_markdown(batch)
    return batch


def evaluate_negative_case_resistance() -> tuple[float, float, int]:
    failure_cases = [
        failure
        for corpus in load_expert_skill_corpus().values()
        for failure in list(corpus.failure_cases or [])
    ]
    if not failure_cases:
        return 1.0, 1.0, 0
    resisted = 0
    generic_resisted = 0
    for failure in failure_cases:
        candidate = build_skill_program_authoring_candidate(
            skill_name=failure.skill_name,
            task_brief=expert_corpus_entry_for_skill(skill_name=failure.skill_name).task_brief if expert_corpus_entry_for_skill(skill_name=failure.skill_name) is not None else "",
            generated_skill_md=failure.bad_output,
        )
        report = build_program_candidate_review_report(candidate)
        if candidate.confidence == "reject" or report.review_status == "fail":
            resisted += 1
            if failure.failure_type == "generic_shell":
                generic_resisted += 1
    generic_count = sum(1 for item in failure_cases if item.failure_type == "generic_shell")
    return (
        round(resisted / max(1, len(failure_cases)), 4),
        round(generic_resisted / max(1, generic_count), 4),
        len(failure_cases) - resisted,
    )
