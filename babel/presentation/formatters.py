"""
Formatters — Data-to-string transformations for consistent output

Centralized formatting logic for all CLI output. This module handles:
- Text truncation with ellipsis
- Artifact summary extraction from nodes
- Event preview generation (dual-display: ID + WHAT)
- Status line formatting
- Semantic digest generation (via digest.py)

Design principles:
- HC6: Human-readable (always show WHAT, not just type)
- P6: Token efficiency (consistent truncation lengths)
- P7: Reasoning travels (digests preserve WHAT + WHY, not just characters)
- DRY: Single source of truth for formatting logic

Dependency direction: commands → presentation → core
Commands import formatters; formatters import core types.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

# Avoid circular imports - only import types for type checking
if TYPE_CHECKING:
    from ..core.graph import Node
    from ..core.events import Event

# Import symbols for format_artifact/format_status_line/format_trace
from .symbols import SymbolSet, symbol_for_type, symbol_for_status

# Import digest generation for semantic summaries
from .digest import generate_digest


# =============================================================================
# Display Truncation Constants
# =============================================================================
# Centralized limits for consistent output across all commands.
# Use truncate() helper to apply these with --full flag support.

SUMMARY_LENGTH = 120      # Default for summaries (captures complete thought)
DETAIL_LENGTH = 200       # For secondary details
ID_DISPLAY_LENGTH = 8     # ID prefixes (e.g., "abc12345")
DATE_DISPLAY_LENGTH = 10  # Date displays (e.g., "2025-01-15")


# =============================================================================
# Text Utilities
# =============================================================================

def truncate(text: str, length: int = SUMMARY_LENGTH, full: bool = False) -> str:
    """
    Truncate text with ellipsis, respecting full mode.

    Args:
        text: Text to truncate
        length: Max length (default: SUMMARY_LENGTH = 120)
        full: If True, never truncate (for --full flag)

    Returns:
        Truncated text with '...' if needed, or full text

    Examples:
        truncate("A very long text...", 50)  -> "A very long text..."[:47] + "..."
        truncate("Short", 50)                -> "Short" (no change)
        truncate("Any length", 50, full=True) -> "Any length" (no truncation)
    """
    if not text:
        return ""
    if full or len(text) <= length:
        return text
    if length <= 3:
        return text[:length]
    return text[:length - 3] + "..."


def generate_summary(
    text: str,
    length: int = None,
    content_type: str = "decision",
    max_keywords: int = 3,
    full: bool = False
) -> str:
    """
    Generate summary with hybrid mode: semantic digest or truncation.

    Behavior:
    - length=None (default): Uses semantic digest (first sentence + keywords)
    - length=<number>: Falls back to truncate() for backward compatibility
    - full=True: Returns complete text without modification

    This enables gradual migration from arbitrary truncation to semantic compression.

    Args:
        text: Full text content
        length: If specified, use truncate() instead of digest (backward compat)
        content_type: Type hint for digest (decision, constraint, question, etc.)
        max_keywords: Maximum keywords to append in digest mode (default: 3)
        full: If True, return full text without any processing

    Returns:
        - Semantic digest: "First sentence. [keyword1, keyword2]" (when length=None)
        - Truncated text: "First 50 chars..." (when length=50)
        - Full text (when full=True)

    Examples:
        # Semantic digest (default - recommended)
        generate_summary("Use Redis for caching. Reduces API calls to 50/min.")
        → "Use Redis for caching. [API, 50/min]"

        # Backward compatible truncation
        generate_summary("Use Redis for caching. Reduces API calls.", length=30)
        → "Use Redis for caching. Redu..."

        # Full text
        generate_summary("Any text here", full=True)
        → "Any text here"
    """
    if not text:
        return ""

    if full:
        return text

    # Backward compatibility: explicit length triggers truncation
    if length is not None:
        return truncate(text, length)

    # Default: semantic digest with length safety net
    try:
        digest = generate_digest(text, content_type=content_type, max_keywords=max_keywords)
        # Ensure output never exceeds SUMMARY_LENGTH (safety net for edge cases)
        if len(digest) > SUMMARY_LENGTH:
            return truncate(digest, SUMMARY_LENGTH)
        return digest
    except Exception:
        # Fallback to simple truncation if digest fails
        return truncate(text, SUMMARY_LENGTH)


def sanitize_control_chars(text: str) -> str:
    """
    Remove dangerous control characters from LLM output.

    Strips control chars that could:
    - Manipulate terminal display (ANSI escapes)
    - Cause parsing issues (null bytes, etc.)

    Preserves: newlines (\\n), tabs (\\t), carriage returns (\\r)

    Args:
        text: Raw text from LLM or untrusted source

    Returns:
        Sanitized text safe for storage and display
    """
    if not text:
        return text

    # Remove control chars except \t (0x09), \n (0x0A), \r (0x0D)
    result = []
    for char in text:
        code = ord(char)
        # Allow printable chars and safe whitespace
        if code >= 32 or code in (9, 10, 13):  # \t, \n, \r
            result.append(char)
        # Skip control chars 0x00-0x08, 0x0B-0x0C, 0x0E-0x1F

    return ''.join(result)


# =============================================================================
# Temporal Formatting (P12: Temporal Attribution)
# =============================================================================
# Time is ALWAYS shown. No parameters. No flags.
# Relative time for recent (<7 days), absolute date for older.
# This enforces P12: temporal context is structural, not optional.

def format_timestamp(iso_str: str) -> str:
    """
    Format ISO timestamp for display. Always returns time - no parameters.

    P12 Temporal Attribution: All surfaced information must include temporal markers.
    Time display is unconditional - not hidden behind flags.

    Args:
        iso_str: ISO 8601 timestamp string (e.g., "2026-01-14T23:48:02.331839+00:00")

    Returns:
        Formatted time string:
        - < 1 hour:  "23m ago"
        - < 24 hours: "5h ago"
        - < 7 days:  "3d ago"
        - >= 7 days: "Jan 15" (month + day)
        - Invalid:   "unknown"

    Examples:
        format_timestamp("2026-01-27T10:30:00+00:00")  # If now is 10:45 → "15m ago"
        format_timestamp("2026-01-20T10:30:00+00:00")  # If 7+ days ago → "Jan 20"
    """
    if not iso_str:
        return "unknown"

    try:
        # Parse ISO timestamp
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'

        # Handle both aware and naive timestamps
        if '+' in iso_str or iso_str.endswith('Z'):
            ts = datetime.fromisoformat(iso_str)
        else:
            # Assume UTC for naive timestamps
            ts = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = now - ts

        # Calculate relative time
        total_seconds = delta.total_seconds()

        if total_seconds < 0:
            # Future timestamp (clock skew) - show as "just now"
            return "just now"

        minutes = int(total_seconds // 60)
        hours = int(total_seconds // 3600)
        days = int(total_seconds // 86400)

        # Threshold: 7 days for relative vs absolute
        if days >= 7:
            # Absolute: "Jan 15"
            return ts.strftime("%b %d")
        elif days >= 1:
            return f"{days}d ago"
        elif hours >= 1:
            return f"{hours}h ago"
        elif minutes >= 1:
            return f"{minutes}m ago"
        else:
            return "just now"

    except (ValueError, TypeError, AttributeError):
        return "unknown"


def format_age_indicator(iso_str: str) -> str:
    """
    Return age category for temporal weighting.

    Used for semantic weight calculation - recent artifacts have higher relevance.

    Args:
        iso_str: ISO 8601 timestamp string

    Returns:
        Age category: "recent" | "today" | "this_week" | "older" | "unknown"

    Examples:
        format_age_indicator("2026-01-27T10:30:00+00:00")  # < 1 hour → "recent"
        format_age_indicator("2026-01-20T10:30:00+00:00")  # >= 7 days → "older"
    """
    if not iso_str:
        return "unknown"

    try:
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'

        if '+' in iso_str or iso_str.endswith('Z'):
            ts = datetime.fromisoformat(iso_str)
        else:
            ts = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = now - ts
        total_seconds = delta.total_seconds()

        if total_seconds < 0:
            return "recent"  # Future = treat as recent

        hours = total_seconds / 3600
        days = total_seconds / 86400

        if hours < 1:
            return "recent"
        elif days < 1:
            return "today"
        elif days < 7:
            return "this_week"
        else:
            return "older"

    except (ValueError, TypeError, AttributeError):
        return "unknown"


# =============================================================================
# Node/Artifact Formatting
# =============================================================================

def get_node_summary(node: 'Node') -> str:
    """
    Extract human-readable summary from node content.

    Tries multiple fields in order of preference to find the best
    human-readable description of the artifact.

    Args:
        node: Graph node to extract summary from

    Returns:
        Human-readable summary string
    """
    content = node.content

    # Try different fields in order of preference
    if 'summary' in content:
        return content['summary']
    if 'purpose' in content:
        return content['purpose']
    if 'what' in content:
        return content['what']

    # Handle proposal nodes (nested 'proposed' dict)
    proposed = content.get('proposed', {})
    if isinstance(proposed, dict):
        if 'summary' in proposed:
            return proposed['summary']
        if 'what' in proposed:
            return proposed['what']

    # Try nested detail
    detail = content.get('detail', {})
    if isinstance(detail, dict):
        if 'what' in detail:
            return detail['what']
        if 'goal' in detail:
            return detail['goal']

    # Handle code_symbol nodes (Output as Prose principle)
    # Format: "class CommitLink (babel-tool.babel.core.commit_links)"
    if 'symbol_type' in content and 'name' in content:
        symbol_type = content['symbol_type']
        name = content['name']
        qualified = content.get('qualified_name', '')
        if qualified and qualified != name and '.' in qualified:
            # Extract parent path from qualified name
            parent = qualified.rsplit('.', 1)[0]
            return f"{symbol_type} {name} ({parent})"
        return f"{symbol_type} {name}"

    # Fallback
    return str(content)[:SUMMARY_LENGTH]


def format_artifact(symbols: SymbolSet, artifact_type: str, summary: str, status: Optional[str] = None) -> str:
    """
    Format an artifact for display.

    Examples:
        ◇ Use SQLite ✓
        [>] Use SQLite [+]
    """
    type_sym = symbol_for_type(symbols, artifact_type)

    if status:
        status_sym = symbol_for_status(symbols, status)
        return f"{type_sym} {summary} {status_sym}"
    else:
        return f"{type_sym} {summary}"


def format_status_line(symbols: SymbolSet, status: str, detail: str) -> str:
    """
    Format a coherence status line.

    Examples:
        Coherence: ✓ checked 2h ago
        Coherence: [+] checked 2h ago
    """
    status_sym = symbol_for_status(symbols, status)
    return f"Coherence: {status_sym} {detail}"


def format_trace(symbols: SymbolSet, from_summary: str, to_type: str, to_summary: str, is_conflict: bool = False) -> str:
    """
    Format a trace/connection line.

    Examples:
        → links to ▢ "offline-first"
        ~> conflicts with [=] "offline-first"
    """
    trace_sym = symbols.trace_conflict if is_conflict else symbols.trace
    to_type_sym = symbol_for_type(symbols, to_type)
    return f"  {trace_sym} {'conflicts with' if is_conflict else 'links to'} {to_type_sym} \"{to_summary}\""


# =============================================================================
# Event Formatting
# =============================================================================

def format_event_preview(event: 'Event', max_length: int = 50) -> str:
    """
    Generate human-readable preview of an event showing WHAT happened.

    Implements dual-display principle [IH-PY]: Every event must show
    meaningful content, not just its type name.

    Args:
        event: Event to format
        max_length: Maximum length for content preview

    Returns:
        Human-readable preview string (e.g., 'Decision: "Use SQLite for..."')
    """
    # Import here to avoid circular imports at module load time
    from ..core.events import EventType

    data = event.data
    event_type = event.type

    # Human events - use generate_summary() for semantic content
    if event_type == EventType.PURPOSE_DECLARED:
        purpose = data.get('purpose', data.get('summary', ''))
        return f"Purpose: {generate_summary(purpose)}"

    if event_type == EventType.BOUNDARY_SET:
        boundary = data.get('boundary', data.get('summary', ''))
        return f"Boundary: {generate_summary(boundary)}"

    if event_type == EventType.ARTIFACT_CONFIRMED:
        artifact_type = data.get('artifact_type', 'artifact')
        summary = data.get('summary', data.get('what', ''))
        if summary:
            return f"Confirmed {artifact_type}: {generate_summary(summary)}"
        return f"Confirmed: {artifact_type}"

    if event_type == EventType.PROPOSAL_REJECTED:
        reason = data.get('reason', data.get('summary', ''))
        return f"Rejected: {generate_summary(reason)}"

    if event_type == EventType.CONVERSATION_CAPTURED:
        content = data.get('content', data.get('summary', ''))
        return f"Captured: \"{generate_summary(content)}\""

    if event_type == EventType.COMMIT_CAPTURED:
        hash_short = data.get('hash', '')[:8]
        message = data.get('message', '')
        return f"Commit: [{hash_short}] {generate_summary(message)}"

    # AI events - use generate_summary() for semantic content
    if event_type == EventType.STRUCTURE_PROPOSED:
        # Summary is nested inside 'proposed' dict
        proposed = data.get('proposed', {})
        summary = proposed.get('summary', data.get('summary', data.get('what', '')))
        return f"Proposed: {generate_summary(summary)}"

    if event_type == EventType.LINK_SUGGESTED:
        source = data.get('source_summary', data.get('source', ''))[:15]
        target = data.get('target_summary', data.get('target', ''))[:15]
        return f"Link: {source} → {target}"

    # System events
    if event_type == EventType.PROJECT_CREATED:
        name = data.get('name', data.get('project', ''))
        return f"Project created: {generate_summary(name)}"

    if event_type == EventType.COHERENCE_CHECKED:
        status = data.get('status', 'unknown')
        issues = data.get('issues', 0)
        return f"Coherence: {status} ({issues} issues)"

    # Collaboration events
    if event_type == EventType.EVENT_PROMOTED:
        promoted_id = data.get('promoted_id', '')[:8]
        return f"Promoted: {promoted_id}"

    # P2: Vocabulary events
    if event_type == EventType.TERM_DEFINED:
        term = data.get('term', data.get('name', ''))
        return f"Term defined: {truncate(term, max_length)}"

    if event_type == EventType.TERM_CHALLENGED:
        term = data.get('term', data.get('name', ''))
        return f"Term challenged: {truncate(term, max_length)}"

    if event_type == EventType.TERM_REFINED:
        term = data.get('term', data.get('name', ''))
        return f"Term refined: {truncate(term, max_length)}"

    if event_type == EventType.TERM_DISCARDED:
        term = data.get('term', data.get('name', ''))
        return f"Term discarded: {truncate(term, max_length)}"

    # P4: Disagreement events - use generate_summary() for semantic content
    if event_type == EventType.CHALLENGE_RAISED:
        reason = data.get('reason', data.get('summary', ''))
        return f"Challenge: {generate_summary(reason)}"

    if event_type == EventType.EVIDENCE_ADDED:
        evidence = data.get('evidence', data.get('summary', ''))
        return f"Evidence: {generate_summary(evidence)}"

    if event_type == EventType.CHALLENGE_RESOLVED:
        outcome = data.get('outcome', 'resolved')
        return f"Challenge resolved: {outcome}"

    # P9: Validation events
    if event_type == EventType.DECISION_REGISTERED:
        summary = data.get('summary', data.get('what', ''))
        return f"Decision: {generate_summary(summary)}"

    if event_type == EventType.DECISION_ENDORSED:
        # Data has decision_id (may be type-prefixed like "decision_abc123"), author, optional comment
        decision_id_raw = data.get('decision_id', '')
        # Strip type prefix if present (e.g., "decision_abc123" -> "abc123")
        decision_id = decision_id_raw.split('_', 1)[-1][:8] if '_' in decision_id_raw else decision_id_raw[:8]
        comment = data.get('comment', '')
        if comment:
            return f"Endorsed [{decision_id}]: {generate_summary(comment)}"
        return f"Endorsed: [{decision_id}]"

    if event_type == EventType.DECISION_EVIDENCED:
        # Data has decision_id (may be type-prefixed), content, evidence_type
        decision_id_raw = data.get('decision_id', '')
        decision_id = decision_id_raw.split('_', 1)[-1][:8] if '_' in decision_id_raw else decision_id_raw[:8]
        content = data.get('content', data.get('evidence', ''))
        return f"Evidenced [{decision_id}]: {generate_summary(content)}"

    # P10: Ambiguity events - use generate_summary() for semantic content
    if event_type == EventType.QUESTION_RAISED:
        question = data.get('question', data.get('summary', ''))
        return f"Question: {generate_summary(question)}"

    if event_type == EventType.QUESTION_RESOLVED:
        answer = data.get('answer', data.get('resolution', 'resolved'))
        return f"Answered: {generate_summary(answer)}"

    # P7: Evidence-weighted memory
    if event_type == EventType.ARTIFACT_DEPRECATED:
        reason = data.get('reason', data.get('summary', ''))
        return f"Deprecated: {generate_summary(reason)}"

    # Implementation planning
    if event_type == EventType.SPECIFICATION_ADDED:
        objective = data.get('objective', data.get('summary', ''))
        return f"Spec: {generate_summary(objective)}"

    # Ontology extension events - use generate_summary() for semantic content
    if event_type == EventType.TENSION_DETECTED:
        description = data.get('description', data.get('summary', ''))
        severity = data.get('severity', 'unknown')
        return f"Tension [{severity}]: {generate_summary(description)}"

    if event_type == EventType.EVOLUTION_CLASSIFIED:
        from_id = data.get('from_id', '')[:6]
        to_id = data.get('to_id', '')[:6]
        return f"Evolution: {from_id} → {to_id}"

    if event_type == EventType.NEGOTIATION_REQUIRED:
        # Data has artifact_id, constraint_ids, severity, reason
        reason = data.get('reason', '')
        severity = data.get('severity', 'info')
        if reason:
            return f"Negotiation [{severity}]: {generate_summary(reason)}"
        return f"Negotiation [{severity}]: constraint overlap detected"

    # Code symbol events
    if event_type == EventType.SYMBOL_INDEXED:
        symbol_name = data.get('name', data.get('symbol', ''))
        symbol_type = data.get('symbol_type', 'symbol')
        return f"Indexed {symbol_type}: {truncate(symbol_name, max_length - len(symbol_type) - 10)}"

    # Fallback: show type name in title case
    type_display = event_type.value.replace('_', ' ').title()
    return type_display
