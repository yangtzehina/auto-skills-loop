# skill-create-v6 Dev Notes

## Current Chain

```text
preloader
-> extractor
-> planner
-> generator
-> validator
-> repair(optional)
-> validator(recheck)
-> persistence
```

## How to Run

### Smoke chain

```bash
PYTHONPATH=src python3 scripts/smoke_chain.py
```

### Smoke chain with real preload data

```bash
PYTHONPATH=src python3 scripts/smoke_chain_real_preload.py
```

### Runtime analysis

```bash
PYTHONPATH=src python3 scripts/run_runtime_analysis.py /path/to/run_record.json
```

Or stream a payload on stdin:

```bash
cat run_record.json | PYTHONPATH=src python3 scripts/run_runtime_analysis.py -
```

### Runtime follow-up

```bash
PYTHONPATH=src python3 scripts/run_runtime_followup.py /path/to/runtime_analysis.json
```

Consume a single `EvolutionPlan` from stdin and materialize a derived request:

```bash
cat evolution_plan.json | PYTHONPATH=src python3 scripts/run_runtime_followup.py --task-summary "Create the derived child skill." -
```

### Runtime cycle

Run analysis and materialize the follow-up decision in one command. This still only returns JSON; it does not mutate the generated skill or run `skill-create` again.

```bash
PYTHONPATH=src python3 scripts/run_runtime_cycle.py /path/to/run_record.json
```

The same follow-up options are supported:

```bash
cat run_record.json | PYTHONPATH=src python3 scripts/run_runtime_cycle.py --skill-name-hint "derived-helper" -
```

### Runtime hook

Run the opt-in runtime governance chain in one command. This returns the cycle result plus replay review, change pack, approval pack, and optional judge envelope.

```bash
PYTHONPATH=src python3 scripts/run_runtime_hook.py /path/to/run_record.json
```

Focus the replay portion on selected scenarios:

```bash
PYTHONPATH=src python3 scripts/run_runtime_hook.py --scenario success_streak --scenario misleading_streak /path/to/run_record.json
```

Runtime replay regression fixtures now live under `tests/fixtures/runtime_replay/` and cover ordered 3-run histories for success, misleading, and stable-gap scenarios without needing OpenSpace.

### Runtime governance bundle

Combine the runtime hook envelope with read-only usage snapshots for just the skills touched in one run:

```bash
PYTHONPATH=src python3 scripts/run_runtime_governance_bundle.py /path/to/run_record.json
```

The same runtime hook options are supported:

```bash
PYTHONPATH=src python3 scripts/run_runtime_governance_bundle.py --scenario success_streak --baseline /tmp/baseline.json /path/to/run_record.json
```

### Runtime governance batch

Aggregate a directory of `SkillRunRecord` JSON files into one read-only governance report:

```bash
PYTHONPATH=src python3 scripts/run_runtime_governance_batch.py --format markdown /path/to/runs
```

You can also point it at a manifest JSON and filter to one skill:

```bash
PYTHONPATH=src python3 scripts/run_runtime_governance_batch.py --skill-id demo-skill__v0_abcd1234 /path/to/manifest.json
```

Governance batch now also carries `create_candidates` plus per-skill `lineage_version` and `latest_lineage_event`, so repeated no-skill gaps and sidecar lineage history are visible without opening the store or `_meta.json` manually.

### Runtime governance intake

Normalize a future execution-surface handoff payload, run the runtime hook, and materialize the governance bundle in one command:

```bash
PYTHONPATH=src python3 scripts/run_runtime_governance_intake.py /path/to/handoff.json
```

Streaming from stdin works too:

```bash
cat handoff.json | PYTHONPATH=src python3 scripts/run_runtime_governance_intake.py -
```

### Runtime create queue

Aggregate repeated no-skill create candidates into a read-only backlog:

```bash
PYTHONPATH=src python3 scripts/run_runtime_create_queue.py --format markdown /path/to/run-manifest.json
```

This queue is intentionally non-mutating; it only groups repeated uncovered gap clusters for later review.

### Runtime create review

Materialize the create queue into a more review-friendly seed pack with suggested titles and descriptions:

