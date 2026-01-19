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

        print(f"\n? Open question raised [{question.id[:8]}]{domain_tag}")
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
        end_command("questions", {"has_open": has_open})

    def _questions_as_output(self, verbose: bool = False, full: bool = False):
        """Return questions data as OutputSpec for rendering."""
        from babel.output import OutputSpec

        stats = self.questions.stats()
        open_questions = self.questions.get_open_questions()

        rows = []
        for q in open_questions:
            domain_tag = f"[{q.domain}]" if q.domain else "-"

            rows.append({
                "id": q.id[:8],
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

        # Find question
        questions_list = self.questions.get_open_questions()
        target = None
        for q in questions_list:
            if q.id.startswith(question_id):
                target = q
                break

        if not target:
            print(f"Open question not found: {question_id}")
            print("\nOpen questions:")
            for q in questions_list[:5]:
                print(f"  {q.id[:8]} | {q.content[:40]}...")
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

            print(f"\n{icon} Question resolved [{target.id[:8]}]")
            print(f"  Question: {target.content[:50]}...")
            print(f"  Outcome: {outcome}")
            print(f"  Resolution: {resolution}")

            # Succession hint (centralized)
            from ..output import end_command
            remaining = self.questions.count_open()
            end_command("resolve-question", {"has_remaining": remaining > 0})
        else:
            print("Failed to resolve question.")
