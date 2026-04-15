from __future__ import annotations

import json
from pathlib import Path

from .runtime_test_helpers import invoke_main, load_script_module


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / 'scripts' / 'run_runtime_prior_gate.py'


def test_runtime_prior_gate_cli_supports_json(monkeypatch, tmp_path: Path):
    module = load_script_module(SCRIPT_PATH, 'skill_create_run_runtime_prior_gate')
    spec_path = tmp_path / 'prior-gate.json'
    spec_path.write_text(
        json.dumps(
            {
                'catalog': [
                    {
                        'candidate_id': 'hf-trainer',
                        'name': 'hf-trainer',
                        'description': 'Handle Hugging Face trainer workflows.',
                        'trigger_phrases': ['hugging face trainer'],
                        'tags': ['huggingface', 'trainer'],
                        'provenance': {
                            'source_type': 'community',
                            'ecosystem': 'codex',
                            'repo_full_name': 'example/hf-trainer',
                            'ref': 'main',
                            'skill_path': 'skills/hf-trainer',
                            'skill_url': 'https://github.com/example/hf-trainer/blob/main/skills/hf-trainer/SKILL.md',
                        },
                    }
                ],
                'runtime_effectiveness_lookup': {
                    'hf-trainer': {
                        'skill_id': 'hf-trainer__v2_deadbeef',
                        'skill_name': 'hf-trainer',
                        'quality_score': 0.9,
                        'run_count': 7,
                    }
                },
                'task_samples': [
                    {
                        'task': 'Fix the Hugging Face trainer resume workflow',
                        'repo_context': {'selected_files': []},
                    }
                ],
            }
        ),
        encoding='utf-8',
    )

    code, stdout, stderr = invoke_main(
        module,
        ['run_runtime_prior_gate.py', str(spec_path)],
        monkeypatch,
    )

    assert code == 0
    assert stderr == ''
    assert json.loads(stdout)['eligibility_summary']['eligible_count'] == 1