```bash
PYTHONPATH=src python3 scripts/run_runtime_create_review.py --format markdown /path/to/run-manifest.json
```

The review pack is still read-only. It does not call the generator or emit a `SkillCreateRequestV6`; it just turns repeated no-skill gaps into candidate briefs for manual triage.

### Runtime create seed proposals

Lift the review pack one step further into a proposal pack with a read-only `SkillCreateRequestV6` preview:

```bash
PYTHONPATH=src python3 scripts/run_runtime_create_seed_proposals.py --format markdown /path/to/run-manifest.json
```

This proposal pack stays non-mutating. It does not write request files, does not call the generator, and does not start a new skill round automatically. It exists to make manual create/no-create decisions easier.

### Runtime prior gate

Review which skill families are eligible for the opt-in runtime effectiveness prior and whether the prior would perturb top-1 ranking:

```bash
PYTHONPATH=src python3 scripts/run_runtime_prior_gate.py --format markdown /path/to/prior-spec.json
```

The report exposes eligibility, per-task top-1 changes, and whether any generic workflow/research family would be promoted unexpectedly.

### Runtime prior rollout

Build a family-level rollout recommendation on top of the prior gate:

```bash
PYTHONPATH=src python3 scripts/run_runtime_prior_rollout.py --format markdown /path/to/prior-spec.json
```

This report stays read-only and opt-in. It recommends `hold`, `pilot`, or `eligible` for each family without changing discovery defaults.

### Runtime prior pilot

Turn a rollout recommendation into an opt-in pilot profile with explicit request overrides:

```bash
PYTHONPATH=src python3 scripts/run_runtime_prior_pilot.py --format markdown /path/to/prior-spec.json
```

Or feed it an already-materialized rollout report:

```bash
PYTHONPATH=src python3 scripts/run_runtime_prior_pilot.py --format markdown /path/to/rollout-report.json
```

Pilot profiles remain read-only. They preview the `runtime_effectiveness_allowed_families` allowlist that would be passed into `SkillCreateRequestV6`, but they do not enable the prior by default.

### Runtime ops decision pack

Gather the current create-seed, prior-pilot, and source-promotion candidates into one review-oriented summary:

```bash
PYTHONPATH=src python3 scripts/run_runtime_ops_decision_pack.py --format markdown
```

This pack stays read-only. It summarizes what is pending, but it does not trigger the generator, does not change discovery defaults, and does not edit seeded collections.

### Runtime prior pilot exercise

Exercise the current pilot candidate against checked-in simulation scenarios before anyone enables the prior manually:

```bash
PYTHONPATH=src python3 scripts/run_runtime_prior_pilot_exercise.py --format markdown
```

By default this evaluates the `hf-trainer` family. It still does not enable the prior; it only reports whether the current allowlisted pilot looks safe enough for manual trial.

### Simulation suite

Run the checked-in simulation harness in quick mode for the most important read-only scenarios:

```bash
PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode quick --format markdown
```

Run the full simulation matrix, including the smoke-chain fixture and source-curation rehearsal:

```bash
PYTHONPATH=src python3 scripts/run_simulation_suite.py --mode full
```

The simulation suite is projection-based rather than raw-output-based. It reuses the existing runtime governance, prior gate, public source verification, and smoke services directly, then compares each scenario against checked-in expected projections under `tests/fixtures/simulation/`.

Simulation exit codes are:

- `0`: every scenario matched its checked-in projection
- `1`: at least one scenario drifted from its checked-in projection
- `2`: fixture or CLI input is invalid

`quick` intentionally stays read-only and non-blocking. `scripts/run_tests.py` remains the only default gate.

### Public source promotion pack

Turn the latest checked-in curation round into a promotion decision pack:

```bash
PYTHONPATH=src python3 scripts/run_public_source_promotion_pack.py --format markdown
```

The default report currently targets `alirezarezvani/claude-skills` because the latest controlled curation round returned it as the single promoted candidate. This pack still does not mutate default seeded collections; it only previews the seed patch and the regressions/smokes that should exist before a manual promotion.

