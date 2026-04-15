from __future__ import annotations

import re


_TASK_PREFIX_PATTERNS = (
    r'^(build|create|generate|write|make)\s+(a|an|the)\s+repo[- ]grounded\s+skill\s+for\s+',
    r'^(build|create|generate|write|make)\s+(a|an|the)\s+skill\s+for\s+',
    r'^(build|create|generate|write|make)\s+repo[- ]grounded\s+workflow\s+for\s+',
)


def _normalize_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text or '').strip())


def _fallback_capability(skill_name: str) -> str:
    words = _normalize_spaces(skill_name.replace('-', ' ').replace('_', ' '))
    if not words:
        return 'Repo-grounded workflow support'
    return words[:1].upper() + words[1:]


def _derive_capability(task: str, skill_name: str) -> str:
    cleaned = _normalize_spaces(task).rstrip('.')
    if not cleaned:
        return _fallback_capability(skill_name)
    lowered = cleaned.lower()
    for pattern in _TASK_PREFIX_PATTERNS:
        candidate = re.sub(pattern, '', lowered, count=1).strip()
        if candidate and candidate != lowered:
            cleaned = candidate
            break
    cleaned = cleaned.strip(' .;:-')
    if not cleaned:
        return _fallback_capability(skill_name)
    return cleaned[:1].upper() + cleaned[1:]


def build_trigger_aware_skill_description(*, skill_name: str, task: str = '') -> str:
    capability = _derive_capability(task, skill_name)
    trigger = capability[:1].lower() + capability[1:]
    return f'{capability}; use when a repo-backed task needs {trigger}.'
