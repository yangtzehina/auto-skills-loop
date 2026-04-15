from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from ..models.online import SkillSourceCandidate
from ..models.observation import OpenSpaceObservationPolicy
from ..models.persistence import PersistencePolicy
from ..models.public_source_verification import PublicSourceCandidateConfig, PublicSourceVerificationReport
from ..models.request import SkillCreateRequestV6
from ..models.artifacts import ArtifactFile, Artifacts
from ..models.findings import RepoFindings
from ..models.plan import SkillPlan
from ..models.runtime_governance import (
    RuntimeCreateQueueReport,
    RuntimeGovernanceBatchReport,
    RuntimeGovernanceIntakeResult,
    RuntimePriorGateReport,
)
from ..models.simulation import SimulationScenarioResult, SimulationSuiteReport
from .orchestrator import derive_validation_severity, run_skill_create
from .operation_coverage import load_operation_coverage_report
from .public_source_verification import verify_public_source_candidates
from .runtime_governance import (
    build_runtime_create_queue_report,
    build_runtime_governance_batch_report,
    build_runtime_governance_intake,
    build_runtime_prior_gate_report,
)
from .runtime_handoff import load_runtime_handoff_input
from .runtime_analysis import analyze_skill_run_deterministically
from .validator import run_validator

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SIMULATION_FIXTURE_ROOT = ROOT / 'tests' / 'fixtures' / 'simulation'

FAMILY_TO_MODE = {
    'runtime_intake': 'runtime-intake',
    'runtime_batch': 'runtime-batch',
    'create_queue': 'create-queue',
    'prior_gate': 'prior-gate',
    'public_source_curation': 'source-curation',
    'smoke_chain': 'smoke-chain',
    'operation_backed': 'operation-backed',
    'methodology_guidance': 'methodology-guidance',
}
MODE_TO_FAMILY = {value: key for key, value in FAMILY_TO_MODE.items()}
FAMILY_ORDER = [
    'runtime_intake',
    'runtime_batch',
    'create_queue',
    'prior_gate',
    'public_source_curation',
    'smoke_chain',
    'operation_backed',
    'methodology_guidance',
]
QUICK_SCENARIOS = [
    ('runtime_intake', 'partial_trace_no_change'),
    ('create_queue', 'no_skill_cluster'),
    ('prior_gate', 'eligible_domain_safe'),
    ('public_source_curation', 'low_yield_reject'),
    ('public_source_curation', 'high_overlap_reject'),
    ('public_source_curation', 'acceptable_accept'),
    ('operation_backed', 'native_cli_guided_safe'),
    ('methodology_guidance', 'concept_to_mvp_pack'),
    ('methodology_guidance', 'decision_loop_stress_test'),
    ('methodology_guidance', 'simulation_resource_loop_design'),
]


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise ValueError(f'Missing fixture file: {path}') from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON in fixture {path}: {exc.msg}') from exc


