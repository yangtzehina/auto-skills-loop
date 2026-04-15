# SkillClaw to skill-create-v6 Mapping Study

Date: 2026-04-13

## Scope

This note maps the current local `SkillClaw` codebase against the current local
`skill-create-v6` baseline.

The goal is not to restate both projects. The goal is to answer:

1. Which `SkillClaw` ideas are already covered by `skill-create-v6`
2. Which gaps are worth closing next
3. Which `SkillClaw` complexities should stay out of our roadmap for now

Baselines used in this study:

- `SkillClaw`
  - `skillclaw/api_server.py`
  - `skillclaw/skill_manager.py`
  - `skillclaw/skill_hub.py`
  - `skillclaw/object_store.py`
  - `evolve_server/server.py`
  - `evolve_server/summarizer.py`
  - `evolve_server/aggregation.py`
  - `evolve_server/execution.py`
  - `evolve_server/session_judge.py`
  - `agent_evolve_server/server.py`

- `skill-create-v6`
  - `docs/status-and-next-plan.md`
  - `models/online.py`
  - `models/review.py`
  - `models/runtime.py`
  - `models/runtime_governance.py`
  - `models/runtime_handoff.py`
  - `models/request.py`
  - `services/online_discovery.py`
  - `services/review.py`
  - `services/repair.py`
  - `services/runtime_analysis.py`
  - `services/runtime_hook.py`
  - `services/runtime_governance.py`
  - `services/runtime_handoff.py`

## Executive Summary

`SkillClaw` is best understood as a shared skill runtime and evolution system,
not a skill generator. Its strongest idea is that skill quality is decided by
real session evidence and then fed back into shared skill evolution.

`skill-create-v6` already covers more of that philosophy than it may look like
at first glance:

- online discovery + blueprint normalization + reuse decision
- eval scaffold + structured quality review
- deterministic runtime analysis + follow-up + governance bundle/batch
- lineage sidecars and runtime quality aggregation
- replay-based regression gating for runtime behavior

The biggest remaining gaps are not "generate better SKILL.md" gaps. They are:

1. a richer runtime evidence contract
2. a first-class "no skill matched" runtime signal that can seed new skills
3. runtime effectiveness feeding back into reuse ranking

The main `SkillClaw` ideas we should reject for now are also clear:

- full proxy interception as the default request plane
- multi-Claw adapter sprawl
- a heavy benchmark/experiment harness inside the main product repo

## Module Mapping Matrix

| Plane | SkillClaw current capability | skill-create-v6 current capability | Gap / overlap | Conclusion |
| --- | --- | --- | --- | --- |
| runtime request plane | FastAPI proxy intercepts `/v1/chat/completions` and `/v1/messages`, injects skills, normalizes provider/tool-call quirks, tracks sessions, and forwards to upstream LLMs | No proxy layer. Current runtime entry is post-run via `SkillRunRecord`, `runtime_hook`, governance bundle/batch, and normalize-only `RuntimeHandoffEnvelope` | We already have a clean handoff contract, but not a real request/runtime surface. SkillClaw owns the whole execution edge; we intentionally do not | `adapt later` |
| skill retrieval / injection plane | Local `SkillManager` loads OpenClaw-compatible `SKILL.md`, ranks by embedding/effectiveness, injects `<available_skills>` catalog, and resolves `read` usage lazily | Discovery is generation-time, not runtime-time: `SkillSourceCandidate`, `SkillBlueprint`, `SkillReuseDecision`, seeded collections, ranking regressions, domain smoke fixtures | Strong overlap on retrieval thinking and reuse selection. Missing runtime-time catalog injection and runtime effectiveness feedback into ranking | `adapt later` |
| session / evidence plane | Captures turn-level prompts, responses, tool calls/results/errors, injected/read skills, PRM, teacher logprobs, then builds `_trajectory` and `_summary` | `SkillRunRecord` + optional `step_trace`, `phase_markers`, `tool_summary`, plus deterministic `SkillRunAnalysis`, replay suites, hook/governance batch | We already have a runtime evidence chain, but it is coarser and more post-hoc. Missing a lossless trajectory layer and semantic session summary layer | `adopt now` |
| evolution / repair plane | Workflow evolve server groups sessions by skill and `__no_skill__`, then chooses improve / optimize_description / create / merge with very conservative prompts | Structured review, deterministic repair, runtime follow-up (`patch_current` / `derive_child` / `no_change`), repo-grounded requirements, eval scaffold | We already have repair and derive hooks, but no first-class no-skill creation signal and no explicit "description-only" evolution mode | `adapt later` |
| sharing / lineage / governance plane | Shared object store, manifest, stable `skill_id`, version history, conflict merge, auto pull/push/sync, server-side registry | `_meta.json`, sidecar lineage, OpenSpace runtime quality history, governance bundle/batch, read-only usage reporting, runtime handoff | We have local lineage and runtime governance, but not a stable shared-skill registry or merge-aware manifest layer | `adapt later` |
| benchmark / experiment plane | Built-in WildClawBench and experiment runners around session evolution | Eval scaffold, structured review, smoke fixtures, runtime replay report/gate/review/change/approval packs | We already have stronger deterministic governance than many repos, but not a large live benchmark harness. That is acceptable today | `do not adopt` |

