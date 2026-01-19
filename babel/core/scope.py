"""
Scope — Hybrid collaboration layer management

Two truth layers:
- Shared: Git-tracked, team-visible, source of truth
- Local: Git-ignored, personal notes, drafts

Graph merges both for unified view.
"""

from enum import Enum
from typing import Optional


class EventScope(Enum):
    """Where an event lives."""
    SHARED = "shared"  # Git-tracked, team-visible
    LOCAL = "local"    # Git-ignored, personal only


# Default scopes by event type
DEFAULT_SCOPES = {
    # Team decisions - shared by default
    "project_created": EventScope.SHARED,
    "purpose_declared": EventScope.SHARED,
    "boundary_set": EventScope.SHARED,
    "artifact_confirmed": EventScope.SHARED,
    "coherence_checked": EventScope.SHARED,

    # Personal/draft - local by default
    "conversation_captured": EventScope.LOCAL,
    "structure_proposed": EventScope.LOCAL,
    "link_suggested": EventScope.LOCAL,
    "commit_captured": EventScope.SHARED,  # Commits are shared (they're in git anyway)
    "proposal_rejected": EventScope.LOCAL,
}


def get_default_scope(event_type: str) -> EventScope:
    """Get default scope for an event type."""
    return DEFAULT_SCOPES.get(event_type, EventScope.LOCAL)


def scope_display_marker(scope: EventScope, use_unicode: bool = True) -> str:
    """Get display marker for scope."""
    if scope == EventScope.SHARED:
        return "●" if use_unicode else "[S]"
    else:
        return "○" if use_unicode else "[L]"


def scope_from_string(s: Optional[str]) -> EventScope:
    """Parse scope from string, defaulting to LOCAL."""
    if s is None:
        return EventScope.LOCAL
    try:
        return EventScope(s.lower())
    except ValueError:
        return EventScope.LOCAL
