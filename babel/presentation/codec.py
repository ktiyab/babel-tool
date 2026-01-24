"""
IDCodec — Deterministic hash-based ID aliasing with AA-BB format

Transforms verbose hex IDs (c4dded21) to memorable 5-char codes (AA-BB).
Reduces cognitive load for AI operators and humans.

Key properties:
- DETERMINISTIC: Same ID always produces same code (hash-based)
- PERSISTENT: Works across commands without storage (computation = persistence)
- READABLE: AA-BB format is distinct and memorable

Usage:
    codec = IDCodec()

    # Encoding (output) - deterministic
    code = codec.encode("c4dded21")       # Returns "KM-XP" (always same)
    code = codec.encode("decision_abc")   # Returns "PL-QR" (always same)

    # Decoding (input) - requires candidate scanning
    full_id = codec.decode("KM-XP", candidate_ids)  # Returns "c4dded21"

Code space: 26^4 = 456,976 combinations (sufficient for any project)
"""

import re
from typing import Optional, List

import xxhash


# Pattern for valid codes: AA-BB (two uppercase letters, dash, two uppercase letters)
CODE_PATTERN = re.compile(r'^[A-Z]{2}-[A-Z]{2}$')


class IDCodec:
    """
    Deterministic hash-based ID aliasing for ergonomic artifact references.

    Uses xxhash for fast, deterministic code generation.
    Same ID always produces same code - no storage needed.
    """

    def __init__(self):
        """Initialize codec (stateless - no instance state needed)."""
        pass  # Stateless - all computation is deterministic

    def encode(self, full_id: str) -> str:
        """
        Generate deterministic code for an ID.

        Args:
            full_id: Full identifier (e.g., "c4dded21", "decision_3b152510")

        Returns:
            5-char code in AA-BB format (e.g., "KM-XP")

        Note:
            DETERMINISTIC: Same full_id always returns same code.
            No storage needed - hash computation is the persistence.
        """
        if not full_id:
            return full_id

        normalized = self._normalize_id(full_id)
        return self._hash_to_code(normalized)

    def decode(self, code: str, candidate_ids: List[str] = None) -> str:
        """
        Resolve code to full ID by scanning candidates.

        Args:
            code: AA-BB format code (e.g., "KM-XP")
            candidate_ids: List of full IDs to scan (required for resolution)

        Returns:
            Full ID if found, original code otherwise (passthrough)

        Note:
            Resolution works by encoding each candidate and comparing.
            Without candidates, returns the code unchanged (passthrough).
        """
        if not code:
            return code

        # Normalize code format
        code_upper = code.upper()

        # If not a valid code pattern, passthrough
        if not self.is_short_code(code_upper):
            return code

        # Without candidates, cannot resolve - passthrough
        if not candidate_ids:
            return code

        # Scan candidates to find match
        for candidate in candidate_ids:
            if self.encode(candidate) == code_upper:
                return candidate

        # No match found - passthrough
        return code

    def is_short_code(self, value: str) -> bool:
        """
        Check if value matches AA-BB code format.

        Args:
            value: String to check

        Returns:
            True if value matches AA-BB pattern
        """
        if not value:
            return False
        return bool(CODE_PATTERN.match(value.upper()))

    def format_with_code(self, full_id: str, display_text: str) -> str:
        """
        Format display with code only (ID hidden).

        Args:
            full_id: Full identifier (used to generate code)
            display_text: Text to display after code

        Returns:
            Formatted string: "[AA-BB] display_text"

        Example:
            format_with_code("c4dded21", "Use SQLite")
            → "[KM-XP] Use SQLite"
        """
        code = self.encode(full_id)
        return f"[{code}] {display_text}"

    def _normalize_id(self, full_id: str) -> str:
        """
        Normalize ID to consistent format for hashing.

        Handles:
        - Full event IDs: "c4dded21" → "c4dded21"
        - Type-prefixed: "decision_3b152510..." → "3b152510"
        - Long hashes: "3b15251098c469f3" → "3b152510"
        """
        if not full_id:
            return full_id

        # Strip type prefix if present
        for prefix in ('decision_', 'purpose_', 'constraint_', 'principle_',
                       'requirement_', 'tension_', 'm_', 'c_'):
            if full_id.startswith(prefix):
                full_id = full_id[len(prefix):]
                break

        # Take first 8 chars (standard display length)
        return full_id[:8] if len(full_id) > 8 else full_id

    def _hash_to_code(self, normalized_id: str) -> str:
        """
        Convert normalized ID to AA-BB code via hash.

        Uses xxhash for fast, deterministic hashing.
        Maps hash to 26^4 = 456,976 code space.

        Args:
            normalized_id: Normalized 8-char ID

        Returns:
            5-char code in AA-BB format
        """
        # Hash the ID
        h = xxhash.xxh32(normalized_id.encode()).intdigest()

        # Map to code space (26^4 = 456,976)
        n = h % (26 ** 4)

        # Convert to base-26 digits
        c0 = n % 26
        c1 = (n // 26) % 26
        c2 = (n // 676) % 26
        c3 = (n // 17576) % 26

        # Format as AA-BB
        return f"{chr(65 + c3)}{chr(65 + c2)}-{chr(65 + c1)}{chr(65 + c0)}"
