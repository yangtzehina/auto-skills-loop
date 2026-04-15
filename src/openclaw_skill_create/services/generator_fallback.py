from __future__ import annotations

from dataclasses import dataclass, field

from ..models.artifacts import ArtifactFile
from .domain_specificity import extract_task_domain_anchors, profile_for_skill
from .expert_structure import expert_profile_for_skill


@dataclass(frozen=True)
class DomainSkillBlueprint:
    core_principle: str
    when_to_use: list[str]
    when_not_to_use: list[str]
    inputs: list[str]
    section_plan: list[tuple[str, list[str]]] = field(default_factory=list)
    output_schema: list[tuple[str, list[str]]] = field(default_factory=list)
    quality_check_matrix: list[str] = field(default_factory=list)
    pitfall_taxonomy: list[str] = field(default_factory=list)


def _display_subject(*, skill_name: str, task: str) -> str:
    profile = profile_for_skill(skill_name=skill_name, task=task)
    if profile is not None:
        return profile.label
    words = skill_name.replace('-', ' ').replace('_', ' ').strip()
    return words or 'methodology task'


def _domain_methodology_sections(*, skill_name: str, task: str) -> dict[str, list[str]]:
    profile = profile_for_skill(skill_name=skill_name, task=task)
    if profile is not None and profile.skill_name == 'concept-to-mvp-pack':
        return {
            'workflow': [
                'Frame the validation question: name the risky promise the concept must prove before scope grows.',
                'Define the smallest honest loop: one playable loop that exposes the core fantasy without hiding behind future content.',
                'Make the feature cut: separate must-prove mechanics from nice-to-have polish, meta, economy, and spectacle.',
                'Set the content scope: choose the smallest level, encounter, toy set, or scenario count that can prove the loop.',
                'Write the out-of-scope list: explicitly park systems that would dilute the MVP pack or delay learning.',
                'Assemble the MVP pack: goal, player promise, loop, feature cut, content scope, risks, and next validation step.',
            ],
            'outputs': [
                '- Validation question: <what must be proven>',
                '- Smallest honest loop: <30-90 second playable loop>',
                '- Feature cut: <keep / cut / defer>',
                '- Content scope: <minimum content needed>',
                '- Out-of-scope: <tempting work not included>',
                '- MVP pack: <the concise build target>',
            ],
            'checks': [
                '- The validation question can fail; it is not a slogan.',
                '- The smallest honest loop can be built without postponed invisible systems.',
                '- The feature cut removes at least one attractive but nonessential idea.',
                '- The content scope is small enough to test before expanding the concept.',
                '- The out-of-scope list is specific enough to stop hidden scope creep.',
                '- The MVP pack is a concrete build target, not a mood board.',
            ],
            'pitfalls': [
                '- Treating the MVP pack as a mini vertical slice with every system represented.',
                '- Hiding uncertainty by adding more content scope instead of testing the loop.',
                '- Leaving the out-of-scope list vague, which lets deferred features sneak back in.',
            ],
        }
    if profile is not None and profile.skill_name == 'decision-loop-stress-test':
        return {
            'workflow': [
                'Map the decision loop: write the repeated choice, feedback, reward, and next-choice trigger.',
                'Test the first hour: ask whether new players understand the choice and feel a reason to repeat it.',
                'Test the midgame: check whether constraints, tradeoffs, and variation quality keep the loop alive.',
                'Test the lategame: identify whether mastery creates new decisions or collapses into rote execution.',
                'Find the solved state: describe the dominant strategy that would make the decision loop stale.',
                'Audit reinforcement: confirm rewards teach the intended behavior instead of rewarding autopilot.',
            ],
            'outputs': [
                '- Decision loop: <choice -> feedback -> reward -> next choice>',
                '- First hour risk: <confusion, boredom, missing hook>',
                '- Midgame pressure: <what changes and why it matters>',
                '- Lategame evolution: <new mastery demand or collapse point>',
                '- Solved state: <dominant strategy to prevent>',
                '- Reinforcement check: <what behavior the game is training>',
            ],
            'checks': [
                '- First hour, midgame, and lategame each create a different stress signal.',
                '- Variation quality changes decisions, not just surface content.',
                '- The solved state is concrete enough to design against.',
                '- Reinforcement aligns with the intended player fantasy.',
            ],
            'pitfalls': [
                '- Confusing more options with better variation quality.',
                '- Testing only the first hour and missing midgame or lategame collapse.',
                '- Rewarding efficiency while claiming to encourage expressive decisions.',
            ],
        }
    if profile is not None and profile.skill_name == 'simulation-resource-loop-design':
        return {
            'workflow': [
                'Draw the variable web: list resources, sinks, converters, bottlenecks, and player-visible states.',
                'Name pressure relationships: explain which variables push or pull on each other over time.',
                'Trace the positive loop: identify what compounds, accelerates, or snowballs when the player succeeds.',
                'Trace the negative loop: identify brakes, costs, decay, scarcity, or counterpressure.',
                'Design failure recovery: define how the player can recover without erasing consequences.',
                'Check emotional fantasy: verify the resource loop supports the intended feeling, not just balance math.',
            ],
            'outputs': [
                '- Variable web: <resources, sinks, converters, caps>',
                '- Pressure relationships: <cause/effect pairs>',
                '- Positive loop: <what compounds>',
                '- Negative loop: <what stabilizes or taxes>',
                '- Failure recovery: <how players recover and what remains costly>',
                '- Emotional fantasy: <what the loop should make the player feel>',
            ],
            'checks': [
                '- The variable web has visible player decisions, not only hidden simulation state.',
                '- Positive loop and negative loop pressures are both present.',
                '- Failure recovery avoids both death spirals and consequence-free resets.',
                '- Emotional fantasy and resource math point in the same direction.',
            ],
            'pitfalls': [
                '- Building a spreadsheet loop that has no player-facing emotional fantasy.',
                '- Adding only a positive loop, creating runaway snowballing.',
                '- Making failure recovery so generous that pressure relationships stop mattering.',
            ],
        }
    anchors = extract_task_domain_anchors(task, limit=6)
    if not anchors:
        anchors = [_display_subject(skill_name=skill_name, task=task), 'decision frame', 'quality bar']
    while len(anchors) < 3:
        anchors.append(f'task-specific slot {len(anchors) + 1}')
    return {
        'workflow': [
            f'Convert `{anchors[0]}` into a concrete decision or output target.',
            f'Use `{anchors[1]}` to define the main tradeoff, constraint, or evaluation lens.',
            f'Turn `{anchors[2]}` into an explicit workflow step with observable evidence.',
            f'Check `{anchors[0]}` against `{anchors[1]}` and name the risk if they conflict.',
            f'Use `{anchors[2]}` to choose the smallest useful next action.',
            'Add one guardrail that would catch a generic answer before it reaches the user.',
            'Produce the structured output and mark any unresolved assumptions.',
        ],
        'outputs': [f'- {anchor}: <task-specific result>' for anchor in anchors[:5]],
        'checks': [f'- Check that `{anchor}` has a specific decision, risk, or quality bar.' for anchor in anchors[:5]],
        'pitfalls': [
            f'- Leaving `{anchors[0]}` only in the description or overview.',
            f'- Reusing a generic methodology shell where `{anchors[1]}` should drive a domain decision.',
            f'- Treating `{anchors[2]}` as permission to invent unsupported details.',
        ],
    }


