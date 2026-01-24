"""
MemoCommand — CLI handler for user memos

Provides commands for:
- Adding/removing/updating memos
- Listing memos (all or context-filtered)
- Managing AI-detected candidates
- Promoting candidates to memos

Design principles:
- HC2: User controls all memo operations
- HC6: Clear, human-readable output
- P6: Token-efficient by default
"""

from typing import Optional, List
from ..commands.base import BaseCommand
from ..presentation.symbols import safe_print, truncate, SUMMARY_LENGTH


class MemoCommand(BaseCommand):
    """
    Command handler for memo operations.

    Memos are user preferences that persist across sessions.
    Unlike decisions, they're mutable and require no reasoning.
    """

    def add(self, content: str, contexts: Optional[List[str]] = None, init: bool = False):
        """
        Add a new memo.

        Args:
            content: The memo content
            contexts: Optional contexts where this applies
            init: If True, this is a foundational instruction (surfaces at session start)
        """
        symbols = self.symbols
        memo = self._cli.memos.add(content, contexts, init=init)

        init_marker = f" {symbols.purpose} INIT" if memo.init else ""
        print(f"\n{symbols.check_pass} Memo saved:{init_marker}")
        print(f"  {self._cli.format_id(memo.id)} {memo.content}")

        if memo.contexts:
            print(f"  Contexts: {', '.join(memo.contexts)}")
        else:
            print(f"  Contexts: (global - applies everywhere)")

        if memo.init:
            print(f"\nThis will surface at session start via 'babel status'.")
        else:
            print(f"\nThis will be surfaced in relevant contexts.")
        print(f"Manage memos: babel memo --list")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("memo", {})

    def remove(self, memo_id: str):
        """
        Remove a memo.

        Args:
            memo_id: Memo ID or prefix to remove
        """
        symbols = self.symbols

        # Get memo before removing (for display)
        memo = self._cli.memos.get(memo_id)
        if not memo:
            print(f"\nMemo not found: {memo_id}")
            return

        if self._cli.memos.remove(memo_id):
            print(f"\n{symbols.check_pass} Memo removed:")
            print(f"  {self._cli.format_id(memo.id)} {memo.content}")

            # Succession hint (centralized)
            from ..output import end_command
            end_command("memo", {})
        else:
            print(f"\nFailed to remove memo: {memo_id}")

    def update(self, memo_id: str, content: Optional[str] = None,
               contexts: Optional[List[str]] = None):
        """
        Update an existing memo.

        Args:
            memo_id: Memo ID or prefix
            content: New content (optional)
            contexts: New contexts (optional)
        """
        symbols = self.symbols

        if content is None and contexts is None:
            print("\nNothing to update. Provide --content or --context.")
            return

        memo = self._cli.memos.update(memo_id, content, contexts)

        if memo:
            print(f"\n{symbols.check_pass} Memo updated:")
            print(f"  {self._cli.format_id(memo.id)} {memo.content}")
            if memo.contexts:
                print(f"  Contexts: {', '.join(memo.contexts)}")
        else:
            print(f"\nMemo not found: {memo_id}")

    def list_memos(self, context: Optional[str] = None, init_only: bool = False):
        """
        List memos.

        Args:
            context: Optional context filter
            init_only: If True, show only init memos
        """
        symbols = self.symbols

        if init_only:
            memos = self._cli.memos.list_init_memos()
            title = "Init Memos (Foundational Instructions)"
        elif context:
            # Filter by context
            memos = self._cli.memos.get_relevant([context])
            title = f"Memos for '{context}'"
        else:
            memos = self._cli.memos.list_memos()
            title = "All Memos"

        if not memos:
            if init_only:
                print("\nNo init memos saved.")
                print("\nAdd an init memo: babel memo \"instruction\" --init")
            elif context:
                print(f"\nNo memos found for context: {context}")
            else:
                print("\nNo memos saved.")
            print("\nAdd a memo: babel memo \"your instruction\"")
            return

        print(f"\n{title} ({len(memos)}):")
        print()

        for memo in memos:
            content_display = truncate(memo.content, SUMMARY_LENGTH - 15)
            ctx_display = f"[{', '.join(memo.contexts)}]" if memo.contexts else "[global]"
            use_info = f"(used {memo.use_count}x)" if memo.use_count > 0 else ""
            init_marker = f"{symbols.purpose} INIT " if memo.init else ""

            safe_print(f"  {init_marker}{self._cli.format_id(memo.id)} {content_display}")
            print(f"           {ctx_display} {use_info}")

        print()
        print(f"Add: babel memo \"instruction\"")
        print(f"Add init: babel memo \"instruction\" --init")
        print(f"Remove: babel memo --remove <id>")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("memo", {})

    def set_init(self, memo_id: str, is_init: bool):
        """
        Set or unset the init flag on a memo.

        Args:
            memo_id: Memo ID or prefix
            is_init: True to make foundational, False to make regular
        """
        symbols = self.symbols

        # Get memo first for display
        memo = self._cli.memos.get(memo_id)
        if not memo:
            print(f"\nMemo not found: {memo_id}")
            return

        updated = self._cli.memos.set_init(memo_id, is_init)

        if updated:
            if is_init:
                print(f"\n{symbols.check_pass} Memo promoted to init:")
                print(f"  {symbols.purpose} {self._cli.format_id(updated.id)} {updated.content}")
                print(f"\nThis will now surface at session start via 'babel status'.")
            else:
                print(f"\n{symbols.check_pass} Memo demoted from init:")
                print(f"  {self._cli.format_id(updated.id)} {updated.content}")
                print(f"\nThis will no longer surface at session start.")
        else:
            print(f"\nFailed to update memo: {memo_id}")

    def show_relevant(self, contexts: List[str]):
        """
        Show memos relevant to given contexts.

        Used internally when AI needs to surface memos.

        Args:
            contexts: List of active context topics
        """
        symbols = self.symbols
        memos = self._cli.memos.get_relevant(contexts)

        if not memos:
            return  # Silent if no relevant memos

        print(f"\n{symbols.purpose} Active memos for [{', '.join(contexts)}]:")
        for memo in memos:
            content_display = truncate(memo.content, SUMMARY_LENGTH)
            safe_print(f"  {symbols.arrow} {content_display}")

            # Increment use count
            self._cli.memos.increment_use(memo.id)

    def candidates(self, include_dismissed: bool = False):
        """
        Show AI-detected candidate patterns.

        Args:
            include_dismissed: Whether to show dismissed candidates
        """
        symbols = self.symbols
        candidates = self._cli.memos.list_candidates(include_dismissed)
        pending = self._cli.memos.get_pending_suggestions()

        if not candidates:
            print("\nNo candidates detected.")
            print("\nCandidates are patterns I detect from repeated instructions.")
            print("When you repeat something often, I'll suggest saving it as a memo.")
            return

        print(f"\nAI-Detected Patterns ({len(candidates)}):")
        print()

        # Show pending promotions first
        if pending:
            print(f"{symbols.tension} Ready to promote ({len(pending)}):")
            for cand in pending:
                content_display = truncate(cand.content, SUMMARY_LENGTH - 20)
                ctx_display = f"[{', '.join(cand.contexts[:3])}]" if cand.contexts else ""
                safe_print(f"  {self._cli.format_id(cand.id)} {content_display}")
                print(f"           Seen {cand.count}x in {len(cand.sessions)} session(s) {ctx_display}")
            print()
            print(f"  {symbols.arrow} Promote: babel memo --promote <id>")
            print(f"  {symbols.arrow} Dismiss: babel memo --dismiss <id>")
            print()

        # Show other candidates
        other = [c for c in candidates if c not in pending]
        if other:
            print(f"Tracking ({len(other)}):")
            for cand in other:
                status = "(dismissed)" if cand.status == "dismissed" else ""
                content_display = truncate(cand.content, SUMMARY_LENGTH - 20)
                safe_print(f"  {self._cli.format_id(cand.id)} {content_display} {status}")
                print(f"           Seen {cand.count}x")

    def add_candidate(self, content: str, contexts: Optional[List[str]] = None):
        """
        Register an AI-detected pattern (called by AI, not user).

        Args:
            content: The detected pattern
            contexts: Contexts where observed
        """
        candidate = self._cli.memos.add_candidate(content, contexts)

        # Check if we should suggest promotion
        if self._cli.memos.should_suggest_promotion(candidate):
            symbols = self.symbols
            content_display = truncate(candidate.content, SUMMARY_LENGTH)
            print(f"\n{symbols.purpose} I've noticed you repeat this often:")
            safe_print(f"  \"{content_display}\"")
            print(f"\n  Seen {candidate.count}x across {len(candidate.sessions)} session(s).")
            print(f"\n  Save as memo? babel memo --promote {candidate.id}")
            print(f"  Dismiss:       babel memo --dismiss {candidate.id}")

    def promote(self, candidate_id: str, contexts: Optional[List[str]] = None):
        """
        Promote a candidate to memo.

        Args:
            candidate_id: Candidate ID or prefix
            contexts: Optional override contexts
        """
        symbols = self.symbols

        # Find candidate using centralized resolve_id
        candidates = self._cli.memos.list_candidates()
        candidate_ids = [c.id for c in candidates]
        resolved_id = self._cli.resolve_id(candidate_id, candidate_ids, "candidate")
        candidate = next((c for c in candidates if c.id == resolved_id), None) if resolved_id else None

        if not candidate:
            print(f"\nCandidate not found: {candidate_id}")
            print("See candidates: babel memo --candidates")
            return

        memo = self._cli.memos.promote(resolved_id, contexts)

        if memo:
            print(f"\n{symbols.check_pass} Promoted to memo:")
            print(f"  {self._cli.format_id(memo.id)} {memo.content}")
            if memo.contexts:
                print(f"  Contexts: {', '.join(memo.contexts)}")
            print(f"\nThis will now surface automatically in relevant contexts.")

            # Succession hint (centralized)
            from ..output import end_command
            end_command("memo", {})
        else:
            print(f"\nFailed to promote candidate: {candidate_id}")

    def dismiss(self, candidate_id: str):
        """
        Dismiss a candidate (won't suggest again).

        Args:
            candidate_id: Candidate ID or prefix
        """
        symbols = self.symbols

        if self._cli.memos.dismiss(candidate_id):
            print(f"\n{symbols.check_pass} Candidate dismissed.")
            print("I won't suggest this pattern again.")

            # Succession hint (centralized)
            from ..output import end_command
            end_command("memo", {})
        else:
            print(f"\nCandidate not found: {candidate_id}")

    def suggest(self):
        """
        Show pending promotion suggestions.

        Alias for candidates filtered to threshold-reached only.
        """
        symbols = self.symbols
        pending = self._cli.memos.get_pending_suggestions()

        if not pending:
            print("\nNo pending suggestions.")
            print("\nI'll suggest patterns when you repeat instructions often.")
            return

        print(f"\n{symbols.purpose} Suggestions based on your repeated instructions:")
        print()

        for cand in pending:
            content_display = truncate(cand.content, SUMMARY_LENGTH - 10)
            ctx_display = f"[{', '.join(cand.contexts[:3])}]" if cand.contexts else ""

            safe_print(f"  {self._cli.format_id(cand.id)} \"{content_display}\"")
            print(f"           Seen {cand.count}x {ctx_display}")
            print()

        print(f"Promote: babel memo --promote <id>")
        print(f"Dismiss: babel memo --dismiss <id>")
        print(f"Promote all: babel memo --promote-all")

    def promote_all(self):
        """
        Promote all pending candidates to memos.
        """
        symbols = self.symbols
        pending = self._cli.memos.get_pending_suggestions()

        if not pending:
            print("\nNo pending candidates to promote.")
            return

        promoted = 0
        for cand in pending:
            memo = self._cli.memos.promote(cand.id)
            if memo:
                promoted += 1
                safe_print(f"  {symbols.check_pass} {self._cli.format_id(memo.id)} {truncate(memo.content, 50)}")

        print(f"\nPromoted {promoted} candidate(s) to memos.")

    def stats(self):
        """
        Show memo statistics.
        """
        stats = self._cli.memos.stats()

        print("\nMemo Statistics:")
        print(f"  Saved memos:        {stats['memos']}")
        print(f"  Init memos:         {stats['init_memos']}")
        print(f"  With contexts:      {stats['with_contexts']}")
        print(f"  Total uses:         {stats['total_uses']}")
        print(f"  Pending candidates: {stats['candidates']}")
        print(f"  Ready to promote:   {stats['pending_suggestions']}")


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'memo'


