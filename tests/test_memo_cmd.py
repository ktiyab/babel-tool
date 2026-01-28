"""
Tests for MemoCommand — HC2/P6 User Preference Management

Tests the memo operations:
- Adding/removing/updating memos
- Listing memos with filtering
- Managing AI-detected candidates
- Init memo promotion/demotion

Aligns with:
- P5: Tests ARE evidence for implementation
- P6: Token-efficient by default
- HC2: User controls all memo operations
- HC6: Clear, human-readable output
"""

import pytest
from unittest.mock import Mock, patch

from babel.commands.memo_cmd import MemoCommand
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def memo_command(babel_factory):
    """Create MemoCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # MemoCommand needs memos store
    cli.memos = Mock()
    cli.memos.add = Mock()
    cli.memos.get = Mock(return_value=None)
    cli.memos.remove = Mock(return_value=True)
    cli.memos.update = Mock()
    cli.memos.list_memos = Mock(return_value=[])
    cli.memos.list_init_memos = Mock(return_value=[])
    cli.memos.get_relevant = Mock(return_value=[])
    cli.memos.set_init = Mock()
    cli.memos.list_candidates = Mock(return_value=[])
    cli.memos.get_pending_suggestions = Mock(return_value=[])
    cli.memos.promote = Mock()
    cli.memos.dismiss = Mock(return_value=True)
    cli.memos.should_suggest_promotion = Mock(return_value=False)
    cli.memos.add_candidate = Mock()
    cli.memos.increment_use = Mock()
    cli.memos.stats = Mock(return_value={
        "memos": 0, "init_memos": 0, "with_contexts": 0,
        "total_uses": 0, "candidates": 0, "pending_suggestions": 0
    })

    # Create command instance
    cmd = MemoCommand.__new__(MemoCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Helper Classes
# =============================================================================

class MockMemo:
    """Mock memo object for testing."""
    def __init__(
        self,
        memo_id="m_123",
        content="Test memo",
        contexts=None,
        init=False,
        use_count=0,
        created="2026-01-28T10:00:00Z"
    ):
        self.id = memo_id
        self.content = content
        self.contexts = contexts or []
        self.init = init
        self.use_count = use_count
        self.created = created  # P12: Temporal attribution


class MockCandidate:
    """Mock candidate object for testing."""
    def __init__(
        self,
        cand_id="c_456",
        content="Repeated instruction",
        contexts=None,
        count=3,
        sessions=None,
        status="pending",
        first_seen="2026-01-28T10:00:00Z"
    ):
        self.id = cand_id
        self.content = content
        self.contexts = contexts or []
        self.count = count
        self.sessions = sessions or ["session1", "session2"]
        self.status = status
        self.first_seen = first_seen  # P12: Temporal attribution


# =============================================================================
# Add Memo Tests
# =============================================================================

class TestAddMemo:
    """Test add method for creating memos."""

    def test_adds_memo_successfully(self, memo_command, capsys):
        """Adds a memo successfully."""
        cmd, factory = memo_command

        mock_memo = MockMemo(content="Always use pytest")
        cmd._cli.memos.add.return_value = mock_memo

        with patch('babel.output.end_command'):
            cmd.add("Always use pytest")

        captured = capsys.readouterr()
        assert "Memo saved" in captured.out
        assert "Always use pytest" in captured.out

    def test_adds_memo_with_contexts(self, memo_command, capsys):
        """Adds memo with contexts."""
        cmd, factory = memo_command

        mock_memo = MockMemo(content="Use pytest", contexts=["testing", "python"])
        cmd._cli.memos.add.return_value = mock_memo

        with patch('babel.output.end_command'):
            cmd.add("Use pytest", contexts=["testing", "python"])

        captured = capsys.readouterr()
        assert "testing" in captured.out
        cmd._cli.memos.add.assert_called_with("Use pytest", ["testing", "python"], init=False)

    def test_adds_init_memo(self, memo_command, capsys):
        """Adds init memo (foundational instruction)."""
        cmd, factory = memo_command

        mock_memo = MockMemo(content="Critical rule", init=True)
        cmd._cli.memos.add.return_value = mock_memo

        with patch('babel.output.end_command'):
            cmd.add("Critical rule", init=True)

        captured = capsys.readouterr()
        assert "INIT" in captured.out
        assert "session start" in captured.out.lower()

    def test_shows_global_when_no_contexts(self, memo_command, capsys):
        """Shows 'global' when no contexts specified."""
        cmd, factory = memo_command

        mock_memo = MockMemo(content="Global memo", contexts=[])
        cmd._cli.memos.add.return_value = mock_memo

        with patch('babel.output.end_command'):
            cmd.add("Global memo")

        captured = capsys.readouterr()
        assert "global" in captured.out.lower()


# =============================================================================
# Remove Memo Tests
# =============================================================================

class TestRemoveMemo:
    """Test remove method for deleting memos."""

    def test_removes_memo_successfully(self, memo_command, capsys):
        """Removes memo successfully."""
        cmd, factory = memo_command

        mock_memo = MockMemo(memo_id="m_remove", content="To be removed")
        cmd._cli.memos.get.return_value = mock_memo
        cmd._cli.memos.remove.return_value = True

        with patch('babel.output.end_command'):
            cmd.remove("m_remove")

        captured = capsys.readouterr()
        assert "Memo removed" in captured.out

    def test_shows_not_found(self, memo_command, capsys):
        """Shows error when memo not found."""
        cmd, factory = memo_command
        cmd._cli.memos.get.return_value = None

        cmd.remove("nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_shows_failure_message(self, memo_command, capsys):
        """Shows failure message when remove fails."""
        cmd, factory = memo_command

        mock_memo = MockMemo()
        cmd._cli.memos.get.return_value = mock_memo
        cmd._cli.memos.remove.return_value = False

        cmd.remove("m_123")

        captured = capsys.readouterr()
        assert "Failed" in captured.out


# =============================================================================
# Update Memo Tests
# =============================================================================

class TestUpdateMemo:
    """Test update method for modifying memos."""

    def test_updates_memo_content(self, memo_command, capsys):
        """Updates memo content."""
        cmd, factory = memo_command

        updated_memo = MockMemo(content="Updated content")
        cmd._cli.memos.update.return_value = updated_memo

        cmd.update("m_123", content="Updated content")

        captured = capsys.readouterr()
        assert "Memo updated" in captured.out
        assert "Updated content" in captured.out

    def test_updates_memo_contexts(self, memo_command, capsys):
        """Updates memo contexts."""
        cmd, factory = memo_command

        updated_memo = MockMemo(content="Test", contexts=["new_context"])
        cmd._cli.memos.update.return_value = updated_memo

        cmd.update("m_123", contexts=["new_context"])

        captured = capsys.readouterr()
        assert "Memo updated" in captured.out
        assert "new_context" in captured.out

    def test_shows_nothing_to_update(self, memo_command, capsys):
        """Shows message when nothing provided to update."""
        cmd, factory = memo_command

        cmd.update("m_123")

        captured = capsys.readouterr()
        assert "Nothing to update" in captured.out

    def test_shows_not_found_on_update(self, memo_command, capsys):
        """Shows not found when memo doesn't exist."""
        cmd, factory = memo_command
        cmd._cli.memos.update.return_value = None

        cmd.update("nonexistent", content="New content")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()


