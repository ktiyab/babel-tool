"""
Tests for MemoManager — Coherence Evidence for memo persistence

These tests validate:
- Memo CRUD operations (add, remove, update, get, list)
- Candidate lifecycle (add, promote, dismiss)
- Context matching for relevant memo surfacing
- Threshold-based promotion suggestions
- Statistics reporting
- Graph integration (node/edge generation)
"""

import pytest
import json
from datetime import datetime, timezone

from babel.preferences import Memo, Candidate, MemoManager


@pytest.fixture
def temp_babel_dir(tmp_path):
    """Create temporary .babel directory."""
    babel_dir = tmp_path / ".babel"
    babel_dir.mkdir()
    return babel_dir


@pytest.fixture
def memo_manager(temp_babel_dir):
    """Create MemoManager with temporary storage."""
    return MemoManager(temp_babel_dir, session_id="test_session")


class TestMemo:
    """Tests for Memo dataclass."""

    def test_memo_defaults(self):
        """Memo has sensible defaults."""
        memo = Memo(id="m_test", content="test content")
        assert memo.id == "m_test"
        assert memo.content == "test content"
        assert memo.contexts == []
        assert memo.source == "manual"
        assert memo.use_count == 0
        assert memo.created != ""
        assert memo.updated != ""

    def test_memo_with_contexts(self):
        """Memo stores contexts."""
        memo = Memo(id="m_test", content="test", contexts=["bash", "testing"])
        assert memo.contexts == ["bash", "testing"]

    def test_memo_timestamps_auto_set(self):
        """Timestamps are auto-set on creation."""
        before = datetime.now(timezone.utc).isoformat()
        memo = Memo(id="m_test", content="test")
        after = datetime.now(timezone.utc).isoformat()

        assert before <= memo.created <= after
        assert memo.updated == memo.created


class TestCandidate:
    """Tests for Candidate dataclass."""

    def test_candidate_defaults(self):
        """Candidate has sensible defaults."""
        cand = Candidate(id="c_test", content="test pattern")
        assert cand.id == "c_test"
        assert cand.content == "test pattern"
        assert cand.contexts == []
        assert cand.sessions == []
        assert cand.count == 1
        assert cand.status == "pending"
        assert cand.first_seen != ""

    def test_candidate_with_sessions(self):
        """Candidate tracks sessions."""
        cand = Candidate(id="c_test", content="test", sessions=["s1", "s2"])
        assert cand.sessions == ["s1", "s2"]


class TestMemoManagerBasics:
    """Basic CRUD operations."""

    def test_add_memo(self, memo_manager):
        """Add creates memo with ID."""
        memo = memo_manager.add("Use python3")
        assert memo.id.startswith("m_")
        assert memo.content == "Use python3"
        assert memo.source == "manual"

    def test_add_memo_with_contexts(self, memo_manager):
        """Add memo with contexts."""
        memo = memo_manager.add("Use pytest", contexts=["testing", "python"])
        assert memo.contexts == ["testing", "python"]

    def test_get_memo(self, memo_manager):
        """Get memo by ID."""
        added = memo_manager.add("Test memo")
        retrieved = memo_manager.get(added.id)
        assert retrieved is not None
        assert retrieved.content == "Test memo"

    def test_get_memo_by_prefix(self, memo_manager):
        """Get memo by ID prefix."""
        added = memo_manager.add("Test memo")
        prefix = added.id[:4]
        retrieved = memo_manager.get(prefix)
        assert retrieved is not None
        assert retrieved.id == added.id

    def test_get_nonexistent_memo(self, memo_manager):
        """Get returns None for missing memo."""
        result = memo_manager.get("nonexistent")
        assert result is None

    def test_remove_memo(self, memo_manager):
        """Remove deletes memo."""
        added = memo_manager.add("To delete")
        assert memo_manager.remove(added.id) is True
        assert memo_manager.get(added.id) is None

    def test_remove_nonexistent(self, memo_manager):
        """Remove returns False for missing memo."""
        result = memo_manager.remove("nonexistent")
        assert result is False

    def test_update_memo_content(self, memo_manager):
        """Update changes memo content."""
        added = memo_manager.add("Original")
        updated = memo_manager.update(added.id, content="Updated")
        assert updated is not None
        assert updated.content == "Updated"

    def test_update_memo_contexts(self, memo_manager):
        """Update changes memo contexts."""
        added = memo_manager.add("Test", contexts=["old"])
        updated = memo_manager.update(added.id, contexts=["new1", "new2"])
        assert updated is not None
        assert updated.contexts == ["new1", "new2"]

    def test_update_nonexistent(self, memo_manager):
        """Update returns None for missing memo."""
        result = memo_manager.update("nonexistent", content="new")
        assert result is None

    def test_list_memos_empty(self, memo_manager):
        """List returns empty for new manager."""
        memos = memo_manager.list_memos()
        assert memos == []

    def test_list_memos(self, memo_manager):
        """List returns all memos."""
        memo_manager.add("First")
        memo_manager.add("Second")
        memos = memo_manager.list_memos()
        assert len(memos) == 2

    def test_increment_use(self, memo_manager):
        """Increment use updates count."""
        added = memo_manager.add("Test")
        assert added.use_count == 0

        memo_manager.increment_use(added.id)
        retrieved = memo_manager.get(added.id)
        assert retrieved.use_count == 1

        memo_manager.increment_use(added.id)
        retrieved = memo_manager.get(added.id)
        assert retrieved.use_count == 2


