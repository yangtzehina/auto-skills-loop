from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.models.runtime import EvolutionPlan, RuntimeSessionEvidence, SkillRunAnalysis, SkillRunRecord
from openclaw_skill_create.services.generator_resources import generate_metadata_artifacts
from openclaw_skill_create.services.openspace_runtime_helper import _analyze_runtime_payload
from openclaw_skill_create.services.runtime_analysis import (
    analyze_skill_run,
    analyze_skill_run_deterministically,
    encode_runtime_judgment_note,
    evolution_plan_to_repair_suggestions,
    evolution_plan_to_skill_create_request,
)


def test_runtime_models_normalize_defaults_and_nested_payloads():
    record = SkillRunRecord(
        run_id='run-1',
        task_id='task-1',
        execution_result='UNKNOWN',
        failure_points=['  missing step  '],
        skills_used=[{'skill_name': 'demo', 'steps_triggered': ['  step one  ']}],
        step_trace=[{'step': '  collect inputs  ', 'status': 'FAILED', 'tool': ' python '}],
        phase_markers=[' prepare ', ' execute '],
        tool_summary=[' python ', ' bash '],
    )
    assert record.execution_result == 'success'
    assert record.failure_points == ['missing step']
    assert record.skills_used[0]['skill_id'] == ''
    assert record.skills_used[0]['steps_triggered'] == ['step one']
    assert record.step_trace[0]['step'] == 'collect inputs'
    assert record.step_trace[0]['status'] == 'failed'
    assert record.phase_markers == ['prepare', 'execute']
    assert record.tool_summary == ['python', 'bash']

    analysis = SkillRunAnalysis(
        run_id='run-1',
        task_id='task-1',
        execution_result='PARTIAL',
        skills_analyzed=[{'skill_name': 'demo', 'recommended_action': 'PATCH_CURRENT'}],
        evolution_plans=[{'run_id': 'run-1', 'skill_id': 'skill-1', 'action': 'DERIVE_CHILD'}],
    )
    assert analysis.execution_result == 'partial'
    assert analysis.skills_analyzed[0]['recommended_action'] == 'patch_current'
    assert analysis.evolution_plans[0].action == 'derive_child'
    analysis_with_candidates = SkillRunAnalysis(
        run_id='run-1',
        task_id='task-1',
        create_candidates=[
            {
                'candidate_id': 'create-hf-trainer',
                'task_summary': 'Create a trainer child skill.',
                'reason': 'Repeated no-skill runtime gap.',
            }
        ],
    )
    assert analysis_with_candidates.create_candidates[0].candidate_id == 'create-hf-trainer'


def test_analyze_skill_run_deterministically_success_no_change():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-success',
            task_id='task-success',
            task_summary='Ship the repo-aware skill.',
            execution_result='success',
            skills_used=[
                {
                    'skill_id': 'skill-1',
                    'skill_name': 'demo-skill',
                    'skill_path': '/tmp/demo-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['review references/usage.md', 'run scripts/build.py'],
                }
            ],
        )
    )

    item = analysis.skills_analyzed[0]
    plan = analysis.evolution_plans[0]
    assert item['helped'] is True
    assert item['run_quality_score'] == 1.0
    assert item['recommended_action'] == 'no_change'
    assert item['quality_score'] == 1.0
    assert item['usage_stats']['run_count'] == 1
    assert plan.action == 'no_change'


def test_analyze_skill_run_deterministically_marks_misleading_runs_for_patch():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-mislead',
            task_id='task-mislead',
            execution_result='failed',
            failure_points=['The run scripts/build.py step used the wrong command and misled execution.'],
            skills_used=[
                {
                    'skill_id': 'skill-2',
                    'skill_name': 'broken-skill',
                    'skill_path': '/tmp/broken-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['run scripts/build.py'],
                }
            ],
        )
    )

    item = analysis.skills_analyzed[0]
    plan = analysis.evolution_plans[0]
    assert item['helped'] is False
    assert item['misleading_step'] == 'run scripts/build.py'
    assert item['run_quality_score'] == 0.0
    assert item['recommended_action'] == 'patch_current'
    assert plan.action == 'patch_current'
    assert plan.repair_suggestions[0].issue_type == 'script_placeholder_heavy'


