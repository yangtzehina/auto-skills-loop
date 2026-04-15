from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.public_source_verification import PublicSourceCurationRoundReport

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_public_source_curation_round.py'


def test_public_source_curation_round_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_public_source_curation_round')
    monkeypatch.setattr(
        module,
        'build_public_source_curation_round',
        lambda **kwargs: PublicSourceCurationRoundReport(
            rehearsal_matched_count=3,
            rehearsal_passed=True,
            live_applied=True,
            promoted_repos=['example/source'],
            summary='ok',
            markdown_summary='# Public Source Curation Round\n\n- Summary: ok',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_public_source_curation_round.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Public Source Curation Round')


def test_public_source_curation_round_cli_rejects_bad_format(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_public_source_curation_round_bad')

    code, stdout, stderr = invoke_main(
        module,
        ['run_public_source_curation_round.py', '--format', 'yaml'],
        monkeypatch,
    )

    assert code == 2
    assert stdout == ''
    assert 'Unsupported format: yaml' in stderr
