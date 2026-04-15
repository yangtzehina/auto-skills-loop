from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Optional

from ..models.ops_approval import OpsApprovalState
from ..models.online import SkillSourceCandidate
from ..models.observation import OpenSpaceObservationPolicy
from ..models.runtime import RuntimeCreateCandidate, RuntimeSessionEvidence, SkillRunRecord
from ..models.runtime_governance import (
    RuntimeGovernanceBatchReport,
    RuntimeGovernanceBatchSkillReport,
    RuntimeGovernanceBundle,
    RuntimeGovernanceIntakeResult,
    RuntimeOpsDecisionPack,
    RuntimeCreateSeedProposal,
    RuntimeCreateSeedProposalPack,
    RuntimeCreateReviewEntry,
    RuntimeCreateReviewPack,
    RuntimeCreateQueueEntry,
    RuntimeCreateQueueReport,
    RuntimePriorEligibleSkill,
    RuntimePriorGateReport,
    RuntimePriorPilotExerciseReport,
    RuntimePriorPilotProfile,
    RuntimePriorPilotReport,
    RuntimePriorRolloutFamilyReport,
    RuntimePriorRolloutReport,
    RuntimePriorTaskImpact,
)
from ..models.request import SkillCreateRequestV6
from ..models.runtime_handoff import RuntimeHandoffEnvelope
from ..models.runtime_usage import RuntimeUsageSkillReport
from ..models.public_source_verification import PublicSourceCurationRoundReport, PublicSourcePromotionPack
from ..models.verify import VerifyReport
from .online_discovery import discover_online_skills
from .ops_approval import (
    apply_approval_to_create_seed_proposal,
    apply_approval_to_prior_pilot_profile,
    summarize_decision_statuses,
)
from .runtime_handoff import normalize_runtime_handoff
from .runtime_hook import run_runtime_hook
from .runtime_lineage import latest_lineage_details
from .runtime_cycle import replay_runtime_runs
from .runtime_replay_judge import LLMRunner
from .runtime_semantic import build_runtime_semantic_summary
from .runtime_usage import build_runtime_usage_report

CREATE_QUEUE_SIMPLE_GAP_KEYWORDS = (
    'file',
    'placeholder',
    'todo',
    'stub',
    'frontmatter',
    'metadata',
    '.skill_id',
)
GENERIC_SKILL_MARKERS = (
    'deep-research',
    'research',
    'orchestration',
    'workflow',
    'planning',
    'docs',
    'documentation',
)


