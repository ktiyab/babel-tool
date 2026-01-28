"""
Tests for Ambiguity — P10 Ambiguity Management

P10: Ambiguity Management
- When evidence is insufficient, ambiguity is explicitly recorded
- Unresolved tensions are tracked as first-class artifacts
- Premature resolution is considered a failure mode
- Holding ambiguity is a sign of epistemic maturity, not weakness
"""

import pytest

from babel.core.events import DualEventStore, EventType, capture_conversation
from babel.tracking.ambiguity import (
    QuestionTracker, OpenQuestion,
    format_question, format_questions_summary,
    detect_uncertainty, check_premature_resolution,
    UNCERTAINTY_SIGNALS, QUESTION_PATTERNS
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
    """Create question tracker."""
    return QuestionTracker(events)


# =============================================================================
# Uncertainty Detection Tests
# =============================================================================

class TestUncertaintyDetection:
    """Test uncertainty signal detection (AI uses these)."""
    
    def test_detect_uncertainty_positive(self):
        """Detects uncertainty language."""
        assert detect_uncertainty("I'm not sure if this is right") is True
        assert detect_uncertainty("Maybe we should use Redis") is True
        assert detect_uncertainty("This might need to be revisited") is True
        assert detect_uncertainty("Unclear how this will scale") is True
        assert detect_uncertainty("TBD: decide on database") is True
    
    def test_detect_uncertainty_negative(self):
        """No false positives on certain statements."""
        assert detect_uncertainty("Use PostgreSQL for data storage") is False
        assert detect_uncertainty("The API returns JSON") is False
        assert detect_uncertainty("Deploy on AWS") is False
    
    def test_uncertainty_signals_list(self):
        """UNCERTAINTY_SIGNALS is non-empty."""
        assert len(UNCERTAINTY_SIGNALS) > 0
        assert "not sure" in UNCERTAINTY_SIGNALS
        assert "uncertain" in UNCERTAINTY_SIGNALS


# =============================================================================
# Question Pattern Detection Tests
# =============================================================================

class TestQuestionPatternDetection:
    """Test question pattern detection (AI uses these)."""
    
    def test_question_patterns_positive(self):
        """Detects question patterns."""
        from babel.tracking.ambiguity import detect_question
        
        assert detect_question("Open question: how should we handle auth?") is True
        assert detect_question("How should we scale the database?") is True
        assert detect_question("We don't know the best approach yet") is True
        assert detect_question("TBD: caching strategy") is True
    
    def test_question_patterns_negative(self):
        """No false positives on statements."""
        from babel.tracking.ambiguity import detect_question
        
        assert detect_question("Use Redis for caching") is False
        assert detect_question("The system handles 1000 requests") is False
    
    def test_question_patterns_list(self):
        """QUESTION_PATTERNS is non-empty."""
        assert len(QUESTION_PATTERNS) > 0
        assert "open question:" in QUESTION_PATTERNS


# =============================================================================
# Question Tracker Tests
# =============================================================================

class TestQuestionTracker:
    """Test QuestionTracker functionality."""
    
    def test_raise_question(self, tracker):
        """Can raise an open question."""
        question = tracker.raise_question(
            content="How should we handle offline sync?",
            context="Users need to work offline",
            domain="architecture"
        )
        
        assert question.content == "How should we handle offline sync?"
        assert question.context == "Users need to work offline"
        assert question.domain == "architecture"
        assert question.status == "open"
    
    def test_get_open_questions(self, tracker):
        """Can get all open questions."""
        tracker.raise_question("Question 1")
        tracker.raise_question("Question 2")
        tracker.raise_question("Question 3")
        
        questions = tracker.get_open_questions()
        assert len(questions) == 3
    
    def test_resolve_question(self, tracker):
        """Can resolve an open question."""
        question = tracker.raise_question("How to handle auth?")
        
        success = tracker.resolve(
            question_id=question.id,
            resolution="Use OAuth2 with JWT tokens",
            outcome="answered"
        )
        
        assert success is True
        
        # Should not be in open questions anymore
        open_questions = tracker.get_open_questions()
        assert len(open_questions) == 0
        
        # Should be in resolved
        resolved = tracker.get_resolved_questions()
        assert len(resolved) == 1
    
    def test_cannot_resolve_nonexistent(self, tracker):
        """Cannot resolve a question that doesn't exist."""
        success = tracker.resolve(
            question_id="nonexistent",
            resolution="Answer",
            outcome="answered"
        )
        
        assert success is False
    
    def test_cannot_resolve_twice(self, tracker):
        """Cannot resolve already resolved question."""
        question = tracker.raise_question("Question")
        
        tracker.resolve(question.id, "Answer", "answered")
        success = tracker.resolve(question.id, "Another answer", "answered")
        
        assert success is False
    
    def test_resolve_outcomes(self, tracker):
        """Different resolution outcomes work."""
        q1 = tracker.raise_question("Question 1")
        q2 = tracker.raise_question("Question 2")
        q3 = tracker.raise_question("Question 3")
        
        tracker.resolve(q1.id, "Found the answer", "answered")
        tracker.resolve(q2.id, "No longer relevant", "dissolved")
        tracker.resolve(q3.id, "Replaced by better question", "superseded")
        
        resolved = tracker.get_resolved_questions()
        outcomes = [q.resolution["outcome"] for q in resolved]
        
        assert "answered" in outcomes
        assert "dissolved" in outcomes
        assert "superseded" in outcomes
    
    def test_count_open(self, tracker):
        """Can count open questions."""
        assert tracker.count_open() == 0
        
        tracker.raise_question("Q1")
        tracker.raise_question("Q2")
        
        assert tracker.count_open() == 2
        
        q3 = tracker.raise_question("Q3")
        tracker.resolve(q3.id, "Answer", "answered")
        
        assert tracker.count_open() == 2
    
    def test_get_by_domain(self, tracker):
        """Can filter questions by domain."""
        tracker.raise_question("Security question", domain="security")
        tracker.raise_question("Performance question", domain="performance")
        tracker.raise_question("Another security question", domain="security")
        
        security_questions = tracker.get_by_domain("security")
        assert len(security_questions) == 2
        
        perf_questions = tracker.get_by_domain("performance")
        assert len(perf_questions) == 1


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Test question statistics."""
    
    def test_stats_empty(self, tracker):
        """Stats work with no data."""
        stats = tracker.stats()
        
        assert stats["total"] == 0
        assert stats["open"] == 0
        assert stats["resolved"] == 0
    
    def test_stats_with_data(self, tracker):
        """Stats reflect actual data."""
        tracker.raise_question("Q1")
        tracker.raise_question("Q2")
        q3 = tracker.raise_question("Q3")
        
        tracker.resolve(q3.id, "Answer", "answered")
        
        stats = tracker.stats()
        
        assert stats["total"] == 3
        assert stats["open"] == 2
        assert stats["resolved"] == 1


# =============================================================================
# Premature Resolution Check Tests
# =============================================================================

class TestPrematureResolutionCheck:
    """Test premature resolution warning (P10 compliance)."""
    
    def test_no_warning_with_sufficient_evidence(self):
        """No warning when evidence is sufficient."""
        check = check_premature_resolution(evidence_count=2)
        
        assert check["is_premature"] is False
        assert check["warning"] is None
    
    def test_warning_with_insufficient_evidence(self):
        """Warning when evidence is insufficient."""
        check = check_premature_resolution(evidence_count=0)
        
        assert check["is_premature"] is True
        assert "premature" in check["warning"].lower()
        assert check["recommendation"] is not None
    
    def test_warning_with_one_evidence(self):
        """Warning with only one evidence item."""
        check = check_premature_resolution(evidence_count=1)
        
        assert check["is_premature"] is True
        assert "1 evidence" in check["warning"]
    
    def test_custom_threshold(self):
        """Can customize minimum evidence threshold."""
        check = check_premature_resolution(evidence_count=2, min_evidence=3)
        
        assert check["is_premature"] is True
        
        check = check_premature_resolution(evidence_count=3, min_evidence=3)
        assert check["is_premature"] is False


# =============================================================================
# Formatting Tests
# =============================================================================

class TestFormatting:
    """Test formatting functions."""
    
    def test_format_question(self, tracker):
        """Format a question for display."""
        question = tracker.raise_question(
            content="How to handle caching?",
            context="Need better performance",
            domain="performance"
        )
        
        output = format_question(question)
        
        assert "?" in output  # Status icon
        assert "How to handle caching?" in output
        assert "performance" in output
    
    def test_format_question_verbose(self, tracker):
        """Format a question with verbose details."""
        question = tracker.raise_question(
            content="How to handle caching?",
            context="Need better performance"
        )
        
        output = format_question(question, verbose=True)
        
        assert "Context:" in output
        assert "Need better performance" in output
    
    def test_format_questions_summary_empty(self, tracker):
        """Format summary with no questions."""
        output = format_questions_summary(tracker)
        
        assert "No open questions" in output
    
    def test_format_questions_summary_with_data(self, tracker):
        """Format summary with questions."""
        tracker.raise_question("Q1")
        tracker.raise_question("Q2")
        
        output = format_questions_summary(tracker)
        
        assert "Open Questions: 2" in output
        assert "not failures" in output.lower()


# =============================================================================
# OpenQuestion Model Tests
# =============================================================================

class TestOpenQuestionModel:
    """Test OpenQuestion dataclass."""
    
    def test_from_event(self, events):
        """Can create from event."""
        from babel.core.events import raise_question
        from babel.core.scope import EventScope
        
        event = raise_question("Test question", context="Test context")
        events.append(event, scope=EventScope.SHARED)
        
        question = OpenQuestion.from_event(event)
        
        assert question.id == event.id
        assert question.content == "Test question"
        assert question.context == "Test context"
        assert question.status == "open"
    
    def test_to_dict(self, tracker):
        """Can convert to dictionary."""
        question = tracker.raise_question(
            content="Test question",
            domain="architecture"
        )
        
        d = question.to_dict()
        
        assert d["id"] == question.id
        assert d["content"] == "Test question"
        assert d["domain"] == "architecture"
        assert d["status"] == "open"


# =============================================================================
# P10 Principle Tests
# =============================================================================

class TestP10Principles:
    """Test P10 principle compliance."""
    
    def test_ambiguity_explicitly_recorded(self, tracker):
        """P10: Ambiguity is explicitly recorded as questions."""
        question = tracker.raise_question(
            content="We don't know how to scale yet",
            context="Unknown territory"
        )
        
        # Question is a first-class artifact
        assert question.id is not None
        assert question.status == "open"
        
        # It's retrievable
        retrieved = tracker.get_question(question.id)
        assert retrieved is not None
    
    def test_unresolved_as_first_class(self, tracker):
        """P10: Unresolved questions are tracked as first-class artifacts."""
        tracker.raise_question("Q1")
        tracker.raise_question("Q2")
        
        # Open questions are queryable
        open_questions = tracker.get_open_questions()
        assert len(open_questions) == 2
        
        # They're counted
        assert tracker.count_open() == 2
        
        # They appear in stats
        stats = tracker.stats()
        assert stats["open"] == 2
    
    def test_premature_resolution_flagged(self):
        """P10: Premature resolution is considered a failure mode."""
        check = check_premature_resolution(evidence_count=0)
        
        assert check["is_premature"] is True
        assert "premature" in check["warning"].lower()
    
    def test_holding_ambiguity_valid(self, tracker):
        """P10: Holding ambiguity is valid — questions can stay open."""
        question = tracker.raise_question("Unresolved question")
        
        # It's okay to not resolve
        assert question.status == "open"
        
        # No system pressure to close
        open_questions = tracker.get_open_questions()
        assert len(open_questions) == 1
        
        # Status shows it positively
        output = format_questions_summary(tracker)
        assert "not failures" in output.lower()


# =============================================================================
# Event Integration Tests
# =============================================================================

class TestEventIntegration:
    """Test integration with event system."""
    
    def test_questions_stored_as_events(self, tracker, events):
        """Questions are stored as events."""
        tracker.raise_question("Test question")
        
        question_events = events.read_by_type(EventType.QUESTION_RAISED)
        assert len(question_events) == 1
    
    def test_questions_shared_by_default(self, events):
        """Questions are stored in shared scope."""
        tracker = QuestionTracker(events)
        tracker.raise_question("Shared question")
        
        shared = events.read_shared()
        assert len(shared) == 1
        assert shared[0].type == EventType.QUESTION_RAISED
    
    def test_capture_with_uncertainty_flag(self, events):
        """Captures can be marked uncertain (P10)."""
        event = capture_conversation(
            content="Use Redis for caching",
            uncertain=True,
            uncertainty_reason="Not sure about scaling"
        )
        
        assert event.data.get("uncertain") is True
        assert event.data.get("uncertainty_reason") == "Not sure about scaling"
