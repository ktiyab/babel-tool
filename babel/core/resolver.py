"""
ID Resolver — Universal fuzzy ID resolution for all commands

Enables users to reference artifacts by:
- Full ID (exact match)
- ID prefix (4+ characters)
- Keywords in summary (case-insensitive)

Provides clear feedback on ambiguous or missing matches.
"""

from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .core.graph import GraphStore, Node


class ResolveStatus(Enum):
    """Resolution outcome."""
    FOUND = "found"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


@dataclass
class ResolveResult:
    """Result of ID resolution."""
    status: ResolveStatus
    node: Optional['Node'] = None
    candidates: List['Node'] = None
    query: str = ""

    def __post_init__(self):
        if self.candidates is None:
            self.candidates = []


class IDResolver:
    """
    Universal ID resolution for artifact references.

    Resolution strategies (in order):
    1. Exact match (full ID)
    2. Prefix match (4+ chars)
    3. Keyword match (search summaries)
    """

    def __init__(self, graph: 'GraphStore'):
        self.graph = graph

    def resolve(
        self,
        query: str,
        artifact_type: str = None,
        min_prefix_length: int = 4
    ) -> ResolveResult:
        """
        Resolve a user-provided ID or keyword to a node.

        Args:
            query: User input (ID, prefix, or keyword)
            artifact_type: Optional filter by type (decision, constraint, etc.)
            min_prefix_length: Minimum chars for prefix matching

        Returns:
            ResolveResult with status and node/candidates
        """
        query = query.strip()

        # Strategy 1: Exact match
        node = self.graph.get_node(query)
        if node:
            if artifact_type is None or node.type == artifact_type:
                return ResolveResult(
                    status=ResolveStatus.FOUND,
                    node=node,
                    query=query
                )

        # Get candidate nodes (filtered by type if specified)
        candidates = self._get_candidates(artifact_type)

        # Strategy 2: Prefix match (on node ID or event ID portion)
        if len(query) >= min_prefix_length:
            query_lower = query.lower()
            prefix_matches = [
                n for n in candidates
                if n.id.startswith(query) or n.id.startswith(query_lower)
                or (n.event_id and n.event_id.startswith(query))
                or (n.event_id and n.event_id.startswith(query_lower))
                # Also check if query matches after the type prefix (e.g., decision_)
                or ('_' in n.id and n.id.split('_', 1)[1].startswith(query))
                or ('_' in n.id and n.id.split('_', 1)[1].startswith(query_lower))
            ]

            if len(prefix_matches) == 1:
                return ResolveResult(
                    status=ResolveStatus.FOUND,
                    node=prefix_matches[0],
                    query=query
                )
            elif len(prefix_matches) > 1:
                return ResolveResult(
                    status=ResolveStatus.AMBIGUOUS,
                    candidates=prefix_matches,
                    query=query
                )

        # Strategy 3: Keyword match in summaries
        keyword_matches = self._search_by_keyword(candidates, query)

        if len(keyword_matches) == 1:
            return ResolveResult(
                status=ResolveStatus.FOUND,
                node=keyword_matches[0],
                query=query
            )
        elif len(keyword_matches) > 1:
            return ResolveResult(
                status=ResolveStatus.AMBIGUOUS,
                candidates=keyword_matches[:10],  # Limit to 10
                query=query
            )

        # Not found - return recent candidates for suggestions
        return ResolveResult(
            status=ResolveStatus.NOT_FOUND,
            candidates=candidates[:5],  # Show 5 suggestions
            query=query
        )

    def _get_candidates(self, artifact_type: str = None) -> List['Node']:
        """Get candidate nodes, optionally filtered by type."""
        if artifact_type:
            return self.graph.get_nodes_by_type(artifact_type)

        # Get all decision-like types
        candidates = []
        for node_type in ['decision', 'constraint', 'principle', 'purpose', 'tension']:
            candidates.extend(self.graph.get_nodes_by_type(node_type))

        return candidates

    def _search_by_keyword(
        self,
        candidates: List['Node'],
        keyword: str
    ) -> List['Node']:
        """Search candidates by keyword in summary."""
        keyword_lower = keyword.lower()
        matches = []

        for node in candidates:
            summary = node.content.get('summary', '')
            if keyword_lower in summary.lower():
                matches.append(node)

        return matches


def format_resolve_prompt(result: ResolveResult, artifact_type: str = "artifact") -> str:
    """
    Format resolution result for user display.

    Returns formatted string for CLI output.
    """
    if result.status == ResolveStatus.FOUND:
        node = result.node
        summary = node.content.get('summary', str(node.content)[:50])
        return f"Found: {node.type} [{node.id[:8]}]\n  \"{summary}\""

    elif result.status == ResolveStatus.AMBIGUOUS:
        lines = [f"Multiple matches for \"{result.query}\":\n"]
        for i, node in enumerate(result.candidates, 1):
            summary = node.content.get('summary', '')[:40]
            lines.append(f"  {i}. [{node.id[:8]}] {summary}")
        lines.append(f"\nWhich one? Enter number or ID prefix:")
        return "\n".join(lines)

    else:  # NOT_FOUND
        lines = [f"No match for \"{result.query}\".\n"]
        if result.candidates:
            lines.append(f"Recent {artifact_type}s:")
            for node in result.candidates:
                summary = node.content.get('summary', '')[:40]
                lines.append(f"  [{node.id[:8]}] {summary}")
        lines.append(f"\nTry: babel <command> <id> ...")
        return "\n".join(lines)


def resolve_with_prompt(
    resolver: IDResolver,
    query: str,
    artifact_type: str = None,
    type_label: str = "artifact"
) -> Optional['Node']:
    """
    Resolve ID with interactive prompt for ambiguous cases.

    Args:
        resolver: IDResolver instance
        query: User input
        artifact_type: Optional type filter
        type_label: Label for display (e.g., "decision")

    Returns:
        Resolved Node or None if cancelled/not found
    """
    result = resolver.resolve(query, artifact_type)

    if result.status == ResolveStatus.FOUND:
        print(format_resolve_prompt(result, type_label))
        return result.node

    elif result.status == ResolveStatus.AMBIGUOUS:
        print(format_resolve_prompt(result, type_label))

        try:
            choice = input("> ").strip()

            # Try as number
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(result.candidates):
                    node = result.candidates[idx]
                    summary = node.content.get('summary', '')[:50]
                    print(f"\nFound: {node.type} [{node.id[:8]}]")
                    print(f"  \"{summary}\"")
                    return node

            # Try as ID prefix
            for node in result.candidates:
                if node.id.startswith(choice):
                    summary = node.content.get('summary', '')[:50]
                    print(f"\nFound: {node.type} [{node.id[:8]}]")
                    print(f"  \"{summary}\"")
                    return node

            print("Invalid selection.")
            return None

        except (EOFError, KeyboardInterrupt):
            return None

    else:  # NOT_FOUND
        print(format_resolve_prompt(result, type_label))
        return None
