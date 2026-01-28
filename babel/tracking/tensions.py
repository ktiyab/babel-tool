"""
Tensions — Disagreement tracking and resolution (P4 compliant)

P4: Disagreement as Hypothesis
- Disagreement is information, not friction
- Disputes are reframed as testable hypotheses
- No participant wins by authority alone
- Resolution requires evidence

Workflow:
1. See decision → Challenge with reason
2. Optionally propose hypothesis + test
3. Add evidence as it's gathered
4. Resolve when evidence supports conclusion

Tensions integrate with:
- Graph (challenges link to parent decisions)
- Scanner (reports open tensions)
- Status (shows tension count)
- Why queries (shows challenges in context)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from ..core.events import (
    DualEventStore, Event, EventType,
    raise_challenge, add_evidence, resolve_challenge
)
from ..core.scope import EventScope
from ..presentation.formatters import generate_summary, format_timestamp
from ..presentation.symbols import get_symbols


@dataclass
class Challenge:
    """A challenge against a decision."""
    id: str
    parent_id: str
    parent_type: str
    reason: str
    hypothesis: Optional[str]
    test: Optional[str]
    status: str  # "open" | "resolved"
    author: str
    domain: Optional[str]
    created_at: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    resolution: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_event(cls, event: Event) -> "Challenge":
        """Create Challenge from event."""
        data = event.data
        return cls(
            id=event.id,
            parent_id=data.get("parent_id", ""),
            parent_type=data.get("parent_type", ""),
            reason=data.get("reason", ""),
            hypothesis=data.get("hypothesis"),
            test=data.get("test"),
            status=data.get("status", "open"),
            author=data.get("author", "unknown"),
            domain=data.get("domain"),
            created_at=event.timestamp
        )
    
    def add_evidence_item(self, evidence_event: Event):
        """Add evidence from event."""
        self.evidence.append({
            "id": evidence_event.id,
            "content": evidence_event.data.get("content", ""),
            "evidence_type": evidence_event.data.get("evidence_type", "observation"),
            "author": evidence_event.data.get("author", "unknown"),
            "timestamp": evidence_event.timestamp
        })
    
    def set_resolution(self, resolution_event: Event):
        """Set resolution from event."""
        self.status = "resolved"
        self.resolution = {
            "id": resolution_event.id,
            "outcome": resolution_event.data.get("outcome", ""),
            "resolution": resolution_event.data.get("resolution", ""),
            "evidence_summary": resolution_event.data.get("evidence_summary"),
            "author": resolution_event.data.get("author", "unknown"),
            "timestamp": resolution_event.timestamp
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "parent_type": self.parent_type,
            "reason": self.reason,
            "hypothesis": self.hypothesis,
            "test": self.test,
            "status": self.status,
            "author": self.author,
            "domain": self.domain,
            "created_at": self.created_at,
            "evidence": self.evidence,
            "resolution": self.resolution
        }


class TensionTracker:
    """
    Track and manage challenges/tensions (P4 compliant).
    
    Provides:
    - Challenge creation and lookup
    - Evidence aggregation
    - Resolution tracking
    - Open tension queries
    """
    
    def __init__(self, events: DualEventStore):
        self.events = events
        self._cache: Optional[Dict[str, Challenge]] = None
    
    def _load_challenges(self) -> Dict[str, Challenge]:
        """Load all challenges from events."""
        if self._cache is not None:
            return self._cache
        
        challenges: Dict[str, Challenge] = {}
        
        # Load challenge events
        challenge_events = self.events.read_by_type(EventType.CHALLENGE_RAISED)
        for event in challenge_events:
            challenge = Challenge.from_event(event)
            challenges[challenge.id] = challenge
        
        # Load evidence events
        evidence_events = self.events.read_by_type(EventType.EVIDENCE_ADDED)
        for event in evidence_events:
            challenge_id = event.data.get("challenge_id", "")
            if challenge_id in challenges:
                challenges[challenge_id].add_evidence_item(event)
        
        # Load resolution events
        resolution_events = self.events.read_by_type(EventType.CHALLENGE_RESOLVED)
        for event in resolution_events:
            challenge_id = event.data.get("challenge_id", "")
            if challenge_id in challenges:
                challenges[challenge_id].set_resolution(event)
        
        self._cache = challenges
        return challenges
    
    def invalidate_cache(self):
        """Invalidate cache after changes."""
        self._cache = None
    
    # =========================================================================
    # Challenge Operations
    # =========================================================================
    
    def raise_challenge(
        self,
        parent_id: str,
        parent_type: str,
        reason: str,
        hypothesis: str = None,
        test: str = None,
        author: str = "user",
        domain: str = None
    ) -> Challenge:
        """
        Raise a new challenge (P4: disagreement as information).
        
        Returns the created Challenge.
        """
        event = raise_challenge(
            parent_id=parent_id,
            parent_type=parent_type,
            reason=reason,
            hypothesis=hypothesis,
            test=test,
            author=author,
            domain=domain
        )
        
        # Challenges are shared — team needs to see disagreements
        self.events.append(event, scope=EventScope.SHARED)
        self.invalidate_cache()
        
        return Challenge.from_event(event)
    
    def add_evidence(
        self,
        challenge_id: str,
        content: str,
        evidence_type: str = "observation",
        author: str = "user"
    ) -> bool:
        """
        Add evidence to a challenge.
        
        Returns True if successful.
        """
        challenges = self._load_challenges()
        
        if challenge_id not in challenges:
            return False
        
        if challenges[challenge_id].status == "resolved":
            return False  # Can't add evidence to resolved challenge
        
        event = add_evidence(
            challenge_id=challenge_id,
            content=content,
            evidence_type=evidence_type,
            author=author
        )
        
        self.events.append(event, scope=EventScope.SHARED)
        self.invalidate_cache()
        
        return True
    
    def resolve(
        self,
        challenge_id: str,
        outcome: str,
        resolution: str,
        evidence_summary: str = None,
        author: str = "user"
    ) -> bool:
        """
        Resolve a challenge (P4: requires evidence, not authority).
        
        Args:
            outcome: "confirmed" | "revised" | "synthesized"
            resolution: What was decided
            evidence_summary: Evidence supporting resolution
        
        Returns True if successful.
        """
        challenges = self._load_challenges()
        
        if challenge_id not in challenges:
            return False
        
        challenge = challenges[challenge_id]
        if challenge.status == "resolved":
            return False  # Already resolved
        
        event = resolve_challenge(
            challenge_id=challenge_id,
            outcome=outcome,
            resolution=resolution,
            evidence_summary=evidence_summary,
            author=author
        )
        
        self.events.append(event, scope=EventScope.SHARED)
        self.invalidate_cache()
        
        return True
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get a specific challenge by ID."""
        challenges = self._load_challenges()
        return challenges.get(challenge_id)
    
    def get_open_challenges(self) -> List[Challenge]:
        """Get all open (unresolved) challenges."""
        challenges = self._load_challenges()
        return [c for c in challenges.values() if c.status == "open"]
    
    def get_resolved_challenges(self) -> List[Challenge]:
        """Get all resolved challenges."""
        challenges = self._load_challenges()
        return [c for c in challenges.values() if c.status == "resolved"]
    
    def get_challenges_for_parent(self, parent_id: str) -> List[Challenge]:
        """Get all challenges against a specific decision/artifact."""
        challenges = self._load_challenges()
        return [c for c in challenges.values() if c.parent_id == parent_id]
    
    def get_open_challenges_for_parent(self, parent_id: str) -> List[Challenge]:
        """Get open challenges against a specific decision/artifact."""
        return [c for c in self.get_challenges_for_parent(parent_id) if c.status == "open"]
    
    def count_open(self) -> int:
        """Count open challenges."""
        return len(self.get_open_challenges())
    
    def get_challenges_by_domain(self, domain: str) -> List[Challenge]:
        """Get challenges in a specific domain."""
        challenges = self._load_challenges()
        return [c for c in challenges.values() if c.domain == domain]
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def stats(self) -> Dict[str, Any]:
        """Get tension statistics."""
        challenges = self._load_challenges()
        open_challenges = [c for c in challenges.values() if c.status == "open"]
        resolved_challenges = [c for c in challenges.values() if c.status == "resolved"]
        
        # Count by outcome
        outcomes = {}
        for c in resolved_challenges:
            if c.resolution:
                outcome = c.resolution.get("outcome", "unknown")
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
        
        return {
            "total": len(challenges),
            "open": len(open_challenges),
            "resolved": len(resolved_challenges),
            "with_hypothesis": len([c for c in challenges.values() if c.hypothesis]),
            "outcomes": outcomes
        }


