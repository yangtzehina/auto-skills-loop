---
name: concept-to-mvp-pack
description: Shape a rough game concept into a scoped MVP pack. Use when Codex needs a repeatable game-design workflow with outputs, checks, and pitfalls.
---

# concept-to-mvp-pack

Use this skill to convert a loose game idea into a concrete MVP package that a small team or agent can start building.

## Overview

The job is to reduce ambiguity without draining the concept of its spark. Treat the prompt as raw ore: extract the player fantasy, choose a narrow loop, name the smallest playable slice, and package the result as decisions rather than vibes.

## When to Use

- The user has a concept but no scoped first build.
- The user asks for a game design pack, MVP, prototype, or first playable.
- The idea has too many mechanics and needs ruthless narrowing.
- The output should guide implementation or further design work.

## When Not to Use

- The user only wants a title, tagline, or theme list.
- The project already has a locked design document and needs production planning.
- The task is about UI polish, asset direction, or code architecture only.
- There is not enough concept material to identify a player loop.

## Inputs

- Concept premise.
- Target player or emotional promise.
- Platform and session length.
- Hard constraints such as team size, genre, tech, or deadline.
- Any must-keep mechanics or must-avoid comparisons.

## Workflow

1. Capture the fantasy.
   - Write one sentence naming what the player gets to feel powerful, clever, scared, expressive, or curious about.
2. Name the core loop.
   - Use a verb chain such as scout, choose, act, react, upgrade.
   - Remove any mechanic that does not support the chain.
3. Pick the MVP boundary.
   - Choose one arena, one enemy or obstacle type, one progression axis, and one win or fail condition.
4. Define the first playable.
   - Specify the exact moment that proves the game exists.
   - Prefer one strong interaction over five shallow systems.
5. Package the design.
   - Convert choices into a compact artifact with sections and acceptance checks.
6. Stress-check scope.
   - Mark anything that belongs in later iterations.

## Output Format

```markdown
## MVP Promise
<One sentence player fantasy.>

## Core Loop
1. <Verb>
2. <Verb>
3. <Verb>

## First Playable
- Scene:
- Main interaction:
- Success condition:
- Fail condition:

## In Scope
- <Small concrete item>

## Later
- <Tempting but deferred item>

## Acceptance Checks
- <What must be true after a prototype session>
```

## Quality Checks

- The MVP can be explained in one sentence.
- The first playable has a clear start and end.
- Every included mechanic supports the core loop.
- Deferred ideas are explicitly parked instead of silently lost.
- The package gives implementation a place to begin.

## Common Pitfalls

- Turning the MVP into a full design bible.
- Keeping every cool idea because it feels related.
- Describing the mood while failing to define interaction.
- Adding progression before the core loop is fun.
- Pretending uncertainty is solved instead of naming open questions.
