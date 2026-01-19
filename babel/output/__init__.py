"""
Output Module — View Layer for Babel CLI

Separates data from presentation (MVC-lite pattern).
Commands return OutputSpec, renderers handle display.

Usage:
    from babel.output import OutputSpec, render

    # In command:
    return OutputSpec(
        data={"items": [...]},
        shape="table",
        columns=["ID", "Name", "Status"]
    )

    # In CLI layer:
    output = render(spec, format="auto", symbols=symbols)
    print(output)
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..presentation.symbols import SymbolSet

# Re-export for convenience
from .base import BaseRenderer
from .table import TableRenderer
from .list import ListRenderer
from .detail import DetailRenderer
from .summary import SummaryRenderer
from .json import JsonRenderer


# =============================================================================
# OutputSpec — Data envelope for rendering
# =============================================================================

@dataclass
class OutputSpec:
    """
    Data envelope that commands return for rendering.

    Commands produce data + hints, renderers handle presentation.
    This enables format switching (table, list, json) without changing commands.

    Attributes:
        data: The actual data (dict, list, or any structure)
        shape: Rendering hint - "table" | "list" | "detail" | "summary" | "auto"
        title: Optional section title/header
        columns: For tables - column headers in order
        column_keys: For tables - dict keys corresponding to columns
        show_actions: Whether to show "next step" prompts
        empty_message: Message when data is empty
        command: Which command produced this output (for succession hints)
        context: State flags for conditional hints (e.g., {"has_pending": True})
    """
    data: Any
    shape: str = "auto"
    title: Optional[str] = None
    columns: Optional[List[str]] = None
    column_keys: Optional[List[str]] = None
    show_actions: bool = True
    empty_message: str = "No data to display."
    # Succession hint context
    command: Optional[str] = None
    context: Optional[dict] = None


# =============================================================================
# Format Registry
# =============================================================================

# Maps format name to renderer class
RENDERERS = {
    "table": TableRenderer,
    "list": ListRenderer,
    "detail": DetailRenderer,
    "summary": SummaryRenderer,
    "json": JsonRenderer,
}

# Valid format values for config/CLI
VALID_FORMATS = ("auto", "table", "list", "detail", "summary", "json")


# =============================================================================
# Auto-Detection
# =============================================================================

def auto_detect_shape(data: Any) -> str:
    """
    Infer best rendering shape from data structure.

    Args:
        data: The data to analyze

    Returns:
        Shape hint: "table" | "list" | "detail" | "summary"
    """
    if data is None:
        return "detail"

    if isinstance(data, list):
        if not data:
            return "list"
        # List of homogeneous dicts → table
        if all(isinstance(x, dict) for x in data):
            if len(data) >= 2:
                # Check if dicts have same keys (homogeneous)
                first_keys = set(data[0].keys())
                if all(set(d.keys()) == first_keys for d in data):
                    return "table"
        return "list"

    if isinstance(data, dict):
        # Dict with "items" or "rows" key → likely list/table
        if "items" in data or "rows" in data:
            items = data.get("items") or data.get("rows", [])
            if isinstance(items, list) and len(items) >= 2:
                return "table"
            return "list"
        # Many top-level keys → summary
        if len(data) > 5:
            return "summary"
        # Few keys → detail
        return "detail"

    return "detail"


# =============================================================================
# Main Render Function
# =============================================================================

def get_renderer(format: str, symbols: "SymbolSet", width: int = None, full: bool = False) -> BaseRenderer:
    """
    Get appropriate renderer instance.

    Args:
        format: Format name from VALID_FORMATS
        symbols: SymbolSet for visual elements
        width: Terminal width (auto-detect if None)
        full: If True, don't truncate content

    Returns:
        Renderer instance

    Raises:
        ValueError: If format is invalid
    """
    if format not in RENDERERS:
        valid = ", ".join(RENDERERS.keys())
        raise ValueError(f"Unknown format '{format}'. Valid: {valid}")

    renderer_class = RENDERERS[format]
    return renderer_class(symbols=symbols, width=width, full=full)


def render(
    spec: OutputSpec,
    format: str = "auto",
    symbols: "SymbolSet" = None,
    width: int = None,
    full: bool = False
) -> str:
    """
    Render OutputSpec to formatted string.

    This is the main entry point for the output system.

    Args:
        spec: OutputSpec from command
        format: "auto" | "table" | "list" | "detail" | "summary" | "json"
        symbols: SymbolSet for visual elements (auto-detect if None)
        width: Terminal width (auto-detect if None)
        full: If True, don't truncate content

    Returns:
        Formatted string ready for printing

    Example:
        spec = OutputSpec(data=[...], shape="table", columns=["ID", "Name"])
        output = render(spec, format="auto")
        print(output)
    """
    import shutil
    from ..presentation.symbols import get_symbols

    # Auto-detect symbols if not provided
    if symbols is None:
        symbols = get_symbols()

    # Auto-detect terminal width if not provided
    if width is None:
        width = shutil.get_terminal_size().columns

    # Determine effective format
    if format == "auto":
        # Use spec's shape hint, or auto-detect from data
        if spec.shape and spec.shape != "auto":
            effective_format = spec.shape
        else:
            effective_format = auto_detect_shape(spec.data)
    else:
        effective_format = format

    # Get renderer and render
    renderer = get_renderer(effective_format, symbols, width, full)
    output = renderer.render(spec)

    # Append succession hint if enabled and command context provided
    if spec.show_actions and spec.command:
        from ..presentation.succession import get_hint
        hint = get_hint(spec.command, spec.context)
        if hint:
            output += f"\n\n{hint}"

    return output


# =============================================================================
# Command Completion — Centralized hint printing
# =============================================================================

def end_command(command: str, context: dict = None):
    """
    Call at end of command to print succession hint.

    This centralizes hint printing for commands that use direct print()
    instead of returning OutputSpec. Place as the LAST statement in
    any command method.

    Args:
        command: Command name (must match key in succession.RULES)
        context: State flags for conditional hints (e.g., {"has_decisions": True})

    Example:
        def capture(self, text, ...):
            print("Captured...")
            # ... other output ...
            end_command("capture", {"queued": True})
    """
    from ..presentation.succession import get_hint
    hint = get_hint(command, context)
    if hint:
        print(f"\n{hint}")


# =============================================================================
# Convenience Functions
# =============================================================================

def render_table(
    rows: List[dict],
    columns: List[str],
    column_keys: List[str] = None,
    title: str = None,
    symbols: "SymbolSet" = None,
    full: bool = False
) -> str:
    """
    Convenience function to render a table directly.

    Args:
        rows: List of dicts with data
        columns: Column headers
        column_keys: Dict keys for columns (defaults to lowercase headers)
        title: Optional table title
        symbols: SymbolSet (auto-detect if None)
        full: Don't truncate content

    Returns:
        Formatted table string
    """
    spec = OutputSpec(
        data=rows,
        shape="table",
        columns=columns,
        column_keys=column_keys,
        title=title
    )
    return render(spec, format="table", symbols=symbols, full=full)


def render_list(
    items: List[Any],
    title: str = None,
    symbols: "SymbolSet" = None,
    full: bool = False
) -> str:
    """
    Convenience function to render a list directly.

    Args:
        items: List of items to display
        title: Optional list title
        symbols: SymbolSet (auto-detect if None)
        full: Don't truncate content

    Returns:
        Formatted list string
    """
    spec = OutputSpec(
        data=items,
        shape="list",
        title=title
    )
    return render(spec, format="list", symbols=symbols, full=full)
