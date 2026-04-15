# Ops Approval Round - 2026-04-13

Round scope: move the current pending create-seed, prior-pilot, and source-promotion candidates into one explicit human-approved round.

## Create-seed

- Candidate: `missing-fits-calibration-and-astropy-verification-workflow`
- Decision: `approved`
- Why:
  - repeated no-skill gaps stayed stable in the checked-in runtime queue and seed proposal pack
  - the resulting artifact remains read-only and only materializes a manual round input
- Apply target:
  - materialize the create-seed handoff artifact

## Prior pilot

- Family: `hf-trainer`
- Decision: `approved`
- Why:
  - the checked-in prior pilot exercise remains `ready_for_manual_pilot`
  - allowlisted simulation scenarios stay matched
  - generic promotion risk remains `0`
- Apply target:
  - materialize the opt-in prior override profile only

## Source promotion

- Repo: `alirezarezvani/claude-skills`
- Decision: `approved`
- Why:
  - the latest checked-in curation round still returns `accept`
  - promotion pack reports `requirements_satisfied=true`
  - required ranking regressions and smoke coverage are already present
- Apply target:
  - append the repo into `KNOWN_SKILL_COLLECTIONS`

## Execution Checklist

1. Run `scripts/run_runtime_ops_decision_pack.py --format markdown`.
2. Update `scripts/ops_approval_manifest.json`.
3. Run `scripts/run_ops_apply_approved.py --format markdown`.
4. Run verify and roundbook.

## Apply Status

- create-seed: `applied`
  - handoff artifact: `<repo-root>/.generated-skills/ops_artifacts/create_seed/missing-fits-calibration-and-astropy-verification-workflow.json`
- prior-pilot: `applied`
  - override artifact: `<repo-root>/.generated-skills/ops_artifacts/prior_pilot/hf-trainer.json`
- source-promotion: `applied`
  - seeded collection updated in `src/openclaw_skill_create/services/online_discovery.py`

## Post-Apply Notes

- verify and roundbook were rerun after apply
- the create-seed candidate now remains a read-only manual round input; no generator flow was triggered
- the `hf-trainer` prior pilot remains opt-in only; approval materialized the override profile but did not enable prior by default
- `alirezarezvani/claude-skills` is now present in `KNOWN_SKILL_COLLECTIONS` as the single applied promotion from this round
