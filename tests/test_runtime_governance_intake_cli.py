from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_governance_intake.py'


def _handoff_payload() -> str:
    return json.dumps(
        {
            'task_id': 'task-intake-cli',
            'task_summary': 'Normalize a runtime handoff payload.',
            'skills': [
                {
                    'skill_id': 'demo-skill__v0_abcd1234',
                    'skill_name': 'demo-skill',
                    'steps_triggered': ['review references/usage.md'],
                }
            ],
            'result': 'success',
            'turn_trace': [
                {
                    'skill_id': 'demo-skill__v0_abcd1234',
                    'step': 'review references/usage.md',
                    'phase': 'prepare',
                    'tool': 'python',
                    'status': 'success',
                }
            ],
        }
    )


def test_runtime_governance_intake_cli_supports_file_input(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_intake')
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False))
    payload_path = tmp_path / 'handoff.json'
    payload_path.write_text(_handoff_payload(), encoding='utf-8')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_intake.py', str(payload_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    parsed = json.loads(stdout)
    assert parsed['normalized']['skill_run_record']['task_id'] == 'task-intake-cli'
    assert parsed['governance_bundle']['runtime_hook']['runtime_cycle']['analysis']['skills_analyzed']


def test_runtime_governance_intake_cli_supports_stdin(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_governance_intake_stdin')
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False))

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_governance_intake.py', '-'],
        monkeypatch,
        stdin_text=_handoff_payload(),
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['summary'].startswith('Runtime governance intake complete')