### Ops approval manifest and controlled apply

Keep manual approvals in one checked-in manifest:

```bash
PYTHONPATH=src python3 scripts/run_runtime_ops_decision_pack.py --format markdown --approval-manifest scripts/ops_approval_manifest.json
```

The default manifest lives at `scripts/ops_approval_manifest.json` and keeps current create-seed, prior-pilot, and source-promotion candidates in `approved | deferred | rejected` states. When the manifest stays empty or deferred, no repo behavior changes.

Materialize only the approved artifacts with:

```bash
PYTHONPATH=src python3 scripts/run_ops_apply_approved.py --format markdown
```

This apply step is still explicit and conservative:

- approved create-seed entries produce read-only handoff artifacts under `.generated-skills/ops_artifacts/`
- approved prior-pilot entries produce read-only request-override profiles under `.generated-skills/ops_artifacts/`
- approved source-promotion entries are the only path that may patch seeded collections, and only when the checked-in promotion pack is still `ready_for_manual_promotion`

No approval means no handoff artifact, no pilot profile, and no seeded-collection mutation.

Use the checked-in round-note template to keep each human approval round explicit:

```bash
open scripts/ops_approval_round_note_template.md
```

For the current pending candidates, you can precompute the manual launch packs without mutating the repo:

```bash
PYTHONPATH=src python3 scripts/run_create_seed_round_pack.py --format markdown
PYTHONPATH=src python3 scripts/run_runtime_prior_manual_trial.py --format markdown
```

With the default deferred manifest, these packs stay `pending` and only show the material, fixture inputs, and rollout checklist that would be used after approval.

After approval has been applied, use the post-apply reports to keep the manual rollout loop explicit:

```bash
PYTHONPATH=src python3 scripts/run_create_seed_launch_report.py --format markdown
PYTHONPATH=src python3 scripts/run_runtime_prior_trial_report.py --format markdown
PYTHONPATH=src python3 scripts/run_source_post_apply_monitor.py --format markdown
PYTHONPATH=src python3 scripts/run_ops_refill_report.py --format markdown
```

These reports stay read-only:

- `run_create_seed_launch_report.py` turns an applied create-seed artifact into a launch-ready manual round summary with a suggested output root.
- `run_runtime_prior_trial_report.py` confirms the applied `hf-trainer` allowlist profile still matches the checked-in prior-gate scenarios before any human trial.
- `run_source_post_apply_monitor.py` checks that an applied promoted source is still present in `KNOWN_SKILL_COLLECTIONS` and that its checked-in smoke scenario remains green.
- `run_ops_refill_report.py` keeps the next create-seed / prior / source candidate visible after the current approved round has been applied.

For the first real manual execution round after approval/apply, we ran the approved FITS/Astropy create-seed candidate against the checked-in scientific fixture repo and persisted the result under `.generated-skills/manual_rounds_run_20260413/`.

For a more human-facing post-apply readout of that real round and the `hf-trainer` pilot behavior, run:

```bash
PYTHONPATH=src python3 scripts/run_create_seed_package_review.py --format markdown
PYTHONPATH=src python3 scripts/run_runtime_prior_retrieval_trial.py --format markdown
```

These stay read-only:

- `run_create_seed_package_review.py` reviews the persisted FITS/Astropy package and tells you whether it looks ready for continued manual use or iteration.
- `run_runtime_prior_retrieval_trial.py` reruns the approved `hf-trainer` allowlist against a checked-in repo fixture and confirms that `hf-trainer` stays on top without promoting generic skills.

On April 14, 2026 we also ran a second, more concrete FITS/Astropy follow-up round under:

- `.generated-skills/manual_rounds_run_20260414/fits-calibration-astropy-followup-local/`

That round persisted successfully and kept all requirements satisfied, but its package review still came back `needs_revision` because trigger accuracy remained at `4/6`. In other words, the package is structurally sound and repo-grounded, but it still needs a focused trigger/description tightening pass before we should treat it as polished.

We also persisted a multi-task `hf-trainer` retrieval trial summary at:

