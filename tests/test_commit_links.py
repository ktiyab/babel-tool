"""
Tests for CommitLinkStore — Decision ↔ Commit proof-of-implementation

Tests that proof-of-implementation is stored in Babel (not Git):
- Links are created and stored in .babel/shared/commit_links.json
- Links are append-only (HC1)
- Links persist and reload correctly
- Prefix matching works for both decision IDs and commit SHAs

Aligns with:
- HC1: Append-only (no deletion of links)
- P7: Reasoning travels (links in shared/, git-tracked)
- P5: Tests ARE evidence for the implementation
"""

import pytest
import json
from pathlib import Path

from babel.core.commit_links import CommitLink, CommitLinkStore


@pytest.fixture
def babel_dir(tmp_path):
    """Create a minimal .babel directory structure."""
    babel_dir = tmp_path / ".babel"
    babel_dir.mkdir()
    (babel_dir / "shared").mkdir()
    (babel_dir / "local").mkdir()
    return babel_dir


@pytest.fixture
def store(babel_dir):
    """Create a CommitLinkStore."""
    return CommitLinkStore(babel_dir)


# =============================================================================
# CommitLink Dataclass Tests
# =============================================================================

class TestCommitLink:
    """Test CommitLink dataclass."""

    def test_create_commit_link(self):
        """CommitLink can be created with required fields."""
        link = CommitLink(
            decision_id="abc12345",
            commit_sha="def67890abcdef",
            linked_at="2026-01-17T10:00:00+00:00",
            linked_by="user"
        )
        assert link.decision_id == "abc12345"
        assert link.commit_sha == "def67890abcdef"
        assert link.linked_by == "user"

    def test_to_dict(self):
        """CommitLink serializes to dict."""
        link = CommitLink(
            decision_id="abc12345",
            commit_sha="def67890",
            linked_at="2026-01-17T10:00:00+00:00",
            linked_by="claude"
        )
        d = link.to_dict()
        assert d["decision_id"] == "abc12345"
        assert d["commit_sha"] == "def67890"
        assert d["linked_by"] == "claude"

    def test_from_dict(self):
        """CommitLink deserializes from dict."""
        data = {
            "decision_id": "abc12345",
            "commit_sha": "def67890",
            "linked_at": "2026-01-17T10:00:00+00:00",
            "linked_by": "auto"
        }
        link = CommitLink.from_dict(data)
        assert link.decision_id == "abc12345"
        assert link.commit_sha == "def67890"
        assert link.linked_by == "auto"

    def test_from_dict_defaults(self):
        """CommitLink handles missing optional fields."""
        data = {
            "decision_id": "abc12345",
            "commit_sha": "def67890"
        }
        link = CommitLink.from_dict(data)
        assert link.decision_id == "abc12345"
        assert link.linked_by == "unknown"


# =============================================================================
# CommitLinkStore Initialization Tests
# =============================================================================

class TestCommitLinkStoreInit:
    """Test CommitLinkStore initialization."""

    def test_init_creates_empty_store(self, store):
        """New store starts empty."""
        assert store.count() == 0
        assert store.all_links() == []

    def test_store_path_in_shared(self, babel_dir, store):
        """Store path is in shared directory (P7: git-tracked)."""
        assert store.store_path == babel_dir / "shared" / "commit_links.json"

    def test_init_loads_existing_links(self, babel_dir):
        """Store loads existing links on init."""
        # Pre-populate the file
        store_path = babel_dir / "shared" / "commit_links.json"
        data = {
            "version": 1,
            "links": [
                {
                    "decision_id": "abc12345",
                    "commit_sha": "def67890",
                    "linked_at": "2026-01-17T10:00:00+00:00",
                    "linked_by": "user"
                }
            ]
        }
        store_path.write_text(json.dumps(data))

        # Create store - should load the link
        store = CommitLinkStore(babel_dir)
        assert store.count() == 1
        assert store.all_links()[0].decision_id == "abc12345"

    def test_init_handles_corrupted_file(self, babel_dir):
        """Store handles corrupted JSON gracefully."""
        store_path = babel_dir / "shared" / "commit_links.json"
        store_path.write_text("not valid json {{{")

        store = CommitLinkStore(babel_dir)
        assert store.count() == 0  # Graceful fallback to empty


# =============================================================================
# Add Links Tests (HC1: Append-Only)
# =============================================================================

class TestAddLinks:
    """Test adding links (append-only per HC1)."""

    def test_add_link(self, store):
        """Can add a link between decision and commit."""
        link = store.add("decision-1", "commit-abc123", linked_by="user")

        assert link.decision_id == "decision-1"
        assert link.commit_sha == "commit-abc123"
        assert link.linked_by == "user"
        assert store.count() == 1

    def test_add_multiple_links(self, store):
        """Can add multiple links."""
        store.add("decision-1", "commit-1")
        store.add("decision-2", "commit-2")
        store.add("decision-1", "commit-3")  # Same decision, different commit

        assert store.count() == 3

    def test_add_duplicate_returns_existing(self, store):
        """Adding duplicate link returns existing (no duplicate)."""
        link1 = store.add("decision-1", "commit-1")
        link2 = store.add("decision-1", "commit-1")

        assert store.count() == 1  # No duplicate
        assert link1.linked_at == link2.linked_at  # Same link returned

    def test_add_strips_whitespace(self, store):
        """IDs are normalized (stripped)."""
        store.add("  decision-1  ", "  commit-1  ")

        links = store.all_links()
        assert links[0].decision_id == "decision-1"
        assert links[0].commit_sha == "commit-1"


# =============================================================================
# Persistence Tests
# =============================================================================