def test_analyze_skill_run_deterministically_prefers_step_trace_for_step_selection():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-trace',
            task_id='task-trace',
            execution_result='partial',
            skills_used=[
                {
                    'skill_id': 'skill-trace',
                    'skill_name': 'trace-aware-skill',
                    'skill_path': '/tmp/trace-aware-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['trainer workflow'],
                }
            ],
            step_trace=[
                {
                    'skill_id': 'skill-trace',
                    'step': 'collect dataset manifest',
                    'phase': 'prepare',
                    'tool': 'python',
                    'status': 'success',
                },
                {
                    'skill_id': 'skill-trace',
                    'step': 'resume trainer from checkpoint',
                    'phase': 'execute',
                    'tool': 'python',
                    'status': 'corrected',
                    'notes': 'Wrong resume flag was suggested.',
                },
            ],
            phase_markers=['prepare', 'execute'],
            tool_summary=['python'],
        )
    )

    item = analysis.skills_analyzed[0]
    assert item['helped'] is False
    assert item['most_valuable_step'] == 'collect dataset manifest'
    assert item['misleading_step'] == 'resume trainer from checkpoint'
    assert item['recommended_action'] == 'patch_current'
    assert 'trace_steps=2' in item['rationale']
    assert 'phases=2' in item['rationale']
    assert 'tools=1' in item['rationale']


def test_analyze_skill_run_deterministically_prefers_runtime_session_evidence():
    record = SkillRunRecord(
        run_id='run-evidence',
        task_id='task-evidence',
        execution_result='partial',
        skills_used=[
            {
                'skill_id': 'skill-evidence',
                'skill_name': 'evidence-aware-skill',
                'skill_path': '/tmp/evidence-aware-skill',
                'selected': True,
                'applied': True,
                'steps_triggered': ['trainer workflow'],
            }
        ],
    )
    evidence = RuntimeSessionEvidence(
        run_id='run-evidence',
        task_id='task-evidence',
        turn_trace=[
            {
                'skill_id': 'skill-evidence',
                'step': 'load dataset card',
                'phase': 'prepare',
                'tool': 'python',
                'status': 'success',
            },
            {
                'skill_id': 'skill-evidence',
                'step': 'resume trainer with outdated flag',
                'phase': 'execute',
                'tool': 'python',
                'status': 'corrected',
            },
        ],
        phase_markers=['prepare', 'execute'],
        tool_summary=['python'],
        failure_points=['The outdated flag misled execution.'],
    )

    analysis = analyze_skill_run_deterministically(record, session_evidence=evidence)

    item = analysis.skills_analyzed[0]
    assert item['most_valuable_step'] == 'load dataset card'
    assert item['misleading_step'] == 'resume trainer with outdated flag'


def test_operation_backed_runtime_analysis_maps_json_gap_to_patch_current():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-op-json',
            task_id='task-op-json',
            execution_result='failed',
            failure_points=['Missing JSON output for the inspect operation.'],
            skills_used=[
                {
                    'skill_id': 'native-cli-skill__v1_demo',
                    'skill_name': 'native-cli-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['inspect'],
                    'skill_archetype': 'operation_backed',
                    'operation_validation_status': 'validated',
                    'operation_contract': {
                        'name': 'native-cli-skill',
                        'backend_kind': 'repo_native_cli',
                        'supports_json': True,
                        'session_model': 'stateless',
                        'mutability': 'read_only',
                        'operations': [{'name': 'main', 'operations': [{'name': 'inspect', 'summary': 'Inspect as JSON.'}]}],
                    },
                }
            ],
        )
    )

    item = analysis.skills_analyzed[0]
    plan = analysis.evolution_plans[0]
    assert item['recommended_action'] == 'patch_current'
    assert item['coverage_gap_summary'] == ['missing_json_surface']
    assert plan.action == 'patch_current'
    assert plan.coverage_gap_types == ['missing_json_surface']


