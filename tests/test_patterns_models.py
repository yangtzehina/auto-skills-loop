from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.models.patterns import ExtractedSkillPatterns


ROOT = Path(__file__).resolve().parents[1]


def test_extracted_skill_patterns_example_parses():
    example_path = ROOT / 'docs' / 'extracted-skill-patterns.example.json'
    payload = json.loads(example_path.read_text(encoding='utf-8'))

    model = ExtractedSkillPatterns.model_validate(payload)

    assert model.schema_version == '1.0.0'
    assert model.pattern_set_id == 'esp_skill_creator_20260325_001'
    assert len(model.patterns) >= 2
    assert model.patterns[0].downstream_hints.validator_checks
