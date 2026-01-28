"""
ChunkBroker — Intelligent chunking for context limits.

The broker decides HOW to chunk sources while maintaining coherence.
It groups related sources together and respects context size limits.

Chunking strategies:
1. SIZE-BASED: Fill chunks until size limit (simple)
2. COHERENCE-BASED: Group related sources (smart)
3. PRIORITY-BASED: Important sources first (adaptive)

Coherence rules:
- Same directory files stay together
- Test + implementation paired
- Search results go last (reference earlier content)
- Metadata/config goes first (provides context)
"""

from typing import List, Dict
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from .plan import GatherPlan, GatherSource, SourceType
from .functions import estimate_file_size, estimate_grep_size


# Default context limit (100KB is a safe default for most LLMs)
DEFAULT_CONTEXT_LIMIT_KB = 100
# Template overhead (header, manifest, formatting)
TEMPLATE_OVERHEAD_BYTES = 2048


class ChunkStrategy(Enum):
    """Chunking strategy selection."""
    SIZE_BASED = "size"          # Simple fill-until-full
    COHERENCE_BASED = "coherence"  # Group related sources
    PRIORITY_BASED = "priority"    # Important sources first


@dataclass
class Chunk:
    """A group of sources that fit within context limits."""
    sources: List[GatherSource] = field(default_factory=list)
    estimated_size: int = 0

    def add(self, source: GatherSource) -> None:
        """Add a source to this chunk."""
        self.sources.append(source)
        self.estimated_size += source.estimated_size_bytes

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def estimated_size_kb(self) -> float:
        return self.estimated_size / 1024


