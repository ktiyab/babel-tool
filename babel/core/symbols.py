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
import fnmatch
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union, Set

from .events import DualEventStore, index_symbol
from .tokenizer import tokenize_name, tokenize_text, token_match_score


@dataclass
class Symbol:
    """A code symbol extracted via AST parsing or tree-sitter."""
    symbol_type: str        # "class" | "function" | "method" | "module" | "interface" | "type" | "enum"
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

        # Token index for O(1) lookup (token -> set of qualified_names)
        self._token_index: Dict[str, set] = {}
        self._build_token_index()

        # Initialize parser registry with default language configs
        self._registry = self._create_default_registry()
        self._extractor = self._create_extractor()

    def _create_default_registry(self) -> 'ParserRegistry':
        """Create parser registry with default language configs."""
        from .parsing import ParserRegistry
        from .parsing.languages import (
            PYTHON_CONFIG,
            JAVASCRIPT_CONFIG,
            TYPESCRIPT_CONFIG,
            HTML_CONFIG,
            CSS_CONFIG,
        )

        registry = ParserRegistry()
        registry.register(PYTHON_CONFIG)
        registry.register(JAVASCRIPT_CONFIG)
        registry.register(TYPESCRIPT_CONFIG)
        registry.register(HTML_CONFIG)
        registry.register(CSS_CONFIG)
        # Note: Markdown uses built-in regex parser, not tree-sitter
        return registry

    def _create_extractor(self) -> Optional['TreeSitterExtractor']:
        """Create tree-sitter extractor if available."""
        try:
            from .parsing import TreeSitterExtractor
            extractor = TreeSitterExtractor(self._registry)
            if extractor.is_available():
                return extractor
        except ImportError:
            pass
        return None

    @property
    def registry(self) -> 'ParserRegistry':
        """Access the parser registry for configuration."""
        return self._registry

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

    def _build_token_index(self):
        """
        Build inverted token index from cached symbols.

        Maps each token to the set of qualified names containing that token.
        Enables O(1) candidate lookup for token-based queries.
        """
        self._token_index = {}
        for qname, sym in self._cache.items():
            self._index_symbol_tokens(sym)

    def _index_symbol_tokens(self, sym: Symbol):
        """
        Add a symbol's tokens to the token index.

        Indexes both the simple name and qualified name.
        """
        # Tokenize symbol name
        name_tokens = tokenize_name(sym.name)
        qname_tokens = tokenize_name(sym.qualified_name)
        all_tokens = set(name_tokens) | set(qname_tokens)

        for token in all_tokens:
            if token not in self._token_index:
                self._token_index[token] = set()
            self._token_index[token].add(sym.qualified_name)

    def _remove_symbol_from_index(self, sym: Symbol):
        """Remove a symbol's tokens from the index."""
        name_tokens = tokenize_name(sym.name)
        qname_tokens = tokenize_name(sym.qualified_name)
        all_tokens = set(name_tokens) | set(qname_tokens)

        for token in all_tokens:
            if token in self._token_index:
                self._token_index[token].discard(sym.qualified_name)

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
            sym = self._cache[qn]
            self._remove_symbol_from_index(sym)
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

    def _find_git_root(self, start_path: Path) -> Optional[Path]:
        """
        Find the git repository root for a given path.

        Args:
            start_path: Starting directory to search from

        Returns:
            Path to git root, or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=start_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            pass
        return None

    def _get_tracked_files(self, extensions: set, base_dir: Path = None) -> Optional[List[Path]]:
        """
        Get files tracked by git, respecting .gitignore.

        Uses git ls-files to get:
        - Tracked files (--cached)
        - Untracked but not ignored (--others --exclude-standard)

        Args:
            extensions: Set of file extensions to filter (e.g., {'.py', '.ts'})
            base_dir: Directory to run git ls-files from (default: project_dir)

        Returns:
            List of file paths, or None if git not available (use fallback)
        """
        cwd = base_dir if base_dir else self.project_dir
        try:
            result = subprocess.run(
                ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                files = []
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    path = Path(line)
                    if path.suffix.lower() in extensions:
                        files.append(path)
                return files
        except Exception:
            pass
        return None  # Fall back to glob + exclusions

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
            # Try to get relative path, fallback to external handling
            try:
                file_path = abs_path.relative_to(self.project_dir)
            except ValueError:
                # File is outside project - use git repo name as prefix
                git_root = self._find_git_root(abs_path.parent)
                if git_root:
                    file_path = abs_path.relative_to(git_root)
                else:
                    # Last resort: use just the filename
                    file_path = Path(abs_path.name)

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
            # Try to get relative path, fallback to external handling
            try:
                file_path = abs_path.relative_to(self.project_dir)
            except ValueError:
                # File is outside project - use git repo name as prefix
                git_root = self._find_git_root(abs_path.parent)
                if git_root:
                    file_path = abs_path.relative_to(git_root)
                else:
                    # Last resort: use just the filename
                    file_path = Path(abs_path.name)

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
        # .babel/manual/link.md -> manual.link
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
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
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

        Uses tree-sitter extractor when available, falls back to built-in parsers.
        Supports: Python, JavaScript, TypeScript, HTML, CSS, Markdown.

        Args:
            file_path: Path to file
            emit_events: Whether to emit SYMBOL_INDEXED events

        Returns:
            List of indexed symbols
        """
        # Normalize path for extension check
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        ext = file_path.suffix.lower()
        symbols = []
        git_hash = self._get_git_hash() or ""

        # Try tree-sitter extractor first (supports all registered languages)
        if self._extractor and self._registry.is_supported(file_path):
            # Read file content
            abs_path = file_path if file_path.is_absolute() else self.project_dir / file_path
            if abs_path.exists():
                try:
                    content = abs_path.read_text(encoding='utf-8', errors='ignore')
                    # Try to get relative path, fallback to absolute if outside project
                    if file_path.is_absolute():
                        try:
                            rel_path = file_path.relative_to(self.project_dir)
                        except ValueError:
                            # File is outside project - use git repo name as prefix
                            git_root = self._find_git_root(file_path.parent)
                            if git_root:
                                rel_path = file_path.relative_to(git_root)
                            else:
                                rel_path = file_path
                    else:
                        rel_path = file_path
                    symbols = self._extractor.extract(rel_path, content, git_hash)
                except Exception:
                    symbols = []

        # Fallback to built-in parsers
        if not symbols:
            if ext == '.py':
                symbols = self.parse_file(file_path)
            elif ext in ('.md', '.markdown'):
                symbols = self.parse_markdown_file(file_path)
            # Note: JS/TS only supported via tree-sitter, no fallback

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

                # Update cache and token index
                self._cache[sym.qualified_name] = sym
                self._index_symbol_tokens(sym)

        return symbols

    def _resolve_pattern_base(self, pattern: str) -> Tuple[Path, str]:
        """
        Extract the base directory and remaining pattern from a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "../babel-dashboard/**/*.py")

        Returns:
            Tuple of (base_dir, relative_pattern)
        """
        # Split pattern at first wildcard
        parts = pattern.split('*', 1)
        base_str = parts[0].rstrip('/')

        if not base_str:
            return self.project_dir, pattern

        # Resolve base path - use CWD for relative paths (patterns come from command line)
        base_path = Path(base_str)
        if not base_path.is_absolute():
            # Relative patterns are relative to CWD, not project_dir
            base_path = Path.cwd() / base_path

        # Find the actual directory (go up until we find an existing dir)
        while not base_path.exists() and base_path != base_path.parent:
            base_path = base_path.parent

        if base_path.is_file():
            base_path = base_path.parent

        # Calculate remaining pattern relative to base
        if len(parts) > 1:
            rel_pattern = '*' + parts[1]
        else:
            rel_pattern = '**/*'

        return base_path.resolve(), rel_pattern

    def index_project(
        self,
        patterns: List[str] = None,
        exclude: List[str] = None,
        respect_gitignore: bool = True
    ) -> Tuple[int, int]:
        """
        Index files in the project.

        Supports all registered languages (Python, JavaScript, TypeScript, Markdown).
        Respects .gitignore by default using git ls-files.
        Handles patterns pointing to external git repositories.

        Args:
            patterns: Glob patterns to include (default: uses registry patterns)
            exclude: Patterns to exclude (default: uses registry exclusions)
            respect_gitignore: Use git ls-files to respect .gitignore (default: True)

        Returns:
            Tuple of (files_indexed, symbols_indexed)
        """
        files_indexed = 0
        symbols_indexed = 0

        # Build set of extensions to index
        extensions = set(self._registry.supported_extensions())
        extensions.update({'.md', '.markdown'})  # Always include markdown

        if patterns:
            # Process each pattern - may point to different git repos
            for pattern in patterns:
                base_dir, rel_pattern = self._resolve_pattern_base(pattern)

                # Get tracked files from the pattern's git root
                tracked_files = None
                if respect_gitignore:
                    git_root = self._find_git_root(base_dir)
                    if git_root:
                        tracked_files = self._get_tracked_files(extensions, git_root)

                if tracked_files is not None:
                    # Files are relative to git_root - convert to absolute and filter by pattern
                    for file_path in tracked_files:
                        abs_path = git_root / file_path
                        # Check if file is within our base_dir
                        try:
                            abs_path.relative_to(base_dir)
                        except ValueError:
                            continue  # File not under base_dir

                        # Check extension
                        if abs_path.suffix.lower() not in extensions:
                            continue

                        # Check pattern match
                        if not abs_path.match(rel_pattern) and not fnmatch.fnmatch(abs_path.name, rel_pattern):
                            # Try matching against the original pattern
                            rel_to_project = abs_path.relative_to(self.project_dir.parent) if abs_path.is_relative_to(self.project_dir.parent) else abs_path
                            if not fnmatch.fnmatch(str(rel_to_project), pattern.lstrip('./')):
                                continue

                        symbols = self.index_file(abs_path)
                        if symbols:
                            files_indexed += 1
                            symbols_indexed += len(symbols)
                else:
                    # Fallback: glob from base_dir
                    for file_path in base_dir.glob(rel_pattern):
                        if file_path.suffix.lower() not in extensions:
                            continue
                        if exclude and any(file_path.match(ex) for ex in exclude):
                            continue
                        symbols = self.index_file(file_path)
                        if symbols:
                            files_indexed += 1
                            symbols_indexed += len(symbols)
        else:
            # Fallback: glob + exclusion patterns (no git or git failed)
            if patterns is None:
                patterns = self._registry.glob_patterns_for_indexing()
                patterns.append("**/*.md")

            if exclude is None:
                exclude = self._registry.all_exclude_patterns()
                exclude.extend(["**/.*"])

            for pattern in patterns:
                for file_path in self.project_dir.glob(pattern):
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
        Get supported files changed since a commit.

        Includes all file types registered in the parser registry.

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

        # Build file patterns for all supported extensions
        extensions = list(self._registry.supported_extensions())
        extensions.append('.md')  # Always include markdown
        file_patterns = [f'*{ext}' for ext in extensions]

        try:
            cmd = ['git', 'diff', '--name-only', since_hash, 'HEAD', '--'] + file_patterns
            result = subprocess.run(
                cmd,
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
            # Remove old symbols for this file from cache and token index
            to_remove = [qn for qn, sym in self._cache.items() if sym.file_path == str(file_path)]
            for qn in to_remove:
                sym = self._cache[qn]
                self._remove_symbol_from_index(sym)
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
        Query symbols by name using token-based matching.

        Supports cross-convention matching:
        - "user profile" matches UserProfile, user_profile, user-profile
        - Exact matches scored highest, token matches next

        Uses token index for O(1) candidate lookup when available.

        Args:
            name: Symbol name, query string, or keywords
            symbol_type: Optional filter by type

        Returns:
            List of matching symbols, sorted by relevance
        """
        scored_results: List[Tuple[float, Symbol]] = []
        seen_qnames = set()
        name_lower = name.lower()
        query_tokens = tokenize_text(name)

        # Get candidates from token index (O(1) per token)
        candidate_qnames = self._get_candidates_from_index(query_tokens)

        # Search cache - use candidates if available, else full scan
        symbols_to_check = (
            (self._cache[qn] for qn in candidate_qnames if qn in self._cache)
            if candidate_qnames
            else self._cache.values()
        )

        for sym in symbols_to_check:
            if symbol_type is not None and sym.symbol_type != symbol_type:
                continue

            score = self._score_symbol_match(sym.name, sym.qualified_name, name_lower, query_tokens)
            if score > 0:
                scored_results.append((score, sym))
                seen_qnames.add(sym.qualified_name)

        # Also search graph for more complete results
        code_symbols = self.graph.get_nodes_by_type("code_symbol")
        for node in code_symbols:
            content = node.content
            qname = content.get('qualified_name', '')

            if qname in seen_qnames:
                continue

            if symbol_type is not None and content.get('symbol_type') != symbol_type:
                continue

            node_name = content.get('name', '')
            score = self._score_symbol_match(node_name, qname, name_lower, query_tokens)

            if score > 0:
                seen_qnames.add(qname)
                sym = Symbol(
                    symbol_type=content.get('symbol_type', ''),
                    name=node_name,
                    qualified_name=qname,
                    file_path=content.get('file_path', ''),
                    line_start=content.get('line_start', 0),
                    line_end=content.get('line_end', 0),
                    signature=content.get('signature', ''),
                    docstring=content.get('docstring', ''),
                    visibility=content.get('visibility', 'public'),
                    git_hash=content.get('git_hash', ''),
                    event_id=node.event_id
                )
                scored_results.append((score, sym))

        # Sort by score descending, return symbols only
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [sym for _, sym in scored_results]

    def _get_candidates_from_index(self, query_tokens: set) -> Optional[set]:
        """
        Get candidate qualified names from the token index.

        Returns the union of all symbols containing ANY query token.
        Returns None if index is empty (fall back to full scan).

        Args:
            query_tokens: Set of tokens from the query

        Returns:
            Set of qualified names, or None if no index
        """
        if not self._token_index or not query_tokens:
            return None

        candidates = set()
        for token in query_tokens:
            if token in self._token_index:
                candidates |= self._token_index[token]

        return candidates if candidates else None

    def _score_symbol_match(
        self,
        name: str,
        qualified_name: str,
        query_lower: str,
        query_tokens: set
    ) -> float:
        """
        Score how well a symbol matches a query.

        Scoring:
        - Exact name match: 10.0 (highest priority)
        - Qualified name ends with query: 8.0
        - Token-based match: 1.0 per matching token + 0.5 for partials

        Args:
            name: Symbol's simple name
            qualified_name: Symbol's qualified name
            query_lower: Lowercased query string
            query_tokens: Tokenized query

        Returns:
            Match score (0 = no match)
        """
        name_lower = name.lower()
        qname_lower = qualified_name.lower()

        # Exact match on simple name - highest priority
        if name_lower == query_lower:
            return 10.0

        # Qualified name ends with query
        if qname_lower.endswith(query_lower):
            return 8.0

        # Token-based matching
        if query_tokens:
            score = token_match_score(query_tokens, name)
            # Also check qualified name for path-based tokens
            qname_score = token_match_score(query_tokens, qualified_name)
            score = max(score, qname_score * 0.8)  # Slight penalty for qname-only match

            if score > 0:
                return score

        return 0.0

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
            # Code symbols (all languages)
            'classes': by_type.get('class', 0),
            'functions': by_type.get('function', 0),
            'methods': by_type.get('method', 0),
            # TypeScript-specific symbols
            'interfaces': by_type.get('interface', 0),
            'types': by_type.get('type', 0),
            'enums': by_type.get('enum', 0),
            # HTML symbols
            'containers': by_type.get('container', 0),
            # CSS symbols
            'ids': by_type.get('id', 0),
            'variables': by_type.get('variable', 0),
            'animations': by_type.get('animation', 0),
            # Documentation symbols
            'documents': by_type.get('document', 0),
            'sections': by_type.get('section', 0),
            'subsections': by_type.get('subsection', 0),
            # File count
            'files': len(set(sym.file_path for sym in self._cache.values())),
            # Token index stats
            'unique_tokens': len(self._token_index),
        }
