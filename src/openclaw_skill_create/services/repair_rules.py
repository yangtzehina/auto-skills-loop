from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Optional

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.plan import SkillPlan
from .evaluation_scaffold import generate_eval_artifacts
from .validator_rules import (
    REFERENCE_PLACEHOLDER_MARKERS,
    REFERENCE_REQUIRED_SECTIONS,
    SCRIPT_PLACEHOLDER_MARKERS,
    SCRIPT_STRONG_TOKENS,
    SCRIPT_SUFFIX_HINTS,
    SCRIPT_WRAPPER_MARKERS,
)


ALLOWED_FRONTMATTER_KEYS = ('name', 'description')
MAX_REFERENCE_KEY_POINTS = 6
MAX_REFERENCE_SNIPPET_LINES = 12


def clone_artifacts(artifacts: Artifacts) -> Artifacts:
    return Artifacts(files=[ArtifactFile.model_validate(file.model_dump()) for file in artifacts.files])


def find_artifact(artifacts: Artifacts, path: str) -> Optional[ArtifactFile]:
    for file in artifacts.files:
        if file.path == path:
            return file
    return None


def replace_artifact(artifacts: Artifacts, new_file: ArtifactFile) -> None:
    for idx, file in enumerate(artifacts.files):
        if file.path == new_file.path:
            artifacts.files[idx] = new_file
            return
    artifacts.files.append(new_file)


def remove_artifact(artifacts: Artifacts, path: str) -> None:
    artifacts.files = [file for file in artifacts.files if file.path != path]


def build_minimal_frontmatter(skill_name: str, description: str) -> str:
    return f"---\nname: {skill_name}\ndescription: {description}\n---\n"


def extract_body_without_frontmatter(content: str) -> str:
    if not content.startswith('---\n'):
        return content.strip()
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return content.strip()
    return parts[2].strip()


def repair_skill_md_frontmatter(*, content: str, skill_name: str, description: str) -> str:
    body = extract_body_without_frontmatter(content)
    frontmatter = build_minimal_frontmatter(skill_name, description)
    if body:
        return f"{frontmatter}\n{body}\n"
    return f"{frontmatter}\n"


def repair_skill_md_budget(*, content: str, max_lines: int) -> str:
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content if content.endswith('\n') else content + '\n'
    trimmed = lines[:max_lines]
    return '\n'.join(trimmed).rstrip() + '\n'


def _missing_reference_lines(skill_md_content: str, reference_paths: Iterable[str]) -> list[str]:
    missing = []
    for path in reference_paths:
        if f'`{path}`' not in skill_md_content:
            missing.append(f'- See `{path}` for more detail.')
    return missing


def repair_reference_navigation(*, skill_md_content: str, artifacts: Artifacts) -> str:
    reference_paths = [file.path for file in artifacts.files if file.path.startswith('references/')]
    if not reference_paths:
        return skill_md_content if skill_md_content.endswith('\n') else skill_md_content + '\n'

    missing = _missing_reference_lines(skill_md_content, reference_paths)
    if not missing:
        return skill_md_content if skill_md_content.endswith('\n') else skill_md_content + '\n'

    base = skill_md_content.rstrip() + '\n\n## References\n\n'
    return base + '\n'.join(missing) + '\n'


def drop_unexpected_files(*, artifacts: Artifacts, skill_plan: SkillPlan) -> None:
    allowed = {file.path for file in skill_plan.files_to_create}
    allowed.update(file.path for file in skill_plan.files_to_update)
    allowed.update(file.path for file in skill_plan.files_to_keep)
    artifacts.files = [file for file in artifacts.files if file.path in allowed]


def _reference_title(path: str) -> str:
    stem = Path(path).stem.replace('_', ' ').replace('-', ' ').strip()
    return stem.title() or 'Reference'


def _clean_reference_lines(raw: str) -> list[str]:
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in REFERENCE_REQUIRED_SECTIONS:
            continue
        if any(marker in stripped for marker in REFERENCE_PLACEHOLDER_MARKERS):
            continue
        if stripped == '## Snippet':
            continue
        if stripped.startswith('```'):
            continue
        if stripped.startswith('- Source repo:') or stripped.startswith('- Source file:'):
            continue
        if stripped.startswith('#'):
            normalized = stripped.lstrip('#').strip()
            if normalized:
                lines.append(normalized)
            continue
        normalized = stripped.lstrip('-*0123456789. ').strip()
        if normalized:
            lines.append(normalized)
    return lines


