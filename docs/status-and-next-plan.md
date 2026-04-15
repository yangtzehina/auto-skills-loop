# Status and Next Plan

## Current status

The current `auto-skills-loop` chain is in a deliverable state.

Completed core items:

- `ExtractedSkillPatterns` schema, example, and model landed
- orchestrator integration across extractor / planner / generator / validator
- planner + validator consumption of extracted pattern hints
- deterministic repair integration with revalidation loop
- regression coverage for repair / revalidate flow
- online skill discovery with reusable blueprint extraction landed
- reuse decisioning now feeds planner / generator / response payloads
- manifest-driven discovery provider support landed for external skill catalogs
- eval scaffold generation landed for trigger / output / benchmark checks
- validator now blocks empty or malformed `evals/*.json` artifacts
- live GitHub repo search discovery landed with dedupe, repo filtering, and traversal guardrails
- repair now rebuilds invalid or empty eval scaffold artifacts and revalidates them in the main chain
- runnable eval harness landed in both orchestrator and `scripts/run_evals.py`
- richer end-to-end fixture coverage landed for online reuse + eval execution together
- compose-existing end-to-end fixture coverage landed for multi-skill reuse + eval execution together
- manual smoke coverage landed in `scripts/smoke_chain_online_eval.py`
- preloader now scans repos correctly even when the repo lives under a hidden parent directory such as `.openclaw`
- team skill catalog manifest docs and sample JSON landed for external seed catalogs
- manifest-driven discovery now fills missing `candidate_id` values before candidate validation
- persisted eval reports can now be saved as first-class artifacts through persistence policy opt-in
- live discovery now scans known public skill collections in addition to static catalog + repo search
- collection discovery now falls back to GitHub HTML pages when anonymous GitHub API rate limits are exhausted
- semantic token expansion and same-name family dedupe now improve live candidate ranking quality
- observation/output surfaces now carry `evaluation_report` context plus persisted `evaluation_report_path`
- repo search now falls back to GitHub HTML search results when anonymous GitHub search API calls are rate limited
- GitHub fetches now use a lightweight in-memory cache to avoid repeated network reads during one discovery run
- live repo search now caps per-repo candidate fan-out and reduces repo-description leakage into candidate ranking
- seeded public collection coverage now includes additional live community libraries with nested skills roots
- collection traversal now prefers reaching leaf skills inside large categorized repositories before the directory budget is exhausted
- real-world verification now confirms categorized libraries such as `xjtulyc/awesome-rosetta-skills` produce live candidates under rate-limited GitHub access
- discovery now supports root-level skill directories via seed-configured prefixes for repos such as `nexscope-ai/Amazon-Skills`
- discovery now supports category-style multi-root collections such as `aaron-he-zhu/seo-geo-claude-skills`
- seeded public collection coverage now includes `huggingface/skills` with standard `skills/` plus MCP-adjacent roots
- combined live verification now returns 30 candidates across seeded public collections in the current network-limited environment
- focused live verification confirms an 18-candidate pool across `huggingface/skills`, `openai/skills`, and `aaron-he-zhu/seo-geo-claude-skills`
- ranking regressions now protect domain-specific public skills so Amazon/SEO specialists stay ahead of generic research workflows for matching tasks
- ranking regressions now also protect Hugging Face domain skills so trainer/data/paper workflows outrank generic research helpers for matching tasks
- smoke coverage now exercises an end-to-end domain reuse path from selected online blueprint through planner, generation, and persisted eval report
- evaluation runner now avoids false-positive trigger hits when negative cases mention a skill name in an explicitly negated form such as `without using ...`
- benchmark coverage now includes `task_alignment`, and observation summaries can surface that score alongside the overall evaluation result
- orchestrator diagnostics notes now surface `task_alignment` and `adaptation_quality` whenever those benchmark dimensions exist, without changing the persisted report schema
- smoke coverage now includes a Hugging Face family adaptation path that validates reuse decisioning, eval scaffold generation, and persisted-vs-memory evaluation report parity
- discovery fixtures now cover multi-source GitHub HTML fallback under anonymous rate limits, so capped runs still surface candidates from more than one seeded collection
- default seeded collection scanning now uses internal priorities so `openai/skills` and `huggingface/skills` are scanned before broader research libraries when the global candidate cap is tight
- repo-grounded extraction now derives `SkillRequirement[]` from entrypoints, scripts, docs, configs, and workflows
- planner now maps repo-grounded requirements onto planned artifacts so generated packages can explain which files satisfy which repo evidence
- `_meta.json` now carries requirement evidence and planned coverage, and quality review emits `evals/review.json` alongside `evals/report.json`
- structured quality review now sits on top of eval + diagnostics, producing `SkillQualityReview` with requirement coverage, repair suggestions, and confidence
- repair can now consume structured review suggestions in addition to validator issue types, so quality-review output is no longer trapped as free-form notes
- runtime analysis now has explicit `SkillRunRecord` / `SkillRunAnalysis` / `EvolutionPlan` contracts for post-run quality scoring and evolution recommendations
- deterministic runtime analysis now persists through an OpenSpace helper, aggregates recent per-skill usage quality, and writes runtime judgments into `ExecutionAnalysis`
- runtime helper now resolves `.skill_id` / `SkillStore` lineage before analysis so post-run aggregation can surface `quality_score`, `usage_stats`, `recent_run_ids`, and parent lineage
- runtime evolution adapters now map `patch_current` back into repair suggestions and `derive_child` back into `SkillCreateRequestV6` input with sidecar lineage preserved in `_meta.json`
- runtime analysis now has a first-class CLI in `scripts/run_runtime_analysis.py`, mirroring the eval runner entrypoint for file or stdin JSON input
- runtime follow-up now has a first-class CLI in `scripts/run_runtime_followup.py`, turning `SkillRunAnalysis` or `EvolutionPlan` payloads into repair-ready or derive-ready follow-up JSON
- runtime cycle now has a first-class CLI in `scripts/run_runtime_cycle.py`, composing analysis and follow-up into one non-mutating automation-friendly JSON envelope
- runtime replay coverage now uses manifest-driven JSON fixtures for ordered success, misleading, and stable-gap histories, validating historical accumulation without OpenSpace persistence
- runtime replay reporting now materializes manifest-vs-actual scenario reports through `scripts/run_runtime_replay_report.py`, making deterministic behavior drift visible without reading individual test assertions
- runtime replay drift gating now compares current replay behavior against a checked-in baseline snapshot through `scripts/run_runtime_replay_gate.py`, so deterministic rule changes can be reviewed as explicit behavior drift
- runtime replay review output now renders gate results as a human-readable markdown or JSON summary through `scripts/run_runtime_replay_review.py`, so rule changes are easier to inspect without spelunking nested gate payloads
- runtime replay change packs now combine drift, review, and baseline-refresh guidance through `scripts/run_runtime_replay_change_pack.py`, making it explicit whether a rule change should be investigated or should refresh the checked-in baseline
- runtime replay approval packs now separate "approve refresh", "reject refresh", and "investigate first" decisions through `scripts/run_runtime_replay_approval_pack.py`, so baseline updates can be reviewed without immediately writing a new snapshot
- runtime hook now has a first-class CLI in `scripts/run_runtime_hook.py`, so the opt-in governance chain is callable through service, orchestrator, and standalone script without changing default main-chain behavior
- runtime usage reporting now has a read-only service plus `scripts/run_runtime_usage_report.py`, making recent per-skill runtime quality, actions, lineage, and run history visible without opening the store directly
- runtime governance bundle now has a first-class CLI in `scripts/run_runtime_governance_bundle.py`, combining `runtime_hook` output with per-skill usage snapshots for the skills touched in a single run
- runtime governance batch now has a first-class CLI in `scripts/run_runtime_governance_batch.py`, aggregating run-record directories or manifests into a read-only per-run and per-skill governance report
- runtime follow-up can now be wired into the orchestrator as an opt-in hook that only runs when `enable_runtime_hook=true` and a `runtime_run_record` is provided, surfacing a compact `runtime_hook` envelope through observation/diagnostics without changing the main response schema
- deterministic runtime analysis now prefers optional `step_trace` / `phase_markers` / `tool_summary` inputs for more stable `most_valuable_step` and `misleading_step` selection while remaining backward-compatible with minimal run payloads
- richer trace replay fixtures now live alongside the baseline-managed runtime replay suite, so step-selection precision can be regression-tested without perturbing the checked-in deterministic baseline snapshot
- a guarded runtime replay judge spike now exists behind an opt-in flag, adding narrative explanation, confidence adjustment, and review hints for drifted or blocking scenarios without changing deterministic recommended actions or baseline snapshots
- runtime test coverage now reuses shared helpers for CLI invocation and replay-fixture loading, reducing duplicated setup across the growing runtime regression suite
- runtime handoff now has a normalize-only contract and CLI in `scripts/run_runtime_handoff_normalize.py`, so future task execution surfaces can emit `SkillRunRecord` plus runtime options without bloating `SkillCreateRequestV6`
- public source verification automation now lives behind `scripts/run_public_source_verification.py` plus a checked-in candidate list, so source triage is repeatable even when a round ends with zero new default seeded collections
- scientific-family smoke coverage now includes an Astropy-oriented end-to-end fixture, ensuring scientific skills stay ahead of generic research helpers through reuse, planning, and persisted eval parity
- public-source maintenance verification on April 13, 2026 sampled `Cam10001110101/claude-skills-base` (0 candidates), `giuseppe-trisciuoglio/developer-kit-claude-code` (0), `alirezarezvani/claude-skills` (6 but high overlap with existing SEO/Amazon coverage), and `K-Dense-AI/claude-scientific-skills` (6 stable scientific candidates); only `K-Dense-AI/claude-scientific-skills` met the “high-value, low-maintenance” bar and was added to default seeded collections

