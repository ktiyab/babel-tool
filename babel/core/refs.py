"""
Refs — Git-like O(1) lookup for events

Refs are lightweight pointers to events, organized by topic.
AI creates refs automatically during extraction.
Users never interact with refs directly.

Structure:
    .babel/refs/
    ├── purpose              → current purpose event_id
    ├── topics/
    │   ├── database.json    → [event_ids...]
    │   └── auth.json        → [event_ids...]
    └── decisions/
        └── confirmed.json   → [event_ids...]

Principles:
    - Refs are derived (like Git's index)
    - Events are source of truth (like Git's objects)
    - Deleting refs loses nothing — rebuild from events
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import re

from .events import Event, EventType


@dataclass
class Ref:
    """A reference pointing to events about a topic."""
    name: str
    event_ids: List[str] = field(default_factory=list)
    updated_at: str = ""
    
    def add(self, event_id: str):
        """Add event ID if not already present."""
        if event_id not in self.event_ids:
            self.event_ids.append(event_id)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "event_ids": self.event_ids,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Ref':
        return cls(
            name=data["name"],
            event_ids=data.get("event_ids", []),
            updated_at=data.get("updated_at", "")
        )


class RefStore:
    """
    Manages refs for O(1) event lookup by topic.
    
    Git-like: refs are cheap pointers, not data.
    AI-native: topics extracted semantically.
    """
    
    def __init__(self, babel_dir: Path):
        self.babel_dir = Path(babel_dir)
        self.refs_dir = self.babel_dir / "refs"
        self.refs_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        (self.refs_dir / "topics").mkdir(exist_ok=True)
        (self.refs_dir / "decisions").mkdir(exist_ok=True)
        
        # In-memory cache
        self._cache: Dict[str, Ref] = {}
        self._loaded = False
    
    # =========================================================================
    # Core Operations
    # =========================================================================
    
    def get(self, ref_path: str) -> Optional[Ref]:
        """
        Get a ref by path.
        
        Examples:
            get("purpose")
            get("topics/database")
            get("decisions/confirmed")
        """
        self._ensure_loaded()
        return self._cache.get(ref_path)
    
    def set(self, ref_path: str, event_ids: List[str], updated_at: str = ""):
        """Set a ref to point to specific events."""
        ref = Ref(name=ref_path, event_ids=event_ids, updated_at=updated_at)
        self._cache[ref_path] = ref
        self._persist_ref(ref_path, ref)
    
    def append(self, ref_path: str, event_id: str, updated_at: str = ""):
        """Append an event to a ref."""
        ref = self.get(ref_path)
        if ref is None:
            ref = Ref(name=ref_path)
        
        ref.add(event_id)
        ref.updated_at = updated_at
        
        self._cache[ref_path] = ref
        self._persist_ref(ref_path, ref)
    
    def find(self, query: str) -> List[str]:
        """
        Find event IDs matching a query.
        
        Searches ref names for matches (O(n) over refs, not events).
        Returns deduplicated event IDs.
        """
        self._ensure_loaded()
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        matches: Set[str] = set()
        
        for ref_path, ref in self._cache.items():
            # Check if query matches ref name
            ref_name = ref_path.split("/")[-1].lower()
            
            # Exact match
            if query_lower == ref_name:
                matches.update(ref.event_ids)
                continue
            
            # Partial match (query word in ref name)
            if any(word in ref_name for word in query_words):
                matches.update(ref.event_ids)
                continue
            
            # Ref name word in query
            ref_words = set(ref_name.replace("-", " ").replace("_", " ").split())
            if ref_words & query_words:
                matches.update(ref.event_ids)
        
        return list(matches)
    
    def list_refs(self, prefix: str = "") -> List[str]:
        """List all ref paths, optionally filtered by prefix."""
        self._ensure_loaded()
        
        if prefix:
            return [p for p in self._cache.keys() if p.startswith(prefix)]
        return list(self._cache.keys())
    
    def list_topics(self) -> List[str]:
        """List all topic names."""
        return [
            p.replace("topics/", "")
            for p in self.list_refs("topics/")
        ]
    
    # =========================================================================
    # Persistence
    # =========================================================================
    
    def _ensure_loaded(self):
        """Load refs from disk if not cached."""
        if self._loaded:
            return
        
        # Load purpose ref
        purpose_file = self.refs_dir / "purpose.json"
        if purpose_file.exists():
            self._cache["purpose"] = Ref.from_dict(
                json.loads(purpose_file.read_text())
            )
        
        # Load topic refs
        topics_dir = self.refs_dir / "topics"
        if topics_dir.exists():
            for f in topics_dir.glob("*.json"):
                ref_path = f"topics/{f.stem}"
                self._cache[ref_path] = Ref.from_dict(
                    json.loads(f.read_text())
                )
        
        # Load decision refs
        decisions_dir = self.refs_dir / "decisions"
        if decisions_dir.exists():
            for f in decisions_dir.glob("*.json"):
                ref_path = f"decisions/{f.stem}"
                self._cache[ref_path] = Ref.from_dict(
                    json.loads(f.read_text())
                )
        
        self._loaded = True
    
    def _persist_ref(self, ref_path: str, ref: Ref):
        """Write a ref to disk."""
        if "/" in ref_path:
            # Nested ref (e.g., topics/database)
            parts = ref_path.split("/", 1)
            subdir = self.refs_dir / parts[0]
            subdir.mkdir(exist_ok=True)
            file_path = subdir / f"{parts[1]}.json"
        else:
            # Top-level ref
            file_path = self.refs_dir / f"{ref_path}.json"
        
        file_path.write_text(json.dumps(ref.to_dict(), indent=2))
    
    # =========================================================================
    # Rebuild from Events
    # =========================================================================
    
    def rebuild(self, events: List[Event]):
        """
        Rebuild all refs from events.
        
        Called when refs are lost or corrupted.
        Events are source of truth.
        """
        # Clear cache
        self._cache = {}
        
        # Clear disk
        for f in self.refs_dir.glob("**/*.json"):
            f.unlink()
        
        # Index each event
        for event in events:
            self.index_event(event)
        
        self._loaded = True
    
    def index_event(self, event: Event, vocabulary: 'Vocabulary' = None):
        """
        Index an event, creating refs for its topics.
        
        Uses vocabulary for semantic understanding.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        
        # Extract topics from event (vocabulary-aware)
        topics = extract_topics(event, vocabulary)
        
        for topic in topics:
            self.append(f"topics/{topic}", event.id, updated_at=now)
        
        # Special refs by event type
        if event.type == EventType.PURPOSE_DECLARED:
            self.set("purpose", [event.id], updated_at=now)
        
        elif event.type == EventType.ARTIFACT_CONFIRMED:
            self.append("decisions/confirmed", event.id, updated_at=now)
            
            # Extract artifact type as topic
            artifact_type = event.data.get("artifact_type", "")
            if artifact_type:
                self.append(f"topics/{artifact_type}", event.id, updated_at=now)
        
        elif event.type == EventType.BOUNDARY_SET:
            self.append("decisions/constraints", event.id, updated_at=now)
        
        elif event.type == EventType.COMMIT_CAPTURED:
            self.append("commits", event.id, updated_at=now)
        
        # Save vocabulary if provided (persist learned terms)
        if vocabulary:
            vocabulary.save()
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def stats(self) -> Dict[str, Any]:
        """Get ref statistics."""
        self._ensure_loaded()
        
        topics = self.list_refs("topics/")
        decisions = self.list_refs("decisions/")
        
        total_refs = len(self._cache)
        total_event_refs = sum(len(r.event_ids) for r in self._cache.values())
        
        return {
            "total_refs": total_refs,
            "topics": len(topics),
            "decisions": len(decisions),
            "total_event_refs": total_event_refs
        }


