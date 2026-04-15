from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.comparison import (
    SkillCreateComparisonCaseResult,
    SkillCreateComparisonMetrics,
    SkillCreateComparisonReport,
)
from ..models.persistence import PersistencePolicy
from ..models.plan import PlannedFile, SkillPlan
from ..models.request import SkillCreateRequestV6
from .body_quality import build_skill_body_quality_report, build_skill_self_review_report
from .depth_quality import build_skill_depth_quality_report
from .domain_expertise import build_skill_domain_expertise_report
from .domain_specificity import build_skill_domain_specificity_report
from .expert_structure import build_skill_expert_structure_report
from .orchestrator import run_skill_create


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPARISON_GOLDEN_ROOT = ROOT / 'tests' / 'fixtures' / 'methodology_guidance' / 'golden'
DEFAULT_EXPERT_DEPTH_GOLDEN_ROOT = ROOT / 'tests' / 'fixtures' / 'methodology_guidance' / 'expert_depth_golden'


def _default_hermes_wrappers() -> list[Path]:
    configured = [
        Path(value).expanduser()
        for value in os.environ.get('HERMES_SKILL_CREATE_WRAPPER', '').split(os.pathsep)
        if value.strip()
    ]
    home = Path.home()
    return configured + [
        home / '.openclaw' / 'workspace' / 'skills' / 'skill-create-agent' / 'scripts' / 'run_skill_create.py',
        home / 'hermes-openclaw-migration' / 'backups' / '20260414-111432' / 'openclaw' / 'workspace' / 'skills' / 'skill-create-agent' / 'scripts' / 'run_skill_create.py',
    ]


def _default_anthropic_skill_creator_paths() -> list[Path]:
    configured = [
        Path(value).expanduser()
        for value in os.environ.get('ANTHROPIC_SKILL_CREATOR_PATH', '').split(os.pathsep)
        if value.strip()
    ]
    home = Path.home()
    return configured + [
        home / '.openclaw' / 'workspace' / 'external-refs' / 'anthropics-skills' / 'skills' / 'skill-creator' / 'SKILL.md',
        home / 'anthropics-skills' / 'skills' / 'skill-creator' / 'SKILL.md',
    ]

COMPARISON_CASES = [
    {
        'case_id': 'concept-to-mvp-pack',
        'skill_name': 'concept-to-mvp-pack',
        'task': 'Create a game design methodology skill that turns a rough game concept into a scoped MVP pack with workflow, output template, quality checks, and common pitfalls.',
    },
    {
        'case_id': 'decision-loop-stress-test',
        'skill_name': 'decision-loop-stress-test',
        'task': 'Create a game design methodology skill for stress-testing a decision loop, including when to use it, workflow, output format, guardrails, and failure modes.',
    },
    {
        'case_id': 'simulation-resource-loop-design',
        'skill_name': 'simulation-resource-loop-design',
        'task': 'Create a game design methodology skill for designing a simulation resource loop, with structured inputs, workflow, output template, quality checks, and pitfalls.',
    },
]


def _artifact_skill_md(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path='SKILL.md', content=content, content_type='text/markdown')])


def _skill_md_content(artifacts: Artifacts) -> str:
    for file in list(artifacts.files or []):
        if file.path == 'SKILL.md':
            return file.content or ''
    return ''


def _request(case: dict[str, str]) -> SkillCreateRequestV6:
    return SkillCreateRequestV6(
        task=case['task'],
        skill_name_hint=case['skill_name'],
        skill_archetype='methodology_guidance',
        enable_eval_scaffold=True,
    )


def _plan(case: dict[str, str]) -> SkillPlan:
    return SkillPlan(
        skill_name=case['skill_name'],
        skill_archetype='methodology_guidance',
        files_to_create=[PlannedFile(path='SKILL.md', purpose='entry', source_basis=[])],
    )


