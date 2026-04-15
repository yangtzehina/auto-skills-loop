from __future__ import annotations

import json
from typing import Any

from ..models.artifacts import ArtifactFile
from ..models.evaluation import (
    BenchmarkDimension,
    BenchmarkEvalSpec,
    OutputEvalCase,
    OutputEvalSpec,
    TriggerEvalCase,
    TriggerEvalSpec,
)
from .operation_contract import operation_validation_artifact
from .operation_coverage import build_operation_coverage_report, operation_coverage_artifact
from .skill_description import build_trigger_aware_skill_description


def _skill_description(request: Any, skill_plan: Any) -> str:
    return build_trigger_aware_skill_description(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        task=getattr(request, 'task', '') or '',
    )


def _trigger_positive_queries(request: Any, skill_plan: Any) -> list[str]:
    skill_name = getattr(skill_plan, 'skill_name', 'generated-skill')
    task = (getattr(request, 'task', '') or '').strip()
    description = _skill_description(request, skill_plan)
    queries = [
        task,
        f'Use {skill_name} to help with: {task}',
        description,
    ]
    return [query for query in queries if query]


def _trigger_negative_queries(skill_plan: Any) -> list[str]:
    skill_name = getattr(skill_plan, 'skill_name', 'generated-skill')
    return [
        'Translate this paragraph to Spanish without changing its tone',
        'Tell me today\'s weather in Shanghai',
        f'Fix an unrelated CSS spacing bug without using {skill_name}',
    ]


def build_trigger_eval_spec(*, request: Any, skill_plan: Any) -> TriggerEvalSpec:
    cases: list[TriggerEvalCase] = []
    for idx, query in enumerate(_trigger_positive_queries(request, skill_plan), start=1):
        cases.append(
            TriggerEvalCase(
                case_id=f'trigger-positive-{idx}',
                query=query,
                expected_trigger=True,
                rationale='This query aligns with the intended skill capability and should trigger the skill',
            )
        )
    for idx, query in enumerate(_trigger_negative_queries(skill_plan), start=1):
        cases.append(
            TriggerEvalCase(
                case_id=f'trigger-negative-{idx}',
                query=query,
                expected_trigger=False,
                rationale='This query is intentionally out of scope and should not trigger the skill',
            )
        )
    return TriggerEvalSpec(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        description=_skill_description(request, skill_plan),
        cases=cases,
    )


def _output_expected_behavior(request: Any, skill_plan: Any, reuse_decision: Any) -> list[str]:
    behavior = [
        'Ground the result in repo evidence or reusable online skill patterns',
        'Produce a SKILL.md that captures both capability and trigger in the description',
        'Generate supporting artifacts when the workflow needs detailed references or deterministic helpers',
    ]

    rationale = list(getattr(reuse_decision, 'rationale', []) or [])
    for item in rationale[:2]:
        behavior.append(item)

    blueprints = list(getattr(request, 'online_skill_blueprints', []) or [])
    if blueprints:
        workflow_summary = list(getattr(blueprints[0], 'workflow_summary', []) or [])
        behavior.extend(workflow_summary[:2])

    return behavior


def _output_success_criteria(skill_plan: Any) -> list[str]:
    files_to_create = list(getattr(skill_plan, 'files_to_create', []) or [])
    criteria = [
        'The generated skill package is internally consistent and ready for validation',
        'Supporting artifacts are present for every planned high-value file',
    ]
    planned_paths = [getattr(item, 'path', '') for item in files_to_create]
    if 'agents/openai.yaml' in planned_paths:
        criteria.append('Agent interface metadata is present in agents/openai.yaml')
    if 'evals/trigger_eval.json' in planned_paths or 'evals/output_eval.json' in planned_paths:
        criteria.append('Evaluation scaffold files exist for trigger and output comparison')
    return criteria


