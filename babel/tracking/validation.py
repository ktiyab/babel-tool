"""
Validation -- Dual-test truth tracking (P9 compliant)

P9: Dual-Test Truth
- Claims evaluated against BOTH consensus AND evidence
- Neither alone is sufficient
- Consensus without evidence is groupthink
- Evidence without consensus is noise

Validation Status Lifecycle:
    proposed   → Only captured, no validation
    consensus  → Team agreed, but no evidence yet (groupthink risk)
    evidenced  → Has evidence, but no consensus (unreviewed risk)
    validated  → BOTH consensus AND evidence (high confidence)

Integration:
- `babel endorse <id>` adds consensus
- `babel evidence <id> "..."` adds grounding
- `babel why` shows validation status
- `babel coherence` warns about partial validation
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from enum import Enum

from ..core.events import (
    DualEventStore, EventType,
    endorse_decision, evidence_decision, register_decision_for_validation
)
from ..core.scope import EventScope
from ..presentation.formatters import generate_summary
from ..presentation.symbols import get_symbols


class ValidationStatus(Enum):
    """Validation status for decisions (P9 compliant)."""
    PROPOSED = "proposed"      # Just captured, no validation
    CONSENSUS = "consensus"    # Team agreed, no evidence (groupthink risk)
    EVIDENCED = "evidenced"    # Has evidence, no consensus (unreviewed risk)
    VALIDATED = "validated"    # Both consensus AND evidence


@dataclass
class DecisionValidation:
    """Validation state for a decision."""
    decision_id: str
    endorsements: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None  # For display in validation status
    
    @property
    def endorsement_count(self) -> int:
        return len(self.endorsements)
    
    @property
    def evidence_count(self) -> int:
        return len(self.evidence)
    
    @property
    def endorsers(self) -> Set[str]:
        return {e["author"] for e in self.endorsements}
    
    @property
    def has_consensus(self) -> bool:
        """Consensus requires at least 1 endorsement (solo project threshold)."""
        return self.endorsement_count >= 1
    
    @property
    def has_evidence(self) -> bool:
        return self.evidence_count >= 1
    
    @property
    def status(self) -> ValidationStatus:
        """Compute validation status (P9: dual-test truth)."""
        if self.has_consensus and self.has_evidence:
            return ValidationStatus.VALIDATED
        elif self.has_consensus:
            return ValidationStatus.CONSENSUS  # Groupthink risk
        elif self.has_evidence:
            return ValidationStatus.EVIDENCED  # Unreviewed risk
        else:
            return ValidationStatus.PROPOSED
    
    @property
    def risk_warning(self) -> Optional[str]:
        """Return risk warning if partially validated."""
        if self.status == ValidationStatus.CONSENSUS:
            return "Groupthink risk: Team agreed but no evidence provided"
        elif self.status == ValidationStatus.EVIDENCED:
            return "Unreviewed risk: Has evidence but lacks team consensus"
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "status": self.status.value,
            "endorsement_count": self.endorsement_count,
            "evidence_count": self.evidence_count,
            "endorsers": list(self.endorsers),
            "has_consensus": self.has_consensus,
            "has_evidence": self.has_evidence,
            "risk_warning": self.risk_warning
        }


class ValidationTracker:
    """
    Track validation status for decisions (P9 compliant).
    
    P9: Dual-Test Truth
    - Consensus alone is groupthink
    - Evidence alone is noise
    - Both together = validated truth
    """
    
    def __init__(self, events: DualEventStore):
        self.events = events
        self._cache: Optional[Dict[str, DecisionValidation]] = None
    
    def _load_validations(self) -> Dict[str, DecisionValidation]:
        """Load all validation data from events."""
        if self._cache is not None:
            return self._cache

        validations: Dict[str, DecisionValidation] = {}

        # Load registration events first (so summary is available)
        registration_events = self.events.read_by_type(EventType.DECISION_REGISTERED)
        for event in registration_events:
            decision_id = event.data.get("decision_id", "")
            if decision_id and decision_id not in validations:
                validations[decision_id] = DecisionValidation(
                    decision_id=decision_id,
                    summary=event.data.get("summary")
                )

        # Load endorsement events
        endorsement_events = self.events.read_by_type(EventType.DECISION_ENDORSED)
        for event in endorsement_events:
            decision_id = event.data.get("decision_id", "")
            if decision_id not in validations:
                validations[decision_id] = DecisionValidation(decision_id=decision_id)
            
            validations[decision_id].endorsements.append({
                "id": event.id,
                "author": event.data.get("author", "unknown"),
                "comment": event.data.get("comment"),
                "timestamp": event.timestamp
            })
        
        # Load evidence events
        evidence_events = self.events.read_by_type(EventType.DECISION_EVIDENCED)
        for event in evidence_events:
            decision_id = event.data.get("decision_id", "")
            if decision_id not in validations:
                validations[decision_id] = DecisionValidation(decision_id=decision_id)
            
            validations[decision_id].evidence.append({
                "id": event.id,
                "content": event.data.get("content", ""),
                "evidence_type": event.data.get("evidence_type", "observation"),
                "author": event.data.get("author", "unknown"),
                "timestamp": event.timestamp
            })
        
        self._cache = validations
        return validations
    
    def invalidate_cache(self):
        """Invalidate cache after changes."""
        self._cache = None

    def register_decision(self, decision_id: str, summary: str = None, persist: bool = True):
        """
        Register a decision for validation tracking.

        Called when a decision is confirmed, so it appears in validation status
        even before any endorsements or evidence are added.

        Args:
            decision_id: ID of the decision to track
            summary: Summary text for display
            persist: If True, persist as event (default). False for in-memory only.
        """
        validations = self._load_validations()
        if decision_id not in validations:
            # Update in-memory cache
            validations[decision_id] = DecisionValidation(
                decision_id=decision_id,
                summary=summary
            )
            self._cache = validations

            # Persist as event for durability
            if persist:
                event = register_decision_for_validation(
                    decision_id=decision_id,
                    summary=summary or ""
                )
                # Registration is shared (visible to team)
                self.events.append(event, scope=EventScope.SHARED)
                self.invalidate_cache()

    # =========================================================================
    # Validation Operations
    # =========================================================================

    def endorse(
        self,
        decision_id: str,
        author: str = "user",
        comment: str = None
    ) -> bool:
        """
        Endorse a decision (P9: consensus component).
        
        Returns True if successful.
        """
        # Check if already endorsed by this author
        validation = self.get_validation(decision_id)
        if validation and author in validation.endorsers:
            return False  # Already endorsed
        
        event = endorse_decision(
            decision_id=decision_id,
            author=author,
            comment=comment
        )
        
        # Endorsements are shared (team consensus)
        self.events.append(event, scope=EventScope.SHARED)
        self.invalidate_cache()
        
        return True
    
    def add_evidence(
        self,
        decision_id: str,
        content: str,
        evidence_type: str = "observation",
        author: str = "user"
    ) -> bool:
        """
        Add evidence to a decision (P9: grounding component).
        
        Returns True if successful.
        """
        event = evidence_decision(
            decision_id=decision_id,
            content=content,
            evidence_type=evidence_type,
            author=author
        )
        
        # Evidence is shared (external grounding)
        self.events.append(event, scope=EventScope.SHARED)
        self.invalidate_cache()
        
        return True
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    def get_validation(self, decision_id: str) -> Optional[DecisionValidation]:
        """Get validation state for a decision."""
        validations = self._load_validations()
        return validations.get(decision_id)
    
    def get_status(self, decision_id: str) -> ValidationStatus:
        """Get validation status for a decision."""
        validation = self.get_validation(decision_id)
        if validation:
            return validation.status
        return ValidationStatus.PROPOSED
    
    def get_by_status(self, status: ValidationStatus) -> List[str]:
        """Get decision IDs with a specific validation status."""
        validations = self._load_validations()
        return [
            decision_id for decision_id, v in validations.items()
            if v.status == status
        ]
    
    def get_partially_validated(self) -> Dict[str, List[str]]:
        """Get decisions that are partially validated (P9 risk cases)."""
        validations = self._load_validations()
        
        return {
            "consensus_only": [
                decision_id for decision_id, v in validations.items()
                if v.status == ValidationStatus.CONSENSUS
            ],
            "evidence_only": [
                decision_id for decision_id, v in validations.items()
                if v.status == ValidationStatus.EVIDENCED
            ]
        }
    
    def get_validated(self) -> List[str]:
        """Get fully validated decision IDs."""
        return self.get_by_status(ValidationStatus.VALIDATED)
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        validations = self._load_validations()
        
        status_counts = {
            "proposed": 0,
            "consensus": 0,
            "evidenced": 0,
            "validated": 0
        }
        
        for v in validations.values():
            status_counts[v.status.value] += 1
        
        partial = self.get_partially_validated()
        
        return {
            "tracked": len(validations),
            "validated": status_counts["validated"],
            "partial": status_counts["consensus"] + status_counts["evidenced"],
            "groupthink_risk": len(partial["consensus_only"]),
            "unreviewed_risk": len(partial["evidence_only"]),
            "status_breakdown": status_counts
        }


# =============================================================================
# Formatting Functions
# =============================================================================

def format_validation_status(validation: DecisionValidation, verbose: bool = False, full: bool = False) -> str:
    """
    Format validation status for display.

    Args:
        validation: Validation state to format
        verbose: Show evidence details
        full: Show full content without truncation
    """
    symbols = get_symbols()
    lines = []

    status = validation.status

    # Status icon
    status_icons = {
        ValidationStatus.PROPOSED: symbols.proposed,
        ValidationStatus.CONSENSUS: symbols.consensus_only,
        ValidationStatus.EVIDENCED: symbols.evidence_only,
        ValidationStatus.VALIDATED: symbols.validated
    }
    icon = status_icons.get(status, "?")

    status_labels = {
        ValidationStatus.PROPOSED: "PROPOSED",
        ValidationStatus.CONSENSUS: "CONSENSUS ONLY",
        ValidationStatus.EVIDENCED: "EVIDENCED ONLY",
        ValidationStatus.VALIDATED: "VALIDATED"
    }
    label = status_labels.get(status, "UNKNOWN")

    lines.append(f"Validation Status: {icon} {label}")
    lines.append("")

    # Consensus
    if validation.has_consensus:
        lines.append(f"{symbols.check_pass} Consensus: {validation.endorsement_count} endorsements ({', '.join(validation.endorsers)})")
    else:
        needed = max(0, 2 - validation.endorsement_count)
        if validation.endorsement_count > 0:
            lines.append(f"{symbols.proposed} Consensus: {validation.endorsement_count} endorsement(s) (need {needed} more)")
        else:
            lines.append(f"{symbols.proposed} Consensus: None (needs team endorsement)")

    # Evidence
    if validation.has_evidence:
        lines.append(f"{symbols.check_pass} Evidence: {validation.evidence_count} item(s)")
        if verbose:
            for e in validation.evidence[-3:]:
                content = generate_summary(e['content'], full=full)
                lines.append(f"   {symbols.bullet} {content}")
    else:
        lines.append(f"{symbols.proposed} Evidence: None provided")

    # Risk warning
    if validation.risk_warning:
        lines.append("")
        lines.append(f"{symbols.check_warn} {validation.risk_warning}")

        if status == ValidationStatus.CONSENSUS:
            lines.append(f"  Consider: babel evidence {validation.decision_id[:8]} \"...\"")
        elif status == ValidationStatus.EVIDENCED:
            lines.append(f"  Consider: babel endorse {validation.decision_id[:8]}")

    return "\n".join(lines)


def format_validation_in_context(validation: DecisionValidation) -> str:
    """Format validation for display in 'why' query context."""
    symbols = get_symbols()
    status = validation.status

    status_icons = {
        ValidationStatus.PROPOSED: symbols.proposed,
        ValidationStatus.CONSENSUS: symbols.consensus_only,
        ValidationStatus.EVIDENCED: symbols.evidence_only,
        ValidationStatus.VALIDATED: symbols.validated
    }
    icon = status_icons.get(status, "?")

    if status == ValidationStatus.VALIDATED:
        return f"{icon} Validated ({validation.endorsement_count} endorsements, {validation.evidence_count} evidence)"
    elif status == ValidationStatus.CONSENSUS:
        return f"{icon} Consensus only -- needs evidence (groupthink risk)"
    elif status == ValidationStatus.EVIDENCED:
        return f"{icon} Evidenced only -- needs consensus (unreviewed)"
    else:
        return f"{icon} Proposed -- not yet validated"


def format_validation_summary(tracker: ValidationTracker, full: bool = False) -> str:
    """
    Format summary of validation status across decisions.

    Args:
        tracker: Validation tracker instance
        full: Show full content without truncation (reserved for future use)
    """
    symbols = get_symbols()
    stats = tracker.stats()

    lines = []

    if stats["tracked"] == 0:
        lines.append("No decisions tracked for validation.")
        return "\n".join(lines)

    lines.append(f"Validation Status: {stats['tracked']} decisions tracked")
    lines.append("")

    # Breakdown
    lines.append(f"{symbols.validated} Validated: {stats['validated']} (consensus + evidence)")

    if stats["partial"] > 0:
        lines.append(f"{symbols.consensus_only} Partial: {stats['partial']}")

        if stats["groupthink_risk"] > 0:
            lines.append(f"   {symbols.check_warn} {stats['groupthink_risk']} with consensus only (groupthink risk)")

        if stats["unreviewed_risk"] > 0:
            lines.append(f"   {symbols.check_warn} {stats['unreviewed_risk']} with evidence only (unreviewed)")

    return "\n".join(lines)
