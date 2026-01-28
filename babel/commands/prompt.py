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
from ..presentation.template import OutputTemplate
from ..config import get_env_variable


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

    def _get_mini_prompt_path(self) -> Path:
        """Get path to system_prompt_mini.md source file."""
        return Path(__file__).parent.parent / "prompts" / "system_prompt_mini.md"

    def _get_mini_prompt_content(self) -> str:
        """
        Get mini system prompt content.

        Mini prompt is used when skills are installed (P6: Token Efficiency).
        Falls back to full prompt if mini not found.
        """
        mini_path = self._get_mini_prompt_path()
        if mini_path.exists():
            return mini_path.read_text(encoding='utf-8')
        # Fallback to full prompt if mini doesn't exist
        return self._get_prompt_content()

    def _should_use_mini(self) -> Tuple[bool, str]:
        """
        Check if mini prompt should be used based on skills installation.

        Reads BABEL_SKILLS_INSTALLED from project .env file.

        Returns:
            Tuple of (use_mini: bool, reason: str)
        """
        skills_installed = get_env_variable(self.project_dir, "BABEL_SKILLS_INSTALLED")

        if skills_installed and skills_installed.lower() == "true":
            target = get_env_variable(self.project_dir, "BABEL_SKILLS_TARGET") or "unknown"
            return True, f"Skills installed for {target}"
        else:
            return False, "Skills not installed (BABEL_SKILLS_INSTALLED != true)"

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

    def install(self, force: bool = False, mode: str = "full"):
        """
        Install system prompt to IDE-specific location.

        Auto-detects IDE (Claude Code, Cursor, etc.) and installs
        the prompt to the appropriate location.

        Args:
            force: Overwrite existing prompt file if True
            mode: "full" | "mini" | "auto"
                  - full: Install complete system prompt (default)
                  - mini: Install lightweight prompt (when skills installed)
                  - auto: Check BABEL_SKILLS_INSTALLED to decide
        """
        symbols = self.symbols
        ide_type, ide_name, target_path = self._detect_ide()

        # Determine prompt mode and content
        if mode == "auto":
            use_mini, reason = self._should_use_mini()
            print(f"Auto-detect: {reason}")
            mode = "mini" if use_mini else "full"

        if mode == "mini":
            prompt_content = self._get_mini_prompt_content()
            source_path = self._get_mini_prompt_path()
            mode_label = "mini"
        else:
            prompt_content = self._get_prompt_content()
            source_path = self._get_system_prompt_path()
            mode_label = "full"

        # Check if target exists
        if target_path.exists() and not force:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL PROMPT", "Already Installed")
            template.section("STATUS", f"{symbols.check_pass} Prompt already installed: {target_path}")
            template.section("ACTION", "To update, use: babel prompt --install --force")
            output = template.render(command="prompt", context={"already_installed": True})
            print(output)
            return

        # Install prompt
        success, message = install_prompt(
            self.project_dir,
            ide_type,
            prompt_content,
            force=force
        )

        if success:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL PROMPT", "Installed")
            template.section("STATUS", f"{symbols.check_pass} {message}")
            template.section("IDE", f"{ide_name} will now use Babel's {mode_label} system prompt.")

            # Show prompt source info
            if source_path.exists():
                line_count = len(prompt_content.splitlines())
                template.section("SOURCE", f"{source_path.name} ({line_count} lines, {mode_label})")
            else:
                template.section("SOURCE", "embedded fallback")

            template.footer(f"{symbols.check_pass} Prompt ready")
            output = template.render(command="prompt", context={"installed": True, "mode": mode_label})
            print(output)
        else:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL PROMPT", "Installation Failed")
            template.section("ERROR", f"{symbols.check_warn} {message}")
            output = template.render(command="prompt", context={"error": True})
            print(output)

    def status(self):
        """
        Show system prompt installation status.

        Displays:
        - Detected IDE
        - Expected prompt location
        - Installation status
        - Skills installation status
        - Recommendations
        """
        symbols = self.symbols
        ide_type, ide_name, target_path = self._detect_ide()
        source_path = self._get_system_prompt_path()
        mini_path = self._get_mini_prompt_path()

        template = OutputTemplate(symbols=symbols)
        template.header("BABEL PROMPT", "Status")

        # IDE detection section
        ide_lines = [
            f"Detected IDE: {ide_name}",
            f"Prompt path:  {target_path}"
        ]
        template.section("IDE", "\n".join(ide_lines))

        # Installation status section
        installed_mode = None
        status_lines = []

        if target_path.exists():
            installed_content = target_path.read_text(encoding='utf-8')
            installed_lines = len(installed_content.splitlines())

            # Detect if mini or full based on line count
            mini_lines_count = len(self._get_mini_prompt_content().splitlines())
            full_lines_count = len(self._get_prompt_content().splitlines())

            if abs(installed_lines - mini_lines_count) < 50:
                installed_mode = "mini"
            elif abs(installed_lines - full_lines_count) < 50:
                installed_mode = "full"
            else:
                installed_mode = "custom"

            status_lines.append(f"{symbols.check_pass} Installed ({installed_lines} lines, {installed_mode})")

            # Check if up-to-date against appropriate source
            if installed_mode == "mini":
                current_content = self._get_mini_prompt_content()
            else:
                current_content = self._get_prompt_content()

            if installed_content.strip() == current_content.strip():
                status_lines.append(f"{symbols.check_pass} Up to date")
            else:
                status_lines.append(f"{symbols.check_warn} Outdated (update with --force)")
        else:
            status_lines.append(f"{symbols.check_fail} Not installed")

        template.section("STATUS", "\n".join(status_lines))

        # Skills installation status section
        use_mini, reason = self._should_use_mini()
        skills_target = get_env_variable(self.project_dir, "BABEL_SKILLS_TARGET") or "none"
        skills_lines = []
        if use_mini:
            skills_lines.append(f"{symbols.check_pass} Installed ({skills_target})")
            skills_lines.append(f"Recommended: mini prompt (--mini or --auto)")
        else:
            skills_lines.append(f"{symbols.check_fail} Not installed")
            skills_lines.append(f"Recommended: full prompt (default)")

        template.section("SKILLS", "\n".join(skills_lines))

        # Source files section
        full_lines = len(self._get_prompt_content().splitlines())
        mini_lines = len(self._get_mini_prompt_content().splitlines())
        source_lines = [
            f"Full: {source_path.name} ({full_lines} lines)",
            f"Mini: {mini_path.name} ({mini_lines} lines)"
        ]
        template.section("SOURCE", "\n".join(source_lines))

        # Actions section
        action_lines = []
        if not target_path.exists():
            action_lines.append("Install full: babel prompt --install")
            action_lines.append("Install mini: babel prompt --install --mini")
            action_lines.append("Auto-detect:  babel prompt --install --auto")
        else:
            action_lines.append("Update full:  babel prompt --install --force")
            action_lines.append("Update mini:  babel prompt --install --mini --force")
            action_lines.append("Auto-detect:  babel prompt --install --auto --force")
        action_lines.append("View:         babel prompt")

        template.section("ACTIONS", "\n".join(action_lines))

        output = template.render(command="prompt", context={
            "installed": target_path.exists(),
            "mode": installed_mode,
            "skills_installed": use_mini
        })
        print(output)


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'prompt'


def register_parser(subparsers):
    """Register prompt command parser."""
    p = subparsers.add_parser('prompt', help='Manage system prompt for LLM integration')
    p.add_argument('--install', action='store_true',
                   help='Install prompt to IDE-specific location (default: full)')
    p.add_argument('--mini', action='store_true',
                   help='With --install: use lightweight prompt (when skills installed)')
    p.add_argument('--auto', action='store_true',
                   help='With --install: auto-select based on BABEL_SKILLS_INSTALLED')
    p.add_argument('--force', action='store_true',
                   help='Overwrite existing prompt file')
    p.add_argument('--status', action='store_true',
                   help='Show installation status and recommendations')
    return p


def handle(cli, args):
    """Handle prompt command dispatch."""
    if args.status:
        cli._prompt_cmd.status()
    elif args.install:
        # Determine mode: auto > mini > full
        if args.auto:
            mode = "auto"
        elif args.mini:
            mode = "mini"
        else:
            mode = "full"
        cli._prompt_cmd.install(force=args.force, mode=mode)
    else:
        cli._prompt_cmd.show()