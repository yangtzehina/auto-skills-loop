from __future__ import annotations

import json
from pathlib import Path

from ..models.comparison import SkillCreateComparisonReport
from ..models.external_eval import (
    ExternalEvalCriterion,
    ExternalEvalExportBundle,
    ExternalEvalProfile,
    ExternalEvalProbe,
    NormalizedEvalSuite,
)
from .expert_skill_studio import build_profile_residual_targets
from .skill_create_comparison import COMPARISON_CASES, build_skill_create_comparison_report


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXTERNAL_EVAL_ROOT = ROOT / "evals" / "external"


def _criteria_catalog() -> list[ExternalEvalCriterion]:
    return [
        ExternalEvalCriterion(
            criterion_id="program_fidelity",
            label="Program Fidelity",
            description="Check whether the generated skill still preserves the expert execution spine, output schema, and repair logic.",
        ),
        ExternalEvalCriterion(
            criterion_id="task_outcome",
            label="Task Outcome",
            description="Check whether using the skill improves task output quality over a no-skill baseline.",
        ),
        ExternalEvalCriterion(
            criterion_id="editorial_force",
            label="Editorial Force",
            description="Check whether the wording keeps pressure, cut strength, and repair clarity instead of drifting into filler.",
        ),
        ExternalEvalCriterion(
            criterion_id="non_regression",
            label="Frontier Non-Regression",
            description="Check whether the candidate does not regress relative to the active frontier on force, coverage, and compactness.",
            mode="pass_fail",
        ),
        ExternalEvalCriterion(
            criterion_id="quality_checks",
            label="Quality Check Coverage",
            description="Check whether the skill includes the domain-specific checks that should catch bad outputs early.",
        ),
        ExternalEvalCriterion(
            criterion_id="pressure",
            label="Decision Pressure",
            description="Check whether the skill identifies collapse points, stop conditions, and false fixes instead of just adding content.",
        ),
        ExternalEvalCriterion(
            criterion_id="leakage",
            label="Generic Leakage",
            description="Check whether the skill avoids generic surface writing and preserves profile-specific judgment.",
        ),
        ExternalEvalCriterion(
            criterion_id="false_fix_rejection",
            label="False Fix Rejection",
            description="Check whether the skill rejects content padding when the real issue is structural.",
            mode="pass_fail",
        ),
    ]


def _adversarial_probe_specs() -> dict[str, list[dict[str, object]]]:
    return {
        "concept-to-mvp-pack": [
            {
                "probe_id": "concept.validation-question-cannot-fail",
                "task": "Evaluate an MVP pack where the validation question sounds attractive but could not actually fail in a short playtest.",
                "criteria": ["quality_checks", "task_outcome", "leakage"],
                "expected_signals": ["validation question can fail", "kill list", "redesign trigger"],
            },
            {
                "probe_id": "concept.support-system-masquerade",
                "task": "Evaluate an MVP pack where support systems are being justified as must-have core features.",
                "criteria": ["quality_checks", "editorial_force", "task_outcome"],
                "expected_signals": ["scope creep", "support systems", "out of scope", "re-entry condition"],
            },
            {
                "probe_id": "concept.no-kill-or-greenlight",
                "task": "Evaluate an MVP pack that sounds complete but still cannot kill or greenlight the first playable.",
                "criteria": ["quality_checks", "task_outcome", "program_fidelity"],
                "expected_signals": ["build recommendation", "failure evidence", "success criteria"],
            },
        ],
        "decision-loop-stress-test": [
            {
                "probe_id": "decision.novelty-masks-weak-choice",
                "task": "Audit a loop whose first-hour novelty hides the fact that the core choice is weak.",
                "criteria": ["pressure", "false_fix_rejection", "task_outcome"],
                "expected_signals": ["first hour", "surface excitement", "weak pressure", "collapse signal"],
            },
            {
                "probe_id": "decision.midgame-autopilot",
                "task": "Audit a loop with lots of content where midgame still collapses into autopilot.",
                "criteria": ["pressure", "task_outcome", "editorial_force"],
                "expected_signals": ["midgame", "autopilot", "dominant strategy", "structural fix"],
            },
            {
                "probe_id": "decision.fake-repair-by-content",
                "task": "Audit a loop where the proposed repair is just more content, events, or rewards instead of a pressure change.",
                "criteria": ["pressure", "false_fix_rejection", "editorial_force"],
                "expected_signals": ["false fix", "structural repair", "pressure problem", "reject content padding"],
            },
            {
                "probe_id": "decision.mastery-throughput-only",
                "task": "Audit a loop where mastery only improves throughput and never creates a new decision problem.",
                "criteria": ["pressure", "false_fix_rejection", "task_outcome"],
                "expected_signals": ["mastery", "throughput", "new decision problem", "solved state"],
            },
        ],
        "simulation-resource-loop-design": [
            {
                "probe_id": "simulation.invisible-pressure",
                "task": "Audit a resource loop where the pressure relationships exist but the player cannot read them early enough to plan.",
                "criteria": ["leakage", "task_outcome", "editorial_force"],
                "expected_signals": ["pressure web", "visible pressure", "player-facing tradeoffs"],
            },
            {
                "probe_id": "simulation.cheap-recovery",
                "task": "Audit a resource loop where recovery keeps no real cost and failure has no structural consequence.",
                "criteria": ["leakage", "false_fix_rejection", "task_outcome"],
                "expected_signals": ["cheap recovery", "costly recovery", "lasting consequence"],
            },
            {
                "probe_id": "simulation.dominant-currency-bypass",
                "task": "Audit a resource loop where one dominant currency bypasses the intended tension web.",
                "criteria": ["leakage", "editorial_force", "task_outcome"],
                "expected_signals": ["dominant currency", "counterpressure", "tension web"],
            },
            {
                "probe_id": "simulation.fantasy-detached",
                "task": "Audit a resource loop whose pressure math is functional but detached from the intended emotional fantasy.",
                "criteria": ["leakage", "editorial_force", "task_outcome"],
                "expected_signals": ["fantasy fit", "emotional fantasy", "pressure relationship"],
            },
        ],
    }


