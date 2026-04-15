from __future__ import annotations

from pathlib import Path

from openclaw_skill_create.models.artifacts import ArtifactFile, Artifacts
from openclaw_skill_create.models.findings import RepoFindings
from openclaw_skill_create.models.operation import OperationContract, OperationGroup, OperationInputSpec, OperationSpec, SafetyProfile
from openclaw_skill_create.models.plan import PlannedFile, SkillPlan
from openclaw_skill_create.models.request import SkillCreateRequestV6
from openclaw_skill_create.services.extractor import run_extractor
from openclaw_skill_create.services.generator import run_generator
from openclaw_skill_create.services.planner import run_planner
from openclaw_skill_create.services.preloader import preload_repo_context
from openclaw_skill_create.services.review import run_skill_quality_review
from openclaw_skill_create.services.security_audit import run_security_audit
from openclaw_skill_create.services.validator import run_validator


FIXTURES_ROOT = Path(__file__).resolve().parent / 'fixtures' / 'operation_backed'


def _plan_for_fixture(repo_name: str, *, task: str | None = None, skill_name_hint: str | None = None):
    request = SkillCreateRequestV6(
        task=task or f'Create a skill for {repo_name}',
        repo_paths=[str(FIXTURES_ROOT / repo_name)],
        skill_name_hint=skill_name_hint or repo_name.replace('_', '-'),
    )
    repo_context = preload_repo_context(request)
    repo_findings = run_extractor(request=request, repo_context=repo_context)
    plan = run_planner(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
    )
    return request, repo_context, repo_findings, plan


def test_planner_keeps_guidance_track_for_doc_only_repo(tmp_path: Path):
    repo = tmp_path / 'docs-only'
    repo.mkdir()
    (repo / 'README.md').write_text('# Notes\n\nExplain the workflow in prose only.\n', encoding='utf-8')

    request = SkillCreateRequestV6(task='Create a documentation skill', repo_paths=[str(repo)], skill_name_hint='docs-only')
    repo_context = preload_repo_context(request)
    repo_findings = run_extractor(request=request, repo_context=repo_context)
    plan = run_planner(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
    )

    assert plan.skill_archetype == 'guidance'
    assert plan.operation_contract is None


def test_planner_selects_operation_backed_for_native_cli_repo():
    _, _, _, plan = _plan_for_fixture('native_cli_repo', skill_name_hint='native-cli-skill')

    paths = {item.path for item in plan.files_to_create}
    assert plan.skill_archetype == 'operation_backed'
    assert plan.operation_contract is not None
    assert plan.operation_contract.backend_kind == 'repo_native_cli'
    assert 'references/operations/contract.json' in paths
    assert 'evals/operation_validation.json' in paths
    assert 'evals/operation_coverage.json' in paths
    assert any(group.operations for group in plan.operation_contract.operations)


def test_planner_adds_helper_for_backend_only_repo():
    _, _, _, plan = _plan_for_fixture('backend_only_repo', skill_name_hint='backend-only-skill')

    paths = {item.path for item in plan.files_to_create}
    assert plan.skill_archetype == 'operation_backed'
    assert plan.operation_contract is not None
    assert plan.operation_contract.backend_kind in {'python_backend', 'api_client'}
    assert 'scripts/operation_helper.py' in paths
    assert 'references/operations/contract.json' in paths


def test_generator_emits_operation_contract_and_operation_specific_skill_md():
    request, repo_context, repo_findings, plan = _plan_for_fixture('native_cli_repo', skill_name_hint='native-cli-skill')

    artifacts = run_generator(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        skill_plan=plan,
    )

    contents = {file.path: file.content for file in artifacts.files}
    assert 'references/operations/contract.json' in contents
    assert 'evals/operation_validation.json' in contents
    assert 'evals/operation_coverage.json' in contents
    assert '## Operation Surface' in contents['SKILL.md']
    assert '`sync`' in contents['SKILL.md']
    assert '"backend_kind": "repo_native_cli"' in contents['references/operations/contract.json']


def test_validator_accepts_well_formed_operation_backed_generation():
    request, repo_context, repo_findings, plan = _plan_for_fixture('native_cli_repo', skill_name_hint='native-cli-skill')
    artifacts = run_generator(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        skill_plan=plan,
    )

    diagnostics = run_validator(
        request=request,
        repo_findings=repo_findings,
        skill_plan=plan,
        artifacts=artifacts,
    )

    assert diagnostics.security_audit is not None
    assert 'operation_contract_missing' not in diagnostics.validation.repairable_issue_types
    assert 'operation_json_contract_mismatch' not in diagnostics.validation.repairable_issue_types


