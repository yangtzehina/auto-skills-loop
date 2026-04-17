---
name: simulation-resource-loop-design
description: Systems brief for visible tradeoffs, counterpressure, costly recovery, and fantasy fit.
---

# simulation-resource-loop-design

Map the pressure web before you balance any single resource in isolation.

## Overview

Frame the system as a visible tension web with costly recovery, upkeep drag, overflow risk, stockpile pressure, and hoarding traps, not as a long list of resources.

## Core Principle

A resource loop is a visible pressure web. Variables matter only when they create choices, feedback, recovery costs, and emotional fantasy alignment.
Positive and negative loops must be paired; snowballing alone is not a design.

## When to Use

- The user asks for economy, survival, management, strategy, or simulation-loop design.
- A resource loop has too many currencies, no pressure, runaway snowballing, or unclear agency.
- The design needs a first-pass model before tuning numbers or implementing simulation code.

## When Not to Use

- The user only wants numeric balancing values.
- The game has no persistent state or repeated resource decisions.
- The task is primarily monetization pricing or engine code.

## Inputs

- Player goal, session rhythm, and emotional fantasy.
- Candidate resources, sinks, converters, producers, caps, decay, and visible states.
- Known failure states, recovery expectations, and snowball risks.

## Default Workflow

1. **Map the Variable Web**
   - Frame: Use this step to map the visible pressure before tuning any single variable.
   - Map: Which variables are visible enough to guide a player decision?
   - Trace: Map resources, sinks, converters, buffers, caps, and player-visible signals.
   - Record: Variable web with resources, sinks, converters, buffers, and signals.
   - Watch For: The variable web is only hidden meters or decorative resources.
   - Correct: Cut or connect each variable to a player-facing decision.
   - Check: Confirm the pressure web is not just one simple currency with nicer labels.
   - Must include: variable web, resources, sinks, converters, player-facing.

2. **Define Each Variable's Role**
   - Frame: Use this step to give every kept variable a player-facing role.
   - Map: What decision does this variable create or constrain?
   - Trace: Classify each variable as source, sink, converter, buffer, cap, signal, cost, or pressure.
   - Record: Variable role table with role, decision, and visibility.
   - Watch For: Variables have names but no behavioral role.
   - Correct: Cut variables without a role or merge duplicated pressures.
   - Must include: variable role, source, sink, converter, pressure.

3. **Map the Pressure Relationships**
   - Frame: Use this step to expose cause, effect, and warning before commitment.
   - Map: Which pressure relationship creates a meaningful tradeoff over time?
   - Trace: Write cause/effect pairs, timing, and player-visible warning signs.
   - Record: Pressure relationships with cause, effect, timing, and warning signal.
   - Watch For: Pressure punishes the player without readable warning.
   - Correct: Expose cause and effect through UI, timing, or predictable state changes.
   - Must include: pressure relationships, cause, effect, tradeoff, visible warning.

4. **Identify Primary Decision Tensions**
   - Frame: Use this step to name the tradeoff the player cannot optimize away.
   - Map: What can the player never maximize all at once?
   - Trace: Name tensions, viable responses, and what each response sacrifices.
   - Record: Decision tensions with tradeoff, pressure, and viable responses.
   - Watch For: The player can optimize everything with one dominant path.
   - Correct: Add opportunity cost, incompatible goals, or non-convertible pressure.
   - Must include: decision tensions, tradeoff, viable responses, opportunity cost.

5. **Design Positive and Negative Feedback Loops**
   - Frame: Use this step to pair compounding force with a visible brake.
   - Map: What compounds, and what counterpressure prevents runaway success?
   - Trace: Trace positive loops, negative loops, brakes, decay, maintenance, and risk.
   - Record: Positive and negative loops with compounding force and counterpressure.
   - Watch For: Only positive loops exist, creating runaway snowballing.
   - Correct: Add decay, scrutiny, maintenance, scarcity, or asymmetric risk.
   - Must include: positive loop, negative loop, counterpressure, runaway.

