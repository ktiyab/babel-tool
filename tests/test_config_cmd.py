"""
Tests for ConfigCommand — Configuration management and queue processing

Tests the configuration operations:
- Processing queued extractions (batch mode for AI)
- Displaying current configuration
- Setting configuration values

Aligns with:
- P5: Tests ARE evidence for implementation
- HC2: Human authority (batch mode enables AI assistants)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from babel.commands.config_cmd import ConfigCommand
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def config_command(babel_factory):
    """Create ConfigCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # ConfigCommand needs extractor for queue processing
    cli.extractor = Mock()
    cli.extractor.is_available = True
    cli.extractor.queue = Mock()
    cli.extractor.queue.count.return_value = 0
    cli.extractor.process_queue = Mock(return_value=[])
    cli.extractor.format_for_confirmation = Mock(return_value="Formatted proposal")

    # ConfigCommand needs config_manager for display/set
    cli.config_manager = Mock()
    cli.config_manager.display.return_value = "Config display output"
    cli.config_manager.set.return_value = None  # No error
    cli.config_manager.project_config_path = Path("/fake/project/.babel/config.yaml")
    cli.config_manager.user_config_path = Path("/fake/user/.babel/config.yaml")

    # Need capture command for proposals
    cli._capture_cmd = Mock()
    cli._capture_cmd._queue_proposal = Mock()
    cli._capture_cmd._confirm_proposal = Mock()

    # Create command instance
    cmd = ConfigCommand.__new__(ConfigCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Helper Classes
# =============================================================================

class MockProposal:
    """Mock proposal object for testing."""
    def __init__(self, artifact_type="decision", summary="Test proposal"):
        self.artifact_type = artifact_type
        self.content = {"summary": summary}


# =============================================================================
# Process Queue Tests
# =============================================================================

class TestProcessQueue:
    """Test process_queue method for queued extraction processing."""

    def test_shows_unavailable_when_no_extractor(self, config_command, capsys):
        """Shows message when AI extraction not available."""
        cmd, factory = config_command
        cmd._cli.extractor.is_available = False

        cmd.process_queue()

        captured = capsys.readouterr()
        assert "not available" in captured.out.lower()

    def test_shows_no_queue_when_queue_missing(self, config_command, capsys):
        """Shows message when no queue configured."""
        cmd, factory = config_command
        cmd._cli.extractor.queue = None

        cmd.process_queue()

        captured = capsys.readouterr()
        assert "No queue configured" in captured.out

    def test_shows_no_items_when_queue_empty(self, config_command, capsys):
        """Shows message when queue is empty."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 0

        cmd.process_queue()

        captured = capsys.readouterr()
        assert "No items queued" in captured.out

    def test_processes_queued_items(self, config_command, capsys):
        """Processes queued items and extracts proposals."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 2

        proposals = [MockProposal("decision", "Test decision")]
        cmd._cli.extractor.process_queue.return_value = proposals

        with patch('babel.output.end_command'):
            # Interactive mode - mock input
            with patch('builtins.input', return_value='y'):
                cmd.process_queue(batch_mode=False)

        captured = capsys.readouterr()
        assert "Processing 2 queued item(s)" in captured.out

    def test_batch_mode_queues_proposals(self, config_command, capsys):
        """Batch mode queues proposals for later review."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 1

        proposals = [
            MockProposal("decision", "Decision 1"),
            MockProposal("constraint", "Constraint 1"),
        ]
        cmd._cli.extractor.process_queue.return_value = proposals

        with patch('babel.output.end_command'):
            cmd.process_queue(batch_mode=True)

        captured = capsys.readouterr()
        assert "Queued 2 proposal(s) for review" in captured.out
        assert "babel review" in captured.out
        # Verify proposals were queued
        assert cmd._cli._capture_cmd._queue_proposal.call_count == 2

    def test_shows_no_artifacts_when_extraction_empty(self, config_command, capsys):
        """Shows message when extraction yields no artifacts."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 1
        cmd._cli.extractor.process_queue.return_value = []

        cmd.process_queue()

        captured = capsys.readouterr()
        assert "No artifacts extracted" in captured.out

    def test_interactive_mode_confirms_proposals(self, config_command, capsys):
        """Interactive mode prompts for confirmation."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 1

        proposals = [MockProposal("decision", "Test")]
        cmd._cli.extractor.process_queue.return_value = proposals

        with patch('babel.output.end_command'):
            with patch('builtins.input', return_value='y'):
                cmd.process_queue(batch_mode=False)

        captured = capsys.readouterr()
        assert "Confirmed" in captured.out
        cmd._cli._capture_cmd._confirm_proposal.assert_called_once()

    def test_interactive_mode_skips_on_no(self, config_command, capsys):
        """Interactive mode skips proposal on 'n' input."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 1

        proposals = [MockProposal("decision", "Test")]
        cmd._cli.extractor.process_queue.return_value = proposals

        with patch('babel.output.end_command'):
            with patch('builtins.input', return_value='n'):
                cmd.process_queue(batch_mode=False)

        captured = capsys.readouterr()
        assert "Skipped" in captured.out
        cmd._cli._capture_cmd._confirm_proposal.assert_not_called()


# =============================================================================
# Show Config Tests
# =============================================================================

class TestShowConfig:
    """Test show_config method for configuration display."""

    def test_displays_configuration(self, config_command, capsys):
        """Displays current configuration."""
        cmd, factory = config_command
        cmd._cli.config_manager.display.return_value = "provider: anthropic\nmodel: claude-3"

        with patch('babel.output.end_command'):
            cmd.show_config()

        captured = capsys.readouterr()
        assert "provider: anthropic" in captured.out
        assert "model: claude-3" in captured.out

    def test_calls_config_manager_display(self, config_command):
        """Calls config_manager.display()."""
        cmd, factory = config_command

        with patch('babel.output.end_command'):
            cmd.show_config()

        cmd._cli.config_manager.display.assert_called_once()


# =============================================================================
# Set Config Tests
# =============================================================================

class TestSetConfig:
    """Test set_config method for setting configuration values."""

    def test_sets_project_config_by_default(self, config_command, capsys):
        """Sets project-scoped config by default."""
        cmd, factory = config_command

        cmd.set_config("llm.provider", "openai")

        captured = capsys.readouterr()
        assert "Set llm.provider = openai" in captured.out
        assert "project" in captured.out.lower() or str(cmd._cli.config_manager.project_config_path) in captured.out
        cmd._cli.config_manager.set.assert_called_with("llm.provider", "openai", "project")

    def test_sets_user_config_when_specified(self, config_command, capsys):
        """Sets user-scoped config when scope='user'."""
        cmd, factory = config_command

        cmd.set_config("llm.model", "gpt-4", scope="user")

        captured = capsys.readouterr()
        assert "Set llm.model = gpt-4" in captured.out
        cmd._cli.config_manager.set.assert_called_with("llm.model", "gpt-4", "user")

    def test_shows_error_on_invalid_key(self, config_command, capsys):
        """Shows error message when config_manager returns error."""
        cmd, factory = config_command
        cmd._cli.config_manager.set.return_value = "Invalid key: foo.bar"

        cmd.set_config("foo.bar", "value")

        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "Invalid key" in captured.out

    def test_shows_saved_path_for_project(self, config_command, capsys):
        """Shows project config path when saved."""
        cmd, factory = config_command

        cmd.set_config("test.key", "test_value", scope="project")

        captured = capsys.readouterr()
        assert "Saved to" in captured.out

    def test_shows_saved_path_for_user(self, config_command, capsys):
        """Shows user config path when saved."""
        cmd, factory = config_command

        cmd.set_config("test.key", "test_value", scope="user")

        captured = capsys.readouterr()
        assert "Saved to" in captured.out


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_unicode_in_config_value(self, config_command, capsys):
        """Handles Unicode in config values."""
        cmd, factory = config_command

        cmd.set_config("display.emoji", "🎉")

        captured = capsys.readouterr()
        assert "Set display.emoji" in captured.out

    def test_handles_empty_proposal_summary(self, config_command, capsys):
        """Handles proposals with missing summary."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 1

        proposal = MockProposal("decision", "")
        proposal.content = {}  # No summary
        cmd._cli.extractor.process_queue.return_value = [proposal]

        with patch('babel.output.end_command'):
            cmd.process_queue(batch_mode=True)

        # Should not crash
        captured = capsys.readouterr()
        assert "Queued" in captured.out

    def test_handles_extractor_exception(self, config_command, capsys):
        """Handles exception from extractor.process_queue."""
        cmd, factory = config_command
        cmd._cli.extractor.queue.count.return_value = 1
        cmd._cli.extractor.process_queue.side_effect = Exception("Extraction failed")

        with pytest.raises(Exception, match="Extraction failed"):
            cmd.process_queue()
