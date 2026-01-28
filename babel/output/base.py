"""
BaseRenderer — Abstract base class for output renderers

All renderers inherit from this class and implement render().
Provides common utilities for terminal width, truncation, and safe output.

ID Formatting:
    Renderers use format_id() for consistent ID display across all output.
    When codec is provided: [AA-BB] (alias only)
    When debug=True: [AA-BB|50164a43] (alias + hex prefix)
    Fallback (no codec): [50164a43] (hex prefix only)
"""

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import shutil

if TYPE_CHECKING:
    from ..presentation.symbols import SymbolSet
    from ..presentation.codec import IDCodec
    from . import OutputSpec


def _is_debug_mode() -> bool:
    """Check if debug mode is enabled via BABEL_DEBUG environment variable."""
    return os.environ.get('BABEL_DEBUG', '').lower() in ('1', 'true', 'yes')


class BaseRenderer(ABC):
    """
    Abstract base class for all output renderers.

    Provides:
    - Symbol set access (Unicode/ASCII)
    - Terminal width detection
    - Truncation utilities
    - Safe output helpers
    - Centralized ID formatting via format_id()

    Subclasses must implement render() method.
    """

    def __init__(
        self,
        symbols: "SymbolSet" = None,
        width: int = None,
        full: bool = False,
        codec: "IDCodec" = None,
        debug: bool = None
    ):
        """
        Initialize renderer.

        Args:
            symbols: SymbolSet for visual elements (auto-detect if None)
            width: Terminal width (auto-detect if None)
            full: If True, don't truncate content
            codec: IDCodec for alias formatting (fallback to hex if None)
            debug: Show debug info in IDs (auto-detect from BABEL_DEBUG if None)
        """
        from ..presentation.symbols import get_symbols

        self.symbols = symbols or get_symbols()
        self.width = width or shutil.get_terminal_size().columns
        self.full = full
        self.codec = codec
        self.debug = debug if debug is not None else _is_debug_mode()

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

    def format_id(self, full_id: str) -> str:
        """
        Format ID for display using centralized codec aliasing.

        This is the SINGLE place where ID display format is determined.
        All renderers should use this method instead of hardcoded id[:8].

        Args:
            full_id: Full identifier (e.g., "decision_50164a43..." or "50164a43")

        Returns:
            Formatted ID string:
            - With codec: "[AA-BB]" (alias only)
            - With codec + debug: "[AA-BB|50164a43]" (alias + hex)
            - Without codec: "[50164a43]" (hex fallback)
        """
        if not full_id:
            return "[]"

        # Extract short hex (first 8 chars, stripping type prefix if present)
        short_hex = full_id
        for prefix in ('decision_', 'purpose_', 'constraint_', 'principle_',
                       'requirement_', 'tension_', 'm_', 'c_'):
            if short_hex.startswith(prefix):
                short_hex = short_hex[len(prefix):]
                break
        short_hex = short_hex[:8] if len(short_hex) > 8 else short_hex

        # Format based on codec availability and debug mode
        if self.codec:
            code = self.codec.encode(full_id)
            if self.debug:
                return f"[{code}|{short_hex}]"
            return f"[{code}]"

        # Fallback: no codec, use hex prefix
        return f"[{short_hex}]"

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
