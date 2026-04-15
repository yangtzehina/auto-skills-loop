# Repair Boundaries

## What the deterministic repair stage covers

The current repair stage is designed to close common validator-detected gaps without inventing new product scope.

It currently targets these issue classes:

- invalid or missing frontmatter repair in `SKILL.md`
- `SKILL.md` over-budget trimming
- missing planned files
- unreferenced reference files / reference navigation repair
- empty reference files
- empty script files
- incomplete reference structure
- placeholder-heavy reference files
- placeholder-heavy scripts
- non-code-like scripts
- wrapper-only scripts
- pattern-aware description / reference-link checks surfaced by validator classification

## What it does not try to do

The repair stage does **not** attempt to:

- add brand-new capability that was never planned
- resolve unsupported or speculative product claims
- infer external APIs or repo facts that were not present in repo findings
- bypass validation severity rules
- loop forever; it respects `max_repair_attempts`

## Runtime behavior

The orchestrator flow is:

```text
validator
-> repair (only when severity=fail and repairable issues exist)
-> validator(recheck)
-> persistence
```

Repair is attempted only when all of the following are true:

1. `enable_repair=True`
2. current severity is `fail`
3. validator surfaced at least one repairable issue type
4. repair attempts are still below `max_repair_attempts`

If repair makes no changes, the loop stops and the validator notes keep that context.
If repair resolves some but not all issues, the response includes the transition notes and the remaining issue list.

## Why this boundary matters

This keeps repair deterministic and auditable:

- planner decides intended shape
- generator produces the initial artifacts
- validator explains the gap
- repair only closes bounded, known classes of defects

That boundary is what makes the current chain suitable for production-style regression coverage.
