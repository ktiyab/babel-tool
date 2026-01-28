"""
Tests for refs and loader modules

Git-like scalability:
- Refs for O(1) lookup
- Lazy loading (only what's traversed)
- Token efficiency
"""

import pytest

from babel.core.refs import RefStore, extract_topics
from babel.core.loader import LazyLoader, TokenBudget, within_budget
from babel.core.events import Event, EventType, DualEventStore
from babel.core.graph import GraphStore


# =============================================================================
# RefStore Tests
# =============================================================================

class TestRefStore:
    """Test RefStore for O(1) lookups."""
    
    def test_creates_directory_structure(self, tmp_path):
        """RefStore creates refs directories."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        refs = RefStore(babel_dir)
        
        assert (babel_dir / "refs").exists()
        assert (babel_dir / "refs" / "topics").exists()
        assert (babel_dir / "refs" / "decisions").exists()
    
    def test_set_and_get_ref(self, tmp_path):
        """Can set and get a ref."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        refs.set("purpose", ["event_123"], updated_at="2025-01-01")
        
        ref = refs.get("purpose")
        assert ref is not None
        assert ref.event_ids == ["event_123"]
    
    def test_append_to_ref(self, tmp_path):
        """Can append to existing ref."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        refs.append("topics/database", "event_1")
        refs.append("topics/database", "event_2")
        refs.append("topics/database", "event_1")  # Duplicate, should not add
        
        ref = refs.get("topics/database")
        assert ref is not None
        assert ref.event_ids == ["event_1", "event_2"]
    
    def test_find_matching_refs(self, tmp_path):
        """Find returns event IDs matching query."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        refs.append("topics/database", "event_1")
        refs.append("topics/postgresql", "event_2")
        refs.append("topics/authentication", "event_3")
        
        # Find database-related
        matches = refs.find("database")
        assert "event_1" in matches
        
        # Find postgres (partial match)
        matches = refs.find("postgres")
        assert "event_2" in matches
    
    def test_list_refs(self, tmp_path):
        """List all refs or filter by prefix."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        refs.set("purpose", ["e1"])
        refs.append("topics/database", "e2")
        refs.append("topics/auth", "e3")
        refs.append("decisions/confirmed", "e4")
        
        all_refs = refs.list_refs()
        assert len(all_refs) == 4
        
        topic_refs = refs.list_refs("topics/")
        assert len(topic_refs) == 2
    
    def test_persistence(self, tmp_path):
        """Refs persist across instances."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        # First instance
        refs1 = RefStore(babel_dir)
        refs1.set("purpose", ["event_abc"])
        refs1.append("topics/python", "event_def")
        
        # Second instance (new load)
        refs2 = RefStore(babel_dir)
        
        purpose = refs2.get("purpose")
        assert purpose is not None
        assert purpose.event_ids == ["event_abc"]
        
        python = refs2.get("topics/python")
        assert python is not None
        assert "event_def" in python.event_ids


class TestExtractTopics:
    """Test topic extraction from events."""
    
    def test_extracts_technology_topics(self):
        """Extracts technology keywords."""
        event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={"content": "We chose PostgreSQL for the database"}
        )
        
        topics = extract_topics(event)
        
        assert "postgresql" in topics or "database" in topics
    
    def test_extracts_from_purpose(self):
        """Extracts from purpose events."""
        event = Event(
            type=EventType.PURPOSE_DECLARED,
            data={"purpose": "Build an offline-first mobile app with React Native"}
        )
        
        topics = extract_topics(event)
        
        assert any(t in topics for t in ["offline", "react", "mobile"])
    
    def test_extracts_from_artifact(self):
        """Extracts from confirmed artifacts."""
        event = Event(
            type=EventType.ARTIFACT_CONFIRMED,
            data={
                "artifact_type": "decision",
                "content": {
                    "summary": "Use SQLite for local storage",
                    "what": "SQLite database for offline data"
                }
            }
        )
        
        topics = extract_topics(event)
        
        assert "sqlite" in topics or "database" in topics
    
    def test_limits_topics(self):
        """Limits number of topics per event."""
        event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={
                "content": "We need postgres mysql sqlite redis memcached "
                          "api rest graphql auth oauth jwt kubernetes docker"
            }
        )
        
        topics = extract_topics(event)
        
        assert len(topics) <= 10