def build_output_eval_spec(*, request: Any, skill_plan: Any, reuse_decision: Any) -> OutputEvalSpec:
    baseline_variants = ['with_skill', 'without_skill']
    if getattr(reuse_decision, 'mode', '') in {'adapt_existing', 'compose_existing'}:
        baseline_variants.append('source_blueprint')
    case = OutputEvalCase(
        case_id='output-primary-1',
        query=getattr(request, 'task', ''),
        baseline_variant='without_skill',
        expected_behavior=_output_expected_behavior(request, skill_plan, reuse_decision),
        success_criteria=_output_success_criteria(skill_plan),
    )
    return OutputEvalSpec(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        baseline_variants=baseline_variants,
        cases=[case],
    )


def build_benchmark_eval_spec(*, request: Any, skill_plan: Any, reuse_decision: Any) -> BenchmarkEvalSpec:
    dimensions = [
        BenchmarkDimension(name='trigger_accuracy', description='Does the skill trigger when it should and stay silent otherwise?'),
        BenchmarkDimension(name='task_alignment', description='Does the generated skill retain the request domain vocabulary and task intent?'),
        BenchmarkDimension(name='repo_grounding', description='Are outputs grounded in repo signals or explicit source blueprints?'),
        BenchmarkDimension(name='artifact_completeness', description='Does the generated package include the planned supporting artifacts?'),
        BenchmarkDimension(name='maintainability', description='Are instructions concise, navigable, and structured for reuse?'),
    ]
    if getattr(reuse_decision, 'mode', '') in {'adapt_existing', 'compose_existing'}:
        dimensions.append(
            BenchmarkDimension(
                name='adaptation_quality',
                description='Does the generated skill preserve the useful parts of the source blueprint while adapting to the new task?',
            )
        )
    return BenchmarkEvalSpec(
        skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
        comparison_target='without_skill',
        dimensions=dimensions,
    )


def generate_eval_artifacts(*, request: Any, skill_plan: Any, reuse_decision: Any) -> list[ArtifactFile]:
    files = {getattr(item, 'path', '') for item in list(getattr(skill_plan, 'files_to_create', []) or [])}
    artifacts: list[ArtifactFile] = []
    operation_contract = getattr(skill_plan, 'operation_contract', None)

    if 'evals/trigger_eval.json' in files:
        trigger_spec = build_trigger_eval_spec(request=request, skill_plan=skill_plan)
        artifacts.append(
            ArtifactFile(
                path='evals/trigger_eval.json',
                content=json.dumps(trigger_spec.model_dump(), indent=2, ensure_ascii=False) + '\n',
                content_type='application/json',
                generated_from=['skill_plan', 'request', 'online_skill_blueprints'],
                status='new',
            )
        )

    if 'evals/output_eval.json' in files:
        output_spec = build_output_eval_spec(request=request, skill_plan=skill_plan, reuse_decision=reuse_decision)
        artifacts.append(
            ArtifactFile(
                path='evals/output_eval.json',
                content=json.dumps(output_spec.model_dump(), indent=2, ensure_ascii=False) + '\n',
                content_type='application/json',
                generated_from=['skill_plan', 'request', 'reuse_decision'],
                status='new',
            )
        )

    if 'evals/benchmark.json' in files:
        benchmark_spec = build_benchmark_eval_spec(request=request, skill_plan=skill_plan, reuse_decision=reuse_decision)
        artifacts.append(
            ArtifactFile(
                path='evals/benchmark.json',
                content=json.dumps(benchmark_spec.model_dump(), indent=2, ensure_ascii=False) + '\n',
                content_type='application/json',
                generated_from=['skill_plan', 'request', 'reuse_decision'],
                status='new',
            )
        )

    if 'evals/operation_validation.json' in files and operation_contract is not None:
        artifacts.append(
            operation_validation_artifact(
                skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
                skill_archetype=getattr(skill_plan, 'skill_archetype', 'guidance'),
                contract=operation_contract,
            )
        )

    if 'evals/operation_coverage.json' in files and operation_contract is not None:
        coverage_report = build_operation_coverage_report(
            skill_plan=skill_plan,
            artifacts=None,
            diagnostics=None,
        )
        artifacts.append(
            operation_coverage_artifact(
                skill_name=getattr(skill_plan, 'skill_name', 'generated-skill'),
                report=coverage_report,
            )
        )

    return artifacts
