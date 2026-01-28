"""
ValidationCommand — Dual-test truth tracking

Handles decision validation (P5: Dual-Test Truth):
- Endorsing decisions (consensus)
- Adding evidence to decisions
- Viewing validation status
"""

from typing import Optional

from ..commands.base import BaseCommand
from ..tracking.validation import ValidationStatus, format_validation_status, format_validation_summary
from ..presentation.formatters import get_node_summary, generate_summary, format_timestamp
from ..presentation.template import OutputTemplate


class ValidationCommand(BaseCommand):
    """
    Command for decision validation.

    P5: Dual-Test Truth — decisions need both consensus AND evidence.
    Consensus alone risks groupthink.
    Evidence alone risks blind spots.
    """

    def endorse(self, decision_id: str, comment: str = None):
        """
        Endorse a decision with fuzzy ID matching.

        Args:
            decision_id: ID (alias code or prefix) to find decision
            comment: Optional comment on why endorsing
        """
        symbols = self.symbols

        # Resolve alias code to raw ID (counterpart to format_id for output)
        decision_id = self._cli.resolve_id(decision_id)

        # Resolve target using fuzzy matching (via CLI)
        target_node = self._cli._resolve_node(decision_id, artifact_type='decision', type_label="decision")

        if not target_node:
            return

        success = self.validation.endorse(
            decision_id=target_node.id,
            comment=comment
        )

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL ENDORSE", "P5: Dual-Test Truth — Consensus")
        template.legend({
            symbols.validated: "validated (both consensus + evidence)",
            symbols.consensus_only: "consensus only",
            symbols.evidence_only: "evidence only",
            symbols.proposed: "proposed"
        })

        if success:
            # Get updated validation
            updated = self.validation.get_validation(target_node.id)

            # Show validation progress
            consensus_needed = 2  # Default threshold
            alias = self._cli.codec.encode(target_node.id)

            progress_lines = [
                "Endorsement added.",
                "",
                f"  Consensus: {updated.endorsement_count} of {consensus_needed}{' needed' if updated.endorsement_count < consensus_needed else ''}",
                f"  Evidence: {updated.evidence_count}{' (none yet)' if updated.evidence_count == 0 else ''}"
            ]
            template.section("PROGRESS", "\n".join(progress_lines))

            if updated.status == ValidationStatus.VALIDATED:
                template.footer("Status: Validated — both team consensus and evidence")
            elif updated.status == ValidationStatus.CONSENSUS:
                template.footer(f"Status: Needs evidence → babel evidence-decision {alias} \"observed...\"")
            else:
                template.footer(f"Status: Needs more consensus → Ask a teammate: babel endorse {alias}")
        else:
            template.section("STATUS", "Already endorsed by you.")
            template.footer("No action needed")

        output = template.render(command="endorse", context={})
        print(output)

    def evidence_decision(
        self,
        decision_id: str,
        content: str,
        evidence_type: str = "observation"
    ):
        """
        Add evidence to a decision with fuzzy ID matching.

        Args:
            decision_id: ID (alias code or prefix) to find decision
            content: The evidence
            evidence_type: observation | benchmark | user_feedback | outcome | other
        """
        symbols = self.symbols

        # Resolve alias code to raw ID (counterpart to format_id for output)
        decision_id = self._cli.resolve_id(decision_id)

        # Resolve target using fuzzy matching (via CLI)
        target_node = self._cli._resolve_node(decision_id, artifact_type='decision', type_label="decision")

        if not target_node:
            return

        success = self.validation.add_evidence(
            decision_id=target_node.id,
            content=content,
            evidence_type=evidence_type
        )

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL EVIDENCE", "P5: Dual-Test Truth — Evidence")
        template.legend({
            symbols.validated: "validated (both consensus + evidence)",
            symbols.consensus_only: "consensus only",
            symbols.evidence_only: "evidence only",
            symbols.proposed: "proposed"
        })

        if success:
            # Get updated validation
            updated = self.validation.get_validation(target_node.id)

            # Show validation progress
            consensus_needed = 2  # Default threshold
            alias = self._cli.codec.encode(target_node.id)

            progress_lines = [
                "Evidence added.",
                f"  Type: {evidence_type}",
                "",
                f"  Consensus: {updated.endorsement_count} of {consensus_needed}{' needed' if updated.endorsement_count < consensus_needed else ''}",
                f"  Evidence: {updated.evidence_count}"
            ]
            template.section("PROGRESS", "\n".join(progress_lines))

            if updated.status == ValidationStatus.VALIDATED:
                template.footer("Status: Validated — both team consensus and evidence")
            elif updated.status == ValidationStatus.EVIDENCED:
                template.footer(f"Status: Needs consensus → babel endorse {alias}")
            else:
                template.footer(f"Status: Needs more consensus → Ask a teammate: babel endorse {alias}")
        else:
            template.section("ERROR", "Failed to add evidence.")
            template.footer("Check decision ID and try again")

        output = template.render(command="evidence-decision", context={})
        print(output)

    def validation_cmd(self, decision_id: str = None, verbose: bool = False, full: bool = False, output_format: str = None):
        """
        Show validation status (P5: dual-test truth tracking).

        Args:
            decision_id: Specific decision ID (or show summary)
            verbose: Show full details
            full: Show full content without truncation
            output_format: If specified, return OutputSpec for rendering instead of printing
        """
        symbols = self.symbols

        # If output_format specified, collect data and return OutputSpec
        if output_format:
            return self._validation_as_output(decision_id, verbose, full)

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL VALIDATION", "P5: Dual-Test Truth")
        template.legend({
            symbols.validated: "validated (both consensus + evidence)",
            symbols.consensus_only: "consensus only (groupthink risk)",
            symbols.evidence_only: "evidence only (unreviewed risk)",
            symbols.proposed: "proposed"
        })

        if decision_id:
            # Show specific decision (use CLI's _find_node_by_id)
            target_node = self._cli._find_node_by_id(decision_id)

            if not target_node:
                template.section("ERROR", f"Decision not found: {decision_id}")
                template.footer("Check decision ID and try again")
                print(template.render())
                return

            validation = self.validation.get_validation(target_node.id)
            alias = self._cli.codec.encode(target_node.id)

            decision_lines = [
                f"Decision [{self._cli.format_id(target_node.id)}]",
                f"  {get_node_summary(target_node)}"
            ]
            template.section("DECISION", "\n".join(decision_lines))

            if validation:
                template.section("STATUS", format_validation_status(validation, verbose=verbose, full=full))
                template.footer(f"Decision {validation.status.value}")
            else:
                action_lines = [
                    f"{symbols.proposed} PROPOSED -- not yet validated",
                    "",
                    "To validate this decision:",
                    f"  * Consensus: babel endorse {alias}",
                    f"  * Evidence: babel evidence-decision {alias} \"...\""
                ]
                template.section("STATUS", "\n".join(action_lines))
                template.footer("Decision needs validation")
        else:
            # Show summary
            template.section("SUMMARY", format_validation_summary(self.validation, full=full))

            # Show partial validations with warnings
            partial = self.validation.get_partially_validated()

            if partial["consensus_only"]:
                groupthink_lines = [f"{symbols.check_warn} Groupthink Risk (consensus without evidence):"]
                for did in partial["consensus_only"][:5]:
                    node = self._cli._find_node_by_id(did)
                    formatted_id = self._cli.format_id(did)
                    if node:
                        summary = generate_summary(get_node_summary(node), full=full)
                        # P12: Time always shown
                        time_str = f" ({format_timestamp(node.created_at)})" if node.created_at else ""
                        groupthink_lines.append(f"  {formatted_id} {summary}{time_str}")
                    else:
                        groupthink_lines.append(f"  {formatted_id} (decision not in graph)")
                groupthink_lines.append(f"\n  {symbols.arrow} babel evidence-decision <id> \"...\" to add evidence")
                template.section("WARNING", "\n".join(groupthink_lines))

            if partial["evidence_only"]:
                unreviewed_lines = [f"{symbols.check_warn} Unreviewed Risk (evidence without consensus):"]
                for did in partial["evidence_only"][:5]:
                    node = self._cli._find_node_by_id(did)
                    formatted_id = self._cli.format_id(did)
                    if node:
                        summary = generate_summary(get_node_summary(node), full=full)
                        # P12: Time always shown
                        time_str = f" ({format_timestamp(node.created_at)})" if node.created_at else ""
                        unreviewed_lines.append(f"  {formatted_id} {summary}{time_str}")
                    else:
                        unreviewed_lines.append(f"  {formatted_id} (decision not in graph)")
                unreviewed_lines.append(f"\n  {symbols.arrow} babel endorse <id> to add consensus")
                template.section("WARNING", "\n".join(unreviewed_lines))

            # Footer summary
            stats = self.validation.stats()
            template.footer(f"{stats['validated']} validated | {stats['tracked']} tracked")

        output = template.render(command="validation", context={})
        print(output)

    def _validation_as_output(self, decision_id: str = None, verbose: bool = False, full: bool = False):
        """
        Return validation data as OutputSpec for rendering.

        This enables --format flag support while keeping original print behavior.
        """
        from babel.output import OutputSpec

        if decision_id:
            # Single decision detail view
            target_node = self._cli._find_node_by_id(decision_id)
            if not target_node:
                return OutputSpec(
                    data={"error": f"Decision not found: {decision_id}"},
                    shape="detail",
                    title="Error"
                )

            validation = self.validation.get_validation(target_node.id)
            alias = self._cli.codec.encode(target_node.id)

            data = {
                "id": alias,
                "summary": get_node_summary(target_node),
                "status": validation.status.value if validation else "proposed",
                "consensus": validation.endorsement_count if validation else 0,
                "evidence": validation.evidence_count if validation else 0,
                "_actions": [
                    {"command": f"babel endorse {alias}", "description": "Add consensus"},
                    {"command": f"babel evidence-decision {alias} \"...\"", "description": "Add evidence"}
                ]
            }

            return OutputSpec(
                data=data,
                shape="detail",
                title=f"Decision [{alias}]"
            )
        else:
            # Summary table view
            stats = self.validation.stats()

            # Build rows for table by iterating through each status
            rows = []
            from ..tracking.validation import ValidationStatus

            for status in [ValidationStatus.VALIDATED, ValidationStatus.CONSENSUS, ValidationStatus.EVIDENCED]:
                decision_ids = self.validation.get_by_status(status)
                for did in decision_ids:
                    node = self._cli._find_node_by_id(did)
                    val = self.validation.get_validation(did)
                    alias = self._cli.codec.encode(did)
                    summary = generate_summary(get_node_summary(node)) if node else "(not in graph)"

                    rows.append({
                        "id": alias,
                        "decision": summary,
                        "status": val.status.value if val else "proposed",
                        "consensus": val.endorsement_count if val else 0,
                        "evidence": val.evidence_count if val else 0
                    })

            return OutputSpec(
                data=rows,
                shape="table",
                columns=["ID", "Decision", "Status", "Consensus", "Evidence"],
                column_keys=["id", "decision", "status", "consensus", "evidence"],
                title=f"Validation Status: {stats['tracked']} decisions tracked\n[V] Validated: {stats['validated']}"
            )


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

