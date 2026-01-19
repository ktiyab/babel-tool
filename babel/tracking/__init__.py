"""
Tracking — State tracking layer for Babel CLI

Contains tracking systems for:
- Validation: Decision validation (P5 dual-test truth)
- Tensions: Disagreement tracking (P4)
- Coherence: Alignment checking (P9)
- Ambiguity: Uncertainty detection (P10)
- Principles: Framework alignment checking (P1-P11)
"""

from .validation import ValidationStatus, DecisionValidation, ValidationTracker, format_validation_status, format_validation_summary
from .tensions import TensionTracker, Challenge, format_challenge, format_tensions_summary
from .coherence import CoherenceChecker, CoherenceResult, format_coherence_status
from .ambiguity import OpenQuestion, QuestionTracker, detect_uncertainty, format_question, format_questions_summary
from .principles import PrincipleStatus, PrincipleCheck, PrincipleResult, PrincipleChecker, format_principles_summary

__all__ = [
    # Validation
    "ValidationStatus", "DecisionValidation", "ValidationTracker",
    "format_validation_status", "format_validation_summary",
    # Tensions
    "TensionTracker", "Challenge", "format_challenge", "format_tensions_summary",
    # Coherence
    "CoherenceChecker", "CoherenceResult", "format_coherence_status",
    # Ambiguity (P10)
    "OpenQuestion", "QuestionTracker", "detect_uncertainty", "format_question", "format_questions_summary",
    # Principles (P1-P11)
    "PrincipleStatus", "PrincipleCheck", "PrincipleResult", "PrincipleChecker", "format_principles_summary",
]
