---
name: simulation-resource-loop-design
description: Design a simulation resource loop. Use when Codex needs structured inputs, workflow, output template, checks, and pitfalls for resource-system design.
---

# simulation-resource-loop-design

Use this skill to design or review a resource loop for a simulation, management, survival, strategy, or systems-driven game.

## Overview

Resource loops become interesting when generation, storage, conversion, pressure, and player intent interact. This skill keeps the loop readable enough to play and systemic enough to produce meaningful tension.

## When to Use

- The user asks for economy, production, survival, or simulation loop design.
- A resource system has too many currencies or no meaningful pressure.
- The design needs a first-pass model before implementation.
- The output should include checks and likely failure modes.

## When Not to Use

- The user only wants spreadsheet tuning values.
- The game has no persistent state or repeated resource decisions.
- The task is primarily about monetization pricing.
- The user needs code for a simulation engine rather than design structure.

## Inputs

- Player goal and time horizon.
- Resources, producers, consumers, sinks, and storage.
- Pressure sources such as decay, enemies, time, scarcity, or opportunity cost.
- Upgrade or unlock structure.
- Desired emotional rhythm such as calm planning, panic recovery, or optimization.

## Workflow

1. Name the loop promise.
   - Decide what kind of tension the resource loop should create.
2. Define resources by role.
   - Classify each candidate as input, output, converter, sink, buffer, or signal.
3. Draw the core flow.
   - Identify where resources enter, transform, bottleneck, and leave.
4. Add pressure.
   - Introduce one source of loss, scarcity, timing, or competing demand.
5. Add agency.
   - Give the player at least two viable responses to pressure.
6. Add feedback.
   - Make the system communicate why it is improving or failing.
7. Scope the first playable model.
   - Keep the smallest set of resources that proves the rhythm.

## Output Format

```markdown
## Loop Promise
<The tension or rhythm this resource loop should create.>

## Resource Roles
| Resource | Role | Source | Sink | Player Decision |
| --- | --- | --- | --- | --- |

## Core Flow
<Producer -> Storage -> Converter -> Sink>

## Pressure
- <Scarcity, decay, time, risk, or competing demand>

## First Playable Scope
- Resources:
- Producers:
- Sinks:
- Win/fail signal:
```

## Quality Checks

- Every resource has a role.
- The loop contains at least one pressure source.
- The player has an understandable response to pressure.
- There is a visible feedback signal.
- The first playable avoids unnecessary currencies.

## Common Pitfalls

- Adding resources that only rename the same decision.
- Creating production without meaningful sinks.
- Creating sinks without player agency.
- Hiding pressure so the player cannot plan.
- Balancing numbers before the loop has a readable purpose.
