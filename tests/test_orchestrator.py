"""
Tests for Task Orchestrator — Parallel Execution Framework

Tests verify:
- Typed worker pools (I/O vs CPU)
- Priority scheduling
- Rate limiting only applies to LLM calls (is_llm_call=True)
- Parallel execution actually runs in parallel
- HC1 compliance (single writer pattern)
"""

import pytest
import time
import threading

from babel.orchestrator import (
    TaskOrchestrator, TaskType, Priority, TaskStatus, TaskResult,
    io_task, cpu_task, reset_orchestrator,
)
from babel.orchestrator.config import OrchestratorConfig
from babel.orchestrator.pools import IOPool, CPUPool
from babel.orchestrator.scheduler import PriorityScheduler
from babel.orchestrator.aggregator import ResultAggregator


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def config():
    """Create test configuration with parallelization enabled."""
    return OrchestratorConfig(
        enabled=True,
        io_workers=4,
        cpu_workers=2,
        llm_concurrent=3,
        llm_rate_limit=10.0,
        task_timeout=10.0
    )


@pytest.fixture
def orchestrator(config):
    """Create orchestrator with test config."""
    orch = TaskOrchestrator(config)
    yield orch
    orch.shutdown(wait=True)


@pytest.fixture(autouse=True)
def reset_global_orchestrator():
    """Reset global orchestrator before each test."""
    reset_orchestrator()
    yield
    reset_orchestrator()


# =============================================================================
# Task Creation Tests
# =============================================================================

class TestTaskCreation:
    """Test task factory functions."""

    def test_io_task_default_not_llm(self):
        """io_task defaults is_llm_call to False."""
        task = io_task(fn=lambda: None)
        assert task.is_llm_call is False
        assert task.task_type == TaskType.IO_BOUND

    def test_io_task_with_llm_flag(self):
        """io_task can be marked as LLM call."""
        task = io_task(fn=lambda: None, is_llm_call=True)
        assert task.is_llm_call is True

    def test_cpu_task_creation(self):
        """cpu_task creates CPU-bound task."""
        task = cpu_task(fn=lambda x: x * 2, args=(5,))
        assert task.task_type == TaskType.CPU_BOUND

    def test_task_priority(self):
        """Tasks respect priority setting."""
        task = io_task(fn=lambda: None, priority=Priority.CRITICAL)
        assert task.priority == Priority.CRITICAL


# =============================================================================
# Rate Limiter Tests (Critical Bug Fix Verification)
# =============================================================================

class TestRateLimiterScope:
    """Test that rate limiter only applies to LLM calls."""

    def test_non_llm_tasks_run_parallel(self, orchestrator):
        """Non-LLM I/O tasks should run in parallel without rate limiting."""
        results = []

        def slow_task(x):
            time.sleep(0.1)
            return x * 2

        # Submit 4 tasks that each take 0.1s
        start = time.time()
        futures = []
        for i in range(4):
            task = io_task(fn=slow_task, args=(i,), is_llm_call=False)
            futures.append(orchestrator.submit(task))

        # Collect results
        for f in futures:
            result = f.result(timeout=5.0)
            results.append(result.result)

        elapsed = time.time() - start

        # With 4 workers and 4 tasks, should complete in ~0.1-0.2s (parallel)
        # If serialized by rate limiter, would take ~0.4s+
        assert elapsed < 0.3, f"Tasks serialized! Took {elapsed:.2f}s, expected <0.3s"
        assert results == [0, 2, 4, 6]

    def test_llm_tasks_are_rate_limited(self, orchestrator):
        """LLM tasks (is_llm_call=True) should be rate limited."""
        def quick_task(x):
            return x

        # Submit 3 tasks marked as LLM calls
        # With rate_limit=10/sec, min interval = 0.1s
        start = time.time()
        futures = []
        for i in range(3):
            task = io_task(fn=quick_task, args=(i,), is_llm_call=True)
            futures.append(orchestrator.submit(task))

        for f in futures:
            f.result(timeout=5.0)

        elapsed = time.time() - start

        # 3 LLM tasks with 0.1s interval = at least 0.2s
        assert elapsed >= 0.15, f"LLM tasks not rate limited! Took {elapsed:.2f}s"


# =============================================================================
# Pool Tests
# =============================================================================

class TestIOPool:
    """Test I/O pool functionality."""

    def test_submit_and_execute(self, config):
        """IOPool executes tasks and returns results."""
        pool = IOPool(config)

        task = io_task(fn=lambda: "hello")
        future = pool.submit(task)
        result = future.result(timeout=5.0)

        assert result.success
        assert result.result == "hello"
        pool.shutdown()

    def test_stats_tracking(self, config):
        """IOPool tracks execution statistics."""
        pool = IOPool(config)

        task = io_task(fn=lambda: 42)
        future = pool.submit(task)
        future.result(timeout=5.0)

        stats = pool.stats()
        assert stats.completed_tasks == 1
        pool.shutdown()


