from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.body_quality import SkillBodyQualityReport, SkillSelfReviewReport
from ..models.depth_quality import SkillDepthQualityReport
from ..models.editorial_quality import SkillEditorialQualityReport
from ..models.expert_dna import SkillMoveQualityReport
from ..models.expert_studio import (
    PairwiseEditorialReport,
    SkillEditorialForceReport,
    SkillProgramFidelityReport,
    SkillPromotionDecision,
    SkillTaskOutcomeReport,
)
from ..models.domain_expertise import SkillDomainExpertiseReport
from ..models.domain_specificity import SkillDomainSpecificityReport
from ..models.expert_structure import SkillExpertStructureReport
from ..models.evaluation import EvaluationRunReport
from ..models.persistence import PersistencePolicy
from ..models.plan import SkillPlan
from ..models.review import SkillQualityReview
from ..models.security import SecurityAuditReport
from ..models.style_diversity import SkillStyleDiversityReport
from ..models.workflow_form import SkillWorkflowFormReport
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
BODY_QUALITY_REPORT_PATH = 'evals/body_quality.json'
SELF_REVIEW_REPORT_PATH = 'evals/self_review.json'
DOMAIN_SPECIFICITY_REPORT_PATH = 'evals/domain_specificity.json'
DOMAIN_EXPERTISE_REPORT_PATH = 'evals/domain_expertise.json'
EXPERT_STRUCTURE_REPORT_PATH = 'evals/expert_structure.json'
DEPTH_QUALITY_REPORT_PATH = 'evals/depth_quality.json'
EDITORIAL_QUALITY_REPORT_PATH = 'evals/editorial_quality.json'
STYLE_DIVERSITY_REPORT_PATH = 'evals/style_diversity.json'
MOVE_QUALITY_REPORT_PATH = 'evals/move_quality.json'
WORKFLOW_FORM_REPORT_PATH = 'evals/workflow_form.json'
PAIRWISE_EDITORIAL_REPORT_PATH = 'evals/pairwise_editorial.json'
PROMOTION_DECISION_REPORT_PATH = 'evals/promotion_decision.json'
EDITORIAL_FORCE_REPORT_PATH = 'evals/editorial_force.json'
PROGRAM_FIDELITY_REPORT_PATH = 'evals/program_fidelity.json'
TASK_OUTCOME_REPORT_PATH = 'evals/task_outcome.json'
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


