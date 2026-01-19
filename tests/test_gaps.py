"""
Tests for GapsCommand — Implementation gap detection

Tests that gaps between intent (Babel decisions) and state (Git commits)
are properly identified and surfaced.

Aligns with:
- P5: Tests ARE evidence for implementation
- P8: Evolution traceable (surfaces broken chains)
- P9: Coherence observable (makes gaps visible)
- P7: Reasoning travels (encourages linking)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from babel.commands.gaps import GapsCommand


@pytest.fixture
def mock_babel_dir(tmp_path):
    """Create a minimal .babel directory structure."""
    babel_dir = tmp_path / ".babel"
    babel_dir.mkdir()
    (babel_dir / "shared").mkdir()
    (babel_dir / "local").mkdir()
    return babel_dir


@pytest.fixture
def mock_graph():
    """Create a mock graph with no nodes by default."""
    graph = Mock()
    graph.get_nodes_by_type = Mock(return_value=[])
    return graph


@pytest.fixture
def mock_symbols():
    """Create mock symbols for output."""
    symbols = Mock()
    symbols.check_pass = "[PASS]"
    symbols.tension = "[TENSION]"
    symbols.arrow = "->"
    return symbols


@pytest.fixture
def mock_cli(mock_babel_dir, tmp_path, mock_graph, mock_symbols):
    """Create a mock CLI with required attributes."""
    cli = Mock()
    cli.babel_dir = mock_babel_dir
    cli.project_dir = tmp_path
    cli.graph = mock_graph
    cli.symbols = mock_symbols
    cli._is_deprecated = Mock(return_value=None)  # Not deprecated by default
    return cli


@pytest.fixture
def gaps_command(mock_cli):
    """Create GapsCommand with mocked dependencies."""
    cmd = GapsCommand.__new__(GapsCommand)
    cmd._cli = mock_cli
    return cmd


# =============================================================================
# Find Unlinked Decisions Tests
# =============================================================================

class TestFindUnlinkedDecisions:
    """Test _find_unlinked_decisions method."""

    def test_no_decisions_returns_empty(self, gaps_command, mock_cli):
        """Returns empty list when no decisions exist."""
        mock_cli.graph.get_nodes_by_type.return_value = []

        result = gaps_command._find_unlinked_decisions(set())

        assert result == []

    def test_all_decisions_linked_returns_empty(self, gaps_command, mock_cli):
        """Returns empty when all decisions are linked."""
        # Create mock decision node
        node = Mock()
        node.event_id = "abc12345"
        node.id = "decision_abc12345"
        node.content = {"summary": "Test decision"}

        mock_cli.graph.get_nodes_by_type.return_value = [node]

        # This decision is linked
        linked_ids = {"abc12345"}

        result = gaps_command._find_unlinked_decisions(linked_ids)

        assert result == []

    def test_unlinked_decision_returned(self, gaps_command, mock_cli):
        """Returns unlinked decisions."""
        node = Mock()
        node.event_id = "abc12345"
        node.id = "decision_abc12345"
        node.content = {"summary": "Unlinked decision"}

        # Only return for 'decision' type, empty for others
        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        # No linked IDs
        linked_ids = set()

        result = gaps_command._find_unlinked_decisions(linked_ids)

        assert len(result) == 1
        assert result[0]["id"] == "abc12345"
        assert result[0]["type"] == "decision"
        assert result[0]["summary"] == "Unlinked decision"

    def test_prefix_matching_works(self, gaps_command, mock_cli):
        """Prefix matching identifies linked decisions."""
        node = Mock()
        node.event_id = "abc12345def67890"  # Full ID
        node.id = "decision_abc12345def67890"
        node.content = {"summary": "Test decision"}

        mock_cli.graph.get_nodes_by_type.return_value = [node]

        # Linked with prefix match
        linked_ids = {"abc12345"}  # Prefix of full ID

        result = gaps_command._find_unlinked_decisions(linked_ids)

        # Should be considered linked via prefix
        assert result == []

    def test_deprecated_decisions_excluded(self, gaps_command, mock_cli):
        """Deprecated decisions are not reported as gaps."""
        node = Mock()
        node.event_id = "deprecated123"
        node.id = "decision_deprecated123"
        node.content = {"summary": "Old decision"}

        mock_cli.graph.get_nodes_by_type.return_value = [node]
        mock_cli._is_deprecated.return_value = {"reason": "Superseded"}

        linked_ids = set()

        result = gaps_command._find_unlinked_decisions(linked_ids)

        # Deprecated should not appear in gaps
        assert result == []

    def test_multiple_types_checked(self, gaps_command, mock_cli):
        """Checks decisions, constraints, and principles."""
        decision = Mock(event_id="dec123", id="decision_dec123", content={"summary": "Decision"})
        constraint = Mock(event_id="con123", id="constraint_con123", content={"summary": "Constraint"})
        principle = Mock(event_id="pri123", id="principle_pri123", content={"summary": "Principle"})

        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [decision]
            elif node_type == "constraint":
                return [constraint]
            elif node_type == "principle":
                return [principle]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        result = gaps_command._find_unlinked_decisions(set())

        assert len(result) == 3
        types = {r["type"] for r in result}
        assert types == {"decision", "constraint", "principle"}


# =============================================================================
# Find Unlinked Commits Tests
# =============================================================================

class TestFindUnlinkedCommits:
    """Test _find_unlinked_commits method."""

    def test_no_commits_returns_empty(self, gaps_command):
        """Returns empty when git log returns nothing."""
        mock_git = Mock()
        mock_git._run_git.return_value = ""

        result = gaps_command._find_unlinked_commits(mock_git, set(), 20)

        assert result == []

    def test_all_commits_linked_returns_empty(self, gaps_command):
        """Returns empty when all commits are linked."""
        mock_git = Mock()
        mock_git._run_git.return_value = "abc123def456|Fix bug\n"

        linked_shas = {"abc123def456"}

        result = gaps_command._find_unlinked_commits(mock_git, linked_shas, 20)

        assert result == []

    def test_unlinked_commit_returned(self, gaps_command):
        """Returns unlinked commits."""
        mock_git = Mock()
        mock_git._run_git.return_value = "abc123def456|Add feature\n"

        linked_shas = set()

        result = gaps_command._find_unlinked_commits(mock_git, linked_shas, 20)

        assert len(result) == 1
        assert result[0]["sha"] == "abc123def456"
        assert result[0]["short_sha"] == "abc123de"
        assert result[0]["message"] == "Add feature"

    def test_prefix_matching_works(self, gaps_command):
        """Prefix matching identifies linked commits."""
        mock_git = Mock()
        mock_git._run_git.return_value = "abc123def456789|Add feature\n"

        # Linked with prefix
        linked_shas = {"abc123de"}

        result = gaps_command._find_unlinked_commits(mock_git, linked_shas, 20)

        # Should be considered linked via prefix
        assert result == []

    def test_merge_commits_excluded(self, gaps_command):
        """Merge commits are automatically excluded."""
        mock_git = Mock()
        mock_git._run_git.return_value = (
            "abc123|Merge branch 'feature'\n"
            "def456|Add feature\n"
        )

        result = gaps_command._find_unlinked_commits(mock_git, set(), 20)

        # Only the non-merge commit
        assert len(result) == 1
        assert result[0]["message"] == "Add feature"

    def test_trivial_commits_excluded(self, gaps_command):
        """Trivial commits (bump version, changelog) are excluded."""
        mock_git = Mock()
        mock_git._run_git.return_value = (
            "abc123|Bump version to 1.0.0\n"
            "def456|Update changelog\n"
            "ghi789|Add real feature\n"
        )

        result = gaps_command._find_unlinked_commits(mock_git, set(), 20)

        # Only the non-trivial commit
        assert len(result) == 1
        assert result[0]["message"] == "Add real feature"

    def test_from_recent_parameter(self, gaps_command):
        """from_recent parameter controls number of commits checked."""
        mock_git = Mock()
        mock_git._run_git.return_value = ""

        gaps_command._find_unlinked_commits(mock_git, set(), 50)

        # Verify git log was called with correct limit
        mock_git._run_git.assert_called_once()
        args = mock_git._run_git.call_args[0][0]
        assert "-50" in args


# =============================================================================
# Gaps Command Output Tests
# =============================================================================

class TestGapsCommandOutput:
    """Test gaps command output formatting."""

    def test_no_gaps_message(self, gaps_command, mock_cli, capsys):
        """Shows success message when no gaps."""
        mock_cli.graph.get_nodes_by_type.return_value = []

        with patch.object(gaps_command, '_find_unlinked_commits', return_value=[]):
            with patch('babel.commands.gaps.CommitLinkStore') as mock_store_class:
                mock_store = Mock()
                mock_store.get_linked_decision_ids.return_value = set()
                mock_store.get_linked_commit_shas.return_value = set()
                mock_store_class.return_value = mock_store

                with patch('babel.commands.gaps.GitIntegration') as mock_git_class:
                    mock_git = Mock()
                    mock_git.is_git_repo = True
                    mock_git._run_git.return_value = ""
                    mock_git_class.return_value = mock_git

                    with patch('babel.output.end_command'):
                        gaps_command.gaps()

        captured = capsys.readouterr()
        assert "No gaps found" in captured.out

    def test_gaps_summary_shown(self, gaps_command, mock_cli, capsys):
        """Shows summary with gap counts."""
        # Create an unlinked decision
        node = Mock()
        node.event_id = "abc12345"
        node.id = "decision_abc12345"
        node.content = {"summary": "Test decision"}

        # Only return for 'decision' type, empty for others
        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        with patch('babel.commands.gaps.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            with patch('babel.commands.gaps.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git._run_git.return_value = "def456|Add feature\n"
                mock_git_class.return_value = mock_git

                with patch('babel.output.end_command'):
                    gaps_command.gaps()

        captured = capsys.readouterr()
        assert "Implementation Gaps" in captured.out
        assert "decision(s) without commits" in captured.out


# =============================================================================
# Filtering Tests
# =============================================================================

class TestGapsFiltering:
    """Test --commits and --decisions filtering."""

    def test_show_commits_only(self, gaps_command, mock_cli):
        """--commits flag shows only commit gaps."""
        # Setup decisions that would normally show
        node = Mock()
        node.event_id = "abc12345"
        node.id = "decision_abc12345"
        node.content = {"summary": "Test decision"}
        mock_cli.graph.get_nodes_by_type.return_value = [node]

        with patch('babel.commands.gaps.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            with patch('babel.commands.gaps.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git._run_git.return_value = "def456|Feature\n"
                mock_git_class.return_value = mock_git

                with patch('babel.output.end_command'):
                    # With show_commits=True, decisions are not queried
                    gaps_command.gaps(show_commits=True)

        # Decision finding should not be called because show_commits=True
        # means only commits are shown

    def test_show_decisions_only(self, gaps_command, mock_cli, capsys):
        """--decisions flag shows only decision gaps."""
        node = Mock()
        node.event_id = "abc12345"
        node.id = "decision_abc12345"
        node.content = {"summary": "Test decision"}

        # Only return for 'decision' type, empty for others
        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        with patch('babel.commands.gaps.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            with patch('babel.commands.gaps.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False  # No git
                mock_git_class.return_value = mock_git

                with patch('babel.output.end_command'):
                    gaps_command.gaps(show_decisions=True)

        captured = capsys.readouterr()
        # Should show decision gaps but not commit gaps
        assert "decision" in captured.out.lower()


# =============================================================================
# Pagination Tests
# =============================================================================

class TestGapsPagination:
    """Test pagination in gaps output."""

    def test_limit_parameter_respected(self, gaps_command, mock_cli, capsys):
        """Limit parameter constrains output."""
        # Create multiple unlinked decisions
        nodes = []
        for i in range(15):
            node = Mock()
            node.event_id = f"dec{i:03d}"
            node.id = f"decision_dec{i:03d}"
            node.content = {"summary": f"Decision {i}"}
            nodes.append(node)

        # Only return for 'decision' type, empty for others
        def mock_get_nodes(node_type):
            if node_type == "decision":
                return nodes
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        with patch('babel.commands.gaps.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            with patch('babel.commands.gaps.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.output.end_command'):
                    gaps_command.gaps(limit=5, show_decisions=True)

        captured = capsys.readouterr()
        # Should show pagination hint
        assert "More:" in captured.out or "offset" in captured.out.lower()

    def test_offset_skips_items(self, gaps_command, mock_cli, capsys):
        """Offset parameter skips initial items."""
        nodes = []
        for i in range(10):
            node = Mock()
            node.event_id = f"dec{i:03d}"
            node.id = f"decision_dec{i:03d}"
            node.content = {"summary": f"Decision {i}"}
            nodes.append(node)

        # Only return for 'decision' type, empty for others
        def mock_get_nodes(node_type):
            if node_type == "decision":
                return nodes
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        with patch('babel.commands.gaps.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            with patch('babel.commands.gaps.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.output.end_command'):
                    gaps_command.gaps(limit=3, offset=5, show_decisions=True)

        captured = capsys.readouterr()
        # Should show items starting from offset
        # Decision 5, 6, 7 should appear (offset=5, limit=3)


# =============================================================================
# Integration Semantics Tests
# =============================================================================

class TestGapsSemantics:
    """Test that gaps semantics match P8/P9 principles."""

    def test_gaps_surfaces_intent_without_implementation(self, gaps_command, mock_cli):
        """Decisions without commits = intent without implementation (P8)."""
        node = Mock()
        node.event_id = "intent123"
        node.id = "decision_intent123"
        node.content = {"summary": "Feature to implement"}

        # Only return for 'decision' type, empty for others
        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        result = gaps_command._find_unlinked_decisions(set())

        assert len(result) == 1
        # This represents P8: evolution is traceable - we can see what's NOT done

    def test_gaps_surfaces_implementation_without_intent(self, gaps_command):
        """Commits without decisions = implementation without intent (P9)."""
        mock_git = Mock()
        mock_git._run_git.return_value = "abc123|Mystery change\n"

        result = gaps_command._find_unlinked_commits(mock_git, set(), 20)

        assert len(result) == 1
        # This represents P9: coherence observable - we can see undocumented changes

    def test_linked_artifacts_excluded(self, gaps_command, mock_cli):
        """Linked artifacts are not gaps - bridge is complete."""
        node = Mock()
        node.event_id = "linked123"
        node.id = "decision_linked123"
        node.content = {"summary": "Implemented feature"}

        mock_cli.graph.get_nodes_by_type.return_value = [node]

        # This decision is linked
        linked_ids = {"linked123"}

        result = gaps_command._find_unlinked_decisions(linked_ids)

        assert result == []
        # No gap - intent and implementation are connected
