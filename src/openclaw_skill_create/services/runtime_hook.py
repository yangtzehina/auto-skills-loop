from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..models.observation import OpenSpaceObservationPolicy
from ..models.runtime import RuntimeSessionEvidence, SkillRunRecord
from ..models.runtime_cycle import RuntimeCycleResult
from ..models.runtime_hook import RuntimeHookResult
from .runtime_cycle import run_runtime_cycle
from .runtime_replay_approval import build_runtime_replay_approval_pack
from .runtime_replay_change import build_runtime_replay_change_pack
from .runtime_replay_judge import LLMRunner, build_runtime_replay_judge_pack
from .runtime_replay_review import build_runtime_replay_review


def run_runtime_hook(
    *,
    run_record: SkillRunRecord,
    policy: Optional[OpenSpaceObservationPolicy],
    session_evidence: Optional[RuntimeSessionEvidence] = None,
    runtime_cycle_result: Optional[RuntimeCycleResult] = None,
    baseline_path: Optional[Path] = None,
    scenario_names: Optional[list[str]] = None,
    enable_llm_judge: bool = False,
    llm_runner: Optional[LLMRunner] = None,
    model: Optional[str] = None,
) -> RuntimeHookResult:
    cycle = runtime_cycle_result or run_runtime_cycle(
        run_record,
        policy,
        session_evidence=session_evidence,
    )
    review = build_runtime_replay_review(
        baseline_path=baseline_path,
        scenario_names=scenario_names,
    )
    change_pack = build_runtime_replay_change_pack(
        baseline_path=baseline_path,
        scenario_names=scenario_names,
    )
    approval_pack = build_runtime_replay_approval_pack(
        baseline_path=baseline_path,
        scenario_names=scenario_names,
    )
    judge_pack = None
    if enable_llm_judge:
        judge_pack = build_runtime_replay_judge_pack(
            change_pack,
            enabled=True,
            llm_runner=llm_runner,
            model=model,
        )
    return RuntimeHookResult(
        applied=True,
        runtime_cycle=cycle,
        replay_review=review,
        change_pack=change_pack,
        approval_pack=approval_pack,
        judge_pack=judge_pack,
        summary=(
            f'Runtime hook complete: cycle_action={cycle.followup.action}; '
            f'change_pack={change_pack.recommended_action}; '
            f'approval={approval_pack.approval_decision}; '
            f'judge={"applied" if judge_pack is not None and judge_pack.applied else "skipped"}'
        ),
    )
