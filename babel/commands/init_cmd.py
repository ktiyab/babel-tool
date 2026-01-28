"""
InitCommand — Project initialization and setup

Handles project initialization (P1 compliance):
- Creating project with purpose grounded in need
- Installing system prompt template
- Installing manual files to .babel/manual/ for AI operator access
- Outputting system prompt for LLM integration
- Auto-detecting IDE and installing LLM-specific prompt
- Auto-detecting CPU cores and configuring parallelization
"""

import multiprocessing
import shutil
from pathlib import Path

from ..commands.base import BaseCommand
from ..core.events import Event, EventType, declare_purpose
from ..core.scope import EventScope
from ..services.providers import get_provider_status
from ..content import MINIMAL_SYSTEM_PROMPT, BABEL_LLM_INSTRUCTIONS
from ..services.ide import detect_ide, get_ide_info, install_prompt, IDEType
from ..presentation.template import OutputTemplate


class InitCommand(BaseCommand):
    """
    Command for project initialization.

    P1: Bootstrap from Need — every project must start from
    an explicitly stated need that grounds the purpose in reality.
    """

    def init(self, purpose: str, need: str = None):
        """
        Initialize project with purpose grounded in need (P1 compliance).

        Args:
            purpose: What we intend to build
            need: What problem we're solving (P1: Bootstrap from Need)

        P1 requires: "Every discussion must start from an explicitly stated need."
        The need grounds the purpose in reality.
        """
        symbols = self.symbols

        # Create project event (shared - team decision)
        event = Event(
            type=EventType.PROJECT_CREATED,
            data={"path": str(self.project_dir)}
        )
        self.events.append(event, scope=EventScope.SHARED)

        # Declare purpose grounded in need (shared - team decision)
        purpose_event = declare_purpose(purpose, need=need)
        self.events.append(purpose_event, scope=EventScope.SHARED)
        self.graph._project_event(purpose_event)

        # Index purpose into refs (O(1) lookup)
        self.refs.index_event(purpose_event, self.vocabulary)

        # Copy system prompt template to project root
        self._install_system_prompt()

        # Install manual files for AI operator access
        manual_installed, manual_message = self._install_manual()

        # Ensure .env files and .babel/manual are protected from git
        env_patterns_added, gitignore_message = self._ensure_gitignore_protection()

        # Auto-detect IDE and install LLM-specific prompt
        ide_type, ide_message = self._install_llm_prompt()

        # Auto-detect CPU cores and configure parallelization
        parallel_config, parallel_message = self._configure_parallelization()

        # Create project-local .babel/.env with BABEL_PROJECT_PATH
        project_env_created, project_env_message = self._create_project_env()

        # Build output with OutputTemplate
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL INIT", "Project Initialized (P1)")
        template.legend({
            symbols.shared: "shared with team via git"
        })

        # PROJECT section
        project_line = f"{symbols.shared} {self.project_dir}"
        template.section("PROJECT", project_line)

        # CONFIG section
        template.section("CONFIG", project_env_message)

        # PURPOSE section (with optional need grounding)
        if need:
            purpose_lines = f"Need: {need}\n{symbols.tree_end} Purpose: {purpose}"
        else:
            purpose_lines = f"Purpose: {purpose}\n  (Consider adding --need to ground in reality)"
        template.section("PURPOSE (P1)", purpose_lines)

        # EXTRACTION section
        status = get_provider_status(self.config)
        extraction_lines = [f"Status: {status}"]
        if not self.extractor.is_available:
            env_key = self.config.llm.remote.api_key_env
            extraction_lines.append(f"Set {env_key} for AI-powered extraction")
            extraction_lines.append("(Basic mode works fine for testing)")
        template.section("EXTRACTION", "\n".join(extraction_lines))

        # USAGE section
        usage_lines = [
            "babel capture \"your text\"        # Capture thoughts",
            "babel capture \"text\" --share     # Share with team"
        ]
        template.section("USAGE", "\n".join(usage_lines))

        # LLM INTEGRATION section
        template.section("LLM INTEGRATION", ide_message)

        # MANUAL section (conditional)
        if manual_installed:
            template.section("MANUAL", manual_message)

        # SECURITY section (conditional)
        if env_patterns_added:
            template.section("SECURITY", f"{gitignore_message} (prevents credential leakage)")

        # PARALLELIZATION section (conditional)
        if parallel_config:
            template.section("PARALLELIZATION", parallel_message)

        template.footer(f"{symbols.shared} Project shared with team via git")
        output = template.render(command="init", context={
            "has_need": bool(need),
            "extractor_available": self.extractor.is_available
        })
        print(output)

    def _install_system_prompt(self):
        """Copy system prompt template to project root."""
        # Find template in package (babel/prompts/system_prompt.md)
        template_path = Path(__file__).parent.parent / "prompts" / "system_prompt.md"
        target_path = self.project_dir / ".system_prompt.md"

        if target_path.exists():
            # Already exists, don't overwrite
            return

        if template_path.exists():
            shutil.copy(template_path, target_path)
        else:
            # Fallback: create minimal prompt if template missing
            self._create_minimal_system_prompt(target_path)

    def _create_minimal_system_prompt(self, path: Path):
        """Create minimal system prompt if template not found."""
        if path.exists():
            return
        path.write_text(MINIMAL_SYSTEM_PROMPT, encoding="utf-8")

    def _install_manual(self) -> tuple:
        """
        Copy manual files from package to .babel/manual/ for AI operator access.

        AI operators need local access to command documentation regardless of
        where the package is installed. This copies the manual files to a
        predictable location within the project.

        Returns:
            Tuple of (files_copied: int, message: str)
        """
        # Find manual in package installation
        source_dir = Path(__file__).parent.parent / "manual"
        target_dir = self.project_dir / ".babel" / "manual"

        if not source_dir.exists():
            return 0, "Manual source not found in package"

        # Create target directory if needed
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy all manual files
        files_copied = 0
        for source_file in source_dir.glob("*.md"):
            target_file = target_dir / source_file.name
            shutil.copy2(source_file, target_file)
            files_copied += 1

        if files_copied > 0:
            return files_copied, f"Installed {files_copied} manual files to .babel/manual/"
        else:
            return 0, "No manual files found to install"

    def _ensure_gitignore_protection(self) -> tuple:
        """
        Ensure .env files and .babel/manual are excluded from git.

        Security: Adds .env patterns to .gitignore if not already present.
        This is secure-by-default behavior - users who want .env committed
        can remove the entries (rare, discouraged).

        .babel/manual/ is excluded because it's regenerable from the package
        installation and should not be tracked in version control.

        Returns:
            Tuple of (entries_added: list, message: str)
        """
        gitignore_path = self.project_dir / ".gitignore"

        # Patterns to protect (NOT .env.example - that's a template)
        # .babel/manual/ is regenerable from package, no need to track
        # .babel/.env contains local paths (BABEL_PROJECT_PATH)
        env_patterns = [".env", ".env.local", ".env*.local", ".babel/.env", ".babel/manual/"]

        # If no .gitignore exists, create one with protection patterns
        if not gitignore_path.exists():
            content = "# Environment files (contain secrets - never commit)\n"
            content += ".env\n.env.local\n.env*.local\n\n"
            content += "# Babel local config (contains machine-specific paths)\n"
            content += ".babel/.env\n\n"
            content += "# Babel manual (regenerable from package)\n"
            content += ".babel/manual/\n"
            gitignore_path.write_text(content, encoding="utf-8")
            return env_patterns, "Created .gitignore with credential and manual protection"

        # Read existing .gitignore
        existing_content = gitignore_path.read_text(encoding="utf-8")
        existing_lines = set(line.strip() for line in existing_content.splitlines())

        # Find patterns not yet excluded
        missing_patterns = [p for p in env_patterns if p not in existing_lines]

        if not missing_patterns:
            return [], "Credential protection already in .gitignore"

        # Append missing patterns
        addition = "\n# Environment files (contain secrets - never commit)\n"
        addition += "\n".join(missing_patterns) + "\n"

        with open(gitignore_path, "a") as f:
            # Ensure we start on a new line
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            f.write(addition)

        return missing_patterns, f"Added {', '.join(missing_patterns)} to .gitignore"

    def _configure_parallelization(self) -> tuple:
        """
        Auto-detect CPU cores and configure parallelization in .env.

        Detects hardware capabilities and sets optimal defaults:
        - BABEL_CPU_WORKERS: Half of available cores (leaves headroom)
        - BABEL_IO_WORKERS: 4 (sufficient for most I/O workloads)
        - BABEL_LLM_CONCURRENT: 3 (respects API rate limits)

        Returns:
            Tuple of (config_dict, message) describing what was configured
        """
        env_path = self.project_dir / ".env"

        # Detect hardware
        cpu_count = multiprocessing.cpu_count()
        cpu_workers = max(1, cpu_count // 2)
        io_workers = 4
        llm_concurrent = 3

        # Build config lines
        parallel_config = {
            "BABEL_PARALLEL_ENABLED": "true",
            "BABEL_CPU_WORKERS": str(cpu_workers),
            "BABEL_IO_WORKERS": str(io_workers),
            "BABEL_LLM_CONCURRENT": str(llm_concurrent),
        }

        # Check what's already configured
        existing_content = ""
        existing_keys = set()
        if env_path.exists():
            existing_content = env_path.read_text(encoding="utf-8")
            for line in existing_content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    # Handle both 'export KEY=val' and 'KEY=val'
                    key_part = line.split("=")[0].replace("export ", "").strip()
                    existing_keys.add(key_part)

        # Find keys not yet configured
        missing_keys = {k: v for k, v in parallel_config.items() if k not in existing_keys}

        if not missing_keys:
            return {}, f"Detected {cpu_count} cores (parallelization already configured)"

        # Build section to append
        section = "\n# -----------------------------------------------------------------------------\n"
        section += f"# Parallelization (auto-detected: {cpu_count} cores)\n"
        section += "# -----------------------------------------------------------------------------\n"
        for key, value in missing_keys.items():
            section += f"export {key}={value}\n"

        # Append to .env
        with open(env_path, "a") as f:
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            f.write(section)

        message = f"Detected {cpu_count} cores → CPU_WORKERS={cpu_workers}, IO_WORKERS={io_workers}"
        return missing_keys, message

    def _create_project_env(self) -> tuple:
        """
        Create .babel/.env file with project-specific configuration.

        Sets BABEL_PROJECT_PATH to ensure commands always target this project
        regardless of current working directory.

        Returns:
            Tuple of (created: bool, message: str)
        """
        babel_dir = self.project_dir / ".babel"
        env_path = babel_dir / ".env"

        # Ensure .babel directory exists
        babel_dir.mkdir(parents=True, exist_ok=True)

        # Get absolute path for the project
        project_path = str(self.project_dir.resolve())

        # Check if already configured
        if env_path.exists():
            existing_content = env_path.read_text(encoding="utf-8")
            if "BABEL_PROJECT_PATH" in existing_content:
                return False, f"Project config exists: {env_path}"

        # Create or append to .babel/.env
        content = ""
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            if content and not content.endswith("\n"):
                content += "\n"

        content += "# -----------------------------------------------------------------------------\n"
        content += "# Babel Project Configuration\n"
        content += "# Generated by: babel init\n"
        content += "# -----------------------------------------------------------------------------\n"
        content += "\n"
        content += "# Project root path - ensures babel commands target this project\n"
        content += "# regardless of current working directory\n"
        content += f"export BABEL_PROJECT_PATH={project_path}\n"

        env_path.write_text(content, encoding="utf-8")

        return True, f"Project config: {env_path}"

    def _install_llm_prompt(self):
        """
        Auto-detect IDE and install LLM-specific prompt.

        Reads from system_prompt.md (single source of truth).
        Falls back to embedded constant if file not found.

        Returns:
            Tuple of (IDEType, message) describing what was installed
        """
        # Get config override if set
        config_override = None
        if hasattr(self.config, 'ide') and hasattr(self.config.ide, 'type'):
            config_override = self.config.ide.type

        # Detect IDE environment
        ide_type = detect_ide(self.project_dir, config_override)
        ide_name, prompt_path = get_ide_info(ide_type)

        # Read system_prompt.md (single source of truth)
        # Primary: babel/prompts/system_prompt.md
        system_prompt_path = Path(__file__).parent.parent / "prompts" / "system_prompt.md"
        if system_prompt_path.exists():
            prompt_content = system_prompt_path.read_text(encoding='utf-8')
        else:
            # Fallback to embedded constant if file missing
            prompt_content = BABEL_LLM_INSTRUCTIONS

        # Install prompt for detected IDE
        success, message = install_prompt(
            self.project_dir,
            ide_type,
            prompt_content,
            force=False
        )

        if success:
            return ide_type, f"Detected {ide_name}: {prompt_path}"
        else:
            # File exists, just inform
            return ide_type, f"{ide_name} prompt exists: {prompt_path}"

    def prompt(self):
        """Output system prompt for LLM integration."""
        prompt_path = self.project_dir / ".system_prompt.md"

        if not prompt_path.exists():
            # Try to install it
            self._install_system_prompt()

        if prompt_path.exists():
            print(prompt_path.read_text(encoding="utf-8"))
        else:
            print("System prompt not found. Run: babel init \"purpose\"")


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

def register_parser(subparsers):
    """Register init command parser."""
    p = subparsers.add_parser('init', help='Start a new project')
    p.add_argument('purpose', help='What are you building?')
    p.add_argument('--need', '-n',
                   help='What problem are you solving? (P1: grounds purpose in reality)')
    return p


def handle(cli, args):
    """Handle init command dispatch."""
    cli._init_cmd.init(args.purpose, need=args.need)
