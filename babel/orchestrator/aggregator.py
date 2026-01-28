"""
ResultAggregator — HC1-compliant result collection

Implements the Single Writer pattern:
- Workers produce results into a thread-safe queue
- Aggregator collects, validates, and batches results
- Single writer thread applies results to event store

This ensures HC1 (append-only) compliance:
- Only one logical writer to event store
- Parallel execution without write conflicts
- Atomic batch commits for efficiency
"""

import threading
import queue
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from .task import TaskResult


@dataclass
class AggregatorStats:
    """Statistics for aggregator observability."""
    results_received: int = 0
    results_processed: int = 0
    batches_committed: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "results_received": self.results_received,
            "results_processed": self.results_processed,
            "batches_committed": self.batches_committed,
            "errors": self.errors,
            "pending": self.results_received - self.results_processed
        }


class ResultAggregator:
    """
    Collects results from parallel workers.

    HC1 Compliance:
    - Results queued from any thread
    - Single consumer drains and processes
    - Batch commits reduce I/O

    Usage:
        aggregator = ResultAggregator()

        # Workers submit results
        aggregator.submit(result)

        # Main thread processes
        results = aggregator.drain()
        for result in results:
            process(result)
    """

    def __init__(self, batch_size: int = 10, flush_interval: float = 1.0):
        """
        Args:
            batch_size: Max results per batch commit
            flush_interval: Seconds between auto-flushes
        """
        self._queue: queue.Queue = queue.Queue()
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._stats = AggregatorStats()
        self._lock = threading.Lock()

        # Result callbacks (for observers)
        self._callbacks: List[Callable[[TaskResult], None]] = []

        # Pending results buffer (for batching)
        self._buffer: List[TaskResult] = []
        self._last_flush = datetime.now(timezone.utc)

    def submit(self, result: TaskResult) -> None:
        """
        Submit a result from a worker.

        Thread-safe. Can be called from any thread.
        """
        self._queue.put(result)

        with self._lock:
            self._stats.results_received += 1

    def drain(self, timeout: float = 0.1) -> List[TaskResult]:
        """
        Drain all available results from the queue.

        Non-blocking after timeout. Returns list of results.
        """
        results = []

        while True:
            try:
                result = self._queue.get(timeout=timeout)
                results.append(result)

                with self._lock:
                    self._stats.results_processed += 1

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception:
                        pass  # Don't let callback errors break aggregation

            except queue.Empty:
                break

        return results

    def drain_blocking(self, count: int, timeout: float = 30.0) -> List[TaskResult]:
        """
        Drain exactly `count` results, blocking until available or timeout.

        Useful for waiting on a batch of parallel tasks.
        """
        results = []
        deadline = datetime.now(timezone.utc).timestamp() + timeout

        while len(results) < count:
            remaining = deadline - datetime.now(timezone.utc).timestamp()
            if remaining <= 0:
                break

            try:
                result = self._queue.get(timeout=min(remaining, 1.0))
                results.append(result)

                with self._lock:
                    self._stats.results_processed += 1

                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception:
                        pass

            except queue.Empty:
                continue

        return results

    def collect_by_task_ids(
        self,
        task_ids: List[str],
        timeout: float = 30.0
    ) -> Dict[str, TaskResult]:
        """
        Collect results for specific task IDs.

        Blocks until all tasks complete or timeout.
        Returns dict mapping task_id -> result.
        """
        collected: Dict[str, TaskResult] = {}
        remaining = set(task_ids)
        deadline = datetime.now(timezone.utc).timestamp() + timeout

        while remaining:
            time_left = deadline - datetime.now(timezone.utc).timestamp()
            if time_left <= 0:
                break

            try:
                result = self._queue.get(timeout=min(time_left, 1.0))

                with self._lock:
                    self._stats.results_processed += 1

                if result.task_id in remaining:
                    collected[result.task_id] = result
                    remaining.discard(result.task_id)

                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception:
                        pass

            except queue.Empty:
                continue

        return collected

    def add_callback(self, callback: Callable[[TaskResult], None]) -> None:
        """
        Add a callback to be notified of each result.

        Callbacks are called synchronously during drain.
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[TaskResult], None]) -> None:
        """Remove a previously added callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def pending_count(self) -> int:
        """Get number of results waiting to be drained."""
        return self._queue.qsize()

    def stats(self) -> AggregatorStats:
        """Get aggregator statistics."""
        with self._lock:
            return AggregatorStats(
                results_received=self._stats.results_received,
                results_processed=self._stats.results_processed,
                batches_committed=self._stats.batches_committed,
                errors=self._stats.errors
            )

    def clear(self) -> int:
        """
        Clear all pending results.

        Returns number of results cleared.
        """
        cleared = 0
        while True:
            try:
                self._queue.get_nowait()
                cleared += 1
            except queue.Empty:
                break

        return cleared


