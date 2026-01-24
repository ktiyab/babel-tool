"""
QuestionsCommand — Open questions and ambiguity management

Handles acknowledged unknowns (P10: Ambiguity Management):
- Raising open questions
- Viewing question status
- Resolving questions when evidence sufficient
"""

from typing import Optional

from ..commands.base import BaseCommand
from ..core.domains import suggest_domain_for_capture, validate_domain
from ..tracking.ambiguity import format_question, format_questions_summary


class QuestionsCommand(BaseCommand):
    """
    Command for managing open questions.

    P10: Ambiguity Management — holding uncertainty is epistemic maturity.
    Acknowledge what you don't know rather than forcing premature closure.
    """

    def question(self, content: str, context: str = None, domain: str = None):
        """
        Raise an open question (P10: holding ambiguity is epistemic maturity).

        Args:
            content: The question
            context: Why this question matters
            domain: Related expertise domain
        """
        # Auto-suggest domain if not provided
        suggested_domain = None
        if not domain:
            suggested_domain = suggest_domain_for_capture(content)

        # Validate explicit domain
        if domain and not validate_domain(domain):
            print(f"Warning: Unknown domain '{domain}'. Using anyway.")

        question = self.questions.raise_question(
            content=content,
            context=context,
            domain=domain or suggested_domain
        )

        domain_tag = f" [{question.domain}]" if question.domain else ""

        print(f"\n? Open question raised {self._cli.format_id(question.id)}{domain_tag}")
        print(f"  {content}")
        if context:
            print(f"  Context: {context}")
        print()
        print("This is an acknowledged unknown -- not a failure.")
        print("Resolve when evidence is sufficient: babel resolve-question ...")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("question", {})

    def questions_cmd(self, verbose: bool = False, full: bool = False, output_format: str = None):
        """
        Show open questions (P10: acknowledged unknowns).

        Args:
            verbose: Show full details
            full: Show full content without truncation
            output_format: If specified, return OutputSpec for rendering
        """
        # If output_format specified, return OutputSpec
        if output_format:
            return self._questions_as_output(verbose, full)

        # Original behavior: print directly
        print(format_questions_summary(self.questions, full=full))

        if verbose:
            open_questions = self.questions.get_open_questions()
            if open_questions:
                print("\n" + "-" * 50)
                for q in open_questions:
                    print()
                    print(format_question(q, verbose=True, full=full))

        # Succession hint (centralized)
        from ..output import end_command
        has_open = self.questions.count_open() > 0
        end_command("questions", {"has_questions": has_open, "no_questions": not has_open})

    def _questions_as_output(self, verbose: bool = False, full: bool = False):
        """Return questions data as OutputSpec for rendering."""
        from babel.output import OutputSpec

        stats = self.questions.stats()
        open_questions = self.questions.get_open_questions()

        rows = []
        for q in open_questions:
            domain_tag = f"[{q.domain}]" if q.domain else "-"

            rows.append({
                "id": self._cli.codec.encode(q.id),
                "question": q.content[:50] if not full else q.content,
                "domain": domain_tag,
                "status": q.status,
                "context": (q.context[:30] if q.context else "-") if not full else (q.context or "-")
            })

        title = f"Open Questions: {stats['open']}" if stats['open'] > 0 else "No open questions"
        if stats['resolved'] > 0:
            title += f" | Resolved: {stats['resolved']}"

        return OutputSpec(
            data=rows,
            shape="table",
            columns=["ID", "Question", "Domain", "Status", "Context"],
            column_keys=["id", "question", "domain", "status", "context"],
            title=title,
            empty_message="No open questions. All unknowns are acknowledged and resolved."
        )

    def resolve_question(
        self,
        question_id: str,
        resolution: str,
        outcome: str = "answered"
    ):
        """
        Resolve an open question (P10: only when evidence sufficient).

        Args:
            question_id: Question ID (or prefix)
            resolution: The answer or conclusion
            outcome: answered | dissolved | superseded
        """
        symbols = self.symbols

        # Find question using centralized resolve_id
        questions_list = self.questions.get_open_questions()
        candidate_ids = [q.id for q in questions_list]
        resolved_id = self._cli.resolve_id(question_id, candidate_ids, "question")
        target = next((q for q in questions_list if q.id == resolved_id), None) if resolved_id else None

        if not target:
            print(f"Open question not found: {question_id}")
            print("\nOpen questions:")
            for q in questions_list[:5]:
                print(f"  {self._cli.format_id(q.id)} {q.content[:40]}...")
            return

        # Validate outcome
        valid_outcomes = ["answered", "dissolved", "superseded"]
        if outcome not in valid_outcomes:
            print(f"Invalid outcome: {outcome}")
            print(f"Valid outcomes: {', '.join(valid_outcomes)}")
            print("  answered -- question was resolved with an answer")
            print("  dissolved -- question became irrelevant")
            print("  superseded -- replaced by a different question")
            return

        success = self.questions.resolve(
            question_id=target.id,
            resolution=resolution,
            outcome=outcome
        )

        if success:
            outcome_icons = {
                "answered": symbols.check_pass,
                "dissolved": symbols.local,
                "superseded": symbols.arrow
            }
            icon = outcome_icons.get(outcome, symbols.validated)

            print(f"\n{icon} Question resolved {self._cli.format_id(target.id)}")
            print(f"  Question: {target.content[:50]}...")
            print(f"  Outcome: {outcome}")
            print(f"  Resolution: {resolution}")

            # Succession hint (centralized)
            from ..output import end_command
            remaining = self.questions.count_open()
            end_command("resolve-question", {"has_remaining": remaining > 0})
        else:
            print("Failed to resolve question.")


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

