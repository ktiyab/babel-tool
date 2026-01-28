"""
ListRenderer — Render data as bullet lists or timelines

Supports:
- Simple bullet lists
- Timeline format with timestamps
- Nested lists
- Scope markers (shared/local)
"""

from typing import TYPE_CHECKING, List, Dict

from .base import BaseRenderer

if TYPE_CHECKING:
    from . import OutputSpec


class ListRenderer(BaseRenderer):
    """
    Render data as formatted lists.

    Formats:
    - Bullet list: Simple items with bullet prefix
    - Timeline: Items with timestamp and ID
    - Nested: Hierarchical items with indentation
    """

    def render(self, spec: "OutputSpec") -> str:
        """
        Render OutputSpec as a list.

        Expected data formats:
        - List of strings: ["item1", "item2"]
        - List of dicts: [{"text": "...", "id": "...", "scope": "shared"}, ...]
        - Dict with "items" key: {"items": [...], "title": "..."}

        Args:
            spec: OutputSpec with data

        Returns:
            Formatted list string
        """
        # Extract items from data
        if isinstance(spec.data, list):
            items = spec.data
        elif isinstance(spec.data, dict):
            items = spec.data.get("items") or spec.data.get("rows", [])
        else:
            items = []

        if not items:
            return spec.empty_message

        lines = []

        # Title if provided
        if spec.title:
            lines.append(f"\n{spec.title}\n")

        # Detect list type and render accordingly
        if self._is_timeline(items):
            lines.extend(self._render_timeline(items))
        elif self._is_nested(items):
            lines.extend(self._render_nested(items))
        else:
            lines.extend(self._render_bullets(items))

        return "\n".join(lines)

    # =========================================================================
    # Type Detection
    # =========================================================================

    def _is_timeline(self, items: List) -> bool:
        """Check if items look like timeline entries (have timestamp/date)."""
        if not items or not isinstance(items[0], dict):
            return False
        first = items[0]
        return any(k in first for k in ("timestamp", "date", "time", "created_at"))

    def _is_nested(self, items: List) -> bool:
        """Check if items have children (nested structure)."""
        if not items or not isinstance(items[0], dict):
            return False
        first = items[0]
        return "children" in first or "items" in first

    # =========================================================================
    # Bullet List
    # =========================================================================

    def _render_bullets(self, items: List) -> List[str]:
        """Render simple bullet list."""
        s = self.symbols
        lines = []

        for item in items:
            if isinstance(item, dict):
                # Dict item - extract text (try common keys)
                text = (
                    item.get("text") or
                    item.get("summary") or
                    item.get("decision") or
                    item.get("content") or
                    item.get("name") or
                    item.get("description") or
                    str(item)
                )
                # Add ID if present (using centralized format_id)
                item_id = item.get("id", "")
                if item_id:
                    text = f"{self.format_id(item_id)} {text}"
            else:
                text = str(item)

            # Truncate and add bullet
            text = self.truncate(text, self.width - 4)
            lines.append(f"  {s.bullet} {text}")

        return lines

    # =========================================================================
    # Timeline List
    # =========================================================================

    def _render_timeline(self, items: List[Dict]) -> List[str]:
        """Render timeline list with timestamps and scope markers."""
        s = self.symbols
        lines = []

        for item in items:
            # Scope marker
            scope = item.get("scope", "local")
            if scope == "shared" or item.get("is_shared"):
                scope_marker = s.shared
            else:
                scope_marker = s.local

            # Timestamp
            timestamp = (
                item.get("timestamp") or
                item.get("date") or
                item.get("time") or
                item.get("created_at") or
                ""
            )
            if timestamp and len(timestamp) > 10:
                timestamp = timestamp[:10]  # Just date part

            # ID (using centralized format_id)
            item_id = item.get("id", "")
            formatted_id = self.format_id(item_id) if item_id else ""

            # Content
            content = (
                item.get("text") or
                item.get("summary") or
                item.get("content") or
                item.get("description") or
                item.get("type", "")
            )

            # Type label if present
            item_type = item.get("type", "")
            if item_type and not content.startswith(item_type):
                content = f"{item_type}: {content}"

            # Build line
            content = self.truncate(content, self.width - 30)
            if timestamp and formatted_id:
                line = f"  {scope_marker} {timestamp} {formatted_id} {content}"
            elif formatted_id:
                line = f"  {scope_marker} {formatted_id} {content}"
            else:
                line = f"  {scope_marker} {content}"

            lines.append(line)

        return lines

    # =========================================================================
    # Nested List
    # =========================================================================

    def _render_nested(self, items: List[Dict], level: int = 0) -> List[str]:
        """Render nested list with indentation."""
        s = self.symbols
        lines = []
        indent = "  " * (level + 1)

        for i, item in enumerate(items):
            is_last = i == len(items) - 1

            # Tree branch marker
            if level > 0:
                branch = s.tree_end if is_last else s.tree_branch
            else:
                branch = s.bullet

            # Item text
            text = (
                item.get("text") or
                item.get("summary") or
                item.get("name") or
                str(item)
            )
            text = self.truncate(text, self.width - len(indent) - 4)

            lines.append(f"{indent}{branch} {text}")

            # Recurse for children
            children = item.get("children") or item.get("items", [])
            if children:
                lines.extend(self._render_nested(children, level + 1))

        return lines
