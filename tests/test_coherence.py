"""
Tests for Coherence — Drift detection validation (P3)

Tests checkpoint caching, incremental checks, and detection logic.
"""

import pytest
from datetime import datetime, timezone, timedelta

from babel.core.events import EventStore, EventType, declare_purpose, confirm_artifact
from babel.core.graph import GraphStore
from babel.config import Config
from babel.tracking.coherence import (
    CoherenceChecker, CoherenceResult, CoherenceScope, EntityStatus,
    format_coherence_status, _format_age,
)
from babel.presentation.symbols import UNICODE, ASCII


@pytest.fixture
def tmp_project(tmp_path):
    """Create temporary project with stores."""
    events = EventStore(tmp_path / "events.jsonl")
    graph = GraphStore(tmp_path / "graph.db")
    config = Config()
    return events, graph, config


@pytest.fixture
def project_with_purpose(tmp_project):
    """Project with a purpose defined."""
    events, graph, config = tmp_project
    
    # Add purpose
    purpose_event = declare_purpose("Build a tool that preserves intent")
    events.append(purpose_event)
    graph._project_event(purpose_event)
    
    return events, graph, config


@pytest.fixture
def project_with_artifacts(project_with_purpose):
    """Project with purpose and some artifacts."""
    events, graph, config = project_with_purpose
    
    # Add a decision
    decision_event = confirm_artifact(
        proposal_id="prop_1",
        artifact_type="decision",
        content={"summary": "Use SQLite for storage", "detail": {"what": "SQLite", "why": "Simple, local"}}
    )
    events.append(decision_event)
    graph._project_event(decision_event)
    
    # Add a constraint
    constraint_event = confirm_artifact(
        proposal_id="prop_2",
        artifact_type="constraint",
        content={"summary": "Must work offline", "detail": {"what": "Offline-first", "why": "Reliability"}}
    )
    events.append(constraint_event)
    graph._project_event(constraint_event)
    
    return events, graph, config


class TestCoherenceChecker:
    """Test CoherenceChecker core functionality."""

    def test_check_without_purpose(self, tmp_project):
        """Check returns ambiguous when no purpose defined."""
        events, graph, config = tmp_project
        checker = CoherenceChecker(events, graph, config)
        
        result = checker.check()
        
        assert result.status == "ambiguous"
        assert "No purpose defined" in result.signals[0]

    def test_check_with_purpose_only(self, project_with_purpose):
        """Check returns coherent when only purpose exists."""
        events, graph, config = project_with_purpose
        checker = CoherenceChecker(events, graph, config)
        
        result = checker.check()
        
        assert result.status == "coherent"
        assert result.checkpoint_id.startswith("chk_")

    def test_check_creates_checkpoint_event(self, project_with_artifacts):
        """Check creates a coherence checkpoint event."""
        events, graph, config = project_with_artifacts
        checker = CoherenceChecker(events, graph, config)
        
        initial_count = events.count()
        result = checker.check()
        
        assert events.count() == initial_count + 1
        
        checkpoint_events = events.read_by_type(EventType.COHERENCE_CHECKED)
        assert len(checkpoint_events) == 1
        assert checkpoint_events[0].data["checkpoint_id"] == result.checkpoint_id

    def test_check_returns_entities(self, project_with_artifacts):
        """Check returns status for each artifact."""
        events, graph, config = project_with_artifacts
        checker = CoherenceChecker(events, graph, config)
        
        result = checker.check()
        
        # Should have entities for decision and constraint
        assert len(result.entities) >= 2

    def test_trigger_recorded(self, project_with_purpose):
        """Trigger type is recorded in result."""
        events, graph, config = project_with_purpose
        checker = CoherenceChecker(events, graph, config)
        
        result = checker.check(trigger="commit", triggered_by="abc123")
        
        assert result.trigger == "commit"
        assert result.triggered_by == "abc123"


