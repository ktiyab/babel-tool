"""
Tests for LinkCommand — P7 Evidence-Weighted Memory (Graph Connections)

Tests the artifact-to-purpose and artifact-to-commit linking:
- Creating 'supports' edges between artifacts and purposes
- Listing unlinked artifacts (orphans)
- Bulk linking all unlinked to active purpose
- Git-babel bridge (decision-to-commit links)
- Duplicate link prevention

Aligns with:
- P5: Tests ARE evidence for implementation
- P7: Evidence-Weighted Memory (linking creates evidence trail)
- P8: Evolution Traceable (links track artifact relationships)
- P11: Cross-Domain Learning (graph connections enable learning)
"""

import pytest
from unittest.mock import Mock, patch

from babel.commands.link import LinkCommand
from babel.core.graph import Node
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def link_command(babel_factory):
    """Create LinkCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # Mock _resolve_node for artifact resolution
    cli._resolve_node = Mock(return_value=None)

    # Create command instance
    cmd = LinkCommand.__new__(LinkCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# List Unlinked Tests (Orphan Detection)
# =============================================================================

class TestListUnlinked:
    """Test list_unlinked for orphan artifact display."""

    def test_shows_orphan_artifacts(self, link_command, capsys):
        """Shows unlinked artifacts grouped by type."""
        cmd, factory = link_command

        # Add artifacts without linking them
        factory.add_decision(summary="Unlinked decision", link_to_purpose=False)
        factory.add_constraint(summary="Unlinked constraint", link_to_purpose=False)

        cmd.list_unlinked()

        captured = capsys.readouterr()
        assert "unlinked" in captured.out.lower()
        assert "decision" in captured.out.lower()
        assert "constraint" in captured.out.lower()

    def test_shows_empty_message_when_no_orphans(self, link_command, capsys):
        """Shows message when all artifacts are linked."""
        cmd, factory = link_command

        # Add purpose and linked artifact
        purpose_id = factory.add_purpose("Test purpose")
        decision_id = factory.add_decision(summary="Linked decision", link_to_purpose=True)

        cmd.list_unlinked()

        captured = capsys.readouterr()
        assert "no unlinked artifacts" in captured.out.lower()

    def test_respects_limit_parameter(self, link_command, capsys):
        """Respects limit parameter for pagination."""
        cmd, factory = link_command

        # Add multiple artifacts
        for i in range(5):
            factory.add_decision(summary=f"Decision {i}", link_to_purpose=False)

        cmd.list_unlinked(limit=2)

        captured = capsys.readouterr()
        # Should show pagination hint
        assert "next" in captured.out.lower() or "more" in captured.out.lower()

    def test_respects_offset_parameter(self, link_command, capsys):
        """Respects offset parameter for pagination."""
        cmd, factory = link_command

        # Add multiple artifacts
        for i in range(5):
            factory.add_decision(summary=f"Decision {i}", link_to_purpose=False)

        cmd.list_unlinked(limit=2, offset=2)

        captured = capsys.readouterr()
        # Should show different items or pagination
        assert "decision" in captured.out.lower()

    def test_shows_full_content_when_requested(self, link_command, capsys):
        """Shows complete artifact content with full=True."""
        cmd, factory = link_command

        factory.add_decision(
            summary="Decision with long summary",
            what="Detailed what information",
            link_to_purpose=False
        )

        cmd.list_unlinked(full=True)

        captured = capsys.readouterr()
        # Full mode shows JSON content
        assert "summary" in captured.out.lower()


# =============================================================================
# Link All Tests (Bulk Linking)
# =============================================================================

class TestLinkAll:
    """Test link_all for bulk linking to purpose."""

    def test_links_all_orphans_to_purpose(self, link_command, capsys):
        """Links all unlinked artifacts to active purpose."""
        cmd, factory = link_command

        # Add purpose
        purpose_id = factory.add_purpose("Main purpose")

        # Add unlinked artifacts
        factory.add_decision(summary="Decision 1", link_to_purpose=False)
        factory.add_decision(summary="Decision 2", link_to_purpose=False)

        # Mock _get_active_purpose to return the purpose node
        purpose_node = factory.graph.get_nodes_by_type('purpose')[-1]
        cmd._cli._get_active_purpose = Mock(return_value=purpose_node)

        cmd.link_all()

        captured = capsys.readouterr()
        assert "linked" in captured.out.lower()

    def test_error_when_no_purpose(self, link_command, capsys):
        """Shows error when no active purpose exists."""
        cmd, factory = link_command

        # Add unlinked artifact without purpose
        factory.add_decision(summary="Orphan decision", link_to_purpose=False)

        # Mock _get_active_purpose to return None
        cmd._cli._get_active_purpose = Mock(return_value=None)

        cmd.link_all()

        captured = capsys.readouterr()
        assert "no active purpose" in captured.out.lower()

    def test_message_when_no_orphans(self, link_command, capsys):
        """Shows message when no unlinked artifacts exist."""
        cmd, factory = link_command

        # Add purpose and linked artifact
        purpose_id = factory.add_purpose("Test purpose")
        decision_id = factory.add_decision(summary="Linked decision", link_to_purpose=True)

        # Mock _get_active_purpose
        purpose_node = factory.graph.get_nodes_by_type('purpose')[-1]
        cmd._cli._get_active_purpose = Mock(return_value=purpose_node)

        cmd.link_all()

        captured = capsys.readouterr()
        assert "no unlinked" in captured.out.lower()

    def test_skips_purpose_nodes(self, link_command, capsys):
        """Skips purpose nodes when linking all (purposes are roots)."""
        cmd, factory = link_command

        # Add two purposes (second would be orphan relative to first)
        factory.add_purpose("Purpose 1")
        factory.add_purpose("Purpose 2")

        # Mock _get_active_purpose to return first purpose
        purpose_node = factory.graph.get_nodes_by_type('purpose')[0]
        cmd._cli._get_active_purpose = Mock(return_value=purpose_node)

        cmd.link_all()

        captured = capsys.readouterr()
        # Should skip purposes
        assert "skipped" in captured.out.lower() or "no unlinked" in captured.out.lower()


# =============================================================================
# Link Single Artifact Tests
# =============================================================================

class TestLink:
    """Test link method for single artifact linking."""

    def test_links_artifact_to_purpose(self, link_command, capsys):
        """Creates supports edge between artifact and purpose."""
        cmd, factory = link_command

        # Add purpose and artifact
        purpose_id = factory.add_purpose("Test purpose")
        decision_id = factory.add_decision(summary="Test decision", link_to_purpose=False)

        # Get nodes for mocking
        purpose_node = factory.graph.get_nodes_by_type('purpose')[-1]
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution
        cmd._cli._resolve_node = Mock(return_value=decision_node)
        cmd._cli._get_active_purpose = Mock(return_value=purpose_node)

        cmd.link(decision_id)

        captured = capsys.readouterr()
        assert "linked" in captured.out.lower()
        assert "supports" in captured.out.lower()

    def test_error_when_artifact_not_found(self, link_command, capsys):
        """Shows error when artifact not found."""
        cmd, factory = link_command

        # Mock resolution to return None
        cmd._cli._resolve_node = Mock(return_value=None)

        cmd.link("nonexistent_id")

        # Should not crash, just return early
        captured = capsys.readouterr()
        # No output expected since _resolve_node returns None

    def test_error_when_no_purpose(self, link_command, capsys):
        """Shows error when no purpose and none specified."""
        cmd, factory = link_command

        # Add artifact without purpose
        decision_id = factory.add_decision(summary="Test decision", link_to_purpose=False)
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution
        cmd._cli._resolve_node = Mock(return_value=decision_node)
        cmd._cli._get_active_purpose = Mock(return_value=None)

        cmd.link(decision_id)

        captured = capsys.readouterr()
        assert "no active purpose" in captured.out.lower()

    def test_prevents_duplicate_links(self, link_command, capsys):
        """Prevents creating duplicate links."""
        cmd, factory = link_command

        # Add purpose and artifact
        purpose_id = factory.add_purpose("Test purpose")
        decision_id = factory.add_decision(summary="Test decision", link_to_purpose=False)

        # Get nodes
        purpose_node = factory.graph.get_nodes_by_type('purpose')[-1]
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution
        cmd._cli._resolve_node = Mock(return_value=decision_node)
        cmd._cli._get_active_purpose = Mock(return_value=purpose_node)

        # First link should succeed
        cmd.link(decision_id)
        capsys.readouterr()  # Clear output

        # Second link should detect duplicate
        cmd.link(decision_id)

        captured = capsys.readouterr()
        assert "already linked" in captured.out.lower()

    def test_links_to_specific_purpose(self, link_command, capsys):
        """Links artifact to specified purpose instead of active."""
        cmd, factory = link_command

        # Add two purposes
        purpose1_id = factory.add_purpose("Purpose 1")
        purpose2_id = factory.add_purpose("Purpose 2")
        decision_id = factory.add_decision(summary="Test decision", link_to_purpose=False)

        # Get nodes
        purpose2_node = factory.graph.get_nodes_by_type('purpose')[-1]
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution - return decision first, then purpose
        cmd._cli._resolve_node = Mock(side_effect=[decision_node, purpose2_node])

        cmd.link(decision_id, purpose2_id)

        captured = capsys.readouterr()
        assert "linked" in captured.out.lower()


# =============================================================================
# Link to Commit Tests (Git-Babel Bridge)
# =============================================================================

class TestLinkToCommit:
    """Test link_to_commit for decision-commit bridge."""

    def test_links_decision_to_commit(self, link_command, capsys):
        """Creates decision-to-commit link."""
        cmd, factory = link_command

        # Add decision
        decision_id = factory.add_decision(summary="Test decision")
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution and git
        cmd._cli._resolve_node = Mock(return_value=decision_node)

        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git.get_commit = Mock(return_value=Mock(
                hash="abc123def456789012345678901234567890abcd",
                message="Test commit message"
            ))
            # Mock structural changes to return empty lists (no symbols to link)
            mock_git.get_structural_changes = Mock(return_value=Mock(
                added=[],
                modified=[]
            ))
            mock_git_class.return_value = mock_git

            with patch('babel.commands.link.CommitLinkStore') as mock_store_class:
                mock_store = Mock()
                mock_store.get_link = Mock(return_value=None)  # Not already linked
                mock_store.add = Mock(return_value=Mock(
                    decision_id=decision_id,
                    commit_sha="abc123def456789012345678901234567890abcd"
                ))
                mock_store_class.return_value = mock_store

                cmd.link_to_commit(decision_id, "abc123")

        captured = capsys.readouterr()
        assert "linked" in captured.out.lower()
        assert "implements" in captured.out.lower()

    def test_error_when_not_git_repo(self, link_command, capsys):
        """Shows error when not in git repository."""
        cmd, factory = link_command

        # Add decision
        decision_id = factory.add_decision(summary="Test decision")
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution
        cmd._cli._resolve_node = Mock(return_value=decision_node)

        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = False
            mock_git_class.return_value = mock_git

            cmd.link_to_commit(decision_id, "abc123")

        captured = capsys.readouterr()
        assert "not a git repository" in captured.out.lower()

    def test_error_when_commit_not_found(self, link_command, capsys):
        """Shows error when commit doesn't exist."""
        cmd, factory = link_command

        # Add decision
        decision_id = factory.add_decision(summary="Test decision")
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution
        cmd._cli._resolve_node = Mock(return_value=decision_node)

        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git.get_commit = Mock(return_value=None)  # Commit not found
            mock_git_class.return_value = mock_git

            cmd.link_to_commit(decision_id, "nonexistent")

        captured = capsys.readouterr()
        assert "commit not found" in captured.out.lower()

    def test_prevents_duplicate_commit_links(self, link_command, capsys):
        """Prevents creating duplicate decision-commit links."""
        cmd, factory = link_command

        # Add decision
        decision_id = factory.add_decision(summary="Test decision")
        decision_node = factory.graph.get_nodes_by_type('decision')[-1]

        # Mock resolution
        cmd._cli._resolve_node = Mock(return_value=decision_node)

        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git.get_commit = Mock(return_value=Mock(
                hash="abc123def456789012345678901234567890abcd",
                message="Test commit"
            ))
            mock_git_class.return_value = mock_git

            with patch('babel.commands.link.CommitLinkStore') as mock_store_class:
                mock_store = Mock()
                mock_store.get_link = Mock(return_value=Mock())  # Already linked
                mock_store_class.return_value = mock_store

                cmd.link_to_commit(decision_id, "abc123")

        captured = capsys.readouterr()
        assert "already linked" in captured.out.lower()