- `.generated-skills/ops_artifacts/prior_pilot/hf-trainer-real-retrieval-trial-20260414.json`

Both checked tasks kept `hf-trainer` at top-1 with `generic_promoted=false`, so the next meaningful step is a human-owned allowlisted trial on real work rather than more scaffolding.

The first `fits-calibration-astropy-followup-local` run also surfaced a real weakness in the fallback trigger wording path: the package was complete, but trigger accuracy stayed at `4/6` and the review verdict was `needs_revision`. We fixed that at the generator/eval-scaffold layer by deriving trigger-aware descriptions from the task itself and using that same description in trigger-eval positives, rather than letting unrelated blueprint phrasing leak into the scaffold.

After that fix, rerunning the same local round as `fits-calibration-astropy-followup-local-v2` moved the package to `ready_for_manual_use` with `overall_score=0.9922`, `requirements_satisfied=5/5`, and trigger accuracy `6/6`.

To hand those results to a human operator without reassembling context, we also materialize four current-use artifacts:

- `.generated-skills/ops_artifacts/create_seed/missing-fits-calibration-and-astropy-verification-workflow-manual-round-pack-20260414.json`
- `.generated-skills/ops_artifacts/create_seed/fits-calibration-astropy-followup-local-v2-package-review-20260414.json`
- `.generated-skills/ops_artifacts/prior_pilot/hf-trainer-manual-trial-pack-20260414.json`
- `.generated-skills/ops_artifacts/prior_pilot/hf-trainer-real-retrieval-trial-current.json`

Taken together, these mean:

- the FITS/Astropy line is now ready for a real human package review / manual-use step
- the `hf-trainer` line is ready for a human-owned allowlisted retrieval trial with a fixed override profile and a current safety snapshot

The operator-facing continuation runbook is now also exercised directly, not just described:

- `run_verify_report.py --mode full` remains `pass`
- `run_ops_roundbook.py --mode quick --format markdown` remains `overall_readiness=ready`
- `run_create_seed_package_review.py --format markdown` now defaults to the current `fits-calibration-astropy-followup-local-v2` baseline by preferring the latest checked-in create-seed review snapshot
- `run_runtime_prior_retrieval_trial.py --format markdown` still keeps `hf-trainer` at top-1 with `pilot_prior_applied=true` and `generic_promotion_risk=0`
- `run_source_post_apply_monitor.py --format markdown` now has a current checked-in snapshot for `alirezarezvani/claude-skills`, and that promoted source is still `stable`

We also now have a checked-in continuation-runbook note at `docs/manual-ops-execution-2026-04-14-continuation-runbook.md`. That note is the compact operator record for the first full pass of:

- `run_verify_report.py --mode full`
- `run_ops_roundbook.py --mode quick --format markdown`
- `run_create_seed_round_pack.py --format markdown`
- `run_create_seed_package_review.py --format markdown`
- `run_runtime_prior_manual_trial.py --format markdown`
- `run_runtime_prior_retrieval_trial.py --format markdown`
- `run_source_post_apply_monitor.py --format markdown`

The current operational conclusion is intentionally conservative:

- keep `fits-calibration-astropy-followup-local-v2` as the create-seed manual-use baseline
- continue only the allowlisted `hf-trainer` pilot path
- keep `alirezarezvani/claude-skills` under stabilization hold

That same operator flow is now also formally closed in `docs/manual-ops-execution-2026-04-14-round-close.md`. The close-out pass reran:

- `run_tests.py`
- `run_simulation_suite.py --mode quick`
- `run_simulation_suite.py --mode full`
- `run_verify_report.py --mode full`
- `run_ops_roundbook.py --mode quick --format markdown`
- `run_create_seed_round_pack.py --format markdown`
- `run_create_seed_package_review.py --format markdown`
- `run_runtime_prior_manual_trial.py --format markdown`
- `run_runtime_prior_retrieval_trial.py --format markdown`
- `run_source_post_apply_monitor.py --format markdown`

and locked the round at:

- create-seed: `keep_current_manual_use_baseline`
- prior pilot: `continue_allowlisted_trial`
- source promotion: `keep_stabilization_hold`
- refill: next prior hold candidate remains `deep-research`

