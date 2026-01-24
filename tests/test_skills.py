"""
Tests for Babel Skills YAML Validation

Ensures all skill YAML files are correctly loadable by the system:
- YAML syntax validity
- Schema compliance (required fields present)
- Category consistency (directory matches declared category)
- Command validation (commands reference valid babel subcommands)

Aligns with:
- P5: Tests ARE evidence for skill correctness
- P11: Babel tests itself (dogfooding)
- HC1: Prevents invalid skills from being committed

This test was created after reverting analyze skill enhancements
that referenced non-existent babel commands.
"""

import pytest
import yaml
import subprocess
from pathlib import Path
from typing import List, Set

# Import skill loading functions
from babel.skills import (
    Skill,
    Protocol,
    SkillCategory,
    get_skills_dir,
    load_skill,
    load_all_skills,
    load_protocols,
    list_skill_categories,
    list_skills_in_category,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def valid_babel_commands() -> Set[str]:
    """
    Get the set of valid babel subcommands from babel --help.

    This ensures command validation stays in sync with actual CLI.
    """
    try:
        result = subprocess.run(
            ["babel", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Parse commands from help output
        # Format: {cmd1,cmd2,cmd3,...}
        output = result.stdout
        # Find the line with commands listed in braces
        for line in output.split('\n'):
            if '{' in line and '}' in line:
                # Extract commands between braces
                start = line.index('{') + 1
                end = line.index('}')
                commands_str = line[start:end]
                return set(commands_str.split(','))
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    # Fallback: hardcoded list if babel --help fails
    return {
        'init', 'capture', 'why', 'status', 'check', 'coherence', 'scan',
        'review', 'share', 'sync', 'history', 'list', 'tensions', 'challenge',
        'evidence', 'resolve', 'validation', 'endorse', 'evidence-decision',
        'questions', 'question', 'resolve-question', 'link', 'suggest-links',
        'gaps', 'deprecate', 'memo', 'config', 'process-queue', 'help',
        'principles', 'capture-commit', 'hooks', 'prompt', 'map', 'skill'
    }


@pytest.fixture(scope="module")
def all_skill_yaml_files() -> List[Path]:
    """Collect all skill YAML files from the skills directory."""
    skills_dir = get_skills_dir()
    yaml_files = list(skills_dir.rglob("*.yaml"))
    return yaml_files


@pytest.fixture(scope="module")
def all_protocol_yaml_files() -> List[Path]:
    """Collect all protocol YAML files."""
    protocols_dir = get_skills_dir() / "protocols"
    if not protocols_dir.exists():
        return []
    return list(protocols_dir.glob("*.yaml"))


@pytest.fixture(scope="module")
def non_protocol_skill_files() -> List[Path]:
    """Collect skill YAML files excluding protocols."""
    skills_dir = get_skills_dir()
    yaml_files = []
    for category in list_skill_categories():
        category_dir = skills_dir / category.value
        if category_dir.exists():
            yaml_files.extend(category_dir.glob("*.yaml"))
    return yaml_files


# =============================================================================
# Helper Functions
# =============================================================================

def get_skill_yaml_files() -> List[Path]:
    """Get all skill YAML files for parametrization."""
    skills_dir = get_skills_dir()
    return list(skills_dir.rglob("*.yaml"))


def get_non_protocol_files() -> List[Path]:
    """Get skill files excluding protocols for parametrization."""
    skills_dir = get_skills_dir()
    files = []
    for category in list_skill_categories():
        category_dir = skills_dir / category.value
        if category_dir.exists():
            files.extend(category_dir.glob("*.yaml"))
    return files


def extract_babel_command(command_str: str) -> str:
    """
    Extract the babel subcommand from a command string.

    Examples:
        'babel status' -> 'status'
        'babel why "topic"' -> 'why'
        'babel list decisions --filter "x"' -> 'list'
        '# comment' -> None
    """
    command_str = command_str.strip()

    # Skip comments
    if command_str.startswith('#'):
        return None

    # Must start with 'babel'
    if not command_str.startswith('babel '):
        return None

    # Extract the subcommand (second word)
    parts = command_str.split()
    if len(parts) >= 2:
        return parts[1]

    return None


# =============================================================================
# YAML Syntax Tests
# =============================================================================

class TestYAMLSyntax:
    """Test that all YAML files have valid syntax."""

    @pytest.mark.parametrize("yaml_file", get_skill_yaml_files(),
                             ids=lambda p: p.name)
    def test_yaml_parses_without_error(self, yaml_file: Path):
        """Each YAML file must parse without syntax errors."""
        content = yaml_file.read_text(encoding='utf-8')

        # Should not raise yaml.YAMLError
        try:
            data = yaml.safe_load(content)
            assert data is not None, f"{yaml_file.name} parsed to None"
            assert isinstance(data, dict), f"{yaml_file.name} must be a mapping"
        except yaml.YAMLError as e:
            pytest.fail(f"{yaml_file.name} has invalid YAML syntax: {e}")


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestSkillSchema:
    """Test that skill files have required fields."""

    REQUIRED_SKILL_FIELDS = {'name', 'category', 'description', 'trigger', 'commands'}
    REQUIRED_PROTOCOL_FIELDS = {'name', 'description', 'rule'}

    @pytest.mark.parametrize("yaml_file", get_non_protocol_files(),
                             ids=lambda p: p.name)
    def test_skill_has_required_fields(self, yaml_file: Path):
        """Each skill must have all required fields."""
        content = yaml_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        missing = self.REQUIRED_SKILL_FIELDS - set(data.keys())
        assert not missing, f"{yaml_file.name} missing required fields: {missing}"

    @pytest.mark.parametrize("yaml_file", get_non_protocol_files(),
                             ids=lambda p: p.name)
    def test_skill_name_matches_filename(self, yaml_file: Path):
        """Skill name should match filename (without extension)."""
        content = yaml_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        expected_name = yaml_file.stem
        actual_name = data.get('name', '')

        assert actual_name == expected_name, \
            f"{yaml_file.name}: name '{actual_name}' should be '{expected_name}'"

    @pytest.mark.parametrize("yaml_file", get_non_protocol_files(),
                             ids=lambda p: p.name)
    def test_skill_commands_is_list(self, yaml_file: Path):
        """Commands field must be a list."""
        content = yaml_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        commands = data.get('commands', [])
        assert isinstance(commands, list), \
            f"{yaml_file.name}: commands must be a list, got {type(commands)}"


class TestProtocolSchema:
    """Test that protocol files have required fields."""

    REQUIRED_FIELDS = {'name', 'description', 'rule'}

    def test_protocols_directory_exists(self):
        """Protocols directory should exist."""
        protocols_dir = get_skills_dir() / "protocols"
        assert protocols_dir.exists(), "protocols/ directory missing"

    def test_all_protocols_have_required_fields(self):
        """Each protocol must have required fields."""
        protocols_dir = get_skills_dir() / "protocols"
        if not protocols_dir.exists():
            pytest.skip("No protocols directory")

        for yaml_file in protocols_dir.glob("*.yaml"):
            content = yaml_file.read_text(encoding='utf-8')
            data = yaml.safe_load(content)

            missing = self.REQUIRED_FIELDS - set(data.keys())
            assert not missing, f"{yaml_file.name} missing required fields: {missing}"


# =============================================================================
# Category Consistency Tests
# =============================================================================

class TestCategoryConsistency:
    """Test that skill categories match their directory location."""

    @pytest.mark.parametrize("yaml_file", get_non_protocol_files(),
                             ids=lambda p: p.name)
    def test_category_matches_directory(self, yaml_file: Path):
        """Skill's declared category must match its directory."""
        content = yaml_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        # Get declared category
        declared_category = data.get('category', '')

        # Get directory category (parent folder name)
        directory_category = yaml_file.parent.name

        assert declared_category == directory_category, \
            f"{yaml_file.name}: declared category '{declared_category}' " \
            f"doesn't match directory '{directory_category}'"

    @pytest.mark.parametrize("yaml_file", get_non_protocol_files(),
                             ids=lambda p: p.name)
    def test_category_is_valid_enum(self, yaml_file: Path):
        """Skill category must be a valid SkillCategory value."""
        content = yaml_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        declared_category = data.get('category', '')
        valid_categories = {c.value for c in SkillCategory if c != SkillCategory.PROTOCOL}

        assert declared_category in valid_categories, \
            f"{yaml_file.name}: category '{declared_category}' not in {valid_categories}"


# =============================================================================
# Skill Loading Tests
# =============================================================================

class TestSkillLoading:
    """Test that skills load correctly via the loading API."""

    @pytest.mark.parametrize("yaml_file", get_non_protocol_files(),
                             ids=lambda p: p.name)
    def test_skill_loads_via_load_skill(self, yaml_file: Path):
        """Each skill file must load via load_skill() without error."""
        skill = load_skill(yaml_file)

        assert skill is not None, f"{yaml_file.name} failed to load"
        assert isinstance(skill, Skill), f"{yaml_file.name} didn't return Skill"
        assert skill.name, f"{yaml_file.name} has empty name"

    def test_load_all_skills_succeeds(self):
        """load_all_skills() must return skills for all categories."""
        all_skills = load_all_skills()

        assert isinstance(all_skills, dict), "load_all_skills() must return dict"

        # Should have at least some categories
        assert len(all_skills) > 0, "No skill categories loaded"

        # Each category should have skills
        for category, skills in all_skills.items():
            assert isinstance(skills, list), f"{category} skills not a list"

    def test_load_protocols_succeeds(self):
        """load_protocols() must return protocol list without error."""
        protocols = load_protocols()

        assert isinstance(protocols, list), "load_protocols() must return list"

        for protocol in protocols:
            assert isinstance(protocol, Protocol), \
                f"Expected Protocol, got {type(protocol)}"
            assert protocol.name, "Protocol has empty name"


# =============================================================================
# Command Validation Tests
# =============================================================================

class TestCommandValidation:
    """Test that skill commands reference valid babel subcommands."""

    @pytest.mark.parametrize("yaml_file", get_non_protocol_files(),
                             ids=lambda p: p.name)
    def test_commands_reference_valid_babel_subcommands(
        self,
        yaml_file: Path,
        valid_babel_commands: Set[str]
    ):
        """Each command in a skill must reference a valid babel subcommand."""
        content = yaml_file.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        commands = data.get('commands', [])
        invalid_commands = []

        for cmd in commands:
            if not isinstance(cmd, str):
                continue

            subcommand = extract_babel_command(cmd)

            # Skip non-babel commands (comments, other tools)
            if subcommand is None:
                continue

            if subcommand not in valid_babel_commands:
                invalid_commands.append((cmd, subcommand))

        assert not invalid_commands, \
            f"{yaml_file.name} has invalid babel commands: {invalid_commands}"

    def test_all_skills_have_valid_commands(self, valid_babel_commands: Set[str]):
        """Aggregate test: all skills across all categories have valid commands."""
        all_skills = load_all_skills()
        invalid_skills = []

        for category, skills in all_skills.items():
            for skill in skills:
                for cmd in skill.commands:
                    subcommand = extract_babel_command(cmd)
                    if subcommand and subcommand not in valid_babel_commands:
                        invalid_skills.append({
                            'skill': skill.name,
                            'category': category.value,
                            'command': cmd,
                            'invalid_subcommand': subcommand
                        })

        assert not invalid_skills, \
            f"Skills with invalid commands: {invalid_skills}"


# =============================================================================
# Integration Tests
# =============================================================================

class TestSkillIntegration:
    """Integration tests for the complete skill loading pipeline."""

    def test_skill_to_dict_roundtrip(self):
        """Skills should survive to_dict() -> from_dict() roundtrip."""
        all_skills = load_all_skills()

        for category, skills in all_skills.items():
            for skill in skills:
                # Convert to dict and back
                skill_dict = skill.to_dict()
                reconstructed = Skill.from_dict(skill_dict)

                # Core fields should match
                assert reconstructed.name == skill.name
                assert reconstructed.category == skill.category
                assert reconstructed.description == skill.description
                assert reconstructed.commands == skill.commands

    def test_protocol_to_dict_roundtrip(self):
        """Protocols should survive to_dict() -> from_dict() roundtrip."""
        protocols = load_protocols()

        for protocol in protocols:
            # Convert to dict and back
            proto_dict = protocol.to_dict()
            reconstructed = Protocol.from_dict(proto_dict)

            # Core fields should match
            assert reconstructed.name == protocol.name
            assert reconstructed.description == protocol.description
            assert reconstructed.rule == protocol.rule

    def test_no_duplicate_skill_names(self):
        """Each skill name must be unique across all categories."""
        all_skills = load_all_skills()
        seen_names = {}
        duplicates = []

        for category, skills in all_skills.items():
            for skill in skills:
                if skill.name in seen_names:
                    duplicates.append({
                        'name': skill.name,
                        'first': seen_names[skill.name],
                        'second': category.value
                    })
                else:
                    seen_names[skill.name] = category.value

        assert not duplicates, f"Duplicate skill names found: {duplicates}"