def _expert_game_design_blueprint(*, skill_name: str, task: str) -> DomainSkillBlueprint | None:
    profile = expert_profile_for_skill(skill_name=skill_name, task=task)
    if profile is None:
        return None
    if profile.skill_name == 'concept-to-mvp-pack':
        return DomainSkillBlueprint(
            core_principle=(
                'An MVP pack is not a small version of the whole game. It is the smallest honest test of the '
                'core player promise, with a validation question that can fail and a feature cut that protects learning.'
            ),
            when_to_use=[
                'The user has a rough game concept and needs a scoped first build.',
                'The idea has too many mechanics, content hopes, or genre references competing for attention.',
                'The next useful output is a buildable MVP pack rather than a mood board or full design bible.',
                'The team needs to know what to keep, cut, defer, and test first.',
            ],
            when_not_to_use=[
                'The user only wants names, theme exploration, or visual tone.',
                'The project already has a locked vertical slice and needs production scheduling.',
                'The task is mainly technical architecture, UI polish, or asset direction.',
                'There is not enough concept material to identify a player fantasy or loop.',
            ],
            inputs=[
                'Concept premise and player fantasy.',
                'Target platform, session length, audience, and team or time constraints.',
                'Must-keep mechanics, inspirations, and must-avoid comparisons.',
                'Any known risks, confusing scope, or features the user is tempted to include.',
            ],
            section_plan=[
                (
                    'Define the Core Validation Question',
                    [
                        'Write the risky promise the MVP pack must prove, using language that could be falsified in a playtest.',
                        'Separate the validation question from theme, story, polish, and feature wish lists.',
                        'Ask what single failure would make the concept need a redesign instead of more content.',
                    ],
                ),
                (
                    'Identify the Minimum Honest Loop',
                    [
                        'Describe the smallest playable loop that exposes the core fantasy without hiding behind future systems.',
                        'Name the repeated player verbs and the feedback that tells the player whether the loop worked.',
                        'Keep the loop honest: it must be playable, not just described as a future possibility.',
                    ],
                ),
                (
                    'Separate Must-Haves from Supports',
                    [
                        'Make the feature cut by sorting mechanics into core, support, defer, and cut.',
                        'Keep only features that prove the validation question or make the smallest honest loop readable.',
                        'Move attractive polish, meta-progression, large content plans, and spectacle into defer or cut unless they are essential evidence.',
                    ],
                ),
                (
                    'Define the Minimum Content Package',
                    [
                        'Choose the smallest arena, encounter, toy set, level beat, or scenario count that can prove the loop.',
                        'Set content scope as evidence, not as a promise to represent the whole final game.',
                        'Prefer one strong test space over several shallow variations.',
                    ],
                ),
                (
                    'Define What Is Out of Scope',
                    [
                        'Write the out-of-scope list in concrete terms so hidden scope creep has nowhere to hide.',
                        'Include tempting work that sounds related but does not help answer the validation question.',
                        'Mark the earliest condition under which each deferred idea may be reconsidered.',
                    ],
                ),
                (
                    'Assemble the MVP Pack',
                    [
                        'Package the validation question, smallest honest loop, feature cut, content scope, and out-of-scope list into one handoff.',
                        'Add the first build target and the first playtest signal.',
                        'Name unresolved assumptions instead of pretending the pack has solved them.',
                    ],
                ),
                (
                    'Run the Failure Pass',
                    [
                        'Check whether the MVP pack could still fail clearly in a short playtest.',
                        'Remove any feature that only makes the concept look bigger without increasing learning.',
                        'Confirm the pack can guide implementation without rereading the original prompt.',
                    ],
                ),
            ],
            output_schema=[
                ('Core Validation Question', ['What must be proven', 'How it could fail', 'What evidence would count']),
                ('Smallest Honest Loop', ['Player verbs', 'Feedback moment', 'Why it exposes the fantasy']),
                ('Feature Cut', ['Core', 'Support', 'Defer', 'Cut']),
                ('Minimum Content Package', ['Test space', 'Encounter or toy set', 'Session length', 'Success and fail condition']),
                ('Out of Scope', ['Deferred ideas', 'Why excluded', 'Re-entry condition']),
                ('MVP Pack', ['Build target', 'Playtest signal', 'Open assumptions']),
            ],
            quality_check_matrix=[
                'The validation question can fail; it is not a slogan.',
                'The smallest honest loop is playable without postponed invisible systems.',
                'The feature cut removes attractive work that does not prove the validation question.',
                'The content scope is small enough to test before expanding the concept.',
                'The out-of-scope list blocks creep by naming tempting excluded work.',
                'The MVP pack is a concrete build target, not a mini design bible.',
            ],
            pitfall_taxonomy=[
                'Vertical-slice inflation: treating the MVP pack as a tiny version of every final system.',
                'Scope creep by empathy: keeping every cool idea because each one feels related to the fantasy.',
                'Mood instead of loop: describing the vibe while failing to define the playable proof.',
                'Content hiding uncertainty: adding more levels, enemies, or modes instead of testing the risky promise.',
                'Invisible defer list: leaving out-of-scope work vague enough that it sneaks back in.',
            ],
        )
    if profile.skill_name == 'decision-loop-stress-test':
        return DomainSkillBlueprint(
            core_principle=(
                'A decision loop is healthy when players can read the state, choose between real alternatives, '
                'see consequences, and adapt. Stress testing asks where that loop collapses across first hour, '
                'midgame, lategame, solved state, variation quality, and reinforcement.'
            ),
            when_to_use=[
                'The user asks whether a game loop has meaningful decisions.',
                'A prototype feels repetitive, obvious, solved, random, or full of cosmetic options.',
                'The team needs a diagnosis across first hour, midgame, and lategame rather than a single gut check.',
                'The output should identify one or two targeted interventions.',
            ],
            when_not_to_use=[
                'The task is pure economy tuning with telemetry already available.',
                'The user only wants new mechanic ideas without evaluating an existing loop.',
                'The choice is narrative-only and has no mechanical consequence to inspect.',
                'The problem is execution polish rather than decision structure.',
            ],
            inputs=[
                'Current decision loop and repeated player choice.',
                'Information visible before the player chooses.',
                'Costs, risks, rewards, timing, and feedback after each choice.',
                'Known dominant strategies, boring phases, confusing phases, or player complaints.',
            ],
            section_plan=[
                (
                    'Define the Current Loop Shape',
                    [
                        'Map observe, decide, act, resolve, reward, and next-choice trigger.',
                        'Identify the decision loop the player repeats, not every action in the game.',
                        'Name what the loop is supposed to train or make the player feel.',
                    ],
                ),
                (
                    'Test the First-Hour Hook',
                    [
                        'Check whether a new player understands the choice quickly enough to care.',
                        'Ask whether the first hour gives readable feedback and a reason to repeat the decision loop.',
                        'Mark confusion, boredom, missing stakes, or fake choice before adding more systems.',
                    ],
                ),
                (
                    'Test Midgame Sustainability',
                    [
                        'Check whether midgame constraints create new tradeoffs instead of merely increasing numbers.',
                        'Judge variation quality by whether it changes decisions, not whether it changes surface content.',
                        'Look for options that become mandatory, irrelevant, or equivalent once the player learns the loop.',
                    ],
                ),
                (
                    'Test Late-Game Expansion or Mutation',
                    [
                        'Ask whether mastery creates new decisions or collapses into rote execution.',
                        'Check whether lategame tools widen expression, deepen risk, or erase pressure.',
                        'Name the late-game mutation the loop needs if the first-hour pattern cannot carry the whole game.',
                    ],
                ),
                (
                    'Look for Solved States',
                    [
                        'Describe the dominant strategy that would make the decision loop stale.',
                        'Identify which information, reward, cost, or timing pattern creates the solved state.',
                        'Prefer targeted counterpressure over simply adding more options.',
                    ],
                ),
                (
                    'Audit Variation Quality',
                    [
                        'Separate meaningful variation from cosmetic swaps, stat bumps, or random noise.',
                        'Check whether each variation changes read, tradeoff, consequence, or adaptation.',
                        'Remove variations that only increase content count.',
                    ],
                ),
                (
                    'Audit Reinforcement',
                    [
                        'Confirm rewards teach the intended behavior instead of rewarding autopilot.',
                        'Check whether the loop reinforces expression, mastery, caution, aggression, or optimization as intended.',
                        'Name any reward that contradicts the stated player fantasy.',
                    ],
                ),
            ],
            output_schema=[
                ('Current Loop Shape', ['Observe', 'Decide', 'Act', 'Resolve', 'Reward', 'Next-choice trigger']),
                ('First-Hour Hook', ['Readability', 'Reason to repeat', 'Confusion or boredom risk']),
                ('Midgame Sustainability', ['New constraint', 'Tradeoff change', 'Variation quality']),
                ('Late-Game Evolution', ['Expansion', 'Mutation', 'Collapse point']),
                ('Solved State Risk', ['Dominant strategy', 'Cause', 'Counterpressure']),
                ('Variation Quality', ['Meaningful changes', 'Cosmetic changes', 'Cuts']),
                ('Reinforcement Check', ['Behavior rewarded', 'Fantasy alignment', 'Fix']),
            ],
            quality_check_matrix=[
                'First hour, midgame, and lategame must differ in the pressure they put on the decision loop.',
                'Variation quality changes decisions, not just content labels.',
                'The solved state is concrete enough to design against.',
                'Reinforcement must teach intended behavior instead of rewarding autopilot.',
                'The decision loop risk is specific enough to change the next playtest.',
                'The recommendation changes the next playtest, not just the wording of the critique.',
            ],
            pitfall_taxonomy=[
                'Cosmetic options: counting menu choices that do not change consequence.',
                'Surface variation: adding enemies, cards, or levels that ask the same decision.',
                'Dominant strategy denial: noticing a solved state but calling it player preference.',
                'Rewarding autopilot: claiming expressive decisions while the reward optimizes one rote behavior.',
                'First-hour tunnel vision: testing the hook while missing midgame or lategame collapse.',
            ],
        )
    if profile.skill_name == 'simulation-resource-loop-design':
        return DomainSkillBlueprint(
            core_principle=(
                'A simulation resource loop is not just a list of currencies. It is a variable web of resources, '
                'pressure relationships, positive and negative feedback, failure recovery, and emotional fantasy.'
            ),
            when_to_use=[
                'The user asks for economy, production, survival, management, strategy, or systems-loop design.',
                'A resource loop has too many currencies, no pressure, runaway snowballing, or unclear player agency.',
                'The design needs a first-pass model before tuning numbers or implementing simulation code.',
                'The output should make variables, feedback loops, and failure recovery explicit.',
            ],
            when_not_to_use=[
                'The user only wants numeric balancing values.',
                'The game has no persistent state or repeated resource decisions.',
                'The task is primarily monetization pricing or store economy.',
                'The user needs engine code rather than design structure.',
            ],
            inputs=[
                'Player goal, session rhythm, and emotional fantasy.',
                'Candidate resources, sinks, converters, producers, caps, decay, and visible states.',
                'Pressure sources such as scarcity, enemies, time, opportunity cost, or maintenance.',
                'Known failure states, recovery expectations, and snowball risks.',
            ],
            section_plan=[
                (
                    'List the Core Resources or Pressures',
                    [
                        'Name each candidate resource, pressure, sink, converter, bottleneck, and player-visible state.',
                        'Sketch the variable web before adding new resources or pressures.',
                        'Remove duplicated currencies that ask the same decision in different words.',
                        'Mark which variables the player can read and which are hidden simulation state.',
                    ],
                ),
                (
                    "Define Each Variable's Role",
                    [
                        'Classify each variable as source, sink, converter, buffer, cap, signal, cost, or pressure.',
                        'Explain the player decision each variable is supposed to create.',
                        'Cut variables that have no player-facing role.',
                    ],
                ),
                (
                    'Map the Pressure Relationships',
                    [
                        'Draw cause and effect pairs between resources, sinks, risks, and timing pressure.',
                        'Identify which relationships push the player toward action and which stabilize the loop.',
                        'Check whether pressure is visible early enough for planning.',
                    ],
                ),
                (
                    'Identify the Primary Decision Tensions',
                    [
                        'Name the recurring tradeoffs the resource loop should force.',
                        'Separate interesting tension from pure punishment, bookkeeping, or hidden randomness.',
                        'Make sure the player has at least two viable responses to pressure.',
                    ],
                ),
                (
                    'Design the Main Feedback Loops',
                    [
                        'Trace the positive loop: what compounds, accelerates, or snowballs when the player succeeds.',
                        'Trace the negative loop: what brakes, taxes, decays, or counterpressures the system.',
                        'Check whether positive and negative loops create rhythm rather than runaway collapse.',
                    ],
                ),
                (
                    'Design Failure and Recovery',
                    [
                        'Define how failure happens, how the player recognizes it, and how recovery begins.',
                        'Keep consequences visible without creating an unrecoverable death spiral.',
                        'Avoid consequence-free resets that make pressure relationships meaningless.',
                    ],
                ),
                (
                    'Align the Loop with the Emotional Fantasy',
                    [
                        'Check whether resource math supports the intended feeling: panic, planning, mastery, scarcity, abundance, or care.',
                        'Use the emotional fantasy to decide which resource loop pressures should feel exciting rather than arbitrary.',
                        'Rewrite variables that produce the wrong fantasy even if the spreadsheet balances.',
                        'Pick the smallest first playable model that proves the emotional rhythm.',
                    ],
                ),
            ],
            output_schema=[
                ('Variable Web', ['Resources', 'Sinks', 'Converters', 'Buffers', 'Signals']),
                ('Pressure Relationships', ['Cause', 'Effect', 'Player-visible signal']),
                ('Primary Decision Tensions', ['Tradeoff', 'Pressure', 'Viable responses']),
                ('Positive Loop', ['What compounds', 'How it accelerates', 'Snowball risk']),
                ('Negative Loop', ['Brake', 'Cost', 'Decay', 'Counterpressure']),
                ('Failure Recovery', ['Failure signal', 'Recovery action', 'Lasting consequence']),
                ('Emotional Fantasy', ['Intended feeling', 'Loop support', 'Mismatch to fix']),
            ],
            quality_check_matrix=[
                'Variables have player-facing roles in the variable web, not only hidden simulation state.',
                'Pressure relationships are visible enough for planning.',
                'Positive and negative loops both exist; positive loop and negative loop pressures create readable rhythm.',
                'Failure recovery keeps consequences without creating an unrecoverable death spiral.',
                'Emotional fantasy matches resource math in the resource loop.',
                'Emotional fantasy must be visible in the pressure relationships, not only stated as theme.',
                'The first playable model avoids unnecessary currencies.',
            ],
            pitfall_taxonomy=[
                'Variable web sprawl: adding resources and pressures that do not create player-facing decisions.',
                'Runaway snowball: adding only positive loops without counterpressure.',
                'Dead brake: adding a negative loop that only slows the game without creating a decision.',
                'Death spiral: making failure recovery mathematically impossible before the player can learn.',
                'Hidden pressure relationships: letting variables punish the player without readable warning.',
                'Emotionless resource loop: producing stable balance math that does not support the emotional fantasy.',
            ],
        )
    return None


