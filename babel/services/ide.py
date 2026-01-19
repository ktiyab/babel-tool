"""
IDE Detection — Auto-detect LLM/IDE environment for prompt installation

Supports multiple LLMs with their specific conventions:
- Auto-detects current environment
- Uses provider standards when known
- Falls back to universal default

Known standards (adapted over time):
- Claude Code: .claude/CLAUDE.md
- Cursor: .cursorrules
- Others: .system_prompt.md (universal fallback)
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class IDEType(Enum):
    """Known IDE/LLM types with their prompt conventions."""
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    GENERIC = "generic"  # Universal fallback


# Mapping of IDE types to their prompt file paths (relative to project root)
IDE_PROMPT_PATHS = {
    IDEType.CLAUDE_CODE: Path(".claude") / "CLAUDE.md",
    IDEType.CURSOR: Path(".cursorrules"),
    IDEType.GENERIC: Path(".system_prompt.md"),
}

# Environment variables that indicate specific IDEs
IDE_ENV_MARKERS = {
    "CLAUDE_CODE": IDEType.CLAUDE_CODE,
    "CLAUDE_API_KEY": IDEType.CLAUDE_CODE,  # Often set in Claude Code
    "CURSOR_SESSION": IDEType.CURSOR,
}

# Directory markers that indicate specific IDEs
IDE_DIR_MARKERS = {
    ".claude": IDEType.CLAUDE_CODE,
    ".cursor": IDEType.CURSOR,
}


def detect_ide(project_dir: Path = None, config_override: str = None) -> IDEType:
    """
    Auto-detect the current LLM/IDE environment.

    Detection priority:
    1. Config override (user explicitly set ide.type)
    2. Environment variables
    3. Directory markers
    4. Fallback to generic

    Args:
        project_dir: Project root to check for markers
        config_override: Value from config if set

    Returns:
        Detected IDEType
    """
    # Priority 1: Config override
    if config_override:
        try:
            return IDEType(config_override)
        except ValueError:
            pass  # Invalid config value, continue detection

    # Priority 2: Environment variables
    for env_var, ide_type in IDE_ENV_MARKERS.items():
        if os.environ.get(env_var):
            return ide_type

    # Priority 3: Directory markers
    if project_dir:
        for marker, ide_type in IDE_DIR_MARKERS.items():
            if (project_dir / marker).exists():
                return ide_type

    # Priority 4: Fallback
    return IDEType.GENERIC


def get_prompt_path(ide_type: IDEType) -> Path:
    """
    Get the prompt file path for a specific IDE type.

    Args:
        ide_type: The detected or configured IDE type

    Returns:
        Relative path to prompt file
    """
    return IDE_PROMPT_PATHS.get(ide_type, IDE_PROMPT_PATHS[IDEType.GENERIC])


def get_ide_info(ide_type: IDEType) -> Tuple[str, str]:
    """
    Get human-readable info about an IDE type.

    Returns:
        Tuple of (display_name, prompt_path_description)
    """
    info = {
        IDEType.CLAUDE_CODE: ("Claude Code", ".claude/CLAUDE.md"),
        IDEType.CURSOR: ("Cursor", ".cursorrules"),
        IDEType.GENERIC: ("Generic LLM", ".system_prompt.md"),
    }
    return info.get(ide_type, ("Unknown", ".system_prompt.md"))


def install_prompt(
    project_dir: Path,
    ide_type: IDEType,
    content: str,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Install prompt file for the specified IDE.

    Args:
        project_dir: Project root directory
        ide_type: Target IDE type
        content: Prompt content to write
        force: Overwrite existing file

    Returns:
        Tuple of (success, message)
    """
    prompt_path = project_dir / get_prompt_path(ide_type)

    # Create parent directory if needed
    prompt_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists
    if prompt_path.exists() and not force:
        return False, f"Prompt file already exists: {prompt_path}"

    # Write content (UTF-8 for Unicode symbols)
    prompt_path.write_text(content, encoding='utf-8')

    ide_name, _ = get_ide_info(ide_type)
    return True, f"Installed {ide_name} prompt: {prompt_path}"
