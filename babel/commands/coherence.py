"""
CoherenceCommand — Project coherence verification and scanning

Handles coherence checking and context-aware scanning:
- Project coherence verification
- Purpose-aware technical scanning
- AI-assisted issue resolution (Living Cycle re-negotiation step)
"""

from ..commands.base import BaseCommand
from ..tracking.coherence import format_coherence_status, format_coherence_report, ResolutionSuggestion
from ..services.scanner import format_scan_result


class CoherenceCommand(BaseCommand):
    """
    Command for project coherence and scanning.

    Verifies alignment between purpose, decisions, and constraints.
    Provides context-aware technical advice based on project knowledge.
    Supports AI-assisted resolution of coherence issues (P4, P8, P11).
    """

    def coherence_check(self, force: bool = False, full: bool = False, qa: bool = False, resolve: bool = False, batch: bool = False):
        """
        Check project coherence.

        Args:
            force: Force full check (ignore cache)
            full: Show full content without truncation
            qa: QA/QC mode with detailed report
            resolve: Enter interactive resolution mode for issues
            batch: Non-interactive mode (for AI operators) - shows suggestions without prompts
        """
        symbols = self.symbols
        purposes = self.graph.get_nodes_by_type('purpose')

        if not purposes:
            print("\nNo purpose defined. Run: babel init \"Your purpose\"")
            return

        trigger = "qa" if qa else ("resolve" if resolve else "manual")
        result = self.coherence.check(
            trigger=trigger,
            triggered_by="user",
            force_full=force or resolve  # Always fresh check for resolution
        )

        if resolve:
            # Enter resolution mode (interactive or batch)
            self._resolve_issues(result, full, batch=batch)
            return

        if qa:
            # Full QA report
            print(f"\n{format_coherence_report(result, symbols, purposes, full=full)}")
        else:
            # Standard output
            print(f"\n{symbols.purpose} Purpose: {purposes[0].content.get('purpose', '')}")
            print(f"\n{format_coherence_status(result, symbols, verbose=True, full=full)}")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("coherence", {"has_issues": result.has_issues if result else False})

    def _resolve_issues(self, result, full: bool = False, batch: bool = False):
        """
        Resolution mode for coherence issues.

        Implements the Living Cycle re-negotiation step:
        1. Surface each issue with AI analysis
        2. Suggest resolution using existing mechanisms
        3. Ask for lesson (P8: Failure Metabolism)
        4. Offer principle capture (P11: Cross-Domain Learning)

        Args:
            result: Coherence check result
            full: Show full content without truncation
            batch: Non-interactive mode - shows all suggestions without prompts (for AI operators)

        HC2: Human decides, AI proposes.
        """
        symbols = self.symbols
        issues = result.get_issues()

        if not issues:
            print(f"\n{symbols.check_pass} No issues to resolve. Project is coherent.")
            return

        if batch:
            # Batch mode: show all suggestions without interaction
            self._resolve_issues_batch(issues)
            return

        # Interactive mode
        print(f"\n{symbols.tension} Found {len(issues)} issue(s) to resolve.")
        print("Walking through each issue with AI guidance (P4: Layered Expertise).\n")
        print("-" * 60)

        resolved_count = 0
        skipped_count = 0

        for i, entity in enumerate(issues, 1):
            print(f"\nIssue {i} of {len(issues)}: {entity.status.upper()}")
            print(f"  [{entity.id[:8]}] {entity.summary[:60]}...")

            if entity.duplicate_of:
                print(f"  Duplicate of: [{entity.duplicate_of[:8]}]")
            if entity.reason:
                print(f"  Reason: {entity.reason}")

            # Try AI-assisted suggestion
            suggestion = self.coherence.suggest_resolution(entity)

            if suggestion:
                print(f"\n  AI Analysis:")
                print(f"    Pattern: {suggestion.pattern_analysis}")
                print(f"    Recommendation: {suggestion.recommended_action}")
                print(f"    Confidence: {suggestion.confidence:.0%}")
                if suggestion.suggested_lesson:
                    print(f"    Suggested lesson: {suggestion.suggested_lesson}")
                if suggestion.suggested_principle:
                    print(f"    Suggested principle: {suggestion.suggested_principle}")
                print(f"\n    Command: {suggestion.resolution_command}")
            else:
                # Fall back to hint-only mode
                print(f"\n  Resolution hint:")
                if entity.resolution_hint:
                    print(f"    {entity.resolution_hint}")
                else:
                    print(f"    No AI available. Use existing commands to resolve.")

            print("\n  Options:")
            print("    1. Execute suggested resolution")
            print("    2. Skip this issue")
            print("    3. Mark as uncertain (need more info)")
            print("    4. Exit resolution mode")

            try:
                choice = input("\n  Choice [1/2/3/4]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Resolution mode exited.")
                break

            if choice == "1":
                # Execute resolution
                resolved = self._execute_resolution(entity, suggestion)
                if resolved:
                    resolved_count += 1
            elif choice == "2":
                print("  Skipped.")
                skipped_count += 1
            elif choice == "3":
                # Mark as uncertain
                self._mark_uncertain(entity)
            elif choice == "4":
                print("\n  Exiting resolution mode.")
                break
            else:
                print("  Invalid choice. Skipping.")
                skipped_count += 1

            print("-" * 60)

        # Summary
        print(f"\n{symbols.check_pass} Resolution complete.")
        print(f"  Resolved: {resolved_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Remaining: {len(issues) - resolved_count - skipped_count}")

        if resolved_count > 0:
            print(f"\n{symbols.arrow} Run `babel coherence` to verify changes.")

    def _resolve_issues_batch(self, issues):
        """
        Batch resolution mode: show all AI suggestions without interaction.

        For AI operators who can't use interactive prompts.
        Shows analysis and commands, user executes manually.

        HC2 preserved: AI proposes, human executes.
        """
        symbols = self.symbols

        print(f"\n{symbols.tension} Found {len(issues)} issue(s) to resolve.")
        print("Batch mode: Showing AI suggestions (no interaction).\n")
        print("=" * 60)

        commands_to_run = []

        for i, entity in enumerate(issues, 1):
            print(f"\n[{i}/{len(issues)}] {entity.status.upper()}: [{entity.id[:8]}]")
            print(f"  {entity.summary[:80]}...")

            if entity.duplicate_of:
                print(f"  Duplicate of: [{entity.duplicate_of[:8]}]")
            if entity.reason:
                print(f"  Reason: {entity.reason}")

            # Get AI suggestion
            suggestion = self.coherence.suggest_resolution(entity)

            if suggestion:
                print(f"\n  AI Analysis ({suggestion.confidence:.0%} confidence):")
                print(f"    {suggestion.pattern_analysis[:100]}...")
                print(f"    Recommendation: {suggestion.recommended_action}")
                if suggestion.suggested_lesson:
                    print(f"    Lesson: {suggestion.suggested_lesson[:80]}...")
                print(f"\n  {symbols.arrow} Command: {suggestion.resolution_command}")
                commands_to_run.append(suggestion.resolution_command)
            else:
                print(f"\n  No AI suggestion available.")
                if entity.resolution_hint:
                    print(f"  Hint: {entity.resolution_hint}")

            print("-" * 60)

        # Summary with actionable commands
        print(f"\n{symbols.check_pass} Batch analysis complete.")
        print(f"  Issues analyzed: {len(issues)}")
        print(f"  Suggestions generated: {len(commands_to_run)}")

        if commands_to_run:
            print(f"\n{symbols.arrow} Suggested commands to execute:")
            for cmd in commands_to_run:
                print(f"  {cmd}")
            print(f"\nReview and execute commands above to resolve issues.")

    def _execute_resolution(self, entity, suggestion) -> bool:
        """Execute a resolution action with P8 lesson extraction."""
        symbols = self.symbols

        # Get lesson (P8: Failure Metabolism)
        print("\n  P8: What did we learn from this issue?")
        if suggestion and suggestion.suggested_lesson:
            print(f"    Suggested: {suggestion.suggested_lesson}")
            use_suggested = input("    Use this lesson? [Y/n]: ").strip().lower()
            if use_suggested in ('', 'y', 'yes'):
                lesson = suggestion.suggested_lesson
            else:
                lesson = input("    Your lesson: ").strip()
        else:
            lesson = input("    Lesson learned: ").strip()

        if not lesson:
            print("  P8 requires a lesson. No silent abandonment.")
            confirm = input("  Continue anyway? [y/N]: ").strip().lower()
            if confirm not in ('y', 'yes'):
                return False

        # Execute the deprecation/resolution
        if entity.status == "duplicate" and entity.duplicate_of:
            reason = f"duplicate of {entity.duplicate_of[:8]}"
            if lesson:
                reason += f" - Lesson: {lesson}"

            print(f"\n  Executing: babel deprecate {entity.id[:8]} \"{reason}\"")

            # Actually deprecate
            try:
                self._cli.deprecate(
                    artifact_id=entity.id[:8],
                    reason=reason
                )
            except Exception as e:
                print(f"  Error: {e}")
                return False

        elif entity.status == "low_alignment":
            print(f"\n  For low alignment, choose:")
            print("    1. Link to purpose (babel link)")
            print("    2. Deprecate (babel deprecate)")
            action = input("    Action [1/2]: ").strip()

            if action == "1":
                print(f"  Executing: babel link {entity.id[:8]}")
                try:
                    self._cli.link(entity.id[:8])
                except Exception as e:
                    print(f"  Error: {e}")
                    return False
            elif action == "2":
                reason = "no longer relevant"
                if lesson:
                    reason += f" - Lesson: {lesson}"
                print(f"  Executing: babel deprecate {entity.id[:8]} \"{reason}\"")
                try:
                    self._cli.deprecate(
                        artifact_id=entity.id[:8],
                        reason=reason
                    )
                except Exception as e:
                    print(f"  Error: {e}")
                    return False

        # Offer principle capture (P11: Cross-Domain Learning)
        if suggestion and suggestion.suggested_principle:
            print(f"\n  P11: Should this become a principle?")
            print(f"    Suggested: {suggestion.suggested_principle}")
            capture = input("    Capture as principle? [y/N]: ").strip().lower()
            if capture in ('y', 'yes'):
                print(f"  Capturing principle...")
                try:
                    self._cli.capture(
                        text=f"PRINCIPLE: {suggestion.suggested_principle}. Learned from: {lesson or 'resolution'}",
                        batch=True
                    )
                    print(f"  {symbols.check_pass} Principle queued for review.")
                except Exception as e:
                    print(f"  Error capturing principle: {e}")

        print(f"\n  {symbols.check_pass} Resolved.")
        return True

    def _mark_uncertain(self, entity):
        """Mark an issue as needing more information."""
        symbols = self.symbols
        context = input("  What's uncertain? ").strip()

        if context:
            try:
                self._cli.question(
                    content=f"Coherence issue [{entity.id[:8]}]: {entity.summary[:50]}... - {context}"
                )
                print(f"  {symbols.check_pass} Marked as open question.")
            except Exception as e:
                print(f"  Error: {e}")
        else:
            print("  Skipped.")

    def scan(
        self,
        scan_type: str = "health",
        deep: bool = False,
        query: str = None,
        verbose: bool = False
    ):
        """
        Context-aware technical scan.

        Uses Babel's knowledge (purpose, decisions, constraints)
        to provide project-specific advice.

        Args:
            scan_type: Type of scan (health, architecture, security, performance, dependencies)
            deep: Run comprehensive analysis
            query: Specific question to answer
            verbose: Show all findings including info
        """
        purposes = self.graph.get_nodes_by_type('purpose')

        if not purposes:
            print("\nNo purpose defined. Run: babel init \"Your purpose\"")
            print("Scan needs context to provide meaningful advice.")
            return

        # Show what we're scanning against
        purpose_text = purposes[0].content.get('purpose', '')
        print(f"\nScanning against: \"{purpose_text[:60]}{'...' if len(purpose_text) > 60 else ''}\"")

        if query:
            print(f"Question: {query}")
        else:
            print(f"Type: {scan_type}{'(deep)' if deep else ''}")

        print()

        # Run scan
        try:
            result = self.scanner.scan(
                scan_type=scan_type,
                deep=deep,
                query=query
            )

            # Format and display
            print(format_scan_result(result, verbose=verbose))

            if not verbose and result.findings:
                info_count = sum(1 for f in result.findings if f.severity == "info")
                if info_count > 0:
                    print(f"\nRun with --verbose to see {info_count} info items")

            if not deep and result.has_concerns:
                print(f"\nRun `babel scan --deep` for comprehensive analysis")

            # Succession hint (centralized)
            from ..output import end_command
            end_command("scan", {"has_concerns": result.has_concerns})

        except Exception as e:
            print(f"Scan failed: {e}")
            print("Check LLM configuration with `babel config`")
