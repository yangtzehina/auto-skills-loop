from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ..models.expert_dna import ExpertSkillDNA
from ..models.expert_studio import (
    AnalysisBlock,
    ExecutionMove,
    ExpertFailureCase,
    ExpertRewritePair,
    ExpertSkillCorpusEntry,
    ExpertTaskProbe,
    ProgramCandidateReviewBatchReport,
    ProgramCandidateReviewReport,
    SkillProgramAuthoringCandidate,
    SkillProgramAuthoringPack,
    SkillProgramIR,
)
from .expert_dna import OUTPUT_FIELD_GUIDANCE, build_domain_move_plan, expert_skill_dna_for_skill
from .expert_dna_authoring import DEFAULT_AUTHORING_CASES, _looks_like_generic_shell, build_expert_dna_authoring_candidate
from .style_diversity import expert_style_profile_for_skill


ROOT = Path(__file__).resolve().parents[3]
EXPERT_DEPTH_GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "expert_depth_golden"


def _golden_markdown(skill_name: str) -> str:
    path = EXPERT_DEPTH_GOLDEN_ROOT / f"{skill_name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _probe(
    probe_id: str,
    task: str,
    *,
    decision_terms: list[str],
    cut_terms: list[str],
    failure_terms: list[str],
    repair_terms: list[str],
    output_fields: list[str],
    anti_generic_terms: list[str],
) -> ExpertTaskProbe:
    return ExpertTaskProbe(
        probe_id=probe_id,
        task=task,
        decision_terms=decision_terms,
        cut_terms=cut_terms,
        failure_terms=failure_terms,
        repair_terms=repair_terms,
        output_fields=output_fields,
        anti_generic_terms=anti_generic_terms,
    )


def _rewrite_pair(skill_name: str, weak_shell: str, expert_revision: str, reason: str) -> ExpertRewritePair:
    return ExpertRewritePair(
        skill_name=skill_name,
        weak_shell=weak_shell,
        expert_revision=expert_revision,
        revision_reason=reason,
    )


def _failure_case(skill_name: str, failure_id: str, bad_output: str, failure_type: str, why: str, fix: str) -> ExpertFailureCase:
    return ExpertFailureCase(
        skill_name=skill_name,
        failure_id=failure_id,
        failure_type=failure_type,
        why_it_fails=why,
        repair_direction=fix,
        bad_output=bad_output,
    )