def _metrics_from_reports(
    *,
    body_quality,
    self_review,
    domain_specificity=None,
    domain_expertise=None,
    expert_structure=None,
    depth_quality=None,
    severity: str = '',
    fully_correct: bool = False,
) -> SkillCreateComparisonMetrics:
    depth_blocking_count = len(list(getattr(depth_quality, 'blocking_issues', []) or []))
    return SkillCreateComparisonMetrics(
        body_lines=int(getattr(body_quality, 'body_lines', 0) or 0),
        body_chars=int(getattr(body_quality, 'body_chars', 0) or 0),
        heading_count=int(getattr(body_quality, 'heading_count', 0) or 0),
        bullet_count=int(getattr(body_quality, 'bullet_count', 0) or 0),
        numbered_step_count=int(getattr(body_quality, 'numbered_step_count', 0) or 0),
        required_sections_present=list(getattr(body_quality, 'required_sections_present', []) or []),
        missing_required_sections=list(getattr(body_quality, 'missing_required_sections', []) or []),
        prompt_echo_ratio=float(getattr(body_quality, 'prompt_echo_ratio', 0.0) or 0.0),
        description_body_ratio=float(getattr(body_quality, 'description_body_ratio', 0.0) or 0.0),
        body_quality_status=str(getattr(body_quality, 'status', 'unknown') or 'unknown'),
        self_review_status=str(getattr(self_review, 'status', 'unknown') or 'unknown'),
        domain_specificity_status=str(getattr(domain_specificity, 'status', 'unknown') or 'unknown'),
        domain_anchor_coverage=float(getattr(domain_specificity, 'domain_anchor_coverage', 0.0) or 0.0),
        missing_domain_anchors=list(getattr(domain_specificity, 'missing_domain_anchors', []) or []),
        generic_template_ratio=float(getattr(domain_specificity, 'generic_template_ratio', 0.0) or 0.0),
        cross_case_similarity=float(getattr(domain_specificity, 'cross_case_similarity', 0.0) or 0.0),
        domain_expertise_status=str(getattr(domain_expertise, 'status', 'unknown') or 'unknown'),
        domain_move_coverage=float(getattr(domain_expertise, 'domain_move_coverage', 0.0) or 0.0),
        prompt_phrase_echo_ratio=float(getattr(domain_expertise, 'prompt_phrase_echo_ratio', 0.0) or 0.0),
        generic_expertise_shell_ratio=float(getattr(domain_expertise, 'generic_expertise_shell_ratio', 0.0) or 0.0),
        expert_structure_status=str(getattr(expert_structure, 'status', 'unknown') or 'unknown'),
        expert_heading_recall=float(getattr(expert_structure, 'expert_heading_recall', 0.0) or 0.0),
        expert_action_cluster_recall=float(getattr(expert_structure, 'expert_action_cluster_recall', 0.0) or 0.0),
        expert_output_field_recall=float(getattr(expert_structure, 'expert_output_field_recall', 0.0) or 0.0),
        expert_pitfall_cluster_recall=float(getattr(expert_structure, 'expert_pitfall_cluster_recall', 0.0) or 0.0),
        expert_quality_check_recall=float(getattr(expert_structure, 'expert_quality_check_recall', 0.0) or 0.0),
        generated_vs_generated_heading_overlap=float(getattr(expert_structure, 'generated_vs_generated_heading_overlap', 0.0) or 0.0),
        generated_vs_generated_line_jaccard=float(getattr(expert_structure, 'generated_vs_generated_line_jaccard', 0.0) or 0.0),
        generic_skeleton_ratio=float(getattr(expert_structure, 'generic_skeleton_ratio', 0.0) or 0.0),
        depth_quality_status=str(getattr(depth_quality, 'status', 'unknown') or 'unknown'),
        expert_depth_recall=float(getattr(depth_quality, 'expert_depth_recall', 0.0) or 0.0),
        section_depth_score=float(getattr(depth_quality, 'section_depth_score', 0.0) or 0.0),
        decision_probe_count=int(getattr(depth_quality, 'decision_probe_count', 0) or 0),
        worked_example_count=int(getattr(depth_quality, 'worked_example_count', 0) or 0),
        failure_pattern_density=int(getattr(depth_quality, 'failure_pattern_density', 0) or 0),
        output_field_guidance_coverage=float(getattr(depth_quality, 'output_field_guidance_coverage', 0.0) or 0.0),
        boundary_rule_coverage=float(getattr(depth_quality, 'boundary_rule_coverage', 0.0) or 0.0),
        depth_gap_count=depth_blocking_count,
        fully_correct=bool(fully_correct),
        severity=str(severity or ''),
    )