6. **Design Failure and Recovery**
   - Frame: Use this step to keep recovery costly without making it hopeless.
   - Map: How does the player notice failure early, recover, and keep a lasting cost?
   - Trace: Define early warning, recovery action, and consequence that remains after recovery.
   - Record: Failure recovery with warning, recovery action, and lasting consequence.
   - Watch For: Recovery either erases consequences or becomes mathematically impossible.
   - Correct: Add costly recovery tools and earlier warning signs.
   - Must include: failure recovery, early warning, lasting consequence, death spiral.

7. **Align With Emotional Fantasy**
   - Frame: Use this step to make the pressure web reinforce the intended fantasy.
   - Map: Does the loop make the player feel the fantasy through choices and consequences?
   - Trace: Check whether scarcity, abundance, care, panic, mastery, or planning emerges from the loop.
   - Record: Emotional fantasy alignment with intended feeling and mismatch to fix.
   - Watch For: The spreadsheet balances while the emotional fantasy disappears.
   - Correct: Rewrite variables that contradict the intended fantasy even if the math works.
   - Must include: emotional fantasy, resource loop, mismatch, intended feeling.

## Analysis Blocks

- Cut repeated map framing and keep only the pressure relationship the player can read and act on.
- Reduce the model to a few strong tensions, stockpiles, warehousing, and upkeep drag; only include a variable if it changes player behavior.
### Variable Web
- Signal: What must `Variable Web` make visible to the user or builder?
- Output: Variable Web, Variable Roles

### Pressure Relationships
- Signal: What must `Pressure Relationships` make visible to the user or builder?
- Output: Pressure Relationships, Primary Decision Tensions

### Feedback Loops
- Signal: What must `Feedback Loops` make visible to the user or builder?
- Output: Positive and Negative Loops, Failure Recovery, Emotional Fantasy Alignment

## Output Format

Prefer a short field set that forces variable role, key tension, dominant risk, and recovery cost.

```markdown
## Variable Web
- Record: Write core resources pressures, time money energy reputation relationships, and every player-facing signal.
- Guardrail: Keep only variables that change player behavior or reveal visible pressure.

## Pressure Relationships
- Record: Write cause, effect, timing, visible warning, gain sources, loss sources, and tradeoff.
- Guardrail: Show the cost, warning, and tradeoff before the player commits.

## Variable Roles
- Record: Write source, sink, converter, buffer, cap, signal, pressure, and what each enables or restricts.

## Primary Decision Tensions
- Record: Write what the player can never maximize all at once and which choices hurt in an interesting way.
- Guardrail: Name what the player cannot maximize all at once.

## Positive Loop
- Record: Write positive loops, conversion, amplification, threshold, runaway risk, and reward pressure.

## Negative Loop
- Record: Write negative counter loops, decay, scarcity, maintenance, and counter-pressure.

## Positive and Negative Loops
- Record: Write the loop pair: what compounds, what corrects it, and where the brake appears.
- Guardrail: Show what compounds and what brakes it in the same read.

## Failure Recovery
- Record: Write failure and recovery, early warning, recovery action, lasting cost, and punishment without agency risk.
- Guardrail: Keep recovery playable, but preserve cost and consequence.

## Resource Loop
- Record: Write how the resource loop creates player-facing tradeoffs rather than one simple currency.

## Emotional Fantasy
- Record: Write aspiration and consequence, intended feeling, mismatch, and emotional or structural backlash.

## Emotional Fantasy Alignment
- Record: Write emotional fantasy alignment: how scarcity, abundance, panic, mastery, or planning emerges.
- Guardrail: Tie the intended feeling to the actual pressure math.

## Design Recommendations
- Record: Write design recommendations that cut decorative resources and strengthen few strong tensions.

```

## Quality Checks

- Gate: Keep the loop readable through visible pressure, costly recovery, and fantasy fit before smoothing the numbers.
- Split the checks into visible pressure, costly recovery, dominant-currency guard, and fantasy fit so the loop does not slide back into a generic template.
- Use extra non-generic headings only when they tighten pressure readability and compactness at the same time.
### Visible Pressure
- Check whether pressure is visible before commitment and early enough for planning.
- Check whether pressure relationships create readable tradeoffs instead of hidden bookkeeping.

### Costly Recovery
- Check whether failure recovery keeps a cost instead of collapsing into a flat reset.
- Check whether recovery preserves consequence, readability, and fantasy at the same time.

