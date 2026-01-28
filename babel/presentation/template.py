"""
OutputTemplate — Consistent CLI output structure

Provides a builder pattern for creating structured command output
with header, sections, and footer. Integrates with existing
presentation utilities (symbols, formatters, succession).

Usage:
    from babel.presentation.template import OutputTemplate

    template = OutputTemplate()
    template.header("BABEL STATUS", "Project Health Overview")
    template.legend({"●": "shared", "○": "local"})
    template.section("METRICS", metrics_content)
    template.section("PURPOSES", purposes_content)
    output = template.render(command="status", context={"has_pending": True})
    print(output)

Design:
    - Standalone utility (not a renderer subclass)
    - Reuses symbols, formatters, succession
    - Terminal-width aware
    - Symbol-agnostic (Unicode/ASCII)
"""

import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from .symbols import SymbolSet, get_symbols
from .succession import get_hint
from .formatters import format_timestamp


# =============================================================================
# Constants
# =============================================================================

HEADER_CHAR = "="
SECTION_CHAR = "-"
DEFAULT_WIDTH = 80


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TemplateSection:
    """A titled section of output."""
    title: str
    content: str
    collapsed: bool = False  # Future: support collapsible sections


@dataclass
class TemplateLegend:
    """Legend mapping symbols to meanings."""
    items: Dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        """Render legend as inline text."""
        if not self.items:
            return ""
        parts = [f"{symbol} {meaning}" for symbol, meaning in self.items.items()]
        return "Legend: " + "  ".join(parts)


# =============================================================================
# OutputTemplate
# =============================================================================

