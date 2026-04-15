from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..models.artifacts import ArtifactFile, Artifacts
from ..models.evaluation import (
    BenchmarkDimensionResult,
    BenchmarkEvalSpec,
    EvaluationRunReport,
    OutputEvalCaseResult,
    OutputEvalSpec,
    TriggerEvalCaseResult,
    TriggerEvalSpec,
)
from .online_discovery import _normalize_tokens
from .validator_rules import validate_skill_md_budget, validate_skill_md_frontmatter


def _artifact_map(artifacts: Artifacts) -> dict[str, ArtifactFile]:
    return {file.path: file for file in artifacts.files}


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith('---\n'):
        return {}, content
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return {}, content
    frontmatter: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter, parts[2]


def _description_is_trigger_aware(description: str) -> bool:
    if not description:
        return False
    lowered = description.lower()
    trigger_markers = ['use when', 'used when', 'when codex needs', 'when the task', 'when you need', '当', '用于']
    for marker in trigger_markers:
        idx = lowered.find(marker)
        if idx == -1:
            continue
        capability = description[:idx].strip(' ,;:-')
        trigger = description[idx + len(marker) :].strip(' ,;:-')
        return len(capability) >= 8 and len(trigger) >= 8
    return False


def _load_spec(artifacts: Artifacts, path: str, model_cls: Any) -> Any | None:
    file = _artifact_map(artifacts).get(path)
    if file is None or not (file.content or '').strip():
        return None
    try:
        return model_cls.model_validate_json(file.content)
    except Exception:
        return None


def _skill_features(artifacts: Artifacts) -> dict[str, Any]:
    files = _artifact_map(artifacts)
    paths = set(files)
    skill_md_content = (files.get('SKILL.md').content if files.get('SKILL.md') else '') or ''
    frontmatter, body = _parse_frontmatter(skill_md_content)
    description = frontmatter.get('description', '')
    name = frontmatter.get('name', '')
    reference_paths = sorted(path for path in paths if path.startswith('references/'))
    meta_payload = {}
    if files.get('_meta.json') and (files['_meta.json'].content or '').strip():
        try:
            meta_payload = json.loads(files['_meta.json'].content)
        except Exception:
            meta_payload = {}

    token_parts = [name, description, body]
    for path in sorted(paths):
        if path.startswith('references/') or path.startswith('scripts/'):
            token_parts.append(Path(path).stem.replace('_', ' ').replace('-', ' '))

    return {
        'skill_name': name or 'generated-skill',
        'description': description,
        'skill_tokens': set(_normalize_tokens(' '.join(token_parts))),
        'frontmatter_valid': validate_skill_md_frontmatter(skill_md_content),
        'trigger_aware': _description_is_trigger_aware(description),
        'within_budget': validate_skill_md_budget(skill_md_content, 300),
        'reference_links_complete': all(f'`{path}`' in skill_md_content for path in reference_paths),
        'has_repo_grounding': bool(meta_payload.get('repo_grounded')) or any(
            'repo_findings' in file.generated_from for file in artifacts.files
        ),
        'has_blueprint_sources': bool(meta_payload.get('online_blueprint_sources')) or any(
            'online_skill_blueprints' in file.generated_from or 'reuse_decision' in file.generated_from
            for file in artifacts.files
        ),
        'has_supporting_artifacts': any(
            path.startswith('references/')
            or path.startswith('scripts/')
            or path in {'agents/openai.yaml', '_meta.json'}
            for path in paths
        ),
        'has_agent_yaml': 'agents/openai.yaml' in paths,
        'has_trigger_eval': 'evals/trigger_eval.json' in paths,
        'has_output_eval': 'evals/output_eval.json' in paths,
        'has_benchmark_eval': 'evals/benchmark.json' in paths,
        'artifact_count': len(paths),
        'reference_count': len(reference_paths),
        'script_count': sum(1 for path in paths if path.startswith('scripts/')),
        'meta_payload': meta_payload,
    }


def _has_negated_skill_reference(query: str, skill_name: str) -> bool:
    lowered_query = (query or '').lower()
    lowered_name = (skill_name or '').lower().strip()
    if not lowered_name or lowered_name not in lowered_query:
        return False
    negated_patterns = [
        f'without using {lowered_name}',
        f'without {lowered_name}',
        f'do not use {lowered_name}',
        f"don't use {lowered_name}",
        f'avoid using {lowered_name}',
        f'instead of {lowered_name}',
    ]
    return any(pattern in lowered_query for pattern in negated_patterns)


