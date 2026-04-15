---
name: simulation-resource-loop-design
description: simulation-resource-loop-design methodology; use when the task needs a domain-specific workflow, output template, quality checks, and pitfalls.
---

# simulation-resource-loop-design

Use this skill when the user needs a domain-specific game-design method, not a generic methodology shell.

## Overview

Read the user request as raw design material, then convert it into expert game-design decisions, templates, checks, and failure modes.

## Core Principle

A simulation resource loop is not just a list of currencies. It is a variable web of resources, pressure relationships, positive and negative feedback, failure recovery, and emotional fantasy.

## When to Use

- The user asks for economy, production, survival, management, strategy, or systems-loop design.
- A resource loop has too many currencies, no pressure, runaway snowballing, or unclear player agency.
- The design needs a first-pass model before tuning numbers or implementing simulation code.
- The output should make variables, feedback loops, and failure recovery explicit.

## When Not to Use

- The user only wants numeric balancing values.
- The game has no persistent state or repeated resource decisions.
- The task is primarily monetization pricing or store economy.
- The user needs engine code rather than design structure.

## Inputs

- Player goal, session rhythm, and emotional fantasy.
- Candidate resources, sinks, converters, producers, caps, decay, and visible states.
- Pressure sources such as scarcity, enemies, time, opportunity cost, or maintenance.
- Known failure states, recovery expectations, and snowball risks.

## Default Workflow

### 1. List the Core Resources or Pressures

- Name each candidate resource, pressure, sink, converter, bottleneck, and player-visible state.
- Sketch the variable web before adding new resources or pressures.
- Remove duplicated currencies that ask the same decision in different words.
- Mark which variables the player can read and which are hidden simulation state.

### 2. Define Each Variable's Role

- Classify each variable as source, sink, converter, buffer, cap, signal, cost, or pressure.
- Explain the player decision each variable is supposed to create.
- Cut variables that have no player-facing role.

### 3. Map the Pressure Relationships

- Draw cause and effect pairs between resources, sinks, risks, and timing pressure.
- Identify which relationships push the player toward action and which stabilize the loop.
- Check whether pressure is visible early enough for planning.

### 4. Identify the Primary Decision Tensions

- Name the recurring tradeoffs the resource loop should force.
- Separate interesting tension from pure punishment, bookkeeping, or hidden randomness.
- Make sure the player has at least two viable responses to pressure.

### 5. Design the Main Feedback Loops

- Trace the positive loop: what compounds, accelerates, or snowballs when the player succeeds.
- Trace the negative loop: what brakes, taxes, decays, or counterpressures the system.
- Check whether positive and negative loops create rhythm rather than runaway collapse.

### 6. Design Failure and Recovery

- Define how failure happens, how the player recognizes it, and how recovery begins.
- Keep consequences visible without creating an unrecoverable death spiral.
- Avoid consequence-free resets that make pressure relationships meaningless.

### 7. Align the Loop with the Emotional Fantasy

- Check whether resource math supports the intended feeling: panic, planning, mastery, scarcity, abundance, or care.
- Use the emotional fantasy to decide which resource loop pressures should feel exciting rather than arbitrary.
- Rewrite variables that produce the wrong fantasy even if the spreadsheet balances.
- Pick the smallest first playable model that proves the emotional rhythm.

## Output Format

```markdown
## Variable Web
- Resources: <fill in>
- Sinks: <fill in>
- Converters: <fill in>
- Buffers: <fill in>
- Signals: <fill in>

## Pressure Relationships
- Cause: <fill in>
- Effect: <fill in>
- Player-visible signal: <fill in>

## Primary Decision Tensions
- Tradeoff: <fill in>
- Pressure: <fill in>
- Viable responses: <fill in>

## Positive Loop
- What compounds: <fill in>
- How it accelerates: <fill in>
- Snowball risk: <fill in>

## Negative Loop
- Brake: <fill in>
- Cost: <fill in>
- Decay: <fill in>
- Counterpressure: <fill in>

## Failure Recovery
- Failure signal: <fill in>
- Recovery action: <fill in>
- Lasting consequence: <fill in>

## Emotional Fantasy
- Intended feeling: <fill in>
- Loop support: <fill in>
- Mismatch to fix: <fill in>

```

## Quality Checks

- Variables have player-facing roles in the variable web, not only hidden simulation state.
- Pressure relationships are visible enough for planning.
- Positive and negative loops both exist; positive loop and negative loop pressures create readable rhythm.
- Failure recovery keeps consequences without creating an unrecoverable death spiral.
- Emotional fantasy matches resource math in the resource loop.
- Emotional fantasy must be visible in the pressure relationships, not only stated as theme.
- The first playable model avoids unnecessary currencies.
- The output must use domain-specific section titles and decisions, not only generic planning language.
- Another agent should be able to apply the result without rereading the original prompt.

## Common Pitfalls

- Variable web sprawl: adding resources and pressures that do not create player-facing decisions.
- Runaway snowball: adding only positive loops without counterpressure.
- Dead brake: adding a negative loop that only slows the game without creating a decision.
- Death spiral: making failure recovery mathematically impossible before the player can learn.
- Hidden pressure relationships: letting variables punish the player without readable warning.
- Emotionless resource loop: producing stable balance math that does not support the emotional fantasy.
- Prompt echo: repeating the request instead of turning it into domain actions.
- False completion: passing shape checks while the expert workflow is still missing.
