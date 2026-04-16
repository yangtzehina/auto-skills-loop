from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from ..models.expert_dna import ExpertSkillDNA
from ..models.expert_studio import (
    AnalysisBlock,
    ExecutionMove,
    ExpertEvidenceGapReport,
    ExpertFailureCase,
    ExpertRewritePair,
    ExpertSectionCorpusEntry,
    ExpertSkillCorpusEntry,
    ExpertTaskProbe,
    MonotonicImprovementReport,
    PairwiseEditorialReport,
    ProfileBaselineBundle,
    ProgramCandidateReviewBatchReport,
    ProgramCandidateReviewReport,
    SectionCompressionPlan,
    SectionCompressionResult,
    SectionRealizationSpec,
    SkillEditorialForceReport,
    SkillProgramAuthoringCandidate,
    SkillProgramAuthoringPack,
    SkillProgramIR,
    SkillPromotionDecision,
    SkillRealizationCandidate,
    SkillRealizationSpec,
)
from .expert_dna import OUTPUT_FIELD_GUIDANCE, build_domain_move_plan, expert_skill_dna_for_skill
from .expert_dna_authoring import DEFAULT_AUTHORING_CASES, _looks_like_generic_shell, build_expert_dna_authoring_candidate
from .style_diversity import expert_style_profile_for_skill
from .body_quality import split_frontmatter
from .domain_specificity import _extract_section
from .editorial_quality import build_skill_editorial_quality_report
from .editorial_force import build_skill_editorial_force_report
from .move_quality import build_skill_move_quality_report
from .style_diversity import build_skill_style_diversity_report
from ..models.artifacts import ArtifactFile, Artifacts
from ..models.plan import SkillPlan
from ..models.request import SkillCreateRequestV6
from .body_quality import build_skill_body_quality_report
from .domain_specificity import build_skill_domain_specificity_report
from .domain_expertise import build_skill_domain_expertise_report
from .depth_quality import build_skill_depth_quality_report


ROOT = Path(__file__).resolve().parents[3]
EXPERT_DEPTH_GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "expert_depth_golden"
CURRENT_BEST_GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "golden"
DUAL_BASELINE_ROOT = ROOT / "tests" / "fixtures" / "methodology_guidance" / "dual_baselines"

PROFILE_FRONTMATTER_DESCRIPTIONS: dict[str, str] = {
    "concept-to-mvp-pack": "Game-design workflow for proving a first playable, cutting scope, and packaging an honest MVP.",
    "decision-loop-stress-test": "Phase-by-phase audit for finding collapse points, dominant routes, and reward-training mistakes.",
    "simulation-resource-loop-design": "Systems workflow for mapping currencies, bottlenecks, counterweights, and costly comeback paths.",
}

PROFILE_QUALITY_GATE_LINES: dict[str, str] = {
    "concept-to-mvp-pack": "Approve the first playable only if the proof, cut, and scope lines are explicit enough to kill or greenlight the build.",
    "decision-loop-stress-test": "Keep the audit on collapse, dominant strategy, and reinforcement before anyone reaches for extra content.",
    "simulation-resource-loop-design": "Keep the loop readable through visible pressure, costly recovery, and fantasy fit before smoothing the numbers.",
}

PROFILE_QUALITY_CHECK_LINES: dict[str, list[str]] = {
    "concept-to-mvp-pack": [
        "Check whether the validation question can fail in a short playtest.",
        "Check whether the smallest honest loop is already playable without future systems or spectacle.",
        "Check whether the feature cut removes supportive work instead of protecting comfort.",
        "Check whether the content scope is just enough to prove the loop.",
        "Check whether the out-of-scope list blocks scope creep instead of sounding polite.",
        "Check whether the MVP pack names the next build and the next playtest signal.",
        "Check whether the build recommendation and success criteria are explicit enough to approve the first playable.",
        "Check whether the pack stays prototype first instead of drifting into a mini vertical slice.",
        "Check whether pass and fail evidence would actually force a redesign instead of just sounding organized.",
        "Check whether a greybox build with stubbed content and placeholder art still answers the validation question.",
    ],
    "decision-loop-stress-test": [
        "Check whether the decision loop is readable in the first hour before novelty wears off.",
        "Check whether first hour, midgame, and lategame differ for the right reason instead of only inflating numbers.",
        "Check whether lategame pressure mutates the problem instead of rewarding autopilot.",
        "Check whether solved state is concrete enough to name, trigger, and attack.",
        "Check whether variation changes decisions rather than surface decoration.",
        "Check whether reinforcement teaches intended behavior instead of efficient repetition.",
        "Check whether the repair changes pressure inside the decision loop instead of adding softer content.",
        "Check whether the review stays on decision quality instead of greenlighting the theme.",
        "Check whether detailed numeric balancing or MVP scope cutting is being used to dodge a structural break.",
    ],
    "simulation-resource-loop-design": [
        "Check whether variables have player-facing roles before any balancing work starts.",
        "Check whether pressure relationships create a readable tradeoff instead of hidden bookkeeping.",
        "Check whether positive and negative loops both exist and counterweight each other on purpose.",
        "Check whether failure recovery keeps consequences instead of flattening the system.",
        "Check whether emotional fantasy matches resource math instead of drifting away from the loop.",
        "Check whether one dominant currency can still bypass the intended tension web.",
        "Check whether the feedback loops create rhythm instead of runaway snowball or pure punishment.",
        "Check whether you can reduce currencies until only a few strong tensions remain and every variable changes player behavior.",
        "Check whether recovery avoids a consequence-free reset, makes pressure visible early, and keeps tradeoffs costly.",
        "Check whether the system is not just one simple currency or a stack of isolated meters.",
        "Check whether the design stops at the pressure web instead of drifting into mostly content writing.",
    ],
}

PROFILE_FAILURE_ENTRIES: dict[str, list[tuple[str, str, str, str]]] = {
    "concept-to-mvp-pack": [
        (
            "Fake MVP",
            "The core question reads like a slogan and no short session could disprove it.",
            "The pack protected confidence instead of proof.",
            "Rewrite the validation question so one failed playtest would force a redesign.",
        ),
        (
            "Scope Creep",
            "Support systems keep sliding back into the first build as if they were core.",
            "The feature cut was polite instead of explicit.",
            "Cut aggressively, then move the supportive work into out of scope with a clear re-entry condition.",
        ),
        (
            "Content-Heavy Validation",
            "The MVP only works if future meta systems, content volume, or presentation arrive first.",
            "The smallest honest loop was never isolated.",
            "Do not fake the entire game; reduce the build to the repeatable loop that already produces the intended feeling.",
        ),
        (
            "Premature Meta Systems",
            "Progression, unlocks, or retention layers are doing the proof work for the loop.",
            "Validation was outsourced to future structure instead of the first playable.",
            "Strip back to the smallest honest loop and test the fantasy before adding meta structure.",
        ),
        (
            "Success Criteria Missing",
            "The handoff sounds polished but still does not say what would count as proof or failure.",
            "Packaging happened before the pass/fail evidence was locked.",
            "End with explicit playtest evidence, build target, and redesign trigger.",
        ),
    ],
    "decision-loop-stress-test": [
        (
            "Novelty-Only Start",
            "Early play only works because the premise is fresh, not because the decision is clear.",
            "The first-hour hook never established readable pressure.",
            "Raise the stakes and feedback around the core choice before adding more content.",
        ),
        (
            "Midgame Autopilot",
            "The player keeps repeating the same answer while the game only changes labels or numbers.",
            "Midgame added volume without adding new constraints.",
            "Introduce counterpressure that forces adaptation instead of simple efficiency scaling.",
        ),
        (
            "Progression Without New Problems",
            "Progression adds throughput or spectacle while the underlying choice stays solved.",
            "Expansion arrived without a new pressure problem.",
            "Add a new constraint or pressure relationship before adding more content or reward layers.",
        ),
        (
            "Variety Without Strategic Consequence",
            "The game offers more variants, but they do not change read, tradeoff, or consequence.",
            "Variation was used as surface freshness instead of decision mutation.",
            "Cut cosmetic variation and keep only the variants that force a new answer.",
        ),
        (
            "Mastery Removes the Game",
            "Late play collapses into rote execution or a dominant route.",
            "Mastery widened throughput without creating a new decision problem.",
            "Change the pressure landscape so mastery unlocks new tradeoffs instead of solving the loop forever.",
        ),
        (
            "Wrong Behavior Training",
            "The reward structure favors autopilot even though the design claims expression or adaptation.",
            "Reinforcement was tuned for throughput rather than the intended behavior.",
            "Move rewards onto the behavior you actually want and strip reward from the safe dominant routine.",
        ),
    ],
    "simulation-resource-loop-design": [
        (
            "Decorative Resources",
            "The loop lists resources, but they do not create a player-facing tradeoff.",
            "Variables were added for flavor or spreadsheet depth rather than decision pressure.",
            "Reduce currencies and cut decorative resources until each remaining variable changes player behavior.",
        ),
        (
            "No Real Tradeoff",
            "Pressure exists on paper, but the player still has one obviously correct answer.",
            "The pressure relationship never creates a real sacrifice.",
            "Make pressure visible and tighten tradeoffs so the player must give something up.",
        ),
        (
            "One Dominant Currency",
            "A single resource or loop answers every problem.",
            "Counterpressure exists on paper but never bites in play.",
            "Add a brake, opportunity cost, or dependency that the dominant currency cannot bypass.",
        ),
        (
            "Positive-Loop Runaway",
            "Success compounds into snowballing without a meaningful brake.",
            "Positive loops were tuned without a matching negative loop or cap.",
            "Pair the runaway loop with a counterpressure that stays visible during success.",
        ),
        (
            "Punishment Without Agency",
            "Pressure punishes the player, but the recovery path offers no meaningful response or tradeoff.",
            "The loop preserved pain without preserving agency.",
            "Add readable warning, viable responses, and recovery with cost instead of a consequence-free reset or pure punishment.",
        ),
        (
            "Fantasy-System Mismatch",
            "The spreadsheet balances, but the player-facing pressure produces the wrong feeling.",
            "Variables were optimized independently from the intended emotional rhythm.",
            "Rewrite the loop so the visible pressures reinforce the fantasy instead of flattening it.",
        ),
        (
            "Hidden Pressure Relationships",
            "Resources move in the background, but the player cannot read the pressure soon enough to plan around it.",
            "Signals were treated as bookkeeping instead of decision surfaces.",
            "Make pressure visible before the player commits so the cost, risk, or bottleneck can actually shape the next move.",
        ),
    ],
}


def _golden_markdown(skill_name: str) -> str:
    path = EXPERT_DEPTH_GOLDEN_ROOT / f"{skill_name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _current_best_markdown(skill_name: str) -> str:
    path = CURRENT_BEST_GOLDEN_ROOT / f"{skill_name}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _dual_baseline_bundle(skill_name: str) -> ProfileBaselineBundle | None:
    path = DUAL_BASELINE_ROOT / f"{skill_name}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return ProfileBaselineBundle.model_validate(payload)