def _ordered_unique(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


def _selected_skill_ids(run_record: SkillRunRecord) -> list[str]:
    return _ordered_unique(item.get('skill_id', '') for item in list(run_record.skills_used or []))


def _select_skill_snapshot(report, *, skill_id: str) -> RuntimeUsageSkillReport | None:
    for item in list(report.skill_reports or []):
        if item.skill_id == skill_id:
            return item
    return report.skill_reports[0] if report.skill_reports else None


def _normalize_gap_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', str(value or '').strip().lower()).strip('-')


def _is_simple_gap(value: str) -> bool:
    normalized = str(value or '').strip().lower()
    return any(keyword in normalized for keyword in CREATE_QUEUE_SIMPLE_GAP_KEYWORDS)


def _recommended_create_status(*, occurrence_count: int, latest_confidence: float) -> str:
    if occurrence_count >= 2 or latest_confidence >= 0.8:
        return 'review'
    if occurrence_count <= 0 and latest_confidence < 0.65:
        return 'ignore'
    return 'defer'


def _suggested_title(candidate_key: str) -> str:
    tokens = [token for token in str(candidate_key or '').strip().split('-') if token]
    if not tokens:
        return 'Runtime Skill Candidate'
    titled = []
    for token in tokens:
        if token.upper() in {'API', 'CLI', 'JSON', 'YAML'} or token in {'fits'}:
            titled.append(token.upper())
        else:
            titled.append(token.capitalize())
    return ' '.join(titled)


def _suggested_skill_name_hint(candidate_key: str, suggested_title: str) -> str:
    normalized = _normalize_gap_key(candidate_key)
    if normalized:
        return normalized
    title_normalized = _normalize_gap_key(suggested_title)
    return title_normalized or 'runtime-skill-candidate'


def _quality_band(value: float) -> str:
    score = float(value or 0.0)
    if score >= 0.8:
        return 'high'
    if score >= 0.6:
        return 'medium'
    return 'low'


def _normalize_allowed_family_values(values: Optional[Iterable[str]]) -> list[str]:
    normalized: list[str] = []
    for value in list(values or []):
        text = _normalize_gap_key(str(value or '').strip().lower())
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _is_generic_candidate(candidate: SkillSourceCandidate) -> bool:
    normalized_name = str(candidate.name or '').strip().lower()
    if any(marker in normalized_name for marker in GENERIC_SKILL_MARKERS):
        return True
    tags = [str(item or '').strip().lower() for item in list(candidate.tags or [])]
    return any(marker in tags for marker in GENERIC_SKILL_MARKERS)


def _family_allowed(
    *,
    family: str,
    allowed_families: Optional[Iterable[str]],
) -> bool:
    normalized_allowed = _normalize_allowed_family_values(allowed_families)
    if not normalized_allowed:
        return True
    return _normalize_gap_key(family) in normalized_allowed


def build_runtime_governance_bundle(
    *,
    run_record: SkillRunRecord,
    policy: Optional[OpenSpaceObservationPolicy],
    session_evidence: Optional[RuntimeSessionEvidence] = None,
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    enable_llm_judge: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
    runtime_hook_result=None,
) -> RuntimeGovernanceBundle:
    normalized_evidence = (
        session_evidence
        if session_evidence is None or isinstance(session_evidence, RuntimeSessionEvidence)
        else RuntimeSessionEvidence.model_validate(session_evidence)
    )
    runtime_hook = runtime_hook_result or run_runtime_hook(
        run_record=run_record,
        policy=policy,
        session_evidence=normalized_evidence,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
        enable_llm_judge=enable_llm_judge,
        llm_runner=llm_runner,
        model=model,
    )

    usage_snapshots: list[RuntimeUsageSkillReport] = []
    skipped_skill_ids: list[str] = []
    for skill_id in _selected_skill_ids(run_record):
        if not skill_id:
            continue
        report = build_runtime_usage_report(policy=policy, skill_id=skill_id)
        snapshot = _select_skill_snapshot(report, skill_id=skill_id) if report.applied else None
        if snapshot is not None:
            usage_snapshots.append(snapshot)
        else:
            skipped_skill_ids.append(skill_id)

    usage_note = f'usage_snapshots={len(usage_snapshots)}'
    if skipped_skill_ids:
        usage_note += f'; usage_skipped={len(skipped_skill_ids)}'
    semantic_summary = None
    if runtime_hook.runtime_cycle is not None:
        semantic_summary = build_runtime_semantic_summary(
            run_record=run_record,
            analysis=runtime_hook.runtime_cycle.analysis,
            session_evidence=normalized_evidence,
        )

    return RuntimeGovernanceBundle(
        run_record=run_record,
        runtime_hook=runtime_hook,
        usage_snapshots=usage_snapshots,
        create_candidates=list(runtime_hook.runtime_cycle.analysis.create_candidates or []),
        semantic_summary=semantic_summary,
        summary=(
            f'Runtime governance bundle complete: '
            f'followup_action={runtime_hook.runtime_cycle.followup.action if runtime_hook.runtime_cycle else "n/a"}; '
            f'create_candidates={len(runtime_hook.runtime_cycle.analysis.create_candidates or [])}; '
            f'semantic_summary={"yes" if semantic_summary is not None else "no"}; '
            f'{usage_note}'
        ),
    )


def build_runtime_governance_intake(
    *,
    handoff: RuntimeHandoffEnvelope | dict[str, Any],
    policy: Optional[OpenSpaceObservationPolicy],
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    enable_llm_judge: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
) -> RuntimeGovernanceIntakeResult:
    envelope = handoff if isinstance(handoff, RuntimeHandoffEnvelope) else RuntimeHandoffEnvelope.model_validate(handoff)
    normalized = normalize_runtime_handoff(envelope)
    runtime_hook = run_runtime_hook(
        run_record=normalized.skill_run_record,
        policy=policy,
        session_evidence=normalized.runtime_session_evidence,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
        enable_llm_judge=enable_llm_judge,
        llm_runner=llm_runner,
        model=model,
    )
    bundle = build_runtime_governance_bundle(
        run_record=normalized.skill_run_record,
        policy=policy,
        session_evidence=normalized.runtime_session_evidence,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
        enable_llm_judge=enable_llm_judge,
        llm_runner=llm_runner,
        model=model,
        runtime_hook_result=runtime_hook,
    )
    return RuntimeGovernanceIntakeResult(
        handoff=envelope,
        normalized=normalized,
        runtime_hook=runtime_hook,
        governance_bundle=bundle,
        semantic_summary=bundle.semantic_summary or normalized.runtime_semantic_summary,
        summary=(
            f'Runtime governance intake complete: '
            f'run_id={normalized.skill_run_record.run_id}; '
            f'trace_steps={len(normalized.skill_run_record.step_trace)}; '
            f'create_candidates={len(bundle.create_candidates)}; '
            f'semantic_summary={"yes" if (bundle.semantic_summary or normalized.runtime_semantic_summary) is not None else "no"}'
        ),
    )


def _load_run_record(raw: str) -> SkillRunRecord:
    payload = json.loads(raw)
    return SkillRunRecord.model_validate(payload)


def _resolve_run_record_paths(source_path: Path) -> list[Path]:
    if source_path.is_dir():
        return sorted(path for path in source_path.glob('*.json') if path.is_file())
    if not source_path.exists() or not source_path.is_file():
        raise ValueError(f'Not a file or directory: {source_path}')

    payload = json.loads(source_path.read_text(encoding='utf-8'))
    relative_paths: list[str]
    if isinstance(payload, list):
        relative_paths = [str(item or '').strip() for item in payload]
    elif isinstance(payload, dict):
        relative_paths = [
            str(item or '').strip()
            for item in (
                payload.get('run_records')
                or payload.get('run_files')
                or payload.get('runs')
                or []
            )
        ]
    else:
        raise ValueError('Batch manifest must be a JSON array or object')

    resolved: list[Path] = []
    for item in relative_paths:
        if not item:
            continue
        path = Path(item)
        if not path.is_absolute():
            path = (source_path.parent / path).resolve()
        if not path.exists() or not path.is_file():
            raise ValueError(f'Run record file not found: {path}')
        resolved.append(path)
    return resolved


def _bundle_targets_skill(bundle: RuntimeGovernanceBundle, skill_id: str) -> bool:
    wanted = str(skill_id or '').strip()
    if not wanted:
        return True
    if any(item.get('skill_id') == wanted for item in list(bundle.run_record.skills_used or [])):
        return True
    if any(item.skill_id == wanted for item in list(bundle.usage_snapshots or [])):
        return True
    if bundle.runtime_hook.runtime_cycle is not None:
        return any(
            item.get('skill_id') == wanted
            for item in list(bundle.runtime_hook.runtime_cycle.analysis.skills_analyzed or [])
        )
    return False


def _aggregate_batch_skill_reports(per_run: list[RuntimeGovernanceBundle]) -> list[RuntimeGovernanceBatchSkillReport]:
    aggregated: dict[str, dict[str, Any]] = {}
    for bundle in per_run:
        run_id = bundle.run_record.run_id
        usage_by_skill = {item.skill_id: item for item in list(bundle.usage_snapshots or [])}
        analysis_items = []
        if bundle.runtime_hook.runtime_cycle is not None:
            analysis_items = list(bundle.runtime_hook.runtime_cycle.analysis.skills_analyzed or [])

        for item in analysis_items:
            skill_id = str(item.get('skill_id') or '').strip()
            if not skill_id:
                continue
            state = aggregated.setdefault(
                skill_id,
                {
                    'skill_name': str(item.get('skill_name') or '').strip(),
                    'skill_archetype': str(item.get('skill_archetype') or 'guidance').strip().lower() or 'guidance',
                    'quality_scores': [],
                    'recent_actions': [],
                    'recent_run_ids': [],
                    'latest_recommended_action': 'no_change',
                    'operation_validation_status': str(item.get('operation_validation_status') or '').strip().lower(),
                    'coverage_gap_summary': list(item.get('coverage_gap_summary') or []),
                    'parent_skill_ids': [],
                    'lineage_version': 0,
                    'latest_lineage_event': '',
                    'snapshot': None,
                },
            )
            if item.get('skill_name'):
                state['skill_name'] = str(item.get('skill_name') or '').strip()
            if item.get('skill_archetype'):
                state['skill_archetype'] = str(item.get('skill_archetype') or 'guidance').strip().lower() or 'guidance'
            state['quality_scores'].append(float(item.get('run_quality_score', 0.0) or 0.0))
            action = str(item.get('recommended_action') or '').strip() or 'no_change'
            state['recent_actions'].append(action)
            state['recent_run_ids'].append(run_id)
            state['latest_recommended_action'] = action
            if item.get('operation_validation_status'):
                state['operation_validation_status'] = str(item.get('operation_validation_status') or '').strip().lower()
            if item.get('coverage_gap_summary'):
                state['coverage_gap_summary'] = _ordered_unique(
                    list(state.get('coverage_gap_summary') or []) + list(item.get('coverage_gap_summary') or [])
                )
            snapshot = usage_by_skill.get(skill_id)
            if snapshot is not None:
                state['snapshot'] = snapshot
                if snapshot.skill_name:
                    state['skill_name'] = snapshot.skill_name
                if snapshot.parent_skill_ids:
                    state['parent_skill_ids'] = list(snapshot.parent_skill_ids)

        for skill_id, snapshot in usage_by_skill.items():
            state = aggregated.setdefault(
                skill_id,
                {
                    'skill_name': snapshot.skill_name,
                    'skill_archetype': 'guidance',
                    'quality_scores': [],
                    'recent_actions': [],
                    'recent_run_ids': [],
                    'latest_recommended_action': snapshot.latest_recommended_action,
                    'operation_validation_status': '',
                    'coverage_gap_summary': [],
                    'parent_skill_ids': list(snapshot.parent_skill_ids),
                    'lineage_version': int(snapshot.lineage_version or 0),
                    'latest_lineage_event': str(snapshot.latest_lineage_event or '').strip(),
                    'snapshot': snapshot,
                },
            )
            state['snapshot'] = snapshot
            if snapshot.skill_name:
                state['skill_name'] = snapshot.skill_name
            if snapshot.parent_skill_ids:
                state['parent_skill_ids'] = list(snapshot.parent_skill_ids)
            state['lineage_version'] = int(snapshot.lineage_version or 0)
            state['latest_lineage_event'] = str(snapshot.latest_lineage_event or '').strip()

    reports: list[RuntimeGovernanceBatchSkillReport] = []
    for skill_id, state in aggregated.items():
        snapshot = state.get('snapshot')
        if snapshot is not None:
            quality_score = snapshot.quality_score
            recent_actions = list(snapshot.recent_actions)
            recent_run_ids = list(snapshot.recent_run_ids)
            latest_action = snapshot.latest_recommended_action
            parent_skill_ids = list(snapshot.parent_skill_ids)
            lineage_version = int(snapshot.lineage_version or 0)
            latest_lineage_event = str(snapshot.latest_lineage_event or '').strip()
        else:
            quality_scores = list(state.get('quality_scores') or [])
            quality_score = round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0
            recent_actions = list(state.get('recent_actions') or [])[-5:]
            recent_run_ids = list(state.get('recent_run_ids') or [])[-5:]
            latest_action = str(state.get('latest_recommended_action') or 'no_change')
            parent_skill_ids = list(state.get('parent_skill_ids') or [])
            lineage_version = int(state.get('lineage_version') or 0)
            latest_lineage_event = str(state.get('latest_lineage_event') or '').strip()
        reports.append(
            RuntimeGovernanceBatchSkillReport(
                skill_id=skill_id,
                skill_name=str(state.get('skill_name') or '').strip(),
                skill_archetype=str(state.get('skill_archetype') or 'guidance').strip().lower() or 'guidance',
                quality_score=quality_score,
                recent_actions=recent_actions,
                recent_run_ids=recent_run_ids,
                latest_recommended_action=latest_action,
                operation_validation_status=str(state.get('operation_validation_status') or '').strip().lower(),
                coverage_gap_summary=list(state.get('coverage_gap_summary') or []),
                parent_skill_ids=parent_skill_ids,
                lineage_version=lineage_version,
                latest_lineage_event=latest_lineage_event,
            )
        )
    reports.sort(key=lambda item: (item.skill_name or item.skill_id, item.skill_id))
    return reports


def render_runtime_governance_batch_markdown(report: RuntimeGovernanceBatchReport) -> str:
    lines = [
        '# Runtime Governance Batch Report',
        '',
        f'- Runs processed: {report.runs_processed}',
        f'- Summary: {report.summary}',
        f'- Action counts: {report.action_counts}',
        f'- Approval counts: {report.approval_counts}',
        f'- Judge applied count: {report.judge_applied_count}',
        '',
        '## Runs',
    ]
    if not report.per_run:
        lines.append('- No run records were processed.')
    else:
        for bundle in report.per_run:
            followup = (
                bundle.runtime_hook.runtime_cycle.followup.action
                if bundle.runtime_hook.runtime_cycle is not None
                else 'n/a'
            )
            approval = (
                bundle.runtime_hook.approval_pack.approval_decision
                if bundle.runtime_hook.approval_pack is not None
                else 'n/a'
            )
            lines.append(f'- `{bundle.run_record.run_id}`: followup={followup}; approval={approval}')

    lines.extend(['', '## Skills'])
    if not report.per_skill:
        lines.append('- No skills matched the selected batch filter.')
    else:
        for item in report.per_skill:
            label = item.skill_name or item.skill_id
            lines.append(f'- `{label}` (`{item.skill_id}`)')
            lines.append(f'  - skill_archetype={item.skill_archetype}')
            lines.append(f'  - quality_score={item.quality_score:.4f}')
            lines.append(f'  - latest_action={item.latest_recommended_action}')
            if item.operation_validation_status:
                lines.append(f'  - operation_validation_status={item.operation_validation_status}')
            if item.coverage_gap_summary:
                lines.append(f'  - coverage_gap_summary={item.coverage_gap_summary}')
            if item.recent_actions:
                lines.append(f'  - recent_actions={item.recent_actions}')
            if item.recent_run_ids:
                lines.append(f'  - recent_run_ids={item.recent_run_ids}')
            if item.parent_skill_ids:
                lines.append(f'  - parent_skill_ids={item.parent_skill_ids}')
            if item.lineage_version:
                lines.append(f'  - lineage_version={item.lineage_version}')
            if item.latest_lineage_event:
                lines.append(f'  - latest_lineage_event={item.latest_lineage_event}')
    lines.extend(['', '## Semantic Summaries'])
    if not report.semantic_summaries:
        lines.append('- No runtime semantic summaries were emitted.')
    else:
        for item in report.semantic_summaries:
            lines.append(f'- `{item.run_id}`')
            lines.append(f'  - concise_summary={item.concise_summary}')
            lines.append(f'  - confidence={item.confidence:.2f}')
            lines.append(f'  - evidence_coverage={item.evidence_coverage:.2f}')
            if item.what_helped:
                lines.append(f'  - what_helped={item.what_helped}')
            if item.what_misled:
                lines.append(f'  - what_misled={item.what_misled}')
            if item.repeated_gaps:
                lines.append(f'  - repeated_gaps={item.repeated_gaps}')
    lines.extend(['', '## Create Candidates'])
    if not report.create_candidates:
        lines.append('- No runtime create candidates were emitted.')
    else:
        for candidate in report.create_candidates:
            lines.append(f'- `{candidate.candidate_id}`')
            lines.append(f'  - reason={candidate.reason}')
            if candidate.requirement_gaps:
                lines.append(f'  - requirement_gaps={candidate.requirement_gaps}')
            if candidate.source_run_ids:
                lines.append(f'  - source_run_ids={candidate.source_run_ids}')
    return '\n'.join(lines).strip()


def build_runtime_governance_batch_report(
    *,
    source_path: Path,
    policy: Optional[OpenSpaceObservationPolicy],
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    enable_llm_judge: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
    skill_id: Optional[str] = None,
) -> RuntimeGovernanceBatchReport:
    run_paths = _resolve_run_record_paths(source_path.resolve())
    run_records = [
        _load_run_record(run_path.read_text(encoding='utf-8'))
        for run_path in run_paths
    ]
    replay_cycles_by_run_id = {
        cycle.run_id: cycle
        for cycle in replay_runtime_runs(run_records)
    }

    bundles: list[RuntimeGovernanceBundle] = []
    for run_record in run_records:
        runtime_cycle_result = replay_cycles_by_run_id.get(run_record.run_id)
        runtime_hook_result = run_runtime_hook(
            run_record=run_record,
            policy=policy,
            runtime_cycle_result=runtime_cycle_result,
            baseline_path=baseline_path,
            scenario_names=scenario_names,
            enable_llm_judge=enable_llm_judge,
            llm_runner=llm_runner,
            model=model,
        )
        bundles.append(
            build_runtime_governance_bundle(
                run_record=run_record,
                policy=policy,
                baseline_path=baseline_path,
                scenario_names=scenario_names,
                enable_llm_judge=enable_llm_judge,
                llm_runner=llm_runner,
                model=model,
                runtime_hook_result=runtime_hook_result,
            )
        )

    if skill_id:
        bundles = [bundle for bundle in bundles if _bundle_targets_skill(bundle, skill_id)]

    action_counts: dict[str, int] = {}
    approval_counts: dict[str, int] = {}
    judge_applied_count = 0
    create_candidates = []
    semantic_summaries = []
    for bundle in bundles:
        followup_action = (
            bundle.runtime_hook.runtime_cycle.followup.action
            if bundle.runtime_hook.runtime_cycle is not None
            else 'n/a'
        )
        action_counts[followup_action] = action_counts.get(followup_action, 0) + 1
        approval = (
            bundle.runtime_hook.approval_pack.approval_decision
            if bundle.runtime_hook.approval_pack is not None
            else 'n/a'
        )
        approval_counts[approval] = approval_counts.get(approval, 0) + 1
        if bundle.runtime_hook.judge_pack is not None and bundle.runtime_hook.judge_pack.applied:
            judge_applied_count += 1
        create_candidates.extend(list(bundle.create_candidates or []))
        if bundle.semantic_summary is not None:
            semantic_summaries.append(bundle.semantic_summary)

    per_skill = _aggregate_batch_skill_reports(bundles)
    if skill_id:
        per_skill = [item for item in per_skill if item.skill_id == skill_id]

    report = RuntimeGovernanceBatchReport(
        runs_processed=len(bundles),
        per_run=bundles,
        per_skill=per_skill,
        create_candidates=create_candidates,
        semantic_summaries=semantic_summaries,
        action_counts=action_counts,
        approval_counts=approval_counts,
        judge_applied_count=judge_applied_count,
        summary=(
            f'Runtime governance batch complete: '
            f'runs={len(bundles)} skills={len(per_skill)} '
            f'create_candidates={len(create_candidates)} semantic_summaries={len(semantic_summaries)} actions={action_counts}'
        ),
    )
    report.markdown_summary = render_runtime_governance_batch_markdown(report)
    return report


def _candidate_key(candidate: RuntimeCreateCandidate) -> str:
    parts = list(candidate.requirement_gaps or [])
    seed = parts[0] if parts else candidate.candidate_id
    return _normalize_gap_key(seed) or candidate.candidate_id


def render_runtime_create_queue_markdown(report: RuntimeCreateQueueReport) -> str:
    lines = [
        '# Runtime Create Queue',
        '',
        f'- Runs processed: {report.runs_processed}',
        f'- Summary: {report.summary}',
        '',
        '## Entries',
    ]
    if not report.entries:
        lines.append('- No runtime create queue entries were emitted.')
        return '\n'.join(lines).strip()
    for entry in report.entries:
        lines.append(f'- `{entry.candidate_key}`')
        lines.append(f'  - recommended_status={entry.recommended_status}')
        lines.append(f'  - occurrence_count={entry.occurrence_count}')
        lines.append(f'  - latest_confidence={entry.latest_confidence:.2f}')
        if entry.requirement_gaps:
            lines.append(f'  - requirement_gaps={entry.requirement_gaps}')
        if entry.source_run_ids:
            lines.append(f'  - source_run_ids={entry.source_run_ids}')
        if entry.task_summaries:
            lines.append(f'  - task_summaries={entry.task_summaries}')
    return '\n'.join(lines).strip()


def build_runtime_create_queue_report(
    *,
    source_path: Path,
    policy: Optional[OpenSpaceObservationPolicy],
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    enable_llm_judge: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
) -> RuntimeCreateQueueReport:
    batch = build_runtime_governance_batch_report(
        source_path=source_path,
        policy=policy,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
        enable_llm_judge=enable_llm_judge,
        llm_runner=llm_runner,
        model=model,
    )
    run_summaries = {bundle.run_record.run_id: bundle.run_record.task_summary for bundle in list(batch.per_run or [])}
    grouped: dict[str, dict[str, Any]] = {}
    for candidate in list(batch.create_candidates or []):
        if str(candidate.candidate_kind or 'no_skill').strip().lower() != 'no_skill':
            continue
        gaps = [gap for gap in list(candidate.requirement_gaps or []) if not _is_simple_gap(gap)]
        if not gaps:
            continue
        key = _candidate_key(candidate)
        state = grouped.setdefault(
            key,
            {
                'task_summaries': [],
                'requirement_gaps': [],
                'source_run_ids': [],
                'occurrence_count': 0,
                'latest_confidence': 0.0,
            },
        )
        state['task_summaries'] = _ordered_unique(
            list(state['task_summaries']) + [run_summaries.get(run_id, candidate.task_summary) for run_id in list(candidate.source_run_ids or [])]
        )
        state['requirement_gaps'] = _ordered_unique(list(state['requirement_gaps']) + gaps)
        state['source_run_ids'] = _ordered_unique(list(state['source_run_ids']) + list(candidate.source_run_ids or []))
        state['occurrence_count'] = max(int(state['occurrence_count']), len(state['source_run_ids']))
        state['latest_confidence'] = max(float(state['latest_confidence']), float(candidate.confidence or 0.0))

    entries: list[RuntimeCreateQueueEntry] = []
    for key, state in grouped.items():
        entries.append(
            RuntimeCreateQueueEntry(
                candidate_key=key,
                task_summaries=list(state['task_summaries'])[:5],
                requirement_gaps=list(state['requirement_gaps'])[:5],
                source_run_ids=list(state['source_run_ids'])[-5:],
                occurrence_count=int(state['occurrence_count']),
                latest_confidence=float(state['latest_confidence']),
                recommended_status=_recommended_create_status(
                    occurrence_count=int(state['occurrence_count']),
                    latest_confidence=float(state['latest_confidence']),
                ),
            )
        )
    entries.sort(key=lambda item: (-item.occurrence_count, -item.latest_confidence, item.candidate_key))
    report = RuntimeCreateQueueReport(
        runs_processed=batch.runs_processed,
        entries=entries,
        summary=f'Runtime create queue complete: runs={batch.runs_processed} entries={len(entries)}',
    )
    report.markdown_summary = render_runtime_create_queue_markdown(report)
    return report


def render_runtime_create_review_markdown(pack: RuntimeCreateReviewPack) -> str:
    lines = [
        '# Runtime Create Review Pack',
        '',
        f'- Runs processed: {pack.runs_processed}',
        f'- Summary: {pack.summary}',
        '',
        '## Entries',
    ]
    if not pack.entries:
        lines.append('- No runtime create review entries were emitted.')
        return '\n'.join(lines).strip()
    for entry in pack.entries:
        lines.append(f'- `{entry.candidate_key}`')
        lines.append(f'  - recommended_next_action={entry.recommended_next_action}')
        lines.append(f'  - occurrence_count={entry.occurrence_count}')
        lines.append(f'  - suggested_title={entry.suggested_title}')
        lines.append(f'  - suggested_description={entry.suggested_description}')
        if entry.distilled_requirement_gaps:
            lines.append(f'  - distilled_requirement_gaps={entry.distilled_requirement_gaps}')
        if entry.representative_task_summaries:
            lines.append(f'  - representative_task_summaries={entry.representative_task_summaries}')
    return '\n'.join(lines).strip()


def build_runtime_create_review_pack(
    *,
    source_path: Path,
    policy: Optional[OpenSpaceObservationPolicy],
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    enable_llm_judge: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
) -> RuntimeCreateReviewPack:
    queue = build_runtime_create_queue_report(
        source_path=source_path,
        policy=policy,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
        enable_llm_judge=enable_llm_judge,
        llm_runner=llm_runner,
        model=model,
    )
    entries: list[RuntimeCreateReviewEntry] = []
    for item in list(queue.entries or []):
        suggested_title = _suggested_title(item.candidate_key)
        description_seed = (
            item.requirement_gaps[0]
            if item.requirement_gaps
            else (item.task_summaries[0] if item.task_summaries else f'Create a focused skill for {suggested_title}.')
        )
        entries.append(
            RuntimeCreateReviewEntry(
                candidate_key=item.candidate_key,
                candidate_brief=(
                    f'Repeated runtime gaps suggest a new skill candidate around {suggested_title}.'
                ),
                representative_task_summaries=list(item.task_summaries or [])[:3],
                distilled_requirement_gaps=list(item.requirement_gaps or [])[:3],
                suggested_title=suggested_title,
                suggested_description=description_seed,
                recommended_next_action=item.recommended_status,
                occurrence_count=item.occurrence_count,
                source_run_ids=list(item.source_run_ids or []),
            )
        )
    pack = RuntimeCreateReviewPack(
        runs_processed=queue.runs_processed,
        entries=entries,
        summary=(
            f'Runtime create review complete: runs={queue.runs_processed} entries={len(entries)}'
        ),
    )
    pack.markdown_summary = render_runtime_create_review_markdown(pack)
    return pack


def render_runtime_create_seed_proposal_markdown(pack: RuntimeCreateSeedProposalPack) -> str:
    lines = [
        '# Runtime Create Seed Proposal Pack',
        '',
        f'- Runs processed: {pack.runs_processed}',
        f'- Summary: {pack.summary}',
        '',
        '## Proposals',
    ]
    if not pack.proposals:
        lines.append('- No create seed proposals were emitted.')
        return '\n'.join(lines).strip()
    for item in pack.proposals:
        lines.append(f'- `{item.candidate_key}`')
        lines.append(f'  - recommended_decision={item.recommended_decision}')
        lines.append(f'  - suggested_title={item.suggested_title}')
        lines.append(f'  - suggested_description={item.suggested_description}')
        lines.append(f'  - preview_request.skill_name_hint={item.preview_request.skill_name_hint}')
        if item.distilled_requirement_gaps:
            lines.append(f'  - distilled_requirement_gaps={item.distilled_requirement_gaps}')
        if item.representative_task_summaries:
            lines.append(f'  - representative_task_summaries={item.representative_task_summaries}')
    return '\n'.join(lines).strip()


def build_runtime_create_seed_proposal_pack(
    *,
    source_path: Path,
    policy: Optional[OpenSpaceObservationPolicy],
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    enable_llm_judge: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
) -> RuntimeCreateSeedProposalPack:
    review_pack = build_runtime_create_review_pack(
        source_path=source_path,
        policy=policy,
        baseline_path=baseline_path,
        scenario_names=scenario_names,
        enable_llm_judge=enable_llm_judge,
        llm_runner=llm_runner,
        model=model,
    )
    proposals: list[RuntimeCreateSeedProposal] = []
    for entry in list(review_pack.entries or []):
        task = entry.suggested_description or (
            entry.representative_task_summaries[0]
            if entry.representative_task_summaries
            else f'Create a skill for {entry.suggested_title}.'
        )
        preview_request = SkillCreateRequestV6(
            task=task,
            skill_name_hint=_suggested_skill_name_hint(entry.candidate_key, entry.suggested_title),
            enable_online_skill_discovery=True,
            enable_eval_scaffold=True,
            enable_repair=True,
        )
        proposals.append(
            RuntimeCreateSeedProposal(
                candidate_key=entry.candidate_key,
                suggested_title=entry.suggested_title,
                suggested_description=entry.suggested_description,
                representative_task_summaries=list(entry.representative_task_summaries or []),
                distilled_requirement_gaps=list(entry.distilled_requirement_gaps or []),
                preview_request=preview_request,
                recommended_decision=entry.recommended_next_action,
                source_run_ids=list(entry.source_run_ids or []),
            )
        )
    pack = RuntimeCreateSeedProposalPack(
        runs_processed=review_pack.runs_processed,
        proposals=proposals,
        summary=(
            f'Runtime create seed proposals complete: runs={review_pack.runs_processed} proposals={len(proposals)}'
        ),
    )
    pack.markdown_summary = render_runtime_create_seed_proposal_markdown(pack)
    return pack


def render_runtime_ops_decision_pack_markdown(pack: RuntimeOpsDecisionPack) -> str:
    lines = [
        '# Runtime Ops Decision Pack',
        '',
        f'- Summary: {pack.summary}',
        f'- decisions_pending={pack.decisions_pending}',
        f'- approved_not_applied={pack.approved_not_applied}',
        f'- applied={pack.applied}',
        '',
        '## Create Seed Candidates',
    ]
    if not pack.create_seed_candidates:
        lines.append('- No create seed candidates are pending review.')
    else:
        for item in pack.create_seed_candidates:
            lines.append(f'- `{item.candidate_key}`')
            lines.append(f'  - recommended_decision={item.recommended_decision}')
            lines.append(f'  - approval_decision={item.approval_decision}')
            lines.append(f'  - decision_status={item.decision_status}')
            lines.append(f'  - suggested_title={item.suggested_title}')

    lines.extend(['', '## Prior Pilot Candidates'])
    if not pack.prior_pilot_candidates:
        lines.append('- No runtime prior pilot candidates are pending review.')
    else:
        for item in pack.prior_pilot_candidates:
            lines.append(f'- `{item.family}`')
            lines.append(f'  - recommended_status={item.recommended_status}')
            lines.append(f'  - approval_decision={item.approval_decision}')
            lines.append(f'  - decision_status={item.decision_status}')
            lines.append(f'  - allowed_families={item.allowed_families}')

    lines.extend(['', '## Source Promotion Candidates'])
    if not pack.source_promotion_candidates:
        lines.append('- No source promotion candidates are pending review.')
    else:
        for item in pack.source_promotion_candidates:
            lines.append(f'- `{item.repo_full_name}`')
            lines.append(f'  - verdict={item.verdict}')
            lines.append(f'  - approval_decision={item.approval_decision}')
            lines.append(f'  - decision_status={item.decision_status}')

    lines.extend(['', '## Recommended Next Actions'])
    if not pack.recommended_next_actions:
        lines.append('- No manual decisions are currently pending.')
    else:
        for action in pack.recommended_next_actions:
            lines.append(f'- {action}')
    return '\n'.join(lines).strip()


def build_runtime_ops_decision_pack(
    *,
    create_seed_pack: RuntimeCreateSeedProposalPack,
    prior_pilot_report: RuntimePriorPilotReport,
    source_curation_round: PublicSourceCurationRoundReport,
    verify_report: Optional[VerifyReport] = None,
    approval_state: Optional[OpsApprovalState] = None,
    artifact_root: Optional[Path] = None,
    collections_file: Optional[Path] = None,
) -> RuntimeOpsDecisionPack:
    from .public_source_curation import build_public_source_promotion_pack

    approval_state = approval_state or OpsApprovalState()
    create_seed_candidates = [
        apply_approval_to_create_seed_proposal(
            item,
            approval_state=approval_state,
            artifact_root=artifact_root,
        )
        for item in list(create_seed_pack.proposals or [])
        if item.recommended_decision in {'review', 'defer'}
    ]
    prior_pilot_candidates = [
        apply_approval_to_prior_pilot_profile(
            item,
            approval_state=approval_state,
            artifact_root=artifact_root,
        )
        for item in list(prior_pilot_report.profiles or [])
        if item.recommended_status in {'pilot', 'eligible'}
    ]
    source_promotion_candidates: list[PublicSourcePromotionPack] = []
    for repo_full_name in list(source_curation_round.promoted_repos or []):
        source_promotion_candidates.append(
            build_public_source_promotion_pack(
                round_report=source_curation_round,
                repo_full_name=repo_full_name,
                approval_state=approval_state,
                collections_file=collections_file,
            )
        )

    status_groups = summarize_decision_statuses(
        create_seed_candidates=create_seed_candidates,
        prior_pilot_candidates=prior_pilot_candidates,
        source_promotion_candidates=source_promotion_candidates,
    )
    decisions_pending = list(status_groups.get('pending') or [])
    approved_not_applied = list(status_groups.get('approved_not_applied') or [])
    applied = list(status_groups.get('applied') or [])
    recommended_next_actions: list[str] = []
    if verify_report is not None and verify_report.overall_status != 'pass':
        recommended_next_actions.append(
            f'Resolve verify status `{verify_report.overall_status}` before approving new pilots or promotions.'
        )
    for item in create_seed_candidates:
        if item.decision_status == 'pending':
            recommended_next_actions.append(
                f'Review create-seed proposal `{item.candidate_key}` before starting a new skill round.'
            )
        elif item.decision_status == 'approved_not_applied':
            recommended_next_actions.append(
                f'Materialize approved create-seed handoff `{item.candidate_key}` before launching the manual round.'
            )
    for item in prior_pilot_candidates:
        if item.decision_status == 'pending':
            recommended_next_actions.append(
                f'Review allowlisted runtime prior pilot for `{item.family}` before enabling opt-in rollout.'
            )
        elif item.decision_status == 'approved_not_applied':
            recommended_next_actions.append(
                f'Materialize the approved prior pilot profile for `{item.family}`; discovery defaults still stay off.'
            )
    for item in source_promotion_candidates:
        if item.decision_status == 'pending':
            recommended_next_actions.append(
                f'Review manual promotion evidence for `{item.repo_full_name}` before editing default seeded collections.'
            )
        elif item.decision_status == 'approved_not_applied':
            recommended_next_actions.append(
                f'Apply the approved source promotion for `{item.repo_full_name}` only after required regressions and smoke stay green.'
            )

    pack = RuntimeOpsDecisionPack(
        create_seed_candidates=create_seed_candidates,
        prior_pilot_candidates=prior_pilot_candidates,
        source_promotion_candidates=source_promotion_candidates,
        decisions_pending=decisions_pending,
        approved_not_applied=approved_not_applied,
        applied=applied,
        recommended_next_actions=recommended_next_actions,
        summary=(
            f'Runtime ops decision pack complete: '
            f'create_seed={len(create_seed_candidates)} '
            f'prior_pilot={len(prior_pilot_candidates)} '
            f'source_promotion={len(source_promotion_candidates)} '
            f'decisions_pending={len(decisions_pending)} '
            f'approved_not_applied={len(approved_not_applied)} '
            f'applied={len(applied)}'
        ),
    )
    pack.markdown_summary = render_runtime_ops_decision_pack_markdown(pack)
    return pack


def _eligible_prior_entries(
    *,
    catalog: list[SkillSourceCandidate],
    runtime_effectiveness_lookup: dict[str, dict[str, Any]],
    runtime_effectiveness_min_runs: int,
    runtime_effectiveness_allowed_families: Optional[list[str]] = None,
) -> list[RuntimePriorEligibleSkill]:
    seen: set[str] = set()
    entries: list[RuntimePriorEligibleSkill] = []
    for candidate in list(catalog or []):
        key = str(candidate.name or candidate.candidate_id or '').strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        payload = runtime_effectiveness_lookup.get(key) or runtime_effectiveness_lookup.get(str(candidate.candidate_id or '').strip().lower()) or {}
        run_count = int(payload.get('run_count', 0) or 0)
        quality_score = float(payload.get('quality_score', 0.0) or 0.0)
        eligible = (
            run_count >= max(int(runtime_effectiveness_min_runs or 0), 0)
            and _family_allowed(
                family=candidate.name,
                allowed_families=runtime_effectiveness_allowed_families,
            )
        )
        runtime_prior_delta = max(-0.06, min(0.06, (quality_score - 0.5) * 0.12)) if eligible else 0.0
        entries.append(
            RuntimePriorEligibleSkill(
                skill_id=str(payload.get('skill_id') or candidate.candidate_id or '').strip(),
                skill_name=candidate.name,
                quality_score=quality_score,
                run_count=run_count,
                runtime_prior_delta=runtime_prior_delta,
                eligible=eligible,
            )
        )
    entries.sort(key=lambda item: (-int(item.eligible), -item.run_count, -item.quality_score, item.skill_name))
    return entries


def render_runtime_prior_gate_markdown(report: RuntimePriorGateReport) -> str:
    lines = [
        '# Runtime Prior Gate Report',
        '',
        f'- Summary: {report.summary}',
        f'- Eligibility: {report.eligibility_summary}',
        f'- Ranking impact: {report.ranking_impact_summary}',
        '',
        '## Eligible Skills',
    ]
    if not report.eligible_skills:
        lines.append('- No runtime prior eligibility data was supplied.')
    else:
        for item in report.eligible_skills:
            lines.append(
                f'- `{item.skill_name or item.skill_id}`: eligible={item.eligible}; '
                f'run_count={item.run_count}; quality_score={item.quality_score:.2f}; '
                f'runtime_prior_delta={item.runtime_prior_delta:+.3f}'
            )
    lines.extend(['', '## Task Impacts'])
    if not report.task_impacts:
        lines.append('- No ranking task samples were evaluated.')
    else:
        for item in report.task_impacts:
            lines.append(f'- `{item.task}`')
            lines.append(f'  - baseline_top_candidate={item.baseline_top_candidate}')
            lines.append(f'  - prior_top_candidate={item.prior_top_candidate}')
            lines.append(f'  - changed_top_1={item.changed_top_1}')
            lines.append(f'  - generic_promoted={item.generic_promoted}')
            lines.append(f'  - prior_applied={item.prior_applied}')
    return '\n'.join(lines).strip()


def build_runtime_prior_gate_report(
    *,
    catalog: list[SkillSourceCandidate],
    runtime_effectiveness_lookup: dict[str, dict[str, Any]],
    task_samples: list[dict[str, Any]],
    runtime_effectiveness_min_runs: int = 5,
    runtime_effectiveness_allowed_families: Optional[list[str]] = None,
) -> RuntimePriorGateReport:
    eligible_skills = _eligible_prior_entries(
        catalog=catalog,
        runtime_effectiveness_lookup=runtime_effectiveness_lookup,
        runtime_effectiveness_min_runs=runtime_effectiveness_min_runs,
        runtime_effectiveness_allowed_families=runtime_effectiveness_allowed_families,
    )
    task_impacts: list[RuntimePriorTaskImpact] = []
    top_1_changed_count = 0
    generic_promoted_count = 0
    prior_applied_count = 0
    for item in list(task_samples or []):
        task = str(item.get('task') or '').strip()
        repo_context = item.get('repo_context') or {'selected_files': []}
        if not task:
            continue
        baseline = discover_online_skills(
            task=task,
            repo_context=repo_context,
            catalog=catalog,
            limit=int(item.get('limit', 5) or 5),
        )
        adjusted = discover_online_skills(
            task=task,
            repo_context=repo_context,
            catalog=catalog,
            limit=int(item.get('limit', 5) or 5),
            runtime_effectiveness_lookup=runtime_effectiveness_lookup,
            enable_runtime_effectiveness_prior=True,
            runtime_effectiveness_min_runs=runtime_effectiveness_min_runs,
            runtime_effectiveness_allowed_families=runtime_effectiveness_allowed_families,
        )
        baseline_top = baseline[0] if baseline else None
        adjusted_top = adjusted[0] if adjusted else None
        prior_applied = any(abs(float(getattr(candidate, 'runtime_prior_delta', 0.0) or 0.0)) > 0.0 for candidate in list(adjusted or []))
        changed_top_1 = (
            baseline_top is not None
            and adjusted_top is not None
            and baseline_top.name != adjusted_top.name
        )
        generic_promoted = bool(adjusted_top is not None and _is_generic_candidate(adjusted_top) and changed_top_1)
        if changed_top_1:
            top_1_changed_count += 1
        if generic_promoted:
            generic_promoted_count += 1
        if prior_applied:
            prior_applied_count += 1
        task_impacts.append(
            RuntimePriorTaskImpact(
                task=task,
                baseline_top_candidate=baseline_top.name if baseline_top is not None else '',
                prior_top_candidate=adjusted_top.name if adjusted_top is not None else '',
                changed_top_1=changed_top_1,
                generic_promoted=generic_promoted,
                prior_applied=prior_applied,
                summary=(
                    f'baseline={baseline_top.name if baseline_top is not None else "n/a"} '
                    f'prior={adjusted_top.name if adjusted_top is not None else "n/a"} '
                    f'changed_top_1={changed_top_1}'
                ),
            )
        )
    eligibility_summary = {
        'skills_considered': len(eligible_skills),
        'eligible_count': sum(1 for item in eligible_skills if item.eligible),
        'positive_delta_count': sum(1 for item in eligible_skills if item.runtime_prior_delta > 0.0),
        'negative_delta_count': sum(1 for item in eligible_skills if item.runtime_prior_delta < 0.0),
    }
    ranking_impact_summary = {
        'tasks_evaluated': len(task_impacts),
        'prior_applied_count': prior_applied_count,
        'top_1_changed_count': top_1_changed_count,
        'generic_promoted_count': generic_promoted_count,
    }
    report = RuntimePriorGateReport(
        eligible_skills=eligible_skills,
        task_impacts=task_impacts,
        eligibility_summary=eligibility_summary,
        ranking_impact_summary=ranking_impact_summary,
        summary=(
            f'Runtime prior gate complete: eligible={eligibility_summary["eligible_count"]} '
            f'tasks={ranking_impact_summary["tasks_evaluated"]} '
            f'top_1_changed={ranking_impact_summary["top_1_changed_count"]}'
        ),
    )
    report.markdown_summary = render_runtime_prior_gate_markdown(report)
    return report


def render_runtime_prior_rollout_markdown(report: RuntimePriorRolloutReport) -> str:
    lines = [
        '# Runtime Prior Rollout Report',
        '',
        f'- Summary: {report.summary}',
        f'- Recommended scope: {report.recommended_scope}',
        '',
        '## Families',
    ]
    if not report.families:
        lines.append('- No runtime prior rollout families were evaluated.')
        return '\n'.join(lines).strip()
    for item in report.families:
        lines.append(f'- `{item.family}`')
        lines.append(f'  - eligible={item.eligible}')
        lines.append(f'  - sample_count={item.sample_count}')
        lines.append(f'  - quality_band={item.quality_band}')
        lines.append(f'  - generic_promotion_risk={item.generic_promotion_risk}')
        lines.append(f'  - recommended_rollout_status={item.recommended_rollout_status}')
        lines.append(f'  - recommended_scope={item.recommended_scope}')
    return '\n'.join(lines).strip()


def build_runtime_prior_rollout_report(
    *,
    gate_report: RuntimePriorGateReport,
    runtime_effectiveness_lookup: dict[str, dict[str, Any]],
    rollout_min_runs: int = 5,
) -> RuntimePriorRolloutReport:
    generic_risk = int((gate_report.ranking_impact_summary or {}).get('generic_promoted_count', 0) or 0)
    families: list[RuntimePriorRolloutFamilyReport] = []
    for item in list(gate_report.eligible_skills or []):
        family = str(item.skill_name or item.skill_id or '').strip()
        sample_count = int(item.run_count or 0)
        quality_band = _quality_band(item.quality_score)
        if not item.eligible or sample_count < max(int(rollout_min_runs or 0), 0):
            rollout_status = 'hold'
        elif generic_risk > 0:
            rollout_status = 'hold'
        elif sample_count >= max(int(rollout_min_runs or 0), 8) and quality_band == 'high' and float(item.runtime_prior_delta or 0.0) > 0.0:
            rollout_status = 'eligible'
        else:
            rollout_status = 'pilot'
        recommended_scope = [family] if rollout_status in {'pilot', 'eligible'} else []
        families.append(
            RuntimePriorRolloutFamilyReport(
                family=family,
                eligible=bool(item.eligible),
                sample_count=sample_count,
                quality_band=quality_band,
                generic_promotion_risk=generic_risk,
                recommended_rollout_status=rollout_status,
                recommended_scope=recommended_scope,
                runtime_prior_delta=float(item.runtime_prior_delta or 0.0),
            )
        )
    families.sort(key=lambda item: (item.recommended_rollout_status != 'eligible', item.recommended_rollout_status != 'pilot', item.family))
    recommended_scope = _ordered_unique(
        family
        for item in families
        for family in list(item.recommended_scope or [])
    )
    report = RuntimePriorRolloutReport(
        families=families,
        recommended_scope=recommended_scope,
        summary=(
            f'Runtime prior rollout complete: families={len(families)} '
            f'pilot_or_eligible={len(recommended_scope)} generic_risk={generic_risk}'
        ),
    )
    report.markdown_summary = render_runtime_prior_rollout_markdown(report)
    return report


def render_runtime_prior_pilot_markdown(report: RuntimePriorPilotReport) -> str:
    lines = [
        '# Runtime Prior Pilot Report',
        '',
        f'- Summary: {report.summary}',
        f'- Allowed families: {report.allowed_families}',
        '',
        '## Profiles',
    ]
    if not report.profiles:
        lines.append('- No runtime prior pilot profiles were emitted.')
        return '\n'.join(lines).strip()
    for item in report.profiles:
        lines.append(f'- `{item.family}`')
        lines.append(f'  - recommended_status={item.recommended_status}')
        lines.append(f'  - sample_count={item.sample_count}')
        lines.append(f'  - quality_band={item.quality_band}')
        lines.append(f'  - generic_promotion_risk={item.generic_promotion_risk}')
        lines.append(f'  - allowed_families={item.allowed_families}')
    return '\n'.join(lines).strip()


def build_runtime_prior_pilot_report(
    *,
    rollout_report: RuntimePriorRolloutReport,
    runtime_effectiveness_min_runs: int = 5,
) -> RuntimePriorPilotReport:
    allowed_families = _ordered_unique(
        family
        for item in list(rollout_report.families or [])
        if item.recommended_rollout_status in {'pilot', 'eligible'}
        for family in [item.family]
    )
    profiles: list[RuntimePriorPilotProfile] = []
    for item in list(rollout_report.families or []):
        request_overrides_preview = {
            'enable_runtime_effectiveness_prior': item.recommended_rollout_status in {'pilot', 'eligible'},
            'runtime_effectiveness_min_runs': int(runtime_effectiveness_min_runs or 5),
            'runtime_effectiveness_allowed_families': (
                list(allowed_families)
                if item.recommended_rollout_status in {'pilot', 'eligible'}
                else []
            ),
        }
        profiles.append(
            RuntimePriorPilotProfile(
                family=item.family,
                recommended_status=item.recommended_rollout_status,
                allowed_families=list(request_overrides_preview['runtime_effectiveness_allowed_families']),
                request_overrides_preview=request_overrides_preview,
                generic_promotion_risk=item.generic_promotion_risk,
                sample_count=item.sample_count,
                quality_band=item.quality_band,
            )
        )
    report = RuntimePriorPilotReport(
        profiles=profiles,
        allowed_families=allowed_families,
        summary=(
            f'Runtime prior pilot report complete: profiles={len(profiles)} '
            f'allowed_families={len(allowed_families)}'
        ),
    )
    report.markdown_summary = render_runtime_prior_pilot_markdown(report)
    return report


def render_runtime_prior_pilot_exercise_markdown(report: RuntimePriorPilotExerciseReport) -> str:
    lines = [
        '# Runtime Prior Pilot Exercise',
        '',
        f'- Family: {report.family}',
        f'- Verdict: {report.verdict}',
        f'- approval_decision={report.approval_decision}',
        f'- decision_status={report.decision_status}',
        f'- Summary: {report.summary}',
        f'- scenarios_run={report.scenarios_run}',
        f'- top_1_changes={report.top_1_changes}',
        f'- generic_promotion_risk={report.generic_promotion_risk}',
        '',
        '## Request Overrides',
    ]
    if not report.request_overrides:
        lines.append('- No request overrides were produced.')
    else:
        lines.append(f'- {report.request_overrides}')
    return '\n'.join(lines).strip()


def build_runtime_prior_pilot_exercise_report(
    *,
    pilot_report: RuntimePriorPilotReport,
    family: str = 'hf-trainer',
    fixture_root: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    approval_state: Optional[OpsApprovalState] = None,
    artifact_root: Optional[Path] = None,
) -> RuntimePriorPilotExerciseReport:
    from .simulation import build_simulation_suite_report

    target_family = str(family or '').strip()
    selected_profile = next(
        (item for item in list(pilot_report.profiles or []) if item.family == target_family),
        None,
    )
    selected_scenarios = list(scenario_names or ['hf_trainer_pilot_ready', 'allowlisted_family_only'])
    simulation_report = build_simulation_suite_report(
        mode='prior-gate',
        fixture_root=fixture_root,
        scenario_names=selected_scenarios,
    )
    top_1_changes = 0
    generic_promotion_risk = 0
    scenarios_run: list[str] = []
    for item in list(simulation_report.scenario_results or []):
        scenarios_run.append(item.scenario_id)
        projection = dict(item.actual_projection or {})
        ranking_impact = dict(projection.get('ranking_impact_summary') or {})
        top_1_changes += int(ranking_impact.get('top_1_changed_count', 0) or 0)
        generic_promotion_risk += int(ranking_impact.get('generic_promoted_count', 0) or 0)

    verdict = 'hold'
    if (
        selected_profile is not None
        and selected_profile.recommended_status in {'pilot', 'eligible'}
        and simulation_report.drifted_count == 0
        and simulation_report.invalid_fixture_count == 0
        and generic_promotion_risk == 0
    ):
        verdict = 'ready_for_manual_pilot'

    report = RuntimePriorPilotExerciseReport(
        family=target_family,
        request_overrides=dict(selected_profile.request_overrides_preview if selected_profile is not None else {}),
        scenarios_run=scenarios_run,
        top_1_changes=top_1_changes,
        generic_promotion_risk=generic_promotion_risk,
        matched_count=simulation_report.matched_count,
        drifted_count=simulation_report.drifted_count,
        invalid_fixture_count=simulation_report.invalid_fixture_count,
        verdict=verdict,
        summary=(
            f'Runtime prior pilot exercise complete: '
            f'family={target_family} matched={simulation_report.matched_count} '
            f'drifted={simulation_report.drifted_count} invalid_fixture={simulation_report.invalid_fixture_count} '
            f'generic_risk={generic_promotion_risk} verdict={verdict}'
        ),
    )
    if selected_profile is not None:
        approved_profile = apply_approval_to_prior_pilot_profile(
            selected_profile,
            approval_state=approval_state or OpsApprovalState(),
            artifact_root=artifact_root,
        )
        report.approval_decision = approved_profile.approval_decision
        report.decision_status = approved_profile.decision_status
        report.profile_artifact_path = approved_profile.profile_artifact_path
    report.markdown_summary = render_runtime_prior_pilot_exercise_markdown(report)
    return report
