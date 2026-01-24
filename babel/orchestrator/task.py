"""
Task — Unit of parallelizable work

Defines the core abstractions for the orchestrator:
- Task: Unit of work with type, priority, and dependencies
- TaskType: I/O-bound vs CPU-bound classification
- Priority: Scheduling priority levels
- TaskResult: Outcome of task execution

Design principles:
- Tasks are immutable after creation
- Tasks carry all context needed for execution
- Results are serializable for cross-process communication
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any, List, Dict, Optional
from datetime import datetime, timezone
import xxhash


class TaskType(Enum):
    """Classification for routing to appropriate worker pool."""
    IO_BOUND = "io"      # LLM calls, file I/O, network (ThreadPool)
    CPU_BOUND = "cpu"    # Parsing, similarity, algorithms (ProcessPool)


class Priority(Enum):
    """
    Task priority levels for scheduling.

    Lower value = higher priority (processed first).
    """
    CRITICAL = 0    # User is waiting, blocking operation
    HIGH = 1        # User-facing, but not blocking
    NORMAL = 2      # Batch operations
    BACKGROUND = 3  # Cache warming, prefetch


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Task:
    """
    Unit of parallelizable work.

    Immutable after creation. Carries all context needed for execution.
    """
    # Identity
    id: str = field(default_factory=lambda: _generate_task_id())

    # Classification
    task_type: TaskType = TaskType.IO_BOUND
    priority: Priority = Priority.NORMAL

    # Execution
    fn: Callable = field(default=None)
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Limits
    timeout: float = 60.0  # seconds
    retries: int = 0

    # Rate limiting (only applies to LLM API calls)
    is_llm_call: bool = False  # If True, rate limiter is applied

    # Metadata (for observability)
    name: str = ""
    command: str = ""  # Which babel command created this
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.id == other.id
        return False


@dataclass
class TaskResult:
    """
    Outcome of task execution.

    Serializable for cross-process communication (ProcessPool).
    """
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None

    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None

    # Retries
    attempt: int = 1

    @property
    def success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return self.status == TaskStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for cross-process communication."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result if _is_serializable(self.result) else str(self.result),
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "attempt": self.attempt
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """Deserialize from cross-process communication."""
        return cls(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms"),
            attempt=data.get("attempt", 1)
        )


def _generate_task_id() -> str:
    """Generate unique task ID using xxhash (5x faster than hashlib)."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return xxhash.xxh64(timestamp.encode()).hexdigest()[:12]


def _is_serializable(obj: Any) -> bool:
    """Check if object can be serialized for cross-process communication."""
    try:
        import orjson
        orjson.dumps(obj)
        return True
    except (TypeError, orjson.JSONEncodeError):
        return False


# Task factory functions for common patterns

def io_task(
    fn: Callable,
    args: tuple = (),
    kwargs: Dict[str, Any] = None,
    priority: Priority = Priority.NORMAL,
    name: str = "",
    timeout: float = 60.0,
    is_llm_call: bool = False
) -> Task:
    """
    Create an I/O-bound task (LLM, file, network).

    Args:
        fn: Function to execute
        args: Positional arguments tuple for fn
        kwargs: Keyword arguments dict for fn
        priority: Task priority (default: NORMAL)
        name: Optional task name for observability
        timeout: Execution timeout in seconds (default: 60)
        is_llm_call: If True, rate limiter is applied (default: False)

    Example:
        task = io_task(fn=call_llm, args=("prompt",), priority=Priority.HIGH, is_llm_call=True)
    """
    return Task(
        task_type=TaskType.IO_BOUND,
        priority=priority,
        fn=fn,
        args=args,
        kwargs=kwargs or {},
        name=name,
        timeout=timeout,
        is_llm_call=is_llm_call
    )


def cpu_task(
    fn: Callable,
    args: tuple = (),
    kwargs: Dict[str, Any] = None,
    priority: Priority = Priority.NORMAL,
    name: str = "",
    timeout: float = 30.0
) -> Task:
    """
    Create a CPU-bound task (parsing, similarity, algorithms).

    Args:
        fn: Function to execute (must be picklable for ProcessPool)
        args: Positional arguments tuple for fn
        kwargs: Keyword arguments dict for fn
        priority: Task priority (default: NORMAL)
        name: Optional task name for observability
        timeout: Execution timeout in seconds (default: 30)

    Example:
        task = cpu_task(fn=compute_similarity, args=(text1, text2))
    """
    return Task(
        task_type=TaskType.CPU_BOUND,
        priority=priority,
        fn=fn,
        args=args,
        kwargs=kwargs or {},
        name=name,
        timeout=timeout
    )