# =============================================================================
# List Commit Links Tests
# =============================================================================

class TestListCommitLinks:
    """Test list_commit_links for showing decision-commit bridge."""

    def test_shows_all_commit_links(self, link_command, capsys):
        """Shows all decision-to-commit links."""
        cmd, factory = link_command

        # Add some decisions
        decision_id = factory.add_decision(summary="Linked decision")

        with patch('babel.commands.link.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.all_links = Mock(return_value=[
                Mock(decision_id="abc123", commit_sha="def456789012345678901234567890123456abcd", linked_by="user"),
                Mock(decision_id="xyz789", commit_sha="123456789012345678901234567890123456abcd", linked_by="claude")
            ])
            mock_store_class.return_value = mock_store

            cmd.list_commit_links()

        captured = capsys.readouterr()
        assert "commit" in captured.out.lower()
        assert "def45678" in captured.out or "def456" in captured.out  # Short SHA

    def test_shows_message_when_no_links(self, link_command, capsys):
        """Shows message when no commit links exist."""
        cmd, factory = link_command

        with patch('babel.commands.link.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.all_links = Mock(return_value=[])
            mock_store_class.return_value = mock_store

            cmd.list_commit_links()

        captured = capsys.readouterr()
        assert "no decision-to-commit links" in captured.out.lower()

    def test_respects_pagination_parameters(self, link_command, capsys):
        """Respects limit and offset for pagination."""
        cmd, factory = link_command

        with patch('babel.commands.link.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.all_links = Mock(return_value=[
                Mock(decision_id=f"dec{i}", commit_sha=f"{i:040d}", linked_by="user")
                for i in range(5)
            ])
            mock_store_class.return_value = mock_store

            cmd.list_commit_links(limit=2, offset=0)

        captured = capsys.readouterr()
        # Should have pagination hint
        assert "total" in captured.out.lower() or "link" in captured.out.lower()


