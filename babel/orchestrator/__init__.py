"""
Task Orchestrator — Parallel execution framework for Babel

Public API for parallelizing Babel operations while maintaining
HC1 (append-only) compliance through single-writer pattern.

Usage:
    from babel.orchestrator import orchestrator, io_task, cpu_task, Priority

    # Submit I/O-bound task (LLM calls, file I/O)
    task = io_task(
        fn=call_llm,
        args=("prompt",),
        priority=Priority.HIGH
    )
    future = orchestrator.submit(task)
    result = future.result()

    # Submit CPU-bound task (parsing, similarity)
    task = cpu_task(
        fn=compute_similarity,
        args=(text1, text2),
        priority=Priority.NORMAL
    )
    future = orchestrator.submit(task)

    # Parallel map for batch operations
    results = orchestrator.map_parallel(process_item, items)

    # Graceful shutdown
    orchestrator.shutdown()

Configuration via environment variables:
    BABEL_PARALLEL_ENABLED=true    # Enable/disable parallelization
    BABEL_IO_WORKERS=4             # Thread pool size for I/O
    BABEL_CPU_WORKERS=2            # Process pool size for CPU (default: CPU_COUNT // 2)
    BABEL_LLM_CONCURRENT=3         # Max concurrent LLM calls
    BABEL_TASK_TIMEOUT=60          # Default task timeout (seconds)
"""

import threading
from typing import List, Callable, Any, Optional, Dict
from concurrent.futures import Future

from .task import (
    Task, TaskType, Priority, TaskStatus, TaskResult,
    io_task, cpu_task
)
from .config import OrchestratorConfig
from .scheduler import PriorityScheduler
from .pools import IOPool, CPUPool
from .aggregator import ResultAggregator, BatchWriter
from .metrics import MetricsCollector


