"""
Extractor — LLM-based structure extraction (P-FRICTION)

Capture is conversational. Structuring is system-proposed.
Human confirms. This module proposes.

Modes:
- Real: Uses configured LLM provider (Claude, OpenAI, Gemini)
- Mock: Keyword-based fallback for testing
- Offline: Queues for later processing (TD4)

Context-Aware Extraction:
- Injects existing artifacts into prompt to prevent duplicates
- Uses text-based similarity for offline-first deduplication (HC3)
- Optional semantic enhancement when online
"""

import json
import re
from typing import Dict, Any, Optional, List, TYPE_CHECKING, Callable, Set
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

from ..presentation.symbols import sanitize_control_chars

if TYPE_CHECKING:
    from .providers import LLMProvider, LLMResponse


@dataclass
class Proposal:
    """Proposed structure from conversation."""
    source_id: str
    artifact_type: str
    content: Dict[str, Any]
    confidence: float
    rationale: str


@dataclass
class QueuedExtraction:
    """Extraction request queued for later (offline support)."""
    text: str
    source_id: str
    queued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExistingArtifact:
    """Summary of an existing artifact for context injection."""
    artifact_type: str
    summary: str
    artifact_id: str = ""


# =============================================================================
# Text Similarity (Offline-First per HC3)
# =============================================================================

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Lowercase, strip, collapse whitespace
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    # Remove punctuation for fuzzy matching
    text = re.sub(r'[^\w\s]', '', text)
    return text


def extract_keywords(text: str) -> Set[str]:
    """Extract meaningful keywords from text."""
    words = normalize_text(text).split()
    # Filter short words and common stopwords
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'be', 'to', 'of', 'in',
                 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'and', 'or',
                 'but', 'not', 'this', 'that', 'use', 'using', 'used'}
    return {w for w in words if len(w) >= 3 and w not in stopwords}


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity using Jaccard coefficient.

    Offline-first (HC3 compliant): No API calls, pure text comparison.
    Returns 0.0-1.0 where 1.0 is identical.
    """
    keywords1 = extract_keywords(text1)
    keywords2 = extract_keywords(text2)

    if not keywords1 or not keywords2:
        return 0.0

    intersection = keywords1 & keywords2
    union = keywords1 | keywords2

    return len(intersection) / len(union) if union else 0.0


class ExtractionQueue:
    """
    Queue for offline extraction requests (TD4: local-first).
    
    When LLM unavailable, requests queue here.
    Process when connection restores.
    """
    
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def add(self, text: str, source_id: str):
        """Add extraction request to queue."""
        item = QueuedExtraction(text=text, source_id=source_id)
        with open(self.path, 'a') as f:
            f.write(json.dumps({
                'text': item.text,
                'source_id': item.source_id,
                'queued_at': item.queued_at
            }) + '\n')
    
    def get_all(self) -> List[QueuedExtraction]:
        """Get all queued items."""
        items = []
        if self.path.exists():
            with open(self.path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        items.append(QueuedExtraction(**data))
        return items
    
    def clear(self):
        """Clear queue after processing."""
        if self.path.exists():
            self.path.unlink()
    
    def count(self) -> int:
        return len(self.get_all())


class Extractor:
    """
    Extract structure from natural language.
    
    Per II (Interpretation Interface):
    - AI Extractor proposes, never commits
    - Confidence signaled on all outputs
    - Human confirmation required (HC2)
    
    Per TD4 (Local-first):
    - Works offline with queue
    - Processes queue when LLM available
    """
    
    SYSTEM_PROMPT = """You are an extraction assistant for an intent preservation system.

Your role: Identify structured artifacts in natural conversation. Propose, don't decide.

ARTIFACT TYPES:
- decision: A choice made, with alternatives considered and rationale
- purpose: A goal, success criterion, or desired outcome
- constraint: A boundary, limitation, or hard requirement
- principle: A guideline derived from experience or failure
- tension: A conflict between competing concerns (may be unresolved)
- requirement: Something a party needs from the system

