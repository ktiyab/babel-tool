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
from ..presentation.symbols import truncate, SUMMARY_LENGTH


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
            decision_id: ID, prefix, or keyword to find decision
            comment: Optional comment on why endorsing
        """
        symbols = self.symbols

        # Resolve target using fuzzy matching (via CLI)
        target_node = self._cli._resolve_node(decision_id, artifact_type='decision', type_label="decision")

        if not target_node:
            return

        success = self.validation.endorse(
            decision_id=target_node.id,
            comment=comment
        )

        if success:
            # Get updated validation
            updated = self.validation.get_validation(target_node.id)

            # Show validation progress
            consensus_needed = 2  # Default threshold
            evidence_needed = 1

            print(f"\nEndorsement added.")
            print(f"\n  Consensus: {updated.endorsement_count} of {consensus_needed}{' needed' if updated.endorsement_count < consensus_needed else ''}")
            print(f"  Evidence: {updated.evidence_count}{' (none yet)' if updated.evidence_count == 0 else ''}")

            short = target_node.event_id[:8] if target_node.event_id else target_node.id.split('_', 1)[-1][:8]
            if updated.status == ValidationStatus.VALIDATED:
                print(f"\n  Status: Validated")
                print(f"  This decision now has both team consensus and evidence.")
            elif updated.status == ValidationStatus.CONSENSUS:
                print(f"\n  Status: Needs evidence")
                print(f"  {symbols.arrow} babel evidence-decision {short} \"observed...\"")
            else:
                print(f"\n  Status: Needs more consensus")
                print(f"  {symbols.arrow} Ask a teammate: babel endorse {short}")
        else:
            print(f"Already endorsed by you.")

    def evidence_decision(
        self,
        decision_id: str,
        content: str,
        evidence_type: str = "observation"
    ):
        """
        Add evidence to a decision with fuzzy ID matching.

        Args:
            decision_id: ID, prefix, or keyword to find decision
            content: The evidence
            evidence_type: observation | benchmark | user_feedback | outcome | other
        """
        symbols = self.symbols

        # Resolve target using fuzzy matching (via CLI)
        target_node = self._cli._resolve_node(decision_id, artifact_type='decision', type_label="decision")

        if not target_node:
            return

        success = self.validation.add_evidence(
            decision_id=target_node.id,
            content=content,
            evidence_type=evidence_type
        )

        if success:
            # Get updated validation
            updated = self.validation.get_validation(target_node.id)

            # Show validation progress
            consensus_needed = 2  # Default threshold

            print(f"\nEvidence added.")
            print(f"  Type: {evidence_type}")
            print(f"\n  Consensus: {updated.endorsement_count} of {consensus_needed}{' needed' if updated.endorsement_count < consensus_needed else ''}")
            print(f"  Evidence: {updated.evidence_count}")

            short = target_node.event_id[:8] if target_node.event_id else target_node.id.split('_', 1)[-1][:8]
            if updated.status == ValidationStatus.VALIDATED:
                print(f"\n  Status: Validated")
                print(f"  This decision now has both team consensus and evidence.")
            elif updated.status == ValidationStatus.EVIDENCED:
                print(f"\n  Status: Needs consensus")
                print(f"  {symbols.arrow} babel endorse {short}")
            else:
                print(f"\n  Status: Needs more consensus")
                print(f"  {symbols.arrow} Ask a teammate: babel endorse {short}")
        else:
            print("Failed to add evidence.")

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

        # Original behavior: print directly
        if decision_id:
            # Show specific decision (use CLI's _find_node_by_id)
            target_node = self._cli._find_node_by_id(decision_id)

            if not target_node:
                print(f"Decision not found: {decision_id}")
                return

            validation = self.validation.get_validation(target_node.id)

            print(f"\nDecision [{target_node.id[:8]}]")
            print(f"  {target_node.content.get('summary', '')}")
            print()

            if validation:
                print(format_validation_status(validation, verbose=verbose, full=full))
            else:
                print(f"{symbols.proposed} PROPOSED -- not yet validated")
                print()
                print("To validate this decision:")
                print(f"  * Consensus: babel endorse {target_node.id[:8]}")
                print(f"  * Evidence: babel evidence {target_node.id[:8]} \"...\"")
        else:
            # Show summary
            print(format_validation_summary(self.validation, full=full))

            # Show partial validations with warnings
            partial = self.validation.get_partially_validated()

            if partial["consensus_only"]:
                print(f"\n{symbols.check_warn} Groupthink Risk (consensus without evidence):")
                for did in partial["consensus_only"][:5]:
                    node = self._cli._find_node_by_id(did)
                    # Extract hash part after "decision_" prefix for display
                    short_id = did.split('_', 1)[-1][:8] if '_' in did else did[:8]
                    if node:
                        summary = truncate(node.content.get('summary', ''), SUMMARY_LENGTH, full)
                        print(f"  [{short_id}] {summary}")
                    else:
                        # Show ID even if node not found in graph
                        print(f"  [{short_id}] (decision not in graph)")
                print(f"\n  {symbols.arrow} babel evidence-decision <id> \"...\" to add evidence")

            if partial["evidence_only"]:
                print(f"\n{symbols.check_warn} Unreviewed Risk (evidence without consensus):")
                for did in partial["evidence_only"][:5]:
                    node = self._cli._find_node_by_id(did)
                    # Extract hash part after "decision_" prefix for display
                    short_id = did.split('_', 1)[-1][:8] if '_' in did else did[:8]
                    if node:
                        summary = truncate(node.content.get('summary', ''), SUMMARY_LENGTH, full)
                        print(f"  [{short_id}] {summary}")
                    else:
                        # Show ID even if node not found in graph
                        print(f"  [{short_id}] (decision not in graph)")
                print(f"\n  {symbols.arrow} babel endorse <id> to add consensus")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("validation", {})

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
            short_id = target_node.id[:8]

            data = {
                "id": short_id,
                "summary": target_node.content.get('summary', ''),
                "status": validation.status.value if validation else "proposed",
                "consensus": validation.endorsement_count if validation else 0,
                "evidence": validation.evidence_count if validation else 0,
                "_actions": [
                    {"command": f"babel endorse {short_id}", "description": "Add consensus"},
                    {"command": f"babel evidence-decision {short_id} \"...\"", "description": "Add evidence"}
                ]
            }

            return OutputSpec(
                data=data,
                shape="detail",
                title=f"Decision [{short_id}]"
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
                    short_id = did.split('_', 1)[-1][:8] if '_' in did else did[:8]
                    summary = node.content.get('summary', '')[:50] if node else "(not in graph)"

                    rows.append({
                        "id": short_id,
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