class ChunkBroker:
    """
    Intelligently chunks sources for context limits.

    Usage:
        broker = ChunkBroker(context_limit_kb=100)
        chunks = broker.plan_chunks(plan)

        for i, chunk in enumerate(chunks):
            # Gather sources in this chunk
            results = gatherer.gather(chunk.sources)
            # Render with chunk info
            content = template.render(results, chunk_number=i+1, total_chunks=len(chunks))
    """

    def __init__(
        self,
        context_limit_kb: int = DEFAULT_CONTEXT_LIMIT_KB,
        strategy: ChunkStrategy = ChunkStrategy.COHERENCE_BASED
    ):
        """
        Initialize broker.

        Args:
            context_limit_kb: Maximum context size in KB
            strategy: Chunking strategy to use
        """
        self.context_limit = context_limit_kb * 1024 - TEMPLATE_OVERHEAD_BYTES
        self.strategy = strategy

    def plan_chunks(self, plan: GatherPlan) -> List[Chunk]:
        """
        Plan how to chunk sources.

        First estimates sizes, then groups according to strategy.

        Args:
            plan: The gather plan with sources

        Returns:
            List of Chunks, each fitting within context limit
        """
        if not plan.sources:
            return []

        # Step 1: Estimate sizes for all sources
        self._estimate_sizes(plan.sources)

        # Step 2: Apply chunking strategy
        if self.strategy == ChunkStrategy.SIZE_BASED:
            return self._chunk_by_size(plan.sources)
        elif self.strategy == ChunkStrategy.COHERENCE_BASED:
            return self._chunk_by_coherence(plan.sources)
        elif self.strategy == ChunkStrategy.PRIORITY_BASED:
            return self._chunk_by_priority(plan.sources)
        else:
            return self._chunk_by_size(plan.sources)

    def _estimate_sizes(self, sources: List[GatherSource]) -> None:
        """Estimate sizes for all sources (mutates sources)."""
        for source in sources:
            if source.estimated_size_bytes > 0:
                continue  # Already estimated

            if source.source_type == SourceType.FILE:
                source.estimated_size_bytes = estimate_file_size(source.reference)
            elif source.source_type == SourceType.GREP:
                path = source.params.get("path", ".")
                source.estimated_size_bytes = estimate_grep_size(source.reference, path)
            elif source.source_type == SourceType.BASH:
                # Assume small output for commands
                source.estimated_size_bytes = 5 * 1024  # 5KB default
            elif source.source_type == SourceType.GLOB:
                # Glob results are typically small (just paths)
                source.estimated_size_bytes = 2 * 1024  # 2KB default

            # Minimum size estimate
            if source.estimated_size_bytes == 0:
                source.estimated_size_bytes = 1024  # 1KB minimum

    def _chunk_by_size(self, sources: List[GatherSource]) -> List[Chunk]:
        """
        Simple size-based chunking.

        Fill chunks until size limit, then start new chunk.
        """
        chunks = []
        current = Chunk()

        for source in sources:
            # Check if adding this source would exceed limit
            if current.estimated_size + source.estimated_size_bytes > self.context_limit:
                # Start new chunk if current has content
                if current.sources:
                    chunks.append(current)
                    current = Chunk()

            current.add(source)

        # Add final chunk
        if current.sources:
            chunks.append(current)

        return chunks

    def _chunk_by_coherence(self, sources: List[GatherSource]) -> List[Chunk]:
        """
        Coherence-based chunking.

        Groups related sources together:
        - Same directory files
        - Test + implementation pairs
        - Priority ordering within groups
        """
        # Step 1: Group sources by affinity
        groups = self._group_by_affinity(sources)

        # Step 2: Sort groups by priority (highest first)
        sorted_groups = sorted(
            groups.items(),
            key=lambda g: min(s.priority.value for s in g[1]) if g[1] else 999
        )

        # Step 3: Fit groups into chunks
        chunks = []
        current = Chunk()

        for group_name, group_sources in sorted_groups:
            # Sort sources within group by priority
            group_sources.sort(key=lambda s: s.priority.value)

            for source in group_sources:
                # Check if adding would exceed limit
                if current.estimated_size + source.estimated_size_bytes > self.context_limit:
                    if current.sources:
                        chunks.append(current)
                        current = Chunk()

                current.add(source)

        if current.sources:
            chunks.append(current)

        return chunks

    def _chunk_by_priority(self, sources: List[GatherSource]) -> List[Chunk]:
        """
        Priority-based chunking.

        Most important sources in first chunk(s).
        Lower priority sources may be dropped if needed.
        """
        # Sort by priority (CRITICAL=0 first)
        sorted_sources = sorted(sources, key=lambda s: s.priority.value)

        return self._chunk_by_size(sorted_sources)

    def _group_by_affinity(self, sources: List[GatherSource]) -> Dict[str, List[GatherSource]]:
        """
        Group sources by affinity.

        Affinity rules:
        1. Explicit group tag
        2. Same directory
        3. Test + implementation pairing
        4. Source type grouping
        """
        groups: Dict[str, List[GatherSource]] = {}

        for source in sources:
            group_key = self._determine_group(source)

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(source)

        return groups

    def _determine_group(self, source: GatherSource) -> str:
        """Determine group key for a source."""
        # Explicit group takes precedence
        if source.group:
            return f"explicit:{source.group}"

        # File-based grouping
        if source.source_type == SourceType.FILE:
            path = Path(source.reference)

            # Check if it's a test file
            if "test" in path.name.lower() or "spec" in path.name.lower():
                # Try to find matching implementation
                impl_name = path.name.replace("test_", "").replace("_test", "")
                impl_name = impl_name.replace("spec_", "").replace("_spec", "")
                return f"test:{impl_name}"

            # Group by directory
            return f"dir:{path.parent}"

        # Grep/search results go in their own group (processed last)
        if source.source_type == SourceType.GREP:
            return "search:grep"

        # Bash commands
        if source.source_type == SourceType.BASH:
            return "meta:commands"

        # Glob results
        if source.source_type == SourceType.GLOB:
            return "meta:glob"

        return "other"

    def estimate_chunk_count(self, plan: GatherPlan) -> int:
        """
        Estimate how many chunks will be needed.

        Useful for planning before actual chunking.
        """
        self._estimate_sizes(plan.sources)
        total_size = sum(s.estimated_size_bytes for s in plan.sources)
        return max(1, (total_size + self.context_limit - 1) // self.context_limit)

    def fits_in_single_chunk(self, plan: GatherPlan) -> bool:
        """Check if plan fits in a single chunk."""
        self._estimate_sizes(plan.sources)
        total_size = sum(s.estimated_size_bytes for s in plan.sources)
        return total_size <= self.context_limit


def plan_chunks(
    plan: GatherPlan,
    context_limit_kb: int = DEFAULT_CONTEXT_LIMIT_KB,
    strategy: ChunkStrategy = ChunkStrategy.COHERENCE_BASED
) -> List[Chunk]:
    """
    Convenience function to plan chunks.

    Args:
        plan: The gather plan
        context_limit_kb: Context size limit in KB
        strategy: Chunking strategy

    Returns:
        List of Chunks
    """
    broker = ChunkBroker(context_limit_kb, strategy)
    return broker.plan_chunks(plan)
