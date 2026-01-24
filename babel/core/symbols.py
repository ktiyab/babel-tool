"""
CodeSymbolStore — Processor-backed code symbol index for strategic loading

Enables LLMs to query symbol locations without loading full files.
Maps folders/classes/functions with precise line locations.

Key design principles:
- Processor-backed (AST parsing), not LLM inference
- Event-sourced (HC1: SYMBOL_INDEXED events)
- Incremental (git diff-based updates)
- Graph-integrated (code_symbol nodes in GraphStore)

Usage:
    from babel.core.symbols import CodeSymbolStore

    store = CodeSymbolStore(babel_dir, events, graph)
    store.index_project(project_dir)           # Full index
    store.index_changed_files(project_dir)     # Incremental
    symbols = store.query("CacheManager")      # Find symbols
"""

import ast
import json
import subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any

from .events import DualEventStore, EventType, index_symbol


@dataclass
class Symbol:
    """A code symbol extracted via AST parsing."""
    symbol_type: str        # "class" | "function" | "method" | "module"
    name: str               # Simple name (e.g., "CacheManager")
    qualified_name: str     # Full path (e.g., "babel.core.cache.CacheManager")
    file_path: str          # Relative path from project root
    line_start: int         # Starting line (1-indexed)
    line_end: int           # Ending line (1-indexed)
    signature: str = ""     # Full signature
    docstring: str = ""     # First line of docstring
    parent_symbol: str = "" # ID of containing symbol (for methods)
    visibility: str = "public"  # "public" | "private"
    git_hash: str = ""      # Commit hash when indexed
    event_id: str = ""      # SYMBOL_INDEXED event ID

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Symbol':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CodeSymbolStore:
    """
    Processor-backed code symbol index.

    Uses AST parsing to extract symbols and emit SYMBOL_INDEXED events.
    Graph projection handled by GraphStore._project_event().

    Architecture:
    - Parse: AST extracts symbols from Python files
    - Event: SYMBOL_INDEXED events emitted (HC1: append-only)
    - Project: GraphStore creates code_symbol nodes
    - Query: Graph traversal finds symbols
    """

    def __init__(
        self,
        babel_dir: Path,
        events: DualEventStore,
        graph: Any,  # GraphStore - avoid circular import
        project_dir: Path = None
    ):
        """
        Initialize symbol store.

        Args:
            babel_dir: Path to .babel directory
            events: Event store for SYMBOL_INDEXED events
            graph: Graph store for projections
            project_dir: Project root (defaults to babel_dir parent)
        """
        self.babel_dir = Path(babel_dir)
        self.events = events
        self.graph = graph
        self.project_dir = Path(project_dir) if project_dir else self.babel_dir.parent

        # Cache for indexed symbols (by qualified_name)
        self._cache: Dict[str, Symbol] = {}
        self._cache_path = self.babel_dir / "symbol_cache.json"
        self._load_cache()

    # =========================================================================
    # Cache Management
    # =========================================================================

    def _load_cache(self):
        """Load symbol cache from disk."""
        if self._cache_path.exists():
            try:
                data = json.loads(self._cache_path.read_text())
                for sym_data in data.get('symbols', []):
                    sym = Symbol.from_dict(sym_data)
                    self._cache[sym.qualified_name] = sym
            except (json.JSONDecodeError, KeyError):
                self._cache = {}

    def _save_cache(self):
        """Save symbol cache to disk."""
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'version': 1,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'symbols': [sym.to_dict() for sym in self._cache.values()]
        }
        self._cache_path.write_text(json.dumps(data, indent=2))

    def clear_symbols(self, pattern: str, exclude: str = None) -> Tuple[int, int]:
        """
        Clear symbols matching a path pattern.

        Code symbols are cache (not intent), so clearing is safe.
        Removes from both in-memory cache and graph projection.

        Args:
            pattern: Path pattern to match (e.g., '.venv' matches any path containing .venv)
            exclude: Optional pattern to exclude from clearing

        Returns:
            Tuple of (cache_cleared, graph_cleared) counts
        """
        # Clear from cache
        cache_cleared = 0
        to_remove = []
        for qn, sym in self._cache.items():
            if pattern in sym.file_path:
                if exclude and exclude in sym.file_path:
                    continue
                to_remove.append(qn)

        for qn in to_remove:
            del self._cache[qn]
            cache_cleared += 1

        self._save_cache()

        # Clear from graph (use SQL LIKE pattern)
        sql_pattern = f'%{pattern}%'
        sql_exclude = f'%{exclude}%' if exclude else None
        graph_cleared = self.graph.delete_nodes_by_type_pattern(
            'code_symbol', sql_pattern, sql_exclude
        )

        return cache_cleared, graph_cleared

    def _get_git_hash(self) -> Optional[str]:
        """Get current HEAD commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    # =========================================================================
    # AST Parsing
    # =========================================================================

    def parse_file(self, file_path: Path) -> List[Symbol]:
        """
        Parse a Python file and extract symbols.

        Args:
            file_path: Path to Python file (absolute or relative to project)

        Returns:
            List of extracted Symbol objects
        """
        # Normalize path
        if not file_path.is_absolute():
            abs_path = self.project_dir / file_path
        else:
            abs_path = file_path
            file_path = abs_path.relative_to(self.project_dir)

        if not abs_path.exists() or not abs_path.suffix == '.py':
            return []

        try:
            content = abs_path.read_text(encoding='utf-8', errors='ignore')

            # Skip very large files
            if len(content) > 200000:  # 200KB limit
                return []

            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []

        symbols = []
        git_hash = self._get_git_hash() or ""

        # Build qualified name prefix from file path
        # babel/core/cache.py -> babel.core.cache
        parts = list(file_path.with_suffix('').parts)
        module_name = '.'.join(parts)

        # Module-level docstring
        module_docstring = ast.get_docstring(tree) or ""
        if module_docstring:
            module_docstring = module_docstring.split('\n')[0][:200]

        # Extract top-level definitions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_sym = self._extract_class(node, module_name, str(file_path), git_hash)
                symbols.append(class_sym)

                # Extract methods within class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_sym = self._extract_function(
                            item,
                            f"{module_name}.{node.name}",
                            str(file_path),
                            git_hash,
                            is_method=True
                        )
                        # Will link parent after event emission
                        symbols.append(method_sym)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_sym = self._extract_function(node, module_name, str(file_path), git_hash)
                symbols.append(func_sym)

        return symbols

    def parse_markdown_file(self, file_path: Path) -> List[Symbol]:
        """
        Parse a markdown file and extract headings as symbols.

        Headings become navigable symbols:
        - H1 (#) -> document symbol
        - H2 (##) -> section symbol
        - H3 (###) -> subsection symbol

        Args:
            file_path: Path to markdown file (absolute or relative to project)

        Returns:
            List of extracted Symbol objects
        """
        import re

        # Normalize path
        if not file_path.is_absolute():
            abs_path = self.project_dir / file_path
        else:
            abs_path = file_path
            file_path = abs_path.relative_to(self.project_dir)

        if not abs_path.exists() or abs_path.suffix not in ('.md', '.markdown'):
            return []

        try:
            content = abs_path.read_text(encoding='utf-8', errors='ignore')

            # Skip very large files
            if len(content) > 500000:  # 500KB limit for markdown
                return []
        except (IOError, UnicodeDecodeError):
            return []

        symbols = []
        git_hash = self._get_git_hash() or ""

        # Build qualified name prefix from file path
        # manual/link.md -> manual.link
        parts = list(file_path.with_suffix('').parts)
        doc_name = '.'.join(parts)

        lines = content.split('\n')
        current_h1 = None
        current_h2 = None

        # Regex for markdown headings (not in code blocks)
        heading_pattern = re.compile(r'^(#{1,3})\s+(.+)$')

        in_code_block = False
        for line_num, line in enumerate(lines, start=1):
            # Track code blocks to skip headings inside them
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            match = heading_pattern.match(line)
            if not match:
                continue

            level = len(match.group(1))
            heading_text = match.group(2).strip()

            # Clean heading text (remove trailing # if any)
            heading_text = heading_text.rstrip('#').strip()

            # Determine symbol type and build qualified name
            if level == 1:
                symbol_type = "document"
                current_h1 = heading_text
                current_h2 = None
                qualified_name = f"{doc_name}.{self._heading_to_id(heading_text)}"
            elif level == 2:
                symbol_type = "section"
                current_h2 = heading_text
                parent = current_h1 or doc_name
                qualified_name = f"{doc_name}.{self._heading_to_id(heading_text)}"
            elif level == 3:
                symbol_type = "subsection"
                qualified_name = f"{doc_name}.{self._heading_to_id(heading_text)}"
            else:
                continue  # Skip H4+ for now

            # Find the end line (next heading of same or higher level, or EOF)
            end_line = len(lines)
            for i, next_line in enumerate(lines[line_num:], start=line_num + 1):
                next_match = heading_pattern.match(next_line)
                if next_match and len(next_match.group(1)) <= level:
                    end_line = i - 1
                    break

            # Extract first paragraph as docstring
            docstring = ""
            for i in range(line_num, min(line_num + 5, len(lines))):
                next_line = lines[i].strip()
                if next_line and not next_line.startswith('#') and not next_line.startswith('```'):
                    docstring = next_line[:200]
                    break

            symbols.append(Symbol(
                symbol_type=symbol_type,
                name=heading_text,
                qualified_name=qualified_name,
                file_path=str(file_path),
                line_start=line_num,
                line_end=end_line,
                signature=f"{'#' * level} {heading_text}",
                docstring=docstring,
                visibility="public",
                git_hash=git_hash
            ))

        return symbols

    def _heading_to_id(self, heading: str) -> str:
        """Convert heading text to a valid identifier."""
        import re
        # Extract section marker if present (e.g., [LNK-06] -> LNK-06)
        marker_match = re.search(r'\[([A-Z]+-\d+)\]', heading)
        if marker_match:
            return marker_match.group(1)

        # Otherwise, create slug from heading
        # Remove special chars, replace spaces with underscores
        slug = re.sub(r'[^\w\s-]', '', heading.lower())
        slug = re.sub(r'[\s-]+', '_', slug)
        return slug[:50]  # Limit length

    def _extract_class(
        self,
        node: ast.ClassDef,
        module_name: str,
        file_path: str,
        git_hash: str
    ) -> Symbol:
        """Extract a class definition."""
        # Build signature with bases
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}" if isinstance(base.value, ast.Name) else base.attr)

        bases_str = f"({', '.join(bases)})" if bases else ""
        signature = f"class {node.name}{bases_str}"

        # Docstring
        docstring = ast.get_docstring(node) or ""
        if docstring:
            docstring = docstring.split('\n')[0][:200]

        # Visibility
        visibility = "private" if node.name.startswith('_') else "public"

        return Symbol(
            symbol_type="class",
            name=node.name,
            qualified_name=f"{module_name}.{node.name}",
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring,
            visibility=visibility,
            git_hash=git_hash
        )

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        module_name: str,
        file_path: str,
        git_hash: str,
        is_method: bool = False
    ) -> Symbol:
        """Extract a function or method definition."""
        # Build signature with parameters
        params = []
        for arg in node.args.args:
            params.append(arg.arg)

        # Add *args, **kwargs
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        signature = f"{async_prefix}def {node.name}({', '.join(params)})"

        # Return annotation
        if node.returns:
            if isinstance(node.returns, ast.Name):
                signature += f" -> {node.returns.id}"
            elif isinstance(node.returns, ast.Constant):
                signature += f" -> {node.returns.value}"

        # Docstring
        docstring = ast.get_docstring(node) or ""
        if docstring:
            docstring = docstring.split('\n')[0][:200]

        # Visibility
        visibility = "private" if node.name.startswith('_') else "public"

        return Symbol(
            symbol_type="method" if is_method else "function",
            name=node.name,
            qualified_name=f"{module_name}.{node.name}",
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring,
            visibility=visibility,
            git_hash=git_hash
        )

    # =========================================================================
    # Indexing
    # =========================================================================

    def index_file(self, file_path: Path, emit_events: bool = True) -> List[Symbol]:
        """
        Index a single file and optionally emit events.

        Dispatches to appropriate parser based on file extension:
        - .py files -> parse_file() (AST-based Python parsing)
        - .md files -> parse_markdown_file() (heading extraction)

        Args:
            file_path: Path to file (Python or Markdown)
            emit_events: Whether to emit SYMBOL_INDEXED events

        Returns:
            List of indexed symbols
        """
        # Normalize path for extension check
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        # Dispatch based on extension
        ext = file_path.suffix.lower()
        if ext == '.py':
            symbols = self.parse_file(file_path)
        elif ext in ('.md', '.markdown'):
            symbols = self.parse_markdown_file(file_path)
        else:
            return []  # Unsupported file type

        if emit_events:
            for sym in symbols:
                event = index_symbol(
                    symbol_type=sym.symbol_type,
                    name=sym.name,
                    qualified_name=sym.qualified_name,
                    file_path=sym.file_path,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    signature=sym.signature,
                    docstring=sym.docstring,
                    visibility=sym.visibility,
                    git_hash=sym.git_hash
                )
                self.events.append(event)
                sym.event_id = event.id

                # Project into graph
                self.graph._project_event(event, auto_commit=True)

                # Update cache
                self._cache[sym.qualified_name] = sym

        return symbols

    def index_project(
        self,
        patterns: List[str] = None,
        exclude: List[str] = None
    ) -> Tuple[int, int]:
        """
        Index all Python files in the project.

        Args:
            patterns: Glob patterns to include (default: ["**/*.py"])
            exclude: Patterns to exclude (default: ["**/test_*", "**/__pycache__/*"])

        Returns:
            Tuple of (files_indexed, symbols_indexed)
        """
        patterns = patterns or ["**/*.py"]
        exclude = exclude or ["**/test_*", "**/__pycache__/*", "**/.*"]

        files_indexed = 0
        symbols_indexed = 0

        for pattern in patterns:
            for file_path in self.project_dir.glob(pattern):
                # Skip excluded patterns
                rel_path = file_path.relative_to(self.project_dir)
                if any(rel_path.match(ex) for ex in exclude):
                    continue

                symbols = self.index_file(rel_path)
                if symbols:
                    files_indexed += 1
                    symbols_indexed += len(symbols)

        self._save_cache()
        return files_indexed, symbols_indexed

    def get_changed_files(self, since_hash: str = None) -> List[Path]:
        """
        Get Python files changed since a commit.

        Args:
            since_hash: Commit hash to compare from (default: use cached hash)

        Returns:
            List of changed file paths
        """
        # Get cached hash if not provided
        if since_hash is None:
            cache_data = {}
            if self._cache_path.exists():
                try:
                    cache_data = json.loads(self._cache_path.read_text())
                except json.JSONDecodeError:
                    pass
            since_hash = cache_data.get('git_hash')

        if not since_hash:
            return []  # No baseline, need full index

        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', since_hash, 'HEAD', '--', '*.py'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return [Path(f) for f in result.stdout.strip().split('\n') if f]
        except Exception:
            pass

        return []

    def index_changed_files(self) -> Tuple[int, int]:
        """
        Incrementally index only changed files.

        Returns:
            Tuple of (files_indexed, symbols_indexed)
        """
        changed = self.get_changed_files()

        if not changed:
            return 0, 0

        files_indexed = 0
        symbols_indexed = 0

        for file_path in changed:
            # Remove old symbols for this file from cache
            to_remove = [qn for qn, sym in self._cache.items() if sym.file_path == str(file_path)]
            for qn in to_remove:
                del self._cache[qn]

            # Re-index if file still exists
            full_path = self.project_dir / file_path
            if full_path.exists():
                symbols = self.index_file(file_path)
                if symbols:
                    files_indexed += 1
                    symbols_indexed += len(symbols)

        self._save_cache()
        return files_indexed, symbols_indexed

    # =========================================================================
    # Querying
    # =========================================================================

    def query(self, name: str, symbol_type: str = None) -> List[Symbol]:
        """
        Query symbols by name.

        Args:
            name: Symbol name (simple or qualified)
            symbol_type: Optional filter by type

        Returns:
            List of matching symbols
        """
        results = []
        name_lower = name.lower()

        for sym in self._cache.values():
            # Match simple name or qualified name
            if sym.name.lower() == name_lower or sym.qualified_name.lower().endswith(name_lower):
                if symbol_type is None or sym.symbol_type == symbol_type:
                    results.append(sym)

        # Also search graph for more complete results
        code_symbols = self.graph.get_nodes_by_type("code_symbol")
        for node in code_symbols:
            content = node.content
            node_name = content.get('name', '').lower()
            node_qname = content.get('qualified_name', '').lower()

            if node_name == name_lower or node_qname.endswith(name_lower):
                if symbol_type is None or content.get('symbol_type') == symbol_type:
                    # Check if already in results
                    qname = content.get('qualified_name')
                    if not any(s.qualified_name == qname for s in results):
                        results.append(Symbol(
                            symbol_type=content.get('symbol_type', ''),
                            name=content.get('name', ''),
                            qualified_name=qname,
                            file_path=content.get('file_path', ''),
                            line_start=content.get('line_start', 0),
                            line_end=content.get('line_end', 0),
                            signature=content.get('signature', ''),
                            docstring=content.get('docstring', ''),
                            visibility=content.get('visibility', 'public'),
                            git_hash=content.get('git_hash', ''),
                            event_id=node.event_id
                        ))

        return results

    def get_symbol(self, qualified_name: str) -> Optional[Symbol]:
        """Get symbol by exact qualified name."""
        return self._cache.get(qualified_name)

    def get_symbols_in_file(self, file_path: str) -> List[Symbol]:
        """Get all symbols in a file."""
        return [sym for sym in self._cache.values() if sym.file_path == file_path]

    def stats(self) -> Dict[str, int]:
        """Return index statistics."""
        by_type = {}
        for sym in self._cache.values():
            by_type[sym.symbol_type] = by_type.get(sym.symbol_type, 0) + 1

        return {
            'total': len(self._cache),
            # Code symbols
            'classes': by_type.get('class', 0),
            'functions': by_type.get('function', 0),
            'methods': by_type.get('method', 0),
            # Documentation symbols
            'documents': by_type.get('document', 0),
            'sections': by_type.get('section', 0),
            'subsections': by_type.get('subsection', 0),
            'files': len(set(sym.file_path for sym in self._cache.values()))
        }