def _render_expert_blueprint_skill_md(
    *,
    skill_name: str,
    description: str,
    blueprint: DomainSkillBlueprint,
    references: list[str],
    scripts: list[str],
) -> str:
    lines = [
        '---',
        f'name: {skill_name}',
        f'description: {description}',
        '---',
        '',
        f'# {skill_name}',
        '',
        'Use this skill when the user needs a domain-specific game-design method, not a generic methodology shell.',
        '',
        '## Overview',
        '',
        'Read the user request as raw design material, then convert it into expert game-design decisions, templates, checks, and failure modes.',
        '',
        '## Core Principle',
        '',
        blueprint.core_principle,
        '',
        '## When to Use',
        '',
    ]
    lines.extend(f'- {item}' for item in blueprint.when_to_use)
    lines.extend(['', '## When Not to Use', ''])
    lines.extend(f'- {item}' for item in blueprint.when_not_to_use)
    lines.extend(['', '## Inputs', ''])
    lines.extend(f'- {item}' for item in blueprint.inputs)
    lines.extend(['', '## Default Workflow', ''])
    for index, (heading, bullets) in enumerate(blueprint.section_plan, start=1):
        lines.extend([f'### {index}. {heading}', ''])
        for bullet in bullets:
            lines.append(f'- {bullet}')
        lines.append('')
    lines.extend(['## Output Format', '', '```markdown'])
    for heading, fields in blueprint.output_schema:
        lines.extend([f'## {heading}'])
        for field in fields:
            lines.append(f'- {field}: <fill in>')
        lines.append('')
    lines.extend(['```', '', '## Quality Checks', ''])
    lines.extend(f'- {item}' for item in blueprint.quality_check_matrix)
    lines.extend([
        '- The output must use domain-specific section titles and decisions, not only generic planning language.',
        '- Another agent should be able to apply the result without rereading the original prompt.',
        '',
        '## Common Pitfalls',
        '',
    ])
    lines.extend(f'- {item}' for item in blueprint.pitfall_taxonomy)
    lines.extend([
        '- Prompt echo: repeating the request instead of turning it into domain actions.',
        '- False completion: passing shape checks while the expert workflow is still missing.',
    ])
    if references:
        lines.extend(['', '## References', ''])
        lines.extend(f'- See `{path}` for supporting material.' for path in references)
    if scripts:
        lines.extend(['', '## Helpers', ''])
        lines.extend(f'- Use `{path}` only when it directly supports this workflow.' for path in scripts)
    return '\n'.join(lines).rstrip() + '\n'


