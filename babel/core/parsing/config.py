"""
Parsing configuration data structures.

Defines LanguageConfig and SymbolQuery — the foundation for
language-agnostic symbol extraction via tree-sitter.

Design principle: New languages are added via config, not code changes.
"""

from dataclasses import dataclass, field
from typing import Set, List, Callable, Optional, Any


@dataclass
class SymbolQuery:
    """
    Defines what AST nodes to extract as symbols.

    Maps tree-sitter node types to Babel symbol types.
    Each query specifies how to extract one kind of symbol.

    Attributes:
        node_type: Tree-sitter AST node type (e.g., "function_definition")
        symbol_type: Babel symbol type (e.g., "function", "class", "interface")
        name_field: AST field containing the symbol name (default: "name")
        capture_signature: Whether to extract full signature
        capture_docstring: Whether to extract docstring/JSDoc
    """
    node_type: str
    symbol_type: str
    name_field: str = "name"
    capture_signature: bool = True
    capture_docstring: bool = True


@dataclass
class LanguageConfig:
    """
    Configuration for parsing a specific programming language.

    Encapsulates all language-specific rules:
    - File extensions to match
    - Tree-sitter grammar name
    - Symbol extraction queries
    - Exclusion patterns
    - Custom hooks for naming, docstrings, visibility

    Attributes:
        name: Human-readable name (e.g., "Python", "TypeScript")
        tree_sitter_name: Grammar name for tree-sitter (e.g., "python", "typescript")
        extensions: File extensions this config handles (e.g., {'.py'})
        symbol_queries: List of SymbolQuery defining what to extract
        max_file_size: Skip files larger than this (bytes, default 300KB)
        exclude_patterns: Glob patterns to exclude (e.g., ['**/node_modules/*'])
        qualified_name_builder: Custom function to build qualified names
        docstring_extractor: Custom function to extract docstrings
        visibility_detector: Custom function to determine public/private
        post_processor: Custom function for final symbol transforms
    """
    # Identity
    name: str
    tree_sitter_name: str
    extensions: Set[str]

    # Extraction rules
    symbol_queries: List[SymbolQuery] = field(default_factory=list)
    max_file_size: int = 300_000  # 300KB default

    # Exclusions
    exclude_patterns: List[str] = field(default_factory=list)

    # Customization hooks (optional)
    name_extractor: Optional[Callable[..., Optional[str]]] = None  # Custom name extraction from node
    qualified_name_builder: Optional[Callable[..., str]] = None
    docstring_extractor: Optional[Callable[..., str]] = None
    visibility_detector: Optional[Callable[..., str]] = None
    signature_extractor: Optional[Callable[..., str]] = None  # Custom signature extraction
    post_processor: Optional[Callable[..., List[Any]]] = None

    def matches_extension(self, ext: str) -> bool:
        """Check if this config handles the given extension."""
        return ext.lower() in self.extensions

    def should_exclude(self, rel_path: str) -> bool:
        """Check if a relative path should be excluded."""
        from pathlib import Path
        path = Path(rel_path)
        return any(path.match(pattern) for pattern in self.exclude_patterns)