def _current_frontier_metrics(case) -> dict[str, float]:
    auto = case.auto_metrics
    return {
        "decision_pressure_score": float(auto.decision_pressure_score or 0.0),
        "failure_repair_force": float(auto.failure_repair_force or 0.0),
        "section_force_distinctness": float(auto.section_force_distinctness or 0.0),
        "domain_move_coverage": float(auto.domain_move_coverage or 0.0),
        "section_depth_score": float(auto.section_depth_score or 0.0),
        "task_outcome_with_skill_average": float(auto.task_outcome_with_skill_average or 0.0),
        "redundancy_ratio": float(auto.redundancy_ratio or 0.0),
        "generic_surface_leakage": float(auto.generic_surface_leakage or 0.0),
        "expert_pitfall_cluster_recall": float(auto.expert_pitfall_cluster_recall or 0.0),
        "output_field_guidance_coverage": float(auto.output_field_guidance_coverage or 0.0),
        "generic_skeleton_ratio": float(auto.generic_skeleton_ratio or 0.0),
        "compression_without_loss": float(auto.compression_without_loss or 0.0),
    }


def build_normalized_eval_suite(
    *,
    comparison_report: SkillCreateComparisonReport | None = None,
) -> NormalizedEvalSuite:
    report = comparison_report or build_skill_create_comparison_report(include_hermes=False)
    criteria = _criteria_catalog()
    criteria_ids = [item.criterion_id for item in criteria]
    probe_specs = _adversarial_probe_specs()
    cases_by_skill = {case.skill_name: case for case in list(report.cases or [])}
    profiles: list[ExternalEvalProfile] = []
    probes: list[ExternalEvalProbe] = []
    current_frontier_metrics: dict[str, dict[str, float]] = {}
    expected_signals: dict[str, list[str]] = {}
    for case_def in COMPARISON_CASES:
        skill_name = str(case_def["skill_name"])
        case = cases_by_skill.get(skill_name)
        if case is None:
            continue
        residual_targets = build_profile_residual_targets(skill_name)
        profile_metrics = _current_frontier_metrics(case)
        current_frontier_metrics[skill_name] = dict(profile_metrics)
        target_signals = [
            f"{metric}>={value:.4f}" if metric not in {"generic_surface_leakage", "redundancy_ratio", "generic_skeleton_ratio"} else f"{metric}<={value:.4f}"
            for metric, value in dict(residual_targets.target_metrics or {}).items()
        ]
        expected_signals[skill_name] = target_signals
        profile_probe_ids: list[str] = []
        for payload in probe_specs.get(skill_name, []):
            probe = ExternalEvalProbe(
                probe_id=str(payload["probe_id"]),
                skill_name=skill_name,
                task=str(payload["task"]),
                probe_family="adversarial",
                criteria=[item for item in list(payload.get("criteria") or []) if item in criteria_ids],
                expected_signals=[str(item) for item in list(payload.get("expected_signals") or [])],
                pass_expectation="pass",
            )
            probes.append(probe)
            profile_probe_ids.append(probe.probe_id)
        profiles.append(
            ExternalEvalProfile(
                skill_name=skill_name,
                active_frontier_version="frontier_v3",
                current_frontier_metrics=profile_metrics,
                residual_targets={str(k): float(v) for k, v in dict(residual_targets.target_metrics or {}).items()},
                expected_signals=target_signals,
                probe_ids=profile_probe_ids,
            )
        )
    return NormalizedEvalSuite(
        suite_version="frontier_v3",
        profiles=profiles,
        probes=probes,
        criteria=criteria,
        current_frontier_metrics=current_frontier_metrics,
        expected_signals=expected_signals,
        summary=[
            "suite_version=frontier_v3",
            f"profile_count={len(profiles)}",
            f"probe_count={len(probes)}",
            f"criteria_count={len(criteria)}",
        ],
    )


