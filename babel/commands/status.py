"""
StatusCommand — Project status display and health assessment

Handles project status overview with:
- Event and artifact counts
- Purpose display
- Coherence status
- Validation status (P9)
- Open tensions (P4)
- Open questions (P10)
- Project health computation (adaptive pace guidance)
"""

from ..commands.base import BaseCommand
from ..core.events import EventType
from ..core.commit_links import CommitLinkStore
from ..presentation.formatters import generate_summary, format_timestamp
from ..presentation.template import OutputTemplate
from ..tracking.coherence import format_coherence_status
from ..tracking.principles import PrincipleChecker, format_principles_summary
from ..services.providers import get_provider_status
from ..services.git import GitIntegration


class StatusCommand(BaseCommand):
    """
    Command for displaying project status and health.

    P9: Adaptive Cycle Rate - health assessment guides pace.
    Multi-factor health scoring: maturity, alignment, confusion.
    """

    def status(self, full: bool = False, git: bool = False, force: bool = False,
               format: str = "auto", limit_purposes: int = 10):
        """
        Show project status.

        Args:
            full: If True, show full content without truncation
            git: If True, show git-babel sync health
            force: If True, bypass cache and force fresh data reads
            format: Output format - "auto", "json", "table", "list", "summary"
            limit_purposes: Max recent purposes to show (default 10, 0 for all)
        """
        # Clear caches if force flag is set
        if force:
            self.events.clear_cache()

        # For JSON format, collect structured data and render via output system
        if format == "json":
            data = self._collect_status_data(full=full, git=git)
            from ..output import OutputSpec, render
            spec = OutputSpec(
                data=data,
                shape="detail",
                title="Project Status",
                command="status"
            )
            output = render(spec, format="json", symbols=self.symbols, full=full)
            print(output)
            return

        # Initialize template
        symbols = self.symbols
        template = OutputTemplate(symbols=symbols, full=full)

        # Collect data
        stats = self.graph.stats()
        shared_count, local_count = self.events.count_by_scope()
        total_events = shared_count + local_count
        orphans = stats['orphans']

        # === HEADER ===
        template.header("BABEL STATUS", "Project Health Overview")
        template.legend({
            symbols.shared: "shared",
            symbols.local: "local",
            symbols.purpose: "purpose",
            symbols.tension: "tension"
        })

        # === INIT INSTRUCTIONS SECTION ===
        init_memos = self._cli.memos.list_init_memos()
        if init_memos:
            init_lines = []
            for memo in init_memos:
                content_display = generate_summary(memo.content)
                init_lines.append(f"{symbols.arrow} {content_display}")
            template.section(f"{symbols.purpose} Init Instructions (read before work)", "\n".join(init_lines))

        # === PROJECT METRICS SECTION ===
        metrics_lines = []
        metrics_lines.append(f"Project: {self.project_dir}")
        metrics_lines.append(f"Events: {total_events} ({symbols.shared} {shared_count} shared, {symbols.local} {local_count} local)")
        metrics_lines.append(f"Artifacts: {stats['nodes']}")
        metrics_lines.append(f"Connections: {stats['edges']}")
        if orphans > 0:
            metrics_lines.append(f"Unlinked: {orphans} (isolated - can't inform 'why' queries)")
            if full:
                metrics_lines.append(f"  Impact: Knowledge silos form, reasoning chains break")
                metrics_lines.append(f"  Action: babel link <id> --to <related-id>")
        template.section("PROJECT METRICS", "\n".join(metrics_lines))

        # === PURPOSES SECTION ===
        all_purposes_count = len(self.graph.get_nodes_by_type('purpose'))
        if limit_purposes > 0:
            purposes = self.graph.get_nodes_by_type_recent('purpose', limit=limit_purposes)
        else:
            purposes = self.graph.get_nodes_by_type('purpose')
        if purposes:
            purpose_lines = []
            for p in purposes:
                purpose_lines.append(self._display_purpose(p.content, full=full, created_at=p.created_at))
            if limit_purposes > 0 and all_purposes_count > limit_purposes:
                purpose_lines.append(f"\n({all_purposes_count - limit_purposes} older purposes hidden)")
                purpose_lines.append(f"{symbols.arrow} babel list purposes --all")
            template.section("ACTIVE PURPOSES", "\n".join(purpose_lines))

        # === COHERENCE SECTION ===
        last_result = self.coherence.get_last_result()
        coherence_lines = []
        if last_result:
            coherence_lines.append(format_coherence_status(last_result, symbols, full=full))
            if last_result.has_issues:
                coherence_lines.append("  Review with: babel coherence")
        elif purposes:
            coherence_lines.append("Coherence: not yet checked")
            coherence_lines.append("  Run: babel coherence")
        if coherence_lines:
            template.section("COHERENCE", "\n".join(coherence_lines))

        # === STATUS SECTION (commits, tensions, validation, questions) ===
        status_lines = []

        # Commits
        commits = self.events.read_by_type(EventType.COMMIT_CAPTURED)
        if commits:
            status_lines.append(f"Commits captured: {len(commits)}")

        # Tensions (P4)
        open_tensions = self.tensions.count_open()
        if open_tensions > 0:
            status_lines.append(f"{symbols.tension} Open Tensions: {open_tensions}")
            status_lines.append(f"  Run: babel tensions")

        # Validation (P9)
        validation_stats = self.validation.stats()
        if validation_stats["tracked"] > 0:
            partial = validation_stats["partial"]
            validated = validation_stats["validated"]
            if partial > 0:
                status_lines.append(f"{symbols.consensus_only} Validation: {validated} validated, {partial} need review (require both consensus + evidence)")
                if validation_stats["groupthink_risk"] > 0:
                    status_lines.append(f"  {symbols.check_warn} {validation_stats['groupthink_risk']} consensus-only (agreed but untested - groupthink risk)")
                if validation_stats["unreviewed_risk"] > 0:
                    status_lines.append(f"  {symbols.check_warn} {validation_stats['unreviewed_risk']} evidence-only (tested but not endorsed)")
                status_lines.append(f"  Run: babel validation")
                if full:
                    status_lines.append(f"  Impact: Unvalidated decisions may be challenged later")
                    status_lines.append(f"  Action: babel endorse <id> (add consensus) or babel evidence-decision <id> (add evidence)")
            elif validated > 0:
                status_lines.append(f"{symbols.validated} Validation: {validated} decisions validated (have both consensus + evidence)")

        # Questions (P10)
        open_questions_count = self.questions.count_open()
        if open_questions_count > 0:
            status_lines.append(f"? Open Questions: {open_questions_count}")
            status_lines.append(f"  (Acknowledged unknowns -- not failures)")
            status_lines.append(f"  Run: babel questions")

        if status_lines:
            template.section("STATUS", "\n".join(status_lines))

        # === SCAN FINDINGS SECTION ===
        scan_summary = self._get_scan_findings_summary()
        if scan_summary:
            scan_lines = []
            for scan_type, counts in scan_summary.items():
                pending = counts.get("pending", 0)
                excluded = counts.get("excluded", 0)
                if pending > 0:
                    scan_lines.append(self._format_scan_type_summary(scan_type, pending, excluded))
            if scan_lines:
                template.section(f"{symbols.check_warn} SCAN FINDINGS", "\n".join(scan_lines))

        # === INFRASTRUCTURE SECTION ===
        infra_lines = []

        # LLM status
        provider_status = get_provider_status(self.config)
        infra_lines.append(f"Extraction: {provider_status}")

        # Git hooks
        git_integration = GitIntegration(self.project_dir)
        if git_integration.is_git_repo:
            hooks_status = git_integration.hooks_status()
            infra_lines.append(f"Git hooks: {hooks_status}")

            if git:
                infra_lines.append(self._format_git_sync_health(git_integration, full=full))
            else:
                commit_links = CommitLinkStore(self.babel_dir)
                link_count = commit_links.count()
                if link_count > 0:
                    infra_lines.append(f"Decision-commit links: {link_count}")
                    infra_lines.append(f"  Run: babel status --git (detailed sync health)")

        # Pending proposals
        pending_proposals = self._count_pending_proposals()
        if pending_proposals > 0:
            infra_lines.append(f"Pending: {pending_proposals} proposal(s) (AI insights awaiting your confirmation)")
            infra_lines.append(f"  Run: babel review")
            if full:
                infra_lines.append(f"  Impact: Unconfirmed proposals are lost when session ends")
                infra_lines.append(f"  Action: Review and confirm valuable insights")

        # Extraction queue
        queued = 0
        if self.extractor.queue:
            queued = self.extractor.queue.count()
            if queued > 0:
                infra_lines.append(f"Queued: {queued} extraction(s) (text awaiting LLM analysis - requires API key)")
                if full:
                    infra_lines.append(f"  Impact: Raw captures exist but structured artifacts not extracted")
                    infra_lines.append(f"  Action: Set API key, then: babel process-queue (interactive) or babel process-queue --batch (AI)")

        if infra_lines:
            template.section("INFRASTRUCTURE", "\n".join(infra_lines))

        # === HEALTH SECTION ===
        principle_checker = PrincipleChecker(
            graph=self.graph,
            validation=self.validation,
            questions=self.questions,
            vocabulary=self.vocabulary
        )
        principle_result = principle_checker.check_all()

        health = self._compute_project_health(
            open_tensions=open_tensions,
            validation_stats=validation_stats,
            open_questions=open_questions_count,
            coherence_result=last_result,
            principle_result=principle_result
        )

        health_lines = []
        health_lines.append(f"{health['indicator']} Project Health: {health['level']} ({principle_result.satisfied_count}/{principle_result.total_applicable} principles)")
        if health['suggestion']:
            health_lines.append(f"  {health['suggestion']}")

        if full or principle_result.warning_count > 0 or principle_result.violation_count > 0:
            health_lines.append(format_principles_summary(principle_result, symbols, full=full))

        health_lines.append("\nReady.")
        template.section("HEALTH", "\n".join(health_lines))

        # === FOOTER with succession hint ===
        template.footer(f"{stats['nodes']} artifacts | {validated if validation_stats['tracked'] > 0 else 0} validated | {principle_result.satisfied_count}/{principle_result.total_applicable} principles")

        # Render and print with succession context
        output = template.render(command="status", context={
            "has_queued_extractions": queued > 0,
            "has_pending": pending_proposals > 0,
            "has_high_unlinked": orphans > 50,
            "has_unlinked": orphans > 0 and orphans <= 50,
            "has_tensions": open_tensions > 0,
            "has_questions": open_questions_count > 0,
            "has_partial_validation": validation_stats.get("partial", 0) > 0,
            "healthy": health['level'] in ("Aligned", "Growing"),
        })
        print(output)

    def _display_purpose(self, content: dict, full: bool = False, created_at: str = "") -> str:
        """
        Format purpose content as string (never raw JSON).

        Handles both legacy format (need/purpose) and new format (summary/detail).

        Args:
            content: Purpose content dictionary
            full: If True, show full content without truncation
            created_at: ISO timestamp when purpose was created (P12: Temporal Attribution)

        Returns:
            Formatted purpose string
        """
        symbols = self.symbols
        lines = []

        # Extract main purpose text
        if 'summary' in content:
            purpose_text = content['summary']
        elif 'purpose' in content:
            purpose_text = content['purpose']
        else:
            # Fallback: try to extract something readable
            purpose_text = generate_summary(str(content.get('goal', content.get('what', ''))), full=full)
            if not purpose_text:
                purpose_text = "Purpose defined"

        # Extract need if present
        need_text = content.get('need')

        # P12: Time always shown
        time_str = format_timestamp(created_at) if created_at else ""
        time_suffix = f" ({time_str})" if time_str else ""

        # Format with proper structure
        if need_text:
            lines.append(f"Need: {need_text}")
            lines.append(f"  {symbols.tree_end} Purpose: {purpose_text}{time_suffix}")
        else:
            lines.append(f"{symbols.purpose} Purpose: {purpose_text}{time_suffix}")

        # Show detail fields if present (indented)
        detail = content.get('detail', {})
        if isinstance(detail, dict):
            goal = detail.get('goal')
            success = detail.get('success_criteria')
            if goal:
                lines.append(f"    Goal: {generate_summary(goal, full=full)}")
            if success:
                lines.append(f"    Success: {generate_summary(success, full=full)}")

        return "\n".join(lines)

    def _count_pending_proposals(self) -> int:
        """
        Count proposals awaiting confirmation.

        STRUCTURE_PROPOSED events without matching ARTIFACT_CONFIRMED
        and without PROPOSAL_REJECTED.
        These are AI insights the user hasn't reviewed yet.
        """
        proposed = self.events.read_by_type(EventType.STRUCTURE_PROPOSED)
        if not proposed:
            return 0

        # Get all confirmed proposal IDs
        confirmed_ids = set()
        for event in self.events.read_by_type(EventType.ARTIFACT_CONFIRMED):
            proposal_id = event.data.get('proposal_id', '')
            if proposal_id:
                confirmed_ids.add(proposal_id)

        # Get all rejected proposal IDs
        rejected_ids = set()
        for event in self.events.read_by_type(EventType.PROPOSAL_REJECTED):
            proposal_id = event.data.get('proposal_id', '')
            if proposal_id:
                rejected_ids.add(proposal_id)

        # Count unconfirmed and non-rejected proposals
        pending = sum(1 for p in proposed if p.id not in confirmed_ids and p.id not in rejected_ids)
        return pending

    def _get_scan_findings_summary(self) -> dict:
        """
        Get summary of cached scan findings.

        Reads .babel/scan/<type>/findings.json and exclusions.json to provide
        counts without running a new scan. Returns empty dict if no cached findings.

        Returns:
            dict: {scan_type: {"total": N, "pending": N, "excluded": N}}
        """
        import json

        scan_dir = self.babel_dir / "scan"
        if not scan_dir.exists():
            return {}

        summary = {}
        for type_dir in scan_dir.iterdir():
            if not type_dir.is_dir():
                continue

            scan_type = type_dir.name
            findings_file = type_dir / "findings.json"
            exclusions_file = type_dir / "exclusions.json"

            if not findings_file.exists():
                continue

            try:
                with open(findings_file) as f:
                    findings_data = json.load(f)

                findings = findings_data.get("findings", [])
                total = len(findings)

                # Load exclusions
                excluded_count = 0
                if exclusions_file.exists():
                    with open(exclusions_file) as f:
                        excl_data = json.load(f)
                    excluded_count = len(excl_data.get("exclusions", {}))

                # Count pending (not resolved, not excluded)
                excl_ids = set(excl_data.get("exclusions", {}).keys()) if exclusions_file.exists() else set()
                pending = 0
                for finding in findings:
                    fid = finding.get("finding_id", "")
                    status = finding.get("status", "pending")
                    # Check if excluded (prefix matching)
                    is_excluded = any(fid.startswith(eid) or eid.startswith(fid) for eid in excl_ids)
                    if status != "resolved" and not is_excluded:
                        pending += 1

                if total > 0:
                    summary[scan_type] = {
                        "total": total,
                        "pending": pending,
                        "excluded": excluded_count
                    }
            except (json.JSONDecodeError, IOError):
                continue

        return summary

    def _format_scan_type_summary(self, scan_type: str, pending: int, excluded: int) -> str:
        """
        Format self-documenting summary for a scan type.

        Follows the principle: every message should be understandable
        by someone with zero prior context.

        Returns:
            Formatted scan summary string
        """
        # Scan type descriptions and workflows (self-documenting)
        # Manual sections: [SCN-03] = Scan Types (detailed workflows), [SCN-06] = AI Operator Guide
        scan_info = {
            "clean": {
                "description": f"{pending} potentially unused imports found by ruff",
                "status": "pending verification (hybrid parser check)",
                "actions": [
                    ("babel scan --type clean --verify", "auto-classify true/false positives"),
                    ("babel scan --type clean --list", "review manually"),
                ],
                "manual": (".babel/manual/scan.md", "[SCN-03]"),  # Detailed clean workflow
            },
            "health": {
                "description": f"{pending} project health concern(s) detected",
                "status": "awaiting review",
                "actions": [
                    ("babel scan --type health", "view details"),
                ],
                "manual": (".babel/manual/scan.md", "[SCN-06]"),
            },
            "security": {
                "description": f"{pending} potential security issue(s) found",
                "status": "awaiting review",
                "actions": [
                    ("babel scan --type security", "view details"),
                ],
                "manual": (".babel/manual/scan.md", "[SCN-06]"),
            },
            "architecture": {
                "description": f"{pending} architectural pattern issue(s) detected",
                "status": "awaiting review",
                "actions": [
                    ("babel scan --type architecture", "view details"),
                ],
                "manual": (".babel/manual/scan.md", "[SCN-06]"),
            },
            "performance": {
                "description": f"{pending} performance concern(s) found",
                "status": "awaiting review",
                "actions": [
                    ("babel scan --type performance", "view details"),
                ],
                "manual": (".babel/manual/scan.md", "[SCN-06]"),
            },
            "dependencies": {
                "description": f"{pending} dependency issue(s) detected",
                "status": "awaiting review",
                "actions": [
                    ("babel scan --type dependencies", "view details"),
                ],
                "manual": (".babel/manual/scan.md", "[SCN-06]"),
            },
        }

        info = scan_info.get(scan_type, {
            "description": f"{pending} finding(s) for {scan_type}",
            "status": "pending",
            "actions": [
                (f"babel scan --type {scan_type} --list", "view details"),
            ],
            "manual": (".babel/manual/scan.md", "[SCN-06]"),
        })

        excl_note = f" ({excluded} excluded as false positives)" if excluded > 0 else ""

        lines = []
        lines.append(f"  {info['description']}{excl_note}")
        lines.append(f"  Status: {info['status']}")
        for cmd, desc in info["actions"]:
            lines.append(f"  → Run: {cmd} ({desc})")
        # Manual reference so operators know where to read before acting
        manual_path, manual_section = info["manual"]
        lines.append(f"  Manual: {manual_path} {manual_section}")

        return "\n".join(lines)

    def _compute_project_health(
        self,
        open_tensions: int,
        validation_stats: dict,
        open_questions: int,
        coherence_result=None,
        principle_result=None
    ) -> dict:
        """
        Compute project health based on maturity, alignment, confusion, and principles.

        Multi-factor assessment:
        - Maturity: artifact count, connection density
        - Alignment: validated decisions, no tensions, coherence
        - Confusion: open tensions, unvalidated, questions
        - Principles: P1-P11 framework alignment (Option 4)

        Returns dict with: indicator, level, suggestion
        """
        symbols = self.symbols

        # === MATURITY SIGNALS ===
        stats = self.graph.stats()
        artifact_count = stats['nodes']
        connection_count = stats['edges']
        connection_ratio = connection_count / max(artifact_count, 1)

        maturity_score = 0
        if artifact_count >= 30:
            maturity_score += 3
        elif artifact_count >= 15:
            maturity_score += 2
        elif artifact_count >= 5:
            maturity_score += 1

        if connection_ratio >= 0.8:
            maturity_score += 1

        # === CONFUSION SIGNALS ===
        confusion_score = 0

        # Open tensions increase confusion
        if open_tensions > 3:
            confusion_score += 3
        elif open_tensions > 1:
            confusion_score += 2
        elif open_tensions > 0:
            confusion_score += 1

        # Unvalidated decisions increase confusion
        partial = validation_stats.get("partial", 0)
        if partial > 3:
            confusion_score += 2
        elif partial > 0:
            confusion_score += 1

        # Open questions increase confusion (but less severely)
        if open_questions > 3:
            confusion_score += 1

        # Coherence issues increase confusion
        if coherence_result and coherence_result.has_issues:
            confusion_score += 2

        # === ALIGNMENT SIGNALS ===
        alignment_score = 0

        # Validated decisions increase alignment
        validated = validation_stats.get("validated", 0)
        if validated > 5:
            alignment_score += 3
        elif validated > 2:
            alignment_score += 2
        elif validated > 0:
            alignment_score += 1

        # No tensions is good
        if open_tensions == 0:
            alignment_score += 1

        # Coherence passing is good
        if coherence_result and not coherence_result.has_issues:
            alignment_score += 1

        # Principle alignment (Option 4: embed in health)
        if principle_result:
            if principle_result.violation_count > 0:
                confusion_score += 2  # Violations increase confusion
            elif principle_result.warning_count > 2:
                confusion_score += 1  # Many warnings add minor confusion
            if principle_result.score >= 0.8:
                alignment_score += 2  # High principle alignment is good
            elif principle_result.score >= 0.5:
                alignment_score += 1

        # === DETERMINE HEALTH LEVEL ===
        # High confusion overrides everything
        if confusion_score >= 4:
            return {
                "indicator": symbols.health_high_confusion,
                "level": "Confused",
                "suggestion": "Consider resolving tensions before new decisions."
            }

        # Moderate confusion needs attention
        if confusion_score >= 2:
            suggestion = None
            if open_tensions > 0:
                suggestion = f"{open_tensions} open tension(s) to address."
            return {
                "indicator": symbols.health_moderate,
                "level": "Moderate",
                "suggestion": suggestion
            }

        # Well aligned with good validation
        if alignment_score >= 3:
            return {
                "indicator": symbols.health_aligned,
                "level": "Aligned",
                "suggestion": "Good position to move forward."
            }

        # Growing - has maturity but needs validation
        if maturity_score >= 2:
            # Count unvalidated decisions
            decision_nodes = len(self.graph.get_nodes_by_type('decision'))

            suggestion = None
            if decision_nodes > 0 and validated == 0:
                suggestion = f"{decision_nodes} decision(s) not yet validated.\n  {symbols.arrow} babel endorse <id>"

            return {
                "indicator": symbols.health_moderate,
                "level": "Growing",
                "suggestion": suggestion
            }

        # Starting - few artifacts
        return {
            "indicator": symbols.health_starting,
            "level": "Starting",
            "suggestion": "Capture decisions as you make them."
        }

    def _format_git_sync_health(self, git_integration: GitIntegration, full: bool = False) -> str:
        """
        Format detailed git-babel sync health as string.

        Displays:
        - Number of decision-to-commit links
        - Unlinked decisions (intent without implementation)
        - Unlinked commits (implementation without intent)

        Returns:
            Formatted git sync health string
        """
        symbols = self.symbols
        lines = []

        lines.append(f"{symbols.purpose} Git-Babel Sync Health:")

        # Get commit links
        commit_links = CommitLinkStore(self.babel_dir)
        all_links = commit_links.all_links()
        linked_decision_ids = commit_links.get_linked_decision_ids()
        linked_commit_shas = commit_links.get_linked_commit_shas()

        lines.append(f"  Decision-commit links: {len(all_links)}")

        # Count unlinked decisions (non-deprecated)
        unlinked_decisions = 0
        for node_type in ['decision', 'constraint', 'principle']:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                node_id = node.event_id or node.id
                # Check if linked
                is_linked = any(
                    node_id.startswith(lid) or lid.startswith(node_id)
                    for lid in linked_decision_ids
                )
                if not is_linked:
                    # Skip deprecated
                    if not self._cli._is_deprecated(node.id):
                        unlinked_decisions += 1

        if unlinked_decisions > 0:
            lines.append(f"  {symbols.tension} Unlinked decisions: {unlinked_decisions}")
            if full:
                lines.append(f"    (Intent captured but not linked to commits)")

        # Count unlinked recent commits
        output = git_integration._run_git([
            "log", "-20", "--format=%H|%s", "--no-merges"
        ])
        unlinked_commits = 0
        if output:
            for line in output.strip().split('\n'):
                if '|' not in line:
                    continue
                sha, message = line.split('|', 1)
                is_linked = any(
                    sha.startswith(lid) or lid.startswith(sha)
                    for lid in linked_commit_shas
                )
                if not is_linked:
                    # Skip trivial commits
                    if not message.lower().startswith(('merge', 'bump version')):
                        unlinked_commits += 1

        if unlinked_commits > 0:
            lines.append(f"  {symbols.tension} Unlinked commits (last 20): {unlinked_commits}")
            if full:
                lines.append(f"    (Implementation without documented intent)")

        # Sync health assessment
        if unlinked_decisions == 0 and unlinked_commits == 0:
            lines.append(f"  {symbols.check_pass} Intent and state are well connected.")
        elif unlinked_decisions > 5 or unlinked_commits > 5:
            lines.append(f"  {symbols.arrow} Run: babel gaps (see all gaps)")
            lines.append(f"  {symbols.arrow} Run: babel suggest-links (AI suggestions)")
        else:
            lines.append(f"  {symbols.arrow} Run: babel gaps (detailed view)")

        return "\n".join(lines)

    def _collect_status_data(self, full: bool = False, git: bool = False) -> dict:
        """
        Collect status data as structured dict for JSON rendering.

        Returns dict with all status metrics suitable for machine consumption.
        Used by --format json for AI operator token efficiency.
        """
        stats = self.graph.stats()
        shared_count, local_count = self.events.count_by_scope()

        # Core metrics
        data = {
            "project": str(self.project_dir),
            "events": {
                "total": shared_count + local_count,
                "shared": shared_count,
                "local": local_count
            },
            "artifacts": stats["nodes"],
            "connections": stats["edges"],
            "orphans": stats["orphans"]
        }

        # Init memos (code only - ID hidden behind alias)
        codec = self._cli.codec
        init_memos = self._cli.memos.list_init_memos()
        if init_memos:
            data["init_memos"] = [
                {"code": codec.encode(m.id), "content": m.content}
                for m in init_memos
            ]

        # Purposes (code only - ID hidden behind alias)
        purposes = self.graph.get_nodes_by_type('purpose')
        if purposes:
            data["purposes"] = [
                {
                    "code": codec.encode(p.id),
                    "summary": p.content.get("summary") or p.content.get("purpose", ""),
                    "goal": p.content.get("detail", {}).get("goal") if isinstance(p.content.get("detail"), dict) else None
                }
                for p in purposes
            ]

        # Coherence
        last_result = self.coherence.get_last_result()
        if last_result:
            # timestamp may be str or datetime, handle both
            ts = last_result.timestamp if hasattr(last_result, 'timestamp') else None
            if ts and hasattr(ts, 'isoformat'):
                ts = ts.isoformat()
            data["coherence"] = {
                "checked": True,
                "has_issues": last_result.has_issues,
                "timestamp": ts
            }

        # Commits
        commits = self.events.read_by_type(EventType.COMMIT_CAPTURED)
        data["commits_captured"] = len(commits) if commits else 0

        # Tensions
        open_tensions = self.tensions.count_open()
        data["open_tensions"] = open_tensions

        # Validation
        validation_stats = self.validation.stats()
        data["validation"] = {
            "tracked": validation_stats.get("tracked", 0),
            "validated": validation_stats.get("validated", 0),
            "partial": validation_stats.get("partial", 0),
            "groupthink_risk": validation_stats.get("groupthink_risk", 0),
            "unreviewed_risk": validation_stats.get("unreviewed_risk", 0)
        }

        # Questions
        data["open_questions"] = self.questions.count_open()

        # Scan findings (cached)
        scan_summary = self._get_scan_findings_summary()
        if scan_summary:
            data["scan_findings"] = scan_summary

        # Pending proposals
        data["pending_proposals"] = self._count_pending_proposals()

        # Extraction queue
        if self.extractor.queue:
            data["extraction_queue"] = self.extractor.queue.count()

        # Provider status
        data["provider"] = get_provider_status(self.config)

        # Git sync (if requested)
        if git:
            git_integration = GitIntegration(self.project_dir)
            if git_integration.is_git_repo:
                commit_links = CommitLinkStore(self.babel_dir)
                data["git_sync"] = {
                    "hooks_installed": git_integration.hooks_status() == "Installed",
                    "decision_commit_links": commit_links.count()
                }

        # Health
        principle_checker = PrincipleChecker(
            graph=self.graph,
            validation=self.validation,
            questions=self.questions,
            vocabulary=self.vocabulary
        )
        principle_result = principle_checker.check_all()
        health = self._compute_project_health(
            open_tensions=open_tensions,
            validation_stats=validation_stats,
            open_questions=data["open_questions"],
            coherence_result=last_result,
            principle_result=principle_result
        )
        data["health"] = {
            "level": health["level"],
            "principles_satisfied": principle_result.satisfied_count,
            "principles_total": principle_result.total_applicable
        }

        # Note: codes are deterministic (hash-based) - no legend needed
        # Any code can be resolved by computing hash(id) for candidates

        return data


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

def register_parser(subparsers):
    """Register status command parser."""
    p = subparsers.add_parser(
        'status',
        help='Show project status and health',
        description='Display project overview: events, artifacts, recent purposes, '
                    'coherence status, and health assessment. Purposes are shown in '
                    'time order (newest first) with configurable limit.'
    )
    p.add_argument('--full', action='store_true',
                   help='Show full content without truncation')
    p.add_argument('--git', action='store_true',
                   help='Show git-babel sync health (decision↔commit links)')
    p.add_argument('--force', action='store_true',
                   help='Bypass cache and force fresh data reads')
    p.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json', 'summary'],
                   help='Output format (overrides config)')
    p.add_argument('--limit-purposes', type=int, default=10, metavar='N',
                   help='Show N most recent purposes (default: 10). '
                        'Use 0 to show all. Older purposes available via: babel list purposes')
    return p


def handle(cli, args):
    """Handle status command dispatch."""
    force = getattr(args, 'force', False)
    format_arg = getattr(args, 'format', 'auto')
    limit_purposes = getattr(args, 'limit_purposes', 10)
    cli._status_cmd.status(full=args.full, git=args.git, force=force,
                           format=format_arg, limit_purposes=limit_purposes)