_KNOWN_CORPUS_DATA: dict[str, dict[str, Any]] = {
    "concept-to-mvp-pack": {
        "domain_family": "game-design",
        "task_brief": "Turn a game direction into a falsifiable first-playable MVP package.",
        "opening_strategy": "Lead with proof-first scope cutting, not broad concept expansion.",
        "expert_notes": [
            "Start from the validation question, not from feature enthusiasm.",
            "Use the smallest honest loop as the unit of truth, then cut anything that does not support it.",
            "The pack must end in an execution-facing MVP package, not a broad design overview.",
            "Always include an out-of-scope kill list and a final failure pass.",
        ],
        "anti_patterns": [
            "vertical slice inflation",
            "content hiding uncertainty",
            "scope creep by empathy",
            "mood instead of loop",
        ],
        "task_probes": [
            _probe(
                "mvp_scope_cut",
                "Scope a first playable for a cozy courier game without letting story and cosmetics hide validation.",
                decision_terms=["validation question", "smallest honest loop", "feature cut", "out of scope"],
                cut_terms=["cut", "defer", "out of scope", "kill list"],
                failure_terms=["scope creep", "vertical slice", "content hiding uncertainty"],
                repair_terms=["cut aggressively", "rewrite as playtest proof", "remove decorative scope"],
                output_fields=["Core Validation Question", "Smallest Honest Loop", "Feature Cut", "MVP Pack"],
                anti_generic_terms=["testability", "falsifiable", "playable proof"],
            ),
            _probe(
                "mvp_loop_proof",
                "Turn a combat-puzzle pitch into a smallest honest loop and explicit out-of-scope list.",
                decision_terms=["core validation question", "smallest honest loop", "minimum content package"],
                cut_terms=["later", "cut for now", "supportive", "out of scope"],
                failure_terms=["fake mvp", "mood instead of loop"],
                repair_terms=["state the repeatable loop", "use kill list"],
                output_fields=["Smallest Honest Loop", "Out of Scope", "Minimum Content Package"],
                anti_generic_terms=["repeat trigger", "system response", "visible feedback"],
            ),
            _probe(
                "mvp_failure_pass",
                "Package a tactics game concept into a first playable and explain what would make the MVP fail.",
                decision_terms=["failure pass", "build recommendation", "playtest signal"],
                cut_terms=["remove supportive systems", "do not overbuild"],
                failure_terms=["cannot fail clearly", "too many systems called core"],
                repair_terms=["rewrite as playtest observation", "shrink the pack"],
                output_fields=["MVP Pack", "Out of Scope", "Build recommendation"],
                anti_generic_terms=["could fail", "playtest signal", "redesign trigger"],
            ),
        ],
        "expected_outputs": [
            "Validation Goal with pass/fail evidence.",
            "Minimum Honest Loop with player input, system response, feedback, and repeat trigger.",
            "Feature Cut table with core/support/defer/cut buckets.",
            "Execution-facing MVP Pack and first playtest signal.",
        ],
        "rewrite_pairs": [
            _rewrite_pair(
                "concept-to-mvp-pack",
                "Use this skill to turn a game idea into a structured plan with goals and tradeoffs.",
                "Force the idea into a validation question, smallest honest loop, feature cut, and out-of-scope kill list.",
                "Replace generic concept planning with proof-first scope cutting.",
            )
        ],
        "failure_cases": [
            _failure_case(
                "concept-to-mvp-pack",
                "generic_shell",
                "# Concept to MVP Pack\n\n## Overview\nThink about what the game could be and list some features to include.\n",
                "generic_shell",
                "It describes planning instead of forcing a falsifiable MVP package.",
                "Rewrite around validation question, smallest honest loop, feature cut, and failure pass.",
            ),
            _failure_case(
                "concept-to-mvp-pack",
                "template_bloat",
                "# Concept to MVP Pack\n\n## Workflow\n1. Understand the context.\n2. Consider options.\n3. Write a summary.\n",
                "template_bloat",
                "It keeps a generic workflow skeleton and never names the actual MVP-cutting moves.",
                "Rebuild the workflow around the concrete MVP move sequence.",
            ),
        ],
    },
    "decision-loop-stress-test": {
        "domain_family": "game-design",
        "task_brief": "Stress test a game decision loop across first-hour, midgame, and mastery phases.",
        "opening_strategy": "Lead with phase stress and collapse-point hunting, not general loop commentary.",
        "expert_notes": [
            "The skill must read like a pressure test across time, not a static loop description.",
            "First hour, midgame, and late game are distinct stress lenses.",
            "Solved state and reinforcement quality are structural, not cosmetic, checks.",
            "Repairs should target decision pressure, not content volume.",
        ],
        "anti_patterns": [
            "loop analysis directory",
            "content instead of pressure repair",
            "variation as surface variety only",
        ],
        "task_probes": [
            _probe(
                "loop_phase_stress",
                "Stress a card-combat loop across first hour, midgame, and mastery pressure.",
                decision_terms=["first-hour hook", "midgame sustainability", "late-game expansion", "solved state"],
                cut_terms=["do not fix with more content", "structural fix", "counterpressure"],
                failure_terms=["repetition", "solved state", "autopilot"],
                repair_terms=["add counterpressure", "reward adaptation", "change decision landscape"],
                output_fields=["First-Hour Performance", "Midgame Performance", "Late-Game Performance", "Solved State Risk"],
                anti_generic_terms=["phase stress", "collapse point", "decision landscape"],
            ),
            _probe(
                "solved_state_repair",
                "Find the solved state in a farming automation loop and propose structural counterpressure.",
                decision_terms=["dominant strategy", "solved state risk", "variation quality"],
                cut_terms=["not more content", "not more cosmetic variation"],
                failure_terms=["dominant option", "flat feedback", "rote execution"],
                repair_terms=["punish repeated safe choices", "reward state-aware adaptation"],
                output_fields=["Solved State Risk", "Variation Quality", "Reinforcement Recommendations"],
                anti_generic_terms=["counterpressure", "state-aware", "autopilot risk"],
            ),
            _probe(
                "reinforcement_audit",
                "Audit whether a tactics loop teaches expressive adaptation or only efficient repetition.",
                decision_terms=["reinforcement check", "what behavior the rewards teach"],
                cut_terms=["avoid shallow reward inflation"],
                failure_terms=["wrong behavior training", "efficiency-only loop"],
                repair_terms=["reward adaptation", "change incentive structure"],
                output_fields=["Reinforcement Check", "Reinforcement Recommendations"],
                anti_generic_terms=["teaches", "reinforces", "behavior"],
            ),
        ],
        "expected_outputs": [
            "Phase-by-phase stress readout from first hour to mastery.",
            "Solved state diagnosis and structural repair direction.",
            "Reinforcement analysis showing what behavior the system trains.",
        ],
        "rewrite_pairs": [
            _rewrite_pair(
                "decision-loop-stress-test",
                "Describe the loop and suggest ways to make it more engaging over time.",
                "Pressure-test the loop across first hour, midgame, late game, solved state, and reinforcement quality.",
                "Turn generic engagement advice into a phase-based stress program.",
            )
        ],
        "failure_cases": [
            _failure_case(
                "decision-loop-stress-test",
                "analysis_directory",
                "# Decision Loop Stress Test\n\n## Current Loop Shape\n- Describe the loop.\n## Midgame\n- Talk about variety.\n",
                "analysis_directory",
                "It lists loop topics but does not run the player through an explicit stress sequence.",
                "Restore first-hour to late-game numbered stress moves and structural repair checks.",
            ),
            _failure_case(
                "decision-loop-stress-test",
                "content_patch_bias",
                "# Decision Loop Stress Test\n\n## Repair Ideas\n- Add more enemies.\n- Add more upgrades.\n",
                "content_patch_bias",
                "It prescribes content expansion instead of structural pressure repair.",
                "Rewrite fixes around pressure, dominant strategies, and reward training.",
            ),
        ],
    },
    "simulation-resource-loop-design": {
        "domain_family": "game-design",
        "task_brief": "Design a simulation resource loop around visible pressures, tradeoffs, and recovery.",
        "opening_strategy": "Lead with map/tension/loop/correct rather than generic systems design commentary.",
        "expert_notes": [
            "The skill should first map the variable web, then show how pressures create player-facing choices.",
            "Positive and negative loops must be paired; snowballing alone is not a design.",
            "Failure recovery must preserve cost, not erase pressure.",
            "The loop should protect emotional fantasy, not drift into spreadsheet simulation.",
        ],
        "anti_patterns": [
            "spreadsheet loop",
            "hidden-state only design",
            "positive loop without brake",
            "free recovery",
        ],
        "task_probes": [
            _probe(
                "resource_pressure_map",
                "Map visible resource pressure for a frontier clinic simulation.",
                decision_terms=["variable web", "pressure relationships", "primary decision tensions"],
                cut_terms=["cut decorative resources", "keep only strong tensions"],
                failure_terms=["flat loop", "no visible pressure", "hidden simulation state"],
                repair_terms=["make pressure visible", "reduce currencies", "tighten tradeoffs"],
                output_fields=["Variable Web", "Pressure Relationships", "Primary Decision Tensions"],
                anti_generic_terms=["player-facing", "pressure", "tradeoff"],
            ),
            _probe(
                "feedback_recovery_loop",
                "Design positive and negative loops plus failure recovery for a survival settlement game.",
                decision_terms=["positive and negative loops", "failure recovery"],
                cut_terms=["avoid consequence-free reset"],
                failure_terms=["runaway snowballing", "death spiral", "free reset"],
                repair_terms=["add brake", "preserve cost", "keep agency"],
                output_fields=["Positive and Negative Loops", "Failure Recovery"],
                anti_generic_terms=["snowball", "counter-pressure", "lasting cost"],
            ),
            _probe(
                "fantasy_alignment",
                "Check whether a social survival economy supports the intended emotional fantasy.",
                decision_terms=["emotional fantasy alignment", "resource pressure"],
                cut_terms=["remove decorative variables"],
                failure_terms=["spreadsheet feeling", "fantasy mismatch"],
                repair_terms=["reconnect scarcity and aspiration", "show consequence in play"],
                output_fields=["Emotional Fantasy Alignment", "Design Recommendations"],
                anti_generic_terms=["fantasy alignment", "aspiration", "consequence"],
            ),
        ],
        "expected_outputs": [
            "Variable web with player-facing signals and roles.",
            "Pressure relationships and main decision tensions.",
            "Positive/negative loop pair plus failure recovery with cost.",
            "Emotional fantasy alignment and design recommendations.",
        ],
        "rewrite_pairs": [
            _rewrite_pair(
                "simulation-resource-loop-design",
                "Explain how resources interact in a simulation game and note any risks.",
                "Map the variable web, trace pressure relationships, pair loops, and define recovery plus fantasy alignment.",
                "Turn generic systems talk into a visible pressure program.",
            )
        ],
        "failure_cases": [
            _failure_case(
                "simulation-resource-loop-design",
                "spreadsheet_pressureless",
                "# Simulation Resource Loop Design\n\n## Resources\n- Money\n- Time\n- Energy\n",
                "spreadsheet_pressureless",
                "It lists resources but never turns them into tensions, loops, or recovery structure.",
                "Rebuild around variable roles, pressure relationships, loop pair, and recovery cost.",
            ),
            _failure_case(
                "simulation-resource-loop-design",
                "all_positive_loops",
                "# Simulation Resource Loop Design\n\n## Positive Loop\n- Success generates more success.\n",
                "all_positive_loops",
                "It creates growth without brakes, making the loop unstable and uninteresting.",
                "Pair each compounding loop with counter-pressure and a costly recovery path.",
            ),
        ],
    },
    "go-to-market-decision-brief": {
        "domain_family": "strategy",
        "task_brief": "Write a go-to-market decision brief with explicit channel bets and failure signals.",
        "opening_strategy": "Lead with market choice and risk, not generic launch advice.",
        "expert_notes": [
            "Choose one primary GTM bet and make the rejection criteria explicit.",
            "Output should end in a decision brief, not a laundry list of channels.",
        ],
        "anti_patterns": ["channel laundry list", "generic launch checklist"],
        "task_probes": [
            _probe(
                "gtm_primary_bet",
                "Choose a primary channel bet for a devtools launch.",
                decision_terms=["primary bet", "channel thesis", "evidence threshold"],
                cut_terms=["not every channel", "defer channels"],
                failure_terms=["channel sprawl", "missing rejection criteria"],
                repair_terms=["pick one bet", "state failure signal"],
                output_fields=["Decision Brief", "Primary Channel", "Failure Signals"],
                anti_generic_terms=["channel thesis", "evidence threshold"],
            )
        ],
        "expected_outputs": ["Decision brief with channel thesis, rejection criteria, and next test."],
    },
    "agent-skill-abuse-review": {
        "domain_family": "security",
        "task_brief": "Review an agent skill for abuse risk and blocked behavior.",
        "opening_strategy": "Lead with abuse path, trust boundary, and refusal rule.",
        "expert_notes": [
            "The skill must identify abuse paths, trust boundaries, and refusal conditions.",
            "Repairs should reduce capability misuse rather than add more vague safety prose.",
        ],
        "anti_patterns": ["generic safety disclaimer", "no refusal criteria"],
        "task_probes": [
            _probe(
                "abuse_boundary",
                "Review whether a skill can be repurposed for credential harvesting.",
                decision_terms=["abuse path", "trust boundary", "refusal condition"],
                cut_terms=["remove unsafe capability"],
                failure_terms=["credential access", "prompt injection", "boundary bypass"],
                repair_terms=["scope credentials", "refuse execution", "separate safe helper"],
                output_fields=["Abuse Path", "Refusal Rule", "Repair Direction"],
                anti_generic_terms=["trust boundary", "refusal", "unsafe capability"],
            )
        ],
        "expected_outputs": ["Abuse review with explicit blocked behavior and repair direction."],
    },
    "messy-dataset-analysis-plan": {
        "domain_family": "data",
        "task_brief": "Plan a messy dataset analysis with cleaning assumptions and failure checks.",
        "opening_strategy": "Lead with data trust, not analysis ambition.",
        "expert_notes": [
            "The first move is to classify data quality risk, not jump to modeling.",
            "Output should name cleaning assumptions, bias risks, and stop conditions.",
        ],
        "anti_patterns": ["straight to modeling", "missing data trust check"],
        "task_probes": [
            _probe(
                "dataset_trust",
                "Plan analysis for a multi-source CSV dump with duplicated IDs and missing timestamps.",
                decision_terms=["data trust", "cleaning assumption", "bias risk"],
                cut_terms=["defer modeling", "reject unreliable slice"],
                failure_terms=["silent duplicate bias", "timestamp drift"],
                repair_terms=["dedupe rule", "trust boundary", "stop condition"],
                output_fields=["Data Trust", "Cleaning Plan", "Stop Condition"],
                anti_generic_terms=["dedupe", "bias risk", "stop condition"],
            )
        ],
        "expected_outputs": ["Analysis plan with trust checks, cleaning assumptions, and stop conditions."],
    },
    "architecture-tradeoff-review": {
        "domain_family": "engineering",
        "task_brief": "Review architecture tradeoffs with explicit decision criteria and rejection reasons.",
        "opening_strategy": "Lead with tradeoff lens and irreversible cost, not generic pros/cons.",
        "expert_notes": [
            "A tradeoff review should force a decision, not restate options.",
            "Output should carry rejection reasons and revisit triggers.",
        ],
        "anti_patterns": ["balanced but indecisive summary", "generic pros cons"],
        "task_probes": [
            _probe(
                "tradeoff_forcing",
                "Choose between a queue-based async workflow and a simpler synchronous path for an internal tool.",
                decision_terms=["decision criteria", "rejection reason", "revisit trigger"],
                cut_terms=["reject one path", "avoid false balance"],
                failure_terms=["false balance", "missing irreversible cost"],
                repair_terms=["name winning criterion", "state reject reason"],
                output_fields=["Decision", "Rejected Option", "Revisit Trigger"],
                anti_generic_terms=["tradeoff lens", "irreversible cost", "revisit trigger"],
            )
        ],
        "expected_outputs": ["Tradeoff review with chosen option, rejected option, and revisit trigger."],
    },
    "research-memo-synthesis": {
        "domain_family": "writing",
        "task_brief": "Synthesize a research memo into a decision-facing narrative with evidence tiers.",
        "opening_strategy": "Lead with claim strength and unresolved questions, not summary prose.",
        "expert_notes": [
            "A memo synthesis should rank claims by evidence quality and uncertainty.",
            "Output should separate what is known, what is inferred, and what is still open.",
        ],
        "anti_patterns": ["summary only", "flattened evidence tiers"],
        "task_probes": [
            _probe(
                "memo_claim_tiers",
                "Synthesize a user-research memo into ranked claims and open questions.",
                decision_terms=["claim strength", "evidence tier", "open question"],
                cut_terms=["remove unsupported narrative"],
                failure_terms=["flattened evidence", "unsupported conclusion"],
                repair_terms=["separate observed vs inferred", "restate uncertainty"],
                output_fields=["Ranked Claims", "Evidence Tier", "Open Questions"],
                anti_generic_terms=["observed", "inferred", "uncertain"],
            )
        ],
        "expected_outputs": ["Memo synthesis with ranked claims, evidence tiers, and open questions."],
    },
}


