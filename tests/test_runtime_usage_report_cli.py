from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_usage import build_runtime_usage_report

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_usage_report.py'


def test_runtime_usage_report_cli_matches_service_output(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_usage_report')
    policy = OpenSpaceObservationPolicy(enabled=False)
    monkeypatch.setattr(module, 'default_observation_policy', lambda auto_enable=True: policy)

    code, stdout, stderr = invoke_main(module, ['run_runtime_usage_report.py'], monkeypatch)
    expected = build_runtime_usage_report(policy=policy)

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout) == expected.model_dump(mode='json')


def test_runtime_usage_report_cli_supports_markdown_output(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_usage_report')
    monkeypatch.setattr(
        module,
        'default_observation_policy',
        lambda auto_enable=True: OpenSpaceObservationPolicy(enabled=False),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_usage_report.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Runtime Usage Report')


def test_runtime_usage_report_cli_forwards_skill_filter(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_usage_report')
    captured: dict[str, object] = {}

    def fake_build_runtime_usage_report(*, policy, skill_id=None):
        captured['policy'] = policy
        captured['skill_id'] = skill_id
        return build_runtime_usage_report(policy=OpenSpaceObservationPolicy(enabled=False))

    monkeypatch.setattr(module, 'build_runtime_usage_report', fake_build_runtime_usage_report)

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_usage_report.py', '--skill-id', 'skill-b'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['applied'] is False
    assert captured['skill_id'] == 'skill-b'


def test_runtime_usage_report_cli_rejects_bad_format(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_usage_report')

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_usage_report.py', '--format', 'html'],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported format' in stderr
