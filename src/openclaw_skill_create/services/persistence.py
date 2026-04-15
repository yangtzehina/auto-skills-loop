from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.evaluation import EvaluationRunReport
from ..models.persistence import PersistencePolicy
from ..models.plan import SkillPlan
from ..models.review import SkillQualityReview
from ..models.security import SecurityAuditReport
from ..models.operation_coverage import OperationCoverageReport


ROOT = Path(__file__).resolve().parents[3]
_OUTPUT_ROOT_ENV = (
    os.environ.get('AUTO_SKILLS_LOOP_OUTPUT_ROOT')
    or os.environ.get('SKILL_CREATE_OUTPUT_ROOT')
    or ''
).strip()
DEFAULT_OUTPUT_ROOT = Path(_OUTPUT_ROOT_ENV).expanduser() if _OUTPUT_ROOT_ENV else ROOT / '.generated-skills'
EVALUATION_REPORT_PATH = 'evals/report.json'
QUALITY_REVIEW_PATH = 'evals/review.json'
SECURITY_AUDIT_REPORT_PATH = 'evals/security_audit.json'
OPERATION_COVERAGE_REPORT_PATH = 'evals/operation_coverage.json'


def artifact_paths(artifacts: Artifacts) -> list[str]:
    return [file.path for file in artifacts.files]


def safe_output_root(output_root: Optional[str]) -> Path:
    if output_root is None:
        return DEFAULT_OUTPUT_ROOT
    root = Path(output_root).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return root


def safe_relative_path(path: str) -> Path:
    rel = Path(path)
    if rel.is_absolute():
        raise ValueError(f'absolute output path is not allowed: {path}')
    if '..' in rel.parts:
        raise ValueError(f'parent traversal is not allowed: {path}')
    return rel


def is_directory_artifact_path(path: str) -> bool:
    return path.endswith('/')


def planned_output_dir(root: Path, skill_plan: SkillPlan) -> Path:
    return root / skill_plan.skill_name


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def artifacts_with_evaluation_report(
    *,
    artifacts: Artifacts,
    evaluation_report: Optional[EvaluationRunReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if evaluation_report is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=EVALUATION_REPORT_PATH,
        content=json.dumps(evaluation_report.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['evaluation_runner'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != EVALUATION_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_quality_review(
    *,
    artifacts: Artifacts,
    quality_review: Optional[SkillQualityReview],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if quality_review is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    review_file = ArtifactFile(
        path=QUALITY_REVIEW_PATH,
        content=json.dumps(quality_review.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['quality_review'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != QUALITY_REVIEW_PATH]
    files.append(review_file)
    return Artifacts(files=files)


def artifacts_with_security_audit(
    *,
    artifacts: Artifacts,
    security_audit: Optional[SecurityAuditReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if security_audit is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    audit_file = ArtifactFile(
        path=SECURITY_AUDIT_REPORT_PATH,
        content=json.dumps(security_audit.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['security_audit'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != SECURITY_AUDIT_REPORT_PATH]
    files.append(audit_file)
    return Artifacts(files=files)


def artifacts_with_operation_coverage(
    *,
    artifacts: Artifacts,
    operation_coverage: Optional[OperationCoverageReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if operation_coverage is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    payload = operation_coverage.model_dump(mode='json')
    coverage_file = ArtifactFile(
        path=OPERATION_COVERAGE_REPORT_PATH,
        content=json.dumps(payload, indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['operation_coverage'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != OPERATION_COVERAGE_REPORT_PATH]
    files.append(coverage_file)
    return Artifacts(files=files)


def persist_artifacts(
    *,
    artifacts: Artifacts,
    skill_plan: SkillPlan,
    output_root: Optional[str],
    severity: str,
    policy: Optional[PersistencePolicy],
) -> dict[str, Any]:
    policy = policy or PersistencePolicy()
    root = safe_output_root(output_root)
    target_dir = planned_output_dir(root, skill_plan)

    written_files: list[str] = []
    backup_files: list[str] = []

    for file in artifacts.files:
        directory_artifact = is_directory_artifact_path(file.path)
        rel = safe_relative_path(file.path.rstrip('/') if directory_artifact else file.path)
        destination = target_dir / rel
        if directory_artifact:
            if destination.exists() and not destination.is_dir():
                if not policy.overwrite:
                    continue
                if policy.backup_on_update:
                    backup_path = destination.with_suffix(destination.suffix + '.bak')
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    backup_path.write_text(destination.read_text(encoding='utf-8'), encoding='utf-8')
                    backup_files.append(str(backup_path))
                if not policy.dry_run:
                    destination.unlink()
            if not policy.dry_run:
                destination.mkdir(parents=True, exist_ok=True)
            written_files.append(str(destination) + '/')
            continue

        if destination.exists() and not policy.overwrite:
            continue

        if destination.exists() and policy.overwrite and policy.backup_on_update:
            backup_path = destination.with_suffix(destination.suffix + '.bak')
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(destination.read_text(encoding='utf-8'), encoding='utf-8')
            backup_files.append(str(backup_path))

        if not policy.dry_run:
            write_atomic(destination, file.content)
        written_files.append(str(destination))

    return {
        'applied': not policy.dry_run,
        'dry_run': policy.dry_run,
        'severity': severity,
        'output_root': str(target_dir),
        'file_count': len(artifacts.files),
        'written_files': written_files,
        'backup_files': backup_files,
        'artifact_paths': artifact_paths(artifacts),
        'evaluation_report_path': (
            str(target_dir / EVALUATION_REPORT_PATH)
            if EVALUATION_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'quality_review_path': (
            str(target_dir / QUALITY_REVIEW_PATH)
            if QUALITY_REVIEW_PATH in artifact_paths(artifacts)
            else None
        ),
        'security_audit_path': (
            str(target_dir / SECURITY_AUDIT_REPORT_PATH)
            if SECURITY_AUDIT_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'operation_coverage_path': (
            str(target_dir / OPERATION_COVERAGE_REPORT_PATH)
            if OPERATION_COVERAGE_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
    }
