from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Optional

from ..models.observation import OpenSpaceObservationPolicy
from ..models.runtime_usage import RuntimeUsageReport


HELPER_MODULE = 'openclaw_skill_create.services.openspace_runtime_usage_helper'
SRC_ROOT = Path(__file__).resolve().parents[2]


def runtime_usage_report_ready(policy: Optional[OpenSpaceObservationPolicy]) -> tuple[bool, str]:
    if policy is None or not policy.enabled:
        return False, 'OpenSpace runtime usage report disabled'
    openspace_python = str(policy.openspace_python or '').strip()
    if not openspace_python:
        return False, 'OpenSpace python not configured'
    if not Path(openspace_python).exists():
        return False, f'OpenSpace python not found: {policy.openspace_python}'
    return True, 'ready'


def _extract_json_line(raw_stdout: str) -> dict[str, object]:
    lines = [line.strip() for line in raw_stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith('{') and line.endswith('}'):
            payload = json.loads(line)
            if isinstance(payload, dict):
                return payload
    raise ValueError('No JSON payload found in helper stdout')


def _normalize_lookup_key(value: str) -> str:
    return str(value or '').strip().lower()


def _prior_lookup_keys(*, skill_id: str, skill_name: str) -> list[str]:
    keys: list[str] = []
    for value in (skill_id, skill_name, skill_id.split('__', 1)[0], skill_name.replace(' ', '-')):
        normalized = _normalize_lookup_key(value)
        if normalized and normalized not in keys:
            keys.append(normalized)
    return keys


def render_runtime_usage_report_markdown(report: RuntimeUsageReport) -> str:
    status_text = 'ready' if report.applied else 'skipped'
    lines = [
        '# Runtime Usage Report',
        '',
        f'- Status: {status_text}',
        f'- Summary: {report.summary}',
    ]
    if report.db_path:
        lines.append(f'- DB: `{report.db_path}`')
    if report.reason:
        lines.append(f'- Reason: {report.reason}')
    if not report.skill_reports:
        lines.extend(['', '## Skills', '- No runtime usage records were available.'])
        return '\n'.join(lines).strip()

    lines.extend(['', '## Skills'])
    for item in list(report.skill_reports):
        skill_label = item.skill_name or item.skill_id
        lines.append(f'- `{skill_label}` (`{item.skill_id}`)')
        lines.append(f'  - quality_score={item.quality_score:.4f}')
        lines.append(f'  - latest_action={item.latest_recommended_action}')
        lines.append(f'  - usage_stats={item.usage_stats}')
        if item.recent_actions:
            lines.append(f'  - recent_actions={item.recent_actions}')
        if item.recent_run_ids:
            lines.append(f'  - recent_run_ids={item.recent_run_ids}')
        if item.parent_skill_ids:
            lines.append(f'  - parent_skill_ids={item.parent_skill_ids}')
        if item.lineage_version:
            lines.append(f'  - lineage_version={item.lineage_version}')
        if item.latest_lineage_event:
            lines.append(f'  - latest_lineage_event={item.latest_lineage_event}')
    return '\n'.join(lines).strip()


def build_runtime_usage_report(
    *,
    policy: Optional[OpenSpaceObservationPolicy],
    skill_id: Optional[str] = None,
) -> RuntimeUsageReport:
    ready, reason = runtime_usage_report_ready(policy)
    if not ready:
        report = RuntimeUsageReport(
            applied=False,
            reason=reason,
            summary=f'Runtime usage report skipped: {reason}',
        )
        report.markdown_summary = render_runtime_usage_report_markdown(report)
        return report

    assert policy is not None
    payload = {
        'db_path': policy.db_path,
        'skill_id': str(skill_id or '').strip(),
    }
    env = os.environ.copy()
    existing_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(SRC_ROOT) if not existing_pythonpath else f'{SRC_ROOT}:{existing_pythonpath}'

    completed = subprocess.run(
        [policy.openspace_python, '-m', HELPER_MODULE],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        env=env,
        timeout=policy.timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        report = RuntimeUsageReport(
            applied=False,
            reason=f'Helper exited with code {completed.returncode}',
            summary=f'Runtime usage report skipped: helper exit {completed.returncode}',
        )
        report.markdown_summary = render_runtime_usage_report_markdown(report)
        return report
    try:
        result = _extract_json_line(completed.stdout)
        report = RuntimeUsageReport.model_validate(result)
    except Exception as exc:  # pragma: no cover - defensive helper boundary
        report = RuntimeUsageReport(
            applied=False,
            reason=str(exc),
            summary=f'Runtime usage report skipped: {exc}',
        )
    report.markdown_summary = render_runtime_usage_report_markdown(report)
    return report


def build_runtime_effectiveness_lookup(
    *,
    policy: Optional[OpenSpaceObservationPolicy],
    skill_id: Optional[str] = None,
) -> dict[str, dict[str, Any]]:
    report = build_runtime_usage_report(policy=policy, skill_id=skill_id)
    if not report.applied:
        return {}

    lookup: dict[str, dict[str, Any]] = {}
    for item in list(report.skill_reports or []):
        payload = {
            'skill_id': item.skill_id,
            'skill_name': item.skill_name,
            'quality_score': float(item.quality_score or 0.0),
            'run_count': int((item.usage_stats or {}).get('run_count', 0) or 0),
        }
        for key in _prior_lookup_keys(skill_id=item.skill_id, skill_name=item.skill_name):
            incumbent = lookup.get(key)
            if incumbent is None or int(payload['run_count']) > int(incumbent.get('run_count', 0) or 0):
                lookup[key] = payload
    return lookup
