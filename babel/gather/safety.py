"""
Safety — Babel command parallelization safety registry.

Prevents parallel execution of babel commands that could:
- Corrupt state (mutation commands)
- Overwhelm rate limits (LLM-heavy commands)
- Fail silently (interactive commands)

The registry is parameterized for easy updates as babel evolves.

Usage:
    from babel.gather.safety import check_bash_commands_safety, SafetyViolation

    try:
        check_bash_commands_safety(["babel list", "babel capture 'text'"])
    except SafetyViolation as e:
        print(e.message)  # Clear explanation of why rejected
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


class SafetyCategory(Enum):
    """Categories of babel command safety for parallelization."""
    SAFE = "safe"                    # Read-only, no LLM, can parallelize
    MUTATION = "mutation"            # Writes state, must be sequential
    LLM_HEAVY = "llm_heavy"          # Calls LLM, rate limiting concerns
    INTERACTIVE = "interactive"      # Requires user input, will fail in parallel


@dataclass(frozen=True)
class BabelCommandSafety:
    """Safety classification for a babel command."""
    command: str
    category: SafetyCategory
    safe_for_parallel: bool
    reason: str
    suggestion: str = ""

    def rejection_message(self) -> str:
        """Generate clear rejection message for LLM understanding."""
        lines = [
            f"REJECTED: 'babel {self.command}' cannot run in parallel gather",
            f"",
            f"Category: {self.category.value}",
            f"Reason: {self.reason}",
        ]
        if self.suggestion:
            lines.append(f"Suggestion: {self.suggestion}")
        return "\n".join(lines)


# =============================================================================
# Babel Command Safety Registry (Parameterized)
# =============================================================================

BABEL_COMMAND_SAFETY: Dict[str, BabelCommandSafety] = {
    # -------------------------------------------------------------------------
    # SAFE: Read-only query commands (no LLM, no state mutation)
    # -------------------------------------------------------------------------
    "list": BabelCommandSafety(
        command="list",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only graph query, no state mutation",
    ),
    "history": BabelCommandSafety(
        command="history",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only event query, no state mutation",
    ),
    "gaps": BabelCommandSafety(
        command="gaps",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only gap analysis, no state mutation",
    ),
    "tensions": BabelCommandSafety(
        command="tensions",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only tension query, no state mutation",
    ),
    "questions": BabelCommandSafety(
        command="questions",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only question query, no state mutation",
    ),
    "validation": BabelCommandSafety(
        command="validation",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only validation query, no state mutation",
    ),
    "check": BabelCommandSafety(
        command="check",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only integrity check, no state mutation",
    ),
    "status": BabelCommandSafety(
        command="status",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only status query, no state mutation",
    ),
    "principles": BabelCommandSafety(
        command="principles",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only principles display, no state mutation",
    ),
    "help": BabelCommandSafety(
        command="help",
        category=SafetyCategory.SAFE,
        safe_for_parallel=True,
        reason="Read-only help display, no state mutation",
    ),

    # -------------------------------------------------------------------------
    # MUTATION: Commands that write state (MUST be sequential)
    # -------------------------------------------------------------------------
    "capture": BabelCommandSafety(
        command="capture",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Writes to event store - parallel writes corrupt append-only log (HC1)",
        suggestion="Run 'babel capture' sequentially after gather completes",
    ),
    "review": BabelCommandSafety(
        command="review",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Mutates decision state - parallel mutations corrupt graph",
        suggestion="Run 'babel review' sequentially after gather completes",
    ),
    "link": BabelCommandSafety(
        command="link",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Creates graph edges - parallel edge creation corrupts relationships",
        suggestion="Run 'babel link' sequentially after gather completes",
    ),
    "deprecate": BabelCommandSafety(
        command="deprecate",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Mutates artifact state - parallel deprecation corrupts status",
        suggestion="Run 'babel deprecate' sequentially after gather completes",
    ),
    "challenge": BabelCommandSafety(
        command="challenge",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Creates tension entries - parallel creation corrupts tension tracking",
        suggestion="Run 'babel challenge' sequentially after gather completes",
    ),
    "resolve": BabelCommandSafety(
        command="resolve",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Resolves tensions - parallel resolution corrupts state",
        suggestion="Run 'babel resolve' sequentially after gather completes",
    ),
    "endorse": BabelCommandSafety(
        command="endorse",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Adds consensus - parallel endorsement corrupts validation state",
        suggestion="Run 'babel endorse' sequentially after gather completes",
    ),
    "evidence-decision": BabelCommandSafety(
        command="evidence-decision",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Adds evidence - parallel evidence addition corrupts validation",
        suggestion="Run 'babel evidence-decision' sequentially after gather completes",
    ),
    "evidence": BabelCommandSafety(
        command="evidence",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Adds evidence to challenges - parallel addition corrupts tracking",
        suggestion="Run 'babel evidence' sequentially after gather completes",
    ),
    "memo": BabelCommandSafety(
        command="memo",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Writes preferences - parallel writes corrupt memo store",
        suggestion="Run 'babel memo' sequentially after gather completes",
    ),
    "share": BabelCommandSafety(
        command="share",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Promotes artifacts to shared scope - parallel promotion corrupts state",
        suggestion="Run 'babel share' sequentially after gather completes",
    ),
    "sync": BabelCommandSafety(
        command="sync",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Merges event stores - parallel sync corrupts merge state",
        suggestion="Run 'babel sync' sequentially after gather completes",
    ),
    "question": BabelCommandSafety(
        command="question",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Creates question entries - parallel creation corrupts tracking",
        suggestion="Run 'babel question' sequentially after gather completes",
    ),
    "resolve-question": BabelCommandSafety(
        command="resolve-question",
        category=SafetyCategory.MUTATION,
        safe_for_parallel=False,
        reason="Resolves questions - parallel resolution corrupts state",
        suggestion="Run 'babel resolve-question' sequentially after gather completes",
    ),

    # -------------------------------------------------------------------------
    # LLM_HEAVY: Commands that call LLM (rate limiting concerns)
    # -------------------------------------------------------------------------
    "why": BabelCommandSafety(
        command="why",
        category=SafetyCategory.LLM_HEAVY,
        safe_for_parallel=False,
        reason="Calls LLM for synthesis - parallel calls overwhelm rate limits",
        suggestion="Run 'babel why' sequentially, or use gather for raw file/grep context first",
    ),
    "coherence": BabelCommandSafety(
        command="coherence",
        category=SafetyCategory.LLM_HEAVY,
        safe_for_parallel=False,
        reason="Calls LLM for analysis - has internal parallelization, don't nest",
        suggestion="Run 'babel coherence' sequentially after gather completes",
    ),
    "suggest-links": BabelCommandSafety(
        command="suggest-links",
        category=SafetyCategory.LLM_HEAVY,
        safe_for_parallel=False,
        reason="Calls LLM for suggestions - parallel calls overwhelm rate limits",
        suggestion="Run 'babel suggest-links' sequentially after gather completes",
    ),

    # -------------------------------------------------------------------------
    # INTERACTIVE: Commands requiring user input (will fail with EOF)
    # -------------------------------------------------------------------------
    "init": BabelCommandSafety(
        command="init",
        category=SafetyCategory.INTERACTIVE,
        safe_for_parallel=False,
        reason="Requires interactive input - will fail with EOF in parallel context",
        suggestion="Run 'babel init' interactively before using gather",
    ),
    "config": BabelCommandSafety(
        command="config",
        category=SafetyCategory.INTERACTIVE,
        safe_for_parallel=False,
        reason="May require interactive input for some operations",
        suggestion="Run 'babel config' interactively if needed",
    ),
}


# =============================================================================
# Safety Check Functions
# =============================================================================

class SafetyViolation(Exception):
    """
    Raised when a bash command contains unsafe babel commands.

    Provides clear message for LLM understanding of why rejected.
    """

    def __init__(self, violations: List[Tuple[str, BabelCommandSafety]]):
        self.violations = violations
        self.message = self._build_message()
        super().__init__(self.message)

    def _build_message(self) -> str:
        """Build comprehensive rejection message."""
        lines = [
            "=" * 60,
            "GATHER SAFETY VIOLATION - OPERATION REJECTED",
            "=" * 60,
            "",
            "The following babel command(s) cannot run in parallel gather:",
            "",
        ]

        for bash_cmd, safety in self.violations:
            lines.append(f"  Command: {bash_cmd}")
            lines.append(f"  Babel command: {safety.command}")
            lines.append(f"  Category: {safety.category.value}")
            lines.append(f"  Reason: {safety.reason}")
            if safety.suggestion:
                lines.append(f"  Suggestion: {safety.suggestion}")
            lines.append("")

        lines.extend([
            "-" * 60,
            "WHY THIS MATTERS:",
            "  Parallel execution of these commands could:",
            "  - Corrupt the append-only event store (HC1 violation)",
            "  - Create race conditions in graph mutations",
            "  - Overwhelm LLM rate limits",
            "  - Fail silently with EOF errors",
            "",
            "WHAT TO DO:",
            "  1. Remove unsafe babel commands from gather",
            "  2. Run gather for raw context (files, grep, bash, glob)",
            "  3. Run babel commands sequentially AFTER gather completes",
            "",
            "ALLOWED in gather --bash:",
            "  - Non-babel commands (git, ls, cat, etc.)",
            "  - babel list, babel history, babel gaps, babel tensions",
            "  - babel questions, babel validation, babel check, babel status",
            "=" * 60,
        ])

        return "\n".join(lines)


def extract_babel_command(bash_command: str) -> Optional[str]:
    """
    Extract babel subcommand from a bash command string.

    Args:
        bash_command: Full bash command (e.g., "babel capture 'text' --batch")

    Returns:
        Babel subcommand name if found, None otherwise

    Examples:
        "babel capture 'text'" -> "capture"
        "babel why 'topic'" -> "why"
        "git status" -> None
        "ls -la" -> None
    """
    # Pattern: babel <subcommand> [args...]
    # Handles: babel cmd, babel-tool cmd, python -m babel cmd
    patterns = [
        r"^\s*babel\s+([a-z][-a-z]*)",           # babel <cmd>
        r"^\s*babel-tool\s+([a-z][-a-z]*)",      # babel-tool <cmd>
        r"python[3]?\s+-m\s+babel\s+([a-z][-a-z]*)",  # python -m babel <cmd>
    ]

    for pattern in patterns:
        match = re.search(pattern, bash_command, re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return None


def check_bash_command_safety(bash_command: str) -> Optional[BabelCommandSafety]:
    """
    Check if a single bash command is safe for parallel gather.

    Args:
        bash_command: The bash command to check

    Returns:
        BabelCommandSafety if unsafe, None if safe
    """
    babel_cmd = extract_babel_command(bash_command)

    if babel_cmd is None:
        # Not a babel command, allow it
        return None

    safety = BABEL_COMMAND_SAFETY.get(babel_cmd)

    if safety is None:
        # Unknown babel command - be conservative, reject
        return BabelCommandSafety(
            command=babel_cmd,
            category=SafetyCategory.MUTATION,
            safe_for_parallel=False,
            reason=f"Unknown babel command '{babel_cmd}' - rejected for safety",
            suggestion="Check 'babel --help' for valid commands",
        )

    if not safety.safe_for_parallel:
        return safety

    return None


def check_bash_commands_safety(bash_commands: List[str]) -> None:
    """
    Check all bash commands for parallel gather safety.

    Args:
        bash_commands: List of bash commands to check

    Raises:
        SafetyViolation: If any command is unsafe for parallel execution
    """
    violations: List[Tuple[str, BabelCommandSafety]] = []

    for cmd in bash_commands:
        safety = check_bash_command_safety(cmd)
        if safety is not None:
            violations.append((cmd, safety))

    if violations:
        raise SafetyViolation(violations)


def get_safe_commands() -> List[str]:
    """Get list of babel commands safe for parallel gather."""
    return [
        cmd for cmd, safety in BABEL_COMMAND_SAFETY.items()
        if safety.safe_for_parallel
    ]


def get_unsafe_commands() -> Dict[str, List[str]]:
    """Get unsafe babel commands grouped by category."""
    result: Dict[str, List[str]] = {
        SafetyCategory.MUTATION.value: [],
        SafetyCategory.LLM_HEAVY.value: [],
        SafetyCategory.INTERACTIVE.value: [],
    }

    for cmd, safety in BABEL_COMMAND_SAFETY.items():
        if not safety.safe_for_parallel:
            result[safety.category.value].append(cmd)

    return result
