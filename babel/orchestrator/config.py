"""
OrchestratorConfig — Configuration for parallel execution

Loads parallelization settings from environment variables.
Provides sensible defaults that work on any machine.

Environment variables:
- BABEL_PARALLEL_ENABLED: Enable/disable parallelization (default: true)
- BABEL_IO_WORKERS: Thread pool size for I/O-bound work (default: 4)
- BABEL_CPU_WORKERS: Process pool size for CPU-bound work (default: CPU_COUNT // 2)
- BABEL_LLM_CONCURRENT: Max concurrent LLM API calls (default: 3)
- BABEL_TASK_TIMEOUT: Default task timeout in seconds (default: 60)
"""

import os
import multiprocessing
from dataclasses import dataclass


@dataclass
class OrchestratorConfig:
    """
    Configuration for the task orchestrator.

    Loaded from environment variables with sensible defaults.
    """

    # Feature toggle
    enabled: bool = True

    # Worker pool sizes
    io_workers: int = 4                    # ThreadPool for I/O-bound
    cpu_workers: int = 2                   # ProcessPool for CPU-bound

    # Rate limiting
    llm_concurrent: int = 3                # Max concurrent LLM calls
    llm_rate_limit: float = 10.0           # Max requests per second

    # Timeouts
    task_timeout: float = 60.0             # Default task timeout (seconds)
    shutdown_timeout: float = 10.0         # Pool shutdown timeout (seconds)

    # Behavior
    fallback_sequential: bool = True       # Fall back on pool failure

    @classmethod
    def from_env(cls) -> 'OrchestratorConfig':
        """
        Load configuration from environment variables.

        Uses sensible defaults that work on any machine:
        - CPU workers: half of available cores (respects user's machine)
        - I/O workers: 4 (sufficient for most LLM/network workloads)
        - LLM concurrent: 3 (avoids API rate limits)
        """
        cpu_count = multiprocessing.cpu_count()

        return cls(
            enabled=_get_bool_env("BABEL_PARALLEL_ENABLED", True),
            io_workers=_get_int_env("BABEL_IO_WORKERS", 4),
            cpu_workers=_get_int_env("BABEL_CPU_WORKERS", max(1, cpu_count // 2)),
            llm_concurrent=_get_int_env("BABEL_LLM_CONCURRENT", 3),
            llm_rate_limit=_get_float_env("BABEL_LLM_RATE_LIMIT", 10.0),
            task_timeout=_get_float_env("BABEL_TASK_TIMEOUT", 60.0),
            shutdown_timeout=_get_float_env("BABEL_SHUTDOWN_TIMEOUT", 10.0),
            fallback_sequential=_get_bool_env("BABEL_FALLBACK_SEQUENTIAL", True),
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if self.io_workers < 1:
            raise ValueError("BABEL_IO_WORKERS must be >= 1")
        if self.cpu_workers < 1:
            raise ValueError("BABEL_CPU_WORKERS must be >= 1")
        if self.llm_concurrent < 1:
            raise ValueError("BABEL_LLM_CONCURRENT must be >= 1")
        if self.task_timeout <= 0:
            raise ValueError("BABEL_TASK_TIMEOUT must be > 0")

    def to_dict(self) -> dict:
        """Serialize for display/logging."""
        return {
            "enabled": self.enabled,
            "io_workers": self.io_workers,
            "cpu_workers": self.cpu_workers,
            "llm_concurrent": self.llm_concurrent,
            "llm_rate_limit": self.llm_rate_limit,
            "task_timeout": self.task_timeout,
            "shutdown_timeout": self.shutdown_timeout,
            "fallback_sequential": self.fallback_sequential,
        }


def _get_bool_env(key: str, default: bool) -> bool:
    """Get boolean from environment variable."""
    value = os.environ.get(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def _get_int_env(key: str, default: int) -> int:
    """Get integer from environment variable."""
    value = os.environ.get(key, "")
    if value:
        try:
            return int(value)
        except ValueError:
            pass
    return default


def _get_float_env(key: str, default: float) -> float:
    """Get float from environment variable."""
    value = os.environ.get(key, "")
    if value:
        try:
            return float(value)
        except ValueError:
            pass
    return default
