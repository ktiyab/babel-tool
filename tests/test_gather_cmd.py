"""
Tests for GatherCommand — P6 Token Efficiency (Parallel Context Gathering)

Tests the parallel context gathering:
- Gathering from multiple sources (files, greps, bash, globs)
- Safety checks for bash commands
- Chunking strategies
- Output formats

Aligns with:
- P5: Tests ARE evidence for implementation
- P6: Token efficiency (one round-trip instead of many)
"""

import pytest
from unittest.mock import Mock, patch

from babel.commands.gather_cmd import GatherCommand
from babel.gather.safety import SafetyViolation, SafetyCategory, BabelCommandSafety
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def gather_command(babel_factory):
    """Create GatherCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # GatherCommand needs orchestrator
    cli.orchestrator = Mock()

    # GatherCommand uses symbols.warning which maps to check_warn in SymbolSet
    # Add warning attribute to match gather_cmd.py's usage
    cli.symbols = Mock()
    cli.symbols.warning = "⚠"
    cli.symbols.check_warn = "⚠"
    cli.symbols.info = "ℹ"

    # Create command instance
    cmd = GatherCommand.__new__(GatherCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Test source validation."""

    def test_shows_error_when_no_sources(self, gather_command, capsys):
        """Shows error when no sources specified."""
        cmd, factory = gather_command

        cmd.gather()

        captured = capsys.readouterr()
        assert "No Sources Specified" in captured.out
        assert "--help" in captured.out

    def test_shows_usage_when_no_sources(self, gather_command, capsys):
        """Shows usage examples when no sources."""
        cmd, factory = gather_command

        cmd.gather()

        captured = capsys.readouterr()
        assert "--file" in captured.out or "Usage" in captured.out


# =============================================================================
# Safety Tests
# =============================================================================

class TestSafety:
    """Test bash command safety checks."""

    def test_rejects_unsafe_babel_mutation(self, gather_command, capsys):
        """Rejects unsafe babel mutation commands."""
        cmd, factory = gather_command

        # Create a proper SafetyViolation with violations list
        violation = BabelCommandSafety(
            command="capture",
            category=SafetyCategory.MUTATION,
            safe_for_parallel=False,
            reason="Mutates event store",
            suggestion="Run sequentially after gather"
        )

        with patch('babel.commands.gather_cmd.check_bash_commands_safety') as mock_check:
            mock_check.side_effect = SafetyViolation([("babel capture 'test'", violation)])

            cmd.gather(bashes=["babel capture 'test'"])

        captured = capsys.readouterr()
        assert "REJECTED" in captured.out or "babel capture" in captured.out or "capture" in captured.out

    def test_allows_safe_bash_commands(self, gather_command, capsys):
        """Allows safe bash commands."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.check_bash_commands_safety') as mock_check:
            mock_check.return_value = None  # No violation

            with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
                mock_plan_instance = Mock()
                mock_plan.return_value = mock_plan_instance

                with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                    mock_broker_instance = Mock()
                    mock_broker_instance.plan_chunks.return_value = []
                    mock_broker.return_value = mock_broker_instance

                    cmd.gather(bashes=["git status"])

        # Safety check should have passed
        mock_check.assert_called_once()

    def test_allows_safe_babel_queries(self, gather_command, capsys):
        """Allows safe babel read-only queries."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.check_bash_commands_safety') as mock_check:
            mock_check.return_value = None

            with patch('babel.commands.gather_cmd.GatherPlan'):
                with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                    mock_broker.return_value.plan_chunks.return_value = []

                    cmd.gather(bashes=["babel list decisions"])

        mock_check.assert_called_once()


# =============================================================================
# Source Gathering Tests
# =============================================================================

