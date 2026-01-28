"""
Tests for DeprecateCommand — P7/P8 Artifact Deprecation

Tests the artifact deprecation management:
- Deprecating artifacts with required explanations (P8)
- De-prioritizing without deleting (P7)
- Tracking deprecated artifact status

Aligns with:
- P5: Tests ARE evidence for implementation
- P7: Living artifacts, not exhaustive archives
- P8: Failure Metabolism (requires explanation)
"""

import pytest
from unittest.mock import Mock, patch

from babel.commands.deprecate import DeprecateCommand
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def deprecate_command(babel_factory):
    """Create DeprecateCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # DeprecateCommand needs _resolve_node
    cli._resolve_node = Mock(return_value=None)
    cli.resolve_id = Mock(return_value=None)

    # Create command instance
    cmd = DeprecateCommand.__new__(DeprecateCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Helper Classes
# =============================================================================

class MockNode:
    """Mock graph node for testing."""
    def __init__(self, node_id, node_type="decision", summary="Test node"):
        self.id = node_id
        self.type = node_type
        self.content = {"summary": summary}


class MockEvent:
    """Mock event for testing."""
    def __init__(self, artifact_id, reason="Test reason", superseded_by=None, timestamp="2024-01-01"):
        self.data = {
            "artifact_id": artifact_id,
            "reason": reason,
            "superseded_by": superseded_by,
            "author": "test_user"
        }
        self.timestamp = timestamp


# =============================================================================
# Get Deprecated IDs Tests
# =============================================================================

class TestGetDeprecatedIds:
    """Test _get_deprecated_ids method."""

    def test_returns_empty_when_no_deprecations(self, deprecate_command):
        """Returns empty dict when no deprecations exist."""
        cmd, factory = deprecate_command
        cmd._cli.events.read_by_type = Mock(return_value=[])

        result = cmd._get_deprecated_ids()

        assert result == {}

    def test_returns_deprecated_artifacts(self, deprecate_command):
        """Returns dict of deprecated artifact IDs."""
        cmd, factory = deprecate_command

        events = [
            MockEvent("artifact_1", "Obsolete"),
            MockEvent("artifact_2", "Replaced", superseded_by="artifact_3"),
        ]
        cmd._cli.events.read_by_type = Mock(return_value=events)

        result = cmd._get_deprecated_ids()

        assert "artifact_1" in result
        assert "artifact_2" in result
        assert result["artifact_1"]["reason"] == "Obsolete"
        assert result["artifact_2"]["superseded_by"] == "artifact_3"

    def test_includes_timestamp_and_author(self, deprecate_command):
        """Includes timestamp and author in deprecation info."""
        cmd, factory = deprecate_command

        events = [MockEvent("art_1", "Test", timestamp="2024-06-15")]
        cmd._cli.events.read_by_type = Mock(return_value=events)

        result = cmd._get_deprecated_ids()

        assert result["art_1"]["timestamp"] == "2024-06-15"
        assert result["art_1"]["author"] == "test_user"


# =============================================================================
# Is Deprecated Tests
# =============================================================================

class TestIsDeprecated:
    """Test _is_deprecated method."""

    def test_returns_none_when_not_deprecated(self, deprecate_command):
        """Returns None when artifact is not deprecated."""
        cmd, factory = deprecate_command
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.resolve_id = Mock(return_value=None)

        result = cmd._is_deprecated("some_id")

        assert result is None

    def test_returns_info_when_deprecated(self, deprecate_command):
        """Returns deprecation info when artifact is deprecated."""
        cmd, factory = deprecate_command

        events = [MockEvent("artifact_123", "Old and obsolete")]
        cmd._cli.events.read_by_type = Mock(return_value=events)
        cmd._cli.resolve_id = Mock(return_value="artifact_123")

        result = cmd._is_deprecated("artifact_123")

        assert result is not None
        assert result["reason"] == "Old and obsolete"

    def test_uses_resolve_id_for_matching(self, deprecate_command):
        """Uses resolve_id for prefix/alias matching."""
        cmd, factory = deprecate_command

        events = [MockEvent("full_artifact_id_12345", "Test")]
        cmd._cli.events.read_by_type = Mock(return_value=events)
        cmd._cli.resolve_id = Mock(return_value="full_artifact_id_12345")

        result = cmd._is_deprecated("full_art")

        cmd._cli.resolve_id.assert_called_once()
        assert result is not None


# =============================================================================
# Deprecate Tests
# =============================================================================

class TestDeprecate:
    """Test deprecate method for artifact deprecation (P7, P8)."""

    def test_requires_reason_p8(self, deprecate_command, capsys):
        """Requires reason per P8 (no silent abandonment)."""
        cmd, factory = deprecate_command

        # Empty reason should prompt
        with patch('builtins.input', return_value=''):
            cmd.deprecate("artifact_id", "")

        captured = capsys.readouterr()
        assert "P8" in captured.out or "Reason required" in captured.out

    def test_rejects_short_reason(self, deprecate_command, capsys):
        """Rejects very short reasons."""
        cmd, factory = deprecate_command

        with patch('builtins.input', return_value='bad'):
            cmd.deprecate("artifact_id", "x")

        captured = capsys.readouterr()
        assert "Deprecation requires explanation" in captured.out

    def test_deprecates_artifact_successfully(self, deprecate_command, capsys):
        """Successfully deprecates an artifact with valid reason."""
        cmd, factory = deprecate_command

        node = MockNode("node_123", "decision", "Test decision")
        cmd._cli._resolve_node = Mock(return_value=node)
        cmd._cli.events.read_by_type = Mock(return_value=[])  # Not already deprecated
        cmd._cli.resolve_id = Mock(return_value=None)  # Not deprecated

        with patch('babel.output.end_command'):
            cmd.deprecate("node_123", "No longer needed because requirements changed")

        captured = capsys.readouterr()
        assert "Deprecated" in captured.out
        assert "node_123" in captured.out or "[" in captured.out

    def test_shows_not_found_error(self, deprecate_command, capsys):
        """Shows error when artifact not found."""
        cmd, factory = deprecate_command
        cmd._cli._resolve_node = Mock(return_value=None)
        factory.graph.get_nodes_by_type = Mock(return_value=[])

        cmd.deprecate("nonexistent", "Valid reason here")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_shows_already_deprecated(self, deprecate_command, capsys):
        """Shows message when artifact already deprecated."""
        cmd, factory = deprecate_command

        node = MockNode("node_456", "decision", "Test")
        cmd._cli._resolve_node = Mock(return_value=node)

        # Mock _is_deprecated to return True
        with patch.object(cmd, '_is_deprecated', return_value={"reason": "Already deprecated"}):
            cmd.deprecate("node_456", "Valid reason")

        captured = capsys.readouterr()
        assert "already deprecated" in captured.out.lower()

    def test_links_superseded_by_artifact(self, deprecate_command, capsys):
        """Links superseding artifact when provided."""
        cmd, factory = deprecate_command

        old_node = MockNode("old_123", "decision", "Old decision")
        new_node = MockNode("new_456", "decision", "New decision")

        cmd._cli._resolve_node = Mock(side_effect=[old_node, new_node])
        cmd._cli.events.read_by_type = Mock(return_value=[])
        # resolve_id signature: (query, candidates=None, entity_type="item")
        # Return query passthrough when candidates is None, None when candidates provided
        cmd._cli.resolve_id = Mock(side_effect=lambda q, c=None, e="item": q if c is None else None)

        with patch('babel.output.end_command'):
            cmd.deprecate("old_123", "Replaced by better approach", superseded_by="new_456")

        captured = capsys.readouterr()
        assert "SUPERSEDED BY" in captured.out

    def test_warns_when_replacement_not_found(self, deprecate_command, capsys):
        """Warns when superseded_by artifact not found."""
        cmd, factory = deprecate_command

        old_node = MockNode("old_123", "decision", "Old")
        cmd._cli._resolve_node = Mock(side_effect=[old_node, None])
        cmd._cli.events.read_by_type = Mock(return_value=[])
        # resolve_id signature: (query, candidates=None, entity_type="item")
        # Return query passthrough when candidates is None, None when candidates provided
        cmd._cli.resolve_id = Mock(side_effect=lambda q, c=None, e="item": q if c is None else None)

        with patch('babel.output.end_command'):
            cmd.deprecate("old_123", "Valid reason here", superseded_by="nonexistent")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "not found" in captured.out.lower()

    def test_creates_shared_event(self, deprecate_command):
        """Creates deprecation event in shared scope."""
        cmd, factory = deprecate_command

        node = MockNode("node_789", "decision", "Test")
        cmd._cli._resolve_node = Mock(return_value=node)
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.resolve_id = Mock(return_value=None)

        # Mock events.append since factory uses real DualEventStore
        cmd._cli.events.append = Mock()

        with patch('babel.output.end_command'):
            cmd.deprecate("node_789", "Valid deprecation reason")

        # Verify events.append was called (shared scope)
        cmd._cli.events.append.assert_called_once()

    def test_shows_lesson_message(self, deprecate_command, capsys):
        """Shows the lesson/reason for deprecation."""
        cmd, factory = deprecate_command

        node = MockNode("node_abc", "decision", "Test decision")
        cmd._cli._resolve_node = Mock(return_value=node)
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.resolve_id = Mock(return_value=None)

        with patch('babel.output.end_command'):
            cmd.deprecate("node_abc", "Technology became obsolete")

        captured = capsys.readouterr()
        assert "LESSON" in captured.out
        assert "Technology became obsolete" in captured.out

    def test_shows_de_prioritized_message(self, deprecate_command, capsys):
        """Shows that artifact is de-prioritized, not deleted (P7)."""
        cmd, factory = deprecate_command

        node = MockNode("node_xyz", "decision", "Test")
        cmd._cli._resolve_node = Mock(return_value=node)
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.resolve_id = Mock(return_value=None)

        with patch('babel.output.end_command'):
            cmd.deprecate("node_xyz", "Valid reason for deprecation")

        captured = capsys.readouterr()
        assert "de-prioritized" in captured.out.lower()
        assert "History preserved" in captured.out or "HC1" in captured.out


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_unicode_in_reason(self, deprecate_command, capsys):
        """Handles Unicode characters in reason."""
        cmd, factory = deprecate_command

        node = MockNode("node_uni", "decision", "Test")
        cmd._cli._resolve_node = Mock(return_value=node)
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.resolve_id = Mock(return_value=None)

        with patch('babel.output.end_command'):
            cmd.deprecate("node_uni", "Reason with 日本語 and émoji 🎉")

        # Should not crash
        captured = capsys.readouterr()
        assert "Deprecated" in captured.out

    def test_handles_very_long_reason(self, deprecate_command, capsys):
        """Handles very long reason text."""
        cmd, factory = deprecate_command

        node = MockNode("node_long", "decision", "Test")
        cmd._cli._resolve_node = Mock(return_value=node)
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.resolve_id = Mock(return_value=None)

        long_reason = "A" * 500

        with patch('babel.output.end_command'):
            cmd.deprecate("node_long", long_reason)

        # Should not crash
        captured = capsys.readouterr()
        assert "Deprecated" in captured.out

    def test_lists_recent_decisions_on_not_found(self, deprecate_command, capsys):
        """Lists recent decisions when artifact not found."""
        cmd, factory = deprecate_command
        cmd._cli._resolve_node = Mock(return_value=None)

        recent_decisions = [
            MockNode("dec_1", "decision", "Recent decision 1"),
            MockNode("dec_2", "decision", "Recent decision 2"),
        ]
        factory.graph.get_nodes_by_type = Mock(return_value=recent_decisions)

        cmd.deprecate("nonexistent", "Valid reason")

        captured = capsys.readouterr()
        assert "RECENT DECISIONS" in captured.out

    def test_prompts_for_reason_interactively(self, deprecate_command, capsys):
        """Prompts for reason when initial reason is too short."""
        cmd, factory = deprecate_command

        node = MockNode("node_prompt", "decision", "Test")
        cmd._cli._resolve_node = Mock(return_value=node)
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.resolve_id = Mock(return_value=None)

        # First reason too short, then provide valid reason
        with patch('builtins.input', return_value='A much better reason for deprecation'):
            with patch('babel.output.end_command'):
                cmd.deprecate("node_prompt", "x")

        captured = capsys.readouterr()
        # Should either abort or succeed with new reason
        assert "Deprecated" in captured.out or "Deprecation requires" in captured.out