def _ordered_unique(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        text = str(item or '').strip()
        if text and text not in result:
            result.append(text)
    return result


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {str(key): _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    return value


def _append_diff(diff: list[str], prefix: str, expected: Any, actual: Any) -> None:
    if len(diff) >= 10:
        return
    if type(expected) is not type(actual):
        diff.append(f'{prefix}: expected type {type(expected).__name__}, got {type(actual).__name__}')
        return
    if isinstance(expected, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                diff.append(f'{prefix}.{key}: unexpected key present')
                if len(diff) >= 10:
                    return
                continue
            if key not in actual:
                diff.append(f'{prefix}.{key}: missing key')
                if len(diff) >= 10:
                    return
                continue
            _append_diff(diff, f'{prefix}.{key}', expected[key], actual[key])
            if len(diff) >= 10:
                return
        return
    if isinstance(expected, list):
        if len(expected) != len(actual):
            diff.append(f'{prefix}: expected list length {len(expected)}, got {len(actual)}')
            return
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            _append_diff(diff, f'{prefix}[{index}]', expected_item, actual_item)
            if len(diff) >= 10:
                return
        return
    if expected != actual:
        diff.append(f'{prefix}: expected {expected!r}, got {actual!r}')


def _ensure_keys(payload: dict[str, Any], keys: list[str], *, context: str) -> None:
    for key in keys:
        if key not in payload:
            raise ValueError(f'Invalid expected projection for {context}: missing key `{key}`')


def _validate_runtime_intake_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for runtime_intake: must be an object')
    _ensure_keys(
        payload,
        ['runtime_followup_action', 'change_pack_action', 'approval_decision', 'skills_analyzed', 'create_candidate_count'],
        context='runtime_intake',
    )
    if not isinstance(payload['skills_analyzed'], list):
        raise ValueError('Invalid expected projection for runtime_intake: `skills_analyzed` must be a list')
    for item in payload['skills_analyzed']:
        if not isinstance(item, dict):
            raise ValueError('Invalid expected projection for runtime_intake: list items must be objects')
        _ensure_keys(
            item,
            ['skill_id', 'recommended_action', 'most_valuable_step', 'misleading_step'],
            context='runtime_intake.skills_analyzed',
        )
    return payload


def _validate_runtime_batch_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for runtime_batch: must be an object')
    _ensure_keys(
        payload,
        ['runs_processed', 'action_counts', 'approval_counts', 'judge_applied_count', 'create_candidate_count', 'per_skill'],
        context='runtime_batch',
    )
    if not isinstance(payload['per_skill'], list):
        raise ValueError('Invalid expected projection for runtime_batch: `per_skill` must be a list')
    for item in payload['per_skill']:
        if not isinstance(item, dict):
            raise ValueError('Invalid expected projection for runtime_batch: list items must be objects')
        _ensure_keys(
            item,
            ['skill_id', 'latest_recommended_action', 'quality_score', 'lineage_version', 'latest_lineage_event'],
            context='runtime_batch.per_skill',
        )
    return payload


def _validate_create_queue_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for create_queue: must be an object')
    _ensure_keys(payload, ['runs_processed', 'entries'], context='create_queue')
    if not isinstance(payload['entries'], list):
        raise ValueError('Invalid expected projection for create_queue: `entries` must be a list')
    for item in payload['entries']:
        if not isinstance(item, dict):
            raise ValueError('Invalid expected projection for create_queue: list items must be objects')
        _ensure_keys(
            item,
            ['candidate_key', 'occurrence_count', 'recommended_status', 'source_run_ids', 'requirement_gaps'],
            context='create_queue.entries',
        )
    return payload


def _validate_prior_gate_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for prior_gate: must be an object')
    _ensure_keys(
        payload,
        ['eligibility_summary', 'ranking_impact_summary', 'eligible_skills', 'task_impacts'],
        context='prior_gate',
    )
    if not isinstance(payload['eligible_skills'], list) or not isinstance(payload['task_impacts'], list):
        raise ValueError('Invalid expected projection for prior_gate: lists are malformed')
    for item in payload['eligible_skills']:
        if not isinstance(item, dict):
            raise ValueError('Invalid expected projection for prior_gate.eligible_skills: list items must be objects')
        _ensure_keys(item, ['skill_name', 'eligible', 'runtime_prior_delta'], context='prior_gate.eligible_skills')
    for item in payload['task_impacts']:
        if not isinstance(item, dict):
            raise ValueError('Invalid expected projection for prior_gate.task_impacts: list items must be objects')
        _ensure_keys(
            item,
            ['task', 'baseline_top_candidate', 'prior_top_candidate', 'changed_top_1', 'generic_promoted', 'prior_applied'],
            context='prior_gate.task_impacts',
        )
    return payload


def _validate_source_curation_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for public_source_curation: must be an object')
    _ensure_keys(payload, ['summary_counts', 'candidates', 'promoted_repos'], context='public_source_curation')
    if not isinstance(payload['candidates'], list):
        raise ValueError('Invalid expected projection for public_source_curation: `candidates` must be a list')
    for item in payload['candidates']:
        if not isinstance(item, dict):
            raise ValueError('Invalid expected projection for public_source_curation: list items must be objects')
        _ensure_keys(
            item,
            ['repo_full_name', 'candidate_count', 'overlap_assessment', 'structure_supported', 'verdict', 'smoke_required', 'selected_for_default'],
            context='public_source_curation.candidates',
        )
    return payload


def _validate_smoke_chain_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for smoke_chain: must be an object')
    _ensure_keys(
        payload,
        ['severity', 'reuse_decision', 'selected_online_skill_names', 'generated_files', 'evaluation_report_present', 'persisted_report_matches_memory'],
        context='smoke_chain',
    )
    return payload


def _validate_operation_backed_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for operation_backed: must be an object')
    _ensure_keys(
        payload,
        ['scenario_kind', 'skill_archetype', 'recommended_followup', 'coverage_gap_summary'],
        context='operation_backed',
    )
    return payload


def _validate_methodology_guidance_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('Invalid expected projection for methodology_guidance: must be an object')
    _ensure_keys(
        payload,
        [
            'severity',
            'skill_archetype',
            'fully_correct',
            'body_quality_status',
            'self_review_status',
            'domain_specificity_status',
            'domain_anchor_coverage_min_met',
            'missing_domain_anchors',
            'domain_expertise_status',
            'domain_move_coverage_min_met',
            'domain_expertise_warn_count',
            'expert_structure_status',
            'expert_structure_min_met',
            'expert_structure_warn_count',
            'depth_quality_status',
            'depth_quality_min_met',
            'depth_quality_warn_count',
            'body_lines_min_met',
            'required_sections_missing',
            'generated_files_contains_sidecars',
        ],
        context='methodology_guidance',
    )
    return payload


PROJECTION_VALIDATORS: dict[str, Callable[[Any], dict[str, Any]]] = {
    'runtime_intake': _validate_runtime_intake_projection,
    'runtime_batch': _validate_runtime_batch_projection,
    'create_queue': _validate_create_queue_projection,
    'prior_gate': _validate_prior_gate_projection,
    'public_source_curation': _validate_source_curation_projection,
    'smoke_chain': _validate_smoke_chain_projection,
    'operation_backed': _validate_operation_backed_projection,
    'methodology_guidance': _validate_methodology_guidance_projection,
}


def _resolve_fixture_root(fixture_root: Path | None) -> Path:
    root = (fixture_root or DEFAULT_SIMULATION_FIXTURE_ROOT).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f'Fixture root does not exist: {root}')
    return root


def _list_family_scenarios(family_root: Path) -> list[Path]:
    if not family_root.exists():
        return []
    return sorted(path for path in family_root.iterdir() if path.is_dir())


def _selected_scenario_paths(*, mode: str, fixture_root: Path, scenario_filters: list[str] | None = None) -> list[tuple[str, Path]]:
    scenario_filters = [str(item or '').strip() for item in list(scenario_filters or []) if str(item or '').strip()]
    selected: list[tuple[str, Path]] = []
    if mode == 'quick':
        requested = [
            (family, fixture_root / family / scenario_id)
            for family, scenario_id in QUICK_SCENARIOS
        ]
    elif mode == 'full':
        requested = []
        for family in FAMILY_ORDER:
            requested.extend((family, path) for path in _list_family_scenarios(fixture_root / family))
    else:
        family = MODE_TO_FAMILY[mode]
        requested = [(family, path) for path in _list_family_scenarios(fixture_root / family)]

    for family, path in requested:
        scenario_id = path.name
        if scenario_filters:
            family_key = f'{family}/{scenario_id}'
            if scenario_id not in scenario_filters and family_key not in scenario_filters:
                continue
        selected.append((family, path))
    return selected


def _runtime_intake_projection(result: RuntimeGovernanceIntakeResult) -> dict[str, Any]:
    analysis = result.runtime_hook.runtime_cycle.analysis if result.runtime_hook.runtime_cycle is not None else None
    items = []
    for item in list(analysis.skills_analyzed if analysis is not None else []):
        items.append(
            {
                'skill_id': str(item.get('skill_id') or '').strip(),
                'recommended_action': str(item.get('recommended_action') or '').strip(),
                'most_valuable_step': str(item.get('most_valuable_step') or '').strip(),
                'misleading_step': str(item.get('misleading_step') or '').strip(),
            }
        )
    return {
        'runtime_followup_action': result.runtime_hook.runtime_cycle.followup.action if result.runtime_hook.runtime_cycle is not None else '',
        'change_pack_action': result.runtime_hook.change_pack.recommended_action if result.runtime_hook.change_pack is not None else '',
        'approval_decision': result.runtime_hook.approval_pack.approval_decision if result.runtime_hook.approval_pack is not None else '',
        'skills_analyzed': items,
        'create_candidate_count': len(analysis.create_candidates or []) if analysis is not None else 0,
    }


def _runtime_batch_projection(report: RuntimeGovernanceBatchReport) -> dict[str, Any]:
    return {
        'runs_processed': report.runs_processed,
        'action_counts': dict(report.action_counts or {}),
        'approval_counts': dict(report.approval_counts or {}),
        'judge_applied_count': report.judge_applied_count,
        'create_candidate_count': len(report.create_candidates or []),
        'per_skill': [
            {
                'skill_id': item.skill_id,
                'latest_recommended_action': item.latest_recommended_action,
                'quality_score': item.quality_score,
                'lineage_version': item.lineage_version,
                'latest_lineage_event': item.latest_lineage_event,
            }
            for item in list(report.per_skill or [])
        ],
    }


def _create_queue_projection(report: RuntimeCreateQueueReport) -> dict[str, Any]:
    return {
        'runs_processed': report.runs_processed,
        'entries': [
            {
                'candidate_key': item.candidate_key,
                'occurrence_count': item.occurrence_count,
                'recommended_status': item.recommended_status,
                'source_run_ids': list(item.source_run_ids or []),
                'requirement_gaps': list(item.requirement_gaps or []),
            }
            for item in list(report.entries or [])
        ],
    }


def _prior_gate_projection(report: RuntimePriorGateReport) -> dict[str, Any]:
    return {
        'eligibility_summary': dict(report.eligibility_summary or {}),
        'ranking_impact_summary': dict(report.ranking_impact_summary or {}),
        'eligible_skills': [
            {
                'skill_name': item.skill_name,
                'eligible': item.eligible,
                'runtime_prior_delta': item.runtime_prior_delta,
            }
            for item in list(report.eligible_skills or [])
        ],
        'task_impacts': [
            {
                'task': item.task,
                'baseline_top_candidate': item.baseline_top_candidate,
                'prior_top_candidate': item.prior_top_candidate,
                'changed_top_1': item.changed_top_1,
                'generic_promoted': item.generic_promoted,
                'prior_applied': item.prior_applied,
            }
            for item in list(report.task_impacts or [])
        ],
    }


def _source_curation_projection(report: PublicSourceVerificationReport) -> dict[str, Any]:
    return {
        'summary_counts': {
            'accepted': len(report.accepted_repos or []),
            'rejected': len(report.rejected_repos or []),
            'manual_review': len(report.manual_review_repos or []),
            'promoted': len(report.promoted_repos or []),
        },
        'candidates': [
            {
                'repo_full_name': item.repo_full_name,
                'candidate_count': item.candidate_count,
                'overlap_assessment': item.overlap_assessment,
                'structure_supported': item.structure_supported,
                'verdict': item.verdict,
                'smoke_required': item.smoke_required,
                'selected_for_default': item.selected_for_default,
            }
            for item in list(report.candidates or [])
        ],
        'promoted_repos': list(report.promoted_repos or []),
    }


def _smoke_chain_projection(response, *, output_root: Path) -> dict[str, Any]:
    selected_ids = set(response.reuse_decision.selected_candidate_ids if response.reuse_decision is not None else [])
    selected_names = [
        item.name
        for item in list(response.online_skill_candidates or [])
        if item.candidate_id in selected_ids
    ]
    persisted_report_matches_memory = False
    persisted_root = Path(str((response.persistence or {}).get('output_root') or output_root))
    report_path = persisted_root / 'evals' / 'report.json'
    if report_path.exists() and response.evaluation_report is not None:
        persisted_report_matches_memory = (
            json.loads(report_path.read_text(encoding='utf-8'))
            == response.evaluation_report.model_dump(mode='json')
        )
    return {
        'severity': response.severity,
        'reuse_decision': response.reuse_decision.mode if response.reuse_decision is not None else '',
        'selected_online_skill_names': selected_names,
        'generated_files': sorted(item.path for item in list(response.artifacts.files or [])) if response.artifacts is not None else [],
        'evaluation_report_present': response.evaluation_report is not None,
        'persisted_report_matches_memory': persisted_report_matches_memory,
    }


def _run_runtime_intake_scenario(scenario_root: Path) -> dict[str, Any]:
    handoff = load_runtime_handoff_input((scenario_root / 'input' / 'handoff.json').read_text(encoding='utf-8'))
    result = build_runtime_governance_intake(
        handoff=handoff,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )
    return _runtime_intake_projection(result)


def _run_runtime_batch_scenario(scenario_root: Path) -> dict[str, Any]:
    report = build_runtime_governance_batch_report(
        source_path=scenario_root / 'input' / 'manifest.json',
        policy=OpenSpaceObservationPolicy(enabled=False),
    )
    return _runtime_batch_projection(report)


def _run_create_queue_scenario(scenario_root: Path) -> dict[str, Any]:
    report = build_runtime_create_queue_report(
        source_path=scenario_root / 'input' / 'manifest.json',
        policy=OpenSpaceObservationPolicy(enabled=False),
    )
    return _create_queue_projection(report)


def _run_prior_gate_scenario(scenario_root: Path) -> dict[str, Any]:
    payload = _load_json(scenario_root / 'input' / 'spec.json')
    if not isinstance(payload, dict):
        raise ValueError(f'Invalid prior gate fixture: {scenario_root / "input" / "spec.json"} must be an object')
    catalog = [
        SkillSourceCandidate.model_validate(item)
        for item in list(payload.get('catalog') or [])
    ]
    report = build_runtime_prior_gate_report(
        catalog=catalog,
        runtime_effectiveness_lookup=dict(payload.get('runtime_effectiveness_lookup') or {}),
        task_samples=list(payload.get('task_samples') or []),
        runtime_effectiveness_min_runs=int(payload.get('runtime_effectiveness_min_runs', 5) or 5),
        runtime_effectiveness_allowed_families=list(payload.get('runtime_effectiveness_allowed_families') or []) or None,
    )
    return _prior_gate_projection(report)


def _source_provider_factory(payload: dict[str, Any]) -> Callable[..., Any]:
    repos = dict(payload.get('repos') or {})

    class _FixtureProvider:
        def __init__(self, *, collections, max_candidates, max_candidates_per_collection):
            seed = collections[0]
            self.repo_full_name = str(seed.get('repo_full_name') or '').strip()

        def list_candidates(self):
            repo_payload = repos.get(self.repo_full_name)
            if repo_payload is None:
                return []
            if isinstance(repo_payload, dict) and repo_payload.get('error'):
                raise RuntimeError(str(repo_payload.get('error')))
            items = repo_payload.get('candidates') if isinstance(repo_payload, dict) else repo_payload
            return [SkillSourceCandidate.model_validate(item) for item in list(items or [])]

    return _FixtureProvider


def _source_existing_resolver(payload: dict[str, Any]) -> Callable[[str], list[SkillSourceCandidate]]:
    task_mapping = dict(payload.get('tasks') or {})

    def _resolver(task: str) -> list[SkillSourceCandidate]:
        return [
            SkillSourceCandidate.model_validate(item)
            for item in list(task_mapping.get(task, []) or [])
        ]

    return _resolver


def _run_source_curation_scenario(scenario_root: Path) -> dict[str, Any]:
    config_payload = _load_json(scenario_root / 'input' / 'config.json')
    raw_configs = config_payload.get('candidates') if isinstance(config_payload, dict) else config_payload
    configs = [PublicSourceCandidateConfig.model_validate(item) for item in list(raw_configs or [])]
    report = verify_public_source_candidates(
        candidate_configs=configs,
        provider_factory=_source_provider_factory(_load_json(scenario_root / 'input' / 'provider_payload.json')),
        existing_candidates_resolver=_source_existing_resolver(_load_json(scenario_root / 'input' / 'existing_candidates.json')),
    )
    return _source_curation_projection(report)


def _resolve_request_paths(payload: dict[str, Any], *, scenario_root: Path) -> dict[str, Any]:
    item = dict(payload)
    repo_paths = []
    for path_value in list(item.get('repo_paths') or []):
        path = Path(str(path_value or '').strip())
        if not path.is_absolute():
            path = (scenario_root / path).resolve()
        repo_paths.append(str(path))
    item['repo_paths'] = repo_paths
    baseline_path = str(item.get('runtime_hook_baseline_path') or '').strip()
    if baseline_path:
        baseline = Path(baseline_path)
        if not baseline.is_absolute():
            baseline = (scenario_root / baseline).resolve()
        item['runtime_hook_baseline_path'] = str(baseline)
    return item


def _run_smoke_chain_scenario(scenario_root: Path) -> dict[str, Any]:
    payload = _load_json(scenario_root / 'input' / 'request.json')
    if not isinstance(payload, dict):
        raise ValueError(f'Invalid smoke chain fixture: {scenario_root / "input" / "request.json"} must be an object')
    request = SkillCreateRequestV6.model_validate(_resolve_request_paths(payload, scenario_root=scenario_root / 'input'))
    with tempfile.TemporaryDirectory(prefix='simulation-smoke-chain-') as tmpdir:
        output_root = Path(tmpdir) / 'generated'
        response = run_skill_create(
            request,
            output_root=str(output_root),
            persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
            fail_fast_on_validation_fail=False,
        )
        return _smoke_chain_projection(response, output_root=output_root)


def _run_operation_backed_scenario(scenario_root: Path) -> dict[str, Any]:
    payload = _load_json(scenario_root / 'input' / 'spec.json')
    if not isinstance(payload, dict):
        raise ValueError(f'Invalid operation-backed fixture: {scenario_root / "input" / "spec.json"} must be an object')
    scenario_kind = str(payload.get('scenario_kind') or 'skill_create').strip().lower()
    if scenario_kind == 'skill_create':
        request = SkillCreateRequestV6.model_validate(_resolve_request_paths(dict(payload.get('request') or {}), scenario_root=scenario_root / 'input'))
        with tempfile.TemporaryDirectory(prefix='simulation-operation-backed-') as tmpdir:
            output_root = Path(tmpdir) / 'generated'
            response = run_skill_create(
                request,
                output_root=str(output_root),
                persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
                fail_fast_on_validation_fail=False,
            )
            coverage = load_operation_coverage_report(response.artifacts)
            security_audit = getattr(response.diagnostics, 'security_audit', None) if response.diagnostics is not None else None
            return {
                'scenario_kind': 'skill_create',
                'severity': response.severity,
                'skill_archetype': str(getattr(response.skill_plan, 'skill_archetype', 'guidance') or 'guidance'),
                'operation_validation_status': (
                    str(getattr(coverage, 'validation_status', '') or '')
                    if coverage is not None
                    else str(getattr(response.quality_review, 'operation_validation_status', '') or '')
                ),
                'recommended_followup': (
                    str(getattr(coverage, 'recommended_followup', 'no_change') or 'no_change')
                    if coverage is not None
                    else str(getattr(response.quality_review, 'recommended_followup', 'no_change') or 'no_change')
                ),
                'coverage_gap_summary': (
                    [item.gap_type for item in list(getattr(coverage, 'gap_summary', []) or [])]
                    if coverage is not None
                    else list(getattr(response.quality_review, 'coverage_gap_summary', []) or [])
                ),
                'security_rating': str(getattr(security_audit, 'rating', 'LOW') or 'LOW'),
                'generated_files': sorted(item.path for item in list(response.artifacts.files or [])) if response.artifacts is not None else [],
            }
    if scenario_kind == 'runtime_analysis':
        analysis = analyze_skill_run_deterministically(
            payload.get('run_record') or {},
            recent_skill_history=dict(payload.get('recent_skill_history') or {}),
            parent_skill_ids=dict(payload.get('parent_skill_ids') or {}),
        )
        selected = next((plan for plan in list(analysis.evolution_plans or []) if plan.action != 'no_change'), analysis.evolution_plans[0])
        matched = next((item for item in list(analysis.skills_analyzed or []) if item.get('skill_id') == selected.skill_id), analysis.skills_analyzed[0])
        return {
            'scenario_kind': 'runtime_analysis',
            'skill_archetype': str(matched.get('skill_archetype') or 'guidance'),
            'selected_action': selected.action,
            'operation_validation_status': str(matched.get('operation_validation_status') or ''),
            'recommended_followup': str(matched.get('recommended_followup') or selected.action or 'no_change'),
            'coverage_gap_summary': list(matched.get('coverage_gap_summary') or []),
        }
    if scenario_kind == 'direct_validation':
        plan = SkillPlan.model_validate(payload.get('skill_plan') or {})
        artifacts = Artifacts(
            files=[
                ArtifactFile.model_validate(item)
                for item in list((payload.get('artifacts') or {}).get('files') or [])
            ]
        )
        diagnostics = run_validator(
            request=SkillCreateRequestV6(task=str(payload.get('task') or 'validate operation-backed fixture').strip()),
            repo_findings=RepoFindings(),
            skill_plan=plan,
            artifacts=artifacts,
        )
        coverage = load_operation_coverage_report(artifacts)
        security_audit = getattr(diagnostics, 'security_audit', None)
        return {
            'scenario_kind': 'direct_validation',
            'severity': derive_validation_severity(diagnostics),
            'skill_archetype': str(getattr(plan, 'skill_archetype', 'guidance') or 'guidance'),
            'operation_validation_status': (
                str(getattr(coverage, 'validation_status', '') or '')
                if coverage is not None
                else 'needs_attention'
            ),
            'recommended_followup': (
                str(getattr(coverage, 'recommended_followup', 'hold') or 'hold')
                if coverage is not None
                else 'hold'
            ),
            'coverage_gap_summary': (
                [item.gap_type for item in list(getattr(coverage, 'gap_summary', []) or [])]
                if coverage is not None
                else [item for item in list(getattr(diagnostics.validation, 'repairable_issue_types', []) or []) if item.startswith('operation_')]
            ),
            'security_rating': str(getattr(security_audit, 'rating', 'LOW') or 'LOW'),
        }
    raise ValueError(f'Unsupported operation_backed scenario_kind: {scenario_kind}')


def _run_methodology_guidance_scenario(scenario_root: Path) -> dict[str, Any]:
    payload = _load_json(scenario_root / 'input' / 'request.json')
    if not isinstance(payload, dict):
        raise ValueError(f'Invalid methodology fixture: {scenario_root / "input" / "request.json"} must be an object')
    request = SkillCreateRequestV6.model_validate(_resolve_request_paths(payload, scenario_root=scenario_root / 'input'))
    with tempfile.TemporaryDirectory(prefix='simulation-methodology-guidance-') as tmpdir:
        output_root = Path(tmpdir) / 'generated'
        response = run_skill_create(
            request,
            output_root=str(output_root),
            persistence_policy=PersistencePolicy(dry_run=False, overwrite=True, persist_evaluation_report=True),
            fail_fast_on_validation_fail=False,
        )
        body_quality = getattr(response.diagnostics, 'body_quality', None) if response.diagnostics is not None else None
        self_review = getattr(response.diagnostics, 'self_review', None) if response.diagnostics is not None else None
        domain_specificity = getattr(response.diagnostics, 'domain_specificity', None) if response.diagnostics is not None else None
        domain_expertise = getattr(response.diagnostics, 'domain_expertise', None) if response.diagnostics is not None else None
        expert_structure = getattr(response.diagnostics, 'expert_structure', None) if response.diagnostics is not None else None
        depth_quality = getattr(response.diagnostics, 'depth_quality', None) if response.diagnostics is not None else None
        generated_files = sorted(item.path for item in list(response.artifacts.files or [])) if response.artifacts is not None else []
        return {
            'severity': response.severity,
            'skill_archetype': str(getattr(response.skill_plan, 'skill_archetype', '') or ''),
            'fully_correct': bool(getattr(response.quality_review, 'fully_correct', False)),
            'body_quality_status': str(getattr(body_quality, 'status', '') or ''),
            'self_review_status': str(getattr(self_review, 'status', '') or ''),
            'domain_specificity_status': str(getattr(domain_specificity, 'status', '') or ''),
            'domain_anchor_coverage_min_met': float(getattr(domain_specificity, 'domain_anchor_coverage', 0.0) or 0.0) >= 0.70,
            'missing_domain_anchors': list(getattr(domain_specificity, 'missing_domain_anchors', []) or []),
            'domain_expertise_status': str(getattr(domain_expertise, 'status', '') or ''),
            'domain_move_coverage_min_met': float(getattr(domain_expertise, 'domain_move_coverage', 0.0) or 0.0) >= 0.45,
            'domain_expertise_warn_count': len(list(getattr(domain_expertise, 'warning_issues', []) or [])),
            'expert_structure_status': str(getattr(expert_structure, 'status', '') or ''),
            'expert_structure_min_met': (
                str(getattr(expert_structure, 'status', '') or '') == 'pass'
                or str(getattr(expert_structure, 'status', '') or '') == 'warn'
            ),
            'expert_structure_warn_count': len(list(getattr(expert_structure, 'warning_issues', []) or [])),
            'depth_quality_status': str(getattr(depth_quality, 'status', '') or ''),
            'depth_quality_min_met': (
                str(getattr(depth_quality, 'status', '') or '') == 'pass'
                or str(getattr(depth_quality, 'status', '') or '') == 'warn'
            ),
            'depth_quality_warn_count': len(list(getattr(depth_quality, 'warning_issues', []) or [])),
            'body_lines_min_met': int(getattr(body_quality, 'body_lines', 0) or 0) >= 35,
            'required_sections_missing': list(getattr(body_quality, 'missing_required_sections', []) or []),
            'generated_files_contains_sidecars': (
                'evals/body_quality.json' in generated_files
                and 'evals/self_review.json' in generated_files
                and 'evals/domain_specificity.json' in generated_files
                and 'evals/domain_expertise.json' in generated_files
                and 'evals/expert_structure.json' in generated_files
                and 'evals/depth_quality.json' in generated_files
            ),
        }


FAMILY_RUNNERS: dict[str, Callable[[Path], dict[str, Any]]] = {
    'runtime_intake': _run_runtime_intake_scenario,
    'runtime_batch': _run_runtime_batch_scenario,
    'create_queue': _run_create_queue_scenario,
    'prior_gate': _run_prior_gate_scenario,
    'public_source_curation': _run_source_curation_scenario,
    'smoke_chain': _run_smoke_chain_scenario,
    'operation_backed': _run_operation_backed_scenario,
    'methodology_guidance': _run_methodology_guidance_scenario,
}


def _load_expected_projection(*, family: str, scenario_root: Path) -> dict[str, Any]:
    expected = _load_json(scenario_root / 'expected' / 'result.json')
    validator = PROJECTION_VALIDATORS[family]
    return _round_floats(validator(expected))


def _run_scenario(*, family: str, scenario_root: Path) -> SimulationScenarioResult:
    scenario_id = scenario_root.name
    try:
        expected_projection = _load_expected_projection(family=family, scenario_root=scenario_root)
    except ValueError as exc:
        return SimulationScenarioResult(
            family=family,
            scenario_id=scenario_id,
            status='invalid-fixture',
            error_kind='fixture_error',
            summary=str(exc),
        )
    try:
        actual_projection = _round_floats(FAMILY_RUNNERS[family](scenario_root))
        PROJECTION_VALIDATORS[family](actual_projection)
    except Exception as exc:
        return SimulationScenarioResult(
            family=family,
            scenario_id=scenario_id,
            status='drifted',
            expected_projection=expected_projection,
            actual_projection={},
            error_kind='execution_error',
            diff_summary=[str(exc)],
            summary=f'{family}/{scenario_id} drifted during execution',
        )

    if actual_projection == expected_projection:
        return SimulationScenarioResult(
            family=family,
            scenario_id=scenario_id,
            status='matched',
            expected_projection=expected_projection,
            actual_projection=actual_projection,
            summary=f'{family}/{scenario_id} matched the checked-in projection',
        )

    diff: list[str] = []
    _append_diff(diff, 'projection', expected_projection, actual_projection)
    return SimulationScenarioResult(
        family=family,
        scenario_id=scenario_id,
        status='drifted',
        expected_projection=expected_projection,
        actual_projection=actual_projection,
        diff_summary=diff or ['Projection mismatch'],
        error_kind='projection_mismatch',
        summary=f'{family}/{scenario_id} drifted from the checked-in projection',
    )


def render_simulation_suite_markdown(report: SimulationSuiteReport) -> str:
    lines = [
        '# Simulation Suite Report',
        '',
        f'- Mode: {report.mode}',
        f'- Fixture root: `{report.fixture_root}`',
        f'- Summary: {report.summary}',
        f'- matched={report.matched_count} drifted={report.drifted_count} invalid_fixture={report.invalid_fixture_count}',
        '',
    ]
    grouped: dict[str, list[SimulationScenarioResult]] = {}
    for item in list(report.scenario_results or []):
        grouped.setdefault(item.family, []).append(item)
    for family in FAMILY_ORDER:
        family_items = grouped.get(family, [])
        if not family_items:
            continue
        lines.append(f'## {family}')
        for item in family_items:
            lines.append(f'- `{item.scenario_id}` [{item.status}]')
            lines.append(f'  - {item.summary}')
            if item.diff_summary:
                lines.append(f'  - diff_summary={item.diff_summary}')
        lines.append('')
    return '\n'.join(lines).strip()


def build_simulation_suite_report(
    *,
    mode: str,
    fixture_root: Path | None = None,
    scenario_names: list[str] | None = None,
) -> SimulationSuiteReport:
    allowed_modes = {'quick', 'full'} | set(MODE_TO_FAMILY)
    if mode not in allowed_modes:
        raise ValueError(f'Unsupported mode: {mode}')
    root = _resolve_fixture_root(fixture_root)
    scenario_paths = _selected_scenario_paths(mode=mode, fixture_root=root, scenario_filters=scenario_names)
    if not scenario_paths:
        raise ValueError(f'No simulation scenarios matched mode `{mode}`')
    scenario_results = [
        _run_scenario(family=family, scenario_root=path)
        for family, path in scenario_paths
    ]
    matched_count = sum(1 for item in scenario_results if item.status == 'matched')
    drifted_count = sum(1 for item in scenario_results if item.status == 'drifted')
    invalid_fixture_count = sum(1 for item in scenario_results if item.status == 'invalid-fixture')
    report = SimulationSuiteReport(
        mode=mode,
        fixture_root=str(root),
        scenario_results=scenario_results,
        matched_count=matched_count,
        drifted_count=drifted_count,
        invalid_fixture_count=invalid_fixture_count,
        summary=(
            f'Simulation suite complete: '
            f'scenarios={len(scenario_results)} matched={matched_count} '
            f'drifted={drifted_count} invalid_fixture={invalid_fixture_count}'
        ),
    )
    report.markdown_summary = render_simulation_suite_markdown(report)
    return report
