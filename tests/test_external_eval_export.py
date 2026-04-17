from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_test_helpers import load_script_module

from openclaw_skill_create.services.external_eval_export import (
    build_external_eval_export_bundle,
    build_normalized_eval_suite,
)


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'run_external_eval_export.py'


def test_normalized_eval_suite_covers_known_profiles():
    suite = build_normalized_eval_suite()

    assert suite.suite_version == 'frontier_v2'
    assert {item.skill_name for item in suite.profiles} == {
        'concept-to-mvp-pack',
        'decision-loop-stress-test',
        'simulation-resource-loop-design',
    }
    assert len(suite.criteria) >= 6
    assert len(suite.probes) >= 11
    assert all(item.active_frontier_version == 'frontier_v2' for item in suite.profiles)
    assert all(item.probe_ids for item in suite.profiles)
    assert 'decision-loop-stress-test' in suite.current_frontier_metrics
    assert suite.current_frontier_metrics['decision-loop-stress-test']['decision_pressure_score'] >= 0.0


def test_external_eval_export_bundle_writes_sidecars(tmp_path: Path):
    bundle = build_external_eval_export_bundle(
        targets=['promptfoo', 'openai'],
        output_root=tmp_path,
    )

    normalized = Path(bundle.normalized_eval_suite_path)
    promptfoo_config = Path(bundle.promptfoo_config_path)
    promptfoo_cases = Path(bundle.promptfoo_cases_path)
    openai_suite = Path(bundle.openai_evals_suite_path)

    assert normalized.exists()
    assert promptfoo_config.exists()
    assert promptfoo_cases.exists()
    assert openai_suite.exists()

    suite_payload = json.loads(normalized.read_text(encoding='utf-8'))
    promptfoo_payload = json.loads(promptfoo_cases.read_text(encoding='utf-8'))
    openai_payload = json.loads(openai_suite.read_text(encoding='utf-8'))

    assert suite_payload['suite_version'] == 'frontier_v2'
    assert len(suite_payload['profiles']) == 3
    assert len(promptfoo_payload) >= 11
    assert len(openai_payload['profiles']) == 3
    assert len(openai_payload['items']) == len(promptfoo_payload)


def test_external_eval_export_cli(tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_external_eval_export')
    exit_code = module.main(
        [
            'run_external_eval_export.py',
            '--targets',
            'promptfoo,openai',
            '--format',
            'json',
            '--output-root',
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / 'normalized_eval_suite.json').exists()
    assert (tmp_path / 'promptfoo' / 'promptfoo.yaml').exists()
    assert (tmp_path / 'promptfoo' / 'cases.json').exists()
    assert (tmp_path / 'openai_evals' / 'suite.json').exists()
