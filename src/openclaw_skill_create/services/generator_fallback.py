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
    ]

    if references:
        lines.extend(['', '## References', ''])
        lines.extend(f'- See `{path}` for more detail.' for path in references)

    if scripts:
        lines.extend(['', '## Scripts', ''])
        lines.extend(f'- Use `{path}` when the workflow requires this helper.' for path in scripts)

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
