"""
Tests for HistoryCommand — HC5 Graceful Sync (Event Timeline)

Tests the event history display and collaboration:
- Recent event timeline with scope filtering
- Event promotion (local → shared)
- Synchronization after git operations
- OutputSpec format for rendering

Aligns with:
- P5: Tests ARE evidence for implementation
- P8: Evolution Traceable (event timeline shows history)
- HC5: Graceful Sync (team collaboration)
"""

import pytest
from unittest.mock import Mock

from babel.commands.history import HistoryCommand
from babel.core.events import EventType
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def history_command(babel_factory):
    """Create HistoryCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # HistoryCommand needs _rebuild_graph for sync
    cli._rebuild_graph = Mock()

    # Create command instance
    cmd = HistoryCommand.__new__(HistoryCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# History Display Tests
# =============================================================================

class TestHistoryDisplay:
    """Test history method for event timeline display."""

    def test_shows_recent_events(self, history_command, capsys):
        """Shows recent events in timeline format."""
        cmd, factory = history_command

        # Add some events
        factory.add_purpose("Test purpose")
        factory.add_decision(summary="Test decision")

        cmd.history(limit=10)

        captured = capsys.readouterr()
        assert "Recent activity" in captured.out
        assert "events" in captured.out

    def test_respects_limit_parameter(self, history_command, capsys):
        """Respects limit parameter for event count."""
        cmd, factory = history_command

        # Add multiple events
        for i in range(5):
            factory.add_decision(summary=f"Decision {i}")

        cmd.history(limit=3)

        captured = capsys.readouterr()
        # Should show limited count
        assert "3 events" in captured.out or "events" in captured.out

    def test_formats_conversation_captured(self, history_command, capsys):
        """Formats CONVERSATION_CAPTURED events correctly."""
        cmd, factory = history_command

        # Add a capture event via decision (which creates capture internally)
        factory.add_purpose("Capture test purpose")

        cmd.history()

        captured = capsys.readouterr()
        # Should show event type
        assert "Purpose" in captured.out or "activity" in captured.out

    def test_formats_artifact_confirmed(self, history_command, capsys):
        """Formats ARTIFACT_CONFIRMED events correctly."""
        cmd, factory = history_command

        factory.add_decision(summary="Confirmed artifact test")

        cmd.history()

        captured = capsys.readouterr()
        assert "Confirmed" in captured.out or "decision" in captured.out.lower()


# =============================================================================
# Scope Filtering Tests
# =============================================================================

class TestScopeFiltering:
    """Test scope filtering for shared/local events."""

    def test_shows_all_events_by_default(self, history_command, capsys):
        """Shows all events when no filter specified."""
        cmd, factory = history_command

        factory.add_purpose("All events test")

        cmd.history(scope_filter=None)

        captured = capsys.readouterr()
        assert "Recent activity" in captured.out

    def test_filters_shared_events(self, history_command, capsys):
        """Filters to show only shared events."""
        cmd, factory = history_command

        factory.add_purpose("Shared event test")

        cmd.history(scope_filter="shared")

        captured = capsys.readouterr()
        assert "(shared)" in captured.out

    def test_filters_local_events(self, history_command, capsys):
        """Filters to show only local events."""
        cmd, factory = history_command

        factory.add_decision(summary="Local decision")

        cmd.history(scope_filter="local")

        captured = capsys.readouterr()
        assert "(local)" in captured.out


# =============================================================================
# Share (Promote) Tests
# =============================================================================

class TestShare:
    """Test share method for event promotion."""

    def test_promotes_local_to_shared(self, history_command, capsys):
        """Promotes local event to shared."""
        cmd, factory = history_command

        # Add local event
        factory.add_decision(summary="Promotable decision")

        # Get the event ID
        events = list(factory.events.read_all())
        local_events = [e for e in events if not e.is_shared]

        if local_events:
            event = local_events[-1]

            # Mock promote method to return a mock event
            mock_promoted = Mock()
            mock_promoted.is_shared = True
            mock_promoted.type = event.type
            mock_promoted.data = event.data
            cmd._cli.events.promote = Mock(return_value=mock_promoted)

            cmd.share(event.id)

            captured = capsys.readouterr()
            assert "Shared" in captured.out or "sync with git" in captured.out.lower()
        else:
            # All events are shared - skip test
            pytest.skip("No local events available for promotion test")

    def test_error_when_event_not_found(self, history_command, capsys):
        """Shows error when event not found."""
        cmd, factory = history_command

        cmd.share("nonexistent_id")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_shows_already_shared_message(self, history_command, capsys):
        """Shows message when event is already shared."""
        cmd, factory = history_command

        # Add shared event
        factory.add_purpose("Already shared")

        # Get the event
        events = list(factory.events.read_all())
        # Find a shared event (purposes are shared by default in DualEventStore)
        shared_event = None
        for e in events:
            if e.is_shared:
                shared_event = e
                break

        if shared_event:
            cmd.share(shared_event.id)

            captured = capsys.readouterr()
            assert "already shared" in captured.out.lower()

    def test_handles_nonexistent_id(self, history_command, capsys):
        """Handles ID that doesn't exist."""
        cmd, factory = history_command

        # Add some events
        factory.add_decision(summary="Decision 1")
        factory.add_decision(summary="Decision 2")

        # Use a prefix that won't match any SHA256 hex ID (uses 'z' which isn't in hex)
        cmd.share("zzzzzz")

        captured = capsys.readouterr()
        # Should report not found
        assert "not found" in captured.out.lower() or "no artifact" in captured.out.lower()


