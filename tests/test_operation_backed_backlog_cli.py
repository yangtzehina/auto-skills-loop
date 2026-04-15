from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_operation_backed_backlog.py'


def _write_snapshot(root: Path, name: str, payload: dict[str, object]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f'{name}.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')


def test_run_operation_backed_backlog_cli_supports_json(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_operation_backed_backlog_json')
    artifact_root = tmp_path / 'operation_backed'
    _write_snapshot(
        artifact_root,
        'derive',
        {
            'skill_id': 'derive',
            'skill_name': 'child-derivation',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'derive_child',
            'coverage_gap_summary': ['missing_operation_group'],
            'security_rating': 'LOW',
        },
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_operation_backed_backlog.py', '--artifact-root', str(artifact_root)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['derive_child_candidates'] == ['child-derivation']
    assert payload['actionable_count'] == 1


def test_run_operation_backed_backlog_cli_supports_markdown(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_operation_backed_backlog_markdown')
    artifact_root = tmp_path / 'operation_backed'
    _write_snapshot(
        artifact_root,
        'hold',
        {
            'skill_id': 'hold',
            'skill_name': 'blocked-helper',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'hold',
            'coverage_gap_summary': ['contract_surface_drift'],
            'security_rating': 'HIGH',
        },
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_operation_backed_backlog.py', '--artifact-root', str(artifact_root), '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Operation-Backed Backlog')
    assert 'blocked-helper' in stdout
