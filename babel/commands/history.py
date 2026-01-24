"""
HistoryCommand — Event timeline and collaboration management

Handles event history display and collaboration:
- Recent event timeline with scope filtering
- Event promotion (local → shared)
- Synchronization after git operations
"""

from typing import Optional

from ..commands.base import BaseCommand
from ..core.events import Event, EventType


class HistoryCommand(BaseCommand):
    """
    Command for event history and collaboration.

    HC5: Graceful Sync — team collaboration works.
    Manages event timeline, promotion, and synchronization.
    """

    def history(self, limit: int = 10, scope_filter: Optional[str] = None, output_format: str = None):
        """
        Show recent events.

        Args:
            limit: Number of events to show
            scope_filter: "shared" | "local" | None (both)
            output_format: If specified, return OutputSpec for rendering
        """
        if scope_filter == "shared":
            events = self.events.read_shared()[-limit:]
        elif scope_filter == "local":
            events = self.events.read_local()[-limit:]
        else:
            events = self.events.read_all()[-limit:]

        # If output_format specified, return OutputSpec
        if output_format:
            return self._history_as_output(events, scope_filter)

        # Original behavior: print directly
        scope_label = f" ({scope_filter})" if scope_filter else ""
        print(f"\nRecent activity{scope_label} ({len(events)} events):\n")

        symbols = self.symbols

        for event in events:
            # Scope marker
            scope_marker = symbols.shared if event.is_shared else symbols.local

            # Human-friendly formatting (HC6)
            # Dual-Display: [ID] + readable description for comprehension AND action
            timestamp = event.timestamp[:10]  # Just date
            formatted_id = self._cli.format_id(event.id)

            if event.type == EventType.CONVERSATION_CAPTURED:
                preview = event.data.get('content', '')[:40]
                print(f"  {scope_marker} {timestamp} {formatted_id} Captured: \"{preview}...\"")
            elif event.type == EventType.PURPOSE_DECLARED:
                print(f"  {scope_marker} {timestamp} {formatted_id} Purpose: {event.data.get('purpose', '')[:40]}")
            elif event.type == EventType.ARTIFACT_CONFIRMED:
                artifact_type = event.data.get('artifact_type', 'artifact')
                print(f"  {scope_marker} {timestamp} {formatted_id} Confirmed: {artifact_type}")
            elif event.type == EventType.COMMIT_CAPTURED:
                hash_short = event.data.get('hash', '')[:8]
                message = event.data.get('message', '')[:35]
                print(f"  {scope_marker} {timestamp} {formatted_id} Commit: [{hash_short}] {message}")
            elif event.type == EventType.EVENT_PROMOTED:
                promoted_id = event.data.get('promoted_id', '')
                promoted_alias = self._cli.codec.encode(promoted_id) if promoted_id else ''
                print(f"  {scope_marker} {timestamp} {formatted_id} Promoted: {promoted_alias}")
            else:
                type_display = event.type.value.replace('_', ' ').title()
                print(f"  {scope_marker} {timestamp} {formatted_id} {type_display}")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("history", {})

    def _history_as_output(self, events: list, scope_filter: Optional[str] = None):
        """Return history data as OutputSpec for rendering."""
        from babel.output import OutputSpec

        rows = []
        for event in events:
            # Generate description based on event type
            if event.type == EventType.CONVERSATION_CAPTURED:
                description = f"Captured: \"{event.data.get('content', '')[:40]}...\""
            elif event.type == EventType.PURPOSE_DECLARED:
                description = f"Purpose: {event.data.get('purpose', '')[:40]}"
            elif event.type == EventType.ARTIFACT_CONFIRMED:
                description = f"Confirmed: {event.data.get('artifact_type', 'artifact')}"
            elif event.type == EventType.COMMIT_CAPTURED:
                hash_short = event.data.get('hash', '')[:8]
                message = event.data.get('message', '')[:35]
                description = f"Commit: [{hash_short}] {message}"
            elif event.type == EventType.EVENT_PROMOTED:
                promoted_id = event.data.get('promoted_id', '')
                promoted_alias = self._cli.codec.encode(promoted_id) if promoted_id else ''
                description = f"Promoted: {promoted_alias}"
            else:
                description = event.type.value.replace('_', ' ').title()

            rows.append({
                "scope": "S" if event.is_shared else "L",
                "date": event.timestamp[:10],
                "id": self._cli.codec.encode(event.id),
                "type": event.type.value.replace('_', ' ').title()[:15],
                "description": description
            })

        scope_label = f" ({scope_filter})" if scope_filter else ""
        return OutputSpec(
            data=rows,
            shape="table",
            columns=["", "Date", "ID", "Type", "Description"],
            column_keys=["scope", "date", "id", "type", "description"],
            title=f"Recent activity{scope_label} ({len(events)} events)",
            command="history",
            context={}
        )

    def share(self, event_id: str):
        """
        Promote an event from local to shared.

        Args:
            event_id: Event ID (or prefix) to promote
        """
        symbols = self.symbols

        # Find event by ID prefix
        all_events = self.events.read_all()
        matches = [e for e in all_events if e.id.startswith(event_id)]

        if not matches:
            print(f"Event not found: {event_id}")
            print(f"\nRecent local events:")
            local = self.events.read_local()[-5:]
            for e in local:
                preview = self._event_preview(e)
                print(f"  {self._cli.format_id(e.id)} {preview}")
            return

        if len(matches) > 1:
            print(f"Multiple matches for '{event_id}':")
            for e in matches:
                preview = self._event_preview(e)
                print(f"  {self._cli.format_id(e.id)} {preview}")
            print(f"\nBe more specific.")
            return

        event = matches[0]

        if event.is_shared:
            print(f"Already shared: {event_id}")
            return

        promoted = self.events.promote(event.id)
        if promoted:
            preview = self._event_preview(promoted)
            print(f"Shared: {preview}")
            print(f"  (Will sync with git push)")

            # Succession hint (centralized)
            from ..output import end_command
            end_command("share", {})
        else:
            print(f"Could not promote: {event_id}")

    def _event_preview(self, event: Event) -> str:
        """Generate short preview of event."""
        if event.type == EventType.CONVERSATION_CAPTURED:
            return f"Capture: \"{event.data.get('content', '')[:40]}...\""
        elif event.type == EventType.PURPOSE_DECLARED:
            return f"Purpose: {event.data.get('purpose', '')[:40]}"
        elif event.type == EventType.ARTIFACT_CONFIRMED:
            return f"Confirmed: {event.data.get('artifact_type', '')}"
        elif event.type == EventType.COMMIT_CAPTURED:
            return f"Commit: {event.data.get('message', '')[:40]}"
        else:
            return event.type.value.replace('_', ' ').title()

    def sync(self, verbose: bool = False):
        """
        Synchronize events after git pull.

        Deduplicates shared events and rebuilds graph.
        """
        symbols = self.symbols

        print("Syncing...")

        result = self.events.sync()

        if result["deduplicated"] > 0:
            print(f"  Resolved {result['deduplicated']} duplicate(s)")

        # Rebuild graph from merged events (via CLI)
        self._cli._rebuild_graph()

        shared, local = self.events.count_by_scope()
        print(f"  Events: {symbols.shared} {shared} shared, {symbols.local} {local} local")

        if verbose:
            # Show recent shared events
            recent_shared = self.events.read_shared()[-5:]
            if recent_shared:
                print(f"\nRecent shared:")
                for e in recent_shared:
                    preview = self._event_preview(e)
                    scope_marker = symbols.shared if e.is_shared else symbols.local
                    print(f"  {scope_marker} {e.timestamp[:10]} | {preview}")

        print("Done.")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("sync", {})


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

def register_parser(subparsers):
    """Register history command parser."""
    p = subparsers.add_parser('history', help='Show recent activity')
    p.add_argument('-n', type=int, default=10, help='Number of events')
    p.add_argument('--shared', action='store_true', help='Show only shared events')
    p.add_argument('--local', action='store_true', help='Show only local events')
    p.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json'],
                   help='Output format (overrides config)')
    return p


def handle(cli, args):
    """Handle history command dispatch."""
    # Convert shared/local flags to scope_filter
    scope_filter = None
    if args.shared:
        scope_filter = "shared"
    elif args.local:
        scope_filter = "local"

    cli._history_cmd.history(
        limit=args.n,
        scope_filter=scope_filter,
        output_format=getattr(args, 'format', None)
    )
