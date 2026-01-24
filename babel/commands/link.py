"""
LinkCommand — Artifact-to-purpose and artifact-to-commit linking

Handles coherence improvement through explicit linking:
- Connecting artifacts to purposes (supports edge)
- Connecting decisions to commits (implements edge via CommitLinkStore)
- Creating 'supports' edges in the graph
- Verifying existing links to avoid duplicates
- Listing unlinked artifacts (--list)
- Bulk linking all unlinked to active purpose (--all)
- Linking decisions to git commits (--to-commit)
"""

import json

from ..commands.base import BaseCommand
from ..core.graph import Edge
from ..core.commit_links import CommitLinkStore
from ..core.symbols import CodeSymbolStore
from ..presentation.symbols import safe_print
from ..utils.pagination import Paginator, DEFAULT_LIMIT


class LinkCommand(BaseCommand):
    """
    Command for linking artifacts to purposes.

    Improves coherence by explicitly connecting artifacts to purposes.
    Unlinked artifacts show up in coherence check as needing connection.
    """

    def _format_node_id(self, node) -> str:
        """Format node ID for display using codec alias (includes brackets)."""
        return self._cli.format_id(node.id)

    def list_unlinked(self, limit: int = DEFAULT_LIMIT, offset: int = 0, show_all: bool = False, full: bool = False):
        """
        List all unlinked artifacts (orphans).

        Shows artifacts that have no incoming edges and can't inform 'why' queries.
        Displays ID + summary for each, enabling bulk linking workflow.

        Args:
            limit: Maximum items to show (default 10)
            offset: Number of items to skip (default 0)
            show_all: Show all items (ignore limit)
            full: Show complete artifact content (default False, truncates to 60 chars)
        """
        symbols = self.symbols
        orphans = self.graph.find_orphans()

        if not orphans:
            print("No unlinked artifacts found.")
            print("\nAll artifacts are connected to purposes.")
            return

        # Use Paginator for consistent pagination
        if show_all:
            paginator = Paginator(orphans, limit=len(orphans) or 1, offset=0)
        else:
            paginator = Paginator(orphans, limit=limit, offset=offset)

        print(f"\n{paginator.header('Unlinked artifacts')}")
        print("(These can't inform 'babel why' queries)\n")

        # Group displayed items by type for clarity
        by_type = {}
        for node in paginator.items():
            node_type = node.type
            if node_type not in by_type:
                by_type[node_type] = []
            by_type[node_type].append(node)

        for node_type, nodes in sorted(by_type.items()):
            print(f"[{node_type}] ({len(nodes)})")
            for node in nodes:
                formatted_id = self._format_node_id(node)
                if full:
                    # Show complete artifact content
                    safe_print(f"  {formatted_id}")
                    content_str = json.dumps(node.content, indent=4, default=str)
                    for line in content_str.split('\n'):
                        safe_print(f"    {line}")
                else:
                    # Default: truncated summary
                    summary = node.content.get('summary', str(node.content)[:50])[:60]
                    safe_print(f"  {formatted_id} {summary}")
            print()

        # Navigation hints
        cmd_base = "babel link --list"

        if paginator.has_more():
            next_offset = paginator.offset + paginator.limit
            print(f"{symbols.arrow} Next: {cmd_base} --offset {next_offset}")

        if paginator.has_previous():
            prev_offset = max(0, paginator.offset - paginator.limit)
            print(f"{symbols.arrow} Prev: {cmd_base} --offset {prev_offset}")

        if paginator.is_truncated() and not show_all:
            print(f"{symbols.arrow} All: {cmd_base} --all")

        print()
        print("Link individually: babel link <id>")
        print("Link all at once:  babel link --all")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("link", {"has_unlinked": True, "total": paginator.total})

    def link_all(self):
        """
        Link all unlinked artifacts to the active purpose.

        Bulk operation that connects all orphan artifacts to the most recent purpose.
        Useful for cleaning up accumulated unlinked artifacts.
        """
        symbols = self.symbols

        # Get active purpose
        purpose_node = self._cli._get_active_purpose()
        if not purpose_node:
            print("No active purpose found.")
            print("Create one with: babel init \"purpose\"")
            return

        # Get all orphans
        orphans = self.graph.find_orphans()

        if not orphans:
            print("No unlinked artifacts to link.")
            return

        purpose_summary = purpose_node.content.get('summary', purpose_node.content.get('purpose', ''))[:50]
        print(f"\nLinking {len(orphans)} artifact(s) to purpose:")
        safe_print(f"  {self._format_node_id(purpose_node)} \"{purpose_summary}\"")
        print()

        linked_count = 0
        skipped_count = 0

        for node in orphans:
            # Skip purposes - they are root nodes, not orphans to link
            if node.type == 'purpose':
                skipped_count += 1
                continue

            # Check if already linked (shouldn't happen, but defensive)
            incoming = self.graph.get_incoming(node.id)
            already_linked = any(
                edge.source_id == purpose_node.id and edge.relation == "supports"
                for edge, _ in incoming
            )

            if already_linked:
                skipped_count += 1
                continue

            # Create edge (with cycle detection)
            try:
                # Event ID uses hex (internal identifier)
                event_id_suffix = node.id.split('_', 1)[-1][:8] if '_' in node.id else node.id[:8]
                self.graph.add_edge(Edge(
                    source_id=purpose_node.id,
                    target_id=node.id,
                    relation="supports",
                    event_id=f"link_{event_id_suffix}"
                ))

                formatted_id = self._format_node_id(node)
                summary = node.content.get('summary', '')[:40]
                safe_print(f"  {symbols.check_pass} {formatted_id} {node.type}: {summary}")
                linked_count += 1
            except ValueError:
                # Would create cycle - skip this artifact
                skipped_count += 1

        print()
        print(f"Linked: {linked_count} artifact(s)")
        if skipped_count > 0:
            print(f"Skipped: {skipped_count} (purposes or already linked)")

        # Show new orphan count (O(1) lookup)
        remaining = self.graph.count_orphans()
        if remaining > 0:
            print(f"\nRemaining unlinked: {remaining}")
        else:
            print(f"\n{symbols.check_pass} All artifacts now linked to purpose.")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("link", {"has_unlinked": remaining > 0})

    def link(self, artifact_id: str, purpose_id: str = None):
        """
        Link artifact to purpose (creates 'supports' edge).

        Improves coherence by explicitly connecting artifacts to purposes.
        Unlinked artifacts show up in coherence check as needing connection.

        Args:
            artifact_id: ID, prefix, or keyword to find artifact
            purpose_id: Optional purpose ID (default: active purpose)
        """
        symbols = self.symbols

        # Resolve artifact using fuzzy matching
        artifact_node = self._cli._resolve_node(artifact_id, type_label="artifact")

        if not artifact_node:
            return

        # Find target purpose
        if purpose_id:
            purpose_node = self._cli._resolve_node(purpose_id, artifact_type='purpose', type_label="purpose")
            if not purpose_node:
                return
        else:
            purpose_node = self._cli._get_active_purpose()
            if not purpose_node:
                print("No active purpose found.")
                print("Specify target: babel link <artifact> <purpose>")

                # Show available purposes
                purposes = self.graph.get_nodes_by_type('purpose')
                if purposes:
                    print("\nAvailable purposes:")
                    for p in purposes[-3:]:
                        summary = p.content.get('summary', p.content.get('purpose', ''))[:50]
                        print(f"  {self._cli.format_id(p.id)} {summary}")
                return

        # Check if already linked
        incoming = self.graph.get_incoming(artifact_node.id)
        already_linked = any(
            edge.source_id == purpose_node.id and edge.relation == "supports"
            for edge, _ in incoming
        )

        if already_linked:
            print(f"Already linked to this purpose.")
            return

        # Create edge (event ID uses hex for internal identifier)
        event_id_suffix = artifact_node.id.split('_', 1)[-1][:8] if '_' in artifact_node.id else artifact_node.id[:8]
        self.graph.add_edge(Edge(
            source_id=purpose_node.id,
            target_id=artifact_node.id,
            relation="supports",
            event_id=f"link_{event_id_suffix}"
        ))

        # Display confirmation
        artifact_summary = artifact_node.content.get('summary', '')[:50]
        purpose_summary = purpose_node.content.get('summary', purpose_node.content.get('purpose', ''))[:50]

        print(f"\nLinked: {artifact_node.type} {self._cli.format_id(artifact_node.id)}")
        print(f"  \"{artifact_summary}\"")
        print(f"\n  {symbols.arrow} purpose {self._cli.format_id(purpose_node.id)}")
        print(f"  \"{purpose_summary}\"")
        print(f"\n  Relation: supports")
        print(f"\nStatus: Now coherent with purpose.")

        # Succession hint (centralized)
        from ..output import end_command
        remaining = self.graph.count_orphans()  # O(1) lookup
        end_command("link", {"has_unlinked": remaining > 0})

    def link_to_commit(self, decision_id: str, commit_sha: str, linked_by: str = "user"):
        """
        Link a decision to a git commit (creates 'implements' relationship).

        This bridges intent (Babel decisions) with state (Git commits).
        Enables 'babel why --commit <sha>' queries.

        Args:
            decision_id: ID, prefix, or keyword to find decision
            commit_sha: Git commit SHA (full or abbreviated)
            linked_by: Who created the link (user, claude, auto)
        """
        symbols = self.symbols

        # Resolve decision using fuzzy matching
        decision_node = self._cli._resolve_node(decision_id, type_label="decision")

        if not decision_node:
            return

        # Validate commit exists using git service
        from ..services.git import GitIntegration
        git = GitIntegration()

        if not git.is_git_repo:
            print("Not a git repository.")
            return

        # Normalize commit SHA (get full hash if abbreviated)
        commit_info = git.get_commit(commit_sha, include_diff=False)
        if not commit_info:
            print(f"Commit not found: {commit_sha}")
            print("Use a valid commit SHA or reference (HEAD, branch name, etc.)")
            return

        full_sha = commit_info.hash
        short_sha = full_sha[:8]

        # Get or create CommitLinkStore
        commit_links = CommitLinkStore(self.babel_dir)

        # Check if already linked
        existing = commit_links.get_link(decision_node.event_id or decision_node.id, full_sha)
        if existing:
            print(f"Already linked: decision {self._cli.format_id(decision_node.id)} → commit [{short_sha}]")
            return

        # Create the link
        decision_alias = self._cli.codec.encode(decision_node.id)
        link = commit_links.add(
            decision_id=decision_node.event_id or decision_node.id,
            commit_sha=full_sha,
            linked_by=linked_by
        )

        # Display confirmation
        decision_summary = decision_node.content.get('summary', '')[:50]

        print(f"\n{symbols.check_pass} Linked decision to commit:")
        print(f"\n  Decision {self._cli.format_id(decision_node.id)}:")
        safe_print(f"    \"{decision_summary}\"")
        print(f"\n  {symbols.arrow} Commit [{short_sha}]:")
        print(f"    \"{commit_info.message[:60]}\"")
        print(f"\n  Relation: implements")
        print(f"\n  Linked by: {linked_by}")

        # Show what this enables
        print(f"\nThis enables:")
        print(f"  babel why --commit {short_sha}  (see why this commit was made)")

        # === RETURN PATH: Link decision to touched symbols ===
        # This completes the semantic bridge: WHY/HOW -> WHAT
        touched_symbols = self._link_decision_to_touched_symbols(
            decision_node, git, full_sha, symbols
        )

        # Succession hint
        from ..output import end_command
        end_command("link", {
            "commit_linked": True,
            "commit_sha": short_sha,
            "symbols_linked": len(touched_symbols)
        })

    def _link_decision_to_touched_symbols(self, decision_node, git, commit_sha: str, symbols) -> list:
        """
        Link decision to code symbols touched by the commit.

        This creates the return path in the semantic bridge:
        Decision (WHY) --implemented_in--> Symbol (WHAT)

        Args:
            decision_node: The decision node being linked
            git: GitIntegration instance
            commit_sha: Full commit SHA
            symbols: Output symbols for display

        Returns:
            List of linked symbol names
        """
        linked_symbols = []

        # Get structural changes from commit
        changes = git.get_structural_changes(commit_sha)
        if not changes:
            return linked_symbols

        # Collect all touched files (added + modified)
        touched_files = changes.added + changes.modified

        if not touched_files:
            return linked_symbols

        # Get symbol store (requires events and graph for full functionality)
        symbol_store = CodeSymbolStore(
            self.babel_dir,
            self.events,
            self.graph,
            project_dir=self.babel_dir.parent
        )

        # Find symbols in touched files
        symbols_to_link = []
        for file_path in touched_files:
            file_symbols = symbol_store.get_symbols_in_file(file_path)
            symbols_to_link.extend(file_symbols)

        if not symbols_to_link:
            return linked_symbols

        # Create edges from decision to symbols
        print(f"\n{symbols.arrow} Symbols touched by this commit:")

        for sym in symbols_to_link:
            # Find the symbol node in graph
            # Symbol nodes are created with id pattern: code_symbol_{event_id}
            symbol_node = None
            symbol_nodes = self.graph.get_nodes_by_type('code_symbol')
            for node in symbol_nodes:
                if (node.content.get('qualified_name') == sym.qualified_name or
                    (node.content.get('name') == sym.name and
                     node.content.get('file_path') == sym.file_path)):
                    symbol_node = node
                    break

            if not symbol_node:
                # Symbol not in graph (not indexed), skip
                continue

            # Check if edge already exists
            existing_edges = self.graph.get_outgoing(decision_node.id)
            already_linked = any(
                edge.target_id == symbol_node.id and edge.relation == "implemented_in"
                for edge, _ in existing_edges
            )

            if already_linked:
                continue

            # Create edge: decision --implemented_in--> symbol
            try:
                self.graph.add_edge(Edge(
                    source_id=decision_node.id,
                    target_id=symbol_node.id,
                    relation="implemented_in",
                    event_id=f"impl_{decision_node.id[:8]}_{symbol_node.id[:8]}"
                ))

                # Display
                symbol_type = sym.symbol_type[0].upper()  # C=class, F=function, M=method
                safe_print(f"  [{symbol_type}] {sym.qualified_name}")
                linked_symbols.append(sym.qualified_name)

            except ValueError:
                # Would create cycle - skip
                pass

        if linked_symbols:
            print(f"\n{symbols.check_pass} Linked decision to {len(linked_symbols)} symbol(s)")

        return linked_symbols

    def list_commit_links(self, limit: int = 10, offset: int = 0):
        """
        List all decision-to-commit links.

        Shows the bridge between intent (decisions) and state (commits).
        """
        symbols = self.symbols
        commit_links = CommitLinkStore(self.babel_dir)
        all_links = commit_links.all_links()

        if not all_links:
            print("No decision-to-commit links found.")
            print("\nCreate links with: babel link <decision_id> --to-commit <sha>")
            return

        # Use Paginator for consistent pagination
        paginator = Paginator(all_links, limit=limit, offset=offset)

        print(f"\n{paginator.header('Decision → Commit Links')}")
        print("(Bridges intent with state)\n")

        for link in paginator.items():
            # Try to get decision summary from graph
            decision_node = self.graph.get_node(f"decision_{link.decision_id}")
            if not decision_node:
                # Try direct lookup
                for node_type in ['decision', 'proposal']:
                    nodes = self.graph.get_nodes_by_type(node_type)
                    for n in nodes:
                        if n.event_id and n.event_id.startswith(link.decision_id):
                            decision_node = n
                            break

            decision_summary = decision_node.content.get('summary', '')[:40] if decision_node else "(decision)"
            commit_short = link.commit_sha[:8]

            safe_print(f"  {self._cli.format_id(link.decision_id)} {decision_summary}")
            print(f"    {symbols.arrow} commit [{commit_short}] (by {link.linked_by})")
            print()

        # Navigation hints
        if paginator.has_more():
            print(f"\n{symbols.arrow} More: babel link --commits --offset {paginator.offset + paginator.limit}")

        print(f"\nTotal links: {paginator.total}")


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'link'


