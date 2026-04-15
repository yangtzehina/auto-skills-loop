from __future__ import annotations

import json
from pathlib import Path

from openclaw_skill_create.services.simulation import build_simulation_suite_report

from .runtime_test_helpers import SIMULATION_FIXTURE_ROOT, copy_tree


def test_build_simulation_suite_report_quick_matches_checked_in_fixtures():
    report = build_simulation_suite_report(
        mode='quick',
        fixture_root=SIMULATION_FIXTURE_ROOT,
    )

    assert report.matched_count == 10
    assert report.drifted_count == 0
    assert report.invalid_fixture_count == 0
    assert 'Simulation suite complete' in report.summary


def test_build_simulation_suite_report_full_includes_smoke_chain():
    report = build_simulation_suite_report(
        mode='full',
        fixture_root=SIMULATION_FIXTURE_ROOT,
    )

    assert report.matched_count == 24
    assert report.drifted_count == 0
    assert report.invalid_fixture_count == 0
    assert any(
        item.family == 'smoke_chain' and item.scenario_id == 'online_reuse_claude_skills_business_adapt'
        for item in report.scenario_results
    )
    assert any(
        item.family == 'operation_backed' and item.scenario_id == 'read_only_contract_mutates'
        for item in report.scenario_results
    )
    assert any(
        item.family == 'methodology_guidance' and item.scenario_id == 'concept_to_mvp_pack'
        for item in report.scenario_results
    )


def test_build_simulation_suite_report_supports_scenario_filter():
    report = build_simulation_suite_report(
        mode='runtime-intake',
        fixture_root=SIMULATION_FIXTURE_ROOT,
        scenario_names=['partial_trace_no_change'],
    )

    assert report.matched_count == 1
    assert len(report.scenario_results) == 1
    assert report.scenario_results[0].scenario_id == 'partial_trace_no_change'


def test_build_simulation_suite_report_detects_projection_drift(tmp_path: Path):
    fixture_root = copy_tree(tmp_path, SIMULATION_FIXTURE_ROOT)
    expected_path = (
        fixture_root
        / 'runtime_intake'
        / 'partial_trace_no_change'
        / 'expected'
        / 'result.json'
    )
    payload = json.loads(expected_path.read_text(encoding='utf-8'))
    payload['runtime_followup_action'] = 'patch_current'
    expected_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    report = build_simulation_suite_report(
        mode='runtime-intake',
        fixture_root=fixture_root,
        scenario_names=['partial_trace_no_change'],
    )

    assert report.matched_count == 0
    assert report.drifted_count == 1
    assert report.invalid_fixture_count == 0
    assert report.scenario_results[0].status == 'drifted'
    assert report.scenario_results[0].error_kind == 'projection_mismatch'


def test_build_simulation_suite_report_marks_invalid_fixture(tmp_path: Path):
    fixture_root = copy_tree(tmp_path, SIMULATION_FIXTURE_ROOT)
    expected_path = (
        fixture_root
        / 'prior_gate'
        / 'eligible_domain_safe'
        / 'expected'
        / 'result.json'
    )
    expected_path.unlink()

    report = build_simulation_suite_report(
        mode='prior-gate',
        fixture_root=fixture_root,
        scenario_names=['eligible_domain_safe'],
    )

    assert report.matched_count == 0
    assert report.drifted_count == 0
    assert report.invalid_fixture_count == 1
    assert report.scenario_results[0].status == 'invalid-fixture'
    assert report.scenario_results[0].error_kind == 'fixture_error'
