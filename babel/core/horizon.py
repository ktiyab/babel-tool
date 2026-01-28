"""
Horizon — Token-efficient event and artifact compression

Implements the compaction pattern:
- Lossy summary + lossless archive
- Structure survives compression
- Incremental recovery
- Threshold-triggered

Events beyond horizon are summarized but never deleted.
Artifact digests enable cheap coherence checks.
"""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict

from .events import EventStore, Event, EventType
from ..presentation.formatters import generate_summary

if TYPE_CHECKING:
    from .graph import GraphStore, Node


# Default horizon: events older than this get summarized
DEFAULT_HORIZON_DAYS = 30

# Maximum tokens for coherence context
MAX_COHERENCE_TOKENS = 1500  # ~6KB text

# Digest lengths
PURPOSE_DIGEST_LENGTH = 100
ARTIFACT_DIGEST_LENGTH = 80
MAX_ARTIFACT_DIGESTS = 20


@dataclass
class EventDigest:
    """Compressed representation of an event."""
    id: str
    type: str
    timestamp: str
    summary: str  # One-line summary
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "summary": self.summary
        }
    
    @classmethod
    def from_event(cls, event: Event) -> 'EventDigest':
        """Create digest from full event."""
        summary = _summarize_event(event)
        return cls(
            id=event.id,
            type=event.type.value,
            timestamp=event.timestamp[:10],  # Date only
            summary=summary
        )


@dataclass
class ArtifactDigest:
    """Compressed representation of an artifact for coherence checking."""
    id: str
    artifact_type: str
    summary: str
    keywords: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.artifact_type,
            "summary": self.summary,
            "keywords": self.keywords
        }
    
    @classmethod
    def from_node(cls, node: 'Node') -> 'ArtifactDigest':
        """Create digest from graph node."""
        # Extract summary
        content = node.content
        summary = content.get('summary', '')
        if not summary:
            summary = content.get('purpose', '')
        if not summary:
            detail = content.get('detail', {})
            summary = detail.get('what', str(content)[:ARTIFACT_DIGEST_LENGTH])
        
        # Truncate if needed
        if len(summary) > ARTIFACT_DIGEST_LENGTH:
            summary = summary[:ARTIFACT_DIGEST_LENGTH-3] + "..."
        
        # Extract keywords for fast matching
        keywords = _extract_keywords(summary)
        
        return cls(
            id=node.id,
            artifact_type=node.type,
            summary=summary,
            keywords=keywords
        )


@dataclass
class HorizonSnapshot:
    """Summary of events beyond the horizon."""
    snapshot_id: str
    created_at: str
    horizon_date: str  # Events before this date are summarized
    event_count: int
    events_by_type: Dict[str, int]
    digests: List[EventDigest]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "horizon_date": self.horizon_date,
            "event_count": self.event_count,
            "events_by_type": self.events_by_type,
            "digests": [d.to_dict() for d in self.digests]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HorizonSnapshot':
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at=data["created_at"],
            horizon_date=data["horizon_date"],
            event_count=data["event_count"],
            events_by_type=data["events_by_type"],
            digests=[EventDigest(**d) for d in data.get("digests", [])]
        )


@dataclass
class CoherenceContext:
    """Token-efficient context for coherence checking."""
    purpose_digest: str
    artifact_digests: List[ArtifactDigest]
    constraint_keywords: Dict[str, List[str]]  # id -> keywords
    total_artifacts: int
    
    @property
    def estimated_tokens(self) -> int:
        """Rough token estimate (1 token ≈ 4 chars)."""
        text_length = len(self.purpose_digest)
        for ad in self.artifact_digests:
            text_length += len(ad.summary) + len(' '.join(ad.keywords))
        return text_length // 4
    
    def to_prompt(self) -> str:
        """Generate compact prompt context."""
        lines = [
            f"Purpose: {self.purpose_digest}",
            f"Artifacts: {self.total_artifacts} total",
            ""
        ]
        
        # Group by type for readability
        by_type = defaultdict(list)
        for ad in self.artifact_digests:
            by_type[ad.artifact_type].append(ad)
        
        for atype, digests in by_type.items():
            lines.append(f"{atype.title()}s:")
            for ad in digests[:10]:  # Max 10 per type
                lines.append(f"  - {ad.summary}")
        
        return "\n".join(lines)


