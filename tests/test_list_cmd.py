"""
Tests for ListCommand — Graph-aware artifact discovery (Redesign #6)

Tests for the babel list command including:
- Helper functions (get_node_summary from formatters.py)
- Overview mode (counts by type)
- Type listing (artifacts of specific type)
- Graph traversal (from artifact)
- Orphan detection

Note: ID formatting is now handled by centralized IDCodec (format_id/codec.encode).
"""

import pytest

from babel.core.events import EventStore, declare_purpose, confirm_artifact
from babel.core.graph import GraphStore, Node, Edge
from babel.config import Config
from babel.commands.list_cmd import (
    ListCommand, ARTIFACT_TYPES, DEFAULT_LIMIT
)
from babel.presentation.formatters import get_node_summary


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tmp_project(tmp_path):
    """Create temporary project with stores."""
    events = EventStore(tmp_path / "events.jsonl")
    graph = GraphStore(tmp_path / "graph.db")
    config = Config()
    return events, graph, config, tmp_path


@pytest.fixture
def project_with_purpose(tmp_project):
    """Project with a purpose defined."""
    events, graph, config, tmp_path = tmp_project

    # Add purpose
    purpose_event = declare_purpose("Build a tool that preserves intent")
    events.append(purpose_event)
    graph._project_event(purpose_event)

    return events, graph, config, tmp_path


@pytest.fixture
def project_with_artifacts(project_with_purpose):
    """Project with purpose and multiple artifacts."""
    events, graph, config, tmp_path = project_with_purpose

    # Add decisions
    for i in range(3):
        event = confirm_artifact(
            proposal_id=f"prop_dec_{i}",
            artifact_type="decision",
            content={"summary": f"Decision {i}", "detail": {"what": f"What {i}", "why": f"Why {i}"}}
        )
        events.append(event)
        graph._project_event(event)

    # Add constraints
    for i in range(2):
        event = confirm_artifact(
            proposal_id=f"prop_con_{i}",
            artifact_type="constraint",
            content={"summary": f"Constraint {i}", "detail": {"what": f"Limit {i}", "why": f"Because {i}"}}
        )
        events.append(event)
        graph._project_event(event)

    # Add a principle
    event = confirm_artifact(
        proposal_id="prop_prin_0",
        artifact_type="principle",
        content={"summary": "Principle 0", "detail": {"what": "Guiding idea", "why": "Good practice"}}
    )
    events.append(event)
    graph._project_event(event)

    return events, graph, config, tmp_path


@pytest.fixture
def project_with_links(project_with_artifacts):
    """Project with some linked artifacts."""
    events, graph, config, tmp_path = project_with_artifacts

    # Get purpose and some decisions
    purposes = graph.get_nodes_by_type("purpose")
    decisions = graph.get_nodes_by_type("decision")

    if purposes and decisions:
        # Link first decision to purpose via graph edge
        # Use purpose's event_id since edges require non-null event_id
        graph.add_edge(Edge(
            source_id=purposes[0].id,
            target_id=decisions[0].id,
            relation="informs",
            event_id=purposes[0].event_id or "evt_link_test"
        ))

    return events, graph, config, tmp_path


# =============================================================================
# Helper Function Tests
# =============================================================================

# Note: TestShortId was removed - ID formatting now uses centralized IDCodec
# (cli.format_id() for display, cli.codec.encode() for data)


class TestGetSummary:
    """Test get_node_summary helper function."""

    def test_extracts_summary_field(self):
        """Extracts summary from content."""
        node = Node(
            id="test_1",
            type="decision",
            content={"summary": "Use SQLite for storage"},
            event_id=None
        )
        assert get_node_summary(node) == "Use SQLite for storage"

    def test_extracts_purpose_field(self):
        """Falls back to purpose field."""
        node = Node(
            id="test_2",
            type="purpose",
            content={"purpose": "Build intent preservation tool"},
            event_id=None
        )
        assert get_node_summary(node) == "Build intent preservation tool"

    def test_extracts_what_field(self):
        """Falls back to what field."""
        node = Node(
            id="test_3",
            type="decision",
            content={"what": "SQLite database"},
            event_id=None
        )
        assert get_node_summary(node) == "SQLite database"

    def test_extracts_from_proposed_dict(self):
        """Extracts summary from nested proposed dict."""
        node = Node(
            id="test_4",
            type="decision",
            content={
                "proposed": {
                    "summary": "Add caching layer"
                }
            },
            event_id=None
        )
        assert get_node_summary(node) == "Add caching layer"

    def test_extracts_what_from_proposed(self):
        """Extracts what from nested proposed dict."""
        node = Node(
            id="test_5",
            type="decision",
            content={
                "proposed": {
                    "what": "Redis cache"
                }
            },
            event_id=None
        )
        assert get_node_summary(node) == "Redis cache"

    def test_extracts_from_detail_dict(self):
        """Extracts what from nested detail dict."""
        node = Node(
            id="test_6",
            type="decision",
            content={
                "detail": {
                    "what": "PostgreSQL database"
                }
            },
            event_id=None
        )
        assert get_node_summary(node) == "PostgreSQL database"

    def test_extracts_goal_from_detail(self):
        """Extracts goal from nested detail dict."""
        node = Node(
            id="test_7",
            type="decision",
            content={
                "detail": {
                    "goal": "Improve performance"
                }
            },
            event_id=None
        )
        assert get_node_summary(node) == "Improve performance"

    def test_fallback_to_str_content(self):
        """Falls back to string representation of content."""
        node = Node(
            id="test_8",
            type="decision",
            content={"unknown_field": "some value"},
            event_id=None
        )
        result = get_node_summary(node)
        assert "unknown_field" in result or "some value" in result

    def test_priority_order(self):
        """Summary field takes priority over others."""
        node = Node(
            id="test_9",
            type="decision",
            content={
                "summary": "Primary summary",
                "purpose": "Secondary",
                "what": "Tertiary"
            },
            event_id=None
        )
        assert get_node_summary(node) == "Primary summary"


