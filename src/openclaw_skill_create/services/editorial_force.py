from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.expert_studio import SkillEditorialForceReport
from .body_quality import _artifact_content, split_frontmatter
from .domain_expertise import build_skill_domain_expertise_report
from .domain_specificity import build_skill_domain_specificity_report
from .style_diversity import build_skill_style_diversity_report, shared_opening_ratio, style_signature_from_markdown

ROOT = Path(__file__).resolve().parents[3]
CURRENT_BEST_GOLDEN_ROOT = ROOT / 'tests' / 'fixtures' / 'methodology_guidance' / 'golden'


def _current_best_markdown(skill_name: str) -> str:
    path = CURRENT_BEST_GOLDEN_ROOT / f'{skill_name}.md'
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8')


def build_skill_editorial_force_report(
    *,
    request: Any,
    skill_plan: Any,
    artifacts: Artifacts,
    body_quality: Any = None,
    domain_specificity: Any = None,
    domain_expertise: Any = None,
    depth_quality: Any = None,
    editorial_quality: Any = None,
    style_diversity: Any = None,
    move_quality: Any = None,
    pairwise_editorial: Any = None,
    promotion_decision: Any = None,
    realization_candidate_count: int = 0,
) -> SkillEditorialForceReport:
    skill_md = _artifact_content(artifacts, 'SKILL.md')
    frontmatter, _ = split_frontmatter(skill_md)
    skill_name = str(getattr(skill_plan, 'skill_name', '') or frontmatter.get('name', '') or '')
    skill_archetype = str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower()
    if skill_archetype != 'methodology_guidance':
        return SkillEditorialForceReport(
            skill_name=skill_name,
            skill_archetype=skill_archetype,
            status='pass',
            summary=['editorial_force_status=pass', 'editorial_force_skipped=non_methodology'],
        )

    if domain_specificity is None:
        domain_specificity = build_skill_domain_specificity_report(request=request, skill_plan=skill_plan, artifacts=artifacts)
    if domain_expertise is None:
        domain_expertise = build_skill_domain_expertise_report(request=request, skill_plan=skill_plan, artifacts=artifacts)
    if depth_quality is None:
        from .depth_quality import build_skill_depth_quality_report

        depth_quality = build_skill_depth_quality_report(request=request, skill_plan=skill_plan, artifacts=artifacts)
    if style_diversity is None:
        style_diversity = build_skill_style_diversity_report(request=request, skill_plan=skill_plan, artifacts=artifacts)

    decision_pressure = float(getattr(editorial_quality, 'decision_pressure_score', 0.0) or 0.0)
    cut_sharpness = round(
        (0.65 * float(getattr(editorial_quality, 'expert_cut_alignment', 0.0) or 0.0))
        + (0.35 * float(getattr(move_quality, 'cut_rule_coverage', 0.0) or 0.0)),
        4,
    )
    failure_repair_force = round(
        (0.55 * float(getattr(editorial_quality, 'failure_correction_score', 0.0) or 0.0))
        + (0.45 * float(getattr(move_quality, 'failure_repair_coverage', 0.0) or 0.0)),
        4,
    )
    boundary_rule_coverage = round(float(getattr(depth_quality, 'boundary_rule_coverage', 0.0) or 0.0), 4)
    output_executability = round(float(getattr(editorial_quality, 'output_executability_score', 0.0) or 0.0), 4)
    anti_filler_score = round(
        max(
            0.0,
            (
                0.50 * max(0.0, 1.0 - float(getattr(editorial_quality, 'redundancy_ratio', 0.0) or 0.0))
                + 0.30 * max(0.0, 1.0 - float(getattr(body_quality, 'prompt_echo_ratio', 0.0) or 0.0))
                + 0.20 * max(0.0, 1.0 - float(getattr(domain_specificity, 'generic_template_ratio', 0.0) or 0.0))
            ),
        ),
        4,
    )
    section_rhythm_distinctness = float(getattr(style_diversity, 'domain_rhythm_score', 0.0) or 0.0)
    section_force_distinctness = round(
        (
            0.60 * float(getattr(style_diversity, 'domain_rhythm_score', 0.0) or 0.0)
            + 0.40 * float(getattr(style_diversity, 'profile_specific_label_coverage', 0.0) or 0.0)
        ),
        4,
    )

    current_best = _current_best_markdown(skill_name)
    if current_best:
        current_signature = style_signature_from_markdown(current_best)
        current_opening = str(current_signature.get('opening') or '')
        current_overlap = shared_opening_ratio(style_signature_from_markdown(skill_md).get('opening', ''), current_opening)
        if current_overlap >= 0.95:
            opening_distinctness = round(float(getattr(style_diversity, 'profile_specific_label_coverage', 0.0) or 0.0), 4)
        else:
            opening_distinctness = round(max(0.0, 1.0 - current_overlap), 4)
    else:
        opening_distinctness = round(float(getattr(style_diversity, 'profile_specific_label_coverage', 0.0) or 0.0), 4)

    compression_without_loss = round(
        (0.60 * float(getattr(editorial_quality, 'compression_score', 0.0) or 0.0))
        + (0.40 * float(getattr(editorial_quality, 'action_density_score', 0.0) or 0.0)),
        4,
    )
    generic_surface_leakage = round(
        max(
            float(getattr(body_quality, 'prompt_echo_ratio', 0.0) or 0.0),
            float(getattr(domain_specificity, 'generic_template_ratio', 0.0) or 0.0),
            float(getattr(domain_expertise, 'generic_expertise_shell_ratio', 0.0) or 0.0),
        ),
        4,
    )
    stop_condition_keywords = {
        'concept-to-mvp-pack': ['out of scope', 'kill', 'cut', 'fail', 'playtest signal', 'build recommendation'],
        'decision-loop-stress-test': ['collapse', 'solved state', 'dominant', 'stall', 'repair', 'reinforcement'],
        'simulation-resource-loop-design': ['runaway', 'recovery', 'cost', 'pressure', 'loop', 'fantasy'],
    }.get(skill_name, ['fail', 'repair', 'cut', 'output'])
    lowered_skill = skill_md.lower()
    stop_condition_hits = sum(1 for token in stop_condition_keywords if token in lowered_skill)
    stop_condition_coverage = round(min(1.0, stop_condition_hits / 4.0), 4)

    primary_force_metrics = {
        'decision_pressure_score': decision_pressure,
        'cut_sharpness_score': cut_sharpness,
        'failure_repair_force': failure_repair_force,
        'boundary_rule_coverage': boundary_rule_coverage,
        'stop_condition_coverage': stop_condition_coverage,
        'output_executability_score': output_executability,
        'section_force_distinctness': section_force_distinctness,
    }

    blocking: list[str] = []
    warnings: list[str] = []
    profile_thresholds = {
        'concept-to-mvp-pack': {
            'decision_pressure_score': 0.72,
            'cut_sharpness_score': 0.74,
            'boundary_rule_coverage': 0.20,
            'output_executability_score': 0.70,
        },
        'decision-loop-stress-test': {
            'decision_pressure_score': 0.78,
            'cut_sharpness_score': 0.70,
            'failure_repair_force': 0.74,
            'stop_condition_coverage': 0.45,
        },
        'simulation-resource-loop-design': {
            'decision_pressure_score': 0.72,
            'failure_repair_force': 0.72,
            'section_force_distinctness': 0.70,
            'boundary_rule_coverage': 0.20,
        },
    }.get(
        skill_name,
        {
            'decision_pressure_score': 0.70,
            'cut_sharpness_score': 0.70,
            'failure_repair_force': 0.70,
            'output_executability_score': 0.70,
        },
    )
    for metric_name, threshold in profile_thresholds.items():
        if float(primary_force_metrics.get(metric_name, 0.0) or 0.0) < threshold:
            blocking.append(f'{metric_name}_low')
    if section_rhythm_distinctness < 0.65:
        warnings.append('weak_section_rhythm_distinctness')
    if opening_distinctness < 0.60:
        warnings.append('opening_distinctness_soft')
    if compression_without_loss < 0.65:
        blocking.append('compression_without_loss_low')
    if generic_surface_leakage > 0.35:
        blocking.append('generic_surface_leakage')
    if anti_filler_score < 0.72:
        blocking.append('anti_filler_score_low')
    if realization_candidate_count and realization_candidate_count < 2:
        warnings.append('single_realization_candidate')
    promotion_status = str(getattr(promotion_decision, 'promotion_status', '') or '')
    promotion_reason = str(getattr(promotion_decision, 'reason', '') or '')
    if (
        promotion_decision is not None
        and promotion_status != 'promote'
        and promotion_reason != 'stable_but_no_breakthrough'
    ):
        warnings.append('pairwise_promotion_not_promoted')
    if (
        pairwise_editorial is not None
        and promotion_status != 'promote'
        and promotion_reason != 'stable_but_no_breakthrough'
        and float(getattr(pairwise_editorial, 'decision_pressure_delta', 0.0) or 0.0) <= 0
    ):
        warnings.append('pairwise_decision_delta_flat')

    status = 'fail' if blocking else ('warn' if warnings else 'pass')
    return SkillEditorialForceReport(
        skill_name=skill_name,
        skill_archetype=skill_archetype,
        status=status,
        decision_pressure_score=decision_pressure,
        cut_sharpness_score=cut_sharpness,
        failure_repair_force=failure_repair_force,
        boundary_rule_coverage=boundary_rule_coverage,
        stop_condition_coverage=stop_condition_coverage,
        output_executability_score=output_executability,
        anti_filler_score=anti_filler_score,
        section_force_distinctness=section_force_distinctness,
        section_rhythm_distinctness=section_rhythm_distinctness,
        opening_distinctness=opening_distinctness,
        compression_without_loss=compression_without_loss,
        generic_surface_leakage=generic_surface_leakage,
        blocking_issues=sorted(set(blocking)),
        warning_issues=sorted(set(warnings)),
        primary_force_metrics=primary_force_metrics,
        summary=[
            f'editorial_force_status={status}',
            f'decision_pressure_score={decision_pressure:.2f}',
            f'cut_sharpness_score={cut_sharpness:.2f}',
            f'failure_repair_force={failure_repair_force:.2f}',
            f'boundary_rule_coverage={boundary_rule_coverage:.2f}',
            f'stop_condition_coverage={stop_condition_coverage:.2f}',
            f'output_executability_score={output_executability:.2f}',
            f'anti_filler_score={anti_filler_score:.2f}',
            f'section_force_distinctness={section_force_distinctness:.2f}',
            f'section_rhythm_distinctness={section_rhythm_distinctness:.2f}',
            f'opening_distinctness={opening_distinctness:.2f}',
            f'compression_without_loss={compression_without_loss:.2f}',
            f'generic_surface_leakage={generic_surface_leakage:.2f}',
        ],
    )


def editorial_force_artifact(report: SkillEditorialForceReport) -> ArtifactFile:
    return ArtifactFile(
        path='evals/editorial_force.json',
        content=json.dumps(report.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['editorial_force'],
        status='new',
    )
