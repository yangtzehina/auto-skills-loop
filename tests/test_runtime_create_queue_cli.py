from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy

from .runtime_test_helpers import CREATE_QUEUE_FIXTURE_ROOT, invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_create_queue.py'


def test_runtime_create_queue_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_create_queue')
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False))

    code, stdout, stderr = invoke_main(
        module,
        [
            'run_runtime_create_queue.py',
            '--format',
            'markdown',
            str(CREATE_QUEUE_FIXTURE_ROOT / 'no_skill_cluster' / 'manifest.json'),
        ],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Create Queue')
    assert 'recommended_status=review' in stdout


def test_runtime_create_queue_cli_rejects_bad_format(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_create_queue_bad')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_create_queue.py', '--format', 'yaml', 'runs'],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported format: yaml' in stderr
