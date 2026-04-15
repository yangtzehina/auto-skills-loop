# Ops Approval Round Note

- Reviewed at: YYYY-MM-DD HH:MM TZ
- Reviewed by: <name>
- Decision pack command:
  - `PYTHONPATH=src python3 scripts/run_runtime_ops_decision_pack.py --format markdown --approval-manifest scripts/ops_approval_manifest.json`
- Apply command:
  - `PYTHONPATH=src python3 scripts/run_ops_apply_approved.py --format markdown`
- Verify commands:
  - `PYTHONPATH=src python3 scripts/run_verify_report.py --mode quick`
  - `PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown`

## Create Seed

- Candidate: `missing-fits-calibration-and-astropy-verification-workflow`
- Decision: `approved | deferred | rejected`
- Why:
- Applied: `yes | no`

## Prior Pilot

- Family: `hf-trainer`
- Decision: `approved | deferred | rejected`
- Why:
- Applied: `yes | no`

## Source Promotion

- Repo: `alirezarezvani/claude-skills`
- Decision: `approved | deferred | rejected`
- Why:
- Applied: `yes | no`

## Notes

- Follow-up verification outcome:
- Risks to watch:
- Next refill candidate(s):
