from __future__ import annotations

import re
from typing import Any

from ..models.expert_dna import DomainMovePlan, ExpertSkillDNA, ExpertWorkflowMove
from .expert_structure import expert_profile_for_skill
from .style_diversity import expert_style_profile_for_skill


def _move(
    name: str,
    *,
    purpose: str,
    decision_probe: str,
    action: str,
    output_fragment: str,
    failure_signal: str,
    repair_move: str,
    must_include_terms: list[str],
    avoid_terms: list[str] | None = None,
) -> ExpertWorkflowMove:
    return ExpertWorkflowMove(
        name=name,
        purpose=purpose,
        decision_probe=decision_probe,
        action=action,
        output_fragment=output_fragment,
        failure_signal=failure_signal,
        repair_move=repair_move,
        must_include_terms=must_include_terms,
        avoid_terms=list(avoid_terms or []),
    )


EXPERT_SKILL_DNA_PROFILES: dict[str, ExpertSkillDNA] = {
    "concept-to-mvp-pack": ExpertSkillDNA(
        skill_name="concept-to-mvp-pack",
        core_thesis=(
            "An MVP pack is the smallest honest proof of the player promise. It should make the core "
            "validation question falsifiable, keep the playable loop honest, and cut anything that hides learning."
        ),
        numbered_spine=[
            "validation question",
            "smallest honest loop",
            "feature cut",
            "content scope",
            "out-of-scope",
            "mvp package",
        ],
        workflow_moves=[
            _move(
                "Define the Core Validation Question",
                purpose="Turn the pitch into one risky claim that can fail in a playtest.",
                decision_probe="What exactly must be proven, and what observation would prove the concept wrong?",
                action="Write the central design hypothesis in falsifiable language before choosing content.",
                output_fragment="Core validation question with success evidence and failure evidence.",
                failure_signal="The question sounds like a slogan or could not fail in a short prototype.",
                repair_move="Rewrite it as a playtest observation that would force a redesign.",
                must_include_terms=["validation question", "can fail", "central design hypothesis"],
                avoid_terms=["mood board", "slogan"],
            ),
            _move(
                "Identify the Minimum Honest Loop",
                purpose="Find the smallest playable loop that exposes the fantasy without future promises.",
                decision_probe="Can the loop be played with visible input, response, feedback, and repeat trigger?",
                action="Name the player input, system response, visible feedback, and repeat trigger.",
                output_fragment="Smallest honest loop: input, response, feedback, repeat trigger.",
                failure_signal="The loop depends on future systems, scripted presentation, or invisible depth.",
                repair_move="Cut back to one playable interaction that can be tested immediately.",
                must_include_terms=["smallest honest loop", "player input", "system response", "visible feedback", "repeat trigger"],
            ),
            _move(
                "Separate Must-Haves from Supports",
                purpose="Protect learning by cutting attractive features that do not prove the question.",
                decision_probe="Which painful feature cut would make the MVP clearer instead of poorer?",
                action="Sort work into core, support, defer, and cut; keep only evidence-bearing features.",
                output_fragment="Feature cut table with Core, Support, Defer, and Cut buckets.",
                failure_signal="Too many systems are called core and the MVP becomes a miniature vertical slice.",
                repair_move="Move polish, meta-progression, spectacle, and nonessential content to defer or cut.",
                must_include_terms=["feature cut", "core", "support", "defer", "cut"],
                avoid_terms=["vertical slice"],
            ),
            _move(
                "Define the Minimum Content Package",
                purpose="Choose the least content needed to expose the loop honestly.",
                decision_probe="How much content is enough to test the loop before content starts hiding uncertainty?",
                action="Pick the smallest arena, encounter, toy set, scene, or run count that can produce evidence.",
                output_fragment="Minimum content scope with test space, session length, success signal, and fail signal.",
                failure_signal="Content volume is being used to make the concept look real instead of testable.",
                repair_move="Reduce to one strong test space and one measurable playtest signal.",
                must_include_terms=["minimum content", "content scope", "success signal", "fail signal"],
            ),
            _move(
                "Define What Is Out of Scope",
                purpose="Stop hidden scope creep before it returns through vague deferred work.",
                decision_probe="Which tempting ideas sound related but do not answer the validation question?",
                action="Write a concrete out-of-scope list with a re-entry condition for each deferred idea.",
                output_fragment="Out-of-scope list with why excluded and re-entry condition.",
                failure_signal="Deferred features are vague enough to sneak back into the first build.",
                repair_move="Name the exact excluded work and the evidence required before it can return.",
                must_include_terms=["out of scope", "scope creep", "re-entry condition"],
            ),
            _move(
                "Package the First Playable",
                purpose="Turn the scope decision into a buildable handoff.",
                decision_probe="Could a builder start the first playable without rereading the original prompt?",
                action="Assemble the validation question, loop, feature cut, content scope, risk, and first test.",
                output_fragment="MVP package with build recommendation, playtest signal, and open assumptions.",
                failure_signal="The pack feels polished but does not tell the team what to build first.",
                repair_move="Rewrite the package as the next work order plus the first player-facing test.",
                must_include_terms=["mvp package", "build recommendation", "playtest signal", "open assumptions"],
            ),
        ],
        output_fields=[
            "Core Validation Question",
            "Smallest Honest Loop",
            "Feature Cut",
            "Minimum Content Package",
            "Out of Scope",
            "MVP Package",
        ],
        decision_rules=[
            "validation question can fail",
            "smallest honest loop is playable",
            "feature cut removes attractive work",
            "content scope serves validation",
            "success signal and fail signal are explicit",
            "out-of-scope list blocks creep",
            "prefer testability over impressiveness",
            "keep the loop honest",
        ],
        cut_rules=[
            "cut aggressively",
            "out of scope blocks scope creep",
            "not a mini vertical slice",
            "defer attractive work that does not prove the question",
        ],
        failure_patterns=[
            "Fake MVP",
            "Scope Creep",
            "Content Hiding Uncertainty",
            "Mood Instead of Loop",
            "Success Criteria Missing",
        ],
        repair_moves=[
            "rewrite as a falsifiable playtest observation",
            "reduce to the smallest playable loop",
            "move nonessential systems to defer or cut",
            "state pass and fail evidence",
        ],
        voice_rules=["proof-first", "cut aggressively", "falsifiable", "buildable handoff"],
    ),
    "decision-loop-stress-test": ExpertSkillDNA(
        skill_name="decision-loop-stress-test",
        core_thesis=(
            "A decision loop is healthy when pressure changes over time. Stress it by phase, find the collapse point, "
            "and fix the structure instead of padding with more content."
        ),
        numbered_spine=[
            "current loop",
            "first hour",
            "midgame",
            "lategame",
            "solved state",
            "variation quality",
            "reinforcement",
        ],
        workflow_moves=[
            _move(
                "Define the Current Loop Shape",
                purpose="Identify the repeated choice instead of listing every player action.",
                decision_probe="What does the player observe, decide, do, receive, and repeat?",
                action="Map observe, decide, act, resolve, reward, and next-choice trigger.",
                output_fragment="Loop under test with choice, feedback structure, and repeat trigger.",
                failure_signal="The loop description lists activities but not the repeated decision.",
                repair_move="Rewrite the loop as choice -> feedback -> reward -> next choice.",
                must_include_terms=["current loop", "core decision", "feedback structure", "next-choice trigger"],
            ),
            _move(
                "Test the First-Hour Hook",
                purpose="Check whether novelty hides a weak loop at onboarding time.",
                decision_probe="Why would a new player understand and repeat this decision in the first hour?",
                action="Stress readability, immediate stakes, cause-effect feedback, and reason to repeat.",
                output_fragment="First-hour performance with hook, confusion risk, and boredom risk.",
                failure_signal="The first hour works only because the premise is fresh.",
                repair_move="Expose a meaningful tradeoff or readable consequence earlier.",
                must_include_terms=["first hour", "readability", "reason to repeat", "novelty"],
            ),
            _move(
                "Test Midgame Sustainability",
                purpose="Find whether learned play becomes richer or turns into autopilot.",
                decision_probe="What prevents the midgame from flattening once the basics are understood?",
                action="Inspect constraints, tradeoffs, variation quality, and dominant-option risk.",
                output_fragment="Midgame pressure with tradeoff change, variation quality, and autopilot risk.",
                failure_signal="Midgame content changes labels while decisions stay identical.",
                repair_move="Add state changes that force adaptation, not just larger numbers.",
                must_include_terms=["midgame", "tradeoffs", "variation quality", "autopilot"],
            ),
            _move(
                "Test Late-Game Expansion or Mutation",
                purpose="Check whether mastery creates new decisions or erases pressure.",
                decision_probe="Does lategame mastery reveal deeper problems or solve the game away?",
                action="Name the expansion, mutation, or collapse point that appears at mastery.",
                output_fragment="Late-game performance with evolution demand and collapse point.",
                failure_signal="Mastery removes the game instead of changing the problem.",
                repair_move="Introduce risk, asymmetry, or pressure that meets mastery.",
                must_include_terms=["late-game", "mastery", "collapse point", "mutation"],
            ),
            _move(
                "Look for Solved States",
                purpose="Name the dominant strategy before it becomes invisible.",
                decision_probe="What answer would a strong player repeat until the loop becomes stale?",
                action="Describe the dominant strategy and the reward, cost, or timing pattern that creates it.",
                output_fragment="Solved-state risk with cause and counterpressure.",
                failure_signal="The solved state is dismissed as player preference.",
                repair_move="Add structural counterpressure instead of another option.",
                must_include_terms=["solved state", "dominant strategy", "counterpressure"],
            ),
            _move(
                "Audit Variation and Reinforcement",
                purpose="Separate decision-changing variation from cosmetic content and check what rewards train.",
                decision_probe="Do variations change read, tradeoff, consequence, or adaptation?",
                action="Cut cosmetic variation and align rewards with the intended behavior.",
                output_fragment="Variation quality and reinforcement recommendations.",
                failure_signal="Rewards teach efficient autopilot while the design claims expressive play.",
                repair_move="Reward adaptation, timing, state-reading, or expressive choices directly.",
                must_include_terms=["variation quality", "reinforcement", "reward", "autopilot"],
            ),
        ],
        output_fields=[
            "Current Loop Shape",
            "First-Hour Hook",
            "First-Hour Performance",
            "Midgame Sustainability",
            "Midgame Performance",
            "Late-Game Evolution",
            "Late-Game Performance",
            "Solved State Risk",
            "Variation Quality",
            "Reinforcement Check",
            "Reinforcement Recommendations",
        ],
        decision_rules=[
            "first hour creates readable pressure",
            "first hour midgame and lategame differ",
            "midgame changes decisions",
            "lategame mastery creates new problems",
            "solved state is concrete",
            "variation changes consequence",
            "variation changes decisions",
            "reinforcement teaches intended behavior",
            "where collapse happens",
            "structural fixes",
            "healthy mastery",
            "decision quality",
        ],
        cut_rules=[
            "not greenlighting theme",
            "not greenlighting the theme",
            "not MVP scope cutting",
            "not detailed numeric balancing",
            "surface excitement is not enough",
            "not content padding",
            "content padding cannot fix weak decision quality",
            "cut cosmetic variation",
            "fix structure before adding options",
        ],
        failure_patterns=[
            "Novelty-Only Start",
            "Midgame Autopilot",
            "Progression Without New Problems",
            "Cosmetic Options",
            "Dominant Strategy",
            "Rewarding Autopilot",
        ],
        repair_moves=[
            "expose meaningful tradeoffs in the first hour",
            "add state changes that force adaptation",
            "add structural counterpressure",
            "reward the intended behavior directly",
        ],
        voice_rules=["phase stress", "collapse point", "structural fix", "not content padding"],
    ),
    "simulation-resource-loop-design": ExpertSkillDNA(
        skill_name="simulation-resource-loop-design",
        core_thesis=(
            "A resource loop is a visible pressure web. Variables matter only when they create choices, feedback, "
            "recovery costs, and emotional fantasy alignment."
        ),
        numbered_spine=[
            "variable web",
            "variable role",
            "pressure relationships",
            "decision tensions",
            "feedback loops",
            "failure recovery",
            "emotional fantasy",
        ],
        workflow_moves=[
            _move(
                "Map the Variable Web",
                purpose="List only resources and pressures that can change player behavior.",
                decision_probe="Which variables are visible enough to guide a player decision?",
                action="Map resources, sinks, converters, buffers, caps, and player-visible signals.",
                output_fragment="Variable web with resources, sinks, converters, buffers, and signals.",
                failure_signal="The variable web is only hidden meters or decorative resources.",
                repair_move="Cut or connect each variable to a player-facing decision.",
                must_include_terms=["variable web", "resources", "sinks", "converters", "player-facing"],
            ),
            _move(
                "Define Each Variable's Role",
                purpose="Prevent resource sprawl by assigning each variable a behavioral job.",
                decision_probe="What decision does this variable create or constrain?",
                action="Classify each variable as source, sink, converter, buffer, cap, signal, cost, or pressure.",
                output_fragment="Variable role table with role, decision, and visibility.",
                failure_signal="Variables have names but no behavioral role.",
                repair_move="Cut variables without a role or merge duplicated pressures.",
                must_include_terms=["variable role", "source", "sink", "converter", "pressure"],
            ),
            _move(
                "Map the Pressure Relationships",
                purpose="Make cause and effect legible before tuning numbers.",
                decision_probe="Which pressure relationship creates a meaningful tradeoff over time?",
                action="Write cause/effect pairs, timing, and player-visible warning signs.",
                output_fragment="Pressure relationships with cause, effect, timing, and warning signal.",
                failure_signal="Pressure punishes the player without readable warning.",
                repair_move="Expose cause and effect through UI, timing, or predictable state changes.",
                must_include_terms=["pressure relationships", "cause", "effect", "tradeoff", "visible warning"],
            ),
            _move(
                "Identify Primary Decision Tensions",
                purpose="Find the recurring sacrifices the loop should force.",
                decision_probe="What can the player never maximize all at once?",
                action="Name tensions, viable responses, and what each response sacrifices.",
                output_fragment="Decision tensions with tradeoff, pressure, and viable responses.",
                failure_signal="The player can optimize everything with one dominant path.",
                repair_move="Add opportunity cost, incompatible goals, or non-convertible pressure.",
                must_include_terms=["decision tensions", "tradeoff", "viable responses", "opportunity cost"],
            ),
            _move(
                "Design Positive and Negative Feedback Loops",
                purpose="Make success compound without removing pressure.",
                decision_probe="What compounds, and what counterpressure prevents runaway success?",
                action="Trace positive loops, negative loops, brakes, decay, maintenance, and risk.",
                output_fragment="Positive and negative loops with compounding force and counterpressure.",
                failure_signal="Only positive loops exist, creating runaway snowballing.",
                repair_move="Add decay, scrutiny, maintenance, scarcity, or asymmetric risk.",
                must_include_terms=["positive loop", "negative loop", "counterpressure", "runaway"],
            ),
            _move(
                "Design Failure and Recovery",
                purpose="Keep failure meaningful without creating a death spiral.",
                decision_probe="How does the player notice failure early, recover, and keep a lasting cost?",
                action="Define early warning, recovery action, and consequence that remains after recovery.",
                output_fragment="Failure recovery with warning, recovery action, and lasting consequence.",
                failure_signal="Recovery either erases consequences or becomes mathematically impossible.",
                repair_move="Add costly recovery tools and earlier warning signs.",
                must_include_terms=["failure recovery", "early warning", "lasting consequence", "death spiral"],
            ),
            _move(
                "Align With Emotional Fantasy",
                purpose="Make the pressure web produce the intended feeling, not just stable math.",
                decision_probe="Does the loop make the player feel the fantasy through choices and consequences?",
                action="Check whether scarcity, abundance, care, panic, mastery, or planning emerges from the loop.",
                output_fragment="Emotional fantasy alignment with intended feeling and mismatch to fix.",
                failure_signal="The spreadsheet balances while the emotional fantasy disappears.",
                repair_move="Rewrite variables that contradict the intended fantasy even if the math works.",
                must_include_terms=["emotional fantasy", "resource loop", "mismatch", "intended feeling"],
            ),
        ],
        output_fields=[
            "Variable Web",
            "Variable Roles",
            "Pressure Relationships",
            "Primary Decision Tensions",
            "Positive Loop",
            "Negative Loop",
            "Positive and Negative Loops",
            "Failure Recovery",
            "Resource Loop",
            "Emotional Fantasy",
            "Emotional Fantasy Alignment",
            "Design Recommendations",
        ],
        decision_rules=[
            "variable web has player-facing roles",
            "variables are player-facing",
            "pressure relationships create tradeoffs",
            "positive loop and negative loop both exist",
            "positive and negative loops balance rhythm",
            "failure recovery keeps cost",
            "emotional fantasy matches system pressure",
            "emotional fantasy matches resource math",
            "player-facing tradeoffs",
            "pressure web",
            "aspiration and consequence",
            "emotional or structural backlash",
        ],
        cut_rules=[
            "cut decorative resources",
            "not one simple currency",
            "not isolated meters",
            "few strong tensions over many weak subsystems",
        ],
        failure_patterns=[
            "Decorative Resources",
            "Variable Web Sprawl",
            "No Real Tradeoff",
            "One Dominant Currency",
            "Positive-Loop Runaway",
            "Runaway Snowball",
            "Death Spiral",
            "Punishment Without Agency",
            "Hidden Pressure Relationships",
            "Emotionless Resource Loop",
            "Fantasy-System Mismatch",
        ],
        repair_moves=[
            "connect each variable to a visible decision",
            "add non-convertible pressure or opportunity cost",
            "add counterpressure to success",
            "add costly recovery with earlier warnings",
            "align variables with intended feeling",
        ],
        voice_rules=["map", "tension", "loop", "correct", "player-facing pressure"],
    ),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def expert_skill_dna_for_skill(*, skill_name: str, task: str = "") -> ExpertSkillDNA | None:
    normalized = str(skill_name or "").strip().lower()
    if normalized in EXPERT_SKILL_DNA_PROFILES:
        return EXPERT_SKILL_DNA_PROFILES[normalized]
    structure_profile = expert_profile_for_skill(skill_name=skill_name, task=task)
    if structure_profile is not None:
        return EXPERT_SKILL_DNA_PROFILES.get(structure_profile.skill_name)
    return None


def build_domain_move_plan(*, skill_name: str, task: str = "") -> DomainMovePlan | None:
    dna = expert_skill_dna_for_skill(skill_name=skill_name, task=task)
    if dna is None:
        return None
    style_profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    opening = (
        style_profile.opening_frame
        if style_profile is not None and style_profile.opening_frame
        else f"Use this skill to apply the {dna.skill_name} expert workflow."
    )
    if dna.skill_name == "concept-to-mvp-pack":
        overview = "Turn a rough concept into a falsifiable first playable: what to prove, what to keep, what to cut, and what to package."
        when_to_use = [
            "The user has a rough game concept and needs a scoped first build.",
            "The idea has too many mechanics, content hopes, or genre references competing for attention.",
            "The next useful output is a buildable MVP pack rather than a mood board or full design bible.",
        ]
        when_not_to_use = [
            "The user only wants names, visual tone, lore, or freeform theme exploration.",
            "The project already has a locked vertical slice and needs production scheduling.",
            "There is not enough concept material to identify a player fantasy or loop.",
        ]
        inputs = [
            "Concept premise and player fantasy.",
            "Target platform, session length, audience, and team or time constraints.",
            "Must-keep mechanics, inspirations, and features the user is tempted to include.",
        ]
    elif dna.skill_name == "decision-loop-stress-test":
        overview = "Stress a loop across first-hour, midgame, mastery, solved-state, variation, and reinforcement pressure before adding content."
        when_to_use = [
            "The user asks whether a game loop has meaningful decisions.",
            "A prototype feels repetitive, obvious, solved, random, or padded with cosmetic options.",
            "The team needs a diagnosis across time rather than a single gut check.",
        ]
        when_not_to_use = [
            "The task is pure numeric balancing with telemetry already available.",
            "The user only wants new mechanic ideas without evaluating an existing loop.",
            "The problem is execution polish rather than decision structure.",
        ]
        inputs = [
            "Current loop and repeated player choice.",
            "Information visible before the choice and feedback after it.",
            "Costs, risks, rewards, timing, known dominant strategies, and boring phases.",
        ]
    else:
        overview = "Map resources into visible pressure, feedback, recovery, and fantasy alignment before tuning numbers."
        when_to_use = [
            "The user asks for economy, survival, management, strategy, or simulation-loop design.",
            "A resource loop has too many currencies, no pressure, runaway snowballing, or unclear agency.",
            "The design needs a first-pass model before tuning numbers or implementing simulation code.",
        ]
        when_not_to_use = [
            "The user only wants numeric balancing values.",
            "The game has no persistent state or repeated resource decisions.",
            "The task is primarily monetization pricing or engine code.",
        ]
        inputs = [
            "Player goal, session rhythm, and emotional fantasy.",
            "Candidate resources, sinks, converters, producers, caps, decay, and visible states.",
            "Known failure states, recovery expectations, and snowball risks.",
        ]
    return DomainMovePlan(
        skill_name=dna.skill_name,
        opening_frame=opening,
        overview=overview,
        when_to_use=when_to_use,
        when_not_to_use=when_not_to_use,
        inputs=inputs,
        dna=dna,
    )


OUTPUT_FIELD_GUIDANCE: dict[str, dict[str, str]] = {
    "concept-to-mvp-pack": {
        "Core Validation Question": "Write the validation goal as a core question that can fail, with success criteria and failure evidence.",
        "Smallest Honest Loop": "Write player input, system response, visible feedback, and repeat trigger; keep the loop honest before adding content.",
        "Feature Cut": "Write must have, support, defer, cut for now, and why each cut protects testability.",
        "Minimum Content Package": "Write minimum content scope, required systems, prototype first target, and the smallest session that can prove the loop.",
        "Out of Scope": "Write the kill list: what stays out of scope, why it blocks scope creep, and what evidence would let it return.",
        "MVP Package": "Write the build recommendation, main production risks, first playable test, and open assumptions.",
    },
    "decision-loop-stress-test": {
        "Current Loop Shape": "Write observe, core decision, action, feedback structure, reward, and next-choice trigger.",
        "First-Hour Hook": "Write first-hour readability, immediate stakes, cause-and-effect chain, and why the player still cares.",
        "First-Hour Performance": "Write whether the first hour creates readable pressure or only novelty-only start.",
        "Midgame Sustainability": "Write compounding tradeoffs, resources or states move, and what prevents flattening.",
        "Midgame Performance": "Write midgame performance, autopilot risk, dominant option, and structural fix.",
        "Late-Game Evolution": "Write late-game expansion, mastery pressure, and whether mastery creates new problems.",
        "Late-Game Performance": "Write late-game performance, collapse point, and healthy mastery check.",
        "Solved State Risk": "Write solved-state risks, dominant strategy, and counterpressure.",
        "Variation Quality": "Write whether variation changes decisions, not just surface variation or cosmetic options.",
        "Reinforcement Check": "Write what behavior the rewards teach and whether they train autopilot.",
        "Reinforcement Recommendations": "Write reinforcement recommendations that reward adaptation, state-reading, or expressive timing.",
    },
    "simulation-resource-loop-design": {
        "Variable Web": "Write core resources pressures, time money energy reputation relationships, and every player-facing signal.",
        "Variable Roles": "Write source, sink, converter, buffer, cap, signal, pressure, and what each enables or restricts.",
        "Pressure Relationships": "Write cause, effect, timing, visible warning, gain sources, loss sources, and tradeoff.",
        "Primary Decision Tensions": "Write what the player can never maximize all at once and which choices hurt in an interesting way.",
        "Positive Loop": "Write positive loops, conversion, amplification, threshold, runaway risk, and reward pressure.",
        "Negative Loop": "Write negative counter loops, decay, scarcity, maintenance, and counter-pressure.",
        "Positive and Negative Loops": "Write the loop pair: what compounds, what corrects it, and where the brake appears.",
        "Failure Recovery": "Write failure and recovery, early warning, recovery action, lasting cost, and punishment without agency risk.",
        "Resource Loop": "Write how the resource loop creates player-facing tradeoffs rather than one simple currency.",
        "Emotional Fantasy": "Write aspiration and consequence, intended feeling, mismatch, and emotional or structural backlash.",
        "Emotional Fantasy Alignment": "Write emotional fantasy alignment: how scarcity, abundance, panic, mastery, or planning emerges.",
        "Design Recommendations": "Write design recommendations that cut decorative resources and strengthen few strong tensions.",
    },
}


def _output_field_guidance(dna: ExpertSkillDNA, field: str) -> str:
    return OUTPUT_FIELD_GUIDANCE.get(dna.skill_name, {}).get(
        field,
        "Write the concrete result with the decision, evidence, and next action clearly enough to use.",
    )


def render_expert_dna_skill_md(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
) -> str | None:
    plan = build_domain_move_plan(skill_name=skill_name, task=task)
    if plan is None:
        return None
    dna = plan.dna
    style_profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    profile_labels = list(getattr(style_profile, "workflow_label_set", []) or [])
    lines = [
        "---",
        f"name: {skill_name}",
        f"description: {description}",
        "---",
        "",
        f"# {skill_name}",
        "",
        plan.opening_frame,
        "",
        "## Overview",
        "",
        plan.overview,
        "",
        "## Core Principle",
        "",
        dna.core_thesis,
        "",
        "## When to Use",
        "",
    ]
    lines.extend(f"- {item}" for item in plan.when_to_use)
    lines.extend(["", "## When Not to Use", ""])
    lines.extend(f"- {item}" for item in plan.when_not_to_use)
    lines.extend(["", "## Inputs", ""])
    lines.extend(f"- {item}" for item in plan.inputs)
    lines.extend(["", "## Default Workflow", ""])
    if profile_labels:
        lines.append(f"Profile rhythm: {', '.join(profile_labels)}.")
    if dna.cut_rules:
        lines.append(f"Workflow guardrails: {', '.join(dna.cut_rules[:6])}.")
    if profile_labels or dna.cut_rules:
        lines.append("")
    for index, move in enumerate(dna.workflow_moves, start=1):
        lines.append(f"{index}. **{move.name}**")
        lines.append(f"   - Decision: {move.decision_probe}")
        lines.append(f"   - Do: {move.action}")
        lines.append(f"   - Output: {move.output_fragment}")
        lines.append(f"   - Failure Signal: {move.failure_signal}")
        lines.append(f"   - Fix: {move.repair_move}")
        if move.must_include_terms:
            lines.append(f"   - Must include: {', '.join(move.must_include_terms[:5])}.")
        lines.append("")
    lines.extend(["## Output Format", "", "```markdown"])
    for field in dna.output_fields:
        lines.append(f"## {field}")
        guidance = _output_field_guidance(dna, field)
        lines.append(f"- Write: {guidance}")
        lines.append(f"- Good: the {field} names the decision, evidence, consequence, and next action clearly enough to act on.")
        lines.append(f"- Weak: the {field} stays abstract, repeats the prompt, or leaves the field as a vague summary.")
        lines.append("")
    lines.extend(["```", "", "## Decision Rules", ""])
    lines.extend(f"- {item}" for item in dna.decision_rules)
    lines.extend(["", "## Cut Rules", ""])
    lines.extend(f"- {item}" for item in dna.cut_rules)
    lines.extend(["", "## Quality Checks", ""])
    for rule in dna.decision_rules:
        lines.append(f"- Check that {rule}.")
    for move in dna.workflow_moves:
        lines.append(f"- {move.name}: {move.failure_signal}")
    lines.extend(["", "## Common Pitfalls: Failure Patterns and Fixes", ""])
    for index, pattern in enumerate(dna.failure_patterns):
        repair = dna.repair_moves[index % len(dna.repair_moves)] if dna.repair_moves else "Return to the workflow and make the judgment explicit."
        lines.append(f"### {pattern}")
        lines.append(f"- Symptom: the output shows `{pattern.lower()}` instead of a usable design decision.")
        lines.append("- Cause: the workflow skipped the hard judgment and accepted a softer description.")
        lines.append(f"- Correction: {repair}.")
        lines.append("")
    lines.extend(["## Worked Micro-Example", ""])
    if dna.skill_name == "concept-to-mvp-pack":
        lines.extend([
            "- Premise: a cozy courier game about choosing routes through weather and social obligations.",
            "- Decision: prove whether tiny route tradeoffs stay interesting before building a city.",
            "- Output: keep route choice, weather pressure, and one reputation consequence; cut cosmetics, meta progression, and branching story.",
        ])
    elif dna.skill_name == "decision-loop-stress-test":
        lines.extend([
            "- Loop: choose a combat card, spend stamina, resolve enemy intent, earn upgrade currency, repeat.",
            "- Decision: first hour is readable, but midgame collapses when one stamina-efficient build dominates.",
            "- Output: add enemies that punish repeated safe choices and reward state-aware adaptation.",
        ])
    else:
        lines.extend([
            "- Fantasy: running a tiny frontier clinic under public scrutiny.",
            "- Decision: trust brings patients and funding, while fatigue raises mistake risk and public scrutiny.",
            "- Output: positive loop is trust -> funding; negative loop is more patients -> fatigue -> scrutiny; recovery costs trust.",
        ])
    lines.extend(["", "## Voice Rules", ""])
    lines.extend(f"- {item}" for item in dna.voice_rules)
    if references:
        lines.extend(["", "## References", ""])
        lines.extend(f"- See `{path}` for supporting material." for path in references)
    if scripts:
        lines.extend(["", "## Helpers", ""])
        lines.extend(f"- Use `{path}` only when it directly supports this workflow." for path in scripts)
    return "\n".join(lines).rstrip() + "\n"


def move_signature_from_markdown(content: str) -> set[str]:
    normalized = _normalize(content)
    signatures: set[str] = set()
    for dna in EXPERT_SKILL_DNA_PROFILES.values():
        for move in dna.workflow_moves:
            if _normalize(move.name) in normalized:
                signatures.add(_normalize(move.name))
    return signatures