class TestRefStoreIndexEvent:
    """Test automatic event indexing."""
    
    def test_indexes_purpose_event(self, tmp_path):
        """Purpose events create purpose ref."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        event = Event(
            type=EventType.PURPOSE_DECLARED,
            data={"purpose": "Build a great app"}
        )
        
        refs.index_event(event)
        
        purpose_ref = refs.get("purpose")
        assert purpose_ref is not None
        assert event.id in purpose_ref.event_ids
    
    def test_indexes_confirmed_artifact(self, tmp_path):
        """Confirmed artifacts go to decisions/confirmed."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        event = Event(
            type=EventType.ARTIFACT_CONFIRMED,
            data={
                "artifact_type": "decision",
                "content": {"summary": "Use Python"}
            }
        )
        
        refs.index_event(event)
        
        confirmed_ref = refs.get("decisions/confirmed")
        assert confirmed_ref is not None
        assert event.id in confirmed_ref.event_ids
    
    def test_indexes_constraint(self, tmp_path):
        """Constraints go to decisions/constraints."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        event = Event(
            type=EventType.BOUNDARY_SET,
            data={"boundary": "Must work offline"}
        )
        
        refs.index_event(event)
        
        constraint_ref = refs.get("decisions/constraints")
        assert constraint_ref is not None
        assert event.id in constraint_ref.event_ids


class TestRefStoreRebuild:
    """Test rebuilding refs from events."""
    
    def test_rebuild_from_events(self, tmp_path):
        """Can rebuild refs from event list."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        refs = RefStore(babel_dir)
        
        events = [
            Event(
                type=EventType.PURPOSE_DECLARED,
                data={"purpose": "Build with Python"}
            ),
            Event(
                type=EventType.ARTIFACT_CONFIRMED,
                data={
                    "artifact_type": "decision",
                    "content": {"summary": "Use PostgreSQL database"}
                }
            ),
            Event(
                type=EventType.CONVERSATION_CAPTURED,
                data={"content": "Discussing authentication options"}
            )
        ]
        
        refs.rebuild(events)
        
        # Purpose should exist
        assert refs.get("purpose") is not None
        
        # Topics should be indexed
        topics = refs.list_topics()
        assert len(topics) > 0


# =============================================================================
# LazyLoader Tests
# =============================================================================

class TestLazyLoader:
    """Test token-efficient lazy loading."""
    
    @pytest.fixture
    def setup_loader(self, tmp_path):
        """Create loader with test data."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        babel_dir = project_dir / ".babel"
        babel_dir.mkdir()
        
        events = DualEventStore(project_dir)
        refs = RefStore(babel_dir)
        graph = GraphStore(babel_dir / "graph.db")
        
        # Add some test events
        purpose_event = Event(
            type=EventType.PURPOSE_DECLARED,
            data={"purpose": "Build offline-first app"}
        )
        events.append(purpose_event)
        refs.index_event(purpose_event)
        
        decision_event = Event(
            type=EventType.ARTIFACT_CONFIRMED,
            data={
                "artifact_type": "decision",
                "content": {"summary": "Use SQLite for database"}
            }
        )
        events.append(decision_event)
        refs.index_event(decision_event)
        
        capture_event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={"content": "We discussed using PostgreSQL but chose SQLite"}
        )
        events.append(capture_event)
        refs.index_event(capture_event)
        
        loader = LazyLoader(events, refs, graph)
        
        return loader, events, refs
    
    def test_load_for_why_uses_refs(self, setup_loader):
        """Why query uses refs for O(1) lookup."""
        loader, events, refs = setup_loader
        
        result = loader.load_for_why("database")
        
        assert result.events  # Found something
        assert result.source == "refs"  # Used refs, not full scan
    
    def test_load_for_why_falls_back_to_search(self, setup_loader):
        """Falls back to search when refs don't match."""
        loader, events, refs = setup_loader
        
        result = loader.load_for_why("nonexistent_topic_xyz")
        
        assert result.source == "full_scan"
    
    def test_load_for_status_minimal(self, setup_loader):
        """Status loads minimal data."""
        loader, events, refs = setup_loader
        
        status = loader.load_for_status()
        
        assert "purpose" in status
        assert "shared_count" in status
        assert "local_count" in status
        assert status["tokens_used"] < 500  # Minimal tokens
    
    def test_load_for_coherence_smart(self, setup_loader):
        """Coherence loads strategically."""
        loader, events, refs = setup_loader
        
        result = loader.load_for_coherence(full=False)
        
        assert result.source == "refs"
        assert result.tokens_used < 5000
    
    def test_load_for_coherence_full(self, setup_loader):
        """Full coherence loads everything."""
        loader, events, refs = setup_loader
        
        result = loader.load_for_coherence(full=True)
        
        assert result.source == "full_scan"