class OutputTemplate:
    """
    Builder for structured CLI output.

    Creates consistent output with:
    - HEADER: Command identity, legend, scope
    - SECTIONS: Titled content blocks
    - FOOTER: Summary metrics, succession hint

    Thread-safe: Each instance is independent.
    """

    def __init__(
        self,
        symbols: Optional[SymbolSet] = None,
        width: Optional[int] = None,
        full: bool = False
    ):
        """
        Initialize template.

        Args:
            symbols: SymbolSet for visual elements (auto-detect if None)
            width: Terminal width (auto-detect if None)
            full: If True, don't truncate content
        """
        self.symbols = symbols or get_symbols()
        self.width = width or shutil.get_terminal_size().columns or DEFAULT_WIDTH
        self.full = full

        # Internal state
        self._title: Optional[str] = None
        self._subtitle: Optional[str] = None
        self._legend: Optional[TemplateLegend] = None
        self._scope: Optional[str] = None
        self._sections: List[TemplateSection] = []
        self._summary: Optional[str] = None
        self._items: List[str] = []  # P12: Accumulated items with timestamps

    # =========================================================================
    # Builder Methods
    # =========================================================================

    def header(self, title: str, subtitle: Optional[str] = None) -> "OutputTemplate":
        """
        Set header with title and optional subtitle.

        Args:
            title: Main title (e.g., "BABEL STATUS")
            subtitle: Optional subtitle (e.g., "Project Health Overview")

        Returns:
            Self for chaining
        """
        self._title = title
        self._subtitle = subtitle
        return self

    def legend(self, items: Dict[str, str]) -> "OutputTemplate":
        """
        Set legend mapping symbols to meanings.

        Args:
            items: Dict mapping symbol to meaning
                   e.g., {"●": "shared", "○": "local"}

        Returns:
            Self for chaining
        """
        self._legend = TemplateLegend(items=items)
        return self

    def scope(self, text: str) -> "OutputTemplate":
        """
        Set scope line (count/context info in header).

        Args:
            text: Scope text (e.g., "25,156 artifacts | 165 validated")

        Returns:
            Self for chaining
        """
        self._scope = text
        return self

    def section(self, title: str, content: str) -> "OutputTemplate":
        """
        Add a titled section.

        Args:
            title: Section title (e.g., "PROJECT METRICS")
            content: Section content (can be multiline)

        Returns:
            Self for chaining
        """
        self._sections.append(TemplateSection(title=title, content=content))
        return self

    def separator(self) -> "OutputTemplate":
        """
        Add a visual separator (empty section with line).

        Returns:
            Self for chaining
        """
        self._sections.append(TemplateSection(title="", content=""))
        return self

    def item(
        self,
        id: str,
        summary: str,
        timestamp: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> "OutputTemplate":
        """
        Add a single item with P12-compliant temporal attribution.

        Accumulates items for later rendering via items_section().
        Timestamps are always shown when provided (P12: no flags, no parameters).

        Args:
            id: Item identifier (shown in brackets)
            summary: Item description
            timestamp: ISO timestamp (auto-formatted via format_timestamp)
            prefix: Optional symbol prefix (e.g., status indicator)

        Returns:
            Self for chaining

        Example:
            template.item("abc123", "Use Redis for caching", "2026-01-15T10:30:00Z")
            # Renders: [abc123] Use Redis for caching (Jan 15)
        """
        # P12: Time always shown when available
        time_str = f" ({format_timestamp(timestamp)})" if timestamp else ""
        prefix_str = f"{prefix} " if prefix else ""
        line = f"{prefix_str}[{id}] {summary}{time_str}"
        self._items.append(line)
        return self

    def items_section(self, title: str) -> "OutputTemplate":
        """
        Render accumulated items as a titled section.

        Clears the items buffer after rendering to allow reuse
        for multiple item sections in the same template.

        Args:
            title: Section title (e.g., "DECISIONS", "PROPOSALS")

        Returns:
            Self for chaining
        """
        if self._items:
            self.section(title, "\n".join(self._items))
            self._items = []
        return self

    def footer(self, summary: Optional[str] = None) -> "OutputTemplate":
        """
        Set footer summary text.

        Args:
            summary: Summary metrics (e.g., "25,156 artifacts | 8/8 principles")

        Returns:
            Self for chaining
        """
        self._summary = summary
        return self

    # =========================================================================
    # Rendering
    # =========================================================================

    def render(
        self,
        command: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render template to formatted string.

        Args:
            command: Command name for succession hint (optional)
            context: Context dict for succession conditions (optional)

        Returns:
            Formatted output string
        """
        lines: List[str] = []

        # Header
        if self._title:
            lines.extend(self._render_header())

        # Sections
        for section in self._sections:
            lines.extend(self._render_section(section))

        # Footer
        lines.extend(self._render_footer(command, context))

        return "\n".join(lines)

    def _render_header(self) -> List[str]:
        """Render header block."""
        lines: List[str] = []

        # Top border
        border = HEADER_CHAR * self.width
        lines.append(border)

        # Title line
        if self._subtitle:
            title_line = f"{self._title} - {self._subtitle}"
        else:
            title_line = self._title or ""
        lines.append(title_line)

        # Bottom border
        lines.append(border)

        # Legend (if set)
        if self._legend:
            legend_text = self._legend.render()
            if legend_text:
                lines.append(legend_text)

        # Scope (if set)
        if self._scope:
            lines.append(self._scope)

        # Blank line after header
        lines.append("")

        return lines

    def _render_section(self, section: TemplateSection) -> List[str]:
        """Render a single section."""
        lines: List[str] = []

        # Empty section = separator only
        if not section.title and not section.content:
            lines.append("")
            return lines

        # Section title with underline
        if section.title:
            lines.append(section.title)
            lines.append(SECTION_CHAR * len(section.title))

        # Section content
        if section.content:
            lines.append(section.content)

        # Blank line after section
        lines.append("")

        return lines

    def _render_footer(
        self,
        command: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Render footer block."""
        lines: List[str] = []

        # Footer separator
        lines.append(SECTION_CHAR * self.width)

        # Summary line
        if self._summary:
            lines.append(f"Summary: {self._summary}")

        # Succession hint
        if command:
            hint = get_hint(command, context)
            if hint:
                lines.append(hint)

        # Bottom border
        lines.append(HEADER_CHAR * self.width)

        return lines

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def truncate(self, text: str, length: Optional[int] = None) -> str:
        """
        Truncate text with ellipsis.

        Args:
            text: Text to truncate
            length: Max length (default: width - 4)

        Returns:
            Truncated text or original if full=True
        """
        if not text:
            return ""

        if self.full:
            return text

        max_len = length or (self.width - 4)
        if len(text) <= max_len:
            return text

        ellipsis = self.symbols.ellipsis
        return text[:max_len - len(ellipsis)] + ellipsis

    def format_table(
        self,
        rows: List[Dict[str, str]],
        columns: List[str],
        keys: Optional[List[str]] = None
    ) -> str:
        """
        Format data as simple aligned table (grep-parseable).

        Args:
            rows: List of dicts with data
            columns: Column headers
            keys: Dict keys for columns (defaults to lowercase headers)

        Returns:
            Formatted table string
        """
        if not rows:
            return ""

        keys = keys or [c.lower().replace(" ", "_") for c in columns]

        # Calculate column widths
        widths = [len(c) for c in columns]
        for row in rows:
            for i, key in enumerate(keys):
                val = str(row.get(key, ""))
                widths[i] = max(widths[i], len(val))

        # Build table
        lines: List[str] = []

        # Header
        header_parts = [col.ljust(widths[i]) for i, col in enumerate(columns)]
        lines.append("  ".join(header_parts))

        # Data rows
        for row in rows:
            row_parts = [str(row.get(key, "")).ljust(widths[i]) for i, key in enumerate(keys)]
            lines.append("  ".join(row_parts))

        return "\n".join(lines)

    def format_list(self, items: List[str], bullet: Optional[str] = None) -> str:
        """
        Format items as bulleted list.

        Args:
            items: List of strings
            bullet: Bullet character (default: from symbols)

        Returns:
            Formatted list string
        """
        if not items:
            return ""

        bullet = bullet or self.symbols.bullet
        return "\n".join(f"{bullet} {item}" for item in items)