def test_operation_backed_runtime_analysis_maps_missing_operation_to_derive_child():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-op-derive',
            task_id='task-op-derive',
            execution_result='failed',
            failure_points=['Missing the sync operation for the workspace flow.'],
            skills_used=[
                {
                    'skill_id': 'workspace-skill__v1_demo',
                    'skill_name': 'workspace-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['inspect'],
                    'skill_archetype': 'operation_backed',
                    'operation_validation_status': 'validated',
                    'operation_contract': {
                        'name': 'workspace-skill',
                        'backend_kind': 'repo_native_cli',
                        'supports_json': True,
                        'session_model': 'stateless',
                        'mutability': 'read_only',
                        'operations': [
                            {
                                'name': 'main',
                                'operations': [
                                    {'name': 'inspect', 'summary': 'Inspect the workspace.'},
                                    {'name': 'sync', 'summary': 'Sync the workspace.'},
                                ],
                            }
                        ],
                    },
                }
            ],
        )
    )

    item = analysis.skills_analyzed[0]
    plan = analysis.evolution_plans[0]
    assert item['recommended_action'] == 'derive_child'
    assert item['coverage_gap_summary'] == ['missing_operation']
    assert plan.action == 'derive_child'
    assert plan.coverage_gap_types == ['missing_operation']


def test_operation_backed_runtime_analysis_holds_on_read_only_contract_conflict():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-op-hold',
            task_id='task-op-hold',
            execution_result='failed',
            failure_points=['The helper tried to write local state even though this should only inspect data.'],
            skills_used=[
                {
                    'skill_id': 'dangerous-op__v1_demo',
                    'skill_name': 'dangerous-op',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['inspect'],
                    'skill_archetype': 'operation_backed',
                    'operation_validation_status': 'validated',
                    'operation_contract': {
                        'name': 'dangerous-op',
                        'backend_kind': 'python_backend',
                        'supports_json': False,
                        'session_model': 'stateless',
                        'mutability': 'read_only',
                        'operations': [{'name': 'main', 'operations': [{'name': 'inspect', 'summary': 'Inspect state.'}]}],
                    },
                }
            ],
        )
    )

    item = analysis.skills_analyzed[0]
    plan = analysis.evolution_plans[0]
    assert item['recommended_action'] == 'hold'
    assert item['coverage_gap_summary'] == ['contract_surface_drift']
    assert plan.action == 'hold'


def test_analyze_skill_run_deterministically_derives_child_for_repeated_gaps():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-gap',
            task_id='task-gap',
            execution_result='partial',
            user_corrections=['Missing Hugging Face trainer resume step for distributed training.'],
            skills_used=[
                {
                    'skill_id': 'skill-3',
                    'skill_name': 'hf-generalist',
                    'skill_path': '/tmp/hf-generalist',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['review references/hf.md'],
                }
            ],
        ),
        recent_skill_history={
            'skill-3': [
                {
                    'run_id': 'older-1',
                    'run_quality_score': 0.6,
                    'recommended_action': 'no_change',
                    'missing_steps': ['Missing Hugging Face trainer resume step for distributed training.'],
                },
                {
                    'run_id': 'older-2',
                    'run_quality_score': 0.6,
                    'recommended_action': 'no_change',
                    'missing_steps': ['Missing Hugging Face trainer resume step for distributed training.'],
                },
            ]
        },
    )

    item = analysis.skills_analyzed[0]
    plan = analysis.evolution_plans[0]
    assert item['run_quality_score'] == 0.6
    assert item['recommended_action'] == 'derive_child'
    assert plan.action == 'derive_child'
    assert 'Hugging Face trainer resume step' in plan.reason
    assert plan.requirement_gaps == ['Missing Hugging Face trainer resume step for distributed training.']


