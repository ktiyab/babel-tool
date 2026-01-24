"""
GatherResult — Common return type for gather functions.

All gather functions (file, grep, bash, glob) return this type,
enabling consistent handling in the gatherer and template layers.

Design principles:
- Immutable after creation (frozen dataclass)
- Carries all context needed for aggregation
- Size tracking enables chunking decisions
- Error handling built-in (success/error fields)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timezone


@dataclass(frozen=True)
class GatherResult:
    """
    Result of a gather operation.

    Returned by gather_file, gather_grep, gather_bash, gather_glob.
    Used by ContextGatherer to aggregate results and ContextTemplate to render.
    """

    # Source identification
    source_type: str  # "file", "grep", "bash", "glob"
    source_ref: str   # path, pattern, command - what was requested

    # Content
    content: str = ""  # The gathered content (may be empty on error)

    # Size tracking (for chunking decisions)
    size_bytes: int = 0
    line_count: int = 0

    # Status
    success: bool = True
    error: Optional[str] = None

    # Timing
    duration_ms: float = 0.0
    gathered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Type-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        """Check if gather failed."""
        return not self.success

    @property
    def size_kb(self) -> float:
        """Size in kilobytes."""
        return self.size_bytes / 1024

    def summary(self) -> str:
        """One-line summary for manifest display."""
        status = "✓" if self.success else "✗"
        size = f"{self.size_kb:.1f}KB" if self.size_bytes > 0 else "-"
        return f"{status} {self.source_type}: {self.source_ref} ({size})"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage or transmission."""
        return {
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "content": self.content,
            "size_bytes": self.size_bytes,
            "line_count": self.line_count,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "gathered_at": self.gathered_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GatherResult":
        """Deserialize from storage or transmission."""
        return cls(
            source_type=data["source_type"],
            source_ref=data["source_ref"],
            content=data.get("content", ""),
            size_bytes=data.get("size_bytes", 0),
            line_count=data.get("line_count", 0),
            success=data.get("success", True),
            error=data.get("error"),
            duration_ms=data.get("duration_ms", 0.0),
            gathered_at=data.get("gathered_at", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def error_result(
        cls,
        source_type: str,
        source_ref: str,
        error: str,
        duration_ms: float = 0.0
    ) -> "GatherResult":
        """Factory for creating error results."""
        return cls(
            source_type=source_type,
            source_ref=source_ref,
            content="",
            size_bytes=0,
            line_count=0,
            success=False,
            error=error,
            duration_ms=duration_ms,
        )
