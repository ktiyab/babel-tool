"""
BaseRenderer — Abstract base class for output renderers

All renderers inherit from this class and implement render().
Provides common utilities for terminal width, truncation, and safe output.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
import shutil

if TYPE_CHECKING:
    from ..presentation.symbols import SymbolSet
    from . import OutputSpec


class BaseRenderer(ABC):
    """
    Abstract base class for all output renderers.

    Provides:
    - Symbol set access (Unicode/ASCII)
    - Terminal width detection
    - Truncation utilities
    - Safe output helpers

    Subclasses must implement render() method.
    """

    def __init__(
        self,
        symbols: "SymbolSet" = None,
        width: int = None,
        full: bool = False
    ):
        """
        Initialize renderer.

        Args:
            symbols: SymbolSet for visual elements (auto-detect if None)
            width: Terminal width (auto-detect if None)
            full: If True, don't truncate content
        """
        from ..presentation.symbols import get_symbols

        self.symbols = symbols or get_symbols()
        self.width = width or shutil.get_terminal_size().columns
        self.full = full

    @abstractmethod
    def render(self, spec: "OutputSpec") -> str:
        """
        Render OutputSpec to formatted string.

        Args:
            spec: OutputSpec with data and hints

        Returns:
            Formatted string for output
        """
        pass

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def truncate(self, text: str, length: int = None, ellipsis: str = None) -> str:
        """
        Truncate text with ellipsis, respecting full mode.

        Args:
            text: Text to truncate
            length: Max length (default: based on terminal width)
            ellipsis: Ellipsis character (default: from symbols)

        Returns:
            Truncated text or original if full=True
        """
        if not text:
            return ""

        if self.full:
            return text

        if length is None:
            length = max(20, self.width - 10)

        if ellipsis is None:
            ellipsis = self.symbols.ellipsis

        if len(text) <= length:
            return text

        ellip_len = len(ellipsis)
        if length <= ellip_len:
            return text[:length]

        return text[:length - ellip_len] + ellipsis

    def indent(self, text: str, spaces: int = 2) -> str:
        """
        Indent text by given number of spaces.

        Args:
            text: Text to indent (can be multiline)
            spaces: Number of spaces to indent

        Returns:
            Indented text
        """
        prefix = " " * spaces
        lines = text.split("\n")
        return "\n".join(prefix + line if line else line for line in lines)

    def safe_str(self, value) -> str:
        """
        Convert value to string safely, handling None and special types.

        Args:
            value: Any value

        Returns:
            String representation
        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value)

    def format_count(self, count: int, singular: str, plural: str = None) -> str:
        """
        Format count with singular/plural noun.

        Args:
            count: The count
            singular: Singular form (e.g., "item")
            plural: Plural form (default: singular + "s")

        Returns:
            Formatted string (e.g., "3 items", "1 item")
        """
        if plural is None:
            plural = singular + "s"
        noun = singular if count == 1 else plural
        return f"{count} {noun}"