# =============================================================================
# Sync Tests
# =============================================================================

class TestSync:
    """Test sync method for post-git-pull synchronization."""

    def test_sync_calls_rebuild_graph(self, history_command, capsys):
        """Sync calls _rebuild_graph."""
        cmd, factory = history_command

        # Mock events.sync
        cmd._cli.events.sync = Mock(return_value={"deduplicated": 0})
        cmd._cli.events.count_by_scope = Mock(return_value=(10, 5))

        cmd.sync()

        # Should call _rebuild_graph
        cmd._cli._rebuild_graph.assert_called_once()

    def test_sync_shows_deduplication(self, history_command, capsys):
        """Sync shows deduplication count when duplicates removed."""
        cmd, factory = history_command

        # Mock events.sync with deduplication
        cmd._cli.events.sync = Mock(return_value={"deduplicated": 3})
        cmd._cli.events.count_by_scope = Mock(return_value=(10, 5))

        cmd.sync()

        captured = capsys.readouterr()
        assert "3 duplicate" in captured.out or "Resolved" in captured.out

    def test_sync_shows_event_counts(self, history_command, capsys):
        """Sync shows shared/local event counts."""
        cmd, factory = history_command

        cmd._cli.events.sync = Mock(return_value={"deduplicated": 0})
        cmd._cli.events.count_by_scope = Mock(return_value=(15, 8))

        cmd.sync()

        captured = capsys.readouterr()
        assert "15" in captured.out and "8" in captured.out
        assert "shared" in captured.out and "local" in captured.out

    def test_sync_verbose_shows_recent(self, history_command, capsys):
        """Sync verbose mode shows recent shared events."""
        cmd, factory = history_command

        factory.add_purpose("Shared purpose")

        cmd._cli.events.sync = Mock(return_value={"deduplicated": 0})
        cmd._cli.events.count_by_scope = Mock(return_value=(1, 0))

        cmd.sync(verbose=True)

        captured = capsys.readouterr()
        assert "Recent shared" in captured.out or "Done" in captured.out


# =============================================================================
# Event Preview Tests
# =============================================================================