# =============================================================================
# Formatting Functions
# =============================================================================

def format_challenge(challenge: Challenge, verbose: bool = False, full: bool = False) -> str:
    """
    Format a challenge for display.

    Args:
        challenge: Challenge to format
        verbose: Show evidence details
        full: Show full content without truncation
    """
    lines = []

    status_icon = "○" if challenge.status == "open" else "●"
    domain_tag = f" [{challenge.domain}]" if challenge.domain else ""

    lines.append(f"{status_icon} Challenge [{challenge.id[:8]}]{domain_tag}")
    lines.append(f"  Against: {challenge.parent_type} [{challenge.parent_id[:8]}]")
    lines.append(f"  Reason: {generate_summary(challenge.reason, full=full)}")

    if challenge.hypothesis:
        lines.append(f"  Hypothesis: {generate_summary(challenge.hypothesis, full=full)}")

    if challenge.test:
        lines.append(f"  Test: {generate_summary(challenge.test, full=full)}")

    # P12: Time always shown
    lines.append(f"  By: {challenge.author} | {format_timestamp(challenge.created_at)}")

    if verbose and challenge.evidence:
        lines.append(f"  Evidence ({len(challenge.evidence)}):")
        for e in challenge.evidence[-3:]:  # Show last 3
            content = generate_summary(e['content'], full=full)
            lines.append(f"    • {content}")

    if challenge.resolution:
        r = challenge.resolution
        lines.append(f"  Resolution: {r['outcome']}")
        lines.append(f"    {generate_summary(r['resolution'], full=full)}")

    return "\n".join(lines)


