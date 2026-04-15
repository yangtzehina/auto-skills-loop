---
name: simulation-resource-loop-design
description: Design and diagnose simulation-style resource loops where multiple pressures such as time, money, reputation, relationships, risk, and emotional state must interact to create meaningful decisions.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [game-design, simulation, resources, systems, economy, pressure]
    category: game-design
    requires_toolsets: []
---

# Simulation Resource Loop Design

Use this skill when a game depends on **interacting pressures**, not just one simple currency or progression bar.

This skill is especially good for games where decisions are driven by tensions between things like:
- time
- money
- energy
- reputation
- relationships
- health
- stress
- fulfillment / emptiness
- visibility / danger
- freedom / obligation

This is a **system-tension design skill**.
It exists to make sure the player is not merely accumulating resources, but managing competing pressures that create meaningful tradeoffs.

## When to Use

Trigger this skill when:
1. The project is a life sim, management sim, strategy sim, tycoon, social simulation, or choice-heavy systemic game.
2. The user wants to design or debug a resource network rather than a single progression path.
3. The game needs stronger tension, consequences, or interdependence between systems.
4. The core fantasy depends on abundance in one dimension but scarcity in others.

## When Not to Use

Do not use this as the main skill when:
1. The direction still needs high-level greenlight judgment first.
2. The MVP has not yet identified its main loop.
3. The task is mostly content writing without needing system interaction design.

## Core Principle

Good simulation loops are not built on “more bars.”
They are built on **pressure relationships**.

A resource system becomes interesting when:
- gaining one thing threatens another
- relief in one area creates risk elsewhere
- short-term wins create long-term instability
- abundance amplifies responsibility rather than deleting tension

If resources do not push against each other, the system is probably flat.

## Default Workflow

### 1. List the Core Resources or Pressures

Identify the key variables that actually matter to player decisions.
Examples:
- money
- time
- labor
- inventory space
- public image
- trust
- family stability
- fatigue
- political capital
- boredom
- guilt
- loneliness

Do not include a variable just because it sounds realistic.
Only include it if it changes player behavior.

### 2. Define Each Variable’s Role

For each resource / pressure, answer:
- What does it enable?
- What does it restrict?
- How does the player gain it?
- How does the player lose it?
- Why does the player care right now?

If a variable has no real behavioral consequence, it is decorative.

### 3. Map the Pressure Relationships

Show how variables interact.
Common interaction types:
- **conversion** — money can buy time, but inefficiently
- **amplification** — fame increases opportunities and risk
- **decay** — relationships weaken without attention
- **threshold** — stress above X causes mistakes or penalties
- **feedback loop** — success brings scrutiny, scrutiny brings instability
- **substitution** — one resource can partially replace another at a cost

This is the heart of the skill.
The system must feel like a web, not a list.

### 4. Identify the Primary Decision Tensions

Ask:
- What choices hurt in an interesting way?
- What can the player never maximize all at once?
- What sacrifice patterns define the fantasy?
- What is the player tempted to over-optimize, and what punishes that?

A strong simulation loop usually has 2-4 recurring tensions that the player keeps revisiting.

### 5. Design the Main Feedback Loops

Separate positive and negative loops.

#### Positive loops
Reward success and create momentum.
Examples:
- wealth unlocks better tools
- reputation unlocks better deals
- good health improves productivity

#### Negative loops / counter-pressure
Stop the system from becoming trivial.
Examples:
- visibility creates public scrutiny
- more assets create maintenance burden
- overwork destroys relationships
- extreme efficiency causes burnout or loss of meaning

If only positive loops exist, the game becomes snowball accumulation.
If only negative loops exist, the game feels oppressive and static.

### 6. Define Failure, Drift, and Recovery

Interesting systems do not only reward optimization.
They also need:
- failure states or near-failure states
- drift toward instability
- recovery tools that cost something

Ask:
- What does structural imbalance look like?
- How does the player notice it early?
- Can the player recover, and at what price?

Recovery is important because otherwise the system becomes either too forgiving or too punishing.

### 7. Define What the Player Is Really Chasing

The visible resources are not always the true motivation.
Clarify whether the player is really chasing:
- survival
- dominance
- freedom
- prestige
- intimacy
- self-expression
- control
- meaning
- peace

The best simulation systems align the resource web with the emotional fantasy.

## Output Format

```md
# Simulation Resource Loop Design

## 1. Core Resources / Pressures
### Resource A
- Enables:
- Restricts:
- Gain sources:
- Loss sources:
- Why player cares:

## 2. Pressure Relationships
- A -> B:
- B -> C:
- C -> A:
- Main feedback loops:

## 3. Primary Decision Tensions
- Tension 1:
- Tension 2:
- Tension 3:

## 4. Positive Loops
-

## 5. Negative / Counter Loops
-

## 6. Failure and Recovery
- Early warning signs:
- Failure shape:
- Recovery tools:
- Cost of recovery:

## 7. Emotional / Fantasy Alignment
- What the player thinks they want:
- What the system actually pressures them to choose:

## 8. Design Recommendations
- What to strengthen:
- What to simplify:
- What to prototype next:
```

## Common Failure Patterns to Catch

### Decorative Resources
Bars exist, but they do not change choices.

### No Real Tradeoff
The player can optimize everything at once, so the system becomes bookkeeping.

### One Dominant Currency
All other variables collapse into a single best resource, killing multidimensional tension.

### Positive-Loop Runaway
Success removes all hardship and makes the system less interesting over time.

### Punishment Without Agency
The player suffers penalties but lacks meaningful recovery choices.

### Fantasy-System Mismatch
The numbers say one thing, but the emotional fantasy promises another.

## Style Rules

- Think in relationships, not isolated meters.
- Push toward player-facing tradeoffs.
- Preserve both aspiration and consequence.
- Prefer a few strong tensions over many decorative subsystems.
- When possible, tie material success to emotional or structural backlash.

## Handoff

Common previous skills:
- **game-direction-evaluation**
- **concept-to-mvp-pack**
- **decision-loop-stress-test**

Use this skill when the project’s main challenge is no longer “what is the idea?” but “what pressure web makes the idea actually interesting?”

## Short Reminder

A simulation becomes compelling when the player is rich in one thing and dangerously poor in another.