## What We Already Cover from SkillClaw

These are core ideas where `skill-create-v6` is already meaningfully aligned:

1. `reuse before regenerate`
   - `SkillClaw` does this at runtime via retrieval/injection
   - we do it at generation time via online discovery and `SkillReuseDecision`

2. `evidence before mutation`
   - `SkillClaw` evolves from session evidence
   - we already require eval + structured review + runtime signals before patch/derive

3. `runtime quality should be a first-class governance input`
   - `SkillClaw` tracks effectiveness and PRM-informed experience
   - we already have `run_quality_score`, `quality_score`, `usage_stats`, and governance batch surfaces

4. `stable lineage matters`
   - `SkillClaw` has `skill_id`, version, manifest, history
   - we already carry `parent_skill_id`, `_meta.json` lineage, and aggregated runtime history

5. `separate human-readable governance from raw test assertions`
   - `SkillClaw` has summary/judge layers
   - we already have replay report, gate, review, change-pack, approval-pack, usage report, and governance bundle/batch

## Five Theme Analysis

### 1. Runtime evidence contract

**SkillClaw**

- Keeps both `_trajectory` and `_summary`
- `_trajectory` is meant to be lossless enough for deterministic reasoning
- `_summary` is meant for causal, semantic interpretation
- Session judge consumes both

**skill-create-v6**

- `SkillRunRecord` captures `skills_used`, `failure_points`, `user_corrections`,
  `step_trace`, `phase_markers`, `tool_summary`
- `analyze_skill_run_deterministically(...)` derives `helped`,
  `most_valuable_step`, `misleading_step`, `missing_steps`, `run_quality_score`,
  `recommended_action`, and history-aware `quality_score`
- governance bundle/batch gives a readable review layer on top

**Gap**

We have a good post-run contract, but not a dual-layer contract:

- no lossless session trajectory model
- no semantic runtime summary artifact
- no clean separation between raw evidence and derived judgment

**Decision**

`adopt now`

**Why**

This is the highest-value borrow that fits our current architecture without
requiring a proxy runtime.

**Where it should land**

- `models/`
  - add `RuntimeTurnTrace`
  - add `RuntimeSessionEvidence`
  - add `RuntimeSemanticSummary`
- `services/runtime_*`
  - add a normalize/build helper that can derive `RuntimeSessionEvidence`
    from richer future handoff payloads
  - optionally add a summary builder that can stay deterministic-first and
    accept an opt-in LLM layer later
- `orchestrator` sidecar / observation
  - only expose summaries by reference, not as a bloated main response body

**Minimum viable version**

- extend handoff/runtime models so one run can carry ordered per-turn evidence
- keep current `SkillRunRecord` valid
- add one derived `semantic_summary` field that is optional and sidecar-only

**Prerequisites**

- none beyond current runtime handoff contract

**Default main-chain impact**

- none if kept sidecar-only and opt-in

**Test impact**

- add replay fixtures with richer turn traces
- add backward-compatibility tests to prove old minimal payloads still work

### 2. No-skill -> create-skill

**SkillClaw**

- `aggregate_sessions_by_skill(...)` places skill-less sessions in `NO_SKILL_KEY`
- `run_once(...)` routes that bucket to `create_skill_from_sessions(...)`

**skill-create-v6**

- `decide_skill_reuse(...)` can choose `generate_fresh`
- runtime follow-up supports `derive_child`, but only from a known skill
- discovery fallback helps generation, but it is not a runtime-originated new-skill signal

**Gap**

We do not have a first-class runtime signal that says:

"no existing skill actually covered this task; consider creating one from the
runtime evidence."

**Decision**

`adapt later`

**Why**

The idea is good, but it becomes much stronger once we have richer runtime
evidence and a reliable way to distinguish "no skill matched" from "the caller
never provided skill context."

**Where it should land**

- `models/runtime_*`
  - add a small `RuntimeNoSkillSignal` or `RuntimeCreateCandidate`
- `services/runtime_analysis.py`
  - emit a no-skill candidate only when explicit conditions are met
- `services/runtime_governance.py`
  - surface these candidates in bundle/batch output

**Minimum viable version**

