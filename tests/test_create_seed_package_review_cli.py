from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.ops_post_apply import CreateSeedPackageReviewReport

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_create_seed_package_review.py'


def test_run_create_seed_package_review_cli_supports_markdown(monkeypatch):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_create_seed_package_review')
    monkeypatch.setattr(
        module,
        'build_create_seed_package_review_report',
        lambda **kwargs: CreateSeedPackageReviewReport(
            candidate_key='missing-fits-calibration-and-astropy-verification-workflow',
            summary='ok',
            markdown_summary='# Create Seed Package Review\n\n- Summary: ok',
        ),
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_create_seed_package_review.py', '--format', 'markdown'],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert stdout.startswith('# Create Seed Package Review')
