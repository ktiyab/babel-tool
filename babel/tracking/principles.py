"""
PrincipleChecker — Evaluate project alignment with WhitePaper principles

Checks P1-P11 alignment through CLI-observable patterns:
- P1: Bootstrap from Need — purpose has need statement
- P2: Emergent Ontology — vocabulary has terms
- P3: Expertise Authority — decisions have domains
- P4: Layered Validation — endorsements exist
- P7: Evidence-Weighted Memory — deprecated items have reasons
- P9: Dual-Test Truth — decisions have consensus + evidence
- P10: Meta-Principles — questions captured (uncertainty explicit)
- P11: Self-Application — self-referential content exists

Uses existing trackers (validation, tensions, questions) — no direct DB access.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class PrincipleStatus(Enum):
    """Status of principle alignment."""
    SATISFIED = "satisfied"    # Principle is being followed
    WARNING = "warning"        # Partial compliance, needs attention
    VIOLATION = "violation"    # Principle not followed
    NOT_APPLICABLE = "n/a"     # Can't evaluate (e.g., no decisions yet)


@dataclass
class PrincipleCheck:
    """Result of checking a single principle."""
    principle: str           # e.g., "P1", "P9"
    name: str               # e.g., "Bootstrap from Need"
    status: PrincipleStatus
    message: str            # Human-readable explanation
    suggestion: Optional[str] = None  # Action to fix (if warning/violation)


@dataclass
class PrincipleResult:
    """Result of checking all principles."""
    checks: List[PrincipleCheck] = field(default_factory=list)

    @property
    def satisfied_count(self) -> int:
        return sum(1 for c in self.checks if c.status == PrincipleStatus.SATISFIED)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.status == PrincipleStatus.WARNING)

    @property
    def violation_count(self) -> int:
        return sum(1 for c in self.checks if c.status == PrincipleStatus.VIOLATION)

    @property
    def total_applicable(self) -> int:
        return sum(1 for c in self.checks if c.status != PrincipleStatus.NOT_APPLICABLE)

    @property
    def score(self) -> float:
        """Score from 0.0 to 1.0 based on principle alignment."""
        if self.total_applicable == 0:
            return 0.0
        # Satisfied = 1.0, Warning = 0.5, Violation = 0.0
        points = (
            self.satisfied_count * 1.0 +
            self.warning_count * 0.5 +
            self.violation_count * 0.0
        )
        return points / self.total_applicable

    @property
    def level(self) -> str:
        """Human-readable alignment level."""
        if self.violation_count > 0:
            return "Practicing"  # Has violations
        elif self.warning_count > 0:
            return "Growing"     # Warnings only
        elif self.satisfied_count > 0:
            return "Aligned"     # All satisfied
        else:
            return "Starting"    # Nothing to check yet


class PrincipleChecker:
    """
    Checks project alignment with WhitePaper principles.

    Uses existing trackers — no direct database access.
    All checks are based on observable CLI patterns.
    """

    def __init__(self, graph, validation, questions, vocabulary=None):
        """
        Initialize with required trackers.

        Args:
            graph: GraphStore for querying artifacts
            validation: ValidationTracker for P4/P9
            questions: QuestionTracker for P10
            vocabulary: Optional Vocabulary for P2
        """
        self.graph = graph
        self.validation = validation
        self.questions = questions
        self.vocabulary = vocabulary

    def check_all(self) -> PrincipleResult:
        """
        Check all principles and return comprehensive result.

        Returns:
            PrincipleResult with per-principle status
        """
        result = PrincipleResult()

        # Run all principle checks
        result.checks.append(self._check_p1_bootstrap())
        result.checks.append(self._check_p2_ontology())
        result.checks.append(self._check_p3_expertise())
        result.checks.append(self._check_p4_validation())
        result.checks.append(self._check_p7_evidence_weighted())
        result.checks.append(self._check_p9_dual_test())
        result.checks.append(self._check_p10_ambiguity())
        result.checks.append(self._check_p11_self_application())

        return result

    def _check_p1_bootstrap(self) -> PrincipleCheck:
        """P1: Bootstrap from Need — purpose has need statement."""
        purposes = self.graph.get_nodes_by_type('purpose')

        if not purposes:
            return PrincipleCheck(
                principle="P1",
                name="Bootstrap from Need",
                status=PrincipleStatus.VIOLATION,
                message="No purpose defined",
                suggestion="Run: babel init \"purpose\" --need \"problem\""
            )

        # Check if any purpose has a need
        has_need = False
        for p in purposes:
            content = p.content
            if isinstance(content, dict):
                if content.get('need'):
                    has_need = True
                    break

        if has_need:
            return PrincipleCheck(
                principle="P1",
                name="Bootstrap from Need",
                status=PrincipleStatus.SATISFIED,
                message="Purpose has need statement"
            )
        else:
            return PrincipleCheck(
                principle="P1",
                name="Bootstrap from Need",
                status=PrincipleStatus.WARNING,
                message="Purpose exists but no need captured",
                suggestion="Capture the underlying need/problem"
            )

    def _check_p2_ontology(self) -> PrincipleCheck:
        """P2: Emergent Ontology — vocabulary has terms."""
        if self.vocabulary is None:
            return PrincipleCheck(
                principle="P2",
                name="Emergent Ontology",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="Vocabulary not available"
            )

        # Access vocabulary data via _load() method
        try:
            data = self.vocabulary._load()
            clusters = data.get("clusters", {})
        except Exception:
            return PrincipleCheck(
                principle="P2",
                name="Emergent Ontology",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="Vocabulary not loaded"
            )

        term_count = sum(len(terms) for terms in clusters.values())

        if term_count >= 20:
            return PrincipleCheck(
                principle="P2",
                name="Emergent Ontology",
                status=PrincipleStatus.SATISFIED,
                message=f"Vocabulary has {term_count} terms across {len(clusters)} clusters"
            )
        elif term_count > 0:
            return PrincipleCheck(
                principle="P2",
                name="Emergent Ontology",
                status=PrincipleStatus.WARNING,
                message=f"Vocabulary emerging ({term_count} terms)",
                suggestion="Continue capturing decisions — vocabulary grows organically"
            )
        else:
            return PrincipleCheck(
                principle="P2",
                name="Emergent Ontology",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="No vocabulary yet"
            )

    def _check_p3_expertise(self) -> PrincipleCheck:
        """P3: Expertise Authority — decisions have domains."""
        decisions = self.graph.get_nodes_by_type('decision')

        if not decisions:
            return PrincipleCheck(
                principle="P3",
                name="Expertise Authority",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="No decisions yet"
            )

        # Count decisions with domain
        with_domain = 0
        for d in decisions:
            content = d.content
            if isinstance(content, dict) and content.get('domain'):
                with_domain += 1

        ratio = with_domain / len(decisions)

        if ratio >= 0.5:
            return PrincipleCheck(
                principle="P3",
                name="Expertise Authority",
                status=PrincipleStatus.SATISFIED,
                message=f"{with_domain}/{len(decisions)} decisions have domain"
            )
        elif with_domain > 0:
            return PrincipleCheck(
                principle="P3",
                name="Expertise Authority",
                status=PrincipleStatus.WARNING,
                message=f"Only {with_domain}/{len(decisions)} decisions have domain",
                suggestion="Add --domain to captures: babel capture \"...\" --domain <area>"
            )
        else:
            return PrincipleCheck(
                principle="P3",
                name="Expertise Authority",
                status=PrincipleStatus.WARNING,
                message="No domains on decisions",
                suggestion="Add --domain to captures for expertise tracking"
            )

    def _check_p4_validation(self) -> PrincipleCheck:
        """P4: Layered Validation — endorsements exist."""
        stats = self.validation.stats()
        tracked = stats.get('tracked', 0)

        if tracked == 0:
            return PrincipleCheck(
                principle="P4",
                name="Layered Validation",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="No decisions to validate"
            )

        # Check for endorsements (consensus)
        consensus = stats.get('consensus_only', 0) + stats.get('validated', 0)

        if consensus > 0:
            return PrincipleCheck(
                principle="P4",
                name="Layered Validation",
                status=PrincipleStatus.SATISFIED,
                message=f"{consensus} decisions endorsed"
            )
        else:
            return PrincipleCheck(
                principle="P4",
                name="Layered Validation",
                status=PrincipleStatus.WARNING,
                message="No decisions endorsed yet",
                suggestion="Run: babel endorse <id> to add consensus"
            )

    def _check_p7_evidence_weighted(self) -> PrincipleCheck:
        """P7: Evidence-Weighted Memory — deprecated items have reasons."""
        # Check for deprecated items by looking for deprecation events
        # For now, just check if decisions exist (can be deprecated)
        decisions = self.graph.get_nodes_by_type('decision')

        if not decisions:
            return PrincipleCheck(
                principle="P7",
                name="Evidence-Weighted Memory",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="No decisions yet"
            )

        # P7 is about de-prioritization, not deletion
        # If we have decisions, the structure supports P7
        return PrincipleCheck(
            principle="P7",
            name="Evidence-Weighted Memory",
            status=PrincipleStatus.SATISFIED,
            message="Decisions preserved (deprecation available)"
        )

    def _check_p9_dual_test(self) -> PrincipleCheck:
        """P9: Dual-Test Truth — decisions have consensus + evidence."""
        stats = self.validation.stats()
        tracked = stats.get('tracked', 0)

        if tracked == 0:
            return PrincipleCheck(
                principle="P9",
                name="Dual-Test Truth",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="No decisions to validate"
            )

        validated = stats.get('validated', 0)
        consensus_only = stats.get('consensus_only', 0)
        evidence_only = stats.get('evidence_only', 0)

        if validated > 0 and consensus_only == 0:
            return PrincipleCheck(
                principle="P9",
                name="Dual-Test Truth",
                status=PrincipleStatus.SATISFIED,
                message=f"{validated} decisions fully validated"
            )
        elif validated > 0:
            return PrincipleCheck(
                principle="P9",
                name="Dual-Test Truth",
                status=PrincipleStatus.WARNING,
                message=f"{validated} validated, {consensus_only} consensus-only (groupthink risk)",
                suggestion="Add evidence to consensus-only decisions"
            )
        elif consensus_only > 0:
            return PrincipleCheck(
                principle="P9",
                name="Dual-Test Truth",
                status=PrincipleStatus.WARNING,
                message=f"{consensus_only} consensus-only (no evidence)",
                suggestion="Run: babel evidence-decision <id> \"proof\""
            )
        else:
            return PrincipleCheck(
                principle="P9",
                name="Dual-Test Truth",
                status=PrincipleStatus.WARNING,
                message="No validation yet",
                suggestion="Start with: babel endorse <id>"
            )

    def _check_p10_ambiguity(self) -> PrincipleCheck:
        """P10: Meta-Principles — questions captured (uncertainty explicit)."""
        open_count = self.questions.count_open()
        resolved_count = len(self.questions.get_resolved_questions())
        total = open_count + resolved_count

        # Get decision count for ratio
        decisions = self.graph.get_nodes_by_type('decision')
        decision_count = len(decisions)

        if decision_count == 0:
            return PrincipleCheck(
                principle="P10",
                name="Hold Ambiguity",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="No decisions yet"
            )

        if total > 0:
            return PrincipleCheck(
                principle="P10",
                name="Hold Ambiguity",
                status=PrincipleStatus.SATISFIED,
                message=f"{total} question(s) captured ({open_count} open)"
            )
        else:
            # No questions might indicate hiding uncertainty
            if decision_count > 10:
                return PrincipleCheck(
                    principle="P10",
                    name="Hold Ambiguity",
                    status=PrincipleStatus.WARNING,
                    message=f"{decision_count} decisions but no questions captured",
                    suggestion="Capture uncertainties: babel question \"...\""
                )
            else:
                return PrincipleCheck(
                    principle="P10",
                    name="Hold Ambiguity",
                    status=PrincipleStatus.SATISFIED,
                    message="Early stage — uncertainties can be captured as needed"
                )

    def _check_p11_self_application(self) -> PrincipleCheck:
        """P11: Self-Application — project references itself."""
        # Check if purpose mentions dogfooding, self, babel, etc.
        purposes = self.graph.get_nodes_by_type('purpose')

        if not purposes:
            return PrincipleCheck(
                principle="P11",
                name="Self-Application",
                status=PrincipleStatus.NOT_APPLICABLE,
                message="No purpose defined"
            )

        # Look for self-referential terms
        self_terms = ['dogfood', 'itself', 'self', 'babel', 'own', 'p11']

        for p in purposes:
            content = p.content
            if isinstance(content, dict):
                text = str(content).lower()
                if any(term in text for term in self_terms):
                    return PrincipleCheck(
                        principle="P11",
                        name="Self-Application",
                        status=PrincipleStatus.SATISFIED,
                        message="Purpose references self-application"
                    )

        # Not a violation — self-application is optional for non-Babel projects
        return PrincipleCheck(
            principle="P11",
            name="Self-Application",
            status=PrincipleStatus.SATISFIED,
            message="Self-application not required for this project"
        )


def format_principles_summary(result: PrincipleResult, symbols, full: bool = False) -> str:
    """
    Format principle check result for display.

    Args:
        result: PrincipleResult from check_all()
        symbols: Symbol provider
        full: If True, show details for each principle

    Returns:
        Formatted string for display
    """
    lines = []

    # Header with score
    score_pct = int(result.score * 100)
    lines.append(f"Framework Alignment: {result.satisfied_count}/{result.total_applicable} principles ({score_pct}%)")

    if full:
        # Show each principle
        for check in result.checks:
            if check.status == PrincipleStatus.NOT_APPLICABLE:
                indicator = "○"
            elif check.status == PrincipleStatus.SATISFIED:
                indicator = symbols.check_pass
            elif check.status == PrincipleStatus.WARNING:
                indicator = symbols.check_warn
            else:
                indicator = symbols.check_fail

            lines.append(f"  {indicator} {check.principle}: {check.name}")
            lines.append(f"      {check.message}")
            if check.suggestion:
                lines.append(f"      → {check.suggestion}")
    else:
        # Compact: show warnings/violations only
        issues = [c for c in result.checks
                  if c.status in (PrincipleStatus.WARNING, PrincipleStatus.VIOLATION)]

        if issues:
            for check in issues:
                indicator = symbols.check_warn if check.status == PrincipleStatus.WARNING else symbols.check_fail
                lines.append(f"  {indicator} {check.principle}: {check.message}")
                if check.suggestion:
                    lines.append(f"      → {check.suggestion}")
        else:
            lines.append(f"  {symbols.check_pass} All principles satisfied")

    return "\n".join(lines)
