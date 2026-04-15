from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.security import SecurityAuditFinding, SecurityAuditReport

_EXECUTABLE_SUFFIXES = {
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".pl",
}
_BINARY_SUFFIXES = {".so", ".dylib", ".dll", ".elf", ".exe", ".wasm", ".bin"}
_ARCHIVE_SUFFIXES = {".zip", ".whl", ".tar", ".gz", ".tgz", ".xz"}
_TRUSTED_DOMAINS = {
    "github.com",
    "raw.githubusercontent.com",
    "npmjs.com",
    "pypi.org",
    "files.pythonhosted.org",
    "clawhub.ai",
}

_OUTBOUND_PATTERNS = (
    re.compile(r"\bcurl\b[^\n]*https?://", re.IGNORECASE),
    re.compile(r"\bwget\b[^\n]*https?://", re.IGNORECASE),
    re.compile(r"\brequests\.(?:get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    re.compile(r"\bhttpx\.(?:get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    re.compile(r"\bfetch\s*\(", re.IGNORECASE),
    re.compile(r"\baxios\.(?:get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    re.compile(r"\burlopen\s*\(", re.IGNORECASE),
)
_CREDENTIAL_PATTERNS = (
    re.compile(r"\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PRIVATE_KEY|ACCESS_KEY)\b"),
    re.compile(r"\bos\.environ\b"),
    re.compile(r"\bprocess\.env\b"),
    re.compile(r"\bgetenv\s*\("),
    re.compile(r"grep\s+-iE?\s+[\"'].*(?:key|token|secret)", re.IGNORECASE),
)
_SENSITIVE_FILE_PATTERNS = (
    re.compile(r"MEMORY\.md", re.IGNORECASE),
    re.compile(r"USER\.md", re.IGNORECASE),
    re.compile(r"SOUL\.md", re.IGNORECASE),
    re.compile(r"\.openclaw[^\n]*(?:MEMORY|USER|SOUL)\.md", re.IGNORECASE),
    re.compile(r"\.openclaw[^\n]*(?:config|credential|secret)", re.IGNORECASE),
    re.compile(r"\.ssh", re.IGNORECASE),
    re.compile(r"\.aws/credentials", re.IGNORECASE),
    re.compile(r"agent config", re.IGNORECASE),
)
_DYNAMIC_EXECUTION_PATTERNS = (
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bnew Function\s*\(", re.IGNORECASE),
    re.compile(r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True", re.IGNORECASE),
    re.compile(r"\bbash\s+-c\b", re.IGNORECASE),
    re.compile(r"\bpython\s+-c\b", re.IGNORECASE),
)
_PRIVILEGE_PATTERNS = (
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+[0-9]{3,4}\b", re.IGNORECASE),
    re.compile(r"\bchown\b", re.IGNORECASE),
    re.compile(r"\bsetuid\b", re.IGNORECASE),
)
_PERSISTENCE_PATTERNS = (
    re.compile(r"\bcrontab\b", re.IGNORECASE),
    re.compile(r"\bsystemctl\b", re.IGNORECASE),
    re.compile(r"\blaunchctl\b", re.IGNORECASE),
    re.compile(r"\.bashrc", re.IGNORECASE),
    re.compile(r"\.zshrc", re.IGNORECASE),
    re.compile(r"startup script", re.IGNORECASE),
)
_RUNTIME_DOWNLOAD_PATTERNS = (
    re.compile(r"curl\s+[^\n|]*\|\s*(?:bash|sh)", re.IGNORECASE),
    re.compile(r"wget\s+[^\n|]*\|\s*(?:bash|sh)", re.IGNORECASE),
    re.compile(r"pip\s+install\s+https?://", re.IGNORECASE),
    re.compile(r"npm\s+install\b[^\n]*(?:--force|-y|--yes)", re.IGNORECASE),
    re.compile(r"(?:clawhub install|npx skills add)\b[^\n]*(?:--force|-y|--yes)", re.IGNORECASE),
)
_OBFUSCATION_PATTERNS = (
    re.compile(r"base64\s+-d", re.IGNORECASE),
    re.compile(r"b64decode", re.IGNORECASE),
    re.compile(r"\batob\s*\(", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9+/=]{100,}"),
)
_RECON_PATTERNS = (
    re.compile(r"\bps aux\b", re.IGNORECASE),
    re.compile(r"\bss\s+-tlnp\b", re.IGNORECASE),
    re.compile(r"\blsof\b", re.IGNORECASE),
    re.compile(r"/proc/", re.IGNORECASE),
    re.compile(r"\bnetstat\b", re.IGNORECASE),
)
_BROWSER_PATTERNS = (
    re.compile(r"document\.cookie", re.IGNORECASE),
    re.compile(r"localStorage", re.IGNORECASE),
    re.compile(r"sessionStorage", re.IGNORECASE),
    re.compile(r"chrome\.cookies", re.IGNORECASE),
    re.compile(r"browser\.cookies", re.IGNORECASE),
)
_WRITE_PATTERNS = (
    re.compile(r"\bwrite_text\s*\(", re.IGNORECASE),
    re.compile(r"\bmkdir\s*\(", re.IGNORECASE),
    re.compile(r"\bopen\s*\([^,\n]+,\s*['\"][wa+]", re.IGNORECASE),
    re.compile(r"\bunlink\s*\(", re.IGNORECASE),
    re.compile(r"\bos\.remove\s*\(", re.IGNORECASE),
)
_CONFIRMATION_BYPASS_PATTERNS = (
    re.compile(r"\s-y\b"),
    re.compile(r"--yes\b"),
    re.compile(r"--force\b"),
    re.compile(r"\byes\s+\|", re.IGNORECASE),
)
_SOCIAL_ENGINEERING_GROUPS = {
    "pseudo_authority": (
        "officially recommended",
        "endorsed by",
        "certified safe",
        "official plugin for",
        "verified safe by independent security researchers",
    ),
    "safety_false_assurance": (
        "safe read-only diagnostics",
        "does not modify any system state",
        "harmless configuration optimization",
        "read-only audit",
    ),
    "urgency_pressure": (
        "install immediately",
        "critical security update",
        "actively exploited",
        "urgent:",
    ),
    "prompt_injection": (
        "ignore previous instructions",
        "override the normal review process",
        "do not ask for confirmation",
        "skip user confirmation",
    ),
}


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s)>'\"]+", text or "")


def _service_boundary_matches(content: str, urls: list[str]) -> bool:
    lowered = content.lower()
    for match in re.finditer(r"\b([A-Z0-9]+)_(?:API_KEY|TOKEN|SECRET|ACCESS_KEY)\b", content):
        prefix = match.group(1).lower()
        if len(prefix) < 3:
            continue
        if prefix in lowered and any(prefix in url.lower() for url in urls):
            return True
    return False


def _max_severity(*levels: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "reject": 3}
    return max(levels, key=lambda item: order[item])


def _report_rating(findings: Iterable[SecurityAuditFinding]) -> str:
    severity = "low"
    for finding in findings:
        severity = _max_severity(severity, finding.severity)
    return severity.upper()


def _recommended_action(rating: str) -> str:
    return {
        "LOW": "proceed",
        "MEDIUM": "caution",
        "HIGH": "human_approval",
        "REJECT": "refuse",
    }[rating]


def _default_trust_tier(*, artifacts: Artifacts) -> int:
    paths = [file.path for file in artifacts.files]
    if not any(_is_executable_path(path) for path in paths):
        return 1
    return 3


def _is_executable_path(path: str) -> bool:
    suffix = Path(path.rstrip("/")).suffix.lower()
    return path.startswith("scripts/") or suffix in _EXECUTABLE_SUFFIXES


def _binary_or_archive_risk(path: str) -> tuple[str, str] | None:
    normalized = path.rstrip("/")
    lowered = normalized.lower()
    if any(lowered.endswith(suffix) for suffix in _BINARY_SUFFIXES):
        return (
            "reject",
            "Binary or native executable artifact cannot be audited safely in generated skills.",
        )
    if any(lowered.endswith(suffix) for suffix in _ARCHIVE_SUFFIXES):
        return (
            "high",
            "Archive or packaged executable artifact requires separate unpacking and audit.",
        )
    return None


def _url_trust_tier(urls: list[str]) -> int:
    if not urls:
        return 1
    domains = {urlparse(url).netloc.lower() for url in urls if urlparse(url).netloc}
    if domains and all(any(domain == trusted or domain.endswith("." + trusted) for trusted in _TRUSTED_DOMAINS) for domain in domains):
        return 3
    return 4


def _summarize_evidence(matches: list[str]) -> list[str]:
    seen: list[str] = []
    for item in matches:
        trimmed = str(item or "").strip()
        if not trimmed:
            continue
        if trimmed not in seen:
            seen.append(trimmed[:160])
    return seen[:3]


def _social_engineering_hits(content: str) -> dict[str, list[str]]:
    lowered = (content or "").lower()
    hits: dict[str, list[str]] = {}
    for group, markers in _SOCIAL_ENGINEERING_GROUPS.items():
        matched = [marker for marker in markers if marker in lowered]
        if matched:
            hits[group] = matched
    return hits


def _make_finding(
    *,
    category: str,
    severity: str,
    path: str,
    evidence: list[str],
    reason: str,
) -> SecurityAuditFinding:
    return SecurityAuditFinding(
        category=category,
        severity=severity,
        paths=[path],
        evidence=_summarize_evidence(evidence),
        reason=reason,
        blocking=severity in {"high", "reject"},
    )


def _scan_file(file: ArtifactFile) -> list[SecurityAuditFinding]:
    findings: list[SecurityAuditFinding] = []
    path = file.path
    content = file.content or ""
    urls = _extract_urls(content)
    lower = content.lower()

    binary_or_archive = _binary_or_archive_risk(path)
    if binary_or_archive is not None:
        severity, reason = binary_or_archive
        findings.append(
            _make_finding(
                category="confirmation_bypass_or_source_trust",
                severity=severity,
                path=path,
                evidence=[path],
                reason=reason,
            )
        )

    outbound_hits = [pattern.pattern for pattern in _OUTBOUND_PATTERNS if pattern.search(content)]
    credential_hits = [pattern.pattern for pattern in _CREDENTIAL_PATTERNS if pattern.search(content)]
    sensitive_hits = [pattern.pattern for pattern in _SENSITIVE_FILE_PATTERNS if pattern.search(content)]
    dynamic_hits = [pattern.pattern for pattern in _DYNAMIC_EXECUTION_PATTERNS if pattern.search(content)]
    privilege_hits = [pattern.pattern for pattern in _PRIVILEGE_PATTERNS if pattern.search(content)]
    persistence_hits = [pattern.pattern for pattern in _PERSISTENCE_PATTERNS if pattern.search(content)]
    runtime_download_hits = [pattern.pattern for pattern in _RUNTIME_DOWNLOAD_PATTERNS if pattern.search(content)]
    obfuscation_hits = [pattern.pattern for pattern in _OBFUSCATION_PATTERNS if pattern.search(content)]
    recon_hits = [pattern.pattern for pattern in _RECON_PATTERNS if pattern.search(content)]
    browser_hits = [pattern.pattern for pattern in _BROWSER_PATTERNS if pattern.search(content)]
    confirmation_hits = [pattern.pattern for pattern in _CONFIRMATION_BYPASS_PATTERNS if pattern.search(content)]
    social_hits = _social_engineering_hits(content)

    if outbound_hits:
        severity = "medium"
        reason = "Artifact performs outbound network operations."
        if sensitive_hits:
            severity = "reject"
            reason = "Artifact combines outbound network activity with sensitive-file access."
        elif credential_hits and not _service_boundary_matches(content, urls):
            severity = "reject"
            reason = "Artifact combines outbound network activity with credential access outside the expected service boundary."
        findings.append(
            _make_finding(
                category="outbound_data",
                severity=severity,
                path=path,
                evidence=outbound_hits + urls,
                reason=reason,
            )
        )

    if credential_hits:
        severity = "high"
        reason = "Artifact accesses credentials or secret-bearing environment variables."
        if outbound_hits and not _service_boundary_matches(content, urls):
            severity = "reject"
            reason = "Credential access does not match the stated service boundary and is paired with outbound network activity."
        elif outbound_hits and _service_boundary_matches(content, urls):
            severity = "medium"
            reason = "Credential access appears scoped to a matching service boundary, but still requires review."
        findings.append(
            _make_finding(
                category="credential_access",
                severity=severity,
                path=path,
                evidence=credential_hits + urls,
                reason=reason,
            )
        )

    if sensitive_hits:
        severity = "high"
        reason = "Artifact touches sensitive local state or agent identity files."
        if outbound_hits:
            severity = "reject"
            reason = "Artifact accesses sensitive local state and sends data externally."
        findings.append(
            _make_finding(
                category="sensitive_file_access",
                severity=severity,
                path=path,
                evidence=sensitive_hits,
                reason=reason,
            )
        )

    if dynamic_hits:
        findings.append(
            _make_finding(
                category="dynamic_code_execution",
                severity="high",
                path=path,
                evidence=dynamic_hits,
                reason="Artifact uses dynamic code execution or shell-eval style behavior.",
            )
        )

    if privilege_hits:
        findings.append(
            _make_finding(
                category="privilege_escalation",
                severity="high",
                path=path,
                evidence=privilege_hits,
                reason="Artifact requests elevated privileges or mutates permissions.",
            )
        )

    if persistence_hits:
        findings.append(
            _make_finding(
                category="persistence_installation",
                severity="high",
                path=path,
                evidence=persistence_hits,
                reason="Artifact installs persistence hooks or startup modifications.",
            )
        )

    if runtime_download_hits:
        severity = "high"
        reason = "Artifact downloads and executes or installs additional code at runtime."
        if any("curl" in hit.lower() or "wget" in hit.lower() for hit in runtime_download_hits):
            severity = "reject"
            reason = "Artifact uses pipe-to-shell or equivalent runtime installation flow."
        findings.append(
            _make_finding(
                category="runtime_download_install",
                severity=severity,
                path=path,
                evidence=runtime_download_hits,
                reason=reason,
            )
        )

    if obfuscation_hits:
        severity = "medium"
        reason = "Artifact contains encoded or obscured payload patterns."
        if dynamic_hits or runtime_download_hits:
            severity = "reject"
            reason = "Artifact combines obfuscation with executable payload behavior."
        findings.append(
            _make_finding(
                category="obfuscation",
                severity=severity,
                path=path,
                evidence=obfuscation_hits,
                reason=reason,
            )
        )

    if recon_hits:
        severity = "medium"
        reason = "Artifact performs host/process/network reconnaissance."
        if social_hits:
            severity = "high"
            reason = "Artifact mixes reconnaissance with deceptive installation or review messaging."
        findings.append(
            _make_finding(
                category="reconnaissance",
                severity=severity,
                path=path,
                evidence=recon_hits,
                reason=reason,
            )
        )

    if browser_hits:
        findings.append(
            _make_finding(
                category="browser_session_access",
                severity="high",
                path=path,
                evidence=browser_hits,
                reason="Artifact accesses browser session state, cookies, or local storage.",
            )
        )

    if social_hits:
        severity = "medium"
        reason = "Artifact contains prompt-injection or social-engineering language."
        if len(social_hits) >= 2 or confirmation_hits or runtime_download_hits:
            severity = "reject"
            reason = "Artifact combines multiple social-engineering or prompt-injection patterns with execution pressure."
        findings.append(
            _make_finding(
                category="prompt_injection_social_engineering",
                severity=severity,
                path=path,
                evidence=[f"{group}:{','.join(matches)}" for group, matches in sorted(social_hits.items())],
                reason=reason,
            )
        )

    if confirmation_hits or (_url_trust_tier(urls) >= 4 and any(token in lower for token in ("install", "npx", "pip install", "npm install", "clawhub install"))):
        severity = "medium"
        reason = "Artifact includes confirmation-bypass flags or untrusted-source installation guidance."
        if confirmation_hits and ("--force" in content or re.search(r"\|\s*(?:bash|sh)", content, re.IGNORECASE)):
            severity = "high"
            reason = "Artifact bypasses confirmation while steering execution or installation."
        findings.append(
            _make_finding(
                category="confirmation_bypass_or_source_trust",
                severity=severity,
                path=path,
                evidence=confirmation_hits + urls,
                reason=reason,
            )
        )

    return findings


def _contract_alignment_findings(*, skill_plan, artifacts: Artifacts) -> list[SecurityAuditFinding]:
    contract = getattr(skill_plan, 'operation_contract', None) if skill_plan is not None else None
    if contract is None:
        return []

    findings: list[SecurityAuditFinding] = []
    mutability = str(getattr(contract, 'mutability', 'read_only') or 'read_only').strip().lower()
    credential_scope = {str(item).strip().upper() for item in list(getattr(getattr(contract, 'safety_profile', None), 'credential_scope', []) or []) if str(item).strip()}

    if mutability == 'read_only':
        mutating_paths: list[str] = []
        evidence: list[str] = []
        for file in artifacts.files:
            content = file.content or ''
            if any(pattern.search(content) for pattern in _WRITE_PATTERNS) or any(pattern.search(content) for pattern in _RUNTIME_DOWNLOAD_PATTERNS):
                mutating_paths.append(file.path)
                evidence.extend(_summarize_evidence([pattern.pattern for pattern in _WRITE_PATTERNS if pattern.search(content)]))
                evidence.extend(_summarize_evidence([pattern.pattern for pattern in _RUNTIME_DOWNLOAD_PATTERNS if pattern.search(content)]))
        if mutating_paths:
            findings.append(
                SecurityAuditFinding(
                    category='confirmation_bypass_or_source_trust',
                    severity='high',
                    paths=sorted(set(mutating_paths))[:3],
                    evidence=evidence[:3],
                    reason='Operation contract declares read_only, but generated artifacts contain mutating or runtime-install behavior.',
                    blocking=True,
                )
            )

    if credential_scope:
        mismatched_paths: list[str] = []
        mismatched_tokens: list[str] = []
        for file in artifacts.files:
            content = file.content or ''
            detected = {
                str(match.group(1) if match.groups() and match.group(1) else match.group(0)).strip().upper()
                for pattern in _CREDENTIAL_PATTERNS
                for match in pattern.finditer(content)
            }
            extra = sorted(token for token in detected if token and token not in credential_scope)
            if extra:
                mismatched_paths.append(file.path)
                mismatched_tokens.extend(extra)
        if mismatched_paths:
            findings.append(
                SecurityAuditFinding(
                    category='credential_access',
                    severity='reject',
                    paths=sorted(set(mismatched_paths))[:3],
                    evidence=_summarize_evidence(mismatched_tokens),
                    reason='Generated artifacts access credentials outside the declared operation contract credential scope.',
                    blocking=True,
                )
            )

    return findings


def _apply_contract_scoped_adjustments(
    *,
    findings: list[SecurityAuditFinding],
    contract,
) -> list[SecurityAuditFinding]:
    if contract is None:
        return findings

    network_scope = {
        str(item).strip().lower()
        for item in list(getattr(getattr(contract, 'safety_profile', None), 'network_scope', []) or [])
        if str(item).strip()
    }
    if not network_scope:
        return findings

    adjusted: list[SecurityAuditFinding] = []
    for finding in findings:
        if (
            finding.category == 'outbound_data'
            and finding.severity == 'medium'
            and any(scope in network_scope for scope in {'external_http', 'service_api', 'repo_api'})
        ):
            adjusted.append(
                finding.model_copy(
                    update={
                        'severity': 'low',
                        'blocking': False,
                        'reason': 'Artifact performs outbound network operations within the declared operation contract network scope.',
                    }
                )
            )
            continue
        adjusted.append(finding)
    return adjusted


def run_security_audit(
    *,
    request,
    repo_findings,
    skill_plan,
    artifacts: Artifacts,
    extracted_patterns=None,
) -> SecurityAuditReport:
    del request, extracted_patterns

    findings: list[SecurityAuditFinding] = []
    trust_tier = _default_trust_tier(artifacts=artifacts)
    repo_risks = []
    for repo in list(getattr(repo_findings, "repos", []) or []):
        repo_risks.extend(list(getattr(repo, "risks", []) or []))
    if repo_risks:
        trust_tier = max(trust_tier, 4)

    for file in artifacts.files:
        findings.extend(_scan_file(file))
        trust_tier = max(trust_tier, _url_trust_tier(_extract_urls(file.content or "")))

    contract = getattr(skill_plan, 'operation_contract', None) if skill_plan is not None else None
    if contract is not None:
        findings.extend(_contract_alignment_findings(skill_plan=skill_plan, artifacts=artifacts))
        findings = _apply_contract_scoped_adjustments(findings=findings, contract=contract)

    rating = _report_rating(findings)
    if rating in {"HIGH", "REJECT"}:
        trust_tier = max(trust_tier, 5)
    elif rating == "MEDIUM":
        trust_tier = max(trust_tier, 4)

    category_counter = Counter(finding.category for finding in findings)
    top_categories = [category for category, _ in category_counter.most_common(3)]
    grouped_paths: dict[str, set[str]] = defaultdict(set)
    for finding in findings:
        for path in finding.paths:
            grouped_paths[finding.category].add(path)

    summary: list[str] = [f"Security audit rating={rating}; trust_tier={trust_tier}"]
    if repo_risks:
        summary.append(f"Repo findings already flagged risks: {', '.join(repo_risks[:3])}")
    if contract is not None:
        summary.append(
            'Operation contract='
            f"{getattr(contract, 'backend_kind', 'python_backend')}; "
            f"mutability={getattr(contract, 'mutability', 'read_only')}; "
            f"credential_scope={list(getattr(getattr(contract, 'safety_profile', None), 'credential_scope', []) or [])[:3]}; "
            f"network_scope={list(getattr(getattr(contract, 'safety_profile', None), 'network_scope', []) or [])[:3]}"
        )
    for category in top_categories:
        severity = _report_rating([item for item in findings if item.category == category])
        paths = sorted(grouped_paths.get(category, set()))
        summary.append(f"{category}={severity.lower()} on {', '.join(paths[:2])}")
    if not findings:
        summary.append("No security red flags detected in generated artifacts.")

    blocking_count = sum(1 for finding in findings if finding.blocking)
    return SecurityAuditReport(
        rating=rating,
        trust_tier=trust_tier,
        findings=findings,
        summary=summary,
        recommended_action=_recommended_action(rating),
        blocking_findings_count=blocking_count,
        top_security_categories=top_categories,
    )
