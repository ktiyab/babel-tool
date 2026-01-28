"""
Tests for Deprecation — P7 Evidence-Weighted Memory

P7: Evidence-Weighted Memory
- Living artifacts, not exhaustive archives
- What works is retained (P5 validation)
- What fails is metabolized (P4 resolution) or deprecated
- Deprecated items are de-prioritized, not deleted (HC1 preserved)

"Accumulated memory can constrain future options and reduce resilience."
"""

import pytest

from babel.core.events import (
    DualEventStore, EventType,
    deprecate_artifact
)
from babel.core.scope import EventScope


@pytest.fixture
def babel_project(tmp_path):
    """Create a minimal Babel project structure."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    babel_dir = project_dir / ".babel"
    babel_dir.mkdir()
    (babel_dir / "shared").mkdir()
    (babel_dir / "local").mkdir()
    return project_dir


@pytest.fixture
def events(babel_project):
    """Create event store."""
    return DualEventStore(babel_project)


# =============================================================================
# Deprecation Event Tests
# =============================================================================

class TestDeprecationEvent:
    """Test deprecation event creation."""
    
    def test_create_deprecation_event(self):
        """Can create a deprecation event."""
        event = deprecate_artifact(
            artifact_id="decision-123",
            reason="Superseded by new approach"
        )
        
        assert event.type == EventType.ARTIFACT_DEPRECATED
        assert event.data["artifact_id"] == "decision-123"
        assert event.data["reason"] == "Superseded by new approach"
    
    def test_deprecation_with_superseded_by(self):
        """Can specify replacement artifact."""
        event = deprecate_artifact(
            artifact_id="decision-123",
            reason="Replaced",
            superseded_by="decision-456"
        )
        
        assert event.data["superseded_by"] == "decision-456"
    
    def test_deprecation_without_superseded_by(self):
        """Superseded_by is optional."""
        event = deprecate_artifact(
            artifact_id="decision-123",
            reason="No longer relevant"
        )
        
        assert "superseded_by" not in event.data
    
    def test_deprecation_has_author(self):
        """Deprecation tracks author."""
        event = deprecate_artifact(
            artifact_id="decision-123",
            reason="Outdated",
            author="alice"
        )
        
        assert event.data["author"] == "alice"


# =============================================================================
# Event Store Integration Tests
# =============================================================================

class TestDeprecationStorage:
    """Test deprecation storage in event store."""
    
    def test_deprecation_stored_in_shared(self, events):
        """Deprecation events are stored in shared scope."""
        event = deprecate_artifact(
            artifact_id="decision-123",
            reason="Outdated"
        )
        
        events.append(event, scope=EventScope.SHARED)
        
        shared = events.read_shared()
        assert len(shared) == 1
        assert shared[0].type == EventType.ARTIFACT_DEPRECATED
    
    def test_read_deprecation_by_type(self, events):
        """Can query deprecation events by type."""
        event1 = deprecate_artifact("d1", "Reason 1")
        event2 = deprecate_artifact("d2", "Reason 2")
        
        events.append(event1, scope=EventScope.SHARED)
        events.append(event2, scope=EventScope.SHARED)
        
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        assert len(deprecated) == 2
    
    def test_deprecation_preserves_history(self, events):
        """Deprecation doesn't delete original (HC1 preserved)."""
        # Add some decision
        from babel.core.events import capture_conversation
        capture = capture_conversation("Use Redis for caching")
        events.append(capture, scope=EventScope.SHARED)
        
        # Deprecate it
        dep = deprecate_artifact(capture.id, "Switched to Memcached")
        events.append(dep, scope=EventScope.SHARED)
        
        # Original still exists
        all_events = events.read_all()
        assert len(all_events) == 2
        assert all_events[0].type == EventType.CONVERSATION_CAPTURED


# =============================================================================
# P7 Principle Tests
# =============================================================================

