from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..models.runtime import SkillRunRecord
from ..models.runtime_replay import (
    RuntimeReplayBaseline,
    RuntimeReplayGateResult,
    RuntimeReplayGateScenarioResult,
    RuntimeReplayReport,
    RuntimeReplayScenarioBaseline,
    RuntimeReplayScenarioReport,
)
from .runtime_cycle import replay_runtime_runs


DEFAULT_RUNTIME_REPLAY_FIXTURES = (
    Path(__file__).resolve().parents[3] / 'tests' / 'fixtures' / 'runtime_replay'
)
DEFAULT_RUNTIME_REPLAY_BASELINE = DEFAULT_RUNTIME_REPLAY_FIXTURES / 'baseline_report.json'


def _normalize_scenario_names(
    fixtures_root: Path,
    scenario_names: Optional[list[str]] = None,
) -> list[str]:
    if scenario_names:
        normalized: list[str] = []
        for name in list(scenario_names or []):
            text = str(name or '').strip()
            if not text:
                continue
            scenario_root = fixtures_root / text
            if not scenario_root.exists() or not scenario_root.is_dir():
                raise ValueError(f'Unknown runtime replay scenario: {text}')
            normalized.append(text)
        if not normalized:
            raise ValueError('No valid runtime replay scenarios were provided')
        return normalized

    scenario_dirs = sorted(
        path.name
        for path in fixtures_root.iterdir()
        if path.is_dir()
    )
    if not scenario_dirs:
        raise ValueError(f'No runtime replay scenarios found under: {fixtures_root}')
    return scenario_dirs


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ValueError(f'Missing manifest file: {path}')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid manifest JSON: {path}') from exc
    if not isinstance(payload, dict):
        raise ValueError(f'Runtime replay manifest must be a JSON object: {path}')
    return payload