class TestMemoManagerContexts:
    """Context matching for relevant memo surfacing."""

    def test_get_relevant_empty_contexts(self, memo_manager):
        """Empty contexts returns empty list."""
        memo_manager.add("Test", contexts=["bash"])
        result = memo_manager.get_relevant([])
        assert result == []

    def test_get_relevant_matching(self, memo_manager):
        """Returns memos with matching contexts."""
        memo_manager.add("Bash memo", contexts=["bash"])
        memo_manager.add("Python memo", contexts=["python"])

        result = memo_manager.get_relevant(["bash"])
        assert len(result) == 1
        assert result[0].content == "Bash memo"

    def test_get_relevant_multiple_matches(self, memo_manager):
        """Returns all matching memos."""
        memo_manager.add("Bash only", contexts=["bash"])
        memo_manager.add("Both", contexts=["bash", "python"])

        result = memo_manager.get_relevant(["bash"])
        assert len(result) == 2

    def test_get_relevant_case_insensitive(self, memo_manager):
        """Context matching is case-insensitive."""
        memo_manager.add("Test", contexts=["Bash"])
        result = memo_manager.get_relevant(["bash"])
        assert len(result) == 1

    def test_get_relevant_global_memos(self, memo_manager):
        """Memos without contexts match everything."""
        memo_manager.add("Global memo", contexts=[])
        result = memo_manager.get_relevant(["anything"])
        assert len(result) == 1


class TestMemoManagerCandidates:
    """Candidate lifecycle (AI-detected patterns)."""

    def test_add_candidate(self, memo_manager):
        """Add candidate creates entry."""
        cand = memo_manager.add_candidate("use python3")
        assert cand.id.startswith("c_")
        assert cand.content == "use python3"
        assert cand.count == 1

    def test_add_candidate_increments_on_repeat(self, memo_manager):
        """Same content increments existing candidate."""
        memo_manager.add_candidate("use python3")

        # Simulate new session
        memo_manager.session_id = "session_2"
        cand = memo_manager.add_candidate("use python3")

        assert cand.count == 2
        assert len(cand.sessions) == 2

    def test_add_candidate_case_insensitive(self, memo_manager):
        """Candidate matching is case-insensitive."""
        memo_manager.add_candidate("Use Python3")

        memo_manager.session_id = "session_2"
        cand = memo_manager.add_candidate("use python3")

        assert cand.count == 2

    def test_add_candidate_with_contexts(self, memo_manager):
        """Candidate tracks contexts."""
        cand = memo_manager.add_candidate("test", contexts=["bash", "testing"])
        assert set(cand.contexts) == {"bash", "testing"}

    def test_add_candidate_merges_contexts(self, memo_manager):
        """Repeated candidate merges contexts."""
        memo_manager.add_candidate("test", contexts=["bash"])

        memo_manager.session_id = "session_2"
        cand = memo_manager.add_candidate("test", contexts=["python"])

        assert set(cand.contexts) == {"bash", "python"}

    def test_should_suggest_promotion(self, memo_manager):
        """Threshold triggers promotion suggestion."""
        cand = memo_manager.add_candidate("test")
        assert memo_manager.should_suggest_promotion(cand) is False

        memo_manager.session_id = "session_2"
        cand = memo_manager.add_candidate("test")
        assert memo_manager.should_suggest_promotion(cand) is True

    def test_promote_candidate(self, memo_manager):
        """Promote creates memo from candidate."""
        cand = memo_manager.add_candidate("test pattern", contexts=["bash"])
        memo = memo_manager.promote(cand.id)

        assert memo is not None
        assert memo.content == "test pattern"
        assert memo.contexts == ["bash"]
        assert memo.source == "promoted"

        # Candidate should be removed
        candidates = memo_manager.list_candidates()
        assert len(candidates) == 0

    def test_promote_with_override_contexts(self, memo_manager):
        """Promote can override contexts."""
        cand = memo_manager.add_candidate("test", contexts=["old"])
        memo = memo_manager.promote(cand.id, contexts=["new1", "new2"])

        assert memo.contexts == ["new1", "new2"]

    def test_promote_nonexistent(self, memo_manager):
        """Promote returns None for missing candidate."""
        result = memo_manager.promote("nonexistent")
        assert result is None

    def test_dismiss_candidate(self, memo_manager):
        """Dismiss marks candidate as dismissed."""
        cand = memo_manager.add_candidate("test")
        assert memo_manager.dismiss(cand.id) is True

        candidates = memo_manager.list_candidates(include_dismissed=False)
        assert len(candidates) == 0

        candidates = memo_manager.list_candidates(include_dismissed=True)
        assert len(candidates) == 1
        assert candidates[0].status == "dismissed"

    def test_list_candidates_excludes_dismissed(self, memo_manager):
        """List candidates excludes dismissed by default."""
        memo_manager.add_candidate("keep")
        dismissed = memo_manager.add_candidate("dismiss")
        memo_manager.dismiss(dismissed.id)

        candidates = memo_manager.list_candidates()
        assert len(candidates) == 1
        assert candidates[0].content == "keep"

    def test_get_pending_suggestions(self, memo_manager):
        """Get pending returns only threshold-reached candidates."""
        # Below threshold
        memo_manager.add_candidate("single")

        # At threshold
        memo_manager.add_candidate("double")
        memo_manager.session_id = "session_2"
        memo_manager.add_candidate("double")

        pending = memo_manager.get_pending_suggestions()
        assert len(pending) == 1
        assert pending[0].content == "double"