def load_expert_skill_corpus() -> dict[str, ExpertSkillCorpusEntry]:
    corpus: dict[str, ExpertSkillCorpusEntry] = {}
    for skill_name, seed in _KNOWN_CORPUS_DATA.items():
        corpus[skill_name] = ExpertSkillCorpusEntry(
            skill_name=skill_name,
            domain_family=str(seed.get("domain_family") or "methodology_guidance"),
            task_brief=str(seed.get("task_brief") or ""),
            expert_skill_markdown=_golden_markdown(skill_name),
            expert_notes=list(seed.get("expert_notes") or []),
            anti_patterns=list(seed.get("anti_patterns") or []),
            task_probes=list(seed.get("task_probes") or []),
            expected_outputs=list(seed.get("expected_outputs") or []),
            rewrite_pairs=list(seed.get("rewrite_pairs") or []),
            failure_cases=list(seed.get("failure_cases") or []),
        )
    return corpus


def expert_corpus_entry_for_skill(*, skill_name: str) -> ExpertSkillCorpusEntry | None:
    return load_expert_skill_corpus().get(skill_name)


def _execution_move(step_id: int, move: Any) -> ExecutionMove:
    return ExecutionMove(
        step_id=str(step_id),
        label=str(getattr(move, "name", "") or ""),
        purpose=str(getattr(move, "purpose", "") or ""),
        decision=str(getattr(move, "decision_probe", "") or ""),
        action=str(getattr(move, "action", "") or ""),
        output=str(getattr(move, "output_fragment", "") or ""),
        failure_signal=str(getattr(move, "failure_signal", "") or ""),
        fix=str(getattr(move, "repair_move", "") or ""),
        must_include_terms=list(getattr(move, "must_include_terms", []) or []),
        avoid_terms=list(getattr(move, "avoid_terms", []) or []),
    )


