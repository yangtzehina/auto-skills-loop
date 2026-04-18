---
name: decision-loop-stress-test
description: Phase-by-phase audit for finding collapse points, dominant routes, and reward-training mistakes.
---

# decision-loop-stress-test

Audit the loop for pressure, collapse, and wrong reinforcement before mastery hardens the wrong habit into the only answer.

## Overview

Audit what mastery teaches, which reward loop currently trains the wrong habit, what player behavior must disappear, what right habit should replace it, what replacement behavior must become optimal, what replacement reward loop makes that new behavior pay, and whether the repair recommendation is a structural fix that makes the old answer stop working because the old dominant line stops paying.

## Core Principle

A decision loop is healthy when pressure changes over time. Stress it by phase, find the collapse point, and fix the structure instead of padding with more content.

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
- Put the collapse signal, collapse witness, stop condition, break point, and structural witness before explanation, then reject surface excitement, first-hour novelty, not just phase explanation, and not just pacing cover.
- Treat not MVP scope cutting and not detailed numeric balancing as guardrails, not excuses for a weak decision.
- Keep weak decision, midgame autopilot, fake variation, shallow reward inflation, the same dominant line, and the same read visible enough to reject them as false fixes in the decision landscape, and state when reward, information, or cost changed in name only while the old answer still works.
- Demand a repair recommendation with a structural fix that is not just numeric tuning, changes read, tradeoff, or consequence, names the dominant line, says what old answer stops working because of the reward, information, or cost shift, what new answer becomes correct because of that shift, what reward, information, or cost changed to cause that shift, why the old dominant line stops paying, how read changes because information changes, how tradeoff changes because cost changes, how consequence changes because reward changes, which reward loop currently trains the wrong habit, what player behavior must disappear, what wrong habit stops paying, what right habit should replace it, what replacement behavior must become optimal, what replacement reward loop makes that replacement behavior pay, and how the decision landscape rule changes before balance values are tuned before you call the loop fixed.

1. **Define the Current Loop Shape**
   - Frame: Use this step to map the wrong habit, the intended right habit, and the pressure that should separate them.
   - Stress Test: What does the player observe, decide, do, receive, and repeat?
   - Watch: Map observe, decide, act, resolve, reward, and next-choice trigger.
   - Write: Loop under test with choice, feedback structure, and repeat trigger.
   - Reinforce / Repair: Rewrite the loop as choice -> feedback -> reward -> next choice.
   - Break If: The loop description lists activities but not the repeated decision.

2. **Test the First-Hour Hook**
   - Frame: Use this step to map the wrong habit, the intended right habit, and the pressure that should separate them.
   - Stress Test: Why would a new player understand and repeat this decision in the first hour? Name the stop condition before proposing more content.
   - Watch: Stress readability, immediate stakes, cause-effect feedback, and reason to repeat.
   - Write: First-hour performance with hook, confusion risk, and boredom risk.
   - Reinforce / Repair: Expose a meaningful tradeoff or readable consequence earlier.
   - Break If: The first hour works only because the premise is fresh.
   - Check: Reject surface excitement, first-hour novelty, and not greenlighting the loop if the first-hour pressure still hides a weak decision; name the collapse witness before phase explanation or pacing cover.

3. **Test Midgame Sustainability**
   - Frame: Use this step to map the wrong habit, the intended right habit, and the pressure that should separate them.
   - Stress Test: What prevents the midgame from flattening once the basics are understood? Name the stop condition before proposing more content.
   - Watch: Inspect constraints, tradeoffs, variation quality, and dominant-option risk. Name the counterpressure, variation audit, read shift, tradeoff change, consequence change, why the old dominant line stops paying, and adaptation test before content gets added.
   - Write: Midgame pressure with tradeoff change, variation quality, and autopilot risk.
   - Reinforce / Repair: Add state changes that force adaptation, not just larger numbers.
   - Break If: Midgame content changes labels while decisions stay identical.
   - Check: Name the dominant strategy, the midgame autopilot risk, the missing counterpressure, and whether the variation audit changes read, tradeoff, or consequence; if the same dominant line still wins, the same answer survives under a new label, the same read under a new label survives, the same consequence under a new label survives, the old answer still works, the new answer never becomes correct, or reward, information, or cost changed in name only while the old dominant line still pays, reject it as fake variation until a reward, information, or cost shift kills the old answer, the old dominant line stops paying, and a new answer becomes correct.