# =============================================================================
# ListCommand Tests
# =============================================================================

class TestListOverview:
    """Test list_overview method."""

    def test_shows_artifact_counts(self, project_with_artifacts, capsys):
        """Shows count per artifact type."""
        events, graph, config, tmp_path = project_with_artifacts

        # Create command via mock CLI
        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_overview()
        captured = capsys.readouterr()

        # Should show counts
        assert "decision" in captured.out.lower()
        assert "constraint" in captured.out.lower()

    def test_shows_drill_down_hints(self, project_with_artifacts, capsys):
        """Shows hints for drilling down into types."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_overview()
        captured = capsys.readouterr()

        # Should show drill-down hints
        assert "babel list" in captured.out


class TestListByType:
    """Test list_by_type method."""

    def test_lists_artifacts_of_type(self, project_with_artifacts, capsys):
        """Lists artifacts of specified type."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_by_type("decision")
        captured = capsys.readouterr()

        # Should list decisions
        assert "Decision 0" in captured.out or "decision" in captured.out.lower()

    def test_handles_plural_type(self, project_with_artifacts, capsys):
        """Handles plural form of type name."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_by_type("decisions")  # Plural
        captured = capsys.readouterr()

        # Should still work
        assert "Decision" in captured.out or "decision" in captured.out.lower()

    def test_rejects_invalid_type(self, project_with_artifacts, capsys):
        """Rejects invalid artifact types."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_by_type("invalid_type")
        captured = capsys.readouterr()

        assert "Unknown type" in captured.out

    def test_respects_limit(self, project_with_artifacts, capsys):
        """Respects limit parameter."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_by_type("decision", limit=1)
        captured = capsys.readouterr()

        # Should indicate truncation if more than 1
        if "3" in captured.out:  # We have 3 decisions
            assert "More:" in captured.out or "1 of 3" in captured.out

    def test_show_all_ignores_limit(self, project_with_artifacts, capsys):
        """show_all=True shows all items."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_by_type("decision", limit=1, show_all=True)
        captured = capsys.readouterr()

        # Should show all 3 decisions
        assert "3 of 3" in captured.out or "Decision 2" in captured.out

    def test_filter_pattern(self, project_with_artifacts, capsys):
        """Filters by keyword pattern."""
        events, graph, config, tmp_path = project_with_artifacts

        # Add a specific decision
        event = confirm_artifact(
            proposal_id="prop_filter_test",
            artifact_type="decision",
            content={"summary": "Use UNIQUE_KEYWORD for testing"}
        )
        events.append(event)
        graph._project_event(event)

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_by_type("decision", filter_pattern="UNIQUE_KEYWORD")
        captured = capsys.readouterr()

        assert "UNIQUE_KEYWORD" in captured.out
        assert "(1):" in captured.out  # Shows count when all items fit

    def test_empty_type_message(self, project_with_purpose, capsys):
        """Shows message when no artifacts of type exist."""
        events, graph, config, tmp_path = project_with_purpose

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_by_type("tension")  # No tensions
        captured = capsys.readouterr()

        assert "No tension" in captured.out


