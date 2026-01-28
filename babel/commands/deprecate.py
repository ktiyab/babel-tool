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
from ..presentation.formatters import get_node_summary, generate_summary
from ..presentation.template import OutputTemplate


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
            artifact_id: Artifact ID (alias code or prefix) to deprecate
            reason: Why it's being deprecated
            superseded_by: ID (alias code or prefix) of replacement (optional)

        Deprecated items are de-prioritized in retrieval, not deleted (HC1 preserved).
        P8: Requires explanation to avoid silent abandonment.
        """
        symbols = self.symbols

        # Resolve alias codes to raw IDs (counterpart to format_id for output)
        artifact_id = self._cli.resolve_id(artifact_id)
        if superseded_by:
            superseded_by = self._cli.resolve_id(superseded_by)

        # P8: Validate non-empty reason (no silent abandonment) - INTERACTIVE
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
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL DEPRECATE", "Artifact Not Found")
            template.section("STATUS", f"Artifact not found: {artifact_id}")

            # Show recent decisions as suggestions
            decisions = self.graph.get_nodes_by_type("decision")[-5:]
            if decisions:
                suggestion_lines = []
                for d in decisions:
                    summary = generate_summary(get_node_summary(d))
                    suggestion_lines.append(f"  {self._cli.format_id(d.id)} {summary}")
                template.section("RECENT DECISIONS", "\n".join(suggestion_lines))

            template.footer("Specify a valid artifact ID")
            output = template.render(command="deprecate", context={"not_found": True})
            print(output)
            return

        # Check if already deprecated
        if self._is_deprecated(target_node.id):
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL DEPRECATE", "Already Deprecated")
            template.section("STATUS", f"Artifact {self._cli.format_id(target_node.id)} is already deprecated.")
            template.footer("No action needed")
            output = template.render(command="deprecate", context={"already_deprecated": True})
            print(output)
            return

        # Validate superseded_by if provided
        replacement_node = None
        replacement_warning = None
        if superseded_by:
            replacement_node = self._cli._resolve_node(superseded_by, type_label="artifact")
            if not replacement_node:
                replacement_warning = f"Replacement artifact '{superseded_by}' not found."

        # Create deprecation event
        event = deprecate_artifact(
            artifact_id=target_node.id,
            reason=reason,
            superseded_by=replacement_node.id if replacement_node else None
        )

        # Deprecation is shared (team needs to know)
        self.events.append(event, scope=EventScope.SHARED)

        # Build success output with OutputTemplate
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL DEPRECATE", "Artifact Deprecated (P7)")
        template.legend({
            symbols.deprecated: "deprecated",
            symbols.shared: "shared with team"
        })

        # ARTIFACT section
        artifact_line = f"{symbols.deprecated} {self._cli.format_id(target_node.id)}"
        artifact_line += f"\n  Type: {target_node.type}"
        artifact_line += f"\n  Summary: {generate_summary(get_node_summary(target_node))}"
        template.section("ARTIFACT", artifact_line)

        # LESSON section (P8)
        template.section("LESSON (P8)", reason)

        # SUPERSEDED BY section (if applicable)
        if replacement_node:
            template.section("SUPERSEDED BY", self._cli.format_id(replacement_node.id))
        elif replacement_warning:
            template.section("WARNING", replacement_warning)

        # STATUS section
        status_lines = [
            "This artifact is now de-prioritized in queries.",
            "History preserved (HC1) — AI will surface this as a lesson learned (P8)."
        ]
        template.section("STATUS", "\n".join(status_lines))

        template.footer(f"{symbols.shared} Deprecation shared with team")
        output = template.render(command="deprecate", context={"deprecated": True})
        print(output)


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