def _metrics_from_markdown(case: dict[str, str], content: str) -> tuple[SkillCreateComparisonMetrics, Any, Any, Any, Any, Any, Any]:
    request = _request(case)
    plan = _plan(case)
    artifacts = _artifact_skill_md(content)
    body_quality = build_skill_body_quality_report(request=request, skill_plan=plan, artifacts=artifacts)
    self_review = build_skill_self_review_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
        body_quality=body_quality,
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
    depth_quality = build_skill_depth_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    return (
        _metrics_from_reports(
            body_quality=body_quality,
            self_review=self_review,
            domain_specificity=domain_specificity,
            domain_expertise=domain_expertise,
            expert_structure=expert_structure,
            depth_quality=depth_quality,
            severity='reference',
            fully_correct=(
                body_quality.passed
                and self_review.status == 'pass'
                and domain_specificity.status == 'pass'
                and domain_expertise.status == 'pass'
                and expert_structure.status == 'pass'
                and depth_quality.status == 'pass'
            ),
        ),
        body_quality,
        self_review,
        domain_specificity,
        domain_expertise,
        expert_structure,
        depth_quality,
    )


def _run_auto_case(case: dict[str, str]) -> tuple[SkillCreateComparisonMetrics, Any, Any, Any, Any, Any, Any, str]:
    with tempfile.TemporaryDirectory(prefix='auto-skills-loop-comparison-') as tmpdir:
        response = run_skill_create(
            _request(case),
            output_root=str(Path(tmpdir) / 'generated'),
            persistence_policy=PersistencePolicy(
                dry_run=False,
                overwrite=True,
                persist_evaluation_report=True,
            ),
            fail_fast_on_validation_fail=False,
        )
    body_quality = getattr(response.diagnostics, 'body_quality', None) if response.diagnostics is not None else None
    self_review = getattr(response.diagnostics, 'self_review', None) if response.diagnostics is not None else None
    domain_specificity = getattr(response.diagnostics, 'domain_specificity', None) if response.diagnostics is not None else None
    domain_expertise = getattr(response.diagnostics, 'domain_expertise', None) if response.diagnostics is not None else None
    expert_structure = getattr(response.diagnostics, 'expert_structure', None) if response.diagnostics is not None else None
    depth_quality = getattr(response.diagnostics, 'depth_quality', None) if response.diagnostics is not None else None
    return (
        _metrics_from_reports(
            body_quality=body_quality,
            self_review=self_review,
            domain_specificity=domain_specificity,
            domain_expertise=domain_expertise,
            expert_structure=expert_structure,
            depth_quality=depth_quality,
            severity=response.severity,
            fully_correct=bool(getattr(response.quality_review, 'fully_correct', False)),
        ),
        body_quality,
        self_review,
        domain_specificity,
        domain_expertise,
        expert_structure,
        depth_quality,
        _skill_md_content(response.artifacts),
    )


def _find_hermes_wrapper(paths: list[Path] | None = None) -> Path | None:
    for path in list(paths or _default_hermes_wrappers()):
        if path.exists() and path.is_file():
            return path
    return None


def _hermes_independence_status(wrapper: Path | None) -> str:
    if wrapper is None:
        return 'golden_only'
    try:
        content = wrapper.read_text(encoding='utf-8')
    except OSError:
        return 'golden_only'
    if 'AUTO_SKILLS_LOOP_PROJECT_ROOT' in content or 'auto-skills-loop' in content:
        return 'same_backend'
    return 'independent'