def _section_corpus(
    skill_name: str,
    expert_markdown: str,
    expert_notes: list[str],
    failure_cases: list[ExpertFailureCase],
) -> list[ExpertSectionCorpusEntry]:
    if not expert_markdown.strip():
        return []
    _, body = split_frontmatter(expert_markdown)
    section_specs = [
        ("Overview", "Frame the skill as a sharp domain method, not a generic planning template."),
        ("Default Workflow", "Carry the primary execution spine and keep the domain moves in explicit order."),
        ("Output Format", "Make the deliverable directly fillable and execution-facing."),
        ("Quality Checks", "Force the hard judgment checks that prevent a soft generic answer."),
        ("Common Pitfalls", "Name failure patterns and corrections sharply enough to fix them."),
    ]
    results: list[ExpertSectionCorpusEntry] = []
    for name, purpose in section_specs:
        excerpt = _extract_section(body, (name.lower(),))
        if not excerpt:
            continue
        lowered = excerpt.lower()
        judgment_moves = [note for note in list(expert_notes or []) if any(token in lowered for token in note.lower().split()[:3])]
        cut_moves = [
            line.strip("- ").strip()
            for line in excerpt.splitlines()
            if "cut" in line.lower() or "out of scope" in line.lower() or "defer" in line.lower()
        ][:6]
        repair_moves = [
            item.repair_direction
            for item in list(failure_cases or [])
            if item.repair_direction and item.failure_type != "generic_shell"
        ][:6]
        results.append(
            ExpertSectionCorpusEntry(
                skill_name=skill_name,
                section_name=name,
                expert_excerpt=excerpt.strip(),
                section_purpose=purpose,
                judgment_moves=judgment_moves,
                cut_moves=cut_moves,
                repair_moves=repair_moves,
            )
        )
    return results


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
            ),
            _rewrite_pair(
                "concept-to-mvp-pack",
                "Describe the MVP and mention a few risks before moving into production planning.",
                "Name what the first playable must prove, what gets cut, what stays out of scope, and what would make the pack fail immediately.",
                "Convert a polite MVP summary into a pressure-tested package decision.",
            ),
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
            ),
            _rewrite_pair(
                "decision-loop-stress-test",
                "List each phase of the loop and offer a few content ideas where it feels weak.",
                "Find the collapse point in each phase, state the wrong behavior being reinforced, and prescribe a structural repair before adding content.",
                "Turn a tidy loop review into a pressure-and-repair audit.",
            ),
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
            ),
            _rewrite_pair(
                "simulation-resource-loop-design",
                "List the resources, explain the loop, and suggest adding recovery if the game feels too punishing.",
                "Show which pressures the player sees, where tradeoffs bite, how positive and negative loops balance, and how recovery preserves cost instead of erasing it.",
                "Replace broad systems commentary with player-facing tension and recovery discipline.",
            ),
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
        expert_markdown = _golden_markdown(skill_name)
        failure_cases = list(seed.get("failure_cases") or [])
        corpus[skill_name] = ExpertSkillCorpusEntry(
            skill_name=skill_name,
            domain_family=str(seed.get("domain_family") or "methodology_guidance"),
            task_brief=str(seed.get("task_brief") or ""),
            expert_skill_markdown=expert_markdown,
            expert_notes=list(seed.get("expert_notes") or []),
            section_corpus=_section_corpus(
                skill_name,
                expert_markdown,
                list(seed.get("expert_notes") or []),
                failure_cases,
            ),
            anti_patterns=list(seed.get("anti_patterns") or []),
            task_probes=list(seed.get("task_probes") or []),
            expected_outputs=list(seed.get("expected_outputs") or []),
            rewrite_pairs=list(seed.get("rewrite_pairs") or []),
            failure_cases=failure_cases,
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


def _surface_label_profile(skill_name: str) -> dict[str, str]:
    profiles = {
        "concept-to-mvp-pack": {
            "decision": "Prove",
            "action": "Do",
            "output": "Package",
            "failure": "Cut If",
            "fix": "Tighten",
            "write": "Write",
            "good": "Good",
            "weak": "Weak",
            "pitfalls": "Failure Patterns and Fixes",
        },
        "decision-loop-stress-test": {
            "decision": "Stress",
            "action": "Run",
            "output": "Report",
            "failure": "Breaks If",
            "fix": "Repair",
            "write": "Report",
            "good": "Strong",
            "weak": "Weak",
            "pitfalls": "Collapse Patterns and Repairs",
        },
        "simulation-resource-loop-design": {
            "decision": "Map",
            "action": "Trace",
            "output": "Record",
            "failure": "Watch For",
            "fix": "Correct",
            "write": "Record",
            "good": "Healthy",
            "weak": "Weak",
            "pitfalls": "Loop Failures and Corrections",
        },
    }
    return profiles.get(
        skill_name,
        {
            "decision": "Decision",
            "action": "Do",
            "output": "Output",
            "failure": "Failure Signal",
            "fix": "Fix",
            "write": "Write",
            "good": "Good",
            "weak": "Weak",
            "pitfalls": "Failure Patterns and Fixes",
        },
    )


def build_skill_realization_spec(
    *,
    skill_name: str,
    task: str,
    program: SkillProgramIR,
) -> SkillRealizationSpec:
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    style_profile = expert_style_profile_for_skill(skill_name=skill_name, task=task)
    section_order = [
        "Overview",
        "Core Principle",
        "When to Use",
        "When Not to Use",
        "Inputs",
        "Default Workflow",
    ]
    if program.workflow_surface == "hybrid":
        section_order.append("Analysis Blocks")
    section_order.extend(
        [
            "Output Format",
            "Decision Rules",
            "Cut Rules",
            "Quality Checks",
            "Failure Patterns and Fixes",
            "Worked Micro-Example",
            "Voice Rules",
        ]
    )
    section_rhythm = list(getattr(style_profile, "section_rhythm", []) or [])
    opening_frame = str(getattr(style_profile, "opening_frame", "") or program.opening_strategy or "")
    sections = [
        SectionRealizationSpec(
            section_name=name,
            rhetorical_purpose=next(
                (entry.section_purpose for entry in list(getattr(corpus, "section_corpus", []) or []) if entry.section_name == name),
                f"Render `{name}` as a domain-facing section instead of a generic methodology block.",
            ),
            allowed_surface_forms=["compact", "direct", "judgment_first"],
            sentence_budget=2 if name in {"Overview", "Core Principle"} else 3,
            required_judgment_moves=next(
                (entry.judgment_moves[:4] for entry in list(getattr(corpus, "section_corpus", []) or []) if entry.section_name == name),
                [],
            ),
            forbidden_filler_patterns=list(getattr(style_profile, "forbidden_boilerplate", []) or []),
        )
        for name in section_order
    ]
    return SkillRealizationSpec(
        skill_name=skill_name,
        workflow_surface=program.workflow_surface,
        opening_frame=opening_frame,
        section_order=section_order,
        section_rhythm=section_rhythm,
        compression_policy="tight" if program.workflow_surface == "execution_spine" else "balanced",
        voice_profile=list(program.voice_constraints or []),
        boilerplate_forbidden=list(getattr(style_profile, "forbidden_boilerplate", []) or []),
        strategy_family="default",
        sections=sections,
        summary=[
            f"workflow_surface={program.workflow_surface}",
            f"section_count={len(section_order)}",
            f"section_rhythm={','.join(section_rhythm) or 'none'}",
        ],
    )


def _ordered_sections(base_order: list[str], preferred_tail: list[str]) -> list[str]:
    head = [item for item in base_order if item not in {
        "Output Format",
        "Decision Rules",
        "Cut Rules",
        "Quality Checks",
        "Failure Patterns and Fixes",
        "Worked Micro-Example",
        "Voice Rules",
    }]
    tail = [item for item in preferred_tail if item in base_order]
    for item in base_order:
        if item not in head and item not in tail:
            tail.append(item)
    ordered: list[str] = []
    for item in head + tail:
        if item not in ordered:
            ordered.append(item)
    return ordered


def _pressure_strategy_family(skill_name: str, workflow_surface: str, base_order: list[str]) -> list[dict[str, Any]]:
    families: dict[str, list[dict[str, Any]]] = {
        "concept-to-mvp-pack": [
            {
                "name": "proof_first",
                "opening_frame": "Decide what the first playable must prove before it grows.",
                "section_order": _ordered_sections(base_order, ["Quality Checks", "Cut Rules", "Output Format", "Failure Patterns and Fixes", "Worked Micro-Example", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 1, "Core Principle": 1, "Default Workflow": 5, "Quality Checks": 4},
                "workflow_mode": "validation_pressure",
                "step_frame": "proof_gate",
                "output_focus": ["Core Validation Question", "Smallest Honest Loop"],
                "quality_tone": "proof-first",
                "quality_mode": "proof_gate",
                "failure_style": "redesign_trigger",
                "failure_mode": "kill_or_fix",
                "strategy_tags": ["proof", "validation", "scope"],
            },
            {
                "name": "cut_first",
                "opening_frame": "Cut scope early, then prove the smallest playable that survives.",
                "section_order": _ordered_sections(base_order, ["Cut Rules", "Quality Checks", "Output Format", "Failure Patterns and Fixes", "Worked Micro-Example", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 1, "Cut Rules": 4, "Default Workflow": 4},
                "workflow_mode": "cut_pressure",
                "step_frame": "scope_gate",
                "output_focus": ["Feature Cut", "Out of Scope", "Minimum Content Package"],
                "quality_tone": "scope_enforcement",
                "quality_mode": "scope_gate",
                "failure_style": "scope_creep",
                "failure_mode": "scope_creep",
                "strategy_tags": ["cut", "scope", "out-of-scope"],
            },
            {
                "name": "package_ready",
                "opening_frame": "Turn the proof into a first-playable package that can actually be built next.",
                "section_order": _ordered_sections(base_order, ["Output Format", "Worked Micro-Example", "Quality Checks", "Cut Rules", "Failure Patterns and Fixes", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 2, "Output Format": 4, "Worked Micro-Example": 3},
                "workflow_mode": "package_readiness",
                "step_frame": "handoff_gate",
                "output_focus": ["MVP Pack", "Build Recommendation", "Minimum Content Package"],
                "quality_tone": "build_ready",
                "quality_mode": "build_gate",
                "failure_style": "pack_failure",
                "failure_mode": "handoff_failure",
                "strategy_tags": ["package", "build", "handoff"],
            },
            {
                "name": "failure_pass",
                "opening_frame": "Prove the first playable, then run a failure pass before approval.",
                "section_order": _ordered_sections(base_order, ["Failure Patterns and Fixes", "Quality Checks", "Output Format", "Cut Rules", "Worked Micro-Example", "Voice Rules", "Decision Rules"]),
                "sentence_budgets": {"Overview": 1, "Failure Patterns and Fixes": 5, "Quality Checks": 4},
                "workflow_mode": "failure_pass",
                "step_frame": "failure_pass",
                "output_focus": ["Failure Pass", "Build Recommendation", "Out of Scope"],
                "quality_tone": "failure_pass",
                "quality_mode": "failure_gate",
                "failure_style": "kill_or_fix",
                "failure_mode": "kill_or_fix",
                "strategy_tags": ["failure", "kill", "repair"],
            },
        ],
        "decision-loop-stress-test": [
            {
                "name": "pressure_first",
                "opening_frame": "Pressure-test the decision game before content smooths over weak structure.",
                "section_order": _ordered_sections(base_order, ["Quality Checks", "Failure Patterns and Fixes", "Output Format", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Default Workflow": 5, "Quality Checks": 4},
                "workflow_mode": "pressure_first",
                "step_frame": "pressure_probe",
                "output_focus": ["Pressure Map", "Break Point", "Repair Recommendation"],
                "quality_tone": "pressure",
                "quality_mode": "pressure_gate",
                "failure_style": "collapse_signals",
                "failure_mode": "collapse_signals",
                "strategy_tags": ["pressure", "stress", "breakpoint"],
            },
            {
                "name": "collapse_first",
                "opening_frame": "Find the collapse point before you propose new content or rewards.",
                "section_order": _ordered_sections(base_order, ["Failure Patterns and Fixes", "Quality Checks", "Decision Rules", "Output Format", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Failure Patterns and Fixes": 5, "Default Workflow": 4},
                "workflow_mode": "collapse_detection",
                "step_frame": "collapse_probe",
                "output_focus": ["Collapse Point", "Solved State Risk", "Repair Recommendation"],
                "quality_tone": "collapse",
                "quality_mode": "collapse_gate",
                "failure_style": "solved_state",
                "failure_mode": "solved_state",
                "strategy_tags": ["collapse", "solved-state", "dominance"],
            },
            {
                "name": "repair_first",
                "opening_frame": "Name the structural repair before anyone reaches for more content.",
                "section_order": _ordered_sections(base_order, ["Output Format", "Failure Patterns and Fixes", "Quality Checks", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Output Format": 4, "Failure Patterns and Fixes": 4},
                "workflow_mode": "repair_priority",
                "step_frame": "repair_commit",
                "output_focus": ["Repair Recommendation", "Pressure Map", "Variation Audit"],
                "quality_tone": "repair",
                "quality_mode": "repair_gate",
                "failure_style": "repair_moves",
                "failure_mode": "repair_moves",
                "strategy_tags": ["repair", "structure", "fix"],
            },
            {
                "name": "reinforcement_audit",
                "opening_frame": "Audit what mastery teaches before the wrong habit hardens.",
                "section_order": _ordered_sections(base_order, ["Decision Rules", "Quality Checks", "Output Format", "Failure Patterns and Fixes", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Decision Rules": 4, "Quality Checks": 4},
                "workflow_mode": "reinforcement_audit",
                "step_frame": "reinforcement_probe",
                "output_focus": ["Reinforcement Check", "Variation Audit", "Repair Recommendation"],
                "quality_tone": "reinforcement",
                "quality_mode": "reinforcement_gate",
                "failure_style": "wrong_behavior",
                "failure_mode": "wrong_behavior",
                "strategy_tags": ["reinforcement", "variation", "mastery"],
            },
        ],
        "simulation-resource-loop-design": [
            {
                "name": "map_first",
                "opening_frame": "Map the pressure web before you balance any single resource in isolation.",
                "section_order": _ordered_sections(base_order, ["Analysis Blocks", "Output Format", "Quality Checks", "Failure Patterns and Fixes", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Analysis Blocks": 5, "Output Format": 3},
                "workflow_mode": "map_first",
                "step_frame": "map_probe",
                "output_focus": ["Variable Web", "Pressure Relationships", "Main Feedback Loops"],
                "quality_tone": "mapping",
                "quality_mode": "mapping_gate",
                "failure_style": "hidden_pressure",
                "failure_mode": "hidden_pressure",
                "strategy_tags": ["map", "web", "visibility"],
            },
            {
                "name": "tension_first",
                "opening_frame": "Force visible tradeoffs before you optimize the system for smoothness.",
                "section_order": _ordered_sections(base_order, ["Quality Checks", "Analysis Blocks", "Output Format", "Failure Patterns and Fixes", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Quality Checks": 4, "Analysis Blocks": 4},
                "workflow_mode": "tension_first",
                "step_frame": "tension_probe",
                "output_focus": ["Primary Decision Tensions", "Pressure Relationships", "Failure and Recovery"],
                "quality_tone": "tension",
                "quality_mode": "tension_gate",
                "failure_style": "no_tradeoff",
                "failure_mode": "no_tradeoff",
                "strategy_tags": ["tension", "tradeoff", "pressure"],
            },
            {
                "name": "loop_balance",
                "opening_frame": "Balance positive and negative loops without letting either side erase the decision game.",
                "section_order": _ordered_sections(base_order, ["Output Format", "Analysis Blocks", "Quality Checks", "Failure Patterns and Fixes", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Output Format": 4, "Quality Checks": 4},
                "workflow_mode": "loop_balance",
                "step_frame": "loop_balance",
                "output_focus": ["Main Feedback Loops", "Failure and Recovery", "Emotional Fantasy Alignment"],
                "quality_tone": "balance",
                "quality_mode": "balance_gate",
                "failure_style": "runaway_loops",
                "failure_mode": "runaway_loops",
                "strategy_tags": ["loops", "balance", "counterweight"],
            },
            {
                "name": "recovery_cost",
                "opening_frame": "Design recovery that preserves cost, clarity, and fantasy instead of flattening the system.",
                "section_order": _ordered_sections(base_order, ["Failure Patterns and Fixes", "Output Format", "Analysis Blocks", "Quality Checks", "Decision Rules", "Cut Rules", "Worked Micro-Example", "Voice Rules"]),
                "sentence_budgets": {"Overview": 1, "Failure Patterns and Fixes": 5, "Output Format": 4},
                "workflow_mode": "recovery_cost",
                "step_frame": "recovery_cost",
                "output_focus": ["Failure and Recovery", "Main Feedback Loops", "Emotional Fantasy Alignment"],
                "quality_tone": "recovery_cost",
                "quality_mode": "recovery_gate",
                "failure_style": "cheap_recovery",
                "failure_mode": "cheap_recovery",
                "strategy_tags": ["recovery", "cost", "fantasy"],
            },
        ],
    }
    default_family = [
        {
            "name": "balanced",
            "opening_frame": "",
            "section_order": list(base_order),
            "sentence_budgets": {},
            "workflow_mode": workflow_surface,
            "step_frame": workflow_surface,
            "output_focus": [],
            "quality_tone": "balanced",
            "quality_mode": "balanced",
            "failure_style": "balanced",
            "failure_mode": "balanced",
            "strategy_tags": [workflow_surface],
        }
    ]
    return families.get(skill_name, default_family)


def _spec_for_strategy(
    *,
    base_spec: SkillRealizationSpec,
    strategy_profile: dict[str, Any],
) -> SkillRealizationSpec:
    budget_overrides = dict(strategy_profile.get("sentence_budgets") or {})
    section_order = list(strategy_profile.get("section_order") or list(base_spec.section_order or []))
    section_map = {section.section_name: section for section in list(base_spec.sections or [])}
    sections: list[SectionRealizationSpec] = []
    for section_name in section_order:
        current = section_map.get(section_name)
        if current is None:
            continue
        sections.append(
            current.model_copy(
                update={
                    "sentence_budget": int(budget_overrides.get(section_name, current.sentence_budget or 3)),
                    "section_form": str(strategy_profile.get("workflow_mode") or current.section_form or "compact"),
                    "primary_force_focus": str(strategy_profile.get("quality_tone") or current.primary_force_focus or ""),
                    "emphasis_level": "high"
                    if section_name in {"Default Workflow", "Output Format", "Quality Checks", "Failure Patterns and Fixes"}
                    else current.emphasis_level,
                }
            )
        )
    return base_spec.model_copy(
        update={
            "opening_frame": str(strategy_profile.get("opening_frame") or base_spec.opening_frame),
            "section_order": section_order,
            "compression_policy": "tight" if "tight" in strategy_profile.get("strategy_tags", []) else base_spec.compression_policy,
            "strategy_family": "pressure_first",
            "strategy_tags": list(strategy_profile.get("strategy_tags") or []),
            "sections": sections,
        }
    )


def _strategy_budget_signature(strategy_profile: dict[str, Any]) -> str:
    budgets = dict(strategy_profile.get("sentence_budgets") or {})
    if not budgets:
        return "default"
    return ",".join(f"{name}:{int(value)}" for name, value in sorted(budgets.items()))


def _artifact_for_markdown(content: str) -> Artifacts:
    return Artifacts(files=[ArtifactFile(path="SKILL.md", content=content, content_type="text/markdown")])


def _request_plan(skill_name: str, task: str) -> tuple[SkillCreateRequestV6, SkillPlan]:
    return (
        SkillCreateRequestV6(task=task, skill_name_hint=skill_name, skill_archetype="methodology_guidance"),
        SkillPlan(skill_name=skill_name, skill_archetype="methodology_guidance"),
    )


def _candidate_editorial_metrics(
    *,
    skill_name: str,
    task: str,
    markdown: str,
    realization_candidate_count: int = 0,
) -> dict[str, Any]:
    from .skill_task_outcome import build_skill_task_outcome_report

    request, plan = _request_plan(skill_name, task)
    artifacts = _artifact_for_markdown(markdown)
    body = build_skill_body_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    domain_specificity = build_skill_domain_specificity_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    domain_expertise = build_skill_domain_expertise_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    depth = build_skill_depth_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    editorial = build_skill_editorial_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    style = build_skill_style_diversity_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    move = build_skill_move_quality_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
    )
    task_outcome = build_skill_task_outcome_report(
        generated_skill_markdown_by_name={skill_name: markdown},
        skill_names=[skill_name],
    )
    profile_result = next(iter(list(task_outcome.profile_results or [])), None)
    editorial_force = build_skill_editorial_force_report(
        request=request,
        skill_plan=plan,
        artifacts=artifacts,
        body_quality=body,
        domain_specificity=domain_specificity,
        domain_expertise=domain_expertise,
        depth_quality=depth,
        editorial_quality=editorial,
        style_diversity=style,
        move_quality=move,
        realization_candidate_count=realization_candidate_count,
    )
    score = (
        0.25 * float(getattr(editorial_force, "decision_pressure_score", 0.0) or 0.0)
        + 0.18 * float(getattr(editorial_force, "cut_sharpness_score", 0.0) or 0.0)
        + 0.16 * float(getattr(editorial_force, "failure_repair_force", 0.0) or 0.0)
        + 0.12 * float(getattr(editorial_force, "output_executability_score", 0.0) or 0.0)
        + 0.10 * float(getattr(editorial_force, "boundary_rule_coverage", 0.0) or 0.0)
        + 0.08 * float(getattr(editorial_force, "stop_condition_coverage", 0.0) or 0.0)
        + 0.06 * float(getattr(editorial_force, "section_force_distinctness", 0.0) or 0.0)
        + 0.05 * float(getattr(style, "domain_rhythm_score", 0.0) or 0.0)
        + 0.05 * max(0.0, 1.0 - float(getattr(editorial, "redundancy_ratio", 0.0) or 0.0))
    )
    return {
        "body": body,
        "domain_specificity": domain_specificity,
        "domain_expertise": domain_expertise,
        "depth": depth,
        "editorial": editorial,
        "editorial_force": editorial_force,
        "style": style,
        "move": move,
        "task_outcome": task_outcome,
        "domain_move_coverage": float(getattr(domain_expertise, "domain_move_coverage", 0.0) or 0.0),
        "section_depth_score": float(getattr(depth, "section_depth_score", 0.0) or 0.0),
        "task_outcome_with_skill_average": float(getattr(profile_result, "with_skill_average", 0.0) or 0.0),
        "redundancy_ratio": float(getattr(editorial, "redundancy_ratio", 0.0) or 0.0),
        "shared_opening_phrase_ratio": float(getattr(style, "shared_opening_phrase_ratio", 0.0) or 0.0),
        "cross_case_similarity": 0.0,
        "compression_without_loss": float(getattr(editorial_force, "compression_without_loss", 0.0) or 0.0),
        "score": round(score, 4),
    }


def _section_entries(corpus: ExpertSkillCorpusEntry | None, section_name: str) -> list[ExpertSectionCorpusEntry]:
    if corpus is None:
        return []
    return [
        entry
        for entry in list(getattr(corpus, "section_corpus", []) or [])
        if entry.section_name == section_name
    ]


def _strategy_rewrite_pairs(
    *,
    corpus: ExpertSkillCorpusEntry | None,
    strategy_profile: dict[str, Any],
) -> list[ExpertRewritePair]:
    if corpus is None:
        return []
    tags = {str(item).lower() for item in list(strategy_profile.get("strategy_tags") or [])}
    quality_tone = str(strategy_profile.get("quality_tone") or "").lower()
    results: list[ExpertRewritePair] = []
    for pair in list(getattr(corpus, "rewrite_pairs", []) or []):
        reason = str(pair.revision_reason or "").lower()
        weak = str(pair.weak_shell or "").lower()
        if quality_tone and quality_tone in reason:
            results.append(pair)
            continue
        if any(tag in reason or tag in weak for tag in tags):
            results.append(pair)
    return results[:2]


def _strategy_failure_cases(
    *,
    corpus: ExpertSkillCorpusEntry | None,
    strategy_profile: dict[str, Any],
) -> list[ExpertFailureCase]:
    if corpus is None:
        return []
    failure_mode = str(strategy_profile.get("failure_mode") or "").lower()
    quality_tone = str(strategy_profile.get("quality_tone") or "").lower()
    results: list[ExpertFailureCase] = []
    for failure in list(getattr(corpus, "failure_cases", []) or []):
        failure_type = str(failure.failure_type or "").lower()
        why = str(failure.why_it_fails or "").lower()
        if failure_mode and (failure_mode in failure_type or failure_mode in why):
            results.append(failure)
            continue
        if quality_tone and quality_tone in why:
            results.append(failure)
    if not results:
        results = list(getattr(corpus, "failure_cases", []) or [])
    return results[:2]


def _strategy_primary_moves(
    *,
    corpus: ExpertSkillCorpusEntry | None,
    section_name: str,
    strategy_profile: dict[str, Any],
) -> list[str]:
    tags = {str(item).lower() for item in list(strategy_profile.get("strategy_tags") or [])}
    moves: list[str] = []
    for entry in _section_entries(corpus, section_name):
        for item in list(entry.judgment_moves or []):
            lowered = item.lower()
            if not tags or any(tag in lowered for tag in tags):
                if item not in moves:
                    moves.append(item)
    if moves:
        return moves[:3]
    return [item for entry in _section_entries(corpus, section_name) for item in list(entry.judgment_moves or [])[:2]][:3]


def _section_variant_text(
    *,
    section_name: str,
    strategy: str,
    strategy_profile: dict[str, Any],
    plan: Any,
    program: SkillProgramIR,
    corpus: ExpertSkillCorpusEntry | None,
) -> list[str]:
    output_focus = list(strategy_profile.get("output_focus") or [])
    quality_tone = str(strategy_profile.get("quality_tone") or "")
    failure_style = str(strategy_profile.get("failure_style") or "")
    rewrite_pairs = _strategy_rewrite_pairs(corpus=corpus, strategy_profile=strategy_profile)
    failure_cases = _strategy_failure_cases(corpus=corpus, strategy_profile=strategy_profile)
    section_moves = _strategy_primary_moves(corpus=corpus, section_name=section_name, strategy_profile=strategy_profile)
    if section_name == "Overview":
        overview_lines = {
            ("concept-to-mvp-pack", "proof_first"): "Start with a question that can fail, then shrink the playable until the proof is honest.",
            ("concept-to-mvp-pack", "cut_first"): "Treat scope as suspect until the smallest surviving proof is clear.",
            ("concept-to-mvp-pack", "package_ready"): "Lock the proof first, then shape the smallest build-ready pack around it.",
            ("concept-to-mvp-pack", "failure_pass"): "Approve the first playable only after a failure pass says what would force a redesign in a greybox build with stubbed content.",
            ("decision-loop-stress-test", "pressure_first"): "Stress each phase until the decision game produces pressure instead of novelty.",
            ("decision-loop-stress-test", "collapse_first"): "Find the collapse point before you discuss more content, rewards, or pacing cover.",
            ("decision-loop-stress-test", "repair_first"): "Name the structural fix before anyone suggests softer compensation.",
            ("decision-loop-stress-test", "reinforcement_audit"): "Check what mastery teaches, then strip reward from the wrong habit.",
            ("simulation-resource-loop-design", "map_first"): "Start by drawing the pressure web; only then judge balance inside it.",
            ("simulation-resource-loop-design", "tension_first"): "Lead with tradeoffs that hurt in visible ways, not with resource lists.",
            ("simulation-resource-loop-design", "loop_balance"): "Balance positive and negative loops so neither side erases the decision game.",
            ("simulation-resource-loop-design", "recovery_cost"): "Recovery should preserve cost, visibility, and fantasy instead of flattening the system.",
        }
        overview = overview_lines.get((program.skill_name, strategy), str(plan.overview or "").strip())
        return [overview or str(strategy_profile.get("opening_frame") or plan.overview)]
    if section_name == "Core Principle":
        lines = [str(getattr(plan.dna, "core_thesis", "") or "")]
        if quality_tone in {"proof-first", "pressure", "tension"}:
            if section_moves:
                lines.append(f"Keep the section anchored on: {', '.join(section_moves[:2])}.")
            return lines[:2]
        if corpus is not None and corpus.expert_notes:
            lines.append(corpus.expert_notes[min(1, len(corpus.expert_notes) - 1)])
        return lines
    if section_name == "Quality Checks":
        if quality_tone == "pressure":
            lines = ["Force a structural answer before anyone reaches for softer compensation."]
        elif quality_tone == "scope_enforcement":
            lines = ["Cut anything that protects comfort instead of proof."]
        elif quality_tone == "recovery_cost":
            lines = ["Keep recovery meaningful instead of flattening the loop."]
        elif quality_tone == "build_ready":
            lines = ["Only keep checks that make the pack buildable without hidden scope."]
        else:
            lines = []
        if section_moves:
            lines.append(f"Keep the checks anchored on {', '.join(section_moves[:2])}.")
        return lines[:2]
    if section_name == "Failure Patterns and Fixes":
        if failure_style == "solved_state":
            return ["Treat solved states and fake variation as structure failures, not balance trivia."]
        if failure_style == "cheap_recovery":
            return ["Treat cheap recovery and invisible pressure as core loop failures, not polish issues."]
        if failure_style == "scope_creep":
            return ["Treat anything that dilutes the proof or hides uncertainty as a failure, not a nice-to-have."]
        if failure_style == "repair_moves":
            return ["Treat repairs that add content without changing pressure as false fixes."]
        if failure_cases:
            return [failure_cases[0].why_it_fails]
        return []
    if section_name == "Output Format" and output_focus:
        lines = [f"Lead with `{output_focus[0]}` and keep the rest of the output subordinate to that decision."]
        if len(output_focus) > 1:
            lines.append(f"Secondary emphasis: {', '.join(output_focus[1:3])}.")
        return lines[:2]
    return []


def _strip_guidance_prefix(text: str, label: str) -> str:
    stripped = str(text or "").strip()
    lowered = stripped.lower()
    prefixes = [f"{label.lower()}:", label.lower()]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            stripped = stripped[len(prefix):].strip(" :")
            break
    return stripped or str(text or "").strip()


def _render_quality_checks(
    *,
    skill_name: str,
    strategy_profile: dict[str, Any],
    plan: Any,
    program: SkillProgramIR,
    corpus: ExpertSkillCorpusEntry | None,
) -> list[str]:
    lines = ["## Quality Checks", ""]
    gate_line = PROFILE_QUALITY_GATE_LINES.get(skill_name, "")
    if gate_line:
        lines.append(f"- Gate: {gate_line}")
    for item in PROFILE_QUALITY_CHECK_LINES.get(skill_name, []):
        lines.append(f"- {item}")
    lines.append("")
    return lines


def _failure_entries(
    *,
    skill_name: str,
    corpus: ExpertSkillCorpusEntry | None,
) -> list[tuple[str, str, str, str]]:
    entries = list(PROFILE_FAILURE_ENTRIES.get(skill_name, []))
    if entries:
        if skill_name == "simulation-resource-loop-design":
            return entries[:6]
        return entries[:5]
    if corpus is None:
        return []
    results: list[tuple[str, str, str, str]] = []
    for failure in list(corpus.failure_cases or [])[:6]:
        results.append(
            (
                str(failure.failure_type or "Failure").replace("-", " ").title(),
                str(failure.bad_output or "The output collapses into a generic answer."),
                str(failure.why_it_fails or "The workflow skipped the hard judgment."),
                str(failure.repair_direction or "Return to the workflow and make the decision explicit."),
            )
        )
    return results


def _render_output_fields(
    *,
    program: SkillProgramIR,
    labels: dict[str, str],
    strategy: str,
    strategy_profile: dict[str, Any],
) -> list[str]:
    output_opening = {
        "concept-to-mvp-pack": "Fill the template so a greybox or cardboard first playable can be greenlit or killed without rereading the pitch deck, wireframe notes, or telemetry plan.",
        "decision-loop-stress-test": "Fill the template so the collapse point, solved state, and repair can be acted on immediately.",
        "simulation-resource-loop-design": "Fill the template so the pressure web, recovery cost, and fantasy fit stay visible in one pass.",
    }.get(program.skill_name, "Fill the template so the next decision is explicit, testable, and ready to act on.")
    fence_language = "text" if program.skill_name == "concept-to-mvp-pack" else "markdown"
    lines = ["## Output Format", "", output_opening, "", f"```{fence_language}"]
    focus = [field for field in list(strategy_profile.get("output_focus") or []) if field in program.output_schema]
    ordered_fields = focus + [field for field in program.output_schema.keys() if field not in focus]
    quality_mode = str(strategy_profile.get("quality_mode") or "")
    for field in ordered_fields:
        guidance_lines = program.output_schema.get(field, [])
        lines.append(f"## {field}")
        write_line = _strip_guidance_prefix(guidance_lines[0], labels["write"]) if guidance_lines else "<fill in>"
        lines.append(f"- {labels['write']}: {write_line}")
        if len(guidance_lines) > 1:
            lines.append(f"- {labels['good']}: {_strip_guidance_prefix(guidance_lines[1], labels['good'])}")
        if len(guidance_lines) > 2:
            lines.append(f"- {labels['weak']}: {_strip_guidance_prefix(guidance_lines[2], labels['weak'])}")
        if field in focus:
            focus_note = {
                "proof_gate": "Make this field strong enough to prove or kill the first playable.",
                "scope_gate": "Make this field sharp enough to remove supportive scope without debate.",
                "build_gate": "Make this field handoff-ready so a builder can act immediately.",
                "pressure_gate": "Make this field sharp enough to expose where the loop breaks.",
                "collapse_gate": "Make this field show the exact collapse point or solved-state risk.",
                "repair_gate": "Make this field point to the structural repair, not extra content.",
                "mapping_gate": "Make this field reveal the pressure web instead of listing resources.",
                "tension_gate": "Make this field state the tradeoff the player can actually feel.",
                "balance_gate": "Make this field show how positive and negative loops stay in tension.",
                "recovery_gate": "Make this field preserve cost and consequence instead of flattening recovery.",
            }.get(quality_mode, "Keep this field sharp enough to drive the next decision.")
            lines.append(f"- Focus: {focus_note}")
        lines.append("")
    lines.extend(["```", ""])
    return lines


def _render_workflow(
    *,
    skill_name: str,
    program: SkillProgramIR,
    labels: dict[str, str],
    strategy: str,
    strategy_profile: dict[str, Any],
) -> list[str]:
    lines = ["## Default Workflow", ""]
    workflow_mode = str(strategy_profile.get("workflow_mode") or "")
    step_frame = str(strategy_profile.get("step_frame") or "")
    workflow_orders = {
        "validation_pressure": ["decision", "action", "output", "failure", "fix"],
        "cut_pressure": ["decision", "failure", "action", "output", "fix"],
        "package_readiness": ["decision", "output", "action", "failure", "fix"],
        "failure_pass": ["decision", "failure", "fix", "output", "action"],
        "pressure_first": ["decision", "action", "failure", "output", "fix"],
        "collapse_detection": ["decision", "failure", "action", "fix", "output"],
        "repair_priority": ["decision", "fix", "failure", "output", "action"],
        "reinforcement_audit": ["decision", "action", "output", "fix", "failure"],
        "map_first": ["decision", "action", "output", "failure", "fix"],
        "tension_first": ["decision", "failure", "action", "output", "fix"],
        "loop_balance": ["decision", "action", "output", "fix", "failure"],
        "recovery_cost": ["decision", "failure", "fix", "action", "output"],
    }
    step_openers = {
        "proof_gate": "Push this step until the loop earns the right to stay.",
        "scope_gate": "Use this step to remove anything that only makes the idea feel safer.",
        "handoff_gate": "Use this step to leave the next builder with a concrete pack, not a concept note.",
        "failure_pass": "Use this step to surface what would kill the MVP before more scope sneaks in.",
        "pressure_probe": "Use this step to pressure the loop until the weak decision shows itself.",
        "collapse_probe": "Use this step to find where the loop caves in or goes automatic.",
        "repair_commit": "Use this step to commit to the structural fix before adding comfort.",
        "reinforcement_probe": "Use this step to check what behavior the system is actually teaching.",
        "map_probe": "Use this step to map the visible pressure before tuning any single variable.",
        "tension_probe": "Use this step to state the tradeoff before the loop gets smoothed over.",
        "loop_balance": "Use this step to prove the loop has both drive and restraint.",
        "recovery_cost": "Use this step to keep recovery meaningful instead of consequence-free.",
    }
    order = workflow_orders.get(workflow_mode, ["decision", "action", "output", "failure", "fix"])
    render_fields = {
        "decision": lambda move: f"   - {labels['decision']}: {move.decision}",
        "action": lambda move: f"   - {labels['action']}: {move.action}",
        "output": lambda move: f"   - {labels['output']}: {move.output}",
        "failure": lambda move: f"   - {labels['failure']}: {move.failure_signal}",
        "fix": lambda move: f"   - {labels['fix']}: {move.fix}",
    }
    for index, move in enumerate(program.execution_spine, start=1):
        decision_text = move.decision
        action_text = move.action
        if skill_name == "decision-loop-stress-test":
            if move.label == "Test Late-Game Expansion or Mutation":
                decision_text = "Test whether lategame mastery reveals a deeper problem or solves the game away."
            elif move.label == "Look for Solved States":
                decision_text = "Test which solved state a strong player would repeat until the loop becomes stale."
            elif move.label == "Audit Variation and Reinforcement":
                decision_text = "Test whether variation quality changes read, tradeoff, consequence, or adaptation."
                action_text = "Audit variation quality and reinforcement so the decision loop trains the intended behavior."
        lines.append(f"{index}. **{move.label}**")
        if step_frame in step_openers:
            lines.append(f"   - Frame: {step_openers[step_frame]}")
        for key in order:
            if key == "decision":
                lines.append(f"   - {labels['decision']}: {decision_text}")
            elif key == "action":
                lines.append(f"   - {labels['action']}: {action_text}")
            else:
                lines.append(render_fields[key](move))
        if strategy_profile.get("quality_tone") not in {"pressure", "collapse", "repair", "recovery_cost"} and move.must_include_terms:
            lines.append(f"   - Must include: {', '.join(move.must_include_terms[:5])}.")
        lines.append("")
    return lines


def _render_analysis_blocks(program: SkillProgramIR, strategy_profile: dict[str, Any]) -> list[str]:
    if not program.analysis_blocks:
        return []
    lines = ["## Analysis Blocks", ""]
    quality_tone = str(strategy_profile.get("quality_tone") or "")
    lead_prefix = {
        "mapping": "Signal",
        "tension": "Tension",
        "balance": "Loop",
        "recovery_cost": "Recovery",
    }.get(quality_tone, "Focus")
    for block in program.analysis_blocks:
        lines.append(f"### {block.name}")
        lines.append(f"- {lead_prefix}: {block.questions[0] if block.questions else block.when_used}")
        if block.questions:
            for item in block.questions[1:2]:
                prefix = {
                    "tension": "Tradeoff",
                    "recovery_cost": "Cost",
                    "balance": "Counterweight",
                    "mapping": "Signal",
                }.get(quality_tone, "Check")
                lines.append(f"- {prefix}: {item}")
        if block.output_fields:
            lines.append(f"- Output: {', '.join(block.output_fields)}")
        lines.append("")
    return lines


def _render_candidate_markdown(
    *,
    program: SkillProgramIR,
    spec: SkillRealizationSpec,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
    strategy: str,
    strategy_profile: dict[str, Any],
) -> str:
    plan = build_domain_move_plan(skill_name=skill_name, task=task)
    corpus = expert_corpus_entry_for_skill(skill_name=skill_name)
    if plan is None:
        return ""
    labels = _surface_label_profile(skill_name)
    frontmatter_description = (
        PROFILE_FRONTMATTER_DESCRIPTIONS.get(skill_name)
        or (plan.opening_frame or program.opening_strategy or description or "").strip().splitlines()[0].strip()
    )
    lines = [
        "---",
        f"name: {skill_name}",
        f"description: {frontmatter_description}",
        "---",
        "",
        f"# {skill_name}",
        "",
        str(strategy_profile.get("opening_frame") or spec.opening_frame or program.opening_strategy or plan.opening_frame),
        "",
    ]
    for section_name in spec.section_order:
        if section_name == "Overview":
            lines.extend(["## Overview", ""])
            lines.extend(_section_variant_text(section_name=section_name, strategy=strategy, strategy_profile=strategy_profile, plan=plan, program=program, corpus=corpus))
            lines.extend([""])
        elif section_name == "Core Principle":
            lines.extend(["## Core Principle", ""])
            lines.extend(_section_variant_text(section_name=section_name, strategy=strategy, strategy_profile=strategy_profile, plan=plan, program=program, corpus=corpus))
            lines.extend([""])
        elif section_name == "When to Use":
            lines.extend(["## When to Use", ""])
            lines.extend(f"- {item}" for item in plan.when_to_use)
            lines.extend([""])
        elif section_name == "When Not to Use":
            lines.extend(["## When Not to Use", ""])
            lines.extend(f"- {item}" for item in plan.when_not_to_use)
            lines.extend([""])
        elif section_name == "Inputs":
            lines.extend(["## Inputs", ""])
            lines.extend(f"- {item}" for item in plan.inputs)
            lines.extend([""])
        elif section_name == "Default Workflow":
            lines.extend(_render_workflow(skill_name=skill_name, program=program, labels=labels, strategy=strategy, strategy_profile=strategy_profile))
        elif section_name == "Analysis Blocks":
            lines.extend(_render_analysis_blocks(program, strategy_profile))
        elif section_name == "Output Format":
            lines.extend(_render_output_fields(program=program, labels=labels, strategy=strategy, strategy_profile=strategy_profile))
        elif section_name == "Decision Rules":
            lines.extend(["## Decision Rules", ""])
            lines.extend(f"- {item}" for item in program.decision_rules)
            lines.extend([""])
        elif section_name == "Cut Rules":
            lines.extend(["## Cut Rules", ""])
            lines.extend(f"- {item}" for item in program.cut_rules)
            lines.extend([""])
        elif section_name == "Quality Checks":
            lines.extend(
                _render_quality_checks(
                    skill_name=skill_name,
                    strategy_profile=strategy_profile,
                    plan=plan,
                    program=program,
                    corpus=corpus,
                )
            )
        elif section_name == "Failure Patterns and Fixes":
            lines.extend([f"## Common Pitfalls: {labels['pitfalls']}", ""])
            intro_lines = _section_variant_text(section_name=section_name, strategy=strategy, strategy_profile=strategy_profile, plan=plan, program=program, corpus=corpus)
            lines.extend(intro_lines[:1])
            if intro_lines:
                lines.append("")
            pattern_names = [item.split(" -> ", 1)[0] for item in list(program.failure_repairs or [])]
            repair_moves = []
            for item in list(program.failure_repairs or []):
                _, _, fix = item.partition(" -> ")
                if fix and fix not in repair_moves:
                    repair_moves.append(fix)
            profile_preface = {
                "concept-to-mvp-pack": "Use these failure patterns to pressure-test the feature cut, out-of-scope line, and first playable package.",
                "decision-loop-stress-test": "Use these failure patterns to pressure-test lategame, variation quality, solved state, and reinforcement before adding content.",
                "simulation-resource-loop-design": "Use these failure patterns to check variable web clarity, pressure relationships, and failure recovery without collapsing into one simple currency, isolated meters, mostly content writing, or anything weaker than a few strong tensions.",
            }.get(skill_name, "")
            if profile_preface:
                lines.append(f"- {profile_preface}")
            if pattern_names:
                lines.append(f"- Pattern index: {', '.join(pattern_names)}.")
            if repair_moves:
                lines.append(f"- Repair moves: {', '.join(repair_moves)}.")
            if profile_preface or pattern_names or repair_moves:
                lines.append("")
            for title, symptom, cause, correction in _failure_entries(skill_name=skill_name, corpus=corpus):
                lines.append(f"### {title}")
                lines.append(f"- Symptom: {symptom}")
                lines.append(f"- Cause: {cause}")
                lines.append(f"- Correction: {correction}")
                lines.append("")
        elif section_name == "Worked Micro-Example":
            lines.extend(["## Worked Micro-Example", ""])
            if corpus is not None and corpus.expected_outputs:
                lines.extend(f"- {item}" for item in corpus.expected_outputs[:3])
            else:
                lines.append("- Use the workflow to produce a compact decision-facing output with explicit evidence and next action.")
            lines.extend([""])
        elif section_name == "Voice Rules":
            lines.extend(["## Voice Rules", ""])
            lines.extend(f"- {item}" for item in program.voice_constraints)
            lines.extend([""])
    if references:
        lines.extend(["## References", ""])
        lines.extend(f"- See `{path}` for supporting material." for path in references)
        lines.extend([""])
    if scripts:
        lines.extend(["## Helpers", ""])
        lines.extend(f"- Use `{path}` only when it directly supports this workflow." for path in scripts)
        lines.extend([""])
    return "\n".join(lines).rstrip() + "\n"


def build_skill_realization_candidates(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
    candidate_dna: ExpertSkillDNA | None = None,
) -> tuple[SkillProgramIR | None, SkillRealizationSpec | None, list[SkillRealizationCandidate]]:
    program = build_skill_program_ir(skill_name=skill_name, task=task, candidate_dna=candidate_dna)
    if program is None:
        return None, None, []
    spec = build_skill_realization_spec(skill_name=skill_name, task=task, program=program)
    strategies = _pressure_strategy_family(skill_name, program.workflow_surface, list(spec.section_order or []))
    base_candidates: list[SkillRealizationCandidate] = []
    for index, strategy_profile in enumerate(strategies, start=1):
        strategy = str(strategy_profile.get("name") or f"variant_{index}")
        strategy_spec = _spec_for_strategy(base_spec=spec, strategy_profile=strategy_profile)
        base_candidates.append(
            SkillRealizationCandidate(
                candidate_id=f"{skill_name}:{strategy}:{index}",
                skill_name=skill_name,
                program_id=f"{skill_name}:{program.workflow_surface}",
                realization_strategy=strategy,
                strategy_family=str(strategy_spec.strategy_family or "pressure_first"),
                strategy_profile={
                    "compression_stage": "pre",
                    "opening_frame": str(strategy_profile.get("opening_frame") or ""),
                    "section_order": " > ".join(list(strategy_spec.section_order or [])),
                    "sentence_budget_profile": _strategy_budget_signature(strategy_profile),
                    "workflow_mode": str(strategy_profile.get("workflow_mode") or ""),
                    "step_frame": str(strategy_profile.get("step_frame") or ""),
                    "output_focus": ",".join(list(strategy_profile.get("output_focus") or [])),
                    "quality_tone": str(strategy_profile.get("quality_tone") or ""),
                    "quality_mode": str(strategy_profile.get("quality_mode") or ""),
                    "failure_style": str(strategy_profile.get("failure_style") or ""),
                    "failure_mode": str(strategy_profile.get("failure_mode") or ""),
                },
                rendered_markdown=_render_candidate_markdown(
                    program=program,
                    spec=strategy_spec,
                    skill_name=skill_name,
                    description=description,
                    task=task,
                    references=references,
                    scripts=scripts,
                    strategy=strategy,
                    strategy_profile=strategy_profile,
                ),
                diagnostic_summary=[
                    f"strategy={strategy}",
                    f"workflow_surface={program.workflow_surface}",
                    f"workflow_mode={strategy_profile.get('workflow_mode', '')}",
                    f"quality_tone={strategy_profile.get('quality_tone', '')}",
                    f"failure_style={strategy_profile.get('failure_style', '')}",
                ],
            )
        )
    scored_base = [
        (
            candidate,
            _candidate_editorial_metrics(
                skill_name=skill_name,
                task=task,
                markdown=candidate.rendered_markdown,
                realization_candidate_count=len(base_candidates),
            ),
        )
        for candidate in base_candidates
    ]
    scored_base.sort(key=lambda item: _coverage_rank_key(skill_name, item[1]), reverse=True)
    compressed_candidates: list[SkillRealizationCandidate] = []
    for candidate, source_metrics in scored_base[:2]:
        compressed_candidate = _compress_candidate_sections(
            skill_name=skill_name,
            candidate=candidate,
            program=program,
        )
        compressed_metrics = _candidate_editorial_metrics(
            skill_name=skill_name,
            task=task,
            markdown=compressed_candidate.rendered_markdown,
            realization_candidate_count=len(base_candidates),
        )
        source_force = _primary_force_values(skill_name, source_metrics.get("editorial_force"))
        compressed_force = _primary_force_values(skill_name, compressed_metrics.get("editorial_force"))
        source_coverage = _coverage_values(source_metrics, skill_name)
        compressed_coverage = _coverage_values(compressed_metrics, skill_name)
        force_regressed = any(
            compressed_force.get(metric, 0.0) + 0.01 < source_force.get(metric, 0.0)
            for metric in _primary_force_metric_names(skill_name)
        )
        coverage_regressed = any(
            compressed_coverage.get(metric, 0.0) + 0.01 < source_coverage.get(metric, 0.0)
            for metric in _coverage_metric_names(skill_name)
        )
        if force_regressed or coverage_regressed:
            continue
        compressed_candidates.append(compressed_candidate)
    return program, spec, base_candidates + compressed_candidates


def _current_best_editorial_metrics(skill_name: str, task: str) -> dict[str, Any] | None:
    current_best = _current_best_markdown(skill_name)
    if not current_best.strip():
        return None
    return _candidate_editorial_metrics(
        skill_name=skill_name,
        task=task,
        markdown=current_best,
    )


def _primary_force_metric_names(skill_name: str) -> list[str]:
    return {
        "concept-to-mvp-pack": [
            "decision_pressure_score",
            "cut_sharpness_score",
            "boundary_rule_coverage",
            "output_executability_score",
        ],
        "decision-loop-stress-test": [
            "decision_pressure_score",
            "cut_sharpness_score",
            "failure_repair_force",
            "stop_condition_coverage",
        ],
        "simulation-resource-loop-design": [
            "decision_pressure_score",
            "failure_repair_force",
            "section_force_distinctness",
            "boundary_rule_coverage",
        ],
    }.get(
        skill_name,
        [
            "decision_pressure_score",
            "cut_sharpness_score",
            "failure_repair_force",
            "output_executability_score",
        ],
    )


def _primary_force_values(skill_name: str, editorial_force: SkillEditorialForceReport | None) -> dict[str, float]:
    if editorial_force is None:
        return {metric: 0.0 for metric in _primary_force_metric_names(skill_name)}
    return {
        metric: round(float(getattr(editorial_force, metric, 0.0) or 0.0), 4)
        for metric in _primary_force_metric_names(skill_name)
    }


def _candidate_rank_key(skill_name: str, metrics: dict[str, Any]) -> tuple[float, ...]:
    editorial_force = metrics.get("editorial_force")
    values = _primary_force_values(skill_name, editorial_force)
    ordered_primary = tuple(round(values.get(metric, 0.0), 4) for metric in _primary_force_metric_names(skill_name))
    return (
        *ordered_primary,
        round(float(getattr(editorial_force, "output_executability_score", 0.0) or 0.0), 4),
        round(float(getattr(editorial_force, "section_force_distinctness", 0.0) or 0.0), 4),
        round(max(0.0, 1.0 - float(getattr(metrics.get("editorial"), "redundancy_ratio", 0.0) or 0.0)), 4),
        round(float(metrics.get("score", 0.0) or 0.0), 4),
    )


def _coverage_metric_names(skill_name: str) -> list[str]:
    return {
        "concept-to-mvp-pack": [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
        "decision-loop-stress-test": [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
        "simulation-resource-loop-design": [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
    }.get(
        skill_name,
        [
            "domain_move_coverage",
            "section_depth_score",
            "task_outcome_with_skill_average",
        ],
    )


def _compactness_metric_names(skill_name: str) -> list[str]:
    return {
        "concept-to-mvp-pack": [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
        "decision-loop-stress-test": [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
        "simulation-resource-loop-design": [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
    }.get(
        skill_name,
        [
            "redundancy_ratio",
            "shared_opening_phrase_ratio",
            "cross_case_similarity",
        ],
    )


def _coverage_values(metrics: dict[str, Any], skill_name: str) -> dict[str, float]:
    domain_expertise = metrics.get("domain_expertise")
    depth = metrics.get("depth")
    task_outcome = metrics.get("task_outcome")
    profile_result = next(iter(list(getattr(task_outcome, "profile_results", []) or [])), None) if task_outcome is not None else None
    values: dict[str, float] = {}
    for metric in _coverage_metric_names(skill_name):
        if metric in metrics:
            value = metrics.get(metric, 0.0)
        elif metric == "domain_move_coverage":
            value = getattr(domain_expertise, "domain_move_coverage", 0.0)
        elif metric == "section_depth_score":
            value = getattr(depth, "section_depth_score", 0.0)
        elif metric == "task_outcome_with_skill_average":
            value = getattr(profile_result, "with_skill_average", 0.0)
        else:
            value = 0.0
        values[metric] = round(float(value or 0.0), 4)
    return values


def _compactness_values(metrics: dict[str, Any], skill_name: str) -> dict[str, float]:
    editorial = metrics.get("editorial")
    style = metrics.get("style")
    values: dict[str, float] = {}
    for metric in _compactness_metric_names(skill_name):
        if metric in metrics:
            value = metrics.get(metric, 0.0)
        elif metric == "redundancy_ratio":
            value = getattr(editorial, "redundancy_ratio", 0.0)
        elif metric == "shared_opening_phrase_ratio":
            value = getattr(style, "shared_opening_phrase_ratio", 0.0)
        else:
            value = 0.0
        values[metric] = round(float(value or 0.0), 4)
    return values


def _coverage_rank_key(skill_name: str, metrics: dict[str, Any]) -> tuple[float, ...]:
    force_values = _primary_force_values(skill_name, metrics.get("editorial_force"))
    coverage_values = _coverage_values(metrics, skill_name)
    return (
        *tuple(round(coverage_values.get(metric, 0.0), 4) for metric in _coverage_metric_names(skill_name)),
        *tuple(round(force_values.get(metric, 0.0), 4) for metric in _primary_force_metric_names(skill_name)),
        round(float(getattr(metrics.get("editorial_force"), "compression_without_loss", 0.0) or 0.0), 4),
        round(float(metrics.get("score", 0.0) or 0.0), 4),
    )


def _compressible_section_names(skill_name: str) -> set[str]:
    names = {"Overview", "Output Format", "Quality Checks", "Failure Patterns and Fixes"}
    if skill_name == "simulation-resource-loop-design":
        names.add("Analysis Blocks")
    return names


def _compression_plans(
    *,
    skill_name: str,
    strategy_profile: dict[str, str],
    program: SkillProgramIR,
) -> list[SectionCompressionPlan]:
    common_rules = [
        "merge repeated framing lines",
        "delete repeated generic setup lines",
        "prefer judgment sentences over explanation sentences",
        "keep at most one framing sentence before bullets",
    ]
    output_terms = list(program.output_schema.keys())[:8]
    decision_terms = [move.label for move in list(program.execution_spine or [])[:6]]
    failure_terms = [item.split(" -> ", 1)[0] for item in list(program.failure_repairs or [])[:6]]
    plans = [
        SectionCompressionPlan(
            section_name="Overview",
            max_sentence_budget=1,
            protected_terms=list(output_terms[:2] or decision_terms[:2]),
            forbidden_removals=list(decision_terms[:2]),
            compression_rules=common_rules + ["rewrite opening into a profile-specific one-liner"],
        ),
        SectionCompressionPlan(
            section_name="Output Format",
            max_sentence_budget=1,
            protected_terms=list(output_terms),
            forbidden_removals=list(output_terms),
            compression_rules=common_rules + ["keep field lines and good/weak guidance"],
        ),
        SectionCompressionPlan(
            section_name="Quality Checks",
            max_sentence_budget=1,
            protected_terms=list(decision_terms),
            forbidden_removals=list(decision_terms[:4]),
            compression_rules=common_rules + ["keep failure-trigger checks and stop conditions"],
        ),
        SectionCompressionPlan(
            section_name="Failure Patterns and Fixes",
            max_sentence_budget=1,
            protected_terms=list(failure_terms),
            forbidden_removals=list(failure_terms[:4]),
            compression_rules=common_rules + ["keep symptom/cause/correction structure intact"],
        ),
    ]
    if skill_name == "simulation-resource-loop-design":
        plans.append(
            SectionCompressionPlan(
                section_name="Analysis Blocks",
                max_sentence_budget=1,
                protected_terms=["Variable Web", "Pressure Relationships", "Main Feedback Loops", "Failure and Recovery"],
                forbidden_removals=["Variable Web", "Pressure Relationships"],
                compression_rules=common_rules + ["preserve map/tension/loop/recovery structure"],
            )
        )
    return plans


def _parse_markdown_sections(markdown: str) -> tuple[list[str], dict[str, list[str]]]:
    lines = markdown.splitlines()
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    current_name: str | None = None
    buffer: list[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            buffer.append(line)
            continue
        if line.startswith("## ") and not in_fence:
            if current_name is None:
                preamble = list(buffer)
            else:
                sections[current_name] = list(buffer)
            current_name = line[3:].strip()
            buffer = [line]
            continue
        buffer.append(line)
    if current_name is None:
        preamble = list(buffer)
    else:
        sections[current_name] = list(buffer)
    return preamble, sections


def _resolve_section_key(sections: dict[str, list[str]], target_name: str) -> str | None:
    if target_name in sections:
        return target_name
    if target_name == "Failure Patterns and Fixes":
        for key in sections:
            if key.lower().startswith("common pitfalls:"):
                return key
    return None


def _restore_markdown_sections(preamble: list[str], sections: dict[str, list[str]], order: list[str]) -> str:
    output: list[str] = list(preamble)
    if output and output[-1] != "":
        output.append("")
    for name in order:
        lines = list(sections.get(name, []))
        if not lines:
            continue
        if output and output[-1] != "":
            output.append("")
        output.extend(lines)
    return "\n".join(output).rstrip() + "\n"


def _sentence_like_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(("#", "-", "*", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "```", "---")):
        return False
    return True


def _compression_opening(skill_name: str, strategy_profile: dict[str, str]) -> str:
    opening = str(strategy_profile.get("opening_frame") or "").strip()
    if opening:
        return opening
    defaults = {
        "concept-to-mvp-pack": "Prove the smallest honest first playable, cut the rest, and package only what survives.",
        "decision-loop-stress-test": "Pressure-test the decision game until the break point and repair move are explicit.",
        "simulation-resource-loop-design": "Map the pressure web, keep the tradeoffs visible, and preserve recovery cost.",
    }
    return defaults.get(skill_name, "")


def _compress_section_lines(
    *,
    skill_name: str,
    section_name: str,
    lines: list[str],
    plan: SectionCompressionPlan,
    strategy_profile: dict[str, str],
) -> tuple[list[str], SectionCompressionResult]:
    if not lines:
        return lines, SectionCompressionResult(section_name=section_name)
    result = SectionCompressionResult(section_name=section_name)
    heading = lines[0]
    body_lines = list(lines[1:])
    compressed: list[str] = []
    seen_norm: set[str] = set()
    framing_count = 0
    generic_prefixes = (
        "use this skill to",
        "use this section to",
        "use these checks to",
        "use this step to",
        "lead with",
        "secondary emphasis:",
        "another agent should",
        "avoid generic",
    )
    opening_override = _compression_opening(skill_name, strategy_profile) if section_name == "Overview" else ""
    for raw_line in body_lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if compressed and compressed[-1] != "":
                compressed.append("")
            continue
        lowered = stripped.lower()
        protected = any(term.lower() in lowered for term in list(plan.protected_terms or []))
        forbidden = any(term.lower() in lowered for term in list(plan.forbidden_removals or []))
        if opening_override and _sentence_like_line(stripped):
            compressed.append(opening_override)
            result.opening_rewrite_applied = True
            opening_override = ""
            result.removed_redundant_lines += 1
            continue
        normalized = " ".join(lowered.split())
        if normalized in seen_norm and not protected and not forbidden:
            result.removed_redundant_lines += 1
            continue
        if any(lowered.startswith(prefix) for prefix in generic_prefixes) and not protected and not forbidden:
            result.filler_removed_count += 1
            continue
        if _sentence_like_line(stripped):
            framing_count += 1
            if framing_count > max(1, int(plan.max_sentence_budget or 1)) and not protected and not forbidden:
                result.filler_removed_count += 1
                continue
            if ":" not in stripped and not any(token in lowered for token in ("must", "cut", "fail", "keep", "output", "check", "watch")) and not protected:
                stripped = stripped.rstrip(".") + "."
        compressed.append(stripped if stripped == line else stripped)
        seen_norm.add(normalized)
    if section_name == "Quality Checks":
        prioritized: list[str] = []
        bullet_count = 0
        for item in compressed:
            stripped = item.strip()
            if not stripped:
                continue
            if not stripped.startswith("- "):
                prioritized.append(item)
                continue
            lowered = stripped.lower()
            is_priority = any(
                token in lowered
                for token in (
                    "gate:",
                    "reject",
                    "must",
                    "fail",
                    "pressure",
                    "scope",
                    "out-of-scope",
                    "solved",
                    "autopilot",
                    "recovery",
                    "tradeoff",
                    "build",
                    "playtest",
                    "reward",
                    "decision quality",
                    "numeric balancing",
                    "prototype first",
                    "consequence-free reset",
                )
            )
            if bullet_count < 10 and (is_priority or "check that" not in lowered):
                prioritized.append(item)
                bullet_count += 1
            else:
                result.filler_removed_count += 1
        compressed = prioritized
    elif section_name == "Failure Patterns and Fixes":
        pruned: list[str] = []
        heading_count = 0
        allow_block = True
        max_headings = 5 if skill_name != "simulation-resource-loop-design" else 6
        for item in compressed:
            stripped = item.strip()
            if stripped.startswith("### "):
                heading_count += 1
                allow_block = heading_count <= max_headings
                if not allow_block:
                    result.filler_removed_count += 1
                    continue
            if allow_block:
                pruned.append(item)
            elif stripped:
                result.filler_removed_count += 1
        compressed = pruned
    elif section_name == "Analysis Blocks":
        pruned_blocks: list[str] = []
        for item in compressed:
            stripped = item.strip()
            lowered = stripped.lower()
            if lowered.startswith("- use when:"):
                result.filler_removed_count += 1
                continue
            pruned_blocks.append(item)
        compressed = pruned_blocks
    while compressed and compressed[-1] == "":
        compressed.pop()
    preserved = True
    lowered_joined = "\n".join(item.lower() for item in compressed)
    for term in list(plan.protected_terms or []):
        if term and term.lower() not in lowered_joined:
            preserved = False
            break
    result.protected_terms_preserved = preserved
    final_lines = [heading]
    if compressed:
        final_lines.extend(compressed)
    return final_lines, result


def _compress_candidate_sections(
    *,
    skill_name: str,
    candidate: SkillRealizationCandidate,
    program: SkillProgramIR,
) -> SkillRealizationCandidate:
    preamble, sections = _parse_markdown_sections(candidate.rendered_markdown)
    plans = {
        item.section_name: item
        for item in _compression_plans(skill_name=skill_name, strategy_profile=dict(candidate.strategy_profile or {}), program=program)
        if item.section_name in _compressible_section_names(skill_name)
    }
    compression_results: list[SectionCompressionResult] = []
    for section_name, plan in plans.items():
        section_key = _resolve_section_key(sections, section_name)
        if section_key is None:
            continue
        compressed_lines, result = _compress_section_lines(
            skill_name=skill_name,
            section_name=section_name,
            lines=list(sections[section_key]),
            plan=plan,
            strategy_profile=dict(candidate.strategy_profile or {}),
        )
        sections[section_key] = compressed_lines
        compression_results.append(result)
    markdown = _restore_markdown_sections(preamble, sections, list(sections.keys()))
    profile = dict(candidate.strategy_profile or {})
    profile["compression_stage"] = "post"
    profile["source_candidate_id"] = candidate.candidate_id
    profile["compression_sections"] = ",".join(item.section_name for item in compression_results if item.removed_redundant_lines or item.filler_removed_count or item.opening_rewrite_applied)
    return candidate.model_copy(
        update={
            "candidate_id": f"{candidate.candidate_id}:compressed",
            "strategy_profile": profile,
            "rendered_markdown": markdown,
            "diagnostic_summary": list(candidate.diagnostic_summary or [])
            + [
                "compression_stage=post",
                f"compression_sections={profile.get('compression_sections', '') or 'none'}",
                f"compression_removed_lines={sum(item.removed_redundant_lines for item in compression_results)}",
                f"compression_removed_fillers={sum(item.filler_removed_count for item in compression_results)}",
            ],
        }
    )


def _candidate_separation_report(candidates: list[SkillRealizationCandidate]) -> tuple[str, float, list[dict[str, str]]]:
    pre_candidates = [
        item for item in candidates
        if str(dict(item.strategy_profile or {}).get("compression_stage") or "pre") != "post"
    ]
    source = pre_candidates or candidates
    matrix = [
        {
            "candidate_id": item.candidate_id,
            "strategy": item.realization_strategy,
            **{str(key): str(value) for key, value in dict(item.strategy_profile or {}).items()},
        }
        for item in source
    ]
    if len(matrix) < 2:
        return "fail", 0.0, matrix

    candidate_count = len(matrix)

    def _norm(key: str) -> float:
        values = {str(item.get(key, "") or "") for item in matrix}
        return round((max(0, len(values) - 1) / max(1, candidate_count - 1)), 4)

    opening = _norm("opening_frame")
    section_order = _norm("section_order")
    sentence_budget_profile = _norm("sentence_budget_profile")
    workflow_mode = _norm("workflow_mode")
    step_frame = _norm("step_frame")
    output_focus = _norm("output_focus")
    quality_tone = _norm("quality_tone")
    quality_mode = _norm("quality_mode")
    failure_style = _norm("failure_style")
    failure_mode = _norm("failure_mode")
    score = round(
        0.14 * opening
        + 0.18 * section_order
        + 0.12 * sentence_budget_profile
        + 0.16 * workflow_mode
        + 0.12 * step_frame
        + 0.10 * output_focus
        + 0.06 * quality_tone
        + 0.06 * quality_mode
        + 0.03 * failure_style
        + 0.03 * failure_mode,
        4,
    )
    strong_axes = sum(
        value >= 0.34
        for value in [
            section_order,
            sentence_budget_profile,
            workflow_mode,
            step_frame,
            output_focus,
            quality_mode,
            failure_mode,
        ]
    )
    status = (
        "pass"
        if score >= 0.78
        and strong_axes >= 4
        and section_order > 0.0
        and workflow_mode > 0.0
        and step_frame > 0.0
        else "fail"
    )
    return status, score, matrix


def _compare_to_dual_baselines(
    *,
    skill_name: str,
    winner_metrics: dict[str, Any],
    source_metrics: dict[str, Any] | None,
    bundle: ProfileBaselineBundle | None,
) -> MonotonicImprovementReport:
    if bundle is None:
        return MonotonicImprovementReport(
            skill_name=skill_name,
            best_balance_comparison_status="missing",
            best_coverage_comparison_status="missing",
            force_non_regression_status="pass",
            coverage_non_regression_status="pass",
            compactness_non_regression_status="pass",
            frontier_dominance_status="pass",
            compression_gain_status="neutral",
            promotion_status="promote",
            promotion_reason="no_dual_baseline_bundle",
            summary=["no dual-baseline bundle available"],
        )

    score_tol = float(dict(bundle.tolerance or {}).get("score_metric", 0.01) or 0.01)
    compactness_tol = float(dict(bundle.tolerance or {}).get("compactness_metric", 0.01) or 0.01)
    winner_force = _primary_force_values(skill_name, winner_metrics.get("editorial_force"))
    winner_coverage = _coverage_values(winner_metrics, skill_name)
    winner_compactness = _compactness_values(winner_metrics, skill_name)

    force_regressions = [
        f"{metric}:{winner_force.get(metric, 0.0):.4f}<{float(value) - score_tol:.4f}"
        for metric, value in dict(bundle.force_floor or {}).items()
        if winner_force.get(metric, 0.0) + score_tol < float(value)
    ]
    coverage_regressions = [
        f"{metric}:{winner_coverage.get(metric, 0.0):.4f}<{float(value) - score_tol:.4f}"
        for metric, value in dict(bundle.coverage_floor or {}).items()
        if winner_coverage.get(metric, 0.0) + score_tol < float(value)
    ]
    compactness_regressions = [
        f"{metric}:{winner_compactness.get(metric, 0.0):.4f}>{float(value) + compactness_tol:.4f}"
        for metric, value in dict(bundle.compactness_ceiling or {}).items()
        if winner_compactness.get(metric, 0.0) > float(value) + compactness_tol
    ]

    def _baseline_force_win(snapshot_name: str) -> int:
        snapshot = getattr(bundle, snapshot_name)
        return sum(
            1
            for metric, baseline in dict(snapshot.primary_force_metrics or {}).items()
            if winner_force.get(metric, 0.0) > float(baseline) + 0.015
        )

    best_balance_force_win_count = _baseline_force_win("best_balance_snapshot")
    best_coverage_force_win_count = _baseline_force_win("best_coverage_snapshot")
    primary_force_win_count = max(best_balance_force_win_count, best_coverage_force_win_count)

    best_balance_comparison_status = "beaten" if best_balance_force_win_count >= 1 else "not_beaten"
    best_coverage_comparison_status = "beaten" if best_coverage_force_win_count >= 1 else "not_beaten"
    force_non_regression_status = "fail" if force_regressions else "pass"
    coverage_non_regression_status = "fail" if coverage_regressions else "pass"
    compactness_non_regression_status = "fail" if compactness_regressions else "pass"
    frontier_dominance_status = (
        "pass"
        if (
            force_non_regression_status == "pass"
            and coverage_non_regression_status == "pass"
            and compactness_non_regression_status == "pass"
        )
        else "fail"
    )

    compactness_gains: list[str] = []
    if source_metrics is not None:
        source_compactness = _compactness_values(source_metrics, skill_name)
        source_compression = round(float(source_metrics.get("compression_without_loss", 0.0) or 0.0), 4)
        winner_compression = round(float(winner_metrics.get("compression_without_loss", 0.0) or 0.0), 4)
        if source_compactness.get("redundancy_ratio", 1.0) - winner_compactness.get("redundancy_ratio", 1.0) >= 0.02:
            compactness_gains.append("redundancy_ratio")
        if source_compactness.get("shared_opening_phrase_ratio", 1.0) - winner_compactness.get("shared_opening_phrase_ratio", 1.0) >= 0.05:
            compactness_gains.append("shared_opening_phrase_ratio")
        if source_compactness.get("cross_case_similarity", 1.0) - winner_compactness.get("cross_case_similarity", 1.0) >= 0.02:
            compactness_gains.append("cross_case_similarity")
        if winner_compression - source_compression >= 0.03:
            compactness_gains.append("compression_without_loss")
    compression_gain_status = (
        "pass"
        if compactness_gains
        else ("neutral" if source_metrics is None else "fail")
    )

    protected_regressions = force_regressions + coverage_regressions + compactness_regressions
    if force_non_regression_status != "pass":
        promotion_status = "hold"
        promotion_reason = "hold_due_to_force_regression"
    elif coverage_non_regression_status != "pass":
        promotion_status = "hold"
        promotion_reason = "hold_due_to_coverage_regression"
    elif compactness_non_regression_status != "pass":
        promotion_status = "hold"
        promotion_reason = "hold_due_to_compactness_regression"
    elif primary_force_win_count >= 1:
        promotion_status = "promote"
        promotion_reason = "breakthrough"
    elif compression_gain_status == "pass":
        promotion_status = "promote"
        promotion_reason = "breakthrough"
    else:
        promotion_status = "hold"
        promotion_reason = "hold_due_to_no_primary_win"

    return MonotonicImprovementReport(
        skill_name=skill_name,
        best_balance_comparison_status=best_balance_comparison_status,
        best_coverage_comparison_status=best_coverage_comparison_status,
        force_non_regression_status=force_non_regression_status,
        coverage_non_regression_status=coverage_non_regression_status,
        compactness_non_regression_status=compactness_non_regression_status,
        frontier_dominance_status=frontier_dominance_status,
        compression_gain_status=compression_gain_status,
        promotion_status=promotion_status,
        promotion_reason=promotion_reason,
        primary_force_win_count=primary_force_win_count,
        protected_regressions=protected_regressions,
        compactness_gains=compactness_gains,
        summary=[
            f"best_balance_comparison_status={best_balance_comparison_status}",
            f"best_coverage_comparison_status={best_coverage_comparison_status}",
            f"force_non_regression_status={force_non_regression_status}",
            f"coverage_non_regression_status={coverage_non_regression_status}",
            f"compactness_non_regression_status={compactness_non_regression_status}",
            f"compression_gain_status={compression_gain_status}",
            f"primary_force_win_count={primary_force_win_count}",
            f"promotion_reason={promotion_reason}",
        ],
    )


def choose_skill_realization_candidate(
    *,
    skill_name: str,
    task: str,
    candidates: list[SkillRealizationCandidate],
) -> tuple[SkillRealizationCandidate | None, PairwiseEditorialReport | None, SkillPromotionDecision, MonotonicImprovementReport | None]:
    if not candidates:
        return None, None, SkillPromotionDecision(skill_name=skill_name, promotion_status="hold", reason="no_candidates"), None
    scored = [
        (
            candidate,
            _candidate_editorial_metrics(
                skill_name=skill_name,
                task=task,
                markdown=candidate.rendered_markdown,
                realization_candidate_count=len(candidates),
            ),
        )
        for candidate in candidates
    ]
    scored.sort(key=lambda item: _candidate_rank_key(skill_name, item[1]), reverse=True)
    winner, winner_metrics = scored[0]
    loser, loser_metrics = scored[1] if len(scored) > 1 else scored[0]
    scored_by_id = {item.candidate_id: metrics for item, metrics in scored}
    candidate_separation_status, candidate_separation_score, candidate_strategy_matrix = _candidate_separation_report(candidates)
    current_best_metrics = _current_best_editorial_metrics(skill_name, task)
    source_candidate_id = str(dict(winner.strategy_profile or {}).get("source_candidate_id") or "")
    source_metrics = scored_by_id.get(source_candidate_id)
    monotonic_report = _compare_to_dual_baselines(
        skill_name=skill_name,
        winner_metrics=winner_metrics,
        source_metrics=source_metrics,
        bundle=_dual_baseline_bundle(skill_name),
    )
    force_non_regression_status = monotonic_report.force_non_regression_status
    current_best_comparison_status = (
        "beaten"
        if monotonic_report.promotion_status == "promote"
        else "not_beaten"
    )
    primary_force_win_count = int(monotonic_report.primary_force_win_count or 0)
    hold_reason = monotonic_report.promotion_reason if monotonic_report.promotion_status != "promote" else ""
    pairwise = PairwiseEditorialReport(
        skill_name=skill_name,
        winner=winner.candidate_id,
        loser=loser.candidate_id,
        decision_pressure_delta=round(
            float(getattr(winner_metrics["editorial_force"], "decision_pressure_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "decision_pressure_score", 0.0) or 0.0),
            4,
        ),
        cut_sharpness_delta=round(
            float(getattr(winner_metrics["editorial_force"], "cut_sharpness_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "cut_sharpness_score", 0.0) or 0.0),
            4,
        ),
        failure_repair_clarity_delta=round(
            float(getattr(winner_metrics["editorial_force"], "failure_repair_force", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "failure_repair_force", 0.0) or 0.0),
            4,
        ),
        output_executability_delta=round(
            float(getattr(winner_metrics["editorial_force"], "output_executability_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["editorial_force"], "output_executability_score", 0.0) or 0.0),
            4,
        ),
        redundancy_delta=round(
            float(getattr(loser_metrics["editorial"], "redundancy_ratio", 0.0) or 0.0)
            - float(getattr(winner_metrics["editorial"], "redundancy_ratio", 0.0) or 0.0),
            4,
        ),
        style_convergence_delta=round(
            float(getattr(winner_metrics["style"], "domain_rhythm_score", 0.0) or 0.0)
            - float(getattr(loser_metrics["style"], "domain_rhythm_score", 0.0) or 0.0),
            4,
        ),
        candidate_separation_status=candidate_separation_status,
        candidate_separation_score=candidate_separation_score,
        force_non_regression_status=force_non_regression_status,
        current_best_comparison_status=current_best_comparison_status,
        primary_force_win_count=primary_force_win_count,
        promotion_hold_reason=hold_reason,
        candidate_strategy_matrix=candidate_strategy_matrix,
        summary=[
            f"winner={winner.candidate_id}",
            f"loser={loser.candidate_id}",
            f"candidate_separation_status={candidate_separation_status}",
            f"force_non_regression_status={force_non_regression_status}",
            f"current_best_comparison_status={current_best_comparison_status}",
            f"primary_force_win_count={primary_force_win_count}",
            f"score_delta={winner_metrics['score'] - loser_metrics['score']:.4f}",
        ],
    )
    if current_best_metrics is None:
        promote_without_best = candidate_separation_status == "pass"
        monotonic_if_missing = monotonic_report.model_copy(
            update={
                "promotion_status": "promote" if promote_without_best else "hold",
                "promotion_reason": "no_current_best_snapshot" if promote_without_best else "hold_due_to_candidate_separation",
            }
        )
        return winner, pairwise, SkillPromotionDecision(
            skill_name=skill_name,
            candidate_id=winner.candidate_id,
            current_best_id="missing",
            promotion_status="promote" if promote_without_best else "hold",
            reason="no_current_best_snapshot" if promote_without_best else "hold_due_to_candidate_separation",
            best_balance_comparison_status=monotonic_if_missing.best_balance_comparison_status,
            best_coverage_comparison_status=monotonic_if_missing.best_coverage_comparison_status,
            candidate_separation_status=candidate_separation_status,
            force_non_regression_status="pass",
            coverage_non_regression_status=monotonic_if_missing.coverage_non_regression_status,
            compactness_non_regression_status=monotonic_if_missing.compactness_non_regression_status,
            frontier_dominance_status=monotonic_if_missing.frontier_dominance_status,
            compression_gain_status=monotonic_if_missing.compression_gain_status,
            current_best_comparison_status="missing_current_best",
            primary_force_win_count=0,
            promotion_hold_reason="" if promote_without_best else "hold_due_to_candidate_separation",
            stable_but_no_breakthrough=not promote_without_best,
            summary=[
                f"promotion_status={'promote' if promote_without_best else 'hold'}",
                f"reason={'no_current_best_snapshot' if promote_without_best else 'hold_due_to_candidate_separation'}",
                f"candidate_separation_status={candidate_separation_status}",
            ],
        ), monotonic_if_missing
    winner_score = float(winner_metrics["score"])
    current_score = float(current_best_metrics["score"])
    promote = (
        candidate_separation_status == "pass"
        and monotonic_report.frontier_dominance_status == "pass"
        and monotonic_report.promotion_status == "promote"
    )
    stable_but_no_breakthrough = (
        candidate_separation_status == "pass"
        and monotonic_report.frontier_dominance_status == "pass"
        and monotonic_report.promotion_status != "promote"
        and monotonic_report.promotion_reason == "hold_due_to_no_primary_win"
    )
    promotion_reason = (
        "breakthrough"
        if promote
        else (
            "hold_due_to_candidate_separation"
            if candidate_separation_status != "pass"
            else (
                "stable_but_no_breakthrough"
                if stable_but_no_breakthrough
                else monotonic_report.promotion_reason
            )
        )
    )
    return winner, pairwise, SkillPromotionDecision(
        skill_name=skill_name,
        candidate_id=winner.candidate_id,
        current_best_id=f"{skill_name}:current_best",
        promotion_status="promote" if promote else "hold",
        reason=promotion_reason,
        best_balance_comparison_status=monotonic_report.best_balance_comparison_status,
        best_coverage_comparison_status=monotonic_report.best_coverage_comparison_status,
        candidate_separation_status=candidate_separation_status,
        force_non_regression_status=force_non_regression_status,
        coverage_non_regression_status=monotonic_report.coverage_non_regression_status,
        compactness_non_regression_status=monotonic_report.compactness_non_regression_status,
        frontier_dominance_status=monotonic_report.frontier_dominance_status,
        compression_gain_status=monotonic_report.compression_gain_status,
        current_best_comparison_status=current_best_comparison_status,
        primary_force_win_count=primary_force_win_count,
        promotion_hold_reason="" if promote else promotion_reason,
        stable_but_no_breakthrough=stable_but_no_breakthrough,
        summary=[
            f"winner_score={winner_score:.4f}",
            f"current_best_score={current_score:.4f}",
            f"candidate_separation_status={candidate_separation_status}",
            f"force_non_regression_status={force_non_regression_status}",
            f"coverage_non_regression_status={monotonic_report.coverage_non_regression_status}",
            f"compactness_non_regression_status={monotonic_report.compactness_non_regression_status}",
            f"frontier_dominance_status={monotonic_report.frontier_dominance_status}",
            f"compression_gain_status={monotonic_report.compression_gain_status}",
            f"current_best_comparison_status={current_best_comparison_status}",
            f"primary_force_win_count={primary_force_win_count}",
            f"promotion_status={'promote' if promote else 'hold'}",
        ],
    ), monotonic_report


def render_skill_program_markdown(
    *,
    skill_name: str,
    description: str,
    task: str,
    references: list[str],
    scripts: list[str],
    candidate_dna: ExpertSkillDNA | None = None,
) -> str | None:
    _, _, candidates = build_skill_realization_candidates(
        skill_name=skill_name,
        description=description,
        task=task,
        references=references,
        scripts=scripts,
        candidate_dna=candidate_dna,
    )
    winner, _, _, _ = choose_skill_realization_candidate(
        skill_name=skill_name,
        task=task,
        candidates=candidates,
    )
    if winner is None:
        return None
    return winner.rendered_markdown


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
    if corpus is None or not list(getattr(corpus, "section_corpus", []) or []):
        backlog_categories.append("missing_section_corpus")
    if corpus is None or not corpus.task_probes:
        backlog_categories.append("missing_probe_outputs")
    if not dna_candidate.stable_move_sequence:
        backlog_categories.append("unstable_move_sequence")
        backlog_categories.append("unstable_program_shape")
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


def build_expert_evidence_gap_report(candidate: SkillProgramAuthoringCandidate) -> ExpertEvidenceGapReport:
    backlog = set(candidate.backlog_categories or [])
    status = "fail" if backlog else "pass"
    return ExpertEvidenceGapReport(
        skill_name=candidate.skill_name,
        status=status,
        missing_expert_golden="missing_expert_golden" in backlog,
        missing_section_corpus="missing_section_corpus" in backlog,
        missing_probe_outputs="missing_probe_outputs" in backlog,
        unstable_move_sequence="unstable_move_sequence" in backlog,
        unstable_program_shape="unstable_program_shape" in backlog or "unstable_move_sequence" in backlog,
        generic_realization_candidate="generic_realization_candidate" in backlog,
        backlog_categories=sorted(backlog),
        summary=[
            f"expert_evidence_gap_status={status}",
            f"backlog_categories={','.join(sorted(backlog)) or 'none'}",
        ],
    )


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
