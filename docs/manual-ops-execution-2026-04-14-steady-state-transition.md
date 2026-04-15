# Manual Ops Execution - 2026-04-14 Steady-State Transition

This note records the first post-close transition from an explicitly closed applied-ops round into a repeatable steady-state operating loop.

## Round 1 - Stability Observation

Reconfirmed the current applied state with the standard gate:

- `PYTHONPATH=src python3 scripts/run_tests.py`
- `PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode quick`
- `PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode full`
- `PYTHONPATH=src python3 scripts/run_verify_report.py --mode full`
- `PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown`
- `PYTHONPATH=src python3 scripts/run_create_seed_package_review.py --format markdown`
- `PYTHONPATH=src python3 scripts/run_runtime_prior_retrieval_trial.py --format markdown`
- `PYTHONPATH=src python3 scripts/run_source_post_apply_monitor.py --format markdown`

Observed result:

- tests: `passed=322 failed=0`
- simulation quick: `matched=6 drifted=0 invalid_fixture=0`
- simulation full: `matched=16 drifted=0 invalid_fixture=0`
- verify: `pass`
- roundbook: `ready`
- create-seed baseline remains `ready_for_manual_use`
- `hf-trainer` remains safe for allowlisted use
- `claude-skills` remains `stable`

## Round 2 - Next Prior Candidate (`deep-research`)

Added a checked-in prior-gate scenario:

- `tests/fixtures/simulation/prior_gate/deep_research_hold_generic_risk/`

That scenario deliberately captures the unsafe shape we care about:

- baseline top-1: `user-interview-synthesis`
- prior top-1: `deep-research`
- `top_1_changed_count=1`
- `generic_promoted_count=1`

Materialized evaluation artifacts:

- `.generated-skills/ops_artifacts/prior_pilot/deep-research-rollout-hold-20260414.json`
- `.generated-skills/ops_artifacts/prior_pilot/deep-research-manual-trial-hold-20260414.json`

Observed result:

- rollout status for `deep-research`: `hold`
- generic promotion risk: `1`
- no new approval round opened for `deep-research`

Conclusion:

- keep `deep-research` as the next named prior candidate
- do not widen beyond `hf-trainer`

## Round 3 - Source Curation

No new source-promotion round was opened.

Reason:

- the only current applied promoted source remains `alirezarezvani/claude-skills`
- the checked-in source post-apply monitor remains `stable`
- the refill signal still says `wait_for_post_apply_stability_before_next_live_round`

Conclusion:

- keep source promotion in stabilization hold
- do not open a new live source-candidate round yet

## Round 4 - Create-seed Refill

No new create-seed refill was opened.

Reason:

- the current baseline `fits-calibration-astropy-followup-local-v2` is still `ready_for_manual_use`
- refill still reports `next_create_seed_candidate=(none)`

Conclusion:

- create-seed is now evidence-driven only
- do not open another create round until a new repeated non-simple gap appears or the current baseline is explicitly rejected

## Steady-State Entry

The repo now has a workable steady-state loop:

- keep the current create-seed baseline until new evidence appears
- keep `hf-trainer` as the only active allowlisted prior pilot
- keep `deep-research` explicitly on `hold`
- keep `claude-skills` as the only applied source promotion under stabilization hold

Further work should now follow the standard steady-state runbook rather than a bespoke next-step plan.