4. **Test Late-Game Expansion or Mutation**
   - Frame: Use this step to map the wrong habit, the intended right habit, and the pressure that should separate them.
   - Stress Test: Test whether lategame mastery reveals a deeper problem or solves the game away.
   - Watch: Name the expansion, mutation, or collapse point that appears at mastery.
   - Write: Late-game performance with evolution demand and collapse point.
   - Reinforce / Repair: Introduce risk, asymmetry, or pressure that meets mastery.
   - Break If: Mastery removes the game instead of changing the problem.
   - Check: Confirm late-game mastery creates a new decision problem instead of pure throughput, pacing cover, reward inflation, or a solved-state witness with no structural response and no right-habit replacement.

5. **Look for Solved States**
   - Frame: Use this step to map the wrong habit, the intended right habit, and the pressure that should separate them.
   - Stress Test: Test which solved state a strong player would repeat until the loop becomes stale.
   - Watch: Describe the dominant strategy and the reward, cost, or timing pattern that creates it. Reject any fix that only widens content, only tunes numbers, only softens pacing, or keeps the same dominant line without changing pressure. Name the landscape rule that changes before balance values are tuned and why numeric-only tuning leaves the old dominant line profitable.
   - Write: Solved-state risk with cause and counterpressure.
   - Reinforce / Repair: Add structural counterpressure instead of another option.
   - Break If: The solved state is dismissed as player preference.
   - Check: Break the dominant strategy with a structural fix and repair recommendation, reject numeric-only tuning or content-only padding, call out when numeric-only tuning keeps the same dominant line still winning, the same read still solving, the same consequence structure still paying out, the old dominant line still profitable, or the old read still intact, and change the decision landscape rule before balance values are tuned so the old answer stops working before balance values are tuned and a new answer becomes correct.

6. **Audit Variation and Reinforcement**
   - Frame: Use this step to map the wrong habit, the intended right habit, and the pressure that should separate them.
   - Stress Test: Test whether variation quality changes read, tradeoff, consequence, or adaptation.
   - Watch: Audit variation quality and reinforcement so the decision loop trains the intended behavior. Reject any fix that only widens content, only tunes numbers, only softens pacing, or keeps the same dominant line without changing pressure. Call out variation that does not change decisions, keeps the same read, preserves the same dominant line, hides the missing behavior shift, or leaves the old dominant line paying under a renamed reward loop.
   - Write: Variation quality and reinforcement recommendations.
   - Reinforce / Repair: Reward adaptation, timing, state-reading, or expressive choices directly.
   - Break If: Rewards teach efficient autopilot while the design claims expressive play.
   - Check: Reinforce the intended behavior, map wrong habit to right habit, name the behavior shift, say which reward loop currently trains the wrong habit, say what player behavior must disappear, say what replacement behavior must become optimal, say what replacement behavior becomes optimal because of the replacement reward logic, say what replacement reward loop makes the right habit profitable, reject fake variation, reject variation that does not change decisions, keeps the same dominant line still winning, keeps the same read, leaves the old answer working, or leaves the old behavior paying, and reject any repair that only improves throughput.

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

