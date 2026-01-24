"""
DetailRenderer — Render single item with full details

Supports:
- Key-value pairs
- Status indicators
- Nested properties
- Action prompts
"""

from typing import TYPE_CHECKING, Dict, Any, List

from .base import BaseRenderer

if TYPE_CHECKING:
    from . import OutputSpec


class DetailRenderer(BaseRenderer):
    """
    Render single item view with detailed information.

    Format:
        Title [ID]
          "summary"

        Field: value
        Field: value

        Status: indicator

        Next steps:
          -> babel command <id>
    """

    def render(self, spec: "OutputSpec") -> str:
        """
        Render OutputSpec as detailed view.

        Expected data format:
        - Dict with fields to display
        - Can have special keys: _id, _type, _summary, _status, _actions

        Args:
            spec: OutputSpec with data

        Returns:
            Formatted detail string
        """
        if not spec.data:
            return spec.empty_message

        if not isinstance(spec.data, dict):
            return str(spec.data)

        data = spec.data
        s = self.symbols
        lines = []

        # Header: Type [ID]
        item_type = data.get("_type", data.get("type", ""))
        item_id = data.get("_id", data.get("id", ""))
        summary = data.get("_summary", data.get("summary", ""))

        if spec.title:
            lines.append(f"\n{spec.title}")
        elif item_type or item_id:
            header = item_type.title() if item_type else "Item"
            if item_id:
                header += f" {self.format_id(item_id)}"
            lines.append(f"\n{header}")

        # Summary quote
        if summary:
            summary = self.truncate(summary, self.width - 6)
            lines.append(f'  "{summary}"')

        lines.append("")  # Blank line

        # Main fields (skip special keys)
        special_keys = {"_id", "_type", "_summary", "_status", "_actions", "id", "type", "summary"}
        for key, value in data.items():
            if key in special_keys:
                continue
            if key.startswith("_"):
                continue

            # Format key nicely
            label = key.replace("_", " ").title()

            # Format value
            if isinstance(value, dict):
                lines.append(f"  {label}:")
                for k, v in value.items():
                    v_str = self.truncate(str(v), self.width - 10)
                    lines.append(f"    {k}: {v_str}")
            elif isinstance(value, list):
                lines.append(f"  {label}:")
                for item in value[:5]:  # Limit to 5 items
                    item_str = self.truncate(str(item), self.width - 6)
                    lines.append(f"    {s.bullet} {item_str}")
                if len(value) > 5:
                    lines.append(f"    ... and {len(value) - 5} more")
            else:
                value_str = self.truncate(str(value), self.width - len(label) - 6)
                lines.append(f"  {label}: {value_str}")

        # Status section
        status = data.get("_status", data.get("status"))
        if status:
            lines.append("")
            if isinstance(status, dict):
                status_text = status.get("text", str(status))
                status_icon = status.get("icon", "")
                lines.append(f"  Status: {status_icon} {status_text}")
            else:
                lines.append(f"  Status: {status}")

        # Actions section
        if spec.show_actions:
            actions = data.get("_actions", data.get("actions", []))
            if actions:
                lines.append("")
                lines.append("  Next steps:")
                for action in actions:
                    if isinstance(action, dict):
                        cmd = action.get("command", "")
                        desc = action.get("description", "")
                        lines.append(f"    {s.arrow} {cmd}")
                        if desc:
                            lines.append(f"       {desc}")
                    else:
                        lines.append(f"    {s.arrow} {action}")

        return "\n".join(lines)
