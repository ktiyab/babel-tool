"""
MetricsCollector — Observability for task orchestration

Collects and exposes metrics:
- Task latency histograms
- Queue depth gauges
- Worker utilization
- Throughput counters
- Error rates by task type

Design: Observable by default. Every task emits timing.
"""

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime, timezone

from .task import Task, TaskResult, TaskStatus, TaskType, Priority


@dataclass
class LatencyHistogram:
    """Simple histogram for latency tracking."""
    count: int = 0
    sum_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0

    # Buckets: <10ms, <50ms, <100ms, <500ms, <1s, <5s, >5s
    buckets: Dict[str, int] = field(default_factory=lambda: {
        "lt_10ms": 0,
        "lt_50ms": 0,
        "lt_100ms": 0,
        "lt_500ms": 0,
        "lt_1s": 0,
        "lt_5s": 0,
        "gt_5s": 0
    })

    def record(self, duration_ms: float) -> None:
        """Record a latency observation."""
        self.count += 1
        self.sum_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)

        # Update buckets
        if duration_ms < 10:
            self.buckets["lt_10ms"] += 1
        elif duration_ms < 50:
            self.buckets["lt_50ms"] += 1
        elif duration_ms < 100:
            self.buckets["lt_100ms"] += 1
        elif duration_ms < 500:
            self.buckets["lt_500ms"] += 1
        elif duration_ms < 1000:
            self.buckets["lt_1s"] += 1
        elif duration_ms < 5000:
            self.buckets["lt_5s"] += 1
        else:
            self.buckets["gt_5s"] += 1

    @property
    def avg_ms(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_ms / self.count

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else 0,
            "max_ms": round(self.max_ms, 2),
            "buckets": self.buckets.copy()
        }


@dataclass
class CounterMetric:
    """Simple counter metric."""
    value: int = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class GaugeMetric:
    """Simple gauge metric (current value)."""
    value: float = 0.0

    def set(self, value: float) -> None:
        self.value = value

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount

    def dec(self, amount: float = 1.0) -> None:
        self.value -= amount


class MetricsCollector:
    """
    Collects metrics for task orchestration observability.

    Thread-safe. All metrics operations are atomic.

    Metrics exposed:
    - tasks_submitted: Counter by type and priority
    - tasks_completed: Counter by type and status
    - task_latency: Histogram by type
    - queue_depth: Gauge by priority
    - active_workers: Gauge by pool type
    - errors: Counter by type and error kind
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Counters
        self._tasks_submitted: Dict[str, CounterMetric] = defaultdict(CounterMetric)
        self._tasks_completed: Dict[str, CounterMetric] = defaultdict(CounterMetric)
        self._errors: Dict[str, CounterMetric] = defaultdict(CounterMetric)

        # Histograms
        self._latency: Dict[str, LatencyHistogram] = defaultdict(LatencyHistogram)

        # Gauges
        self._queue_depth: Dict[str, GaugeMetric] = defaultdict(GaugeMetric)
        self._active_workers: Dict[str, GaugeMetric] = defaultdict(GaugeMetric)

        # Start time for uptime calculation
        self._start_time = datetime.now(timezone.utc)

    def record_task_submitted(self, task: Task) -> None:
        """Record a task submission."""
        with self._lock:
            key = f"{task.task_type.value}:{task.priority.name}"
            self._tasks_submitted[key].inc()
            self._tasks_submitted["total"].inc()

    def record_task_completed(self, result: TaskResult, task_type: TaskType) -> None:
        """Record a task completion."""
        with self._lock:
            status_key = f"{task_type.value}:{result.status.value}"
            self._tasks_completed[status_key].inc()
            self._tasks_completed[f"total:{result.status.value}"].inc()

            if result.duration_ms is not None:
                self._latency[task_type.value].record(result.duration_ms)
                self._latency["all"].record(result.duration_ms)

            if result.status == TaskStatus.FAILED:
                error_key = f"{task_type.value}:failed"
                self._errors[error_key].inc()
                self._errors["total:failed"].inc()

    def record_error(self, task_type: TaskType, error_kind: str) -> None:
        """Record an error."""
        with self._lock:
            key = f"{task_type.value}:{error_kind}"
            self._errors[key].inc()
            self._errors["total"].inc()

    def set_queue_depth(self, priority: Priority, depth: int) -> None:
        """Set queue depth gauge."""
        with self._lock:
            self._queue_depth[priority.name].set(depth)

    def set_queue_depths(self, depths: Dict[Priority, int]) -> None:
        """Set all queue depths at once."""
        with self._lock:
            for priority, depth in depths.items():
                self._queue_depth[priority.name].set(depth)

    def set_active_workers(self, pool_type: str, count: int) -> None:
        """Set active workers gauge."""
        with self._lock:
            self._active_workers[pool_type].set(count)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        with self._lock:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

            submitted_total = self._tasks_submitted.get("total", CounterMetric()).value
            completed_total = sum(
                c.value for k, c in self._tasks_completed.items()
                if k.startswith("total:")
            )
            failed_total = self._errors.get("total:failed", CounterMetric()).value

            return {
                "uptime_seconds": round(uptime, 2),
                "tasks": {
                    "submitted": submitted_total,
                    "completed": completed_total,
                    "failed": failed_total,
                    "success_rate": round(
                        (completed_total - failed_total) / max(completed_total, 1) * 100, 1
                    )
                },
                "latency": {
                    task_type: hist.to_dict()
                    for task_type, hist in self._latency.items()
                },
                "queues": {
                    priority: int(gauge.value)
                    for priority, gauge in self._queue_depth.items()
                },
                "workers": {
                    pool: int(gauge.value)
                    for pool, gauge in self._active_workers.items()
                }
            }

    def get_throughput(self, window_seconds: float = 60.0) -> Dict[str, float]:
        """
        Get throughput metrics (tasks per second).

        Note: This is a simple calculation, not a sliding window.
        """
        with self._lock:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            window = min(uptime, window_seconds)

            if window <= 0:
                return {"submitted_per_sec": 0, "completed_per_sec": 0}

            submitted = self._tasks_submitted.get("total", CounterMetric()).value
            completed = sum(
                c.value for k, c in self._tasks_completed.items()
                if k.startswith("total:completed")
            )

            return {
                "submitted_per_sec": round(submitted / window, 2),
                "completed_per_sec": round(completed / window, 2)
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._tasks_submitted.clear()
            self._tasks_completed.clear()
            self._errors.clear()
            self._latency.clear()
            self._queue_depth.clear()
            self._active_workers.clear()
            self._start_time = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Export all metrics as dictionary."""
        with self._lock:
            return {
                "submitted": {k: c.value for k, c in self._tasks_submitted.items()},
                "completed": {k: c.value for k, c in self._tasks_completed.items()},
                "errors": {k: c.value for k, c in self._errors.items()},
                "latency": {k: h.to_dict() for k, h in self._latency.items()},
                "queue_depth": {k: g.value for k, g in self._queue_depth.items()},
                "active_workers": {k: g.value for k, g in self._active_workers.items()},
                "start_time": self._start_time.isoformat()
            }