def _analysis_blocks(skill_name: str, workflow_surface: str, output_fields: list[str], expert_notes: list[str]) -> list[AnalysisBlock]:
    if workflow_surface == "execution_spine":
        return []
    if workflow_surface == "hybrid":
        field_groups = [
            ("Variable Web", ["Variable Web", "Variable Roles"]),
            ("Pressure Relationships", ["Pressure Relationships", "Primary Decision Tensions"]),
            ("Feedback Loops", ["Positive and Negative Loops", "Failure Recovery", "Emotional Fantasy Alignment"]),
        ]
    else:
        field_groups = [(field, [field]) for field in output_fields[:6]]
    blocks: list[AnalysisBlock] = []
    notes = list(expert_notes or [])
    for index, (name, fields) in enumerate(field_groups, start=1):
        blocks.append(
            AnalysisBlock(
                name=name,
                when_used=notes[(index - 1) % len(notes)] if notes else f"Use `{name}` to hold the mapped analysis after the workflow makes the decision.",
                questions=[f"What must `{name}` make visible to the user or builder?"],
                output_fields=[field for field in fields if field in output_fields],
            )
        )
    return blocks


def build_skill_program_ir(
    *,
    skill_name: str,
    task: str = "",
    candidate_dna: ExpertSkillDNA | None = None,
) -> SkillProgramIR | None:
    dna = candidate_dna or expert_skill_dna_for_skill(skill_name=skill_name, task=task)
    if dna is None:
        return None
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    plan = build_domain_move_plan(skill_name=skill_name, task=task)
    style_profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    workflow_surface = str(getattr(dna, "workflow_surface", "") or "execution_spine").strip().lower()
    execution_spine = [_execution_move(index, move) for index, move in enumerate(list(dna.workflow_moves or []), start=1)]
    output_schema = {
        field: [
            OUTPUT_FIELD_GUIDANCE.get(dna.skill_name, {}).get(
                field,
                "Write the concrete result with the decision, evidence, and next action clearly enough to use.",
            ),
            f"Good: {field} names the decision, evidence, consequence, and next action clearly enough to act on.",
            f"Weak: {field} stays abstract, repeats the prompt, or leaves the field as a vague summary.",
        ]
        for field in list(dna.output_fields or [])
    }
    failure_repairs = [
        f"{pattern} -> {dna.repair_moves[index % len(dna.repair_moves)] if dna.repair_moves else 'Return to the workflow and make the judgment explicit.'}"
        for index, pattern in enumerate(list(dna.failure_patterns or []))
    ]
    style_profile_items = list(getattr(style_profile, "workflow_label_set", []) or [])
    if corpus is not None:
        style_profile_items = style_profile_items + list(corpus.anti_patterns or [])
    program = SkillProgramIR(
        skill_name=skill_name,
        workflow_surface=workflow_surface,
        opening_strategy=(
            str(_KNOWN_CORPUS_DATA.get(skill_name, {}).get("opening_strategy") or "")
            or str(getattr(plan, "opening_frame", "") or "")
        ),
        execution_spine=execution_spine,
        analysis_blocks=_analysis_blocks(
            skill_name,
            workflow_surface,
            list(dna.output_fields or []),
            list(corpus.expert_notes if corpus is not None else []),
        ),
        decision_rules=list(dna.decision_rules or []),
        cut_rules=list(dna.cut_rules or []),
        failure_repairs=failure_repairs,
        output_schema=output_schema,
        style_profile=style_profile_items,
        voice_constraints=list(dna.voice_rules or []),
        source_skill_name=skill_name,
        source_confidence="checked_in" if candidate_dna is None else "candidate",
        summary=[
            f"workflow_surface={workflow_surface}",
            f"execution_move_count={len(execution_spine)}",
            f"analysis_block_count={len(_analysis_blocks(skill_name, workflow_surface, list(dna.output_fields or []), list(corpus.expert_notes if corpus is not None else [])))}",
        ],
    )
    return program


