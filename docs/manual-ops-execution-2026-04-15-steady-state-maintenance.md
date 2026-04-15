# Steady-State Maintenance - 2026-04-15

This note records a no-change maintenance pass after the initial applied-ops round had already been closed.

## Baseline Gate

Commands run:

- `PYTHONPATH=src python3 scripts/run_tests.py`
- `PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode full`
- `PYTHONPATH=src python3 scripts/run_verify_report.py --mode full`
- `PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown`

Results:

- `run_tests.py`: `passed=330 failed=0`
- `run_simulation_suite.py --mode full`: `matched=16 drifted=0 invalid_fixture=0`
- `run_verify_report.py --mode full`: `overall_status=pass`
- `run_ops_roundbook.py --mode quick`: `overall_readiness=ready`

## Applied-Line Checks

Additional commands run:

- `PYTHONPATH=src python3 scripts/run_create_seed_package_review.py --format markdown`
- `PYTHONPATH=src python3 scripts/run_runtime_prior_retrieval_trial.py --format markdown`
- `PYTHONPATH=src python3 scripts/run_source_post_apply_monitor.py --format markdown`

Current conclusions:

- create-seed:
  - candidate: `missing-fits-calibration-and-astropy-verification-workflow`
  - baseline: `fits-calibration-astropy-followup-local-v2`
  - verdict: `ready_for_manual_use`
  - decision: `keep_current_manual_use_baseline`
- prior:
  - family: `hf-trainer`
  - baseline top-1: `hf-trainer`
  - pilot top-1: `hf-trainer`
  - `baseline_prior_applied=false`
  - `pilot_prior_applied=true`
  - `generic_promotion_risk=0`
  - decision: `continue_allowlisted_trial`
- source:
  - repo: `alirezarezvani/claude-skills`
  - `decision_status=applied`
  - `monitor_status=stable`
  - `requirements_satisfied=true`
  - decision: `keep_stabilization_hold`

## Refill And Default Action

- `next_create_seed_candidate=(none)`
- `next_prior_family_on_hold=deep-research`
- `next_source_round_status=wait_for_post_apply_stability_before_next_live_round`

Default action after this pass:

- do not open a new approval round
- do not reopen create-seed
- do not widen prior beyond `hf-trainer`
- do not open another live source curation round

This means the repo stays in steady-state maintenance mode until a real trigger appears.
