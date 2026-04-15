# Manual Ops Execution Round — April 13, 2026

This note captures the first real post-approval execution round after the approval/apply flow was put in place.

## Executed Actions

### Create-Seed Manual Round

- Candidate: `missing-fits-calibration-and-astropy-verification-workflow`
- Approval state: `approved` and already `applied`
- Source pack: `<repo-root>/.generated-skills/ops_artifacts/create_seed/missing-fits-calibration-and-astropy-verification-workflow.json`
- Repo fixture: `<repo-root>/tests/fixtures/scientific_reuse_eval_repo`
- Output root:
  `<repo-root>/.generated-skills/manual_rounds_run_20260413/missing-fits-calibration-and-astropy-verification-workflow`

Result:

- severity: `pass`
- reuse decision: `generate_fresh`
- selected online skills:
  - `deep-research`
  - `spec-kit-skill`
  - `kiro-skill`
  - `orchestration`
- evaluation report persisted
- quality review persisted

Post-apply package review:

- package review verdict: `ready_for_manual_use`
- requirements satisfied: `5/5`
- overall score: `0.7754`
- confidence: `0.8989`
- repair suggestions: `0`

### HF Prior Manual Trial

- Family: `hf-trainer`
- Approval state: `approved` and already `applied`
- Source profile:
  `<repo-root>/.generated-skills/ops_artifacts/prior_pilot/hf-trainer.json`

Observed comparison:

- baseline top candidate: `hf-trainer`
- allowlisted pilot top candidate: `hf-trainer`
- baseline generic promoted: `false`
- allowlisted pilot generic promoted: `false`
- verdict: `ready_for_manual_trial`

Checked-in retrieval trial:

- repo fixture:
  `<repo-root>/tests/fixtures/hf_prior_trial_repo`
- selected files: `4`
- baseline prior applied: `false`
- allowlisted pilot prior applied: `true`
- baseline top candidate: `hf-trainer`
- allowlisted pilot top candidate: `hf-trainer`
- generic promotion risk: `0`
- retrieval-trial verdict: `ready_for_manual_trial`

## Follow-up Notes

- A persistence bug surfaced during the first create-seed execution attempt: planner output contained a directory-style artifact path (`references/domains/`), and persistence originally tried to write it as a file.
- Persistence now treats trailing-slash artifact paths as directory artifacts and materializes them with `mkdir`, which unblocked the manual create-seed round.
- The next operational step is not more tooling; it is deciding whether to run a second real manual skill-create round from the same create-seed candidate, or to begin a human-owned `hf-trainer` allowlisted retrieval trial.