def fallback_generate_skill_md(*, skill_name: str, description: str, references: list[str], scripts: list[str]) -> str:
    lines = [
        '---',
        f'name: {skill_name}',
        f'description: {description}',
        '---',
        '',
        f'# {skill_name}',
        '',
        'Use this skill when the repo-grounded workflow and helper resources match the current task.',
        '',
        '## When to Use',
        '',
        '- Use it when the task matches the capability and trigger described in the frontmatter.',
        '- Use it when the supporting references or helper scripts listed below are relevant to the user request.',
        '',
        '## Workflow',
        '',
        '1. Re-read the user request and confirm the skill trigger actually applies.',
        '2. Review the linked references or helper scripts before making repo-specific claims.',
        '3. Apply the repo-grounded guidance in the smallest useful steps.',
        '4. Summarize any assumptions, outputs, or follow-up checks the user should know about.',
        '',
        '## Output Format',
        '',
        '- State the chosen workflow path.',
        '- List the concrete files, commands, or artifacts used.',
        '- Close with verification status or the next safe action.',
    ]

    if references:
        lines.extend(['', '## References', ''])
        lines.extend(f'- See `{path}` for more detail.' for path in references)

    if scripts:
        lines.extend(['', '## Scripts', ''])
        lines.extend(f'- Use `{path}` when the workflow requires this helper.' for path in scripts)

    return '\n'.join(lines).rstrip() + '\n'


