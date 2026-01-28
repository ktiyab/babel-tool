"""
TypeScript language configuration for symbol extraction.

Defines TYPESCRIPT_CONFIG with tree-sitter queries for TypeScript files (.ts, .tsx).
Extends JavaScript queries with TypeScript-specific types.

Symbol types extracted:
- class: Class declarations
- function: Function declarations and arrow functions
- method: Functions inside classes
- interface: Interface declarations
- type: Type alias declarations
- enum: Enum declarations
"""

from pathlib import Path
from typing import List, TYPE_CHECKING

from ..config import LanguageConfig, SymbolQuery
from .javascript import (
    JAVASCRIPT_QUERIES,
    javascript_qualified_name_builder,
    javascript_docstring_extractor,
    javascript_visibility_detector,
)

if TYPE_CHECKING:
    from tree_sitter import Node


# =============================================================================
# TypeScript-Specific Symbol Queries
# =============================================================================

TYPESCRIPT_SPECIFIC_QUERIES = [
    # Interface declarations: interface Foo {}
    SymbolQuery(
        node_type="interface_declaration",
        symbol_type="interface",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Type alias declarations: type Foo = ...
    SymbolQuery(
        node_type="type_alias_declaration",
        symbol_type="type",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Enum declarations: enum Foo {}
    SymbolQuery(
        node_type="enum_declaration",
        symbol_type="enum",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Abstract class declarations
    SymbolQuery(
        node_type="abstract_class_declaration",
        symbol_type="class",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
]

# Combine JavaScript queries with TypeScript-specific ones
TYPESCRIPT_QUERIES = JAVASCRIPT_QUERIES + TYPESCRIPT_SPECIFIC_QUERIES


# =============================================================================
# Custom Hooks (TypeScript-specific overrides)
# =============================================================================

def typescript_signature_extractor(node: 'Node', content: str) -> str:
    """
    Extract TypeScript signature including type annotations.

    Handles interfaces, types, enums in addition to JS patterns.
    """
    if node.type == 'interface_declaration':
        return _extract_interface_signature(node, content)
    elif node.type == 'type_alias_declaration':
        return _extract_type_alias_signature(node, content)
    elif node.type == 'enum_declaration':
        return _extract_enum_signature(node, content)
    elif node.type == 'abstract_class_declaration':
        return _extract_abstract_class_signature(node, content)
    else:
        # Fall back to JavaScript extraction
        from .javascript import javascript_signature_extractor
        return javascript_signature_extractor(node, content)


def _extract_interface_signature(node: 'Node', content: str) -> str:
    """Extract interface signature with extends."""
    name = None
    extends = []

    for child in node.children:
        if child.type == 'type_identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'extends_type_clause':
            # Get extended interfaces
            for sub in child.children:
                if sub.type == 'type_identifier':
                    extends.append(content[sub.start_byte:sub.end_byte])

    if not name:
        return ""

    if extends:
        return f"interface {name} extends {', '.join(extends)}"
    return f"interface {name}"


def _extract_type_alias_signature(node: 'Node', content: str) -> str:
    """Extract type alias signature."""
    name = None
    type_params = []

    for child in node.children:
        if child.type == 'type_identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'type_parameters':
            # Generic type parameters: <T, U>
            type_params_text = content[child.start_byte:child.end_byte]
            type_params = [type_params_text]

    if not name:
        return ""

    if type_params:
        return f"type {name}{type_params[0]} ="
    return f"type {name} ="


def _extract_enum_signature(node: 'Node', content: str) -> str:
    """Extract enum signature."""
    name = None
    is_const = False

    # Check for const enum
    node_text = content[node.start_byte:node.start_byte + 20]
    if 'const' in node_text:
        is_const = True

    for child in node.children:
        if child.type == 'identifier':
            name = content[child.start_byte:child.end_byte]
            break

    if not name:
        return ""

    prefix = "const " if is_const else ""
    return f"{prefix}enum {name}"


def _extract_abstract_class_signature(node: 'Node', content: str) -> str:
    """Extract abstract class signature."""
    name = None
    extends = None
    implements = []

    for child in node.children:
        if child.type == 'type_identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'class_heritage':
            for sub in child.children:
                if sub.type == 'extends_clause':
                    for ext_child in sub.children:
                        if ext_child.type == 'identifier':
                            extends = content[ext_child.start_byte:ext_child.end_byte]
                elif sub.type == 'implements_clause':
                    for impl_child in sub.children:
                        if impl_child.type == 'type_identifier':
                            implements.append(content[impl_child.start_byte:impl_child.end_byte])

    if not name:
        return ""

    sig = f"abstract class {name}"
    if extends:
        sig += f" extends {extends}"
    if implements:
        sig += f" implements {', '.join(implements)}"

    return sig[:200]


def typescript_post_processor(
    symbols: List['Symbol'],
    file_path: Path,
    content: str
) -> List['Symbol']:
    """
    Post-process TypeScript symbols.

    - Filter out non-function variable declarations
    - Handle .d.ts declaration files specially if needed
    """
    from ...symbols import Symbol

    # Check if this is a declaration file
    is_declaration_file = str(file_path).endswith('.d.ts')

    filtered = []
    for sym in symbols:
        # Skip non-function variable declarations
        if sym.signature and 'const' in sym.signature:
            if '=>' not in sym.signature and 'function' not in sym.signature:
                continue

        # For declaration files, all exports are public
        if is_declaration_file:
            sym = Symbol(
                symbol_type=sym.symbol_type,
                name=sym.name,
                qualified_name=sym.qualified_name,
                file_path=sym.file_path,
                line_start=sym.line_start,
                line_end=sym.line_end,
                signature=sym.signature,
                docstring=sym.docstring,
                parent_symbol=sym.parent_symbol,
                visibility="public",
                git_hash=sym.git_hash,
                event_id=sym.event_id,
            )

        filtered.append(sym)

    return filtered


# =============================================================================
# Configuration
# =============================================================================

def _get_typescript_exclude_patterns() -> list:
    """Get exclude patterns from central configuration."""
    from ..exclusions import ExclusionConfig
    return ExclusionConfig.get_patterns('typescript')


TYPESCRIPT_CONFIG = LanguageConfig(
    name="TypeScript",
    tree_sitter_name="typescript",
    extensions={'.ts', '.tsx'},
    symbol_queries=TYPESCRIPT_QUERIES,
    max_file_size=300_000,  # 300KB
    exclude_patterns=_get_typescript_exclude_patterns(),
    qualified_name_builder=javascript_qualified_name_builder,  # Same as JS
    docstring_extractor=javascript_docstring_extractor,  # JSDoc same as JS
    visibility_detector=javascript_visibility_detector,  # Export-based same as JS
    post_processor=typescript_post_processor,
)
