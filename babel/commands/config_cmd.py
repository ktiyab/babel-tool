"""
ConfigCommand — Configuration management and queue processing

Handles configuration operations:
- Processing queued extractions
- Displaying current configuration
- Setting configuration values
- LLM benchmark for comparing local vs remote extraction
"""

from ..commands.base import BaseCommand
from ..presentation.symbols import safe_print
from ..presentation.template import OutputTemplate
from ..services.benchmark import run_benchmark, format_results


class ConfigCommand(BaseCommand):
    """
    Command for configuration management.

    Provides access to configuration display, modification,
    and extraction queue processing.
    """

    def process_queue(self, batch_mode: bool = False):
        """
        Process queued extractions (after coming back online).

        Args:
            batch_mode: If True, queue proposals for review instead of interactive confirm.
                        Enables AI assistants to complete the flow (HC2 compliant).
        """
        symbols = self.symbols

        if not self.extractor.is_available:
            env_key = self.config.llm.remote.api_key_env
            print(f"AI extraction not available. Set {env_key} to enable.")
            return

        if not self.extractor.queue:
            print("No queue configured.")
            return

        queued = self.extractor.queue.count()
        if queued == 0:
            print("No items queued.")
            return

        print(f"Processing {queued} queued item(s)...\n")

        proposals = self.extractor.process_queue()

        if not proposals:
            print("No artifacts extracted from queued items.")
            return

        # Batch mode: queue all proposals for later review (for AI assistants)
        if batch_mode:
            queued_count = 0
            proposal_lines = []
            for proposal in proposals:
                summary = proposal.content.get('summary', 'No summary')
                proposal_lines.append(f"[{proposal.artifact_type.upper()}] {summary}")
                self._cli._capture_cmd._queue_proposal(proposal)
                queued_count += 1

            # Build output with OutputTemplate
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL PROCESS-QUEUE", f"Processed {queued} Item(s)")
            template.section("ARTIFACTS FOUND", "\n".join(proposal_lines))
            template.section("STATUS", f"Queued {queued_count} proposal(s) for review.")
            template.section("ACTION", "Human review with: babel review")
            template.footer(f"{symbols.check_pass} {queued_count} proposal(s) ready for review")
            output = template.render(command="process-queue", context={"has_proposals": queued_count > 0})
            print(output)
            return

        # Interactive mode: confirm each proposal (for humans) - PRESERVED
        print(f"Found {len(proposals)} artifact(s):\n")
        for proposal in proposals:
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(self.extractor.format_for_confirmation(proposal))
            response = input("> ").strip().lower()

            if response in ['y', 'yes', '']:
                self._cli._capture_cmd._confirm_proposal(proposal)
                print("Confirmed.\n")
            else:
                print("Skipped.\n")

    def show_config(self):
        """Show current configuration."""
        symbols = self.symbols

        # Build output with OutputTemplate
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL CONFIG", "Current Configuration")
        template.section("SETTINGS", self._cli.config_manager.display())
        output = template.render(command="config", context={})
        print(output)

    def set_config(self, key: str, value: str, scope: str = "project"):
        """Set a configuration value."""
        symbols = self.symbols
        error = self._cli.config_manager.set(key, value, scope)

        template = OutputTemplate(symbols=symbols)

        if error:
            template.header("BABEL CONFIG", "Error")
            template.section("ERROR", error)
            output = template.render(command="config", context={"error": True})
        else:
            template.header("BABEL CONFIG", "Configuration Updated")
            template.section("SETTING", f"Set {key} = {value}")
            if scope == "project":
                template.section("SAVED TO", str(self._cli.config_manager.project_config_path))
            else:
                template.section("SAVED TO", str(self._cli.config_manager.user_config_path))
            template.footer(f"{symbols.check_pass} Configuration saved")
            output = template.render(command="config", context={"updated": True})

        print(output)

    def benchmark(self, local_only: bool = False, remote_only: bool = False):
        """
        Run LLM benchmark comparing local vs remote extraction quality.

        Executes calibrated test cases at three difficulty levels (simple, medium, high)
        and displays side-by-side results for human evaluation.

        Args:
            local_only: Only test local LLM (skip remote)
            remote_only: Only test remote LLM (skip local)
        """
        symbols = self.symbols
        print("Running LLM benchmark...\n")

        # Progress callback (incremental output - not using OutputTemplate)
        test_count = [0]
        total_tests = 9 * (2 - int(local_only) - int(remote_only))

        def on_progress(test_id: str, provider: str):
            test_count[0] += 1
            print(f"  [{test_count[0]}/{total_tests}] {test_id} ({provider})")

        results = run_benchmark(
            self.config,
            local_only=local_only,
            remote_only=remote_only,
            on_test_complete=on_progress
        )

        # Check if any providers were available
        if not results.results:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL BENCHMARK", "No Providers Available")

            error_lines = []
            if results.local_error:
                error_lines.append(f"Local: {results.local_error}")
            if results.remote_error:
                error_lines.append(f"Remote: {results.remote_error}")
            if error_lines:
                template.section("ERRORS", "\n".join(error_lines))

            template.section("ACTION", "Fix provider configuration and retry.")
            output = template.render(command="config", context={"benchmark_error": True})
            print(output)
            return

        # Results output (format_results has its own formatting)
        print("\n")
        print(format_results(results))

        # Footer with succession hint
        template = OutputTemplate(symbols=symbols)
        template.footer(f"{symbols.check_pass} Benchmark complete")
        output = template.render(command="config", context={"benchmark": True})
        print(output)


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

# Multiple commands registered by this module
COMMAND_NAMES = ['config', 'process-queue', 'help', 'principles']


def register_parser(subparsers):
    """Register config, process-queue, help, and principles command parsers."""
    # config command
    p1 = subparsers.add_parser('config', help='View or set configuration')
    p1.add_argument('--set', metavar='KEY=VALUE',
                    help='Set config value (e.g., llm.provider=openai)')
    p1.add_argument('--user', action='store_true',
                    help='Apply to user config instead of project')
    p1.add_argument('--benchmark', action='store_true',
                    help='Run LLM benchmark comparing local vs remote extraction')
    p1.add_argument('--local-only', action='store_true',
                    help='Benchmark local LLM only (with --benchmark)')
    p1.add_argument('--remote-only', action='store_true',
                    help='Benchmark remote LLM only (with --benchmark)')

    # process-queue command
    p2 = subparsers.add_parser('process-queue',
                               help='Process queued extractions (after offline)')
    p2.add_argument('--batch', action='store_true',
                    help='Queue proposals for review instead of interactive confirm (for AI assistants)')

    # help command
    subparsers.add_parser('help', help='Show comprehensive help for all commands')

    # principles command
    subparsers.add_parser('principles', help='Show Babel principles for self-check (P11)')

    return p1, p2


def handle(cli, args):
    """Handle config, process-queue, help, or principles command dispatch."""
    if args.command == 'config':
        if args.benchmark:
            local_only = getattr(args, 'local_only', False)
            remote_only = getattr(args, 'remote_only', False)
            cli._config_cmd.benchmark(local_only=local_only, remote_only=remote_only)
        elif args.set:
            if '=' not in args.set:
                print("Error: Use format KEY=VALUE (e.g., llm.provider=openai)")
            else:
                key, value = args.set.split('=', 1)
                scope = "user" if args.user else "project"
                cli._config_cmd.set_config(key, value, scope)
        else:
            cli._config_cmd.show_config()
    elif args.command == 'process-queue':
        cli._config_cmd.process_queue(batch_mode=args.batch)
    elif args.command == 'help':
        cli.help()
    elif args.command == 'principles':
        cli.principles()