def fallback_generate_methodology_skill_md(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
) -> str:
    expert_blueprint = _expert_game_design_blueprint(skill_name=skill_name, task=task)
    if expert_blueprint is not None:
        return _render_expert_blueprint_skill_md(
            skill_name=skill_name,
            description=description,
            blueprint=expert_blueprint,
            references=references,
            scripts=scripts,
        )

    subject = _display_subject(skill_name=skill_name, task=task)
    domain_sections = _domain_methodology_sections(skill_name=skill_name, task=task)
    workflow_lines = domain_sections['workflow']
    output_lines = domain_sections['outputs']
    check_lines = domain_sections['checks']
    pitfall_lines = domain_sections['pitfalls']
    lines = [
        '---',
        f'name: {skill_name}',
        f'description: {description}',
        '---',
        '',
        f'# {skill_name}',
        '',
        'Use this skill to turn an ambiguous design or decision task into a structured working method with explicit outputs and guardrails.',
        '',
        '## Overview',
        '',
        f'This skill helps Codex turn a {subject} request into a domain-specific method and output.',
        '',
        'The goal is to avoid a generic advice shell. Convert the user request into domain actions, produce a concrete artifact, and catch failure modes that would make the result look structured but feel unusable.',
        '',
        '## When to Use',
        '',
        '- The user asks for a framework, design method, decision loop, stress test, or simulation-style reasoning pass.',
        '- The answer needs more than a short explanation and should produce a structured artifact.',
        '- The task has judgment calls, tradeoffs, or possible false positives that need explicit handling.',
        '- The user would benefit from a reusable checklist or output template.',
        '',
        '## When Not to Use',
        '',
        '- The user only needs a tiny factual answer or a mechanical rewrite.',
        '- The task is better handled by a repo operation, CLI command, or existing implementation workflow.',
        '- The user explicitly asks for freeform brainstorming with no structured output.',
        '- The available context is too thin to make meaningful judgments; ask one focused question instead.',
        '',
        '## Inputs',
        '',
        '- User goal: what the user wants to decide, design, or evaluate.',
        '- Constraints: audience, scope, time, platform, non-goals, and must-avoid outcomes.',
        '- Raw material: notes, examples, design fragments, task descriptions, or prior attempts.',
        '- Quality bar: what would make the final output useful enough to act on.',
        '',
        '## Workflow',
        '',
    ]
    for index, item in enumerate(workflow_lines, start=1):
        lines.append(f'{index}. {item}')
    lines.extend([
        '',
        '## Output Format',
        '',
        'Use this structure unless the user requested a different one:',
        '',
        '```markdown',
        '## Goal',
        '<One sentence describing the concrete decision or artifact.>',
        '',
        '## Domain Frame',
    ])
    lines.extend(output_lines)
    lines.extend([
        '',
        '## Method Result',
        '<The actual designed artifact, decision, checklist, or recommendation.>',
        '',
        '## Tradeoffs',
        '- <Choice made and why>',
        '- <Risk accepted or deferred>',
        '',
        '## Quality Checks',
    ])
    lines.extend(check_lines[:4])
    lines.extend([
        '```',
        '',
        '## Quality Checks',
        '',
    ])
    lines.extend(check_lines)
    lines.extend([
        '- The workflow must include domain actions, not just generic planning verbs.',
        '- The output template must be specific enough for another agent to fill without rereading the prompt.',
        '- The final answer should name tradeoffs and unresolved assumptions.',
        '',
        '## Common Pitfalls',
        '',
    ])
    lines.extend(pitfall_lines)
    lines.extend([
        '- Prompt echo: copying the request into description or overview instead of transforming it.',
        '- False completion: passing shape checks while the domain-specific workflow is still missing.',
    ])
    if references:
        lines.extend(['', '## References', ''])
        lines.extend(f'- See `{path}` for supporting material.' for path in references)
    if scripts:
        lines.extend(['', '## Helpers', ''])
        lines.extend(f'- Use `{path}` only when it directly supports the workflow.' for path in scripts)
    return '\n'.join(lines).rstrip() + '\n'


