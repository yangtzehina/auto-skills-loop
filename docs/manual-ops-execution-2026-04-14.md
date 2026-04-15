# Manual Ops Execution Round — April 14, 2026

This note captures the next manual follow-up step after the first post-approval round had already been applied and validated.

## Executed Actions

### FITS/Astropy Follow-up Manual Round

- Candidate lineage: `missing-fits-calibration-and-astropy-verification-workflow`
- Follow-up skill name: `fits-calibration-astropy-followup-local`
- Input repo fixture:
  `<repo-root>/tests/fixtures/scientific_reuse_eval_repo`
- Output root:
  `<repo-root>/.generated-skills/manual_rounds_run_20260414/fits-calibration-astropy-followup-local/fits-calibration-astropy-followup-local`
- Run summary:
  `<repo-root>/.generated-skills/manual_rounds_run_20260414/fits-calibration-astropy-followup-local-run-summary.json`

Result:

- severity: `pass`
- reuse decision: `generate_fresh`
- selected online skill names:
  - `notion-knowledge-capture`
- evaluation report persisted
- quality review persisted

Package review:

- verdict: `needs_revision`
- fully_correct: `false`
- requirements satisfied: `5/5`
- overall score: `0.7190`
- confidence: `0.8736`
- repair suggestions: `0`
- notable weakness:
  - trigger accuracy stayed at `4/6`, so the package is repo-grounded and complete, but its trigger wording still needs tightening before we treat it as polished

Follow-up fix and rerun:

- We traced the weakness to a systemic issue in fallback description/eval-scaffold generation: task-derived trigger wording was being diluted by generic fallback copy and unrelated online blueprint phrasing.
- We fixed that generator/evaluation path in code, then reran the same local follow-up round as:
  - `fits-calibration-astropy-followup-local-v2`
- Updated run summary:
  - `<repo-root>/.generated-skills/manual_rounds_run_20260414/fits-calibration-astropy-followup-local-v2-run-summary.json`

Rerun result:

- severity: `pass`
- reuse decision: `generate_fresh`
- package review verdict: `ready_for_manual_use`
- fully_correct: `true`
- requirements satisfied: `5/5`
- overall score: `0.9922`
- confidence: `0.9965`
- repair suggestions: `0`
- trigger accuracy: `6/6`

This means the first follow-up round exposed a real trigger-quality issue, and the rerun confirmed the fix rather than hiding it with a one-off manual patch.

### HF Prior Real Retrieval Trial

- Family: `hf-trainer`
- Override profile:
  `<repo-root>/.generated-skills/ops_artifacts/prior_pilot/hf-trainer.json`
- Trial summary:
  `<repo-root>/.generated-skills/ops_artifacts/prior_pilot/hf-trainer-real-retrieval-trial-20260414.json`
- Repo fixture:
  `<repo-root>/tests/fixtures/hf_prior_trial_repo`

Tasks checked:

1. Resume a Hugging Face Trainer run from checkpoint without losing evaluation state.
2. Fix duplicated evaluation metrics after a Trainer checkpoint resume in a Hugging Face training workflow.

Observed comparison:

- baseline top candidate: `hf-trainer` for both tasks
- allowlisted pilot top candidate: `hf-trainer` for both tasks
- allowlisted pilot prior applied: `true` for both tasks
- generic promoted: `false` for both tasks
- verdict: `ready_for_manual_trial`

## Follow-up Notes

- The FITS/Astropy follow-up round is now beyond “can we generate anything useful” and into “can we keep trigger quality stable under more realistic reruns.” The v2 rerun is now strong enough to treat as `ready_for_manual_use`.
- The `hf-trainer` line is stable enough for a human-owned allowlisted retrieval trial on real tasks. The checked-in repo fixture and two concrete tasks both kept `hf-trainer` on top.

## Materialized Manual-Use Artifacts

### Create-seed Round Materials

- Manual round pack:
  `<repo-root>/.generated-skills/ops_artifacts/create_seed/missing-fits-calibration-and-astropy-verification-workflow-manual-round-pack-20260414.json`
- Current package review:
  `<repo-root>/.generated-skills/ops_artifacts/create_seed/fits-calibration-astropy-followup-local-v2-package-review-20260414.json`

Current state:

- create-seed approval decision: `approved`
- create-seed decision status: `applied`
- current package review verdict: `ready_for_manual_use`
- current package review score: `0.9922`

### HF Prior Manual-Trial Materials

- Manual trial pack:
  `<repo-root>/.generated-skills/ops_artifacts/prior_pilot/hf-trainer-manual-trial-pack-20260414.json`
- Current retrieval-trial snapshot:
  `<repo-root>/.generated-skills/ops_artifacts/prior_pilot/hf-trainer-real-retrieval-trial-current.json`

Current state:

- prior approval decision: `approved`
- prior decision status: `applied`
- manual trial verdict: `ready_for_manual_trial`
- baseline top candidate: `hf-trainer`
- pilot top candidate: `hf-trainer`
- generic promotion risk: `0`

### Claude-skills Stabilization Materials

- Current post-apply monitor:
  `<repo-root>/.generated-skills/ops_artifacts/source_promotion/claude-skills-post-apply-monitor-current.json`

Current state:

- source approval decision: `approved`
- source decision status: `applied`
- monitor status: `stable`
- rehearsal passed: `true`
- live applied: `true`

## Continuation Runbook Check

We reran the fixed execution stack in the same order the operator runbook now expects:

1. `run_verify_report.py --mode full`
2. `run_ops_roundbook.py --mode quick --format markdown`
3. `run_create_seed_package_review.py --format markdown`
4. `run_runtime_prior_retrieval_trial.py --format markdown`

Observed result:

- verify report: `pass`
- ops roundbook: `overall_readiness=ready`
- create-seed package review now defaults to the current `fits-calibration-astropy-followup-local-v2` baseline rather than the older 20260413 round
- create-seed conclusion: keep `fits-calibration-astropy-followup-local-v2` as the current manual-use baseline
- `hf-trainer` conclusion: continue the allowlisted pilot only; do not widen to another family yet
- `claude-skills` conclusion: keep the promoted source under stabilization hold; do not open another live curation round yet
