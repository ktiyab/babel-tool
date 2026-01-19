"""
SummaryRenderer — Render overview/status summaries

Supports:
- Key-value metrics
- Conditional sections (only shown if relevant)
- Status indicators with icons
- Warning/alert sections
"""

from typing import TYPE_CHECKING, Dict, Any, List

from .base import BaseRenderer

if TYPE_CHECKING:
    from . import OutputSpec


class SummaryRenderer(BaseRenderer):
    """
    Render summary/overview displays.

    Format:
        Title
        Key: value
        Key: value

        [Conditional Section]
        Warning: message
          -> action

        [OK] Health: Good
    """

    def render(self, spec: "OutputSpec") -> str:
        """
        Render OutputSpec as summary view.

        Expected data format:
        - Dict with sections/metrics
        - Special keys: _metrics, _sections, _health, _warnings, _actions

        Args:
            spec: OutputSpec with data

        Returns:
            Formatted summary string
        """
        if not spec.data:
            return spec.empty_message

        if not isinstance(spec.data, dict):
            return str(spec.data)

        data = spec.data
        s = self.symbols
        lines = []

        # Title
        if spec.title:
            lines.append(spec.title)
            lines.append("")

        # Metrics section (key-value pairs at top)
        metrics = data.get("_metrics", {})
        if not metrics:
            # Extract simple top-level values as metrics
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                if isinstance(value, (str, int, float, bool)):
                    metrics[key] = value

        for key, value in metrics.items():
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {value}")

        # Sections (conditional display)
        sections = data.get("_sections", [])
        for section in sections:
            if not section:
                continue

            # Check condition
            condition = section.get("condition", True)
            if callable(condition):
                condition = condition()
            if not condition:
                continue

            lines.append("")  # Blank before section

            # Section header with icon
            title = section.get("title", "")
            icon = section.get("icon", "")
            if title:
                lines.append(f"{icon} {title}" if icon else title)

            # Section items
            items = section.get("items", [])
            for item in items[:5]:
                if isinstance(item, dict):
                    text = item.get("text", str(item))
                    item_id = item.get("id", "")
                    if item_id:
                        short_id = item_id[:8]
                        text = f"[{short_id}] {text}"
                else:
                    text = str(item)
                text = self.truncate(text, self.width - 4)
                lines.append(f"  {text}")

            if len(items) > 5:
                lines.append(f"  ... and {len(items) - 5} more")

            # Section action
            action = section.get("action")
            if action:
                lines.append(f"  {s.arrow} {action}")

        # Warnings section
        warnings = data.get("_warnings", [])
        if warnings:
            lines.append("")
            for warning in warnings:
                if isinstance(warning, dict):
                    text = warning.get("text", str(warning))
                    icon = warning.get("icon", s.check_warn)
                else:
                    text = str(warning)
                    icon = s.check_warn
                lines.append(f"{icon} {text}")

        # Health indicator
        health = data.get("_health")
        if health:
            lines.append("")
            if isinstance(health, dict):
                status = health.get("status", "")
                message = health.get("message", "")
                icon = health.get("icon", s.health_aligned)
                lines.append(f"{icon} {status}")
                if message:
                    lines.append(f"  {message}")
            else:
                lines.append(f"{s.health_aligned} {health}")

        # Actions at bottom
        if spec.show_actions:
            actions = data.get("_actions", [])
            if actions:
                lines.append("")
                for action in actions:
                    if isinstance(action, dict):
                        cmd = action.get("command", "")
                        lines.append(f"{s.arrow} {cmd}")
                    else:
                        lines.append(f"{s.arrow} {action}")

        return "\n".join(lines)