### Dominant Currency Guard
- Check whether one resource can bypass the intended tension web.
- Check whether positive and negative loops counterweight each other instead of feeding one dominant route.

### Fantasy Fit
- Check whether emotional fantasy still matches the pressure math.
- Check whether every kept variable still changes player behavior inside the pressure web.

## Common Pitfalls: Loop Failures and Corrections

Keep cheap recovery and hidden pressure as first-class failures, then repair readability and cost before adding new variables.

- Use these failure patterns to check variable web clarity, pressure relationships, and failure recovery without collapsing into one simple currency, isolated meters, mostly content writing, or anything weaker than a few strong tensions; only include a variable if it changes player behavior.
- Pattern index: Decorative Resources, Variable Web Sprawl, No Real Tradeoff, One Dominant Currency, Positive-Loop Runaway, Runaway Snowball, Death Spiral, Punishment Without Agency, Hidden Pressure Relationships, Emotionless Resource Loop, Fantasy-System Mismatch.
- Repair moves: connect each variable to a visible decision, add non-convertible pressure or opportunity cost, add counterpressure to success, add costly recovery with earlier warnings, align variables with intended feeling.

### Decorative Resources
- Symptom: The loop lists resources, but they do not create a player-facing tradeoff.
- Cause: Variables were added for flavor or spreadsheet depth rather than decision pressure.
- Correction: Reduce currencies and cut decorative resources until each remaining variable changes player behavior.

### No Real Tradeoff
- Symptom: Pressure exists on paper, but the player still has one obviously correct answer.
- Cause: The pressure relationship never creates a real sacrifice.
- Correction: Make pressure visible and tighten tradeoffs so the player must give something up.

### One Dominant Currency
- Symptom: A single resource or loop answers every problem.
- Cause: Counterpressure exists on paper but never bites in play.
- Correction: Add a brake, opportunity cost, or dependency that the dominant currency cannot bypass.

### Positive-Loop Runaway
- Symptom: Success compounds into snowballing without a meaningful brake.
- Cause: Positive loops were tuned without a matching negative loop or cap.
- Correction: Pair the runaway loop with a counterpressure that stays visible during success.

### Punishment Without Agency
- Symptom: Pressure punishes the player, but the recovery path offers no meaningful response or tradeoff.
- Cause: The loop preserved pain without preserving agency.
- Correction: Add readable warning, viable responses, and recovery with cost instead of a consequence-free reset or pure punishment.

### Fantasy-System Mismatch
- Symptom: The spreadsheet balances, but the player-facing pressure produces the wrong feeling.
- Cause: Variables were optimized independently from the intended emotional rhythm.
- Correction: Rewrite the loop so the visible pressures reinforce the fantasy instead of flattening it.

### Hidden Pressure Relationships
- Symptom: Resources move in the background, but the player cannot read the pressure soon enough to plan around it.
- Cause: Signals were treated as bookkeeping instead of decision surfaces.
- Correction: Make pressure visible before the player commits so the cost, risk, or bottleneck can actually shape the next move.

### Cheap Recovery
- Symptom: Recovery resets pressure so cleanly that failure loses most of its cost, memory, or structural consequence.
- Cause: The loop is protecting comfort instead of preserving the meaning of failure and recovery.
- Correction: Keep recovery playable, but attach a visible cost, lost position, or delayed opportunity before tuning anything else.

## Decision Rules

- variable web has player-facing roles
- variables are player-facing
- pressure relationships create tradeoffs
- positive loop and negative loop both exist
- positive and negative loops balance rhythm
- failure recovery keeps cost
- emotional fantasy matches system pressure
- emotional fantasy matches resource math
- player-facing tradeoffs
- pressure web
- aspiration and consequence
- emotional or structural backlash

## Cut Rules

- cut decorative resources
- not one simple currency
- not isolated meters
- few strong tensions over many weak subsystems

## Worked Micro-Example

- Variable web with player-facing signals and roles.
- Pressure relationships and main decision tensions.
- Positive/negative loop pair plus failure recovery with cost.

## Voice Rules

- map
- tension
- loop
- correct
- player-facing pressure
