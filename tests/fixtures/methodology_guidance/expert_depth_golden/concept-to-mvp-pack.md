---
name: concept-to-mvp-pack
description: Convert a selected game direction into a first-playable MVP package, including validation goal, core loop slice, feature boundary, content scope, system priorities, and execution-ready output.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [game-design, mvp, prototyping, planning, scope, validation]
    category: game-design
    requires_toolsets: []
---

# Concept to MVP Pack

Use this skill when a game direction has already passed early evaluation and now needs to become a **small, testable first version**.

This skill answers:
- What exactly is the MVP trying to validate?
- What is the smallest playable loop?
- Which features are truly core, and which should be cut?
- How much content is needed for a credible first test?
- What materials should exist so the team can actually build the prototype?

This is a **scope-cutting and packaging skill**, not a dream-expanding skill.

## When to Use

Trigger this skill when:
1. A direction already looks promising and the next step is a prototype or first playable.
2. The user asks for MVP scope, prototype boundary, feature list, or execution materials.
3. The team risks overbuilding before validating the main fun hypothesis.
4. The user needs a bridge between concept-level thinking and production-facing documents.

## When Not to Use

Do not use this as the main skill when:
1. The direction itself is still unstable and needs go/no-go judgment first.
2. The main problem is balancing a known system rather than cutting an MVP.
3. The task is purely content writing without needing structural scope decisions.

## Core Principle

An MVP is not the smallest amount of content.
It is the smallest version that can **honestly test the central design hypothesis**.

Always define the MVP around a validation question, not around a random feature bundle.

## Default Workflow

### 1. Define the Core Validation Question

Start by forcing the project into 1-2 validation questions, such as:
- Will players enjoy this decision loop at all?
- Does the core tension survive beyond the novelty layer?
- Does this fantasy still work when production scale is tiny?
- Can the main feedback system drive replay or retention?

If the validation question is fuzzy, the MVP will sprawl.

### 2. Identify the Minimum Honest Loop

Define the smallest playable loop that still represents the real game.
Break it into:
- player input
- system response
- visible feedback
- repeat trigger

Important rule:
Do not fake the entire game with a vertical slice that looks good but does not test the actual repeatable loop.

### 3. Separate Must-Haves from Supports

Split proposed features into 3 buckets:
- **Core** — without this, the test is invalid
- **Supportive** — useful but not required for first proof
- **Later / cut** — dangerous to include in MVP

You must cut aggressively.
If too many things are labeled core, the scope is wrong.

### 4. Define the Minimum Content Package

Specify how much content is needed for the loop to be meaningfully tested.
Examples:
- number of events
- number of enemy types
- number of maps / scenes
- number of upgrade choices
- number of runs / days / weeks represented

Do not confuse content volume with legitimacy.
The question is: how much content is enough to reveal whether the loop works?

### 5. Define the Primary Systems

State which systems must exist in first version, and what depth each needs.
For each system, label:
- purpose in the MVP
- minimum viable behavior
- what can be mocked / simplified

Examples of systems:
- resource economy
- progression
- event delivery
- AI / opponent logic
- shop / loadout / deckbuilding
- social / reputation / relationship layer

### 6. Define What Is Explicitly Out of Scope

Always include a kill list.
Examples:
- extra modes
- narrative branching depth
- cosmetic systems
- meta progression
- long-tail onboarding polish
- large content pools
- secondary currencies

This section is mandatory.
A good MVP document cuts things on purpose.

### 7. Package the Output for Execution

Convert the above into concrete build-facing output.
At minimum, produce:
- MVP goal
- core loop summary
- feature boundary
- required content counts
- required systems
- out-of-scope list
- main risks
- next build recommendation

## Output Format

```md
# MVP Pack

## 1. Validation Goal
- Core question:
- Why this matters:

## 2. Minimum Honest Loop
- Input:
- System response:
- Feedback:
- Repeat trigger:

## 3. Core Features
- Must have:
- Supportive but optional:
- Cut for now:

## 4. Minimum Content Scope
- Events / levels / enemies / cards / scenes:
- Why this amount is enough:

## 5. Required Systems
### System A
- Purpose:
- Minimum viable implementation:
- Can simplify how:

## 6. Explicitly Out of Scope
-

## 7. Main Production Risks
-

## 8. Build Recommendation
- What to prototype first:
- What to test with players:
- What result would count as success:
```

## Common Failure Patterns to Catch

### Fake MVP
A polished intro or scripted demo that does not test the actual repeatable loop.

### Scope Creep Through “Just One More Core Feature”
If too many systems become mandatory, the MVP stops being a test and becomes a small full game.

### Content-Heavy Validation
If the concept only works after dozens or hundreds of content units, flag that as dangerous.

### Premature Meta Systems
Meta progression, collection layers, and monetization scaffolding often hide weak core play instead of validating it.

### Success Criteria Missing
If the team does not know what would count as “validated,” they will keep building forever.

## Style Rules

- Be practical and ruthless about cuts.
- Keep the loop honest.
- Prefer testability over impressiveness.
- Translate design intent into execution-ready scope.
- Name what not to build as clearly as what to build.

## Handoff

Use after **game-direction-evaluation**.
Common next handoffs:
- **decision-loop-stress-test** to pressure test whether the selected loop can sustain early/mid/late play.
- **simulation-resource-loop-design** when the MVP depends on a meaningful resource / relationship / pressure system.

## Short Reminder

The MVP is not there to prove you can build a lot.
It is there to prove the game deserves to exist.
