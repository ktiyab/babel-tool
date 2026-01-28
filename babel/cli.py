"""
CLI -- Command interface (MVP interface)

Quiet librarian: Present when needed, invisible otherwise.
No jargon (HC6). Graceful dormancy.

Git-informed scalability:
- Refs for O(1) lookup
- Lazy loading (only what's needed)
- Token-efficient by default

Hybrid Collaboration:
- Local by default (low friction)
- --share flag for team decisions
- babel share <id> to promote
- babel sync after git pull
"""

import argparse
import atexit
import os
from pathlib import Path
from typing import Optional

from .core.events import DualEventStore, EventType
from .core.graph import GraphStore, Node
from .services.extractor import Extractor
from .config import ConfigManager
from .services.providers import get_provider, LLMResponse
from .presentation.formatters import get_node_summary, generate_summary
from .presentation.symbols import get_symbols, safe_print
from .tracking.coherence import CoherenceChecker
from .core.refs import RefStore
from .core.loader import LazyLoader
from .core.vocabulary import Vocabulary
from .services.scanner import Scanner
from .tracking.tensions import TensionTracker
from .tracking.validation import ValidationTracker
from .tracking.ambiguity import QuestionTracker
from .core.resolver import IDResolver, ResolveStatus
from .presentation.codec import IDCodec
from .commands.review import ReviewCommand
from .commands.capture import CaptureCommand
from .commands.why import WhyCommand
from .commands.status import StatusCommand
from .commands.history import HistoryCommand
from .commands.questions import QuestionsCommand
from .commands.validation import ValidationCommand
from .commands.tensions import TensionsCommand
from .commands.coherence import CoherenceCommand
from .commands.check import CheckCommand
from .commands.git_cmd import GitCommand
from .commands.deprecate import DeprecateCommand
from .commands.init_cmd import InitCommand
from .commands.link import LinkCommand
from .commands.config_cmd import ConfigCommand
from .commands.prompt import PromptCommand
from .commands.map_cmd import MapCommand
from .commands.list_cmd import ListCommand
from .commands.memo_cmd import MemoCommand
from .commands.suggest_links import SuggestLinksCommand
from .commands.gaps import GapsCommand
from .commands.skill_cmd import SkillCommand
from .commands.gather_cmd import GatherCommand
from .preferences import MemoManager
from .content import HELP_TEXT, PRINCIPLES_TEXT
from .orchestrator import get_orchestrator
from . import __version__


