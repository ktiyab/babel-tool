"""
GatherPlan — Contract between LLM planning and parallel execution.

The LLM's planning phase produces a GatherPlan that specifies:
- What sources to gather (files, greps, commands)
- Why they're needed (operation intent)
- Priority hints for chunking

This plan is the INPUT to the parallel gather system.
It is produced by sequential LLM reasoning (cannot be parallelized).

Design principles:
- Explicit and reviewable (HC2: Human Authority)
- Serializable for storage/transmission
- Supports size estimation before execution
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class SourceType(Enum):
    """Types of sources that can be gathered."""
    FILE = "file"      # Read file content
    GREP = "grep"      # Search for pattern
    BASH = "bash"      # Execute command
    GLOB = "glob"      # Find files matching pattern
    SYMBOL = "symbol"  # Load code symbol by name (class, function, method)


class SourcePriority(Enum):
    """Priority levels for chunking decisions."""
    CRITICAL = 0   # Must be in first chunk
    HIGH = 1       # Important, prefer early chunks
    NORMAL = 2     # Standard priority
    LOW = 3        # Can be in later chunks or skipped


@dataclass
class GatherSource:
    """
    Specification for a single source to gather.

    Created by LLM during planning phase.
    Executed by ContextGatherer during parallel phase.
    """

    # What to gather
    source_type: SourceType
    reference: str  # path, pattern, or command

    # Optional parameters (type-specific)
    params: Dict[str, Any] = field(default_factory=dict)

    # Chunking hints
    priority: SourcePriority = SourcePriority.NORMAL
    group: Optional[str] = None  # Grouping hint (e.g., "cache", "api")

    # Size estimate (populated by broker before execution)
    estimated_size_bytes: int = 0

    @property
    def type_str(self) -> str:
        """String representation of source type."""
        return self.source_type.value

    def args(self) -> Tuple:
        """Arguments tuple for gather function call."""
        if self.source_type == SourceType.FILE:
            return (self.reference,)
        elif self.source_type == SourceType.GREP:
            path = self.params.get("path", ".")
            return (self.reference, path)
        elif self.source_type == SourceType.BASH:
            return (self.reference,)
        elif self.source_type == SourceType.GLOB:
            return (self.reference,)
        elif self.source_type == SourceType.SYMBOL:
            project_dir = self.params.get("project_dir")
            return (self.reference, project_dir)
        return (self.reference,)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage."""
        return {
            "source_type": self.source_type.value,
            "reference": self.reference,
            "params": self.params,
            "priority": self.priority.value,
            "group": self.group,
            "estimated_size_bytes": self.estimated_size_bytes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GatherSource":
        """Deserialize from storage."""
        return cls(
            source_type=SourceType(data["source_type"]),
            reference=data["reference"],
            params=data.get("params", {}),
            priority=SourcePriority(data.get("priority", 2)),
            group=data.get("group"),
            estimated_size_bytes=data.get("estimated_size_bytes", 0),
        )

    # Factory methods for common source types

    @classmethod
    def file(
        cls,
        path: str,
        priority: SourcePriority = SourcePriority.NORMAL,
        group: Optional[str] = None
    ) -> "GatherSource":
        """Create a file source."""
        return cls(
            source_type=SourceType.FILE,
            reference=path,
            priority=priority,
            group=group,
        )

    @classmethod
    def grep(
        cls,
        pattern: str,
        path: str = ".",
        priority: SourcePriority = SourcePriority.NORMAL,
        group: Optional[str] = None
    ) -> "GatherSource":
        """Create a grep source."""
        return cls(
            source_type=SourceType.GREP,
            reference=pattern,
            params={"path": path},
            priority=priority,
            group=group,
        )

    @classmethod
    def bash(
        cls,
        command: str,
        priority: SourcePriority = SourcePriority.NORMAL,
        group: Optional[str] = None,
        timeout: float = 30.0
    ) -> "GatherSource":
        """Create a bash source."""
        return cls(
            source_type=SourceType.BASH,
            reference=command,
            params={"timeout": timeout},
            priority=priority,
            group=group,
        )

    @classmethod
    def glob(
        cls,
        pattern: str,
        priority: SourcePriority = SourcePriority.NORMAL,
        group: Optional[str] = None
    ) -> "GatherSource":
        """Create a glob source."""
        return cls(
            source_type=SourceType.GLOB,
            reference=pattern,
            priority=priority,
            group=group,
        )

    @classmethod
    def symbol(
        cls,
        name: str,
        project_dir: Optional[str] = None,
        priority: SourcePriority = SourcePriority.NORMAL,
        group: Optional[str] = None
    ) -> "GatherSource":
        """
        Create a symbol source (loads code symbol by name).

        Args:
            name: Symbol name (e.g., "GraphStore", "gather_file")
            project_dir: Project directory for symbol lookup
            priority: Priority for chunking
            group: Grouping hint

        Returns:
            GatherSource for the symbol
        """
        return cls(
            source_type=SourceType.SYMBOL,
            reference=name,
            params={"project_dir": project_dir},
            priority=priority,
            group=group,
        )


@dataclass
class GatherPlan:
    """
    Complete specification for a context gather operation.

    Produced by LLM planning phase.
    Consumed by ChunkBroker and ContextGatherer.
    """

    # Intent (for template header)
    operation: str       # What task this supports (e.g., "Fix caching bug")
    intent: str          # Why this context is needed

    # Sources to gather
    sources: List[GatherSource] = field(default_factory=list)

    # Metadata
    created_by: str = ""  # Which LLM/agent created this plan

    @property
    def source_count(self) -> int:
        """Number of sources in plan."""
        return len(self.sources)

    @property
    def total_estimated_size(self) -> int:
        """Total estimated size in bytes."""
        return sum(s.estimated_size_bytes for s in self.sources)

    @property
    def total_estimated_size_kb(self) -> float:
        """Total estimated size in KB."""
        return self.total_estimated_size / 1024

    def sources_by_type(self, source_type: SourceType) -> List[GatherSource]:
        """Get sources of a specific type."""
        return [s for s in self.sources if s.source_type == source_type]

    def sources_by_group(self, group: str) -> List[GatherSource]:
        """Get sources in a specific group."""
        return [s for s in self.sources if s.group == group]

    def sources_by_priority(self, priority: SourcePriority) -> List[GatherSource]:
        """Get sources with a specific priority."""
        return [s for s in self.sources if s.priority == priority]

    def add_file(self, path: str, **kwargs) -> "GatherPlan":
        """Add a file source (fluent interface)."""
        self.sources.append(GatherSource.file(path, **kwargs))
        return self

    def add_grep(self, pattern: str, path: str = ".", **kwargs) -> "GatherPlan":
        """Add a grep source (fluent interface)."""
        self.sources.append(GatherSource.grep(pattern, path, **kwargs))
        return self

    def add_bash(self, command: str, **kwargs) -> "GatherPlan":
        """Add a bash source (fluent interface)."""
        self.sources.append(GatherSource.bash(command, **kwargs))
        return self

    def add_glob(self, pattern: str, **kwargs) -> "GatherPlan":
        """Add a glob source (fluent interface)."""
        self.sources.append(GatherSource.glob(pattern, **kwargs))
        return self

    def add_symbol(self, name: str, project_dir: str = None, **kwargs) -> "GatherPlan":
        """Add a symbol source (fluent interface)."""
        self.sources.append(GatherSource.symbol(name, project_dir=project_dir, **kwargs))
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage."""
        return {
            "operation": self.operation,
            "intent": self.intent,
            "sources": [s.to_dict() for s in self.sources],
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GatherPlan":
        """Deserialize from storage."""
        return cls(
            operation=data["operation"],
            intent=data["intent"],
            sources=[GatherSource.from_dict(s) for s in data.get("sources", [])],
            created_by=data.get("created_by", ""),
        )

    def summary(self) -> str:
        """Human-readable summary of the plan."""
        lines = [
            f"GatherPlan: {self.operation}",
            f"  Intent: {self.intent}",
            f"  Sources: {self.source_count}",
        ]

        # Count by type
        by_type = {}
        for s in self.sources:
            by_type[s.type_str] = by_type.get(s.type_str, 0) + 1

        for t, count in by_type.items():
            lines.append(f"    - {t}: {count}")

        if self.total_estimated_size > 0:
            lines.append(f"  Estimated size: {self.total_estimated_size_kb:.1f} KB")

        return "\n".join(lines)
