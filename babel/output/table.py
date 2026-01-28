"""
TableRenderer — Render data as formatted tables

Supports:
- Unicode and ASCII borders
- Auto-sizing columns
- Content truncation with ellipsis
- Detail rows for expanded content
- Terminal width awareness
"""

from typing import TYPE_CHECKING, List, Dict, Optional

from .base import BaseRenderer

if TYPE_CHECKING:
    from . import OutputSpec


class TableRenderer(BaseRenderer):
    """
    Render structured data as formatted tables.

    Features:
    - Dynamic column width calculation
    - Unicode/ASCII borders (based on symbols)
    - Content truncation with ellipsis
    - Optional title row
    - Detail expansion rows
    """

    def render(self, spec: "OutputSpec") -> str:
        """
        Render OutputSpec as a table.

        Expected data formats:
        - List of dicts: [{col1: val1, col2: val2}, ...]
        - Dict with "rows" key: {"rows": [...], "summary": "..."}

        Args:
            spec: OutputSpec with data and column hints

        Returns:
            Formatted table string
        """
        # Extract rows from data
        if isinstance(spec.data, list):
            rows = spec.data
        elif isinstance(spec.data, dict):
            rows = spec.data.get("rows") or spec.data.get("items", [])
        else:
            rows = []

        if not rows:
            return spec.empty_message

        # Get column configuration
        columns = spec.columns or self._infer_columns(rows)
        column_keys = spec.column_keys or self._infer_keys(columns, rows)

        # Calculate column widths
        widths = self._calculate_widths(rows, columns, column_keys)

        # Build table
        lines = []

        # Title if provided
        if spec.title:
            lines.append(f"\n{spec.title}\n")

        # Table structure
        lines.append(self._separator(widths, "top"))
        lines.append(self._header_row(columns, widths))
        lines.append(self._separator(widths, "middle"))

        for i, row in enumerate(rows):
            lines.append(self._data_row(row, column_keys, widths))
            # Add separator between rows (except last)
            if i < len(rows) - 1:
                lines.append(self._separator(widths, "middle"))

        lines.append(self._separator(widths, "bottom"))

        return "\n".join(lines)

    # =========================================================================
    # Column Inference
    # =========================================================================

    def _infer_columns(self, rows: List[Dict]) -> List[str]:
        """Infer column headers from first row's keys."""
        if not rows or not isinstance(rows[0], dict):
            return []
        # Use keys from first row, title-cased
        return [k.replace("_", " ").title() for k in rows[0].keys()]

    def _infer_keys(self, columns: List[str], rows: List[Dict]) -> List[str]:
        """Infer dict keys from column headers."""
        if not rows or not isinstance(rows[0], dict):
            return columns

        row_keys = list(rows[0].keys())

        # If columns match row keys count, use row keys directly
        if len(columns) == len(row_keys):
            return row_keys

        # Otherwise, try to match columns to keys
        keys = []
        for col in columns:
            # Try exact match (lowercase, no spaces)
            col_normalized = col.lower().replace(" ", "_")
            for key in row_keys:
                if key.lower() == col_normalized:
                    keys.append(key)
                    break
            else:
                # No match found, use column as-is
                keys.append(col.lower().replace(" ", "_"))

        return keys

    # =========================================================================
    # Width Calculation
    # =========================================================================

    def _calculate_widths(
        self,
        rows: List[Dict],
        columns: List[str],
        column_keys: List[str]
    ) -> List[int]:
        """Calculate optimal column widths."""
        # Start with header widths
        widths = [len(col) for col in columns]

        # Expand for data
        for row in rows:
            for i, key in enumerate(column_keys):
                if i < len(widths):
                    value = self.safe_str(row.get(key, ""))
                    widths[i] = max(widths[i], len(value))

        # Apply constraints
        total_border = len(widths) + 1  # Vertical separators
        available = self.width - total_border - 2  # 2 for padding

        # If total exceeds available, scale down proportionally
        total_width = sum(widths)
        if total_width > available:
            scale = available / total_width
            widths = [max(4, int(w * scale)) for w in widths]

        return widths

    # =========================================================================
    # Row Rendering
    # =========================================================================

    def _separator(self, widths: List[int], position: str = "middle") -> str:
        """Render horizontal separator line."""
        s = self.symbols

        if position == "top":
            left, cross, right = s.box_tl, s.box_t_down, s.box_tr
        elif position == "bottom":
            left, cross, right = s.box_bl, s.box_t_up, s.box_br
        else:  # middle
            left, cross, right = s.box_t_right, s.box_cross, s.box_t_left

        parts = [left]
        for i, w in enumerate(widths):
            parts.append(s.box_h * w)
            parts.append(cross if i < len(widths) - 1 else right)

        return "".join(parts)

    def _header_row(self, columns: List[str], widths: List[int]) -> str:
        """Render header row."""
        s = self.symbols
        parts = [s.box_v]

        for col, w in zip(columns, widths):
            # Center header text
            text = col[:w].center(w)
            parts.append(text)
            parts.append(s.box_v)

        return "".join(parts)

    def _data_row(
        self,
        row: Dict,
        column_keys: List[str],
        widths: List[int]
    ) -> str:
        """Render data row."""
        s = self.symbols
        ellipsis = s.ellipsis
        ellip_len = len(ellipsis)

        parts = [s.box_v]

        for key, w in zip(column_keys, widths):
            value = self.safe_str(row.get(key, ""))

            # Truncate if needed
            if len(value) > w:
                if w > ellip_len:
                    value = value[:w - ellip_len] + ellipsis
                else:
                    value = value[:w]

            # Left-align data
            parts.append(value.ljust(w))
            parts.append(s.box_v)

        return "".join(parts)

    # =========================================================================
    # Legacy Support: render_themes (from symbols.py)
    # =========================================================================

    def render_themes(self, themes: List[Dict]) -> str:
        """
        Render synthesized themes as structured table.

        Backward compatible with symbols.TableRenderer.render_themes().

        Args:
            themes: List of theme dicts with keys:
                    letter, name, risk, recommendation, description, rationale, proposals

        Returns:
            Formatted table string
        """
        if not themes:
            return "No themes to display."

        s = self.symbols
        ellipsis = s.ellipsis
        ellip_len = len(ellipsis)

        # Column widths: # | THEME | RISK | REC | N
        col_letter = 3
        col_risk = 6
        col_rec = 8
        col_count = 3
        # Theme gets remaining space (min 20)
        fixed = col_letter + col_risk + col_rec + col_count + 6  # 6 for borders
        col_theme = max(20, self.width - fixed - 2)

        widths = [col_letter, col_theme, col_risk, col_rec, col_count]
        inner_width = sum(widths) + len(widths) - 1

        lines = []

        # Header
        lines.append(self._separator(widths, "top"))
        lines.append(self._theme_row(["#", "THEME", "RISK", "REC", "N"], widths))
        lines.append(self._separator(widths, "middle"))

        # Each theme
        for i, theme in enumerate(themes):
            letter = theme.get("letter", chr(65 + i))
            name = theme.get("name", "Unknown")
            risk = theme.get("risk", "?").upper()[:6]
            rec = theme.get("recommendation", "?")[:8]
            count = str(len(theme.get("proposals", [])))

            lines.append(self._theme_row([letter, name, risk, rec, count], widths))

            # IMPACT row
            impact = theme.get("description", "No impact specified")
            impact_text = f"  IMPACT: {impact}"
            if not self.full and len(impact_text) > inner_width:
                impact_text = impact_text[:inner_width - ellip_len] + ellipsis
            lines.append(f"{s.box_v}{impact_text.ljust(inner_width)}{s.box_v}")

            # WHY row
            rationale = theme.get("rationale", "No rationale")
            rationale_text = f"  WHY: {rationale}"
            if not self.full and len(rationale_text) > inner_width:
                rationale_text = rationale_text[:inner_width - ellip_len] + ellipsis
            lines.append(f"{s.box_v}{rationale_text.ljust(inner_width)}{s.box_v}")

            if i < len(themes) - 1:
                lines.append(self._separator(widths, "middle"))

        lines.append(self._separator(widths, "bottom"))
        return "\n".join(lines)

    def _theme_row(self, cells: List[str], widths: List[int]) -> str:
        """Render theme table row."""
        s = self.symbols
        ellipsis = s.ellipsis
        ellip_len = len(ellipsis)

        parts = [s.box_v]
        for cell, w in zip(cells, widths):
            cell_str = str(cell) if cell is not None else ""
            if len(cell_str) > w:
                if w > ellip_len:
                    cell_str = cell_str[:w - ellip_len] + ellipsis
                else:
                    cell_str = cell_str[:w]
            parts.append(cell_str.ljust(w))
            parts.append(s.box_v)
        return "".join(parts)