def _build_reference_overview(path: str, lines: list[str]) -> str:
    if lines:
        return lines[0]
    return f'This reference summarizes `{path}`.'


def _build_reference_key_points(lines: list[str]) -> list[str]:
    points = []
    seen = set()
    for line in lines:
        if not line or line in seen:
            continue
        seen.add(line)
        points.append(line)
        if len(points) >= MAX_REFERENCE_KEY_POINTS:
            break
    return points


def _build_reference_snippet(lines: list[str]) -> str:
    return '\n'.join(lines[:MAX_REFERENCE_SNIPPET_LINES]).strip()


def build_repaired_reference_content(*, path: str, raw: str) -> str:
    title = _reference_title(path)
    lines = _clean_reference_lines(raw)
    overview = _build_reference_overview(path, lines)
    key_points = _build_reference_key_points(lines)
    snippet = _build_reference_snippet(lines)

    blocks = [f'# {title}', '', f'- Source file: `{path}`', '', '## Overview', '', overview, '', '## Key points', '']

    if key_points:
        for point in key_points:
            blocks.append(f'- {point}')
    else:
        blocks.append(f'- Review `{path}` for implementation-specific details.')

    if snippet:
        blocks.extend(['', '## Snippet', '', '```text', snippet, '```'])

    return '\n'.join(blocks).rstrip() + '\n'


def _script_language_hint(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        '.py': 'python',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.go': 'go',
        '.rs': 'rust',
    }.get(suffix, 'script')


