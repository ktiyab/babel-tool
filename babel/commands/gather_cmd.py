"""
GatherCommand — Parallel context gathering for LLM operators

Exposes the gather module via CLI, enabling LLMs to batch multiple
source requests (files, greps, bash commands, globs) into a single
command that executes in parallel and returns aggregated structured context.

Aligns with:
- P6: Token efficiency (one round-trip instead of many sequential calls)
- Existing orchestrator parallelization (is_llm_call=False for I/O)

Usage:
    # Gather multiple files and searches in parallel
    babel gather --file src/cache.py --file src/api.py --grep "CacheError:src/"

    # With custom context limit and strategy
    babel gather --file main.py --limit 50 --strategy priority

    # Output to file instead of stdout
    babel gather --file src/*.py --output /tmp/context.md
"""

from typing import List, Optional
from pathlib import Path

from ..commands.base import BaseCommand
from ..gather import (
    GatherPlan,
    GatherSource,
    SourceType,
    SourcePriority,
    ContextGatherer,
    ChunkBroker,
    ChunkStrategy,
    render_context,
    render_to_file,
)
from ..gather.safety import check_bash_commands_safety, SafetyViolation
from ..presentation.symbols import safe_print


class GatherCommand(BaseCommand):
    """
    Command for parallel context gathering.

    Enables LLM operators to batch multiple source requests into a single
    command, leveraging the orchestrator for parallel I/O execution.
    """

    def gather(
        self,
        files: List[str] = None,
        greps: List[str] = None,
        bashes: List[str] = None,
        globs: List[str] = None,
        symbols_list: List[str] = None,
        operation: str = "Context Gather",
        intent: str = "Gather context for analysis",
        output_format: str = "markdown",
        output_file: Optional[str] = None,
        context_limit_kb: int = 100,
        strategy: str = "coherence",
    ):
        """
        Gather context from multiple sources in parallel.

        Args:
            files: List of file paths to read
            greps: List of grep patterns (format: "pattern" or "pattern:path")
            bashes: List of bash commands to execute
            globs: List of glob patterns to find files
            symbols_list: List of symbol names to load (class, function, method)
            operation: Operation name for template header
            intent: Intent description for template header
            output_format: Output format (markdown or json)
            output_file: Optional file path to write output
            context_limit_kb: Context size limit in KB (for chunking)
            strategy: Chunking strategy (size, coherence, priority)
        """
        symbols = self.symbols
        files = files or []
        greps = greps or []
        bashes = bashes or []
        globs = globs or []
        symbols_list = symbols_list or []

        # Validate we have at least one source
        total_sources = len(files) + len(greps) + len(bashes) + len(globs) + len(symbols_list)
        if total_sources == 0:
            print(f"{symbols.warning} No sources specified.")
            print("\nUsage:")
            print("  babel gather --file src/cache.py --file src/api.py")
            print("  babel gather --grep 'CacheError:src/' --bash 'git log -5'")
            print("\nRun: babel gather --help")
            return

        # Safety check: Reject unsafe babel commands in --bash
        # Prevents parallel execution of mutation/LLM-heavy commands
        if bashes:
            try:
                check_bash_commands_safety(bashes)
            except SafetyViolation as e:
                # Print the detailed violation message
                print(e.message)
                return

        # Build the gather plan
        plan = GatherPlan(operation=operation, intent=intent)

        # Add file sources
        for path in files:
            plan.add_file(path)

        # Add grep sources (format: "pattern" or "pattern:path")
        for grep_spec in greps:
            if ':' in grep_spec:
                pattern, path = grep_spec.rsplit(':', 1)
            else:
                pattern, path = grep_spec, "."
            plan.add_grep(pattern, path)

        # Add bash sources
        for command in bashes:
            plan.add_bash(command)

        # Add glob sources
        for pattern in globs:
            plan.add_glob(pattern)

        # Add symbol sources (uses project_dir from CLI context)
        for symbol_name in symbols_list:
            plan.add_symbol(symbol_name, project_dir=str(self.project_dir))

        # Map strategy string to enum
        strategy_map = {
            "size": ChunkStrategy.SIZE_BASED,
            "coherence": ChunkStrategy.COHERENCE_BASED,
            "priority": ChunkStrategy.PRIORITY_BASED,
        }
        chunk_strategy = strategy_map.get(strategy, ChunkStrategy.COHERENCE_BASED)

        # Plan chunks if needed
        broker = ChunkBroker(
            context_limit_kb=context_limit_kb,
            strategy=chunk_strategy
        )
        chunks = broker.plan_chunks(plan)

        if not chunks:
            print(f"{symbols.warning} No sources to gather after planning.")
            return

        # Show progress for multiple chunks
        total_chunks = len(chunks)
        if total_chunks > 1:
            print(f"{symbols.info} Gathering in {total_chunks} chunk(s)...")

        # Gather context using orchestrator (parallel execution)
        gatherer = ContextGatherer(orchestrator=self.orchestrator)

        all_output = []

        for i, chunk in enumerate(chunks, 1):
            # Gather this chunk's sources in parallel
            results = gatherer.gather_sources(chunk.sources)

            # Render to template
            if output_format == "json":
                import json
                chunk_output = json.dumps([r.to_dict() for r in results], indent=2)
            else:
                chunk_output = render_context(
                    plan, results,
                    chunk_number=i,
                    total_chunks=total_chunks
                )

            all_output.append(chunk_output)

        # Combine all chunks
        full_output = "\n\n".join(all_output)

        # Output result
        if output_file:
            Path(output_file).write_text(full_output, encoding="utf-8")
            print(f"{symbols.check_pass} Context written to: {output_file}")
            print(f"  Sources: {total_sources}")
            print(f"  Chunks: {total_chunks}")
        else:
            # Print to stdout for LLM consumption
            print(full_output)

        # Succession hint
        from ..output import end_command
        end_command("gather", {
            "sources": total_sources,
            "chunks": total_chunks,
            "output_file": output_file,
        })


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'gather'