# =============================================================================
# Topic Extraction
# =============================================================================

def extract_topics(event: Event, vocabulary: 'Vocabulary' = None) -> List[str]:
    """
    Extract topics from an event.
    
    Uses vocabulary for semantic understanding.
    Falls back to word extraction if no vocabulary.
    """
    from .vocabulary import Vocabulary
    
    topics: Set[str] = set()
    
    # Get text to analyze
    text = _get_event_text(event)
    words = _extract_words(text)
    
    if vocabulary:
        # Vocabulary-based extraction (semantic)
        for word in words:
            cluster = vocabulary.find_cluster(word)
            if cluster:
                topics.add(cluster)  # Add cluster name as topic
                topics.add(word)     # Also add specific term
        
        # Learn any new meaningful words
        vocabulary.learn_from_extraction(words)
    else:
        # Fallback: just use extracted words
        topics.update(words)
    
    return list(topics)[:10]


def _extract_words(text: str) -> List[str]:
    """Extract meaningful words from text."""
    words = text.lower().split()
    meaningful = []
    
    for word in words:
        word = word.strip('.,;:!?()"\'[]{}')
        if len(word) >= 3 and word.isalpha() and word not in STOPWORDS:
            meaningful.append(word)
    
    return meaningful[:20]  # Limit to prevent noise


def _get_event_text(event: Event) -> str:
    """Extract searchable text from event."""
    parts = []
    
    data = event.data
    
    # Common fields
    for key in ['content', 'purpose', 'summary', 'message', 'body']:
        if key in data:
            value = data[key]
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, dict):
                parts.append(str(value))
    
    # Nested content
    if 'content' in data and isinstance(data['content'], dict):
        content = data['content']
        for key in ['summary', 'what', 'why', 'detail']:
            if key in content:
                parts.append(str(content[key]))
    
    return " ".join(parts)


def _normalize_topic(raw: str) -> str:
    """Normalize a topic string."""
    # Lowercase
    topic = raw.lower().strip()
    
    # Canonical names
    canonicals = {
        'postgres': 'postgresql',
        'pg': 'postgresql',
        'db': 'database',
        'auth': 'authentication',
        'k8s': 'kubernetes',
    }
    
    return canonicals.get(topic, topic)


STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
    'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just',
    'that', 'this', 'these', 'those', 'what', 'which', 'who', 'whom',
    'when', 'where', 'why', 'how', 'all', 'each', 'every', 'any', 'some',
    'such', 'more', 'most', 'other', 'another', 'much', 'many', 'few',
    'use', 'used', 'using', 'make', 'made', 'take', 'taken', 'get', 'got',
    'want', 'need', 'like', 'think', 'know', 'see', 'come', 'also',
}
