---
name: decision-loop-stress-test
description: decision-loop-stress-test methodology; use when the task needs a domain-specific workflow, output template, quality checks, and pitfalls.
---

# decision-loop-stress-test

Use this skill when the user needs a domain-specific game-design method, not a generic methodology shell.

## Overview

Read the user request as raw design material, then convert it into expert game-design decisions, templates, checks, and failure modes.

## Core Principle

A decision loop is healthy when players can read the state, choose between real alternatives, see consequences, and adapt. Stress testing asks where that loop collapses across first hour, midgame, lategame, solved state, variation quality, and reinforcement.

## When to Use

- The user asks whether a game loop has meaningful decisions.
- A prototype feels repetitive, obvious, solved, random, or full of cosmetic options.
- The team needs a diagnosis across first hour, midgame, and lategame rather than a single gut check.
- The output should identify one or two targeted interventions.

## When Not to Use

- The task is pure economy tuning with telemetry already available.
- The user only wants new mechanic ideas without evaluating an existing loop.
- The choice is narrative-only and has no mechanical consequence to inspect.
- The problem is execution polish rather than decision structure.

## Inputs

- Current decision loop and repeated player choice.
- Information visible before the player chooses.
- Costs, risks, rewards, timing, and feedback after each choice.
- Known dominant strategies, boring phases, confusing phases, or player complaints.

## Default Workflow

### 1. Define the Current Loop Shape

- Map observe, decide, act, resolve, reward, and next-choice trigger.
- Identify the decision loop the player repeats, not every action in the game.
- Name what the loop is supposed to train or make the player feel.

### 2. Test the First-Hour Hook

- Check whether a new player understands the choice quickly enough to care.
- Ask whether the first hour gives readable feedback and a reason to repeat the decision loop.
- Mark confusion, boredom, missing stakes, or fake choice before adding more systems.

### 3. Test Midgame Sustainability

- Check whether midgame constraints create new tradeoffs instead of merely increasing numbers.
- Judge variation quality by whether it changes decisions, not whether it changes surface content.
- Look for options that become mandatory, irrelevant, or equivalent once the player learns the loop.

### 4. Test Late-Game Expansion or Mutation

- Ask whether mastery creates new decisions or collapses into rote execution.
- Check whether lategame tools widen expression, deepen risk, or erase pressure.
- Name the late-game mutation the loop needs if the first-hour pattern cannot carry the whole game.

### 5. Look for Solved States

- Describe the dominant strategy that would make the decision loop stale.
- Identify which information, reward, cost, or timing pattern creates the solved state.
- Prefer targeted counterpressure over simply adding more options.

### 6. Audit Variation Quality

- Separate meaningful variation from cosmetic swaps, stat bumps, or random noise.
- Check whether each variation changes read, tradeoff, consequence, or adaptation.
- Remove variations that only increase content count.

### 7. Audit Reinforcement

- Confirm rewards teach the intended behavior instead of rewarding autopilot.
- Check whether the loop reinforces expression, mastery, caution, aggression, or optimization as intended.
- Name any reward that contradicts the stated player fantasy.

## Output Format

```markdown
## Current Loop Shape
- Observe: <fill in>
- Decide: <fill in>
- Act: <fill in>
- Resolve: <fill in>
- Reward: <fill in>
- Next-choice trigger: <fill in>

## First-Hour Hook
- Readability: <fill in>
- Reason to repeat: <fill in>
- Confusion or boredom risk: <fill in>

## Midgame Sustainability
- New constraint: <fill in>
- Tradeoff change: <fill in>
- Variation quality: <fill in>

## Late-Game Evolution
- Expansion: <fill in>
- Mutation: <fill in>
- Collapse point: <fill in>

## Solved State Risk
- Dominant strategy: <fill in>
- Cause: <fill in>
- Counterpressure: <fill in>

## Variation Quality
- Meaningful changes: <fill in>
- Cosmetic changes: <fill in>
- Cuts: <fill in>

## Reinforcement Check
- Behavior rewarded: <fill in>
- Fantasy alignment: <fill in>
- Fix: <fill in>

```

## Quality Checks

- First hour, midgame, and lategame must differ in the pressure they put on the decision loop.
- Variation quality changes decisions, not just content labels.
- The solved state is concrete enough to design against.
- Reinforcement must teach intended behavior instead of rewarding autopilot.
- The decision loop risk is specific enough to change the next playtest.
- The recommendation changes the next playtest, not just the wording of the critique.
- The output must use domain-specific section titles and decisions, not only generic planning language.
- Another agent should be able to apply the result without rereading the original prompt.

## Common Pitfalls

- Cosmetic options: counting menu choices that do not change consequence.
- Surface variation: adding enemies, cards, or levels that ask the same decision.
- Dominant strategy denial: noticing a solved state but calling it player preference.
- Rewarding autopilot: claiming expressive decisions while the reward optimizes one rote behavior.
- First-hour tunnel vision: testing the hook while missing midgame or lategame collapse.
- Prompt echo: repeating the request instead of turning it into domain actions.
- False completion: passing shape checks while the expert workflow is still missing.
