"""
Digest — Semantic summary generation for Babel artifacts

Produces meaningful digests instead of arbitrary character truncation.
Uses YAKE for keyword extraction to preserve WHAT + WHY in compressed form.

Design principles:
- P7: Reasoning travels (digests preserve intent, not just characters)
- P6: Token efficiency (semantic compression > truncation)
- HC6: Human-readable (meaningful summaries, not cut-off text)

Architecture:
- Capture-time: Generate digest when artifact captured
- Display-time: Show pre-computed digest (no truncation needed)
- On-demand: Full content always available via `babel show`
"""

import re
from typing import Optional, List

# YAKE is optional - graceful fallback if not installed
try:
    import yake
    YAKE_AVAILABLE = True
except ImportError:
    YAKE_AVAILABLE = False


# =============================================================================
# Sentence Splitting (No external dependencies)
# =============================================================================

# Common abbreviations that shouldn't trigger sentence splits
ABBREVIATIONS = {
    'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr',
    'vs', 'etc', 'inc', 'ltd', 'corp',
    'e.g', 'i.e', 'eg', 'ie',
    'min', 'max', 'avg',
    'api', 'url', 'http', 'https',
}


def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences without external libraries.

    Handles common abbreviations and edge cases.
    Returns list of sentences preserving original text.
    """
    if not text:
        return []

    # Protect abbreviations by replacing their dots temporarily
    protected = text
    for abbr in ABBREVIATIONS:
        # Case-insensitive replacement
        pattern = re.compile(rf'\b({abbr})\.', re.IGNORECASE)
        protected = pattern.sub(r'\1<DOT>', protected)

    # Also protect decimal numbers (e.g., "3.14", "1000/min")
    protected = re.sub(r'(\d)\.(\d)', r'\1<DOT>\2', protected)

    # Split on sentence boundaries: .!? followed by space and capital
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected)

    # Restore protected dots
    sentences = [s.replace('<DOT>', '.').strip() for s in sentences]

    # Filter empty sentences
    return [s for s in sentences if s]


# =============================================================================
# Technical Term Detection
# =============================================================================

def extract_technical_terms(text: str) -> List[str]:
    """
    Extract technical terms based on patterns.

    Detects: CamelCase, ACRONYMS, snake_case, kebab-case, numbers with units.
    These are almost always domain-relevant.
    """
    terms = []

    # CamelCase (e.g., Redis, GraphQL, UserService)
    terms.extend(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text))

    # ACRONYMS (e.g., API, CRUD, SQL) - 2+ uppercase letters
    terms.extend(re.findall(r'\b[A-Z]{2,}\b', text))

    # Capitalized single words that look like proper nouns/tech (e.g., Redis, Python)
    terms.extend(re.findall(r'\b[A-Z][a-z]{2,}\b', text))

    # snake_case (e.g., rate_limit, user_id)
    terms.extend(re.findall(r'\b[a-z]+_[a-z_]+\b', text))

    # kebab-case (e.g., blue-green, event-sourcing)
    terms.extend(re.findall(r'\b[a-z]+-[a-z-]+\b', text))

    # Numbers with context (e.g., 30s, 50/min, 1000ms)
    terms.extend(re.findall(r'\b\d+(?:ms|s|m|min|h|hr|d|kb|mb|gb|%|/\w+)\b', text, re.IGNORECASE))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for term in terms:
        lower = term.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(term)

    return unique


# =============================================================================
# Digest Generator
# =============================================================================

class DigestGenerator:
    """
    Generate semantic digests for Babel artifacts.

    Produces: First sentence + [relevant keywords not in first sentence]

    Example:
        Input:  "Use Redis for caching because rate limits require local storage
                 and reduce API calls from 1000/min to 50/min."
        Output: "Use Redis for caching because rate limits require local storage.
                 [API calls, 50/min]"
    """

    def __init__(self, language: str = "en", max_keywords: int = 3):
        """
        Initialize digest generator.

        Args:
            language: Language code for YAKE (default: "en")
            max_keywords: Maximum keywords to append (default: 3)
        """
        self.language = language
        self.max_keywords = max_keywords
        self._extractor = None

        # Initialize YAKE if available
        if YAKE_AVAILABLE:
            self._extractor = yake.KeywordExtractor(
                lan=language,
                n=2,              # Max 2-word phrases
                top=10,           # Extract top 10, filter later
                dedupLim=0.7,     # Deduplication threshold
                features=None,    # Use default features
            )

    def generate(
        self,
        content: str,
        content_type: str = "decision",
        max_keywords: int = None
    ) -> str:
        """
        Generate semantic digest from content.

        Args:
            content: Full text content
            content_type: Type hint (decision, constraint, question, etc.)
            max_keywords: Override default max keywords

        Returns:
            Semantic digest: first sentence + [keywords]
        """
        if not content:
            return ""

        content = content.strip()

        # Short content: return as-is
        if len(content) < 80:
            return content

        max_kw = max_keywords or self.max_keywords

        # Extract first sentence (usually contains the decision/main point)
        sentences = split_sentences(content)
        first = sentences[0] if sentences else content

        # Get keywords to append
        keywords = self._extract_keywords(content, first, max_kw)

        if keywords:
            return f"{first} [{', '.join(keywords)}]"
        return first

    def _extract_keywords(
        self,
        content: str,
        first_sentence: str,
        max_keywords: int
    ) -> List[str]:
        """
        Extract keywords not present in first sentence.

        Uses YAKE if available, falls back to technical term extraction.
        """
        first_lower = first_sentence.lower()

        if self._extractor:
            # Use YAKE for keyword extraction
            keywords = self._extractor.extract_keywords(content)
            terms = [kw for kw, score in keywords]
        else:
            # Fallback: extract technical terms
            terms = extract_technical_terms(content)

        # Filter: keywords not already in first sentence
        additional = []
        for term in terms:
            term_lower = term.lower()
            # Check if term (or its words) already appear in first sentence
            if term_lower not in first_lower:
                # Also check individual words for multi-word terms
                words = term_lower.split()
                if not all(w in first_lower for w in words):
                    additional.append(term)

        return additional[:max_keywords]

    def generate_for_type(
        self,
        content: str,
        artifact_type: str
    ) -> str:
        """
        Generate digest with type-specific handling.

        Different artifact types may benefit from different strategies.
        """
        # Currently all types use same strategy
        # Future: could customize per type
        return self.generate(content, content_type=artifact_type)


# =============================================================================
# Module-level convenience function
# =============================================================================

# Singleton instance for efficiency
_generator: Optional[DigestGenerator] = None


def get_generator() -> DigestGenerator:
    """Get or create singleton DigestGenerator instance."""
    global _generator
    if _generator is None:
        _generator = DigestGenerator()
    return _generator


def generate_digest(
    content: str,
    content_type: str = "decision",
    max_keywords: int = 3
) -> str:
    """
    Generate semantic digest from content.

    Convenience function using singleton generator.

    Args:
        content: Full text content
        content_type: Type hint (decision, constraint, question, etc.)
        max_keywords: Maximum keywords to append

    Returns:
        Semantic digest: first sentence + [keywords]

    Example:
        >>> generate_digest(
        ...     "Use Redis for caching because rate limits require local storage.",
        ...     content_type="decision"
        ... )
        "Use Redis for caching because rate limits require local storage."
    """
    return get_generator().generate(content, content_type, max_keywords)
