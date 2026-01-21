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
import sys
from pathlib import Path
from typing import Optional

from .core.events import DualEventStore
from .core.graph import GraphStore, Node
from .services.extractor import Extractor
from .config import ConfigManager, get_config, PROVIDERS
from .services.providers import get_provider, LLMResponse
from .services.git import GitIntegration
from .presentation.symbols import get_symbols, format_artifact, symbol_for_type, symbol_for_status, safe_print
from .tracking.coherence import CoherenceChecker
from .core.refs import RefStore
from .core.loader import LazyLoader, TokenBudget
from .core.vocabulary import Vocabulary
from .services.scanner import Scanner
from .tracking.tensions import TensionTracker
from .tracking.validation import ValidationTracker
from .tracking.ambiguity import QuestionTracker
from .core.resolver import IDResolver, ResolveStatus
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
from .preferences import MemoManager
from .content import HELP_TEXT, PRINCIPLES_TEXT
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

        # Initialize memo manager for user preferences (P6: token efficiency)
        self.memos = MemoManager(self.babel_dir)

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

    def _find_node_by_id(self, node_id: str):
        """Find a graph node by ID prefix (legacy, use _resolve_node for UX)."""
        # Check decisions first (most common target)
        for node_type in ["decision", "constraint", "purpose", "boundary"]:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                if node.id.startswith(node_id):
                    return node
        return None

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
        result = self.resolver.resolve(query, artifact_type)

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
            summary = node.content.get('summary', str(node.content)[:50])
            print(f"\nFound: {node.type} [{short_id(node)}]")
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"  \"{summary}\"")
            return node

        elif result.status == ResolveStatus.AMBIGUOUS:
            print(f"\nMultiple matches for \"{query}\":\n")
            for i, node in enumerate(result.candidates, 1):
                summary = node.content.get('summary', '')[:40]
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
                        summary = node.content.get('summary', '')[:50]
                        print(f"\nFound: {node.type} [{short_id(node)}]")
                        # Layer 2 (Encoding): Use safe_print for LLM-generated content
                        safe_print(f"  \"{summary}\"")
                        return node

                # Try as ID prefix
                for node in result.candidates:
                    if node.id.startswith(choice) or (node.event_id and node.event_id.startswith(choice)):
                        summary = node.content.get('summary', '')[:50]
                        print(f"\nFound: {node.type} [{short_id(node)}]")
                        # Layer 2 (Encoding): Use safe_print for LLM-generated content
                        safe_print(f"  \"{summary}\"")
                        return node

                print("Invalid selection.")
                return None

            except (EOFError, KeyboardInterrupt):
                return None

        else:  # NOT_FOUND
            print(f"\nNo match for \"{query}\".\n")
            if result.candidates:
                print(f"Recent {type_label}s:")
                for node in result.candidates:
                    summary = node.content.get('summary', '')[:40]
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
    parser = argparse.ArgumentParser(
        description="Babel -- Intent preservation tool",
        epilog="Captures reasoning. Answers 'why?'. Quiet until needed."
    )

    parser.add_argument(
        '--project', '-p',
        default='.',
        help='Project directory (default: current)'
    )

    parser.add_argument(
        '--version', '-V',
        action='version',
        version=f'babel {__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # init
    init_parser = subparsers.add_parser('init', help='Start a new project')
    init_parser.add_argument('purpose', help='What are you building?')
    init_parser.add_argument('--need', '-n', help='What problem are you solving? (P1: grounds purpose in reality)')

    # capture
    capture_parser = subparsers.add_parser('capture', help='Capture a thought or decision')
    capture_parser.add_argument('text', help='What to capture')
    capture_parser.add_argument('--raw', action='store_true', help='Skip extraction')
    capture_parser.add_argument('--share', '-s', action='store_true', help='Share with team (default: local only)')
    capture_parser.add_argument('--domain', '-d', help='Expertise domain (P3: security, performance, architecture, etc.)')
    capture_parser.add_argument('--uncertain', '-u', action='store_true', help='Mark as uncertain/provisional (P10: holding ambiguity)')
    capture_parser.add_argument('--uncertainty-reason', help='Why this is uncertain')
    capture_parser.add_argument('--batch', '-b', action='store_true', help='Queue proposals for later review (use: babel review)')
    capture_parser.add_argument('--spec', metavar='NEED_ID', help='Add specification to existing need (text becomes spec content)')

    # why
    why_parser = subparsers.add_parser('why', help='Ask why something is the way it is')
    why_parser.add_argument('query', nargs='?', help='What do you want to understand?')
    why_parser.add_argument('--commit', help='Query why a specific commit was made (shows linked decisions)')

    # status
    status_parser = subparsers.add_parser('status', help='Show project status')
    status_parser.add_argument('--full', action='store_true', help='Show full content without truncation')
    status_parser.add_argument('--git', action='store_true', help='Show git-babel sync health (decision↔commit links)')
    status_parser.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json', 'summary'],
                               help='Output format (overrides config)')

    # check - integrity verification (P11)
    check_parser = subparsers.add_parser('check', help='Verify project integrity and suggest recovery')
    check_parser.add_argument('--repair', action='store_true', help='Attempt automatic repair of issues')

    # coherence
    coherence_parser = subparsers.add_parser('coherence', help='Check project coherence')
    coherence_parser.add_argument('--force', action='store_true', help='Force full check (ignore cache)')
    coherence_parser.add_argument('--full', action='store_true', help='Show full content without truncation')
    coherence_parser.add_argument('--qa', action='store_true', help='QA/QC mode with detailed report')
    coherence_parser.add_argument('--resolve', action='store_true', help='Interactive resolution mode for issues (Living Cycle re-negotiation)')
    coherence_parser.add_argument('--batch', action='store_true', help='Non-interactive mode with --resolve (for AI operators)')

    # scan - context-aware technical advisor
    scan_parser = subparsers.add_parser('scan', help='Context-aware technical scan')
    scan_parser.add_argument('query', nargs='?', default=None, help='Specific question to answer')
    scan_parser.add_argument('--type', dest='scan_type', default='health',
                            choices=['health', 'architecture', 'security', 'performance', 'dependencies'],
                            help='Type of scan (default: health)')
    scan_parser.add_argument('--deep', action='store_true', help='Run comprehensive analysis')
    scan_parser.add_argument('-v', '--verbose', action='store_true', help='Show all findings')

    # P4: Disagreement handling
    # challenge - raise a challenge against a decision
    challenge_parser = subparsers.add_parser('challenge', help='Challenge a decision (P4: disagreement as information)')
    challenge_parser.add_argument('target_id', help='Decision ID (or prefix) to challenge')
    challenge_parser.add_argument('reason', help='Why you disagree')
    challenge_parser.add_argument('--hypothesis', '-H', help='Testable alternative claim')
    challenge_parser.add_argument('--test', '-t', help='How to test the hypothesis')
    challenge_parser.add_argument('--domain', '-d', help='Expertise domain (P3)')

    # evidence - add evidence to a challenge
    evidence_parser = subparsers.add_parser('evidence', help='Add evidence to an open challenge')
    evidence_parser.add_argument('challenge_id', help='Challenge ID (or prefix)')
    evidence_parser.add_argument('content', help='The evidence')
    evidence_parser.add_argument('--type', dest='evidence_type', default='observation',
                                choices=['observation', 'benchmark', 'user_feedback', 'other'],
                                help='Type of evidence (default: observation)')

    # resolve - resolve a challenge
    resolve_parser = subparsers.add_parser('resolve', help='Resolve a challenge with outcome')
    resolve_parser.add_argument('challenge_id', help='Challenge ID (or prefix)')
    resolve_parser.add_argument('--outcome', '-o', required=True,
                               choices=['confirmed', 'revised', 'synthesized', 'uncertain'],
                               help='Resolution outcome (uncertain = P10 holding ambiguity)')
    resolve_parser.add_argument('--resolution', '-r', help='What was decided (prompted if not provided)')
    resolve_parser.add_argument('--evidence', '-e', dest='evidence_summary', help='Summary of evidence')
    resolve_parser.add_argument('--force', '-f', action='store_true', help='Skip premature resolution warning')

    # tensions - show open tensions
    tensions_parser = subparsers.add_parser('tensions', help='Show open tensions and challenges')
    tensions_parser.add_argument('-v', '--verbose', action='store_true', help='Show full details')
    tensions_parser.add_argument('--full', action='store_true', help='Show full content without truncation')
    tensions_parser.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json'],
                                 help='Output format (overrides config)')

    # P9: Dual-test truth validation
    # endorse - add consensus to a decision
    endorse_parser = subparsers.add_parser('endorse', help='Endorse a decision (P9: consensus)')
    endorse_parser.add_argument('decision_id', help='Decision ID (or prefix) to endorse')
    endorse_parser.add_argument('--comment', '-c', help='Optional comment on why endorsing')

    # evidence-decision - add evidence to a decision (note: 'evidence' is for challenges)
    evdec_parser = subparsers.add_parser('evidence-decision', help='Add evidence to a decision (P9: grounding)')
    evdec_parser.add_argument('decision_id', help='Decision ID (or prefix)')
    evdec_parser.add_argument('content', help='The evidence')
    evdec_parser.add_argument('--type', dest='evidence_type', default='observation',
                             choices=['observation', 'benchmark', 'user_feedback', 'outcome', 'other'],
                             help='Type of evidence (default: observation)')

    # validation - show validation status
    validation_parser = subparsers.add_parser('validation', help='Show validation status (P9: dual-test truth)')
    validation_parser.add_argument('decision_id', nargs='?', help='Specific decision ID (optional)')
    validation_parser.add_argument('-v', '--verbose', action='store_true', help='Show full details')
    validation_parser.add_argument('--full', action='store_true', help='Show full content without truncation')
    validation_parser.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json', 'detail'],
                                   help='Output format (overrides config)')

    # link - connect artifact to purpose (coherence)
    link_parser = subparsers.add_parser('link', help='Link artifact to purpose (improves coherence)')
    link_parser.add_argument('artifact_id', nargs='?', help='Artifact ID (or prefix) to link')
    link_parser.add_argument('purpose_id', nargs='?', help='Purpose ID (default: active purpose)')
    link_parser.add_argument('--list', action='store_true', help='List unlinked artifacts')
    link_parser.add_argument('--all', action='store_true', help='Link all unlinked to active purpose')
    link_parser.add_argument('--limit', type=int, default=10, help='Maximum items for --list (default: 10)')
    link_parser.add_argument('--offset', type=int, default=0, help='Skip first N items for --list (default: 0)')
    link_parser.add_argument('--to-commit', dest='to_commit', help='Link decision to a git commit (P8: bridges intent with state)')
    link_parser.add_argument('--commits', action='store_true', help='List all decision-to-commit links')

    # suggest-links - AI-assisted link suggestions (P7, P8)
    suggest_links_parser = subparsers.add_parser('suggest-links', help='Suggest decision-to-commit links (AI-assisted)')
    suggest_links_parser.add_argument('--from-recent', dest='from_recent', type=int, default=5,
                                      help='Number of recent commits to analyze (default: 5)')
    suggest_links_parser.add_argument('--commit', help='Analyze a specific commit instead of recent')
    suggest_links_parser.add_argument('--min-score', dest='min_score', type=float, default=0.3,
                                      help='Minimum confidence score (0-1, default: 0.3)')
    suggest_links_parser.add_argument('--all', action='store_true', help='Show all suggestions, even low-confidence')

    # gaps - show implementation gaps (P8, P9)
    gaps_parser = subparsers.add_parser('gaps', help='Show implementation gaps between decisions and commits')
    gaps_parser.add_argument('--commits', action='store_true', help='Only show unlinked commits')
    gaps_parser.add_argument('--decisions', action='store_true', help='Only show unlinked decisions')
    gaps_parser.add_argument('--from-recent', dest='from_recent', type=int, default=20,
                             help='Number of recent commits to check (default: 20)')
    gaps_parser.add_argument('--limit', type=int, default=10, help='Maximum items per section (default: 10)')
    gaps_parser.add_argument('--offset', type=int, default=0, help='Skip first N items (default: 0)')

    # P10: Ambiguity Management
    # question - raise an open question
    question_parser = subparsers.add_parser('question', help='Raise an open question (P10: holding ambiguity)')
    question_parser.add_argument('content', help='The question')
    question_parser.add_argument('--context', '-c', help='Why this question matters')
    question_parser.add_argument('--domain', '-d', help='Related expertise domain')

    # questions - list open questions
    questions_parser = subparsers.add_parser('questions', help='Show open questions (P10: acknowledged unknowns)')
    questions_parser.add_argument('-v', '--verbose', action='store_true', help='Show full details')
    questions_parser.add_argument('--full', action='store_true', help='Show full content without truncation')
    questions_parser.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json'],
                                  help='Output format (overrides config)')

    # resolve-question - resolve an open question
    resolve_q_parser = subparsers.add_parser('resolve-question', help='Resolve an open question (P10)')
    resolve_q_parser.add_argument('question_id', help='Question ID (or prefix)')
    resolve_q_parser.add_argument('resolution', help='The answer or conclusion')
    resolve_q_parser.add_argument('--outcome', default='answered',
                                  choices=['answered', 'dissolved', 'superseded'],
                                  help='How it was resolved (default: answered)')

    # P7: Evidence-weighted memory
    # deprecate - mark artifact as deprecated (not deleted)
    deprecate_parser = subparsers.add_parser('deprecate', help='Deprecate an artifact (P7: living memory)')
    deprecate_parser.add_argument('artifact_id', help='Artifact ID (or prefix) to deprecate')
    deprecate_parser.add_argument('reason', help='Why it is being deprecated')
    deprecate_parser.add_argument('--superseded-by', help='ID of replacement artifact')

    # history
    history_parser = subparsers.add_parser('history', help='Show recent activity')
    history_parser.add_argument('-n', type=int, default=10, help='Number of events')
    history_parser.add_argument('--shared', action='store_true', help='Show only shared events')
    history_parser.add_argument('--local', action='store_true', help='Show only local events')
    history_parser.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json'],
                                help='Output format (overrides config)')

    # review - review pending proposals (HC2: Human Authority)
    review_parser = subparsers.add_parser('review', help='Review pending proposals (HC2: Human Authority)')
    review_parser.add_argument('--synthesize', '-s', action='store_true',
                               help='Synthesize proposals into themes for directional review')
    review_parser.add_argument('--by-theme', action='store_true',
                               help='Review by theme (requires --synthesize first)')
    review_parser.add_argument('--accept-theme', metavar='THEME',
                               help='Accept all proposals in a theme (non-interactive)')
    review_parser.add_argument('--list-themes', action='store_true',
                               help='List synthesized themes without reviewing')
    review_parser.add_argument('--list', action='store_true',
                               help='List proposals without prompting (AI-safe)')
    review_parser.add_argument('--accept', metavar='ID', action='append',
                               help='Accept specific proposal by ID (can repeat)')
    review_parser.add_argument('--accept-all', action='store_true',
                               help='Accept all proposals (AI-safe)')
    review_parser.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json'],
                               help='Output format for --list (overrides config)')

    # share - promote local event to shared
    share_parser = subparsers.add_parser('share', help='Share a local event with team')
    share_parser.add_argument('event_id', help='Event ID (or prefix) to share')

    # sync - synchronize after git pull
    sync_parser = subparsers.add_parser('sync', help='Sync events after git pull')
    sync_parser.add_argument('-v', '--verbose', action='store_true', help='Show details')

    # prompt - system prompt management for LLM integration
    prompt_parser = subparsers.add_parser('prompt', help='Manage system prompt for LLM integration')
    prompt_parser.add_argument('--install', action='store_true', help='Install prompt to IDE-specific location')
    prompt_parser.add_argument('--force', action='store_true', help='Overwrite existing prompt file')
    prompt_parser.add_argument('--status', action='store_true', help='Show prompt installation status')

    # map - project structure documentation for LLM understanding
    map_parser = subparsers.add_parser('map', help='Generate project structure map for LLM understanding')
    map_parser.add_argument('--refresh', action='store_true', help='Regenerate map from scratch (all phases)')
    map_parser.add_argument('--update', action='store_true', help='Incremental update (only changed files)')
    map_parser.add_argument('--status', action='store_true', help='Show map status')

    # list - graph-aware artifact discovery
    list_parser = subparsers.add_parser('list', help='List and discover artifacts (graph-aware)')
    list_parser.add_argument('type', nargs='?', help='Artifact type to list (decisions, constraints, principles)')
    list_parser.add_argument('--from', dest='from_id', help='Show artifacts connected to this ID (graph traversal)')
    list_parser.add_argument('--orphans', action='store_true', help='Show artifacts with no connections')
    list_parser.add_argument('--all', action='store_true', help='Show all items (no limit)')
    list_parser.add_argument('--filter', dest='filter_pattern', help='Filter by keyword (case-insensitive)')
    list_parser.add_argument('--limit', type=int, default=10, help='Maximum items to show (default: 10)')
    list_parser.add_argument('--offset', type=int, default=0, help='Skip first N items (default: 0)')

    # memo - persistent user preferences (P6: token efficiency)
    memo_parser = subparsers.add_parser('memo', help='Save persistent preferences (reduces repetition)')
    memo_parser.add_argument('content', nargs='?', help='Memo content to save')
    memo_parser.add_argument('--context', '-c', action='append', dest='contexts',
                             help='Context where this applies (can repeat)')
    memo_parser.add_argument('--init', '-i', action='store_true',
                             help='Foundational instruction - surfaces at session start via status')
    memo_parser.add_argument('--list', '-l', action='store_true', help='List all memos')
    memo_parser.add_argument('--list-init', action='store_true', help='List only init memos')
    memo_parser.add_argument('--remove', '-r', metavar='ID', help='Remove memo by ID')
    memo_parser.add_argument('--update', '-u', metavar='ID', help='Update memo by ID')
    memo_parser.add_argument('--promote-init', metavar='ID', help='Make memo foundational (init)')
    memo_parser.add_argument('--demote-init', metavar='ID', help='Make memo regular (not init)')
    memo_parser.add_argument('--candidates', action='store_true', help='Show AI-detected patterns')
    memo_parser.add_argument('--promote', metavar='ID', help='Promote candidate to memo')
    memo_parser.add_argument('--promote-all', action='store_true', help='Promote all pending candidates')
    memo_parser.add_argument('--dismiss', metavar='ID', help='Dismiss a candidate')
    memo_parser.add_argument('--suggest', action='store_true', help='Show pending promotion suggestions')
    memo_parser.add_argument('--relevant', metavar='CONTEXT', help='Show memos relevant to context')
    memo_parser.add_argument('--stats', action='store_true', help='Show memo statistics')

    # help - comprehensive help
    subparsers.add_parser('help', help='Show comprehensive help for all commands')

    # principles - P11 Framework Self-Application
    subparsers.add_parser('principles', help='Show Babel principles for self-check (P11)')

    # process-queue
    process_queue_parser = subparsers.add_parser('process-queue', help='Process queued extractions (after offline)')
    process_queue_parser.add_argument('--batch', action='store_true', help='Queue proposals for review instead of interactive confirm (for AI assistants)')

    # config
    config_parser = subparsers.add_parser('config', help='View or set configuration')
    config_parser.add_argument('--set', metavar='KEY=VALUE', help='Set config value (e.g., llm.provider=openai)')
    config_parser.add_argument('--user', action='store_true', help='Apply to user config instead of project')

    # capture-commit
    commit_parser = subparsers.add_parser('capture-commit', help='Capture last git commit')
    commit_parser.add_argument('--async', dest='async_mode', action='store_true', help='Queue extraction for later')

    # hooks
    hooks_parser = subparsers.add_parser('hooks', help='Manage git hooks')
    hooks_sub = hooks_parser.add_subparsers(dest='hooks_command')
    hooks_sub.add_parser('install', help='Install git hooks')
    hooks_sub.add_parser('uninstall', help='Remove git hooks')
    hooks_sub.add_parser('status', help='Show hooks status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = IntentCLI(Path(args.project))

    if args.command == 'init':
        cli.init(args.purpose, need=args.need)
    elif args.command == 'capture':
        if args.spec:
            # Specification capture mode: enrich existing need with spec
            cli.capture_spec(
                need_id=args.spec,
                spec_text=args.text,
                batch_mode=args.batch
            )
        else:
            # Regular capture mode
            cli.capture(
                args.text,
                auto_extract=not args.raw,
                share=args.share,
                domain=args.domain,
                uncertain=args.uncertain,
                uncertainty_reason=args.uncertainty_reason,
                batch_mode=args.batch
            )
    elif args.command == 'why':
        cli.why(args.query, commit=args.commit)
    elif args.command == 'status':
        cli.status(full=args.full, git=args.git)
    elif args.command == 'check':
        cli.check(repair=args.repair)
    elif args.command == 'coherence':
        cli.coherence_check(force=args.force, full=args.full, qa=args.qa, resolve=args.resolve, batch=args.batch)
    elif args.command == 'scan':
        cli.scan(
            scan_type=args.scan_type,
            deep=args.deep,
            query=args.query,
            verbose=args.verbose
        )
    elif args.command == 'history':
        scope_filter = None
        if args.shared:
            scope_filter = "shared"
        elif args.local:
            scope_filter = "local"
        result = cli.history(args.n, scope_filter=scope_filter, output_format=getattr(args, 'format', None))
        if result is not None:
            from babel.output import OutputSpec, render
            if isinstance(result, OutputSpec):
                output = render(result, format=args.format or 'auto', full=False)
                safe_print(output)
    elif args.command == 'review':
        result = cli.review(
            synthesize=args.synthesize,
            by_theme=args.by_theme,
            accept_theme=args.accept_theme,
            list_themes=args.list_themes,
            list_only=args.list,
            accept_ids=args.accept,
            accept_all=args.accept_all,
            output_format=getattr(args, 'format', None)
        )
        if result is not None:
            from babel.output import OutputSpec, render
            if isinstance(result, OutputSpec):
                output = render(result, format=args.format or 'auto', full=False)
                safe_print(output)
    elif args.command == 'share':
        cli.share(args.event_id)
    elif args.command == 'sync':
        cli.sync(verbose=args.verbose)
    elif args.command == 'challenge':
        cli.challenge(
            target_id=args.target_id,
            reason=args.reason,
            hypothesis=args.hypothesis,
            test=args.test,
            domain=args.domain
        )
    elif args.command == 'evidence':
        cli.evidence(
            challenge_id=args.challenge_id,
            content=args.content,
            evidence_type=args.evidence_type
        )
    elif args.command == 'resolve':
        cli.resolve(
            challenge_id=args.challenge_id,
            outcome=args.outcome,
            resolution=args.resolution,
            evidence_summary=args.evidence_summary,
            force=args.force
        )
    elif args.command == 'tensions':
        result = cli.tensions_cmd(verbose=args.verbose, full=args.full, output_format=getattr(args, 'format', None))
        if result is not None:
            from babel.output import OutputSpec, render
            if isinstance(result, OutputSpec):
                output = render(result, format=args.format or 'auto', full=args.full)
                safe_print(output)
    elif args.command == 'endorse':
        cli.endorse(
            decision_id=args.decision_id,
            comment=args.comment
        )
    elif args.command == 'evidence-decision':
        cli.evidence_decision(
            decision_id=args.decision_id,
            content=args.content,
            evidence_type=args.evidence_type
        )
    elif args.command == 'validation':
        result = cli.validation_cmd(
            decision_id=args.decision_id,
            verbose=args.verbose,
            full=args.full,
            output_format=getattr(args, 'format', None)
        )
        # If command returns OutputSpec, render it
        if result is not None:
            from babel.output import OutputSpec, render
            if isinstance(result, OutputSpec):
                output = render(result, format=args.format or 'auto', full=args.full)
                safe_print(output)
    elif args.command == 'link':
        cli.link(
            artifact_id=args.artifact_id,
            purpose_id=args.purpose_id,
            list_unlinked=getattr(args, 'list', False),
            link_all=getattr(args, 'all', False),
            limit=args.limit,
            offset=args.offset,
            to_commit=args.to_commit,
            list_commits=args.commits
        )
    elif args.command == 'suggest-links':
        cli.suggest_links(
            from_recent=args.from_recent,
            min_score=args.min_score,
            show_all=getattr(args, 'all', False),
            commit=args.commit
        )
    elif args.command == 'gaps':
        cli.gaps(
            show_commits=args.commits,
            show_decisions=args.decisions,
            from_recent=args.from_recent,
            limit=args.limit,
            offset=args.offset
        )
    elif args.command == 'question':
        cli.question(
            content=args.content,
            context=args.context,
            domain=args.domain
        )
    elif args.command == 'questions':
        result = cli.questions_cmd(verbose=args.verbose, full=args.full, output_format=getattr(args, 'format', None))
        if result is not None:
            from babel.output import OutputSpec, render
            if isinstance(result, OutputSpec):
                output = render(result, format=args.format or 'auto', full=args.full)
                safe_print(output)
    elif args.command == 'resolve-question':
        cli.resolve_question(
            question_id=args.question_id,
            resolution=args.resolution,
            outcome=args.outcome
        )
    elif args.command == 'deprecate':
        cli.deprecate(
            artifact_id=args.artifact_id,
            reason=args.reason,
            superseded_by=args.superseded_by
        )
    elif args.command == 'prompt':
        if args.install:
            cli._prompt_cmd.install(force=args.force)
        elif args.status:
            cli._prompt_cmd.status()
        else:
            cli._prompt_cmd.show()
    elif args.command == 'map':
        if args.refresh:
            cli._map_cmd.refresh()
        elif args.update:
            cli._map_cmd.update()
        elif args.status:
            cli._map_cmd.status()
        else:
            cli._map_cmd.show()
    elif args.command == 'list':
        cli.list_artifacts(
            artifact_type=args.type,
            from_id=args.from_id,
            orphans=args.orphans,
            limit=args.limit,
            offset=args.offset,
            show_all=getattr(args, 'all', False),
            filter_pattern=args.filter_pattern
        )
    elif args.command == 'memo':
        if args.remove:
            cli._memo_cmd.remove(args.remove)
        elif args.update:
            cli._memo_cmd.update(args.update, content=args.content, contexts=args.contexts)
        elif getattr(args, 'list_init', False):
            cli._memo_cmd.list_memos(init_only=True)
        elif getattr(args, 'list', False):
            cli._memo_cmd.list_memos()
        elif getattr(args, 'promote_init', None):
            cli._memo_cmd.set_init(args.promote_init, is_init=True)
        elif getattr(args, 'demote_init', None):
            cli._memo_cmd.set_init(args.demote_init, is_init=False)
        elif args.candidates:
            cli._memo_cmd.candidates()
        elif args.promote:
            cli._memo_cmd.promote(args.promote, contexts=args.contexts)
        elif getattr(args, 'promote_all', False):
            cli._memo_cmd.promote_all()
        elif args.dismiss:
            cli._memo_cmd.dismiss(args.dismiss)
        elif args.suggest:
            cli._memo_cmd.suggest()
        elif args.relevant:
            cli._memo_cmd.show_relevant([args.relevant])
        elif args.stats:
            cli._memo_cmd.stats()
        elif args.content:
            cli._memo_cmd.add(args.content, contexts=args.contexts, init=getattr(args, 'init', False))
        else:
            cli._memo_cmd.list_memos()
    elif args.command == 'help':
        cli.help()
    elif args.command == 'principles':
        cli.principles()
    elif args.command == 'process-queue':
        cli.process_queue(batch_mode=args.batch)
    elif args.command == 'config':
        if args.set:
            if '=' not in args.set:
                print("Error: Use format KEY=VALUE (e.g., llm.provider=openai)")
            else:
                key, value = args.set.split('=', 1)
                scope = "user" if args.user else "project"
                cli.set_config(key, value, scope)
        else:
            cli.show_config()
    elif args.command == 'capture-commit':
        cli.capture_git_commit(async_mode=args.async_mode)
    elif args.command == 'hooks':
        if args.hooks_command == 'install':
            cli.install_hooks()
        elif args.hooks_command == 'uninstall':
            cli.uninstall_hooks()
        elif args.hooks_command == 'status':
            cli.hooks_status()
        else:
            print("Usage: babel hooks [install|uninstall|status]")


if __name__ == '__main__':
    main()