# Multiple commands registered by this module
COMMAND_NAMES = ['validation', 'endorse', 'evidence-decision']


def register_parser(subparsers):
    """Register validation, endorse, and evidence-decision command parsers."""
    # validation command
    p1 = subparsers.add_parser('validation', help='Show validation status (P9: dual-test truth)')
    p1.add_argument('decision_id', nargs='?', help='Specific decision ID (optional)')
    p1.add_argument('-v', '--verbose', action='store_true', help='Show full details')
    p1.add_argument('--full', action='store_true', help='Show full content without truncation')
    p1.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json', 'detail'],
                    help='Output format (overrides config)')

    # endorse command
    p2 = subparsers.add_parser('endorse', help='Endorse a decision (P9: consensus)')
    p2.add_argument('decision_id', help='Decision ID (or prefix) to endorse')
    p2.add_argument('--comment', '-c', help='Optional comment on why endorsing')

    # evidence-decision command
    p3 = subparsers.add_parser('evidence-decision', help='Add evidence to a decision (P9: grounding)')
    p3.add_argument('decision_id', help='Decision ID (or prefix)')
    p3.add_argument('content', help='The evidence')
    p3.add_argument('--type', dest='evidence_type', default='observation',
                    choices=['observation', 'benchmark', 'user_feedback', 'outcome', 'other'],
                    help='Type of evidence (default: observation)')

    return p1, p2, p3


def handle(cli, args):
    """Handle validation, endorse, or evidence-decision command dispatch."""
    if args.command == 'validation':
        cli._validation_cmd.validation_cmd(
            decision_id=args.decision_id,
            verbose=args.verbose,
            full=args.full,
            output_format=getattr(args, 'format', None)
        )
    elif args.command == 'endorse':
        cli._validation_cmd.endorse(
            args.decision_id,
            comment=args.comment
        )
    elif args.command == 'evidence-decision':
        cli._validation_cmd.evidence_decision(
            args.decision_id,
            args.content,
            evidence_type=args.evidence_type
        )