# =============================================================================
# List Memos Tests
# =============================================================================

class TestListMemos:
    """Test list_memos method."""

    def test_shows_no_memos_message(self, memo_command, capsys):
        """Shows message when no memos saved."""
        cmd, factory = memo_command
        cmd._cli.memos.list_memos.return_value = []

        cmd.list_memos()

        captured = capsys.readouterr()
        assert "No memos saved" in captured.out

    def test_lists_all_memos(self, memo_command, capsys):
        """Lists all saved memos."""
        cmd, factory = memo_command

        memos = [
            MockMemo("m_1", "First memo", use_count=5),
            MockMemo("m_2", "Second memo", contexts=["testing"]),
        ]
        cmd._cli.memos.list_memos.return_value = memos

        with patch('babel.output.end_command'):
            cmd.list_memos()

        captured = capsys.readouterr()
        assert "All Memos" in captured.out
        assert "First memo" in captured.out
        assert "Second memo" in captured.out

    def test_filters_by_context(self, memo_command, capsys):
        """Filters memos by context."""
        cmd, factory = memo_command

        memos = [MockMemo("m_1", "Testing memo", contexts=["testing"])]
        cmd._cli.memos.get_relevant.return_value = memos

        with patch('babel.output.end_command'):
            cmd.list_memos(context="testing")

        captured = capsys.readouterr()
        assert "testing" in captured.out.lower()

    def test_lists_init_memos_only(self, memo_command, capsys):
        """Lists only init memos."""
        cmd, factory = memo_command

        init_memos = [MockMemo("m_init", "Init instruction", init=True)]
        cmd._cli.memos.list_init_memos.return_value = init_memos

        with patch('babel.output.end_command'):
            cmd.list_memos(init_only=True)

        captured = capsys.readouterr()
        assert "Init Memos" in captured.out

    def test_shows_use_count(self, memo_command, capsys):
        """Shows memo use count."""
        cmd, factory = memo_command

        memos = [MockMemo("m_1", "Used memo", use_count=10)]
        cmd._cli.memos.list_memos.return_value = memos

        with patch('babel.output.end_command'):
            cmd.list_memos()

        captured = capsys.readouterr()
        assert "10" in captured.out


