from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Optional

from ..models.artifacts import Artifacts
from ..models.diagnostics import Diagnostics
from ..models.evaluation import EvaluationRunReport
from ..models.observation import OpenSpaceObservationPolicy
from ..models.orchestrator import ExecutionTimings
from ..models.plan import SkillPlan
from ..models.request import SkillCreateRequestV6


HELPER_MODULE = 'openclaw_skill_create.services.openspace_observer_helper'
SRC_ROOT = Path(__file__).resolve().parents[2]


def default_observation_policy(
    *,
    auto_enable: bool = False,
    db_path: Optional[str] = None,
) -> OpenSpaceObservationPolicy:
    policy = OpenSpaceObservationPolicy()
    openspace_python = str(policy.openspace_python or '').strip()
    policy.enabled = auto_enable and bool(openspace_python) and Path(openspace_python).exists()
    if db_path:
        policy.db_path = db_path
    return policy


def should_observe_with_openspace(
    *,
    policy: Optional[OpenSpaceObservationPolicy],
    persistence: Optional[dict[str, Any]],
) -> tuple[bool, str]:
    if policy is None or not policy.enabled:
        return False, 'OpenSpace observation disabled'
    if persistence is None:
        return False, 'No persistence result available'
    if not persistence.get('applied'):
        return False, 'Persistence not applied'
    if not persistence.get('written_files'):
        return False, 'No files were written'
    output_root = persistence.get('output_root')
    if not output_root or not Path(output_root).is_dir():
        return False, 'Observed output directory does not exist'
    openspace_python = str(policy.openspace_python or '').strip()
    if not openspace_python:
        return False, 'OpenSpace python not configured'
    if not Path(openspace_python).exists():
        return False, f'OpenSpace python not found: {policy.openspace_python}'
    return True, 'ready'


def _extract_json_line(raw_stdout: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith('{') and line.endswith('}'):
            return json.loads(line)
    raise ValueError('No JSON payload found in helper stdout')


def observe_with_openspace(
    *,
    request: SkillCreateRequestV6,
    request_id: str,
    severity: str,
    skill_plan: Optional[SkillPlan],
    artifacts: Optional[Artifacts],
    diagnostics: Optional[Diagnostics],
    evaluation_report: Optional[EvaluationRunReport],
    persistence: Optional[dict[str, Any]],
    timings: Optional[ExecutionTimings],
    policy: Optional[OpenSpaceObservationPolicy],
) -> dict[str, Any]:
    ready, reason = should_observe_with_openspace(policy=policy, persistence=persistence)
    if not ready:
        return {
            'applied': False,
            'mode': 'observe-only',
            'reason': reason,
        }

    assert policy is not None
    assert persistence is not None

    payload = {
        'request_id': request_id,
        'task_id': f'auto-skills-loop:{request_id}',
        'task': request.task,
        'repo_paths': list(request.repo_paths),
        'severity': severity,
        'skill_plan': skill_plan.model_dump() if skill_plan is not None else None,
        'artifacts': artifacts.model_dump() if artifacts is not None else None,
        'diagnostics': diagnostics.model_dump() if diagnostics is not None else None,
        'evaluation_report': evaluation_report.model_dump() if evaluation_report is not None else None,
        'persistence': persistence,
        'timings': timings.model_dump() if timings is not None else None,
        'db_path': policy.db_path,
        'analyzed_by': policy.analyzed_by,
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
        return {
            'applied': False,
            'mode': 'observe-only',
            'reason': f'Helper exited with code {completed.returncode}',
            'stderr': completed.stderr.strip()[-1000:],
            'stdout': completed.stdout.strip()[-1000:],
        }

    try:
        result = _extract_json_line(completed.stdout)
    except Exception as exc:  # pragma: no cover - defensive parsing
        return {
            'applied': False,
            'mode': 'observe-only',
            'reason': f'Failed to parse helper JSON: {exc}',
            'stdout': completed.stdout.strip()[-1000:],
            'stderr': completed.stderr.strip()[-1000:],
        }

    result.setdefault('mode', 'observe-only')
    return result
