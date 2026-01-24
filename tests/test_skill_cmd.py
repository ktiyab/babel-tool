"""
Tests for SkillCommand — P7 Skill Export to AI Platforms

Tests the skill export functionality:
- Showing skill export status
- Exporting skills to platforms
- Syncing/removing exported skills
- Listing available skills

Aligns with:
- P5: Tests ARE evidence for implementation
- P7: Reasoning Travels (skills travel with project)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from babel.commands.skill_cmd import SkillCommand
from babel.services.skills import SkillTarget
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def skill_command(babel_factory):
    """Create SkillCommand with mocked CLI."""
    cli = babel_factory.create_cli_mock()

    # Create command instance (SkillCommand has __init__)
    cmd = SkillCommand(cli)

    return cmd, babel_factory


# =============================================================================
# Helper Classes
# =============================================================================

class MockExportResult:
    """Mock export result for testing."""
    def __init__(self, success=True, message="OK", files_created=None):
        self.success = success
        self.message = message
        self.files_created = files_created or []


class MockSkill:
    """Mock skill object for testing."""
    def __init__(self, name="test-skill", description="Test skill", trigger="on test"):
        self.name = name
        self.description = description
        self.trigger = trigger


class MockProtocol:
    """Mock protocol object for testing."""
    def __init__(self, name="test-protocol", rule="Test rule"):
        self.name = name
        self.rule = rule


# =============================================================================
# Status Tests
# =============================================================================

class TestStatus:
    """Test status method for skill export status."""

    def test_shows_status(self, skill_command, capsys):
        """Shows skill export status."""
        cmd, factory = skill_command

        with patch('babel.commands.skill_cmd.get_skills_status') as mock_status:
            mock_status.return_value = {"exported": [], "available": []}

            with patch('babel.commands.skill_cmd.format_skills_status', return_value="Skills Status Output"):
                cmd.status()

        captured = capsys.readouterr()
        assert "Skills Status Output" in captured.out


# =============================================================================
# Export Tests
# =============================================================================

class TestExport:
    """Test export method for skill export."""

    def test_exports_to_specified_target(self, skill_command, capsys):
        """Exports skills to specified target."""
        cmd, factory = skill_command

        result = MockExportResult(success=True, message="Skills exported to Cursor")

        with patch('babel.commands.skill_cmd.export_skills', return_value=result):
            cmd.export(target="cursor")

        captured = capsys.readouterr()
        assert "Skills exported" in captured.out or "✓" in captured.out

    def test_exports_to_all_targets(self, skill_command, capsys):
        """Exports skills to all targets."""
        cmd, factory = skill_command

        result = MockExportResult(success=True, message="Exported to all platforms")

        with patch('babel.commands.skill_cmd.export_skills', return_value=result):
            cmd.export(target="all")

        captured = capsys.readouterr()
        assert "Exported" in captured.out or "✓" in captured.out

    def test_auto_detects_single_platform(self, skill_command, capsys):
        """Auto-detects platform when single platform active."""
        cmd, factory = skill_command

        result = MockExportResult(success=True, message="OK")

        with patch('babel.commands.skill_cmd.detect_active_platforms', return_value=[SkillTarget.CURSOR]):
            with patch('babel.commands.skill_cmd.export_skills', return_value=result):
                cmd.export()

        captured = capsys.readouterr()
        assert "Auto-detected" in captured.out

    def test_shows_multiple_platforms_message(self, skill_command, capsys):
        """Shows message when multiple platforms detected."""
        cmd, factory = skill_command

        with patch('babel.commands.skill_cmd.detect_active_platforms', return_value=[SkillTarget.CURSOR, SkillTarget.CLAUDE_CODE]):
            cmd.export()

        captured = capsys.readouterr()
        assert "Multiple platforms" in captured.out

    def test_shows_unknown_target_error(self, skill_command, capsys):
        """Shows error for unknown target."""
        cmd, factory = skill_command

        cmd.export(target="invalid_target")

        captured = capsys.readouterr()
        assert "Unknown target" in captured.out

    def test_shows_files_created(self, skill_command, capsys):
        """Shows list of created files."""
        cmd, factory = skill_command

        files = [
            factory.tmp_path / ".cursor/skills/babel/skill1.md",
            factory.tmp_path / ".cursor/skills/babel/skill2.md",
        ]
        result = MockExportResult(success=True, message="OK", files_created=files)

        with patch('babel.commands.skill_cmd.export_skills', return_value=result):
            cmd.export(target="cursor")

        captured = capsys.readouterr()
        assert "Files created" in captured.out

    def test_shows_export_failure(self, skill_command, capsys):
        """Shows failure message on export error."""
        cmd, factory = skill_command

        result = MockExportResult(success=False, message="Permission denied")

        with patch('babel.commands.skill_cmd.export_skills', return_value=result):
            cmd.export(target="cursor")

        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()
        assert "Permission denied" in captured.out


# =============================================================================
# Sync Tests
# =============================================================================

class TestSync:
    """Test sync method for re-exporting skills."""

    def test_syncs_successfully(self, skill_command, capsys):
        """Syncs skills successfully."""
        cmd, factory = skill_command

        result = MockExportResult(success=True, message="Synced to 2 platforms")

        with patch('babel.commands.skill_cmd.sync_skills', return_value=result):
            cmd.sync()

        captured = capsys.readouterr()
        assert "Sync complete" in captured.out or "✓" in captured.out

    def test_shows_sync_failure(self, skill_command, capsys):
        """Shows failure message on sync error."""
        cmd, factory = skill_command

        result = MockExportResult(success=False, message="No previous exports")

        with patch('babel.commands.skill_cmd.sync_skills', return_value=result):
            cmd.sync()

        captured = capsys.readouterr()
        assert "No previous exports" in captured.out or "✗" in captured.out


# =============================================================================
# Remove Tests
# =============================================================================

class TestRemove:
    """Test remove method for removing exported skills."""

    def test_removes_from_target(self, skill_command, capsys):
        """Removes skills from specified target."""
        cmd, factory = skill_command

        result = MockExportResult(success=True, message="Skills removed from Cursor")

        with patch('babel.commands.skill_cmd.remove_skills', return_value=result):
            cmd.remove(target="cursor")

        captured = capsys.readouterr()
        assert "removed" in captured.out.lower() or "✓" in captured.out

    def test_removes_from_all_with_force(self, skill_command, capsys):
        """Removes from all platforms with force flag."""
        cmd, factory = skill_command

        result = MockExportResult(success=True, message="Removed from all")

        with patch('babel.commands.skill_cmd.remove_skills', return_value=result):
            cmd.remove(target="all", force=True)

        captured = capsys.readouterr()
        assert "Removed" in captured.out or "✓" in captured.out

    def test_auto_detects_for_removal(self, skill_command, capsys):
        """Auto-detects platform from manifest for removal."""
        cmd, factory = skill_command

        mock_manifest = Mock()
        mock_manifest.exports = {"cursor": {"timestamp": "2024-01-01"}}

        result = MockExportResult(success=True, message="Removed")

        with patch('babel.services.skills.load_manifest', return_value=mock_manifest):
            with patch('babel.commands.skill_cmd.remove_skills', return_value=result):
                cmd.remove()

        captured = capsys.readouterr()
        assert "Auto-detected" in captured.out

    def test_shows_no_exports_message(self, skill_command, capsys):
        """Shows message when no platforms exported."""
        cmd, factory = skill_command

        mock_manifest = Mock()
        mock_manifest.exports = {}

        with patch('babel.services.skills.load_manifest', return_value=mock_manifest):
            cmd.remove()

        captured = capsys.readouterr()
        assert "No platforms exported" in captured.out

    def test_shows_unknown_target_error(self, skill_command, capsys):
        """Shows error for unknown target."""
        cmd, factory = skill_command

        cmd.remove(target="invalid_target")

        captured = capsys.readouterr()
        assert "Unknown target" in captured.out


# =============================================================================
# List Skills Tests
# =============================================================================

class TestListSkills:
    """Test list_skills method."""

    def test_lists_all_skills(self, skill_command, capsys):
        """Lists all available skills."""
        cmd, factory = skill_command

        from babel.skills import SkillCategory

        mock_skills = {
            SkillCategory.LIFECYCLE: [MockSkill("commit", "Commit changes")],
            SkillCategory.KNOWLEDGE: [MockSkill("why", "Query context")],
        }

        with patch('babel.commands.skill_cmd.load_all_skills', return_value=mock_skills):
            with patch('babel.commands.skill_cmd.load_protocols', return_value=[MockProtocol()]):
                cmd.list_skills()

        captured = capsys.readouterr()
        assert "Babel Skills" in captured.out
        assert "commit" in captured.out or "Total" in captured.out

    def test_lists_skills_by_category(self, skill_command, capsys):
        """Lists skills filtered by category."""
        cmd, factory = skill_command

        from babel.skills import SkillCategory

        mock_skills = {
            SkillCategory.LIFECYCLE: [
                MockSkill("commit", "Commit changes", "on commit"),
            ],
        }

        with patch('babel.commands.skill_cmd.load_all_skills', return_value=mock_skills):
            cmd.list_skills(category="lifecycle")

        captured = capsys.readouterr()
        assert "Lifecycle Skills" in captured.out or "commit" in captured.out

    def test_shows_unknown_category_error(self, skill_command, capsys):
        """Shows error for unknown category."""
        cmd, factory = skill_command

        with patch('babel.commands.skill_cmd.load_all_skills', return_value={}):
            cmd.list_skills(category="invalid_category")

        captured = capsys.readouterr()
        assert "Unknown category" in captured.out

    def test_shows_no_skills_in_category(self, skill_command, capsys):
        """Shows message when category has no skills."""
        cmd, factory = skill_command

        with patch('babel.commands.skill_cmd.load_all_skills', return_value={}):
            cmd.list_skills(category="lifecycle")

        captured = capsys.readouterr()
        assert "No skills" in captured.out


# =============================================================================
# Help Tests
# =============================================================================

class TestHelp:
    """Test help method."""

    def test_shows_help(self, skill_command, capsys):
        """Shows command help."""
        cmd, factory = skill_command

        cmd.help()

        captured = capsys.readouterr()
        assert "Babel Skill" in captured.out
        assert "export" in captured.out
        assert "sync" in captured.out
        assert "remove" in captured.out


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_empty_skills_list(self, skill_command, capsys):
        """Handles empty skills list."""
        cmd, factory = skill_command

        with patch('babel.commands.skill_cmd.load_all_skills', return_value={}):
            with patch('babel.commands.skill_cmd.load_protocols', return_value=[]):
                cmd.list_skills()

        # Should not crash
        captured = capsys.readouterr()
        assert "Babel Skills" in captured.out

    def test_handles_many_files_created(self, skill_command, capsys):
        """Handles many files created (shows first 5)."""
        cmd, factory = skill_command

        files = [factory.tmp_path / f"skill{i}.md" for i in range(10)]
        result = MockExportResult(success=True, message="OK", files_created=files)

        with patch('babel.commands.skill_cmd.export_skills', return_value=result):
            cmd.export(target="cursor")

        captured = capsys.readouterr()
        assert "5 more" in captured.out or "..." in captured.out

    def test_handles_force_flag(self, skill_command, capsys):
        """Handles force flag on export."""
        cmd, factory = skill_command

        result = MockExportResult(success=True, message="Overwritten")

        with patch('babel.commands.skill_cmd.export_skills', return_value=result) as mock_export:
            cmd.export(target="cursor", force=True)

        mock_export.assert_called_once()
        call_kwargs = mock_export.call_args.kwargs
        assert call_kwargs.get("force") == True