# =============================================================================
# Set Init Tests
# =============================================================================

class TestSetInit:
    """Test set_init method for init memo promotion/demotion."""

    def test_promotes_to_init(self, memo_command, capsys):
        """Promotes memo to init status."""
        cmd, factory = memo_command

        mock_memo = MockMemo(init=False)
        cmd._cli.memos.get.return_value = mock_memo

        updated = MockMemo(init=True)
        cmd._cli.memos.set_init.return_value = updated

        cmd.set_init("m_123", is_init=True)

        captured = capsys.readouterr()
        assert "promoted to init" in captured.out.lower()
        assert "session start" in captured.out.lower()

    def test_demotes_from_init(self, memo_command, capsys):
        """Demotes memo from init status."""
        cmd, factory = memo_command

        mock_memo = MockMemo(init=True)
        cmd._cli.memos.get.return_value = mock_memo

        updated = MockMemo(init=False)
        cmd._cli.memos.set_init.return_value = updated

        cmd.set_init("m_123", is_init=False)

        captured = capsys.readouterr()
        assert "demoted" in captured.out.lower()

    def test_shows_not_found(self, memo_command, capsys):
        """Shows not found when memo doesn't exist."""
        cmd, factory = memo_command
        cmd._cli.memos.get.return_value = None

        cmd.set_init("nonexistent", is_init=True)

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()


# =============================================================================
# Candidate Management Tests
# =============================================================================