def test_validator_flags_json_contract_mismatch():
    contract = OperationContract(
        name='json-skill',
        backend_kind='repo_native_cli',
        supports_json=True,
        session_model='stateless',
        mutability='read_only',
        operations=[
            OperationGroup(
                name='main',
                operations=[
                    OperationSpec(
                        name='inspect',
                        summary='Inspect resources.',
                        inputs=[OperationInputSpec(name='resource', source='flag')],
                        outputs=['JSON result payload'],
                        preconditions=['Run inside repo.'],
                        side_effects=['Reads state only.'],
                        examples=['tool inspect --json'],
                    )
                ],
            )
        ],
        safety_profile=SafetyProfile(),
    )
    plan = SkillPlan(
        skill_name='json-skill',
        skill_archetype='operation_backed',
        operation_contract=contract,
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='references/operations/contract.json', purpose='contract', source_basis=[]),
            PlannedFile(path='evals/operation_validation.json', purpose='validation', source_basis=[]),
        ],
    )
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='---\nname: json-skill\ndescription: Inspect resources. Use when Codex needs repo-backed inspection.\n---\n\n# json-skill\n',
            ),
            ArtifactFile(
                path='references/operations/contract.json',
                content=contract.model_dump_json(indent=2) + '\n',
                content_type='application/json',
            ),
            ArtifactFile(
                path='evals/operation_validation.json',
                content='{"skill_name":"json-skill","checks":[]}\n',
                content_type='application/json',
            ),
        ]
    )

    diagnostics = run_validator(
        request=SkillCreateRequestV6(task='validate operation skill'),
        repo_findings=RepoFindings(),
        skill_plan=plan,
        artifacts=artifacts,
    )

    assert 'operation_json_contract_mismatch' in diagnostics.validation.repairable_issue_types


def test_security_audit_rejects_contract_scope_mismatch():
    contract = OperationContract(
        name='dangerous-op',
        backend_kind='python_backend',
        supports_json=False,
        session_model='stateless',
        mutability='read_only',
        operations=[
            OperationGroup(
                name='main',
                operations=[
                    OperationSpec(
                        name='inspect',
                        summary='Inspect state.',
                        preconditions=['Run inside repo.'],
                        side_effects=['Reads state only.'],
                    )
                ],
            )
        ],
        safety_profile=SafetyProfile(credential_scope=['SERVICE_API_KEY']),
    )
    plan = SkillPlan(
        skill_name='dangerous-op',
        skill_archetype='operation_backed',
        operation_contract=contract,
        files_to_create=[
            PlannedFile(path='SKILL.md', purpose='entry', source_basis=[]),
            PlannedFile(path='scripts/run.py', purpose='helper', source_basis=[]),
        ],
    )
    artifacts = Artifacts(
        files=[
            ArtifactFile(
                path='SKILL.md',
                content='---\nname: dangerous-op\ndescription: Inspect state. Use when Codex needs repo-backed diagnostics.\n---\n',
            ),
            ArtifactFile(
                path='scripts/run.py',
                content='import os\nopen("state.txt", "w").write("x")\nprint(os.environ["OPENAI_API_KEY"])\n',
            ),
        ]
    )

    report = run_security_audit(
        request=SkillCreateRequestV6(task='audit dangerous operation skill'),
        repo_findings=RepoFindings(),
        skill_plan=plan,
        artifacts=artifacts,
    )

    assert report.rating == 'REJECT'
    assert any(item.category == 'credential_access' for item in report.findings)


def test_review_reports_operation_validation_summary():
    request, repo_context, repo_findings, plan = _plan_for_fixture('native_cli_repo', skill_name_hint='native-cli-skill')
    artifacts = run_generator(
        request=request,
        repo_context=repo_context,
        repo_findings=repo_findings,
        skill_plan=plan,
    )
    diagnostics = run_validator(
        request=request,
        repo_findings=repo_findings,
        skill_plan=plan,
        artifacts=artifacts,
    )

    review = run_skill_quality_review(
        repo_findings=repo_findings,
        skill_plan=plan,
        artifacts=artifacts,
        diagnostics=diagnostics,
    )

    assert review.skill_archetype == 'operation_backed'
    assert review.operation_count >= 1
    assert review.operation_validation_status == 'validated'
    assert review.recommended_followup == 'no_change'
