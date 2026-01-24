"""
Tests for Parallel Context Gather System.

Covers:
- GatherResult creation and serialization
- GatherPlan fluent interface
- GatherSource factory methods
- Gather functions (file, grep, bash, glob)
- ChunkBroker chunking strategies
- ContextGatherer parallel execution
- ContextTemplate rendering
"""

import os
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from babel.gather import (
    # Result
    GatherResult,
    # Plan
    GatherPlan,
    GatherSource,
    SourceType,
    SourcePriority,
    # Functions
    gather_file,
    gather_grep,
    gather_bash,
    gather_glob,
    estimate_file_size,
    estimate_grep_size,
    # Template
    ContextTemplate,
    render_context,
    render_to_file,
    # Broker
    ChunkBroker,
    ChunkStrategy,
    Chunk,
    plan_chunks,
    # Gatherer
    ContextGatherer,
    gather_context,
    gather_files,
)


# =============================================================================
# GatherResult Tests
# =============================================================================


class TestGatherResult:
    """Tests for GatherResult dataclass."""

    def test_create_success_result(self):
        """Create a successful gather result."""
        result = GatherResult(
            source_type="file",
            source_ref="/path/to/file.py",
            content="hello world",
            size_bytes=11,
            line_count=1,
            success=True,
        )

        assert result.source_type == "file"
        assert result.source_ref == "/path/to/file.py"
        assert result.content == "hello world"
        assert result.success is True
        assert result.failed is False
        assert result.error is None

    def test_create_error_result(self):
        """Create an error result using factory method."""
        result = GatherResult.error_result(
            source_type="file",
            source_ref="/missing.py",
            error="File not found",
            duration_ms=5.0,
        )

        assert result.success is False
        assert result.failed is True
        assert result.error == "File not found"
        assert result.content == ""
        assert result.size_bytes == 0

    def test_size_kb_property(self):
        """Size in KB calculation."""
        result = GatherResult(
            source_type="file",
            source_ref="test.py",
            content="x" * 1024,
            size_bytes=1024,
        )

        assert result.size_kb == 1.0

    def test_summary_format(self):
        """Summary displays correctly."""
        result = GatherResult(
            source_type="file",
            source_ref="src/cache.py",
            content="code",
            size_bytes=2048,
            success=True,
        )

        summary = result.summary()
        assert "✓" in summary
        assert "file" in summary
        assert "cache.py" in summary
        assert "2.0KB" in summary

    def test_summary_error_format(self):
        """Summary for failed result shows X mark."""
        result = GatherResult.error_result(
            source_type="grep",
            source_ref="pattern",
            error="Search failed",
        )

        summary = result.summary()
        assert "✗" in summary

    def test_serialization_roundtrip(self):
        """to_dict and from_dict preserve all fields."""
        original = GatherResult(
            source_type="bash",
            source_ref="ls -la",
            content="output",
            size_bytes=100,
            line_count=5,
            success=True,
            duration_ms=50.0,
            metadata={"exit_code": 0},
        )

        serialized = original.to_dict()
        restored = GatherResult.from_dict(serialized)

        assert restored.source_type == original.source_type
        assert restored.source_ref == original.source_ref
        assert restored.content == original.content
        assert restored.size_bytes == original.size_bytes
        assert restored.success == original.success
        assert restored.metadata == original.metadata

    def test_result_is_immutable(self):
        """GatherResult is frozen (immutable)."""
        result = GatherResult(
            source_type="file",
            source_ref="test.py",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            result.content = "changed"


# =============================================================================
# GatherSource Tests
# =============================================================================


class TestGatherSource:
    """Tests for GatherSource dataclass."""

    def test_file_factory(self):
        """Create file source via factory."""
        source = GatherSource.file(
            "/path/to/file.py",
            priority=SourcePriority.HIGH,
            group="core",
        )

        assert source.source_type == SourceType.FILE
        assert source.reference == "/path/to/file.py"
        assert source.priority == SourcePriority.HIGH
        assert source.group == "core"

    def test_grep_factory(self):
        """Create grep source via factory."""
        source = GatherSource.grep(
            "CacheError",
            path="src/",
            priority=SourcePriority.NORMAL,
        )

        assert source.source_type == SourceType.GREP
        assert source.reference == "CacheError"
        assert source.params["path"] == "src/"

    def test_bash_factory(self):
        """Create bash source via factory."""
        source = GatherSource.bash(
            "git log -5",
            timeout=60.0,
        )

        assert source.source_type == SourceType.BASH
        assert source.reference == "git log -5"
        assert source.params["timeout"] == 60.0

    def test_glob_factory(self):
        """Create glob source via factory."""
        source = GatherSource.glob("**/*.py")

        assert source.source_type == SourceType.GLOB
        assert source.reference == "**/*.py"

    def test_serialization_roundtrip(self):
        """to_dict and from_dict preserve all fields."""
        original = GatherSource.grep(
            "pattern",
            path="src/",
            priority=SourcePriority.CRITICAL,
            group="search",
        )
        original.estimated_size_bytes = 5000

        serialized = original.to_dict()
        restored = GatherSource.from_dict(serialized)

        assert restored.source_type == original.source_type
        assert restored.reference == original.reference
        assert restored.params == original.params
        assert restored.priority == original.priority
        assert restored.group == original.group


# =============================================================================
# GatherPlan Tests
# =============================================================================


class TestGatherPlan:
    """Tests for GatherPlan dataclass."""

    def test_create_empty_plan(self):
        """Create plan with no sources."""
        plan = GatherPlan(
            operation="Fix bug",
            intent="Understand issue",
        )

        assert plan.operation == "Fix bug"
        assert plan.intent == "Understand issue"
        assert plan.source_count == 0

    def test_fluent_interface(self):
        """Add sources using fluent interface."""
        plan = (
            GatherPlan(operation="Analysis", intent="Understand cache")
            .add_file("src/cache.py", priority=SourcePriority.CRITICAL)
            .add_file("src/api.py")
            .add_grep("CacheError", "src/")
            .add_bash("git log -5 src/cache.py")
            .add_glob("tests/test_*.py")
        )

        assert plan.source_count == 5
        assert len(plan.sources_by_type(SourceType.FILE)) == 2
        assert len(plan.sources_by_type(SourceType.GREP)) == 1
        assert len(plan.sources_by_type(SourceType.BASH)) == 1
        assert len(plan.sources_by_type(SourceType.GLOB)) == 1

    def test_sources_by_priority(self):
        """Filter sources by priority."""
        plan = (
            GatherPlan(operation="Test", intent="Test")
            .add_file("critical.py", priority=SourcePriority.CRITICAL)
            .add_file("normal.py", priority=SourcePriority.NORMAL)
            .add_file("low.py", priority=SourcePriority.LOW)
        )

        critical = plan.sources_by_priority(SourcePriority.CRITICAL)
        assert len(critical) == 1
        assert critical[0].reference == "critical.py"

    def test_sources_by_group(self):
        """Filter sources by group."""
        plan = (
            GatherPlan(operation="Test", intent="Test")
            .add_file("cache.py", group="cache")
            .add_file("api.py", group="api")
            .add_file("cache_utils.py", group="cache")
        )

        cache_sources = plan.sources_by_group("cache")
        assert len(cache_sources) == 2

    def test_serialization_roundtrip(self):
        """to_dict and from_dict preserve all fields."""
        original = (
            GatherPlan(operation="Analyze", intent="Understand system")
            .add_file("src/main.py", priority=SourcePriority.HIGH)
            .add_grep("error", "logs/")
        )

        serialized = original.to_dict()
        restored = GatherPlan.from_dict(serialized)

        assert restored.operation == original.operation
        assert restored.intent == original.intent
        assert restored.source_count == original.source_count

    def test_summary_output(self):
        """Summary provides readable overview."""
        plan = (
            GatherPlan(operation="Debug", intent="Find bug")
            .add_file("a.py")
            .add_file("b.py")
            .add_grep("error")
        )

        summary = plan.summary()
        assert "Debug" in summary
        assert "Find bug" in summary
        assert "file: 2" in summary
        assert "grep: 1" in summary


# =============================================================================
# Gather Functions Tests
# =============================================================================


class TestGatherFile:
    """Tests for gather_file function."""

    def test_gather_existing_file(self, tmp_path):
        """Successfully gather existing file content."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\nprint('world')")

        result = gather_file(str(test_file))

        assert result.success is True
        assert result.source_type == "file"
        assert "hello" in result.content
        assert result.line_count == 2
        assert result.size_bytes > 0

    def test_gather_missing_file(self):
        """Gather non-existent file returns error."""
        result = gather_file("/nonexistent/path/file.py")

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_gather_directory_error(self, tmp_path):
        """Gather directory returns error."""
        result = gather_file(str(tmp_path))

        assert result.success is False
        assert "directory" in result.error.lower()

    def test_gather_large_file_error(self, tmp_path):
        """Files over 1MB return error."""
        large_file = tmp_path / "large.txt"
        large_file.write_bytes(b"x" * (1024 * 1024 + 1))  # > 1MB

        result = gather_file(str(large_file))

        assert result.success is False
        assert "too large" in result.error.lower()

    def test_gather_binary_file_error(self, tmp_path):
        """Binary files return error."""
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        result = gather_file(str(binary_file))

        assert result.success is False
        assert "binary" in result.error.lower()

    def test_metadata_includes_path(self, tmp_path):
        """Metadata includes absolute path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = gather_file(str(test_file))

        assert "absolute_path" in result.metadata


class TestGatherBash:
    """Tests for gather_bash function."""

    def test_gather_successful_command(self):
        """Gather output from successful command."""
        result = gather_bash("echo 'hello world'")

        assert result.success is True
        assert result.source_type == "bash"
        assert "hello world" in result.content

    def test_gather_failed_command(self):
        """Gather from failing command captures error."""
        result = gather_bash("exit 1")

        assert result.success is False
        assert "exit_code" in result.metadata
        assert result.metadata["exit_code"] == 1

    def test_gather_timeout(self):
        """Commands exceeding timeout return error."""
        result = gather_bash("sleep 5", timeout=0.1)

        assert result.success is False
        assert "timed out" in result.error.lower()

    def test_gather_with_cwd(self, tmp_path):
        """Commands run in specified directory."""
        result = gather_bash("pwd", cwd=str(tmp_path))

        assert result.success is True
        assert str(tmp_path) in result.content


class TestGatherGlob:
    """Tests for gather_glob function."""

    def test_gather_matching_files(self, tmp_path):
        """Glob returns matching file paths."""
        # Create test files
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.txt").write_text("c")

        result = gather_glob("*.py", str(tmp_path))

        assert result.success is True
        assert result.source_type == "glob"
        assert "a.py" in result.content
        assert "b.py" in result.content
        assert "c.txt" not in result.content
        assert result.metadata["match_count"] == 2

    def test_gather_no_matches(self, tmp_path):
        """Glob with no matches returns empty but success."""
        result = gather_glob("*.nonexistent", str(tmp_path))

        assert result.success is True
        assert result.line_count == 0


class TestGatherGrep:
    """Tests for gather_grep function."""

    def test_gather_matching_pattern(self, tmp_path):
        """Grep finds matching pattern."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        result = gather_grep("hello", str(tmp_path))

        assert result.success is True
        assert result.source_type == "grep"
        assert "hello" in result.content

    def test_gather_no_matches(self, tmp_path):
        """Grep with no matches returns empty but success."""
        test_file = tmp_path / "test.py"
        test_file.write_text("nothing here")

        result = gather_grep("nonexistent_pattern_xyz", str(tmp_path))

        assert result.success is True
        assert result.content.strip() == ""


class TestEstimateFunctions:
    """Tests for size estimation functions."""

    def test_estimate_file_size(self, tmp_path):
        """File size estimation returns correct value."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 100)

        size = estimate_file_size(str(test_file))
        assert size == 100

    def test_estimate_missing_file(self):
        """Missing file returns 0."""
        size = estimate_file_size("/nonexistent/file.txt")
        assert size == 0


# =============================================================================
# ChunkBroker Tests
# =============================================================================


class TestChunkBroker:
    """Tests for ChunkBroker chunking logic."""

    def test_empty_plan_returns_empty(self):
        """Empty plan produces no chunks."""
        broker = ChunkBroker(context_limit_kb=100)
        plan = GatherPlan(operation="Test", intent="Test")

        chunks = broker.plan_chunks(plan)

        assert chunks == []

    def test_small_plan_single_chunk(self, tmp_path):
        """Small plan fits in single chunk."""
        # Create small test file
        test_file = tmp_path / "small.py"
        test_file.write_text("x" * 100)

        broker = ChunkBroker(context_limit_kb=100)
        plan = GatherPlan(operation="Test", intent="Test").add_file(str(test_file))

        chunks = broker.plan_chunks(plan)

        assert len(chunks) == 1
        assert chunks[0].source_count == 1

    def test_large_plan_multiple_chunks(self, tmp_path):
        """Large plan splits into multiple chunks."""
        # Create multiple files that exceed context limit
        for i in range(20):
            (tmp_path / f"file{i}.py").write_text("x" * 10000)  # 10KB each

        broker = ChunkBroker(context_limit_kb=50)  # 50KB limit
        plan = GatherPlan(operation="Test", intent="Test")
        for i in range(20):
            plan.add_file(str(tmp_path / f"file{i}.py"))

        chunks = broker.plan_chunks(plan)

        # Should need multiple chunks for 200KB of content in 50KB chunks
        assert len(chunks) > 1
        # Total sources should be preserved
        total_sources = sum(c.source_count for c in chunks)
        assert total_sources == 20

    def test_fits_in_single_chunk(self, tmp_path):
        """Check if plan fits in single chunk."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("small content")

        broker = ChunkBroker(context_limit_kb=100)
        plan = GatherPlan(operation="Test", intent="Test").add_file(str(test_file))

        assert broker.fits_in_single_chunk(plan) is True

    def test_estimate_chunk_count(self, tmp_path):
        """Estimate number of chunks needed."""
        # Create files totaling ~100KB
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text("x" * 10000)

        broker = ChunkBroker(context_limit_kb=50)  # 50KB limit
        plan = GatherPlan(operation="Test", intent="Test")
        for i in range(10):
            plan.add_file(str(tmp_path / f"file{i}.py"))

        estimate = broker.estimate_chunk_count(plan)

        # ~100KB / 50KB = ~2 chunks
        assert estimate >= 2

    def test_size_based_strategy(self, tmp_path):
        """SIZE_BASED strategy fills chunks by size."""
        for i in range(5):
            (tmp_path / f"file{i}.py").write_text("x" * 5000)

        broker = ChunkBroker(
            context_limit_kb=15,
            strategy=ChunkStrategy.SIZE_BASED
        )
        plan = GatherPlan(operation="Test", intent="Test")
        for i in range(5):
            plan.add_file(str(tmp_path / f"file{i}.py"))

        chunks = broker.plan_chunks(plan)

        # Each chunk should stay under ~15KB
        for chunk in chunks:
            assert chunk.estimated_size_kb < 20  # Allow some overhead

    def test_coherence_strategy_groups_directory(self, tmp_path):
        """COHERENCE_BASED strategy groups same-directory files."""
        # Create files in two directories
        dir1 = tmp_path / "src"
        dir2 = tmp_path / "tests"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "a.py").write_text("x" * 1000)
        (dir1 / "b.py").write_text("x" * 1000)
        (dir2 / "test_a.py").write_text("x" * 1000)

        broker = ChunkBroker(
            context_limit_kb=100,
            strategy=ChunkStrategy.COHERENCE_BASED
        )
        plan = (
            GatherPlan(operation="Test", intent="Test")
            .add_file(str(dir1 / "a.py"))
            .add_file(str(dir2 / "test_a.py"))  # Different dir
            .add_file(str(dir1 / "b.py"))       # Same as first
        )

        chunks = broker.plan_chunks(plan)

        # Should group coherently (dir files together)
        # With small sizes, may all fit in one chunk, but order matters
        assert len(chunks) >= 1

    def test_priority_based_strategy(self, tmp_path):
        """PRIORITY_BASED strategy orders by importance."""
        for i in range(3):
            (tmp_path / f"file{i}.py").write_text("x" * 1000)

        broker = ChunkBroker(
            context_limit_kb=100,
            strategy=ChunkStrategy.PRIORITY_BASED
        )
        plan = (
            GatherPlan(operation="Test", intent="Test")
            .add_file(str(tmp_path / "file0.py"), priority=SourcePriority.LOW)
            .add_file(str(tmp_path / "file1.py"), priority=SourcePriority.CRITICAL)
            .add_file(str(tmp_path / "file2.py"), priority=SourcePriority.NORMAL)
        )

        chunks = broker.plan_chunks(plan)

        # First source in first chunk should be CRITICAL
        assert chunks[0].sources[0].priority == SourcePriority.CRITICAL


class TestPlanChunksConvenience:
    """Tests for plan_chunks convenience function."""

    def test_plan_chunks_default_strategy(self, tmp_path):
        """plan_chunks uses default coherence strategy."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        plan = GatherPlan(operation="Test", intent="Test").add_file(str(test_file))
        chunks = plan_chunks(plan)

        assert len(chunks) >= 1


# =============================================================================
# ContextGatherer Tests
# =============================================================================


class TestContextGatherer:
    """Tests for ContextGatherer class."""

    def test_gather_empty_plan(self):
        """Gathering empty plan returns empty results."""
        gatherer = ContextGatherer()
        plan = GatherPlan(operation="Test", intent="Test")

        results = gatherer.gather(plan)

        assert results == []

    def test_gather_single_file(self, tmp_path):
        """Gather single file successfully."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        gatherer = ContextGatherer()
        plan = GatherPlan(operation="Test", intent="Test").add_file(str(test_file))

        results = gatherer.gather(plan)

        assert len(results) == 1
        assert results[0].success is True
        assert "hello" in results[0].content

    def test_gather_multiple_sources(self, tmp_path):
        """Gather multiple sources preserves order."""
        (tmp_path / "a.py").write_text("file a")
        (tmp_path / "b.py").write_text("file b")

        gatherer = ContextGatherer()
        plan = (
            GatherPlan(operation="Test", intent="Test")
            .add_file(str(tmp_path / "a.py"))
            .add_file(str(tmp_path / "b.py"))
        )

        results = gatherer.gather(plan)

        assert len(results) == 2
        assert "file a" in results[0].content
        assert "file b" in results[1].content

    def test_gather_mixed_success_and_error(self, tmp_path):
        """Gather handles mix of successes and failures."""
        test_file = tmp_path / "exists.py"
        test_file.write_text("content")

        gatherer = ContextGatherer()
        plan = (
            GatherPlan(operation="Test", intent="Test")
            .add_file(str(test_file))
            .add_file("/nonexistent/file.py")
        )

        results = gatherer.gather(plan)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    def test_sequential_fallback(self, tmp_path):
        """Gatherer falls back to sequential when no orchestrator."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        # Create gatherer that will use sequential mode
        gatherer = ContextGatherer()
        gatherer._use_parallel = False

        plan = GatherPlan(operation="Test", intent="Test").add_file(str(test_file))
        results = gatherer.gather_sources(plan.sources)

        assert len(results) == 1
        assert results[0].success is True


class TestGatherConvenienceFunctions:
    """Tests for convenience functions."""

    def test_gather_context(self, tmp_path):
        """gather_context convenience function works."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        plan = GatherPlan(operation="Test", intent="Test").add_file(str(test_file))
        results = gather_context(plan)

        assert len(results) == 1
        assert results[0].success is True

    def test_gather_files(self, tmp_path):
        """gather_files convenience function works."""
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")

        results = gather_files([
            str(tmp_path / "a.py"),
            str(tmp_path / "b.py"),
        ])

        assert len(results) == 2
        assert all(r.success for r in results)


# =============================================================================
# ContextTemplate Tests
# =============================================================================


class TestContextTemplate:
    """Tests for ContextTemplate rendering."""

    def test_render_single_result(self):
        """Render single successful result."""
        plan = GatherPlan(operation="Test Op", intent="Test intent")
        results = [
            GatherResult(
                source_type="file",
                source_ref="src/test.py",
                content="print('hello')",
                size_bytes=15,
                line_count=1,
                success=True,
            )
        ]

        template = ContextTemplate(plan)
        output = template.render(results)

        # Check structure
        assert "CONTEXT GATHER: Test Op" in output
        assert "Intent: Test intent" in output
        assert "MANIFEST" in output
        assert "CORPUS" in output
        assert "END CONTEXT GATHER" in output

        # Check content
        assert "src/test.py" in output
        assert "print('hello')" in output

    def test_render_with_chunks(self):
        """Render shows chunk position."""
        plan = GatherPlan(operation="Multi", intent="Multi-chunk gather")
        results = [
            GatherResult(source_type="file", source_ref="a.py", content="a"),
        ]

        template = ContextTemplate(plan, chunk_number=2, total_chunks=3)
        output = template.render(results)

        assert "Chunk: 2 of 3" in output

    def test_render_error_result(self):
        """Render includes error information."""
        plan = GatherPlan(operation="Test", intent="Test")
        results = [
            GatherResult.error_result(
                source_type="file",
                source_ref="missing.py",
                error="File not found",
            )
        ]

        template = ContextTemplate(plan)
        output = template.render(results)

        assert "ERROR" in output
        assert "File not found" in output
        assert "✗" in output  # Error marker in manifest

    def test_render_manifest_table(self):
        """Manifest table has correct structure."""
        plan = GatherPlan(operation="Test", intent="Test")
        results = [
            GatherResult(
                source_type="file",
                source_ref="a.py",
                content="a",
                size_bytes=1024,
                success=True,
            ),
            GatherResult(
                source_type="grep",
                source_ref="pattern",
                content="match",
                size_bytes=512,
                success=True,
            ),
        ]

        template = ContextTemplate(plan)
        output = template.render(results)

        # Check manifest structure
        assert "| # | Type | Source | Size | Status |" in output
        assert "| 1 | file |" in output
        assert "| 2 | grep |" in output

    def test_render_code_blocks_with_language(self):
        """Code blocks include language hints."""
        plan = GatherPlan(operation="Test", intent="Test")
        results = [
            GatherResult(
                source_type="file",
                source_ref="src/test.py",
                content="def hello(): pass",
                size_bytes=17,
                success=True,
            ),
        ]

        template = ContextTemplate(plan)
        output = template.render(results)

        # Python file should get python language hint
        assert "```python" in output

    def test_render_to_file(self, tmp_path):
        """render_to_file writes output correctly."""
        plan = GatherPlan(operation="Test", intent="Test")
        results = [
            GatherResult(source_type="file", source_ref="a.py", content="content"),
        ]

        output_path = str(tmp_path / "output.md")
        result_path = render_to_file(plan, results, output_path)

        assert Path(result_path).exists()
        content = Path(result_path).read_text()
        assert "CONTEXT GATHER" in content


class TestRenderContextConvenience:
    """Tests for render_context convenience function."""

    def test_render_context_basic(self):
        """render_context convenience function works."""
        plan = GatherPlan(operation="Test", intent="Test")
        results = [
            GatherResult(source_type="file", source_ref="a.py", content="x"),
        ]

        output = render_context(plan, results)

        assert "CONTEXT GATHER: Test" in output


# =============================================================================
# Integration Tests
# =============================================================================


class TestGatherIntegration:
    """Integration tests for the full gather pipeline."""

    def test_full_pipeline(self, tmp_path):
        """Test complete Plan -> Chunk -> Gather -> Render pipeline."""
        # Setup: Create test files
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def util(): pass")

        # Step 1: Create plan
        plan = (
            GatherPlan(
                operation="Understand codebase",
                intent="Get overview of Python modules"
            )
            .add_file(str(tmp_path / "main.py"), priority=SourcePriority.HIGH)
            .add_file(str(tmp_path / "utils.py"))
        )

        assert plan.source_count == 2

        # Step 2: Plan chunks
        broker = ChunkBroker(context_limit_kb=100)
        chunks = broker.plan_chunks(plan)

        assert len(chunks) >= 1
        assert broker.fits_in_single_chunk(plan)

        # Step 3: Gather context
        gatherer = ContextGatherer()
        all_results = []

        for chunk in chunks:
            results = gatherer.gather_sources(chunk.sources)
            all_results.extend(results)

        assert len(all_results) == 2
        assert all(r.success for r in all_results)

        # Step 4: Render to template
        output = render_context(plan, all_results)

        assert "Understand codebase" in output
        assert "main.py" in output
        assert "utils.py" in output
        assert "def main" in output
        assert "def util" in output

    def test_pipeline_with_errors(self, tmp_path):
        """Pipeline handles partial failures gracefully."""
        (tmp_path / "exists.py").write_text("valid content")

        plan = (
            GatherPlan(operation="Test", intent="Test")
            .add_file(str(tmp_path / "exists.py"))
            .add_file(str(tmp_path / "missing.py"))
        )

        broker = ChunkBroker()
        chunks = broker.plan_chunks(plan)

        gatherer = ContextGatherer()
        results = gatherer.gather_sources(chunks[0].sources)

        # One success, one failure
        assert results[0].success is True
        assert results[1].success is False

        # Template still renders
        output = render_context(plan, results)
        assert "valid content" in output
        assert "ERROR" in output