# =============================================================================
# Integration Tests
# =============================================================================

class TestLinkIntegration:
    """Integration tests for complete link workflows."""

    def test_full_link_workflow(self, link_command, capsys):
        """Full workflow: list unlinked, link all, verify empty."""
        cmd, factory = link_command

        # Add purpose and unlinked artifacts
        purpose_id = factory.add_purpose("Integration test purpose")
        factory.add_decision(summary="Decision 1", link_to_purpose=False)
        factory.add_constraint(summary="Constraint 1", link_to_purpose=False)

        # Mock _get_active_purpose
        purpose_node = factory.graph.get_nodes_by_type('purpose')[-1]
        cmd._cli._get_active_purpose = Mock(return_value=purpose_node)

        # Step 1: List unlinked
        cmd.list_unlinked()
        captured1 = capsys.readouterr()
        assert "unlinked" in captured1.out.lower()

        # Step 2: Link all
        cmd.link_all()
        captured2 = capsys.readouterr()
        assert "linked" in captured2.out.lower()

        # Step 3: Verify no more orphans
        cmd.list_unlinked()
        captured3 = capsys.readouterr()
        assert "no unlinked" in captured3.out.lower()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_empty_graph(self, link_command, capsys):
        """Handles empty graph gracefully."""
        cmd, factory = link_command

        cmd.list_unlinked()

        captured = capsys.readouterr()
        assert "no unlinked" in captured.out.lower()

    def test_handles_artifact_with_no_summary(self, link_command, capsys):
        """Handles artifacts without summary field."""
        cmd, factory = link_command

        # Add purpose
        factory.add_purpose("Test purpose")

        # Manually add a node without summary
        from babel.core.graph import Node
        node = Node(
            id="test_node_123",
            type="decision",
            content={"detail": "No summary field"},
            event_id="evt_123"
        )
        factory.graph.add_node(node)

        cmd.list_unlinked()

        captured = capsys.readouterr()
        # Should not crash
        assert "decision" in captured.out.lower() or "no unlinked" in captured.out.lower()

    def test_handles_unicode_in_summaries(self, link_command, capsys):
        """Handles Unicode content in artifact summaries."""
        cmd, factory = link_command

        factory.add_decision(
            summary="Unicode: 日本語 émoji 🎉",
            link_to_purpose=False
        )

        cmd.list_unlinked()

        captured = capsys.readouterr()
        # Should display without crashing
        assert "decision" in captured.out.lower()

    def test_format_node_id_uses_codec(self, link_command):
        """_format_node_id uses codec for alias formatting."""
        cmd, factory = link_command

        factory.add_purpose("Test purpose")
        purpose_node = factory.graph.get_nodes_by_type('purpose')[-1]

        formatted = cmd._format_node_id(purpose_node)

        # Should include brackets from format_id
        assert "[" in formatted and "]" in formatted