def test_analyze_skill_run_deterministically_emits_no_skill_create_candidates():
    analysis = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-no-skill',
            task_id='task-no-skill',
            task_summary='Handle astronomy FITS calibration edge cases.',
            execution_result='failed',
            skills_used=[
                {
                    'skill_id': 'generic-research__v0',
                    'skill_name': 'generic-research',
                    'skill_path': '/tmp/generic-research',
                    'selected': True,
                    'applied': False,
                    'steps_triggered': [],
                }
            ],
            failure_points=['Missing FITS calibration and astropy verification workflow.'],
            user_corrections=['Missing FITS calibration and astropy verification workflow.'],
        ),
        recent_skill_history={
            '__no_skill__': [
                {
                    'run_id': 'older-no-skill-1',
                    'run_quality_score': 0.0,
                    'recommended_action': 'no_change',
                    'missing_steps': ['Missing FITS calibration and astropy verification workflow.'],
                },
                {
                    'run_id': 'older-no-skill-2',
                    'run_quality_score': 0.0,
                    'recommended_action': 'no_change',
                    'missing_steps': ['Missing FITS calibration and astropy verification workflow.'],
                },
            ]
        },
    )

    assert analysis.create_candidates
    candidate = analysis.create_candidates[0]
    assert candidate.candidate_id.startswith('create-')
    assert 'No existing skill applied cleanly' in candidate.reason
    assert candidate.source_run_ids[-1] == 'run-no-skill'


def test_analyze_skill_run_skips_helper_when_policy_unavailable():
    analysis = analyze_skill_run(
        SkillRunRecord(
            run_id='run-local',
            task_id='task-local',
            execution_result='success',
            skills_used=[
                {
                    'skill_id': 'skill-local',
                    'skill_name': 'local',
                    'skill_path': '/tmp/local',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['review references/local.md'],
                }
            ],
        ),
        OpenSpaceObservationPolicy(enabled=False),
    )

    assert analysis.skills_analyzed[0]['recommended_action'] == 'no_change'
    assert 'store_persistence=skipped' in analysis.summary


def test_analyze_skill_run_invokes_helper(monkeypatch):
    captured: dict[str, object] = {}
    expected = analyze_skill_run_deterministically(
        SkillRunRecord(
            run_id='run-helper',
            task_id='task-helper',
            execution_result='success',
            skills_used=[
                {
                    'skill_id': 'skill-helper',
                    'skill_name': 'helper-skill',
                    'skill_path': '/tmp/helper-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['review references/helper.md'],
                }
            ],
        )
    )

    def fake_run(args, **kwargs):
        captured['args'] = args
        captured['kwargs'] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({'applied': True, 'analysis': expected.model_dump(mode='json')}) + '\n',
            stderr='',
        )

    monkeypatch.setattr('openclaw_skill_create.services.runtime_analysis.subprocess.run', fake_run)

    analysis = analyze_skill_run(
        SkillRunRecord(
            run_id='run-helper',
            task_id='task-helper',
            execution_result='success',
            skills_used=[
                {
                    'skill_id': 'skill-helper',
                    'skill_name': 'helper-skill',
                    'skill_path': '/tmp/helper-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['review references/helper.md'],
                }
            ],
        ),
        OpenSpaceObservationPolicy(enabled=True, openspace_python=sys.executable, db_path='/tmp/runtime-analysis.db'),
    )

    assert analysis.skills_analyzed[0]['skill_id'] == 'skill-helper'
    assert captured['args'] == [sys.executable, '-m', 'openclaw_skill_create.services.openspace_runtime_helper']
    assert '"run_id": "run-helper"' in captured['kwargs']['input']


