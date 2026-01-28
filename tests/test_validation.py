"""
Tests for Validation — P9 Dual-Test Truth

P9: Dual-Test Truth
- Claims evaluated against BOTH consensus AND evidence
- Neither alone is sufficient
- Consensus without evidence is groupthink
- Evidence without consensus is noise
"""

import pytest

from babel.core.events import DualEventStore, EventType
from babel.tracking.validation import (
    ValidationTracker, ValidationStatus, DecisionValidation,
    format_validation_status, format_validation_in_context, format_validation_summary
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
    """Create validation tracker."""
    return ValidationTracker(events)


# =============================================================================
# Validation Status Tests
# =============================================================================

class TestValidationStatus:
    """Test validation status computation."""
    
    def test_proposed_status_default(self, tracker):
        """Decisions start as proposed."""
        status = tracker.get_status("nonexistent-id")
        assert status == ValidationStatus.PROPOSED
    
    def test_consensus_status(self, tracker):
        """Consensus without evidence = groupthink risk."""
        # Add endorsements (2 required for consensus)
        tracker.endorse("decision-1", author="alice")
        tracker.endorse("decision-1", author="bob")
        
        validation = tracker.get_validation("decision-1")
        assert validation.status == ValidationStatus.CONSENSUS
        assert validation.has_consensus is True
        assert validation.has_evidence is False
        assert "groupthink" in validation.risk_warning.lower()
    
    def test_evidenced_status(self, tracker):
        """Evidence without consensus = unreviewed risk."""
        tracker.add_evidence("decision-1", "Benchmark showed 2x improvement")
        
        validation = tracker.get_validation("decision-1")
        assert validation.status == ValidationStatus.EVIDENCED
        assert validation.has_consensus is False
        assert validation.has_evidence is True
        assert "unreviewed" in validation.risk_warning.lower()
    
    def test_validated_status(self, tracker):
        """Both consensus AND evidence = validated."""
        # Add consensus
        tracker.endorse("decision-1", author="alice")
        tracker.endorse("decision-1", author="bob")
        
        # Add evidence
        tracker.add_evidence("decision-1", "Load test confirmed")
        
        validation = tracker.get_validation("decision-1")
        assert validation.status == ValidationStatus.VALIDATED
        assert validation.has_consensus is True
        assert validation.has_evidence is True
        assert validation.risk_warning is None


# =============================================================================
# Endorsement Tests
# =============================================================================

class TestEndorsement:
    """Test endorsement (consensus) functionality."""
    
    def test_endorse_decision(self, tracker):
        """Can endorse a decision."""
        success = tracker.endorse("decision-1", author="alice")
        assert success is True
        
        validation = tracker.get_validation("decision-1")
        assert validation.endorsement_count == 1
        assert "alice" in validation.endorsers
    
    def test_multiple_endorsements(self, tracker):
        """Multiple people can endorse."""
        tracker.endorse("decision-1", author="alice")
        tracker.endorse("decision-1", author="bob")
        tracker.endorse("decision-1", author="carol")
        
        validation = tracker.get_validation("decision-1")
        assert validation.endorsement_count == 3
        assert validation.endorsers == {"alice", "bob", "carol"}
    
    def test_no_duplicate_endorsement(self, tracker):
        """Same person cannot endorse twice."""
        tracker.endorse("decision-1", author="alice")
        success = tracker.endorse("decision-1", author="alice")
        
        assert success is False
        
        validation = tracker.get_validation("decision-1")
        assert validation.endorsement_count == 1
    
    def test_endorse_with_comment(self, tracker):
        """Can endorse with comment."""
        tracker.endorse("decision-1", author="alice", comment="LGTM")
        
        validation = tracker.get_validation("decision-1")
        assert validation.endorsements[0]["comment"] == "LGTM"
    
    def test_consensus_requires_one(self, tracker):
        """Consensus requires at least 1 endorsement (solo project threshold)."""
        # Register decision first
        tracker.register_decision("decision-1", "Test decision")
        validation = tracker.get_validation("decision-1")
        assert validation.has_consensus is False  # No endorsements yet

        tracker.endorse("decision-1", author="alice")
        tracker.invalidate_cache()

        validation = tracker.get_validation("decision-1")
        assert validation.has_consensus is True  # 1 endorsement = consensus for solo


# =============================================================================
# Evidence Tests
# =============================================================================

class TestEvidence:
    """Test evidence (grounding) functionality."""
    
    def test_add_evidence(self, tracker):
        """Can add evidence to a decision."""
        success = tracker.add_evidence(
            "decision-1",
            "Benchmark showed 50% improvement",
            evidence_type="benchmark"
        )
        assert success is True
        
        validation = tracker.get_validation("decision-1")
        assert validation.evidence_count == 1
    
    def test_multiple_evidence(self, tracker):
        """Can add multiple evidence items."""
        tracker.add_evidence("decision-1", "User feedback positive", "user_feedback")
        tracker.add_evidence("decision-1", "Load test passed", "benchmark")
        tracker.add_evidence("decision-1", "Production stable for 2 weeks", "outcome")
        
        validation = tracker.get_validation("decision-1")
        assert validation.evidence_count == 3
    
    def test_evidence_types(self, tracker):
        """Evidence types are tracked."""
        tracker.add_evidence("decision-1", "Test content", "benchmark")
        
        validation = tracker.get_validation("decision-1")
        assert validation.evidence[0]["evidence_type"] == "benchmark"
    
    def test_evidence_is_shared(self, tracker, events):
        """Evidence is stored in shared scope."""
        tracker.add_evidence("decision-1", "Test evidence")
        
        shared = events.read_shared()
        assert len(shared) == 1
        assert shared[0].type == EventType.DECISION_EVIDENCED


# =============================================================================
# Query Tests
# =============================================================================

class TestQueries:
    """Test query functionality."""
    
    def test_get_by_status(self, tracker):
        """Can get decisions by status."""
        # Create decisions with different statuses
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")  # d1 = consensus
        
        tracker.add_evidence("d2", "Evidence")  # d2 = evidenced
        
        tracker.endorse("d3", "alice")
        tracker.endorse("d3", "bob")
        tracker.add_evidence("d3", "Evidence")  # d3 = validated
        
        consensus_only = tracker.get_by_status(ValidationStatus.CONSENSUS)
        evidenced_only = tracker.get_by_status(ValidationStatus.EVIDENCED)
        validated = tracker.get_by_status(ValidationStatus.VALIDATED)
        
        assert "d1" in consensus_only
        assert "d2" in evidenced_only
        assert "d3" in validated
    
    def test_get_partially_validated(self, tracker):
        """Can get partially validated decisions."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")  # consensus only
        
        tracker.add_evidence("d2", "Evidence")  # evidence only
        
        partial = tracker.get_partially_validated()
        
        assert "d1" in partial["consensus_only"]
        assert "d2" in partial["evidence_only"]
    
    def test_get_validated(self, tracker):
        """Can get fully validated decisions."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        tracker.add_evidence("d1", "Evidence")
        
        validated = tracker.get_validated()
        assert "d1" in validated


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Test validation statistics."""
    
    def test_stats_basic(self, tracker):
        """Stats include basic counts."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")  # consensus
        
        tracker.add_evidence("d2", "Evidence")  # evidenced
        
        tracker.endorse("d3", "alice")
        tracker.endorse("d3", "bob")
        tracker.add_evidence("d3", "Evidence")  # validated
        
        stats = tracker.stats()
        
        assert stats["tracked"] == 3
        assert stats["validated"] == 1
        assert stats["partial"] == 2
        assert stats["groupthink_risk"] == 1
        assert stats["unreviewed_risk"] == 1
    
    def test_stats_empty(self, tracker):
        """Stats work with no data."""
        stats = tracker.stats()
        
        assert stats["tracked"] == 0
        assert stats["validated"] == 0


