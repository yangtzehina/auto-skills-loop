# Steady-State Ops Runbook

Use this runbook after the initial applied-ops round has been closed.

## 0. Default Mode

When all gates are green and no new evidence appears, the default action is to stop.

- do not open a new approval round
- do not reopen create-seed
- do not widen prior beyond the current active family
- do not reopen live source curation

Only leave steady-state maintenance mode when a concrete trigger appears:

- the current create-seed baseline is explicitly rejected, or a new repeated non-simple gap appears
- the current prior pilot drifts, or the next hold family is intentionally being re-evaluated
- the current applied source stops being stable, or a fresh rehearsal-first curation round is explicitly justified
- the current operation-backed backlog stops being read-only steady-state maintenance and starts surfacing a real `patch_current`, `derive_child`, or `hold` trigger that needs a new round

## 1. Baseline Gate

Run:

- `PYTHONPATH=src python3 scripts/run_tests.py`
- `PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode quick`
- `PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode full`
- `PYTHONPATH=src python3 scripts/run_verify_report.py --mode full`
- `PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown`

Only continue when:

- tests are green
- simulation quick/full are fully matched
- verify is `pass`
- roundbook is `ready`

## 2. Applied-Line Checks

### Create-seed

Run:

- `PYTHONPATH=src python3 scripts/run_create_seed_package_review.py --format markdown`

Default decision:

- if the current package review stays `ready_for_manual_use`, keep the current baseline
- only reopen create-seed when the baseline is explicitly rejected or a new repeated non-simple gap appears

### Prior

Run:

- `PYTHONPATH=src python3 scripts/run_runtime_prior_retrieval_trial.py --format markdown`

Default decision:

- keep the current allowlisted family only when top-1 is preserved and `generic_promotion_risk=0`
- evaluate the next hold family only after the current active pilot is stable

### Source

Run:

- `PYTHONPATH=src python3 scripts/run_source_post_apply_monitor.py --format markdown`

Default decision:

- keep the current applied source under stabilization hold while the monitor stays `stable`
- only reopen live curation when the source line is stable and a fresh candidate set exists

### Operation-backed

Run:

- `PYTHONPATH=src python3 scripts/run_operation_backed_status.py --format markdown`
- `PYTHONPATH=src python3 scripts/run_operation_backed_backlog.py --format markdown`

Default decision:

- keep `recommended_followup=no_change` skills out of the active backlog
- treat `patch_current` as a current-skill follow-up candidate, not a no-skill create trigger
- treat `derive_child` as a child-skill candidate only when repo-grounded operation evidence exists
- treat `hold` as blocked and read-only until a concrete new round is justified

## 3. Decision Paths

### If all applied lines stay stable

- record a short round note
- keep approval manifest unchanged
- do not open new approval items
- return to steady-state maintenance mode

### If create-seed produces new evidence

- reopen the create queue -> review pack -> seed proposal path
- only then add a new create-seed approval item

### If the next prior hold family should be evaluated

- add a checked-in prior-gate scenario
- add one regression that protects generic top-1 risk
- run rollout / pilot evaluation
- only open approval if the new family is not `hold`

### If source curation should reopen

- rerun rehearsal-first curation
- require `0-1` promoted repos
- require ranking regression and any needed smoke before approval

### If operation-backed follow-up should reopen

- use the backlog report to separate `patch_current`, `derive_child`, and `hold`
- do not send operation-backed coverage gaps into the no-skill create queue
- only open a new round when the backlog indicates a real repo-grounded follow-up, not a one-off note

## 4. Current Defaults

Current steady-state defaults are:

- create-seed baseline: `fits-calibration-astropy-followup-local-v2`
- active prior pilot: `hf-trainer`
- next prior hold family: `deep-research`
- applied source promotion: `alirezarezvani/claude-skills`
- operation-backed steady-state backlog: `patch_current=(none)`, `derive_child=(none)`, `hold=(none)`
