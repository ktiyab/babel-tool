"""
TensionsCommand — Disagreement tracking and resolution

Handles P4 (Disagreement as Hypothesis):
- Raising challenges against decisions
- Adding evidence to challenges
- Resolving challenges with outcomes
- Viewing tension status
"""

import json
from typing import Optional

from ..commands.base import BaseCommand
from ..tracking.tensions import format_challenge, format_tensions_summary
from ..tracking.ambiguity import check_premature_resolution
from ..core.domains import suggest_domain_for_capture
from ..core.events import classify_evolution


class TensionsCommand(BaseCommand):
    """
    Command for tension and disagreement management.

    P4: Disagreement as Hypothesis — disagreement is information, not noise.
    Challenges require hypotheses and tests.
    """

    def challenge(
        self,
        target_id: str,
        reason: str,
        hypothesis: str = None,
        test: str = None,
        domain: str = None
    ):
        """
        Challenge a decision with fuzzy ID matching.

        Args:
            target_id: ID, prefix, or keyword to find decision
            reason: Why you disagree
            hypothesis: Testable alternative (optional)
            test: How to test the hypothesis (optional)
            domain: Expertise domain
        """
        symbols = self.symbols

        # Resolve target using fuzzy matching (via CLI)
        target_node = self._cli._resolve_node(target_id, type_label="decision")

        if not target_node:
            return

        # Auto-suggest hypothesis if not provided
        if not hypothesis and self.extractor.is_available:
            print(f"\nChallenging: {target_node.content.get('summary', '')[:60]}")
            print(f"Reason: {reason}")
            print("\nThis could be tested. Propose a hypothesis?")

            suggested = self._suggest_hypothesis(reason, target_node)
            if suggested:
                print(f"  Suggestion: \"{suggested['hypothesis']}\"")
                if suggested.get('test'):
                    print(f"  Test with: \"{suggested['test']}\"")
                print()
                response = input("[Y]es, add / [N]o, just record / [E]dit: ").strip().lower()

                if response in ['y', 'yes', '']:
                    hypothesis = suggested['hypothesis']
                    test = suggested.get('test', test)
                elif response in ['e', 'edit']:
                    hypothesis = input("Your hypothesis: ").strip() or None
                    if hypothesis:
                        test = input("Test (optional): ").strip() or None

        # Infer domain if not provided
        if not domain:
            domain = suggest_domain_for_capture(reason)

        # Create challenge
        challenge = self.tensions.raise_challenge(
            parent_id=target_node.id,
            parent_type=target_node.type,
            reason=reason,
            hypothesis=hypothesis,
            test=test,
            domain=domain
        )

        domain_tag = f" [{domain}]" if domain else ""
        print(f"\n{symbols.tension} Challenge raised [{challenge.id[:8]}]{domain_tag}")
        print(f"  Against: {target_node.type} [{target_node.id[:8]}]")
        print(f"  Reason: {reason}")

        if hypothesis:
            print(f"  Hypothesis: {hypothesis}")
        if test:
            print(f"  Test: {test}")

        print(f"\n{symbols.arrow} Add evidence: babel evidence {challenge.id[:8]} \"what you learned\"")
        print(f"{symbols.arrow} Resolve: babel resolve {challenge.id[:8]} --outcome confirmed|revised|synthesized")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("challenge", {})

    def evidence(self, challenge_id: str, content: str, evidence_type: str = "observation"):
        """
        Add evidence to an open challenge (P4).

        Args:
            challenge_id: Challenge ID (or prefix)
            content: The evidence
            evidence_type: observation | benchmark | user_feedback | other
        """
        symbols = self.symbols

        # Find challenge
        challenge = self._find_challenge_by_id(challenge_id)

        if not challenge:
            print(f"Challenge not found: {challenge_id}")
            open_challenges = self.tensions.get_open_challenges()
            if open_challenges:
                print("\nOpen challenges:")
                for c in open_challenges[:5]:
                    print(f"  {c.id[:8]} | {c.reason[:40]}")
            return

        if challenge.status == "resolved":
            print(f"Challenge [{challenge_id[:8]}] is already resolved.")
            return

        success = self.tensions.add_evidence(
            challenge_id=challenge.id,
            content=content,
            evidence_type=evidence_type
        )

        if success:
            evidence_count = len(challenge.evidence) + 1
            print(f"Evidence added to [{challenge.id[:8]}] ({evidence_count} total)")
            print(f"  Type: {evidence_type}")
            print(f"  Content: {content[:60]}...")

            if challenge.hypothesis:
                print(f"\n{symbols.arrow} When ready: babel resolve {challenge.id[:8]} --outcome confirmed|revised|synthesized")

            # Succession hint (centralized)
            from ..output import end_command
            end_command("evidence", {})
        else:
            print("Failed to add evidence.")

    def resolve(
        self,
        challenge_id: str,
        outcome: str,
        resolution: str = None,
        evidence_summary: str = None,
        force: bool = False
    ):
        """
        Resolve a challenge (P4: requires evidence, not authority).

        Args:
            challenge_id: Challenge ID (or prefix)
            outcome: confirmed | revised | synthesized | uncertain
            resolution: What was decided (prompted if not provided)
            evidence_summary: Summary of evidence
            force: Skip premature resolution warning (P10)
        """
        symbols = self.symbols

        # Find challenge
        challenge = self._find_challenge_by_id(challenge_id)

        if not challenge:
            print(f"Challenge not found: {challenge_id}")
            return

        if challenge.status == "resolved":
            print(f"Challenge [{challenge_id[:8]}] is already resolved.")
            if challenge.resolution:
                print(f"  Outcome: {challenge.resolution['outcome']}")
                print(f"  Resolution: {challenge.resolution['resolution']}")
            return

        # Validate outcome (P10: add 'uncertain' as valid outcome)
        valid_outcomes = ["confirmed", "revised", "synthesized", "uncertain"]
        if outcome not in valid_outcomes:
            print(f"Invalid outcome: {outcome}")
            print(f"Valid outcomes: {', '.join(valid_outcomes)}")
            return

        # P10: Check for premature resolution
        if outcome != "uncertain" and not force:
            check = check_premature_resolution(len(challenge.evidence))
            if check["is_premature"]:
                print(f"\n{symbols.check_warn} {check['warning']}")
                print(f"  {check['recommendation']}")
                print()
                print("Options:")
                print("  1. Continue anyway (resolve with current evidence)")
                print("  2. Mark as uncertain (hold ambiguity)")
                print("  3. Cancel (gather more evidence)")
                print()
                choice = input("Choice [1/2/3]: ").strip()

                if choice == "2":
                    outcome = "uncertain"
                    print("\nMarking as uncertain -- holding ambiguity is epistemic maturity.")
                elif choice == "3" or choice not in ["1", "2", "3"]:
                    print("Cancelled. Gather more evidence with: babel evidence ...")
                    return

        # Prompt for resolution if not provided
        if not resolution:
            print(f"\nResolving challenge [{challenge.id[:8]}]")
            print(f"  Reason: {challenge.reason}")
            if challenge.hypothesis:
                print(f"  Hypothesis: {challenge.hypothesis}")
            print(f"  Evidence items: {len(challenge.evidence)}")
            print(f"  Outcome: {outcome}")
            print()

            # P8: Emphasize lesson-learned for revised outcome
            if outcome == "revised":
                print("P8: What did we learn from this? (Failure is not loss; unexamined failure is)")
                resolution = input("Lesson learned: ").strip()
            else:
                resolution = input("Resolution (what was decided and why): ").strip()

            if not resolution:
                if outcome == "revised":
                    print("Lesson required for revised outcome (P8: no silent abandonment).")
                else:
                    print("Resolution required. Aborting.")
                return

        # P8: Validate non-empty resolution for revised outcome (failure metabolism)
        if outcome == "revised" and resolution and len(resolution.strip()) < 10:
            print(f"\n{symbols.check_warn} P8: Resolution seems too brief for a lesson.")
            print("  What specifically did we learn from this failure?")
            more = input("  Add more detail (or press Enter to continue): ").strip()
            if more:
                resolution = f"{resolution} -- {more}"

        # Auto-summarize evidence if not provided
        if not evidence_summary and challenge.evidence:
            evidence_summary = "; ".join([e['content'][:50] for e in challenge.evidence[-3:]])

        success = self.tensions.resolve(
            challenge_id=challenge.id,
            outcome=outcome,
            resolution=resolution,
            evidence_summary=evidence_summary
        )

        if success:
            outcome_icons = {
                "confirmed": symbols.check_pass,
                "revised": symbols.revised,
                "synthesized": symbols.synthesized
            }
            icon = outcome_icons.get(outcome, symbols.validated)

            print(f"\n{icon} Challenge resolved [{challenge.id[:8]}]")
            print(f"  Outcome: {outcome}")
            print(f"  Resolution: {resolution}")

            if outcome == "confirmed":
                print(f"\n  Original decision stands.")
            elif outcome == "revised":
                print(f"\n  Original superseded.")
                # P8: Create evolves_from relation for traceability
                # If force=True, assume non-interactive (AI operator)
                self._prompt_evolution_link(challenge, resolution, batch=force)
            elif outcome == "synthesized":
                print(f"\n  New understanding emerged from disagreement.")

            # Succession hint (centralized)
            from ..output import end_command
            remaining = self.tensions.count_open()
            end_command("resolve", {"has_remaining": remaining > 0})
        else:
            print("Failed to resolve challenge.")

    def tensions_cmd(self, verbose: bool = False, full: bool = False, output_format: str = None):
        """
        Show open tensions (P4: disagreement tracking).

        Args:
            verbose: Show full details including evidence
            full: Show full content without truncation
            output_format: If specified, return OutputSpec for rendering
        """
        # If output_format specified, return OutputSpec
        if output_format:
            return self._tensions_as_output(verbose, full)

        # Original behavior: print directly
        print(format_tensions_summary(self.tensions, full=full))

        if verbose:
            open_challenges = self.tensions.get_open_challenges()
            if open_challenges:
                print("\n" + "-" * 50)
                for challenge in open_challenges:
                    print()
                    print(format_challenge(challenge, verbose=True, full=full))

        # Succession hint (centralized)
        from ..output import end_command
        has_open = self.tensions.count_open() > 0
        end_command("tensions", {"has_open": has_open})

        # Option 3: Contextual P10 hint when no tensions AND no questions
        if not has_open:
            questions_count = self.questions.count_open() + len(self.questions.get_resolved_questions())
            decisions_count = len(self.graph.get_nodes_by_type('decision'))
            if questions_count == 0 and decisions_count > 10:
                symbols = self.symbols
                print(f"\n{symbols.check_warn} P10: {decisions_count} decisions but no questions captured.")
                print(f"  Consider: babel question \"...\" to capture uncertainties.")

    def _tensions_as_output(self, verbose: bool = False, full: bool = False):
        """Return tensions data as OutputSpec for rendering."""
        from babel.output import OutputSpec

        stats = self.tensions.stats()
        open_challenges = self.tensions.get_open_challenges()

        rows = []
        for challenge in open_challenges:
            # Get target info
            target_node = self._cli._find_node_by_id(challenge.target_id) if hasattr(self, '_cli') else None
            target_summary = target_node.content.get('summary', '')[:30] if target_node else challenge.target_id[:8]

            # Evidence status
            evidence_count = len(challenge.evidence) if challenge.evidence else 0
            hypothesis_status = "untested" if challenge.hypothesis and evidence_count == 0 else f"{evidence_count} ev." if evidence_count > 0 else "-"

            rows.append({
                "id": challenge.id[:8],
                "target": target_summary,
                "status": challenge.status,
                "reason": challenge.reason[:40] if challenge.reason else "",
                "evidence": hypothesis_status
            })

        title = f"Open Tensions: {stats['open']}" if stats['open'] > 0 else "No open tensions"
        if stats['resolved'] > 0:
            title += f" | Resolved: {stats['resolved']}"

        return OutputSpec(
            data=rows,
            shape="table",
            columns=["ID", "Target", "Status", "Reason", "Evidence"],
            column_keys=["id", "target", "status", "reason", "evidence"],
            title=title,
            empty_message="No open tensions. Project is in agreement."
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _find_challenge_by_id(self, challenge_id: str):
        """Find a challenge by ID prefix."""
        challenges = self.tensions._load_challenges()
        for cid, challenge in challenges.items():
            if cid.startswith(challenge_id):
                return challenge
        return None

    def _is_interactive(self) -> bool:
        """Check if running in interactive mode (has stdin)."""
        import sys
        return sys.stdin.isatty()

    def _prompt_evolution_link(self, challenge, resolution: str, batch: bool = False):
        """
        Prompt user to create evolves_from link for revised outcome (P8: Evolution Traceable).

        When a challenge results in revision, the new artifact should be linked
        to the old one via evolves_from relation for traceability.

        Args:
            challenge: The resolved challenge
            resolution: The resolution text
            batch: If True, skip interactive prompts (for AI operators)
        """
        symbols = self.symbols
        parent_id = challenge.parent_id

        # Non-interactive mode: just show the hint without prompting
        if batch or not self._is_interactive():
            print(f"\n  P8: Evolution link available from [{parent_id[:8]}]")
            print(f"  To link: babel link <new_artifact_id> {parent_id[:8]}")
            return

        print(f"\n  P8: Track evolution from original [{parent_id[:8]}]?")
        print(f"  This creates an evolves_from link for traceability.")
        print()

        # Check if there's a recently captured decision that might be the replacement
        recent_decisions = self._get_recent_decisions(limit=5)
        if recent_decisions:
            print("  Recent decisions that might supersede the original:")
            for i, (node_id, summary) in enumerate(recent_decisions, 1):
                print(f"    {i}. [{node_id[:8]}] {summary[:50]}")
            print()
            try:
                choice = input("  Enter number to link, or [S]kip: ").strip().lower()
            except EOFError:
                print("  Skipped (non-interactive).")
                return

            if choice in ['s', 'skip', '']:
                print("  Skipped. You can manually link later with: babel link <new_id> <old_id>")
                return

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(recent_decisions):
                    new_id, new_summary = recent_decisions[idx]

                    # Create evolves_from event
                    evolution_event = classify_evolution(
                        artifact_id=new_id,
                        evolves_from_id=parent_id,
                        classification_method="manual",
                        confidence=1.0,
                        reason=resolution,
                        author="user"
                    )
                    self.events.append(evolution_event)

                    print(f"\n  {symbols.check_pass} Evolution link created:")
                    print(f"    [{new_id[:8]}] evolves_from [{parent_id[:8]}]")
                    return
            except ValueError:
                pass

        # No recent decisions or user didn't select
        new_id = input("  Enter superseding artifact ID (or [S]kip): ").strip()
        if new_id.lower() in ['s', 'skip', '']:
            print("  Skipped.")
            return

        # Try to resolve the ID
        node = self._cli._resolve_node(new_id, type_label="decision") if hasattr(self, '_cli') else None
        if node:
            evolution_event = classify_evolution(
                artifact_id=node.id,
                evolves_from_id=parent_id,
                classification_method="manual",
                confidence=1.0,
                reason=resolution,
                author="user"
            )
            self.events.append(evolution_event)
            print(f"\n  {symbols.check_pass} Evolution link created:")
            print(f"    [{node.id[:8]}] evolves_from [{parent_id[:8]}]")
        else:
            print(f"  Could not find artifact: {new_id}")

    def _get_recent_decisions(self, limit: int = 5):
        """Get recently captured decisions for evolution linking."""
        from ..core.events import EventType

        decisions = []
        # Read events in reverse order (most recent first)
        all_events = list(reversed(self.events.read_all()))

        for event in all_events:
            if event.type == EventType.ARTIFACT_CONFIRMED:
                if event.data.get('artifact_type') == 'decision':
                    node_id = f"decision_{event.id}"
                    summary = event.data.get('content', {}).get('summary', '')
                    decisions.append((node_id, summary))
                    if len(decisions) >= limit:
                        break

        return decisions

    def _suggest_hypothesis(self, reason: str, target_node) -> Optional[dict]:
        """Use AI to suggest a hypothesis from disagreement reason."""
        if not self.extractor.is_available:
            return None

        try:
            prompt = f"""A team member disagrees with a decision.

Decision: {target_node.content.get('summary', '')}
Disagreement reason: {reason}

Suggest a testable hypothesis that could resolve this disagreement.
Respond with JSON: {{"hypothesis": "...", "test": "..."}}
Keep both under 100 characters."""

            response = self.provider.complete(prompt)

            # Try to parse JSON from response
            start = response.text.find('{')
            end = response.text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response.text[start:end])
        except Exception:
            pass

        return None