def _load_run_records(scenario_root: Path, manifest: dict[str, Any]) -> list[SkillRunRecord]:
    run_records: list[SkillRunRecord] = []
    for relative_path in list(manifest.get('run_files') or []):
        run_path = scenario_root / str(relative_path)
        if not run_path.exists() or not run_path.is_file():
            raise ValueError(f'Missing runtime replay run file: {run_path}')
        try:
            payload = json.loads(run_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise ValueError(f'Invalid runtime replay run JSON: {run_path}') from exc
        run_records.append(SkillRunRecord.model_validate(payload))
    if not run_records:
        raise ValueError(f'Runtime replay scenario has no run files: {scenario_root}')
    return run_records


def build_runtime_replay_scenario_report(scenario_root: Path) -> RuntimeReplayScenarioReport:
    manifest = _load_manifest(scenario_root / 'manifest.json')
    run_records = _load_run_records(scenario_root, manifest)
    results = replay_runtime_runs(run_records)
    if not results:
        raise ValueError(f'Runtime replay scenario produced no results: {scenario_root}')

    actual_actions = [
        str(result.analysis.skills_analyzed[0].get('recommended_action') or 'no_change')
        if result.analysis.skills_analyzed
        else 'no_change'
        for result in results
    ]
    final_result = results[-1]
    final_item = final_result.analysis.skills_analyzed[0] if final_result.analysis.skills_analyzed else {}
    actual_followup_action = final_result.followup.action
    actual_quality_score = round(float(final_item.get('quality_score', 0.0) or 0.0), 4)
    actual_usage_stats = dict(final_item.get('usage_stats') or {})
    actual_recent_run_ids = list(final_item.get('recent_run_ids') or [])
    actual_requirement_gaps = (
        list(final_result.followup.selected_plan.requirement_gaps)
        if final_result.followup.selected_plan is not None
        else []
    )

    expected_actions = list(manifest.get('expected_actions') or [])
    expected_followup_action = str(manifest.get('expected_final_followup_action') or '')
    expected_quality_score = round(float(manifest.get('expected_final_quality_score', 0.0) or 0.0), 4)
    expected_usage_stats = dict(manifest.get('expected_final_usage_stats') or {})
    expected_recent_run_ids = list(manifest.get('expected_final_recent_run_ids') or [])
    expected_requirement_gaps = list(manifest.get('expected_final_requirement_gaps') or [])

    mismatches: list[str] = []
    if actual_actions != expected_actions:
        mismatches.append(f'expected_actions={expected_actions} actual_actions={actual_actions}')
    if actual_followup_action != expected_followup_action:
        mismatches.append(
            f'expected_final_followup_action={expected_followup_action} actual_final_followup_action={actual_followup_action}'
        )
    if actual_quality_score != expected_quality_score:
        mismatches.append(
            f'expected_final_quality_score={expected_quality_score} actual_final_quality_score={actual_quality_score}'
        )
    if actual_usage_stats != expected_usage_stats:
        mismatches.append(
            f'expected_final_usage_stats={expected_usage_stats} actual_final_usage_stats={actual_usage_stats}'
        )
    if actual_recent_run_ids != expected_recent_run_ids:
        mismatches.append(
            f'expected_final_recent_run_ids={expected_recent_run_ids} actual_final_recent_run_ids={actual_recent_run_ids}'
        )
    if actual_requirement_gaps != expected_requirement_gaps:
        mismatches.append(
            f'expected_final_requirement_gaps={expected_requirement_gaps} actual_final_requirement_gaps={actual_requirement_gaps}'
        )

    return RuntimeReplayScenarioReport(
        scenario_id=str(manifest.get('scenario_id') or scenario_root.name),
        description=str(manifest.get('description') or '').strip(),
        run_count=len(run_records),
        expected_actions=expected_actions,
        actual_actions=actual_actions,
        expected_final_followup_action=expected_followup_action,
        actual_final_followup_action=actual_followup_action,
        expected_final_quality_score=expected_quality_score,
        actual_final_quality_score=actual_quality_score,
        expected_final_usage_stats=expected_usage_stats,
        actual_final_usage_stats=actual_usage_stats,
        expected_final_recent_run_ids=expected_recent_run_ids,
        actual_final_recent_run_ids=actual_recent_run_ids,
        expected_final_requirement_gaps=expected_requirement_gaps,
        actual_final_requirement_gaps=actual_requirement_gaps,
        passed=not mismatches,
        mismatches=mismatches,
    )


def build_runtime_replay_report(
    *,
    fixtures_root: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> RuntimeReplayReport:
    root = Path(fixtures_root or DEFAULT_RUNTIME_REPLAY_FIXTURES).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f'Runtime replay fixtures root not found: {root}')

    reports = [
        build_runtime_replay_scenario_report(root / scenario_name)
        for scenario_name in _normalize_scenario_names(root, scenario_names)
    ]
    passed_count = sum(1 for report in reports if report.passed)
    failed_count = len(reports) - passed_count
    return RuntimeReplayReport(
        fixture_root=str(root),
        scenario_reports=reports,
        passed=failed_count == 0,
        summary=(
            f'Runtime replay report complete: scenarios={len(reports)} '
            f'passed={passed_count} failed={failed_count}'
        ),
    )


def scenario_report_to_baseline(report: RuntimeReplayScenarioReport) -> RuntimeReplayScenarioBaseline:
    return RuntimeReplayScenarioBaseline(
        scenario_id=report.scenario_id,
        actual_actions=list(report.actual_actions),
        actual_final_followup_action=report.actual_final_followup_action,
        actual_final_quality_score=round(float(report.actual_final_quality_score or 0.0), 4),
        actual_final_usage_stats=dict(report.actual_final_usage_stats),
        actual_final_recent_run_ids=list(report.actual_final_recent_run_ids),
        actual_final_requirement_gaps=list(report.actual_final_requirement_gaps),
    )


def build_runtime_replay_baseline(
    *,
    fixtures_root: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> RuntimeReplayBaseline:
    report = build_runtime_replay_report(
        fixtures_root=fixtures_root,
        scenario_names=scenario_names,
    )
    baselines = [
        scenario_report_to_baseline(item)
        for item in list(report.scenario_reports)
    ]
    return RuntimeReplayBaseline(
        scenario_baselines=baselines,
        summary=f'Runtime replay baseline complete: scenarios={len(baselines)}',
    )


def load_runtime_replay_baseline(path: Path) -> RuntimeReplayBaseline:
    baseline_path = Path(path).expanduser().resolve()
    if not baseline_path.exists() or not baseline_path.is_file():
        raise ValueError(f'Runtime replay baseline not found: {baseline_path}')
    try:
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid runtime replay baseline JSON: {baseline_path}') from exc
    return RuntimeReplayBaseline.model_validate(payload)


def write_runtime_replay_baseline(
    baseline_path: Path,
    *,
    fixtures_root: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> RuntimeReplayBaseline:
    baseline = build_runtime_replay_baseline(
        fixtures_root=fixtures_root,
        scenario_names=scenario_names,
    )
    target = Path(baseline_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(baseline.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )
    return baseline


def _compare_baseline(
    current: RuntimeReplayScenarioReport,
    baseline: RuntimeReplayScenarioBaseline,
) -> list[str]:
    drifts: list[str] = []
    if list(current.actual_actions) != list(baseline.actual_actions):
        drifts.append(
            f'actual_actions drifted: baseline={baseline.actual_actions} current={current.actual_actions}'
        )
    if current.actual_final_followup_action != baseline.actual_final_followup_action:
        drifts.append(
            'actual_final_followup_action drifted: '
            f'baseline={baseline.actual_final_followup_action} '
            f'current={current.actual_final_followup_action}'
        )
    if round(float(current.actual_final_quality_score or 0.0), 4) != round(float(baseline.actual_final_quality_score or 0.0), 4):
        drifts.append(
            'actual_final_quality_score drifted: '
            f'baseline={baseline.actual_final_quality_score} '
            f'current={current.actual_final_quality_score}'
        )
    if dict(current.actual_final_usage_stats) != dict(baseline.actual_final_usage_stats):
        drifts.append(
            'actual_final_usage_stats drifted: '
            f'baseline={baseline.actual_final_usage_stats} '
            f'current={current.actual_final_usage_stats}'
        )
    if list(current.actual_final_recent_run_ids) != list(baseline.actual_final_recent_run_ids):
        drifts.append(
            'actual_final_recent_run_ids drifted: '
            f'baseline={baseline.actual_final_recent_run_ids} '
            f'current={current.actual_final_recent_run_ids}'
        )
    if list(current.actual_final_requirement_gaps) != list(baseline.actual_final_requirement_gaps):
        drifts.append(
            'actual_final_requirement_gaps drifted: '
            f'baseline={baseline.actual_final_requirement_gaps} '
            f'current={current.actual_final_requirement_gaps}'
        )
    return drifts


def build_runtime_replay_gate_result(
    *,
    fixtures_root: Optional[Path] = None,
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
) -> RuntimeReplayGateResult:
    report = build_runtime_replay_report(
        fixtures_root=fixtures_root,
        scenario_names=scenario_names,
    )
    resolved_baseline_path = Path(
        baseline_path or DEFAULT_RUNTIME_REPLAY_BASELINE
    ).expanduser().resolve()
    baseline = load_runtime_replay_baseline(resolved_baseline_path)
    baseline_map = {
        item.scenario_id: item
        for item in list(baseline.scenario_baselines)
    }

    scenario_results: list[RuntimeReplayGateScenarioResult] = []
    for current in list(report.scenario_reports):
        current_baseline = baseline_map.get(current.scenario_id)
        drift_messages = (
            ['Missing baseline scenario snapshot']
            if current_baseline is None
            else _compare_baseline(current, current_baseline)
        )
        scenario_results.append(
            RuntimeReplayGateScenarioResult(
                scenario_id=current.scenario_id,
                manifest_passed=current.passed,
                baseline_present=current_baseline is not None,
                baseline_matched=not drift_messages and current_baseline is not None,
                passed=current.passed and current_baseline is not None and not drift_messages,
                drift_messages=drift_messages,
                current=current,
                baseline=current_baseline,
            )
        )

    current_ids = {item.scenario_id for item in list(report.scenario_reports)}
    extra_baseline_scenarios = sorted(
        scenario_id
        for scenario_id in baseline_map
        if scenario_id not in current_ids
    ) if scenario_names is None else []
    manifest_failed = sum(1 for item in scenario_results if not item.manifest_passed)
    drifted = sum(1 for item in scenario_results if item.baseline_present and not item.baseline_matched)
    missing_baseline = sum(1 for item in scenario_results if not item.baseline_present)

    return RuntimeReplayGateResult(
        fixture_root=report.fixture_root,
        baseline_path=str(resolved_baseline_path),
        report=report,
        baseline=baseline,
        scenario_results=scenario_results,
        extra_baseline_scenarios=extra_baseline_scenarios,
        passed=(
            report.passed
            and manifest_failed == 0
            and drifted == 0
            and missing_baseline == 0
            and not extra_baseline_scenarios
        ),
        summary=(
            f'Runtime replay drift gate complete: scenarios={len(scenario_results)} '
            f'manifest_failed={manifest_failed} drifted={drifted} '
            f'missing_baseline={missing_baseline} extra_baseline={len(extra_baseline_scenarios)}'
        ),
    )