def _run_hermes_case(case: dict[str, str], wrapper: Path) -> tuple[SkillCreateComparisonMetrics | None, str | None]:
    with tempfile.TemporaryDirectory(prefix='hermes-skill-create-comparison-') as tmpdir:
        output_root = Path(tmpdir) / 'generated'
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        proc = subprocess.run(
            [
                sys.executable,
                str(wrapper),
                '--task',
                case['task'],
                '--skill-name',
                case['skill_name'],
                '--apply',
                '--overwrite',
                '--output-root',
                str(output_root),
                '--disable-openspace-observation',
                '--disable-skill-governance-sync',
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if proc.returncode != 0:
            return None, proc.stderr.strip() or proc.stdout.strip() or f'Hermes wrapper exited {proc.returncode}'
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None, 'Hermes wrapper did not emit JSON'
        persistence = payload.get('persistence') if isinstance(payload, dict) else {}
        generated_root = Path(str((persistence or {}).get('output_root') or output_root / case['skill_name']))
        skill_md = generated_root / 'SKILL.md'
        if not skill_md.exists():
            return None, f'Hermes wrapper did not write SKILL.md under {generated_root}'
        metrics, _, _, _, _, _, _ = _metrics_from_markdown(case, skill_md.read_text(encoding='utf-8'))
        metrics.severity = str(payload.get('severity') or '')
        return metrics, None


def _golden_content(case: dict[str, str], golden_root: Path) -> str:
    path = golden_root / f'{case["case_id"]}.md'
    if not path.exists():
        raise ValueError(f'Missing golden baseline: {path}')
    return path.read_text(encoding='utf-8')


def _body_tokens(content: str) -> set[str]:
    tokens = {
        token.lower()
        for token in content.replace('```', ' ').split()
        if len(token.strip('`*#:-,.<>')) >= 4
    }
    return {
        token.strip('`*#:-,.<>')
        for token in tokens
        if token.strip('`*#:-,.<>')
        and token.strip('`*#:-,.<>') not in {'overview', 'workflow', 'output', 'format', 'quality', 'checks', 'common', 'pitfalls'}
    }


def _content_similarity(left: str, right: str) -> float:
    left_tokens = _body_tokens(left)
    right_tokens = _body_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens)), 4)


def _normalized_headings(content: str) -> set[str]:
    headings: set[str] = set()
    in_fence = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith('#'):
            continue
        heading = stripped.lstrip('#').strip().lower()
        heading = ' '.join(token for token in heading.replace(':', ' ').split() if token)
        if heading:
            headings.add(heading)
    return headings


def _heading_overlap(left: str, right: str) -> float:
    left_headings = _normalized_headings(left)
    right_headings = _normalized_headings(right)
    if not left_headings or not right_headings:
        return 0.0
    return round(len(left_headings & right_headings) / max(1, min(len(left_headings), len(right_headings))), 4)


def _normalized_body_lines(content: str) -> set[str]:
    lines: set[str] = set()
    in_frontmatter = False
    seen_first_fm = False
    in_fence = False
    for raw in content.splitlines():
        stripped = raw.strip()
        if stripped == '---' and not seen_first_fm:
            seen_first_fm = True
            in_frontmatter = True
            continue
        if stripped == '---' and in_frontmatter:
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        normalized = ' '.join(stripped.lower().split())
        if normalized and normalized not in {'## overview', '## workflow', '## output format', '## quality checks', '## common pitfalls'}:
            lines.add(normalized)
    return lines


def _line_jaccard(left: str, right: str) -> float:
    left_lines = _normalized_body_lines(left)
    right_lines = _normalized_body_lines(right)
    if not left_lines or not right_lines:
        return 0.0
    return round(len(left_lines & right_lines) / max(1, len(left_lines | right_lines)), 4)