class BatchWriter:
    """
    Batches results for efficient event store writes.

    HC1 Compliance:
    - Single writer thread
    - Atomic batch commits
    - Preserves order within batch

    Usage:
        writer = BatchWriter(event_store)
        writer.start()

        # Submit results
        writer.submit(result)

        # Shutdown
        writer.stop()
    """

    def __init__(
        self,
        write_fn: Callable[[List[TaskResult]], None],
        batch_size: int = 10,
        flush_interval: float = 1.0
    ):
        """
        Args:
            write_fn: Function to write batch of results
            batch_size: Max results per batch
            flush_interval: Seconds between auto-flushes
        """
        self._write_fn = write_fn
        self._batch_size = batch_size
        self._flush_interval = flush_interval

        self._queue: queue.Queue = queue.Queue()
        self._buffer: List[TaskResult] = []
        self._last_flush = datetime.now(timezone.utc)

        self._thread: Optional[threading.Thread] = None
        self._shutdown = threading.Event()
        self._stats = AggregatorStats()
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the writer thread."""
        if self._thread is not None:
            return

        self._shutdown.clear()
        self._thread = threading.Thread(
            target=self._writer_loop,
            name="babel-batch-writer",
            daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the writer thread and flush remaining."""
        self._shutdown.set()

        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def submit(self, result: TaskResult) -> None:
        """Submit a result for batched writing."""
        self._queue.put(result)

        with self._lock:
            self._stats.results_received += 1

    def _writer_loop(self) -> None:
        """Writer thread main loop."""
        while not self._shutdown.is_set():
            try:
                # Get results with timeout
                try:
                    result = self._queue.get(timeout=0.1)
                    self._buffer.append(result)

                    with self._lock:
                        self._stats.results_processed += 1

                except queue.Empty:
                    pass

                # Check if we should flush
                should_flush = (
                    len(self._buffer) >= self._batch_size or
                    (self._buffer and self._time_since_flush() >= self._flush_interval)
                )

                if should_flush:
                    self._flush()

            except Exception as e:
                with self._lock:
                    self._stats.errors += 1

        # Final flush on shutdown
        self._drain_and_flush()

    def _flush(self) -> None:
        """Flush buffer to event store."""
        if not self._buffer:
            return

        try:
            self._write_fn(self._buffer)

            with self._lock:
                self._stats.batches_committed += 1

        except Exception:
            with self._lock:
                self._stats.errors += 1

        finally:
            self._buffer = []
            self._last_flush = datetime.now(timezone.utc)

    def _drain_and_flush(self) -> None:
        """Drain queue and flush all remaining."""
        while True:
            try:
                result = self._queue.get_nowait()
                self._buffer.append(result)

                with self._lock:
                    self._stats.results_processed += 1

            except queue.Empty:
                break

        self._flush()

    def _time_since_flush(self) -> float:
        """Seconds since last flush."""
        return (datetime.now(timezone.utc) - self._last_flush).total_seconds()

    def stats(self) -> AggregatorStats:
        """Get writer statistics."""
        with self._lock:
            return AggregatorStats(
                results_received=self._stats.results_received,
                results_processed=self._stats.results_processed,
                batches_committed=self._stats.batches_committed,
                errors=self._stats.errors
            )
