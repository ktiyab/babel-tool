"""
Tests for Tensions — P4 Disagreement Handling

P4: Disagreement as Hypothesis
- Disagreement is information, not friction
- Disputes are reframed as testable hypotheses
- No participant wins by authority alone
- Resolution requires evidence
"""

import pytest

from babel.core.events import DualEventStore, EventType
from babel.tracking.tensions import (
    TensionTracker, Challenge,
    format_challenge, format_tensions_summary, format_challenge_in_context
)


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


@pytest.fixture
def tracker(events):
    """Create tension tracker."""
    return TensionTracker(events)


# =============================================================================
# Challenge Creation Tests
# =============================================================================

class TestChallengeCreation:
    """Test creating challenges."""
    
    def test_raise_challenge_basic(self, tracker):
        """Can raise a basic challenge."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="This approach has performance issues"
        )
        
        assert challenge is not None
        assert challenge.parent_id == "decision-123"
        assert challenge.parent_type == "decision"
        assert challenge.reason == "This approach has performance issues"
        assert challenge.status == "open"
    
    def test_raise_challenge_with_hypothesis(self, tracker):
        """Can raise a challenge with hypothesis."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Query performance is slow",
            hypothesis="NoSQL would handle our access patterns better",
            test="Benchmark both approaches with 10K documents"
        )
        
        assert challenge.hypothesis == "NoSQL would handle our access patterns better"
        assert challenge.test == "Benchmark both approaches with 10K documents"
    
    def test_raise_challenge_with_domain(self, tracker):
        """Can raise a challenge with domain (P3 integration)."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Security concern",
            domain="security"
        )
        
        assert challenge.domain == "security"
    
    def test_challenge_is_shared(self, tracker, events):
        """Challenges are stored in shared scope."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Team needs to see this"
        )
        
        # Should be in shared events
        shared = events.read_shared()
        assert len(shared) == 1
        assert shared[0].type == EventType.CHALLENGE_RAISED


# =============================================================================
# Evidence Tests
# =============================================================================

class TestEvidence:
    """Test adding evidence to challenges."""
    
    def test_add_evidence(self, tracker):
        """Can add evidence to open challenge."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Performance concern",
            hypothesis="Redis would be faster"
        )
        
        success = tracker.add_evidence(
            challenge_id=challenge.id,
            content="Benchmark showed 2x improvement with Redis",
            evidence_type="benchmark"
        )
        
        assert success is True
    
    def test_add_multiple_evidence(self, tracker):
        """Can add multiple evidence items."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Test hypothesis"
        )
        
        tracker.add_evidence(challenge.id, "First observation", "observation")
        tracker.add_evidence(challenge.id, "User feedback", "user_feedback")
        tracker.add_evidence(challenge.id, "Benchmark result", "benchmark")
        
        # Reload and check
        updated = tracker.get_challenge(challenge.id)
        assert len(updated.evidence) == 3
    
    def test_cannot_add_evidence_to_resolved(self, tracker):
        """Cannot add evidence to resolved challenge."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Test"
        )
        
        tracker.resolve(challenge.id, "confirmed", "Original was correct")
        
        success = tracker.add_evidence(challenge.id, "Late evidence")
        assert success is False
    
    def test_cannot_add_evidence_to_nonexistent(self, tracker):
        """Cannot add evidence to nonexistent challenge."""
        success = tracker.add_evidence("fake-id", "Evidence")
        assert success is False


# =============================================================================
# Resolution Tests
# =============================================================================

class TestResolution:
    """Test resolving challenges."""
    
    def test_resolve_confirmed(self, tracker):
        """Can resolve as confirmed (original stands)."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Might not scale"
        )
        
        success = tracker.resolve(
            challenge_id=challenge.id,
            outcome="confirmed",
            resolution="Load testing showed it handles 10x expected load"
        )
        
        assert success is True
        
        resolved = tracker.get_challenge(challenge.id)
        assert resolved.status == "resolved"
        assert resolved.resolution["outcome"] == "confirmed"
    
    def test_resolve_revised(self, tracker):
        """Can resolve as revised (challenger was right)."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Should use GraphQL"
        )
        
        success = tracker.resolve(
            challenge_id=challenge.id,
            outcome="revised",
            resolution="Team agreed GraphQL fits better for our use case"
        )
        
        assert success is True
        
        resolved = tracker.get_challenge(challenge.id)
        assert resolved.resolution["outcome"] == "revised"
    
    def test_resolve_synthesized(self, tracker):
        """Can resolve as synthesized (new understanding)."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="REST vs GraphQL"
        )
        
        success = tracker.resolve(
            challenge_id=challenge.id,
            outcome="synthesized",
            resolution="Use REST for public API, GraphQL for internal"
        )
        
        assert success is True
        
        resolved = tracker.get_challenge(challenge.id)
        assert resolved.resolution["outcome"] == "synthesized"
    
    def test_cannot_resolve_twice(self, tracker):
        """Cannot resolve an already resolved challenge."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Test"
        )
        
        tracker.resolve(challenge.id, "confirmed", "First resolution")
        success = tracker.resolve(challenge.id, "revised", "Second resolution")
        
        assert success is False
    
    def test_resolution_includes_evidence_summary(self, tracker):
        """Resolution can include evidence summary."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Test"
        )
        
        tracker.add_evidence(challenge.id, "Benchmark showed 2x improvement")
        
        tracker.resolve(
            challenge_id=challenge.id,
            outcome="revised",
            resolution="Switched to new approach",
            evidence_summary="Benchmark showed 2x improvement"
        )
        
        resolved = tracker.get_challenge(challenge.id)
        assert resolved.resolution["evidence_summary"] == "Benchmark showed 2x improvement"


# =============================================================================
# Query Tests
# =============================================================================

class TestQueries:
    """Test querying challenges."""
    
    def test_get_open_challenges(self, tracker):
        """Can get all open challenges."""
        tracker.raise_challenge("d1", "decision", "Reason 1")
        tracker.raise_challenge("d2", "decision", "Reason 2")
        c3 = tracker.raise_challenge("d3", "decision", "Reason 3")
        
        tracker.resolve(c3.id, "confirmed", "Resolved")
        
        open_challenges = tracker.get_open_challenges()
        assert len(open_challenges) == 2
    
    def test_get_resolved_challenges(self, tracker):
        """Can get all resolved challenges."""
        c1 = tracker.raise_challenge("d1", "decision", "Reason 1")
        tracker.raise_challenge("d2", "decision", "Reason 2")
        
        tracker.resolve(c1.id, "confirmed", "Resolved")
        
        resolved = tracker.get_resolved_challenges()
        assert len(resolved) == 1
    
    def test_get_challenges_for_parent(self, tracker):
        """Can get challenges for specific parent."""
        tracker.raise_challenge("d1", "decision", "Challenge to d1")
        tracker.raise_challenge("d1", "decision", "Another challenge to d1")
        tracker.raise_challenge("d2", "decision", "Challenge to d2")
        
        d1_challenges = tracker.get_challenges_for_parent("d1")
        assert len(d1_challenges) == 2
        
        d2_challenges = tracker.get_challenges_for_parent("d2")
        assert len(d2_challenges) == 1
    
    def test_get_open_challenges_for_parent(self, tracker):
        """Can get open challenges for specific parent."""
        c1 = tracker.raise_challenge("d1", "decision", "Open challenge")
        c2 = tracker.raise_challenge("d1", "decision", "Resolved challenge")
        
        tracker.resolve(c2.id, "confirmed", "Done")
        
        open_for_d1 = tracker.get_open_challenges_for_parent("d1")
        assert len(open_for_d1) == 1
        assert open_for_d1[0].id == c1.id
    
    def test_count_open(self, tracker):
        """Can count open challenges."""
        tracker.raise_challenge("d1", "decision", "R1")
        tracker.raise_challenge("d2", "decision", "R2")
        c3 = tracker.raise_challenge("d3", "decision", "R3")
        
        assert tracker.count_open() == 3
        
        tracker.resolve(c3.id, "confirmed", "Done")
        
        # Need to invalidate cache
        tracker.invalidate_cache()
        assert tracker.count_open() == 2
    
    def test_get_challenges_by_domain(self, tracker):
        """Can get challenges by domain."""
        tracker.raise_challenge("d1", "decision", "Security issue", domain="security")
        tracker.raise_challenge("d2", "decision", "Perf issue", domain="performance")
        tracker.raise_challenge("d3", "decision", "Another security", domain="security")
        
        security = tracker.get_challenges_by_domain("security")
        assert len(security) == 2


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Test tension statistics."""
    
    def test_stats_basic(self, tracker):
        """Stats include basic counts."""
        tracker.raise_challenge("d1", "decision", "R1", hypothesis="H1")
        tracker.raise_challenge("d2", "decision", "R2")
        c3 = tracker.raise_challenge("d3", "decision", "R3")
        
        tracker.resolve(c3.id, "confirmed", "Done")
        
        tracker.invalidate_cache()
        stats = tracker.stats()
        
        assert stats["total"] == 3
        assert stats["open"] == 2
        assert stats["resolved"] == 1
        assert stats["with_hypothesis"] == 1
    
    def test_stats_outcomes(self, tracker):
        """Stats include outcome breakdown."""
        c1 = tracker.raise_challenge("d1", "decision", "R1")
        c2 = tracker.raise_challenge("d2", "decision", "R2")
        c3 = tracker.raise_challenge("d3", "decision", "R3")
        
        tracker.resolve(c1.id, "confirmed", "Done")
        tracker.resolve(c2.id, "revised", "Changed")
        tracker.resolve(c3.id, "synthesized", "New understanding")
        
        tracker.invalidate_cache()
        stats = tracker.stats()
        
        assert stats["outcomes"]["confirmed"] == 1
        assert stats["outcomes"]["revised"] == 1
        assert stats["outcomes"]["synthesized"] == 1


# =============================================================================
# Formatting Tests
# =============================================================================

class TestFormatting:
    """Test challenge formatting."""
    
    def test_format_challenge_basic(self, tracker):
        """Can format a basic challenge."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Performance concern"
        )
        
        output = format_challenge(challenge)
        
        assert "Challenge" in output
        assert "Performance concern" in output
        assert "decision" in output
    
    def test_format_challenge_with_hypothesis(self, tracker):
        """Format includes hypothesis if present."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Performance concern",
            hypothesis="Redis would be faster",
            test="Benchmark both"
        )
        
        output = format_challenge(challenge)
        
        assert "Hypothesis:" in output
        assert "Redis would be faster" in output
        assert "Test:" in output
    
    def test_format_tensions_summary_empty(self, tracker):
        """Format handles no tensions."""
        output = format_tensions_summary(tracker)
        assert "No open tensions" in output
    
    def test_format_tensions_summary_with_tensions(self, tracker):
        """Format shows open tensions."""
        tracker.raise_challenge("d1", "decision", "First issue")
        tracker.raise_challenge("d2", "decision", "Second issue")
        
        output = format_tensions_summary(tracker)
        
        assert "Open Tensions: 2" in output
        assert "First issue" in output
        assert "Second issue" in output
    
    def test_format_challenge_in_context(self, tracker):
        """Format for why query context."""
        challenge = tracker.raise_challenge(
            parent_id="decision-123",
            parent_type="decision",
            reason="Should reconsider this"
        )
        
        output = format_challenge_in_context(challenge)
        
        assert "CHALLENGE" in output
        assert "Should reconsider this" in output


# =============================================================================
# Challenge Model Tests
# =============================================================================

class TestChallengeModel:
    """Test Challenge dataclass."""
    
    def test_from_event(self):
        """Can create Challenge from event."""
        from babel.core.events import raise_challenge
        
        event = raise_challenge(
            parent_id="d1",
            parent_type="decision",
            reason="Test reason",
            hypothesis="Test hypothesis"
        )
        
        challenge = Challenge.from_event(event)
        
        assert challenge.id == event.id
        assert challenge.parent_id == "d1"
        assert challenge.reason == "Test reason"
        assert challenge.hypothesis == "Test hypothesis"
    
    def test_to_dict(self, tracker):
        """Can convert to dictionary."""
        challenge = tracker.raise_challenge(
            parent_id="d1",
            parent_type="decision",
            reason="Test"
        )
        
        d = challenge.to_dict()
        
        assert d["id"] == challenge.id
        assert d["parent_id"] == "d1"
        assert d["reason"] == "Test"
        assert d["status"] == "open"


# =============================================================================
# P4 Principle Tests
# =============================================================================

class TestP4Principles:
    """Test P4 principle compliance."""
    
    def test_disagreement_is_information(self, tracker, events):
        """Disagreement is captured as information, not friction."""
        # Challenge doesn't delete or modify original
        challenge = tracker.raise_challenge(
            parent_id="original-decision",
            parent_type="decision",
            reason="I disagree with this approach"
        )
        
        # Original remains (if it existed)
        # Challenge adds context
        assert challenge.status == "open"
        assert challenge.reason == "I disagree with this approach"
    
    def test_disputes_become_hypotheses(self, tracker):
        """Disputes can be reframed as testable hypotheses."""
        challenge = tracker.raise_challenge(
            parent_id="d1",
            parent_type="decision",
            reason="PostgreSQL might not scale",
            hypothesis="MongoDB handles our access patterns better",
            test="Benchmark with real production queries"
        )
        
        assert challenge.hypothesis is not None
        assert challenge.test is not None
    
    def test_resolution_requires_evidence(self, tracker):
        """Resolution captures evidence, not just authority."""
        challenge = tracker.raise_challenge(
            parent_id="d1",
            parent_type="decision",
            reason="Should we use GraphQL?"
        )
        
        # Add evidence
        tracker.add_evidence(challenge.id, "API consumers prefer GraphQL")
        tracker.add_evidence(challenge.id, "Benchmark shows 30% faster")
        
        # Resolution includes evidence
        tracker.resolve(
            challenge.id,
            outcome="revised",
            resolution="Switching to GraphQL based on evidence",
            evidence_summary="Consumer preference + 30% performance gain"
        )
        
        resolved = tracker.get_challenge(challenge.id)
        assert resolved.resolution["evidence_summary"] is not None
        assert len(resolved.evidence) == 2
