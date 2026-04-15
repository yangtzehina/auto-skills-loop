from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ExecutionTimings(BaseModel):
    started_at_ms: int
    finished_at_ms: Optional[int] = None
    extractor_started_at_ms: Optional[int] = None
    extractor_finished_at_ms: Optional[int] = None
    planner_started_at_ms: Optional[int] = None
    planner_finished_at_ms: Optional[int] = None
    generator_started_at_ms: Optional[int] = None
    generator_finished_at_ms: Optional[int] = None
    validator_started_at_ms: Optional[int] = None
    validator_finished_at_ms: Optional[int] = None
    eval_runner_started_at_ms: Optional[int] = None
    eval_runner_finished_at_ms: Optional[int] = None
    repair_attempted: bool = False
    repair_applied: bool = False
    repair_iteration_count: int = 0
