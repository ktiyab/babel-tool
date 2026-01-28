"""
QuestionsCommand — Open questions and ambiguity management

Handles acknowledged unknowns (P10: Ambiguity Management):
- Raising open questions
- Viewing question status
- Resolving questions when evidence sufficient
"""


from ..commands.base import BaseCommand
from ..core.domains import suggest_domain_for_capture, validate_domain
from ..tracking.ambiguity import format_question, format_questions_summary
from ..presentation.formatters import generate_summary, format_timestamp
from ..presentation.template import OutputTemplate


class QuestionsCommand(BaseCommand):
    """
    Command for managing open questions.

    P10: Ambiguity Management — holding uncertainty is epistemic maturity.
    Acknowledge what you don't know rather than forcing premature closure.
    """

    def question(self, content: str, context: str = None, domain: str = None, batch_mode: bool = False):
        """
        Raise an open question (P10: holding ambiguity is epistemic maturity).

        Args:
            content: The question
            context: Why this question matters
            domain: Related expertise domain
            batch_mode: Queue for review (AI-safe)
        """
        symbols = self.symbols

        # Auto-suggest domain if not provided
        suggested_domain = None
        if not domain:
            suggested_domain = suggest_domain_for_capture(content)

        # Validate explicit domain
        if domain and not validate_domain(domain):
            print(f"Warning: Unknown domain '{domain}'. Using anyway.")

        question_obj = self.questions.raise_question(
            content=content,
            context=context,
            domain=domain or suggested_domain
        )

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL QUESTION", "P10: Ambiguity Management")
        template.legend({
            "?": "open question (acknowledged unknown)",
            symbols.check_pass: "resolved"
        })

        domain_tag = f" [{question_obj.domain}]" if question_obj.domain else ""

        question_lines = [
            f"? Open question raised {self._cli.format_id(question_obj.id)}{domain_tag}",
            f"  {content}"
        ]
        if context:
            question_lines.append(f"  Context: {context}")
        question_lines.append("")
        question_lines.append("This is an acknowledged unknown — not a failure.")

        template.section("QUESTION RAISED", "\n".join(question_lines))
        template.footer(f"Resolve when evidence is sufficient → babel resolve-question {self._cli.codec.encode(question_obj.id)} \"answer\"")

        output = template.render(command="question", context={})
        print(output)

    def questions_cmd(self, verbose: bool = False, full: bool = False, output_format: str = None):
        """
        Show open questions (P10: acknowledged unknowns).

        Args:
            verbose: Show full details
            full: Show full content without truncation
            output_format: If specified, return OutputSpec for rendering
        """
        symbols = self.symbols

        # If output_format specified, return OutputSpec
        if output_format:
            return self._questions_as_output(verbose, full)

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL QUESTIONS", "P10: Acknowledged Unknowns")
        template.legend({
            "?": "open question",
            symbols.check_pass: "resolved",
            symbols.arrow: "superseded"
        })

        # Summary section
        template.section("SUMMARY", format_questions_summary(self.questions, full=full))

        # Verbose: show all open questions
        if verbose:
            open_questions = self.questions.get_open_questions()
            if open_questions:
                question_lines = []
                for q in open_questions:
                    question_lines.append(format_question(q, verbose=True, full=full))
                template.section("OPEN QUESTIONS", "\n\n".join(question_lines))

        # Footer
        has_open = self.questions.count_open() > 0
        if has_open:
            template.footer(f"{self.questions.count_open()} open question(s) — holding ambiguity")
        else:
            template.footer("No open questions — all unknowns resolved")

        output = template.render(command="questions", context={
            "has_questions": has_open,
            "no_questions": not has_open
        })
        print(output)

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
                "time": format_timestamp(q.created_at),  # P12: Time always shown
                "question": generate_summary(q.content) if not full else q.content,
                "domain": domain_tag,
                "status": q.status,
                "context": (generate_summary(q.context) if q.context else "-") if not full else (q.context or "-")
            })

        title = f"Open Questions: {stats['open']}" if stats['open'] > 0 else "No open questions"
        if stats['resolved'] > 0:
            title += f" | Resolved: {stats['resolved']}"

        return OutputSpec(
            data=rows,
            shape="table",
            columns=["ID", "Time", "Question", "Domain", "Status", "Context"],
            column_keys=["id", "time", "question", "domain", "status", "context"],
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

        # Build template
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL RESOLVE-QUESTION", "P10: Evidence Sufficient")
        template.legend({
            symbols.check_pass: "answered",
            symbols.local: "dissolved (became irrelevant)",
            symbols.arrow: "superseded (replaced)"
        })

        if not target:
            error_lines = [f"Open question not found: {question_id}", "", "Open questions:"]
            for q in questions_list[:5]:
                error_lines.append(f"  {self._cli.format_id(q.id)} {generate_summary(q.content)}")
            template.section("ERROR", "\n".join(error_lines))
            template.footer("Check question ID and try again")
            print(template.render())
            return

        # Validate outcome
        valid_outcomes = ["answered", "dissolved", "superseded"]
        if outcome not in valid_outcomes:
            error_lines = [
                f"Invalid outcome: {outcome}",
                f"Valid outcomes: {', '.join(valid_outcomes)}",
                "  answered -- question was resolved with an answer",
                "  dissolved -- question became irrelevant",
                "  superseded -- replaced by a different question"
            ]
            template.section("ERROR", "\n".join(error_lines))
            template.footer("Use a valid outcome")
            print(template.render())
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

            resolved_lines = [
                f"{icon} Question resolved {self._cli.format_id(target.id)}",
                f"  Question: {generate_summary(target.content)}",
                f"  Outcome: {outcome}",
                f"  Resolution: {resolution}"
            ]
            template.section("RESOLVED", "\n".join(resolved_lines))

            remaining = self.questions.count_open()
            if remaining > 0:
                template.footer(f"{remaining} question(s) remaining")
            else:
                template.footer("All questions resolved")

            output = template.render(command="resolve-question", context={"has_remaining": remaining > 0})
            print(output)
        else:
            template.section("ERROR", "Failed to resolve question.")
            template.footer("Check question ID and try again")
            print(template.render())


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