- if a run has zero `applied=True` skills and repeated missing-step evidence,
  emit a non-mutating `create_new_skill_candidate`

**Prerequisites**

- richer runtime evidence contract
- a reliable explicit "candidate set existed but none was used" signal

**Default main-chain impact**

- none if this only appears in governance output

**Test impact**

- needs new replay/fixture coverage for no-skill scenarios

### 3. Effectiveness-aware retrieval

**SkillClaw**

- `SkillManager` records injection and PRM feedback in `skill_stats.json`
- embedding retrieval multiplies semantic similarity by effectiveness

**skill-create-v6**

- discovery ranking is task-shaped and domain-regression-tested
- runtime stack already aggregates `quality_score`, `usage_stats`,
  `recent_actions`, and `recent_run_ids`
- usage report and governance batch expose the data, but discovery does not use it

**Gap**

We already compute runtime quality, but currently it stops at governance and
does not influence discovery ranking or reuse decisions.

**Decision**

`adapt later`

**Why**

This is highly promising, but it needs enough runtime history to avoid noisy
feedback loops. If introduced too early, it can punish new or sparsely used
skills unfairly.

**Where it should land**

- `services/online_discovery.py`
  - optional score prior in candidate ranking
- `services/runtime_usage.py`
  - adapter that exposes a compact retrieval prior
- optionally observation/diagnostics notes for explainability

**Minimum viable version**

- add an opt-in scoring adjustment:
  - default weight near zero
  - only applies when a skill has enough runtime samples

**Prerequisites**

- more real runtime history
- a clear rule for minimum sample count

**Default main-chain impact**

- should remain off by default at first

**Test impact**

- ranking regression coverage
- at least one smoke path where a historically good domain skill stays top-1

### 4. Conservative evolution governance

**SkillClaw**

- `execution.py` sharply distinguishes improve vs optimize_description vs create vs skip
- prompts explicitly protect correct environment details from being deleted
- prompts repeatedly prefer targeted edits over rewrites

**skill-create-v6**

- structured review already emits typed `RepairSuggestion`
- deterministic repair uses issue types and repo-grounded coverage
- runtime follow-up already distinguishes patch vs derive vs no-change

**Gap**

We have the mechanics, but not yet an explicit policy layer that says:

- patch scope should be narrow unless evidence is strong
- description-only fixes should be first-class
- correct environment facts must not be removed just because a run failed

**Decision**

`adopt now`

**Why**

This is a low-risk, high-signal improvement to an area we already own.

**Where it should land**

- `models/review.py`
  - add a narrow evolution intent or repair scope field
- `services/review.py`
  - emit scope hints such as `description_only`, `body_patch`, `derive_child`
- `services/repair.py`
  - honor scope hints so small trigger mismatches do not cause broad repairs
- `services/runtime_followup.py`
  - map runtime evidence into the same scoped mutation language

**Minimum viable version**

- add one new typed field, for example `repair_scope`
- support at least:
  - `description_only`
  - `body_patch`
  - `derive_child`

**Prerequisites**

- none

**Default main-chain impact**

- small and positive; should not require a new user-visible mode

**Test impact**

- unit tests for scope mapping
- replay/smoke tests proving description-only cases do not trigger broad rewrites

### 5. Shared storage + stable lineage

**SkillClaw**

- shared object store abstraction
- manifest with skill metadata
- persistent `SkillIDRegistry`
- per-skill version and content history
- same-name conflict detection and merge

**skill-create-v6**

- `_meta.json` and sidecar lineage already carry parent/evidence
- OpenSpace runtime history stores quality evolution
- request/runtime paths can preserve `parent_skill_id`
- no shared manifest, no conflict-aware multi-writer flow

**Gap**

Our lineage is real but local and sidecar-oriented. It is not yet a stable,
portable registry/manifest contract.

**Decision**

`adapt later`

**Why**

The design direction is right, but shared storage becomes worth it only once
skills are actually being patched/derived in a multi-surface or multi-user flow.

**Where it should land**

- `models/`
  - stable lineage manifest record
- `services/runtime_*` and persistence
  - adapter from `_meta.json` / store history to manifest-like records
- not in frontmatter

**Minimum viable version**

- promote stable sidecar fields:
  - `skill_id`
  - `version`
  - `parent_skill_id`
  - `content_sha`
  - `history`

**Prerequisites**

- a mutation surface beyond read-only governance

**Default main-chain impact**

- none if sidecar/store-only

**Test impact**

- lineage/version evolution fixtures
- no need for cloud sync tests yet

## High-Level Takeaways

### SkillClaw's core innovation

Its real innovation is not "skill injection." It is:

`real runtime evidence -> shared skill evolution -> future runtime improvement`