def artifacts_with_body_quality(
    *,
    artifacts: Artifacts,
    body_quality: Optional[SkillBodyQualityReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if body_quality is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=BODY_QUALITY_REPORT_PATH,
        content=json.dumps(body_quality.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['body_quality'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != BODY_QUALITY_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_self_review(
    *,
    artifacts: Artifacts,
    self_review: Optional[SkillSelfReviewReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if self_review is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=SELF_REVIEW_REPORT_PATH,
        content=json.dumps(self_review.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['self_review'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != SELF_REVIEW_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_domain_specificity(
    *,
    artifacts: Artifacts,
    domain_specificity: Optional[SkillDomainSpecificityReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if domain_specificity is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=DOMAIN_SPECIFICITY_REPORT_PATH,
        content=json.dumps(domain_specificity.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['domain_specificity'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != DOMAIN_SPECIFICITY_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_domain_expertise(
    *,
    artifacts: Artifacts,
    domain_expertise: Optional[SkillDomainExpertiseReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if domain_expertise is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=DOMAIN_EXPERTISE_REPORT_PATH,
        content=json.dumps(domain_expertise.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['domain_expertise'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != DOMAIN_EXPERTISE_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_expert_structure(
    *,
    artifacts: Artifacts,
    expert_structure: Optional[SkillExpertStructureReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if expert_structure is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=EXPERT_STRUCTURE_REPORT_PATH,
        content=json.dumps(expert_structure.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['expert_structure'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != EXPERT_STRUCTURE_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_depth_quality(
    *,
    artifacts: Artifacts,
    depth_quality: Optional[SkillDepthQualityReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if depth_quality is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=DEPTH_QUALITY_REPORT_PATH,
        content=json.dumps(depth_quality.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['depth_quality'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != DEPTH_QUALITY_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_editorial_quality(
    *,
    artifacts: Artifacts,
    editorial_quality: Optional[SkillEditorialQualityReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if editorial_quality is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=EDITORIAL_QUALITY_REPORT_PATH,
        content=json.dumps(editorial_quality.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['editorial_quality'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != EDITORIAL_QUALITY_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_style_diversity(
    *,
    artifacts: Artifacts,
    style_diversity: Optional[SkillStyleDiversityReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if style_diversity is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=STYLE_DIVERSITY_REPORT_PATH,
        content=json.dumps(style_diversity.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['style_diversity'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != STYLE_DIVERSITY_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_move_quality(
    *,
    artifacts: Artifacts,
    move_quality: Optional[SkillMoveQualityReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if move_quality is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=MOVE_QUALITY_REPORT_PATH,
        content=json.dumps(move_quality.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['move_quality'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != MOVE_QUALITY_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_workflow_form(
    *,
    artifacts: Artifacts,
    workflow_form: Optional[SkillWorkflowFormReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if workflow_form is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=WORKFLOW_FORM_REPORT_PATH,
        content=json.dumps(workflow_form.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['workflow_form'],
        status='new',
    )

    files = [file for file in artifacts.files if file.path != WORKFLOW_FORM_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_pairwise_editorial(
    *,
    artifacts: Artifacts,
    pairwise_editorial: Optional[PairwiseEditorialReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if pairwise_editorial is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=PAIRWISE_EDITORIAL_REPORT_PATH,
        content=json.dumps(pairwise_editorial.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['pairwise_editorial'],
        status='new',
    )
    files = [file for file in artifacts.files if file.path != PAIRWISE_EDITORIAL_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_promotion_decision(
    *,
    artifacts: Artifacts,
    promotion_decision: Optional[SkillPromotionDecision],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if promotion_decision is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=PROMOTION_DECISION_REPORT_PATH,
        content=json.dumps(promotion_decision.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['promotion_decision'],
        status='new',
    )
    files = [file for file in artifacts.files if file.path != PROMOTION_DECISION_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_editorial_force(
    *,
    artifacts: Artifacts,
    editorial_force: Optional[SkillEditorialForceReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if editorial_force is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=EDITORIAL_FORCE_REPORT_PATH,
        content=json.dumps(editorial_force.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['editorial_force'],
        status='new',
    )
    files = [file for file in artifacts.files if file.path != EDITORIAL_FORCE_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_program_fidelity(
    *,
    artifacts: Artifacts,
    program_fidelity: Optional[SkillProgramFidelityReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if program_fidelity is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=PROGRAM_FIDELITY_REPORT_PATH,
        content=json.dumps(program_fidelity.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['program_fidelity'],
        status='new',
    )
    files = [file for file in artifacts.files if file.path != PROGRAM_FIDELITY_REPORT_PATH]
    files.append(report_file)
    return Artifacts(files=files)


def artifacts_with_task_outcome(
    *,
    artifacts: Artifacts,
    task_outcome: Optional[SkillTaskOutcomeReport],
    policy: Optional[PersistencePolicy],
) -> Artifacts:
    if task_outcome is None:
        return artifacts

    effective_policy = policy or PersistencePolicy()
    if not effective_policy.persist_evaluation_report:
        return artifacts

    report_file = ArtifactFile(
        path=TASK_OUTCOME_REPORT_PATH,
        content=json.dumps(task_outcome.model_dump(mode='json'), indent=2, ensure_ascii=False) + '\n',
        content_type='application/json',
        generated_from=['task_outcome'],
        status='new',
    )
    files = [file for file in artifacts.files if file.path != TASK_OUTCOME_REPORT_PATH]
    files.append(report_file)
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
        'body_quality_path': (
            str(target_dir / BODY_QUALITY_REPORT_PATH)
            if BODY_QUALITY_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'self_review_path': (
            str(target_dir / SELF_REVIEW_REPORT_PATH)
            if SELF_REVIEW_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'domain_specificity_path': (
            str(target_dir / DOMAIN_SPECIFICITY_REPORT_PATH)
            if DOMAIN_SPECIFICITY_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'domain_expertise_path': (
            str(target_dir / DOMAIN_EXPERTISE_REPORT_PATH)
            if DOMAIN_EXPERTISE_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'expert_structure_path': (
            str(target_dir / EXPERT_STRUCTURE_REPORT_PATH)
            if EXPERT_STRUCTURE_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'depth_quality_path': (
            str(target_dir / DEPTH_QUALITY_REPORT_PATH)
            if DEPTH_QUALITY_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'editorial_quality_path': (
            str(target_dir / EDITORIAL_QUALITY_REPORT_PATH)
            if EDITORIAL_QUALITY_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'style_diversity_path': (
            str(target_dir / STYLE_DIVERSITY_REPORT_PATH)
            if STYLE_DIVERSITY_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'move_quality_path': (
            str(target_dir / MOVE_QUALITY_REPORT_PATH)
            if MOVE_QUALITY_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'workflow_form_path': (
            str(target_dir / WORKFLOW_FORM_REPORT_PATH)
            if WORKFLOW_FORM_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'program_fidelity_path': (
            str(target_dir / PROGRAM_FIDELITY_REPORT_PATH)
            if PROGRAM_FIDELITY_REPORT_PATH in artifact_paths(artifacts)
            else None
        ),
        'task_outcome_path': (
            str(target_dir / TASK_OUTCOME_REPORT_PATH)
            if TASK_OUTCOME_REPORT_PATH in artifact_paths(artifacts)
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
