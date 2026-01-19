"""
Tests for Scope — Hybrid collaboration layer

Tests shared/local event management and synchronization.
"""

import pytest
from pathlib import Path

from babel.core.events import Event, EventType, DualEventStore, capture_conversation, declare_purpose, confirm_artifact
from babel.core.scope import EventScope, get_default_scope, scope_display_marker, scope_from_string


# ============================================================================
# SCOPE ENUM TESTS
# ============================================================================

class TestEventScope:
    """Test EventScope enum and utilities."""

    def test_shared_scope(self):
        """SHARED scope value."""
        assert EventScope.SHARED.value == "shared"

    def test_local_scope(self):
        """LOCAL scope value."""
        assert EventScope.LOCAL.value == "local"

    def test_scope_from_string_shared(self):
        """Parse 'shared' string."""
        assert scope_from_string("shared") == EventScope.SHARED

    def test_scope_from_string_local(self):
        """Parse 'local' string."""
        assert scope_from_string("local") == EventScope.LOCAL

    def test_scope_from_string_none(self):
        """None defaults to LOCAL."""
        assert scope_from_string(None) == EventScope.LOCAL

    def test_scope_from_string_invalid(self):
        """Invalid string defaults to LOCAL."""
        assert scope_from_string("invalid") == EventScope.LOCAL


class TestDefaultScopes:
    """Test default scope assignment by event type."""

    def test_purpose_is_shared(self):
        """PURPOSE_DECLARED defaults to SHARED."""
        assert get_default_scope("purpose_declared") == EventScope.SHARED

    def test_artifact_confirmed_is_shared(self):
        """ARTIFACT_CONFIRMED defaults to SHARED."""
        assert get_default_scope("artifact_confirmed") == EventScope.SHARED

    def test_conversation_captured_is_local(self):
        """CONVERSATION_CAPTURED defaults to LOCAL."""
        assert get_default_scope("conversation_captured") == EventScope.LOCAL

    def test_commit_captured_is_shared(self):
        """COMMIT_CAPTURED defaults to SHARED (commits are in git)."""
        assert get_default_scope("commit_captured") == EventScope.SHARED

    def test_unknown_defaults_to_local(self):
        """Unknown event types default to LOCAL (safe)."""
        assert get_default_scope("unknown_type") == EventScope.LOCAL


class TestScopeDisplayMarker:
    """Test scope display markers."""

    def test_shared_unicode(self):
        """Shared marker in unicode."""
        assert scope_display_marker(EventScope.SHARED, use_unicode=True) == "●"

    def test_local_unicode(self):
        """Local marker in unicode."""
        assert scope_display_marker(EventScope.LOCAL, use_unicode=True) == "○"

    def test_shared_ascii(self):
        """Shared marker in ASCII."""
        assert scope_display_marker(EventScope.SHARED, use_unicode=False) == "[S]"

    def test_local_ascii(self):
        """Local marker in ASCII."""
        assert scope_display_marker(EventScope.LOCAL, use_unicode=False) == "[L]"


# ============================================================================
# EVENT SCOPE PROPERTY TESTS
# ============================================================================

class TestEventScopeProperty:
    """Test Event scope properties."""

    def test_event_default_scope(self):
        """Event gets default scope based on type."""
        event = capture_conversation("Test message")
        assert event.scope == "local"
        assert event.is_local
        assert not event.is_shared

    def test_purpose_default_shared(self):
        """Purpose events default to shared."""
        event = declare_purpose("Build something")
        assert event.scope == "shared"
        assert event.is_shared
        assert not event.is_local

    def test_event_scope_property(self):
        """event_scope property returns enum."""
        event = capture_conversation("Test")
        assert event.event_scope == EventScope.LOCAL


# ============================================================================
# DUAL EVENT STORE TESTS
# ============================================================================

@pytest.fixture
def dual_store(tmp_path):
    """Create temporary DualEventStore."""
    return DualEventStore(tmp_path)


