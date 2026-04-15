# Manual Ops Continuation Runbook — April 14, 2026

This note records the first full pass of the operator-facing continuation runbook after the current create-seed baseline, prior pilot materials, and source post-apply monitor had all been materialized.

## Commands Run

```bash
PYTHONPATH=src python3 scripts/run_verify_report.py --mode full
PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown
PYTHONPATH=src python3 scripts/run_create_seed_round_pack.py --format markdown
PYTHONPATH=src python3 scripts/run_create_seed_package_review.py --format markdown
PYTHONPATH=src python3 scripts/run_runtime_prior_manual_trial.py --format markdown
PYTHONPATH=src python3 scripts/run_runtime_prior_retrieval_trial.py --format markdown
PYTHONPATH=src python3 scripts/run_source_post_apply_monitor.py --format markdown
PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown
```

## Observed Results

### Global Gate

- `run_verify_report.py --mode full`: `pass`
- `run_ops_roundbook.py --mode quick`: `overall_readiness=ready`

### Create-seed Line

- Candidate: `missing-fits-calibration-and-astropy-verification-workflow`
- Current baseline: `fits-calibration-astropy-followup-local-v2`
- Manual round pack still resolves to the approved/applied create-seed handoff artifact
- Default package review now resolves to the current `fits-calibration-astropy-followup-local-v2` run summary
- Package review result:
  - verdict: `ready_for_manual_use`
  - overall score: `0.9922`
  - confidence: `0.9965`
  - requirements satisfied: `5/5`

Conclusion:

- `keep_current_manual_use_baseline`
- Do not reopen the create-seed candidate
- Do not open a new synthesize round from this runbook step

### HF-trainer Prior Pilot Line

- Manual trial pack result: `ready_for_manual_trial`
- Retrieval trial result:
  - baseline top-1: `hf-trainer`
  - pilot top-1: `hf-trainer`
  - baseline prior applied: `false`
  - pilot prior applied: `true`
  - generic promotion risk: `0`

Conclusion:

- `continue_allowlisted_trial`
- Keep the override strictly opt-in
- Do not widen to `deep-research` yet

### Claude-skills Source Promotion Line

- Current repo: `alirezarezvani/claude-skills`
- Post-apply monitor result:
  - decision status: `applied`
  - monitor status: `stable`
  - requirements satisfied: `true`
  - rehearsal passed: `true`
  - live applied: `true`

Conclusion:

- `keep_stabilization_hold`
- Do not open a second source promotion
- Do not reopen live curation yet

## Refill State

- `next_create_seed_candidate=(none)`
- `next_prior_family_on_hold=deep-research`
- `next_source_round_status=wait_for_post_apply_stability_before_next_live_round`

## Operator Decision Summary

- Create-seed: keep `fits-calibration-astropy-followup-local-v2` as the current manual-use baseline
- HF-trainer: continue only the allowlisted pilot path
- Claude-skills: keep the promoted source under stabilization hold
