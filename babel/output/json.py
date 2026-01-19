"""
JsonRenderer — Render data as JSON for piping/LLM consumption

Supports:
- Pretty-printed JSON output
- Compact mode for piping
- Clean data (strips internal keys)
"""

import json
from typing import TYPE_CHECKING, Any

from .base import BaseRenderer

if TYPE_CHECKING:
    from . import OutputSpec


class JsonRenderer(BaseRenderer):
    """
    Render data as JSON.

    Useful for:
    - Piping to jq or other tools
    - LLM consumption
    - Machine-readable output
    - Integration with other systems
    """

    def __init__(self, *args, compact: bool = False, **kwargs):
        """
        Initialize JSON renderer.

        Args:
            compact: If True, output single line (no indentation)
            *args, **kwargs: Passed to BaseRenderer
        """
        super().__init__(*args, **kwargs)
        self.compact = compact

    def render(self, spec: "OutputSpec") -> str:
        """
        Render OutputSpec as JSON.

        Args:
            spec: OutputSpec with data

        Returns:
            JSON string
        """
        # Clean the data (remove internal keys starting with _)
        data = self._clean_data(spec.data)

        # Add metadata wrapper if title provided
        if spec.title:
            output = {
                "title": spec.title,
                "data": data
            }
        else:
            output = data

        # Render JSON
        if self.compact:
            return json.dumps(output, default=self._json_serializer, ensure_ascii=False)
        else:
            return json.dumps(
                output,
                indent=2,
                default=self._json_serializer,
                ensure_ascii=False
            )

    def _clean_data(self, data: Any) -> Any:
        """
        Clean data by removing internal keys (starting with _).

        Args:
            data: Raw data

        Returns:
            Cleaned data
        """
        if isinstance(data, dict):
            return {
                k: self._clean_data(v)
                for k, v in data.items()
                if not k.startswith("_")
            }
        elif isinstance(data, list):
            return [self._clean_data(item) for item in data]
        else:
            return data

    def _json_serializer(self, obj: Any) -> Any:
        """
        Custom JSON serializer for non-standard types.

        Args:
            obj: Object to serialize

        Returns:
            JSON-serializable representation
        """
        # Handle common non-serializable types
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return {
                k: v for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        if hasattr(obj, "value"):  # Enum
            return obj.value
        # Last resort: string representation
        return str(obj)
