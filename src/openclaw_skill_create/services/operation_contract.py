from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..models.artifacts import ArtifactFile
from ..models.operation import OperationContract, OperationGroup, OperationInputSpec, OperationSpec, SafetyProfile


_CLI_SIGNAL_PATTERNS = (
    re.compile(r"\bclick\.(?:group|command)\b", re.IGNORECASE),
    re.compile(r"\btyper\.Typer\b", re.IGNORECASE),
    re.compile(r"\bargparse\.ArgumentParser\b", re.IGNORECASE),
    re.compile(r"\badd_parser\s*\(", re.IGNORECASE),
    re.compile(r"\bUse:\s*[\"'][^\"']+[\"']", re.IGNORECASE),
    re.compile(r"@[\w\.]+\.command\s*\(", re.IGNORECASE),
)
_BACKEND_SIGNAL_PATTERNS = (
    re.compile(r"\bclass\s+\w+(?:Client|Service|Backend)\b"),
    re.compile(r"\bdef\s+\w+_client\b"),
    re.compile(r"\bdef\s+\w+_service\b"),
    re.compile(r"\brequests\.(?:get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    re.compile(r"\bhttpx\.(?:get|post|put|patch|delete)\s*\(", re.IGNORECASE),
)
_JSON_PATTERNS = (
    re.compile(r"--json\b", re.IGNORECASE),
    re.compile(r"\bjson\.dumps\s*\(", re.IGNORECASE),
    re.compile(r"application/json", re.IGNORECASE),
    re.compile(r"\bresponse_model\b", re.IGNORECASE),
)
_SESSION_PATTERNS = (
    re.compile(r"\bsession\b", re.IGNORECASE),
    re.compile(r"\brepl\b", re.IGNORECASE),
    re.compile(r"\binteractive\b", re.IGNORECASE),
    re.compile(r"\blogin\b", re.IGNORECASE),
    re.compile(r"\bconnect\b", re.IGNORECASE),
)
_NETWORK_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\brequests\.", re.IGNORECASE),
    re.compile(r"\bhttpx\.", re.IGNORECASE),
    re.compile(r"\bfetch\s*\(", re.IGNORECASE),
)
_EXTERNAL_PROCESS_PATTERNS = (
    re.compile(r"\bsubprocess\.", re.IGNORECASE),
    re.compile(r"\bos\.system\s*\(", re.IGNORECASE),
    re.compile(r"\bPopen\s*\(", re.IGNORECASE),
)
_CREDENTIAL_PATTERNS = (
    re.compile(r"\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|ACCESS_KEY))\b"),
    re.compile(r"\bos\.environ\[['\"]([A-Z0-9_]+)['\"]\]"),
    re.compile(r"\bprocess\.env\.([A-Z0-9_]+)"),
)
_WRITE_PATTERNS = (
    re.compile(r"\bwrite_text\s*\(", re.IGNORECASE),
    re.compile(r"\bmkdir\s*\(", re.IGNORECASE),
    re.compile(r"\bopen\s*\([^,\n]+,\s*['\"][wa+]", re.IGNORECASE),
    re.compile(r"\bunlink\s*\(", re.IGNORECASE),
    re.compile(r"\bos\.remove\s*\(", re.IGNORECASE),
)
_MUTATING_VERBS = {"create", "update", "delete", "remove", "write", "apply", "install", "deploy", "set", "save", "push"}
_READ_ONLY_VERBS = {"list", "show", "get", "inspect", "read", "check", "validate", "review", "audit", "describe"}
_COMMAND_PATTERNS = (
    re.compile(r"@[\w\.]+\.command\s*\(\s*[\"'](?P<name>[^\"']+)[\"']\s*\)", re.IGNORECASE),
    re.compile(r"@[\w\.]+\.command\s*\(\s*\)", re.IGNORECASE),
    re.compile(r"\badd_parser\s*\(\s*[\"'](?P<name>[^\"']+)[\"']\s*\)", re.IGNORECASE),
    re.compile(r"\bUse:\s*[\"'](?P<name>[a-z0-9:_-]+)(?:\s+[a-z0-9:_-]+)?[\"']", re.IGNORECASE),
)
_FLAG_PATTERN = re.compile(r"--([a-z0-9][a-z0-9-]*)", re.IGNORECASE)


def _path_has_cli_hint(path: str) -> bool:
    normalized = str(path or "").strip().lower()
    pure = Path(normalized)
    parts = {part for part in pure.parts}
    stem = pure.stem
    return (
        stem == 'cli'
        or any(part == 'cli' for part in parts)
        or normalized.startswith('bin/')
        or normalized.endswith('/cli.py')
        or normalized.endswith('/cli.sh')
    )


def _selected_files(repo_context: Any) -> list[dict[str, Any]]:
    if isinstance(repo_context, dict):
        return list(repo_context.get("selected_files", []) or [])
    return list(getattr(repo_context, "selected_files", []) or [])


def _repo_findings_repos(repo_findings: Any) -> list[Any]:
    if isinstance(repo_findings, dict):
        return list(repo_findings.get("repos", []) or [])
    return list(getattr(repo_findings, "repos", []) or [])


def _preview(item: dict[str, Any]) -> str:
    absolute_path = item.get("absolute_path")
    if absolute_path:
        try:
            return Path(absolute_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    return str(item.get("preview", "") or "")


def _iter_text_samples(repo_context: Any) -> list[tuple[str, str]]:
    return [(str(item.get("path", "")), _preview(item)) for item in _selected_files(repo_context)]


def detect_skill_archetype(*, request: Any, repo_context: Any, repo_findings: Any) -> str:
    explicit = str(getattr(request, "skill_archetype", "auto") or "auto").strip().lower()
    if explicit in {"guidance", "operation_backed", "methodology_guidance"}:
        return explicit

    text_samples = _iter_text_samples(repo_context)
    has_cli = False
    has_backend = False
    has_multi_step_surface = False

    for path, content in text_samples:
        lowered_path = path.lower()
        if _path_has_cli_hint(lowered_path):
            has_cli = True
        if any(pattern.search(content) for pattern in _CLI_SIGNAL_PATTERNS):
            has_cli = True
        if any(pattern.search(content) for pattern in _BACKEND_SIGNAL_PATTERNS):
            has_backend = True
        if any(pattern.search(content) for pattern in _SESSION_PATTERNS):
            has_multi_step_surface = True

    for repo in _repo_findings_repos(repo_findings):
        entrypoints = list(getattr(repo, "entrypoints", []) or (repo.get("entrypoints", []) if isinstance(repo, dict) else []))
        workflows = list(getattr(repo, "workflows", []) or (repo.get("workflows", []) if isinstance(repo, dict) else []))
        scripts = list(getattr(repo, "scripts", []) or (repo.get("scripts", []) if isinstance(repo, dict) else []))
        if entrypoints:
            has_cli = has_cli or any(_path_has_cli_hint(str(item.get("path", "")).lower()) for item in entrypoints if isinstance(item, dict))
            has_backend = has_backend or bool(entrypoints)
        if len(workflows) + len(scripts) >= 2:
            has_multi_step_surface = True

    if has_cli or (has_backend and has_multi_step_surface):
        return "operation_backed"
    return "guidance"


def _backend_kind(text_samples: list[tuple[str, str]]) -> str:
    if any(_path_has_cli_hint(path.lower()) or any(pattern.search(content) for pattern in _CLI_SIGNAL_PATTERNS) for path, content in text_samples):
        return "repo_native_cli"
    if any("api" in path.lower() or "client" in path.lower() or re.search(r"\brequests\.|\bhttpx\.", content) for path, content in text_samples):
        return "api_client"
    if any(Path(path).suffix.lower() in {".sh", ".bash", ".zsh"} for path, _ in text_samples):
        return "shell_wrapper"
    return "python_backend"


def _supports_json(text_samples: list[tuple[str, str]]) -> bool:
    return any(any(pattern.search(content) for pattern in _JSON_PATTERNS) for _, content in text_samples)


def _session_model(text_samples: list[tuple[str, str]]) -> str:
    hits = sum(1 for _, content in text_samples if any(pattern.search(content) for pattern in _SESSION_PATTERNS))
    if hits >= 2:
        return "session_required"
    if hits == 1:
        return "session_optional"
    return "stateless"


def _mutability(text_samples: list[tuple[str, str]], operation_names: list[str]) -> str:
    has_write_signal = any(any(pattern.search(content) for pattern in _WRITE_PATTERNS) for _, content in text_samples)
    if not has_write_signal:
        mutating = [name for name in operation_names if any(verb in name for verb in _MUTATING_VERBS)]
        read_only = [name for name in operation_names if any(verb in name for verb in _READ_ONLY_VERBS)]
        if mutating and read_only:
            return "mixed"
        if mutating:
            return "mutating"
        return "read_only"
    if any(any(verb in name for verb in _READ_ONLY_VERBS) for name in operation_names):
        return "mixed"
    return "mutating"


def _entrypoint_hint(repo_findings: Any, text_samples: list[tuple[str, str]]) -> str | None:
    for repo in _repo_findings_repos(repo_findings):
        entrypoints = list(getattr(repo, "entrypoints", []) or (repo.get("entrypoints", []) if isinstance(repo, dict) else []))
        for item in entrypoints:
            if isinstance(item, dict) and item.get("path"):
                return str(item["path"])
    for path, _ in text_samples:
        if _path_has_cli_hint(path.lower()):
            return path
    return None


def _extract_operation_names(text_samples: list[tuple[str, str]]) -> list[str]:
    names: list[str] = []
    for path, content in text_samples:
        for pattern in _COMMAND_PATTERNS:
            for match in pattern.finditer(content):
                name = (match.groupdict().get("name") or "").strip()
                if name:
                    normalized = name.replace("_", "-").strip().lower()
                    if normalized not in names:
                        names.append(normalized)
        if names:
            continue
        if Path(path).suffix.lower() in {".py", ".sh", ".js", ".ts"}:
            stem = Path(path).stem.replace("_", "-").strip().lower()
            if stem and stem not in {"main", "app", "index"} and stem not in names:
                names.append(stem)
    if not names:
        names.append("run")
    return names[:8]


def _operation_inputs(text_samples: list[tuple[str, str]], operation_name: str) -> list[OperationInputSpec]:
    del operation_name
    flags: list[str] = []
    for _, content in text_samples:
        for match in _FLAG_PATTERN.finditer(content):
            flag = match.group(1).strip().lower()
            if flag and flag not in flags:
                flags.append(flag)
    return [
        OperationInputSpec(name=flag, kind="string", required=False, source="flag", description=f"CLI flag --{flag}")
        for flag in flags[:5]
    ]


def _operation_examples(*, entrypoint_hint: str | None, backend_kind: str, operation_name: str, supports_json: bool) -> list[str]:
    if backend_kind == "repo_native_cli" and entrypoint_hint:
        command = Path(entrypoint_hint).stem.replace("_", "-").lower()
        example = f"{command} {operation_name}"
        if supports_json:
            example += " --json"
        return [example]
    if entrypoint_hint:
        return [f"Use `{entrypoint_hint}` to invoke `{operation_name}` through the repo-native backend."]
    return [f"Invoke `{operation_name}` through the detected {backend_kind} surface."]


def _operation_spec(*, operation_name: str, text_samples: list[tuple[str, str]], backend_kind: str, entrypoint_hint: str | None, supports_json: bool, session_model: str, mutability: str) -> OperationSpec:
    preconditions = ["Run inside the cloned repository with dependencies available."]
    if session_model == "session_required":
        preconditions.append("Establish an active session before calling this operation.")

    side_effects = ["Reads repository or runtime state without mutating it."]
    if mutability in {"mixed", "mutating"} and any(verb in operation_name for verb in _MUTATING_VERBS):
        side_effects = ["May modify local repo state or external service state."]

    outputs = ["Structured stdout summary"]
    if supports_json:
        outputs.insert(0, "JSON result payload")

    error_modes = [
        "Validation failure when required inputs are missing.",
        "Backend execution failure if the underlying repo command or wrapper is unavailable.",
    ]

    return OperationSpec(
        name=operation_name,
        summary=f"Execute the `{operation_name}` workflow through the detected {backend_kind} surface.",
        inputs=_operation_inputs(text_samples, operation_name),
        outputs=outputs,
        preconditions=preconditions,
        side_effects=side_effects,
        error_modes=error_modes,
        examples=_operation_examples(
            entrypoint_hint=entrypoint_hint,
            backend_kind=backend_kind,
            operation_name=operation_name,
            supports_json=supports_json,
        ),
    )


def _safety_profile(text_samples: list[tuple[str, str]], mutability: str) -> SafetyProfile:
    credential_scope: list[str] = []
    network_scope: list[str] = []
    filesystem_scope = ["read_only" if mutability == "read_only" else "mixed_or_mutating"]
    external_process_usage: list[str] = []

    for _, content in text_samples:
        for pattern in _CREDENTIAL_PATTERNS:
            for match in pattern.finditer(content):
                token = next((item for item in match.groups() if item), match.group(0))
                token = str(token).strip()
                if token and token not in credential_scope:
                    credential_scope.append(token)
        if any(pattern.search(content) for pattern in _NETWORK_PATTERNS) and "external_http" not in network_scope:
            network_scope.append("external_http")
        if any(pattern.search(content) for pattern in _EXTERNAL_PROCESS_PATTERNS) and "subprocess" not in external_process_usage:
            external_process_usage.append("subprocess")

    return SafetyProfile(
        credential_scope=credential_scope[:5],
        network_scope=network_scope[:3],
        filesystem_scope=filesystem_scope,
        external_process_usage=external_process_usage[:3],
        confirmation_required=mutability in {"mixed", "mutating"},
    )


def build_operation_contract(*, request: Any, repo_context: Any, repo_findings: Any, skill_name: str) -> OperationContract | None:
    archetype = detect_skill_archetype(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
    )
    if archetype != "operation_backed":
        return None

    text_samples = _iter_text_samples(repo_context)
    if not text_samples:
        return None

    entrypoint_hint = _entrypoint_hint(repo_findings, text_samples)
    backend_kind = _backend_kind(text_samples)
    supports_json = _supports_json(text_samples)
    session_model = _session_model(text_samples)
    operation_names = _extract_operation_names(text_samples)
    mutability = _mutability(text_samples, operation_names)

    operations = [
        _operation_spec(
            operation_name=name,
            text_samples=text_samples,
            backend_kind=backend_kind,
            entrypoint_hint=entrypoint_hint,
            supports_json=supports_json,
            session_model=session_model,
            mutability=mutability,
        )
        for name in operation_names
    ]
    group_name = Path(entrypoint_hint).stem.replace("_", "-").lower() if entrypoint_hint else "operations"
    group_description = f"Primary operation surface derived from {entrypoint_hint or backend_kind}."

    install_prerequisites: list[str] = []
    runtime_dependencies: list[str] = []
    stack_tokens: list[str] = []
    for repo in _repo_findings_repos(repo_findings):
        stack_tokens.extend(list(getattr(repo, "detected_stack", []) or (repo.get("detected_stack", []) if isinstance(repo, dict) else [])))
    for token in stack_tokens:
        normalized = str(token).strip().lower()
        if normalized and normalized not in install_prerequisites:
            install_prerequisites.append(normalized)
    for _, content in text_samples:
        for token in ("click", "typer", "requests", "httpx", "argparse"):
            if token in content.lower() and token not in runtime_dependencies:
                runtime_dependencies.append(token)

    return OperationContract(
        name=skill_name,
        backend_kind=backend_kind,
        supports_json=supports_json,
        session_model=session_model,
        mutability=mutability,
        operations=[OperationGroup(name=group_name or "operations", description=group_description, operations=operations)],
        safety_profile=_safety_profile(text_samples, mutability),
        entrypoint_hint=entrypoint_hint,
        install_prerequisites=install_prerequisites[:5],
        runtime_dependencies=runtime_dependencies[:5],
    )


def contract_to_artifact(contract: OperationContract) -> ArtifactFile:
    return ArtifactFile(
        path="references/operations/contract.json",
        content=json.dumps(contract.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["operation_contract"],
        status="new",
    )


def operation_validation_artifact(*, skill_name: str, skill_archetype: str, contract: OperationContract) -> ArtifactFile:
    checks = [
        "operation_contract_present",
        "operation_groups_non_empty",
        "operation_examples_present",
        "safety_profile_present",
    ]
    if contract.supports_json:
        checks.append("json_surface_documented")
    if contract.mutability in {"mixed", "mutating"}:
        checks.append("mutating_operations_declare_side_effects")
    payload = {
        "skill_name": skill_name,
        "skill_archetype": skill_archetype,
        "backend_kind": contract.backend_kind,
        "supports_json": contract.supports_json,
        "session_model": contract.session_model,
        "mutability": contract.mutability,
        "operation_groups": [group.name for group in contract.operations],
        "checks": checks,
    }
    return ArtifactFile(
        path="evals/operation_validation.json",
        content=json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        content_type="application/json",
        generated_from=["operation_contract"],
        status="new",
    )


def operation_helper_artifact(*, skill_name: str, contract: OperationContract, path: str = "scripts/operation_helper.py") -> ArtifactFile:
    operations = [
        {
            "group": group.name,
            "name": operation.name,
            "summary": operation.summary,
            "supports_json": contract.supports_json,
        }
        for group in contract.operations
        for operation in group.operations
    ]
    payload = json.dumps({"skill_name": skill_name, "operations": operations}, indent=2, ensure_ascii=False)
    content = (
        "#!/usr/bin/env python3\n"
        "\"\"\"Thin helper that exposes the operation-backed skill contract as JSON.\"\"\"\n"
        "from __future__ import annotations\n\n"
        "import json\n\n"
        "PAYLOAD = json.loads(\n"
        f"    {payload!r}\n"
        ")\n\n"
        "def main() -> None:\n"
        "    print(json.dumps(PAYLOAD, ensure_ascii=False))\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )
    return ArtifactFile(
        path=path,
        content=content,
        content_type="text/plain",
        generated_from=["operation_contract"],
        status="new",
    )