def register_parser(subparsers):
    """Register gather command parser."""
    p = subparsers.add_parser(
        'gather',
        help='Gather context from multiple sources in parallel'
    )

    # Source specifications (repeatable)
    p.add_argument(
        '--file', '-f',
        action='append',
        dest='files',
        default=[],
        metavar='PATH',
        help='File path to read (repeatable)'
    )
    p.add_argument(
        '--grep', '-g',
        action='append',
        dest='greps',
        default=[],
        metavar='PATTERN[:PATH]',
        help='Grep pattern, optionally with path (repeatable). Format: "pattern" or "pattern:path"'
    )
    p.add_argument(
        '--bash', '-b',
        action='append',
        dest='bashes',
        default=[],
        metavar='COMMAND',
        help='Bash command to execute (repeatable)'
    )
    p.add_argument(
        '--glob',
        action='append',
        dest='globs',
        default=[],
        metavar='PATTERN',
        help='Glob pattern to find files (repeatable)'
    )
    p.add_argument(
        '--symbol', '-s',
        action='append',
        dest='symbols',
        default=[],
        metavar='NAME',
        help='Symbol name to load (class, function, method) (repeatable)'
    )

    # Template metadata
    p.add_argument(
        '--operation', '-o',
        default='Context Gather',
        help='Operation name for template header (default: "Context Gather")'
    )
    p.add_argument(
        '--intent', '-i',
        default='Gather context for analysis',
        help='Intent description for template header'
    )

    # Output options
    p.add_argument(
        '--format',
        dest='output_format',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    p.add_argument(
        '--output',
        dest='output_file',
        metavar='FILE',
        help='Write output to file instead of stdout'
    )

    # Chunking options
    p.add_argument(
        '--limit',
        dest='context_limit_kb',
        type=int,
        default=100,
        help='Context size limit in KB (default: 100)'
    )
    p.add_argument(
        '--strategy',
        choices=['size', 'coherence', 'priority'],
        default='coherence',
        help='Chunking strategy (default: coherence)'
    )

    return p


def handle(cli, args):
    """Handle gather command dispatch."""
    cli._gather_cmd.gather(
        files=args.files,
        greps=args.greps,
        bashes=args.bashes,
        globs=args.globs,
        symbols_list=args.symbols,
        operation=args.operation,
        intent=args.intent,
        output_format=args.output_format,
        output_file=args.output_file,
        context_limit_kb=args.context_limit_kb,
        strategy=args.strategy,
    )
