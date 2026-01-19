"""
Loader — Lazy loading for token-efficient event access

Git-like principle: Load only what's traversed.
Never load all events when refs can answer.

Loading strategy:
    1. Expand query using vocabulary (semantic)
    2. Check refs (O(1), zero tokens)
    3. Load summaries if needed (low tokens)
    4. Load full events only for "why" queries (full tokens)

Compliance:
    - "Why" queries always get full events (P1: reasoning travels)
    - Summaries only for navigation/triage
    - Full reconstruction always possible
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from dataclasses import dataclass

from .events import Event, EventType, DualEventStore
from .refs import RefStore
from .horizon import ArtifactDigest, EventDigest, estimate_tokens

if TYPE_CHECKING:
    from .graph import GraphStore, Node
    from .vocabulary import Vocabulary


@dataclass
class LoadResult:
    """Result of a lazy load operation."""
    events: List[Event]
    source: str  # "refs" | "summaries" | "full_scan"
    tokens_used: int
    total_available: int


class LazyLoader:
    """
    Token-efficient event loading.
    
    Implements Git-like lazy loading:
    - Expand query with vocabulary (semantic)
    - Follow refs first (cheap)
    - Expand search only if needed (expensive)
    """
    
    def __init__(
        self,
        events: DualEventStore,
        refs: RefStore,
        graph: 'GraphStore',
        vocabulary: 'Vocabulary' = None
    ):
        self.events = events
        self.refs = refs
        self.graph = graph
        self.vocabulary = vocabulary
        
        # Cache for session
        self._event_cache: Dict[str, Event] = {}
        self._summary_cache: Dict[str, str] = {}
    
    # =========================================================================
    # Primary Interface
    # =========================================================================
    
    def load_for_why(self, query: str) -> LoadResult:
        """
        Load events to answer a "why" query.
        
        ALWAYS returns full events (P1 compliance).
        Uses vocabulary for semantic expansion.
        Uses refs for O(1) lookup when possible.
        """
        # Step 1: Expand query using vocabulary
        expanded_terms = self._expand_query(query)
        
        # Step 2: Check refs for all expanded terms
        event_ids = set()
        for term in expanded_terms:
            event_ids.update(self.refs.find(term))
        
        if event_ids:
            # Found via refs — load full events
            events = self._load_events_by_ids(list(event_ids))
            return LoadResult(
                events=events,
                source="refs",
                tokens_used=self._estimate_tokens(events),
                total_available=self.events.count()
            )
        
        # Step 3: Fall back to full scan (expensive)
        events = self._search_all_events(query)
        return LoadResult(
            events=events,
            source="full_scan",
            tokens_used=self._estimate_tokens(events),
            total_available=self.events.count()
        )
    
    def _expand_query(self, query: str) -> List[str]:
        """
        Expand query using vocabulary.
        
        "postgres" → ["postgres", "postgresql", "pg", "database", ...]
        """
        if self.vocabulary:
            # Use vocabulary for semantic expansion
            terms = query.lower().split()
            expanded = set()
            for term in terms:
                expanded.update(self.vocabulary.expand(term))
            return list(expanded) if expanded else [query.lower()]
        else:
            # No vocabulary — just use raw terms
            return query.lower().split()
    
    def load_for_status(self) -> Dict[str, Any]:
        """
        Load minimal data for status display.
        
        Uses refs and counts only — no full event loading.
        """
        ref_stats = self.refs.stats()
        shared, local = self.events.count_by_scope()
        
        # Get purpose from ref (O(1))
        purpose_ref = self.refs.get("purpose")
        purpose_text = None
        if purpose_ref and purpose_ref.event_ids:
            # Load just the purpose event
            purpose_event = self._get_event(purpose_ref.event_ids[-1])
            if purpose_event:
                purpose_text = purpose_event.data.get('purpose', '')
        
        return {
            "purpose": purpose_text,
            "shared_count": shared,
            "local_count": local,
            "topics": ref_stats.get("topics", 0),
            "decisions": ref_stats.get("decisions", 0),
            "tokens_used": estimate_tokens(purpose_text or "")
        }
    
    def load_for_coherence(self, full: bool = False) -> LoadResult:
        """
        Load events for coherence checking.
        
        Default: Load summaries for triage, full events for conflicts.
        Full mode: Load all events (expensive).
        """
        if full:
            events = self.events.read_all()
            return LoadResult(
                events=events,
                source="full_scan",
                tokens_used=self._estimate_tokens(events),
                total_available=len(events)
            )
        
        # Smart loading: purpose + constraints + recent decisions
        event_ids = set()
        
        # Always include purpose
        purpose_ref = self.refs.get("purpose")
        if purpose_ref:
            event_ids.update(purpose_ref.event_ids)
        
        # Include constraints (important for conflict detection)
        constraint_ref = self.refs.get("decisions/constraints")
        if constraint_ref:
            event_ids.update(constraint_ref.event_ids)
        
        # Include recent confirmed decisions (last 20)
        confirmed_ref = self.refs.get("decisions/confirmed")
        if confirmed_ref:
            event_ids.update(confirmed_ref.event_ids[-20:])
        
        events = self._load_events_by_ids(list(event_ids))
        
        return LoadResult(
            events=events,
            source="refs",
            tokens_used=self._estimate_tokens(events),
            total_available=self.events.count()
        )
    
    def load_for_history(
        self,
        limit: int = 10,
        scope_filter: Optional[str] = None
    ) -> LoadResult:
        """
        Load events for history display.
        
        Returns summaries, not full events (navigation only).
        """
        if scope_filter == "shared":
            events = self.events.read_shared()[-limit:]
        elif scope_filter == "local":
            events = self.events.read_local()[-limit:]
        else:
            events = self.events.read_all()[-limit:]
        
        return LoadResult(
            events=events,
            source="summaries",
            tokens_used=self._estimate_tokens(events),
            total_available=self.events.count()
        )
    
    # =========================================================================
    # Event Access
    # =========================================================================
    
    def _get_event(self, event_id: str) -> Optional[Event]:
        """Get single event by ID, using cache."""
        if event_id in self._event_cache:
            return self._event_cache[event_id]
        
        event = self.events.get(event_id)
        if event:
            self._event_cache[event_id] = event
        
        return event
    
    def _load_events_by_ids(self, event_ids: List[str]) -> List[Event]:
        """Load multiple events by ID."""
        events = []
        for eid in event_ids:
            event = self._get_event(eid)
            if event:
                events.append(event)
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        return events
    
    def _search_all_events(self, query: str) -> List[Event]:
        """
        Full scan search (expensive fallback).
        
        Used when refs don't find anything.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        matches = []
        
        for event in self.events.read_all():
            text = self._get_event_text(event).lower()
            
            # Check for query matches
            if query_lower in text:
                matches.append(event)
            elif any(word in text for word in query_words):
                matches.append(event)
        
        return matches
    
    def _get_event_text(self, event: Event) -> str:
        """Extract searchable text from event."""
        parts = []
        data = event.data
        
        for key in ['content', 'purpose', 'summary', 'message', 'body']:
            if key in data:
                value = data[key]
                if isinstance(value, str):
                    parts.append(value)
        
        if 'content' in data and isinstance(data['content'], dict):
            content = data['content']
            for key in ['summary', 'what', 'why']:
                if key in content:
                    parts.append(str(content[key]))
        
        return " ".join(parts)
    
    # =========================================================================
    # Token Estimation
    # =========================================================================
    
    def _estimate_tokens(self, events: List[Event]) -> int:
        """Estimate token count for events."""
        total = 0
        for event in events:
            text = self._get_event_text(event)
            total += estimate_tokens(text)
        return total
    
    # =========================================================================
    # Index Management
    # =========================================================================
    
    def ensure_indexed(self):
        """Ensure all events are indexed in refs."""
        # Get all indexed event IDs
        indexed = set()
        for ref_path in self.refs.list_refs():
            ref = self.refs.get(ref_path)
            if ref:
                indexed.update(ref.event_ids)
        
        # Index any missing events
        for event in self.events.read_all():
            if event.id not in indexed:
                self.refs.index_event(event)
    
    def rebuild_index(self):
        """Rebuild refs index from events."""
        self.refs.rebuild(self.events.read_all())
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def clear_cache(self):
        """Clear in-memory caches."""
        self._event_cache.clear()
        self._summary_cache.clear()


# =============================================================================
# Token Budget Management
# =============================================================================

@dataclass
class TokenBudget:
    """Manages token consumption per session."""
    system_prompt: int = 1500
    active_context: int = 5000
    query_context: int = 2000
    response_reserve: int = 3000
    
    @property
    def total(self) -> int:
        return (
            self.system_prompt +
            self.active_context +
            self.query_context +
            self.response_reserve
        )
    
    def remaining_for_context(self, used: int) -> int:
        """How many tokens left for loading context."""
        max_context = self.active_context + self.query_context
        return max(0, max_context - used)


DEFAULT_BUDGET = TokenBudget()


def within_budget(tokens: int, budget: TokenBudget = DEFAULT_BUDGET) -> bool:
    """Check if token count is within budget."""
    max_context = budget.active_context + budget.query_context
    return tokens <= max_context
