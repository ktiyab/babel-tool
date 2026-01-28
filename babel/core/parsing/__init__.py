"""
Parsing module — Language-agnostic symbol extraction via tree-sitter.

This module provides the foundation for multi-language code indexing:
- LanguageConfig: Per-language parsing rules
- SymbolQuery: AST node to symbol mapping
- ParserRegistry: Extension-based routing

Design principle: Add new languages via config files, not code changes.

Usage:
    from babel.core.parsing import LanguageConfig, SymbolQuery, ParserRegistry

    # Define language config
    config = LanguageConfig(
        name="Go",
        tree_sitter_name="go",
        extensions={'.go'},
        symbol_queries=[
            SymbolQuery(node_type="function_declaration", symbol_type="function"),
        ],
    )

    # Register
    registry = ParserRegistry()
    registry.register(config)

    # Use
    config = registry.get_config(Path("main.go"))
"""

from .config import LanguageConfig, SymbolQuery
from .registry import ParserRegistry
from .extractor import TreeSitterExtractor
from .exclusions import ExclusionConfig

__all__ = [
    'LanguageConfig',
    'SymbolQuery',
    'ParserRegistry',
    'TreeSitterExtractor',
    'ExclusionConfig',
]