# =============================================================================
# Formatting Tests
# =============================================================================

class TestFormatting:
    """Test formatting functions."""
    
    def test_format_validated(self, tracker):
        """Format validated decision."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        tracker.add_evidence("d1", "Test evidence")
        
        validation = tracker.get_validation("d1")
        output = format_validation_status(validation)
        
        assert "VALIDATED" in output
        assert "Consensus" in output
        assert "Evidence" in output
    
    def test_format_consensus_warning(self, tracker):
        """Format shows groupthink warning."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        
        validation = tracker.get_validation("d1")
        output = format_validation_status(validation)
        
        assert "CONSENSUS ONLY" in output
        assert "⚠" in output
        assert "evidence" in output.lower()
    
    def test_format_evidenced_warning(self, tracker):
        """Format shows unreviewed warning."""
        tracker.add_evidence("d1", "Evidence")
        
        validation = tracker.get_validation("d1")
        output = format_validation_status(validation)
        
        assert "EVIDENCED ONLY" in output
        assert "⚠" in output
        assert "consensus" in output.lower()
    
    def test_format_in_context(self, tracker):
        """Format for context display."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        tracker.add_evidence("d1", "Evidence")
        
        validation = tracker.get_validation("d1")
        output = format_validation_in_context(validation)
        
        assert "Validated" in output
        assert "2 endorsements" in output
    
    def test_format_summary(self, tracker):
        """Format summary."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        tracker.add_evidence("d2", "Evidence")
        
        output = format_validation_summary(tracker)
        
        assert "2 decisions tracked" in output
        assert "groupthink" in output.lower()