def register_parser(subparsers):
    """Register link command parser."""
    p = subparsers.add_parser('link', help='Link artifact to purpose (improves coherence)')
    p.add_argument('artifact_id', nargs='?', help='Artifact ID (or prefix) to link')
    p.add_argument('purpose_id', nargs='?', help='Purpose ID (default: active purpose)')
    p.add_argument('--list', action='store_true', help='List unlinked artifacts')
    p.add_argument('--full', action='store_true', help='Show complete artifact content (with --list)')
    p.add_argument('--all', action='store_true', help='Link all unlinked to active purpose')
    p.add_argument('--limit', type=int, default=10,
                   help='Maximum items for --list (default: 10)')
    p.add_argument('--offset', type=int, default=0,
                   help='Skip first N items for --list (default: 0)')
    p.add_argument('--to-commit', dest='to_commit',
                   help='Link decision to a git commit (P8: bridges intent with state)')
    p.add_argument('--commits', action='store_true',
                   help='List all decision-to-commit links')
    return p


def handle(cli, args):
    """Handle link command dispatch."""
    if args.commits:
        cli._link_cmd.list_commit_links(
            limit=args.limit,
            offset=args.offset
        )
    elif args.to_commit:
        cli._link_cmd.link_to_commit(args.artifact_id, args.to_commit)
    elif args.list:
        cli._link_cmd.list_unlinked(limit=args.limit, offset=args.offset, full=args.full)
    elif args.all:
        cli._link_cmd.link_all()
    elif args.artifact_id:
        cli._link_cmd.link(args.artifact_id, args.purpose_id)
    else:
        # No args - show usage
        print("Usage:")
        print("  babel link <artifact_id>              Link artifact to purpose")
        print("  babel link <artifact_id> <purpose_id> Link to specific purpose")
        print("  babel link --list                     List unlinked artifacts")
        print("  babel link --all                      Link all unlinked")
        print("  babel link --to-commit <sha>          Link decision to commit")
        print("  babel link --commits                  List decision-commit links")
