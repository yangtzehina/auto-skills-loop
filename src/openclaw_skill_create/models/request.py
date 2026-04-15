from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .online import SkillBlueprint, SkillSourceCandidate
from .patterns import ExtractedSkillPatterns
from .runtime import EvolutionPlan, SkillRunRecord


class SkillCreateRequestV6(BaseModel):
    version: str = "v6"
    task: str
    mode: str = "synthesize"
    output_mode: Optional[str] = None
    skill_archetype: str = "auto"
    repo_paths: list[str] = Field(default_factory=list)
    skill_name_hint: Optional[str] = None
    extracted_patterns: Optional[ExtractedSkillPatterns] = None
    enable_llm_extractor: bool = False
    enable_llm_planner: bool = False
    enable_llm_skill_md: bool = False
    enable_online_skill_discovery: bool = False
    enable_live_online_search: bool = True
    online_skill_limit: int = 5
    online_skill_manifest_urls: list[str] = Field(default_factory=list)
    online_skill_candidates: list[SkillSourceCandidate] = Field(default_factory=list)
    online_skill_blueprints: list[SkillBlueprint] = Field(default_factory=list)
    enable_eval_scaffold: bool = False
    enable_repair: bool = True
    max_repair_attempts: int = 1
    parent_skill_id: Optional[str] = None
    runtime_evolution_plan: Optional[EvolutionPlan] = None
    enable_runtime_hook: bool = False
    runtime_run_record: Optional[SkillRunRecord] = None
    runtime_hook_baseline_path: Optional[str] = None
    runtime_hook_scenarios: list[str] = Field(default_factory=list)
    enable_runtime_llm_judge: bool = False
    runtime_judge_model: Optional[str] = None
    enable_runtime_effectiveness_prior: bool = False
    runtime_effectiveness_min_runs: int = 5
    runtime_effectiveness_allowed_families: Optional[list[str]] = None