class TestMemoManagerPersistence:
    """Storage persistence tests."""

    def test_persistence_across_instances(self, temp_babel_dir):
        """Data persists across manager instances."""
        # Create and add
        manager1 = MemoManager(temp_babel_dir)
        manager1.add("Persistent memo")

        # New instance should see data
        manager2 = MemoManager(temp_babel_dir)
        memos = manager2.list_memos()
        assert len(memos) == 1
        assert memos[0].content == "Persistent memo"

    def test_storage_file_location(self, temp_babel_dir):
        """Storage file is in correct location."""
        manager = MemoManager(temp_babel_dir)
        manager.add("Test")

        storage_path = temp_babel_dir / "local" / "memos.json"
        assert storage_path.exists()

    def test_storage_file_format(self, temp_babel_dir):
        """Storage file is valid JSON."""
        manager = MemoManager(temp_babel_dir)
        manager.add("Test memo", contexts=["test"])
        manager.add_candidate("candidate")

        storage_path = temp_babel_dir / "local" / "memos.json"
        with open(storage_path) as f:
            data = json.load(f)

        assert "memos" in data
        assert "candidates" in data
        assert len(data["memos"]) == 1
        assert len(data["candidates"]) == 1


class TestMemoManagerGraphIntegration:
    """Graph node/edge generation."""

    def test_get_graph_nodes(self, memo_manager):
        """Generates nodes for memos."""
        memo_manager.add("Test memo")
        nodes = memo_manager.get_graph_nodes()

        assert len(nodes) == 1
        assert nodes[0]["type"] == "memo"
        assert nodes[0]["content"]["instruction"] == "Test memo"

    def test_get_graph_edges(self, memo_manager):
        """Generates edges for memo contexts."""
        memo_manager.add("Test", contexts=["bash", "python"])
        edges = memo_manager.get_graph_edges()

        assert len(edges) == 2
        assert all(e["relation"] == "applies_to" for e in edges)

        targets = {e["target_id"] for e in edges}
        assert "topic:bash" in targets
        assert "topic:python" in targets

    def test_get_graph_edges_empty_contexts(self, memo_manager):
        """No edges for memos without contexts."""
        memo_manager.add("Global memo", contexts=[])
        edges = memo_manager.get_graph_edges()
        assert len(edges) == 0


class TestMemoManagerStats:
    """Statistics reporting."""

    def test_stats_empty(self, memo_manager):
        """Stats for empty manager."""
        stats = memo_manager.stats()
        assert stats["memos"] == 0
        assert stats["candidates"] == 0
        assert stats["pending_suggestions"] == 0

    def test_stats_with_data(self, memo_manager):
        """Stats with memos and candidates."""
        memo_manager.add("With context", contexts=["test"])
        memo_manager.add("Without context")
        memo_manager.add_candidate("candidate")

        stats = memo_manager.stats()
        assert stats["memos"] == 2
        assert stats["with_contexts"] == 1
        assert stats["candidates"] == 1

    def test_stats_total_uses(self, memo_manager):
        """Stats tracks total uses."""
        m1 = memo_manager.add("Memo 1")
        m2 = memo_manager.add("Memo 2")

        memo_manager.increment_use(m1.id)
        memo_manager.increment_use(m1.id)
        memo_manager.increment_use(m2.id)

        stats = memo_manager.stats()
        assert stats["total_uses"] == 3