class TestP7Principles:
    """Test P7 principle compliance."""
    
    def test_living_artifacts_not_deleted(self, events):
        """P7: Deprecated items are de-prioritized, not deleted."""
        # Create and deprecate
        event = deprecate_artifact(
            artifact_id="decision-123",
            reason="Outdated approach"
        )
        events.append(event, scope=EventScope.SHARED)
        
        # It's still in the event log
        all_events = events.read_all()
        assert len(all_events) == 1
        
        # Can be queried
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        assert len(deprecated) == 1
    
    def test_what_fails_is_metabolized(self, events):
        """P7: Failed/outdated items are marked, not lost."""
        event = deprecate_artifact(
            artifact_id="failed-decision",
            reason="Didn't scale as expected",
            superseded_by="better-decision"
        )
        events.append(event, scope=EventScope.SHARED)
        
        # The failure reason is preserved
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        assert deprecated[0].data["reason"] == "Didn't scale as expected"
        
        # The path forward is clear
        assert deprecated[0].data["superseded_by"] == "better-decision"
    
    def test_hc1_preserved_with_deprecation(self, events):
        """P7 + HC1: History is trustworthy even with deprecation."""
        # Original capture
        from babel.core.events import capture_conversation
        original = capture_conversation("Use session-based auth")
        events.append(original, scope=EventScope.SHARED)
        
        # Later: deprecate it
        dep = deprecate_artifact(
            artifact_id=original.id,
            reason="Mobile apps need stateless auth",
            superseded_by="jwt-decision-id"
        )
        events.append(dep, scope=EventScope.SHARED)
        
        # History shows the evolution
        history = events.read_all()
        assert len(history) == 2
        assert history[0].type == EventType.CONVERSATION_CAPTURED
        assert history[1].type == EventType.ARTIFACT_DEPRECATED
        
        # Both timestamps preserved
        assert history[0].timestamp is not None
        assert history[1].timestamp is not None


# =============================================================================
# AI Weighting Guidance Tests
# =============================================================================

class TestAIWeightingGuidance:
    """Test that deprecation provides signals for AI weighting."""
    
    def test_deprecation_provides_weight_signal(self, events):
        """Deprecation event provides signal for AI to de-weight."""
        event = deprecate_artifact(
            artifact_id="old-decision",
            reason="Better approach found"
        )
        events.append(event, scope=EventScope.SHARED)
        
        # AI can query deprecated items
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        deprecated_ids = {e.data["artifact_id"] for e in deprecated}
        
        # AI can check if an artifact is deprecated
        assert "old-decision" in deprecated_ids
        assert "current-decision" not in deprecated_ids
    
    def test_multiple_deprecations_trackable(self, events):
        """Can track multiple deprecated items for AI filtering."""
        events.append(deprecate_artifact("d1", "Reason 1"), scope=EventScope.SHARED)
        events.append(deprecate_artifact("d2", "Reason 2"), scope=EventScope.SHARED)
        events.append(deprecate_artifact("d3", "Reason 3"), scope=EventScope.SHARED)
        
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        deprecated_ids = [e.data["artifact_id"] for e in deprecated]
        
        assert len(deprecated_ids) == 3
        assert "d1" in deprecated_ids
        assert "d2" in deprecated_ids
        assert "d3" in deprecated_ids


# =============================================================================
# Integration with Existing Signals Tests
# =============================================================================

class TestIntegrationWithExistingSignals:
    """Test that deprecation works alongside P4/P5/P6 signals."""
    
    def test_deprecation_alongside_validation(self, events):
        """Deprecation works with P5 validation events."""
        from babel.core.events import endorse_decision, evidence_decision
        
        # Add validation (P5)
        events.append(endorse_decision("d1", "alice"), scope=EventScope.SHARED)
        events.append(evidence_decision("d1", "Benchmark result"), scope=EventScope.SHARED)
        
        # Later deprecate (P7)
        events.append(deprecate_artifact("d1", "Superseded"), scope=EventScope.SHARED)
        
        # All signals preserved
        all_events = events.read_all()
        assert len(all_events) == 3
        
        # Can query each type
        endorsements = events.read_by_type(EventType.DECISION_ENDORSED)
        evidence = events.read_by_type(EventType.DECISION_EVIDENCED)
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        
        assert len(endorsements) == 1
        assert len(evidence) == 1
        assert len(deprecated) == 1
    
    def test_deprecation_alongside_challenges(self, events):
        """Deprecation works with P4 challenge events."""
        from babel.core.events import raise_challenge
        
        # Challenge raised (P4)
        events.append(
            raise_challenge(
                parent_id="d1",
                parent_type="decision",
                reason="Doesn't scale",
                author="bob"
            ),
            scope=EventScope.SHARED
        )
        
        # Deprecate the original (P7)
        events.append(
            deprecate_artifact("d1", "Revised after challenge"),
            scope=EventScope.SHARED
        )
        
        # History shows the evolution
        all_events = events.read_all()
        assert len(all_events) == 2


