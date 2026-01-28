"""
GapsCommand — Shows implementation gaps between decisions and commits

Identifies:
- Decisions without linked commits (unimplemented intent)
- Recent commits without linked decisions (undocumented state changes)

Aligns with:
- P8: Evolution traceable (surfaces broken chains)
- P9: Coherence observable (makes gaps visible)
- P7: Reasoning travels (encourages linking)
"""

from typing import List, Dict, Set

from ..commands.base import BaseCommand
from ..core.commit_links import CommitLinkStore
from ..services.git import GitIntegration
from ..presentation.template import OutputTemplate
from ..presentation.formatters import format_timestamp
from ..utils.pagination import Paginator, DEFAULT_LIMIT


class GapsCommand(BaseCommand):
    """
    Command for identifying implementation gaps.

    Shows where the bridge between intent (Babel) and state (Git) is incomplete.
    """

    def gaps(self, show_commits: bool = False, show_decisions: bool = False,
             from_recent: int = 20, limit: int = DEFAULT_LIMIT, offset: int = 0):
        """
        Show implementation gaps between decisions and commits.

        Args:
            show_commits: Only show unlinked commits
            show_decisions: Only show unlinked decisions
            from_recent: Number of recent commits to check (default: 20)
            limit: Maximum items to show per section
            offset: Skip first N items
        """
        symbols = self.symbols

        # Get git integration
        git = GitIntegration(self.project_dir)

        # Get commit link store
        commit_links = CommitLinkStore(self.babel_dir)
        linked_decision_ids = commit_links.get_linked_decision_ids()
        linked_commit_shas = commit_links.get_linked_commit_shas()

        # Gather data
        unlinked_decisions = []
        unlinked_commits = []

        # Find unlinked decisions
        if not show_commits:  # Show decisions unless only commits requested
            unlinked_decisions = self._find_unlinked_decisions(linked_decision_ids)

        # Find unlinked commits
        if not show_decisions:  # Show commits unless only decisions requested
            if git.is_git_repo:
                unlinked_commits = self._find_unlinked_commits(git, linked_commit_shas, from_recent)

        # Summary header
        total_gaps = len(unlinked_decisions) + len(unlinked_commits)

        if total_gaps == 0:
            print(f"\n{symbols.check_pass} No gaps found!")
            print("All decisions are linked to commits.")
            return

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL GAPS", "Intent ↔ State Bridge")
        template.legend({
            symbols.tension: "gap (unlinked)",
            "[ID]": "decision/constraint/principle",
            "[sha]": "commit"
        })

        # Show unlinked decisions
        if unlinked_decisions and not show_commits:
            decisions_content = self._format_unlinked_decisions(unlinked_decisions, limit, offset)
            template.section("DECISIONS WITHOUT COMMITS", decisions_content)

        # Show unlinked commits
        if unlinked_commits and not show_decisions:
            commits_content = self._format_unlinked_commits(unlinked_commits, limit, offset)
            template.section("COMMITS WITHOUT DECISIONS", commits_content)

        # Action hints section
        action_lines = [
            "babel link <decision_id> --to-commit <sha>",
            "babel suggest-links  (AI-assisted suggestions)"
        ]
        template.section("TO LINK", "\n".join(action_lines))

        # Footer summary
        summary_parts = []
        if unlinked_decisions:
            summary_parts.append(f"{len(unlinked_decisions)} decision(s) without commits")
        if unlinked_commits:
            summary_parts.append(f"{len(unlinked_commits)} commit(s) without decisions")
        template.footer(" | ".join(summary_parts))

        # Render with succession hints
        output = template.render(
            command="gaps",
            context={
                "unlinked_decisions": len(unlinked_decisions),
                "unlinked_commits": len(unlinked_commits)
            }
        )
        print(output)

    def _find_unlinked_decisions(self, linked_ids: Set[str]) -> List[Dict]:
        """Find decisions that aren't linked to any commit."""
        unlinked = []

        for node_type in ['decision', 'constraint', 'principle']:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                node_id = node.event_id or node.id
                alias = self._cli.codec.encode(node.id)

                # Check if linked (match full ID or prefix)
                is_linked = any(
                    node_id.startswith(linked_id) or linked_id.startswith(node_id)
                    for linked_id in linked_ids
                )

                if not is_linked:
                    # Check deprecation status
                    dep_info = self._cli._is_deprecated(node.id)

                    # Skip deprecated decisions (they don't need implementation)
                    if dep_info:
                        continue

                    summary = node.content.get('summary', str(node.content)[:60])

                    unlinked.append({
                        'id': node_id,
                        'short_id': alias,
                        'type': node_type,
                        'summary': summary,
                        'node': node,
                        'created_at': node.created_at  # P12: Temporal attribution
                    })

        return unlinked

    def _find_unlinked_commits(self, git: GitIntegration, linked_shas: Set[str],
                               from_recent: int) -> List[Dict]:
        """Find recent commits that aren't linked to any decision."""
        unlinked = []

        # Get recent commits with date (P12: Temporal attribution)
        # Format: sha|date|message
        output = git._run_git([
            "log", f"-{from_recent}", "--format=%H|%aI|%s", "--no-merges"
        ])

        if not output:
            return []

        for line in output.strip().split('\n'):
            if '|' not in line:
                continue
            parts = line.split('|', 2)
            if len(parts) < 3:
                continue
            sha, date, message = parts

            # Check if linked
            is_linked = any(
                sha.startswith(linked_sha) or linked_sha.startswith(sha)
                for linked_sha in linked_shas
            )

            if not is_linked:
                # Skip merge commits and trivial commits
                if message.lower().startswith(('merge', 'bump version', 'update changelog')):
                    continue

                unlinked.append({
                    'sha': sha,
                    'short_sha': sha[:8],
                    'message': message,
                    'date': date  # P12: Temporal attribution
                })

        return unlinked

    def _format_unlinked_decisions(self, decisions: List[Dict], limit: int, offset: int) -> str:
        """Format unlinked decisions as string."""
        symbols = self.symbols

        paginator = Paginator(decisions, limit=limit, offset=offset)

        lines = [
            f"({paginator.total} total)",
            "(Intent captured but not implemented)",
            ""
        ]

        # Group by type
        by_type: Dict[str, List[Dict]] = {}
        for d in paginator.items():
            if d['type'] not in by_type:
                by_type[d['type']] = []
            by_type[d['type']].append(d)

        for dtype, items in sorted(by_type.items()):
            lines.append(f"  [{dtype}]")
            for item in items:
                # P12: Time always shown
                time_str = f" ({format_timestamp(item.get('created_at', ''))})"
                lines.append(f"    [{item['short_id']}] {item['summary'][:50]}{time_str}")
            lines.append("")

        # Navigation
        if paginator.has_more():
            lines.append(f"  {symbols.arrow} More: babel gaps --decisions --offset {paginator.offset + paginator.limit}")

        return "\n".join(lines)

    def _format_unlinked_commits(self, commits: List[Dict], limit: int, offset: int) -> str:
        """Format unlinked commits as string."""
        symbols = self.symbols

        paginator = Paginator(commits, limit=limit, offset=offset)

        lines = [
            f"({paginator.total} total)",
            "(State changed but intent not documented)",
            ""
        ]

        for commit in paginator.items():
            # P12: Time always shown
            time_str = f" ({format_timestamp(commit.get('date', ''))})"
            lines.append(f"  [{commit['short_sha']}] {commit['message'][:50]}{time_str}")

        lines.append("")

        # Navigation
        if paginator.has_more():
            lines.append(f"  {symbols.arrow} More: babel gaps --commits --offset {paginator.offset + paginator.limit}")

        return "\n".join(lines)


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'gaps'


def register_parser(subparsers):
    """Register gaps command parser."""
    p = subparsers.add_parser('gaps',
                              help='Show implementation gaps between decisions and commits')
    p.add_argument('--commits', action='store_true',
                   help='Only show unlinked commits')
    p.add_argument('--decisions', action='store_true',
                   help='Only show unlinked decisions')
    p.add_argument('--from-recent', dest='from_recent', type=int, default=20,
                   help='Number of recent commits to check (default: 20)')
    p.add_argument('--limit', type=int, default=10,
                   help='Maximum items per section (default: 10)')
    p.add_argument('--offset', type=int, default=0,
                   help='Skip first N items (default: 0)')
    return p


def handle(cli, args):
    """Handle gaps command dispatch."""
    cli._gaps_cmd.gaps(
        show_commits=args.commits,
        show_decisions=args.decisions,
        from_recent=args.from_recent,
        limit=args.limit,
        offset=args.offset
    )
