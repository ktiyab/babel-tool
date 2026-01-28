"""
Event Store — Append-only event persistence (HC1)

Events are immutable. Once written, never modified.
This is the source of truth. Everything else is projection.

Hybrid Collaboration:
- Shared events: Git-tracked, team-visible
- Local events: Git-ignored, personal only
- Graph merges both for unified view
"""

import orjson
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from .scope import EventScope, get_default_scope, scope_from_string


class EventType(Enum):
    # Human events
    PURPOSE_DECLARED = "purpose_declared"
    BOUNDARY_SET = "boundary_set"
    ARTIFACT_CONFIRMED = "artifact_confirmed"
    PROPOSAL_REJECTED = "proposal_rejected"
    CONVERSATION_CAPTURED = "conversation_captured"
    COMMIT_CAPTURED = "commit_captured"

    # AI events
    STRUCTURE_PROPOSED = "structure_proposed"
    LINK_SUGGESTED = "link_suggested"

    # System events
    PROJECT_CREATED = "project_created"
    COHERENCE_CHECKED = "coherence_checked"

    # Collaboration events
    EVENT_PROMOTED = "event_promoted"  # Local → Shared

    # P2: Vocabulary events (definitions as artifacts)
    TERM_DEFINED = "term_defined"
    TERM_CHALLENGED = "term_challenged"
    TERM_REFINED = "term_refined"
    TERM_DISCARDED = "term_discarded"

    # P4: Disagreement events (disagreement as hypothesis)
    CHALLENGE_RAISED = "challenge_raised"
    EVIDENCE_ADDED = "evidence_added"
    CHALLENGE_RESOLVED = "challenge_resolved"

    # P9: Validation events (dual-test truth)
    DECISION_REGISTERED = "decision_registered"  # Track decision for validation
    DECISION_ENDORSED = "decision_endorsed"
    DECISION_EVIDENCED = "decision_evidenced"

    # P10: Ambiguity events (holding uncertainty)
    QUESTION_RAISED = "question_raised"
    QUESTION_RESOLVED = "question_resolved"

    # P7: Evidence-weighted memory (living artifacts)
    ARTIFACT_DEPRECATED = "artifact_deprecated"

    # Implementation planning (intent chain: need → spec → implementation)
    SPECIFICATION_ADDED = "specification_added"  # Links implementation plan to need

    # Ontology Extension Events (renegotiation-aligned relations)
    TENSION_DETECTED = "tension_detected"          # Auto-detected tension between artifacts
    EVOLUTION_CLASSIFIED = "evolution_classified"  # evolves_from relation classified
    NEGOTIATION_REQUIRED = "negotiation_required"  # Artifact touches constrained area

    # Code Symbol Events (processor-backed index for strategic loading)
    SYMBOL_INDEXED = "symbol_indexed"              # Code symbol extracted via AST


class TensionSeverity(Enum):
    """
    Graded severity levels for detected tensions (P5: Adaptive Cycle Rate).

    Enables calibrated response:
    - CRITICAL: Fundamental conflict requiring immediate attention
    - WARNING: Notable tension that should be addressed
    - INFO: Informational tension, awareness-level
    """
    CRITICAL = "critical"  # Cycle should accelerate
    WARNING = "warning"    # Maintain current rate
    INFO = "info"          # Continue normally


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    id: str = field(default="")
    scope: str = field(default="")  # "shared" | "local"
    parent_id: Optional[str] = None  # Causal chain: references originating event

    def __post_init__(self):
        if not self.id:
            content = f"{self.type.value}{self.timestamp}{orjson.dumps(self.data, option=orjson.OPT_SORT_KEYS).decode()}"
            self.id = hashlib.sha256(content.encode()).hexdigest()[:16]
        if not self.scope:
            self.scope = get_default_scope(self.type.value).value

    @property
    def event_scope(self) -> EventScope:
        """Get scope as enum."""
        return scope_from_string(self.scope)

    @property
    def is_shared(self) -> bool:
        return self.event_scope == EventScope.SHARED

    @property
    def is_local(self) -> bool:
        return self.event_scope == EventScope.LOCAL

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['type'] = self.type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Event':
        d['type'] = EventType(d['type'])
        # Handle legacy events without scope
        if 'scope' not in d:
            d['scope'] = get_default_scope(d['type'].value).value
        # Handle legacy events without parent_id
        if 'parent_id' not in d:
            d['parent_id'] = None
        return cls(**d)


