from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_operation_backed_status.py'


def _write_snapshot(root: Path, name: str, payload: dict[str, object]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f'{name}.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')


def test_run_operation_backed_status_cli_supports_json(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_operation_backed_status_json')
    artifact_root = tmp_path / 'operation_backed'
    _write_snapshot(
        artifact_root,
        'safe',
        {
            'skill_id': 'safe',
            'skill_name': 'safe-cli',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'validated',
            'recommended_followup': 'no_change',
            'security_rating': 'LOW',
        },
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_operation_backed_status.py', '--artifact-root', str(artifact_root)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    payload = json.loads(stdout)
    assert payload['total_operation_backed_skills'] == 1
    assert payload['recommended_followup_counts'] == {'no_change': 1}


def test_run_operation_backed_status_cli_supports_markdown(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_operation_backed_status_markdown')
    artifact_root = tmp_path / 'operation_backed'
    _write_snapshot(
        artifact_root,
        'patch',
        {
            'skill_id': 'patch',
            'skill_name': 'patchable-helper',
            'skill_archetype': 'operation_backed',
            'operation_validation_status': 'needs_attention',
            'recommended_followup': 'patch_current',
            'coverage_gap_summary': ['missing_json_surface'],
            'security_rating': 'LOW',
        },
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_operation_backed_status.py', '--artifact-root', str(artifact_root), '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Operation-Backed Status')
    assert 'patchable-helper' in stdout