class TestDualEventStore:
    """Test DualEventStore functionality."""

    def test_creates_directories(self, dual_store):
        """Creates shared and local directories."""
        assert dual_store.shared_dir.exists()
        assert dual_store.local_dir.exists()

    def test_creates_gitignore(self, dual_store):
        """Creates .gitignore with local/ excluded."""
        gitignore = dual_store.babel_dir / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "local/" in content
        assert "graph.db" in content

    def test_append_local_default(self, dual_store):
        """Conversation captured goes to local by default."""
        event = capture_conversation("Test thought")
        dual_store.append(event)
        
        local = dual_store.read_local()
        shared = dual_store.read_shared()
        
        assert len(local) == 1
        assert len(shared) == 0

    def test_append_shared_explicit(self, dual_store):
        """Can explicitly append to shared."""
        event = capture_conversation("Team decision")
        dual_store.append(event, scope=EventScope.SHARED)
        
        local = dual_store.read_local()
        shared = dual_store.read_shared()
        
        assert len(local) == 0
        assert len(shared) == 1

    def test_append_purpose_shared_by_default(self, dual_store):
        """Purpose declarations go to shared by default."""
        event = declare_purpose("Build something great")
        dual_store.append(event)
        
        shared = dual_store.read_shared()
        assert len(shared) == 1

    def test_read_all_merges(self, dual_store):
        """read_all() merges both stores."""
        local_event = capture_conversation("Local thought")
        shared_event = declare_purpose("Shared purpose")
        
        dual_store.append(local_event)
        dual_store.append(shared_event)
        
        all_events = dual_store.read_all()
        assert len(all_events) == 2

    def test_read_all_excludes_local(self, dual_store):
        """read_all(include_local=False) excludes local."""
        local_event = capture_conversation("Local thought")
        shared_event = declare_purpose("Shared purpose")
        
        dual_store.append(local_event)
        dual_store.append(shared_event)
        
        shared_only = dual_store.read_all(include_local=False)
        assert len(shared_only) == 1
        assert shared_only[0].type == EventType.PURPOSE_DECLARED

    def test_count_by_scope(self, dual_store):
        """count_by_scope returns (shared, local) tuple."""
        dual_store.append(capture_conversation("Local 1"))
        dual_store.append(capture_conversation("Local 2"))
        dual_store.append(declare_purpose("Shared"))
        
        shared, local = dual_store.count_by_scope()
        assert shared == 1
        assert local == 2

    def test_get_event_by_id(self, dual_store):
        """Can get event by ID from either store."""
        local_event = capture_conversation("Local")
        shared_event = declare_purpose("Shared")
        
        dual_store.append(local_event)
        dual_store.append(shared_event)
        
        found_local = dual_store.get(local_event.id)
        found_shared = dual_store.get(shared_event.id)
        
        assert found_local is not None
        assert found_shared is not None
        assert found_local.id == local_event.id
        assert found_shared.id == shared_event.id


class TestPromote:
    """Test promoting local events to shared."""

    def test_promote_moves_to_shared(self, dual_store):
        """promote() moves event from local to shared."""
        event = capture_conversation("Important thought")
        dual_store.append(event, scope=EventScope.LOCAL)
        
        # Verify it's local
        assert len(dual_store.read_local()) == 1
        assert len(dual_store.read_shared()) == 0
        
        # Promote
        promoted = dual_store.promote(event.id)
        
        assert promoted is not None
        assert promoted.id == event.id
        
        # Verify it moved (plus promotion event)
        local = dual_store.read_local()
        shared = dual_store.read_shared()
        assert len(local) == 0
        assert len(shared) == 2  # Promoted event + promotion record

    def test_promote_returns_none_if_not_found(self, dual_store):
        """promote() returns None if event not found."""
        result = dual_store.promote("nonexistent")
        assert result is None

    def test_promote_returns_none_if_already_shared(self, dual_store):
        """promote() returns None if already shared."""
        event = declare_purpose("Already shared")
        dual_store.append(event, scope=EventScope.SHARED)
        
        result = dual_store.promote(event.id)
        assert result is None