- Gate: Keep the audit on collapse witness, structural repair, dominant strategy, and reinforcement before anyone reaches for extra content.
- Hard fail any solved-state repair that keeps the same dominant line, the same read, the same consequence structure, or the old answer alive inside the same decision landscape before balance values are tuned.
- Hard fail any variation pass that names variation but keeps the same dominant line, the same read, the same consequence, or never says what old answer stops working and what new answer is required.
- Check whether first-hour novelty is masking a weak decision before the loop gets greenlit.
- Check whether the decision loop is readable in the first hour before novelty wears off.
- Check whether first hour midgame and lategame differ for the right reason instead of throughput-only inflation.
- Check whether midgame autopilot is appearing because the loop lost counterpressure and adaptation.
- Check whether lategame pressure creates a new decision problem instead of throughput-only mastery.
- Check whether solved state is concrete enough to name, trigger, and attack.
- Check whether fake variation, shallow reward inflation, or content padding are being mistaken for repair.
- Check whether the repair changes pressure inside the decision loop instead of adding softer content or softer compensation.
- Check whether the repair recommendation is not just numeric tuning, not just more content, not just phase explanation, and not just pacing cover.
- Check whether solved-state repair changes the decision landscape instead of leaving the same read, tradeoff, or consequence alive.
- Check whether the variation audit changes read, tradeoff, consequence, or dominant line instead of renaming the same answer.
- Check whether reinforcement teaches intended behavior instead of rewarding autopilot, safe throughput, or the wrong habit.
- Check whether reinforcement maps wrong habit to right habit, names the intended behavior shift, and rejects throughput-only mastery.
- Check whether the stop condition, collapse witness, and break point appear together as the structural witness for repair.
- Check whether the audit maps the wrong habit to the intended right habit, names the current reward loop, and states what player behavior must disappear instead of only praising faster throughput or keeping the same read.
- Hard fail variation named but same dominant line, same read, or same consequence under a new label.
- Hard fail the same dominant line still wins under a new label, the same answer survives under a new label, the same read under a new label, or the same consequence under a new label.
- Hard fail variation where reward, information, or cost changed in name only, the old answer still works, the old dominant line still pays, or the new answer never becomes correct.
- Hard fail habit mapping named but reward loop unchanged, the reward loop currently trains the wrong habit, the wrong habit still pays, the replacement reward loop is unnamed, or replacement behavior never becomes optimal.
- Hard fail solved-state repair named but decision landscape unchanged before balance values are tuned, the same dominant line still wins, the same read still solves, the same consequence structure still pays out, the old dominant line stays profitable, the old answer still works, or the new answer never becomes correct.
- Check whether a named stop condition also includes a concrete collapse witness and a break point the player can observe.
- Check whether variation does not change decisions, keeps the same dominant line, preserves the same read under a new label, or never says why the old dominant line stops paying and why the new answer becomes correct.
- Check whether reinforcement names what reward loop currently trains the wrong behavior, what replacement reward loop makes the right habit profitable, and what replacement behavior must become optimal.
- Check whether solved-state repair says numeric-only tuning keeps the same dominant line, the same read, the same consequence structure, and the old dominant line profitable until the decision landscape rule changes.
- Check whether every repair recommendation names a structural fix instead of numeric-only tuning, content-only padding, pacing-only relief, or throughput-only mastery.

## Output Format

Keep the deliverable focused on collapse point, solved state, repair move, and the next pressure test.

```markdown
## Reinforcement Check
- Write: what behavior the rewards teach and whether they train autopilot.
- Strong: Good: Reinforcement Check names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Reinforcement Check stays abstract, repeats the prompt, or leaves the field as a vague summary.
- Guardrail: State whether the loop teaches the wrong habit, throughput only, or the intended behavior under pressure.
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
- Guardrail: Name the dominant strategy, the counterpressure, and the move that punishes repeated safe choices.

## Variation Quality
- Write: whether variation changes decisions, not just surface variation or cosmetic options.
- Strong: Good: Variation Quality names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Variation Quality stays abstract, repeats the prompt, or leaves the field as a vague summary.
- Guardrail: Reject fake variation and keep only changes that alter read, tradeoff, consequence, or adaptation.

## Reinforcement Recommendations
- Write: reinforcement recommendations that reward adaptation, state-reading, or expressive timing.
- Strong: Good: Reinforcement Recommendations names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Reinforcement Recommendations stays abstract, repeats the prompt, or leaves the field as a vague summary.
- Guardrail: Avoid shallow reward inflation; reward state-aware adaptation and change incentive structure instead.

```

## Common Pitfalls: Collapse Patterns and Repairs

Treat reinforcement that leaves the wrong habit alive, keeps the same read or dominant line, never says which reward loop currently trains it, never says what wrong habit stops paying, never says what player behavior must disappear, never says what replacement reward loop makes the right habit profitable, or never names the behavior shift as a failed repair.

