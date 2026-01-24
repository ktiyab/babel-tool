"""
ContextTemplate — Structured aggregation format for gathered context.

Renders GatherResults into a well-structured markdown document that:
- Has a clear header with operation intent
- Includes a manifest (quick overview table)
- Provides indexed corpus (numbered source contents)
- Is chunk-aware (shows position in multi-chunk gather)

The template format is designed for LLM consumption:
- Easy to parse and navigate
- Metadata inline for quick reference
- Code blocks with language hints
"""

from typing import List, Optional, Dict
from datetime import datetime, timezone
from pathlib import Path

from .result import GatherResult
from .plan import GatherPlan


# File extension to language mapping for code blocks
EXTENSION_LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".fish": "fish",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".env": "bash",
    ".dockerfile": "dockerfile",
    ".makefile": "makefile",
}


def get_language_hint(source_ref: str) -> str:
    """Determine language hint for code block from source reference."""
    if "/" in source_ref or "\\" in source_ref:
        # It's a file path
        ext = Path(source_ref).suffix.lower()
        return EXTENSION_LANG_MAP.get(ext, "")
    return ""


class ContextTemplate:
    """
    Renders gathered results into structured markdown.

    Format:
        ═══════════════════════════════════════════════════════
        CONTEXT GATHER: {operation}
        ═══════════════════════════════════════════════════════

        ## HEADER
        - Intent: {intent}
        - Chunk: {N} of {M}
        - Total Size: {X} KB across {Y} sources
        - Gathered: {timestamp}

        ## MANIFEST
        | # | Type | Source | Size | Status |
        |---|------|--------|------|--------|
        | 1 | file | src/cache.py | 24KB | ✓ |
        ...

        ───────────────────────────────────────────────────────
        ## CORPUS
        ───────────────────────────────────────────────────────

        ### [1/N] FILE: src/cache.py
        - Lines: 800 | Size: 24KB
        ```python
        [content]
        ```

        ...

        ═══════════════════════════════════════════════════════
        END CONTEXT GATHER
        ═══════════════════════════════════════════════════════
    """

    def __init__(
        self,
        plan: GatherPlan,
        chunk_number: int = 1,
        total_chunks: int = 1
    ):
        """
        Initialize template.

        Args:
            plan: The gather plan (for operation/intent)
            chunk_number: Current chunk (1-indexed)
            total_chunks: Total number of chunks
        """
        self.plan = plan
        self.chunk_number = chunk_number
        self.total_chunks = total_chunks

    def render(self, results: List[GatherResult]) -> str:
        """
        Render results into structured markdown.

        Args:
            results: List of GatherResults to render

        Returns:
            Formatted markdown string
        """
        sections = [
            self._render_banner(),
            self._render_header(results),
            self._render_manifest(results),
            self._render_corpus(results),
            self._render_footer(),
        ]

        return "\n".join(sections)

    def _render_banner(self) -> str:
        """Render the opening banner."""
        line = "═" * 60
        return f"""{line}
CONTEXT GATHER: {self.plan.operation}
{line}
"""

    def _render_header(self, results: List[GatherResult]) -> str:
        """Render the header section."""
        total_size_kb = sum(r.size_bytes for r in results) / 1024
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        chunk_info = ""
        if self.total_chunks > 1:
            chunk_info = f"\n- Chunk: {self.chunk_number} of {self.total_chunks}"

        status_note = ""
        if failed > 0:
            status_note = f"\n- Warnings: {failed} source(s) failed to gather"

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""## HEADER
- Intent: {self.plan.intent}{chunk_info}
- Total Size: {total_size_kb:.1f} KB across {len(results)} sources
- Gathered: {timestamp}{status_note}
"""

    def _render_manifest(self, results: List[GatherResult]) -> str:
        """Render the manifest table."""
        lines = [
            "## MANIFEST",
            "",
            "| # | Type | Source | Size | Status |",
            "|---|------|--------|------|--------|",
        ]

        for i, result in enumerate(results, 1):
            status = "✓" if result.success else "✗"
            size = f"{result.size_kb:.1f}KB" if result.size_bytes > 0 else "-"

            # Truncate long source refs
            source_ref = result.source_ref
            if len(source_ref) > 40:
                source_ref = "..." + source_ref[-37:]

            lines.append(f"| {i} | {result.source_type} | {source_ref} | {size} | {status} |")

        lines.append("")
        return "\n".join(lines)

    def _render_corpus(self, results: List[GatherResult]) -> str:
        """Render the corpus (source contents)."""
        lines = [
            "─" * 60,
            "## CORPUS",
            "─" * 60,
            "",
        ]

        total = len(results)
        for i, result in enumerate(results, 1):
            lines.append(self._render_source(result, i, total))
            lines.append("")  # Blank line between sources

        return "\n".join(lines)

    def _render_source(self, result: GatherResult, index: int, total: int) -> str:
        """Render a single source."""
        # Header with index and type
        type_label = result.source_type.upper()
        header = f"### [{index}/{total}] {type_label}: {result.source_ref}"

        # Metadata line
        meta_parts = []
        if result.line_count > 0:
            meta_parts.append(f"Lines: {result.line_count}")
        if result.size_bytes > 0:
            meta_parts.append(f"Size: {result.size_kb:.1f}KB")
        if result.duration_ms > 0:
            meta_parts.append(f"Time: {result.duration_ms:.0f}ms")

        meta_line = f"- {' | '.join(meta_parts)}" if meta_parts else ""

        # Error handling
        if not result.success:
            return f"""{header}
{meta_line}
- **ERROR**: {result.error}
"""

        # Content with appropriate code block
        lang = self._get_content_language(result)
        content = result.content

        # Add trailing newline if missing
        if content and not content.endswith("\n"):
            content += "\n"

        return f"""{header}
{meta_line}
```{lang}
{content}```
"""

    def _get_content_language(self, result: GatherResult) -> str:
        """Determine code block language for result."""
        if result.source_type == "file":
            return get_language_hint(result.source_ref)
        elif result.source_type == "grep":
            return ""  # Mixed file types in grep results
        elif result.source_type == "bash":
            return "bash"
        elif result.source_type == "glob":
            return ""  # Just file paths
        return ""

    def _render_footer(self) -> str:
        """Render the closing footer."""
        line = "═" * 60
        return f"""{line}
END CONTEXT GATHER
{line}
"""


def render_context(
    plan: GatherPlan,
    results: List[GatherResult],
    chunk_number: int = 1,
    total_chunks: int = 1
) -> str:
    """
    Convenience function to render context.

    Args:
        plan: The gather plan
        results: Gathered results
        chunk_number: Current chunk (1-indexed)
        total_chunks: Total chunks

    Returns:
        Formatted markdown string
    """
    template = ContextTemplate(plan, chunk_number, total_chunks)
    return template.render(results)


def render_to_file(
    plan: GatherPlan,
    results: List[GatherResult],
    output_path: str,
    chunk_number: int = 1,
    total_chunks: int = 1
) -> str:
    """
    Render context to a file.

    Args:
        plan: The gather plan
        results: Gathered results
        output_path: Path to write output
        chunk_number: Current chunk (1-indexed)
        total_chunks: Total chunks

    Returns:
        Path to the output file
    """
    content = render_context(plan, results, chunk_number, total_chunks)
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path
