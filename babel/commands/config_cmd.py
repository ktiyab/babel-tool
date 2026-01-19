"""
ConfigCommand — Configuration management and queue processing

Handles configuration operations:
- Processing queued extractions
- Displaying current configuration
- Setting configuration values
"""

from ..commands.base import BaseCommand
from ..presentation.symbols import safe_print


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
        if not self.extractor.is_available:
            env_key = self.config.llm.api_key_env
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

        print(f"Found {len(proposals)} artifact(s):\n")

        # Batch mode: queue all proposals for later review (for AI assistants)
        if batch_mode:
            queued_count = 0
            for proposal in proposals:
                # Layer 2 (Encoding): Use safe_print for LLM-generated content
                safe_print(f"[{proposal.artifact_type.upper()}] {proposal.content.get('summary', 'No summary')}")
                self._cli._capture_cmd._queue_proposal(proposal)
                queued_count += 1

            print(f"\nQueued {queued_count} proposal(s) for review.")
            print("Human review with: babel review")

            # Succession hint (centralized)
            from ..output import end_command
            end_command("process-queue", {"has_proposals": queued_count > 0})
            return

        # Interactive mode: confirm each proposal (for humans)
        for proposal in proposals:
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(self.extractor.format_for_confirmation(proposal))
            response = input("> ").strip().lower()

            if response in ['y', 'yes', '']:
                self._cli._capture_cmd._confirm_proposal(proposal)
                print("Confirmed.\n")
            else:
                print("Skipped.\n")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("process-queue", {})

    def show_config(self):
        """Show current configuration."""
        print(self._cli.config_manager.display())

        # Succession hint (centralized)
        from ..output import end_command
        end_command("config", {})

    def set_config(self, key: str, value: str, scope: str = "project"):
        """Set a configuration value."""
        error = self._cli.config_manager.set(key, value, scope)
        if error:
            print(f"Error: {error}")
        else:
            print(f"Set {key} = {value}")
            if scope == "project":
                print(f"Saved to: {self._cli.config_manager.project_config_path}")
            else:
                print(f"Saved to: {self._cli.config_manager.user_config_path}")