class EventHorizon:
    """
    Manages event compression beyond a time horizon.
    
    Events within horizon: Full detail available
    Events beyond horizon: Summarized in snapshot, originals still accessible
    """
    
    def __init__(self, events: EventStore, horizon_days: int = DEFAULT_HORIZON_DAYS):
        self.events = events
        self.horizon = timedelta(days=horizon_days)
        self._snapshot_cache: Optional[HorizonSnapshot] = None
    
    @property
    def horizon_date(self) -> str:
        """ISO date string for the horizon cutoff."""
        cutoff = datetime.now(timezone.utc) - self.horizon
        return cutoff.isoformat()
    
    def get_active_events(self) -> List[Event]:
        """Get events within the horizon (full detail)."""
        cutoff = self.horizon_date
        return [e for e in self.events.read_all() if e.timestamp >= cutoff]
    
    def get_archived_events(self) -> List[Event]:
        """Get events beyond the horizon (for snapshotting)."""
        cutoff = self.horizon_date
        return [e for e in self.events.read_all() if e.timestamp < cutoff]
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Access any event by ID (active or archived)."""
        for event in self.events.read_all():
            if event.id == event_id:
                return event
        return None
    
    def get_or_create_snapshot(self) -> Optional[HorizonSnapshot]:
        """Get existing snapshot or create new one if needed."""
        archived = self.get_archived_events()
        
        if not archived:
            return None
        
        # Check if we have a recent snapshot
        existing = self._find_existing_snapshot()
        if existing and self._snapshot_is_current(existing, archived):
            return existing
        
        # Create new snapshot
        return self._create_snapshot(archived)
    
    def _find_existing_snapshot(self) -> Optional[HorizonSnapshot]:
        """Find most recent horizon snapshot event."""
        # Look for snapshot in events (stored as special event type)
        for event in reversed(self.events.read_all()):
            if event.type == EventType.COHERENCE_CHECKED:
                data = event.data
                if data.get("checkpoint_id", "").startswith("horizon_"):
                    return HorizonSnapshot.from_dict(data.get("snapshot", {}))
        return None
    
    def _snapshot_is_current(self, snapshot: HorizonSnapshot, archived: List[Event]) -> bool:
        """Check if snapshot covers all archived events."""
        return snapshot.event_count >= len(archived)
    
    def _create_snapshot(self, archived: List[Event]) -> HorizonSnapshot:
        """Create a new snapshot summarizing archived events."""
        # Count by type
        by_type: Dict[str, int] = defaultdict(int)
        for event in archived:
            by_type[event.type.value] += 1
        
        # Create digests for important events (purposes, decisions, constraints)
        important_types = {
            EventType.PURPOSE_DECLARED,
            EventType.ARTIFACT_CONFIRMED,
            EventType.BOUNDARY_SET
        }
        digests = [
            EventDigest.from_event(e)
            for e in archived
            if e.type in important_types
        ][-50:]  # Keep last 50 important events
        
        snapshot_id = f"horizon_{hashlib.sha256(self.horizon_date.encode()).hexdigest()[:12]}"
        
        return HorizonSnapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            horizon_date=self.horizon_date,
            event_count=len(archived),
            events_by_type=dict(by_type),
            digests=digests
        )
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get statistics about active vs archived events."""
        active = self.get_active_events()
        archived = self.get_archived_events()
        
        return {
            "active_count": len(active),
            "archived_count": len(archived),
            "horizon_date": self.horizon_date[:10],
            "total_count": len(active) + len(archived)
        }