def _gap_issues(auto: SkillCreateComparisonMetrics, reference: SkillCreateComparisonMetrics) -> list[str]:
    issues: list[str] = []
    if auto.body_lines < 40 and reference.body_lines > 150:
        issues.append('auto_body_much_shorter_than_reference')
    if 'workflow' in reference.required_sections_present and 'workflow' not in auto.required_sections_present:
        issues.append('auto_missing_workflow')
    if 'output_format' in reference.required_sections_present and 'output_format' not in auto.required_sections_present:
        issues.append('auto_missing_output_template')
    if auto.fully_correct and auto.body_quality_status != 'pass':
        issues.append('auto_fully_correct_with_body_quality_failure')
    if auto.description_body_ratio > 0.75 and auto.body_lines < 10:
        issues.append('auto_description_stuffing')
    if auto.body_quality_status != 'pass':
        issues.append('auto_body_quality_not_pass')
    if auto.self_review_status != 'pass':
        issues.append('auto_self_review_not_pass')
    if auto.domain_specificity_status != 'pass':
        issues.append('auto_domain_specificity_not_pass')
    if auto.domain_expertise_status != 'pass':
        issues.append('auto_domain_expertise_not_pass')
    if auto.expert_structure_status != 'pass':
        issues.append('auto_expert_structure_not_pass')
    if auto.depth_quality_status != 'pass':
        issues.append('auto_depth_quality_not_pass')
    if auto.expert_action_cluster_recall < 0.75 and reference.expert_action_cluster_recall >= 0.75:
        issues.append('auto_expert_action_clusters_missing')
    if auto.expert_output_field_recall < 0.70 and reference.expert_output_field_recall >= 0.70:
        issues.append('auto_expert_output_fields_missing')
    if auto.expert_heading_recall < 0.30 and reference.expert_heading_recall >= 0.30:
        issues.append('auto_expert_headings_missing')
    if auto.expert_quality_check_recall < 0.70 and reference.expert_quality_check_recall >= 0.70:
        issues.append('auto_expert_quality_checks_missing')
    if auto.expert_depth_recall < 0.70 and reference.expert_depth_recall >= 0.70:
        issues.append('auto_expert_depth_recall_low')
    if auto.section_depth_score < 0.65 and reference.section_depth_score >= 0.65:
        issues.append('auto_section_depth_score_low')
    if auto.output_field_guidance_coverage < 0.70 and reference.output_field_guidance_coverage >= 0.70:
        issues.append('auto_output_field_guidance_weak')
    if auto.worked_example_count < 1 and reference.worked_example_count >= 1:
        issues.append('auto_worked_examples_missing')
    if auto.failure_pattern_density < 4 and reference.failure_pattern_density >= 4:
        issues.append('auto_failure_patterns_thin')
    if auto.generated_vs_generated_heading_overlap >= 0.80:
        issues.append('auto_generated_heading_overlap_high')
    if auto.generated_vs_generated_line_jaccard >= 0.42:
        issues.append('auto_generated_line_jaccard_high')
    if auto.missing_domain_anchors:
        issues.append('auto_missing_domain_anchors')
    if auto.cross_case_similarity >= 0.82:
        issues.append('auto_generic_shell_gap')
    if auto.generic_skeleton_ratio >= 0.50 and auto.expert_action_cluster_recall < 0.90:
        issues.append('auto_generic_skeleton_gap')
    return sorted(set(issues))


def _anthropic_reference_metrics() -> tuple[SkillCreateComparisonMetrics | None, list[str]]:
    for path in _default_anthropic_skill_creator_paths():
        if not path.exists() or not path.is_file():
            continue
        content = path.read_text(encoding='utf-8')
        case = {
            'case_id': 'anthropic-skill-creator',
            'skill_name': 'skill-creator',
            'task': 'Create and iteratively improve skills with evals, baseline comparisons, qualitative review, and quantitative benchmarks.',
        }
        metrics, _, _, _, _, _, _ = _metrics_from_markdown(case, content)
        summary = [
            'Anthropic skill-creator reference available',
            f'body_lines={metrics.body_lines}',
            'reference_patterns=iterative eval loop, baseline comparison, qualitative viewer, quantitative benchmark',
        ]
        return metrics, summary
    return None, ['Anthropic skill-creator reference unavailable']