class TestCPUPool:
    """Test CPU pool functionality."""

    def test_cpu_task_execution(self, config):
        """CPUPool executes CPU-bound tasks."""
        pool = CPUPool(config)

        # Must use top-level function for pickling
        task = cpu_task(fn=_cpu_work, args=(5,))
        future = pool.submit(task)
        result = future.result(timeout=10.0)

        assert result.success
        assert result.result == 10  # 5 * 2
        pool.shutdown()

    def test_parallel_map(self, config):
        """CPUPool.map executes items in parallel."""
        pool = CPUPool(config)

        results = pool.map(_cpu_work, [1, 2, 3, 4], timeout=10.0)

        assert results == [2, 4, 6, 8]
        pool.shutdown()


# Top-level function for CPUPool pickling
def _cpu_work(x):
    return x * 2


# =============================================================================
# Scheduler Tests
# =============================================================================

class TestPriorityScheduler:
    """Test priority scheduling."""

    def test_priority_ordering(self):
        """Higher priority tasks are processed first."""
        scheduler = PriorityScheduler()

        # Submit in reverse priority order
        low = io_task(fn=lambda: "low", priority=Priority.BACKGROUND)
        normal = io_task(fn=lambda: "normal", priority=Priority.NORMAL)
        high = io_task(fn=lambda: "high", priority=Priority.HIGH)
        critical = io_task(fn=lambda: "critical", priority=Priority.CRITICAL)

        scheduler.submit(low)
        scheduler.submit(normal)
        scheduler.submit(high)
        scheduler.submit(critical)

        # Should get in priority order
        assert scheduler.get_nowait().priority == Priority.CRITICAL
        assert scheduler.get_nowait().priority == Priority.HIGH
        assert scheduler.get_nowait().priority == Priority.NORMAL
        assert scheduler.get_nowait().priority == Priority.BACKGROUND

    def test_fifo_within_priority(self):
        """Tasks with same priority maintain FIFO order."""
        scheduler = PriorityScheduler()

        first = io_task(fn=lambda: 1, priority=Priority.NORMAL, name="first")
        second = io_task(fn=lambda: 2, priority=Priority.NORMAL, name="second")

        scheduler.submit(first)
        scheduler.submit(second)

        assert scheduler.get_nowait().name == "first"
        assert scheduler.get_nowait().name == "second"


# =============================================================================
# Aggregator Tests (HC1 Compliance)
# =============================================================================

class TestResultAggregator:
    """Test result aggregation for HC1 compliance."""

    def test_thread_safe_submit(self):
        """Multiple threads can submit results safely."""
        aggregator = ResultAggregator()

        def submit_result(i):
            result = TaskResult(
                task_id=f"task_{i}",
                status=TaskStatus.COMPLETED,
                result=i
            )
            aggregator.submit(result)

        threads = [threading.Thread(target=submit_result, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        results = aggregator.drain(timeout=1.0)
        assert len(results) == 10

    def test_drain_collects_all(self):
        """drain() collects all submitted results."""
        aggregator = ResultAggregator()

        for i in range(5):
            result = TaskResult(task_id=f"t{i}", status=TaskStatus.COMPLETED, result=i)
            aggregator.submit(result)

        results = aggregator.drain(timeout=1.0)
        assert len(results) == 5

        # Second drain should return empty
        results = aggregator.drain(timeout=0.1)
        assert len(results) == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestOrchestratorIntegration:
    """Test full orchestrator integration."""

    def test_map_parallel_io(self, orchestrator):
        """map_parallel executes I/O tasks in parallel."""
        def work(x):
            time.sleep(0.05)
            return x * 2

        start = time.time()
        results = orchestrator.map_parallel(work, [1, 2, 3, 4], task_type=TaskType.IO_BOUND)
        elapsed = time.time() - start

        assert results == [2, 4, 6, 8]
        # 4 tasks × 0.05s = 0.2s sequential, should be ~0.05-0.1s parallel
        assert elapsed < 0.2, f"Not parallel! Took {elapsed:.2f}s"

    def test_sequential_fallback_when_disabled(self):
        """Orchestrator falls back to sequential when disabled."""
        config = OrchestratorConfig(enabled=False)
        orch = TaskOrchestrator(config)

        def work(x):
            return x + 1

        results = orch.map_parallel(work, [1, 2, 3])
        assert results == [2, 3, 4]

    def test_metrics_collection(self, orchestrator):
        """Orchestrator collects execution metrics."""
        task = io_task(fn=lambda: 42)
        future = orchestrator.submit(task)
        future.result(timeout=5.0)

        metrics = orchestrator.get_metrics()
        assert metrics["enabled"] is True
        assert metrics["tasks"]["submitted"] >= 1
        assert metrics["tasks"]["completed"] >= 1

    def test_graceful_shutdown(self, config):
        """Orchestrator shuts down gracefully."""
        orch = TaskOrchestrator(config)

        # Submit a task
        task = io_task(fn=lambda: "done")
        future = orch.submit(task)
        future.result(timeout=5.0)

        # Shutdown should complete without error
        orch.shutdown(wait=True)

        # Further submissions should fail
        with pytest.raises(RuntimeError):
            orch.submit(io_task(fn=lambda: None))
