"""
PromptCommand — System prompt management for LLM integration

Handles system prompt operations:
- Outputting prompt to stdout for manual use
- Installing prompt to IDE-specific location (Claude Code, Cursor, etc.)
- Showing prompt installation status
- Updating prompt after babel package upgrades

The system prompt is REQUIRED for LLMs to correctly use Babel:
- Teaches workflow (why -> capture -> review -> link -> implement)
- Enables transparency protocol
- Documents command groups and validation states
"""

from pathlib import Path
from typing import Tuple

from ..commands.base import BaseCommand
from ..services.ide import detect_ide, get_ide_info, get_prompt_path, install_prompt, IDEType
from ..content import BABEL_LLM_INSTRUCTIONS
from ..presentation.symbols import safe_print


class PromptCommand(BaseCommand):
    """
    Command for system prompt management.

    P7 (Reasoning Travels): The prompt must travel with the project.
    This command enables installing and updating the prompt for existing projects.
    """

    def _get_system_prompt_path(self) -> Path:
        """Get path to system_prompt.md source file."""
        # babel/prompts/system_prompt.md
        prompts_path = Path(__file__).parent.parent / "prompts" / "system_prompt.md"
        if prompts_path.exists():
            return prompts_path
        # Fallback: babel/system_prompt.md
        return Path(__file__).parent.parent / "system_prompt.md"

    def _get_prompt_content(self) -> str:
        """
        Get system prompt content.

        Reads from system_prompt.md (single source of truth).
        Falls back to embedded constant if file not found.
        """
        prompt_path = self._get_system_prompt_path()
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        return BABEL_LLM_INSTRUCTIONS

    def _detect_ide(self) -> Tuple[IDEType, str, Path]:
        """
        Detect IDE and return type, name, and prompt path.

        Returns:
            Tuple of (IDEType, display_name, prompt_path)
        """
        config_override = None
        if hasattr(self.config, 'ide') and hasattr(self.config.ide, 'type'):
            config_override = self.config.ide.type

        ide_type = detect_ide(self.project_dir, config_override)
        ide_name, _ = get_ide_info(ide_type)
        prompt_path = self.project_dir / get_prompt_path(ide_type)

        return ide_type, ide_name, prompt_path

    # -------------------------------------------------------------------------
    # Main Commands
    # -------------------------------------------------------------------------

    def show(self):
        """
        Output system prompt to stdout.

        Use case: Manual copy, piping to file, inspection.
        Uses safe_print for Windows encoding compatibility.
        """
        safe_print(self._get_prompt_content())

    def install(self, force: bool = False):
        """
        Install system prompt to IDE-specific location.

        Auto-detects IDE (Claude Code, Cursor, etc.) and installs
        the prompt to the appropriate location.

        Args:
            force: Overwrite existing prompt file if True
        """
        symbols = self.symbols
        ide_type, ide_name, target_path = self._detect_ide()
        prompt_content = self._get_prompt_content()

        # Check if target exists
        if target_path.exists() and not force:
            print(f"{symbols.check_pass} Prompt already installed: {target_path}")
            print(f"\nTo update, use: babel prompt --install --force")
            return

        # Install prompt
        success, message = install_prompt(
            self.project_dir,
            ide_type,
            prompt_content,
            force=force
        )

        if success:
            print(f"{symbols.check_pass} {message}")
            print(f"\n{ide_name} will now use Babel's system prompt.")

            # Show prompt source info
            source_path = self._get_system_prompt_path()
            if source_path.exists():
                line_count = len(prompt_content.splitlines())
                print(f"\nSource: {source_path.name} ({line_count} lines)")
            else:
                print(f"\nSource: embedded fallback")
        else:
            print(f"{symbols.check_warn} {message}")

    def status(self):
        """
        Show system prompt installation status.

        Displays:
        - Detected IDE
        - Expected prompt location
        - Installation status
        - Source file status
        """
        symbols = self.symbols
        ide_type, ide_name, target_path = self._detect_ide()
        source_path = self._get_system_prompt_path()

        print(f"\nSystem Prompt Status")
        print(f"{'=' * 40}")

        # IDE detection
        print(f"\nDetected IDE: {ide_name}")
        print(f"Prompt path:  {target_path}")

        # Installation status
        if target_path.exists():
            installed_content = target_path.read_text(encoding='utf-8')
            installed_lines = len(installed_content.splitlines())
            print(f"Status:       {symbols.check_pass} Installed ({installed_lines} lines)")

            # Check if up-to-date
            current_content = self._get_prompt_content()
            if installed_content.strip() == current_content.strip():
                print(f"Version:      {symbols.check_pass} Up to date")
            else:
                print(f"Version:      {symbols.check_warn} Outdated (update with --force)")
        else:
            print(f"Status:       {symbols.check_fail} Not installed")

        # Source status
        print(f"\nSource File")
        print(f"{'-' * 40}")
        if source_path.exists():
            source_lines = len(self._get_prompt_content().splitlines())
            print(f"Path:         {source_path}")
            print(f"Size:         {source_lines} lines")
        else:
            print(f"Path:         (embedded fallback)")

        # Actions
        print(f"\nActions")
        print(f"{'-' * 40}")
        if not target_path.exists():
            print(f"Install:      babel prompt --install")
        else:
            print(f"Update:       babel prompt --install --force")
        print(f"View:         babel prompt")