def render_skill_create_comparison_markdown(report: SkillCreateComparisonReport) -> str:
    lines = [
        '# Skill Create Comparison Report',
        '',
        f'- overall_status={report.overall_status}',
        f'- gap_count={report.gap_count}',
        f'- include_hermes={report.include_hermes}',
        f'- hermes_available={report.hermes_available}',
        f'- hermes_execution_status={report.hermes_execution_status}',
        f'- hermes_error_count={report.hermes_error_count}',
        f'- comparison_source={report.comparison_source}',
        f'- comparison_independence_status={report.comparison_independence_status}',
        f'- reference_role={report.reference_role}',
        f'- anthropic_reference_available={report.anthropic_reference_available}',
        f'- expert_structure_gap_count={report.expert_structure_gap_count}',
        f'- depth_quality_gap_count={report.depth_quality_gap_count}',
        f'- generic_shell_gap_count={report.generic_shell_gap_count}',
        f'- pairwise_similarity_gap_count={report.pairwise_similarity_gap_count}',
        f'- Summary: {report.summary}',
        '',
    ]
    for case in list(report.cases or []):
        lines.append(f'## {case.case_id}')
        lines.append(f'- status={case.status}')
        lines.append(f'- auto_body_lines={case.auto_metrics.body_lines}')
        lines.append(f'- auto_body_quality={case.auto_metrics.body_quality_status}')
        lines.append(f'- auto_self_review={case.auto_metrics.self_review_status}')
        lines.append(f'- auto_domain_specificity={case.auto_metrics.domain_specificity_status}')
        lines.append(f'- auto_domain_anchor_coverage={case.auto_metrics.domain_anchor_coverage:.2f}')
        lines.append(f'- auto_domain_expertise={case.auto_metrics.domain_expertise_status}')
        lines.append(f'- auto_domain_move_coverage={case.auto_metrics.domain_move_coverage:.2f}')
        lines.append(f'- auto_expert_structure={case.auto_metrics.expert_structure_status}')
        lines.append(f'- auto_expert_heading_recall={case.auto_metrics.expert_heading_recall:.2f}')
        lines.append(f'- auto_expert_action_cluster_recall={case.auto_metrics.expert_action_cluster_recall:.2f}')
        lines.append(f'- auto_expert_output_field_recall={case.auto_metrics.expert_output_field_recall:.2f}')
        lines.append(f'- auto_expert_pitfall_cluster_recall={case.auto_metrics.expert_pitfall_cluster_recall:.2f}')
        lines.append(f'- auto_expert_quality_check_recall={case.auto_metrics.expert_quality_check_recall:.2f}')
        lines.append(f'- auto_depth_quality={case.auto_metrics.depth_quality_status}')
        lines.append(f'- auto_expert_depth_recall={case.auto_metrics.expert_depth_recall:.2f}')
        lines.append(f'- auto_section_depth_score={case.auto_metrics.section_depth_score:.2f}')
        lines.append(f'- auto_decision_probe_count={case.auto_metrics.decision_probe_count}')
        lines.append(f'- auto_worked_example_count={case.auto_metrics.worked_example_count}')
        lines.append(f'- auto_failure_pattern_density={case.auto_metrics.failure_pattern_density}')
        lines.append(f'- auto_output_field_guidance_coverage={case.auto_metrics.output_field_guidance_coverage:.2f}')
        lines.append(f'- auto_generated_heading_overlap={case.auto_metrics.generated_vs_generated_heading_overlap:.2f}')
        lines.append(f'- auto_generated_line_jaccard={case.auto_metrics.generated_vs_generated_line_jaccard:.2f}')
        lines.append(f'- auto_generic_skeleton_ratio={case.auto_metrics.generic_skeleton_ratio:.2f}')
        lines.append(f'- auto_prompt_phrase_echo_ratio={case.auto_metrics.prompt_phrase_echo_ratio:.2f}')
        if case.auto_metrics.missing_domain_anchors:
            lines.append(f'- missing_domain_anchors={case.auto_metrics.missing_domain_anchors}')
        if case.auto_metrics.cross_case_similarity:
            lines.append(f'- cross_case_similarity={case.auto_metrics.cross_case_similarity:.2f}')
        lines.append(f'- golden_body_lines={case.golden_metrics.body_lines}')
        if case.hermes_metrics is not None:
            lines.append(f'- hermes_body_lines={case.hermes_metrics.body_lines}')
        if case.gap_issues:
            lines.append(f'- gap_issues={case.gap_issues}')
        lines.append('')
    if report.hermes_errors:
        lines.append('## Hermes Errors')
        for item in report.hermes_errors:
            lines.append(f'- {item}')
    if report.anthropic_reference_summary:
        lines.extend(['', '## Anthropic Skill-Creator Reference'])
        for item in report.anthropic_reference_summary:
            lines.append(f'- {item}')
    return '\n'.join(lines).strip()