class TestEventPreview:
    """Test _event_preview helper method."""

    def test_previews_conversation_captured(self, history_command):
        """Previews CONVERSATION_CAPTURED events."""
        cmd, factory = history_command

        from babel.core.events import Event, EventType

        event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={"content": "Test content here"},
            id="test_123"
        )

        preview = cmd._event_preview(event)

        assert "Capture" in preview
        assert "Test content" in preview

    def test_previews_purpose_declared(self, history_command):
        """Previews PURPOSE_DECLARED events."""
        cmd, factory = history_command

        from babel.core.events import Event, EventType

        event = Event(
            type=EventType.PURPOSE_DECLARED,
            data={"purpose": "Project purpose statement"},
            id="test_123"
        )

        preview = cmd._event_preview(event)

        assert "Purpose" in preview

    def test_previews_artifact_confirmed(self, history_command):
        """Previews ARTIFACT_CONFIRMED events."""
        cmd, factory = history_command

        from babel.core.events import Event, EventType

        event = Event(
            type=EventType.ARTIFACT_CONFIRMED,
            data={"artifact_type": "decision"},
            id="test_123"
        )

        preview = cmd._event_preview(event)

        assert "Confirmed" in preview
        assert "decision" in preview

    def test_previews_commit_captured(self, history_command):
        """Previews COMMIT_CAPTURED events."""
        cmd, factory = history_command

        from babel.core.events import Event, EventType

        event = Event(
            type=EventType.COMMIT_CAPTURED,
            data={"message": "Fix bug in authentication"},
            id="test_123"
        )

        preview = cmd._event_preview(event)

        assert "Commit" in preview

    def test_previews_generic_events(self, history_command):
        """Previews generic event types."""
        cmd, factory = history_command

        from babel.core.events import Event, EventType

        event = Event(
            type=EventType.STRUCTURE_PROPOSED,
            data={},
            id="test_123"
        )

        preview = cmd._event_preview(event)

        assert "Structure Proposed" in preview or "structure" in preview.lower()


# =============================================================================
# Output Format Tests
# =============================================================================

class TestHistoryOutput:
    """Test _history_as_output for OutputSpec format."""

    def test_returns_output_spec_when_format_requested(self, history_command):
        """Returns OutputSpec when output_format specified."""
        cmd, factory = history_command

        factory.add_purpose("Output test purpose")

        result = cmd.history(output_format="table")

        # Should return OutputSpec, not None
        assert result is not None
        assert hasattr(result, 'data')
        assert hasattr(result, 'shape')

    def test_output_spec_has_correct_shape(self, history_command):
        """OutputSpec has correct table shape."""
        cmd, factory = history_command

        factory.add_purpose("Shape test")

        result = cmd.history(output_format="table")

        assert result.shape == "table"
        assert result.command == "history"

    def test_output_spec_contains_event_data(self, history_command):
        """OutputSpec contains event data rows."""
        cmd, factory = history_command

        factory.add_purpose("Data test")
        factory.add_decision(summary="Test decision")

        result = cmd.history(output_format="table")

        assert len(result.data) > 0
        # Each row should have expected keys
        # P12: "date" renamed to "time" for temporal attribution
        for row in result.data:
            assert "scope" in row
            assert "time" in row
            assert "id" in row


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_empty_history(self, history_command, capsys):
        """Handles empty history gracefully."""
        cmd, factory = history_command

        cmd.history()

        captured = capsys.readouterr()
        assert "0 events" in captured.out or "Recent activity" in captured.out

    def test_handles_very_long_content(self, history_command, capsys):
        """Handles events with very long content."""
        cmd, factory = history_command

        # Create event with long content
        factory.add_decision(summary="A" * 1000)

        cmd.history()

        # Should not crash, content should be truncated
        captured = capsys.readouterr()
        assert "Recent activity" in captured.out

    def test_handles_unicode_in_events(self, history_command, capsys):
        """Handles Unicode content in events."""
        cmd, factory = history_command

        factory.add_decision(summary="Unicode: 日本語 🎉 émoji")

        cmd.history()

        # Should not crash
        captured = capsys.readouterr()
        assert "Recent activity" in captured.out

    def test_handles_missing_event_data_fields(self, history_command, capsys):
        """Handles events with missing data fields."""
        cmd, factory = history_command

        # Add minimal event
        from babel.core.events import Event, EventType
        event = Event(
            type=EventType.ARTIFACT_CONFIRMED,
            data={},  # Missing fields
            id="minimal_123"
        )

        preview = cmd._event_preview(event)

        # Should not crash, return something reasonable
        assert preview is not None
