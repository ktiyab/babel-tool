"""
ContextGatherer — Parallel context gathering using orchestrator.

Bridges the gather functions with the TaskOrchestrator for parallel execution.
All gather operations are I/O-bound (file reads, subprocess calls) and use
is_llm_call=False to bypass rate limiting.

Usage:
    from babel.gather import ContextGatherer, GatherPlan

    plan = GatherPlan(
        operation="Fix caching bug",
        intent="Understand cache implementation"
    ).add_file("src/cache.py").add_grep("CacheError")

    gatherer = ContextGatherer()
    results = gatherer.gather(plan)

    # Or gather from specific sources
    results = gatherer.gather_sources(plan.sources)
"""

from typing import List, Optional, Dict, Callable
from concurrent.futures import Future

from .plan import GatherPlan, GatherSource, SourceType
from .result import GatherResult
from .functions import gather_file, gather_grep, gather_bash, gather_glob, gather_symbol


# Function registry mapping source type to gather function
GATHER_FUNCTIONS: Dict[SourceType, Callable] = {
    SourceType.FILE: gather_file,
    SourceType.GREP: gather_grep,
    SourceType.BASH: gather_bash,
    SourceType.GLOB: gather_glob,
    SourceType.SYMBOL: gather_symbol,
}


class ContextGatherer:
    """
    Parallel context gathering using TaskOrchestrator.

    Submits gather operations as io_task to the orchestrator's IOPool,
    enabling true parallel execution of file reads, searches, and commands.

    Key design decisions:
    - is_llm_call=False for all tasks (no rate limiting)
    - Graceful fallback to sequential if orchestrator unavailable
    - Preserves source order in results
    """

    def __init__(self, orchestrator=None):
        """
        Initialize gatherer.

        Args:
            orchestrator: Optional TaskOrchestrator instance.
                         If None, will get global instance on first use.
        """
        self._orchestrator = orchestrator
        self._use_parallel = True

    @property
    def orchestrator(self):
        """Get orchestrator (lazy initialization)."""
        if self._orchestrator is None:
            try:
                from ..orchestrator import get_orchestrator
                self._orchestrator = get_orchestrator()
            except Exception:
                self._use_parallel = False
                self._orchestrator = None
        return self._orchestrator

    def gather(self, plan: GatherPlan) -> List[GatherResult]:
        """
        Gather all sources in a plan.

        Uses parallel execution if orchestrator is available and enabled.
        Falls back to sequential execution otherwise.

        Args:
            plan: The gather plan with sources

        Returns:
            List of GatherResults in same order as plan.sources
        """
        return self.gather_sources(plan.sources)

    def gather_sources(self, sources: List[GatherSource]) -> List[GatherResult]:
        """
        Gather from a list of sources.

        Args:
            sources: List of GatherSource specifications

        Returns:
            List of GatherResults in same order as sources
        """
        if not sources:
            return []

        # Try parallel execution
        if self._use_parallel and self.orchestrator:
            try:
                return self._gather_parallel(sources)
            except Exception:
                # Fall back to sequential on any error
                pass

        # Sequential fallback
        return self._gather_sequential(sources)

    def _gather_parallel(self, sources: List[GatherSource]) -> List[GatherResult]:
        """
        Gather sources in parallel using orchestrator.

        Submits all sources as io_task to IOPool.
        Collects results maintaining original order.
        """
        from ..orchestrator import io_task, Priority

        orch = self.orchestrator
        if not orch or not orch.enabled:
            return self._gather_sequential(sources)

        # Submit all gather tasks
        futures: List[tuple] = []  # (index, source, future)

        for i, source in enumerate(sources):
            fn = GATHER_FUNCTIONS.get(source.source_type)
            if fn is None:
                # Unknown source type - create error result
                futures.append((i, source, None))
                continue

            # Create task with appropriate args
            args = self._get_gather_args(source)

            task = io_task(
                fn=fn,
                args=args,
                is_llm_call=False,  # Critical: no rate limiting for I/O
                priority=self._map_priority(source.priority),
                name=f"gather_{source.source_type.value}_{i}",
                timeout=30.0,
            )

            future = orch.submit(task)
            futures.append((i, source, future))

        # Collect results in order
        results: List[Optional[GatherResult]] = [None] * len(sources)

        for i, source, future in futures:
            if future is None:
                # Unknown source type
                results[i] = GatherResult.error_result(
                    source_type=source.source_type.value,
                    source_ref=source.reference,
                    error=f"Unknown source type: {source.source_type}",
                )
            else:
                try:
                    task_result = future.result(timeout=35.0)
                    if task_result.success:
                        results[i] = task_result.result
                    else:
                        results[i] = GatherResult.error_result(
                            source_type=source.source_type.value,
                            source_ref=source.reference,
                            error=task_result.error or "Task failed",
                        )
                except Exception as e:
                    results[i] = GatherResult.error_result(
                        source_type=source.source_type.value,
                        source_ref=source.reference,
                        error=str(e),
                    )

        return results

    def _gather_sequential(self, sources: List[GatherSource]) -> List[GatherResult]:
        """
        Gather sources sequentially (fallback mode).

        Used when orchestrator is unavailable or disabled.
        """
        results = []

        for source in sources:
            fn = GATHER_FUNCTIONS.get(source.source_type)
            if fn is None:
                results.append(GatherResult.error_result(
                    source_type=source.source_type.value,
                    source_ref=source.reference,
                    error=f"Unknown source type: {source.source_type}",
                ))
                continue

            args = self._get_gather_args(source)

            try:
                result = fn(*args)
                results.append(result)
            except Exception as e:
                results.append(GatherResult.error_result(
                    source_type=source.source_type.value,
                    source_ref=source.reference,
                    error=str(e),
                ))

        return results

    def _get_gather_args(self, source: GatherSource) -> tuple:
        """Get arguments tuple for gather function call."""
        if source.source_type == SourceType.FILE:
            return (source.reference,)

        elif source.source_type == SourceType.GREP:
            path = source.params.get("path", ".")
            max_matches = source.params.get("max_matches", 100)
            return (source.reference, path, max_matches)

        elif source.source_type == SourceType.BASH:
            timeout = source.params.get("timeout", 30.0)
            cwd = source.params.get("cwd")
            return (source.reference, timeout, cwd)

        elif source.source_type == SourceType.GLOB:
            base_path = source.params.get("base_path", ".")
            return (source.reference, base_path)

        elif source.source_type == SourceType.SYMBOL:
            project_dir = source.params.get("project_dir")
            context_lines = source.params.get("context_lines", 5)
            return (source.reference, project_dir, context_lines)

        return (source.reference,)

    def _map_priority(self, source_priority) -> "Priority":
        """Map GatherSource priority to orchestrator Priority."""
        from ..orchestrator import Priority

        # Import SourcePriority enum values
        from .plan import SourcePriority

        mapping = {
            SourcePriority.CRITICAL: Priority.CRITICAL,
            SourcePriority.HIGH: Priority.HIGH,
            SourcePriority.NORMAL: Priority.NORMAL,
            SourcePriority.LOW: Priority.BACKGROUND,
        }
        return mapping.get(source_priority, Priority.NORMAL)


def gather_context(plan: GatherPlan) -> List[GatherResult]:
    """
    Convenience function to gather context from a plan.

    Args:
        plan: The gather plan

    Returns:
        List of GatherResults
    """
    gatherer = ContextGatherer()
    return gatherer.gather(plan)


def gather_files(paths: List[str]) -> List[GatherResult]:
    """
    Convenience function to gather multiple files.

    Args:
        paths: List of file paths

    Returns:
        List of GatherResults
    """
    plan = GatherPlan(operation="gather_files", intent="Gather multiple files")
    for path in paths:
        plan.add_file(path)
    return gather_context(plan)
