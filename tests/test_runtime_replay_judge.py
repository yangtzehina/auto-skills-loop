from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.runtime_replay_change import build_runtime_replay_change_pack
from openclaw_skill_create.services.runtime_replay_judge import build_runtime_replay_judge_pack


FIXTURE_ROOT = Path(__file__).resolve().parent / 'fixtures' / 'runtime_replay'
BASELINE_PATH = FIXTURE_ROOT / 'baseline_report.json'


def test_runtime_replay_judge_pack_is_disabled_by_default():
    change_pack = build_runtime_replay_change_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=BASELINE_PATH,
    )

    judge_pack = build_runtime_replay_judge_pack(change_pack)

    assert judge_pack.enabled is False
    assert judge_pack.applied is False
    assert judge_pack.scenario_judgments == []
    assert 'disabled' in judge_pack.reason


def test_runtime_replay_judge_pack_adds_explanations_without_changing_deterministic_action(tmp_path: Path):
    baseline_path = tmp_path / 'baseline_report.json'
    payload = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    payload['scenario_baselines'][0]['actual_final_quality_score'] = 0.25
    baseline_path.write_text(json.dumps(payload), encoding='utf-8')
    change_pack = build_runtime_replay_change_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=baseline_path,
    )

    def fake_llm_runner(messages, model):
        assert model == 'gpt-test'
        user_payload = json.loads(messages[-1]['content'])
        return json.dumps(
            {
                'narrative_explanation': f"Scenario {user_payload['scenario_id']} drifted for an intentional rules update.",
                'confidence_adjustment': 0.15,
                'review_hints': ['Confirm the updated drift is intended.', 'Refresh the baseline after review.'],
            }
        )

    judge_pack = build_runtime_replay_judge_pack(
        change_pack,
        enabled=True,
        llm_runner=fake_llm_runner,
        model='gpt-test',
    )

    assert change_pack.recommended_action == 'refresh_baseline'
    assert judge_pack.enabled is True
    assert judge_pack.applied is True
    assert len(judge_pack.scenario_judgments) == 1
    assert judge_pack.scenario_judgments[0].scenario_id == change_pack.drifted_scenarios[0]
    assert judge_pack.scenario_judgments[0].confidence_adjustment == 0.15
    assert judge_pack.scenario_judgments[0].review_hints


def test_runtime_replay_judge_pack_falls_back_when_llm_runner_fails(tmp_path: Path):
    baseline_path = tmp_path / 'baseline_report.json'
    payload = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    payload['scenario_baselines'][1]['actual_final_quality_score'] = 0.25
    baseline_path.write_text(json.dumps(payload), encoding='utf-8')
    change_pack = build_runtime_replay_change_pack(
        fixtures_root=FIXTURE_ROOT,
        baseline_path=baseline_path,
    )

    def failing_llm_runner(messages, model):
        raise RuntimeError('judge unavailable')

    judge_pack = build_runtime_replay_judge_pack(
        change_pack,
        enabled=True,
        llm_runner=failing_llm_runner,
        model='gpt-test',
    )

    assert judge_pack.enabled is True
    assert judge_pack.applied is False
    assert judge_pack.scenario_judgments == []
    assert 'judge unavailable' in judge_pack.reason
    assert 'deterministic-only' in judge_pack.summary