# =============================================================================
# P8: Failure Metabolism Tests
# =============================================================================

class TestP8FailureMetabolism:
    """Test P8 failure metabolism compliance."""
    
    def test_deprecation_captures_lesson(self, events):
        """P8: Deprecation reason serves as lesson learned."""
        event = deprecate_artifact(
            artifact_id="failed-approach",
            reason="Monolith couldn't handle 1000 concurrent users"
        )
        events.append(event, scope=EventScope.SHARED)
        
        # The lesson is preserved
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        lesson = deprecated[0].data["reason"]
        
        assert "1000 concurrent users" in lesson
        assert len(lesson) > 10  # Not a trivial explanation
    
    def test_failure_is_not_lost(self, events):
        """P8: Failure is not loss — it's captured as learning."""
        # Simulate a failed decision being deprecated with lesson
        event = deprecate_artifact(
            artifact_id="session-auth-decision",
            reason="Session-based auth failed for mobile; stateless tokens work better",
            superseded_by="jwt-auth-decision"
        )
        events.append(event, scope=EventScope.SHARED)
        
        # The failure AND the lesson are preserved
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        assert len(deprecated) == 1
        
        data = deprecated[0].data
        assert "session-auth-decision" in data["artifact_id"]
        assert "stateless tokens" in data["reason"]
        assert "jwt-auth-decision" in data["superseded_by"]
    
    def test_lessons_queryable_from_deprecations(self, events):
        """P8: Lessons can be extracted from deprecation events."""
        # Multiple deprecations with lessons
        events.append(
            deprecate_artifact("d1", "Didn't scale: Redis hit memory limits at 10GB"),
            scope=EventScope.SHARED
        )
        events.append(
            deprecate_artifact("d2", "User feedback: REST was too chatty, switched to GraphQL"),
            scope=EventScope.SHARED
        )
        events.append(
            deprecate_artifact("d3", "Security audit found SQL injection, moved to ORM"),
            scope=EventScope.SHARED
        )
        
        # AI can query all deprecations to surface lessons
        deprecated = events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        lessons = [e.data["reason"] for e in deprecated]
        
        assert len(lessons) == 3
        assert any("Redis" in l for l in lessons)
        assert any("GraphQL" in l for l in lessons)
        assert any("SQL injection" in l for l in lessons)
    
    def test_revised_challenge_captures_lesson(self, events):
        """P8: Revised challenges serve as lessons via P4."""
        from babel.core.events import raise_challenge, resolve_challenge
        
        # Challenge raised and resolved as revised (P4)
        challenge = raise_challenge(
            parent_id="mongodb-decision",
            parent_type="decision",
            reason="MongoDB can't handle our join patterns"
        )
        events.append(challenge, scope=EventScope.SHARED)
        
        resolution = resolve_challenge(
            challenge_id=challenge.id,
            outcome="revised",
            resolution="Switched to PostgreSQL; joins are 3x faster",
            evidence_summary="Benchmark: 50ms vs 150ms for typical query"
        )
        events.append(resolution, scope=EventScope.SHARED)
        
        # The lesson is in the resolution
        resolutions = events.read_by_type(EventType.CHALLENGE_RESOLVED)
        lesson = resolutions[0].data["resolution"]
        
        assert "PostgreSQL" in lesson
        assert "3x faster" in lesson