def test_analyze_skill_run_falls_back_when_helper_fails(monkeypatch):
    def fake_run(args, **kwargs):
        return SimpleNamespace(returncode=2, stdout='', stderr='boom')

    monkeypatch.setattr('openclaw_skill_create.services.runtime_analysis.subprocess.run', fake_run)

    analysis = analyze_skill_run(
        SkillRunRecord(
            run_id='run-fallback',
            task_id='task-fallback',
            execution_result='success',
            skills_used=[
                {
                    'skill_id': 'skill-fallback',
                    'skill_name': 'fallback-skill',
                    'skill_path': '/tmp/fallback-skill',
                    'selected': True,
                    'applied': True,
                    'steps_triggered': ['review references/fallback.md'],
                }
            ],
        ),
        OpenSpaceObservationPolicy(enabled=True, openspace_python=sys.executable, db_path='/tmp/runtime-analysis.db'),
    )

    assert analysis.skills_analyzed[0]['skill_id'] == 'skill-fallback'
    assert 'store_persistence=failed' in analysis.summary


def test_runtime_helper_records_execution_analysis_and_aggregates(tmp_path: Path):
    skill_dir = tmp_path / 'demo-skill'
    skill_dir.mkdir()
    (skill_dir / '.skill_id').write_text('skill-store-1\n', encoding='utf-8')

    class FakeLineage:
        def __init__(self):
            self.parent_skill_ids = ['parent-1']

    class FakeRecord:
        def __init__(self):
            self.skill_id = 'skill-store-1'
            self.lineage = FakeLineage()

    class FakeJudgment:
        def __init__(self, skill_id, skill_applied=False, note=''):
            self.skill_id = skill_id
            self.skill_applied = skill_applied
            self.note = note

    class FakeExecutionAnalysis:
        def __init__(self, **kwargs):
            self.task_id = kwargs['task_id']
            self.timestamp = kwargs['timestamp']
            self.task_completed = kwargs['task_completed']
            self.execution_note = kwargs['execution_note']
            self.tool_issues = kwargs['tool_issues']
            self.skill_judgments = kwargs['skill_judgments']
            self.evolution_suggestions = kwargs['evolution_suggestions']
            self.analyzed_by = kwargs['analyzed_by']
            self.analyzed_at = kwargs['analyzed_at']

        def get_judgment(self, skill_id):
            for judgment in self.skill_judgments:
                if judgment.skill_id == skill_id:
                    return judgment
            return None

    class FakeEvolutionSuggestion:
        def __init__(self, **kwargs):
            self.evolution_type = kwargs['evolution_type']
            self.target_skill_ids = kwargs['target_skill_ids']
            self.direction = kwargs['direction']

    class FakeEvolutionType:
        FIX = 'fix'
        DERIVED = 'derived'

    previous_note = encode_runtime_judgment_note(
        {
            'run_id': 'older-run',
            'helped': True,
            'run_quality_score': 1.0,
            'recommended_action': 'no_change',
            'missing_steps': [],
            'quality_score': 1.0,
            'usage_stats': {'run_count': 1},
            'recent_run_ids': ['older-run'],
            'parent_skill_ids': ['parent-1'],
        }
    )

    class FakeStore:
        def __init__(self, db_path=None):
            self.db_path = Path(db_path or tmp_path / 'runtime.db')
            self.record = FakeRecord()
            self.history = [
                FakeExecutionAnalysis(
                    task_id='older-task',
                    timestamp='',
                    task_completed=True,
                    execution_note='older',
                    tool_issues=[],
                    skill_judgments=[FakeJudgment('skill-store-1', True, previous_note)],
                    evolution_suggestions=[],
                    analyzed_by='older',
                    analyzed_at='',
                )
            ]
            self.saved = None
            self.closed = False

        def load_record_by_path(self, skill_dir):
            return self.record if str(skill_dir).endswith('demo-skill') else None

        def load_record(self, skill_id):
            return self.record if skill_id == self.record.skill_id else None

        def load_analyses(self, skill_id=None, limit=9):
            if skill_id == self.record.skill_id:
                return list(self.history[:limit])
            return []

        async def record_analysis(self, analysis):
            self.saved = analysis
            self.history.append(analysis)

        def close(self):
            self.closed = True

    store = FakeStore()
    result = asyncio.run(
        _analyze_runtime_payload(
            {
                'run_record': SkillRunRecord(
                    run_id='run-store',
                    task_id='task-store',
                    task_summary='Exercise runtime analysis.',
                    execution_result='success',
                    skills_used=[
                        {
                            'skill_name': 'demo-skill',
                            'skill_path': str(skill_dir),
                            'selected': True,
                            'applied': True,
                            'steps_triggered': ['review references/runtime.md'],
                        }
                    ],
                ).model_dump(mode='json'),
                'db_path': str(tmp_path / 'runtime.db'),
                'analyzed_by': 'auto-skills-loop.runtime-analysis',
            },
            store_factory=lambda db_path=None: store,
            execution_analysis_cls=FakeExecutionAnalysis,
            skill_judgment_cls=FakeJudgment,
            evolution_suggestion_cls=FakeEvolutionSuggestion,
            evolution_type_enum=FakeEvolutionType,
        )
    )

    assert result['applied'] is True
    item = result['analysis']['skills_analyzed'][0]
    assert item['skill_id'] == 'skill-store-1'
    assert item['quality_score'] == 1.0
    assert item['usage_stats']['run_count'] == 2
    assert item['recent_run_ids'] == ['older-run', 'run-store']
    assert item['parent_skill_ids'] == ['parent-1']
    assert store.saved is not None
    assert store.saved.skill_judgments[0].skill_id == 'skill-store-1'
    assert store.closed is True