def _trigger_case_result(case: Any, *, features: dict[str, Any]) -> TriggerEvalCaseResult:
    query = getattr(case, 'query', '') or ''
    query_tokens = set(_normalize_tokens(query))
    overlap = sorted(query_tokens & features['skill_tokens'])
    score = round(len(overlap) / max(len(query_tokens), 1), 4)
    skill_name_hit = bool(
        features['skill_name']
        and features['skill_name'].lower() in query.lower()
        and not _has_negated_skill_reference(query, features['skill_name'])
    )
    predicted = bool(
        score >= 0.18
        or skill_name_hit
    )
    return TriggerEvalCaseResult(
        case_id=getattr(case, 'case_id', ''),
        expected_trigger=bool(getattr(case, 'expected_trigger', False)),
        predicted_trigger=predicted,
        score=score,
        passed=predicted == bool(getattr(case, 'expected_trigger', False)),
        matched_terms=overlap[:6],
    )


def _assess_expectation(expectation: str, *, features: dict[str, Any]) -> tuple[bool, str]:
    lowered = expectation.lower()
    if not expectation.strip():
        return True, 'empty expectation'
    if 'repo evidence' in lowered or 'repo signals' in lowered or 'repo-grounded' in lowered:
        return features['has_repo_grounding'], 'repo grounding markers present'
    if 'online skill patterns' in lowered or 'source blueprint' in lowered:
        return features['has_blueprint_sources'], 'online blueprint sources present'
    if 'capability and trigger' in lowered:
        return features['trigger_aware'], 'SKILL.md description encodes both capability and trigger'
    if 'supporting artifacts' in lowered or 'detailed references' in lowered or 'deterministic helpers' in lowered:
        return features['has_supporting_artifacts'], 'supporting references/scripts detected'
    if 'agents/openai.yaml' in lowered:
        return features['has_agent_yaml'], 'agents/openai.yaml present'
    if 'evaluation scaffold' in lowered or 'trigger and output comparison' in lowered:
        return features['has_trigger_eval'] and features['has_output_eval'], 'trigger and output eval files present'
    if 'internally consistent' in lowered or 'ready for validation' in lowered:
        return features['frontmatter_valid'] and features['artifact_count'] >= 1, 'core skill artifacts are present'
    if 'planned supporting artifacts' in lowered or 'supporting artifacts are present' in lowered:
        return features['artifact_count'] >= 2, 'multiple artifacts are present'
    return features['frontmatter_valid'], 'frontmatter validation passed'


