---
name: decision-loop-stress-test
description: Stress test a game’s decision loop across early, mid, and late play to identify where engagement, clarity, variety, or tension is most likely to collapse.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [game-design, loop, retention, pacing, pressure-test, progression]
    category: game-design
    requires_toolsets: []
---

# Decision Loop Stress Test

Use this skill when a game already has a candidate core loop and the question becomes:

- Does this loop hold up beyond the pitch?
- Why would the player still care after the first 10 minutes?
- Where does the structure become repetitive, solved, or hollow?
- What pressure points need reinforcement before production expands?

This is a **sustainability and tension** skill.
It is not about greenlighting the theme. It is about testing whether the loop survives time.

## When to Use

Trigger this skill when:
1. A promising direction or MVP loop already exists.
2. The user wants to know whether the loop survives first hour, midgame, and later play.
3. There are concerns about repetition, shallow decisions, solved states, or weak retention.
4. The team wants to identify where to add variation, escalation, or new pressure.

## When Not to Use

Do not use this as the main skill when:
1. The concept still lacks a basic loop definition.
2. The problem is mainly MVP scope cutting, not endurance testing.
3. The need is detailed numeric balancing rather than structural pressure analysis.

## Core Principle

A loop fails long before players say “I’m bored.”
It usually fails because one of these happens:
- the optimal strategy becomes too obvious
- feedback becomes flat
- tradeoffs stop being painful
- variety stops producing new decisions
- progression stops changing the decision landscape

Your job is to find where that collapse begins.

## Default Workflow

### 1. Define the Current Loop Shape

First restate the loop clearly:
- what decision the player makes
- what uncertainty exists
- what resources or states move
- what the player is trying to optimize

If the loop is not explicit, the stress test cannot be trusted.

### 2. Test the First-Hour Hook

Ask:
- What immediately feels interesting?
- What meaningful decision appears early enough?
- Is there a readable cause-and-effect chain?
- Does the player feel agency, curiosity, or growth quickly?

Common first-hour failure modes:
- too much setup before meaningful choice
- feedback too abstract to feel satisfying
- novelty carries the experience more than the loop itself

### 3. Test Midgame Sustainability

Ask:
- What keeps the player making interesting choices after initial learning?
- What new tensions appear once the basics are understood?
- Does the player face compounding tradeoffs or just larger numbers?
- Are there multiple viable approaches, or does one path dominate?

Common midgame collapse:
- pattern solved too early
- fake variety with same underlying decision
- progression makes the game easier without creating new tension

### 4. Test Late-Game Expansion or Mutation

Ask:
- How does the loop deepen, mutate, or recombine later?
- What prevents the game from flattening into maintenance?
- Does mastery reveal more interesting problems or remove them?

A good late game does not merely repeat the loop at bigger scale.
It usually introduces deeper constraints, more interacting systems, or more painful tradeoffs.

### 5. Look for Solved States

Explicitly check whether the player can “figure out the answer” too early.
Look for:
- dominant strategy
- one obviously best upgrade route
- one clearly best resource conversion
- low cost for wrong choices
- weak downside pressure

If mastery erases tension too quickly, the loop is fragile.

### 6. Check Variation Quality

Not all variation matters.
Separate:
- cosmetic variation
- content variation
- state variation
- decision variation

Highest value comes from **decision variation**: changes that force the player to rethink.
If variation only changes flavor, say so.

### 7. Recommend Reinforcements

End by identifying:
- where the loop is strongest
- where it collapses first
- what reinforcement would help most

Typical reinforcement categories:
- stronger resource tension
- sharper downside / risk
- more asymmetric options
- delayed consequences
- stronger state carryover
- branching goals
- more meaningful uncertainty

## Output Format

```md
# Decision Loop Stress Test

## 1. Loop Under Test
- Core decision:
- Feedback structure:
- Progression driver:

## 2. First-Hour Performance
- What works:
- What feels weak:
- Main risk:

## 3. Midgame Performance
- What sustains interest:
- Where repetition starts:
- Main risk:

## 4. Late-Game Performance
- What expands:
- What flattens:
- Main risk:

## 5. Solved-State Risks
- Dominant strategy:
- Shallow optimization:
- Weak penalties:

## 6. Variation Quality
- Cosmetic:
- Content:
- State:
- Decision:

## 7. Reinforcement Recommendations
- Most urgent fix:
- Secondary fix:
- Suggested next prototype test:
```

## Common Failure Patterns to Catch

### Novelty-Only Start
The first session works because the premise is new, not because the decisions are strong.

### Midgame Autopilot
The player learns a stable routine and stops making real tradeoffs.

### Progression Without New Problems
The player gets bigger numbers, but the structure does not become deeper.

### Variety Without Strategic Consequence
Different content appears, but it does not change how the player thinks.

### Mastery Removes the Game
The better the player gets, the less interesting the decisions become.

## Style Rules

- Focus on decision quality, not surface excitement.
- Be specific about when and why collapse happens.
- Distinguish shallow repetition from healthy mastery.
- Prefer structural fixes over content padding.

## Handoff

Common previous skills:
- **game-direction-evaluation**
- **concept-to-mvp-pack**

Common next skill:
- **simulation-resource-loop-design** when the loop needs stronger pressure, scarcity, or interlocking systems.

## Short Reminder

Do not ask only whether the loop is fun once.
Ask whether it is still interesting after the player understands it.