class TestCheckpointCaching:
    """Test checkpoint cache logic."""

    def test_cache_used_when_valid(self, project_with_artifacts):
        """Second check uses cache if nothing changed."""
        events, graph, config = project_with_artifacts
        checker = CoherenceChecker(events, graph, config)
        
        # First check
        result1 = checker.check()
        assert result1.from_cache is False
        
        # Second check (no changes)
        result2 = checker.check()
        assert result2.from_cache is True
        assert result2.checkpoint_id == result1.checkpoint_id

    def test_cache_invalidated_by_new_artifact(self, project_with_artifacts):
        """Cache invalidated when new artifact added."""
        events, graph, config = project_with_artifacts
        checker = CoherenceChecker(events, graph, config)
        
        # First check
        result1 = checker.check()
        
        # Add new artifact
        new_event = confirm_artifact(
            proposal_id="prop_3",
            artifact_type="decision",
            content={"summary": "Use JSON for config"}
        )
        events.append(new_event)
        graph._project_event(new_event)
        
        # Second check (should recompute)
        result2 = checker.check()
        assert result2.from_cache is False
        assert result2.checkpoint_id != result1.checkpoint_id

    def test_force_full_bypasses_cache(self, project_with_artifacts):
        """force_full=True bypasses cache."""
        events, graph, config = project_with_artifacts
        checker = CoherenceChecker(events, graph, config)
        
        # First check
        result1 = checker.check()
        
        # Force full check
        result2 = checker.check(force_full=True)
        assert result2.from_cache is False


class TestConflictDetection:
    """Test conflict detection heuristics."""

    def test_detects_offline_vs_sync_conflict(self, project_with_purpose):
        """Detects conflict between offline constraint and sync decision."""
        events, graph, config = project_with_purpose
        
        # Add offline constraint
        constraint_event = confirm_artifact(
            proposal_id="prop_1",
            artifact_type="constraint",
            content={"summary": "Must work offline"}
        )
        events.append(constraint_event)
        graph._project_event(constraint_event)
        
        # Add conflicting decision
        decision_event = confirm_artifact(
            proposal_id="prop_2",
            artifact_type="decision",
            content={"summary": "Add real-time sync feature"}
        )
        events.append(decision_event)
        graph._project_event(decision_event)
        
        checker = CoherenceChecker(events, graph, config)
        result = checker.check()
        
        # Should detect tension
        tensions = [e for e in result.entities if e.status == "tension"]
        assert len(tensions) >= 1

    def test_no_false_positive_on_compatible(self, project_with_purpose):
        """Doesn't flag false positives on compatible artifacts."""
        events, graph, config = project_with_purpose
        
        # Add compatible artifacts
        decision_event = confirm_artifact(
            proposal_id="prop_1",
            artifact_type="decision",
            content={"summary": "Use SQLite for local storage"}
        )
        events.append(decision_event)
        graph._project_event(decision_event)
        
        constraint_event = confirm_artifact(
            proposal_id="prop_2",
            artifact_type="constraint",
            content={"summary": "Data must persist locally"}
        )
        events.append(constraint_event)
        graph._project_event(constraint_event)
        
        checker = CoherenceChecker(events, graph, config)
        result = checker.check()
        
        # Should not detect tension for compatible artifacts
        assert result.status == "coherent"


class TestEntityStatus:
    """Test EntityStatus dataclass."""

    def test_to_dict(self):
        """Converts to dictionary."""
        status = EntityStatus(
            id="dec_1",
            node_type="decision",
            summary="Use SQLite",
            status="coherent"
        )
        
        d = status.to_dict()
        
        assert d["id"] == "dec_1"
        assert d["type"] == "decision"
        assert d["status"] == "coherent"

    def test_from_dict(self):
        """Creates from dictionary."""
        d = {
            "id": "dec_1",
            "type": "decision",
            "summary": "Use SQLite",
            "status": "tension",
            "reason": "May conflict",
            "related_to": ["con_1"]
        }
        
        status = EntityStatus.from_dict(d)
        
        assert status.id == "dec_1"
        assert status.status == "tension"
        assert status.related_to == ["con_1"]


class TestCoherenceScope:
    """Test CoherenceScope dataclass."""

    def test_to_dict(self):
        """Converts to dictionary."""
        scope = CoherenceScope(
            purpose_ids=["pur_1"],
            artifact_ids=["dec_1", "con_1"],
            since="2025-01-01T00:00:00Z"
        )
        
        d = scope.to_dict()
        
        assert d["purpose_ids"] == ["pur_1"]
        assert len(d["artifact_ids"]) == 2

    def test_from_dict(self):
        """Creates from dictionary."""
        d = {
            "purpose_ids": ["pur_1"],
            "artifact_ids": ["dec_1"],
            "since": None
        }
        
        scope = CoherenceScope.from_dict(d)
        
        assert scope.purpose_ids == ["pur_1"]
        assert scope.since is None