Validation snapshot from the current workspace:

- full test harness pass (`passed=294 failed=0`)
- simulation quick pass (`matched=6 drifted=0 invalid_fixture=0`)
- simulation full pass (`matched=14 drifted=0 invalid_fixture=0`)
- smoke chain pass

## What is still left

The core five-phase follow-up plan is now complete. Remaining work is optional expansion rather than baseline completion:

- continue adding only high-signal public collections whose structure and quality justify ongoing maintenance
- add more domain-specific end-to-end fixtures only when a new family changes ranking or reuse behavior in a material way
- keep the runtime hook opt-in and sidecar-oriented until there is a stronger task-execution product surface that truly benefits from automatic follow-up
- only promote the guarded runtime judge beyond experimental status if real usage shows deterministic replay review is no longer expressive enough
- keep extending lineage quality scoring and derive/patch recommendations as more live runtime history accumulates
- keep runtime usage reporting read-only unless a future governance surface genuinely needs a stronger mutation flow
- keep runtime governance bundle/batch read-only unless a future task surface truly needs mutation or approval workflows attached to them
- keep the runtime handoff envelope narrow and execution-surface-facing rather than expanding `SkillCreateRequestV6` again
- keep tightening developer ergonomics and duplicated test setup over time
- keep runtime create queue as a read-only backlog until there is a stronger review or promotion workflow for new-skill candidates
- keep runtime prior promotion gated and diagnostics-heavy until more live runtime history exists across multiple domain families
- keep lineage manifest evolution local-sidecar-first unless real multi-writer conflicts justify a heavier shared registry
- keep runtime seed proposal packs read-only until there is a stronger human review surface for starting new-skill rounds
- keep runtime prior pilot profiles allowlist-bounded and opt-in until at least one family is explicitly approved for a live pilot
- keep live source curation rounds rehearsal-first and promotion-capped; external network variability should block promotion, not weaken the gate
- keep unified verify reporting optional so the default developer gate stays lightweight
- keep runtime ops decision packs, prior pilot exercises, source promotion packs, and ops roundbooks read-only until humans explicitly approve a pilot or promotion

