"""
Tests for GitCommand — Git Integration and Commit Capture

Tests the git integration:
- Capturing git commits with enhanced diff info
- Installing/uninstalling git hooks
- Git hooks status reporting

Aligns with:
- P5: Tests ARE evidence for implementation
- P7: Reasoning Travels (commits carry intent)
- P8: Evolution Traceable (commit history)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from babel.commands.git_cmd import GitCommand
from babel.core.events import EventType
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def git_command(babel_factory):
    """Create GitCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # GitCommand needs extractor and coherence
    cli.extractor = Mock()
    cli.extractor.queue = Mock()
    cli.extractor.queue.add = Mock()

    cli.coherence = Mock()
    cli.coherence.check = Mock(return_value=Mock(has_issues=False))

    cli._capture_cmd = Mock()
    cli._capture_cmd.extract_and_confirm = Mock()

    # Create command instance
    cmd = GitCommand.__new__(GitCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Helper Classes
# =============================================================================

class MockCommit:
    """Mock commit object for testing."""
    def __init__(
        self,
        hash="abc123def",
        message="Test commit",
        body="",
        author="test@example.com",
        files=None,
        diff_id=None
    ):
        self.hash = hash
        self.message = message
        self.body = body
        self.author = author
        self.files = files or ["test.py"]
        self.diff_id = diff_id or hash
        self.structural = None
        self.comment_diff = None


class MockGitIntegration:
    """Mock GitIntegration for testing."""
    def __init__(self, is_git_repo=True, last_commit=None):
        self.is_git_repo = is_git_repo
        self._last_commit = last_commit

    def get_last_commit(self, include_diff=False):
        return self._last_commit

    def install_hooks(self):
        return True, "Hooks installed"

    def uninstall_hooks(self):
        return True, "Hooks removed"

    def hooks_status(self):
        return "installed"


# =============================================================================
# Capture Git Commit Tests
# =============================================================================

class TestCaptureGitCommit:
    """Test capture_git_commit method."""

    def test_shows_not_git_repo(self, git_command, capsys):
        """Shows message when not a git repository."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = False

            cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "Not a git repository" in captured.out

    def test_silent_in_async_mode_not_git(self, git_command, capsys):
        """Silent when not git repo in async mode."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = False

            cmd.capture_git_commit(async_mode=True)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_shows_no_commit(self, git_command, capsys):
        """Shows message when cannot read commit."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = None

            cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "Could not read last commit" in captured.out

    def test_detects_duplicate_commit(self, git_command, capsys):
        """Detects and skips duplicate commits."""
        cmd, factory = git_command

        commit = MockCommit(hash="abc123", diff_id="abc123")

        # Mock existing event with same diff_id
        mock_event = Mock()
        mock_event.data = {"diff_id": "abc123"}
        cmd._cli.events.read_by_type = Mock(return_value=[mock_event])

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "already captured" in captured.out.lower()

    def test_captures_new_commit(self, git_command, capsys):
        """Captures new commit successfully."""
        cmd, factory = git_command

        commit = MockCommit(hash="new123abc")
        cmd._cli.events.read_by_type = Mock(return_value=[])

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Commit text"):
                cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "Captured" in captured.out
        assert "new123ab" in captured.out  # First 8 chars

    def test_shows_structural_info(self, git_command, capsys):
        """Shows structural diff summary."""
        cmd, factory = git_command

        commit = MockCommit(hash="struct123")
        commit.structural = Mock()
        commit.structural.to_dict.return_value = {"added": 1, "removed": 0}
        commit.structural.summary = "1 function added"

        cmd._cli.events.read_by_type = Mock(return_value=[])

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Text"):
                cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "1 function added" in captured.out

    def test_shows_comment_diff_count(self, git_command, capsys):
        """Shows count of extracted code comments."""
        cmd, factory = git_command

        commit = MockCommit(hash="comment123")
        commit.comment_diff = "# Comment 1\n# Comment 2\n# Comment 3"

        cmd._cli.events.read_by_type = Mock(return_value=[])

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Text"):
                cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "code comment" in captured.out.lower()

    def test_async_mode_queues_extraction(self, git_command):
        """Async mode queues extraction for later."""
        cmd, factory = git_command

        commit = MockCommit(hash="async123")
        cmd._cli.events.read_by_type = Mock(return_value=[])

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Text"):
                cmd.capture_git_commit(async_mode=True)

        cmd._cli.extractor.queue.add.assert_called_once()

    def test_runs_coherence_check_when_enabled(self, git_command, capsys):
        """Runs coherence check when auto_check enabled."""
        cmd, factory = git_command

        commit = MockCommit(hash="cohere123")
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.config.coherence = Mock()
        cmd._cli.config.coherence.auto_check = True

        coherence_result = Mock()
        coherence_result.has_issues = True
        cmd._cli.coherence.check.return_value = coherence_result

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Text"):
                with patch('babel.commands.git_cmd.format_coherence_status', return_value="Status"):
                    cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "Coherence" in captured.out


# =============================================================================
# Install Hooks Tests
# =============================================================================

class TestInstallHooks:
    """Test install_hooks method."""

    def test_installs_hooks_successfully(self, git_command, capsys):
        """Installs hooks successfully."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.install_hooks.return_value = (True, "Git hooks installed")

            cmd.install_hooks()

        captured = capsys.readouterr()
        assert "installed" in captured.out.lower()
        assert "babel history" in captured.out

    def test_shows_failure_message(self, git_command, capsys):
        """Shows failure message when installation fails."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.install_hooks.return_value = (False, "Permission denied")

            cmd.install_hooks()

        captured = capsys.readouterr()
        assert "Permission denied" in captured.out


# =============================================================================
# Uninstall Hooks Tests
# =============================================================================

class TestUninstallHooks:
    """Test uninstall_hooks method."""

    def test_uninstalls_hooks_successfully(self, git_command, capsys):
        """Uninstalls hooks successfully."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.uninstall_hooks.return_value = (True, "Git hooks removed")

            cmd.uninstall_hooks()

        captured = capsys.readouterr()
        assert "removed" in captured.out.lower()

    def test_shows_failure_message(self, git_command, capsys):
        """Shows failure message when uninstall fails."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.uninstall_hooks.return_value = (False, "Hooks not found")

            cmd.uninstall_hooks()

        captured = capsys.readouterr()
        assert "Hooks not found" in captured.out


# =============================================================================
# Hooks Status Tests
# =============================================================================

class TestHooksStatus:
    """Test hooks_status method."""

    def test_shows_installed_status(self, git_command, capsys):
        """Shows 'installed' status."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.hooks_status.return_value = "installed"

            cmd.hooks_status()

        captured = capsys.readouterr()
        assert "installed" in captured.out

    def test_shows_not_installed_status(self, git_command, capsys):
        """Shows 'not installed' status."""
        cmd, factory = git_command

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.hooks_status.return_value = "not installed"

            cmd.hooks_status()

        captured = capsys.readouterr()
        assert "not installed" in captured.out


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_commit_with_empty_message(self, git_command, capsys):
        """Handles commit with empty message."""
        cmd, factory = git_command

        commit = MockCommit(hash="empty123", message="")
        cmd._cli.events.read_by_type = Mock(return_value=[])

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Text"):
                cmd.capture_git_commit()

        captured = capsys.readouterr()
        assert "Captured" in captured.out

    def test_handles_unicode_in_commit_message(self, git_command, capsys):
        """Handles Unicode in commit message."""
        cmd, factory = git_command

        commit = MockCommit(hash="uni123", message="Fix bug with 日本語 support")
        cmd._cli.events.read_by_type = Mock(return_value=[])

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Text"):
                cmd.capture_git_commit()

        # Should not crash
        captured = capsys.readouterr()
        assert "Captured" in captured.out

    def test_async_coherence_check_fails_silently(self, git_command, capsys):
        """Coherence check fails silently in async mode."""
        cmd, factory = git_command

        commit = MockCommit(hash="async_coh")
        cmd._cli.events.read_by_type = Mock(return_value=[])
        cmd._cli.config.coherence = Mock()
        cmd._cli.config.coherence.auto_check = True
        cmd._cli.coherence.check.side_effect = Exception("Check failed")

        with patch('babel.commands.git_cmd.GitIntegration') as mock_git:
            mock_git.return_value.is_git_repo = True
            mock_git.return_value.get_last_commit.return_value = commit

            with patch('babel.commands.git_cmd.format_commit_for_extraction', return_value="Text"):
                # Should not raise
                cmd.capture_git_commit(async_mode=True)

        # No error in output
        captured = capsys.readouterr()
        assert "error" not in captured.out.lower()
