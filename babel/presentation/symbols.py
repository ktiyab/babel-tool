"""
Symbols — Visual vocabulary for coherence states

Progressive enhancement: Unicode when supported, ASCII fallback.
Configurable via display.symbols setting.

Also provides safe output utilities:
- safe_print(): Encoding-safe printing for untrusted content
- sanitize_control_chars(): Security sanitization for LLM output
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# Safe Output Utilities (Two-Layer Defense)
# =============================================================================
# Layer 1 (Security): sanitize_control_chars() - strips dangerous control chars
# Layer 2 (Encoding): safe_print() - handles display encoding gracefully

# Common Unicode to ASCII replacements for display
UNICODE_TO_ASCII = {
    '→': '->',
    '←': '<-',
    '↑': '^',
    '↓': 'v',
    '…': '...',
    '–': '-',
    '—': '--',
    '"': '"',
    '"': '"',
    ''': "'",
    ''': "'",
    '•': '*',
    '·': '.',
    '×': 'x',
    '÷': '/',
    '≈': '~',
    '≠': '!=',
    '≤': '<=',
    '≥': '>=',
    '±': '+/-',
}


def sanitize_control_chars(text: str) -> str:
    """
    Layer 1 (Security): Remove dangerous control characters from LLM output.

    Strips control chars that could:
    - Manipulate terminal display (ANSI escapes)
    - Cause parsing issues (null bytes, etc.)

    Preserves: newlines (\\n), tabs (\\t), carriage returns (\\r)

    Args:
        text: Raw text from LLM or untrusted source

    Returns:
        Sanitized text safe for storage and display
    """
    if not text:
        return text

    # Remove control chars except \t (0x09), \n (0x0A), \r (0x0D)
    result = []
    for char in text:
        code = ord(char)
        # Allow printable chars and safe whitespace
        if code >= 32 or code in (9, 10, 13):  # \t, \n, \r
            result.append(char)
        # Skip control chars 0x00-0x08, 0x0B-0x0C, 0x0E-0x1F

    return ''.join(result)


def safe_print(text: str, end: str = '\n', file=None) -> None:
    """
    Layer 2 (Encoding): Print with graceful encoding fallback.

    Handles UnicodeEncodeError by replacing unencodable characters
    with ASCII equivalents or '?' as last resort.

    Use this when printing untrusted content (LLM output, user input).

    Args:
        text: Text to print (may contain any Unicode)
        end: String appended after text (default: newline)
        file: Output stream (default: sys.stdout)
    """
    if file is None:
        file = sys.stdout

    try:
        print(text, end=end, file=file)
    except UnicodeEncodeError:
        # Replace known Unicode chars with ASCII equivalents
        safe_text = text
        for unicode_char, ascii_equiv in UNICODE_TO_ASCII.items():
            safe_text = safe_text.replace(unicode_char, ascii_equiv)

        try:
            print(safe_text, end=end, file=file)
        except UnicodeEncodeError:
            # Last resort: replace all unencodable chars with ?
            encoding = getattr(file, 'encoding', 'utf-8') or 'utf-8'
            encoded = safe_text.encode(encoding, errors='replace')
            print(encoded.decode(encoding), end=end, file=file)


# =============================================================================
# Display Truncation Constants
# =============================================================================
# Centralized limits for consistent output across all commands.
# Use truncate() helper to apply these with --full flag support.

SUMMARY_LENGTH = 120      # Default for summaries (captures complete thought)
DETAIL_LENGTH = 200       # For secondary details
ID_DISPLAY_LENGTH = 8     # ID prefixes (e.g., "abc12345")
DATE_DISPLAY_LENGTH = 10  # Date displays (e.g., "2025-01-15")


def truncate(text: str, length: int = SUMMARY_LENGTH, full: bool = False) -> str:
    """
    Truncate text with ellipsis, respecting full mode.

    Args:
        text: Text to truncate
        length: Max length (default: SUMMARY_LENGTH = 120)
        full: If True, never truncate (for --full flag)

    Returns:
        Truncated text with '...' if needed, or full text

    Examples:
        truncate("A very long text...", 50)  -> "A very long text..."[:47] + "..."
        truncate("Short", 50)                -> "Short" (no change)
        truncate("Any length", 50, full=True) -> "Any length" (no truncation)
    """
    if not text:
        return ""
    if full or len(text) <= length:
        return text
    if length <= 3:
        return text[:length]
    return text[:length - 3] + "..."


@dataclass(frozen=True)
class SymbolSet:
    """Complete set of symbols for artifact types and states."""
    # Artifact types
    purpose: str
    decision: str
    constraint: str
    principle: str
    tension_type: str

    # States
    coherent: str
    tension: str
    drift: str
    ambiguous: str

    # Structural
    checkpoint: str
    trace: str
    trace_conflict: str

    # Scope markers
    shared: str
    local: str

    # Validation states (P5)
    validated: str
    consensus_only: str
    evidence_only: str
    proposed: str

    # Health indicators
    health_high_confusion: str
    health_moderate: str
    health_aligned: str
    health_starting: str

    # Status markers
    check_pass: str
    check_warn: str
    check_fail: str
    deprecated: str
    arrow: str

    # Event type markers
    conversation: str
    commit: str
    revised: str
    synthesized: str

    # Tree/structure markers
    tree_branch: str
    tree_end: str
    bullet: str

    # LLM/Token indicators
    llm_thinking: str
    llm_done: str
    tokens_in: str
    tokens_out: str
    tokens_total: str

    # Table borders
    box_h: str       # horizontal ─ or -
    box_v: str       # vertical │ or |
    box_tl: str      # top-left ┌ or +
    box_tr: str      # top-right ┐ or +
    box_bl: str      # bottom-left └ or +
    box_br: str      # bottom-right ┘ or +
    box_cross: str   # cross ┼ or +
    box_t_down: str  # T down ┬ or +
    box_t_up: str    # T up ┴ or +
    box_t_right: str # T right ├ or +
    box_t_left: str  # T left ┤ or +

    # Text truncation
    ellipsis: str    # … or ...


UNICODE = SymbolSet(
    # Types
    purpose='◎',
    decision='◇',
    constraint='▢',
    principle='△',
    tension_type='⊘',
    # States
    coherent='✓',
    tension='⚡',
    drift='↔',
    ambiguous='?',
    # Structural
    checkpoint='●',
    trace='→',
    trace_conflict='⤳',
    # Scope
    shared='●',
    local='○',
    # Validation (P5)
    validated='●',
    consensus_only='◐',
    evidence_only='◑',
    proposed='○',
    # Health
    health_high_confusion='◔',
    health_moderate='◐',
    health_aligned='●',
    health_starting='○',
    # Status
    check_pass='✓',
    check_warn='⚠',
    check_fail='❌',
    deprecated='⊘',
    arrow='→',
    # Event types
    conversation='◈',
    commit='◆',
    revised='↻',
    synthesized='◊',
    # Tree
    tree_branch='├─',
    tree_end='└─',
    bullet='•',
    # LLM
    llm_thinking='◌',
    llm_done='●',
    tokens_in='↓',
    tokens_out='↑',
    tokens_total='≡',
    # Table borders
    box_h='─',
    box_v='│',
    box_tl='┌',
    box_tr='┐',
    box_bl='└',
    box_br='┘',
    box_cross='┼',
    box_t_down='┬',
    box_t_up='┴',
    box_t_right='├',
    box_t_left='┤',
    # Truncation
    ellipsis='…',
)

ASCII = SymbolSet(
    # Types
    purpose='[o]',
    decision='[>]',
    constraint='[=]',
    principle='[^]',
    tension_type='[x]',
    # States
    coherent='[+]',
    tension='[!]',
    drift='[~]',
    ambiguous='[?]',
    # Structural
    checkpoint='[*]',
    trace='->',
    trace_conflict='~>',
    # Scope
    shared='[S]',
    local='[L]',
    # Validation (P5)
    validated='[V]',
    consensus_only='[C]',
    evidence_only='[E]',
    proposed='[ ]',
    # Health
    health_high_confusion='[!!]',
    health_moderate='[!]',
    health_aligned='[OK]',
    health_starting='[..]',
    # Status
    check_pass='[OK]',
    check_warn='[!]',
    check_fail='[ERR]',
    deprecated='[DEP]',
    arrow='->',
    # Event types
    conversation='[MSG]',
    commit='[CMT]',
    revised='[REV]',
    synthesized='[SYN]',
    # Tree
    tree_branch='+-',
    tree_end='+-',
    bullet='*',
    # LLM
    llm_thinking='...',
    llm_done='[OK]',
    tokens_in='<-',
    tokens_out='->',
    tokens_total='==',
    # Table borders
    box_h='-',
    box_v='|',
    box_tl='+',
    box_tr='+',
    box_bl='+',
    box_br='+',
    box_cross='+',
    box_t_down='+',
    box_t_up='+',
    box_t_right='+',
    box_t_left='+',
    # Truncation
    ellipsis='...',
)


# Mapping from artifact type string to symbol attribute
TYPE_TO_SYMBOL = {
    'purpose': 'purpose',
    'decision': 'decision',
    'constraint': 'constraint',
    'principle': 'principle',
    'tension': 'tension_type',
}

# Mapping from status string to symbol attribute
STATUS_TO_SYMBOL = {
    'coherent': 'coherent',
    'tension': 'tension',
    'drift': 'drift',
    'ambiguous': 'ambiguous',
}


def supports_unicode() -> bool:
    """
    Check if environment likely supports Unicode output.

    Conservative: defaults to ASCII if uncertain.
    Checks stdout encoding first (most reliable on Windows).
    """
    # Explicit environment override
    if os.environ.get('BABEL_ASCII_ONLY', '').lower() in ('1', 'true', 'yes'):
        return False
    if os.environ.get('BABEL_UNICODE', '').lower() in ('1', 'true', 'yes'):
        return True

    # Check stdout encoding directly (most reliable for Windows)
    # This catches cp1252, cp437, and other non-Unicode Windows encodings
    stdout_encoding = getattr(sys.stdout, 'encoding', None)
    if stdout_encoding:
        encoding_lower = stdout_encoding.lower().replace('-', '').replace('_', '')
        # UTF-8 and UTF-16 support Unicode
        if encoding_lower in ('utf8', 'utf16', 'utf16le', 'utf16be', 'utf32'):
            pass  # Continue checking, but this is a good sign
        # Windows code pages that don't support our Unicode symbols
        elif encoding_lower.startswith('cp') or encoding_lower in ('ascii', 'latin1', 'iso88591'):
            return False

    # Check locale
    lang = os.environ.get('LANG', '').lower()
    lc_all = os.environ.get('LC_ALL', '').lower()

    if 'utf-8' in lang or 'utf8' in lang:
        return True
    if 'utf-8' in lc_all or 'utf8' in lc_all:
        return True

    # Known good terminals
    term_program = os.environ.get('TERM_PROGRAM', '')
    if term_program in ('vscode', 'iTerm.app', 'Apple_Terminal', 'Hyper'):
        return True

    # Windows Terminal (supports Unicode)
    if os.environ.get('WT_SESSION'):
        return True

    # Modern terminal emulators
    term = os.environ.get('TERM', '')
    if term in ('xterm-256color', 'screen-256color', 'alacritty', 'kitty'):
        # These usually support Unicode, but check locale too
        if lang or lc_all:  # Some locale is set
            return True

    # Check if stdout encoding is UTF-8 (final check)
    if stdout_encoding and 'utf' in stdout_encoding.lower():
        return True

    # Default: ASCII for safety
    return False


def get_symbols(preference: Optional[str] = None) -> SymbolSet:
    """
    Get appropriate symbol set based on preference or auto-detection.
    
    Args:
        preference: "unicode", "ascii", or "auto" (None = auto)
        
    Returns:
        Appropriate SymbolSet for the environment
    """
    if preference == 'unicode':
        return UNICODE
    if preference == 'ascii':
        return ASCII
    # Auto-detect
    return UNICODE if supports_unicode() else ASCII


def symbol_for_type(symbols: SymbolSet, artifact_type: str) -> str:
    """Get symbol for an artifact type."""
    attr = TYPE_TO_SYMBOL.get(artifact_type, 'decision')  # Default to decision
    return getattr(symbols, attr)


def symbol_for_status(symbols: SymbolSet, status: str) -> str:
    """Get symbol for a coherence status."""
    attr = STATUS_TO_SYMBOL.get(status, 'ambiguous')  # Default to ambiguous
    return getattr(symbols, attr)


def format_artifact(symbols: SymbolSet, artifact_type: str, summary: str, status: Optional[str] = None) -> str:
    """
    Format an artifact for display.
    
    Examples:
        ◇ Use SQLite ✓
        [>] Use SQLite [+]
    """
    type_sym = symbol_for_type(symbols, artifact_type)
    
    if status:
        status_sym = symbol_for_status(symbols, status)
        return f"{type_sym} {summary} {status_sym}"
    else:
        return f"{type_sym} {summary}"


def format_status_line(symbols: SymbolSet, status: str, detail: str) -> str:
    """
    Format a coherence status line.
    
    Examples:
        Coherence: ✓ checked 2h ago
        Coherence: [+] checked 2h ago
    """
    status_sym = symbol_for_status(symbols, status)
    return f"Coherence: {status_sym} {detail}"


def format_trace(symbols: SymbolSet, from_summary: str, to_type: str, to_summary: str, is_conflict: bool = False) -> str:
    """
    Format a trace/connection line.

    Examples:
        → links to ▢ "offline-first"
        ~> conflicts with [=] "offline-first"
    """
    trace_sym = symbols.trace_conflict if is_conflict else symbols.trace
    to_type_sym = symbol_for_type(symbols, to_type)
    return f"  {trace_sym} {'conflicts with' if is_conflict else 'links to'} {to_type_sym} \"{to_summary}\""


# =============================================================================
# Table Renderer
# =============================================================================

class TableRenderer:
    """
    Render structured data as formatted tables.

    Supports ASCII and Unicode borders, terminal width detection,
    and integration with truncate() for --full flag support.
    """

    def __init__(self, symbols: SymbolSet = None, width: int = None, full: bool = False):
        """
        Initialize table renderer.

        Args:
            symbols: SymbolSet for borders (auto-detect if None)
            width: Terminal width (auto-detect if None)
            full: If True, don't truncate content
        """
        import shutil
        self.symbols = symbols or get_symbols()
        self.width = width or shutil.get_terminal_size().columns
        self.full = full

    def _separator(self, widths: list, position: str = 'middle') -> str:
        """Render a horizontal separator line."""
        s = self.symbols
        if position == 'top':
            left, cross, right = s.box_tl, s.box_t_down, s.box_tr
        elif position == 'bottom':
            left, cross, right = s.box_bl, s.box_t_up, s.box_br
        else:  # middle
            left, cross, right = s.box_t_right, s.box_cross, s.box_t_left

        parts = [left]
        for i, w in enumerate(widths):
            parts.append(s.box_h * w)
            parts.append(cross if i < len(widths) - 1 else right)
        return ''.join(parts)

    def _row(self, cells: list, widths: list) -> str:
        """Render a single row with vertical separators."""
        s = self.symbols
        ellip = s.ellipsis
        ellip_len = len(ellip)
        parts = [s.box_v]
        for cell, w in zip(cells, widths):
            # Pad or truncate cell content
            cell_str = str(cell) if cell is not None else ''
            if len(cell_str) > w:
                cell_str = cell_str[:w-ellip_len] + ellip if w > ellip_len else cell_str[:w]
            parts.append(cell_str.ljust(w))
            parts.append(s.box_v)
        return ''.join(parts)

    def render_themes(self, themes: list) -> str:
        """
        Render synthesized themes as a structured table.

        Args:
            themes: List of theme dicts with keys:
                    letter, name, risk, recommendation, description, rationale, proposals

        Returns:
            Formatted table string
        """
        if not themes:
            return "No themes to display."

        s = self.symbols
        ellip = s.ellipsis
        ellip_len = len(ellip)

        # Column widths: # | THEME | RISK | REC | N
        col_letter = 3
        col_risk = 6
        col_rec = 8
        col_count = 3
        # Theme gets remaining space (min 20)
        fixed = col_letter + col_risk + col_rec + col_count + 6  # 6 for borders
        col_theme = max(20, self.width - fixed - 2)

        widths = [col_letter, col_theme, col_risk, col_rec, col_count]
        # Inner width for detail rows (everything except outer borders)
        inner_width = sum(widths) + len(widths) - 1  # sum + separators between columns

        lines = []

        # Header
        lines.append(self._separator(widths, 'top'))
        lines.append(self._row(['#', 'THEME', 'RISK', 'REC', 'N'], widths))
        lines.append(self._separator(widths, 'middle'))

        # Each theme
        for i, theme in enumerate(themes):
            letter = theme.get('letter', chr(65 + i))
            name = theme.get('name', 'Unknown')
            risk = theme.get('risk', '?').upper()[:6]
            rec = theme.get('recommendation', '?')[:8]
            count = str(len(theme.get('proposals', [])))

            # Main row
            lines.append(self._row([letter, name, risk, rec, count], widths))

            # Detail rows span full width (simpler layout)
            # IMPACT row
            impact = theme.get('description', 'No impact specified')
            impact_text = f"  IMPACT: {impact}"
            if not self.full and len(impact_text) > inner_width:
                impact_text = impact_text[:inner_width - ellip_len] + ellip
            lines.append(f"{s.box_v}{impact_text.ljust(inner_width)}{s.box_v}")

            # RATIONALE row
            rationale = theme.get('rationale', 'No rationale')
            rationale_text = f"  WHY: {rationale}"
            if not self.full and len(rationale_text) > inner_width:
                rationale_text = rationale_text[:inner_width - ellip_len] + ellip
            lines.append(f"{s.box_v}{rationale_text.ljust(inner_width)}{s.box_v}")

            # Separator (middle for all but last)
            if i < len(themes) - 1:
                lines.append(self._separator(widths, 'middle'))

        # Bottom border
        lines.append(self._separator(widths, 'bottom'))

        return '\n'.join(lines)