## Suggested follow-up plan

### Phase 1 — done

- mark the chain as main-path complete
- keep the delivery statement focused on landed capability
- treat remaining items as follow-up expansion rather than missing baseline functionality
- wire online reuse context into planning, generation, and validation

### Phase 2 — done

- widen seeded collection coverage with more public skill libraries that match current skill-create demand
- let downstream automation or observation consumers ingest evaluation score/path without extra parsing
- keep tightening live ranking quality so generic workflow skills do not outrank strongly task-shaped skills
- keep adding only the public collections whose structure and quality justify long-term maintenance
- extend smoke and fixture coverage whenever a new public-skill family changes discovery or reuse behavior

### Phase 3 — done

- surface benchmark signals through diagnostics and observation layers without breaking compatibility
- add richer repo fixtures for repo-grounded planning + online reuse
- keep model-backed evaluation or replay-based judging as a future enhancement

### Phase 4 — P2 landed

- explicit post-run runtime analysis now emits deterministic `SkillRunRecord` / `SkillRunAnalysis` / `EvolutionPlan`
- runtime quality is now aggregated from recent `ExecutionAnalysis` history without changing the OpenSpace DB schema
- runtime suggestions now flow back into repair / derive adapters without rewriting the orchestrator
- runtime analysis is now callable through a stable CLI contract for human and automation use
- runtime follow-up is now callable through a stable CLI contract that materializes either repair suggestions, derived requests, or explicit no-op decisions
- runtime cycle is now callable through a stable CLI contract that runs analysis and follow-up together without mutating the generated skill or the skill-create main chain
- runtime hook is now callable through a stable CLI contract that packages cycle, replay review, change-pack, approval-pack, and guarded judge output together without mutating the skill or baseline
- runtime usage is now callable through a stable CLI contract that surfaces aggregated per-skill runtime quality and lineage from existing store history
- runtime governance bundle and batch are now callable through stable CLI contracts, covering single-run and multi-run governance review without opening the store directly or mutating runtime state
- runtime replay reporting, gating, review, change-pack, and approval-pack flows now cover deterministic behavior drift from fixture manifest all the way to baseline update guidance
- runtime hook integration is now available as an opt-in orchestrator path rather than a mandatory default behavior
- richer runtime trace inputs and replay fixtures now extend deterministic runtime judgment without breaking old payloads
- guarded LLM-backed replay judging now exists as an experimental supplement, but deterministic action selection remains the source of truth
- public seeded collection maintenance now includes a verified scientific domain family via `K-Dense-AI/claude-scientific-skills` while still rejecting high-overlap or low-yield candidates
- runtime handoff normalization is now available as a dedicated pre-hook contract so future execution surfaces can hand off into the runtime governance chain without changing the main skill-create request schema
- runtime handoff can now normalize optional turn-trace evidence into both `SkillRunRecord` and sidecar `RuntimeSessionEvidence` / `RuntimeSemanticSummary`, so richer execution traces improve deterministic step selection without changing the minimal runtime contract
- runtime repair suggestions now carry explicit mutation scope (`description_only` / `body_patch` / `derive_child`), and deterministic repair respects that scope instead of broad-patching every failure mode
- runtime analysis can now emit top-level no-skill create candidates for repeated uncovered gaps, and runtime governance bundle/batch surfaces those candidates without auto-generating a skill
- online discovery can now apply an opt-in runtime effectiveness prior, exposing `base_score`, `runtime_prior_delta`, and `adjusted_score` on candidates while keeping domain ranking as the primary signal
- `_meta.json` now carries a stable lineage manifest block with `skill_id`, `version`, `parent_skill_id`, `content_sha`, `quality_score`, and `history`, while frontmatter remains limited to `name` and `description`
- runtime governance intake now has a single-entry service and CLI, so future execution surfaces can submit one `RuntimeHandoffEnvelope` and receive normalized handoff, runtime hook output, and governance bundle in one read-only envelope
- runtime create queue now aggregates repeated no-skill create candidates into a reviewable backlog keyed by normalized gap clusters instead of leaving those signals buried inside single-run analyses
- runtime prior promotion gating now reports eligibility, prior deltas, and top-1 ranking impact before any wider rollout of runtime effectiveness priors
- runtime usage and governance summaries now surface `lineage_version` and `latest_lineage_event`, making local sidecar lineage visible in read-only governance reports
- lineage sidecars now append patch/derive history entries instead of overwriting a single lineage snapshot, keeping local version history traceable without introducing a second storage system
- public source verification reports now mark `smoke_required`, `selected_for_default`, and `promoted_repos`, so curation rounds can end with either zero promotion or one clearly selected default-seed candidate without ambiguity
- simulation fixtures now live under `tests/fixtures/simulation/`, covering runtime intake, runtime batch, create queue, prior gate, public source curation rehearsal, and one checked-in smoke-chain scenario
- `scripts/run_simulation_suite.py` now provides a single read-only harness with `quick`, `full`, and family-specific modes, comparing projection-based golden outputs instead of raw stdout
- simulation scenarios now return explicit `matched`, `drifted`, or `invalid-fixture` results, making higher-level behavior drift visible without replacing the existing runtime replay gate
- public source curation rehearsal is now available as a fake-provider simulation family, so accept/reject/manual-review behavior can be regression-tested without hitting live GitHub
- simulation validation is now an optional lane layered on top of `scripts/run_tests.py`, rather than a mandatory default gate
- runtime governance outputs now surface a sidecar semantic summary whenever richer session evidence exists, without changing deterministic runtime actions or replay baselines
- runtime create queue can now be lifted into a read-only review pack with suggested titles, descriptions, and representative task summaries for repeated no-skill gaps
- runtime create review output can now be lifted again into a read-only seed proposal pack with suggested titles, descriptions, representative tasks, and preview `SkillCreateRequestV6` payloads for manual new-skill decisions
- runtime prior gating can now be promoted into a family-level rollout report that recommends `hold`, `pilot`, or `eligible` without enabling the prior by default
- runtime prior rollout output can now be translated into read-only pilot profiles with `runtime_effectiveness_allowed_families` previews, so family-bounded opt-in prior trials are explicit before anyone enables them
- online discovery now honors an opt-in family allowlist before applying runtime effectiveness priors, keeping pilot-style runtime prior usage bounded even when enough run history exists
- public source curation now has a rehearsal-first live round wrapper, so fake-provider rehearsal can pass before any live verification round runs against the checked-in candidate list
- controlled live source promotion rounds now remain rehearsal-first and promotion-capped at `0-1` repos per round, with regression coverage in place even when live external verification depends on runtime network conditions
- the latest controlled live curation round on April 13, 2026 passed rehearsal and returned `alirezarezvani/claude-skills` as the single promoted candidate while still leaving actual seeded-collection mutation as a separate manual decision
- local verification now has an optional wrapper lane that runs the default test gate plus either quick or full simulation coverage in one command
- local verification now also has a unified verify report entrypoint that summarizes tests, simulation, and optional live curation as one `pass | warn | fail` decision without changing the default gate
- runtime ops decision packs now gather current create-seed proposals, prior-pilot candidates, and source-promotion candidates into one read-only review artifact
- runtime prior pilot exercises now turn the current `hf-trainer` pilot profile plus checked-in prior-gate simulation scenarios into a `ready_for_manual_pilot | hold` decision without enabling the prior
- public source promotion packs now turn the latest checked-in curation round into a manual-promotion artifact, including required ranking regressions, required smoke, and a seed patch preview for `KNOWN_SKILL_COLLECTIONS`
- simulation coverage now includes an `hf-trainer` pilot-ready prior scenario, so allowlisted runtime-prior pilots have explicit checked-in regression coverage
- ops roundbook reporting now combines verify status, runtime ops decisions, prior pilot exercise output, and source promotion packs into one release-style read-only summary
- a checked-in `scripts/ops_approval_manifest.json` now acts as the single fact source for manual approval state across create-seed, prior-pilot, and source-promotion candidates
- approval-aware decision models now distinguish `pending`, `approved_not_applied`, and `applied`, so ops decision packs, verify reports, and roundbooks can surface manual approval state without performing hidden mutations
- `scripts/run_ops_apply_approved.py` now materializes only explicitly approved create-seed handoffs and prior-pilot override profiles, and only approved source-promotion entries may patch seeded collections
- the April 13, 2026 approval round moved the FITS/Astropy create-seed candidate, the `hf-trainer` prior pilot, and the `alirezarezvani/claude-skills` source promotion from `pending` to `approved`
- a checked-in `scripts/ops_approval_round_note_template.md` now provides a stable per-round note format, so approval decisions, rationale, and apply status can be recorded in one place
- approved create-seed candidates can now be lifted again into a read-only manual round pack with handoff path, preview request, recommended fixture inputs, and launch checklist, but the repo still does not auto-run generator flows
- approved `hf-trainer` prior-pilot candidates can now be lifted into a read-only manual trial pack with request overrides, recommended trial tasks, expected safe signals, and rollback steps, while discovery defaults still keep runtime prior off
- source promotion packs now mark `requirements_satisfied` explicitly before any apply step is allowed, so `approved_not_applied` can be distinguished cleanly from truly `applied`
- the same approval round then applied all three approved items: the create-seed handoff artifact was materialized, the `hf-trainer` override profile was materialized, and `alirezarezvani/claude-skills` was appended to `KNOWN_SKILL_COLLECTIONS`
- ops roundbook now includes a refill section for `next_create_seed_candidate`, `next_prior_family_on_hold`, and `next_source_round_status`, keeping the next likely manual candidate visible after the current round has been applied
- post-apply reporting now has explicit read-only entrypoints for create-seed launch readiness, `hf-trainer` prior-trial observation, and `alirezarezvani/claude-skills` post-apply monitoring, so applied decisions can be revalidated without reopening the approval/apply flow
- the current post-apply state is stable: the create-seed launch report is `launch_ready`, the `hf-trainer` trial observation is `trial_ready`, and the `claude-skills` post-apply monitor is `stable`, while refill still points the next prior family at `deep-research`
- the first real post-approval execution round is now recorded in `docs/manual-ops-execution-2026-04-13.md`: the FITS/Astropy create-seed candidate completed a persisted manual skill-create round under `.generated-skills/manual_rounds_run_20260413/`, and the `hf-trainer` allowlisted prior trial stayed stable with `hf-trainer` as top-1 and `generic_promoted=false`
- persistence now supports directory-style artifact paths such as `references/domains/`, which unblocked real manual rounds for planner outputs that mix directory markers and nested files
- the persisted FITS/Astropy package review is now `ready_for_manual_use` with `requirements_satisfied=5/5`, `overall_score=0.7754`, and no repair suggestions
- the checked-in `hf-trainer` retrieval trial on `tests/fixtures/hf_prior_trial_repo` kept `hf-trainer` as top-1 in both baseline and allowlisted pilot, with `baseline_prior_applied=false`, `pilot_prior_applied=true`, and `generic_promotion_risk=0`
- a second local FITS/Astropy follow-up round is now recorded in `docs/manual-ops-execution-2026-04-14.md`; its first pass exposed a real trigger-quality issue (`needs_revision`, trigger accuracy `4/6`), and the subsequent `fits-calibration-astropy-followup-local-v2` rerun fixed that path systemically and now lands at `ready_for_manual_use` with `overall_score=0.9922` and trigger accuracy `6/6`
- a multi-task real retrieval trial for `hf-trainer` is now persisted under `.generated-skills/ops_artifacts/prior_pilot/hf-trainer-real-retrieval-trial-20260414.json`; both checked tasks kept `hf-trainer` as top-1 and did not promote generic skills
- the current human-facing handoff materials are now also materialized: a create-seed manual round pack, a fresh package-review snapshot for `fits-calibration-astropy-followup-local-v2`, an `hf-trainer` manual-trial pack, and a current retrieval-trial snapshot; together they mean the FITS/Astropy package is ready for manual use and the `hf-trainer` line is ready for a human-owned allowlisted trial
- the continuation runbook has now been exercised directly against the live operator-facing CLI stack: `run_verify_report.py --mode full` stays `pass`, `run_ops_roundbook.py --mode quick` stays `ready`, the default create-seed package review now follows the current `fits-calibration-astropy-followup-local-v2` baseline, and `claude-skills` now also has a checked-in current post-apply monitor snapshot marked `stable`
- a full continuation-runbook pass is now recorded in `docs/manual-ops-execution-2026-04-14-continuation-runbook.md`: create-seed stays on `keep_current_manual_use_baseline`, `hf-trainer` stays on `continue_allowlisted_trial`, `claude-skills` stays on `keep_stabilization_hold`, and refill still points the next prior hold candidate at `deep-research`
- the current applied-ops round is now formally closed in `docs/manual-ops-execution-2026-04-14-round-close.md`: all global gates stayed green, create-seed remains on `keep_current_manual_use_baseline`, `hf-trainer` remains on `continue_allowlisted_trial`, `claude-skills` remains on `keep_stabilization_hold`, and the only named next-round prior candidate remains `deep-research`
- steady-state transition is now recorded in `docs/manual-ops-execution-2026-04-14-steady-state-transition.md`: Round 1 stability revalidation stayed green, `deep-research` now has an explicit checked-in hold path because it promotes a generic research skill over `user-interview-synthesis`, source curation remains unopened beyond the current applied repo, and create-seed refill remains evidence-driven
- the checked-in steady-state operator template now lives in `docs/steady-state-ops-runbook.md`, so follow-on work no longer needs a bespoke “next step” plan once the repo stays within the current gate -> decision -> approval -> apply -> verify -> round-close loop
- `skill create` now includes a built-in security audit gate inspired by SlowMist's agent-security framework: generated artifacts are scanned for outbound data, credential access, sensitive local state, dynamic execution, privilege escalation, persistence, runtime downloads, obfuscation, reconnaissance, browser session access, prompt injection/social engineering, and confirmation-bypass patterns; the audit persists `evals/security_audit.json`, upgrades severity to `warn/fail`, and blocks deterministic repair on `HIGH/REJECT` findings
- a no-change steady-state maintenance pass is now recorded in `docs/manual-ops-execution-2026-04-15-steady-state-maintenance.md`: tests stayed green, simulation full stayed fully matched, verify stayed `pass`, roundbook stayed `ready`, the current create-seed baseline remained `ready_for_manual_use`, the `hf-trainer` allowlisted pilot remained stable, and `alirezarezvani/claude-skills` remained `applied + stable`; the default action after this pass is to stop and wait for a real trigger before opening another round
- `skill create` can now split planning between `guidance` and `operation_backed` tracks: operation-backed repos produce a machine-readable `references/operations/contract.json`, an `evals/operation_validation.json` sidecar, a contract-derived `SKILL.md`, and, when needed, a thin `scripts/operation_helper.py` wrapper without forcing every skill into an installable CLI model
- `operation_backed` is now a full-chain archetype instead of a planner-only feature: runtime analysis, runtime follow-up, governance reporting, create-queue filtering, review summaries, observer notes, security audit, and simulation fixtures all preserve and use `skill_archetype`, contract validation status, and coverage-gap summaries
- operation-backed packages now also emit `evals/operation_coverage.json`, which acts as the shared contract-runtime coverage report and stabilizes `patch_current | derive_child | hold` follow-up decisions without disturbing the existing guidance steady-state
- operation-backed steady-state maintenance is now operator-facing too: `run_operation_backed_status.py` reports checked-in operation-backed health counts, `run_operation_backed_backlog.py` reports actionable `patch_current | derive_child | hold` candidates, verify now includes operation-backed summary counts, and roundbook now surfaces the current operation-backed backlog without changing the existing create-seed / prior / source gates
- the only default operation-backed `patch_current` backlog item, `backend-only-patchable`, is now closed: checked-in snapshots report `validated`, `recommended_followup=no_change`, `coverage_gap_summary=[]`, and the steady-state backlog is back to `actionable_count=0`