The next prior family is no longer just a note in the refill output. We now have an explicit checked-in hold scenario for `deep-research`:

- `tests/fixtures/simulation/prior_gate/deep_research_hold_generic_risk/`

That scenario captures the unsafe case where runtime prior would move a task from `user-interview-synthesis` to the generic `deep-research` family, which forces rollout status back to `hold`. The current generated artifacts for that branch are:

- `.generated-skills/ops_artifacts/prior_pilot/deep-research-rollout-hold-20260414.json`
- `.generated-skills/ops_artifacts/prior_pilot/deep-research-manual-trial-hold-20260414.json`

We also now have a post-close transition note at `docs/manual-ops-execution-2026-04-14-steady-state-transition.md` and a reusable steady-state operator template at `docs/steady-state-ops-runbook.md`. In practice, this means:

- create-seed stays on the current manual-use baseline until new evidence appears
- `hf-trainer` stays the only active allowlisted prior family
- `deep-research` stays the next named hold family until its generic-risk story changes
- `alirezarezvani/claude-skills` stays the only applied promoted source until another rehearsal-first curation round is justified

Persistence now also treats trailing-slash artifact paths such as `references/domains/` as directory artifacts. This matters for real manual rounds because some planner outputs mix directory markers with nested reference files.

`RuntimeHandoffEnvelope` also accepts optional `turn_trace`, and normalization now emits both the legacy `SkillRunRecord` and richer sidecar evidence objects. The deterministic analyzer still treats `SkillRunRecord` as the source of truth, but when trace evidence is present it uses it to stabilize `most_valuable_step` and `misleading_step` without changing the default runtime action contract.

Runtime governance bundle, intake, and batch now also expose a sidecar `RuntimeSemanticSummary` when richer evidence is present. The semantic summary is human-readable, remains read-only, and is intentionally excluded from deterministic replay baselines.

Online discovery also supports an opt-in runtime effectiveness prior through `SkillCreateRequestV6.enable_runtime_effectiveness_prior=true`. When enabled and enough runtime history exists, candidates expose `base_score`, `runtime_prior_delta`, and `adjusted_score`; otherwise ranking falls back to the existing discovery signals unchanged.

`_meta.json` lineage is now append-only for patch/derive events, and runtime usage/governance output surfaces the latest lineage version/event so local skill evolution history is visible in read-only reports.

### Runtime replay report

Generate a manifest-vs-actual replay report across the runtime history fixtures:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_report.py
```

Focus on a single scenario when tuning one rule family:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_report.py --scenario stable_gap_streak
```

The command exits `0` when every scenario matches its manifest, `1` when mismatches are detected, and `2` for invalid CLI input.

### Verify report and roundbook

Run the unified verify report:

```bash
PYTHONPATH=src python3 scripts/run_verify_report.py --mode quick
```

Or the higher-level operations roundbook:

```bash
PYTHONPATH=src python3 scripts/run_ops_roundbook.py --mode quick --format markdown
```

The roundbook stays read-only. It combines verify status, current create-seed candidates, current prior-pilot exercise output, and the latest checked-in source-promotion pack into one release-style summary.

### Runtime replay gate

Compare the current replay behavior against the checked-in baseline snapshot:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_gate.py
```

Refresh the baseline snapshot intentionally after accepted rule changes:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_gate.py --write-baseline
```

The gate exits `0` when the manifest and baseline both match, `1` when drift is detected, and `2` for invalid CLI input.

### Runtime replay review

Render a human-friendly review summary on top of the drift gate:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_review.py --format markdown
```

Or keep the structured JSON envelope for automation:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_review.py
```

### Runtime replay change pack

Generate a rule-change oriented decision pack that tells us whether to investigate or refresh the baseline:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_change_pack.py --format markdown
```

Keep the structured JSON when another tool needs the recommendation and affected scenarios:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_change_pack.py
```

### Runtime replay approval pack

