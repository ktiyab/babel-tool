"""
ListCommand — Graph-aware artifact discovery

Provides fast, offline artifact discovery by leveraging the graph structure:
- Overview: counts by type (instant orientation)
- Type listing: artifacts of a specific type (limited by default)
- Graph traversal: artifacts connected to a given artifact
- Orphans: artifacts with no connections

Design principles:
- P6: Token efficiency (limited default, progressive disclosure)
- HC3: Offline-first (no LLM required)
- HC6: Human-readable (dual-display: ID + summary)
"""

from typing import Optional, List
from ..commands.base import BaseCommand
from ..core.graph import Node
from ..presentation.symbols import truncate, SUMMARY_LENGTH
from ..utils.pagination import Paginator, DEFAULT_LIMIT


# Artifact types that can be listed
ARTIFACT_TYPES = ['decision', 'constraint', 'principle', 'purpose', 'tension']


def _get_summary(node: Node) -> str:
    """Extract human-readable summary from node content."""
    content = node.content

    # Try different fields in order of preference
    if 'summary' in content:
        return content['summary']
    if 'purpose' in content:
        return content['purpose']
    if 'what' in content:
        return content['what']

    # Handle proposal nodes (nested 'proposed' dict)
    proposed = content.get('proposed', {})
    if isinstance(proposed, dict):
        if 'summary' in proposed:
            return proposed['summary']
        if 'what' in proposed:
            return proposed['what']

    # Try nested detail
    detail = content.get('detail', {})
    if isinstance(detail, dict):
        if 'what' in detail:
            return detail['what']
        if 'goal' in detail:
            return detail['goal']

    # Fallback
    return str(content)[:SUMMARY_LENGTH]