def format_tensions_summary(tracker: TensionTracker, full: bool = False) -> str:
    """
    Format summary of all tensions.

    Args:
        tracker: Tension tracker instance
        full: Show full content without truncation
    """
    symbols = get_symbols()
    stats = tracker.stats()
    open_challenges = tracker.get_open_challenges()

    lines = []

    if stats["open"] == 0:
        lines.append("No open tensions.")
    else:
        lines.append(f"{symbols.tension} Open Tensions: {stats['open']}")
        lines.append("")

        for challenge in open_challenges[:10]:  # Limit display
            hypothesis_note = ""
            if challenge.hypothesis:
                status = "untested" if not challenge.evidence else f"{len(challenge.evidence)} evidence"
                hypothesis_note = f" ({status})"

            reason = generate_summary(challenge.reason, full=full)
            lines.append(f"  {symbols.bullet} [{challenge.id[:8]}] {reason}{hypothesis_note}")

        if len(open_challenges) > 10:
            lines.append(f"  ... and {len(open_challenges) - 10} more")

    if stats["resolved"] > 0:
        lines.append("")
        lines.append(f"Resolved: {stats['resolved']} (confirmed: {stats['outcomes'].get('confirmed', 0)}, "
                    f"revised: {stats['outcomes'].get('revised', 0)}, "
                    f"synthesized: {stats['outcomes'].get('synthesized', 0)})")

    return "\n".join(lines)


def format_challenge_in_context(challenge: Challenge) -> str:
    """Format a challenge for display within a 'why' query."""
    symbols = get_symbols()
    lines = []

    status_icon = symbols.tension if challenge.status == "open" else symbols.check_pass

    lines.append(f"{symbols.tree_branch} {status_icon} CHALLENGE [{challenge.id[:8]}]")
    lines.append(f"|  \"{challenge.reason}\"")
    # P12: Time always shown
    lines.append(f"|  By: {challenge.author} | {format_timestamp(challenge.created_at)}")

    if challenge.hypothesis:
        evidence_status = "untested" if not challenge.evidence else f"{len(challenge.evidence)} evidence"
        lines.append(f"|  Hypothesis: {challenge.hypothesis}")
        lines.append(f"|  Status: {symbols.proposed} {evidence_status}")

    if challenge.resolution:
        lines.append(f"|  Resolved: {challenge.resolution['outcome']}")

    return "\n".join(lines)
