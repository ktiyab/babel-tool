"""
Command Succession — Data-driven next-step guidance

Centralizes workflow knowledge (single source of truth):
- Main loop: why -> capture -> review -> link -> [IMPLEMENT]
- Validation: endorse + evidence-decision -> validation
- Challenge: challenge -> evidence -> resolve -> tensions
- Ambiguity: question -> resolve-question -> questions

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
            NextStep("link", "babel link <id>", condition="found_unlinked",
                    why="Connect isolated knowledge"),
        ]
    ),

    "capture": Succession(
        default=NextStep("review", "babel review --list",
                        why="See queued proposals"),
        alternatives=[
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
            NextStep("validation", "babel validation", condition="has_decisions",
                    why="See which decisions need endorsement"),
            NextStep("link", "babel link --all", condition="many_unlinked",
                    why="Bulk link to active purpose"),
        ]
    ),

    "link": Succession(
        default=NextStep(None, "Ready to implement",
                        why="Knowledge connected"),
        alternatives=[
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
            NextStep("review", "babel review --list", condition="has_pending",
                    why="See queued proposals"),
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
    ),

    "map": Succession(
        default=NextStep("why", "babel why \"topic\"",
                        why="Query captured knowledge"),
    ),

    # -------------------------------------------------------------------------
    # SYNC COMMANDS: sync, process-queue, share
    # -------------------------------------------------------------------------
    "sync": Succession(
        default=NextStep("status", "babel status",
                        why="Check sync result"),
    ),

    "process-queue": Succession(
        default=NextStep("review", "babel review",
                        why="Review extracted proposals"),
    ),

    "share": Succession(
        default=NextStep("sync", "babel sync",
                        why="Sync after sharing"),
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
    """Format NextStep as display hint."""
    if not step.command:
        # Terminal state
        return f"-> {step.label}" + (f"  ({step.why})" if step.why else "")

    hint = f"-> Next: {step.label}"
    if step.why:
        hint += f"  ({step.why})"
    return hint


def get_workflow_summary() -> str:
    """
    Get overview of command workflows for documentation.

    Returns:
        Formatted workflow summary
    """
    return """Command Workflows:

  MAIN LOOP:     why -> capture -> review -> link -> [IMPLEMENT]
  VALIDATION:    endorse + evidence-decision -> validation
  CHALLENGE:     challenge -> evidence -> resolve -> tensions
  AMBIGUITY:     question -> resolve-question -> questions
  HEALTH:        status <-> coherence
"""