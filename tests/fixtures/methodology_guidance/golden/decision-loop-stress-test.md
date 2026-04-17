---
name: decision-loop-stress-test
description: Phase-by-phase audit for finding collapse points, dominant routes, and reward-training mistakes.
---

# decision-loop-stress-test

Audit what mastery teaches before the wrong habit hardens.

## Overview
Audit what mastery teaches before the wrong habit hardens.

## Core Principle

A decision loop is healthy when pressure changes over time. Stress it by phase, find the collapse point, and fix the structure instead of padding with more content.
First hour, midgame, and late game are distinct stress lenses.

## When to Use

- The user asks whether a game loop has meaningful decisions.
- A prototype feels repetitive, obvious, solved, random, or padded with cosmetic options.
- The team needs a diagnosis across time rather than a single gut check.

## When Not to Use

- The task is pure numeric balancing with telemetry already available.
- The user only wants new mechanic ideas without evaluating an existing loop.
- The problem is execution polish rather than decision structure.

## Inputs

- Current loop and repeated player choice.
- Information visible before the choice and feedback after it.
- Costs, risks, rewards, timing, known dominant strategies, and boring phases.

## Default Workflow
- Keep the audit on first-hour, midgame, late-game, solved state, dominant strategy, variation quality, reinforcement, and structural fixes.
- Watch the first collapse signal and reinforce the intended behavior before anyone reaches for more content.
- Reject surface excitement, content padding, MVP scope cutting, and detailed numeric balancing before proposing more content.

1. **Define the Current Loop Shape**
- Frame: Use this step to check what behavior the system is actually teaching.
- Stress Test: What does the player observe, decide, do, receive, and repeat?
- Check: Map observe, decide, act, resolve, reward, and next-choice trigger.
- Write: Loop under test with choice, feedback structure, and repeat trigger.
- Repair: Rewrite the loop as choice -> feedback -> reward -> next choice.
- Reject If: The loop description lists activities but not the repeated decision.
- Must include: current loop, core decision, feedback structure, next-choice trigger.

2. **Test the First-Hour Hook**
- Stress Test: Why would a new player understand and repeat this decision in the first hour? Name the stop condition before proposing more content.
- Check: Stress readability, immediate stakes, cause-effect feedback, and reason to repeat.
- Write: First-hour performance with hook, confusion risk, and boredom risk.
- Repair: Expose a meaningful tradeoff or readable consequence earlier.
- Reject If: The first hour works only because the premise is fresh.
- Check: Reject surface excitement if the first-hour pressure still feels weak.
- Must include: first hour, readability, reason to repeat, novelty.

3. **Test Midgame Sustainability**
- Stress Test: What prevents the midgame from flattening once the basics are understood? Name the stop condition before proposing more content.
- Check: Inspect constraints, tradeoffs, variation quality, and dominant-option risk.
- Write: Midgame pressure with tradeoff change, variation quality, and autopilot risk.
- Repair: Add state changes that force adaptation, not just larger numbers.
- Reject If: Midgame content changes labels while decisions stay identical.
- Check: Name the dominant strategy or autopilot risk before adding content.
- Must include: midgame, tradeoffs, variation quality, autopilot.

4. **Test Late-Game Expansion or Mutation**
- Stress Test: Test whether lategame mastery reveals a deeper problem or solves the game away.
- Check: Name the expansion, mutation, or collapse point that appears at mastery.
- Write: Late-game performance with evolution demand and collapse point.
- Repair: Introduce risk, asymmetry, or pressure that meets mastery.
- Reject If: Mastery removes the game instead of changing the problem.
- Check: Confirm late-game mastery creates a new decision problem instead of pure throughput.
- Must include: late-game, mastery, collapse point, mutation.

5. **Look for Solved States**
- Stress Test: Test which solved state a strong player would repeat until the loop becomes stale.
- Check: Describe the dominant strategy and the reward, cost, or timing pattern that creates it. Reject any fix that only widens content without changing pressure.
- Write: Solved-state risk with cause and counterpressure.
- Repair: Add structural counterpressure instead of another option.
- Reject If: The solved state is dismissed as player preference.
- Check: Break the dominant strategy with structural fixes, not softer compensation.
- Must include: solved state, dominant strategy, counterpressure.

6. **Audit Variation and Reinforcement**
- Stress Test: Test whether variation quality changes read, tradeoff, consequence, or adaptation.
- Check: Audit variation quality and reinforcement so the decision loop trains the intended behavior. Reject any fix that only widens content without changing pressure.
- Write: Variation quality and reinforcement recommendations.
- Repair: Reward adaptation, timing, state-reading, or expressive choices directly.
- Reject If: Rewards teach efficient autopilot while the design claims expressive play.
- Check: Reinforce the intended behavior and reject content padding or fake variation.
- Must include: variation quality, reinforcement, reward, autopilot.

## Decision Rules

- first hour creates readable pressure
- first hour midgame and lategame differ
- midgame changes decisions
- lategame mastery creates new problems
- solved state is concrete
- variation changes consequence
- variation changes decisions
- reinforcement teaches intended behavior
- where collapse happens
- structural fixes
- healthy mastery
- decision quality

