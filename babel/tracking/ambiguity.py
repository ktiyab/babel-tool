"""
Ambiguity -- Open question tracking (P10 compliant)

P10: Ambiguity Management
- When evidence is insufficient, ambiguity is explicitly recorded
- Unresolved tensions are tracked as first-class artifacts
- Premature resolution is considered a failure mode
- Holding ambiguity is a sign of epistemic maturity, not weakness

"Anomalies accumulate before paradigms shift."

This module is intentionally minimal. The AI layer handles:
- Detecting uncertainty language in captures
- Suggesting when to mark decisions uncertain
- Warning about premature resolution
- Surfacing ambiguity in conversation
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ..core.events import (
    DualEventStore, Event, EventType,
    raise_question, resolve_question
)
from ..core.scope import EventScope
from ..presentation.symbols import get_symbols, truncate, SUMMARY_LENGTH


# =============================================================================
# Uncertainty Detection (AI uses these patterns)
# =============================================================================

UNCERTAINTY_SIGNALS = [
    "not sure", "might", "maybe", "unclear", "uncertain",
    "need to revisit", "provisional", "for now", "temporary",
    "don't know", "tbd", "open question", "?",
    "could be wrong", "might need to", "possibly",
    "haven't decided", "still figuring", "not certain"
]

QUESTION_PATTERNS = [
    "open question:",
    "question:",
    "how should we",
    "how do we",
    "how can we",
    "what's the best way",
    "what is the right way",
    "we don't know",
    "we haven't figured",
    "we need to decide",
    "should we",
    "unknown:",
    "tbd:"
]


def detect_uncertainty(text: str) -> bool:
    """
    Detect if text contains uncertainty signals.
    AI uses this to suggest --uncertain flag.
    """
    text_lower = text.lower()
    return any(signal in text_lower for signal in UNCERTAINTY_SIGNALS)


def detect_question(text: str) -> bool:
    """
    Detect if text is phrased as an open question.
    AI uses this to suggest creating a question artifact.
    """
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in QUESTION_PATTERNS)


# =============================================================================
# Question Model
# =============================================================================

@dataclass
class OpenQuestion:
    """An open question (P10: acknowledged unknown)."""
    id: str
    content: str
    context: Optional[str]
    domain: Optional[str]
    author: str
    status: str  # "open" | "resolved"
    created_at: str
    resolution: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_event(cls, event: Event) -> "OpenQuestion":
        """Create OpenQuestion from event."""
        data = event.data
        return cls(
            id=event.id,
            content=data.get("content", ""),
            context=data.get("context"),
            domain=data.get("domain"),
            author=data.get("author", "unknown"),
            status=data.get("status", "open"),
            created_at=event.timestamp
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "context": self.context,
            "domain": self.domain,
            "author": self.author,
            "status": self.status,
            "created_at": self.created_at,
            "resolution": self.resolution
        }


# =============================================================================
# Question Tracker
# =============================================================================

class QuestionTracker:
    """
    Track open questions (P10 compliant).
    
    P10: Holding ambiguity is epistemic maturity, not weakness.
    Open questions are first-class artifacts, not failures.
    """
    
    def __init__(self, events: DualEventStore):
        self.events = events
        self._cache: Optional[Dict[str, OpenQuestion]] = None
    
    def _load_questions(self) -> Dict[str, OpenQuestion]:
        """Load all questions from events."""
        if self._cache is not None:
            return self._cache
        
        questions: Dict[str, OpenQuestion] = {}
        
        # Load question events
        question_events = self.events.read_by_type(EventType.QUESTION_RAISED)
        for event in question_events:
            question = OpenQuestion.from_event(event)
            questions[question.id] = question
        
        # Load resolution events
        resolution_events = self.events.read_by_type(EventType.QUESTION_RESOLVED)
        for event in resolution_events:
            question_id = event.data.get("question_id", "")
            if question_id in questions:
                questions[question_id].status = "resolved"
                questions[question_id].resolution = {
                    "id": event.id,
                    "resolution": event.data.get("resolution", ""),
                    "outcome": event.data.get("outcome", "answered"),
                    "author": event.data.get("author", "unknown"),
                    "timestamp": event.timestamp
                }
        
        self._cache = questions
        return questions
    
    def invalidate_cache(self):
        """Invalidate cache after changes."""
        self._cache = None
    
    # =========================================================================
    # Question Operations
    # =========================================================================
    
    def raise_question(
        self,
        content: str,
        context: str = None,
        domain: str = None,
        author: str = "user"
    ) -> OpenQuestion:
        """
        Raise an open question (P10: holding ambiguity).
        
        Returns the created OpenQuestion.
        """
        event = raise_question(
            content=content,
            context=context,
            domain=domain,
            author=author
        )
        
        # Questions are shared -- team needs visibility
        self.events.append(event, scope=EventScope.SHARED)
        self.invalidate_cache()
        
        return OpenQuestion.from_event(event)
    
    def resolve(
        self,
        question_id: str,
        resolution: str,
        outcome: str = "answered",
        author: str = "user"
    ) -> bool:
        """
        Resolve an open question (P10: only when evidence sufficient).
        
        Args:
            question_id: ID of the question
            resolution: The answer or conclusion
            outcome: "answered" | "dissolved" | "superseded"
        
        Returns True if successful.
        """
        questions = self._load_questions()
        
        if question_id not in questions:
            return False
        
        if questions[question_id].status == "resolved":
            return False  # Already resolved
        
        event = resolve_question(
            question_id=question_id,
            resolution=resolution,
            outcome=outcome,
            author=author
        )
        
        self.events.append(event, scope=EventScope.SHARED)
        self.invalidate_cache()
        
        return True
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    def get_question(self, question_id: str) -> Optional[OpenQuestion]:
        """Get a specific question by ID."""
        questions = self._load_questions()
        return questions.get(question_id)
    
    def get_open_questions(self) -> List[OpenQuestion]:
        """Get all open (unresolved) questions."""
        questions = self._load_questions()
        return [q for q in questions.values() if q.status == "open"]
    
    def get_resolved_questions(self) -> List[OpenQuestion]:
        """Get all resolved questions."""
        questions = self._load_questions()
        return [q for q in questions.values() if q.status == "resolved"]
    
    def count_open(self) -> int:
        """Count open questions."""
        return len(self.get_open_questions())
    
    def get_by_domain(self, domain: str) -> List[OpenQuestion]:
        """Get questions in a specific domain."""
        questions = self._load_questions()
        return [q for q in questions.values() if q.domain == domain]
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def stats(self) -> Dict[str, Any]:
        """Get question statistics."""
        questions = self._load_questions()
        open_questions = [q for q in questions.values() if q.status == "open"]
        resolved_questions = [q for q in questions.values() if q.status == "resolved"]
        
        return {
            "total": len(questions),
            "open": len(open_questions),
            "resolved": len(resolved_questions)
        }


# =============================================================================
# Premature Resolution Check
# =============================================================================

def check_premature_resolution(evidence_count: int, min_evidence: int = 2) -> Dict[str, Any]:
    """
    Check if resolving would be premature (P10 compliance).
    
    P10: Premature resolution is a failure mode.
    
    Args:
        evidence_count: Number of evidence items
        min_evidence: Minimum recommended evidence
    
    Returns:
        Dict with 'is_premature', 'warning', 'recommendation'
    """
    if evidence_count >= min_evidence:
        return {
            "is_premature": False,
            "warning": None,
            "recommendation": None
        }
    
    return {
        "is_premature": True,
        "warning": f"Only {evidence_count} evidence item(s). Resolution may be premature.",
        "recommendation": "Consider marking as uncertain or gathering more evidence."
    }


# =============================================================================
# Formatting Functions
# =============================================================================

def format_question(question: OpenQuestion, verbose: bool = False, full: bool = False) -> str:
    """
    Format a question for display.

    Args:
        question: Question to format
        verbose: Show context details
        full: Show full content without truncation
    """
    symbols = get_symbols()
    lines = []

    status_icon = "?" if question.status == "open" else symbols.check_pass
    domain_tag = f" [{question.domain}]" if question.domain else ""

    lines.append(f"{status_icon} Question [{question.id[:8]}]{domain_tag}")
    lines.append(f"  {truncate(question.content, SUMMARY_LENGTH, full)}")

    if verbose and question.context:
        lines.append(f"  Context: {truncate(question.context, SUMMARY_LENGTH, full)}")

    lines.append(f"  By: {question.author} | {question.created_at[:10]}")

    if question.resolution:
        r = question.resolution
        lines.append(f"  Resolved: {r['outcome']}")
        lines.append(f"    {truncate(r['resolution'], SUMMARY_LENGTH, full)}")

    return "\n".join(lines)


def format_questions_summary(tracker: QuestionTracker, full: bool = False) -> str:
    """
    Format summary of all open questions.

    Args:
        tracker: Question tracker instance
        full: Show full content without truncation
    """
    symbols = get_symbols()
    stats = tracker.stats()
    open_questions = tracker.get_open_questions()

    lines = []

    if stats["open"] == 0:
        lines.append("No open questions.")
        lines.append("(This is fine -- or you haven't recorded your unknowns yet)")
    else:
        lines.append(f"? Open Questions: {stats['open']}")
        lines.append("")
        lines.append("These are acknowledged unknowns, not failures:")
        lines.append("")

        for question in open_questions[:10]:
            domain_tag = f" [{question.domain}]" if question.domain else ""
            age = question.created_at[:10]
            content = truncate(question.content, SUMMARY_LENGTH, full)
            lines.append(f"  {symbols.bullet} [{question.id[:8]}]{domain_tag} {content}")
            lines.append(f"    Raised: {age} by {question.author}")

        if len(open_questions) > 10:
            lines.append(f"  ... and {len(open_questions) - 10} more")

    if stats["resolved"] > 0:
        lines.append("")
        lines.append(f"Resolved: {stats['resolved']} question(s) answered")

    return "\n".join(lines)


def format_uncertain_decision(event: Event, full: bool = False) -> str:
    """
    Format an uncertain decision for display.

    Args:
        event: Event containing uncertain decision
        full: Show full content without truncation
    """
    data = event.data
    content = truncate(data.get("content", ""), SUMMARY_LENGTH, full)
    reason = data.get("uncertainty_reason", "No reason given")

    return f"[?] UNCERTAIN: {content}\n  Reason: {reason}"
