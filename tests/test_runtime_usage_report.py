from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.openspace_runtime_usage_helper import _build_runtime_usage_payload
from openclaw_skill_create.services.runtime_analysis import encode_runtime_judgment_note
from openclaw_skill_create.services.runtime_usage import build_runtime_effectiveness_lookup, build_runtime_usage_report


def test_build_runtime_usage_report_skips_when_policy_disabled():
    report = build_runtime_usage_report(policy=OpenSpaceObservationPolicy(enabled=False))

    assert report.applied is False
    assert report.skill_reports == []
    assert 'disabled' in report.reason
    assert 'skipped' in report.summary


def test_runtime_usage_helper_aggregates_single_skill(tmp_path: Path):
    skill_dir = tmp_path / 'demo-skill'
    skill_dir.mkdir()
    (skill_dir / '_meta.json').write_text(
        """
        {
          "lineage": {
            "skill_id": "skill-1",
            "version": 4,
            "parent_skill_id": "parent-1",
            "content_sha": "beadfeed1234",
            "quality_score": 0.0,
            "history": [
              {
                "event": "patch_current",
                "skill_id": "skill-1",
                "version": 4,
                "parent_skill_id": "parent-1",
                "content_sha": "beadfeed1234",
                "quality_score": 0.0,
                "summary": "Patched runtime guidance."
              }
            ]
          }
        }
        """.strip(),
        encoding='utf-8',
    )

    class FakeLineage:
        def __init__(self):
            self.parent_skill_ids = ['parent-1']

    class FakeRecord:
        def __init__(self, skill_id: str, skill_name: str):
            self.skill_id = skill_id
            self.name = skill_name
            self.lineage = FakeLineage()
            self.path = str(skill_dir)

    class FakeJudgment:
        def __init__(self, skill_id: str, note: str):
            self.skill_id = skill_id
            self.note = note

    class FakeAnalysis:
        def __init__(self, judgments):
            self.skill_judgments = judgments

        def get_judgment(self, skill_id):
            for judgment in self.skill_judgments:
                if judgment.skill_id == skill_id:
                    return judgment
            return None

    latest_note = encode_runtime_judgment_note(
        {
            'run_id': 'run-2',
            'recommended_action': 'patch_current',
            'quality_score': 0.55,
            'usage_stats': {'run_count': 2, 'helped_count': 1, 'misled_count': 1, 'patch_count': 1, 'derive_count': 0},
            'recent_run_ids': ['run-1', 'run-2'],
            'parent_skill_ids': ['parent-1'],
        }
    )
    older_note = encode_runtime_judgment_note(
        {
            'run_id': 'run-1',
            'recommended_action': 'no_change',
            'quality_score': 1.0,
            'usage_stats': {'run_count': 1, 'helped_count': 1, 'misled_count': 0, 'patch_count': 0, 'derive_count': 0},
            'recent_run_ids': ['run-1'],
            'parent_skill_ids': ['parent-1'],
        }
    )

    class FakeStore:
        def __init__(self, db_path=None):
            self.db_path = Path(db_path or tmp_path / 'runtime.db')
            self.closed = False

        def list_records(self):
            return [FakeRecord('skill-1', 'demo-skill')]

        def load_analyses(self, skill_id=None, limit=10):
            assert skill_id == 'skill-1'
            return [
                FakeAnalysis([FakeJudgment('skill-1', latest_note)]),
                FakeAnalysis([FakeJudgment('skill-1', older_note)]),
            ][:limit]

        def close(self):
            self.closed = True

    store = FakeStore()
    payload = asyncio.run(
        _build_runtime_usage_payload(
            {'db_path': str(tmp_path / 'runtime.db')},
            store_factory=lambda db_path=None: store,
        )
    )

    assert payload['applied'] is True
    assert payload['skill_reports'][0]['skill_id'] == 'skill-1'
    assert payload['skill_reports'][0]['skill_name'] == 'demo-skill'
    assert payload['skill_reports'][0]['quality_score'] == 0.55
    assert payload['skill_reports'][0]['usage_stats']['run_count'] == 2
    assert payload['skill_reports'][0]['recent_actions'] == ['patch_current', 'no_change']
    assert payload['skill_reports'][0]['latest_recommended_action'] == 'patch_current'
    assert payload['skill_reports'][0]['parent_skill_ids'] == ['parent-1']
    assert payload['skill_reports'][0]['lineage_version'] == 4
    assert payload['skill_reports'][0]['latest_lineage_event'] == 'patch_current'
    assert store.closed is True