- Use these failure patterns to pressure-test lategame, variation quality, solved state, and reinforcement before adding content.
- Pattern index: Novelty-Only Start, Midgame Autopilot, Progression Without New Problems, Cosmetic Options, Dominant Strategy, Rewarding Autopilot.
- Repair moves: expose meaningful tradeoffs in the first hour, add state changes that force adaptation, add structural counterpressure, reward the intended behavior directly.

### Novelty-Only Start
- Symptom: Early play only works because the premise is fresh, not because the decision is clear.
- Cause: The first-hour hook never established readable pressure.
- Correction: Raise the stakes and feedback around the core choice, call the weak decision directly, and do not greenlight a repair that only adds more content.

### Midgame Autopilot
- Symptom: The player keeps repeating the same answer while the game only changes labels or numbers.
- Cause: Midgame added volume without adding new constraints.
- Correction: Introduce structural counterpressure that forces adaptation, changes the read, tradeoff, or consequence, makes the old answer stop working, makes a new answer become correct, and maps the wrong habit to the right habit instead of rewarding simple efficiency scaling.

### Variety Without Strategic Consequence
- Symptom: The game offers more variants, but they do not change read, tradeoff, or consequence.
- Cause: Variation was used as surface freshness instead of decision mutation.
- Correction: Cut cosmetic variation, call fake variation by name, reject any variation that does not change decisions or keeps the same read, same consequence, or dominant line, say what old answer stops working, what new answer becomes required, what reward, information, or cost changed to cause that shift, and what reward, information, or cost shift kills the old answer, and keep only the variants that force a new read, tradeoff, or consequence.
- Fake version: Variation named, but the same dominant line still wins, the same answer survives under a new label, the same read survives under a new label, and the same consequence still survives under a new label.
- Structural replacement: Change reward, information, or cost so the old answer stops working because that shift kills the old answer, the old dominant line stops paying, a new answer becomes required, and the variation changes read, tradeoff, or consequence.

### Mastery Removes the Game
- Symptom: Late play collapses into rote execution or a dominant route.
- Cause: Mastery widened throughput without creating a new decision problem.
- Correction: Change the pressure landscape so mastery unlocks new tradeoffs instead of solving the loop forever.

### Wrong Behavior Training
- Symptom: The reward structure favors autopilot even though the design claims expression or adaptation.
- Cause: Reinforcement was tuned for throughput rather than the intended behavior.
- Correction: Map the wrong habit to the right habit, name the intended behavior shift, state which reward loop currently trains the wrong behavior, say what player behavior must disappear, say what replacement behavior must become optimal, say what reward, information, or cost shift causes that behavior shift, rewrite the replacement reward logic so the wrong habit stops paying and the right habit becomes the profitable answer, move rewards onto that right habit, and strip reward from throughput-only or safe dominant routines.
- Fake version: A fake reinforcement loop keeps rewarding the same safe behavior, so the wrong habit survives, the wrong habit still pays, the reward loop currently trains the wrong habit, the old behavior still pays, and the review names the right habit without changing the reward logic.
- Structural replacement: Name the reward loop currently training the wrong habit, remove reward from that behavior, rewrite the replacement reward logic so the old behavior stops paying, and make the replacement behavior become optimal because the new pressure makes the right habit the profitable answer.

### Numeric-Only Repair
- Symptom: The loop identifies a solved state, then proposes softer numbers or reward tuning while the same decision still wins.
- Cause: The repair changed intensity instead of changing the pressure relationship.
- Correction: Reject numeric-only or content-only fixes, write a structural repair recommendation, call out when numeric-only tuning keeps the same dominant line still winning, the same read still solving, and the same consequence structure still paying out, and rewrite the fix so the decision landscape changes before balance values are tuned and the old answer stops working before balance values are tuned.
- Fake version: Numeric-only fake fix: softer numbers still keep the same dominant line still winning, the same read still solving, the same consequence structure still paying out, and the old dominant line still profitable.
- Structural replacement: Structural replacement: change the decision landscape rule first so the old answer stops working before balance values are tuned, then tune balance values after the new answer becomes correct.

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
