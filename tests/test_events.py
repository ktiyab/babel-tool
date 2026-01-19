"""
Tests for Event Store — Coherence Evidence for HC1

These tests validate: "Append-only event integrity"
If these pass, HC1 is honored.
"""

import pytest
import tempfile
from pathlib import Path

from babel.core.events import (
    EventStore, Event, EventType,
    capture_conversation, declare_purpose, confirm_artifact
)


class TestEventIntegrity:
    """HC1: Events, once written, are never mutated or deleted."""
    
    def test_events_persist(self, tmp_path):
        """Events survive store recreation."""
        store_path = tmp_path / "events.jsonl"
        
        # Write events
        store1 = EventStore(store_path)
        event = capture_conversation("Test thought")
        store1.append(event)
        
        # Recreate store, read back
        store2 = EventStore(store_path)
        events = store2.read_all()
        
        assert len(events) == 1
        assert events[0].data['content'] == "Test thought"
    
    def test_events_are_append_only(self, tmp_path):
        """Multiple appends don't overwrite."""
        store = EventStore(tmp_path / "events.jsonl")
        
        store.append(capture_conversation("First"))
        store.append(capture_conversation("Second"))
        store.append(capture_conversation("Third"))
        
        events = store.read_all()
        
        assert len(events) == 3
        assert events[0].data['content'] == "First"
        assert events[1].data['content'] == "Second"
        assert events[2].data['content'] == "Third"
    
    def test_events_have_unique_ids(self, tmp_path):
        """Each event has unique identifier."""
        store = EventStore(tmp_path / "events.jsonl")
        
        e1 = store.append(capture_conversation("Same content"))
        # Small delay ensures different timestamp
        import time; time.sleep(0.01)
        e2 = store.append(capture_conversation("Same content"))
        
        assert e1.id != e2.id
    
    def test_integrity_verification(self, tmp_path):
        """Integrity check detects tampering."""
        store = EventStore(tmp_path / "events.jsonl")
        store.append(capture_conversation("Original"))
        
        # Verify passes normally
        assert store.verify_integrity() == True
        
        # Tamper with file
        with open(store.path, 'r') as f:
            content = f.read()
        
        tampered = content.replace("Original", "Tampered")
        with open(store.path, 'w') as f:
            f.write(tampered)
        
        # Verify now fails
        assert store.verify_integrity() == False
    
    def test_event_ordering_preserved(self, tmp_path):
        """Events maintain insertion order."""
        store = EventStore(tmp_path / "events.jsonl")
        
        for i in range(100):
            store.append(capture_conversation(f"Event {i}"))
        
        events = store.read_all()
        
        for i, event in enumerate(events):
            assert event.data['content'] == f"Event {i}"


class TestEventTypes:
    """Event type coverage for MVP."""
    
    def test_conversation_capture(self, tmp_path):
        """Can capture conversation."""
        store = EventStore(tmp_path / "events.jsonl")
        event = capture_conversation("We decided to use Python", author="alice")
        stored = store.append(event)
        
        assert stored.type == EventType.CONVERSATION_CAPTURED
        assert stored.data['content'] == "We decided to use Python"
        assert stored.data['author'] == "alice"
    
    def test_purpose_declaration(self, tmp_path):
        """Can declare purpose."""
        store = EventStore(tmp_path / "events.jsonl")
        event = declare_purpose("Build intent preservation tool")
        stored = store.append(event)
        
        assert stored.type == EventType.PURPOSE_DECLARED
        assert stored.data['purpose'] == "Build intent preservation tool"
    
    def test_artifact_confirmation(self, tmp_path):
        """Can confirm artifacts with proposal linkage."""
        store = EventStore(tmp_path / "events.jsonl")
        event = confirm_artifact(
            proposal_id="abc123",
            artifact_type="decision",
            content={"summary": "Use SQLite for MVP"}
        )
        stored = store.append(event)
        
        assert stored.type == EventType.ARTIFACT_CONFIRMED
        assert stored.data['proposal_id'] == "abc123"
        assert stored.data['artifact_type'] == "decision"


class TestEventFiltering:
    """Query capabilities on event store."""
    
    def test_filter_by_type(self, tmp_path):
        """Can retrieve events by type."""
        store = EventStore(tmp_path / "events.jsonl")
        
        store.append(capture_conversation("Chat 1"))
        store.append(declare_purpose("Purpose 1"))
        store.append(capture_conversation("Chat 2"))
        store.append(declare_purpose("Purpose 2"))
        
        conversations = store.read_by_type(EventType.CONVERSATION_CAPTURED)
        purposes = store.read_by_type(EventType.PURPOSE_DECLARED)
        
        assert len(conversations) == 2
        assert len(purposes) == 2


class TestP1NeedGrounding:
    """P1: Bootstrap from Need — Purpose must be grounded in reality."""
    
    def test_declare_purpose_with_need(self, tmp_path):
        """Purpose can include need (P1 compliance)."""
        store = EventStore(tmp_path / "events.jsonl")
        
        event = declare_purpose(
            purpose="Build offline-first mobile app",
            need="Field workers lose data when connectivity drops"
        )
        store.append(event)
        
        events = store.read_all()
        assert len(events) == 1
        assert events[0].data['purpose'] == "Build offline-first mobile app"
        assert events[0].data['need'] == "Field workers lose data when connectivity drops"
    
    def test_declare_purpose_without_need(self, tmp_path):
        """Purpose works without need (backward compatible)."""
        store = EventStore(tmp_path / "events.jsonl")
        
        event = declare_purpose(purpose="Build an app")
        store.append(event)
        
        events = store.read_all()
        assert len(events) == 1
        assert events[0].data['purpose'] == "Build an app"
        assert 'need' not in events[0].data  # Should not be present
    
    def test_need_grounds_purpose(self, tmp_path):
        """Need provides grounding for purpose (P1 principle)."""
        # P1: "What is broken, insufficient, or at risk in reality?"
        
        event = declare_purpose(
            need="3 data loss incidents last month, $50K rework cost",
            purpose="Build offline-first mobile app"
        )
        
        # Need should be present and distinct from purpose
        assert event.data['need'] != event.data['purpose']
        assert "data loss" in event.data['need']
        assert "offline" in event.data['purpose']