"""
CommitLinkStore — Decision ↔ Commit bidirectional linking

The minimal bridge between intent (Babel) and state (Git).
Enables:
- babel why --commit (what decisions led to this commit?)
- babel gaps (what decisions aren't implemented?)
- babel status --git (sync health)

Storage: .babel/shared/commit_links.json (git-tracked, team-visible)

Aligns with:
- HC1: Append-only (no deletion of links)
- P7: Reasoning travels (links shared via git)
- P8: Evolution traceable (completes intent→state chain)
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class CommitLink:
    """A link between a Babel decision and a Git commit."""
    decision_id: str      # Babel artifact ID (8-char prefix or full)
    commit_sha: str       # Git commit SHA (full or abbreviated)
    linked_at: str        # ISO timestamp
    linked_by: str        # Who created the link (user, claude, auto)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CommitLink':
        return cls(
            decision_id=data['decision_id'],
            commit_sha=data['commit_sha'],
            linked_at=data.get('linked_at', datetime.now(timezone.utc).isoformat()),
            linked_by=data.get('linked_by', 'unknown')
        )


class CommitLinkStore:
    """
    Storage for Decision ↔ Commit links.

    Simple JSON file in shared directory (git-tracked).
    Append-only semantics (HC1 alignment).
    """

    def __init__(self, babel_dir: Path):
        """
        Initialize commit link store.

        Args:
            babel_dir: Path to .babel directory
        """
        self.babel_dir = babel_dir
        self.shared_dir = babel_dir / "shared"
        self.store_path = self.shared_dir / "commit_links.json"
        self._links: List[CommitLink] = []
        self._load()

    def _load(self):
        """Load links from disk."""
        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text())
                self._links = [CommitLink.from_dict(link) for link in data.get('links', [])]
            except (json.JSONDecodeError, KeyError):
                self._links = []
        else:
            self._links = []

    def _save(self):
        """Save links to disk."""
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        data = {
            'version': 1,
            'links': [link.to_dict() for link in self._links]
        }
        self.store_path.write_text(json.dumps(data, indent=2))

    def add(self, decision_id: str, commit_sha: str, linked_by: str = "user") -> CommitLink:
        """
        Add a new link between decision and commit.

        Args:
            decision_id: Babel artifact ID
            commit_sha: Git commit SHA
            linked_by: Who created the link

        Returns:
            The created CommitLink
        """
        # Normalize IDs
        decision_id = decision_id.strip()
        commit_sha = commit_sha.strip()

        # Check for duplicate
        existing = self.get_link(decision_id, commit_sha)
        if existing:
            return existing

        link = CommitLink(
            decision_id=decision_id,
            commit_sha=commit_sha,
            linked_at=datetime.now(timezone.utc).isoformat(),
            linked_by=linked_by
        )

        self._links.append(link)
        self._save()

        return link

    def get_link(self, decision_id: str, commit_sha: str) -> Optional[CommitLink]:
        """Get existing link if it exists."""
        for link in self._links:
            if link.decision_id == decision_id and link.commit_sha == commit_sha:
                return link
        return None

    def get_decisions_for_commit(self, commit_sha: str) -> List[CommitLink]:
        """
        Get all decisions linked to a commit.

        Supports both full SHA and prefix matching.
        """
        results = []
        for link in self._links:
            if link.commit_sha == commit_sha or link.commit_sha.startswith(commit_sha) or commit_sha.startswith(link.commit_sha):
                results.append(link)
        return results

    def get_commits_for_decision(self, decision_id: str) -> List[CommitLink]:
        """
        Get all commits linked to a decision.

        Supports both full ID and prefix matching.
        """
        results = []
        for link in self._links:
            if link.decision_id == decision_id or link.decision_id.startswith(decision_id) or decision_id.startswith(link.decision_id):
                results.append(link)
        return results

    def get_linked_decision_ids(self) -> Set[str]:
        """Get set of all decision IDs that have commit links."""
        return {link.decision_id for link in self._links}

    def get_linked_commit_shas(self) -> Set[str]:
        """Get set of all commit SHAs that have decision links."""
        return {link.commit_sha for link in self._links}

    def all_links(self) -> List[CommitLink]:
        """Get all links."""
        return list(self._links)

    def count(self) -> int:
        """Get total number of links."""
        return len(self._links)
