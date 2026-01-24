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
from ..presentation.symbols import truncate, SUMMARY_LENGTH, safe_print
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

        # For other formats, use existing print-based output (backward compatible)
        stats = self.graph.stats()
        shared_count, local_count = self.events.count_by_scope()
        total_events = shared_count + local_count
        symbols = self.symbols

        # Show init memos first (foundational instructions for AI operators)
        init_memos = self._cli.memos.list_init_memos()
        if init_memos:
            print(f"\n{symbols.purpose} Init Instructions (read before work):")
            for memo in init_memos:
                content_display = truncate(memo.content, SUMMARY_LENGTH)
                safe_print(f"  {symbols.arrow} {content_display}")
            print()

        print(f"Project: {self.project_dir}")
        print(f"Events: {total_events} ({symbols.shared} {shared_count} shared, {symbols.local} {local_count} local)")
        print(f"Artifacts: {stats['nodes']}")
        print(f"Connections: {stats['edges']}")

        orphans = stats['orphans']
        if orphans > 0:
            print(f"Unlinked: {orphans} (isolated - can't inform 'why' queries)")
            if full:
                print(f"  Impact: Knowledge silos form, reasoning chains break")
                print(f"  Action: babel link <id> --to <related-id>")

        # Show purposes with symbols (formatted, never raw JSON)
        # Use time-ordered query for recent purposes (P6: token efficiency)
        all_purposes_count = len(self.graph.get_nodes_by_type('purpose'))
        if limit_purposes > 0:
            purposes = self.graph.get_nodes_by_type_recent('purpose', limit=limit_purposes)
        else:
            purposes = self.graph.get_nodes_by_type('purpose')
        if purposes:
            for p in purposes:
                self._display_purpose(p.content, full=full)
            # Show truncation hint if there are more purposes
            if limit_purposes > 0 and all_purposes_count > limit_purposes:
                print(f"\n  ({all_purposes_count - limit_purposes} older purposes hidden)")
                print(f"  {symbols.arrow} babel list purposes --all")

        # Show coherence status
        last_result = self.coherence.get_last_result()
        if last_result:
            print(f"\n{format_coherence_status(last_result, symbols, full=full)}")
            if last_result.has_issues:
                print(f"\n  Review with: babel coherence")
        elif purposes:
            print(f"\nCoherence: not yet checked")
            print(f"  Run: babel coherence")

        # Show commit count
        commits = self.events.read_by_type(EventType.COMMIT_CAPTURED)
        if commits:
            print(f"\nCommits captured: {len(commits)}")

        # Show open tensions (P4)
        open_tensions = self.tensions.count_open()
        if open_tensions > 0:
            print(f"\n{symbols.tension} Open Tensions: {open_tensions}")
            print(f"  Run: babel tensions")

        # Show validation status (P9)
        validation_stats = self.validation.stats()
        if validation_stats["tracked"] > 0:
            partial = validation_stats["partial"]
            validated = validation_stats["validated"]
            if partial > 0:
                # Clarify: "partial" means missing consensus OR evidence (P5 requires both)
                print(f"\n{symbols.consensus_only} Validation: {validated} validated, {partial} need review (require both consensus + evidence)")
                if validation_stats["groupthink_risk"] > 0:
                    print(f"  {symbols.check_warn} {validation_stats['groupthink_risk']} consensus-only (agreed but untested - groupthink risk)")
                if validation_stats["unreviewed_risk"] > 0:
                    print(f"  {symbols.check_warn} {validation_stats['unreviewed_risk']} evidence-only (tested but not endorsed)")
                print(f"  Run: babel validation")
                if full:
                    print(f"  Impact: Unvalidated decisions may be challenged later")
                    print(f"  Action: babel endorse <id> (add consensus) or babel evidence-decision <id> (add evidence)")
            elif validated > 0:
                print(f"\n{symbols.validated} Validation: {validated} decisions validated (have both consensus + evidence)")

        # Show open questions (P10: acknowledged unknowns)
        open_questions_count = self.questions.count_open()
        if open_questions_count > 0:
            print(f"\n? Open Questions: {open_questions_count}")
            print(f"  (Acknowledged unknowns -- not failures)")
            print(f"  Run: babel questions")

        # Show LLM status
        provider_status = get_provider_status(self.config)
        print(f"\nExtraction: {provider_status}")

        # Show git hooks status
        git_integration = GitIntegration(self.project_dir)
        if git_integration.is_git_repo:
            hooks_status = git_integration.hooks_status()
            print(f"Git hooks: {hooks_status}")

            # Show git-babel sync health if --git flag or always show summary
            if git:
                self._show_git_sync_health(git_integration, full=full)
            else:
                # Just show a brief summary
                commit_links = CommitLinkStore(self.babel_dir)
                link_count = commit_links.count()
                if link_count > 0:
                    print(f"Decision-commit links: {link_count}")
                    print(f"  Run: babel status --git (detailed sync health)")

        # Show pending proposals (STRUCTURE_PROPOSED without ARTIFACT_CONFIRMED)
        pending_proposals = self._count_pending_proposals()
        if pending_proposals > 0:
            print(f"Pending: {pending_proposals} proposal(s) (AI insights awaiting your confirmation)")
            print(f"  Run: babel review")
            if full:
                print(f"  Impact: Unconfirmed proposals are lost when session ends")
                print(f"  Action: Review and confirm valuable insights")

        # Show extraction queue (offline LLM requests)
        if self.extractor.queue:
            queued = self.extractor.queue.count()
            if queued > 0:
                print(f"Queued: {queued} extraction(s) (text awaiting LLM analysis - requires API key)")
                if full:
                    print(f"  Impact: Raw captures exist but structured artifacts not extracted")
                    print(f"  Action: Set API key, then: babel process-queue (interactive) or babel process-queue --batch (AI)")

        # Check principle alignment (P1-P11)
        principle_checker = PrincipleChecker(
            graph=self.graph,
            validation=self.validation,
            questions=self.questions,
            vocabulary=self.vocabulary
        )
        principle_result = principle_checker.check_all()

        # P9: Project health summary (adaptive pace guidance)
        # Now includes principle alignment
        health = self._compute_project_health(
            open_tensions=open_tensions,
            validation_stats=validation_stats,
            open_questions=open_questions_count,
            coherence_result=last_result,
            principle_result=principle_result
        )
        print(f"\n{health['indicator']} Project Health: {health['level']} ({principle_result.satisfied_count}/{principle_result.total_applicable} principles)")
        if health['suggestion']:
            print(f"  {health['suggestion']}")

        # Show principle issues (compact unless --full)
        # With --full, always show principle breakdown
        if full or principle_result.warning_count > 0 or principle_result.violation_count > 0:
            print(f"\n{format_principles_summary(principle_result, symbols, full=full)}")

        print("\nReady.")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("status", {
            "has_pending": pending_proposals > 0,
            "has_high_unlinked": orphans > 50,  # Likely from map indexing garbage
            "has_unlinked": orphans > 0 and orphans <= 50,
            "has_tensions": open_tensions > 0,
            "has_questions": open_questions_count > 0,
            "has_partial_validation": validation_stats.get("partial", 0) > 0,
            "healthy": health['level'] in ("Aligned", "Growing"),
        })

    def _display_purpose(self, content: dict, full: bool = False):
        """
        Display purpose content in readable format (never raw JSON).

        Handles both legacy format (need/purpose) and new format (summary/detail).

        Args:
            content: Purpose content dictionary
            full: If True, show full content without truncation
        """
        symbols = self.symbols

        # Extract main purpose text
        if 'summary' in content:
            purpose_text = content['summary']
        elif 'purpose' in content:
            purpose_text = content['purpose']
        else:
            # Fallback: try to extract something readable
            purpose_text = truncate(str(content.get('goal', content.get('what', ''))), SUMMARY_LENGTH, full)
            if not purpose_text:
                purpose_text = "Purpose defined"

        # Extract need if present
        need_text = content.get('need')

        # Display with proper formatting
        if need_text:
            print(f"\nNeed: {need_text}")
            print(f"  {symbols.tree_end} Purpose: {purpose_text}")
        else:
            print(f"\n{symbols.purpose} Purpose: {purpose_text}")

        # Show detail fields if present (indented)
        detail = content.get('detail', {})
        if isinstance(detail, dict):
            goal = detail.get('goal')
            success = detail.get('success_criteria')
            if goal:
                print(f"    Goal: {truncate(goal, SUMMARY_LENGTH, full)}")
            if success:
                print(f"    Success: {truncate(success, SUMMARY_LENGTH, full)}")

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

    def _show_git_sync_health(self, git_integration: GitIntegration, full: bool = False):
        """
        Show detailed git-babel sync health.

        Displays:
        - Number of decision-to-commit links
        - Unlinked decisions (intent without implementation)
        - Unlinked commits (implementation without intent)
        """
        symbols = self.symbols

        print(f"\n{symbols.purpose} Git-Babel Sync Health:")

        # Get commit links
        commit_links = CommitLinkStore(self.babel_dir)
        all_links = commit_links.all_links()
        linked_decision_ids = commit_links.get_linked_decision_ids()
        linked_commit_shas = commit_links.get_linked_commit_shas()

        print(f"  Decision-commit links: {len(all_links)}")

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
            print(f"  {symbols.tension} Unlinked decisions: {unlinked_decisions}")
            if full:
                print(f"    (Intent captured but not linked to commits)")

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
            print(f"  {symbols.tension} Unlinked commits (last 20): {unlinked_commits}")
            if full:
                print(f"    (Implementation without documented intent)")

        # Sync health assessment
        if unlinked_decisions == 0 and unlinked_commits == 0:
            print(f"  {symbols.check_pass} Intent and state are well connected.")
        elif unlinked_decisions > 5 or unlinked_commits > 5:
            print(f"\n  {symbols.arrow} Run: babel gaps (see all gaps)")
            print(f"  {symbols.arrow} Run: babel suggest-links (AI suggestions)")
        else:
            print(f"\n  {symbols.arrow} Run: babel gaps (detailed view)")

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
