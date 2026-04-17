---
name: concept-to-mvp-pack
description: Proof-driven brief for deciding the first playable, the hard cuts, and the first build target.
---

# concept-to-mvp-pack

Turn the proof into a first-playable package that can actually be built next.

## Overview

Lock the proof first, then shape the smallest build-ready pack around it.

## Core Principle

An MVP pack is the smallest honest proof of the player promise. It should make the core validation question falsifiable, keep the playable loop honest, and cut anything that hides learning.
Use the smallest honest loop as the unit of truth, then cut anything that does not support it.

## When to Use

- The user has a rough game concept and needs a scoped first build.
- The idea has too many mechanics, content hopes, or genre references competing for attention.
- The next useful output is a buildable MVP pack rather than a mood board or full design bible.

## When Not to Use

- The user only wants names, visual tone, lore, or freeform theme exploration.
- The project already has a locked vertical slice and needs production scheduling.
- There is not enough concept material to identify a player fantasy or loop.

## Inputs

- Concept premise and player fantasy.
- Target platform, session length, audience, and team or time constraints.
- Must-keep mechanics, inspirations, and features the user is tempted to include.

## Default Workflow

1. **Define the Core Validation Question**
   - Frame: Use this step to leave the next builder with a concrete pack, not a concept note.
   - Prove: What exactly must be proven, and what observation would prove the concept wrong?
   - Package: Core validation question with success evidence and failure evidence.
   - Do: Write the central design hypothesis in falsifiable language before choosing content.
   - Cut If: The question sounds like a slogan or could not fail in a short prototype.
   - Tighten: Rewrite it as a playtest observation that would force a redesign.
   - Must include: validation question, can fail, central design hypothesis.

2. **Identify the Minimum Honest Loop**
   - Frame: Use this step to leave the next builder with a concrete pack, not a concept note.
   - Prove: Can the loop be played with visible input, response, feedback, and repeat trigger?
   - Package: Smallest honest loop: input, response, feedback, repeat trigger.
   - Do: Name the player input, system response, visible feedback, and repeat trigger.
   - Cut If: The loop depends on future systems, scripted presentation, or invisible depth.
   - Tighten: Cut back to one playable interaction that can be tested immediately.
   - Must include: smallest honest loop, player input, system response, visible feedback, repeat trigger.

3. **Separate Must-Haves from Supports**
   - Frame: Use this step to leave the next builder with a concrete pack, not a concept note.
   - Prove: Which painful feature cut would make the MVP clearer instead of poorer?
   - Package: Feature cut table with Core, Support, Defer, and Cut buckets.
   - Do: Sort work into core, support, defer, and cut; keep only evidence-bearing features.
   - Cut If: Too many systems are called core and the MVP becomes a miniature vertical slice.
   - Tighten: Move polish, meta-progression, spectacle, and nonessential content to defer or cut.
   - Must include: feature cut, core, support, defer, cut.

4. **Define the Minimum Content Package**
   - Frame: Use this step to leave the next builder with a concrete pack, not a concept note.
   - Prove: How much content is enough to test the loop before content starts hiding uncertainty?
   - Package: Minimum content scope with test space, session length, success signal, and fail signal.
   - Do: Pick the smallest arena, encounter, toy set, scene, or run count that can produce evidence.
   - Cut If: Content volume is being used to make the concept look real instead of testable.
   - Tighten: Reduce to one strong test space and one measurable playtest signal.
   - Must include: minimum content, content scope, success signal, fail signal.

5. **Define What Is Out of Scope**
   - Frame: Use this step to leave the next builder with a concrete pack, not a concept note.
   - Prove: Which tempting ideas sound related but do not answer the validation question?
   - Package: Out-of-scope list with why excluded and re-entry condition.
   - Do: Write a concrete out-of-scope list with a re-entry condition for each deferred idea.
   - Cut If: Deferred features are vague enough to sneak back into the first build.
   - Tighten: Name the exact excluded work and the evidence required before it can return.
   - Must include: out of scope, scope creep, re-entry condition.

6. **Package the First Playable**
   - Frame: Use this step to leave the next builder with a concrete pack, not a concept note.
   - Prove: Could a builder start the first playable without rereading the original prompt?
   - Package: MVP package with build recommendation, playtest signal, and open assumptions.
   - Do: Assemble the validation question, loop, feature cut, content scope, risk, and first test.
   - Cut If: The pack feels polished but does not tell the team what to build first.
   - Tighten: Rewrite the package as the next work order plus the first player-facing test.
   - Must include: mvp package, build recommendation, playtest signal, open assumptions.

## Output Format

Keep the field list explicit: validation goal, minimum honest loop, core features, minimum content scope, required systems, explicitly out of scope, main production risks, and build recommendation.

Keep the field list explicit: validation goal, minimum honest loop, core features, minimum content scope, required systems, explicitly out of scope, main production risks, and build recommendation.