def fallback_generate_operation_skill_md(
    *,
    skill_name: str,
    description: str,
    contract,
    references: list[str],
    scripts: list[str],
) -> str:
    lines = [
        '---',
        f'name: {skill_name}',
        f'description: {description}',
        '---',
        '',
        f'# {skill_name}',
        '',
        'Use this skill when the task matches the repo\'s stable operation surface and you want a contract-backed workflow instead of freeform guidance.',
        '',
        '## Operation Surface',
        '',
        f'- backend_kind: `{getattr(contract, "backend_kind", "python_backend")}`',
        f'- supports_json: `{bool(getattr(contract, "supports_json", False))}`',
        f'- session_model: `{getattr(contract, "session_model", "stateless")}`',
        f'- mutability: `{getattr(contract, "mutability", "read_only")}`',
    ]

    entrypoint_hint = getattr(contract, 'entrypoint_hint', None)
    if entrypoint_hint:
        lines.append(f'- entrypoint_hint: `{entrypoint_hint}`')

    lines.extend(['', '## Operation Groups', ''])
    for group in list(getattr(contract, 'operations', []) or []):
        lines.append(f'### {getattr(group, "name", "operations")}')
        description_text = getattr(group, 'description', '')
        if description_text:
            lines.extend(['', description_text, ''])
        for operation in list(getattr(group, 'operations', []) or []):
            lines.append(f'- `{getattr(operation, "name", "run")}`: {getattr(operation, "summary", "").strip()}')
            if getattr(operation, 'inputs', None):
                input_names = [item.name for item in list(getattr(operation, 'inputs', []) or [])]
                lines.append(f'  - Inputs: `{", ".join(input_names[:5])}`')
            if getattr(operation, 'examples', None):
                lines.append(f'  - Example: `{list(getattr(operation, "examples", []) or [])[0]}`')
            if getattr(operation, 'side_effects', None):
                lines.append(f'  - Side effects: {list(getattr(operation, "side_effects", []) or [""])[0]}')

    lines.extend(['', '## Safety', ''])
    safety = getattr(contract, 'safety_profile', None)
    if safety is not None:
        lines.append(f'- credential_scope: `{", ".join(list(getattr(safety, "credential_scope", []) or [])[:5]) or "none"}`')
        lines.append(f'- network_scope: `{", ".join(list(getattr(safety, "network_scope", []) or [])[:3]) or "none"}`')
        lines.append(f'- filesystem_scope: `{", ".join(list(getattr(safety, "filesystem_scope", []) or [])[:3]) or "none"}`')
        lines.append(f'- confirmation_required: `{bool(getattr(safety, "confirmation_required", False))}`')

    if references:
        lines.extend(['', '## References', ''])
        lines.extend(f'- See `{path}` for contract and supporting detail.' for path in references)

    if scripts:
        lines.extend(['', '## Helpers', ''])
        lines.extend(f'- Use `{path}` when you need a thin helper around the operation contract.' for path in scripts)

    return '\n'.join(lines).rstrip() + '\n'