## Quality Checks
- Gate: Keep the audit on collapse, dominant strategy, and reinforcement before anyone reaches for extra content.
- Reject fixes that only add content, rewards, or softer compensation; keep only the ones that change the pressure problem.
- Call out mastery that only improves throughput and still fails to create a new decision problem.
- Check whether the decision loop is readable in the first hour before novelty wears off.
- Check whether first hour, midgame, and lategame differ for the right reason instead of only inflating numbers.
- Check whether lategame pressure mutates the problem instead of rewarding autopilot.
- Check whether solved state is concrete enough to name, trigger, and attack.
- Check whether variation changes decisions rather than surface decoration.
- Check whether reinforcement teaches intended behavior instead of efficient repetition.
- Check whether the repair changes pressure inside the decision loop instead of adding softer content.

## Output Format

Keep the deliverable focused on collapse point, solved state, repair move, and the next pressure test.

```markdown
## Reinforcement Check
- Write: what behavior the rewards teach and whether they train autopilot.
- Strong: Good: Reinforcement Check names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Reinforcement Check stays abstract, repeats the prompt, or leaves the field as a vague summary.
- Focus: Keep this field sharp enough to drive the next decision.

## Current Loop Shape
- Write: observe, core decision, action, feedback structure, reward, and next-choice trigger.
- Strong: Good: Current Loop Shape names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Current Loop Shape stays abstract, repeats the prompt, or leaves the field as a vague summary.

## First-Hour Hook
- Write: first-hour readability, immediate stakes, cause-and-effect chain, and why the player still cares.
- Strong: Good: First-Hour Hook names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: First-Hour Hook stays abstract, repeats the prompt, or leaves the field as a vague summary.

## First-Hour Performance
- Write: whether the first hour creates readable pressure or only novelty-only start.
- Strong: Good: First-Hour Performance names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: First-Hour Performance stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Midgame Sustainability
- Write: compounding tradeoffs, resources or states move, and what prevents flattening.
- Strong: Good: Midgame Sustainability names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Midgame Sustainability stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Midgame Performance
- Write: midgame performance, autopilot risk, dominant option, and structural fix.
- Strong: Good: Midgame Performance names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Midgame Performance stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Late-Game Evolution
- Write: late-game expansion, mastery pressure, and whether mastery creates new problems.
- Strong: Good: Late-Game Evolution names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Late-Game Evolution stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Late-Game Performance
- Write: late-game performance, collapse point, and healthy mastery check.
- Strong: Good: Late-Game Performance names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Late-Game Performance stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Solved State Risk
- Write: solved-state risks, dominant strategy, and counterpressure.
- Strong: Good: Solved State Risk names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Solved State Risk stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Variation Quality
- Write: whether variation changes decisions, not just surface variation or cosmetic options.
- Strong: Good: Variation Quality names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Variation Quality stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Reinforcement Recommendations
- Write: reinforcement recommendations that reward adaptation, state-reading, or expressive timing.
- Strong: Good: Reinforcement Recommendations names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Reinforcement Recommendations stays abstract, repeats the prompt, or leaves the field as a vague summary.

```

## Common Pitfalls: Collapse Patterns and Repairs
If mastery removes the decision, the repair must alter pressure, not reward players with more throughput.

- Use these failure patterns to pressure-test lategame, variation quality, solved state, and reinforcement before adding content.
- Pattern index: Novelty-Only Start, Midgame Autopilot, Progression Without New Problems, Cosmetic Options, Dominant Strategy, Rewarding Autopilot.
- Repair moves: expose meaningful tradeoffs in the first hour, add state changes that force adaptation, add structural counterpressure, reward the intended behavior directly.

### Novelty-Only Start
- Symptom: Early play only works because the premise is fresh, not because the decision is clear.
- Cause: The first-hour hook never established readable pressure.
- Correction: Raise the stakes and feedback around the core choice before adding more content.

### Midgame Autopilot
- Symptom: The player keeps repeating the same answer while the game only changes labels or numbers.
- Cause: Midgame added volume without adding new constraints.
- Correction: Introduce counterpressure that forces adaptation instead of simple efficiency scaling.

### Progression Without New Problems
- Symptom: Progression adds throughput or spectacle while the underlying choice stays solved.
- Cause: Expansion arrived without a new pressure problem.
- Correction: Add a new constraint or pressure relationship before adding more content or reward layers.

### Variety Without Strategic Consequence
- Symptom: The game offers more variants, but they do not change read, tradeoff, or consequence.
- Cause: Variation was used as surface freshness instead of decision mutation.
- Correction: Cut cosmetic variation and keep only the variants that force a new answer.

### Mastery Removes the Game
- Symptom: Late play collapses into rote execution or a dominant route.
- Cause: Mastery widened throughput without creating a new decision problem.
- Correction: Change the pressure landscape so mastery unlocks new tradeoffs instead of solving the loop forever.

## Cut Rules

- not greenlighting theme
- not greenlighting the theme
- not MVP scope cutting
- not detailed numeric balancing
- surface excitement is not enough
- not content padding
- content padding cannot fix weak decision quality
- cut cosmetic variation
- fix structure before adding options

## Worked Micro-Example

- Phase-by-phase stress readout from first hour to mastery.
- Solved state diagnosis and structural repair direction.
- Reinforcement analysis showing what behavior the system trains.

## Voice Rules

- phase stress
- collapse point
- structural fix
- not content padding
