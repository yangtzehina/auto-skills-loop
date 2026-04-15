---
name: decision-loop-stress-test
description: Stress-test a game decision loop. Use when Codex needs to evaluate player choices, tradeoffs, failure modes, and output a structured diagnosis.
---

# decision-loop-stress-test

Use this skill to test whether a proposed decision loop creates meaningful play or only the appearance of choice.

## Overview

A decision loop is healthy when the player can read the situation, choose between real alternatives, see consequences, and update their next decision. This skill turns that idea into a repeatable stress test.

## When to Use

- The user asks whether a game loop has meaningful decisions.
- A prototype feels repetitive, obvious, or random.
- A mechanic has several options but one seems always best.
- The output should identify fixes, not just criticize the loop.

## When Not to Use

- The user needs economy balancing math only.
- The task is about narrative branching without mechanical consequence.
- The decision already has telemetry and needs statistical analysis.
- The user only wants a brainstorm of new mechanics.

## Inputs

- The loop description.
- Available player actions.
- Information the player can see before acting.
- Costs, risks, rewards, and timing.
- Known dominant strategies or player complaints.

## Workflow

1. Map the loop.
   - Name the observe, decide, act, resolve, and learn phases.
2. List the decisions.
   - Separate real choices from cosmetic options.
3. Test readability.
   - Ask what information the player has before choosing.
   - Mark hidden randomness or unreadable state.
4. Test tradeoffs.
   - For each option, name what it gains and what it gives up.
   - Flag any option with no real downside.
5. Test consequence.
   - Identify what changes after the choice.
   - If nothing changes, the decision is decorative.
6. Test adaptation.
   - Confirm the outcome teaches the player something for the next loop.
7. Recommend intervention.
   - Prefer one targeted change over redesigning the entire system.

## Output Format

```markdown
## Loop Map
- Observe:
- Decide:
- Act:
- Resolve:
- Learn:

## Decision Health
| Decision | Readable? | Tradeoff? | Consequence? | Adaptation? |
| --- | --- | --- | --- | --- |

## Dominant Strategy Risk
<Low / Medium / High with reason>

## Recommended Fix
<One focused design intervention>
```

## Quality Checks

- The diagnosis distinguishes weak information from weak consequences.
- At least one concrete player decision is analyzed.
- Dominant strategy risk is explicit.
- The recommendation changes the next playtest behavior.
- The output does not hide behind generic design language.

## Common Pitfalls

- Calling a menu option a decision when it has no consequence.
- Fixing unreadability by adding more UI instead of clearer state.
- Adding randomness to disguise a dominant strategy.
- Recommending more options when the existing options lack tradeoffs.
- Ignoring what the player learns between loops.