def _script_entrypoint_line(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == '.py':
        return 'def main() -> int:'
    if suffix in {'.sh', '.bash', '.zsh'}:
        return 'main() {'
    if suffix in {'.js', '.ts'}:
        return 'function main() {'
    return '# entrypoint'


def _minimal_script_placeholder(path: str) -> str:
    filename = Path(path).name
    suffix = Path(path).suffix.lower()
    language = _script_language_hint(path)
    if suffix == '.py':
        return (
            f'"""Minimal placeholder for {filename}."""\n\n'
            'def main() -> int:\n'
            f'    raise NotImplementedError("Implement {filename}.")\n\n'
            'if __name__ == "__main__":\n'
            '    raise SystemExit(main())\n'
        )
    if suffix in {'.sh', '.bash', '.zsh'}:
        return (
            '#!/usr/bin/env bash\n'
            'set -euo pipefail\n\n'
            'main() {\n'
            f'  echo "TODO: implement {filename}" >&2\n'
            '  exit 1\n'
            '}\n\n'
            'main "$@"\n'
        )
    if suffix in {'.js', '.ts'}:
        return (
            f'// Minimal placeholder for {filename}.\n\n'
            'function main() {\n'
            f'  throw new Error("Implement {filename}.");\n'
            '}\n\n'
            'main();\n'
        )
    return (
        f'# Minimal {language} placeholder for {filename}.\n'
        f'# TODO: implement {filename}.\n'
    )


def _extract_fenced_code(raw: str) -> str:
    match = re.search(r"```[A-Za-z0-9_+-]*\n(.*?)\n```", raw, flags=re.DOTALL)
    if not match:
        return ''
    return match.group(1).strip('\n')



def _script_non_empty_lines(content: str) -> list[str]:
    return [line.strip() for line in content.splitlines() if line.strip()]



def _script_code_signal_count(path: str, content: str) -> int:
    score = 0
    stripped = content.strip()
    if not stripped:
        return 0
    if stripped.startswith('#!'):
        score += 2
    for token in SCRIPT_STRONG_TOKENS:
        if token in stripped:
            score += 1
    suffix = Path(path).suffix.lower()
    if suffix == '.py':
        try:
            compile(content, path, 'exec')
            score += 2
        except SyntaxError:
            pass
        except Exception:
            score += 1
    elif suffix in SCRIPT_SUFFIX_HINTS:
        if any(token in stripped for token in ('=', '(', ')', '{', '}', '$', ';')):
            score += 1
    return score


def _recover_script_candidate(path: str, raw: str) -> str:
    fenced = _extract_fenced_code(raw)
    if fenced and _script_code_signal_count(path, fenced) >= 2:
        return fenced if fenced.endswith('\n') else fenced + '\n'

    stripped_lines = [line for line in raw.splitlines()]
    if any(marker in raw.lower() for marker in SCRIPT_WRAPPER_MARKERS):
        candidate_lines = []
        for line in stripped_lines:
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped:
                if candidate_lines:
                    candidate_lines.append('')
                continue
            if stripped.startswith('```'):
                continue
            if any(marker in lowered for marker in SCRIPT_WRAPPER_MARKERS):
                continue
            if stripped.startswith('# ') or stripped.startswith('## ') or stripped.startswith('- '):
                continue
            candidate_lines.append(line)
        candidate = '\n'.join(candidate_lines).strip('\n')
        if candidate and _script_code_signal_count(path, candidate) >= 2:
            return candidate if candidate.endswith('\n') else candidate + '\n'

    return ''



def script_needs_rebuild(path: str, raw: str) -> bool:
    stripped = raw.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    non_empty_lines = _script_non_empty_lines(raw)
    placeholder_line_count = sum(
        1 for line in non_empty_lines if any(marker in line.lower() for marker in SCRIPT_PLACEHOLDER_MARKERS)
    )
    if placeholder_line_count >= max(1, len(non_empty_lines) - 1):
        return True
    if any(marker in lower for marker in SCRIPT_WRAPPER_MARKERS) and _script_code_signal_count(path, raw) <= 1:
        return True
    markdown_like_lines = sum(
        1
        for line in non_empty_lines[:8]
        if line.startswith('# ') or line.startswith('## ') or line.startswith('- ') or line.startswith('* ')
    )
    if markdown_like_lines >= max(2, len(non_empty_lines[:8]) // 2) and _script_code_signal_count(path, raw) == 0:
        return True
    return False



def build_repaired_script_content(*, path: str, raw: str) -> str:
    if not script_needs_rebuild(path, raw):
        return raw if raw.endswith('\n') else raw + '\n'

    recovered = _recover_script_candidate(path, raw)
    if recovered:
        return recovered

    return _minimal_script_placeholder(path)


def build_repaired_eval_content(
    *,
    path: str,
    request: Any,
    skill_plan: SkillPlan,
    reuse_decision: Any = None,
) -> str:
    generated = {
        artifact.path: artifact.content
        for artifact in generate_eval_artifacts(
            request=request,
            skill_plan=skill_plan,
            reuse_decision=reuse_decision,
        )
    }
    return generated.get(path, '{}\n')


def repair_missing_planned_files(
    *,
    artifacts: Artifacts,
    skill_plan: SkillPlan,
    request: Any = None,
    reuse_decision: Any = None,
) -> None:
    for planned in skill_plan.files_to_create:
        if find_artifact(artifacts, planned.path) is None:
            if planned.path == 'SKILL.md':
                replace_artifact(
                    artifacts,
                    ArtifactFile(
                        path='SKILL.md',
                        content='',
                        content_type='text/markdown',
                        generated_from=['repair'],
                        status='repaired',
                    ),
                )
            elif planned.path.startswith('references/'):
                replace_artifact(
                    artifacts,
                    ArtifactFile(
                        path=planned.path,
                        content=build_repaired_reference_content(path=planned.path, raw=''),
                        content_type='text/markdown',
                        generated_from=['repair'],
                        status='repaired',
                    ),
                )
            elif planned.path.startswith('scripts/'):
                replace_artifact(
                    artifacts,
                    ArtifactFile(
                        path=planned.path,
                        content=build_repaired_script_content(path=planned.path, raw=''),
                        content_type='text/plain',
                        generated_from=['repair'],
                        status='repaired',
                    ),
                )
            elif planned.path.startswith('evals/') and planned.path.endswith('.json'):
                replace_artifact(
                    artifacts,
                    ArtifactFile(
                        path=planned.path,
                        content=build_repaired_eval_content(
                            path=planned.path,
                            request=request,
                            skill_plan=skill_plan,
                            reuse_decision=reuse_decision,
                        ),
                        content_type='application/json',
                        generated_from=['repair'],
                        status='repaired',
                    ),
                )
            else:
                replace_artifact(
                    artifacts,
                    ArtifactFile(
                        path=planned.path,
                        content='',
                        content_type='text/plain',
                        generated_from=['repair'],
                        status='repaired',
                    ),
                )