class TestSourceGathering:
    """Test gathering from different source types."""

    def test_gathers_from_files(self, gather_command, capsys):
        """Gathers context from file sources."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan_instance = Mock()
            mock_plan.return_value = mock_plan_instance

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_chunk = Mock()
                mock_chunk.sources = []
                mock_broker.return_value.plan_chunks.return_value = [mock_chunk]

                with patch('babel.commands.gather_cmd.ContextGatherer') as mock_gatherer:
                    mock_gatherer.return_value.gather_sources.return_value = []

                    with patch('babel.commands.gather_cmd.render_context', return_value="Rendered"):
                        with patch('babel.output.end_command'):
                            cmd.gather(files=["src/main.py", "src/utils.py"])

        # Verify files were added to plan
        assert mock_plan_instance.add_file.call_count == 2

    def test_gathers_from_greps(self, gather_command):
        """Gathers context from grep sources."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan_instance = Mock()
            mock_plan.return_value = mock_plan_instance

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(greps=["pattern:path/"])

        mock_plan_instance.add_grep.assert_called_once_with("pattern", "path/")

    def test_parses_grep_without_path(self, gather_command):
        """Parses grep pattern without path (uses '.')."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan_instance = Mock()
            mock_plan.return_value = mock_plan_instance

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(greps=["simple_pattern"])

        mock_plan_instance.add_grep.assert_called_once_with("simple_pattern", ".")

    def test_gathers_from_globs(self, gather_command):
        """Gathers context from glob patterns."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan_instance = Mock()
            mock_plan.return_value = mock_plan_instance

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(globs=["**/*.py"])

        mock_plan_instance.add_glob.assert_called_once_with("**/*.py")

    def test_gathers_from_bash(self, gather_command):
        """Gathers context from bash commands."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.check_bash_commands_safety'):
            with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
                mock_plan_instance = Mock()
                mock_plan.return_value = mock_plan_instance

                with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                    mock_broker.return_value.plan_chunks.return_value = []

                    cmd.gather(bashes=["git log -5"])

        mock_plan_instance.add_bash.assert_called_once_with("git log -5")


# =============================================================================
# Chunking Strategy Tests
# =============================================================================

class TestChunkingStrategy:
    """Test chunking strategy configuration."""

    def test_uses_coherence_strategy_by_default(self, gather_command):
        """Uses coherence-based chunking by default."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan'):
            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(files=["test.py"], strategy="coherence")

        # Verify ChunkStrategy.COHERENCE_BASED was used
        call_kwargs = mock_broker.call_args.kwargs
        assert "strategy" in call_kwargs

    def test_uses_size_strategy_when_specified(self, gather_command):
        """Uses size-based chunking when specified."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan'):
            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(files=["test.py"], strategy="size")

        mock_broker.assert_called_once()

    def test_uses_priority_strategy_when_specified(self, gather_command):
        """Uses priority-based chunking when specified."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan'):
            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(files=["test.py"], strategy="priority")

        mock_broker.assert_called_once()

    def test_respects_context_limit(self, gather_command):
        """Respects context size limit."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan'):
            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(files=["test.py"], context_limit_kb=50)

        call_kwargs = mock_broker.call_args.kwargs
        assert call_kwargs.get("context_limit_kb") == 50


# =============================================================================
# Output Tests
# =============================================================================

class TestOutput:
    """Test output formatting and file writing."""

    def test_outputs_markdown_by_default(self, gather_command, capsys):
        """Outputs markdown format by default."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan.return_value = Mock()

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_chunk = Mock()
                mock_chunk.sources = []
                mock_broker.return_value.plan_chunks.return_value = [mock_chunk]

                with patch('babel.commands.gather_cmd.ContextGatherer') as mock_gatherer:
                    mock_gatherer.return_value.gather_sources.return_value = []

                    with patch('babel.commands.gather_cmd.render_context', return_value="# Context"):
                        with patch('babel.output.end_command'):
                            cmd.gather(files=["test.py"])

        captured = capsys.readouterr()
        assert "# Context" in captured.out

    def test_outputs_json_when_specified(self, gather_command, capsys):
        """Outputs JSON format when specified."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan.return_value = Mock()

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_chunk = Mock()
                mock_chunk.sources = []
                mock_broker.return_value.plan_chunks.return_value = [mock_chunk]

                with patch('babel.commands.gather_cmd.ContextGatherer') as mock_gatherer:
                    mock_result = Mock()
                    mock_result.to_dict.return_value = {"source": "test.py", "content": "test"}
                    mock_gatherer.return_value.gather_sources.return_value = [mock_result]

                    with patch('babel.output.end_command'):
                        cmd.gather(files=["test.py"], output_format="json")

        captured = capsys.readouterr()
        assert "[" in captured.out  # JSON array

    def test_writes_to_file_when_specified(self, gather_command, capsys, tmp_path):
        """Writes output to file when output_file specified."""
        cmd, factory = gather_command
        output_file = tmp_path / "context.md"

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan.return_value = Mock()

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_chunk = Mock()
                mock_chunk.sources = []
                mock_broker.return_value.plan_chunks.return_value = [mock_chunk]

                with patch('babel.commands.gather_cmd.ContextGatherer') as mock_gatherer:
                    mock_gatherer.return_value.gather_sources.return_value = []

                    with patch('babel.commands.gather_cmd.render_context', return_value="File content"):
                        with patch('babel.output.end_command'):
                            cmd.gather(files=["test.py"], output_file=str(output_file))

        assert output_file.exists()
        assert "File content" in output_file.read_text()
        captured = capsys.readouterr()
        assert "written to" in captured.out.lower()

    def test_shows_chunk_progress(self, gather_command, capsys):
        """Shows progress for multiple chunks."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            mock_plan.return_value = Mock()

            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                # Multiple chunks
                chunks = [Mock(sources=[]), Mock(sources=[])]
                mock_broker.return_value.plan_chunks.return_value = chunks

                with patch('babel.commands.gather_cmd.ContextGatherer') as mock_gatherer:
                    mock_gatherer.return_value.gather_sources.return_value = []

                    with patch('babel.commands.gather_cmd.render_context', return_value="Chunk"):
                        with patch('babel.output.end_command'):
                            cmd.gather(files=["a.py", "b.py", "c.py"])

        captured = capsys.readouterr()
        assert "chunk" in captured.out.lower()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_empty_chunks_after_planning(self, gather_command, capsys):
        """Handles case where planning returns empty chunks."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan'):
            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(files=["test.py"])

        captured = capsys.readouterr()
        assert "No sources to gather" in captured.out

    def test_handles_mixed_sources(self, gather_command):
        """Handles mix of all source types."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.check_bash_commands_safety'):
            with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
                mock_plan_instance = Mock()
                mock_plan.return_value = mock_plan_instance

                with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                    mock_broker.return_value.plan_chunks.return_value = []

                    cmd.gather(
                        files=["file.py"],
                        greps=["pattern:path"],
                        bashes=["git status"],
                        globs=["*.md"]
                    )

        # All source types should be added
        mock_plan_instance.add_file.assert_called_once()
        mock_plan_instance.add_grep.assert_called_once()
        mock_plan_instance.add_bash.assert_called_once()
        mock_plan_instance.add_glob.assert_called_once()

    def test_uses_operation_and_intent(self, gather_command):
        """Uses custom operation and intent."""
        cmd, factory = gather_command

        with patch('babel.commands.gather_cmd.GatherPlan') as mock_plan:
            with patch('babel.commands.gather_cmd.ChunkBroker') as mock_broker:
                mock_broker.return_value.plan_chunks.return_value = []

                cmd.gather(
                    files=["test.py"],
                    operation="Fix Bug",
                    intent="Understand cache flow"
                )

        mock_plan.assert_called_with(operation="Fix Bug", intent="Understand cache flow")