class TaskOrchestrator:
    """
    Central coordinator for parallel task execution.

    Manages:
    - Priority scheduling (CRITICAL > HIGH > NORMAL > BACKGROUND)
    - Typed worker pools (ThreadPool for I/O, ProcessPool for CPU)
    - Result aggregation (thread-safe collection)
    - Metrics collection (observability)

    HC1 Compliance:
    - Single writer pattern for event store
    - Results aggregated before writing
    - Atomic batch commits

    Thread Safety:
    - All public methods are thread-safe
    - Internal state protected by locks
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        Initialize the orchestrator.

        Args:
            config: Configuration. If None, loads from environment.
        """
        self._config = config or OrchestratorConfig.from_env()
        self._config.validate()

        self._lock = threading.Lock()
        self._started = False
        self._shutdown = False

        # Core components (lazy initialization)
        self._scheduler: Optional[PriorityScheduler] = None
        self._io_pool: Optional[IOPool] = None
        self._cpu_pool: Optional[CPUPool] = None
        self._aggregator: Optional[ResultAggregator] = None
        self._metrics: Optional[MetricsCollector] = None

    def _ensure_started(self) -> None:
        """Lazily initialize components on first use."""
        if self._started:
            return

        with self._lock:
            if self._started:
                return

            if not self._config.enabled:
                self._started = True
                return

            self._scheduler = PriorityScheduler()
            self._io_pool = IOPool(self._config)
            self._cpu_pool = CPUPool(self._config)
            self._aggregator = ResultAggregator()
            self._metrics = MetricsCollector()

            self._started = True

    @property
    def enabled(self) -> bool:
        """Check if parallelization is enabled."""
        return self._config.enabled

    @property
    def config(self) -> OrchestratorConfig:
        """Get current configuration."""
        return self._config

    def submit(self, task: Task) -> Future:
        """
        Submit a task for parallel execution.

        Routes to appropriate pool based on task type:
        - IO_BOUND → ThreadPool (LLM, file, network)
        - CPU_BOUND → ProcessPool (parsing, similarity)

        Args:
            task: Task to execute

        Returns:
            Future that resolves to TaskResult

        Raises:
            RuntimeError: If orchestrator is shut down or disabled
        """
        self._ensure_started()

        if self._shutdown:
            raise RuntimeError("Orchestrator is shut down")

        if not self._config.enabled:
            # Sequential fallback
            return self._execute_sequential(task)

        # Record submission
        if self._metrics:
            self._metrics.record_task_submitted(task)

        # Route to appropriate pool
        if task.task_type == TaskType.IO_BOUND:
            future = self._io_pool.submit(task)
        else:
            future = self._cpu_pool.submit(task)

        # Add result callback
        future.add_done_callback(
            lambda f: self._on_task_complete(f, task)
        )

        return future

    def submit_batch(self, tasks: List[Task]) -> List[Future]:
        """
        Submit multiple tasks atomically.

        All tasks are scheduled before any execution begins,
        ensuring priority ordering is respected.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of Futures in same order as tasks
        """
        self._ensure_started()

        if self._shutdown:
            raise RuntimeError("Orchestrator is shut down")

        if not self._config.enabled:
            return [self._execute_sequential(t) for t in tasks]

        futures = []
        for task in tasks:
            futures.append(self.submit(task))

        return futures

    def map_parallel(
        self,
        fn: Callable,
        items: List[Any],
        task_type: TaskType = TaskType.CPU_BOUND,
        priority: Priority = Priority.NORMAL,
        timeout: Optional[float] = None
    ) -> List[Any]:
        """
        Parallel map operation.

        Applies fn to each item in parallel, returning results
        in the same order as items.

        Args:
            fn: Function to apply (must be picklable for CPU tasks)
            items: Items to process
            task_type: IO_BOUND or CPU_BOUND
            priority: Task priority
            timeout: Optional timeout for entire operation

        Returns:
            List of results in same order as items

        Raises:
            RuntimeError: If orchestrator is shut down
        """
        self._ensure_started()

        if not items:
            return []

        if self._shutdown:
            raise RuntimeError("Orchestrator is shut down")

        if not self._config.enabled:
            # Sequential fallback
            return [fn(item) for item in items]

        # For CPU-bound work, use ProcessPool's built-in map
        if task_type == TaskType.CPU_BOUND and self._cpu_pool:
            return self._cpu_pool.map(fn, items, timeout=timeout)

        # For I/O-bound work, submit individual tasks
        tasks = [
            io_task(fn=fn, args=(item,), priority=priority)
            for item in items
        ]
        futures = self.submit_batch(tasks)

        # Collect results in order
        results = []
        for future in futures:
            result = future.result(timeout=timeout)
            if result.success:
                results.append(result.result)
            else:
                # Propagate error
                raise RuntimeError(f"Task failed: {result.error}")

        return results

    def drain_results(self, timeout: float = 0.1) -> List[TaskResult]:
        """
        Drain all completed results.

        Non-blocking after timeout. Used for batch processing.

        Args:
            timeout: Max wait time for first result

        Returns:
            List of completed TaskResults
        """
        self._ensure_started()

        if not self._config.enabled or not self._aggregator:
            return []

        return self._aggregator.drain(timeout=timeout)

    def collect_results(
        self,
        task_ids: List[str],
        timeout: float = 30.0
    ) -> Dict[str, TaskResult]:
        """
        Collect results for specific task IDs.

        Blocks until all tasks complete or timeout.

        Args:
            task_ids: IDs of tasks to collect
            timeout: Max wait time

        Returns:
            Dict mapping task_id -> TaskResult
        """
        self._ensure_started()

        if not self._config.enabled or not self._aggregator:
            return {}

        return self._aggregator.collect_by_task_ids(task_ids, timeout=timeout)

    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics summary."""
        self._ensure_started()

        if not self._config.enabled or not self._metrics:
            return {"enabled": False}

        summary = self._metrics.get_summary()
        summary["enabled"] = True
        summary["config"] = self._config.to_dict()

        # Add pool stats
        if self._io_pool:
            summary["io_pool"] = self._io_pool.stats().to_dict()
        if self._cpu_pool:
            summary["cpu_pool"] = self._cpu_pool.stats().to_dict()

        return summary

    def get_throughput(self, window_seconds: float = 60.0) -> Dict[str, float]:
        """Get throughput metrics (tasks per second)."""
        self._ensure_started()

        if not self._config.enabled or not self._metrics:
            return {"enabled": False}

        return self._metrics.get_throughput(window_seconds)

    def pending_count(self) -> int:
        """Get number of pending tasks in scheduler."""
        if not self._config.enabled or not self._scheduler:
            return 0
        return self._scheduler.pending_count()

    def shutdown(self, wait: bool = True, cancel_pending: bool = False) -> None:
        """
        Shutdown the orchestrator.

        Args:
            wait: If True, wait for pending tasks to complete
            cancel_pending: If True, cancel pending tasks
        """
        with self._lock:
            if self._shutdown:
                return

            self._shutdown = True

            # Shutdown scheduler first
            if self._scheduler:
                self._scheduler.shutdown(cancel_pending=cancel_pending)

            # Shutdown pools
            timeout = self._config.shutdown_timeout if wait else 0

            if self._io_pool:
                self._io_pool.shutdown(wait=wait)

            if self._cpu_pool:
                self._cpu_pool.shutdown(wait=wait)

    def _execute_sequential(self, task: Task) -> Future:
        """
        Execute task sequentially (fallback mode).

        Returns a completed Future for API compatibility.
        """
        from concurrent.futures import Future
        from datetime import datetime

        future = Future()
        started_at = datetime.utcnow()

        try:
            result_value = task.fn(*task.args, **task.kwargs)
            completed_at = datetime.utcnow()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result=result_value,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms
            )
            future.set_result(result)

        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms
            )
            future.set_result(result)

        return future

    def _on_task_complete(self, future: Future, task: Task) -> None:
        """Callback when a task completes."""
        try:
            result = future.result()

            # Record metrics
            if self._metrics:
                self._metrics.record_task_completed(result, task.task_type)

            # Add to aggregator
            if self._aggregator:
                self._aggregator.submit(result)

        except Exception:
            # Task raised exception
            if self._metrics:
                self._metrics.record_error(task.task_type, "exception")


# Global orchestrator instance (singleton pattern)
_orchestrator: Optional[TaskOrchestrator] = None
_orchestrator_lock = threading.Lock()


def get_orchestrator() -> TaskOrchestrator:
    """
    Get the global orchestrator instance.

    Creates one if it doesn't exist, using environment configuration.
    """
    global _orchestrator

    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                _orchestrator = TaskOrchestrator()

    return _orchestrator


def reset_orchestrator() -> None:
    """
    Reset the global orchestrator.

    Useful for testing or reconfiguration.
    """
    global _orchestrator

    with _orchestrator_lock:
        if _orchestrator is not None:
            _orchestrator.shutdown(wait=True)
            _orchestrator = None


# Convenience alias
orchestrator = property(lambda self: get_orchestrator())


# Public API exports
__all__ = [
    # Main class
    "TaskOrchestrator",

    # Task types
    "Task",
    "TaskType",
    "Priority",
    "TaskStatus",
    "TaskResult",

    # Factory functions
    "io_task",
    "cpu_task",

    # Configuration
    "OrchestratorConfig",

    # Components (for advanced usage)
    "PriorityScheduler",
    "IOPool",
    "CPUPool",
    "ResultAggregator",
    "BatchWriter",
    "MetricsCollector",

    # Global instance
    "get_orchestrator",
    "reset_orchestrator",
]
