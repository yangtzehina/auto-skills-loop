from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.public_source_verification import PublicSourceVerificationReport

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_public_source_verification.py'


def test_public_source_verification_cli_uses_config(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_public_source_verification')
    config_path = tmp_path / 'candidates.json'
    config_path.write_text(
        json.dumps(
            [
                {
                    'repo_full_name': 'example/source',
                    'root_paths': ['skills'],
                    'verification_task': 'Find source skills.',
                }
            ]
        ),
        encoding='utf-8',
    )
    captured = {}

    def fake_verify_public_source_candidates(*, candidate_configs):
        captured['candidate_configs'] = candidate_configs
        return PublicSourceVerificationReport(summary='ok', promoted_repos=['example/source'])

    monkeypatch.setattr(module, 'verify_public_source_candidates', fake_verify_public_source_candidates)

    code, stdout, stderr = invoke_main(
        module,
        ['run_public_source_verification.py', '--config', str(config_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['summary'] == 'ok'
    assert json.loads(stdout)['promoted_repos'] == ['example/source']
    assert captured['candidate_configs'][0].repo_full_name == 'example/source'


def test_public_source_verification_cli_rejects_bad_config(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_public_source_verification')
    config_path = tmp_path / 'broken.json'
    config_path.write_text('{bad json', encoding='utf-8')

    code, stdout, stderr = invoke_main(
        module,
        ['run_public_source_verification.py', '--config', str(config_path)],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Invalid JSON config' in stderr
