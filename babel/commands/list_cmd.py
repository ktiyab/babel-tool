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
from ..presentation.formatters import get_node_summary, generate_summary, format_timestamp
from ..presentation.template import OutputTemplate
from ..utils.pagination import Paginator, DEFAULT_LIMIT


# Artifact types that can be listed
ARTIFACT_TYPES = ['decision', 'constraint', 'principle', 'purpose', 'tension']

# Artifact type → actionable commands mapping (Legend Pattern)
# Shown once per listing, not repeated per-item
ARTIFACT_ACTIONS = {
    'decision': ['link', 'why', 'endorse', 'evidence-decision', 'deprecate'],
    'constraint': ['link', 'why', 'deprecate'],
    'principle': ['link', 'why'],
    'purpose': ['link', 'why'],
    'tension': ['why', 'resolve', 'evidence'],
}


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

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL LIST", "Artifact Discovery")
        template.legend({
            symbols.purpose: "purpose",
            symbols.arrow: "drill-down hint"
        })

        # Count by type
        type_counts = {}
        for artifact_type in ARTIFACT_TYPES:
            nodes = self.graph.get_nodes_by_type(artifact_type)
            if nodes:
                type_counts[artifact_type] = len(nodes)

        # Build type counts section
        lines = [f"Total: {stats['nodes']} artifacts", ""]
        for artifact_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {artifact_type}s: {count:>4}  {symbols.arrow} babel list {artifact_type}s")

        # Show orphan count (O(1) lookup)
        orphan_count = self.graph.count_orphans()
        if orphan_count > 0:
            lines.append(f"\n  orphans: {orphan_count:>4}  {symbols.arrow} babel list --orphans")

        template.section("BY TYPE", "\n".join(lines))

        # Navigation hint
        template.section("TRAVERSAL", f"Graph traversal: babel list --from <id>")

        # Footer summary
        template.footer(f"{stats['nodes']} artifacts | {orphan_count} orphans")

        # Render with succession hints
        output = template.render(
            command="list",
            context={"has_orphans": orphan_count > 0}
        )
        print(output)

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
            nodes = [n for n in nodes if pattern_lower in get_node_summary(n).lower()]

            if not nodes:
                print(f"\nNo {artifact_type}s matching '{filter_pattern}'.")
                return

        # Use Paginator for consistent pagination
        if show_all:
            paginator = Paginator(nodes, limit=len(nodes) or 1, offset=0)
        else:
            paginator = Paginator(nodes, limit=limit, offset=offset)

        # Build template
        title = f"{artifact_type.capitalize()}s"
        if filter_pattern:
            title = f"{title} matching '{filter_pattern}'"

        template = OutputTemplate(symbols=symbols)
        template.header("BABEL LIST", title)

        # Action legend (Legend Pattern: state once, not per-item)
        actions = ARTIFACT_ACTIONS.get(artifact_type, ['link', 'why'])
        action_legend = {f"[ID]": f"use with: {', '.join(actions)}"}
        template.legend(action_legend)

        # Build artifact list
        lines = [paginator.header(title), ""]
        for node in paginator.items():
            formatted_id = self._cli.format_id(node.id)
            summary = generate_summary(get_node_summary(node))
            time_str = format_timestamp(node.created_at)
            lines.append(f"  {formatted_id} {time_str} {summary}")

        template.section("ARTIFACTS", "\n".join(lines))

        # Navigation hints section
        cmd_base = f"babel list {artifact_type}s"
        if filter_pattern:
            cmd_base = f"{cmd_base} --filter \"{filter_pattern}\""

        nav_lines = []
        if paginator.has_more():
            next_offset = paginator.offset + paginator.limit
            nav_lines.append(f"{symbols.arrow} Next: {cmd_base} --offset {next_offset}")

        if paginator.has_previous():
            prev_offset = max(0, paginator.offset - paginator.limit)
            nav_lines.append(f"{symbols.arrow} Prev: {cmd_base} --offset {prev_offset}")

        if paginator.is_truncated() and not show_all:
            nav_lines.append(f"{symbols.arrow} All: {cmd_base} --all")

        if nav_lines:
            template.section("NAVIGATION", "\n".join(nav_lines))

        # Footer summary
        template.footer(f"{paginator.total} {artifact_type}s | showing {len(list(paginator.items()))} items")

        # Render with succession hints
        output = template.render(
            command="list",
            context={"type": artifact_type, "truncated": paginator.is_truncated()}
        )
        print(output)

    def list_from(self, artifact_id: str, depth: int = 1):
        """
        Show artifacts connected to a given artifact (graph traversal).

        Args:
            artifact_id: ID (alias code or prefix) of the starting artifact
            depth: Traversal depth (default 1 = immediate connections)
        """
        symbols = self.symbols

        # Resolve alias code to raw ID (counterpart to format_id for output)
        artifact_id = self._cli.resolve_id(artifact_id)

        # Resolve ID using IDResolver (supports short codes via codec)
        result = self.resolver.resolve(artifact_id, codec=self.codec)
        if not result or not result.node:
            print(f"\nArtifact not found: {artifact_id}")
            print("Use full ID or unique prefix.")
            return

        node = result.node

        # Build template
        formatted_id = self._cli.format_id(node.id)
        alias_code = self._cli.codec.encode(node.id)  # For actionable hints
        summary = generate_summary(get_node_summary(node))
        time_str = format_timestamp(node.created_at)

        template = OutputTemplate(symbols=symbols)
        template.header("BABEL LIST", f"Graph Traversal from {formatted_id}")
        template.legend({
            symbols.arrow: "connection direction"
        })

        # Origin section - P12: Time always shown
        origin_lines = [
            f"{formatted_id} {time_str} {summary}",
            f"  Type: {node.type}"
        ]
        template.section("ORIGIN", "\n".join(origin_lines))

        # Get incoming edges (what points TO this artifact)
        incoming = self.graph.get_incoming(node.id)
        if incoming:
            inc_lines = []
            for edge, source_node in incoming:
                src_formatted = self._cli.format_id(source_node.id)
                src_summary = generate_summary(get_node_summary(source_node))
                src_time = format_timestamp(source_node.created_at)
                inc_lines.append(f"  {src_formatted} {src_time} ({edge.relation}) {src_summary}")
            template.section(f"SUPPORTED BY ({len(incoming)})", "\n".join(inc_lines))

        # Get outgoing edges (what this artifact points TO)
        outgoing = self.graph.get_outgoing(node.id)
        if outgoing:
            out_lines = []
            for edge, target_node in outgoing:
                tgt_formatted = self._cli.format_id(target_node.id)
                tgt_summary = generate_summary(get_node_summary(target_node))
                tgt_time = format_timestamp(target_node.created_at)
                out_lines.append(f"  {tgt_formatted} {tgt_time} ({edge.relation}) {tgt_summary}")
            template.section(f"INFORMS ({len(outgoing)})", "\n".join(out_lines))

        # Orphan case
        if not incoming and not outgoing:
            template.section("STATUS", f"No connections (orphan artifact)\n  {symbols.arrow} Link it: babel link {alias_code}")

        # Footer summary
        total_connections = len(incoming) + len(outgoing)
        template.footer(f"{total_connections} connections | {len(incoming)} incoming | {len(outgoing)} outgoing")

        # Render with succession hints
        output = template.render(
            command="list",
            context={"from_id": alias_code, "has_connections": bool(incoming or outgoing)}
        )
        print(output)

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

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL LIST", "Orphan Artifacts")
        template.legend({
            symbols.tension: "orphan (no incoming connections)"
        })
        template.scope("Can't inform 'why' queries — consider linking")

        # Group displayed items by type for clarity
        by_type = {}
        for node in paginator.items():
            node_type = node.type
            if node_type not in by_type:
                by_type[node_type] = []
            by_type[node_type].append(node)

        # Build grouped content
        lines = [paginator.header("Orphan Artifacts"), ""]
        for node_type, nodes in sorted(by_type.items()):
            lines.append(f"  [{node_type}] ({len(nodes)})")
            for node in nodes:
                formatted_id = self._cli.format_id(node.id)
                summary = generate_summary(get_node_summary(node))
                time_str = format_timestamp(node.created_at)
                lines.append(f"    {formatted_id} {time_str} {summary}")

        template.section("ORPHANS", "\n".join(lines))

        # Navigation hints section
        cmd_base = "babel list --orphans"
        nav_lines = []

        if paginator.has_more():
            next_offset = paginator.offset + paginator.limit
            nav_lines.append(f"{symbols.arrow} Next: {cmd_base} --offset {next_offset}")

        if paginator.has_previous():
            prev_offset = max(0, paginator.offset - paginator.limit)
            nav_lines.append(f"{symbols.arrow} Prev: {cmd_base} --offset {prev_offset}")

        if paginator.is_truncated() and not show_all:
            nav_lines.append(f"{symbols.arrow} All: {cmd_base} --all")

        nav_lines.append(f"{symbols.arrow} Link: babel link <id>")

        template.section("ACTIONS", "\n".join(nav_lines))

        # Footer summary
        template.footer(f"{paginator.total} orphans | showing {len(list(paginator.items()))} items")

        # Render with succession hints
        output = template.render(
            command="list",
            context={"orphans": True, "count": paginator.total}
        )
        print(output)


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