class TestTokenBudget:
    """Test token budget management."""
    
    def test_default_budget(self):
        """Default budget is reasonable."""
        budget = TokenBudget()
        
        assert budget.total < 15000  # Fits in most models
        assert budget.system_prompt == 1500
        assert budget.response_reserve == 3000
    
    def test_within_budget(self):
        """Check if tokens within budget."""
        budget = TokenBudget()
        
        assert within_budget(1000, budget)
        assert within_budget(5000, budget)
        assert not within_budget(50000, budget)
    
    def test_remaining_for_context(self):
        """Calculate remaining context budget."""
        budget = TokenBudget()
        
        remaining = budget.remaining_for_context(2000)
        assert remaining > 0
        
        # If we've used a lot, remaining should be small
        remaining = budget.remaining_for_context(6000)
        assert remaining < 2000


# =============================================================================
# Integration Tests
# =============================================================================

class TestRefsLoaderIntegration:
    """Test refs and loader working together."""
    
    def test_index_then_query(self, tmp_path):
        """Index events, then query efficiently."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        babel_dir = project_dir / ".babel"
        babel_dir.mkdir()
        
        events = DualEventStore(project_dir)
        refs = RefStore(babel_dir)
        graph = GraphStore(babel_dir / "graph.db")
        
        # Index multiple events
        for i in range(10):
            event = Event(
                type=EventType.CONVERSATION_CAPTURED,
                data={"content": f"Discussion about database option {i}"}
            )
            events.append(event)
            refs.index_event(event)
        
        # Create loader
        loader = LazyLoader(events, refs, graph)
        
        # Query should use refs
        result = loader.load_for_why("database")
        
        assert result.source == "refs"
        assert len(result.events) > 0
    
    def test_rebuild_preserves_functionality(self, tmp_path):
        """Rebuilding refs preserves query ability."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        babel_dir = project_dir / ".babel"
        babel_dir.mkdir()
        
        events = DualEventStore(project_dir)
        refs = RefStore(babel_dir)
        graph = GraphStore(babel_dir / "graph.db")
        
        # Add events without indexing
        event1 = Event(
            type=EventType.PURPOSE_DECLARED,
            data={"purpose": "Build with Python"}
        )
        events.append(event1)
        
        event2 = Event(
            type=EventType.ARTIFACT_CONFIRMED,
            data={
                "artifact_type": "decision",
                "content": {"summary": "Use Flask framework"}
            }
        )
        events.append(event2)
        
        # Rebuild refs from events
        refs.rebuild(events.read_all())
        
        # Now queries should work
        loader = LazyLoader(events, refs, graph)
        result = loader.load_for_why("Python")
        
        assert len(result.events) > 0
    
    def test_ensure_indexed_fills_gaps(self, tmp_path):
        """ensure_indexed adds missing events to refs."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        babel_dir = project_dir / ".babel"
        babel_dir.mkdir()
        
        events = DualEventStore(project_dir)
        refs = RefStore(babel_dir)
        graph = GraphStore(babel_dir / "graph.db")
        
        # Add event directly to events (bypassing refs)
        event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={"content": "Important discussion about architecture"}
        )
        events.append(event)
        
        # Refs don't know about it yet
        assert len(refs.find("architecture")) == 0
        
        # Ensure indexed
        loader = LazyLoader(events, refs, graph)
        loader.ensure_indexed()
        
        # Now refs should find it
        assert len(refs.find("architecture")) > 0


class TestSyncWithRefs:
    """Test that sync rebuilds refs properly."""
    
    def test_refs_survive_sync(self, tmp_path):
        """Refs are rebuilt after sync."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        babel_dir = project_dir / ".babel"
        babel_dir.mkdir()
        
        events = DualEventStore(project_dir)
        refs = RefStore(babel_dir)
        
        # Add and index
        event = Event(
            type=EventType.PURPOSE_DECLARED,
            data={"purpose": "Test purpose"}
        )
        events.append(event)
        refs.index_event(event)
        
        # Sync (simulating git pull)
        events.sync()
        
        # Rebuild refs
        refs.rebuild(events.read_all())
        
        # Should still find purpose
        purpose_ref = refs.get("purpose")
        assert purpose_ref is not None