class IntentCLI:
    """Command-line interface for Babel intent preservation tool."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.babel_dir = self.project_dir / ".babel"
        
        # Use DualEventStore for collaboration
        self.events = DualEventStore(self.project_dir)
        self.graph = GraphStore(self.babel_dir / "graph.db")
        self.config_manager = ConfigManager(self.project_dir)
        self.config = self.config_manager.load()
        
        # Initialize refs for O(1) lookup
        self.refs = RefStore(self.babel_dir)
        
        # Initialize vocabulary for semantic understanding
        self.vocabulary = Vocabulary(self.babel_dir)
        
        # Initialize symbols based on config
        self.symbols = get_symbols(self.config.display.symbols)

        # Initialize extractor with configured provider and LLM callbacks
        provider = get_provider(self.config)
        self.provider = provider  # Store for scanner
        self.extractor = Extractor(
            provider=provider,
            queue_path=self.babel_dir / "extraction_queue.jsonl",
            on_llm_start=self._on_llm_start,
            on_llm_complete=self._on_llm_complete
        )
        
        # Initialize lazy loader for token efficiency (with vocabulary)
        self.loader = LazyLoader(self.events, self.refs, self.graph, self.vocabulary)
        
        # Initialize coherence checker
        self.coherence = CoherenceChecker(
            events=self.events,
            graph=self.graph,
            config=self.config,
            provider=provider
        )
        
        # Initialize scanner for technical advice
        self.scanner = Scanner(
            events=self.events,
            graph=self.graph,
            provider=provider,
            loader=self.loader,
            vocabulary=self.vocabulary,
            cache_path=self.babel_dir / "scan_cache.json"
        )
        
        # Initialize tension tracker for disagreement handling (P4)
        self.tensions = TensionTracker(self.events)
        
        # Initialize validation tracker for dual-test truth (P9)
        self.validation = ValidationTracker(self.events)
        
        # Initialize question tracker for ambiguity management (P10)
        self.questions = QuestionTracker(self.events)

        # Initialize ID resolver for fuzzy artifact lookup
        self.resolver = IDResolver(self.graph)

        # Initialize session-scoped ID codec for short aliases (AI operator ergonomics)
        self.codec = IDCodec()

        # Initialize memo manager for user preferences (P6: token efficiency)
        self.memos = MemoManager(self.babel_dir)

        # Initialize task orchestrator for parallelization (lazy, respects config)
        self._orchestrator = None  # Lazy init on first use
        atexit.register(self._shutdown_orchestrator)

        # Initialize command handlers (modular architecture)
        self._review_cmd = ReviewCommand(self)
        self._capture_cmd = CaptureCommand(self)
        self._why_cmd = WhyCommand(self)
        self._status_cmd = StatusCommand(self)
        self._history_cmd = HistoryCommand(self)
        self._questions_cmd = QuestionsCommand(self)
        self._validation_cmd = ValidationCommand(self)
        self._tensions_cmd = TensionsCommand(self)
        self._coherence_cmd = CoherenceCommand(self)
        self._check_cmd = CheckCommand(self)
        self._git_cmd = GitCommand(self)
        self._deprecate_cmd = DeprecateCommand(self)
        self._init_cmd = InitCommand(self)
        self._link_cmd = LinkCommand(self)
        self._config_cmd = ConfigCommand(self)
        self._prompt_cmd = PromptCommand(self)
        self._map_cmd = MapCommand(self)
        self._list_cmd = ListCommand(self)
        self._memo_cmd = MemoCommand(self)
        self._suggest_links_cmd = SuggestLinksCommand(self)
        self._gaps_cmd = GapsCommand(self)
        self._skill_cmd = SkillCommand(self)
        self._gather_cmd = GatherCommand(self)

        # Auto-sync and index on startup (graceful, no friction)
        self._auto_sync()
        self._ensure_indexed()

    def _on_llm_start(self):
        """Callback when LLM call begins — show thinking indicator."""
        print(f"{self.symbols.llm_thinking} Analyzing...", end="", flush=True)

    def _on_llm_complete(self, response: LLMResponse):
        """Callback when LLM call completes — show token usage."""
        token_info = response.format_tokens(self.symbols)
        print(f"\r{self.symbols.llm_done} Done  {token_info}")

    @property
    def orchestrator(self):
        """
        Get task orchestrator for parallel execution (lazy initialization).

        Returns global orchestrator instance, created on first access.
        Configuration loaded from environment variables.
        """
        if self._orchestrator is None:
            self._orchestrator = get_orchestrator()
        return self._orchestrator

    def _shutdown_orchestrator(self):
        """Shutdown orchestrator on process exit (atexit handler)."""
        if self._orchestrator is not None:
            try:
                self._orchestrator.shutdown(wait=True)
            except Exception:
                pass  # Fail silently on shutdown

    def _auto_sync(self):
        """Auto-sync on startup if needed."""
        try:
            result = self.events.sync()
            if result["deduplicated"] > 0:
                print(f"Synced: {result['deduplicated']} duplicate(s) resolved")
                self._rebuild_graph()
                self._rebuild_refs()
        except Exception:
            pass  # Fail silently on auto-sync
    
    def _ensure_indexed(self):
        """Ensure all events are indexed in refs."""
        try:
            self.loader.ensure_indexed()
        except Exception:
            pass  # Fail silently
    
    def _rebuild_refs(self):
        """Rebuild refs index from events."""
        try:
            self.refs.rebuild(self.events.read_all())
        except Exception:
            pass  # Fail silently
    
    def _rebuild_graph(self):
        """Rebuild graph from events."""
        # Clear and rebuild
        self.graph = GraphStore(self.babel_dir / "graph.db")
        for event in self.events.read_all():
            try:
                self.graph._project_event(event)
            except Exception:
                continue

    # NOTE: Legacy why cache methods removed - now in commands/why.py
    # NOTE: _display_purpose() removed - now in commands/status.py

    def _get_active_purpose(self) -> Optional[Node]:
        """
        Get the active (most recent) purpose node.

        Returns the most recently created purpose, which is considered
        the current working context for auto-linking decisions.
        """
        purposes = self.graph.get_nodes_by_type('purpose')
        if not purposes:
            return None
        # Return the last one (most recent)
        return purposes[-1]

    def init(self, purpose: str, need: str = None):
        """Initialize project with purpose. Delegates to InitCommand."""
        return self._init_cmd.init(purpose, need=need)

    def _install_system_prompt(self):
        """Install system prompt. Delegates to InitCommand."""
        return self._init_cmd._install_system_prompt()

    def _create_minimal_system_prompt(self, path: Path):
        """Create minimal system prompt. Delegates to InitCommand."""
        return self._init_cmd._create_minimal_system_prompt(path)

    def prompt(self):
        """Output system prompt. Delegates to InitCommand."""
        return self._init_cmd.prompt()

    def help(self):
        """Show comprehensive help for all commands."""
        print(HELP_TEXT)

    def principles(self):
        """
        Show Babel's core principles (P11: Framework Self-Application).

        The framework applies to its own discussion.
        Use this to check if your usage aligns with Babel's principles.
        """
        print(PRINCIPLES_TEXT)

    def capture(self, text: str, auto_extract: bool = True, share: bool = False, domain: str = None,
                uncertain: bool = False, uncertainty_reason: str = None, batch_mode: bool = False):
        """
        Capture conversation/thought (P3 + P10 compliant).

        Delegates to CaptureCommand for implementation.

        Args:
            text: Content to capture
            auto_extract: Run extraction (default True)
            share: Share with team (default False - local only)
            domain: Expertise domain (P3: bounded expertise attribution)
            uncertain: Mark as uncertain/provisional (P10: holding ambiguity)
            uncertainty_reason: Why this is uncertain
            batch_mode: Queue proposals for later review (HC2)
        """
        return self._capture_cmd.capture(
            text=text,
            auto_extract=auto_extract,
            share=share,
            domain=domain,
            uncertain=uncertain,
            uncertainty_reason=uncertainty_reason,
            batch_mode=batch_mode
        )

    # NOTE: Legacy capture methods removed - now in commands/capture.py

    def capture_spec(self, need_id: str, spec_text: str, batch_mode: bool = False):
        """
        Capture specification for an existing need.

        Enriches a need with structured implementation plan (OBJECTIVE, ADD, MODIFY, etc.).
        Creates SPECIFICATION_ADDED event linked to the need (HC1: append-only).

        Args:
            need_id: ID of the need to enrich
            spec_text: Specification text (structured or freeform)
            batch_mode: Queue for later review (HC2)
        """
        return self._capture_cmd.capture_spec(
            need_id=need_id,
            spec_text=spec_text,
            batch_mode=batch_mode
        )

    def review(
        self,
        synthesize: bool = False,
        by_theme: bool = False,
        accept_theme: str = None,
        list_themes: bool = False,
        list_only: bool = False,
        accept_ids: list = None,
        accept_all: bool = False,
        reject_ids: list = None,
        reject_reason: str = None,
        list_rejected: bool = False,
        output_format: str = None
    ):
        """
        Review pending proposals.

        Shows all queued proposals and allows batch confirmation.
        Decisions are auto-registered for validation tracking.

        Non-interactive modes (AI-safe):
            --list: Show proposals without prompting
            --accept <id>: Accept specific proposal(s) by ID
            --accept-all: Accept all proposals at once
            --reject <id>: Reject specific proposal(s) by ID with reason
            --rejected: List rejected proposals with reasons (P8: learn from rejections)

        Synthesis mode (--synthesize):
            AI clusters proposals into themes with impact assessment.
            Human approves themes (directional), not atoms (micro).
            Preserves HC2 at appropriate abstraction level.
        """
        # Delegate to ReviewCommand (modular architecture)
        return self._review_cmd.review(
            synthesize=synthesize,
            by_theme=by_theme,
            accept_theme=accept_theme,
            list_themes=list_themes,
            list_only=list_only,
            accept_ids=accept_ids,
            accept_all=accept_all,
            reject_ids=reject_ids,
            reject_reason=reject_reason,
            list_rejected=list_rejected,
            output_format=output_format
        )

    # NOTE: Legacy review methods removed - now in commands/review.py

    def why(self, query: str = None, commit: str = None):
        """
        Answer a 'why' query with LLM-synthesized explanation.

        Delegates to WhyCommand for implementation.

        P1: Synthesizes complexity into clarity (not just search results).
        P7: Surfaces graph relationships as readable insight.
        P8: With --commit, traces state back to intent.
        """
        if commit:
            return self._why_cmd.why_commit(commit)
        elif query:
            return self._why_cmd.why(query)
        else:
            print("Usage: babel why \"topic\"           (query decisions)")
            print("       babel why --commit <sha>    (why was this commit made?)")

    # NOTE: Legacy why methods removed - now in commands/why.py

    def status(self, full: bool = False, git: bool = False):
        """Show project status. Delegates to StatusCommand."""
        return self._status_cmd.status(full=full, git=git)

    def check(self, repair: bool = False):
        """Verify project integrity. Delegates to CheckCommand."""
        return self._check_cmd.check(repair=repair)

    def coherence_check(self, force: bool = False, full: bool = False, qa: bool = False, resolve: bool = False, batch: bool = False):
        """Check project coherence. Delegates to CoherenceCommand."""
        return self._coherence_cmd.coherence_check(force=force, full=full, qa=qa, resolve=resolve, batch=batch)
    
    def scan(
        self,
        scan_type: str = "health",
        deep: bool = False,
        query: str = None,
        verbose: bool = False
    ):
        """Context-aware technical scan. Delegates to CoherenceCommand."""
        return self._coherence_cmd.scan(scan_type=scan_type, deep=deep, query=query, verbose=verbose)

    def list_artifacts(
        self,
        artifact_type: str = None,
        from_id: str = None,
        orphans: bool = False,
        limit: int = 10,
        offset: int = 0,
        show_all: bool = False,
        filter_pattern: str = None
    ):
        """
        List and discover artifacts. Delegates to ListCommand.

        Graph-aware discovery: browse by type, traverse connections, find orphans.
        """
        if from_id:
            return self._list_cmd.list_from(from_id)
        elif orphans:
            return self._list_cmd.list_orphans(limit=limit, offset=offset, show_all=show_all)
        elif artifact_type:
            return self._list_cmd.list_by_type(artifact_type, limit=limit, offset=offset, show_all=show_all, filter_pattern=filter_pattern)
        else:
            return self._list_cmd.list_overview()

    # =========================================================================
    # P4: Disagreement Handling - Delegates to TensionsCommand
    # =========================================================================

    def challenge(self, target_id: str, reason: str, hypothesis: str = None, test: str = None, domain: str = None):
        """Challenge a decision. Delegates to TensionsCommand."""
        return self._tensions_cmd.challenge(target_id, reason, hypothesis=hypothesis, test=test, domain=domain)

    def evidence(self, challenge_id: str, content: str, evidence_type: str = "observation"):
        """Add evidence to a challenge. Delegates to TensionsCommand."""
        return self._tensions_cmd.evidence(challenge_id, content, evidence_type=evidence_type)

    def resolve(self, challenge_id: str, outcome: str, resolution: str = None, evidence_summary: str = None, force: bool = False):
        """Resolve a challenge. Delegates to TensionsCommand."""
        return self._tensions_cmd.resolve(challenge_id, outcome, resolution=resolution, evidence_summary=evidence_summary, force=force)

    def tensions_cmd(self, verbose: bool = False, full: bool = False, output_format: str = None):
        """Show open tensions. Delegates to TensionsCommand."""
        return self._tensions_cmd.tensions_cmd(verbose=verbose, full=full, output_format=output_format)

    def _compute_project_health(
        self,
        open_tensions: int,
        validation_stats: dict,
        open_questions: int,
        coherence_result=None
    ) -> dict:
        """Compute project health. Delegates to StatusCommand."""
        return self._status_cmd._compute_project_health(
            open_tensions=open_tensions,
            validation_stats=validation_stats,
            open_questions=open_questions,
            coherence_result=coherence_result
        )

    def resolve_id(self, query: str, candidates: list = None, entity_type: str = "item") -> str:
        """
        Universal ID resolution with codec alias support.

        Centralized method for ALL ID resolution. Commands should use this
        instead of local startswith() patterns.

        Resolution order:
        1. Codec alias (AA-BB pattern) - deterministic hash match
        2. Exact match
        3. Prefix match (unambiguous)

        Args:
            query: User input (code alias, full ID, or prefix)
            candidates: List of valid IDs to match against (auto-gathered if None)
            entity_type: For error messages (e.g., "proposal", "memo")

        Returns:
            Resolved full ID, or None if not found/ambiguous
            When candidates=None and query is alias code, returns decoded ID or original
        """
        if not query:
            return None

        query = query.strip()

        # Auto-gather candidates if not provided (convenience for alias-only resolution)
        if candidates is None:
            # Only resolve alias codes when no candidates provided
            if not self.codec.is_short_code(query):
                return query  # Passthrough non-alias input

            # Gather candidates from events and graph nodes
            candidates = []
            candidates.extend(e.id for e in self.events.read_all())
            for node_type in ["decision", "constraint", "purpose", "principle",
                              "requirement", "boundary", "tension"]:
                candidates.extend(n.id for n in self.graph.get_nodes_by_type(node_type))

            # Decode alias and return (passthrough if not found)
            resolved = self.codec.decode(query, candidates)
            return resolved  # Returns original if not found

        # 1. Codec alias resolution (AA-BB pattern)
        if self.codec.is_short_code(query):
            resolved = self.codec.decode(query, candidates)
            if resolved != query:  # Successfully decoded
                return resolved

        # 2. Exact match
        if query in candidates:
            return query

        # 3. Prefix match
        matches = [c for c in candidates if c.startswith(query)]
        if len(matches) == 1:
            return matches[0]

        # Ambiguous or not found
        return None

    def render(self, spec: 'OutputSpec', format: str = 'auto', full: bool = False) -> str:
        """
        Render OutputSpec with automatic codec injection.

        Centralized render method for ALL command output. Commands should use this
        instead of calling output.render() directly.

        This method auto-passes self.codec to enable [AA-BB] alias display.

        Args:
            spec: OutputSpec from command
            format: "auto" | "table" | "list" | "detail" | "summary" | "json"
            full: If True, don't truncate content

        Returns:
            Formatted string ready for printing

        Example:
            spec = OutputSpec(data=[...], shape="table", columns=["ID", "Name"])
            print(self.render(spec))
        """
        from babel.output import render as output_render
        return output_render(
            spec,
            format=format,
            symbols=self.symbols,
            full=full,
            codec=self.codec
        )

    def format_id(self, full_id: str) -> str:
        """
        Format ID for display using codec alias.

        Centralized ID formatting for command output. Use this instead of
        hardcoded `[{id[:8]}]` patterns.

        Args:
            full_id: Full identifier (e.g., "decision_50164a43...")

        Returns:
            Formatted ID: "[AA-BB]" normally, "[AA-BB|50164a43]" in debug mode

        Example:
            # Before: print(f"[{node.id[:8]}] {summary}")
            # After:  print(f"{self._cli.format_id(node.id)} {summary}")
        """
        from babel.output.base import _is_debug_mode

        if not full_id:
            return "[]"

        # Extract short hex (first 8 chars, stripping type prefix)
        short_hex = full_id
        for prefix in ('decision_', 'purpose_', 'constraint_', 'principle_',
                       'requirement_', 'tension_', 'm_', 'c_'):
            if short_hex.startswith(prefix):
                short_hex = short_hex[len(prefix):]
                break
        short_hex = short_hex[:8] if len(short_hex) > 8 else short_hex

        # Format with codec
        code = self.codec.encode(full_id)
        if _is_debug_mode():
            return f"[{code}|{short_hex}]"
        return f"[{code}]"

    def _find_node_by_id(self, node_id: str):
        """Find a graph node by ID prefix (legacy, use _resolve_node for UX)."""
        # Check decisions first (most common target)
        for node_type in ["decision", "constraint", "purpose", "boundary"]:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                if node.id.startswith(node_id):
                    return node
        return None

    def _is_pending_proposal(self, query: str):
        """
        Check if query matches a pending proposal ID.

        Proposals are STRUCTURE_PROPOSED events that haven't been
        confirmed (ARTIFACT_CONFIRMED) or rejected (PROPOSAL_REJECTED).

        Args:
            query: User input (alias code, full ID, or prefix)

        Returns:
            (is_proposal, proposal_event) - True and event if pending proposal found
        """
        # Resolve alias code to raw ID if needed
        resolved_query = self.resolve_id(query)
        if not resolved_query:
            return False, None

        # Get all proposal events
        proposed_events = self.events.read_by_type(EventType.STRUCTURE_PROPOSED)

        # Get confirmed and rejected IDs
        confirmed_events = self.events.read_by_type(EventType.ARTIFACT_CONFIRMED)
        confirmed_ids = {e.data.get('proposal_id') for e in confirmed_events}

        rejected_events = self.events.read_by_type(EventType.PROPOSAL_REJECTED)
        rejected_ids = {e.data.get('proposal_id') for e in rejected_events}

        # Check if query matches any pending proposal
        for proposal in proposed_events:
            if proposal.id in confirmed_ids or proposal.id in rejected_ids:
                continue  # Not pending

            # Check by full ID, prefix, or alias code
            proposal_code = self.codec.encode(proposal.id)
            if (proposal.id == resolved_query or
                proposal.id.startswith(resolved_query) or
                proposal_code == query.upper()):
                return True, proposal

        return False, None

    def _resolve_node(
        self,
        query: str,
        artifact_type: str = None,
        type_label: str = "artifact"
    ):
        """
        Resolve user input to a node with fuzzy matching and interactive prompts.

        Uses IDResolver to find nodes by:
        1. Exact match (full ID)
        2. Prefix match (4+ chars)
        3. Keyword match (search summaries)

        Args:
            query: User input (ID, prefix, or keyword)
            artifact_type: Optional filter by type (decision, constraint, etc.)
            type_label: Label for display (e.g., "decision")

        Returns:
            Resolved Node or None if cancelled/not found
        """
        result = self.resolver.resolve(query, artifact_type, codec=self.codec)

        def short_id(node):
            """Get short display ID (event_id preferred, else node ID suffix)."""
            if node.event_id:
                return node.event_id[:8]
            # For IDs like "decision_abc123", return the suffix
            if '_' in node.id:
                return node.id.split('_', 1)[1][:8]
            return node.id[:8]

        if result.status == ResolveStatus.FOUND:
            node = result.node
            summary = generate_summary(get_node_summary(node))
            print(f"\nFound: {node.type} [{short_id(node)}]")
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"  \"{summary}\"")
            return node

        elif result.status == ResolveStatus.AMBIGUOUS:
            print(f"\nMultiple matches for \"{query}\":\n")
            for i, node in enumerate(result.candidates, 1):
                summary = generate_summary(get_node_summary(node))
                # Layer 2 (Encoding): Use safe_print for LLM-generated content
                safe_print(f"  {i}. [{short_id(node)}] {summary}")
            print(f"\nWhich one? Enter number or ID prefix:")

            try:
                choice = input("> ").strip()

                # Try as number
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(result.candidates):
                        node = result.candidates[idx]
                        summary = generate_summary(get_node_summary(node))
                        print(f"\nFound: {node.type} [{short_id(node)}]")
                        # Layer 2 (Encoding): Use safe_print for LLM-generated content
                        safe_print(f"  \"{summary}\"")
                        return node

                # Try as ID prefix
                for node in result.candidates:
                    if node.id.startswith(choice) or (node.event_id and node.event_id.startswith(choice)):
                        summary = generate_summary(get_node_summary(node))
                        print(f"\nFound: {node.type} [{short_id(node)}]")
                        # Layer 2 (Encoding): Use safe_print for LLM-generated content
                        safe_print(f"  \"{summary}\"")
                        return node

                print("Invalid selection.")
                return None

            except (EOFError, KeyboardInterrupt):
                return None

        else:  # NOT_FOUND
            symbols = get_symbols()

            # Check if query is a pending proposal (actionable error per [CR-UZ])
            is_proposal, proposal = self._is_pending_proposal(query)
            if is_proposal:
                # Extract proposal details
                content = proposal.data.get('proposed', {})
                artifact_type = content.get('type', 'unknown')
                summary = content.get('summary', 'No summary')
                proposal_code = self.format_id(proposal.id)

                # Actionable error message (follows tensions pattern)
                print(f"\n{symbols.warning} Cannot link: {proposal_code} is a pending proposal, not an accepted artifact.\n")
                print(f"  Type: {artifact_type}")
                # Layer 2 (Encoding): Use safe_print for LLM-generated content
                safe_print(f"  \"{generate_summary(summary)}\"")
                print(f"\n  Proposals must be accepted before linking.\n")
                print(f"  {symbols.arrow} Run: babel review --accept {proposal_code}")
                print(f"  {symbols.arrow} Then: babel link <new-id>")
                print(f"\n  Manual: .babel/manual/link.md [LNK-03]")
                return None

            # Generic not found error (unchanged)
            print(f"\nNo match for \"{query}\".\n")
            if result.candidates:
                print(f"Recent {type_label}s:")
                for node in result.candidates:
                    summary = generate_summary(get_node_summary(node))
                    # Layer 2 (Encoding): Use safe_print for LLM-generated content
                    safe_print(f"  [{short_id(node)}] {summary}")
            print(f"\nTry: babel <command> <id> ...")
            return None

    # NOTE: _find_challenge_by_id() and _suggest_hypothesis() moved to commands/tensions.py

    # =========================================================================
    # P9: Dual-Test Truth (Validation)
    # =========================================================================
    
    def endorse(self, decision_id: str, comment: str = None):
        """Endorse a decision. Delegates to ValidationCommand."""
        return self._validation_cmd.endorse(decision_id, comment=comment)

    def evidence_decision(self, decision_id: str, content: str, evidence_type: str = "observation"):
        """Add evidence to a decision. Delegates to ValidationCommand."""
        return self._validation_cmd.evidence_decision(decision_id, content, evidence_type=evidence_type)

    def link(self, artifact_id: str = None, purpose_id: str = None, list_unlinked: bool = False, link_all: bool = False,
             limit: int = 10, offset: int = 0, show_all: bool = False, to_commit: str = None, list_commits: bool = False):
        """Link artifact to purpose or commit. Delegates to LinkCommand."""
        if list_unlinked:
            return self._link_cmd.list_unlinked(limit=limit, offset=offset, show_all=show_all)
        elif list_commits:
            return self._link_cmd.list_commit_links(limit=limit, offset=offset)
        elif link_all:
            return self._link_cmd.link_all()
        elif artifact_id and to_commit:
            return self._link_cmd.link_to_commit(artifact_id, to_commit)
        elif artifact_id:
            return self._link_cmd.link(artifact_id, purpose_id=purpose_id)
        else:
            print("Usage: babel link <artifact_id> [purpose_id]")
            print("       babel link <decision_id> --to-commit <sha>  (link to git commit)")
            print("       babel link --list     (show unlinked artifacts)")
            print("       babel link --commits  (show decision→commit links)")
            print("       babel link --all      (link all unlinked to active purpose)")

    def suggest_links(self, from_recent: int = 5, min_score: float = 0.3,
                      show_all: bool = False, commit: str = None):
        """Suggest decision-to-commit links. Delegates to SuggestLinksCommand."""
        return self._suggest_links_cmd.suggest_links(
            from_recent=from_recent,
            min_score=min_score,
            show_all=show_all,
            commit_sha=commit
        )

    def gaps(self, show_commits: bool = False, show_decisions: bool = False,
             from_recent: int = 20, limit: int = 10, offset: int = 0):
        """Show implementation gaps. Delegates to GapsCommand."""
        return self._gaps_cmd.gaps(
            show_commits=show_commits,
            show_decisions=show_decisions,
            from_recent=from_recent,
            limit=limit,
            offset=offset
        )

    def validation_cmd(self, decision_id: str = None, verbose: bool = False, full: bool = False, output_format: str = None):
        """Show validation status. Delegates to ValidationCommand."""
        return self._validation_cmd.validation_cmd(decision_id=decision_id, verbose=verbose, full=full, output_format=output_format)

    # =========================================================================
    # P10: Ambiguity Management (Open Questions) - Delegates to QuestionsCommand
    # =========================================================================

    def question(self, content: str, context: str = None, domain: str = None):
        """Raise an open question. Delegates to QuestionsCommand."""
        return self._questions_cmd.question(content, context=context, domain=domain)

    def questions_cmd(self, verbose: bool = False, full: bool = False, output_format: str = None):
        """Show open questions. Delegates to QuestionsCommand."""
        return self._questions_cmd.questions_cmd(verbose=verbose, full=full, output_format=output_format)

    def resolve_question(self, question_id: str, resolution: str, outcome: str = "answered"):
        """Resolve an open question. Delegates to QuestionsCommand."""
        return self._questions_cmd.resolve_question(question_id, resolution, outcome=outcome)

    # =========================================================================
    # P7: Evidence-Weighted Memory (Deprecation) - Delegates to DeprecateCommand
    # =========================================================================

    def _get_deprecated_ids(self) -> dict:
        """Get deprecated artifact IDs. Delegates to DeprecateCommand."""
        return self._deprecate_cmd._get_deprecated_ids()

    def _is_deprecated(self, artifact_id: str) -> Optional[dict]:
        """Check if artifact is deprecated. Delegates to DeprecateCommand."""
        return self._deprecate_cmd._is_deprecated(artifact_id)

    def deprecate(self, artifact_id: str, reason: str, superseded_by: str = None):
        """Deprecate an artifact. Delegates to DeprecateCommand."""
        return self._deprecate_cmd.deprecate(artifact_id, reason, superseded_by=superseded_by)

    def history(self, limit: int = 10, scope_filter: Optional[str] = None, output_format: str = None):
        """Show recent events. Delegates to HistoryCommand."""
        return self._history_cmd.history(limit=limit, scope_filter=scope_filter, output_format=output_format)

    def share(self, event_id: str):
        """Promote event from local to shared. Delegates to HistoryCommand."""
        return self._history_cmd.share(event_id)

    # NOTE: _event_preview() removed - now in commands/history.py

    def sync(self, verbose: bool = False):
        """Synchronize events after git pull. Delegates to HistoryCommand."""
        return self._history_cmd.sync(verbose=verbose)

    def process_queue(self, batch_mode: bool = False):
        """Process queued extractions. Delegates to ConfigCommand."""
        return self._config_cmd.process_queue(batch_mode=batch_mode)

    def show_config(self):
        """Show current configuration. Delegates to ConfigCommand."""
        return self._config_cmd.show_config()

    def set_config(self, key: str, value: str, scope: str = "project"):
        """Set a configuration value. Delegates to ConfigCommand."""
        return self._config_cmd.set_config(key, value, scope=scope)

    def capture_git_commit(self, async_mode: bool = False):
        """Capture git commit. Delegates to GitCommand."""
        return self._git_cmd.capture_git_commit(async_mode=async_mode)

    def install_hooks(self):
        """Install git hooks. Delegates to GitCommand."""
        return self._git_cmd.install_hooks()

    def uninstall_hooks(self):
        """Remove git hooks. Delegates to GitCommand."""
        return self._git_cmd.uninstall_hooks()

    def hooks_status(self):
        """Show git hooks status. Delegates to GitCommand."""
        return self._git_cmd.hooks_status()


def main():
    """
    Main entry point for Babel CLI.

    Uses command registry pattern for modular command handling.
    Parser definitions and dispatch logic are in individual command modules.
    """
    parser = argparse.ArgumentParser(
        description="Babel -- Intent preservation tool",
        epilog="Captures reasoning. Answers 'why?'. Quiet until needed."
    )

    parser.add_argument(
        '--project', '-p',
        default=os.environ.get("BABEL_PROJECT_PATH", "."),
        help='Project directory (default: BABEL_PROJECT_PATH or current)'
    )

    parser.add_argument(
        '--version', '-V',
        action='version',
        version=f'babel {__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Register all commands from command modules (self-registration pattern)
    from .commands import register_all, dispatch
    register_all(subparsers)

    # Parse arguments and dispatch to registered handler
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize CLI and dispatch to command handler
    cli = IntentCLI(Path(args.project))

    try:
        dispatch(args.command, cli, args)
    except KeyError as e:
        print(f"Error: {e}")
        parser.print_help()


if __name__ == '__main__':
    main()