class TestCandidateManagement:
    """Test candidate-related methods."""

    def test_shows_no_candidates(self, memo_command, capsys):
        """Shows message when no candidates detected."""
        cmd, factory = memo_command
        cmd._cli.memos.list_candidates.return_value = []

        cmd.candidates()

        captured = capsys.readouterr()
        assert "No candidates detected" in captured.out

    def test_lists_candidates(self, memo_command, capsys):
        """Lists detected candidates."""
        cmd, factory = memo_command

        candidates = [
            MockCandidate("c_1", "Repeated pattern", count=5),
        ]
        cmd._cli.memos.list_candidates.return_value = candidates
        cmd._cli.memos.get_pending_suggestions.return_value = candidates

        cmd.candidates()

        captured = capsys.readouterr()
        assert "Repeated pattern" in captured.out
        assert "5" in captured.out

    def test_promotes_candidate(self, memo_command, capsys):
        """Promotes candidate to memo."""
        cmd, factory = memo_command

        candidate = MockCandidate("c_promote", "Promoted pattern")
        cmd._cli.memos.list_candidates.return_value = [candidate]
        cmd._cli.resolve_id = Mock(return_value="c_promote")

        promoted_memo = MockMemo("m_new", "Promoted pattern")
        cmd._cli.memos.promote.return_value = promoted_memo

        with patch('babel.output.end_command'):
            cmd.promote("c_promote")

        captured = capsys.readouterr()
        assert "Promoted to memo" in captured.out

    def test_shows_candidate_not_found(self, memo_command, capsys):
        """Shows error when candidate not found."""
        cmd, factory = memo_command
        cmd._cli.memos.list_candidates.return_value = []
        cmd._cli.resolve_id = Mock(return_value=None)

        cmd.promote("nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_dismisses_candidate(self, memo_command, capsys):
        """Dismisses a candidate."""
        cmd, factory = memo_command
        cmd._cli.memos.dismiss.return_value = True

        with patch('babel.output.end_command'):
            cmd.dismiss("c_123")

        captured = capsys.readouterr()
        assert "Candidate dismissed" in captured.out

    def test_shows_dismiss_not_found(self, memo_command, capsys):
        """Shows error when candidate to dismiss not found."""
        cmd, factory = memo_command
        cmd._cli.memos.dismiss.return_value = False

        cmd.dismiss("nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()


# =============================================================================
# Stats Tests
# =============================================================================

class TestStats:
    """Test stats method."""

    def test_shows_statistics(self, memo_command, capsys):
        """Shows memo statistics."""
        cmd, factory = memo_command
        cmd._cli.memos.stats.return_value = {
            "memos": 10,
            "init_memos": 2,
            "with_contexts": 5,
            "total_uses": 50,
            "candidates": 3,
            "pending_suggestions": 1
        }

        cmd.stats()

        captured = capsys.readouterr()
        assert "Memo Statistics" in captured.out
        assert "10" in captured.out
        assert "2" in captured.out


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_unicode_in_content(self, memo_command, capsys):
        """Handles Unicode in memo content."""
        cmd, factory = memo_command

        mock_memo = MockMemo(content="Memo with 日本語 and 🎉")
        cmd._cli.memos.add.return_value = mock_memo

        with patch('babel.output.end_command'):
            cmd.add("Memo with 日本語 and 🎉")

        # Should not crash
        captured = capsys.readouterr()
        assert "Memo saved" in captured.out

    def test_handles_very_long_content(self, memo_command, capsys):
        """Handles very long memo content."""
        cmd, factory = memo_command

        long_content = "A" * 500
        mock_memo = MockMemo(content=long_content)
        cmd._cli.memos.add.return_value = mock_memo

        with patch('babel.output.end_command'):
            cmd.add(long_content)

        # Should not crash, content may be truncated
        captured = capsys.readouterr()
        assert "Memo saved" in captured.out

    def test_handles_empty_contexts_list(self, memo_command, capsys):
        """Handles empty contexts list."""
        cmd, factory = memo_command

        mock_memo = MockMemo(content="Test", contexts=[])
        cmd._cli.memos.add.return_value = mock_memo

        with patch('babel.output.end_command'):
            cmd.add("Test", contexts=[])

        captured = capsys.readouterr()
        assert "global" in captured.out.lower()

    def test_show_relevant_silent_when_none(self, memo_command, capsys):
        """show_relevant is silent when no relevant memos."""
        cmd, factory = memo_command
        cmd._cli.memos.get_relevant.return_value = []

        cmd.show_relevant(["testing"])

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_show_relevant_displays_memos(self, memo_command, capsys):
        """show_relevant displays relevant memos."""
        cmd, factory = memo_command

        memos = [MockMemo("m_1", "Relevant memo")]
        cmd._cli.memos.get_relevant.return_value = memos

        cmd.show_relevant(["testing"])

        captured = capsys.readouterr()
        assert "Active memos" in captured.out
        assert "Relevant memo" in captured.out