EXTRACTION RULES:
1. Only extract what's clearly present. Don't infer or elaborate.
2. Preserve original language where possible.
3. Rate confidence honestly:
   - 0.9+: Explicitly stated, unambiguous
   - 0.7-0.9: Clearly implied, context supports
   - 0.5-0.7: Possibly present, needs confirmation
   - <0.5: Uncertain, flag for human judgment
4. One artifact per distinct item. Don't merge.
5. If nothing extractable, say so. Empty is valid.
6. CRITICAL: Check EXISTING ARTIFACTS section. Do NOT extract duplicates of existing items.
   If the text contains something very similar to an existing artifact, skip it.

OUTPUT FORMAT (JSON only, no markdown):
{
  "artifacts": [
    {
      "type": "decision",
      "summary": "One-line summary (under 100 chars)",
      "content": {
        "what": "What was decided",
        "why": "Rationale given",
        "alternatives": ["Other options mentioned"],
        "context": "Relevant context"
      },
      "confidence": 0.85,
      "rationale": "Why I extracted this, what signals I saw"
    }
  ],
  "meta": {
    "extractable": true,
    "ambiguities": ["Any unclear points"],
    "suggestions": ["Follow-up questions that might help"]
  }
}

If nothing to extract:
{
  "artifacts": [],
  "meta": {
    "extractable": false,
    "reason": "Why nothing was found"
  }
}"""

    # Default similarity threshold for deduplication
    DEFAULT_SIMILARITY_THRESHOLD = 0.6

    def __init__(self, provider: Optional['LLMProvider'] = None, queue_path: Optional[Path] = None,
                 on_llm_start: Optional[Callable[[], None]] = None,
                 on_llm_complete: Optional[Callable[['LLMResponse'], None]] = None,
                 similarity_threshold: float = None):
        """
        Initialize extractor.

        Args:
            provider: LLM provider instance. If None, uses mock.
            queue_path: Path for offline queue. If None, no queueing.
            on_llm_start: Callback when LLM call begins (for UX feedback).
            on_llm_complete: Callback when LLM call completes (receives LLMResponse with tokens).
            similarity_threshold: Threshold for deduplication (0.0-1.0). Default 0.6.
        """
        self.provider = provider
        self.queue = ExtractionQueue(queue_path) if queue_path else None
        self._on_llm_start = on_llm_start
        self._on_llm_complete = on_llm_complete
        self._last_response: Optional['LLMResponse'] = None
        self.similarity_threshold = similarity_threshold or self.DEFAULT_SIMILARITY_THRESHOLD

    @property
    def last_response(self) -> Optional['LLMResponse']:
        """Get the last LLM response (for token usage display)."""
        return self._last_response
    
    @property
    def is_available(self) -> bool:
        """Check if LLM extraction is available."""
        return self.provider is not None and self.provider.is_available
    
    def extract(self, text: str, source_id: str, allow_mock: bool = True,
                existing_context: Optional[List[ExistingArtifact]] = None) -> List[Proposal]:
        """
        Extract structured artifacts from text.

        Args:
            text: Natural language input
            source_id: ID of source event
            allow_mock: Fall back to mock if LLM unavailable
            existing_context: List of existing artifacts to prevent duplicates

        Returns:
            List of proposals for human confirmation (deduplicated)
        """
        existing_context = existing_context or []

        if self.is_available:
            try:
                proposals = self._extract_with_llm(text, source_id, existing_context)
                return self._deduplicate_proposals(proposals, existing_context)
            except Exception:
                # LLM failed — queue for later if possible
                if self.queue:
                    self.queue.add(text, source_id)
                    return []  # Will process later
                elif allow_mock:
                    proposals = self._mock_extract(text, source_id)
                    return self._deduplicate_proposals(proposals, existing_context)
                else:
                    raise
        elif allow_mock:
            proposals = self._mock_extract(text, source_id)
            return self._deduplicate_proposals(proposals, existing_context)
        else:
            if self.queue:
                self.queue.add(text, source_id)
            return []
    
    def _extract_with_llm(self, text: str, source_id: str,
                          existing_context: Optional[List[ExistingArtifact]] = None) -> List[Proposal]:
        """Extract using configured LLM provider with context awareness."""
        # Signal LLM call starting (for UX feedback)
        if self._on_llm_start:
            self._on_llm_start()

        # Build context-aware prompt
        system_prompt = self.SYSTEM_PROMPT
        user_prompt = self._build_user_prompt(text, existing_context or [])

        response = self.provider.complete(
            system=system_prompt,
            user=user_prompt,
            max_tokens=2048
        )

        # Store response for token access
        self._last_response = response

        # Signal LLM call complete (for token display)
        if self._on_llm_complete:
            self._on_llm_complete(response)

        return self._parse_response(response.text, source_id)

    def _build_user_prompt(self, text: str, existing_context: List[ExistingArtifact]) -> str:
        """Build user prompt with existing artifacts context."""
        prompt_parts = []

        # Add existing artifacts context if available
        if existing_context:
            prompt_parts.append("EXISTING ARTIFACTS (do NOT extract duplicates):")
            for artifact in existing_context[:20]:  # Limit to prevent token overflow
                prompt_parts.append(f"- [{artifact.artifact_type}] {artifact.summary}")
            prompt_parts.append("")  # Blank line

        prompt_parts.append("Extract artifacts from this text:")
        prompt_parts.append("")
        prompt_parts.append(text)

        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, source_id: str) -> List[Proposal]:
        """Parse LLM response into proposals."""
        try:
            # Handle potential markdown code blocks
            clean = response.strip()
            if clean.startswith("```"):
                # Remove code fence
                lines = clean.split('\n')
                clean = '\n'.join(lines[1:-1]) if lines[-1] == "```" else '\n'.join(lines[1:])
                clean = clean.strip()
            
            data = json.loads(clean)

            proposals = []
            for artifact in data.get("artifacts", []):
                artifact_type = artifact.get("type", "unknown")

                # Layer 1 (Security): Sanitize LLM output before storing
                # Removes control chars that could manipulate display
                summary = sanitize_control_chars(artifact.get("summary", ""))
                rationale = sanitize_control_chars(artifact.get("rationale", ""))

                proposals.append(Proposal(
                    source_id=source_id,
                    artifact_type=artifact_type,
                    content={
                        "summary": summary,
                        "detail": artifact.get("content", {}),
                        "extraction_rationale": rationale
                    },
                    confidence=float(artifact.get("confidence", 0.5)),
                    rationale=rationale
                ))
            
            return proposals
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def _deduplicate_proposals(self, proposals: List[Proposal],
                               existing_context: List[ExistingArtifact]) -> List[Proposal]:
        """
        Remove proposals too similar to existing artifacts.

        Uses text-based Jaccard similarity (offline-first per HC3).
        No API calls required.
        """
        if not existing_context:
            return proposals

        deduplicated = []
        existing_summaries = [a.summary for a in existing_context]

        for proposal in proposals:
            proposal_summary = proposal.content.get('summary', '')

            # Check similarity against all existing artifacts
            is_duplicate = False
            for existing_summary in existing_summaries:
                similarity = calculate_similarity(proposal_summary, existing_summary)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(proposal)

        return deduplicated

    def _mock_extract(self, text: str, source_id: str) -> List[Proposal]:
        """Mock extraction for testing without LLM."""
        proposals = []
        text_lower = text.lower()
        
        # Decision detection
        decision_signals = ["decided", "chose", "picked", "went with", "selected", "decision"]
        if any(s in text_lower for s in decision_signals):
            proposals.append(Proposal(
                source_id=source_id,
                artifact_type="decision",
                content={
                    "summary": self._extract_summary(text, "decision"),
                    "detail": {"raw_text": text[:500]},
                    "extraction_rationale": "Contains decision-related language"
                },
                confidence=0.6,
                rationale="Mock: detected decision keywords"
            ))
        
        # Purpose detection
        purpose_signals = ["goal", "purpose", "success", "objective", "aim", "want to", "need to"]
        if any(s in text_lower for s in purpose_signals):
            proposals.append(Proposal(
                source_id=source_id,
                artifact_type="purpose",
                content={
                    "summary": self._extract_summary(text, "purpose"),
                    "detail": {"raw_text": text[:500]},
                    "extraction_rationale": "Contains purpose-related language"
                },
                confidence=0.6,
                rationale="Mock: detected purpose keywords"
            ))
        
        # Constraint detection
        constraint_signals = ["must", "cannot", "shouldn't", "constraint", "limit", "boundary", "require"]
        if any(s in text_lower for s in constraint_signals):
            proposals.append(Proposal(
                source_id=source_id,
                artifact_type="constraint",
                content={
                    "summary": self._extract_summary(text, "constraint"),
                    "detail": {"raw_text": text[:500]},
                    "extraction_rationale": "Contains constraint-related language"
                },
                confidence=0.6,
                rationale="Mock: detected constraint keywords"
            ))
        
        # Principle detection  
        principle_signals = ["learned", "principle", "always", "never", "rule", "guideline"]
        if any(s in text_lower for s in principle_signals):
            proposals.append(Proposal(
                source_id=source_id,
                artifact_type="principle",
                content={
                    "summary": self._extract_summary(text, "principle"),
                    "detail": {"raw_text": text[:500]},
                    "extraction_rationale": "Contains principle-related language"
                },
                confidence=0.6,
                rationale="Mock: detected principle keywords"
            ))
        
        # Tension detection
        tension_signals = ["conflict", "tension", "tradeoff", "vs", "versus", "but", "however"]
        if any(s in text_lower for s in tension_signals):
            proposals.append(Proposal(
                source_id=source_id,
                artifact_type="tension",
                content={
                    "summary": self._extract_summary(text, "tension"),
                    "detail": {"raw_text": text[:500]},
                    "extraction_rationale": "Contains tension-related language"
                },
                confidence=0.5,
                rationale="Mock: detected tension keywords"
            ))
        
        return proposals
    
    def _extract_summary(self, text: str, artifact_type: str) -> str:
        """Extract a simple summary (mock mode)."""
        # Take first sentence or first 100 chars
        first_sentence = text.split('.')[0].strip()
        if len(first_sentence) > 100:
            return first_sentence[:97] + "..."
        return first_sentence
    
    def process_queue(self) -> List[Proposal]:
        """
        Process queued extractions (when coming back online).
        
        Returns all proposals from queued items.
        """
        if not self.queue or not self.is_available:
            return []
        
        proposals = []
        items = self.queue.get_all()
        
        for item in items:
            try:
                item_proposals = self._extract_with_llm(item.text, item.source_id)
                proposals.extend(item_proposals)
            except Exception:
                continue  # Keep in queue for next attempt
        
        if proposals:
            self.queue.clear()
        
        return proposals
    
    def format_for_confirmation(self, proposal: Proposal) -> str:
        """Format proposal for human confirmation (HC6: no jargon)."""
        # Confidence to human language
        if proposal.confidence >= 0.9:
            confidence_word = "clearly"
        elif proposal.confidence >= 0.7:
            confidence_word = "likely"
        elif proposal.confidence >= 0.5:
            confidence_word = "possibly"
        else:
            confidence_word = "might be"
        
        # Type to human language
        type_display = {
            "decision": "a decision",
            "purpose": "a goal or purpose", 
            "constraint": "a constraint or requirement",
            "principle": "a principle or guideline",
            "tension": "a tension or tradeoff",
            "requirement": "a requirement"
        }.get(proposal.artifact_type, f"a {proposal.artifact_type}")
        
        summary = proposal.content.get('summary', 'No summary available')
        
        output = f"\nThis {confidence_word} looks like {type_display}:\n\n"
        output += f"  \"{summary}\"\n"
        
        if proposal.rationale:
            output += f"\n  Why: {proposal.rationale}\n"
        
        output += "\nIs this right? [yes / edit / skip] "
        
        return output