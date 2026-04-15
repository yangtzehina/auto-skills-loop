from __future__ import annotations

from ..models.artifacts import ArtifactFile
from .domain_specificity import extract_task_domain_anchors, profile_for_skill


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
