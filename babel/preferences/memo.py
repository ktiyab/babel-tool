"""
MemoManager — Persistent user preferences with graph integration

Memos are operational shortcuts that:
- Persist across sessions (survives context compression)
- Surface contextually based on graph edges
- Are mutable (unlike HC1 decisions)
- Require no WHY (operational, not architectural)

Design:
- Storage: .babel/local/memos.json (mutable JSON, not event-sourced)
- Graph integration: memo nodes with applies_to edges to topics
- Candidates: AI-detected patterns awaiting user confirmation
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set


@dataclass
class Memo:
    """
    A confirmed user preference.

    Memos are operational shortcuts, not architectural decisions.
    They're mutable and require no reasoning (WHY).

    Init memos (init=True) are foundational instructions that surface
    automatically at session start via 'babel status'. They survive
    context compression and ensure AI operators see critical rules.
    """
    id: str
    content: str
    contexts: List[str] = field(default_factory=list)  # Topics this applies to
    created: str = ""
    updated: str = ""
    source: str = "manual"  # "manual" | "promoted" (from candidate)
    use_count: int = 0  # Times surfaced/applied
    init: bool = False  # Foundational instruction - surfaces at session start

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now(timezone.utc).isoformat()
        if not self.updated:
            self.updated = self.created


@dataclass
class Candidate:
    """
    An AI-detected pattern awaiting user confirmation.

    Candidates track repeated instructions across sessions.
    When threshold is met, user is prompted to promote to memo.
    """
    id: str
    content: str
    contexts: List[str] = field(default_factory=list)  # Where it was observed
    sessions: List[str] = field(default_factory=list)  # Session IDs where seen
    first_seen: str = ""
    count: int = 1
    status: str = "pending"  # "pending" | "dismissed"

    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = datetime.now(timezone.utc).isoformat()


class MemoManager:
    """
    Manager for user memos and candidates.

    Storage: .babel/local/memos.json
    Graph integration: Generates edges for contextual surfacing

    Key methods:
    - add/remove/update: CRUD for memos
    - get_relevant: Context-aware memo retrieval
    - add_candidate/promote/dismiss: Candidate lifecycle
    """

    # Threshold for suggesting candidate promotion
    PROMOTION_THRESHOLD = 2  # Sessions or same-session repeats

    def __init__(self, babel_dir: Path, session_id: Optional[str] = None):
        """
        Initialize MemoManager.

        Args:
            babel_dir: Path to .babel directory
            session_id: Current session identifier (for candidate tracking)
        """
        self.babel_dir = Path(babel_dir)
        self.local_dir = self.babel_dir / "local"
        self.storage_path = self.local_dir / "memos.json"
        self.session_id = session_id or self._generate_session_id()

        self._ensure_storage()
        self._data = self._load()

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        now = datetime.now(timezone.utc).isoformat()
        return hashlib.sha256(now.encode()).hexdigest()[:8]

    def _ensure_storage(self):
        """Ensure storage directory and file exist."""
        self.local_dir.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save({"memos": [], "candidates": []})

    def _load(self) -> Dict[str, Any]:
        """Load data from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                # Ensure required keys exist
                if "memos" not in data:
                    data["memos"] = []
                if "candidates" not in data:
                    data["candidates"] = []
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {"memos": [], "candidates": []}

    def _save(self, data: Optional[Dict[str, Any]] = None):
        """Save data to storage."""
        if data is None:
            data = self._data
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_id(self, prefix: str, content: str) -> str:
        """Generate unique ID for memo or candidate."""
        hash_input = f"{content}{datetime.now(timezone.utc).isoformat()}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        return f"{prefix}_{hash_value}"

    # -------------------------------------------------------------------------
    # Memo CRUD Operations
    # -------------------------------------------------------------------------

    def add(self, content: str, contexts: Optional[List[str]] = None, init: bool = False) -> Memo:
        """
        Add a new memo.

        Args:
            content: The memo content (operational instruction)
            contexts: Optional list of contexts where this applies
            init: If True, this is a foundational instruction that surfaces at session start

        Returns:
            The created Memo
        """
        memo = Memo(
            id=self._generate_id("m", content),
            content=content,
            contexts=contexts or [],
            source="manual",
            init=init
        )
        self._data["memos"].append(asdict(memo))
        self._save()
        return memo

    def remove(self, memo_id: str) -> bool:
        """
        Remove a memo by ID.

        Args:
            memo_id: The memo ID (or prefix)

        Returns:
            True if removed, False if not found
        """
        original_count = len(self._data["memos"])
        self._data["memos"] = [
            m for m in self._data["memos"]
            if not m["id"].startswith(memo_id)
        ]

        if len(self._data["memos"]) < original_count:
            self._save()
            return True
        return False

    def update(self, memo_id: str, content: Optional[str] = None,
               contexts: Optional[List[str]] = None) -> Optional[Memo]:
        """
        Update an existing memo.

        Args:
            memo_id: The memo ID (or prefix)
            content: New content (if provided)
            contexts: New contexts (if provided)

        Returns:
            Updated Memo or None if not found
        """
        for memo_data in self._data["memos"]:
            if memo_data["id"].startswith(memo_id):
                if content is not None:
                    memo_data["content"] = content
                if contexts is not None:
                    memo_data["contexts"] = contexts
                memo_data["updated"] = datetime.now(timezone.utc).isoformat()
                self._save()
                return Memo(**memo_data)
        return None

    def get(self, memo_id: str) -> Optional[Memo]:
        """
        Get a memo by ID.

        Args:
            memo_id: The memo ID (or prefix)

        Returns:
            Memo or None if not found
        """
        for memo_data in self._data["memos"]:
            if memo_data["id"].startswith(memo_id):
                return Memo(**memo_data)
        return None

    def list_memos(self) -> List[Memo]:
        """
        List all memos.

        Returns:
            List of all Memo objects
        """
        return [Memo(**m) for m in self._data["memos"]]

    def list_init_memos(self) -> List[Memo]:
        """
        List only init memos (foundational instructions).

        Init memos surface at session start via 'babel status'.
        They ensure AI operators see critical rules after context compression.

        Returns:
            List of Memo objects where init=True
        """
        return [Memo(**m) for m in self._data["memos"] if m.get("init", False)]

    def set_init(self, memo_id: str, is_init: bool) -> Optional[Memo]:
        """
        Set or unset the init flag on a memo.

        Args:
            memo_id: The memo ID (or prefix)
            is_init: True to make foundational, False to make regular

        Returns:
            Updated Memo or None if not found
        """
        for memo_data in self._data["memos"]:
            if memo_data["id"].startswith(memo_id):
                memo_data["init"] = is_init
                memo_data["updated"] = datetime.now(timezone.utc).isoformat()
                self._save()
                return Memo(**memo_data)
        return None

    def get_relevant(self, contexts: List[str]) -> List[Memo]:
        """
        Get memos relevant to given contexts.

        Uses set intersection: memo surfaces if any of its contexts
        match any of the query contexts.

        Args:
            contexts: List of active context topics

        Returns:
            List of matching Memo objects
        """
        if not contexts:
            return []

        context_set = set(c.lower() for c in contexts)
        relevant = []

        for memo_data in self._data["memos"]:
            memo_contexts = set(c.lower() for c in memo_data.get("contexts", []))

            # Match if contexts intersect, or memo has no contexts (global)
            if not memo_contexts or memo_contexts & context_set:
                memo = Memo(**memo_data)
                relevant.append(memo)

        return relevant

    def increment_use(self, memo_id: str) -> bool:
        """
        Increment use count for a memo.

        Args:
            memo_id: The memo ID (or prefix)

        Returns:
            True if incremented, False if not found
        """
        for memo_data in self._data["memos"]:
            if memo_data["id"].startswith(memo_id):
                memo_data["use_count"] = memo_data.get("use_count", 0) + 1
                self._save()
                return True
        return False

    # -------------------------------------------------------------------------
    # Candidate Operations (AI-detected patterns)
    # -------------------------------------------------------------------------

    def add_candidate(self, content: str, contexts: Optional[List[str]] = None) -> Candidate:
        """
        Register an AI-detected pattern as candidate.

        If same content exists, increments count and adds session.
        If threshold reached, returns candidate with ready-to-promote status.

        Args:
            content: The detected instruction pattern
            contexts: Contexts where it was observed

        Returns:
            The Candidate (new or updated)
        """
        content_lower = content.lower().strip()
        contexts = contexts or []

        # Check for existing candidate with similar content
        for cand_data in self._data["candidates"]:
            if cand_data["content"].lower().strip() == content_lower:
                # Update existing candidate
                if self.session_id not in cand_data["sessions"]:
                    cand_data["sessions"].append(self.session_id)
                    cand_data["count"] = len(cand_data["sessions"])

                # Add new contexts
                existing_contexts = set(cand_data.get("contexts", []))
                for ctx in contexts:
                    existing_contexts.add(ctx)
                cand_data["contexts"] = list(existing_contexts)

                self._save()
                return Candidate(**cand_data)

        # Create new candidate
        candidate = Candidate(
            id=self._generate_id("c", content),
            content=content,
            contexts=contexts,
            sessions=[self.session_id],
            count=1,
            status="pending"
        )
        self._data["candidates"].append(asdict(candidate))
        self._save()
        return candidate

    def should_suggest_promotion(self, candidate: Candidate) -> bool:
        """
        Check if candidate has reached promotion threshold.

        Args:
            candidate: The Candidate to check

        Returns:
            True if threshold reached
        """
        return candidate.count >= self.PROMOTION_THRESHOLD

    def promote(self, candidate_id: str, contexts: Optional[List[str]] = None) -> Optional[Memo]:
        """
        Promote a candidate to memo.

        Args:
            candidate_id: The candidate ID (or prefix)
            contexts: Optional override contexts for the memo

        Returns:
            The created Memo or None if candidate not found
        """
        for i, cand_data in enumerate(self._data["candidates"]):
            if cand_data["id"].startswith(candidate_id):
                # Create memo from candidate
                final_contexts = contexts if contexts is not None else cand_data.get("contexts", [])
                memo = Memo(
                    id=self._generate_id("m", cand_data["content"]),
                    content=cand_data["content"],
                    contexts=final_contexts,
                    source="promoted"
                )
                self._data["memos"].append(asdict(memo))

                # Remove candidate
                del self._data["candidates"][i]
                self._save()
                return memo
        return None

    def dismiss(self, candidate_id: str) -> bool:
        """
        Dismiss a candidate (won't suggest again).

        Args:
            candidate_id: The candidate ID (or prefix)

        Returns:
            True if dismissed, False if not found
        """
        for cand_data in self._data["candidates"]:
            if cand_data["id"].startswith(candidate_id):
                cand_data["status"] = "dismissed"
                self._save()
                return True
        return False

    def list_candidates(self, include_dismissed: bool = False) -> List[Candidate]:
        """
        List candidates.

        Args:
            include_dismissed: Whether to include dismissed candidates

        Returns:
            List of Candidate objects
        """
        candidates = []
        for cand_data in self._data["candidates"]:
            if include_dismissed or cand_data.get("status") != "dismissed":
                candidates.append(Candidate(**cand_data))
        return candidates

    def get_pending_suggestions(self) -> List[Candidate]:
        """
        Get candidates that have reached promotion threshold.

        Returns:
            List of candidates ready for promotion
        """
        return [
            c for c in self.list_candidates()
            if self.should_suggest_promotion(c)
        ]

    # -------------------------------------------------------------------------
    # Graph Integration
    # -------------------------------------------------------------------------

    def get_graph_nodes(self) -> List[Dict[str, Any]]:
        """
        Generate graph nodes for memos.

        Returns:
            List of node dicts suitable for graph projection
        """
        nodes = []
        for memo in self.list_memos():
            nodes.append({
                "id": memo.id,
                "type": "memo",
                "content": {
                    "instruction": memo.content,
                    "source": memo.source,
                    "use_count": memo.use_count
                },
                "event_id": memo.id  # Self-referencing for memos
            })
        return nodes

    def get_graph_edges(self) -> List[Dict[str, Any]]:
        """
        Generate graph edges for memo context relationships.

        Returns:
            List of edge dicts (memo --applies_to--> context)
        """
        edges = []
        for memo in self.list_memos():
            for context in memo.contexts:
                edges.append({
                    "source_id": memo.id,
                    "target_id": f"topic:{context}",  # Topic pseudo-node
                    "relation": "applies_to",
                    "event_id": memo.id
                })
        return edges

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def stats(self) -> Dict[str, int]:
        """
        Return memo statistics.

        Returns:
            Dict with counts
        """
        memos = self.list_memos()
        candidates = self.list_candidates()
        pending = self.get_pending_suggestions()
        init_memos = self.list_init_memos()

        return {
            "memos": len(memos),
            "init_memos": len(init_memos),
            "candidates": len(candidates),
            "pending_suggestions": len(pending),
            "with_contexts": sum(1 for m in memos if m.contexts),
            "total_uses": sum(m.use_count for m in memos)
        }
