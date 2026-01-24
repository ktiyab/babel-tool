"""
Parallel Context Gather System

A system for gathering context from multiple sources in parallel,
aggregating results into structured documents for LLM consumption.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │  LLM Planning Phase (Sequential)                        │
    │  - Produces GatherPlan with sources to gather           │
    └─────────────────────────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────────────┐
    │  ChunkBroker                                            │
    │  - Estimates sizes                                      │
    │  - Groups related sources (coherence)                   │
    │  - Creates chunks that fit context limits               │
    └─────────────────────────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────────────┐
    │  ContextGatherer (per chunk)                            │
    │  - Submits io_tasks to TaskOrchestrator                 │
    │  - Sources execute in PARALLEL (IOPool)                 │
    │  - Returns GatherResults                                │
    └─────────────────────────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────────────┐
    │  ContextTemplate                                        │
    │  - Renders results to structured markdown               │
    │  - Header + Manifest + Corpus format                    │
    │  - Chunk-aware (shows N of M)                           │
    └─────────────────────────────────────────────────────────┘

Usage:
    from babel.gather import (
        GatherPlan, GatherSource, SourceType, SourcePriority,
        ContextGatherer, ChunkBroker, render_context
    )

    # 1. Create plan (LLM planning phase)
    plan = GatherPlan(
        operation="Fix caching bug",
        intent="Understand cache implementation"
    )
    plan.add_file("src/cache.py", priority=SourcePriority.CRITICAL)
    plan.add_file("src/api.py")
    plan.add_grep("CacheError", "src/")
    plan.add_bash("git log -5 src/cache.py")

    # 2. Check if chunking needed
    broker = ChunkBroker(context_limit_kb=100)
    chunks = broker.plan_chunks(plan)

    # 3. Gather and render each chunk
    gatherer = ContextGatherer()
    for i, chunk in enumerate(chunks):
        results = gatherer.gather_sources(chunk.sources)
        content = render_context(
            plan, results,
            chunk_number=i+1,
            total_chunks=len(chunks)
        )
        # content is structured markdown ready for LLM
"""

# Result type
from .result import GatherResult

# Plan types
from .plan import (
    GatherPlan,
    GatherSource,
    SourceType,
    SourcePriority,
)

# Gather functions (LLM-agnostic primitives)
from .functions import (
    gather_file,
    gather_grep,
    gather_bash,
    gather_glob,
    gather_symbol,
    estimate_file_size,
    estimate_grep_size,
)

# Template rendering
from .template import (
    ContextTemplate,
    render_context,
    render_to_file,
)

# Chunking broker
from .broker import (
    ChunkBroker,
    ChunkStrategy,
    Chunk,
    plan_chunks,
)

# Orchestrator integration
from .gatherer import (
    ContextGatherer,
    gather_context,
    gather_files,
)

# Safety checks for babel command parallelization
from .safety import (
    SafetyViolation,
    SafetyCategory,
    BabelCommandSafety,
    BABEL_COMMAND_SAFETY,
    check_bash_commands_safety,
    check_bash_command_safety,
    extract_babel_command,
    get_safe_commands,
    get_unsafe_commands,
)


__all__ = [
    # Result
    "GatherResult",

    # Plan
    "GatherPlan",
    "GatherSource",
    "SourceType",
    "SourcePriority",

    # Functions
    "gather_file",
    "gather_grep",
    "gather_bash",
    "gather_glob",
    "gather_symbol",
    "estimate_file_size",
    "estimate_grep_size",

    # Template
    "ContextTemplate",
    "render_context",
    "render_to_file",

    # Broker
    "ChunkBroker",
    "ChunkStrategy",
    "Chunk",
    "plan_chunks",

    # Gatherer
    "ContextGatherer",
    "gather_context",
    "gather_files",

    # Safety
    "SafetyViolation",
    "SafetyCategory",
    "BabelCommandSafety",
    "BABEL_COMMAND_SAFETY",
    "check_bash_commands_safety",
    "check_bash_command_safety",
    "extract_babel_command",
    "get_safe_commands",
    "get_unsafe_commands",
]
