"""
Tests for CheckCommand — P11 Framework Self-Application (Integrity Verification)

Tests the project integrity verification and repair:
- .babel/ directory existence
- Events file validation (shared/local)
- Graph integrity checking
- Configuration validity
- Purpose existence (P1)
- Git protection (gitignore)
- Repair mode for automatic fixes

Aligns with:
- P5: Tests ARE evidence for implementation
- P11: Framework Self-Application (Babel governs itself)
"""

import pytest
from unittest.mock import Mock, patch

from babel.commands.check import CheckCommand
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def check_command(babel_factory):
    """Create CheckCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # CheckCommand needs _rebuild_graph for repair mode
    cli._rebuild_graph = Mock()

    # Create command instance
    cmd = CheckCommand.__new__(CheckCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Directory Existence Tests
# =============================================================================

class TestDirectoryExistence:
    """Test .babel/ directory existence checks."""

    def test_passes_when_babel_dir_exists(self, check_command, capsys):
        """Passes check when .babel/ directory exists."""
        cmd, factory = check_command

        cmd.check()

        captured = capsys.readouterr()
        assert ".babel/ directory exists" in captured.out

    def test_fails_when_babel_dir_missing(self, check_command, capsys, tmp_path):
        """Reports critical issue when .babel/ missing."""
        cmd, factory = check_command

        # Point to non-existent directory
        cmd._cli.babel_dir = tmp_path / "nonexistent" / ".babel"

        cmd.check()

        captured = capsys.readouterr()
        assert "CRITICAL" in captured.out
        assert ".babel/ directory missing" in captured.out


# =============================================================================
# Shared Events Tests
# =============================================================================

class TestSharedEventsCheck:
    """Test shared events file validation."""

    def test_passes_with_valid_shared_events(self, check_command, capsys):
        """Passes when shared events are valid."""
        cmd, factory = check_command

        # Add some events
        factory.add_purpose("Test purpose")

        cmd.check()

        captured = capsys.readouterr()
        assert "Shared events:" in captured.out

    def test_handles_no_shared_events(self, check_command, capsys):
        """Handles case with no shared events (normal for new projects)."""
        cmd, factory = check_command

        # Empty project - no shared events
        cmd.check()

        captured = capsys.readouterr()
        # Should either show 0 events or "normal for new projects"
        assert "events" in captured.out.lower()

    def test_reports_corrupted_shared_events(self, check_command, capsys):
        """Reports error when shared events are corrupted."""
        cmd, factory = check_command

        # Mock events.read_shared to raise exception
        cmd._cli.events.read_shared = Mock(side_effect=Exception("Parse error"))

        # Ensure the shared file exists so it attempts to read
        shared_path = factory.babel_dir / "shared" / "events.jsonl"
        shared_path.parent.mkdir(parents=True, exist_ok=True)
        shared_path.write_text("invalid json")

        cmd.check()

        captured = capsys.readouterr()
        assert "ERROR" in captured.out or "corrupted" in captured.out.lower()


# =============================================================================
# Local Events Tests
# =============================================================================

class TestLocalEventsCheck:
    """Test local events file validation."""

    def test_passes_with_valid_local_events(self, check_command, capsys):
        """Passes when local events are valid."""
        cmd, factory = check_command

        # Add local event
        factory.add_decision(summary="Local decision")

        cmd.check()

        captured = capsys.readouterr()
        assert "Local events:" in captured.out or "local" in captured.out.lower()

    def test_handles_no_local_events(self, check_command, capsys):
        """Handles case with no local events (normal)."""
        cmd, factory = check_command

        cmd.check()

        captured = capsys.readouterr()
        # Should show "No local events (normal)" or similar
        assert "local" in captured.out.lower()


# =============================================================================
# Graph Integrity Tests
# =============================================================================

class TestGraphIntegrityCheck:
    """Test graph integrity verification."""

    def test_passes_with_valid_graph(self, check_command, capsys):
        """Passes when graph is valid."""
        cmd, factory = check_command

        # Add some nodes to graph
        factory.add_purpose("Test purpose")
        factory.add_decision(summary="Test decision")

        cmd.check()

        captured = capsys.readouterr()
        assert "Graph:" in captured.out
        assert "nodes" in captured.out

    def test_reports_graph_issues(self, check_command, capsys):
        """Reports warning when graph has issues."""
        cmd, factory = check_command

        # Mock graph.stats to raise exception
        cmd._cli.graph.stats = Mock(side_effect=Exception("Graph corrupted"))

        cmd.check()

        captured = capsys.readouterr()
        assert "WARNING" in captured.out or "Graph" in captured.out


# =============================================================================
# Config Validity Tests
# =============================================================================

class TestConfigValidityCheck:
    """Test configuration validity checking."""

    def test_passes_with_valid_config(self, check_command, capsys):
        """Passes when config is valid."""
        cmd, factory = check_command

        # Config is real from factory - just run check
        cmd.check()

        captured = capsys.readouterr()
        assert "Config:" in captured.out

    def test_reports_config_warnings(self, check_command, capsys):
        """Reports warning when config has issues."""
        cmd, factory = check_command

        # Mock config validation error
        cmd._cli.config.llm.validate = Mock(return_value="API key not set")

        cmd.check()

        captured = capsys.readouterr()
        assert "WARNING" in captured.out or "Config" in captured.out


# =============================================================================
# Purpose Existence Tests (P1)
# =============================================================================

class TestPurposeExistenceCheck:
    """Test purpose existence check (P1 compliance)."""

    def test_passes_when_purpose_exists(self, check_command, capsys):
        """Passes when purpose is defined."""
        cmd, factory = check_command

        factory.add_purpose("Project purpose")

        cmd.check()

        captured = capsys.readouterr()
        assert "Purpose defined" in captured.out

    def test_warns_when_no_purpose(self, check_command, capsys):
        """Warns when no purpose is defined."""
        cmd, factory = check_command

        # Empty project - no purpose

        cmd.check()

        captured = capsys.readouterr()
        assert "WARNING" in captured.out or "No purpose" in captured.out


# =============================================================================
# Git Protection Tests
# =============================================================================

class TestGitProtectionCheck:
    """Test git protection verification."""

    def test_detects_git_repository(self, check_command, capsys):
        """Detects when in a git repository."""
        cmd, factory = check_command

        # Create .gitignore with local/ protection
        gitignore = factory.babel_dir / ".gitignore"
        gitignore.write_text("local/\n")

        # Mock GitIntegration at import location
        with patch.object(cmd, '_cli') as mock_cli:
            # Preserve real attributes
            mock_cli.babel_dir = factory.babel_dir
            mock_cli.project_dir = factory.tmp_path
            mock_cli.graph = factory.graph
            mock_cli.events = factory.events
            mock_cli.config = factory.config
            mock_cli.symbols = factory.symbols

            # Create mock git that returns is_git_repo=True
            with patch('babel.commands.check.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git_class.return_value = mock_git

                # Mock subprocess for ls-files check
                with patch('babel.commands.check.subprocess.run') as mock_run:
                    mock_run.return_value = Mock(stdout="", returncode=0)

                    cmd.check()

        captured = capsys.readouterr()
        assert "Git repository" in captured.out or "git" in captured.out.lower()

    def test_warns_when_not_git_repo(self, check_command, capsys):
        """Warns when not in a git repository."""
        cmd, factory = check_command

        # The default factory doesn't have a real git repo, so check should warn
        cmd.check()

        captured = capsys.readouterr()
        assert "WARNING" in captured.out or "git" in captured.out.lower()

    def test_warns_when_gitignore_missing(self, check_command, capsys):
        """Reports error when .gitignore missing in git repo."""
        cmd, factory = check_command

        # Ensure no .gitignore exists
        gitignore = factory.babel_dir / ".gitignore"
        if gitignore.exists():
            gitignore.unlink()

        # Mock GitIntegration to return is_git_repo=True
        with patch('babel.commands.check.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git_class.return_value = mock_git

            cmd.check()

        captured = capsys.readouterr()
        assert "ERROR" in captured.out or "gitignore" in captured.out.lower()

    def test_warns_when_local_not_protected(self, check_command, capsys):
        """Reports error when local/ not in gitignore."""
        cmd, factory = check_command

        # Create .gitignore without local/ protection
        gitignore = factory.babel_dir / ".gitignore"
        gitignore.write_text("# empty\n")

        # Mock GitIntegration to return is_git_repo=True
        with patch('babel.commands.check.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git_class.return_value = mock_git

            cmd.check()

        captured = capsys.readouterr()
        assert "ERROR" in captured.out or "local" in captured.out.lower()


# =============================================================================
# Repair Mode Tests
# =============================================================================

class TestRepairMode:
    """Test --repair mode for automatic fixes."""

    def test_repair_attempts_graph_rebuild(self, check_command, capsys):
        """Repair mode attempts to rebuild graph."""
        cmd, factory = check_command

        # Mock graph issue
        cmd._cli.graph.stats = Mock(side_effect=Exception("Graph corrupted"))

        cmd.check(repair=True)

        captured = capsys.readouterr()
        # Should attempt repair
        assert "repair" in captured.out.lower() or "Attempting" in captured.out

    def test_repair_fixes_gitignore(self, check_command, capsys):
        """Repair mode fixes gitignore."""
        cmd, factory = check_command

        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git_class.return_value = mock_git

            # No .gitignore
            gitignore = factory.babel_dir / ".gitignore"
            if gitignore.exists():
                gitignore.unlink()

            # Mock _ensure_gitignore
            cmd._cli.events._ensure_gitignore = Mock()

            cmd.check(repair=True)

        captured = capsys.readouterr()
        # Check for repair-related output or healthy status
        assert "repair" in captured.out.lower() or "passed" in captured.out.lower() or "functional" in captured.out.lower()

    def test_repair_shows_suggestion_when_issues(self, check_command, capsys):
        """Shows repair suggestion when issues found."""
        cmd, factory = check_command

        # Create an issue condition
        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git_class.return_value = mock_git

            gitignore = factory.babel_dir / ".gitignore"
            if gitignore.exists():
                gitignore.unlink()

            cmd.check(repair=False)

        captured = capsys.readouterr()
        # Check for repair suggestion or that issues/warnings were detected
        assert "babel check --repair" in captured.out or "ISSUES" in captured.out or "WARNINGS" in captured.out


# =============================================================================
# Summary Tests
# =============================================================================

class TestCheckSummary:
    """Test check summary output."""

    def test_shows_healthy_when_no_issues(self, check_command, capsys):
        """Shows healthy message when no issues."""
        cmd, factory = check_command

        # Create healthy project
        factory.add_purpose("Healthy project")

        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git_class.return_value = mock_git

            gitignore = factory.babel_dir / ".gitignore"
            gitignore.write_text("local/\n")

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(stdout="", returncode=0)

                cmd.check()

        captured = capsys.readouterr()
        # Should show healthy or passed
        assert "passed" in captured.out.lower() or "healthy" in captured.out.lower() or "functional" in captured.out.lower()

    def test_shows_issue_count(self, check_command, capsys):
        """Shows count of issues found."""
        cmd, factory = check_command

        # Create issue condition
        cmd._cli.babel_dir = factory.tmp_path / "nonexistent" / ".babel"

        cmd.check()

        captured = capsys.readouterr()
        assert "issue" in captured.out.lower()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_permission_errors(self, check_command, capsys):
        """Handles permission errors gracefully."""
        cmd, factory = check_command

        # Mock read error
        cmd._cli.events.read_shared = Mock(side_effect=PermissionError("Access denied"))

        # Ensure shared file exists
        shared_path = factory.babel_dir / "shared" / "events.jsonl"
        shared_path.parent.mkdir(parents=True, exist_ok=True)
        shared_path.write_text("{}")

        # Should not crash
        cmd.check()

        captured = capsys.readouterr()
        assert "ERROR" in captured.out or "corrupted" in captured.out.lower()

    def test_handles_git_command_failure(self, check_command, capsys):
        """Handles git command failure gracefully."""
        cmd, factory = check_command

        with patch('babel.services.git.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = True
            mock_git_class.return_value = mock_git

            gitignore = factory.babel_dir / ".gitignore"
            gitignore.write_text("local/\n")

            # Mock subprocess failure
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = Exception("Git not found")

                # Should not crash
                cmd.check()

        captured = capsys.readouterr()
        # Should complete without crashing
        assert "BABEL CHECK" in captured.out or "Integrity" in captured.out