def render_skill_program_markdown(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
    candidate_dna: ExpertSkillDNA | None = None,
) -> str | None:
    program = build_skill_program_ir(skill_name=skill_name, task=task, candidate_dna=candidate_dna)
    plan = build_domain_move_plan(skill_name=skill_name, task=task)
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    if program is None or plan is None:
        return None
    lines = [
        "---",
        f"name: {skill_name}",
        f"description: {description}",
        "---",
        "",
        f"# {skill_name}",
        "",
        program.opening_strategy or plan.opening_frame,
        "",
        "## Overview",
        "",
        plan.overview,
        "",
        "## Core Principle",
        "",
        str(getattr(plan.dna, "core_thesis", "") or ""),
        "",
        "## When to Use",
        "",
    ]
    lines.extend(f"- {item}" for item in plan.when_to_use)
    lines.extend(["", "## When Not to Use", ""])
    lines.extend(f"- {item}" for item in plan.when_not_to_use)
    lines.extend(["", "## Inputs", ""])
    lines.extend(f"- {item}" for item in plan.inputs)
    lines.extend(["", "## Default Workflow", ""])
    if program.style_profile:
        lines.append(f"Profile rhythm: {', '.join(program.style_profile[:4])}.")
    if program.cut_rules:
        lines.append(f"Workflow guardrails: {', '.join(program.cut_rules[:6])}.")
    if program.style_profile or program.cut_rules:
        lines.append("")
    for index, move in enumerate(program.execution_spine, start=1):
        lines.append(f"{index}. **{move.label}**")
        lines.append(f"   - Decision: {move.decision}")
        lines.append(f"   - Do: {move.action}")
        lines.append(f"   - Output: {move.output}")
        lines.append(f"   - Failure Signal: {move.failure_signal}")
        lines.append(f"   - Fix: {move.fix}")
        if move.must_include_terms:
            lines.append(f"   - Must include: {', '.join(move.must_include_terms[:5])}.")
        lines.append("")
    if program.analysis_blocks:
        lines.extend(["## Analysis Blocks", ""])
        for block in program.analysis_blocks:
            lines.append(f"### {block.name}")
            lines.append(f"- Use when: {block.when_used}")
            if block.questions:
                lines.extend(f"- Question: {item}" for item in block.questions)
            if block.output_fields:
                lines.append(f"- Output fields: {', '.join(block.output_fields)}")
            lines.append("")
    lines.extend(["## Output Format", "", "```markdown"])
    for field, guidance_lines in program.output_schema.items():
        lines.append(f"## {field}")
        lines.extend(f"- {item}" for item in guidance_lines)
        lines.append("")
    lines.extend(["```", "", "## Decision Rules", ""])
    lines.extend(f"- {item}" for item in program.decision_rules)
    lines.extend(["", "## Cut Rules", ""])
    lines.extend(f"- {item}" for item in program.cut_rules)
    lines.extend(["", "## Quality Checks", ""])
    for rule in program.decision_rules:
        lines.append(f"- Check that {rule}.")
    for move in program.execution_spine:
        lines.append(f"- {move.label}: {move.failure_signal}")
    lines.extend(["", "## Common Pitfalls: Failure Patterns and Fixes", ""])
    for pair in program.failure_repairs:
        pattern, _, fix = pair.partition(" -> ")
        lines.append(f"### {pattern}")
        lines.append(f"- Symptom: the output shows `{pattern.lower()}` instead of a usable decision.")
        lines.append("- Cause: the workflow skipped the hard judgment and accepted a softer description.")
        lines.append(f"- Correction: {fix or 'Return to the workflow and make the judgment explicit.'}.")
        lines.append("")
    lines.extend(["## Worked Micro-Example", ""])
    if corpus is not None and corpus.expected_outputs:
        lines.extend(f"- {item}" for item in corpus.expected_outputs[:4])
    else:
        lines.append("- Use the workflow to produce a compact decision-facing output with explicit evidence and next action.")
    lines.extend(["", "## Voice Rules", ""])
    lines.extend(f"- {item}" for item in program.voice_constraints)
    if references:
        lines.extend(["", "## References", ""])
        lines.extend(f"- See `{path}` for supporting material." for path in references)
    if scripts:
        lines.extend(["", "## Helpers", ""])
        lines.extend(f"- Use `{path}` only when it directly supports this workflow." for path in scripts)
    return "\n".join(lines).rstrip() + "\n"