Generate the approval-oriented pack that separates "can refresh" from "should investigate first":

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_approval_pack.py --format markdown
```

Keep the structured JSON when another tool needs the approval decision, suggested command, or pending summary:

```bash
PYTHONPATH=src python3 scripts/run_runtime_replay_approval_pack.py
```

### Runtime usage report

Render a read-only report from the current runtime history store:

```bash
PYTHONPATH=src python3 scripts/run_runtime_usage_report.py --format markdown
```

Focus on one skill when debugging repeated runtime recommendations:

```bash
PYTHONPATH=src python3 scripts/run_runtime_usage_report.py --skill-id demo-skill__v0_abcd1234
```

### Runtime handoff normalize

Normalize a future execution-surface payload into `SkillRunRecord` plus runtime options without running the hook itself:

```bash
PYTHONPATH=src python3 scripts/run_runtime_handoff_normalize.py /path/to/handoff.json
```

Streaming from stdin works too:

```bash
cat handoff.json | PYTHONPATH=src python3 scripts/run_runtime_handoff_normalize.py -
```

### Public source verification

Run the checked-in public source candidate list through the verification flow:

```bash
PYTHONPATH=src python3 scripts/run_public_source_verification.py
```

Or point to a custom candidate config:

```bash
PYTHONPATH=src python3 scripts/run_public_source_verification.py --config /path/to/candidates.json
```

Verification output now also marks `smoke_required`, `selected_for_default`, and `promoted_repos`, so each curation round can end cleanly with either zero promotions or one explicitly selected default-seed repo.

Run a rehearsal-first live curation round in one command:

```bash
PYTHONPATH=src python3 scripts/run_public_source_curation_round.py --format markdown
```

The round first checks the fake-provider source-curation rehearsal scenarios through the simulation suite. Only if rehearsal is fully matched does it run live verification against the checked-in candidate list.

This wrapper is still conservative: a rehearsal mismatch blocks the live round, and even a clean live round can promote at most one repo.

### Verify stack

For day-to-day validation, wrap the default test gate plus the simulation harness in one command:

```bash
PYTHONPATH=src python3 scripts/run_verify_stack.py --mode quick
PYTHONPATH=src python3 scripts/run_verify_stack.py --mode full
```

`quick` runs `scripts/run_tests.py` plus `run_simulation_suite.py --mode quick`; `full` swaps in the full simulation matrix. This wrapper stays opt-in and does not replace `scripts/run_tests.py` as the default gate.

### Verify report

When you want one consolidated report instead of reading several command outputs, use:

```bash
PYTHONPATH=src python3 scripts/run_verify_report.py --mode quick --format markdown
PYTHONPATH=src python3 scripts/run_verify_report.py --mode full --format markdown
```

Optionally include the rehearsal-first live curation round:

```bash
PYTHONPATH=src python3 scripts/run_verify_report.py --mode quick --include-live-curation --format markdown
```

The verify report now also surfaces approval-aware decision status groups:

- `pending`
- `approved_not_applied`
- `applied`

So release-style checks can distinguish "nothing approved yet" from "approved but still intentionally not applied".

`run_ops_roundbook.py` now also includes a refill section:

- `next_create_seed_candidate`
- `next_prior_family_on_hold`
- `next_source_round_status`

That keeps the next likely candidate visible even while the current round is still pending.

```bash
PYTHONPATH=src python3 scripts/run_verify_report.py --mode full --include-live-curation --format markdown
```

The verify report stays read-only. It summarizes the test gate, the simulation gate, and optional live curation into one `pass | warn | fail` result without changing the default CI/test gate.

### Tests (pytest preferred)

```bash
python3 -m pytest
```

If `pytest` is not installed in the current environment, use the local fallback runner:

```bash
PYTHONPATH=src python3 scripts/run_tests.py
```

## Current Status

- ExtractedSkillPatterns schema / example / model are landed
- orchestrator now carries the main chain through planner / generator / validator / repair / revalidate
- planner and validator consume extracted pattern hints
- deterministic repair is connected and bounded by validator issue classification + `max_repair_attempts`
- persistence uses safe path checks + dry-run by default
- current local regression state is green (`python3 -m pytest`)

## Delivery Readout

This work should now be treated as **main-chain complete** rather than "repair still pending".
Remaining items are engineering polish, not blockers for the delivered capability.

## Guardrails

- Python 3.9 compatibility preferred
- avoid `str | None` style unions in core models
- persistence defaults stay conservative:
  - `dry_run=True`
  - `overwrite=False`
  - `backup_on_update=True`
- repair stays deterministic and only addresses bounded validator-classified issues

## Runtime Payload Notes

- input JSON must validate as `SkillRunRecord`
- `recommended_action` is currently limited to `patch_current | derive_child | no_change`
- `quality_score` currently reflects runtime quality only; it does not mix in build-time eval scores
- follow-up CLI accepts either `SkillRunAnalysis` or a single `EvolutionPlan`
- when given a full analysis, follow-up defaults to the first actionable plan unless `--plan-index` overrides it
- cycle CLI accepts `SkillRunRecord` and returns both `analysis` and `followup` in one JSON envelope
- `SkillRunRecord.step_trace` is optional and may include `skill_id`, `skill_name`, `step`, `phase`, `tool`, `status`, and `notes`
- deterministic runtime analysis prefers `step_trace` for `most_valuable_step` / `misleading_step`, but falls back to `steps_triggered` when richer trace data is absent
- opt-in runtime hook lives on `SkillCreateRequestV6` via `enable_runtime_hook`, `runtime_run_record`, `runtime_hook_baseline_path`, and `runtime_hook_scenarios`
- guarded runtime judge stays opt-in through `enable_runtime_llm_judge` and only adds supplemental explanation; it never changes deterministic `recommended_action`
- runtime hook CLI mirrors the service/orchestrator contract and still never writes baseline or auto-runs patch/derive actions
- runtime usage report is read-only and summarizes existing runtime aggregation without changing the OpenSpace store schema
- runtime governance bundle is also read-only: it combines `runtime_hook` with per-skill usage snapshots, but it never refreshes baseline or auto-runs repair/derive
- runtime governance batch builds on the bundle results; it aggregates runs for review without changing store state or baseline state
- runtime handoff normalize is intentionally pre-hook only; it converts an upstream payload into `SkillRunRecord` + runtime options and stops there
- checked-in public source verification config lives in `scripts/public_source_candidates.json`; it drives repeatable source triage without forcing a new default seeded collection every round

Minimal payload example:

```json
{
  "run_id": "run-001",
  "task_id": "task-001",
  "task_summary": "Use the generated skill in a real task run.",
  "execution_result": "partial",
  "skills_used": [
    {
      "skill_id": "demo-skill__v0_abcd1234",
      "skill_name": "demo-skill",
      "skill_path": "/tmp/demo-skill",
      "selected": true,
      "applied": true,
      "steps_triggered": [
        "review references/usage.md",
        "run scripts/build.py"
      ],
      "notes": "Applied the packaged helper flow."
    }
  ],
  "failure_points": [
    "The run scripts/build.py step used the wrong command."
  ],
  "user_corrections": [
    "Missing a repo-specific verification step."
  ],
  "output_summary": "Task finished with manual corrections.",
  "repo_paths": [
    "/tmp/repo"
  ],
  "step_trace": [
    {
      "skill_id": "demo-skill__v0_abcd1234",
      "skill_name": "demo-skill",
      "step": "run scripts/build.py",
      "phase": "execute",
      "tool": "python",
      "status": "corrected",
      "notes": "The command needed a repo-specific flag."
    }
  ],
  "phase_markers": [
    "prepare",
    "execute"
  ],
  "tool_summary": [
    "python"
  ],
  "completed_at": "2026-04-11T00:00:00+08:00"
}
```

Runtime hook usage inside the main chain is still opt-in. When enabled, the orchestrator adds a `runtime_hook` envelope to `response.observation` and a compact diagnostics note, but it does not mutate the generated skill, refresh baselines, or auto-run repair/generation follow-up.

Trace-oriented replay coverage now also lives under `tests/fixtures/runtime_trace_replay/`, where richer `step_trace` payloads validate step-selection precision without affecting the default baseline-managed replay set.

## Security Audit Gate

`skill create` now includes a built-in security audit stage inspired by SlowMist's agent-security review flow. The validator still performs the existing structural checks first, then runs a local rule-based scan across generated `SKILL.md`, scripts, references, eval artifacts, and metadata. The audit classifies findings into `LOW | MEDIUM | HIGH | REJECT`, writes a machine-readable sidecar at `evals/security_audit.json`, and feeds the result back into the shared diagnostics object.

This gate is deliberately conservative about what it blocks. `MEDIUM` findings downgrade the overall result to `warn`; `HIGH` and `REJECT` findings force `fail`, are carried into observer/review summaries, and do not enter the deterministic repair loop. The current rule families cover outbound data, credential access, sensitive local state, dynamic execution, privilege escalation, persistence, runtime downloads, obfuscation, reconnaissance, browser session access, prompt injection/social engineering, and confirmation-bypass or source-trust abuse.

## Operation-backed Skill Track

`skill-create-v6` now has a second planning/generation track inspired by CLI-Anything's split between executable operation surface and downstream skill guidance. The planner still defaults to the existing `guidance` track for documentation-heavy or workflow-only repos, but it can now promote a repo into `operation_backed` when it detects a stable CLI or backend operation surface.

For operation-backed plans, the generated package now carries a machine-readable `references/operations/contract.json`, an `evals/operation_validation.json` sidecar, and a contract-derived `SKILL.md`. Backend-only repos also get a thin `scripts/operation_helper.py` helper instead of a fake installable CLI. Validator, review, observer summaries, and the security audit all understand this contract and can fail the build when the generated surface drifts from declared JSON/session/mutability constraints.

That contract-aware track now runs through the rest of the pipeline too. Runtime analysis emits operation-aware gaps such as `missing_json_surface`, `missing_operation`, and `contract_surface_drift`; runtime follow-up can now return `patch_current`, `derive_child`, or `hold` based on those gaps; and runtime governance/create-queue processing preserves `skill_archetype`, `operation_validation_status`, and `coverage_gap_summary` so “missing operation coverage” no longer gets mistaken for “no skill exists.”

Operation-backed packages now also emit an `evals/operation_coverage.json` sidecar, and validator/review/observer paths consume it as the shared contract-runtime coverage view. The coverage report drives `recommended_followup`, keeps JSON/session/mutating-safeguard drift explicit, and helps keep repair scoped to repo-grounded contract synchronization instead of inventing new operations.

Default simulation coverage now includes a dedicated `operation_backed` fixture family covering safe native CLI repos, safe backend-only helpers, JSON-surface patch cases, derive-child operation gaps, and read-only contract violations. That family now runs in both quick and full suite execution, so the long-standing guidance baseline and the new contract-aware track regress together.

Operation-backed is now also part of steady-state ops. Two new read-only CLI surfaces, `scripts/run_operation_backed_status.py` and `scripts/run_operation_backed_backlog.py`, scan checked-in operation-backed snapshots under `.generated-skills/ops_artifacts/operation_backed` and summarize health, validation status, recommended follow-up, blocked holds, and actionable `patch_current` / `derive_child` candidates. The default steady-state samples currently keep both the safe native-CLI entry and the backend-only entry at `no_change`.

Verify and roundbook now surface that operation-backed steady-state view without changing the default gates. `run_verify_report.py --mode full` reports `operation_backed_status_counts`, `operation_backed_actionable_count`, and `operation_backed_hold_count`; `run_ops_roundbook.py --mode quick --format markdown` adds an `Operation-Backed Backlog` section listing `patch_current`, `derive_child`, and `hold` candidates. Operation-backed coverage drift continues to stay out of the no-skill create queue.

## Follow-up Engineering (non-blocking)

1. reduce duplicated test scaffolding with shared fixtures/helpers
2. tighten model constraints and type coverage
3. improve repo-grounded planner/resource usage on more realistic repos
4. expand end-to-end regression samples for pattern-aware repair flows
5. extend runtime replay fixtures when new evolution rules land
6. only expand default seeded public collections when live sampling shows clear, low-maintenance value beyond the current set
