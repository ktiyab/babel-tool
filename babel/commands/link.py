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

from ..commands.base import BaseCommand
from ..core.graph import Edge
from ..core.commit_links import CommitLinkStore
from ..presentation.symbols import safe_print
from ..utils.pagination import Paginator, DEFAULT_LIMIT


class LinkCommand(BaseCommand):
    """
    Command for linking artifacts to purposes.

    Improves coherence by explicitly connecting artifacts to purposes.
    Unlinked artifacts show up in coherence check as needing connection.
    """

    def _get_short_id(self, node) -> str:
        """Get short display ID (event_id preferred, else node ID suffix)."""
        if node.event_id:
            return node.event_id[:8]
        if '_' in node.id:
            return node.id.split('_', 1)[1][:8]
        return node.id[:8]

    def list_unlinked(self, limit: int = DEFAULT_LIMIT, offset: int = 0, show_all: bool = False):
        """
        List all unlinked artifacts (orphans).

        Shows artifacts that have no incoming edges and can't inform 'why' queries.
        Displays ID + summary for each, enabling bulk linking workflow.

        Args:
            limit: Maximum items to show (default 10)
            offset: Number of items to skip (default 0)
            show_all: Show all items (ignore limit)
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
                short_id = self._get_short_id(node)
                summary = node.content.get('summary', str(node.content)[:50])[:60]
                safe_print(f"  [{short_id}] {summary}")
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
        safe_print(f"  [{self._get_short_id(purpose_node)}] \"{purpose_summary}\"")
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
                self.graph.add_edge(Edge(
                    source_id=purpose_node.id,
                    target_id=node.id,
                    relation="supports",
                    event_id=f"link_{node.id[:8]}"
                ))

                short_id = self._get_short_id(node)
                summary = node.content.get('summary', '')[:40]
                safe_print(f"  {symbols.check_pass} [{short_id}] {node.type}: {summary}")
                linked_count += 1
            except ValueError:
                # Would create cycle - skip this artifact
                skipped_count += 1

        print()
        print(f"Linked: {linked_count} artifact(s)")
        if skipped_count > 0:
            print(f"Skipped: {skipped_count} (purposes or already linked)")

        # Show new orphan count
        remaining = len(self.graph.find_orphans())
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
                        print(f"  [{p.id[:8]}] {summary}")
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

        # Create edge
        self.graph.add_edge(Edge(
            source_id=purpose_node.id,
            target_id=artifact_node.id,
            relation="supports",
            event_id=f"link_{artifact_node.id[:8]}"
        ))

        # Display confirmation
        artifact_summary = artifact_node.content.get('summary', '')[:50]
        purpose_summary = purpose_node.content.get('summary', purpose_node.content.get('purpose', ''))[:50]

        print(f"\nLinked: {artifact_node.type} [{artifact_node.id.split('_', 1)[-1][:8]}]")
        print(f"  \"{artifact_summary}\"")
        print(f"\n  {symbols.arrow} purpose [{purpose_node.id.split('_', 1)[-1][:8]}]")
        print(f"  \"{purpose_summary}\"")
        print(f"\n  Relation: supports")
        print(f"\nStatus: Now coherent with purpose.")

        # Succession hint (centralized)
        from ..output import end_command
        remaining = len(self.graph.find_orphans())
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
            print(f"Already linked: decision [{decision_node.event_id[:8] if decision_node.event_id else decision_node.id[:8]}] → commit [{short_sha}]")
            return

        # Create the link
        decision_short = decision_node.event_id[:8] if decision_node.event_id else decision_node.id[:8]
        link = commit_links.add(
            decision_id=decision_node.event_id or decision_node.id,
            commit_sha=full_sha,
            linked_by=linked_by
        )

        # Display confirmation
        decision_summary = decision_node.content.get('summary', '')[:50]

        print(f"\n{symbols.check_pass} Linked decision to commit:")
        print(f"\n  Decision [{decision_short}]:")
        safe_print(f"    \"{decision_summary}\"")
        print(f"\n  {symbols.arrow} Commit [{short_sha}]:")
        print(f"    \"{commit_info.message[:60]}\"")
        print(f"\n  Relation: implements")
        print(f"\n  Linked by: {linked_by}")

        # Show what this enables
        print(f"\nThis enables:")
        print(f"  babel why --commit {short_sha}  (see why this commit was made)")

        # Succession hint
        from ..output import end_command
        end_command("link", {"commit_linked": True, "commit_sha": short_sha})

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

            safe_print(f"  [{link.decision_id[:8]}] {decision_summary}")
            print(f"    {symbols.arrow} commit [{commit_short}] (by {link.linked_by})")
            print()

        # Navigation hints
        if paginator.has_more():
            print(f"\n{symbols.arrow} More: babel link --commits --offset {paginator.offset + paginator.limit}")

        print(f"\nTotal links: {paginator.total}")
