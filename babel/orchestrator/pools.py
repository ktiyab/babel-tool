"""
WorkerPools — Typed execution pools for parallel work

Implements two pool types:
- IOPool: ThreadPoolExecutor for I/O-bound work (LLM, file, network)
- CPUPool: ProcessPoolExecutor for CPU-bound work (parsing, similarity)

Design principles:
- ThreadPool for I/O (GIL doesn't block I/O operations)
- ProcessPool for CPU (bypasses GIL for true parallelism)
- Rate limiting for external APIs (LLM rate limits)
- Graceful degradation to sequential on failure
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from typing import Callable, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from .task import Task, TaskResult, TaskStatus
from .config import OrchestratorConfig


@dataclass
class PoolStats:
    """Statistics for pool observability."""
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        if self.completed_tasks == 0:
            return 0.0
        return self.total_duration_ms / self.completed_tasks

    def to_dict(self) -> dict:
        return {
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_duration_ms": round(self.avg_duration_ms, 2)
        }


class RateLimiter:
    """
    Token bucket rate limiter for LLM API calls.

    Prevents overwhelming external APIs with too many concurrent requests.
    """

    def __init__(self, max_concurrent: int = 3, rate_limit: float = 10.0):
        """
        Args:
            max_concurrent: Maximum concurrent requests
            rate_limit: Maximum requests per second
        """
        self._semaphore = threading.Semaphore(max_concurrent)
        self._rate_limit = rate_limit
        self._last_request = 0.0
        self._lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request.

        Blocks until permission granted or timeout.
        Returns True if acquired, False on timeout.
        """
        if not self._semaphore.acquire(timeout=timeout):
            return False

        # Enforce rate limit
        with self._lock:
            now = time.time()
            min_interval = 1.0 / self._rate_limit
            elapsed = now - self._last_request

            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

            self._last_request = time.time()

        return True

    def release(self) -> None:
        """Release permission after request completes."""
        self._semaphore.release()


class IOPool:
    """
    ThreadPool for I/O-bound operations.

    Suitable for: LLM API calls, file I/O, network requests.
    Uses threads because GIL doesn't block I/O operations.
    """

    def __init__(self, config: OrchestratorConfig):
        self._config = config
        self._executor = ThreadPoolExecutor(
            max_workers=config.io_workers,
            thread_name_prefix="babel-io-"
        )
        self._rate_limiter = RateLimiter(
            max_concurrent=config.llm_concurrent,
            rate_limit=config.llm_rate_limit
        )
        self._stats = PoolStats()
        self._lock = threading.Lock()
        self._shutdown = False

    def submit(self, task: Task) -> Future:
        """
        Submit an I/O-bound task for execution.

        Returns a Future that can be used to get the result.
        """
        if self._shutdown:
            raise RuntimeError("Pool is shut down")

        with self._lock:
            self._stats.active_tasks += 1

        future = self._executor.submit(self._execute_task, task)
        future.add_done_callback(lambda f: self._on_complete(f, task))
        return future

    def _execute_task(self, task: Task) -> TaskResult:
        """Execute a task with optional rate limiting and error handling."""
        started_at = datetime.now(timezone.utc)
        rate_limited = task.is_llm_call  # Only rate limit actual LLM calls

        # Acquire rate limit permission (only for LLM calls)
        if rate_limited:
            if not self._rate_limiter.acquire(timeout=task.timeout):
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error="Rate limit timeout",
                    started_at=started_at.isoformat()
                )

        try:
            result = task.fn(*task.args, **task.kwargs)

            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result=result,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms
            )

        except Exception as e:
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms
            )

        finally:
            if rate_limited:
                self._rate_limiter.release()

    def _on_complete(self, future: Future, task: Task) -> None:
        """Callback when task completes."""
        with self._lock:
            self._stats.active_tasks -= 1

            try:
                result = future.result()
                if result.success:
                    self._stats.completed_tasks += 1
                    self._stats.total_duration_ms += result.duration_ms or 0
                else:
                    self._stats.failed_tasks += 1
            except Exception:
                self._stats.failed_tasks += 1

    def stats(self) -> PoolStats:
        """Get pool statistics."""
        with self._lock:
            return PoolStats(
                active_tasks=self._stats.active_tasks,
                completed_tasks=self._stats.completed_tasks,
                failed_tasks=self._stats.failed_tasks,
                total_duration_ms=self._stats.total_duration_ms
            )

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the pool."""
        self._shutdown = True
        self._executor.shutdown(wait=wait)


class CPUPool:
    """
    ProcessPool for CPU-bound operations.

    Suitable for: Text similarity, AST parsing, graph algorithms.
    Uses processes to bypass GIL for true parallelism.
    """

    def __init__(self, config: OrchestratorConfig):
        self._config = config
        self._executor = ProcessPoolExecutor(max_workers=config.cpu_workers)
        self._stats = PoolStats()
        self._lock = threading.Lock()
        self._shutdown = False

    def submit(self, task: Task) -> Future:
        """
        Submit a CPU-bound task for execution.

        Note: task.fn must be picklable (top-level function).
        """
        if self._shutdown:
            raise RuntimeError("Pool is shut down")

        with self._lock:
            self._stats.active_tasks += 1

        # Use standalone function for pickling compatibility with ProcessPool
        future = self._executor.submit(_execute_cpu_task, task)
        future.add_done_callback(lambda f: self._on_complete(f, task))
        return future

    def _on_complete(self, future: Future, task: Task) -> None:
        """Callback when task completes."""
        with self._lock:
            self._stats.active_tasks -= 1

            try:
                result = future.result()
                if result.success:
                    self._stats.completed_tasks += 1
                    self._stats.total_duration_ms += result.duration_ms or 0
                else:
                    self._stats.failed_tasks += 1
            except Exception:
                self._stats.failed_tasks += 1

    def map(self, fn: Callable, items: List[Any], timeout: Optional[float] = None) -> List[Any]:
        """
        Parallel map operation.

        Blocks until all items processed.
        Returns results in same order as items.
        """
        if not items:
            return []

        if self._shutdown:
            raise RuntimeError("Pool is shut down")

        return list(self._executor.map(fn, items, timeout=timeout))

    def stats(self) -> PoolStats:
        """Get pool statistics."""
        with self._lock:
            return PoolStats(
                active_tasks=self._stats.active_tasks,
                completed_tasks=self._stats.completed_tasks,
                failed_tasks=self._stats.failed_tasks,
                total_duration_ms=self._stats.total_duration_ms
            )

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the pool."""
        self._shutdown = True
        self._executor.shutdown(wait=wait)


# Standalone execution for ProcessPool (must be picklable)
def _execute_cpu_task(task: Task) -> TaskResult:
    """Execute a CPU-bound task (standalone for ProcessPool)."""
    started_at = datetime.now(timezone.utc)

    try:
        result = task.fn(*task.args, **task.kwargs)

        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            result=result,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms
        )

    except Exception as e:
        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error=str(e),
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms
        )
