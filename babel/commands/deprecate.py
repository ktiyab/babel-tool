"""
DeprecateCommand — Artifact deprecation management

Handles P7 (Evidence-Weighted Memory) and P8 (Failure Metabolism):
- Deprecating artifacts with required explanations
- Tracking deprecated artifact status
- Preserving history while de-prioritizing in queries
"""

from typing import Optional

from ..commands.base import BaseCommand
from ..core.events import EventType, deprecate_artifact
from ..core.scope import EventScope


class DeprecateCommand(BaseCommand):
    """
    Command for artifact deprecation.

    P7: Living artifacts, not exhaustive archives — deprecated items
    are de-prioritized, not deleted.
    P8: Failure Metabolism — requires explanation to avoid silent abandonment.
    """

    def _get_deprecated_ids(self) -> dict:
        """Get all deprecated artifact IDs with their deprecation info."""
        deprecated = {}
        events = self.events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        for event in events:
            artifact_id = event.data.get("artifact_id", "")
            deprecated[artifact_id] = {
                "reason": event.data.get("reason", ""),
                "superseded_by": event.data.get("superseded_by"),
                "author": event.data.get("author", "unknown"),
                "timestamp": event.timestamp
            }
        return deprecated

    def _is_deprecated(self, artifact_id: str) -> Optional[dict]:
        """Check if artifact is deprecated. Returns deprecation info or None."""
        deprecated = self._get_deprecated_ids()
        # Use centralized resolve_id for codec alias and prefix matching
        candidate_ids = list(deprecated.keys())
        resolved_id = self._cli.resolve_id(artifact_id, candidate_ids, "deprecated artifact")
        if resolved_id:
            return deprecated[resolved_id]
        return None

    def deprecate(
        self,
        artifact_id: str,
        reason: str,
        superseded_by: str = None
    ):
        """
        Deprecate an artifact (P7: living artifacts, not exhaustive archives).

        Args:
            artifact_id: Artifact ID (or prefix) to deprecate
            reason: Why it's being deprecated
            superseded_by: ID of replacement (optional)

        Deprecated items are de-prioritized in retrieval, not deleted (HC1 preserved).
        P8: Requires explanation to avoid silent abandonment.
        """
        symbols = self.symbols

        # P8: Validate non-empty reason (no silent abandonment)
        if not reason or len(reason.strip()) < 5:
            print(f"{symbols.check_warn} P8: Reason required for deprecation (no silent abandonment).")
            print("  Why is this being deprecated? What did we learn?")
            reason = input("Reason: ").strip()
            if not reason or len(reason.strip()) < 5:
                print("Deprecation requires explanation. Aborting.")
                return

        # Find the target artifact (decision, constraint, etc.)
        target_node = self._cli._resolve_node(artifact_id, type_label="artifact")

        if not target_node:
            print(f"Artifact not found: {artifact_id}")
            print("\nRecent decisions:")
            decisions = self.graph.get_nodes_by_type("decision")[-5:]
            for d in decisions:
                summary = d.content.get("summary", "")[:40]
                print(f"  {self._cli.format_id(d.id)} {summary}")
            return

        # Check if already deprecated
        if self._is_deprecated(target_node.id):
            print(f"Artifact {self._cli.format_id(target_node.id)} is already deprecated.")
            return

        # Validate superseded_by if provided
        replacement_node = None
        if superseded_by:
            replacement_node = self._cli._resolve_node(superseded_by, type_label="artifact")
            if not replacement_node:
                print(f"Warning: Replacement artifact '{superseded_by}' not found.")

        # Create deprecation event
        event = deprecate_artifact(
            artifact_id=target_node.id,
            reason=reason,
            superseded_by=replacement_node.id if replacement_node else None
        )

        # Deprecation is shared (team needs to know)
        self.events.append(event, scope=EventScope.SHARED)

        print(f"\n{symbols.deprecated} Deprecated {self._cli.format_id(target_node.id)}")
        print(f"  {target_node.type}: {target_node.content.get('summary', '')[:50]}")
        print(f"  Lesson: {reason}")

        if replacement_node:
            print(f"  Superseded by: {self._cli.format_id(replacement_node.id)}")

        print()
        print("This artifact is now de-prioritized in queries.")
        print("History preserved (HC1) -- AI will surface this as a lesson learned (P8).")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("deprecate", {})


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'deprecate'


def register_parser(subparsers):
    """Register deprecate command parser."""
    p = subparsers.add_parser('deprecate', help='Deprecate an artifact (P7: living memory)')
    p.add_argument('artifact_id', help='Artifact ID (or prefix) to deprecate')
    p.add_argument('reason', help='Why it is being deprecated')
    p.add_argument('--superseded-by', help='ID of replacement artifact')
    return p


def handle(cli, args):
    """Handle deprecate command dispatch."""
    cli._deprecate_cmd.deprecate(
        args.artifact_id,
        args.reason,
        superseded_by=args.superseded_by
    )