def build_skill_program_authoring_candidate(
    *,
    skill_name: str,
    task_brief: str = "",
    generated_skill_md: str = "",
    design_notes: str = "",
) -> SkillProgramAuthoringCandidate:
    dna_candidate = build_expert_dna_authoring_candidate(
        skill_name=skill_name,
        task_brief=task_brief,
        generated_skill_md=generated_skill_md,
        design_notes=design_notes,
    )
    program = build_skill_program_ir(
        skill_name=skill_name,
        task=task_brief,
        candidate_dna=dna_candidate.candidate_dna,
    )
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    backlog_categories: list[str] = []
    missing_evidence = list(dna_candidate.missing_expert_evidence or [])
    if corpus is None or not corpus.expert_skill_markdown.strip():
        backlog_categories.append("missing_expert_golden")
        if "expert_golden" not in missing_evidence:
            missing_evidence.append("expert_golden")
    if corpus is None or not corpus.task_probes:
        backlog_categories.append("missing_probe_outputs")
    if not dna_candidate.stable_move_sequence:
        backlog_categories.append("unstable_move_sequence")
    if dna_candidate.confidence == "reject":
        backlog_categories.append("generic_program_candidate")
    if program is None:
        backlog_categories.append("program_ir_missing")
    if generated_skill_md:
        lowered = generated_skill_md.lower()
        if _looks_like_generic_shell(generated_skill_md):
            backlog_categories.append("generic_program_candidate")
        if program is not None:
            move_labels = [move.label for move in list(program.execution_spine or [])]
            move_hits = sum(1 for label in move_labels if label.lower() in lowered)
            output_fields = list(program.output_schema.keys())
            output_hits = sum(1 for field in output_fields if field.lower() in lowered)
            if move_labels and move_hits / max(1, len(move_labels)) < 0.5:
                backlog_categories.append("unstable_move_sequence")
            if output_fields and output_hits / max(1, len(output_fields)) < 0.5:
                backlog_categories.append("generic_program_candidate")
    confidence = "ready_for_review"
    if "generic_program_candidate" in backlog_categories:
        confidence = "reject"
    elif backlog_categories:
        confidence = "needs_human_authoring"
    return SkillProgramAuthoringCandidate(
        skill_name=skill_name,
        task_brief=task_brief,
        candidate_program=program
        or SkillProgramIR(
            skill_name=skill_name,
            workflow_surface=str(getattr(dna_candidate.candidate_dna, "workflow_surface", "execution_spine") or "execution_spine"),
            source_skill_name=skill_name,
            source_confidence="candidate",
        ),
        source_confidence=confidence,
        backlog_categories=sorted(set(backlog_categories)),
        missing_expert_evidence=missing_evidence,
        stable_move_sequence=bool(dna_candidate.stable_move_sequence),
        ready_for_review=(confidence == "ready_for_review"),
        confidence=confidence,
        summary=[
            f"confidence={confidence}",
            f"backlog_categories={','.join(sorted(set(backlog_categories))) or 'none'}",
            f"missing_expert_evidence={','.join(missing_evidence) or 'none'}",
        ],
    )


