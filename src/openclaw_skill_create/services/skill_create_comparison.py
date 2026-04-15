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
from .orchestrator import run_skill_create


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COMPARISON_GOLDEN_ROOT = ROOT / 'tests' / 'fixtures' / 'methodology_guidance' / 'golden'


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
    severity: str = '',
    fully_correct: bool = False,
) -> SkillCreateComparisonMetrics:
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
        fully_correct=bool(fully_correct),
        severity=str(severity or ''),
    )


def _metrics_from_markdown(case: dict[str, str], content: str) -> tuple[SkillCreateComparisonMetrics, Any, Any]:
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
    return (
        _metrics_from_reports(
            body_quality=body_quality,
            self_review=self_review,
            severity='reference',
            fully_correct=body_quality.passed and self_review.status == 'pass',
        ),
        body_quality,
        self_review,
    )


def _run_auto_case(case: dict[str, str]) -> tuple[SkillCreateComparisonMetrics, Any, Any]:
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
    return (
        _metrics_from_reports(
            body_quality=body_quality,
            self_review=self_review,
            severity=response.severity,
            fully_correct=bool(getattr(response.quality_review, 'fully_correct', False)),
        ),
        body_quality,
        self_review,
    )


def _find_hermes_wrapper(paths: list[Path] | None = None) -> Path | None:
    for path in list(paths or _default_hermes_wrappers()):
        if path.exists() and path.is_file():
            return path
    return None


def _run_hermes_case(case: dict[str, str], wrapper: Path) -> tuple[SkillCreateComparisonMetrics | None, str | None]:
    with tempfile.TemporaryDirectory(prefix='hermes-skill-create-comparison-') as tmpdir:
        output_root = Path(tmpdir) / 'generated'
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
        metrics, _, _ = _metrics_from_markdown(case, skill_md.read_text(encoding='utf-8'))
        metrics.severity = str(payload.get('severity') or '')
        return metrics, None


def _golden_content(case: dict[str, str], golden_root: Path) -> str:
    path = golden_root / f'{case["case_id"]}.md'
    if not path.exists():
        raise ValueError(f'Missing golden baseline: {path}')
    return path.read_text(encoding='utf-8')


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
    return sorted(set(issues))


def render_skill_create_comparison_markdown(report: SkillCreateComparisonReport) -> str:
    lines = [
        '# Skill Create Comparison Report',
        '',
        f'- overall_status={report.overall_status}',
        f'- gap_count={report.gap_count}',
        f'- include_hermes={report.include_hermes}',
        f'- hermes_available={report.hermes_available}',
        f'- Summary: {report.summary}',
        '',
    ]
    for case in list(report.cases or []):
        lines.append(f'## {case.case_id}')
        lines.append(f'- status={case.status}')
        lines.append(f'- auto_body_lines={case.auto_metrics.body_lines}')
        lines.append(f'- auto_body_quality={case.auto_metrics.body_quality_status}')
        lines.append(f'- auto_self_review={case.auto_metrics.self_review_status}')
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
    return '\n'.join(lines).strip()


def build_skill_create_comparison_report(
    *,
    include_hermes: bool = False,
    golden_root: Path | None = None,
    hermes_wrappers: list[Path] | None = None,
) -> SkillCreateComparisonReport:
    root = (golden_root or DEFAULT_COMPARISON_GOLDEN_ROOT).expanduser()
    hermes_wrapper = _find_hermes_wrapper(hermes_wrappers) if include_hermes else None
    hermes_errors: list[str] = []
    cases: list[SkillCreateComparisonCaseResult] = []
    for case in COMPARISON_CASES:
        auto_metrics, body_quality, self_review = _run_auto_case(case)
        golden_metrics, _, _ = _metrics_from_markdown(case, _golden_content(case, root))
        hermes_metrics = None
        if hermes_wrapper is not None:
            hermes_metrics, error = _run_hermes_case(case, hermes_wrapper)
            if error:
                hermes_errors.append(f'{case["case_id"]}: {error}')
        reference_metrics = hermes_metrics or golden_metrics
        gap_issues = _gap_issues(auto_metrics, reference_metrics)
        status = 'gap' if gap_issues else 'matched'
        cases.append(
            SkillCreateComparisonCaseResult(
                case_id=case['case_id'],
                skill_name=case['skill_name'],
                auto_metrics=auto_metrics,
                golden_metrics=golden_metrics,
                hermes_metrics=hermes_metrics,
                body_quality=body_quality,
                self_review=self_review,
                gap_issues=gap_issues,
                status=status,
                summary=f'{case["case_id"]}: {status}',
            )
        )
    gap_count = sum(1 for item in cases if item.status == 'gap')
    report = SkillCreateComparisonReport(
        cases=cases,
        include_hermes=include_hermes,
        hermes_available=hermes_wrapper is not None,
        hermes_errors=hermes_errors,
        gap_count=gap_count,
        overall_status='fail' if gap_count else 'pass',
        summary=f'Skill create comparison complete: cases={len(cases)} gaps={gap_count}',
    )
    report.markdown_summary = render_skill_create_comparison_markdown(report)
    return report