class DigestBuilder:
    """Builds token-efficient digests for coherence checking."""
    
    def __init__(self, graph: 'GraphStore'):
        self.graph = graph
    
    def build_coherence_context(
        self,
        purposes: List['Node'],
        artifacts: List['Node'],
        max_artifacts: int = MAX_ARTIFACT_DIGESTS
    ) -> CoherenceContext:
        """
        Build compact context for coherence checking.
        
        Target: ~500 tokens instead of ~2000+
        """
        # Purpose digest
        purpose_texts = []
        for p in purposes:
            text = p.content.get('purpose', str(p.content))
            if len(text) > PURPOSE_DIGEST_LENGTH:
                text = text[:PURPOSE_DIGEST_LENGTH-3] + "..."
            purpose_texts.append(text)
        purpose_digest = " | ".join(purpose_texts)
        
        # Artifact digests (prioritize recent, constraints first)
        constraints = [a for a in artifacts if a.type == 'constraint']
        others = [a for a in artifacts if a.type != 'constraint']
        
        # Constraints are important for conflict detection
        prioritized = constraints + others
        
        artifact_digests = [
            ArtifactDigest.from_node(a)
            for a in prioritized[:max_artifacts]
        ]
        
        # Build keyword lookup for constraints (fast conflict detection)
        constraint_keywords = {
            ad.id: ad.keywords
            for ad in artifact_digests
            if ad.artifact_type == 'constraint'
        }
        
        return CoherenceContext(
            purpose_digest=purpose_digest,
            artifact_digests=artifact_digests,
            constraint_keywords=constraint_keywords,
            total_artifacts=len(artifacts)
        )
    
    def check_conflicts_fast(
        self,
        artifact: ArtifactDigest,
        constraint_keywords: Dict[str, List[str]]
    ) -> List[str]:
        """
        Fast conflict detection using keyword matching.
        
        Returns list of constraint IDs that may conflict.
        No LLM call needed.
        """
        conflicts = []
        artifact_keywords = set(artifact.keywords)
        
        for constraint_id, keywords in constraint_keywords.items():
            if _keywords_conflict(artifact_keywords, set(keywords)):
                conflicts.append(constraint_id)
        
        return conflicts


# ============================================================================
# Helper Functions
# ============================================================================

def _summarize_event(event: Event) -> str:
    """Create one-line summary of an event."""
    data = event.data
    
    if event.type == EventType.PURPOSE_DECLARED:
        purpose = data.get('purpose', '')[:60]
        return f"Purpose: {purpose}"
    
    elif event.type == EventType.ARTIFACT_CONFIRMED:
        atype = data.get('artifact_type', 'artifact')
        summary = generate_summary(data.get('content', {}).get('summary', ''))
        return f"{atype}: {summary}"
    
    elif event.type == EventType.COMMIT_CAPTURED:
        msg = data.get('message', '')[:40]
        return f"Commit: {msg}"
    
    elif event.type == EventType.CONVERSATION_CAPTURED:
        content = data.get('content', '')[:40]
        return f"Captured: {content}"
    
    elif event.type == EventType.COHERENCE_CHECKED:
        status = data.get('status', 'unknown')
        return f"Coherence: {status}"
    
    else:
        return event.type.value.replace('_', ' ').title()


def _extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from text."""
    # Lowercase and split
    words = text.lower().split()
    
    # Remove stopwords
    stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'to', 'for', 'of', 'and', 'or', 'in', 'on', 'with', 'as',
        'at', 'by', 'this', 'that', 'it', 'we', 'our', 'must', 'should',
        'will', 'can', 'use', 'using', 'used'
    }
    
    # Keep meaningful words (3+ chars, not stopwords)
    keywords = [
        w.strip('.,;:!?()[]"\'')
        for w in words
        if len(w) >= 3 and w not in stopwords
    ]
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    
    return unique[:10]  # Max 10 keywords


def _keywords_conflict(artifact_kw: set, constraint_kw: set) -> bool:
    """
    Check if artifact keywords conflict with constraint keywords.
    
    Conflict patterns:
    - offline constraint vs sync/online/cloud artifact
    - simple/mvp constraint vs complex/full artifact
    - single constraint vs multi artifact
    - local constraint vs remote/cloud artifact
    """
    conflicts = [
        # (constraint contains, artifact contains)
        ({'offline', 'local'}, {'sync', 'online', 'cloud', 'remote', 'real-time'}),
        ({'simple', 'mvp', 'minimal'}, {'complex', 'full', 'complete', 'advanced'}),
        ({'single'}, {'multi', 'multiple', 'distributed'}),
        ({'local'}, {'remote', 'cloud', 'distributed', 'network'}),
        ({'synchronous', 'blocking'}, {'async', 'asynchronous', 'background'}),
    ]
    
    for constraint_markers, artifact_markers in conflicts:
        if constraint_kw & constraint_markers and artifact_kw & artifact_markers:
            return True
    
    return False


def estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 4 characters for English)."""
    return len(text) // 4
