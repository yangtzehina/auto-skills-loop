from __future__ import annotations

import json
from typing import Any

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.operation import OperationContract
from ..models.operation_coverage import OperationCoverageGap, OperationCoverageReport


OPERATION_COVERAGE_PATH = 'evals/operation_coverage.json'
_JSON_MARKERS = ('--json', '`--json`', 'json.dumps', 'application/json', 'structured json', 'json result payload')
_SESSION_MARKERS = ('session', 'login', 'connect', 'repl', 'interactive')
_CONFIRMATION_MARKERS = ('confirm', 'confirmation', '--force', '-y', 'dry-run')


def _find_file_content(artifacts: Artifacts | None, path: str) -> str:
    if artifacts is None:
        return ''
    for file in list(getattr(artifacts, 'files', []) or []):
        if file.path == path:
            return str(file.content or '')
    return ''


def _operation_names(contract: OperationContract | None) -> list[tuple[str, str, str]]:
    if contract is None:
        return []
    return [
        (str(group.name or '').strip(), str(operation.name or '').strip(), str(operation.summary or '').strip())
        for group in list(contract.operations or [])
        for operation in list(group.operations or [])
        if str(operation.name or '').strip()
    ]


def _helper_paths(artifacts: Artifacts | None) -> list[str]:
    if artifacts is None:
        return []
    return [file.path for file in list(getattr(artifacts, 'files', []) or []) if file.path.startswith('scripts/')]


def _all_surface_text(artifacts: Artifacts | None) -> str:
    if artifacts is None:
        return ''
    chunks: list[str] = []
    for file in list(getattr(artifacts, 'files', []) or []):
        if file.path == 'SKILL.md' or file.path.startswith('scripts/'):
            chunks.append(str(file.content or ''))
    return '\n'.join(chunks).lower()


def _covered_operations(contract: OperationContract | None, artifacts: Artifacts | None) -> tuple[list[str], list[tuple[str, str]]]:
    surface = _all_surface_text(artifacts)
    covered: list[str] = []
    missing: list[tuple[str, str]] = []
    for group_name, operation_name, summary in _operation_names(contract):
        needles = [operation_name.lower()]
        if summary:
            needles.append(summary.lower())
        if any(needle and needle in surface for needle in needles):
            covered.append(operation_name)
        else:
            missing.append((group_name, operation_name))
    return covered, missing


def _security_alignment(diagnostics: Any) -> str:
    if diagnostics is None:
        return 'unknown'
    security_audit = getattr(diagnostics, 'security_audit', None)
    rating = str(getattr(security_audit, 'rating', 'LOW') or 'LOW').upper()
    if rating in {'HIGH', 'REJECT'}:
        return 'blocked'
    if rating == 'MEDIUM':
        return 'caution'
    return 'aligned'


