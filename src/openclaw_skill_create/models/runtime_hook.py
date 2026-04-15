from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .runtime_cycle import RuntimeCycleResult
from .runtime_replay_approval import RuntimeReplayApprovalPack
from .runtime_replay_change import RuntimeReplayChangePack
from .runtime_replay_judge import RuntimeReplayJudgePack
from .runtime_replay_review import RuntimeReplayReviewResult


class RuntimeHookResult(BaseModel):
    applied: bool = False
    reason: str = ''
    runtime_cycle: Optional[RuntimeCycleResult] = None
    replay_review: Optional[RuntimeReplayReviewResult] = None
    change_pack: Optional[RuntimeReplayChangePack] = None
    approval_pack: Optional[RuntimeReplayApprovalPack] = None
    judge_pack: Optional[RuntimeReplayJudgePack] = None
    summary: str = ''