def _render_promptfoo_yaml(suite: NormalizedEvalSuite) -> str:
    return "\n".join(
        [
            f"description: {suite.suite_version} external eval export",
            "prompts:",
            "  - \"{{task}}\"",
            "providers:",
            "  - \"openai:gpt-5.4\"",
            "tests: file://cases.json",
            "",
        ]
    )


def _render_promptfoo_cases(suite: NormalizedEvalSuite) -> list[dict[str, object]]:
    criteria_lookup = {item.criterion_id: item.label for item in list(suite.criteria or [])}
    cases: list[dict[str, object]] = []
    for probe in list(suite.probes or []):
        cases.append(
            {
                "description": probe.probe_id,
                "vars": {
                    "skill_name": probe.skill_name,
                    "task": probe.task,
                    "expected_signals": list(probe.expected_signals or []),
                },
                "assert": [
                    {
                        "type": "contains-all",
                        "value": list(probe.expected_signals or []),
                    },
                    {
                        "type": "rubric",
                        "value": [criteria_lookup.get(item, item) for item in list(probe.criteria or [])],
                    },
                ],
                "metadata": {
                    "probe_family": probe.probe_family,
                    "pass_expectation": probe.pass_expectation,
                },
            }
        )
    return cases


def _render_openai_evals_suite(suite: NormalizedEvalSuite) -> dict[str, object]:
    return {
        "suite_version": suite.suite_version,
        "format": "criteria-first",
        "criteria": [item.model_dump(mode="json") for item in list(suite.criteria or [])],
        "items": [
            {
                "probe_id": probe.probe_id,
                "skill_name": probe.skill_name,
                "input": probe.task,
                "criteria": list(probe.criteria or []),
                "expected_signals": list(probe.expected_signals or []),
                "pass_expectation": probe.pass_expectation,
            }
            for probe in list(suite.probes or [])
        ],
        "profiles": [profile.model_dump(mode="json") for profile in list(suite.profiles or [])],
    }


def render_external_eval_export_markdown(bundle: ExternalEvalExportBundle) -> str:
    lines = ["# External Eval Export", ""]
    lines.extend(f"- {item}" for item in list(bundle.summary or []))
    return "\n".join(lines).rstrip() + "\n"


def build_external_eval_export_bundle(
    *,
    targets: list[str] | tuple[str, ...],
    output_root: Path | None = None,
    comparison_report: SkillCreateComparisonReport | None = None,
) -> ExternalEvalExportBundle:
    normalized_targets = [item.strip().lower() for item in list(targets or []) if item and item.strip()]
    if not normalized_targets:
        normalized_targets = ["promptfoo", "openai"]
    suite = build_normalized_eval_suite(comparison_report=comparison_report)
    root = (output_root or DEFAULT_EXTERNAL_EVAL_ROOT).expanduser()
    root.mkdir(parents=True, exist_ok=True)

    normalized_path = root / "normalized_eval_suite.json"
    normalized_path.write_text(json.dumps(suite.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    promptfoo_config_path = root / "promptfoo" / "promptfoo.yaml"
    promptfoo_cases_path = root / "promptfoo" / "cases.json"
    openai_suite_path = root / "openai_evals" / "suite.json"
    generated_targets = ["normalized"]

    if "promptfoo" in normalized_targets:
        promptfoo_config_path.parent.mkdir(parents=True, exist_ok=True)
        promptfoo_config_path.write_text(_render_promptfoo_yaml(suite), encoding="utf-8")
        promptfoo_cases_path.write_text(
            json.dumps(_render_promptfoo_cases(suite), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        generated_targets.append("promptfoo")

    if "openai" in normalized_targets or "openai_evals" in normalized_targets:
        openai_suite_path.parent.mkdir(parents=True, exist_ok=True)
        openai_suite_path.write_text(
            json.dumps(_render_openai_evals_suite(suite), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        generated_targets.append("openai")

    bundle = ExternalEvalExportBundle(
        normalized_eval_suite_path=str(normalized_path),
        promptfoo_config_path=str(promptfoo_config_path),
        promptfoo_cases_path=str(promptfoo_cases_path),
        openai_evals_suite_path=str(openai_suite_path),
        generated_targets=generated_targets,
        summary=[
            f"suite_version={suite.suite_version}",
            f"profile_count={len(list(suite.profiles or []))}",
            f"probe_count={len(list(suite.probes or []))}",
            f"generated_targets={','.join(generated_targets)}",
            f"normalized_eval_suite={normalized_path}",
            f"promptfoo_config={promptfoo_config_path}",
            f"promptfoo_cases={promptfoo_cases_path}",
            f"openai_evals_suite={openai_suite_path}",
        ],
    )
    bundle.markdown_summary = render_external_eval_export_markdown(bundle)
    return bundle