class TestSync:
    """Test synchronization after git pull."""

    def test_sync_deduplicates(self, dual_store):
        """sync() removes duplicates."""
        event = declare_purpose("Same event")
        
        # Simulate duplicate from git merge
        dual_store.append(event, scope=EventScope.SHARED)
        dual_store.append(event, scope=EventScope.SHARED)  # Same ID
        
        # Before sync
        shared = dual_store.read_shared()
        assert len(shared) == 2
        
        # Sync
        result = dual_store.sync()
        
        assert result["deduplicated"] == 1
        assert result["total"] == 1
        
        # After sync
        shared = dual_store.read_shared()
        assert len(shared) == 1

    def test_sync_no_duplicates(self, dual_store):
        """sync() reports 0 when no duplicates."""
        dual_store.append(declare_purpose("Event 1"), scope=EventScope.SHARED)
        dual_store.append(declare_purpose("Event 2"), scope=EventScope.SHARED)
        
        result = dual_store.sync()
        
        assert result["deduplicated"] == 0
        assert result["total"] == 2


class TestLegacyMigration:
    """Test migration from single-file to dual-store."""

    def test_migrates_legacy_events(self, tmp_path):
        """Migrates events.jsonl to shared/local."""
        # Create legacy file
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir(parents=True)
        
        import json
        from datetime import datetime, timezone
        
        legacy_path = babel_dir / "events.jsonl"
        
        # Write legacy events
        legacy_events = [
            {
                "type": "purpose_declared",
                "data": {"purpose": "Test"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": 1,
                "id": "abc123"
            },
            {
                "type": "conversation_captured",
                "data": {"content": "Note"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": 1,
                "id": "def456"
            }
        ]
        
        with open(legacy_path, 'w') as f:
            for e in legacy_events:
                f.write(json.dumps(e) + '\n')
        
        # Create DualEventStore (triggers migration)
        store = DualEventStore(tmp_path)
        
        # Legacy file should be renamed
        assert not legacy_path.exists()
        assert (babel_dir / "events.jsonl.migrated").exists()
        
        # Events should be distributed
        shared = store.read_shared()
        local = store.read_local()
        
        # Purpose -> shared, Conversation -> local
        assert len(shared) == 1
        assert len(local) == 1
        assert shared[0].type == EventType.PURPOSE_DECLARED
        assert local[0].type == EventType.CONVERSATION_CAPTURED


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestCollaborationWorkflow:
    """Test typical collaboration workflow."""

    def test_local_to_shared_workflow(self, dual_store):
        """Capture locally, then share when ready."""
        # 1. Capture local thought
        thought = capture_conversation("Maybe we should use Redis?")
        dual_store.append(thought, scope=EventScope.LOCAL)
        
        # 2. Verify it's local
        shared, local = dual_store.count_by_scope()
        assert local == 1
        assert shared == 0
        
        # 3. Decide it's worth sharing
        dual_store.promote(thought.id)
        
        # 4. Now it's shared
        shared, local = dual_store.count_by_scope()
        assert local == 0
        assert shared == 2  # thought + promotion event

    def test_team_sync_workflow(self, tmp_path):
        """Simulate team collaboration with git."""
        # User A's store
        store_a = DualEventStore(tmp_path / "user_a")
        
        # User A captures team decision
        decision = declare_purpose("Build awesome thing")
        store_a.append(decision, scope=EventScope.SHARED)
        
        # Simulate git: copy shared events to User B
        import shutil
        store_b_path = tmp_path / "user_b"
        store_b_path.mkdir(parents=True)
        (store_b_path / ".babel" / "shared").mkdir(parents=True)
        shutil.copy(
            store_a.shared_path,
            store_b_path / ".babel" / "shared" / "events.jsonl"
        )
        
        # User B opens project
        store_b = DualEventStore(store_b_path)
        
        # User B sees shared events
        shared_b = store_b.read_shared()
        assert len(shared_b) == 1
        assert shared_b[0].id == decision.id
