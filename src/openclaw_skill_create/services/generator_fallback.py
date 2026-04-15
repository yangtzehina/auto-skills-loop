from __future__ import annotations

from ..models.artifacts import ArtifactFile


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
    subject = task.strip() or skill_name.replace('-', ' ')
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
        f'This skill helps Codex handle: {subject}',
        '',
        'The goal is not to restate the request. The goal is to transform it into a repeatable method: clarify the decision, run the workflow, produce a concrete output, and catch common failure modes before they leak into the final answer.',
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
        '1. Name the real job.',
        '   - Convert the user request into one sentence that says what decision or artifact must exist at the end.',
        '   - Separate the desired outcome from any accidental phrasing in the prompt.',
        '2. Identify the operating context.',
        '   - Capture audience, constraints, available inputs, missing context, and risk level.',
        '   - Mark anything that should remain out of scope.',
        '3. Build the working frame.',
        '   - Choose 3-5 criteria that determine whether the output is good.',
        '   - Turn abstract goals into concrete checks.',
        '4. Run the method.',
        '   - Work through the criteria in order.',
        '   - Make tradeoffs visible instead of hiding them inside prose.',
        '   - Keep intermediate judgments short and grounded in the provided context.',
        '5. Produce the artifact.',
        '   - Use the output template below.',
        '   - Make the result directly usable, not just descriptive.',
        '6. Run the guardrail pass.',
        '   - Check for prompt echo, unsupported certainty, missing constraints, and vague recommendations.',
        '   - If a blocker appears, report it instead of pretending the method succeeded.',
        '',
        '## Output Format',
        '',
        'Use this structure unless the user requested a different one:',
        '',
        '```markdown',
        '## Goal',
        '<One sentence describing the concrete decision or artifact.>',
        '',
        '## Context',
        '- Audience: <who this is for>',
        '- Constraints: <hard limits>',
        '- Non-goals: <what not to solve>',
        '',
        '## Method',
        '1. <Step name>: <finding or action>',
        '2. <Step name>: <finding or action>',
        '3. <Step name>: <finding or action>',
        '',
        '## Output',
        '<The actual designed artifact, decision, checklist, or recommendation.>',
        '',
        '## Quality Checks',
        '- <Check 1>',
        '- <Check 2>',
        '- <Check 3>',
        '',
        '## Open Questions',
        '- <Only include questions that materially change the result.>',
        '```',
        '',
        '## Quality Checks',
        '',
        '- The body must do real work; it cannot simply repeat the original prompt.',
        '- The workflow must produce a concrete artifact or decision.',
        '- The output must include the user-facing template or structured result.',
        '- Tradeoffs and failure risks must be visible.',
        '- The final answer should be usable by another agent without rereading the entire conversation.',
        '',
        '## Common Pitfalls',
        '',
        '- Prompt echo: copying the request into the description and leaving the body generic.',
        '- False completion: saying the skill is ready while omitting the workflow or template.',
        '- Over-broad advice: giving generic design principles instead of task-shaped steps.',
        '- Hidden assumptions: making a recommendation without naming constraints or uncertainty.',
        '- Missing guardrails: failing to include when not to use the method or how to reject a bad result.',
    ]
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
