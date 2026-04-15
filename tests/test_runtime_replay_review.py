from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_replay_review import (
    build_runtime_replay_review,
    render_runtime_replay_review_markdown,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / 'fixtures' / 'runtime_replay'
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'


def test_build_runtime_replay_review_passes_against_default_gate():
    review = build_runtime_replay_review(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    assert review.passed is True
    assert review.total_scenarios == 3
    assert review.passed_scenarios == 3
    assert review.failed_scenarios == 0
    assert '# Runtime Replay Review' in review.markdown_summary


def test_build_runtime_replay_review_surfaces_drift_in_review(tmp_path: Path):
    baseline_path = tmp_path / 'baseline_report.json'
    payload = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    payload['scenario_baselines'][2]['actual_actions'] = ['patch_current', 'patch_current', 'patch_current']
    baseline_path.write_text(json.dumps(payload), encoding='utf-8')

    review = build_runtime_replay_review(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=baseline_path,
    )

    assert review.passed is False
    failing = [item for item in review.scenario_reviews if item.status != 'passed']
    assert failing
    assert failing[0].status == 'drifted'
    assert 'actual_actions drifted' in failing[0].issues[0]


def test_render_runtime_replay_review_markdown_includes_extra_baseline_section():
    review = build_runtime_replay_review(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
        scenario_names=['success_streak'],
    )

    markdown = render_runtime_replay_review_markdown(review)
    assert '## Extra Baseline Scenarios' not in markdown
