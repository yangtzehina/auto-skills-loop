from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Optional

from openclaw_skill_create.models.runtime import SkillRunRecord


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'runtime_replay'
TRACE_FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'runtime_trace_replay'
CREATE_QUEUE_FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'runtime_create_queue'
SIMULATION_FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'simulation'
PUBLIC_SOURCE_CURATION_ROUND_REPORT = ROOT / 'tests' / 'fixtures' / 'public_source_curation' / 'latest_round_report.json'
OPS_APPROVAL_MANIFEST = ROOT / 'scripts' / 'ops_approval_manifest.json'


def load_script_module(script_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def invoke_main(module: Any, argv: list[str], monkeypatch, *, stdin_text: str = '') -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    if monkeypatch is not None:
        monkeypatch.setattr(sys, 'stdin', io.StringIO(stdin_text))
    else:
        original_stdin = sys.stdin
        sys.stdin = io.StringIO(stdin_text)
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = module.main(argv)
    if monkeypatch is None:
        sys.stdin = original_stdin
    return code, stdout.getvalue(), stderr.getvalue()


def sample_run_record(
    *,
    run_id: str = 'run-cli-1',
    task_id: str = 'task-cli-1',
    task_summary: str = 'Exercise runtime CLI.',
    execution_result: str = 'partial',
    steps_triggered: Optional[list[str]] = None,
    failure_points: Optional[list[str]] = None,
    user_corrections: Optional[list[str]] = None,
) -> SkillRunRecord:
    return SkillRunRecord(
        run_id=run_id,
        task_id=task_id,
        task_summary=task_summary,
        execution_result=execution_result,
        skills_used=[
            {
                'skill_id': 'demo-skill__v0_abcd1234',
                'skill_name': 'demo-skill',
                'skill_path': '/tmp/demo-skill',
                'selected': True,
                'applied': True,
                'steps_triggered': list(steps_triggered or ['review references/usage.md', 'run scripts/build.py']),
                'notes': 'Applied packaged workflow.',
            }
        ],
        failure_points=list(failure_points or ['The run scripts/build.py step used the wrong command.']),
        user_corrections=list(user_corrections or ['Missing a repo-specific verification step.']),
        output_summary='Task finished with manual corrections.',
        repo_paths=['/tmp/repo'],
        completed_at='2026-04-11T00:00:00+08:00',
    )


def load_replay_scenario(name: str, *, fixtures_root: Optional[Path] = None) -> tuple[dict[str, object], list[SkillRunRecord]]:
    root = fixtures_root or FIXTURE_ROOT
    scenario_root = root / name
    manifest = json.loads((scenario_root / 'manifest.json').read_text(encoding='utf-8'))
    runs = [
        SkillRunRecord.model_validate(
            json.loads((scenario_root / relative_path).read_text(encoding='utf-8'))
        )
        for relative_path in list(manifest.get('run_files') or [])
    ]
    return manifest, runs


def write_run_record(tmp_path: Path, record: SkillRunRecord, *, name: Optional[str] = None) -> Path:
    path = tmp_path / (name or f'{record.run_id}.json')
    path.write_text(json.dumps(record.model_dump(mode='json')), encoding='utf-8')
    return path


def write_run_manifest(tmp_path: Path, run_paths: list[Path], *, name: str = 'manifest.json') -> Path:
    path = tmp_path / name
    payload = {'run_records': [item.name if item.parent == tmp_path else str(item) for item in run_paths]}
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path


def copy_replay_scenario(tmp_path: Path, name: str, *, fixtures_root: Optional[Path] = None) -> Path:
    root = fixtures_root or FIXTURE_ROOT
    scenario_root = tmp_path / root.name / name
    run_root = scenario_root / 'runs'
    run_root.mkdir(parents=True)
    source_root = root / name
    (scenario_root / 'manifest.json').write_text(
        (source_root / 'manifest.json').read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    for run_file in (source_root / 'runs').glob('*.json'):
        (run_root / run_file.name).write_text(run_file.read_text(encoding='utf-8'), encoding='utf-8')
    return tmp_path / root.name


def copy_tree(tmp_path: Path, source_root: Path, *, name: Optional[str] = None) -> Path:
    target_root = tmp_path / (name or source_root.name)
    for source_path in source_root.rglob('*'):
        relative = source_path.relative_to(source_root)
        target_path = target_root / relative
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(source_path.read_text(encoding='utf-8'), encoding='utf-8')
    return target_root