def test_runtime_adapters_and_metadata_handoff():
    patch_plan = EvolutionPlan(
        run_id='run-patch',
        skill_id='skill-patch',
        action='patch_current',
        parent_skill_id='skill-patch',
        reason='Runtime step kept misleading the model.',
        repair_suggestions=[
            {
                'issue_type': 'reference_structure_incomplete',
                'instruction': 'Strengthen reference guidance.',
                'target_paths': ['references/usage.md'],
                'priority': 88,
            }
        ],
    )
    derive_plan = EvolutionPlan(
        run_id='run-derive',
        skill_id='skill-derive',
        action='derive_child',
        parent_skill_id='skill-derive',
        reason='Recurring domain-specific gap.',
        requirement_gaps=['Missing Hugging Face trainer resume step for distributed training.'],
        summary='Derive a child skill for trainer resume workflows.',
    )

    suggestions = evolution_plan_to_repair_suggestions(patch_plan)
    request = evolution_plan_to_skill_create_request(
        derive_plan,
        task_summary='Improve the Hugging Face workflow skill.',
        repo_paths=['/tmp/repo'],
    )
    plan = SkillPlan(
        skill_name='hf-trainer-child',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='_meta.json', purpose='metadata', source_basis=[]),
        ],
    )
    meta_artifacts = generate_metadata_artifacts(request=request, skill_plan=plan)
    meta_payload = json.loads(next(item.content for item in meta_artifacts if item.path == '_meta.json'))

    assert suggestions[0].issue_type == 'reference_structure_incomplete'
    assert suggestions[0].repair_scope == 'body_patch'
    assert request.parent_skill_id == 'skill-derive'
    assert request.runtime_evolution_plan.action == 'derive_child'
    assert meta_payload['parent_skill_id'] == 'skill-derive'
    assert meta_payload['runtime_evolution_plan']['action'] == 'derive_child'
    assert meta_payload['runtime_evolution_plan']['summary'] == 'Derive a child skill for trainer resume workflows.'
    assert meta_payload['lineage']['parent_skill_id'] == 'skill-derive'
    assert meta_payload['lineage']['version'] == 0
    assert meta_payload['lineage']['history'][0]['event'] == 'derive_child'