def render_skill_program_authoring_pack_markdown(pack: SkillProgramAuthoringPack) -> str:
    lines = [
        "# Skill Program Authoring Pack",
        "",
        f"- candidate_program_count={pack.candidate_program_count}",
        f"- ready_for_review={len(pack.ready_for_review)}",
        f"- needs_human_authoring={len(pack.needs_human_authoring)}",
        f"- rejected={len(pack.rejected)}",
        f"- backlog_counts={pack.backlog_counts}",
        f"- Summary: {pack.summary}",
    ]
    for candidate in pack.candidates:
        lines.extend(
            [
                "",
                f"## {candidate.skill_name}",
                f"- confidence={candidate.confidence}",
                f"- workflow_surface={candidate.candidate_program.workflow_surface}",
                f"- stable_move_sequence={candidate.stable_move_sequence}",
                f"- backlog_categories={', '.join(candidate.backlog_categories) or 'none'}",
                f"- missing_expert_evidence={', '.join(candidate.missing_expert_evidence) or 'none'}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_skill_program_authoring_pack(
    *,
    cases: list[dict[str, str]] | None = None,
) -> SkillProgramAuthoringPack:
    candidates = [
        build_skill_program_authoring_candidate(
            skill_name=str(case.get("skill_name") or ""),
            task_brief=str(case.get("task") or ""),
            generated_skill_md=str(case.get("generated_skill_md") or ""),
            design_notes=str(case.get("design_notes") or ""),
        )
        for case in list(cases or DEFAULT_AUTHORING_CASES)
    ]
    ready = [candidate.skill_name for candidate in candidates if candidate.confidence == "ready_for_review"]
    needs_human = [candidate.skill_name for candidate in candidates if candidate.confidence == "needs_human_authoring"]
    rejected = [candidate.skill_name for candidate in candidates if candidate.confidence == "reject"]
    backlog_counts = dict(Counter(category for candidate in candidates for category in candidate.backlog_categories))
    pack = SkillProgramAuthoringPack(
        candidates=candidates,
        ready_for_review=ready,
        needs_human_authoring=needs_human,
        rejected=rejected,
        backlog_counts=backlog_counts,
        candidate_program_count=len(candidates),
        summary=(
            f"Skill program authoring complete: candidates={len(candidates)} ready_for_review={len(ready)} "
            f"needs_human_authoring={len(needs_human)} rejected={len(rejected)}"
        ),
    )
    pack.markdown_summary = render_skill_program_authoring_pack_markdown(pack)
    return pack


def render_program_candidate_review_markdown(report: ProgramCandidateReviewReport) -> str:
    lines = [
        "# Skill Program Review",
        "",
        f"- skill_name={report.skill_name}",
        f"- review_status={report.review_status}",
        f"- candidate_confidence={report.candidate_confidence}",
        f"- workflow_surface={report.workflow_surface}",
        f"- approved_for_release_gate={report.approved_for_release_gate}",
        f"- blocking_issues={', '.join(report.blocking_issues) or 'none'}",
    ]
    return "\n".join(lines) + "\n"


def render_program_candidate_review_batch_markdown(batch: ProgramCandidateReviewBatchReport) -> str:
    lines = [
        "# Skill Program Review Batch",
        "",
        f"- pass_count={batch.pass_count}",
        f"- fail_count={batch.fail_count}",
        f"- approved_for_release_gate_count={batch.approved_for_release_gate_count}",
        f"- Summary: {batch.summary}",
    ]
    for report in batch.reports:
        lines.extend(
            [
                "",
                f"## {report.skill_name}",
                f"- review_status={report.review_status}",
                f"- candidate_confidence={report.candidate_confidence}",
                f"- blocking_issues={', '.join(report.blocking_issues) or 'none'}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_program_candidate_review_report(candidate: SkillProgramAuthoringCandidate) -> ProgramCandidateReviewReport:
    program = candidate.candidate_program
    output_field_count = len(list(program.output_schema.keys()))
    checklist = {
        "has_execution_spine": len(program.execution_spine) >= 4,
        "has_output_schema": output_field_count >= 3,
        "has_decision_rules": len(program.decision_rules) >= 3,
        "has_failure_repairs": len(program.failure_repairs) >= 2,
        "has_expert_evidence": not candidate.missing_expert_evidence,
        "stable_move_sequence": candidate.stable_move_sequence,
        "ready_for_review": candidate.confidence == "ready_for_review",
    }
    if program.workflow_surface == "hybrid":
        checklist["has_analysis_blocks"] = len(program.analysis_blocks) >= 2
    blocking = [name for name, passed in checklist.items() if not passed]
    status = "pass" if not blocking else "fail"
    report = ProgramCandidateReviewReport(
        skill_name=candidate.skill_name,
        review_status=status,
        candidate_confidence=candidate.confidence,
        workflow_surface=program.workflow_surface,
        execution_move_count=len(program.execution_spine),
        analysis_block_count=len(program.analysis_blocks),
        output_field_count=output_field_count,
        checklist=checklist,
        blocking_issues=blocking,
        approved_for_release_gate=False,
        summary=[
            f"review_status={status}",
            "approved_for_release_gate=false",
            "candidate program must be checked in explicitly before it can affect fully_correct",
        ],
    )
    report.markdown_summary = render_program_candidate_review_markdown(report)
    return report


def build_program_candidate_review_batch_report(pack: SkillProgramAuthoringPack) -> ProgramCandidateReviewBatchReport:
    reports = [build_program_candidate_review_report(candidate) for candidate in pack.candidates]
    pass_count = sum(1 for report in reports if report.review_status == "pass")
    fail_count = len(reports) - pass_count
    batch = ProgramCandidateReviewBatchReport(
        reports=reports,
        pass_count=pass_count,
        fail_count=fail_count,
        approved_for_release_gate_count=sum(1 for report in reports if report.approved_for_release_gate),
        summary=(
            f"Skill program review complete: reports={len(reports)} pass={pass_count} "
            f"fail={fail_count} auto_enabled=0"
        ),
    )
    batch.markdown_summary = render_program_candidate_review_batch_markdown(batch)
    return batch


def evaluate_negative_case_resistance() -> tuple[float, float, int]:
    failure_cases = [
        failure
        for corpus in load_expert_skill_corpus().values()
        for failure in list(corpus.failure_cases or [])
    ]
    if not failure_cases:
        return 1.0, 1.0, 0
    resisted = 0
    generic_resisted = 0
    for failure in failure_cases:
        candidate = build_skill_program_authoring_candidate(
            skill_name=failure.skill_name,
            task_brief=expert_corpus_entry_for_skill(skill_name=failure.skill_name).task_brief if expert_corpus_entry_for_skill(skill_name=failure.skill_name) is not None else "",
            generated_skill_md=failure.bad_output,
        )
        report = build_program_candidate_review_report(candidate)
        if candidate.confidence == "reject" or report.review_status == "fail":
            resisted += 1
            if failure.failure_type == "generic_shell":
                generic_resisted += 1
    generic_count = sum(1 for item in failure_cases if item.failure_type == "generic_shell")
    return (
        round(resisted / max(1, len(failure_cases)), 4),
        round(generic_resisted / max(1, generic_count), 4),
        len(failure_cases) - resisted,
    )