# Multiple commands registered by this module
COMMAND_NAMES = ['questions', 'question', 'resolve-question']


def register_parser(subparsers):
    """Register questions, question, and resolve-question command parsers."""
    # questions command (list)
    p1 = subparsers.add_parser('questions', help='Show open questions (P10: acknowledged unknowns)')
    p1.add_argument('-v', '--verbose', action='store_true', help='Show full details')
    p1.add_argument('--full', action='store_true', help='Show full content without truncation')
    p1.add_argument('--format', '-f', choices=['auto', 'table', 'list', 'json'],
                    help='Output format (overrides config)')

    # question command (add)
    p2 = subparsers.add_parser('question', help='Raise an open question (P10: holding ambiguity)')
    p2.add_argument('content', help='The question')
    p2.add_argument('--context', '-c', help='Why this question matters')
    p2.add_argument('--domain', '-d', help='Related expertise domain')
    p2.add_argument('--batch', '-b', action='store_true',
                    help='Queue for review (AI-safe)')

    # resolve-question command
    p3 = subparsers.add_parser('resolve-question', help='Resolve an open question (P10)')
    p3.add_argument('question_id', help='Question ID (or prefix)')
    p3.add_argument('resolution', help='The answer or conclusion')
    p3.add_argument('--outcome', default='answered',
                    choices=['answered', 'dissolved', 'superseded'],
                    help='How it was resolved (default: answered)')

    return p1, p2, p3


def handle(cli, args):
    """Handle questions, question, or resolve-question command dispatch."""
    if args.command == 'questions':
        cli._questions_cmd.questions_cmd(
            verbose=args.verbose,
            full=args.full,
            output_format=getattr(args, 'format', None)
        )
    elif args.command == 'question':
        cli._questions_cmd.question(
            args.content,
            context=args.context,
            domain=args.domain,
            batch_mode=getattr(args, 'batch', False)
        )
    elif args.command == 'resolve-question':
        cli._questions_cmd.resolve_question(
            args.question_id,
            args.resolution,
            outcome=args.outcome
        )