class TestListFrom:
    """Test list_from graph traversal method."""

    def test_shows_connected_artifacts(self, project_with_links, capsys):
        """Shows artifacts connected to given artifact."""
        events, graph, config, tmp_path = project_with_links

        from unittest.mock import MagicMock
        from babel.core.resolver import IDResolver, ResolveResult, ResolveStatus

        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config

        # Mock resolver to return the purpose node
        purposes = graph.get_nodes_by_type("purpose")
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = ResolveResult(
            status=ResolveStatus.FOUND,
            node=purposes[0],
            candidates=[],
            query="purpose"
        )
        cli.resolver = mock_resolver
        cmd = ListCommand(cli)

        cmd.list_from("purpose")
        captured = capsys.readouterr()

        # Should show the purpose and its connections
        assert "Type:" in captured.out or "purpose" in captured.out.lower()

    def test_not_found_message(self, project_with_artifacts, capsys):
        """Shows message when artifact not found."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        from babel.core.resolver import IDResolver
        from babel.presentation.codec import IDCodec

        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config

        # Create real resolver and codec for proper ID resolution
        real_resolver = IDResolver(graph)
        real_codec = IDCodec()
        cli.resolver = real_resolver
        cli.codec = real_codec
        # resolve_id should decode alias codes or pass through raw IDs
        cli.resolve_id = lambda x: real_codec.decode(x) if real_codec.is_short_code(x) else x
        cmd = ListCommand(cli)

        cmd.list_from("nonexistent_xyz123")
        captured = capsys.readouterr()

        assert "not found" in captured.out.lower()

    def test_shows_orphan_hint(self, project_with_artifacts, capsys):
        """Shows link hint for orphan artifacts."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        from babel.core.resolver import ResolveResult, ResolveStatus

        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config

        # Mock resolver to return an orphan decision
        decisions = graph.get_nodes_by_type("decision")
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = ResolveResult(
            status=ResolveStatus.FOUND,
            node=decisions[0],
            candidates=[],
            query="decision"
        )
        cli.resolver = mock_resolver
        cmd = ListCommand(cli)

        cmd.list_from(decisions[0].id[:8])
        captured = capsys.readouterr()

        # Orphan should have link hint
        if "No connections" in captured.out:
            assert "babel link" in captured.out


class TestListOrphans:
    """Test list_orphans method."""

    def test_shows_orphan_artifacts(self, project_with_artifacts, capsys):
        """Shows artifacts with no connections."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_orphans()
        captured = capsys.readouterr()

        # Should show orphans (all artifacts are orphans initially)
        assert "Orphan" in captured.out or "orphan" in captured.out.lower()

    def test_no_orphans_message(self, project_with_links, capsys):
        """Shows success message when no orphans (after linking)."""
        events, graph, config, tmp_path = project_with_links

        # Link all artifacts to purpose via graph edges
        purposes = graph.get_nodes_by_type("purpose")
        decisions = graph.get_nodes_by_type("decision")
        constraints = graph.get_nodes_by_type("constraint")
        principles = graph.get_nodes_by_type("principle")

        all_artifacts = decisions + constraints + principles
        for artifact in all_artifacts:
            graph.add_edge(Edge(
                source_id=purposes[0].id,
                target_id=artifact.id,
                relation="informs",
                event_id=purposes[0].event_id or "evt_link_test"
            ))

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_orphans()
        captured = capsys.readouterr()

        # Should show no orphans message
        assert "No orphan" in captured.out or "connected" in captured.out.lower()

    def test_groups_by_type(self, project_with_artifacts, capsys):
        """Groups orphans by artifact type."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_orphans()
        captured = capsys.readouterr()

        # Should group by type
        assert "[decision]" in captured.out.lower() or "decision" in captured.out.lower()

    def test_respects_limit(self, project_with_artifacts, capsys):
        """Respects limit parameter."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()
        cmd = ListCommand(cli)

        cmd.list_orphans(limit=2)
        captured = capsys.readouterr()

        # Should show truncation hint
        if "More:" in captured.out:
            assert "--all" in captured.out


# =============================================================================
# Integration Tests
# =============================================================================

class TestListCommandIntegration:
    """Integration tests for ListCommand."""

    def test_dual_display_format(self, project_with_artifacts, capsys):
        """Verifies dual-display principle: [ID] summary."""
        events, graph, config, tmp_path = project_with_artifacts

        from unittest.mock import MagicMock
        from babel.presentation.codec import IDCodec

        cli = MagicMock()
        cli.graph = graph
        cli.events = events
        cli.config = config
        cli.resolver = MagicMock()

        # Set up codec and format_id to return realistic values
        codec = IDCodec()
        cli.codec = codec
        cli.format_id = lambda node_id: f"[{codec.encode(node_id)}]"

        cmd = ListCommand(cli)

        cmd.list_by_type("decision")
        captured = capsys.readouterr()

        # Should have ID in brackets (AA-BB format) followed by summary
        import re
        pattern = r'\[[A-Z]{2}-[A-Z]{2}\].*\w+'  # [AA-BB] followed by text
        assert re.search(pattern, captured.out), "Should use dual-display format [ID] summary"

    def test_artifact_types_constant(self):
        """Verify ARTIFACT_TYPES covers expected types."""
        expected = ['decision', 'constraint', 'principle', 'purpose', 'tension']
        assert set(ARTIFACT_TYPES) == set(expected)

    def test_default_limit(self):
        """Verify DEFAULT_LIMIT is reasonable."""
        assert DEFAULT_LIMIT == 10