# =============================================================================
# P9 Principle Tests
# =============================================================================

class TestP9Principles:
    """Test P9 principle compliance."""
    
    def test_consensus_without_evidence_is_groupthink(self, tracker):
        """P9: Consensus alone is not sufficient."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        tracker.endorse("d1", "carol")
        
        validation = tracker.get_validation("d1")
        
        # Strong consensus but...
        assert validation.endorsement_count == 3
        # Not validated without evidence
        assert validation.status != ValidationStatus.VALIDATED
        assert validation.status == ValidationStatus.CONSENSUS
        assert "groupthink" in validation.risk_warning.lower()
    
    def test_evidence_without_consensus_is_noise(self, tracker):
        """P9: Evidence alone is not sufficient."""
        tracker.add_evidence("d1", "Benchmark 1")
        tracker.add_evidence("d1", "Benchmark 2")
        tracker.add_evidence("d1", "User feedback")
        
        validation = tracker.get_validation("d1")
        
        # Strong evidence but...
        assert validation.evidence_count == 3
        # Not validated without consensus
        assert validation.status != ValidationStatus.VALIDATED
        assert validation.status == ValidationStatus.EVIDENCED
        assert "unreviewed" in validation.risk_warning.lower()
    
    def test_both_required_for_validation(self, tracker):
        """P9: Both consensus AND evidence required."""
        # Start with nothing
        assert tracker.get_status("d1") == ValidationStatus.PROPOSED
        
        # Add consensus only
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        tracker.invalidate_cache()
        assert tracker.get_status("d1") == ValidationStatus.CONSENSUS
        
        # Add evidence → now validated
        tracker.add_evidence("d1", "Test passed")
        tracker.invalidate_cache()
        assert tracker.get_status("d1") == ValidationStatus.VALIDATED
    
    def test_validation_is_dual_test(self, tracker):
        """P9: Validation requires passing both tests."""
        # Approach from evidence side
        tracker.add_evidence("d1", "Evidence")
        tracker.invalidate_cache()
        assert tracker.get_status("d1") == ValidationStatus.EVIDENCED

        # Add one endorsement → now validated (solo project threshold)
        tracker.endorse("d1", "alice")
        tracker.invalidate_cache()
        assert tracker.get_status("d1") == ValidationStatus.VALIDATED


# =============================================================================
# DecisionValidation Model Tests
# =============================================================================

class TestDecisionValidationModel:
    """Test DecisionValidation dataclass."""
    
    def test_to_dict(self, tracker):
        """Can convert to dictionary."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        tracker.add_evidence("d1", "Evidence")
        
        validation = tracker.get_validation("d1")
        d = validation.to_dict()
        
        assert d["decision_id"] == "d1"
        assert d["status"] == "validated"
        assert d["endorsement_count"] == 2
        assert d["evidence_count"] == 1
        assert d["has_consensus"] is True
        assert d["has_evidence"] is True
    
    def test_endorsers_property(self, tracker):
        """Endorsers property returns set of authors."""
        tracker.endorse("d1", "alice")
        tracker.endorse("d1", "bob")
        
        validation = tracker.get_validation("d1")
        assert validation.endorsers == {"alice", "bob"}
