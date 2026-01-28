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
from ..presentation.formatters import format_timestamp
from ..presentation.template import OutputTemplate


class HistoryCommand(BaseCommand):
    """
    Command for event history and collaboration.

    HC5: Graceful Sync — team collaboration works.
    Manages event timeline, promotion, and synchronization.
    """

    # Artifact type → actionable commands mapping
    # Used for legend display (DRY: stated once, not repeated per-event)
    ARTIFACT_ACTIONS = {
        'decision': ['link', 'endorse', 'evidence-decision', 'deprecate'],
        'constraint': ['link', 'deprecate'],
        'purpose': ['link'],
        'principle': ['link'],
        'requirement': ['link'],
        'boundary': ['link'],
        'tension': ['resolve', 'evidence'],
    }

    def _format_artifact_legend(self, events: list) -> dict:
        """
        Build legend of artifact types → available actions.

        Only shows types present in the event list.
        Follows DRY: actions stated once in legend, not repeated per-event.

        Returns:
            Dict mapping artifact types to action descriptions for template legend.
        """
        # Collect unique artifact types present in events
        types_present = set()
        for event in events:
            if event.parent_id:
                node = self.graph.get_node(event.parent_id)
                if node:
                    types_present.add(node.type)
                elif event.data.get('artifact_type'):
                    types_present.add(event.data.get('artifact_type'))

        if not types_present:
            return {}

        legend = {}
        for artifact_type in sorted(types_present):
            actions = self.ARTIFACT_ACTIONS.get(artifact_type, ['link'])
            legend[artifact_type] = ', '.join(actions)
        return legend

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

        symbols = self.symbols
        scope_label = f" ({scope_filter})" if scope_filter else ""

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL HISTORY", f"Recent activity{scope_label}")

        # Legend: scope markers + artifact types → actions (DRY)
        base_legend = {
            symbols.shared: "shared",
            symbols.local: "local"
        }
        artifact_legend = self._format_artifact_legend(events)
        template.legend(base_legend)

        # Build events list
        event_lines = []
        for event in events:
            # Scope marker
            scope_marker = symbols.shared if event.is_shared else symbols.local

            # Human-friendly formatting (HC6)
            # Dual-Display: [ID] + readable description for comprehension AND action
            # P12: Time always shown - no flags, no parameters
            timestamp = format_timestamp(event.timestamp)
            event_id_formatted = self._cli.format_id(event.id)

            if event.type == EventType.CONVERSATION_CAPTURED:
                preview = event.data.get('content', '')[:40]
                event_lines.append(f"  {scope_marker} {timestamp} {event_id_formatted} Captured: \"{preview}...\"")
            elif event.type == EventType.PURPOSE_DECLARED:
                event_lines.append(f"  {scope_marker} {timestamp} {event_id_formatted} Purpose: {event.data.get('purpose', '')[:40]}")
            elif event.type == EventType.ARTIFACT_CONFIRMED:
                artifact_type = event.data.get('artifact_type', 'artifact')
                event_lines.append(f"  {scope_marker} {timestamp} {event_id_formatted} Confirmed: {artifact_type}")
            elif event.type == EventType.COMMIT_CAPTURED:
                hash_short = event.data.get('hash', '')[:8]
                message = event.data.get('message', '')[:35]
                event_lines.append(f"  {scope_marker} {timestamp} {event_id_formatted} Commit: [{hash_short}] {message}")
            elif event.type == EventType.EVENT_PROMOTED:
                promoted_id = event.data.get('promoted_id', '')
                promoted_alias = self._cli.codec.encode(promoted_id) if promoted_id else ''
                event_lines.append(f"  {scope_marker} {timestamp} {event_id_formatted} Promoted: {promoted_alias}")
            else:
                type_display = event.type.value.replace('_', ' ').title()
                event_lines.append(f"  {scope_marker} {timestamp} {event_id_formatted} {type_display}")

            # Self-documenting: show artifact info when available
            # Actions shown in legend (DRY), here just type + ID
            artifact_id, artifact_type = self._get_artifact_info(event)
            if artifact_id:
                artifact_id_formatted = self._cli.format_id(artifact_id)
                event_lines.append(f"      {artifact_type} {artifact_id_formatted}")

        template.section(f"EVENTS ({len(events)} events)", "\n".join(event_lines))

        # Artifact actions legend section (if any)
        if artifact_legend:
            legend_lines = [f"  {atype}: {actions}" for atype, actions in artifact_legend.items()]
            template.section("ARTIFACT ACTIONS", "\n".join(legend_lines))

        # Footer
        template.footer(f"{len(events)} events displayed")

        # Render with succession hints
        output = template.render(command="history", context={})
        print(output)

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

            # Use parent_id when set (artifact ID) for consistent command usage
            display_id = event.parent_id if event.parent_id else event.id
            rows.append({
                "scope": "S" if event.is_shared else "L",
                "time": format_timestamp(event.timestamp),  # P12: time always shown
                "id": self._cli.codec.encode(display_id),
                "type": event.type.value.replace('_', ' ').title()[:15],
                "description": description
            })

        scope_label = f" ({scope_filter})" if scope_filter else ""
        return OutputSpec(
            data=rows,
            shape="table",
            columns=["", "Time", "ID", "Type", "Description"],
            column_keys=["scope", "time", "id", "type", "description"],
            title=f"Recent activity{scope_label} ({len(events)} events)",
            command="history",
            context={}
        )

    def share(self, event_id: str):
        """
        Promote an event from local to shared.

        Args:
            event_id: Event ID (alias code or prefix) to promote
        """
        symbols = self.symbols

        # Resolve alias code to raw ID (counterpart to format_id for output)
        event_id = self._cli.resolve_id(event_id)

        # Find event by ID prefix
        all_events = self.events.read_all()
        matches = [e for e in all_events if e.id.startswith(event_id)]

        if not matches:
            # Build error template
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SHARE", "Event Promotion")
            template.section("ERROR", f"Event not found: {event_id}")

            local = self.events.read_local()[-5:]
            if local:
                local_lines = []
                for e in local:
                    preview = self._event_preview(e)
                    local_lines.append(f"  {self._cli.format_id(e.id)} {preview}")
                template.section("RECENT LOCAL EVENTS", "\n".join(local_lines))

            print(template.render())
            return

        if len(matches) > 1:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SHARE", "Event Promotion")

            match_lines = []
            for e in matches:
                preview = self._event_preview(e)
                match_lines.append(f"  {self._cli.format_id(e.id)} {preview}")
            template.section("MULTIPLE MATCHES", f"Multiple matches for '{event_id}':\n" + "\n".join(match_lines))
            template.footer("Be more specific")

            print(template.render())
            return

        event = matches[0]

        if event.is_shared:
            print(f"Already shared: {event_id}")
            return

        promoted = self.events.promote(event.id)
        if promoted:
            preview = self._event_preview(promoted)

            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SHARE", "Event Promotion")
            template.section("SHARED", f"{preview}\n  (Will sync with git push)")
            template.footer("Event promoted to shared scope")

            output = template.render(command="share", context={})
            print(output)
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

    def _get_artifact_info(self, event: Event) -> tuple:
        """
        Get artifact info for an event if it has an associated artifact.

        Returns:
            Tuple of (artifact_id, artifact_type) or (None, None)
            Actions are shown in legend (DRY), not returned per-event.
        """
        if not event.parent_id:
            return None, None

        # Try to find artifact type from graph
        artifact_type = None
        node = self.graph.get_node(event.parent_id)
        if node:
            artifact_type = node.type

        # Fallback: check event data for artifact_type
        if not artifact_type:
            artifact_type = event.data.get('artifact_type', 'artifact')

        return event.parent_id, artifact_type

    def sync(self, verbose: bool = False):
        """
        Synchronize events after git pull.

        Deduplicates shared events and rebuilds graph.
        """
        symbols = self.symbols

        # Perform sync operation
        result = self.events.sync()

        # Rebuild graph from merged events (via CLI)
        self._cli._rebuild_graph()

        shared, local = self.events.count_by_scope()

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL SYNC", "Post-Git-Pull Synchronization")
        template.legend({
            symbols.shared: "shared",
            symbols.local: "local"
        })

        # Sync results section
        result_lines = []
        if result["deduplicated"] > 0:
            result_lines.append(f"Resolved {result['deduplicated']} duplicate(s)")
        result_lines.append(f"Events: {symbols.shared} {shared} shared, {symbols.local} {local} local")
        template.section("SYNC RESULTS", "\n".join(result_lines))

        # Verbose: show recent shared events
        if verbose:
            recent_shared = self.events.read_shared()[-5:]
            if recent_shared:
                recent_lines = []
                for e in recent_shared:
                    preview = self._event_preview(e)
                    scope_marker = symbols.shared if e.is_shared else symbols.local
                    # P12: Time always shown
                    recent_lines.append(f"  {scope_marker} {format_timestamp(e.timestamp)} | {preview}")
                template.section("RECENT SHARED", "\n".join(recent_lines))

        # Footer
        template.footer("Done")

        # Render with succession hints
        output = template.render(command="sync", context={})
        print(output)


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