def _output_case_result(case: Any, *, features: dict[str, Any]) -> OutputEvalCaseResult:
    satisfied_behavior: list[str] = []
    missing_behavior: list[str] = []
    for expectation in list(getattr(case, 'expected_behavior', []) or []):
        passed, _detail = _assess_expectation(expectation, features=features)
        if passed:
            satisfied_behavior.append(expectation)
        else:
            missing_behavior.append(expectation)

    satisfied_criteria: list[str] = []
    missing_criteria: list[str] = []
    for criterion in list(getattr(case, 'success_criteria', []) or []):
        passed, _detail = _assess_expectation(criterion, features=features)
        if passed:
            satisfied_criteria.append(criterion)
        else:
            missing_criteria.append(criterion)

    total_checks = len(satisfied_behavior) + len(missing_behavior) + len(satisfied_criteria) + len(missing_criteria)
    score = round((len(satisfied_behavior) + len(satisfied_criteria)) / max(total_checks, 1), 4)
    passed = not missing_criteria and score >= 0.6
    return OutputEvalCaseResult(
        case_id=getattr(case, 'case_id', ''),
        baseline_variant=getattr(case, 'baseline_variant', 'without_skill'),
        score=score,
        passed=passed,
        satisfied_behavior=satisfied_behavior,
        missing_behavior=missing_behavior,
        satisfied_criteria=satisfied_criteria,
        missing_criteria=missing_criteria,
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _benchmark_dimension_result(
    dimension_name: str,
    *,
    benchmark_spec: BenchmarkEvalSpec,
    trigger_results: list[TriggerEvalCaseResult],
    output_results: list[OutputEvalCaseResult],
    features: dict[str, Any],
) -> BenchmarkDimensionResult:
    if dimension_name == 'trigger_accuracy':
        score = round(_average([1.0 if item.passed else 0.0 for item in trigger_results]), 4)
        return BenchmarkDimensionResult(name=dimension_name, score=score, rationale='Measured from trigger eval pass rate')
    if dimension_name == 'task_alignment':
        positive_scores = [
            item.score for item in trigger_results if item.expected_trigger
        ]
        score = round(_average(positive_scores), 4) if positive_scores else 0.0
        return BenchmarkDimensionResult(
            name=dimension_name,
            score=score,
            rationale='Derived from positive trigger overlap with task-domain terms',
        )
    if dimension_name == 'repo_grounding':
        score = 1.0 if features['has_repo_grounding'] else (0.85 if features['has_blueprint_sources'] else 0.35)
        return BenchmarkDimensionResult(name=dimension_name, score=round(score, 4), rationale='Derived from repo_findings / blueprint markers')
    if dimension_name == 'artifact_completeness':
        score = round(max(_average([item.score for item in output_results]), 0.0), 4)
        return BenchmarkDimensionResult(name=dimension_name, score=score, rationale='Derived from output eval completeness checks')
    if dimension_name == 'maintainability':
        score = _average(
            [
                1.0 if features['frontmatter_valid'] else 0.0,
                1.0 if features['trigger_aware'] else 0.0,
                1.0 if features['within_budget'] else 0.0,
                1.0 if (features['reference_links_complete'] or features['reference_count'] == 0) else 0.0,
            ]
        )
        return BenchmarkDimensionResult(name=dimension_name, score=round(score, 4), rationale='Combines frontmatter, trigger wording, budget, and reference navigation')
    if dimension_name == 'adaptation_quality':
        score = 1.0 if features['has_blueprint_sources'] else 0.0
        return BenchmarkDimensionResult(name=dimension_name, score=round(score, 4), rationale='Checks whether blueprint reuse markers survived into the package')
    return BenchmarkDimensionResult(name=dimension_name, score=0.5, rationale='No dedicated heuristic for this dimension yet')


def run_evaluations(*, artifacts: Artifacts) -> Optional[EvaluationRunReport]:
    trigger_spec = _load_spec(artifacts, 'evals/trigger_eval.json', TriggerEvalSpec)
    output_spec = _load_spec(artifacts, 'evals/output_eval.json', OutputEvalSpec)
    benchmark_spec = _load_spec(artifacts, 'evals/benchmark.json', BenchmarkEvalSpec)

    if trigger_spec is None and output_spec is None and benchmark_spec is None:
        return None

    features = _skill_features(artifacts)
    skill_name = (
        getattr(trigger_spec, 'skill_name', '')
        or getattr(output_spec, 'skill_name', '')
        or getattr(benchmark_spec, 'skill_name', '')
        or features['skill_name']
    )

    trigger_results = [
        _trigger_case_result(case, features=features)
        for case in list(getattr(trigger_spec, 'cases', []) or [])
    ]
    output_results = [
        _output_case_result(case, features=features)
        for case in list(getattr(output_spec, 'cases', []) or [])
    ]

    benchmark_results: list[BenchmarkDimensionResult] = []
    if benchmark_spec is not None:
        for dimension in list(getattr(benchmark_spec, 'dimensions', []) or []):
            benchmark_results.append(
                _benchmark_dimension_result(
                    getattr(dimension, 'name', ''),
                    benchmark_spec=benchmark_spec,
                    trigger_results=trigger_results,
                    output_results=output_results,
                    features=features,
                )
            )

    overall_components = [item.score for item in output_results] + [item.score for item in benchmark_results]
    overall_score = round(_average(overall_components), 4) if overall_components else round(_average([item.score for item in trigger_results]), 4)

    summary = [
        f'trigger_pass_rate={sum(1 for item in trigger_results if item.passed)}/{len(trigger_results)}'
        if trigger_results
        else 'trigger_eval_skipped',
        f'output_pass_rate={sum(1 for item in output_results if item.passed)}/{len(output_results)}'
        if output_results
        else 'output_eval_skipped',
        f'benchmark_dimensions={len(benchmark_results)}',
        f'overall_score={overall_score:.2f}',
    ]

    return EvaluationRunReport(
        skill_name=skill_name,
        trigger_results=trigger_results,
        output_results=output_results,
        benchmark_results=benchmark_results,
        overall_score=overall_score,
        summary=summary,
    )
