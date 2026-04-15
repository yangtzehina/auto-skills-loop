---
name: concept-to-mvp-pack
description: concept-to-mvp-pack methodology; use when the task needs a domain-specific workflow, output template, quality checks, and pitfalls.
---

# concept-to-mvp-pack

Use this skill when the user needs a domain-specific game-design method, not a generic methodology shell.

## Overview

Read the user request as raw design material, then convert it into expert game-design decisions, templates, checks, and failure modes.

## Core Principle

An MVP pack is not a small version of the whole game. It is the smallest honest test of the core player promise, with a validation question that can fail and a feature cut that protects learning.

## When to Use

- The user has a rough game concept and needs a scoped first build.
- The idea has too many mechanics, content hopes, or genre references competing for attention.
- The next useful output is a buildable MVP pack rather than a mood board or full design bible.
- The team needs to know what to keep, cut, defer, and test first.

## When Not to Use

- The user only wants names, theme exploration, or visual tone.
- The project already has a locked vertical slice and needs production scheduling.
- The task is mainly technical architecture, UI polish, or asset direction.
- There is not enough concept material to identify a player fantasy or loop.

## Inputs

- Concept premise and player fantasy.
- Target platform, session length, audience, and team or time constraints.
- Must-keep mechanics, inspirations, and must-avoid comparisons.
- Any known risks, confusing scope, or features the user is tempted to include.

## Default Workflow

### 1. Define the Core Validation Question

- Write the risky promise the MVP pack must prove, using language that could be falsified in a playtest.
- Separate the validation question from theme, story, polish, and feature wish lists.
- Ask what single failure would make the concept need a redesign instead of more content.

### 2. Identify the Minimum Honest Loop

- Describe the smallest playable loop that exposes the core fantasy without hiding behind future systems.
- Name the repeated player verbs and the feedback that tells the player whether the loop worked.
- Keep the loop honest: it must be playable, not just described as a future possibility.

### 3. Separate Must-Haves from Supports

- Make the feature cut by sorting mechanics into core, support, defer, and cut.
- Keep only features that prove the validation question or make the smallest honest loop readable.
- Move attractive polish, meta-progression, large content plans, and spectacle into defer or cut unless they are essential evidence.

### 4. Define the Minimum Content Package

- Choose the smallest arena, encounter, toy set, level beat, or scenario count that can prove the loop.
- Set content scope as evidence, not as a promise to represent the whole final game.
- Prefer one strong test space over several shallow variations.

### 5. Define What Is Out of Scope

- Write the out-of-scope list in concrete terms so hidden scope creep has nowhere to hide.
- Include tempting work that sounds related but does not help answer the validation question.
- Mark the earliest condition under which each deferred idea may be reconsidered.

### 6. Assemble the MVP Pack

- Package the validation question, smallest honest loop, feature cut, content scope, and out-of-scope list into one handoff.
- Add the first build target and the first playtest signal.
- Name unresolved assumptions instead of pretending the pack has solved them.

### 7. Run the Failure Pass

- Check whether the MVP pack could still fail clearly in a short playtest.
- Remove any feature that only makes the concept look bigger without increasing learning.
- Confirm the pack can guide implementation without rereading the original prompt.

## Output Format

```markdown
## Core Validation Question
- What must be proven: <fill in>
- How it could fail: <fill in>
- What evidence would count: <fill in>

## Smallest Honest Loop
- Player verbs: <fill in>
- Feedback moment: <fill in>
- Why it exposes the fantasy: <fill in>

## Feature Cut
- Core: <fill in>
- Support: <fill in>
- Defer: <fill in>
- Cut: <fill in>

## Minimum Content Package
- Test space: <fill in>
- Encounter or toy set: <fill in>
- Session length: <fill in>
- Success and fail condition: <fill in>

## Out of Scope
- Deferred ideas: <fill in>
- Why excluded: <fill in>
- Re-entry condition: <fill in>

## MVP Pack
- Build target: <fill in>
- Playtest signal: <fill in>
- Open assumptions: <fill in>

```

## Quality Checks

- The validation question can fail; it is not a slogan.
- The smallest honest loop is playable without postponed invisible systems.
- The feature cut removes attractive work that does not prove the validation question.
- The content scope is small enough to test before expanding the concept.
- The out-of-scope list blocks creep by naming tempting excluded work.
- The MVP pack is a concrete build target, not a mini design bible.
- The output must use domain-specific section titles and decisions, not only generic planning language.
- Another agent should be able to apply the result without rereading the original prompt.

## Common Pitfalls

- Vertical-slice inflation: treating the MVP pack as a tiny version of every final system.
- Scope creep by empathy: keeping every cool idea because each one feels related to the fantasy.
- Mood instead of loop: describing the vibe while failing to define the playable proof.
- Content hiding uncertainty: adding more levels, enemies, or modes instead of testing the risky promise.
- Invisible defer list: leaving out-of-scope work vague enough that it sneaks back in.
- Prompt echo: repeating the request instead of turning it into domain actions.
- False completion: passing shape checks while the expert workflow is still missing.
