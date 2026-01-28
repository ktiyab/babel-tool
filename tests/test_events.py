"""
Tests for Event Store — Coherence Evidence for HC1

These tests validate: "Append-only event integrity"
If these pass, HC1 is honored.
"""


from babel.core.events import (
    EventStore, Event, EventType,
    capture_conversation, declare_purpose, confirm_artifact,
    endorse_decision, evidence_decision, register_decision_for_validation,
    deprecate_artifact, resolve_question, add_evidence,
    resolve_challenge
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


# =============================================================================
# Parent ID Consistency Tests (OF-FX decision)
# =============================================================================

class TestParentIdConsistency:
    """
    Artifact-referencing events must set parent_id for consistent ID display.

    Enables history to show artifact IDs that work with follow-up commands
    like endorse, evidence-decision, etc.
    """

    def test_endorse_decision_sets_parent_id(self):
        """endorse_decision sets parent_id to decision_id."""
        event = endorse_decision(decision_id="decision_abc123", author="user")

        assert event.parent_id == "decision_abc123"
        assert event.data["decision_id"] == "decision_abc123"

    def test_evidence_decision_sets_parent_id(self):
        """evidence_decision sets parent_id to decision_id."""
        event = evidence_decision(
            decision_id="decision_def456",
            content="Tests pass",
            evidence_type="observation"
        )

        assert event.parent_id == "decision_def456"
        assert event.data["decision_id"] == "decision_def456"

    def test_register_decision_for_validation_sets_parent_id(self):
        """register_decision_for_validation sets parent_id to decision_id."""
        event = register_decision_for_validation(
            decision_id="decision_ghi789",
            summary="Use SQLite for storage"
        )

        assert event.parent_id == "decision_ghi789"
        assert event.data["decision_id"] == "decision_ghi789"

    def test_deprecate_artifact_sets_parent_id(self):
        """deprecate_artifact sets parent_id to artifact_id."""
        event = deprecate_artifact(
            artifact_id="constraint_jkl012",
            reason="No longer applicable"
        )

        assert event.parent_id == "constraint_jkl012"
        assert event.data["artifact_id"] == "constraint_jkl012"

    def test_resolve_question_sets_parent_id(self):
        """resolve_question sets parent_id to question_id."""
        event = resolve_question(
            question_id="question_mno345",
            resolution="Decided to use REST",
            outcome="answered"
        )

        assert event.parent_id == "question_mno345"
        assert event.data["question_id"] == "question_mno345"

    def test_add_evidence_sets_parent_id(self):
        """add_evidence sets parent_id to challenge_id."""
        event = add_evidence(
            challenge_id="challenge_pqr678",
            content="Benchmark shows 50ms latency"
        )

        assert event.parent_id == "challenge_pqr678"
        assert event.data["challenge_id"] == "challenge_pqr678"

    def test_resolve_challenge_sets_parent_id(self):
        """resolve_challenge sets parent_id to challenge_id."""
        event = resolve_challenge(
            challenge_id="challenge_stu901",
            outcome="revised",
            resolution="Adopted new approach based on evidence"
        )

        assert event.parent_id == "challenge_stu901"
        assert event.data["challenge_id"] == "challenge_stu901"

    def test_capture_conversation_parent_id_optional(self):
        """capture_conversation has optional parent_id (root events)."""
        # Root capture - no parent
        event1 = capture_conversation("Test thought")
        assert event1.parent_id is None

        # Child capture - with parent
        event2 = capture_conversation("Follow-up", parent_id="parent_123")
        assert event2.parent_id == "parent_123"

    def test_confirm_artifact_sets_parent_id(self):
        """confirm_artifact sets parent_id to proposal_id (existing behavior)."""
        event = confirm_artifact(
            proposal_id="proposal_vwx234",
            artifact_type="decision",
            content={"summary": "Use Postgres"}
        )

        assert event.parent_id == "proposal_vwx234"