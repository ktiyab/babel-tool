"""
Gather Functions — Pure I/O primitives for context gathering.

These functions are LLM-agnostic and can be used by any AI system.
They are designed to be:
- Pure: No side effects beyond reading
- Testable: Simple inputs/outputs
- Safe: Handle errors gracefully
- Picklable: Can be used with ProcessPool if needed

Each function returns a GatherResult with consistent structure.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional
from glob import glob as glob_files

from .result import GatherResult


def gather_file(path: str, encoding: str = "utf-8") -> GatherResult:
    """
    Gather content from a file.

    Args:
        path: Path to file (absolute or relative)
        encoding: File encoding (default: utf-8)

    Returns:
        GatherResult with file content, size, line count

    Handles:
        - Missing files (returns error result)
        - Binary files (detected and skipped)
        - Encoding errors (fallback to latin-1)
    """
    start_time = time.time()

    try:
        file_path = Path(path)

        # Check existence
        if not file_path.exists():
            return GatherResult.error_result(
                source_type="file",
                source_ref=path,
                error=f"File not found: {path}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Check if directory
        if file_path.is_dir():
            return GatherResult.error_result(
                source_type="file",
                source_ref=path,
                error=f"Path is a directory: {path}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Get file size
        size_bytes = file_path.stat().st_size

        # Skip large files (> 1MB)
        max_size = 1024 * 1024  # 1MB
        if size_bytes > max_size:
            return GatherResult.error_result(
                source_type="file",
                source_ref=path,
                error=f"File too large: {size_bytes / 1024:.1f}KB (max: {max_size / 1024:.0f}KB)",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Try to read content
        try:
            content = file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            # Try fallback encoding
            try:
                content = file_path.read_text(encoding="latin-1")
            except Exception as e:
                return GatherResult.error_result(
                    source_type="file",
                    source_ref=path,
                    error=f"Encoding error: {e}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

        # Check for binary content (null bytes)
        if "\x00" in content:
            return GatherResult.error_result(
                source_type="file",
                source_ref=path,
                error="Binary file detected",
                duration_ms=(time.time() - start_time) * 1000,
            )

        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        duration_ms = (time.time() - start_time) * 1000

        return GatherResult(
            source_type="file",
            source_ref=path,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            line_count=line_count,
            success=True,
            duration_ms=duration_ms,
            metadata={
                "encoding": encoding,
                "absolute_path": str(file_path.absolute()),
            },
        )

    except Exception as e:
        return GatherResult.error_result(
            source_type="file",
            source_ref=path,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )


def gather_grep(
    pattern: str,
    path: str = ".",
    max_matches: int = 100,
    context_lines: int = 0
) -> GatherResult:
    """
    Gather grep search results.

    Uses ripgrep (rg) if available, falls back to grep.

    Args:
        pattern: Regex pattern to search for
        path: Directory or file to search in
        max_matches: Maximum matches to return (default: 100)
        context_lines: Lines of context around matches (default: 0)

    Returns:
        GatherResult with match lines, count, files searched
    """
    start_time = time.time()

    try:
        # Build command (prefer ripgrep)
        rg_available = subprocess.run(
            ["which", "rg"],
            capture_output=True,
            timeout=5
        ).returncode == 0

        if rg_available:
            cmd = [
                "rg",
                "--line-number",
                "--no-heading",
                "--color=never",
                f"--max-count={max_matches}",
            ]
            if context_lines > 0:
                cmd.append(f"-C{context_lines}")
            cmd.extend([pattern, path])
        else:
            cmd = [
                "grep",
                "-rn",
                "--color=never",
            ]
            if context_lines > 0:
                cmd.extend(["-C", str(context_lines)])
            cmd.extend([pattern, path])

        # Execute search
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # grep/rg return 1 if no matches (not an error)
        if result.returncode not in (0, 1):
            return GatherResult.error_result(
                source_type="grep",
                source_ref=pattern,
                error=f"Search failed: {result.stderr}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        content = result.stdout
        lines = content.strip().split("\n") if content.strip() else []
        match_count = len([l for l in lines if l and not l.startswith("--")])

        duration_ms = (time.time() - start_time) * 1000

        return GatherResult(
            source_type="grep",
            source_ref=pattern,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            line_count=len(lines),
            success=True,
            duration_ms=duration_ms,
            metadata={
                "path": path,
                "match_count": match_count,
                "tool": "rg" if rg_available else "grep",
                "max_matches": max_matches,
            },
        )

    except subprocess.TimeoutExpired:
        return GatherResult.error_result(
            source_type="grep",
            source_ref=pattern,
            error="Search timed out",
            duration_ms=(time.time() - start_time) * 1000,
        )
    except Exception as e:
        return GatherResult.error_result(
            source_type="grep",
            source_ref=pattern,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )


def gather_bash(
    command: str,
    timeout: float = 30.0,
    cwd: Optional[str] = None
) -> GatherResult:
    """
    Gather output from a bash command.

    Args:
        command: Shell command to execute
        timeout: Execution timeout in seconds (default: 30)
        cwd: Working directory (default: current)

    Returns:
        GatherResult with command output, exit code

    Security:
        - Commands run in a subprocess, not directly evaluated
        - Timeout prevents hanging
        - Output truncated if too large
    """
    start_time = time.time()

    try:
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\n--- STDERR ---\n{result.stderr}"

        # Truncate if too large (> 100KB)
        max_output = 100 * 1024
        truncated = False
        if len(output) > max_output:
            output = output[:max_output] + "\n... (truncated)"
            truncated = True

        line_count = output.count("\n") + (1 if output and not output.endswith("\n") else 0)
        duration_ms = (time.time() - start_time) * 1000

        return GatherResult(
            source_type="bash",
            source_ref=command,
            content=output,
            size_bytes=len(output.encode("utf-8")),
            line_count=line_count,
            success=result.returncode == 0,
            error=f"Exit code: {result.returncode}" if result.returncode != 0 else None,
            duration_ms=duration_ms,
            metadata={
                "exit_code": result.returncode,
                "cwd": cwd or os.getcwd(),
                "truncated": truncated,
            },
        )

    except subprocess.TimeoutExpired:
        return GatherResult.error_result(
            source_type="bash",
            source_ref=command,
            error=f"Command timed out after {timeout}s",
            duration_ms=(time.time() - start_time) * 1000,
        )
    except Exception as e:
        return GatherResult.error_result(
            source_type="bash",
            source_ref=command,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )


def gather_glob(pattern: str, base_path: str = ".") -> GatherResult:
    """
    Gather file paths matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., "**/*.py", "src/*.js")
        base_path: Base directory for pattern (default: current)

    Returns:
        GatherResult with matching paths, count, total size
    """
    start_time = time.time()

    try:
        # Ensure pattern is relative to base_path
        if not pattern.startswith("/"):
            full_pattern = os.path.join(base_path, pattern)
        else:
            full_pattern = pattern

        # Find matching files
        matches = glob_files(full_pattern, recursive=True)

        # Filter to files only (not directories)
        file_matches = [m for m in matches if os.path.isfile(m)]

        # Sort by path
        file_matches.sort()

        # Calculate total size
        total_size = sum(os.path.getsize(f) for f in file_matches)

        # Format content as file list
        content = "\n".join(file_matches)

        duration_ms = (time.time() - start_time) * 1000

        return GatherResult(
            source_type="glob",
            source_ref=pattern,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            line_count=len(file_matches),
            success=True,
            duration_ms=duration_ms,
            metadata={
                "base_path": base_path,
                "match_count": len(file_matches),
                "total_file_size": total_size,
                "total_file_size_kb": total_size / 1024,
            },
        )

    except Exception as e:
        return GatherResult.error_result(
            source_type="glob",
            source_ref=pattern,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )


def estimate_file_size(path: str) -> int:
    """
    Quickly estimate file size without reading content.

    Used by ChunkBroker for size estimation before gathering.

    Args:
        path: Path to file

    Returns:
        Size in bytes, or 0 if file doesn't exist
    """
    try:
        return Path(path).stat().st_size
    except Exception:
        return 0


def estimate_grep_size(pattern: str, path: str = ".") -> int:
    """
    Estimate grep result size (rough approximation).

    Uses quick count of matches * average line length.

    Args:
        pattern: Search pattern
        path: Search path

    Returns:
        Estimated size in bytes
    """
    try:
        # Quick count using grep -c
        result = subprocess.run(
            ["grep", "-rc", pattern, path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return 0

        # Sum up match counts
        total_matches = 0
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                try:
                    count = int(line.split(":")[-1])
                    total_matches += count
                except ValueError:
                    pass

        # Estimate: ~100 bytes per match line
        return total_matches * 100

    except Exception:
        return 0


def gather_symbol(
    name: str,
    project_dir: Optional[str] = None,
    context_lines: int = 5
) -> GatherResult:
    """
    Gather code for a symbol by name (class, function, method).

    Uses the symbol index cache to find the symbol location,
    then loads only the relevant lines from the file.

    Args:
        name: Symbol name (e.g., "GraphStore", "gather_file")
        project_dir: Project directory containing .babel (default: current)
        context_lines: Extra lines before/after symbol (default: 5)

    Returns:
        GatherResult with symbol code, location info

    This function enables token-efficient code loading:
    - Instead of loading entire files, load only the symbol
    - Uses processor-backed index (AST), not LLM inference
    """
    import json
    start_time = time.time()

    try:
        # Find project directory and .babel
        if project_dir:
            project_path = Path(project_dir)
        else:
            project_path = Path.cwd()

        # Look for .babel directory (try current and parent directories)
        babel_dir = None
        search_path = project_path
        for _ in range(5):  # Search up to 5 levels
            candidate = search_path / ".babel"
            if candidate.exists():
                babel_dir = candidate
                project_path = search_path
                break
            search_path = search_path.parent

        if not babel_dir:
            return GatherResult.error_result(
                source_type="symbol",
                source_ref=name,
                error="No .babel directory found (run: babel map --index)",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Load symbol cache
        cache_path = babel_dir / "symbol_cache.json"
        if not cache_path.exists():
            return GatherResult.error_result(
                source_type="symbol",
                source_ref=name,
                error="Symbol index not found (run: babel map --index)",
                duration_ms=(time.time() - start_time) * 1000,
            )

        try:
            cache_data = json.loads(cache_path.read_text())
            symbols = cache_data.get("symbols", [])
        except (json.JSONDecodeError, KeyError) as e:
            return GatherResult.error_result(
                source_type="symbol",
                source_ref=name,
                error=f"Failed to read symbol cache: {e}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Find matching symbol
        name_lower = name.lower()
        matching_symbol = None
        for sym in symbols:
            sym_name = sym.get("name", "").lower()
            sym_qname = sym.get("qualified_name", "").lower()
            # Match by simple name or qualified name
            if sym_name == name_lower or sym_qname.endswith(name_lower):
                matching_symbol = sym
                break

        if not matching_symbol:
            return GatherResult.error_result(
                source_type="symbol",
                source_ref=name,
                error=f"Symbol not found: {name}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Extract symbol info
        file_path = matching_symbol.get("file_path", "")
        line_start = matching_symbol.get("line_start", 1)
        line_end = matching_symbol.get("line_end", line_start)
        symbol_type = matching_symbol.get("symbol_type", "unknown")
        signature = matching_symbol.get("signature", "")
        qualified_name = matching_symbol.get("qualified_name", name)

        # Build full file path
        full_path = project_path / file_path
        if not full_path.exists():
            return GatherResult.error_result(
                source_type="symbol",
                source_ref=name,
                error=f"Source file not found: {file_path}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Read only the relevant lines (with context)
        try:
            all_lines = full_path.read_text(encoding="utf-8").split("\n")
        except UnicodeDecodeError:
            all_lines = full_path.read_text(encoding="latin-1").split("\n")

        # Calculate range with context
        start_idx = max(0, line_start - 1 - context_lines)
        end_idx = min(len(all_lines), line_end + context_lines)

        # Extract lines
        extracted_lines = all_lines[start_idx:end_idx]
        content = "\n".join(extracted_lines)

        # Build formatted output with header
        header = f"# Symbol: {qualified_name}\n"
        header += f"# Type: {symbol_type}\n"
        header += f"# File: {file_path}:{line_start}-{line_end}\n"
        if signature:
            header += f"# Signature: {signature}\n"
        header += f"# Lines: {start_idx + 1}-{end_idx} (context: {context_lines})\n"
        header += "\n"

        formatted_content = header + content

        duration_ms = (time.time() - start_time) * 1000

        return GatherResult(
            source_type="symbol",
            source_ref=name,
            content=formatted_content,
            size_bytes=len(formatted_content.encode("utf-8")),
            line_count=len(extracted_lines),
            success=True,
            duration_ms=duration_ms,
            metadata={
                "qualified_name": qualified_name,
                "symbol_type": symbol_type,
                "file_path": file_path,
                "line_start": line_start,
                "line_end": line_end,
                "signature": signature,
                "context_lines": context_lines,
                "actual_lines": f"{start_idx + 1}-{end_idx}",
            },
        )

    except Exception as e:
        return GatherResult.error_result(
            source_type="symbol",
            source_ref=name,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )
