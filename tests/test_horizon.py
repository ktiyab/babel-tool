"""
Tests for Horizon — Token efficiency validation

Tests event horizon, artifact digests, and conflict detection.
"""

import pytest

from babel.core.events import EventStore, EventType, declare_purpose, confirm_artifact
from babel.core.graph import GraphStore
from babel.core.horizon import (
    EventHorizon, DigestBuilder, ArtifactDigest, CoherenceContext,
    EventDigest,
    _extract_keywords, _keywords_conflict, estimate_tokens,
    ARTIFACT_DIGEST_LENGTH,
)


@pytest.fixture
def tmp_stores(tmp_path):
    """Create temporary event and graph stores."""
    events = EventStore(tmp_path / "events.jsonl")
    graph = GraphStore(tmp_path / "graph.db")
    return events, graph


@pytest.fixture
def populated_stores(tmp_stores):
    """Stores with some events and artifacts."""
    events, graph = tmp_stores
    
    # Add purpose
    purpose_event = declare_purpose("Build a tool that preserves intent")
    events.append(purpose_event)
    graph._project_event(purpose_event)
    
    # Add decision
    decision_event = confirm_artifact(
        proposal_id="prop_1",
        artifact_type="decision",
        content={"summary": "Use SQLite for local storage"}
    )
    events.append(decision_event)
    graph._project_event(decision_event)
    
    # Add constraint
    constraint_event = confirm_artifact(
        proposal_id="prop_2",
        artifact_type="constraint",
        content={"summary": "Must work offline without network"}
    )
    events.append(constraint_event)
    graph._project_event(constraint_event)
    
    return events, graph


# ============================================================================
# KEYWORD EXTRACTION TESTS
# ============================================================================

class TestKeywordExtraction:
    """Test keyword extraction for conflict detection."""

    def test_extracts_meaningful_words(self):
        """Extracts meaningful keywords."""
        text = "Use SQLite for local storage and caching"
        keywords = _extract_keywords(text)
        
        assert "sqlite" in keywords
        assert "local" in keywords
        assert "storage" in keywords
        assert "caching" in keywords

    def test_removes_stopwords(self):
        """Removes common stopwords."""
        text = "The system must be able to work offline"
        keywords = _extract_keywords(text)
        
        assert "the" not in keywords
        assert "must" not in keywords
        assert "be" not in keywords
        assert "offline" in keywords

    def test_limits_keyword_count(self):
        """Limits to max 10 keywords."""
        text = "one two three four five six seven eight nine ten eleven twelve"
        keywords = _extract_keywords(text)
        
        assert len(keywords) <= 10

    def test_handles_empty_text(self):
        """Handles empty text."""
        keywords = _extract_keywords("")
        assert keywords == []


# ============================================================================
# KEYWORD CONFLICT TESTS
# ============================================================================

class TestKeywordConflict:
    """Test keyword-based conflict detection."""

    def test_offline_vs_sync_conflict(self):
        """Detects offline vs sync conflict."""
        constraint_kw = {"offline", "local"}
        artifact_kw = {"sync", "real-time", "feature"}
        
        assert _keywords_conflict(artifact_kw, constraint_kw) is True

    def test_simple_vs_complex_conflict(self):
        """Detects simple vs complex conflict."""
        constraint_kw = {"mvp", "simple"}
        artifact_kw = {"complex", "advanced", "system"}
        
        assert _keywords_conflict(artifact_kw, constraint_kw) is True

    def test_no_conflict_compatible(self):
        """No conflict for compatible keywords."""
        constraint_kw = {"offline", "local"}
        artifact_kw = {"sqlite", "storage", "local"}
        
        assert _keywords_conflict(artifact_kw, constraint_kw) is False

    def test_single_vs_multi_conflict(self):
        """Detects single vs multi conflict."""
        constraint_kw = {"single", "user"}
        artifact_kw = {"multi", "user", "support"}
        
        assert _keywords_conflict(artifact_kw, constraint_kw) is True


# ============================================================================
# ARTIFACT DIGEST TESTS
# ============================================================================

class TestArtifactDigest:
    """Test artifact digest creation."""

    def test_creates_from_node(self, populated_stores):
        """Creates digest from graph node."""
        _, graph = populated_stores
        
        decisions = graph.get_nodes_by_type('decision')
        assert len(decisions) > 0
        
        digest = ArtifactDigest.from_node(decisions[0])
        
        assert digest.artifact_type == 'decision'
        assert len(digest.summary) <= ARTIFACT_DIGEST_LENGTH
        assert len(digest.keywords) > 0

    def test_truncates_long_summary(self, populated_stores):
        """Truncates long summaries."""
        events, graph = populated_stores
        
        # Add artifact with long summary
        long_summary = "x" * 200
        event = confirm_artifact(
            proposal_id="prop_long",
            artifact_type="decision",
            content={"summary": long_summary}
        )
        events.append(event)
        graph._project_event(event)
        
        decisions = graph.get_nodes_by_type('decision')
        long_node = [d for d in decisions if len(d.content.get('summary', '')) > 100][0]
        
        digest = ArtifactDigest.from_node(long_node)
        
        assert len(digest.summary) <= ARTIFACT_DIGEST_LENGTH
        assert digest.summary.endswith("...")

    def test_to_dict(self):
        """Converts to dictionary."""
        digest = ArtifactDigest(
            id="dec_1",
            artifact_type="decision",
            summary="Use SQLite",
            keywords=["sqlite", "storage"]
        )
        
        d = digest.to_dict()
        
        assert d["id"] == "dec_1"
        assert d["type"] == "decision"
        assert d["keywords"] == ["sqlite", "storage"]


# ============================================================================
# COHERENCE CONTEXT TESTS
# ============================================================================

class TestCoherenceContext:
    """Test coherence context building."""

    def test_estimated_tokens(self):
        """Estimates token count."""
        context = CoherenceContext(
            purpose_digest="Build a tool",
            artifact_digests=[
                ArtifactDigest("1", "decision", "Use SQLite", ["sqlite"]),
                ArtifactDigest("2", "constraint", "Work offline", ["offline"]),
            ],
            constraint_keywords={"2": ["offline"]},
            total_artifacts=2
        )
        
        tokens = context.estimated_tokens
        
        # Should be reasonable estimate
        assert tokens > 0
        assert tokens < 100  # Small context

    def test_to_prompt(self):
        """Generates prompt context."""
        context = CoherenceContext(
            purpose_digest="Build a tool",
            artifact_digests=[
                ArtifactDigest("1", "decision", "Use SQLite", ["sqlite"]),
            ],
            constraint_keywords={},
            total_artifacts=1
        )
        
        prompt = context.to_prompt()
        
        assert "Purpose: Build a tool" in prompt
        assert "Artifacts: 1 total" in prompt
        assert "Use SQLite" in prompt


# ============================================================================
# DIGEST BUILDER TESTS
# ============================================================================

class TestDigestBuilder:
    """Test DigestBuilder functionality."""

    def test_build_coherence_context(self, populated_stores):
        """Builds token-efficient context."""
        _, graph = populated_stores
        
        builder = DigestBuilder(graph)
        purposes = graph.get_nodes_by_type('purpose')
        artifacts = (
            graph.get_nodes_by_type('decision') +
            graph.get_nodes_by_type('constraint')
        )
        
        context = builder.build_coherence_context(purposes, artifacts)
        
        assert context.purpose_digest
        assert len(context.artifact_digests) > 0
        assert context.total_artifacts == len(artifacts)

    def test_prioritizes_constraints(self, populated_stores):
        """Constraints come first in digests."""
        _, graph = populated_stores
        
        builder = DigestBuilder(graph)
        purposes = graph.get_nodes_by_type('purpose')
        
        # Add more artifacts
        decisions = graph.get_nodes_by_type('decision')
        constraints = graph.get_nodes_by_type('constraint')
        artifacts = decisions + constraints  # Wrong order
        
        context = builder.build_coherence_context(purposes, artifacts)
        
        # Constraints should be first after reordering
        if context.artifact_digests:
            constraint_count = sum(
                1 for d in context.artifact_digests
                if d.artifact_type == 'constraint'
            )
            if constraint_count > 0:
                # First constraint should come before first decision
                first_constraint_idx = next(
                    (i for i, d in enumerate(context.artifact_digests)
                     if d.artifact_type == 'constraint'),
                    len(context.artifact_digests)
                )
                first_decision_idx = next(
                    (i for i, d in enumerate(context.artifact_digests)
                     if d.artifact_type == 'decision'),
                    len(context.artifact_digests)
                )
                assert first_constraint_idx <= first_decision_idx

    def test_check_conflicts_fast(self, populated_stores):
        """Fast conflict detection without LLM."""
        _, graph = populated_stores
        
        builder = DigestBuilder(graph)
        
        # Create artifact that conflicts with offline constraint
        conflicting = ArtifactDigest(
            id="dec_conflict",
            artifact_type="decision",
            summary="Add real-time sync feature",
            keywords=["real-time", "sync", "feature"]
        )
        
        constraint_keywords = {
            "con_1": ["offline", "local", "work"]
        }
        
        conflicts = builder.check_conflicts_fast(conflicting, constraint_keywords)
        
        assert "con_1" in conflicts

    def test_no_false_conflicts(self, populated_stores):
        """Compatible artifacts don't trigger conflicts."""
        _, graph = populated_stores
        
        builder = DigestBuilder(graph)
        
        compatible = ArtifactDigest(
            id="dec_ok",
            artifact_type="decision",
            summary="Use local SQLite database",
            keywords=["local", "sqlite", "database"]
        )
        
        constraint_keywords = {
            "con_1": ["offline", "local"]
        }
        
        conflicts = builder.check_conflicts_fast(compatible, constraint_keywords)
        
        assert len(conflicts) == 0


# ============================================================================
# EVENT HORIZON TESTS
# ============================================================================

class TestEventHorizon:
    """Test event horizon management."""

    def test_get_active_events(self, populated_stores):
        """Gets events within horizon."""
        events, _ = populated_stores
        
        horizon = EventHorizon(events)
        active = horizon.get_active_events()
        
        # All events are recent, should be active
        assert len(active) == events.count()

    def test_get_archived_events_empty(self, populated_stores):
        """No archived events when all are recent."""
        events, _ = populated_stores
        
        horizon = EventHorizon(events)
        archived = horizon.get_archived_events()
        
        assert len(archived) == 0

    def test_get_event_by_id(self, populated_stores):
        """Can retrieve any event by ID."""
        events, _ = populated_stores
        
        horizon = EventHorizon(events)
        all_events = events.read_all()
        
        # Can find any event
        for event in all_events:
            found = horizon.get_event(event.id)
            assert found is not None
            assert found.id == event.id

    def test_summary_stats(self, populated_stores):
        """Gets summary statistics."""
        events, _ = populated_stores
        
        horizon = EventHorizon(events)
        stats = horizon.get_summary_stats()
        
        assert "active_count" in stats
        assert "archived_count" in stats
        assert stats["active_count"] > 0
        assert stats["archived_count"] == 0


# ============================================================================
# EVENT DIGEST TESTS
# ============================================================================

class TestEventDigest:
    """Test event digest creation."""

    def test_from_purpose_event(self, populated_stores):
        """Creates digest from purpose event."""
        events, _ = populated_stores
        
        purpose_events = events.read_by_type(EventType.PURPOSE_DECLARED)
        digest = EventDigest.from_event(purpose_events[0])
        
        assert digest.type == "purpose_declared"
        assert "Purpose:" in digest.summary

    def test_from_artifact_event(self, populated_stores):
        """Creates digest from artifact event."""
        events, _ = populated_stores
        
        artifact_events = events.read_by_type(EventType.ARTIFACT_CONFIRMED)
        if artifact_events:
            digest = EventDigest.from_event(artifact_events[0])
            
            assert digest.type == "artifact_confirmed"
            assert len(digest.summary) > 0

    def test_to_dict(self):
        """Converts to dictionary."""
        digest = EventDigest(
            id="evt_1",
            type="purpose_declared",
            timestamp="2025-01-14",
            summary="Purpose: Build a tool"
        )
        
        d = digest.to_dict()
        
        assert d["id"] == "evt_1"
        assert d["type"] == "purpose_declared"


# ============================================================================
# TOKEN ESTIMATION TESTS
# ============================================================================

class TestTokenEstimation:
    """Test token estimation utility."""

    def test_estimate_tokens(self):
        """Estimates tokens from text."""
        text = "This is a test sentence with about forty characters"
        tokens = estimate_tokens(text)
        
        # ~50 chars / 4 = ~12 tokens
        assert 10 <= tokens <= 20

    def test_empty_text(self):
        """Handles empty text."""
        assert estimate_tokens("") == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestHorizonIntegration:
    """Integration tests for horizon with coherence."""

    def test_coherence_uses_digests(self, populated_stores):
        """Coherence checker uses digest-based checking."""
        from babel.tracking.coherence import CoherenceChecker
        from babel.config import Config
        
        events, graph = populated_stores
        config = Config()
        
        checker = CoherenceChecker(events, graph, config)
        
        # Should have digest builder
        assert checker.digest_builder is not None
        
        # Check should work
        result = checker.check()
        assert result.status in ("coherent", "tension", "drift", "ambiguous")

    def test_token_efficient_context(self, populated_stores):
        """Context is token-efficient."""
        _, graph = populated_stores
        
        builder = DigestBuilder(graph)
        purposes = graph.get_nodes_by_type('purpose')
        artifacts = (
            graph.get_nodes_by_type('decision') +
            graph.get_nodes_by_type('constraint')
        )
        
        context = builder.build_coherence_context(purposes, artifacts)
        
        # Should be well under token limit
        assert context.estimated_tokens < 500  # Much less than 2000
