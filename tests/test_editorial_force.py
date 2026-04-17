from __future__ import annotations

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.expert_studio import PairwiseEditorialReport, SkillPromotionDecision
from openclaw_skill_create.models.plan import SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.editorial_force import build_skill_editorial_force_report


def _report_stub(**values):
    return type("ReportStub", (), values)()


def test_editorial_force_accepts_decision_loop_outcome_only_breakthrough(monkeypatch):
    monkeypatch.setattr(
        "openclaw_skill_create.services.editorial_force._current_best_markdown",
        lambda _skill_name: "# Current Best\n\nAudit pressure before novelty turns the loop into a solved state.\n",
    )

    report = build_skill_editorial_force_report(
        request=SkillCreateRequestV6(
            task="Create a game design methodology skill for stress-testing a decision loop."
        ),
        skill_plan=SkillPlan(
            skill_name="decision-loop-stress-test",
            skill_archetype="methodology_guidance",
        ),
        artifacts=Artifacts(
            files=[
                ArtifactFile(
                    path="SKILL.md",
                    content=(
                        "---\n"
                        "name: decision-loop-stress-test\n"
                        "---\n"
                        "# Overview\n"
                        "Find the collapse witness before novelty can hide the weak decision, the solved state, the dominant line, the stall point, the repair need, and the reinforcement failure.\n"
                    ),
                    content_type="text/markdown",
                )
            ]
        ),
        body_quality=_report_stub(prompt_echo_ratio=0.0),
        domain_specificity=_report_stub(generic_template_ratio=0.0),
        domain_expertise=_report_stub(generic_expertise_shell_ratio=0.0),
        depth_quality=_report_stub(boundary_rule_coverage=0.75),
        editorial_quality=_report_stub(
            decision_pressure_score=1.0,
            expert_cut_alignment=1.0,
            failure_correction_score=1.0,
            output_executability_score=1.0,
            redundancy_ratio=0.02,
            compression_score=0.9,
            action_density_score=0.8,
        ),
        style_diversity=_report_stub(
            domain_rhythm_score=1.0,
            profile_specific_label_coverage=1.0,
        ),
        move_quality=_report_stub(
            cut_rule_coverage=1.0,
            failure_repair_coverage=1.0,
        ),
        pairwise_editorial=PairwiseEditorialReport(
            skill_name="decision-loop-stress-test",
            decision_pressure_delta=0.0,
        ),
        promotion_decision=SkillPromotionDecision(
            skill_name="decision-loop-stress-test",
            promotion_status="hold",
            reason="hold_due_to_no_primary_win",
            residual_gap_count=0,
            outcome_only_reranker_status="pass",
            outcome_only_probe_mode="probe_expanded_v7",
            outcome_only_frontier_comparison_status="beaten",
            outcome_only_probe_pass_count=8,
            outcome_only_probe_count=8,
            outcome_only_improved_probe_count=2,
        ),
        realization_candidate_count=4,
    )

    assert report.status == "pass"
    assert "pairwise_promotion_not_promoted" not in report.warning_issues
    assert "pairwise_decision_delta_flat" not in report.warning_issues