def register_parser(subparsers):
    """Register memo command parser."""
    p = subparsers.add_parser('memo', help='Save persistent preferences (reduces repetition)')
    p.add_argument('content', nargs='?', help='Memo content to save')
    p.add_argument('--context', '-c', action='append', dest='contexts',
                   help='Context where this applies (can repeat)')
    p.add_argument('--init', '-i', action='store_true',
                   help='Foundational instruction - surfaces at session start via status')
    p.add_argument('--list', '-l', action='store_true', help='List all memos')
    p.add_argument('--list-init', action='store_true', help='List only init memos')
    p.add_argument('--remove', '-r', metavar='ID', help='Remove memo by ID')
    p.add_argument('--update', '-u', metavar='ID', help='Update memo by ID')
    p.add_argument('--promote-init', metavar='ID', help='Make memo foundational (init)')
    p.add_argument('--demote-init', metavar='ID', help='Make memo regular (not init)')
    p.add_argument('--candidates', action='store_true', help='Show AI-detected patterns')
    p.add_argument('--promote', metavar='ID', help='Promote candidate to memo')
    p.add_argument('--promote-all', action='store_true', help='Promote all pending candidates')
    p.add_argument('--dismiss', metavar='ID', help='Dismiss a candidate')
    p.add_argument('--suggest', action='store_true', help='Show pending promotion suggestions')
    p.add_argument('--relevant', metavar='CONTEXT', help='Show memos relevant to context')
    p.add_argument('--stats', action='store_true', help='Show memo statistics')
    return p


def handle(cli, args):
    """Handle memo command dispatch."""
    cmd = cli._memo_cmd
    if args.list:
        cmd.list_memos()
    elif args.list_init:
        cmd.list_memos(init_only=True)
    elif args.remove:
        cmd.remove(args.remove)
    elif args.update:
        cmd.update(args.update, args.content)
    elif args.promote_init:
        cmd.promote_init(args.promote_init)
    elif args.demote_init:
        cmd.demote_init(args.demote_init)
    elif args.candidates:
        cmd.show_candidates()
    elif args.promote:
        cmd.promote(args.promote)
    elif args.promote_all:
        cmd.promote_all()
    elif args.dismiss:
        cmd.dismiss(args.dismiss)
    elif args.suggest:
        cmd.suggest()
    elif args.relevant:
        cmd.show_relevant(args.relevant)
    elif args.stats:
        cmd.stats()
    elif args.content:
        cmd.add(args.content, contexts=args.contexts, init=args.init)
    else:
        print("Usage:")
        print("  babel memo \"instruction\"             Save memo")
        print("  babel memo \"text\" --init             Save as init memo")
        print("  babel memo --list                    List memos")
        print("  babel memo --list-init               List init memos")
        print("  babel memo --remove <id>             Remove memo")
