"""
PriorityScheduler — Task scheduling with priority queues

Implements a 4-level priority queue system:
- CRITICAL: User is waiting, blocking operation
- HIGH: User-facing, but not blocking
- NORMAL: Batch operations
- BACKGROUND: Cache warming, prefetch

Higher priority tasks are always processed first.
Within same priority, FIFO order is maintained.
"""

import threading
from collections import deque
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from .task import Task, Priority


@dataclass
class SchedulerStats:
    """Statistics for scheduler observability."""
    total_submitted: int = 0
    total_processed: int = 0
    queue_depths: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_submitted": self.total_submitted,
            "total_processed": self.total_processed,
            "queue_depths": self.queue_depths,
            "pending": self.total_submitted - self.total_processed
        }


class PriorityScheduler:
    """
    Task scheduler with 4 priority levels.

    Thread-safe. Higher priority = processed first.
    """

    def __init__(self):
        # One queue per priority level
        self._queues: Dict[Priority, deque] = {
            Priority.CRITICAL: deque(),
            Priority.HIGH: deque(),
            Priority.NORMAL: deque(),
            Priority.BACKGROUND: deque(),
        }

        # Thread safety
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

        # Statistics
        self._stats = SchedulerStats()

        # Shutdown flag
        self._shutdown = False

    def submit(self, task: Task) -> None:
        """
        Submit a task for scheduling.

        Thread-safe. Task is placed in priority-appropriate queue.
        """
        with self._not_empty:
            if self._shutdown:
                raise RuntimeError("Scheduler is shut down")

            self._queues[task.priority].append(task)
            self._stats.total_submitted += 1
            self._not_empty.notify()

    def submit_batch(self, tasks: List[Task]) -> None:
        """
        Submit multiple tasks atomically.

        Thread-safe. All tasks added before any notifications.
        """
        with self._not_empty:
            if self._shutdown:
                raise RuntimeError("Scheduler is shut down")

            for task in tasks:
                self._queues[task.priority].append(task)
                self._stats.total_submitted += 1

            # Notify once for all (more efficient than per-task)
            self._not_empty.notify_all()

    def get(self, timeout: Optional[float] = None) -> Optional[Task]:
        """
        Get the highest priority task.

        Blocks until a task is available or timeout expires.
        Returns None on timeout or shutdown.
        """
        with self._not_empty:
            # Wait for a task to be available
            while not self._has_tasks() and not self._shutdown:
                if not self._not_empty.wait(timeout):
                    return None  # Timeout

            if self._shutdown and not self._has_tasks():
                return None

            # Get from highest priority non-empty queue
            for priority in Priority:
                queue = self._queues[priority]
                if queue:
                    task = queue.popleft()
                    self._stats.total_processed += 1
                    return task

            return None

    def get_nowait(self) -> Optional[Task]:
        """
        Get the highest priority task without blocking.

        Returns None if no tasks available.
        """
        with self._lock:
            for priority in Priority:
                queue = self._queues[priority]
                if queue:
                    task = queue.popleft()
                    self._stats.total_processed += 1
                    return task
            return None

    def peek(self) -> Optional[Task]:
        """
        Peek at the highest priority task without removing it.

        Returns None if no tasks available.
        """
        with self._lock:
            for priority in Priority:
                queue = self._queues[priority]
                if queue:
                    return queue[0]
            return None

    def pending_count(self) -> int:
        """Get total number of pending tasks."""
        with self._lock:
            return sum(len(q) for q in self._queues.values())

    def pending_by_priority(self) -> Dict[Priority, int]:
        """Get pending task counts by priority."""
        with self._lock:
            return {p: len(q) for p, q in self._queues.items()}

    def stats(self) -> SchedulerStats:
        """Get scheduler statistics."""
        with self._lock:
            self._stats.queue_depths = {
                p.name: len(q) for p, q in self._queues.items()
            }
            return SchedulerStats(
                total_submitted=self._stats.total_submitted,
                total_processed=self._stats.total_processed,
                queue_depths=self._stats.queue_depths.copy()
            )

    def shutdown(self, cancel_pending: bool = False) -> List[Task]:
        """
        Shutdown the scheduler.

        Args:
            cancel_pending: If True, return and clear pending tasks

        Returns:
            List of cancelled tasks if cancel_pending=True, else empty list
        """
        cancelled = []

        with self._not_empty:
            self._shutdown = True

            if cancel_pending:
                for queue in self._queues.values():
                    cancelled.extend(queue)
                    queue.clear()

            # Wake all waiting threads
            self._not_empty.notify_all()

        return cancelled

    def _has_tasks(self) -> bool:
        """Check if any queue has tasks (must hold lock)."""
        return any(q for q in self._queues.values())