That is the part worth learning from.

### Most valuable ideas to borrow

1. Dual evidence contract
   - keep both structured trajectory and semantic summary

2. Explicit no-skill creation signal
   - treat repeated uncovered runtime tasks as future skill seeds

3. Runtime effectiveness back into retrieval
   - let good runtime history slightly strengthen reuse ranking

4. Conservative mutation policy
   - patch narrowly, avoid rewriting, and separate description fixes from body fixes

5. Stable lineage contract
   - promote `skill_id/version/history` to a stronger sidecar/store concept before shared sync exists

### Least valuable ideas to copy directly

1. Full proxy request interception
   - high engineering cost and heavy runtime coupling

2. Multi-Claw adapter matrix
   - impressive, but a maintenance trap for our current scope

3. Heavy benchmark harness inside the main repo
   - useful for research, not yet worth product complexity

4. Agent-evolve server as the default mutation engine
   - too open-ended before deterministic governance saturates

## Engineering Recommendations

### Adopt now

1. Dual runtime evidence contract
   - add richer raw evidence models beside `SkillRunRecord`
   - keep current deterministic analysis as the first derived layer

2. Conservative mutation scope
   - introduce explicit repair/evolution scope
   - make description-only adjustments first-class

### Adapt later

1. No-skill runtime creation signal
   - add only after richer runtime evidence exists

2. Runtime effectiveness-aware ranking
   - keep opt-in until runtime sample counts are reliable

3. Stable lineage manifest contract
   - promote local sidecar/store fields before any shared sync rollout

### Do not adopt now

1. Full proxy runtime plane
2. Multi-framework Claw compatibility layer
3. SkillClaw's heavy experiment harness as a main-repo dependency

## Backlog Proposal

### P0

1. Add dual runtime evidence contract
   - Reason: highest-value borrow that is fully compatible with the current runtime governance stack
   - Main-chain impact: no
   - Default: opt-in / sidecar-friendly
   - Tests: new replay fixtures for richer evidence plus backward compatibility

2. Add conservative mutation scope to review and repair
   - Reason: small change, high leverage, directly improves patch/derive quality
   - Main-chain impact: low
   - Default: on
   - Tests: unit tests plus targeted runtime follow-up regressions

### P1

1. Add no-skill runtime creation candidates
   - Reason: strong fit with SkillClaw's evolution logic, but depends on better runtime evidence
   - Main-chain impact: none if emitted as governance output only
   - Default: opt-in or sidecar-only
   - Tests: new no-skill replay fixtures

2. Add effectiveness-aware discovery prior
   - Reason: promising ranking improvement, but only once runtime data is dense enough
   - Main-chain impact: none if introduced as a disabled-by-default score adjustment
   - Default: off initially
   - Tests: ranking regressions and one smoke path

3. Promote lineage fields into a stronger manifest-like sidecar contract
   - Reason: prepares for future patch/derive mutation flows without forcing shared storage yet
   - Main-chain impact: none
   - Default: on in sidecar/store only
   - Tests: lineage/version evolution fixtures

### P2

1. Add semantic runtime summarizer on top of richer evidence
   - Reason: useful, but only after raw evidence is richer and stable
   - Main-chain impact: none if optional
   - Default: off
   - Tests: replay plus summary quality fixtures

2. Add a guarded judge that consumes richer runtime evidence instead of only replay drift
   - Reason: extension of current experimental judge, not a replacement for deterministic logic
   - Main-chain impact: none
   - Default: off
   - Tests: judge-enabled and judge-disabled parity tests

### Rejected

1. Full SkillClaw-style proxy as the default runtime request plane
   - Reason: too much architectural weight for current product shape

2. Multi-Claw adapter compatibility as a roadmap item
   - Reason: maintenance cost is higher than current product value

3. Large benchmark harness as a main product dependency
   - Reason: our deterministic replay and smoke chain already cover the more immediate governance needs

## Direct Answers

### Which SkillClaw core ideas are already covered?

- reuse before regenerate
- structured evidence before mutation
- runtime quality as governance input
- sidecar lineage thinking
- readable governance surfaces on top of raw regression data

### What are the top missing 1-3 items?

1. richer dual-layer runtime evidence
2. no-skill runtime creation signal
3. runtime effectiveness feeding back into reuse ranking

### Which advanced-looking ideas are not worth bringing in now?

- full request proxy
- multi-framework Claw adapter layer
- heavy experiment harness inside the main product repo

## Recommended next implementation order

1. `P0`: dual runtime evidence contract
2. `P0`: conservative mutation scope
3. `P1`: no-skill runtime creation candidates
4. `P1`: effectiveness-aware retrieval prior
5. `P1`: stronger lineage manifest sidecar contract