def test_runtime_usage_helper_filters_by_skill_id(tmp_path: Path):
    class FakeRecord:
        def __init__(self, skill_id: str):
            self.skill_id = skill_id
            self.name = skill_id
            self.lineage = SimpleNamespace(parent_skill_ids=[])

    note = encode_runtime_judgment_note(
        {
            'run_id': 'run-1',
            'recommended_action': 'no_change',
            'quality_score': 1.0,
            'usage_stats': {'run_count': 1},
            'recent_run_ids': ['run-1'],
        }
    )

    class FakeStore:
        def __init__(self, db_path=None):
            self.db_path = Path(db_path or tmp_path / 'runtime.db')

        def list_records(self):
            return [FakeRecord('skill-a'), FakeRecord('skill-b')]

        def load_analyses(self, skill_id=None, limit=10):
            if skill_id == 'skill-b':
                return [SimpleNamespace(get_judgment=lambda lookup: SimpleNamespace(skill_id='skill-b', note=note))]
            return []

        def close(self):
            pass

    payload = asyncio.run(
        _build_runtime_usage_payload(
            {'db_path': str(tmp_path / 'runtime.db'), 'skill_id': 'skill-b'},
            store_factory=FakeStore,
        )
    )

    assert payload['applied'] is True
    assert len(payload['skill_reports']) == 1
    assert payload['skill_reports'][0]['skill_id'] == 'skill-b'


def test_runtime_usage_helper_reports_multiple_skills_in_quality_order(tmp_path: Path):
    def note_for(run_id: str, quality_score: float, action: str) -> str:
        return encode_runtime_judgment_note(
            {
                'run_id': run_id,
                'recommended_action': action,
                'quality_score': quality_score,
                'usage_stats': {'run_count': 1},
                'recent_run_ids': [run_id],
            }
        )

    class FakeRecord:
        def __init__(self, skill_id: str, name: str):
            self.skill_id = skill_id
            self.name = name
            self.lineage = SimpleNamespace(parent_skill_ids=[])

    class FakeStore:
        def __init__(self, db_path=None):
            self.db_path = Path(db_path or tmp_path / 'runtime.db')

        def list_records(self):
            return [FakeRecord('skill-low', 'low-skill'), FakeRecord('skill-high', 'high-skill')]

        def load_analyses(self, skill_id=None, limit=10):
            note = note_for('run-high', 0.9, 'no_change') if skill_id == 'skill-high' else note_for('run-low', 0.2, 'patch_current')
            return [SimpleNamespace(get_judgment=lambda lookup, n=note, s=skill_id: SimpleNamespace(skill_id=s, note=n))]

        def close(self):
            pass

    payload = asyncio.run(
        _build_runtime_usage_payload(
            {'db_path': str(tmp_path / 'runtime.db')},
            store_factory=FakeStore,
        )
    )

    assert payload['applied'] is True
    assert [item['skill_id'] for item in payload['skill_reports']] == ['skill-high', 'skill-low']
    assert payload['skill_reports'][0]['latest_recommended_action'] == 'no_change'
    assert payload['skill_reports'][1]['latest_recommended_action'] == 'patch_current'


def test_build_runtime_usage_report_handles_helper_failure(monkeypatch):
    def fake_run(args, **kwargs):
        return SimpleNamespace(returncode=1, stdout='', stderr='boom')

    monkeypatch.setattr('openclaw_skill_create.services.runtime_usage.subprocess.run', fake_run)

    report = build_runtime_usage_report(
        policy=OpenSpaceObservationPolicy(enabled=True, openspace_python='/bin/echo', db_path='/tmp/runtime.db')
    )

    assert report.applied is False
    assert report.skill_reports == []
    assert 'Helper exited with code 1' in report.reason


def test_build_runtime_effectiveness_lookup_indexes_skill_family(monkeypatch):
    monkeypatch.setattr(
        'openclaw_skill_create.services.runtime_usage.build_runtime_usage_report',
        lambda **kwargs: SimpleNamespace(
            applied=True,
            skill_reports=[
                SimpleNamespace(
                    skill_id='hf-trainer__v2_deadbeef',
                    skill_name='hf-trainer',
                    quality_score=0.88,
                    usage_stats={'run_count': 7},
                )
            ],
        ),
    )

    lookup = build_runtime_effectiveness_lookup(policy=OpenSpaceObservationPolicy(enabled=False))

    assert lookup['hf-trainer']['quality_score'] == 0.88
    assert lookup['hf-trainer']['run_count'] == 7
    assert lookup['hf-trainer__v2_deadbeef']['skill_name'] == 'hf-trainer'