def build_skill_create_comparison_report(
    *,
    include_hermes: bool = False,
    golden_root: Path | None = None,
    hermes_wrappers: list[Path] | None = None,
) -> SkillCreateComparisonReport:
    root = (golden_root or DEFAULT_COMPARISON_GOLDEN_ROOT).expanduser()
    hermes_wrapper = _find_hermes_wrapper(hermes_wrappers) if include_hermes else None
    initial_independence_status = _hermes_independence_status(hermes_wrapper) if include_hermes else 'golden_only'
    hermes_errors: list[str] = []
    case_payloads: list[dict[str, Any]] = []
    for case in COMPARISON_CASES:
        auto_metrics, body_quality, self_review, domain_specificity, domain_expertise, expert_structure, depth_quality, auto_content = _run_auto_case(case)
        reference_root = DEFAULT_EXPERT_DEPTH_GOLDEN_ROOT if DEFAULT_EXPERT_DEPTH_GOLDEN_ROOT.exists() else root
        golden_metrics, _, _, _, _, _, _ = _metrics_from_markdown(case, _golden_content(case, reference_root))
        hermes_metrics = None
        if hermes_wrapper is not None:
            hermes_metrics, error = _run_hermes_case(case, hermes_wrapper)
            if error:
                hermes_errors.append(f'{case["case_id"]}: {error}')
        case_payloads.append(
            {
                'case': case,
                'auto_metrics': auto_metrics,
                'golden_metrics': golden_metrics,
                'hermes_metrics': hermes_metrics,
                'body_quality': body_quality,
                'self_review': self_review,
                'domain_specificity': domain_specificity,
                'domain_expertise': domain_expertise,
                'expert_structure': expert_structure,
                'depth_quality': depth_quality,
                'auto_content': auto_content,
            }
        )

    for payload in case_payloads:
        similarities = [
            _content_similarity(payload['auto_content'], other['auto_content'])
            for other in case_payloads
            if other is not payload
        ]
        max_similarity = max(similarities or [0.0])
        heading_overlaps = [
            _heading_overlap(payload['auto_content'], other['auto_content'])
            for other in case_payloads
            if other is not payload
        ]
        line_jaccards = [
            _line_jaccard(payload['auto_content'], other['auto_content'])
            for other in case_payloads
            if other is not payload
        ]
        max_heading_overlap = max(heading_overlaps or [0.0])
        max_line_jaccard = max(line_jaccards or [0.0])
        payload['auto_metrics'].cross_case_similarity = max_similarity
        payload['auto_metrics'].generated_vs_generated_heading_overlap = max_heading_overlap
        payload['auto_metrics'].generated_vs_generated_line_jaccard = max_line_jaccard
        if payload['domain_specificity'] is not None:
            payload['domain_specificity'].cross_case_similarity = max_similarity
            if max_similarity >= 0.82 and 'high_cross_case_similarity' not in payload['domain_specificity'].blocking_issues:
                payload['domain_specificity'].blocking_issues.append('high_cross_case_similarity')
                payload['domain_specificity'].status = 'fail'
            payload['auto_metrics'].domain_specificity_status = payload['domain_specificity'].status
        if payload['expert_structure'] is not None:
            payload['expert_structure'].generated_vs_generated_heading_overlap = max_heading_overlap
            payload['expert_structure'].generated_vs_generated_line_jaccard = max_line_jaccard
            if max_heading_overlap >= 0.80 and 'high_generated_heading_overlap' not in payload['expert_structure'].blocking_issues:
                payload['expert_structure'].blocking_issues.append('high_generated_heading_overlap')
                payload['expert_structure'].status = 'fail'
            if max_line_jaccard >= 0.42 and 'high_generated_line_jaccard' not in payload['expert_structure'].blocking_issues:
                payload['expert_structure'].blocking_issues.append('high_generated_line_jaccard')
                payload['expert_structure'].status = 'fail'
            payload['auto_metrics'].expert_structure_status = payload['expert_structure'].status

    if not include_hermes:
        hermes_execution_status = 'not_requested'
        comparison_independence_status = 'golden_only'
        comparison_source = 'expert_golden'
        reference_role = 'quality_baseline'
    elif hermes_wrapper is None:
        hermes_execution_status = 'unavailable'
        comparison_independence_status = 'golden_only'
        comparison_source = 'expert_golden'
        reference_role = 'quality_baseline'
    elif hermes_errors:
        hermes_execution_status = 'failed'
        comparison_independence_status = 'golden_only'
        comparison_source = 'expert_golden'
        reference_role = 'quality_baseline'
    else:
        hermes_execution_status = 'passed'
        comparison_independence_status = initial_independence_status
        if comparison_independence_status == 'independent':
            comparison_source = 'hermes'
            reference_role = 'quality_baseline'
        else:
            comparison_source = 'expert_golden'
            reference_role = 'entrypoint_smoke'

    cases: list[SkillCreateComparisonCaseResult] = []
    for payload in case_payloads:
        case = payload['case']
        reference_metrics = (
            payload['hermes_metrics']
            if comparison_source == 'hermes' and payload['hermes_metrics'] is not None
            else payload['golden_metrics']
        )
        gap_issues = _gap_issues(payload['auto_metrics'], reference_metrics)
        status = 'gap' if gap_issues else 'matched'
        cases.append(
            SkillCreateComparisonCaseResult(
                case_id=case['case_id'],
                skill_name=case['skill_name'],
                auto_metrics=payload['auto_metrics'],
                golden_metrics=payload['golden_metrics'],
                hermes_metrics=payload['hermes_metrics'],
                body_quality=payload['body_quality'],
                self_review=payload['self_review'],
                domain_specificity=payload['domain_specificity'],
                domain_expertise=payload['domain_expertise'],
                expert_structure=payload['expert_structure'],
                depth_quality=payload['depth_quality'],
                gap_issues=gap_issues,
                status=status,
                summary=f'{case["case_id"]}: {status}',
            )
        )
    gap_count = sum(1 for item in cases if item.status == 'gap')
    expert_structure_gap_count = sum(
        1
        for item in cases
        if any(issue.startswith('auto_expert_') for issue in list(item.gap_issues or []))
        or item.auto_metrics.expert_structure_status != 'pass'
    )
    depth_quality_gap_count = sum(
        1
        for item in cases
        if any(
            issue
            in {
                'auto_depth_quality_not_pass',
                'auto_expert_depth_recall_low',
                'auto_section_depth_score_low',
                'auto_output_field_guidance_weak',
                'auto_worked_examples_missing',
                'auto_failure_patterns_thin',
            }
            for issue in list(item.gap_issues or [])
        )
        or item.auto_metrics.depth_quality_status != 'pass'
    )
    generic_shell_gap_count = sum(
        1
        for item in cases
        if any(issue in {'auto_generic_shell_gap', 'auto_generic_skeleton_gap'} for issue in list(item.gap_issues or []))
    )
    pairwise_similarity_gap_count = sum(
        1
        for item in cases
        if any(
            issue in {'auto_generated_heading_overlap_high', 'auto_generated_line_jaccard_high'}
            for issue in list(item.gap_issues or [])
        )
    )
    anthropic_metrics, anthropic_summary = _anthropic_reference_metrics()
    report = SkillCreateComparisonReport(
        cases=cases,
        include_hermes=include_hermes,
        hermes_available=hermes_wrapper is not None,
        hermes_execution_status=hermes_execution_status,
        hermes_error_count=len(hermes_errors),
        hermes_errors=hermes_errors,
        comparison_source=comparison_source,
        comparison_independence_status=comparison_independence_status,
        reference_role=reference_role,
        anthropic_reference_available=anthropic_metrics is not None,
        anthropic_reference_metrics=anthropic_metrics,
        anthropic_reference_summary=anthropic_summary,
        expert_structure_gap_count=expert_structure_gap_count,
        depth_quality_gap_count=depth_quality_gap_count,
        generic_shell_gap_count=generic_shell_gap_count,
        pairwise_similarity_gap_count=pairwise_similarity_gap_count,
        gap_count=gap_count,
        overall_status='fail' if gap_count else 'pass',
        summary=(
            f'Skill create comparison complete: cases={len(cases)} gaps={gap_count} '
            f'comparison_source={comparison_source} '
            f'independence={comparison_independence_status} '
            f'reference_role={reference_role} '
            f'hermes_status={hermes_execution_status}'
        ),
    )
    report.markdown_summary = render_skill_create_comparison_markdown(report)
    return report