def build_operation_coverage_report(
    *,
    skill_plan: Any,
    artifacts: Artifacts | None = None,
    diagnostics: Any = None,
    runtime_gap_hints: list[dict[str, Any]] | None = None,
) -> OperationCoverageReport:
    skill_archetype = str(getattr(skill_plan, 'skill_archetype', 'guidance') or 'guidance').strip().lower()
    if skill_archetype != 'operation_backed':
        return OperationCoverageReport(skill_archetype=skill_archetype)

    contract = getattr(skill_plan, 'operation_contract', None)
    if contract is not None and not isinstance(contract, OperationContract):
        contract = OperationContract.model_validate(contract)

    operation_pairs = _operation_names(contract)
    operation_count = len(operation_pairs)
    if artifacts is None:
        covered_operations = [operation_name for _, operation_name, _ in operation_pairs]
        missing_operation_pairs: list[tuple[str, str]] = []
    else:
        covered_operations, missing_operation_pairs = _covered_operations(contract, artifacts)
    missing_operations = [operation_name for _, operation_name in missing_operation_pairs]
    gap_summary: list[OperationCoverageGap] = []

    helper_paths = _helper_paths(artifacts)
    surface = _all_surface_text(artifacts)

    if contract is None:
        gap_summary.append(
            OperationCoverageGap(
                gap_type='contract_surface_drift',
                reason='operation-backed skill is missing an operation contract',
                recommended_action='hold',
            )
        )
    else:
        if missing_operation_pairs:
            group_to_operation_names = {
                str(group.name or '').strip(): [
                    str(operation.name or '').strip()
                    for operation in list(group.operations or [])
                    if str(operation.name or '').strip()
                ]
                for group in list(contract.operations or [])
                if str(group.name or '').strip()
            }
            missing_groups = {
                group_name
                for group_name, operation_names in group_to_operation_names.items()
                if operation_names and all(
                    any(existing_group == group_name and existing_operation == operation_name for existing_group, existing_operation in missing_operation_pairs)
                    for operation_name in operation_names
                )
            }
            for group_name, operation_name in missing_operation_pairs:
                gap_summary.append(
                    OperationCoverageGap(
                        gap_type='missing_operation_group' if group_name in missing_groups and len(missing_operation_pairs) > 1 else 'missing_operation',
                        operation_group=group_name,
                        operation_name=operation_name,
                        reason=f'Generated skill surface does not yet cover `{operation_name}` from group `{group_name}`.',
                        recommended_action='derive_child',
                    )
                )

        if artifacts is not None and contract.supports_json and not any(marker in surface for marker in _JSON_MARKERS):
            gap_summary.append(
                OperationCoverageGap(
                    gap_type='missing_json_surface',
                    reason='Contract expects a JSON surface but the generated skill surface does not document or expose one.',
                    recommended_action='patch_current',
                )
            )

        if (
            artifacts is not None
            and str(contract.session_model or 'stateless').strip().lower() == 'session_required'
            and not any(marker in surface for marker in _SESSION_MARKERS)
        ):
            gap_summary.append(
                OperationCoverageGap(
                    gap_type='missing_session_model',
                    reason='Contract requires a session-aware lifecycle but the generated skill surface does not explain it.',
                    recommended_action='patch_current',
                )
            )

        if artifacts is not None and str(contract.mutability or 'read_only').strip().lower() in {'mixed', 'mutating'}:
            weak_operations = [
                operation.name
                for group in list(contract.operations or [])
                for operation in list(group.operations or [])
                if (
                    not list(operation.preconditions or [])
                    or not list(operation.side_effects or [])
                    or (
                        bool(getattr(contract.safety_profile, 'confirmation_required', False))
                        and not any(marker in surface for marker in _CONFIRMATION_MARKERS)
                    )
                )
            ]
            if weak_operations:
                gap_summary.append(
                    OperationCoverageGap(
                        gap_type='missing_mutating_safeguards',
                        operation_name=weak_operations[0],
                        reason='Mutating operation coverage is missing preconditions, side-effect notes, or confirmation semantics.',
                        recommended_action='patch_current',
                    )
                )

    for item in list(runtime_gap_hints or []):
        gap = item if isinstance(item, OperationCoverageGap) else OperationCoverageGap.model_validate(item)
        gap_summary.append(gap)

    validation_status = 'validated'
    validation = getattr(diagnostics, 'validation', None)
    repairable_issues = list(getattr(validation, 'repairable_issue_types', []) or [])
    operation_issues = [item for item in repairable_issues if item.startswith('operation_')]
    if contract is None:
        validation_status = 'missing'
    elif operation_issues or gap_summary:
        validation_status = 'needs_attention'

    security_alignment = _security_alignment(diagnostics)
    recommended_followup = 'no_change'
    if security_alignment == 'blocked':
        recommended_followup = 'hold'
    elif any(item.recommended_action == 'hold' for item in gap_summary):
        recommended_followup = 'hold'
    elif any(item.recommended_action == 'derive_child' for item in gap_summary):
        recommended_followup = 'derive_child'
    elif any(item.recommended_action == 'patch_current' for item in gap_summary):
        recommended_followup = 'patch_current'

    if (
        artifacts is not None
        and not helper_paths
        and skill_archetype == 'operation_backed'
        and str(getattr(contract, 'backend_kind', 'python_backend') or 'python_backend') in {'python_backend', 'api_client', 'shell_wrapper'}
    ):
        gap_summary.append(
            OperationCoverageGap(
                gap_type='contract_surface_drift',
                reason='Operation-backed helper surface is missing for a non-native backend.',
                recommended_action='patch_current',
            )
        )
        if recommended_followup == 'no_change':
            recommended_followup = 'patch_current'

    return OperationCoverageReport(
        skill_archetype=skill_archetype,
        operation_count=operation_count,
        covered_operations=covered_operations,
        missing_operations=missing_operations,
        gap_summary=gap_summary,
        validation_status=validation_status,
        security_alignment=security_alignment,
        recommended_followup=recommended_followup,
    )


def operation_coverage_artifact(
    *,
    skill_name: str,
    report: OperationCoverageReport,
) -> ArtifactFile:
    payload = report.model_dump(mode='json')
    payload['skill_name'] = skill_name
    return ArtifactFile(
        path=OPERATION_COVERAGE_PATH,
        content=json.dumps(payload, indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['operation_contract', 'operation_coverage'],
        status='new',
    )


def load_operation_coverage_report(artifacts: Artifacts | None) -> OperationCoverageReport | None:
    content = _find_file_content(artifacts, OPERATION_COVERAGE_PATH)
    if not content:
        return None
    try:
        payload = json.loads(content)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    payload.pop('skill_name', None)
    try:
        return OperationCoverageReport.model_validate(payload)
    except Exception:
        return None