class TestCoherenceResult:
    """Test CoherenceResult properties."""

    def test_has_issues_true(self):
        """has_issues is True for tension/drift."""
        result = CoherenceResult(
            checkpoint_id="chk_1",
            timestamp="2025-01-14T00:00:00Z",
            status="tension",
            scope=CoherenceScope([], [], None),
            signals=[],
            entities=[],
            trigger="manual"
        )
        
        assert result.has_issues is True

    def test_has_issues_false(self):
        """has_issues is False for coherent."""
        result = CoherenceResult(
            checkpoint_id="chk_1",
            timestamp="2025-01-14T00:00:00Z",
            status="coherent",
            scope=CoherenceScope([], [], None),
            signals=[],
            entities=[],
            trigger="manual"
        )
        
        assert result.has_issues is False

    def test_counts(self):
        """Counts are correct."""
        entities = [
            EntityStatus("1", "decision", "A", "coherent"),
            EntityStatus("2", "decision", "B", "coherent"),
            EntityStatus("3", "decision", "C", "tension"),
            EntityStatus("4", "decision", "D", "low_alignment"),
        ]

        result = CoherenceResult(
            checkpoint_id="chk_1",
            timestamp="2025-01-14T00:00:00Z",
            status="tension",
            scope=CoherenceScope([], [], None),
            signals=[],
            entities=entities,
            trigger="manual"
        )

        assert result.coherent_count == 2
        assert result.tension_count == 1
        assert result.low_alignment_count == 1
        assert result.drift_count == 0


