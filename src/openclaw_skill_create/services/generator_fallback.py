from __future__ import annotations

from dataclasses import dataclass, field

from ..models.artifacts import ArtifactFile
from .domain_specificity import extract_task_domain_anchors, profile_for_skill
from .expert_dna import render_expert_dna_skill_md
from .expert_skill_studio import render_skill_program_markdown
from .expert_structure import expert_profile_for_skill
from .style_diversity import expert_style_profile_for_skill


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
    decision_probes: list[str] = field(default_factory=list)
    workflow_output_fragments: list[str] = field(default_factory=list)
    workflow_failure_signals: list[str] = field(default_factory=list)
    boundary_rules: list[str] = field(default_factory=list)
    worked_micro_examples: list[tuple[str, list[str]]] = field(default_factory=list)
    failure_patterns: list[tuple[str, list[str]]] = field(default_factory=list)
    revision_moves: list[str] = field(default_factory=list)
    output_field_guidance: list[tuple[str, list[str]]] = field(default_factory=list)
    quality_check_rubric: list[tuple[str, list[str]]] = field(default_factory=list)


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
                ('Smallest Honest Loop', ['Input', 'System response', 'Feedback', 'Repeat trigger']),
                ('Feature Cut', ['Must have', 'Supportive but optional', 'Defer', 'Cut for now']),
                ('Minimum Content Package', ['Test space', 'Encounter or toy set', 'Session length', 'Success and fail condition']),
                ('Out of Scope', ['Deferred ideas', 'Why excluded', 'Re-entry condition']),
                ('MVP Pack', ['Build recommendation', 'Playtest signal', 'Open assumptions']),
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
            decision_probes=[
                'What exactly is the MVP trying to validate, and what result would prove it wrong?',
                'Can the smallest honest loop be played without promising future systems?',
                'Which attractive feature would be painful to cut but does not prove the central design hypothesis?',
                'How much content is enough to expose the loop before scope becomes camouflage?',
                'What would count as validated, and what would force a redesign?',
            ],
            workflow_output_fragments=[
                'Validation Goal with the risky promise, expected evidence, and failure condition.',
                'Minimum Honest Loop with player input, system response, visible feedback, and repeat trigger.',
                'Feature Cut table with Core, Supportive, Later, and Cut buckets.',
                'Minimum Content Scope with events, levels, enemies, cards, scenes, or runs needed for a credible first test.',
                'Explicitly Out of Scope kill list with why each tempting idea stays out.',
                'Build Recommendation naming what to prototype first and what to test with players.',
            ],
            workflow_failure_signals=[
                'The validation question sounds like a slogan and cannot fail in a playtest.',
                'The loop depends on invisible future depth or scripted presentation.',
                'Too many systems are called core, so the MVP stops being a test.',
                'Content volume is being used to hide uncertainty.',
                'Deferred features have no re-entry condition and will creep back in.',
                'The pack cannot tell a builder what to implement first.',
            ],
            boundary_rules=[
                'This is a scope-cutting skill, not a dream-expanding skill.',
                'Do not fake the entire game with a polished vertical slice that misses the repeatable loop.',
                'Use a kill list; name what not to build as clearly as what to build.',
                'Cut aggressively when a feature does not answer the validation question.',
            ],
            worked_micro_examples=[
                (
                    'Compact MVP scope example',
                    [
                        'Premise: a cozy courier game about choosing routes through weather and social obligations.',
                        'Validation question: will route tradeoffs stay interesting when the map is tiny?',
                        'Smallest honest loop: accept delivery, choose route, absorb weather/social cost, see reputation and stamina feedback, repeat.',
                        'Cut: cosmetics, meta progression, large city map, branching story; keep only route choice, weather pressure, and one reputation consequence.',
                    ],
                )
            ],
            failure_patterns=[
                ('Fake MVP / Vertical Slice Trap', ['Symptom: the build is polished but does not test the repeatable loop.', 'Cause: presentation replaced validation.', 'Correction: reduce content and expose input, response, feedback, and repeat trigger.']),
                ('Scope Creep Through One More Core Feature', ['Symptom: every attractive idea becomes mandatory.', 'Cause: core/support/cut buckets are not enforced.', 'Correction: keep only features that answer the validation question.']),
                ('Content Hiding Uncertainty', ['Symptom: the concept needs dozens of units before it can be judged.', 'Cause: content-heavy validation hides a weak loop.', 'Correction: define the minimum content package that can reveal the truth.']),
                ('Mood Instead of Loop', ['Symptom: the pack sells tone but not repeatable play.', 'Cause: fantasy language replaced player input, system response, and feedback.', 'Correction: rewrite the smallest honest loop before adding mood or lore.']),
                ('Success Criteria Missing', ['Symptom: the team keeps building after the first test.', 'Cause: no pass/fail signal was written.', 'Correction: state what result would count as success or redesign.']),
            ],
            revision_moves=[
                'If the MVP pack is still too large, remove supportive systems before touching the core loop.',
                'If the validation question cannot fail, rewrite it as a playtest observation.',
                'If the out-of-scope list feels vague, name specific features and their re-entry condition.',
            ],
            output_field_guidance=[
                ('Validation Goal', ['Write the core question, why it matters, and what evidence would count.', 'Good output can fail; weak output is a slogan.']),
                ('Minimum Honest Loop', ['Write input, system response, feedback, and repeat trigger.', 'Good output is playable; weak output depends on future content.']),
                ('Core Features', ['Separate must-have, supportive, and cut items.', 'Good output removes desirable work; weak output keeps everything.']),
                ('Minimum Content Scope', ['Write the smallest events, levels, enemies, cards, scenes, or runs needed.', 'Good output proves enough without padding; weak output hides uncertainty with volume.']),
                ('Required Systems', ['Write each system purpose, minimum behavior, and simplification path.', 'Good output supports the MVP goal; weak output imports full production scope.']),
                ('Explicitly Out of Scope', ['List tempting exclusions and why they stay out.', 'Good output blocks creep; weak output says later without conditions.']),
                ('Main Production Risks', ['Write the scope, loop, content, and system risks that could invalidate the build.', 'Good output names risk signals before production expands.']),
                ('Build Recommendation', ['Write what to prototype first, what to test with players, and what result counts as success.', 'Good output becomes the next work order.']),
            ],
            quality_check_rubric=[
                ('Testability', ['The MVP has a success signal and a failure signal.']),
                ('Scope Discipline', ['The feature cut removes work that feels attractive but is not necessary evidence.']),
                ('Execution Readiness', ['A builder can start the first playable without rereading the original prompt.']),
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
                ('Current Loop Shape', ['Core decision', 'Feedback structure', 'Observe', 'Decide', 'Act', 'Resolve', 'Reward', 'Next-choice trigger']),
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
            decision_probes=[
                'Does this loop hold up beyond the pitch and first novelty burst?',
                'Why would the player still care after the first hour?',
                'What prevents midgame from becoming autopilot once the basics are learned?',
                'Does lategame mastery create new decisions or erase pressure?',
                'What dominant strategy would make the loop stale?',
            ],
            workflow_output_fragments=[
                'Loop Under Test with observe, decide, act, resolve, reward, and next-choice trigger.',
                'First-Hour Performance with readability, agency, and hook risks.',
                'Midgame Performance with new constraints, compounding tradeoffs, and dominant-option risks.',
                'Late-Game Performance with expansion, mutation, or collapse point.',
                'Solved-State Risks with dominant strategy, cause, and counterpressure.',
                'Reinforcement Recommendations with urgent fix, secondary fix, and next prototype test.',
            ],
            workflow_failure_signals=[
                'The loop description lists actions but not the repeated decision.',
                'The first hour works only because novelty is carrying the experience.',
                'Midgame variation changes content labels but not decisions.',
                'Lategame mastery removes the game instead of revealing deeper problems.',
                'The dominant strategy is noticed but not designed against.',
                'Rewards teach efficient autopilot while the design claims expressive play.',
            ],
            boundary_rules=[
                'This is not about greenlighting theme; it tests whether the loop survives time.',
                'Do not treat more options as better variation unless they change decisions.',
                'Prefer structural counterpressure over content padding.',
                'Do not use this for detailed numeric balancing when the structural loop is still unclear.',
            ],
            worked_micro_examples=[
                (
                    'Compact loop stress example',
                    [
                        'Loop: choose a combat card, spend stamina, resolve enemy intent, earn upgrade currency, repeat.',
                        'First-hour risk: cards are readable but enemy intent is too abstract to feel causal.',
                        'Midgame risk: one stamina-efficient build dominates because penalties are too weak.',
                        'Reinforcement fix: add enemies that punish repeated low-risk choices and reward adapting to state.',
                    ],
                )
            ],
            failure_patterns=[
                ('Novelty-Only Start', ['Symptom: the first session feels fine but repetition arrives fast.', 'Cause: premise is carrying weak decisions.', 'Correction: expose meaningful tradeoffs within the first hour.']),
                ('Midgame Autopilot', ['Symptom: players learn a stable routine and stop thinking.', 'Cause: constraints scale numbers but not decisions.', 'Correction: add state changes that force adaptation.']),
                ('Progression Without New Problems', ['Symptom: upgrades make the loop easier but not deeper.', 'Cause: progression removes pressure.', 'Correction: make mastery reveal new constraints or costs.']),
                ('Cosmetic Options / Surface Variation', ['Symptom: content changes but decisions stay identical.', 'Cause: variation is cosmetic or statistical.', 'Correction: require variation to change read, tradeoff, consequence, or adaptation.']),
                ('Dominant Strategy', ['Symptom: one option becomes correct in most states.', 'Cause: rewards and penalties do not create enough counterpressure.', 'Correction: add structural risk, asymmetry, or delayed consequence.']),
                ('Rewarding Autopilot', ['Symptom: rewards train the player to repeat a safe routine.', 'Cause: reinforcement points at efficiency instead of decisions.', 'Correction: reward adaptation, timing, or state-aware choices.']),
                ('Mastery Removes the Game', ['Symptom: skillful play eliminates tension too early.', 'Cause: no counterpressure meets mastery.', 'Correction: introduce risk, uncertainty, or asymmetric options.']),
            ],
            revision_moves=[
                'If the loop is too easy to solve, add counterpressure before adding more content.',
                'If variation is cosmetic, rewrite it as a decision-changing state difference.',
                'If reinforcement rewards the wrong behavior, change the reward before changing player instructions.',
            ],
            output_field_guidance=[
                ('Loop Under Test', ['Write the repeated choice and feedback chain.', 'Good output names a loop; weak output lists disconnected actions.']),
                ('First-Hour Performance', ['Write what works, what is weak, and the main hook risk.', 'Good output names a readable cause-effect chain.']),
                ('Midgame Performance', ['Write what sustains interest and where repetition starts.', 'Good output distinguishes new decisions from larger numbers.']),
                ('Solved-State Risks', ['Write the dominant strategy and why it appears.', 'Good output names counterpressure; weak output says add variety.']),
                ('Reinforcement Recommendations', ['Write the most urgent fix and the next prototype test.', 'Good output changes the next test plan.']),
            ],
            quality_check_rubric=[
                ('Time Horizon', ['First hour, midgame, and lategame each have distinct stress signals.']),
                ('Decision Variation', ['Variation changes player decisions, not just presentation.']),
                ('Reinforcement Fit', ['Rewards train the intended behavior and player fantasy.']),
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
            decision_probes=[
                'What choices hurt in an interesting way?',
                'What can the player never maximize all at once?',
                'Which pressure relationship is visible early enough for planning?',
                'How does the player notice failure before the death spiral is complete?',
                'What emotional fantasy should the resource loop make legible?',
            ],
            workflow_output_fragments=[
                'Variable Web with resources, sinks, converters, buffers, caps, and player-visible signals.',
                'Variable Role table with source, sink, converter, buffer, cap, signal, cost, or pressure.',
                'Pressure Relationships with cause, effect, timing, and player-visible warning.',
                'Primary Decision Tensions with tradeoff, pressure, and viable responses.',
                'Positive and Negative Loops with compounding force and counterpressure.',
                'Failure Recovery with early warning, recovery action, and lasting consequence.',
                'Emotional Fantasy Alignment with intended feeling and loop mismatch to fix.',
            ],
            workflow_failure_signals=[
                'The variable web is a list of meters with no player-facing decision.',
                'Variables have labels but no behavioral role.',
                'Pressure relationships punish the player without readable warning.',
                'The loop creates bookkeeping instead of painful tradeoffs.',
                'Only positive loops exist, causing runaway snowballing.',
                'Recovery either erases consequences or creates an unrecoverable death spiral.',
                'The spreadsheet balances while the emotional fantasy disappears.',
            ],
            boundary_rules=[
                'Use this when the game depends on interacting pressures, not one simple currency.',
                'Only include a variable if it changes player behavior.',
                'Think in relationships, not isolated meters.',
                'Prefer a few strong tensions over many decorative subsystems.',
            ],
            worked_micro_examples=[
                (
                    'Compact pressure-web example',
                    [
                        'Fantasy: running a tiny frontier clinic under public scrutiny.',
                        'Variable web: money funds supplies, trust increases patients, fatigue raises mistake risk, reputation attracts donors and scrutiny.',
                        'Positive loop: trust brings more patients and funding; negative loop: more patients increase fatigue and public risk.',
                        'Failure recovery: close early to reduce fatigue, losing trust but preserving long-term stability.',
                    ],
                )
            ],
            failure_patterns=[
                ('Decorative Resources / Variable Web Sprawl', ['Symptom: bars exist but do not change choices.', 'Cause: variables lack player-facing roles.', 'Correction: cut or connect each variable to a decision tension.']),
                ('No Real Tradeoff', ['Symptom: the player can optimize everything at once.', 'Cause: pressure relationships do not conflict.', 'Correction: add opportunity cost or mutually exclusive responses.']),
                ('One Dominant Currency', ['Symptom: every variable collapses into the same best resource.', 'Cause: conversion rates erase multidimensional tension.', 'Correction: make at least one pressure non-convertible or costly to convert.']),
                ('Positive-Loop Runaway', ['Symptom: success removes all hardship.', 'Cause: positive loops lack counterpressure.', 'Correction: add scrutiny, maintenance, decay, or risk.']),
                ('Death Spiral / Punishment Without Agency', ['Symptom: players suffer penalties without recovery choices.', 'Cause: failure is hidden or irreversible.', 'Correction: add early warning and costly recovery tools.']),
                ('Hidden Pressure Relationships', ['Symptom: outcomes change but players cannot tell why.', 'Cause: pressure links are invisible or too delayed.', 'Correction: expose cause and effect through readable signals.']),
                ('Emotionless Resource Loop / Fantasy-System Mismatch', ['Symptom: math is stable but feels emotionally wrong.', 'Cause: resource pressure contradicts fantasy.', 'Correction: align variables with the intended feeling.']),
            ],
            revision_moves=[
                'If the resource list is bloated, cut variables without player-facing roles.',
                'If the loop snowballs, add counterpressure tied to success.',
                'If pressure feels arbitrary, add visible warning before consequences land.',
            ],
            output_field_guidance=[
                ('Variable Web', ['Write resources, sinks, converters, buffers, and signals.', 'Good output names decisions; weak output lists meters.']),
                ('Core Resources / Pressures', ['Write the player-facing resources and pressures that actually change behavior.', 'Good output filters decorative variables.']),
                ('Pressure Relationships', ['Write cause, effect, and player-visible signal.', 'Good output shows how variables push against each other.']),
                ('Primary Decision Tensions', ['Write the recurring sacrifices the player cannot avoid.', 'Good output has at least two viable responses.']),
                ('Positive Loop', ['Write what compounds and the snowball risk.', 'Good output names how success accelerates.']),
                ('Negative / Counter Loops', ['Write the brake, cost, decay, or counterpressure that prevents runaway success.', 'Good output creates rhythm without static punishment.']),
                ('Negative Loop', ['Write the brake, cost, decay, or counterpressure.', 'Good output creates rhythm rather than static punishment.']),
                ('Failure Recovery', ['Write early warning, recovery action, and lasting consequence.', 'Good output avoids both death spiral and free reset.']),
                ('Emotional Fantasy', ['Write intended feeling and mismatch to fix.', 'Good output connects math to fantasy.']),
                ('Design Recommendations', ['Write what to strengthen, simplify, and prototype next.', 'Good output turns the pressure web into a next design move.']),
            ],
            quality_check_rubric=[
                ('Player-Facing Roles', ['Every variable changes a visible choice or signal.']),
                ('Feedback Balance', ['Positive and negative loops both shape rhythm.']),
                ('Fantasy Alignment', ['Resource pressure produces the intended feeling, not just balanced numbers.']),
            ],
        )
    return None


def _render_expert_blueprint_skill_md(
    *,
    skill_name: str,
    description: str,
    task: str,
    blueprint: DomainSkillBlueprint,
    references: list[str],
    scripts: list[str],
) -> str:
    output_guidance = {heading: bullets for heading, bullets in blueprint.output_field_guidance}
    output_guidance_items = list(blueprint.output_field_guidance)
    style_profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    opening = (
        style_profile.opening_frame
        if style_profile is not None and style_profile.opening_frame
        else 'Use this skill to turn the requested methodology into a concrete, task-facing decision artifact.'
    )
    labels = list(getattr(style_profile, 'workflow_label_set', []) or [])
    if skill_name == 'concept-to-mvp-pack':
        workflow_labels = ('Test', 'Keep / Cut', 'Package', 'Watch scope')
        overview = 'Turn the concept into a falsifiable MVP proof: the loop to test, the work to keep, the cuts to make, and the package that can start now.'
    elif skill_name == 'decision-loop-stress-test':
        workflow_labels = ('Stress', 'Watch', 'Break / Reinforce', 'Fix structurally')
        overview = 'Pressure-test the loop by phase, expose where novelty collapses, and turn the failure point into a structural fix rather than content padding.'
    elif skill_name == 'simulation-resource-loop-design':
        workflow_labels = ('Map', 'Tension', 'Loop output', 'Correct')
        overview = 'Map variables into visible player pressure, then shape loops, recovery, and fantasy alignment so the system creates real decisions.'
    else:
        workflow_labels = (
            labels[0].title() if len(labels) > 0 else 'Act',
            labels[1].title() if len(labels) > 1 else 'Question',
            labels[2].title() if len(labels) > 2 else 'Deliver',
            labels[3].title() if len(labels) > 3 else 'Guard',
        )
        overview = 'Convert the request into concrete decisions, outputs, and guardrails without widening the skill beyond its task.'
    lines = [
        '---',
        f'name: {skill_name}',
        f'description: {description}',
        '---',
        '',
        f'# {skill_name}',
        '',
        opening,
        '',
        '## Overview',
        '',
        overview,
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
        probe = blueprint.decision_probes[(index - 1) % len(blueprint.decision_probes)] if blueprint.decision_probes else ''
        output_fragment = (
            blueprint.workflow_output_fragments[(index - 1) % len(blueprint.workflow_output_fragments)]
            if blueprint.workflow_output_fragments
            else ''
        )
        failure_signal = (
            blueprint.workflow_failure_signals[(index - 1) % len(blueprint.workflow_failure_signals)]
            if blueprint.workflow_failure_signals
            else ''
        )
        if bullets:
            action = bullets[0]
            if len(bullets) > 1:
                action = f'{action} {bullets[1]}'
            lines.append(f'- {workflow_labels[0]}: {action}')
        if probe:
            lines.append(f'- {workflow_labels[1]}: {probe}')
        if output_fragment:
            lines.append(f'- {workflow_labels[2]}: {output_fragment}')
        if failure_signal:
            lines.append(f'- {workflow_labels[3]}: {failure_signal}')
        lines.append('')

    if blueprint.boundary_rules:
        lines.extend(['## Boundary Rules', ''])
        lines.extend(f'- {item}' for item in blueprint.boundary_rules)
        lines.append('')

    if blueprint.worked_micro_examples:
        lines.extend(['## Worked Micro-Examples', ''])
        heading, bullets = blueprint.worked_micro_examples[0]
        lines.extend([f'### {heading}', ''])
        for bullet in bullets[:4]:
            lines.append(f'- {bullet}')
        lines.append('')

    lines.extend(['## Output Format', '', '```markdown'])
    for index, (heading, fields) in enumerate(blueprint.output_schema):
        lines.extend([f'## {heading}'])
        guidance_heading, guidance = output_guidance_items[index] if index < len(output_guidance_items) else (heading, [])
        guidance = output_guidance.get(heading, guidance)
        lines.append(f'- Field use: {guidance_heading}')
        for field in fields:
            lines.append(f'- {field}: <fill in>')
        if guidance:
            good = guidance[1] if len(guidance) > 1 else guidance[0]
            weak = guidance[2] if len(guidance) > 2 else 'Weak output stays abstract or leaves the field unactionable.'
            lines.append(f'- Good: {good}')
            lines.append(f'- Weak: {weak}')
        lines.append('')
    lines.extend(['```'])

    lines.extend(['## Quality Checks', ''])
    lines.extend(f'- {item}' for item in blueprint.quality_check_matrix)
    if blueprint.quality_check_rubric:
        lines.append('')
        lines.append('### Quality Check Rubric')
        lines.append('')
        for heading, bullets in blueprint.quality_check_rubric:
            lines.extend([f'#### {heading}', ''])
            for bullet in bullets:
                lines.append(f'- {bullet}')
            lines.append('')
    lines.extend([
        '',
        '## Common Pitfalls: Failure Patterns and Fixes',
        '',
    ])
    if blueprint.failure_patterns:
        for heading, bullets in blueprint.failure_patterns:
            lines.extend([f'### {heading}', ''])
            symptom = bullets[0] if bullets else heading
            cause = bullets[1] if len(bullets) > 1 else 'The workflow skipped the hard design judgment.'
            correction = bullets[2] if len(bullets) > 2 else 'Return to the relevant workflow step and make the cut explicit.'
            lines.append(f'- Symptom: {symptom}')
            lines.append(f'- Cause: {cause}')
            lines.append(f'- Correction: {correction}')
            lines.append('')
    else:
        lines.extend(f'- {item}' for item in blueprint.pitfall_taxonomy)
    if blueprint.revision_moves:
        lines.extend(['## Revision Moves', ''])
        lines.extend(f'- {item}' for item in blueprint.revision_moves)
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
    program_content = render_skill_program_markdown(
        skill_name=skill_name,
        description=description,
        task=task,
        references=references,
        scripts=scripts,
    )
    if program_content is not None:
        return program_content

    expert_dna_content = render_expert_dna_skill_md(
        skill_name=skill_name,
        description=description,
        task=task,
        references=references,
        scripts=scripts,
    )
    if expert_dna_content is not None:
        return expert_dna_content

    expert_blueprint = _expert_game_design_blueprint(skill_name=skill_name, task=task)
    if expert_blueprint is not None:
        return _render_expert_blueprint_skill_md(
            skill_name=skill_name,
            description=description,
            task=task,
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