```text
## Minimum Content Package
- Write: minimum content scope, required systems, prototype first target, and the smallest session that can prove the loop; keep the minimum content scope, required systems, and the prototype first target explicit.
- Good: Minimum Content Package names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Minimum Content Package stays abstract, repeats the prompt, or leaves the field as a vague summary.
- Focus: Make this field handoff-ready so a builder can act immediately.

## Core Validation Question
- Write: the validation goal as a core question that can fail, with success criteria and failure evidence; keep the validation goal with success criteria and failure evidence explicit.
- Good: Core Validation Question names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Core Validation Question stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Smallest Honest Loop
- Write: player input, system response, visible feedback, and repeat trigger; keep the loop honest before adding content; keep the minimum honest loop with player input, system response, visible feedback, and repeat trigger explicit.
- Good: Smallest Honest Loop names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Smallest Honest Loop stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Feature Cut
- Write: must have, support, defer, cut for now, and why each cut protects testability; keep the core features, support, defer, and cut for now explicit.
- Good: Feature Cut names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Feature Cut stays abstract, repeats the prompt, or leaves the field as a vague summary.

## Out of Scope
- Write: the kill list: what stays out of scope, why it blocks scope creep, and what evidence would let it return; keep the explicitly out of scope with re-entry condition explicit.
- Good: Out of Scope names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: Out of Scope stays abstract, repeats the prompt, or leaves the field as a vague summary.

## MVP Package
- Write: the build recommendation, main production risks, first playable test, and open assumptions; keep the build recommendation, main production risks, and redesign trigger explicit.
- Good: MVP Package names the decision, evidence, consequence, and next action clearly enough to act on.
- Weak: MVP Package stays abstract, repeats the prompt, or leaves the field as a vague summary.

```

## Worked Micro-Example

- Validation Goal with pass/fail evidence.
- Minimum Honest Loop with player input, system response, feedback, and repeat trigger.
- Feature Cut table with core/support/defer/cut buckets.

## Quality Checks

- Gate: Approve the first playable only if the proof, cut, and scope lines are explicit enough to kill or greenlight the build.
- Check whether the validation question can fail fast enough to trigger a redesign.
- Check whether the smallest honest loop is playable after art, meta systems, and comfort features are stripped away.
- Check whether the validation question can fail in a short playtest.
- Check whether the smallest honest loop is playable without future systems or spectacle.
- Check whether the feature cut removes attractive work instead of protecting comfort.
- Check whether the content scope is just enough to prove the loop.
- Check whether the out-of-scope list blocks creep instead of sounding polite.
- Check whether the pack keeps a kill list so this does not turn into a dream-expanding skill.
- Check whether the MVP pack names the next build and the next playtest signal.
- Check whether the build recommendation and success criteria are explicit enough to approve the first playable.
- Check whether the pack stays prototype first instead of drifting into a mini vertical slice.
- Check whether pass and fail evidence would actually force a redesign instead of just sounding organized.
- Check whether a greybox build with stubbed content and placeholder art still answers the validation question.

## Cut Rules

- cut aggressively
- out of scope blocks scope creep
- not a mini vertical slice
- defer attractive work that does not prove the question

## Common Pitfalls: Failure Patterns and Fixes

If support systems keep sneaking back in, move them to out of scope with a condition for re-entry and keep a kill list so this does not become a dream-expanding skill.

- Use these failure patterns to pressure-test the feature cut, out-of-scope line, and first playable package against scope creep, vertical slice drift, mood instead of loop, and content hiding uncertainty.
- Pattern index: Fake MVP, Scope Creep, Content Hiding Uncertainty, Mood Instead of Loop, Success Criteria Missing.
- Repair moves: rewrite as a falsifiable playtest observation, reduce to the smallest playable loop, move nonessential systems to defer or cut, state pass and fail evidence.

### Fake MVP
- Symptom: The core question reads like a slogan and no short session could disprove it.
- Cause: The pack protected confidence instead of proof.
- Correction: Rewrite the validation question so one failed playtest would force a redesign.

### Scope Creep
- Symptom: Support systems keep sliding back into the first build as if they were core.
- Cause: The feature cut was polite instead of explicit.
- Correction: Cut aggressively, then move the supportive work into out of scope with a clear re-entry condition.

### Content Hiding Uncertainty
- Symptom: The MVP only works if future meta systems, content volume, or presentation arrive first.
- Cause: The smallest honest loop was never isolated, so content is hiding uncertainty instead of proving the idea.
- Correction: Do not fake the entire game; reduce the build to the repeatable loop that already produces the intended feeling.

### Mood Instead of Loop
- Symptom: The package sells fantasy, tone, or mood, but it still does not say which repeatable loop proves the concept.
- Cause: The handoff is carrying aspiration instead of a smallest honest loop.
- Correction: Rewrite the pack around the repeatable loop, then cut any line that is only mood instead of loop.

### Vertical Slice Drift
- Symptom: The first build quietly grows into a mini vertical slice with polish, onboarding, and support systems doing proof work.
- Cause: The feature cut stopped protecting the prototype-first boundary and the pack drifted toward a vertical slice.
- Correction: Return to the proof target, restore the kill list, and keep only the work required to validate the loop.

## Voice Rules

- proof-first
- cut aggressively
- falsifiable
- buildable handoff

## Decision Rules

- validation question can fail
- smallest honest loop is playable
- feature cut removes attractive work
- content scope serves validation
- success signal and fail signal are explicit
- out-of-scope list blocks creep
- prefer testability over impressiveness
- keep the loop honest
