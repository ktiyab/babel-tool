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
from ..presentation.template import OutputTemplate


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
            # Build error template
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL COHERENCE", "Project Alignment Check")
            template.section("ERROR", "No purpose defined.")
            template.footer("Run: babel init \"Your purpose\"")
            print(template.render())
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

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL COHERENCE", "Project Alignment Check")
        template.legend({
            symbols.health_aligned: "aligned",
            symbols.health_moderate: "moderate drift",
            symbols.health_high_confusion: "high confusion",
            symbols.tension: "issue detected"
        })

        if qa:
            # Full QA report
            template.section("QA REPORT", format_coherence_report(result, symbols, purposes, full=full))
        else:
            # Standard output
            purpose_text = purposes[0].content.get('purpose', '')
            template.section("PURPOSE", f"{symbols.purpose} {purpose_text}")
            template.section("STATUS", format_coherence_status(result, symbols, verbose=True, full=full))

        # Footer with summary
        has_issues = result.has_issues if result else False
        if has_issues:
            template.footer("Issues detected → babel coherence --resolve")
        else:
            template.footer("Coherent — safe to proceed")

        output = template.render(command="coherence", context={
            "has_issues": has_issues,
            "has_drift": has_issues,
            "has_orphans": self.graph.stats().get('orphans', 0) > 0,
            "implementation_verified": not has_issues
        })
        print(output)

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
            print(f"  {self._cli.format_id(entity.id)} {entity.summary[:60]}...")

            if entity.duplicate_of:
                print(f"  Duplicate of: {self._cli.format_id(entity.duplicate_of)}")
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

        Uses orchestrator for parallel LLM calls when enabled.
        HC2 preserved: AI proposes, human executes.
        """
        symbols = self.symbols

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL COHERENCE", "Batch Resolution Mode (HC2)")
        template.legend({
            symbols.tension: "issue",
            symbols.arrow: "suggested command",
            symbols.check_pass: "analysis complete"
        })

        # Try parallel execution if orchestrator is available and enabled
        suggestions = self._get_suggestions_parallel(issues)

        commands_to_run = []
        issue_lines = []

        for i, entity in enumerate(issues, 1):
            lines = [f"[{i}/{len(issues)}] {entity.status.upper()}: {self._cli.format_id(entity.id)}"]
            lines.append(f"  {entity.summary[:80]}...")

            if entity.duplicate_of:
                lines.append(f"  Duplicate of: {self._cli.format_id(entity.duplicate_of)}")
            if entity.reason:
                lines.append(f"  Reason: {entity.reason}")

            # Get AI suggestion from pre-fetched results
            suggestion = suggestions.get(entity.id)

            if suggestion:
                lines.append(f"\n  AI Analysis ({suggestion.confidence:.0%} confidence):")
                lines.append(f"    {suggestion.pattern_analysis[:100]}...")
                lines.append(f"    Recommendation: {suggestion.recommended_action}")
                if suggestion.suggested_lesson:
                    lines.append(f"    Lesson: {suggestion.suggested_lesson[:80]}...")
                lines.append(f"\n  {symbols.arrow} Command: {suggestion.resolution_command}")
                commands_to_run.append(suggestion.resolution_command)
            else:
                lines.append(f"\n  No AI suggestion available.")
                if entity.resolution_hint:
                    lines.append(f"  Hint: {entity.resolution_hint}")

            issue_lines.append("\n".join(lines))

        template.section(f"ISSUES ({len(issues)} found)", "\n\n".join(issue_lines))

        # Summary with actionable commands
        summary_lines = [
            f"Issues analyzed: {len(issues)}",
            f"Suggestions generated: {len(commands_to_run)}"
        ]

        if commands_to_run:
            summary_lines.append(f"\n{symbols.arrow} Suggested commands to execute:")
            for cmd in commands_to_run:
                summary_lines.append(f"  {cmd}")
            summary_lines.append("\nReview and execute commands above to resolve issues.")

        template.section("SUMMARY", "\n".join(summary_lines))
        template.footer(f"{len(commands_to_run)} suggestion(s) ready")

        print(template.render())

    def _get_suggestions_parallel(self, issues):
        """
        Get AI suggestions for all issues, using parallel execution if available.

        Falls back to sequential execution if orchestrator is disabled or unavailable.

        Returns:
            Dict mapping entity.id -> ResolutionSuggestion (or None)
        """
        suggestions = {}

        # Check if orchestrator is available and enabled
        orchestrator = self.orchestrator
        if orchestrator and orchestrator.enabled and len(issues) > 1:
            # Use parallel execution for multiple issues
            from ..orchestrator import io_task, Priority

            print(f"  (Parallelizing {len(issues)} LLM calls...)")

            # Submit all suggestion requests as I/O tasks (LLM calls)
            futures = []
            for entity in issues:
                task = io_task(
                    fn=self.coherence.suggest_resolution,
                    args=(entity,),
                    priority=Priority.HIGH,
                    name=f"suggest_{self._cli.codec.encode(entity.id)}",
                    timeout=30.0,
                    is_llm_call=True  # Rate limit applies to LLM calls
                )
                future = orchestrator.submit(task)
                futures.append((entity.id, future))

            # Collect results
            for entity_id, future in futures:
                try:
                    result = future.result(timeout=35.0)
                    if result.success:
                        suggestions[entity_id] = result.result
                    else:
                        suggestions[entity_id] = None
                except Exception:
                    suggestions[entity_id] = None
        else:
            # Sequential fallback
            for entity in issues:
                suggestions[entity.id] = self.coherence.suggest_resolution(entity)

        return suggestions

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
            dup_alias = self._cli.codec.encode(entity.duplicate_of)
            reason = f"duplicate of {dup_alias}"
            if lesson:
                reason += f" - Lesson: {lesson}"

            alias = self._cli.codec.encode(entity.id)
            print(f"\n  Executing: babel deprecate {alias} \"{reason}\"")

            # Actually deprecate
            try:
                self._cli.deprecate(
                    artifact_id=alias,
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

            alias = self._cli.codec.encode(entity.id)
            if action == "1":
                print(f"  Executing: babel link {alias}")
                try:
                    self._cli.link(alias)
                except Exception as e:
                    print(f"  Error: {e}")
                    return False
            elif action == "2":
                reason = "no longer relevant"
                if lesson:
                    reason += f" - Lesson: {lesson}"
                print(f"  Executing: babel deprecate {alias} \"{reason}\"")
                try:
                    self._cli.deprecate(
                        artifact_id=alias,
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
                    content=f"Coherence issue {self._cli.format_id(entity.id)}: {entity.summary[:50]}... - {context}"
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
        verbose: bool = False,
        list_findings: bool = False,
        validate_id: str = None,
        invalidate_id: str = None,
        invalidate_reason: str = None,
        resolve_id: str = None,
        show_exclusions: bool = False,
        verify: bool = False,
        remove: bool = False
    ):
        """
        Context-aware technical scan.

        Uses Babel's knowledge (purpose, decisions, constraints)
        to provide project-specific advice.

        Args:
            scan_type: Type of scan (health, architecture, security, performance, dependencies, clean)
            deep: Run comprehensive analysis
            query: Specific question to answer
            verbose: Show all findings including info
            list_findings: List persisted findings from last scan
            validate_id: Mark finding as true positive
            invalidate_id: Mark finding as false positive
            invalidate_reason: Reason for invalidation
            resolve_id: Mark finding as resolved
            show_exclusions: Show excluded findings
            verify: Auto-verify findings using hybrid parser
            remove: Remove verified unused imports (creates git checkpoint)
        """
        symbols = self.symbols

        # Handle findings management operations
        if remove:
            self._remove_verified(scan_type)
            return

        if verify:
            self._verify_findings(scan_type)
            return

        if list_findings:
            self._list_findings(scan_type)
            return

        if validate_id:
            self._validate_finding(scan_type, validate_id)
            return

        if invalidate_id:
            if not invalidate_reason:
                print(f"\n{symbols.check_fail} --reason required with --invalidate")
                print("Example: babel scan --type clean --invalidate abc123 --reason \"Re-export, not unused\"")
                return
            self._invalidate_finding(scan_type, invalidate_id, invalidate_reason)
            return

        if resolve_id:
            self._resolve_finding(scan_type, resolve_id)
            return

        if show_exclusions:
            self._show_exclusions(scan_type)
            return

        # Standard scan
        purposes = self.graph.get_nodes_by_type('purpose')

        if not purposes:
            # Build error template
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SCAN", f"Context-Aware {scan_type.title()} Scan")
            template.section("ERROR", "No purpose defined.\nScan needs context to provide meaningful advice.")
            template.footer("Run: babel init \"Your purpose\"")
            print(template.render())
            return

        # Build template
        template = OutputTemplate(symbols=symbols)
        deep_label = " (deep)" if deep else ""
        template.header("BABEL SCAN", f"{scan_type.title()} Scan{deep_label}")
        template.legend({
            symbols.check_fail: "critical",
            symbols.check_warn: "warning",
            symbols.bullet: "info"
        })

        # Show context
        purpose_text = purposes[0].content.get('purpose', '')
        context_lines = [f"Scanning against: \"{purpose_text[:60]}{'...' if len(purpose_text) > 60 else ''}\""]
        if query:
            context_lines.append(f"Question: {query}")
        else:
            context_lines.append(f"Type: {scan_type}{deep_label}")
        template.section("CONTEXT", "\n".join(context_lines))

        # Run scan
        try:
            result = self.scanner.scan(
                scan_type=scan_type,
                deep=deep,
                query=query
            )

            # Format and display findings
            template.section("FINDINGS", format_scan_result(result, verbose=verbose))

            # Additional hints
            hint_lines = []
            if not verbose and result.findings:
                info_count = sum(1 for f in result.findings if f.severity == "info")
                if info_count > 0:
                    hint_lines.append(f"Run with --verbose to see {info_count} info items")

            if not deep and result.has_concerns:
                hint_lines.append("Run `babel scan --deep` for comprehensive analysis")

            # For clean scan, show management hints
            if scan_type == "clean" and result.findings:
                hint_lines.extend([
                    "",
                    "Manage findings:",
                    "  babel scan --type clean --list              # List findings with IDs",
                    "  babel scan --type clean --validate ID       # Confirm as true issue",
                    "  babel scan --type clean --invalidate ID --reason \"...\"  # False positive",
                    "  babel scan --type clean --resolve-finding ID  # After fixing"
                ])

            if hint_lines:
                template.section("HINTS", "\n".join(hint_lines))

            # Footer with summary
            finding_count = len(result.findings) if result.findings else 0
            if result.has_concerns:
                template.footer(f"{finding_count} finding(s) — concerns detected")
            else:
                template.footer(f"{finding_count} finding(s) — no concerns")

            output = template.render(command="scan", context={"has_concerns": result.has_concerns})
            print(output)

        except Exception as e:
            template.section("ERROR", f"Scan failed: {e}")
            template.footer("Check LLM configuration with `babel config`")
            print(template.render())

    def _list_findings(self, scan_type: str):
        """List persisted findings from last scan."""
        symbols = self.symbols
        findings = self.scanner.get_findings(scan_type)
        summary = self.scanner.get_findings_summary(scan_type)

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL SCAN", f"{scan_type.title()} Findings")
        template.legend({
            symbols.bullet: "pending",
            symbols.check_warn: "validated (confirmed issue)",
            symbols.check_pass: "resolved"
        })

        # Summary section
        summary_text = (f"Pending: {summary['pending']}  Validated: {summary['validated']}  "
                       f"Resolved: {summary['resolved']}  Excluded: {summary['excluded']}")
        template.section("SUMMARY", summary_text)

        if not findings:
            template.section("FINDINGS", f"No findings. Run: babel scan --type {scan_type}")
            template.footer("No findings to display")
            print(template.render())
            return

        # Build findings list
        finding_lines = []
        for f in findings:
            status_icon = {
                "pending": symbols.bullet,
                "validated": symbols.check_warn,
                "resolved": symbols.check_pass
            }.get(f.status, symbols.bullet)

            # Show ID + location + symbol
            id_str = f"[{f.finding_id[:8]}]" if f.finding_id else ""
            loc_str = f"{f.file}:{f.line}" if f.file and f.line else ""
            sym_str = f" ({f.containing_symbol})" if f.containing_symbol else ""

            lines = [f"{status_icon} {id_str} {f.title}"]
            lines.append(f"   {loc_str}{sym_str}")
            if f.linked_decisions:
                lines.append(f"   Linked: {', '.join(f.linked_decisions)}")
            finding_lines.append("\n".join(lines))

        template.section("FINDINGS", "\n\n".join(finding_lines))
        template.footer(f"{len(findings)} finding(s) listed")
        print(template.render())

    def _validate_finding(self, scan_type: str, finding_id: str):
        """Mark finding as true positive (confirmed issue)."""
        symbols = self.symbols

        updated = self.scanner.update_finding_status(scan_type, finding_id, "validated")
        if updated:
            print(f"\n{symbols.check_pass} Finding [{finding_id[:8]}] marked as validated (true positive)")
            print(f"   {updated.title}")
            if updated.file:
                print(f"   {updated.file}:{updated.line}")
        else:
            print(f"\n{symbols.check_fail} Finding not found: {finding_id}")
            print(f"   Run: babel scan --type {scan_type} --list")

    def _invalidate_finding(self, scan_type: str, finding_id: str, reason: str):
        """Mark finding as false positive and add to exclusions."""
        symbols = self.symbols

        # Get finding first for metadata
        finding = self.scanner.get_finding(scan_type, finding_id)
        if not finding:
            print(f"\n{symbols.check_fail} Finding not found: {finding_id}")
            print(f"   Run: babel scan --type {scan_type} --list")
            return

        success = self.scanner.add_exclusion(scan_type, finding_id, reason, finding)
        if success:
            print(f"\n{symbols.check_pass} Finding [{finding_id[:8]}] invalidated (false positive)")
            print(f"   {finding.title}")
            print(f"   Reason: {reason}")
            print(f"   Will be excluded from future scans.")
        else:
            print(f"\n{symbols.check_warn} Finding already excluded: {finding_id}")

    def _resolve_finding(self, scan_type: str, finding_id: str):
        """Mark finding as resolved (after fixing)."""
        symbols = self.symbols

        updated = self.scanner.update_finding_status(scan_type, finding_id, "resolved")
        if updated:
            print(f"\n{symbols.check_pass} Finding [{finding_id[:8]}] marked as resolved")
            print(f"   {updated.title}")
            print(f"\nNote: Run scan again to verify the fix.")
        else:
            print(f"\n{symbols.check_fail} Finding not found: {finding_id}")
            print(f"   Run: babel scan --type {scan_type} --list")

    def _show_exclusions(self, scan_type: str):
        """Show excluded findings (false positives)."""
        symbols = self.symbols
        exclusions = self.scanner.get_exclusions(scan_type)

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL SCAN", f"{scan_type.title()} Exclusions")
        template.legend({
            symbols.local: "excluded (false positive)"
        })

        if not exclusions:
            template.section("EXCLUSIONS", "No exclusions.")
            template.footer("No exclusions configured")
            print(template.render())
            return

        # Build exclusions list
        exclusion_lines = []
        for finding_id, info in exclusions.items():
            file_str = info.get('file', 'unknown')
            line_str = info.get('line', '?')
            reason = info.get('reason', 'No reason provided')
            excluded_at = info.get('excluded_at', '')[:10]  # Date only

            lines = [
                f"[{finding_id[:8]}] {file_str}:{line_str}",
                f"   Reason: {reason}",
                f"   Excluded: {excluded_at}"
            ]
            exclusion_lines.append("\n".join(lines))

        template.section("EXCLUSIONS", "\n\n".join(exclusion_lines))
        template.footer(f"{len(exclusions)} exclusion(s) configured")
        print(template.render())

    def _verify_findings(self, scan_type: str):
        """
        Auto-verify findings using hybrid parser.

        Uses regex fast-path + AST cross-check to determine if findings
        are true positives (genuinely unused) or false positives (actually used).
        """
        symbols = self.symbols
        from ..services.scanner import VERIFIED_TRUE, UNCERTAIN

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL SCAN", f"Verify {scan_type.title()} Findings")
        template.legend({
            symbols.check_pass: "true positive (safe to remove)",
            symbols.check_warn: "false positive (actually used)",
            "?": "uncertain (needs manual review)"
        })

        # Run verification
        results = self.scanner.verify_findings(scan_type)

        verified_true = results.get("verified_true", 0)
        verified_false = results.get("verified_false", 0)
        uncertain = results.get("uncertain", 0)
        total = verified_true + verified_false + uncertain

        if total == 0:
            template.section("STATUS", f"No findings to verify.\nRun: babel scan --type {scan_type}")
            template.footer("No findings")
            print(template.render())
            return

        # Summary section
        summary_lines = [
            f"Verified: {total} findings",
            "",
            f"{symbols.check_pass} True positives (safe to remove): {verified_true}",
            f"{symbols.check_warn} False positives (actually used): {verified_false}",
            f"? Uncertain (needs manual review): {uncertain}"
        ]
        template.section("SUMMARY", "\n".join(summary_lines))

        # Show breakdown by status
        if verified_true > 0:
            true_lines = []
            for f in results.get("findings", []):
                if f.status == VERIFIED_TRUE:
                    true_lines.append(f"[{f.finding_id[:8]}] {f.symbol} in {f.file}:{f.line}")
            template.section("TRUE POSITIVES (ready for removal)", "\n".join(true_lines))

        if uncertain > 0:
            uncertain_lines = []
            for f in results.get("findings", []):
                if f.status == UNCERTAIN:
                    uncertain_lines.append(f"[{f.finding_id[:8]}] {f.symbol} in {f.file}:{f.line}")
            template.section("UNCERTAIN (needs manual review)", "\n".join(uncertain_lines))

        # Next step hints
        if verified_true > 0:
            template.footer(f"Next: babel scan --type {scan_type} --remove (removes {verified_true} verified)")
        elif uncertain > 0:
            template.footer(f"Next: Review uncertain findings manually")

        print(template.render())

    def _remove_verified(self, scan_type: str):
        """
        Remove verified unused imports with safety checkpoint.

        Creates git commit before modifications for rollback.
        All-or-nothing: reverts on any failure OR test failure.
        """
        symbols = self.symbols
        from pathlib import Path

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL SCAN", f"Remove Verified {scan_type.title()} Findings")
        template.legend({
            symbols.check_pass: "success",
            symbols.check_fail: "failed/reverted"
        })

        # Run removal (with automatic test execution)
        result = self.scanner.remove_verified_imports(scan_type, run_tests=True)

        # Handle test failure (auto-reverted)
        test_results = result.get("test_results")
        if not result["success"] and test_results and not test_results["success"]:
            error_lines = [
                f"{symbols.check_fail} Tests Failed - Auto-Reverted",
                "",
                f"Tests run:    {test_results['tests_run']}",
                f"Tests passed: {test_results['tests_passed']}",
                f"Tests failed: {test_results['tests_failed']}",
                "",
                "Test files checked:"
            ]
            for tf in test_results.get("test_files", [])[:5]:
                try:
                    rel_path = Path(tf).relative_to(Path.cwd())
                except ValueError:
                    rel_path = tf
                error_lines.append(f"  - {rel_path}")
            error_lines.append("")
            error_lines.append(f"Error: {test_results.get('error', 'Unknown')}")
            template.section("TEST FAILURE", "\n".join(error_lines))
            template.footer("Review test failures and fix before retrying — changes auto-reverted")
            print(template.render())
            return

        if not result["success"]:
            template.section("ERROR", f"Removal failed: {result['error']}")
            template.footer("Check error and retry")
            print(template.render())
            return

        removed_count = result["removed_count"]
        files_modified = result["files_modified"]
        checkpoint_sha = result["checkpoint_sha"]

        # Show removal summary
        summary_lines = [
            f"Removed: {removed_count} unused imports",
            f"Files:   {len(files_modified)} modified",
            ""
        ]

        # Show file breakdown
        for file_info in files_modified[:10]:  # Limit display
            file_path = file_info["file"]
            count = len(file_info["removals"])
            try:
                rel_path = Path(file_path).relative_to(Path.cwd())
            except ValueError:
                rel_path = file_path
            summary_lines.append(f"  {rel_path} - {count} import(s)")

        if len(files_modified) > 10:
            summary_lines.append(f"  ... ({len(files_modified) - 10} more files)")

        template.section("CLEANUP COMPLETE", "\n".join(summary_lines))

        # Show test results if tests were run
        if test_results:
            test_lines = [
                f"{symbols.check_pass} Tests Passed",
                f"Tests run:    {test_results['tests_run']}",
                f"Tests passed: {test_results['tests_passed']}"
            ]
            if test_results.get("test_files"):
                test_lines.append(f"Test files:   {len(test_results['test_files'])}")
            template.section("TESTS", "\n".join(test_lines))

        # Auto-capture per file (one capture per modified file)
        captures = self.scanner.create_cleanup_captures(files_modified, test_results)
        if captures:
            # Add proposals to batch queue
            for capture in captures:
                proposal = capture["proposal"]
                self.events.append(proposal)
            template.section("CAPTURES", f"{len(captures)} proposal(s) added to batch queue")

        # Footer with rollback and next steps
        template.footer(f"Rollback: git revert {checkpoint_sha[:7]} | Next: babel review --list")
        print(template.render())


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

# Multiple commands registered by this module
COMMAND_NAMES = ['coherence', 'scan']


def register_parser(subparsers):
    """Register coherence and scan command parsers."""
    # coherence command
    p1 = subparsers.add_parser('coherence', help='Check project coherence')
    p1.add_argument('--force', action='store_true', help='Force full check (ignore cache)')
    p1.add_argument('--full', action='store_true', help='Show full content without truncation')
    p1.add_argument('--qa', action='store_true', help='QA/QC mode with detailed report')
    p1.add_argument('--resolve', action='store_true',
                    help='Interactive resolution mode for issues (Living Cycle re-negotiation)')
    p1.add_argument('--batch', action='store_true',
                    help='Non-interactive mode with --resolve (for AI operators)')

    # scan command
    p2 = subparsers.add_parser('scan', help='Context-aware technical scan')
    p2.add_argument('query', nargs='?', default=None, help='Specific question to answer')
    p2.add_argument('--type', dest='scan_type', default='health',
                    choices=['health', 'architecture', 'security', 'performance', 'dependencies', 'clean'],
                    help='Type of scan (default: health). clean=code cleanup via ruff')
    p2.add_argument('--deep', action='store_true', help='Run comprehensive analysis')
    p2.add_argument('-v', '--verbose', action='store_true', help='Show all findings')

    # Findings management (for clean scan workflow)
    p2.add_argument('--list', dest='list_findings', action='store_true',
                    help='List persisted findings from last scan')
    p2.add_argument('--validate', dest='validate_id', metavar='ID',
                    help='Mark finding as true positive (confirmed issue)')
    p2.add_argument('--invalidate', dest='invalidate_id', metavar='ID',
                    help='Mark finding as false positive (exclude from future scans)')
    p2.add_argument('--reason', dest='invalidate_reason', metavar='REASON',
                    help='Reason for invalidation (required with --invalidate)')
    p2.add_argument('--resolve-finding', dest='resolve_id', metavar='ID',
                    help='Mark finding as resolved (after fixing)')
    p2.add_argument('--exclusions', dest='show_exclusions', action='store_true',
                    help='Show excluded findings (false positives)')

    # Verification and removal (for clean scan automation)
    p2.add_argument('--verify', dest='verify', action='store_true',
                    help='Auto-verify findings using hybrid parser (regex + AST)')
    p2.add_argument('--remove', dest='remove', action='store_true',
                    help='Remove verified unused imports (creates git checkpoint, requires --verify first)')

    return p1, p2


def handle(cli, args):
    """Handle coherence or scan command dispatch."""
    if args.command == 'coherence':
        cli._coherence_cmd.coherence_check(
            force=args.force,
            full=args.full,
            qa=args.qa,
            resolve=args.resolve,
            batch=args.batch
        )
    elif args.command == 'scan':
        cli._coherence_cmd.scan(
            scan_type=args.scan_type,
            deep=args.deep,
            query=args.query,
            verbose=args.verbose,
            list_findings=getattr(args, 'list_findings', False),
            validate_id=getattr(args, 'validate_id', None),
            invalidate_id=getattr(args, 'invalidate_id', None),
            invalidate_reason=getattr(args, 'invalidate_reason', None),
            resolve_id=getattr(args, 'resolve_id', None),
            show_exclusions=getattr(args, 'show_exclusions', False),
            verify=getattr(args, 'verify', False),
            remove=getattr(args, 'remove', False)
        )
