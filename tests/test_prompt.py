"""
Tests for PromptCommand — P7 Reasoning Travels (System Prompt Management)

Tests the system prompt management:
- Outputting prompt to stdout
- Installing prompt to IDE-specific location
- Showing installation status
- Mini vs full prompt selection

Aligns with:
- P5: Tests ARE evidence for implementation
- P7: Reasoning Travels (prompt must travel with project)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from babel.commands.prompt import PromptCommand
from babel.services.ide import IDEType
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def prompt_command(babel_factory):
    """Create PromptCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # Create command instance
    cmd = PromptCommand.__new__(PromptCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Show Command Tests
# =============================================================================

class TestShowCommand:
    """Test show method for outputting system prompt."""

    def test_outputs_prompt_content(self, prompt_command, capsys):
        """Outputs system prompt content to stdout."""
        cmd, factory = prompt_command

        # Mock _get_prompt_content - no need to create actual files
        # Tests should be isolated and not touch source tree
        with patch.object(cmd, '_get_prompt_content', return_value="# Test System Prompt\nTest content"):
            cmd.show()

        captured = capsys.readouterr()
        assert "Test System Prompt" in captured.out

    def test_uses_safe_print(self, prompt_command):
        """Uses safe_print for encoding compatibility."""
        cmd, factory = prompt_command

        with patch('babel.commands.prompt.safe_print') as mock_safe_print:
            with patch.object(cmd, '_get_prompt_content', return_value="Test content"):
                cmd.show()

            mock_safe_print.assert_called_once_with("Test content")

    def test_handles_unicode_content(self, prompt_command, capsys):
        """Handles Unicode content in prompt."""
        cmd, factory = prompt_command

        unicode_content = "# Prompt with 日本語 and émoji 🚀"

        with patch.object(cmd, '_get_prompt_content', return_value=unicode_content):
            cmd.show()

        captured = capsys.readouterr()
        assert "Prompt" in captured.out


# =============================================================================
# Install Command Tests
# =============================================================================

class TestInstallCommand:
    """Test install method for IDE-specific prompt installation."""

    def test_installs_full_prompt_by_default(self, prompt_command, capsys):
        """Installs full prompt by default."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_prompt_content', return_value="Full prompt content"):
                with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                    with patch('babel.commands.prompt.install_prompt', return_value=(True, "Installed")):
                        cmd.install()

        captured = capsys.readouterr()
        assert "Installed" in captured.out or "full system prompt" in captured.out.lower()

    def test_installs_mini_prompt_when_requested(self, prompt_command, capsys):
        """Installs mini prompt when mode='mini'."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_mini_prompt_content', return_value="Mini prompt"):
                with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                    with patch('babel.commands.prompt.install_prompt', return_value=(True, "Installed")):
                        cmd.install(mode="mini")

        captured = capsys.readouterr()
        assert "mini" in captured.out.lower()

    def test_auto_mode_checks_skills(self, prompt_command, capsys):
        """Auto mode checks BABEL_SKILLS_INSTALLED."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_should_use_mini', return_value=(True, "Skills installed")):
                with patch.object(cmd, '_get_mini_prompt_content', return_value="Mini"):
                    with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                        with patch('babel.commands.prompt.install_prompt', return_value=(True, "OK")):
                            cmd.install(mode="auto")

        captured = capsys.readouterr()
        assert "Auto-detect" in captured.out

    def test_skips_when_file_exists_without_force(self, prompt_command, capsys):
        """Skips installation when file exists and force=False."""
        cmd, factory = prompt_command

        # Create existing file
        target_path = factory.tmp_path / ".system_prompt.md"
        target_path.write_text("Existing content")

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            cmd.install(force=False)

        captured = capsys.readouterr()
        assert "already installed" in captured.out.lower()
        assert "--force" in captured.out

    def test_force_overwrites_existing(self, prompt_command, capsys):
        """Force mode overwrites existing file."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"
        target_path.write_text("Old content")

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_prompt_content', return_value="New content"):
                with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                    with patch('babel.commands.prompt.install_prompt', return_value=(True, "Updated")):
                        cmd.install(force=True)

        captured = capsys.readouterr()
        assert "Updated" in captured.out or "full" in captured.out.lower()

    def test_shows_ide_specific_info(self, prompt_command, capsys):
        """Shows IDE-specific information after installation."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".cursorrules"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.CURSOR, "Cursor", target_path)):
            with patch.object(cmd, '_get_prompt_content', return_value="Content"):
                with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                    with patch('babel.commands.prompt.install_prompt', return_value=(True, "Installed")):
                        cmd.install()

        captured = capsys.readouterr()
        assert "Cursor" in captured.out

    def test_handles_install_failure(self, prompt_command, capsys):
        """Handles installation failure gracefully."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_prompt_content', return_value="Content"):
                with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                    with patch('babel.commands.prompt.install_prompt', return_value=(False, "Permission denied")):
                        cmd.install()

        captured = capsys.readouterr()
        assert "Permission denied" in captured.out


# =============================================================================
# Status Command Tests
# =============================================================================

class TestStatusCommand:
    """Test status method for showing installation status."""

    def test_shows_detected_ide(self, prompt_command, capsys):
        """Shows detected IDE information."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.CURSOR, "Cursor", target_path)):
            with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                    with patch.object(cmd, '_get_prompt_content', return_value="x" * 100):
                        with patch.object(cmd, '_get_mini_prompt_content', return_value="x" * 50):
                            with patch.object(cmd, '_should_use_mini', return_value=(False, "Not installed")):
                                cmd.status()

        captured = capsys.readouterr()
        assert "Cursor" in captured.out
        assert "Detected IDE" in captured.out

    def test_shows_not_installed_status(self, prompt_command, capsys):
        """Shows 'not installed' when prompt file missing."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / "nonexistent.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                    with patch.object(cmd, '_get_prompt_content', return_value="x" * 100):
                        with patch.object(cmd, '_get_mini_prompt_content', return_value="x" * 50):
                            with patch.object(cmd, '_should_use_mini', return_value=(False, "Not installed")):
                                cmd.status()

        captured = capsys.readouterr()
        assert "Not installed" in captured.out

    def test_shows_installed_status(self, prompt_command, capsys):
        """Shows 'installed' when prompt file exists."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"
        target_path.write_text("# Installed prompt\n" * 100)

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                    with patch.object(cmd, '_get_prompt_content', return_value="# Installed prompt\n" * 100):
                        with patch.object(cmd, '_get_mini_prompt_content', return_value="x" * 50):
                            with patch.object(cmd, '_should_use_mini', return_value=(False, "Not installed")):
                                cmd.status()

        captured = capsys.readouterr()
        assert "Installed" in captured.out

    def test_shows_skills_status(self, prompt_command, capsys):
        """Shows skills installation status."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                    with patch.object(cmd, '_get_prompt_content', return_value="x" * 100):
                        with patch.object(cmd, '_get_mini_prompt_content', return_value="x" * 50):
                            with patch.object(cmd, '_should_use_mini', return_value=(True, "Skills installed")):
                                with patch('babel.commands.prompt.get_env_variable', return_value="cursor"):
                                    cmd.status()

        captured = capsys.readouterr()
        assert "Skills" in captured.out

    def test_shows_actions(self, prompt_command, capsys):
        """Shows available actions."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                    with patch.object(cmd, '_get_prompt_content', return_value="x" * 100):
                        with patch.object(cmd, '_get_mini_prompt_content', return_value="x" * 50):
                            with patch.object(cmd, '_should_use_mini', return_value=(False, "Not")):
                                cmd.status()

        captured = capsys.readouterr()
        assert "Actions" in captured.out
        assert "--install" in captured.out


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestHelperMethods:
    """Test helper methods for prompt content and detection."""

    def test_get_prompt_content_from_file(self, prompt_command):
        """Gets prompt content from file when it exists."""
        cmd, factory = prompt_command

        # Create temporary prompt file
        prompt_dir = factory.tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "system_prompt.md"
        prompt_file.write_text("# File Content")

        with patch.object(cmd, '_get_system_prompt_path', return_value=prompt_file):
            content = cmd._get_prompt_content()

        assert "File Content" in content

    def test_get_prompt_content_fallback(self, prompt_command):
        """Falls back to embedded constant when file missing."""
        cmd, factory = prompt_command

        nonexistent = factory.tmp_path / "nonexistent.md"

        with patch.object(cmd, '_get_system_prompt_path', return_value=nonexistent):
            content = cmd._get_prompt_content()

        # Should return something (the fallback constant)
        assert content is not None
        assert len(content) > 0

    def test_get_mini_prompt_content(self, prompt_command):
        """Gets mini prompt content."""
        cmd, factory = prompt_command

        # Create temporary mini prompt file
        prompt_dir = factory.tmp_path / "prompts"
        prompt_dir.mkdir(exist_ok=True)
        mini_file = prompt_dir / "system_prompt_mini.md"
        mini_file.write_text("# Mini Prompt")

        with patch.object(cmd, '_get_mini_prompt_path', return_value=mini_file):
            content = cmd._get_mini_prompt_content()

        assert "Mini Prompt" in content

    def test_should_use_mini_when_skills_installed(self, prompt_command):
        """Returns True when BABEL_SKILLS_INSTALLED is true."""
        cmd, factory = prompt_command

        with patch('babel.commands.prompt.get_env_variable') as mock_get_env:
            mock_get_env.side_effect = lambda path, key: {
                "BABEL_SKILLS_INSTALLED": "true",
                "BABEL_SKILLS_TARGET": "cursor"
            }.get(key)

            use_mini, reason = cmd._should_use_mini()

        assert use_mini == True
        assert "cursor" in reason.lower()

    def test_should_not_use_mini_when_skills_not_installed(self, prompt_command):
        """Returns False when skills not installed."""
        cmd, factory = prompt_command

        with patch('babel.commands.prompt.get_env_variable', return_value=None):
            use_mini, reason = cmd._should_use_mini()

        assert use_mini == False

    def test_detect_ide_returns_type_and_path(self, prompt_command):
        """_detect_ide returns IDE type, name, and path."""
        cmd, factory = prompt_command

        with patch('babel.commands.prompt.detect_ide', return_value=IDEType.CURSOR):
            with patch('babel.commands.prompt.get_ide_info', return_value=("Cursor", ".cursorrules")):
                with patch('babel.commands.prompt.get_prompt_path', return_value=".cursorrules"):
                    ide_type, ide_name, prompt_path = cmd._detect_ide()

        assert ide_type == IDEType.CURSOR
        assert ide_name == "Cursor"
        assert ".cursorrules" in str(prompt_path)


# =============================================================================
# IDE Detection Tests
# =============================================================================

class TestIDEDetection:
    """Test IDE detection scenarios."""

    def test_detects_cursor_ide(self, prompt_command):
        """Detects Cursor IDE environment."""
        cmd, factory = prompt_command

        with patch('babel.commands.prompt.detect_ide', return_value=IDEType.CURSOR):
            with patch('babel.commands.prompt.get_ide_info', return_value=("Cursor", ".cursorrules")):
                with patch('babel.commands.prompt.get_prompt_path', return_value=".cursorrules"):
                    ide_type, ide_name, _ = cmd._detect_ide()

        assert ide_type == IDEType.CURSOR
        assert ide_name == "Cursor"

    def test_detects_claude_code_ide(self, prompt_command):
        """Detects Claude Code environment."""
        cmd, factory = prompt_command

        with patch('babel.commands.prompt.detect_ide', return_value=IDEType.CLAUDE_CODE):
            with patch('babel.commands.prompt.get_ide_info', return_value=("Claude Code", "CLAUDE.md")):
                with patch('babel.commands.prompt.get_prompt_path', return_value="CLAUDE.md"):
                    ide_type, ide_name, _ = cmd._detect_ide()

        assert ide_type == IDEType.CLAUDE_CODE
        assert "Claude" in ide_name

    def test_detects_generic_ide(self, prompt_command):
        """Detects generic IDE when no specific IDE found."""
        cmd, factory = prompt_command

        with patch('babel.commands.prompt.detect_ide', return_value=IDEType.GENERIC):
            with patch('babel.commands.prompt.get_ide_info', return_value=("Generic", ".system_prompt.md")):
                with patch('babel.commands.prompt.get_prompt_path', return_value=".system_prompt.md"):
                    ide_type, ide_name, _ = cmd._detect_ide()

        assert ide_type == IDEType.GENERIC

    def test_uses_config_override(self, prompt_command):
        """Uses config override for IDE detection."""
        cmd, factory = prompt_command

        # Set config override
        cmd._cli.config.ide = Mock()
        cmd._cli.config.ide.type = "cursor"

        with patch('babel.commands.prompt.detect_ide') as mock_detect:
            mock_detect.return_value = IDEType.CURSOR
            with patch('babel.commands.prompt.get_ide_info', return_value=("Cursor", ".cursorrules")):
                with patch('babel.commands.prompt.get_prompt_path', return_value=".cursorrules"):
                    cmd._detect_ide()

            # Should pass config override to detect_ide
            mock_detect.assert_called_once()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_missing_prompts_directory(self, prompt_command):
        """Handles missing prompts directory gracefully."""
        cmd, factory = prompt_command

        nonexistent = factory.tmp_path / "nonexistent" / "prompt.md"

        with patch.object(cmd, '_get_system_prompt_path', return_value=nonexistent):
            content = cmd._get_prompt_content()

        # Should return fallback content
        assert content is not None

    def test_handles_empty_prompt_file(self, prompt_command, capsys):
        """Handles empty prompt file."""
        cmd, factory = prompt_command

        empty_file = factory.tmp_path / "empty.md"
        empty_file.write_text("")

        with patch.object(cmd, '_get_system_prompt_path', return_value=empty_file):
            content = cmd._get_prompt_content()

        # Empty file returns empty string, fallback not triggered
        assert content == ""

    def test_handles_binary_characters_in_prompt(self, prompt_command, capsys):
        """Handles binary characters gracefully."""
        cmd, factory = prompt_command

        # Create file with unusual content
        weird_file = factory.tmp_path / "weird.md"
        weird_file.write_text("Normal text with \x00 null byte")

        with patch.object(cmd, '_get_system_prompt_path', return_value=weird_file):
            # Should not crash
            content = cmd._get_prompt_content()

        assert "Normal text" in content

    def test_status_with_corrupted_installed_file(self, prompt_command, capsys):
        """Handles corrupted installed prompt file."""
        cmd, factory = prompt_command

        target_path = factory.tmp_path / ".system_prompt.md"
        target_path.write_text("")  # Empty/corrupted

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                with patch.object(cmd, '_get_mini_prompt_path', return_value=Path("/fake/mini.md")):
                    with patch.object(cmd, '_get_prompt_content', return_value="x" * 100):
                        with patch.object(cmd, '_get_mini_prompt_content', return_value="x" * 50):
                            with patch.object(cmd, '_should_use_mini', return_value=(False, "Not")):
                                # Should not crash
                                cmd.status()

        captured = capsys.readouterr()
        assert "Status" in captured.out

    def test_install_creates_parent_directories(self, prompt_command, capsys):
        """Install creates parent directories if needed."""
        cmd, factory = prompt_command

        # Path with non-existent parent
        target_path = factory.tmp_path / "subdir" / ".system_prompt.md"

        with patch.object(cmd, '_detect_ide', return_value=(IDEType.GENERIC, "Generic", target_path)):
            with patch.object(cmd, '_get_prompt_content', return_value="Content"):
                with patch.object(cmd, '_get_system_prompt_path', return_value=Path("/fake/path.md")):
                    with patch('babel.commands.prompt.install_prompt', return_value=(True, "OK")):
                        cmd.install()

        # Should complete without error
        captured = capsys.readouterr()
        assert "OK" in captured.out or "full" in captured.out.lower()
