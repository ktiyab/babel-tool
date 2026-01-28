"""
GitCommand — Git integration and commit capture

Handles git-related operations:
- Capturing git commits with enhanced diff information
- Installing/uninstalling git hooks for automatic capture
- Git hooks status reporting
"""

from ..commands.base import BaseCommand
from ..core.events import EventType, capture_commit
from ..services.git import GitIntegration, format_commit_for_extraction
from ..tracking.coherence import format_coherence_status
from ..presentation.template import OutputTemplate


class GitCommand(BaseCommand):
    """
    Command for git integration and commit capture.

    Provides automatic capture of git commits and hook management
    for seamless integration with development workflow.
    """

    def capture_git_commit(self, async_mode: bool = False):
        """Capture the last git commit with enhanced diff information."""
        symbols = self.symbols
        git = GitIntegration(self.project_dir)

        if not git.is_git_repo:
            if not async_mode:
                print("Not a git repository.")
            return

        # Get commit with enhanced diff info
        commit = git.get_last_commit(include_diff=True)
        if not commit:
            if not async_mode:
                print("Could not read last commit.")
            return

        # Deduplication check using diff_id
        existing = self.events.read_by_type(EventType.COMMIT_CAPTURED)
        for e in existing:
            if e.data.get('diff_id', e.data.get('hash')) == commit.diff_id:
                if not async_mode:
                    print(f"Commit {commit.hash[:8]} already captured.")
                return

        # Create commit event with enhanced data
        structural_dict = commit.structural.to_dict() if commit.structural else None

        event = capture_commit(
            commit_hash=commit.hash,
            message=commit.message,
            body=commit.body,
            author=commit.author,
            files=commit.files,
            structural=structural_dict,
            comment_diff=commit.comment_diff
        )
        self.events.append(event)

        if not async_mode:
            print(f"Captured: {commit.hash[:8]} -- {commit.message[:50]}")
            if commit.structural:
                print(f"  {commit.structural.summary}")
            if commit.comment_diff:
                comment_lines = commit.comment_diff.count('\n') + 1
                print(f"  {comment_lines} code comment(s) extracted")

        # Extract from commit (queue if async or no LLM)
        text = format_commit_for_extraction(commit)

        if async_mode:
            # Queue for later extraction
            if self.extractor.queue:
                self.extractor.queue.add(text, event.id)

            # Silent coherence check if enabled
            if self.config.coherence.auto_check:
                try:
                    self.coherence.check(
                        trigger="commit",
                        triggered_by=commit.hash
                    )
                    # Don't print in async mode - user discovers via status
                except Exception:
                    pass  # Fail silently in async mode
        else:
            # Extract now (via capture command)
            self._cli._capture_cmd.extract_and_confirm(text, event.id)

            # Coherence check if enabled
            if self.config.coherence.auto_check:
                result = self.coherence.check(
                    trigger="commit",
                    triggered_by=commit.hash
                )
                if result.has_issues:
                    print(f"\n{symbols.tension} Coherence note:")
                    print(f"  {format_coherence_status(result, symbols)}")

    def install_hooks(self):
        """Install git hooks for automatic capture."""
        symbols = self.symbols
        git = GitIntegration(self.project_dir)

        success, message = git.install_hooks()

        template = OutputTemplate(symbols=symbols)

        if success:
            template.header("BABEL HOOKS", "Git Hooks Installed")
            template.section("STATUS", f"{symbols.check_pass} {message}")
            template.section("INFO", "Commits will now be captured automatically.")
            template.section("ACTION", "View captured commits with: babel history")
            template.footer(f"{symbols.check_pass} Hooks ready")
            output = template.render(command="hooks", context={"installed": True})
        else:
            template.header("BABEL HOOKS", "Installation Failed")
            template.section("ERROR", f"{symbols.check_fail} {message}")
            output = template.render(command="hooks", context={"error": True})

        print(output)

    def uninstall_hooks(self):
        """Remove git hooks."""
        symbols = self.symbols
        git = GitIntegration(self.project_dir)

        success, message = git.uninstall_hooks()

        template = OutputTemplate(symbols=symbols)

        if success:
            template.header("BABEL HOOKS", "Git Hooks Removed")
            template.section("STATUS", f"{symbols.check_pass} {message}")
            template.footer(f"{symbols.check_pass} Hooks removed")
            output = template.render(command="hooks", context={"uninstalled": True})
        else:
            template.header("BABEL HOOKS", "Uninstall Failed")
            template.section("ERROR", f"{symbols.check_fail} {message}")
            output = template.render(command="hooks", context={"error": True})

        print(output)

    def hooks_status(self):
        """Show git hooks status."""
        symbols = self.symbols
        git = GitIntegration(self.project_dir)

        status = git.hooks_status()

        template = OutputTemplate(symbols=symbols)
        template.header("BABEL HOOKS", "Status")
        template.section("GIT HOOKS", status)
        output = template.render(command="hooks", context={"status": status})
        print(output)


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

# Multiple commands registered by this module
COMMAND_NAMES = ['capture-commit', 'hooks']


def register_parser(subparsers):
    """Register capture-commit and hooks command parsers."""
    # capture-commit command
    p1 = subparsers.add_parser('capture-commit', help='Capture last git commit')
    p1.add_argument('--async', dest='async_mode', action='store_true',
                    help='Queue extraction for later')

    # hooks command
    p2 = subparsers.add_parser('hooks', help='Manage git hooks')
    hooks_sub = p2.add_subparsers(dest='hooks_command')
    hooks_sub.add_parser('install', help='Install git hooks')
    hooks_sub.add_parser('uninstall', help='Remove git hooks')
    hooks_sub.add_parser('status', help='Show hooks status')

    return p1, p2


def handle(cli, args):
    """Handle capture-commit or hooks command dispatch."""
    if args.command == 'capture-commit':
        cli._git_cmd.capture_git_commit(async_mode=args.async_mode)
    elif args.command == 'hooks':
        if args.hooks_command == 'install':
            cli._git_cmd.install_hooks()
        elif args.hooks_command == 'uninstall':
            cli._git_cmd.uninstall_hooks()
        elif args.hooks_command == 'status':
            cli._git_cmd.hooks_status()
        else:
            print("Usage: babel hooks {install|uninstall|status}")