class EventStore:
    """
    Single-file event store for backward compatibility.

    For new projects, use DualEventStore instead.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, event: Event) -> Event:
        """Append event to store. Returns event with ID."""
        with open(self.path, 'a') as f:
            f.write(orjson.dumps(event.to_dict()).decode() + '\n')
        return event

    def read_all(self) -> List[Event]:
        """Read all events in order."""
        events = []
        if self.path.exists():
            with open(self.path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(Event.from_dict(orjson.loads(line)))
                        except (orjson.JSONDecodeError, KeyError):
                            continue  # Skip malformed lines
        return events

    def read_by_type(self, event_type: EventType) -> List[Event]:
        """Read events of specific type."""
        return [e for e in self.read_all() if e.type == event_type]

    def count(self) -> int:
        """Count total events."""
        return len(self.read_all())

    def get(self, event_id: str) -> Optional[Event]:
        """Get event by ID."""
        for event in self.read_all():
            if event.id == event_id:
                return event
        return None

    def verify_integrity(self) -> bool:
        """Verify all events have valid hashes."""
        for event in self.read_all():
            content = f"{event.type.value}{event.timestamp}{orjson.dumps(event.data, option=orjson.OPT_SORT_KEYS).decode()}"
            expected = hashlib.sha256(content.encode()).hexdigest()[:16]
            if event.id != expected:
                return False
        return True


class DualEventStore:
    """
    Hybrid event store with shared (git) and local (personal) layers.

    Shared: .babel/shared/events.jsonl - Git tracked, team visible
    Local:  .babel/local/events.jsonl  - Git ignored, personal

    Graph is built from merged view (shared + local).
    """

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.babel_dir = self.project_dir / ".babel"

        self.shared_dir = self.babel_dir / "shared"
        self.local_dir = self.babel_dir / "local"

        self.shared_path = self.shared_dir / "events.jsonl"
        self.local_path = self.local_dir / "events.jsonl"

        # Mtime-based cache: {path: (mtime, events)}
        # Avoids re-reading 24MB+ files on every call
        self._cache: Dict[Path, Tuple[float, List[Event]]] = {}

        # Type-indexed cache for read_by_type() O(1) lookups
        # Invalidated when files change
        self._type_index: Optional[Dict[EventType, List[Event]]] = None
        self._type_index_mtime: Tuple[float, float] = (0.0, 0.0)  # (shared_mtime, local_mtime)

        # Create directories
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        self.local_dir.mkdir(parents=True, exist_ok=True)

        # Create gitignore for local
        self._ensure_gitignore()

        # Migrate legacy events if needed
        self._migrate_legacy()

    def _ensure_gitignore(self):
        """Ensure local directory is git-ignored."""
        gitignore_path = self.babel_dir / ".gitignore"

        ignore_patterns = [
            "local/",
            "graph.db",
            "graph.db-journal",
            "*.pyc",
            "__pycache__/",
        ]

        existing = set()
        if gitignore_path.exists():
            existing = set(gitignore_path.read_text().splitlines())

        missing = [p for p in ignore_patterns if p not in existing]

        if missing:
            with open(gitignore_path, 'a') as f:
                if existing:
                    f.write('\n')
                f.write('\n'.join(missing) + '\n')

    def _migrate_legacy(self):
        """Migrate legacy single-file events to dual store."""
        legacy_path = self.babel_dir / "events.jsonl"

        if legacy_path.exists() and not self.shared_path.exists():
            # Read legacy events
            legacy_events = []
            with open(legacy_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            legacy_events.append(Event.from_dict(orjson.loads(line)))
                        except (orjson.JSONDecodeError, KeyError):
                            continue

            # Distribute to shared/local based on type
            for event in legacy_events:
                self.append(event, scope=event.event_scope)

            # Rename legacy file
            os.replace(legacy_path, legacy_path.with_suffix('.jsonl.migrated'))

    def append(self, event: Event, scope: Optional[EventScope] = None) -> Event:
        """
        Append event to appropriate store.

        Args:
            event: Event to store
            scope: Override default scope (if None, uses event's scope)
        """
        if scope is None:
            scope = event.event_scope

        # Update event scope
        event.scope = scope.value

        path = self.shared_path if scope == EventScope.SHARED else self.local_path

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a') as f:
            f.write(orjson.dumps(event.to_dict()).decode() + '\n')

        # Invalidate cache for this file (mtime changed)
        if path in self._cache:
            del self._cache[path]

        # Also invalidate type index (new event added)
        self._type_index = None

        return event

    def read_shared(self) -> List[Event]:
        """Read shared events only."""
        return self._read_file(self.shared_path)

    def read_local(self) -> List[Event]:
        """Read local events only."""
        return self._read_file(self.local_path)

    def read_all(self, include_local: bool = True) -> List[Event]:
        """
        Read merged events from both stores.

        Args:
            include_local: Include local events (True for full view, False for team-only)
        """
        events = self.read_shared()
        if include_local:
            events.extend(self.read_local())

        # Sort by timestamp, deduplicate by ID
        seen = set()
        unique = []
        for event in sorted(events, key=lambda e: e.timestamp):
            if event.id not in seen:
                seen.add(event.id)
                unique.append(event)

        return unique

    def read_by_type(self, event_type: EventType, include_local: bool = True) -> List[Event]:
        """
        Read events of specific type using type-indexed cache.

        Uses pre-built type index for O(1) lookup instead of O(n) filtering.
        Index is rebuilt when underlying files change.
        """
        if not include_local:
            # Non-cached path for team-only view (less common)
            return [e for e in self.read_all(include_local) if e.type == event_type]

        # Check if type index needs rebuild
        shared_mtime = self.shared_path.stat().st_mtime if self.shared_path.exists() else 0.0
        local_mtime = self.local_path.stat().st_mtime if self.local_path.exists() else 0.0
        current_mtimes = (shared_mtime, local_mtime)

        if self._type_index is None or self._type_index_mtime != current_mtimes:
            # Rebuild type index
            self._type_index = {}
            for event in self.read_all(include_local=True):
                if event.type not in self._type_index:
                    self._type_index[event.type] = []
                self._type_index[event.type].append(event)
            self._type_index_mtime = current_mtimes

        return self._type_index.get(event_type, [])

    def get(self, event_id: str) -> Optional[Event]:
        """Get event by ID from either store."""
        for event in self.read_all():
            if event.id == event_id:
                return event
        return None

    def count(self, include_local: bool = True) -> int:
        """Count total events."""
        return len(self.read_all(include_local))

    def count_by_scope(self) -> Tuple[int, int]:
        """Return (shared_count, local_count)."""
        return len(self.read_shared()), len(self.read_local())

    def promote(self, event_id: str) -> Optional[Event]:
        """
        Promote an event from local to shared.

        Returns the promoted event, or None if not found/already shared.
        """
        # Find in local
        local_events = self.read_local()
        target = None
        remaining = []

        for event in local_events:
            if event.id == event_id:
                target = event
            else:
                remaining.append(event)

        if target is None:
            return None  # Not found in local

        if target.is_shared:
            return None  # Already shared

        # Update scope and append to shared
        target.scope = EventScope.SHARED.value
        with open(self.shared_path, 'a') as f:
            f.write(orjson.dumps(target.to_dict()).decode() + '\n')

        # Invalidate shared cache (file content changed)
        if self.shared_path in self._cache:
            del self._cache[self.shared_path]
        self._type_index = None

        # Rewrite local without the promoted event
        self._write_file(self.local_path, remaining)

        # Record promotion event
        promotion = Event(
            type=EventType.EVENT_PROMOTED,
            data={"promoted_id": event_id, "original_type": target.type.value}
        )
        self.append(promotion, scope=EventScope.SHARED)

        return target

    def sync(self) -> Dict[str, int]:
        """
        Synchronize after git pull.

        - Deduplicates shared events by ID
        - Keeps timestamps for ordering

        Returns: {"deduplicated": count, "total": count}
        """
        shared = self._read_file(self.shared_path)

        # Deduplicate by ID, keeping first occurrence
        seen = set()
        unique = []
        duplicates = 0

        for event in sorted(shared, key=lambda e: e.timestamp):
            if event.id not in seen:
                seen.add(event.id)
                unique.append(event)
            else:
                duplicates += 1

        if duplicates > 0:
            self._write_file(self.shared_path, unique)

        return {"deduplicated": duplicates, "total": len(unique)}

    def _read_file(self, path: Path) -> List[Event]:
        """
        Read events from a single file with mtime-based caching.

        Per SQLite best practices guide: application-level caching for
        large files that are read repeatedly. Converts 10 x 720ms = 7.2s
        into 720ms + 9 x ~1ms = ~730ms.
        """
        if not path.exists():
            return []

        current_mtime = path.stat().st_mtime

        # Check cache validity
        if path in self._cache:
            cached_mtime, cached_events = self._cache[path]
            if cached_mtime == current_mtime:
                return cached_events  # Cache hit: O(1)

        # Cache miss: read and parse file
        events = []
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(Event.from_dict(orjson.loads(line)))
                    except (orjson.JSONDecodeError, KeyError):
                        continue

        # Store in cache
        self._cache[path] = (current_mtime, events)
        return events

    def _write_file(self, path: Path, events: List[Event]):
        """Write events to a file (overwrite)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            for event in events:
                f.write(orjson.dumps(event.to_dict()).decode() + '\n')

        # Invalidate caches (file content changed)
        if path in self._cache:
            del self._cache[path]
        self._type_index = None

    def clear_cache(self):
        """
        Clear in-memory event caches.

        Forces re-read from disk on next access.
        Called by --force flag to bypass stale cache.
        """
        self._cache.clear()
        self._type_index = None
        self._type_index_mtime = (0.0, 0.0)


# Convenience functions for creating events

def capture_conversation(
    content: str,
    author: str = "user",
    domain: str = None,
    role: str = None,
    uncertain: bool = False,
    uncertainty_reason: str = None,
    parent_id: str = None
) -> Event:
    """
    Capture a conversation/decision (P3 + P10 compliant).

    Args:
        content: The content being captured
        author: Who is capturing this
        domain: Expertise domain (P3: bounded expertise)
        role: Author's role (optional, for attribution)
        uncertain: Mark as uncertain/provisional (P10: holding ambiguity)
        uncertainty_reason: Why this is uncertain
        parent_id: Causal parent event ID (typically None for root captures)

    P3 requires: Authority derives from declared, bounded expertise.
    P10 requires: Ambiguity explicitly recorded, not forced into closure.

    Returns:
        Event with optional parent_id for causal chain tracking
    """
    data = {"content": content, "author": author}
    if domain:
        data["domain"] = domain
    if role:
        data["role"] = role
    if uncertain:
        data["uncertain"] = True
        if uncertainty_reason:
            data["uncertainty_reason"] = uncertainty_reason
    return Event(
        type=EventType.CONVERSATION_CAPTURED,
        data=data,
        parent_id=parent_id  # Typically None for root captures
    )

def declare_purpose(purpose: str, need: str = None, author: str = "user") -> Event:
    """
    Declare project purpose grounded in need (P1 compliance).

    Args:
        purpose: What we intend to build
        need: What problem we're solving (P1: Bootstrap from Need)
        author: Who declared this

    P1 requires grounding in reality: "What is broken, insufficient, or at risk?"
    The need anchors the purpose to real-world problems.
    """
    data = {"purpose": purpose, "author": author}
    if need:
        data["need"] = need
    return Event(
        type=EventType.PURPOSE_DECLARED,
        data=data
    )

def confirm_artifact(proposal_id: str, artifact_type: str, content: Dict, author: str = "user", parent_id: str = None) -> Event:
    """
    Confirm an artifact from a proposal (human action).

    Args:
        proposal_id: ID of the STRUCTURE_PROPOSED event being confirmed
        artifact_type: Type of artifact (decision, constraint, principle, etc.)
        content: Artifact content dict
        author: Who confirmed it
        parent_id: Causal parent event ID (typically proposal_id for confirmations)

    Returns:
        Event with parent_id set for causal chain tracking (HC1: append-only)
    """
    return Event(
        type=EventType.ARTIFACT_CONFIRMED,
        data={
            "proposal_id": proposal_id,
            "artifact_type": artifact_type,
            "content": content,
            "author": author
        },
        parent_id=parent_id or proposal_id  # Default to proposal_id for causal linkage
    )


def reject_proposal(proposal_id: str, reason: str, author: str = "user", parent_id: str = None) -> Event:
    """
    Reject a proposal with reason (P8: Failure Metabolism).

    Rejection is recorded as an event (HC1: append-only), not deletion.
    The reason enables learning from rejected proposals.

    Args:
        proposal_id: ID of the STRUCTURE_PROPOSED event being rejected
        reason: Why it was rejected (enables learning)
        author: Who rejected it
        parent_id: Causal parent event ID (typically proposal_id)

    Returns:
        Event with parent_id set for causal chain tracking
    """
    return Event(
        type=EventType.PROPOSAL_REJECTED,
        data={
            "proposal_id": proposal_id,
            "reason": reason,
            "author": author
        },
        parent_id=parent_id or proposal_id  # Default to proposal_id for causal linkage
    )


def propose_structure(source_id: str, proposed: Dict, confidence: float, parent_id: str = None) -> Event:
    """
    Propose a structure extracted from a conversation (AI action).

    Args:
        source_id: ID of the source event (conversation/commit)
        proposed: Proposed artifact content
        confidence: Extraction confidence (0.0-1.0)
        parent_id: Causal parent event ID (typically source_id for proposals)

    Returns:
        Event with parent_id set for causal chain tracking
    """
    return Event(
        type=EventType.STRUCTURE_PROPOSED,
        data={
            "source_id": source_id,
            "proposed": proposed,
            "confidence": confidence
        },
        parent_id=parent_id or source_id  # Default to source_id for causal linkage
    )


def capture_commit(
    commit_hash: str,
    message: str,
    body: str,
    author: str,
    files: List[str],
    structural: Optional[Dict[str, Any]] = None,
    comment_diff: Optional[str] = None
) -> Event:
    """
    Capture a git commit with enhanced diff information.

    Args:
        commit_hash: Full commit hash (also serves as diff_id for deduplication)
        message: Commit message (first line)
        body: Commit body (additional lines)
        author: Author name
        files: List of changed files
        structural: Structural changes dict {added, modified, deleted, renamed}
        comment_diff: Extracted comment changes from diff
    """
    data = {
        "hash": commit_hash,
        "diff_id": commit_hash,  # Explicit deduplication key
        "message": message,
        "body": body,
        "author": author,
        "files": files
    }

    # Include enhanced data if available
    if structural is not None:
        data["structural"] = structural

    if comment_diff is not None:
        data["comment_diff"] = comment_diff

    return Event(
        type=EventType.COMMIT_CAPTURED,
        data=data
    )


def record_coherence_check(
    checkpoint_id: str,
    status: str,
    scope: Dict[str, Any],
    signals: List[str],
    entities: List[Dict[str, Any]],
    trigger: str,
    triggered_by: Optional[str] = None
) -> Event:
    """
    Record a coherence check result.

    Args:
        checkpoint_id: Unique identifier for this checkpoint
        status: "coherent" | "tension" | "drift"
        scope: What was compared {purpose_ids, artifact_ids, since}
        signals: What triggered/was noticed
        entities: List of {id, type, status, reason} for each entity checked
        trigger: "commit" | "pull" | "manual" | "scheduled"
        triggered_by: Identifier of trigger source (commit hash, user, etc.)
    """
    return Event(
        type=EventType.COHERENCE_CHECKED,
        data={
            "checkpoint_id": checkpoint_id,
            "status": status,
            "scope": scope,
            "signals": signals,
            "entities": entities,
            "trigger": trigger,
            "triggered_by": triggered_by
        }
    )


# =============================================================================
# P2: Vocabulary Events (Definitions as Artifacts)
# =============================================================================

def define_term(term: str, cluster: str, reason: str = None, author: str = "user") -> Event:
    """
    Record a term definition (P2: definitions as artifacts).

    Args:
        term: The term being defined
        cluster: Which cluster it belongs to
        reason: Why this definition
        author: Who defined it
    """
    return Event(
        type=EventType.TERM_DEFINED,
        data={
            "term": term,
            "cluster": cluster,
            "reason": reason,
            "author": author
        }
    )


def challenge_term(term: str, current_cluster: str, reason: str, author: str = "user") -> Event:
    """
    Record a term challenge (P2: terms can be challenged).

    Args:
        term: The term being challenged
        current_cluster: Its current cluster assignment
        reason: Why challenging
        author: Who challenged it
    """
    return Event(
        type=EventType.TERM_CHALLENGED,
        data={
            "term": term,
            "current_cluster": current_cluster,
            "reason": reason,
            "author": author
        }
    )


def refine_term(term: str, from_cluster: str, to_cluster: str, reason: str = None, author: str = "user") -> Event:
    """
    Record a term refinement (P2: terms can be refined).

    Args:
        term: The term being refined
        from_cluster: Previous cluster
        to_cluster: New cluster
        reason: Why this refinement
        author: Who refined it
    """
    return Event(
        type=EventType.TERM_REFINED,
        data={
            "term": term,
            "from_cluster": from_cluster,
            "to_cluster": to_cluster,
            "reason": reason,
            "author": author
        }
    )


def discard_term(term: str, from_cluster: str, reason: str = None, author: str = "user") -> Event:
    """
    Record a term discard (P2: terms can be discarded).

    Args:
        term: The term being discarded
        from_cluster: Its previous cluster
        reason: Why discarding
        author: Who discarded it
    """
    return Event(
        type=EventType.TERM_DISCARDED,
        data={
            "term": term,
            "from_cluster": from_cluster,
            "reason": reason,
            "author": author
        }
    )


# =============================================================================
# P4: Disagreement Events (Disagreement as Hypothesis)
# =============================================================================

def raise_challenge(
    parent_id: str,
    parent_type: str,
    reason: str,
    hypothesis: str = None,
    test: str = None,
    author: str = "user",
    domain: str = None
) -> Event:
    """
    Raise a challenge against a decision (P4: disagreement as information).

    Args:
        parent_id: ID of the decision/artifact being challenged
        parent_type: Type of parent ("decision", "constraint", etc.)
        reason: Why disagreeing
        hypothesis: Testable alternative claim (optional)
        test: How to test the hypothesis (optional)
        author: Who is challenging
        domain: Expertise domain (P3)

    P4 requires: Disagreement is information, not friction.
    Challenges don't override — they add context.
    """
    data = {
        "parent_id": parent_id,
        "parent_type": parent_type,
        "reason": reason,
        "status": "open",
        "author": author
    }
    if hypothesis:
        data["hypothesis"] = hypothesis
    if test:
        data["test"] = test
    if domain:
        data["domain"] = domain

    return Event(
        type=EventType.CHALLENGE_RAISED,
        data=data
    )


def add_evidence(
    challenge_id: str,
    content: str,
    evidence_type: str = "observation",
    author: str = "user"
) -> Event:
    """
    Add evidence to an open challenge (P4: build toward resolution).

    Args:
        challenge_id: ID of the challenge
        content: The evidence being added
        evidence_type: "observation" | "benchmark" | "user_feedback" | "other"
        author: Who is adding evidence

    Evidence accumulates until resolution is possible.
    """
    return Event(
        type=EventType.EVIDENCE_ADDED,
        data={
            "challenge_id": challenge_id,
            "content": content,
            "evidence_type": evidence_type,
            "author": author
        },
        parent_id=challenge_id  # Enable consistent ID display in history
    )


def resolve_challenge(
    challenge_id: str,
    outcome: str,
    resolution: str,
    evidence_summary: str = None,
    author: str = "user"
) -> Event:
    """
    Resolve a challenge with outcome (P4: no winning by authority alone).

    Args:
        challenge_id: ID of the challenge being resolved
        outcome: "confirmed" (original stands) | "revised" (challenger was right) | "synthesized" (new understanding)
        resolution: What was decided and why
        evidence_summary: Summary of evidence that led to resolution
        author: Who is resolving

    P4 requires: Resolution based on evidence, not authority.
    """
    return Event(
        type=EventType.CHALLENGE_RESOLVED,
        data={
            "challenge_id": challenge_id,
            "outcome": outcome,
            "resolution": resolution,
            "evidence_summary": evidence_summary,
            "author": author
        },
        parent_id=challenge_id  # Enable consistent ID display in history
    )


# =============================================================================
# P9: Validation Events (Dual-Test Truth)
# =============================================================================

def register_decision_for_validation(
    decision_id: str,
    summary: str,
    author: str = "user"
) -> Event:
    """
    Register a decision for validation tracking (P9).

    Called when a decision is confirmed, so it appears in validation status
    even before any endorsements or evidence are added.

    Args:
        decision_id: ID of the decision to track
        summary: Summary text for display
        author: Who registered it
    """
    return Event(
        type=EventType.DECISION_REGISTERED,
        data={
            "decision_id": decision_id,
            "summary": summary,
            "author": author
        },
        parent_id=decision_id  # Enable consistent ID display in history
    )


def endorse_decision(
    decision_id: str,
    author: str = "user",
    comment: str = None
) -> Event:
    """
    Endorse a decision (P9: consensus component of dual-test truth).

    Args:
        decision_id: ID of the decision being endorsed
        author: Who is endorsing
        comment: Optional comment on why endorsing

    P9 requires: Consensus alone is not sufficient (need evidence too).
    """
    data = {
        "decision_id": decision_id,
        "author": author
    }
    if comment:
        data["comment"] = comment

    return Event(
        type=EventType.DECISION_ENDORSED,
        data=data,
        parent_id=decision_id  # Enable consistent ID display in history
    )


def evidence_decision(
    decision_id: str,
    content: str,
    evidence_type: str = "observation",
    author: str = "user"
) -> Event:
    """
    Add evidence supporting a decision (P9: grounding component of dual-test truth).

    Args:
        decision_id: ID of the decision being evidenced
        content: The evidence
        evidence_type: "observation" | "benchmark" | "user_feedback" | "outcome" | "other"
        author: Who is providing evidence

    P9 requires: Evidence alone is not sufficient (need consensus too).
    """
    return Event(
        type=EventType.DECISION_EVIDENCED,
        data={
            "decision_id": decision_id,
            "content": content,
            "evidence_type": evidence_type,
            "author": author
        },
        parent_id=decision_id  # Enable consistent ID display in history
    )


# =============================================================================
# P10: Ambiguity Events (Holding Uncertainty)
# =============================================================================

def raise_question(
    content: str,
    context: str = None,
    domain: str = None,
    author: str = "user"
) -> Event:
    """
    Raise an open question (P10: holding ambiguity is epistemic maturity).

    Args:
        content: The question being raised
        context: Why this question matters
        domain: Related expertise domain (P3)
        author: Who raised it

    P10 requires: Unresolved tensions tracked as first-class artifacts.
    """
    data = {
        "content": content,
        "status": "open",
        "author": author
    }
    if context:
        data["context"] = context
    if domain:
        data["domain"] = domain

    return Event(
        type=EventType.QUESTION_RAISED,
        data=data
    )


def resolve_question(
    question_id: str,
    resolution: str,
    outcome: str = "answered",
    author: str = "user"
) -> Event:
    """
    Resolve an open question (P10: only when evidence sufficient).

    Args:
        question_id: ID of the question being resolved
        resolution: The answer or conclusion
        outcome: "answered" | "dissolved" | "superseded"
        author: Who resolved it

    P10 requires: Premature resolution is a failure mode.
    """
    return Event(
        type=EventType.QUESTION_RESOLVED,
        data={
            "question_id": question_id,
            "resolution": resolution,
            "outcome": outcome,
            "author": author
        },
        parent_id=question_id  # Enable consistent ID display in history
    )


# =============================================================================
# P7: Evidence-Weighted Memory (Deprecation)
# =============================================================================

def deprecate_artifact(
    artifact_id: str,
    reason: str,
    superseded_by: str = None,
    author: str = "user"
) -> Event:
    """
    Deprecate an artifact (P7: what fails is metabolized, not deleted).

    Args:
        artifact_id: ID of the artifact being deprecated
        reason: Why it's deprecated
        superseded_by: ID of replacement artifact (if any)
        author: Who deprecated it

    P7 requires: Living artifacts, not exhaustive archives.
    Deprecated items are de-prioritized in retrieval, not deleted (HC1 preserved).
    """
    data = {
        "artifact_id": artifact_id,
        "reason": reason,
        "author": author
    }
    if superseded_by:
        data["superseded_by"] = superseded_by

    return Event(
        type=EventType.ARTIFACT_DEPRECATED,
        data=data,
        parent_id=artifact_id  # Enable consistent ID display in history
    )


# =============================================================================
# Implementation Planning (Intent Chain: Need → Spec → Implementation)
# =============================================================================

def add_specification(
    need_id: str,
    objective: str,
    add: List[str] = None,
    modify: List[str] = None,
    remove: List[str] = None,
    preserve: List[str] = None,
    related_files: List[str] = None,
    author: str = "user",
    parent_id: str = None
) -> Event:
    """
    Add implementation specification to an existing need (HC1: append-only enrichment).

    The specification captures HOW we intend to implement a need:
    - OBJECTIVE: What this achieves
    - ADD: New things being introduced
    - MODIFY: Existing things being changed
    - REMOVE: Things being deleted deliberately
    - PRESERVE: Things that must NOT change
    - RELATED_FILES: Files to keep in mind

    This enables complete intent preservation: Need → Spec → Implementation.
    AI context recovery: `babel why "topic"` returns need + spec + implementation.

    Args:
        need_id: ID of the need/artifact being enriched
        objective: Single sentence describing what this achieves
        add: List of new things to introduce
        modify: List of existing things to change
        remove: List of things to deliberately delete
        preserve: List of things that must NOT change
        related_files: List of files to keep in lookback
        author: Who created this specification
        parent_id: Causal parent event ID (typically need_id)

    Returns:
        Event with parent_id set for causal chain tracking
    """
    data = {
        "need_id": need_id,
        "objective": objective,
        "author": author
    }
    if add:
        data["add"] = add
    if modify:
        data["modify"] = modify
    if remove:
        data["remove"] = remove
    if preserve:
        data["preserve"] = preserve
    if related_files:
        data["related_files"] = related_files

    return Event(
        type=EventType.SPECIFICATION_ADDED,
        data=data,
        parent_id=parent_id or need_id  # Default to need_id for causal linkage
    )


# =============================================================================
# Ontology Extension Events (Renegotiation-Aligned Relations)
# =============================================================================

def detect_tension(
    artifact_a_id: str,
    artifact_b_id: str,
    severity: str,
    reason: str,
    detection_method: str = "auto",
    author: str = "system"
) -> Event:
    """
    Record an auto-detected tension between artifacts (P4: disagreement as information).

    Args:
        artifact_a_id: First artifact in tension
        artifact_b_id: Second artifact in tension
        severity: "critical" | "warning" | "info" (P5: graded response)
        reason: Why tension was detected
        detection_method: "auto" (AI/graph) | "manual" (human)
        author: Who/what detected it

    Tensions express disagreement without implying one is wrong.
    Both artifacts preserved (HC1), tension surfaced for negotiation (P4).
    """
    return Event(
        type=EventType.TENSION_DETECTED,
        data={
            "artifact_a_id": artifact_a_id,
            "artifact_b_id": artifact_b_id,
            "severity": severity,
            "reason": reason,
            "detection_method": detection_method,
            "author": author,
            "status": "open"
        }
    )


def classify_evolution(
    artifact_id: str,
    evolves_from_id: str,
    classification_method: str = "llm",
    confidence: float = 0.0,
    reason: str = None,
    author: str = "system"
) -> Event:
    """
    Record an evolves_from classification (P2: emergent ontology, P4: layered validation).

    Args:
        artifact_id: The newer artifact
        evolves_from_id: The artifact it evolved from
        classification_method: "llm" (semantic analysis) | "manual" (human)
        confidence: LLM confidence score (0.0-1.0)
        reason: Why this classification
        author: Who/what classified

    Tracks lineage without deletion (HC1). New artifact preferred in queries,
    old artifact remains for history and context.
    """
    data = {
        "artifact_id": artifact_id,
        "evolves_from_id": evolves_from_id,
        "classification_method": classification_method,
        "confidence": confidence,
        "author": author
    }
    if reason:
        data["reason"] = reason

    return Event(
        type=EventType.EVOLUTION_CLASSIFIED,
        data=data
    )


def require_negotiation(
    artifact_id: str,
    constraint_ids: list,
    severity: str = "warning",
    reason: str = None,
    author: str = "system"
) -> Event:
    """
    Record that an artifact requires negotiation with constraints (HC2: human authority).

    Args:
        artifact_id: Artifact that touches constrained area
        constraint_ids: List of constraint IDs that may be affected
        severity: "critical" | "warning" | "info"
        reason: Why negotiation is required
        author: Who/what detected this

    Advisory only — warns but proceeds (HC2: AI proposes, human decides).
    Preserves human autonomy and sustainable adoption.
    """
    data = {
        "artifact_id": artifact_id,
        "constraint_ids": constraint_ids,
        "severity": severity,
        "author": author,
        "warning_surfaced": True
    }
    if reason:
        data["reason"] = reason

    return Event(
        type=EventType.NEGOTIATION_REQUIRED,
        data=data
    )


# =============================================================================
# Code Symbol Events (Processor-backed Index for Strategic Loading)
# =============================================================================

def index_symbol(
    symbol_type: str,
    name: str,
    qualified_name: str,
    file_path: str,
    line_start: int,
    line_end: int,
    signature: str = None,
    docstring: str = None,
    parent_symbol: str = None,
    visibility: str = "public",
    git_hash: str = None,
    author: str = "system"
) -> Event:
    """
    Record a code symbol indexed via AST (processor-backed, not LLM inference).

    Args:
        symbol_type: "class" | "function" | "method" | "module" | "variable"
        name: Simple name (e.g., "CacheManager")
        qualified_name: Full path (e.g., "babel.core.cache.CacheManager")
        file_path: Relative file path from project root
        line_start: Starting line number (1-indexed)
        line_end: Ending line number (1-indexed)
        signature: Full signature (e.g., "class CacheManager(BaseCache)")
        docstring: First line of docstring (truncated for storage)
        parent_symbol: ID of containing symbol (for methods in classes)
        visibility: "public" | "private" (based on leading underscore)
        git_hash: Commit hash when indexed (for staleness detection)
        author: Who/what indexed it (typically "system")

    Purpose: Enable strategic code loading by mapping symbols to locations.
    LLMs query the index to find code, then load only required portions.
    Links to babel decisions via 'touches' edges in graph.
    """
    data = {
        "symbol_type": symbol_type,
        "name": name,
        "qualified_name": qualified_name,
        "file_path": file_path,
        "line_start": line_start,
        "line_end": line_end,
        "visibility": visibility,
        "author": author
    }
    if signature:
        data["signature"] = signature
    if docstring:
        data["docstring"] = docstring[:200]  # Truncate for storage efficiency
    if parent_symbol:
        data["parent_symbol"] = parent_symbol
    if git_hash:
        data["git_hash"] = git_hash

    return Event(
        type=EventType.SYMBOL_INDEXED,
        data=data
    )
