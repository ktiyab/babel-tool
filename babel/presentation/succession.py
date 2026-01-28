"""
Command Succession — Data-driven next-step guidance

Centralizes workflow knowledge (single source of truth):
- Main loop: why -> capture [-> spec] -> review -> link -> [IMPLEMENT]
- Validation: endorse + evidence-decision -> validation
- Challenge: challenge -> evidence -> resolve -> tensions
- Ambiguity: question -> resolve-question -> questions
- Git-Babel: gaps -> suggest-links -> link --to-commit (P7/P8)
- Lifecycle: deprecate -> capture (replacement)
- Discovery: list -> why | link (orphans)
- Preference: memo -> status
- Maintenance: sync -> coherence -> tensions -> [address issues]
- Task (new): orient -> why -> capture -> spec -> [IMPLEMENT] -> coherence -> capture COMPLETE -> share
- Task (cont): orient -> review -> history -> why "TASK" -> [RESUME]
- Semantic bridge: map --index -> why -> gather --symbol -> [IMPLEMENT] -> link --to-commit (WHY↔WHAT)
- Context gather: gather -> why | capture (parallel I/O for token efficiency)

THE SEMANTIC BRIDGE:
  Meaning flows in circles. `map --index` enables bidirectional discovery:
  - why "topic" → surfaces decisions AND code/doc locations
  - gather --symbol → loads specific code or documentation sections
  - link --to-commit → auto-links decisions to touched symbols

  Hints suggest `map --index` when:
  - init in existing project (has code to index)
  - why returns no code symbols (index would enrich results)
  - gather --symbol fails (no index exists)
  - link --to-commit has no symbols (index would enable auto-linking)
  - status shows no symbol index (setup opportunity)

Each command knows its successors + conditions for context-aware hints.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class NextStep:
    """Single next-step hint with optional condition."""
    command: Optional[str]    # e.g., "capture" (None = terminal)
    label: str                # e.g., "Capture decision"
    condition: str = None     # When to show (None = always)
    why: str = None           # Brief rationale


@dataclass
class Succession:
    """Succession rules for a command."""
    default: NextStep
    alternatives: List[NextStep] = field(default_factory=list)


# =============================================================================
# MANUAL MAPPING (commands that don't match their manual filename)
# =============================================================================

MANUAL_MAP: Dict[str, str] = {
    # Validation flow → validation.md
    "endorse": "validation",
    "evidence-decision": "evidence-decision",
    # Challenge flow → challenge.md
    "evidence": "challenge",
    "resolve": "challenge",
    # Question flow → question.md
    "resolve-question": "question",
}


def _get_manual_file(command: str) -> str:
    """Get manual filename for a command."""
    base = MANUAL_MAP.get(command, command)
    return f".babel/manual/{base}.md"


# =============================================================================
# CORE SUCCESSION DATA (Single Source of Truth)
# =============================================================================

RULES: Dict[str, Succession] = {
    # -------------------------------------------------------------------------
    # MAIN LOOP: why -> capture -> review -> link -> [IMPLEMENT]
    # -------------------------------------------------------------------------
    "why": Succession(
        default=NextStep("capture", "babel capture \"...\" --batch",
                        why="Propose before implement (HC2)"),
        alternatives=[
            NextStep("gather", "babel gather --symbol <name>", condition="found_symbols",
                    why="Load specific code or documentation section, not entire file"),
            NextStep("map", "babel map --index src/ .babel/manual/", condition="no_symbols",
                    why="No code/doc symbols found - index to enrich results (semantic bridge)"),
            NextStep("link", "babel link <id>", condition="found_unlinked",
                    why="Connect isolated knowledge"),
        ]
    ),

    "capture": Succession(
        default=NextStep("review", "babel review --list",
                        why="See queued proposals"),
        alternatives=[
            NextStep("capture", "babel capture --spec <id> \"...\" --batch",
                    condition="has_accepted_need",
                    why="Add implementation specification"),
            NextStep("review", "babel review --synthesize", condition="many_proposals",
                    why="Group proposals into themes"),
            NextStep("why", "babel why \"topic\"", condition="uncertain",
                    why="Check existing knowledge first"),
        ]
    ),

    "review": Succession(
        default=NextStep("link", "babel link --list",
                        why="See unlinked artifacts"),
        alternatives=[
            NextStep("history", "babel history -n 30", condition="task_workflow",
                    why="Check task progress after review"),
            NextStep("link", "babel link <artifact_id>", condition="just_accepted_with_unlinked",
                    why="Link accepted artifacts before validation (P7)"),
            NextStep("link", "babel link --all", condition="many_unlinked",
                    why="Bulk link to active purpose"),
            NextStep("validation", "babel validation", condition="has_decisions",
                    why="See which decisions need endorsement"),
        ]
    ),

    "link": Succession(
        default=NextStep(None, "Ready to implement",
                        why="Knowledge connected"),
        alternatives=[
            NextStep("link", "babel link <id> --to-commit HEAD",
                    condition="just_implemented",
                    why="Connect decision to commit + auto-link symbols (semantic bridge)"),
            NextStep("map", "babel map --index src/",
                    condition="commit_no_symbols",
                    why="No symbols auto-linked - index codebase to complete semantic bridge"),
            NextStep("link", "babel link --list", condition="has_unlinked",
                    why="More artifacts to link"),
            NextStep("validation", "babel validation", condition="has_decisions",
                    why="Validate linked decisions"),
        ]
    ),

    # -------------------------------------------------------------------------
    # VALIDATION FLOW: endorse + evidence-decision -> validation
    # -------------------------------------------------------------------------
    "endorse": Succession(
        default=NextStep("evidence-decision", "babel evidence-decision <id> \"...\"",
                        why="Validation needs both consensus + evidence"),
        alternatives=[
            NextStep("validation", "babel validation", condition="has_evidence",
                    why="Check validation status"),
        ]
    ),

    "evidence-decision": Succession(
        default=NextStep("validation", "babel validation",
                        why="Verify validation complete"),
    ),

    "validation": Succession(
        default=NextStep("status", "babel status",
                        why="Check overall project health"),
    ),

    # -------------------------------------------------------------------------
    # CHALLENGE FLOW: challenge -> evidence -> resolve -> tensions
    # -------------------------------------------------------------------------
    "challenge": Succession(
        default=NextStep("evidence", "babel evidence <id> \"...\"",
                        why="Support challenge with facts"),
    ),

    "evidence": Succession(
        default=NextStep("resolve", "babel resolve <id>",
                        why="Resolve with evidence"),
    ),

    "resolve": Succession(
        default=NextStep("tensions", "babel tensions",
                        why="Monitor open conflicts"),
        alternatives=[
            NextStep("link", "babel link <new_id> <old_id>",
                    condition="outcome_revised",
                    why="Create evolves_from link (P8)"),
        ]
    ),

    "tensions": Succession(
        default=NextStep("challenge", "babel challenge <id> \"...\"",
                        condition="has_tensions",
                        why="Address open tensions"),
        alternatives=[
            NextStep("status", "babel status", condition="no_tensions",
                    why="All tensions resolved"),
        ]
    ),

    # -------------------------------------------------------------------------
    # AMBIGUITY FLOW: question -> resolve-question -> questions
    # -------------------------------------------------------------------------
    "question": Succession(
        default=NextStep("questions", "babel questions",
                        why="Track acknowledged unknowns"),
    ),

    "resolve-question": Succession(
        default=NextStep("questions", "babel questions",
                        why="Monitor remaining unknowns"),
    ),

    "questions": Succession(
        default=NextStep("resolve-question", "babel resolve-question <id> \"...\"",
                        condition="has_questions",
                        why="Resolve when answer found"),
        alternatives=[
            NextStep("status", "babel status", condition="no_questions",
                    why="All questions resolved"),
        ]
    ),

    # -------------------------------------------------------------------------
    # HEALTH COMMANDS: status, coherence, check
    # -------------------------------------------------------------------------
    "status": Succession(
        default=NextStep("coherence", "babel coherence",
                        condition="not_checked",
                        why="Ensure alignment"),
        alternatives=[
            NextStep("process-queue", "babel process-queue --batch",
                    condition="has_queued_extractions",
                    why="Process queued extractions awaiting LLM analysis"),
            NextStep("review", "babel review --list", condition="has_pending",
                    why="See queued proposals"),
            NextStep("map", "babel map --index-clear <pattern> (indexed garbage) OR babel link --list (legitimate artifacts)",
                    condition="has_high_unlinked",
                    why="High unlinked count - identify cause first"),
            NextStep("map", "babel map --index src/",
                    condition="no_symbols_indexed",
                    why="No symbol index - enables why to surface code locations + gather --symbol"),
            NextStep("link", "babel link --list", condition="has_unlinked",
                    why="See unlinked artifacts"),
            NextStep("validation", "babel validation", condition="has_partial_validation",
                    why="See decisions needing validation"),
            NextStep("tensions", "babel tensions", condition="has_tensions",
                    why="Address open tensions"),
            NextStep("questions", "babel questions", condition="has_questions",
                    why="Review open questions"),
            NextStep("why", "babel why \"topic\"", condition="healthy",
                    why="Explore existing knowledge"),
        ]
    ),

    "coherence": Succession(
        default=NextStep("status", "babel status",
                        why="Overview after alignment check"),
        alternatives=[
            NextStep("capture", "babel capture \"TASK X.Y COMPLETE: ...\" --batch",
                    condition="task_implemented",
                    why="Capture task completion"),
            NextStep("capture", "babel capture \"decision made during implementation\" --batch",
                    condition="implementation_verified",
                    why="Capture decisions before context loss"),
            NextStep("challenge", "babel challenge <id> \"...\"",
                    condition="has_drift",
                    why="Address detected misalignment (P4)"),
            NextStep("link", "babel link <id>", condition="has_orphans",
                    why="Connect unlinked artifacts"),
        ]
    ),

    "check": Succession(
        default=NextStep("status", "babel status",
                        why="Review overall state"),
    ),

    # -------------------------------------------------------------------------
    # FOUNDATION COMMANDS: init, config, hooks
    # -------------------------------------------------------------------------
    "init": Succession(
        default=NextStep("capture", "babel capture \"...\" --batch",
                        why="Start capturing decisions"),
        alternatives=[
            NextStep("map", "babel map --index src/",
                    condition="existing_project",
                    why="Index existing code for semantic discovery (enables why + gather --symbol)"),
            NextStep("status", "babel status", condition="fresh_project",
                    why="Check initial state"),
        ]
    ),

    "config": Succession(
        default=NextStep("status", "babel status",
                        why="Verify configuration"),
    ),

    "hooks": Succession(
        default=NextStep("status", "babel status",
                        why="Verify hooks installed"),
    ),

    # -------------------------------------------------------------------------
    # KNOWLEDGE COMMANDS: scan, history, map
    # -------------------------------------------------------------------------
    "scan": Succession(
        default=NextStep("capture", "babel capture \"...\" --batch",
                        why="Capture findings"),
    ),

    "history": Succession(
        default=NextStep("why", "babel why \"topic\"",
                        why="Explore related decisions"),
        alternatives=[
            NextStep("review", "babel review --list", condition="found_tasks",
                    why="Check pending before continuing"),
            NextStep("why", "babel why \"TASK X.Y topic\"", condition="found_incomplete",
                    why="Get context for next task"),
            NextStep("list", "babel list constraints --filter depends",
                    condition="has_dependencies",
                    why="Check task dependencies"),
        ]
    ),

    "map": Succession(
        default=NextStep("why", "babel why \"topic\"",
                        why="Query captured knowledge - now includes code/doc locations"),
        alternatives=[
            NextStep("map", "babel map --query <name>", condition="indexed",
                    why="Index built - find symbol by name (code: class/function, docs: section)"),
            NextStep("gather", "babel gather --symbol <name>", condition="query",
                    why="Found symbol - load code or documentation without reading entire file"),
            NextStep("map", "babel map --index-incremental", condition="needs_refresh",
                    why="Files changed since last index - update incrementally"),
        ]
    ),

    "gather": Succession(
        default=NextStep("why", "babel why \"topic\"",
                        why="Context loaded - query babel for related decisions"),
        alternatives=[
            NextStep("capture", "babel capture \"...\" --batch", condition="found_relevant",
                    why="Found something important? Capture before context loss"),
            NextStep("gather", "babel gather --symbol <name>", condition="needs_more",
                    why="Need more code or docs? Add symbols to load in parallel"),
            NextStep("map", "babel map --index src/ .babel/manual/", condition="no_index",
                    why="No symbol index - build one to enable --symbol loading (code + docs)"),
        ]
    ),

    # -------------------------------------------------------------------------
    # SYNC COMMANDS: sync, process-queue, share
    # -------------------------------------------------------------------------
    "sync": Succession(
        default=NextStep("coherence", "babel coherence",
                        why="Check for drift after team sync"),
        alternatives=[
            NextStep("status", "babel status", condition="no_changes",
                    why="No team changes to check"),
            NextStep("tensions", "babel tensions", condition="known_conflicts",
                    why="Address known conflicts"),
        ]
    ),

    "process-queue": Succession(
        default=NextStep("review", "babel review",
                        why="Review extracted proposals"),
    ),

    "share": Succession(
        default=NextStep("sync", "babel sync",
                        why="Sync after sharing"),
        alternatives=[
            NextStep("history", "babel history -n 10", condition="task_complete",
                    why="Check for next task"),
            NextStep("status", "babel status", condition="milestone_reached",
                    why="Review overall progress"),
        ]
    ),

    # -------------------------------------------------------------------------
    # LIFECYCLE COMMANDS: deprecate, gaps, suggest-links
    # -------------------------------------------------------------------------
    "deprecate": Succession(
        default=NextStep("capture", "babel capture \"...\" --batch",
                        why="Capture replacement decision"),
        alternatives=[
            NextStep("status", "babel status", condition="no_replacement",
                    why="Verify deprecation recorded"),
        ]
    ),

    "gaps": Succession(
        default=NextStep("suggest-links", "babel suggest-links",
                        why="AI-assisted gap closure"),
        alternatives=[
            NextStep("link", "babel link <id> --to-commit <sha>",
                    condition="known_mapping",
                    why="Apply known decision-commit link"),
        ]
    ),

    "suggest-links": Succession(
        default=NextStep("link", "babel link <id> --to-commit <sha>",
                        why="Apply suggested links"),
        alternatives=[
            NextStep("gaps", "babel gaps", condition="more_gaps",
                    why="Check remaining gaps"),
            NextStep("status", "babel status --git", condition="all_linked",
                    why="Verify git-babel sync health"),
        ]
    ),

    # -------------------------------------------------------------------------
    # DISCOVERY COMMANDS: list, memo
    # -------------------------------------------------------------------------
    "list": Succession(
        default=NextStep("why", "babel why \"topic\"",
                        why="Query discovered artifacts"),
        alternatives=[
            NextStep("link", "babel link <id>", condition="found_orphans",
                    why="Connect orphan artifacts"),
            NextStep("list", "babel list --from <id>", condition="found_artifact",
                    why="Explore connections"),
        ]
    ),

    "memo": Succession(
        default=NextStep("status", "babel status",
                        why="Verify preference saved"),
        alternatives=[
            NextStep("memo", "babel memo --list", condition="checking_existing",
                    why="Review saved preferences"),
            NextStep("memo", "babel memo --candidates", condition="ai_operator",
                    why="Check AI-detected patterns"),
        ]
    ),
}


# =============================================================================
# HINT GENERATION
# =============================================================================

def get_hint(command: str, context: dict = None) -> Optional[str]:
    """
    Get contextual next-step hint for command.

    Args:
        command: Command that just ran (e.g., "why", "review")
        context: Result state flags (e.g., {"found": True, "has_pending": True})

    Returns:
        Formatted hint string or None
    """
    context = context or {}
    rules = RULES.get(command)

    if not rules:
        return None

    # Check alternatives first (condition-specific)
    for alt in rules.alternatives:
        if alt.condition and context.get(alt.condition):
            return _format_hint(alt)

    # Check default condition
    if rules.default.condition:
        if not context.get(rules.default.condition):
            # Default has condition that's not met - no hint
            return None

    # Fall back to default
    return _format_hint(rules.default)


def _format_hint(step: NextStep) -> str:
    """Format NextStep as display hint with manual reminder."""
    if not step.command:
        # Terminal state
        return f"-> {step.label}" + (f"  ({step.why})" if step.why else "")

    # Check for compound hint (multiple commands separated by " OR ")
    if " OR " in step.label:
        # Parse compound format: "babel cmd1 ... (reason1) OR babel cmd2 ... (reason2)"
        parts = step.label.split(" OR ")
        hint = f"-> Next: Choose based on cause:"
        if step.why:
            hint += f"  ({step.why})"
        for part in parts:
            part = part.strip()
            hint += f"\n   • {part}"
            # Extract command name from "babel <cmd> ..." pattern
            if part.startswith("babel "):
                cmd = part.split()[1]  # Get command name after "babel"
                hint += f"\n     Manual: {_get_manual_file(cmd)} [CMD-05]"
        return hint

    hint = f"-> Next: {step.label}"
    if step.why:
        hint += f"  ({step.why})"
    # Always append manual reminder - verbosity beats forgetting
    hint += f"\n   Manual: {_get_manual_file(step.command)} [CMD-05]"
    return hint


def get_workflow_summary() -> str:
    """
    Get overview of command workflows for documentation.

    Returns:
        Formatted workflow summary
    """
    return """Command Workflows:

  MAIN LOOP:     why -> capture [-> spec] -> review -> link -> [IMPLEMENT]
  VALIDATION:    endorse + evidence-decision -> validation
  CHALLENGE:     challenge -> evidence -> resolve -> tensions
  AMBIGUITY:     question -> resolve-question -> questions
  HEALTH:        status <-> coherence
  GIT-BABEL:     gaps -> suggest-links -> link --to-commit (P7/P8)
  LIFECYCLE:     deprecate -> capture (replacement)
  DISCOVERY:     list -> why | link (orphans)
  PREFERENCE:    memo -> status
  MAINTENANCE:   sync -> coherence -> tensions -> [address issues]
  TASK (NEW):    orient -> why -> capture -> spec -> [IMPLEMENT] -> coherence -> capture COMPLETE -> share
  TASK (CONT):   orient -> review -> history -> why "TASK" -> [RESUME]
  SEMANTIC BRIDGE: map --index -> why -> gather --symbol -> [IMPLEMENT] -> link --to-commit
                   (WHY↔WHAT: decisions connect to code + docs bidirectionally)
  CONTEXT:       gather -> why | capture (parallel I/O for token efficiency)
"""