class TestPersistence:
    """Test that links persist across store reloads."""

    def test_links_persist_to_file(self, babel_dir, store):
        """Links are saved to JSON file."""
        store.add("decision-1", "commit-1")

        # Verify file exists and contains link
        assert store.store_path.exists()
        data = json.loads(store.store_path.read_text())
        assert len(data["links"]) == 1
        assert data["links"][0]["decision_id"] == "decision-1"

    def test_links_survive_reload(self, babel_dir):
        """Links persist across store recreation."""
        # Create store and add links
        store1 = CommitLinkStore(babel_dir)
        store1.add("decision-1", "commit-1")
        store1.add("decision-2", "commit-2")

        # Create new store instance (simulates restart)
        store2 = CommitLinkStore(babel_dir)

        assert store2.count() == 2
        assert store2.get_link("decision-1", "commit-1") is not None


# =============================================================================
# Query By Commit Tests
# =============================================================================

class TestQueryByCommit:
    """Test querying decisions for a commit."""

    def test_get_decisions_for_commit(self, store):
        """Can find all decisions linked to a commit."""
        store.add("decision-1", "commit-abc")
        store.add("decision-2", "commit-abc")
        store.add("decision-3", "commit-xyz")

        results = store.get_decisions_for_commit("commit-abc")
        decision_ids = [r.decision_id for r in results]

        assert len(results) == 2
        assert "decision-1" in decision_ids
        assert "decision-2" in decision_ids
        assert "decision-3" not in decision_ids

    def test_get_decisions_prefix_match(self, store):
        """Commit SHA prefix matching works."""
        store.add("decision-1", "abc123def456")

        # Full match
        results = store.get_decisions_for_commit("abc123def456")
        assert len(results) == 1

        # Prefix match
        results = store.get_decisions_for_commit("abc123")
        assert len(results) == 1

    def test_get_decisions_no_match(self, store):
        """Returns empty list when no match."""
        store.add("decision-1", "commit-abc")

        results = store.get_decisions_for_commit("nonexistent")
        assert results == []


# =============================================================================
# Query By Decision Tests
# =============================================================================

class TestQueryByDecision:
    """Test querying commits for a decision."""

    def test_get_commits_for_decision(self, store):
        """Can find all commits linked to a decision."""
        store.add("decision-1", "commit-a")
        store.add("decision-1", "commit-b")
        store.add("decision-2", "commit-c")

        results = store.get_commits_for_decision("decision-1")
        commit_shas = [r.commit_sha for r in results]

        assert len(results) == 2
        assert "commit-a" in commit_shas
        assert "commit-b" in commit_shas
        assert "commit-c" not in commit_shas

    def test_get_commits_prefix_match(self, store):
        """Decision ID prefix matching works."""
        store.add("abc123def456", "commit-1")

        # Full match
        results = store.get_commits_for_decision("abc123def456")
        assert len(results) == 1

        # Prefix match (8-char typical)
        results = store.get_commits_for_decision("abc123de")
        assert len(results) == 1

    def test_get_commits_no_match(self, store):
        """Returns empty list when no match."""
        store.add("decision-1", "commit-abc")

        results = store.get_commits_for_decision("nonexistent")
        assert results == []


# =============================================================================
# Set Operations Tests
# =============================================================================

class TestSetOperations:
    """Test set operations for linked IDs."""

    def test_get_linked_decision_ids(self, store):
        """Can get set of all linked decision IDs."""
        store.add("decision-1", "commit-a")
        store.add("decision-1", "commit-b")
        store.add("decision-2", "commit-c")

        ids = store.get_linked_decision_ids()

        assert ids == {"decision-1", "decision-2"}

    def test_get_linked_commit_shas(self, store):
        """Can get set of all linked commit SHAs."""
        store.add("decision-1", "commit-a")
        store.add("decision-2", "commit-a")
        store.add("decision-3", "commit-b")

        shas = store.get_linked_commit_shas()

        assert shas == {"commit-a", "commit-b"}

    def test_empty_sets_when_no_links(self, store):
        """Empty sets when no links exist."""
        assert store.get_linked_decision_ids() == set()
        assert store.get_linked_commit_shas() == set()


# =============================================================================
# Proof-of-Implementation Semantics Tests
# =============================================================================

class TestProofSemantics:
    """Test that links serve as proof-of-implementation."""

    def test_link_is_proof_in_babel(self, babel_dir, store):
        """Proof of implementation is stored in Babel, not Git."""
        store.add("decision-xyz", "commit-abc")

        # The proof exists in .babel/shared/ (Babel territory)
        assert store.store_path.exists()
        assert ".babel/shared" in str(store.store_path)

        # Verify the proof contains the binding
        data = json.loads(store.store_path.read_text())
        link = data["links"][0]
        assert link["decision_id"] == "decision-xyz"
        assert link["commit_sha"] == "commit-abc"
        # The commit_sha is a REFERENCE to Git, but the proof is HERE in Babel

    def test_multiple_commits_strengthen_proof(self, store):
        """Multiple commits for one decision = stronger proof."""
        store.add("decision-1", "commit-a")
        store.add("decision-1", "commit-b")
        store.add("decision-1", "commit-c")

        results = store.get_commits_for_decision("decision-1")
        assert len(results) == 3  # 3 pieces of evidence

    def test_linked_at_timestamp_is_proof_time(self, store):
        """linked_at is when proof was created, not when code was written."""
        link = store.add("decision-1", "commit-from-last-week")

        # The linked_at is NOW (when we created proof), not when commit was made
        assert link.linked_at is not None
        assert "2026" in link.linked_at or "202" in link.linked_at  # Current year