def fallback_generate_skill_md_artifact(*, skill_name: str, description: str, references: list[str], scripts: list[str]) -> ArtifactFile:
    return ArtifactFile(
        path='SKILL.md',
        content=fallback_generate_skill_md(
            skill_name=skill_name,
            description=description,
            references=references,
            scripts=scripts,
        ),
        content_type='text/markdown',
        generated_from=['skill_plan', 'repo_findings'],
        status='new',
    )


def fallback_generate_methodology_skill_md_artifact(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
) -> ArtifactFile:
    return ArtifactFile(
        path='SKILL.md',
        content=fallback_generate_methodology_skill_md(
            skill_name=skill_name,
            description=description,
            task=task,
            references=references,
            scripts=scripts,
        ),
        content_type='text/markdown',
        generated_from=['skill_plan', 'repo_findings', 'methodology_guidance'],
        status='new',
    )


def fallback_generate_operation_skill_md_artifact(
    *,
    skill_name: str,
    description: str,
    contract,
    references: list[str],
    scripts: list[str],
) -> ArtifactFile:
    return ArtifactFile(
        path='SKILL.md',
        content=fallback_generate_operation_skill_md(
            skill_name=skill_name,
            description=description,
            contract=contract,
            references=references,
            scripts=scripts,
        ),
        content_type='text/markdown',
        generated_from=['skill_plan', 'operation_contract'],
        status='new',
    )
