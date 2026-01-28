"""
Presentation — Display layer for Babel CLI

Contains display and formatting:
- Symbols: Visual vocabulary (unicode/ascii)
- Formatters: Text truncation, digest generation
- Succession: Workflow hints
- Template: Structured output with header/section/footer
"""

from .symbols import (
    SymbolSet, get_symbols,
    safe_print, sanitize_control_chars,
    SUMMARY_LENGTH
)
from .formatters import (
    truncate,
    generate_summary, generate_digest
)
from .succession import get_hint, RULES
from .template import OutputTemplate, TemplateSection

__all__ = [
    # Symbols
    "SymbolSet", "get_symbols",
    "truncate", "safe_print", "sanitize_control_chars",
    "generate_summary", "generate_digest",
    "SUMMARY_LENGTH",
    # Succession
    "get_hint", "RULES",
    # Template
    "OutputTemplate", "TemplateSection",
]