class ListCommand(BaseCommand):
    """
    Command for graph-aware artifact discovery.

    Leverages graph structure for fast, offline discovery.
    No LLM required — uses graph edges and node data directly.
    """

    def list_overview(self):
        """
        Show artifact counts by type with drill-down hints.

        Default entry point — instant orientation without loading all artifacts.
        """
        symbols = self.symbols
        stats = self.graph.stats()

        print(f"\n{symbols.purpose} Artifacts: {stats['nodes']} total")
        print()

        # Count by type
        type_counts = {}
        for artifact_type in ARTIFACT_TYPES:
            nodes = self.graph.get_nodes_by_type(artifact_type)
            if nodes:
                type_counts[artifact_type] = len(nodes)

        # Display with hints
        for artifact_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {artifact_type}s: {count:>4}  {symbols.arrow} babel list {artifact_type}s")

        # Show orphan count (O(1) lookup)
        orphan_count = self.graph.count_orphans()
        if orphan_count > 0:
            print(f"\n  orphans: {orphan_count:>4}  {symbols.arrow} babel list --orphans")

        print()
        print(f"Graph traversal: babel list --from <id>")

        # Succession hint
        from ..output import end_command
        end_command("list", {"has_orphans": orphan_count > 0})

    def list_by_type(
        self,
        artifact_type: str,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        show_all: bool = False,
        filter_pattern: Optional[str] = None
    ):
        """
        List artifacts of a specific type.

        Args:
            artifact_type: Type to list (decision, constraint, principle, etc.)
            limit: Maximum items to show (default 10)
            offset: Number of items to skip (default 0)
            show_all: Show all items (ignore limit)
            filter_pattern: Optional keyword filter (case-insensitive)
        """
        symbols = self.symbols

        # Normalize type name (handle plural)
        if artifact_type.endswith('s'):
            artifact_type = artifact_type[:-1]

        if artifact_type not in ARTIFACT_TYPES:
            print(f"\nUnknown type: {artifact_type}")
            print(f"Valid types: {', '.join(ARTIFACT_TYPES)}")
            return

        # Get nodes
        nodes = self.graph.get_nodes_by_type(artifact_type)

        if not nodes:
            print(f"\nNo {artifact_type}s found.")
            return

        # Apply filter if provided
        if filter_pattern:
            pattern_lower = filter_pattern.lower()
            nodes = [n for n in nodes if pattern_lower in _get_summary(n).lower()]

            if not nodes:
                print(f"\nNo {artifact_type}s matching '{filter_pattern}'.")
                return

        # Use Paginator for consistent pagination
        if show_all:
            paginator = Paginator(nodes, limit=len(nodes) or 1, offset=0)
        else:
            paginator = Paginator(nodes, limit=limit, offset=offset)

        # Header
        title = f"{artifact_type.capitalize()}s"
        if filter_pattern:
            title = f"{title} matching '{filter_pattern}'"
        print(f"\n{paginator.header(title)}")

        # Display artifacts (dual-display: ID alias + summary)
        for node in paginator.items():
            formatted_id = self._cli.format_id(node.id)
            summary = truncate(_get_summary(node), SUMMARY_LENGTH - 15)
            print(f"  {formatted_id} {summary}")

        # Navigation hints
        cmd_base = f"babel list {artifact_type}s"
        if filter_pattern:
            cmd_base = f"{cmd_base} --filter \"{filter_pattern}\""

        if paginator.has_more():
            print()
            next_offset = paginator.offset + paginator.limit
            print(f"{symbols.arrow} Next: {cmd_base} --offset {next_offset}")

        if paginator.has_previous():
            prev_offset = max(0, paginator.offset - paginator.limit)
            print(f"{symbols.arrow} Prev: {cmd_base} --offset {prev_offset}")

        if paginator.is_truncated() and not show_all:
            print(f"{symbols.arrow} All: {cmd_base} --all")

        # Succession hint
        from ..output import end_command
        end_command("list", {"type": artifact_type, "truncated": paginator.is_truncated()})

    def list_from(self, artifact_id: str, depth: int = 1):
        """
        Show artifacts connected to a given artifact (graph traversal).

        Args:
            artifact_id: ID of the starting artifact
            depth: Traversal depth (default 1 = immediate connections)
        """
        symbols = self.symbols

        # Resolve ID using IDResolver (supports short codes via codec)
        result = self.resolver.resolve(artifact_id, codec=self.codec)
        if not result or not result.node:
            print(f"\nArtifact not found: {artifact_id}")
            print("Use full ID or unique prefix.")
            return

        node = result.node

        # Display the starting artifact (using alias formatting)
        formatted_id = self._cli.format_id(node.id)
        alias_code = self._cli.codec.encode(node.id)  # For actionable hints
        summary = truncate(_get_summary(node), SUMMARY_LENGTH)
        print(f"\n{formatted_id} {summary}")
        print(f"  Type: {node.type}")

        # Get incoming edges (what points TO this artifact)
        incoming = self.graph.get_incoming(node.id)
        if incoming:
            print(f"\n  {symbols.arrow} Supported by ({len(incoming)}):")
            for edge, source_node in incoming:
                src_formatted = self._cli.format_id(source_node.id)
                src_summary = truncate(_get_summary(source_node), SUMMARY_LENGTH - 20)
                print(f"    {src_formatted} ({edge.relation}) {src_summary}")

        # Get outgoing edges (what this artifact points TO)
        outgoing = self.graph.get_outgoing(node.id)
        if outgoing:
            print(f"\n  {symbols.arrow} Informs ({len(outgoing)}):")
            for edge, target_node in outgoing:
                tgt_formatted = self._cli.format_id(target_node.id)
                tgt_summary = truncate(_get_summary(target_node), SUMMARY_LENGTH - 20)
                print(f"    {tgt_formatted} ({edge.relation}) {tgt_summary}")

        if not incoming and not outgoing:
            print(f"\n  No connections (orphan artifact)")
            print(f"  {symbols.arrow} Link it: babel link {alias_code}")

        # Succession hint
        from ..output import end_command
        end_command("list", {"from_id": alias_code, "has_connections": bool(incoming or outgoing)})

    def list_orphans(self, limit: int = DEFAULT_LIMIT, offset: int = 0, show_all: bool = False):
        """
        Show artifacts with no incoming connections.

        These artifacts are isolated — they can't inform 'why' queries
        and represent potential knowledge silos.

        Args:
            limit: Maximum items to show (default 10)
            offset: Number of items to skip (default 0)
            show_all: Show all items (ignore limit)
        """
        symbols = self.symbols

        orphans = self.graph.find_orphans()

        if not orphans:
            print(f"\n{symbols.check_pass} No orphan artifacts. All artifacts are connected.")
            return

        # Use Paginator for consistent pagination
        if show_all:
            paginator = Paginator(orphans, limit=len(orphans) or 1, offset=0)
        else:
            paginator = Paginator(orphans, limit=limit, offset=offset)

        print(f"\n{symbols.tension} {paginator.header('Orphan Artifacts')}")
        print("(No incoming connections — can't inform 'why' queries)")
        print()

        # Group displayed items by type for clarity
        by_type = {}
        for node in paginator.items():
            node_type = node.type
            if node_type not in by_type:
                by_type[node_type] = []
            by_type[node_type].append(node)

        for node_type, nodes in sorted(by_type.items()):
            print(f"  [{node_type}] ({len(nodes)})")
            for node in nodes:
                formatted_id = self._cli.format_id(node.id)
                summary = truncate(_get_summary(node), SUMMARY_LENGTH - 20)
                print(f"    {formatted_id} {summary}")

        # Navigation hints
        cmd_base = "babel list --orphans"
        print()

        if paginator.has_more():
            next_offset = paginator.offset + paginator.limit
            print(f"{symbols.arrow} Next: {cmd_base} --offset {next_offset}")

        if paginator.has_previous():
            prev_offset = max(0, paginator.offset - paginator.limit)
            print(f"{symbols.arrow} Prev: {cmd_base} --offset {prev_offset}")

        if paginator.is_truncated() and not show_all:
            print(f"{symbols.arrow} All: {cmd_base} --all")

        print(f"{symbols.arrow} Link: babel link <id>")

        # Succession hint
        from ..output import end_command
        end_command("list", {"orphans": True, "count": paginator.total})


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'list'


def register_parser(subparsers):
    """Register list command parser."""
    p = subparsers.add_parser('list', help='List and discover artifacts (graph-aware)')
    p.add_argument('type', nargs='?',
                   help='Artifact type to list (decisions, constraints, principles)')
    p.add_argument('--from', dest='from_id',
                   help='Show artifacts connected to this ID (graph traversal)')
    p.add_argument('--orphans', action='store_true',
                   help='Show artifacts with no connections')
    p.add_argument('--all', action='store_true', help='Show all items (no limit)')
    p.add_argument('--filter', dest='filter_pattern',
                   help='Filter by keyword (case-insensitive)')
    p.add_argument('--limit', type=int, default=10,
                   help='Maximum items to show (default: 10)')
    p.add_argument('--offset', type=int, default=0,
                   help='Skip first N items (default: 0)')
    return p


def handle(cli, args):
    """Handle list command dispatch."""
    if args.from_id:
        cli._list_cmd.list_from(args.from_id)
    elif args.orphans:
        cli._list_cmd.list_orphans(
            limit=args.limit,
            offset=args.offset,
            show_all=getattr(args, 'all', False)
        )
    elif args.type:
        cli._list_cmd.list_by_type(
            artifact_type=args.type,
            limit=args.limit,
            offset=args.offset,
            show_all=getattr(args, 'all', False),
            filter_pattern=args.filter_pattern
        )
    else:
        cli._list_cmd.list_overview()