class TestFormatting:
    """Test output formatting."""

    def test_format_coherence_status_coherent(self):
        """Formats coherent status."""
        result = CoherenceResult(
            checkpoint_id="chk_1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="coherent",
            scope=CoherenceScope([], [], None),
            signals=["All good"],
            entities=[],
            trigger="manual"
        )
        
        output = format_coherence_status(result, UNICODE)
        
        assert UNICODE.coherent in output
        assert "Coherence:" in output

    def test_format_coherence_status_tension(self):
        """Formats tension status with issues."""
        result = CoherenceResult(
            checkpoint_id="chk_1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="tension",
            scope=CoherenceScope([], [], None),
            signals=["Issues found"],
            entities=[
                EntityStatus("1", "decision", "Add sync", "tension", "Conflicts with offline")
            ],
            trigger="manual"
        )
        
        output = format_coherence_status(result, UNICODE)
        
        assert UNICODE.tension in output
        assert "Add sync" in output

    def test_format_coherence_status_cached(self):
        """Shows cached indicator."""
        result = CoherenceResult(
            checkpoint_id="chk_1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="coherent",
            scope=CoherenceScope([], [], None),
            signals=[],
            entities=[],
            trigger="manual",
            from_cache=True
        )
        
        output = format_coherence_status(result, UNICODE)
        
        assert "cached" in output

    def test_format_age_just_now(self):
        """Formats recent timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        assert _format_age(now) == "just now"

    def test_format_age_hours(self):
        """Formats hours ago."""
        two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert "h ago" in _format_age(two_hours_ago)


class TestGetLastResult:
    """Test retrieving last result."""

    def test_get_last_result_none(self, project_with_purpose):
        """Returns None when no checks done."""
        events, graph, config = project_with_purpose
        checker = CoherenceChecker(events, graph, config)
        
        assert checker.get_last_result() is None

    def test_get_last_result_returns_previous(self, project_with_artifacts):
        """Returns previous check result."""
        events, graph, config = project_with_artifacts
        checker = CoherenceChecker(events, graph, config)
        
        # Do a check
        original = checker.check()
        
        # Get last result
        last = checker.get_last_result()
        
        assert last is not None
        assert last.checkpoint_id == original.checkpoint_id


class TestConfigIntegration:
    """Test coherence config integration."""

    def test_respects_display_symbols(self, project_with_purpose):
        """Uses configured symbol set."""
        events, graph, config = project_with_purpose
        config.display.symbols = "ascii"

        checker = CoherenceChecker(events, graph, config)

        assert checker.symbols is ASCII


class TestTemporalGrace:
    """Test temporal grace period for recent artifacts (Redesign #5)."""

    def test_recent_artifact_gets_grace_period(self, project_with_purpose):
        """
        Recent artifacts (< 1 hour) with low alignment are marked coherent,
        not flagged as low_alignment. They haven't had time to be linked yet.
        """
        events, graph, config = project_with_purpose

        # Add artifact with keywords that won't align with purpose
        # Purpose is "Build a tool that preserves intent"
        # This artifact has unrelated keywords
        unrelated_event = confirm_artifact(
            proposal_id="prop_unrelated",
            artifact_type="decision",
            content={"summary": "Use blue color scheme for dashboard"}
        )
        events.append(unrelated_event)
        graph._project_event(unrelated_event)

        checker = CoherenceChecker(events, graph, config)
        result = checker.check()

        # Should NOT be flagged as low_alignment due to temporal grace
        low_alignment = [e for e in result.entities if e.status == "low_alignment"]
        assert len(low_alignment) == 0, "Recent artifact should get grace period"

        # Should be marked coherent with grace reason
        coherent = [e for e in result.entities if "blue color" in e.summary.lower()]
        assert len(coherent) == 1
        assert coherent[0].status == "coherent"

    def test_recent_artifact_shows_grace_reason(self, project_with_purpose):
        """Recent artifacts show grace period reason when they have low alignment."""
        events, graph, config = project_with_purpose

        # Add artifact with unrelated content (will have low alignment)
        unrelated_event = confirm_artifact(
            proposal_id="prop_xyz",
            artifact_type="decision",
            content={"summary": "Configure nginx for reverse proxy"}
        )
        events.append(unrelated_event)
        graph._project_event(unrelated_event)

        checker = CoherenceChecker(events, graph, config)
        result = checker.check()

        # Find the entity
        nginx_entities = [e for e in result.entities if "nginx" in e.summary.lower()]
        assert len(nginx_entities) == 1

        # Should have grace period reason if it would have been low_alignment
        entity = nginx_entities[0]
        if entity.reason:
            assert "grace period" in entity.reason.lower() or entity.status == "coherent"

    def test_is_recent_artifact_no_event_id(self, project_with_purpose):
        """Artifact with no event_id is not considered recent."""
        events, graph, config = project_with_purpose
        checker = CoherenceChecker(events, graph, config)

        # Create a node mock without event_id
        from babel.core.graph import Node
        node = Node(
            id="test_no_event",
            type="decision",
            content={"summary": "Test"},
            event_id=None  # No event_id
        )

        # Should return False for no event_id
        assert checker._is_recent_artifact(node) is False

    def test_is_recent_artifact_with_valid_recent_event(self, project_with_purpose):
        """Artifact with recent event_id is considered recent."""
        events, graph, config = project_with_purpose

        # Add an artifact (will have recent timestamp)
        recent_event = confirm_artifact(
            proposal_id="prop_recent",
            artifact_type="decision",
            content={"summary": "Recent decision"}
        )
        events.append(recent_event)
        graph._project_event(recent_event)

        checker = CoherenceChecker(events, graph, config)

        # Get the node
        nodes = graph.get_nodes_by_type("decision")
        recent_node = [n for n in nodes if "Recent decision" in n.content.get("summary", "")][0]

        # Should be recent
        assert checker._is_recent_artifact(recent_node) is True

    def test_is_recent_artifact_custom_grace_period(self, project_with_purpose):
        """Grace period can be customized."""
        events, graph, config = project_with_purpose

        # Add artifact
        event = confirm_artifact(
            proposal_id="prop_test",
            artifact_type="decision",
            content={"summary": "Test decision"}
        )
        events.append(event)
        graph._project_event(event)

        checker = CoherenceChecker(events, graph, config)

        # Get the node
        nodes = graph.get_nodes_by_type("decision")
        node = [n for n in nodes if "Test decision" in n.content.get("summary", "")][0]

        # With 1 second grace, a just-created artifact is still recent
        assert checker._is_recent_artifact(node, grace_seconds=1) is True

        # With 0 seconds grace, nothing is recent
        assert checker._is_recent_artifact(node, grace_seconds=0) is False

    def test_is_recent_artifact_event_not_found(self, project_with_purpose):
        """Artifact with event_id not in events returns False."""
        events, graph, config = project_with_purpose
        checker = CoherenceChecker(events, graph, config)

        # Create a node with non-existent event_id
        from babel.core.graph import Node
        node = Node(
            id="test_missing_event",
            type="decision",
            content={"summary": "Test"},
            event_id="evt_does_not_exist"
        )

        # Should return False for missing event
        assert checker._is_recent_artifact(node) is False
