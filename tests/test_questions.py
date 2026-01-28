"""
Tests for QuestionsCommand — P10 Ambiguity Management (Open Questions)

Tests the question and ambiguity handling:
- Raising open questions
- Viewing question status
- Resolving questions with different outcomes
- OutputSpec format for rendering

Aligns with:
- P5: Tests ARE evidence for implementation
- P10: Ambiguity Management (holding uncertainty is epistemic maturity)
"""

import pytest
from unittest.mock import Mock, patch

from babel.commands.questions import QuestionsCommand
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def questions_command(babel_factory):
    """Create QuestionsCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # QuestionsCommand needs questions tracker
    cli.questions = Mock()
    cli.questions.raise_question = Mock()
    cli.questions.get_open_questions = Mock(return_value=[])
    cli.questions.count_open = Mock(return_value=0)
    cli.questions.stats = Mock(return_value={"open": 0, "resolved": 0})
    cli.questions.resolve = Mock(return_value=True)

    # Create command instance
    cmd = QuestionsCommand.__new__(QuestionsCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Helper Classes for Mocking
# =============================================================================

class MockQuestion:
    """Mock question object for testing."""
    def __init__(self, qid, content, domain=None, context=None, status="open"):
        from datetime import datetime, timezone
        self.id = qid
        self.content = content
        self.domain = domain
        self.context = context
        self.status = status
        self.created_at = datetime.now(timezone.utc)  # P12: Time always shown


# =============================================================================
# Question (Raise) Tests
# =============================================================================

class TestQuestionRaise:
    """Test question method for raising open questions (P10)."""

    def test_raises_question_successfully(self, questions_command, capsys):
        """Raises an open question successfully."""
        cmd, factory = questions_command

        # Mock the return value
        mock_question = MockQuestion("q_123", "Should we use caching?", domain="performance")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            cmd.question("Should we use caching?")

        captured = capsys.readouterr()
        assert "Open question raised" in captured.out
        assert "caching" in captured.out

    def test_raises_question_with_context(self, questions_command, capsys):
        """Raises question with context information."""
        cmd, factory = questions_command

        mock_question = MockQuestion("q_124", "REST or GraphQL?", context="API design choice")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            cmd.question("REST or GraphQL?", context="API design choice")

        captured = capsys.readouterr()
        assert "Context:" in captured.out
        assert "API design choice" in captured.out

    def test_raises_question_with_domain(self, questions_command, capsys):
        """Raises question with explicit domain."""
        cmd, factory = questions_command

        mock_question = MockQuestion("q_125", "Test question", domain="testing")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            with patch('babel.commands.questions.validate_domain', return_value=True):
                cmd.question("Test question", domain="testing")

        captured = capsys.readouterr()
        assert "[testing]" in captured.out

    def test_warns_on_unknown_domain(self, questions_command, capsys):
        """Warns when using unknown domain."""
        cmd, factory = questions_command

        mock_question = MockQuestion("q_126", "Question", domain="unknown_domain")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            with patch('babel.commands.questions.validate_domain', return_value=False):
                cmd.question("Question", domain="unknown_domain")

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "unknown" in captured.out.lower()

    def test_auto_suggests_domain(self, questions_command, capsys):
        """Auto-suggests domain when not provided."""
        cmd, factory = questions_command

        mock_question = MockQuestion("q_127", "Database choice?", domain="database")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            with patch('babel.commands.questions.suggest_domain_for_capture', return_value="database"):
                cmd.question("Database choice?")

        # Should pass suggested domain to raise_question
        cmd._cli.questions.raise_question.assert_called_once()
        call_args = cmd._cli.questions.raise_question.call_args
        assert call_args.kwargs.get('domain') == "database" or call_args[1].get('domain') == "database"

    def test_shows_resolution_hint(self, questions_command, capsys):
        """Shows hint about resolving questions."""
        cmd, factory = questions_command

        mock_question = MockQuestion("q_128", "Test?")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            cmd.question("Test?")

        captured = capsys.readouterr()
        assert "resolve-question" in captured.out
        assert "acknowledged unknown" in captured.out.lower()


# =============================================================================
# Questions List Tests
# =============================================================================

class TestQuestionsList:
    """Test questions_cmd method for listing open questions."""

    def test_shows_no_questions_message(self, questions_command, capsys):
        """Shows appropriate message when no questions."""
        cmd, factory = questions_command
        cmd._cli.questions.get_open_questions.return_value = []

        with patch('babel.commands.questions.format_questions_summary', return_value="No open questions"):
            with patch('babel.output.end_command'):
                cmd.questions_cmd()

        captured = capsys.readouterr()
        assert "No open questions" in captured.out

    def test_lists_open_questions(self, questions_command, capsys):
        """Lists open questions."""
        cmd, factory = questions_command

        questions = [
            MockQuestion("q1", "Question 1", status="open"),
            MockQuestion("q2", "Question 2", status="open"),
        ]
        cmd._cli.questions.get_open_questions.return_value = questions
        cmd._cli.questions.count_open.return_value = 2

        with patch('babel.commands.questions.format_questions_summary', return_value="2 open questions"):
            with patch('babel.output.end_command'):
                cmd.questions_cmd()

        captured = capsys.readouterr()
        assert "2 open questions" in captured.out

    def test_verbose_shows_details(self, questions_command, capsys):
        """Verbose mode shows full question details."""
        cmd, factory = questions_command

        questions = [MockQuestion("q1", "Detailed question", context="Important context")]
        cmd._cli.questions.get_open_questions.return_value = questions

        with patch('babel.commands.questions.format_questions_summary', return_value="1 question"):
            with patch('babel.commands.questions.format_question', return_value="[q1] Detailed question"):
                with patch('babel.output.end_command'):
                    cmd.questions_cmd(verbose=True)

        captured = capsys.readouterr()
        assert "[q1]" in captured.out or "Detailed" in captured.out

    def test_full_shows_untruncated(self, questions_command, capsys):
        """Full mode shows untruncated content."""
        cmd, factory = questions_command

        with patch('babel.commands.questions.format_questions_summary') as mock_format:
            mock_format.return_value = "Full content"
            with patch('babel.output.end_command'):
                cmd.questions_cmd(full=True)

            # Verify full=True was passed
            mock_format.assert_called_once()
            assert mock_format.call_args.kwargs.get('full') == True

    def test_returns_output_spec_when_format_requested(self, questions_command):
        """Returns OutputSpec when output_format specified."""
        cmd, factory = questions_command

        questions = [MockQuestion("q1", "Test question", domain="test", status="open")]
        cmd._cli.questions.get_open_questions.return_value = questions
        cmd._cli.questions.stats.return_value = {"open": 1, "resolved": 0}

        result = cmd.questions_cmd(output_format="table")

        assert result is not None
        assert hasattr(result, 'data')
        assert hasattr(result, 'shape')
        assert result.shape == "table"


# =============================================================================
# Resolve Question Tests
# =============================================================================

class TestResolveQuestion:
    """Test resolve_question method."""

    def test_resolves_question_answered(self, questions_command, capsys):
        """Resolves question with 'answered' outcome."""
        cmd, factory = questions_command

        question = MockQuestion("q_resolve1", "What database?", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_resolve1")
        cmd._cli.questions.resolve.return_value = True

        with patch('babel.output.end_command'):
            cmd.resolve_question("q_resolve1", "Use PostgreSQL", outcome="answered")

        captured = capsys.readouterr()
        assert "resolved" in captured.out.lower()
        assert "answered" in captured.out

    def test_resolves_question_dissolved(self, questions_command, capsys):
        """Resolves question with 'dissolved' outcome."""
        cmd, factory = questions_command

        question = MockQuestion("q_resolve2", "Obsolete question", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_resolve2")

        with patch('babel.output.end_command'):
            cmd.resolve_question("q_resolve2", "No longer relevant", outcome="dissolved")

        captured = capsys.readouterr()
        assert "resolved" in captured.out.lower()
        assert "dissolved" in captured.out

    def test_resolves_question_superseded(self, questions_command, capsys):
        """Resolves question with 'superseded' outcome."""
        cmd, factory = questions_command

        question = MockQuestion("q_resolve3", "Old question", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_resolve3")

        with patch('babel.output.end_command'):
            cmd.resolve_question("q_resolve3", "Replaced by new question", outcome="superseded")

        captured = capsys.readouterr()
        assert "resolved" in captured.out.lower()
        assert "superseded" in captured.out

    def test_error_question_not_found(self, questions_command, capsys):
        """Shows error when question not found."""
        cmd, factory = questions_command

        cmd._cli.questions.get_open_questions.return_value = []
        cmd._cli.resolve_id = Mock(return_value=None)

        cmd.resolve_question("nonexistent", "Resolution")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_error_invalid_outcome(self, questions_command, capsys):
        """Shows error for invalid outcome."""
        cmd, factory = questions_command

        question = MockQuestion("q_invalid", "Test", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_invalid")

        cmd.resolve_question("q_invalid", "Resolution", outcome="invalid_outcome")

        captured = capsys.readouterr()
        assert "Invalid outcome" in captured.out
        assert "answered" in captured.out  # Should list valid outcomes

    def test_shows_remaining_questions(self, questions_command, capsys):
        """Shows remaining questions count after resolution."""
        cmd, factory = questions_command

        question = MockQuestion("q_remaining", "Test", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_remaining")
        cmd._cli.questions.count_open.return_value = 2  # 2 remaining

        cmd.resolve_question("q_remaining", "Done")

        # Verify output shows remaining count
        captured = capsys.readouterr()
        assert "2 question(s) remaining" in captured.out

    def test_handles_resolve_failure(self, questions_command, capsys):
        """Handles failure from questions.resolve."""
        cmd, factory = questions_command

        question = MockQuestion("q_fail", "Test", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_fail")
        cmd._cli.questions.resolve.return_value = False

        cmd.resolve_question("q_fail", "Resolution")

        captured = capsys.readouterr()
        assert "Failed" in captured.out


# =============================================================================
# OutputSpec Tests
# =============================================================================

class TestQuestionsOutputSpec:
    """Test _questions_as_output for OutputSpec format."""

    def test_returns_correct_shape(self, questions_command):
        """Returns OutputSpec with correct table shape."""
        cmd, factory = questions_command

        cmd._cli.questions.get_open_questions.return_value = []
        cmd._cli.questions.stats.return_value = {"open": 0, "resolved": 0}

        result = cmd._questions_as_output()

        assert result.shape == "table"
        assert "questions" in result.title.lower() or "Questions" in result.title

    def test_includes_question_data(self, questions_command):
        """OutputSpec includes question data rows."""
        cmd, factory = questions_command

        questions = [
            MockQuestion("q1", "First question", domain="testing", status="open", context="Test context"),
            MockQuestion("q2", "Second question", domain=None, status="open"),
        ]
        cmd._cli.questions.get_open_questions.return_value = questions
        cmd._cli.questions.stats.return_value = {"open": 2, "resolved": 1}

        result = cmd._questions_as_output()

        assert len(result.data) == 2
        assert "question" in result.data[0]
        assert "status" in result.data[0]

    def test_truncates_long_content(self, questions_command):
        """Truncates long content by default using SUMMARY_LENGTH."""
        cmd, factory = questions_command

        # Content longer than SUMMARY_LENGTH (120) to trigger truncation
        long_content = "A" * 200
        questions = [MockQuestion("q1", long_content, status="open")]
        cmd._cli.questions.get_open_questions.return_value = questions
        cmd._cli.questions.stats.return_value = {"open": 1, "resolved": 0}

        result = cmd._questions_as_output(full=False)

        # Should be truncated to SUMMARY_LENGTH (120) or less via generate_summary
        assert len(result.data[0]["question"]) <= 120

    def test_full_mode_no_truncation(self, questions_command):
        """Full mode shows complete content."""
        cmd, factory = questions_command

        long_content = "A" * 200
        questions = [MockQuestion("q1", long_content, status="open")]
        cmd._cli.questions.get_open_questions.return_value = questions
        cmd._cli.questions.stats.return_value = {"open": 1, "resolved": 0}

        result = cmd._questions_as_output(full=True)

        # Should NOT be truncated
        assert len(result.data[0]["question"]) == 200

    def test_shows_resolved_count_in_title(self, questions_command):
        """Shows resolved count in title when present."""
        cmd, factory = questions_command

        cmd._cli.questions.get_open_questions.return_value = []
        cmd._cli.questions.stats.return_value = {"open": 0, "resolved": 5}

        result = cmd._questions_as_output()

        assert "Resolved: 5" in result.title or "resolved" in result.title.lower()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_unicode_in_question(self, questions_command, capsys):
        """Handles Unicode in question content."""
        cmd, factory = questions_command

        mock_question = MockQuestion("q_unicode", "Question with 日本語 and 🎉")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            cmd.question("Question with 日本語 and 🎉")

        # Should not crash
        captured = capsys.readouterr()
        assert "Open question raised" in captured.out

    def test_handles_empty_context(self, questions_command, capsys):
        """Handles empty context string."""
        cmd, factory = questions_command

        mock_question = MockQuestion("q_empty", "Test?", context="")
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            cmd.question("Test?", context="")

        captured = capsys.readouterr()
        # Empty context should not show "Context:" line
        assert "Open question raised" in captured.out

    def test_handles_very_long_question(self, questions_command, capsys):
        """Handles very long question content."""
        cmd, factory = questions_command

        long_content = "Q" * 1000
        mock_question = MockQuestion("q_long", long_content)
        cmd._cli.questions.raise_question.return_value = mock_question

        with patch('babel.output.end_command'):
            cmd.question(long_content)

        # Should not crash
        captured = capsys.readouterr()
        assert "Open question raised" in captured.out

    def test_handles_special_chars_in_resolution(self, questions_command, capsys):
        """Handles special characters in resolution text."""
        cmd, factory = questions_command

        question = MockQuestion("q_special", "Test", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_special")

        with patch('babel.output.end_command'):
            cmd.resolve_question("q_special", "Resolution with <html> & 'quotes'")

        captured = capsys.readouterr()
        assert "resolved" in captured.out.lower()

    def test_prefix_matching_for_question_id(self, questions_command, capsys):
        """Uses prefix matching for question IDs."""
        cmd, factory = questions_command

        question = MockQuestion("q_full_id_12345", "Test", status="open")
        cmd._cli.questions.get_open_questions.return_value = [question]
        cmd._cli.resolve_id = Mock(return_value="q_full_id_12345")

        with patch('babel.output.end_command'):
            cmd.resolve_question("q_full", "Resolution")

        # Should resolve via prefix
        cmd._cli.resolve_id.assert_called_once()
        captured = capsys.readouterr()
        assert "resolved" in captured.out.lower()
