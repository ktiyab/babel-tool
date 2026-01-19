"""
Presentation — Display layer for Babel CLI

Contains display and formatting:
- Symbols: Visual vocabulary (unicode/ascii)
- Succession: Workflow hints
"""

from .symbols import (
    SymbolSet, get_symbols,
    truncate, safe_print, sanitize_control_chars,
    SUMMARY_LENGTH
)
from .succession import get_hint, RULES

__all__ = [
    # Symbols
    "SymbolSet", "get_symbols",
    "truncate", "safe_print", "sanitize_control_chars",
    "SUMMARY_LENGTH",
    # Succession
    "get_hint", "RULES",
]
