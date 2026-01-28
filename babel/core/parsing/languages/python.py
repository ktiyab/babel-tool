"""
Python language configuration for symbol extraction.

Defines PYTHON_CONFIG with tree-sitter queries and custom hooks
that replicate the behavior of CodeSymbolStore.parse_file().

Symbol types extracted:
- class: Class definitions
- function: Module-level functions
- method: Functions inside classes
"""

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from ..config import LanguageConfig, SymbolQuery

if TYPE_CHECKING:
    from tree_sitter import Node


# =============================================================================
# Symbol Queries
# =============================================================================

PYTHON_QUERIES = [
    # Class definitions: class Foo:
    SymbolQuery(
        node_type="class_definition",
        symbol_type="class",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Function definitions: def foo():
    SymbolQuery(
        node_type="function_definition",
        symbol_type="function",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
]


# =============================================================================
# Custom Hooks
# =============================================================================

def python_qualified_name_builder(
    file_path: Path,
    name: str,
    parent_symbol: Optional[str]
) -> str:
    """
    Build Python-style qualified name.

    Examples:
        babel/core/cache.py + CacheManager -> babel.core.cache.CacheManager
        babel/core/cache.py + get + babel.core.cache.CacheManager -> babel.core.cache.CacheManager.get
    """
    # Convert path to module notation
    module = str(file_path.with_suffix('')).replace('/', '.').replace('\\', '.')

    if parent_symbol:
        return f"{parent_symbol}.{name}"
    return f"{module}.{name}"


def python_docstring_extractor(node: 'Node', content: str) -> str:
    """
    Extract Python docstring from AST node.

    Looks for triple-quoted string as first statement in function/class body.
    Returns first line of docstring, truncated to 200 chars.
    """
    # Find the 'body' or 'block' child
    body = None
    for child in node.children:
        if child.type == 'block':
            body = child
            break

    if not body or not body.children:
        return ""

    # First child in block might be expression_statement containing string
    first_stmt = body.children[0]

    # Skip if it's a pass, comment, etc.
    if first_stmt.type != 'expression_statement':
        return ""

    # Check if the expression is a string
    if first_stmt.children:
        expr = first_stmt.children[0]
        if expr.type == 'string':
            text = content[expr.start_byte:expr.end_byte]
            # Clean up triple quotes
            text = text.strip()
            for quote in ('"""', "'''", '"', "'"):
                if text.startswith(quote):
                    text = text[len(quote):]
                if text.endswith(quote):
                    text = text[:-len(quote)]
            # Return first line
            first_line = text.strip().split('\n')[0]
            return first_line[:200]

    return ""


def python_visibility_detector(node: 'Node', name: str, content: str) -> str:
    """
    Determine Python symbol visibility.

    Convention: underscore prefix = private
    """
    return "private" if name.startswith('_') else "public"


def python_signature_extractor(node: 'Node', content: str) -> str:
    """
    Extract Python function/class signature.

    For functions: def foo(arg1, arg2, *args, **kwargs) -> ReturnType
    For classes: class Foo(Base1, Base2)
    """
    if node.type == 'class_definition':
        return _extract_class_signature(node, content)
    elif node.type == 'function_definition':
        return _extract_function_signature(node, content)
    else:
        # Fallback: first line
        text = content[node.start_byte:node.end_byte]
        return text.split('\n')[0].strip()[:200]


def _extract_class_signature(node: 'Node', content: str) -> str:
    """Extract class signature with bases."""
    name = None
    bases = []

    for child in node.children:
        if child.type == 'identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'argument_list':
            # Base classes
            for arg in child.children:
                if arg.type == 'identifier':
                    bases.append(content[arg.start_byte:arg.end_byte])
                elif arg.type == 'attribute':
                    bases.append(content[arg.start_byte:arg.end_byte])

    if not name:
        return ""

    bases_str = f"({', '.join(bases)})" if bases else ""
    return f"class {name}{bases_str}"


def _extract_function_signature(node: 'Node', content: str) -> str:
    """Extract function signature with parameters and return type."""
    name = None
    params = []
    return_type = None
    is_async = False

    for child in node.children:
        if child.type == 'identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'parameters':
            params = _extract_parameters(child, content)
        elif child.type == 'type':
            return_type = content[child.start_byte:child.end_byte]

    # Check for async
    first_text = content[node.start_byte:node.start_byte + 10]
    if first_text.strip().startswith('async'):
        is_async = True

    if not name:
        return ""

    async_prefix = "async " if is_async else ""
    signature = f"{async_prefix}def {name}({', '.join(params)})"

    if return_type:
        signature += f" -> {return_type}"

    return signature[:200]


def _extract_parameters(params_node: 'Node', content: str) -> list:
    """Extract parameter names from parameters node."""
    params = []

    for child in params_node.children:
        if child.type == 'identifier':
            params.append(content[child.start_byte:child.end_byte])
        elif child.type in ('typed_parameter', 'default_parameter', 'typed_default_parameter'):
            # Get the identifier inside
            for sub in child.children:
                if sub.type == 'identifier':
                    params.append(content[sub.start_byte:sub.end_byte])
                    break
        elif child.type == 'list_splat_pattern':
            # *args
            for sub in child.children:
                if sub.type == 'identifier':
                    params.append(f"*{content[sub.start_byte:sub.end_byte]}")
                    break
        elif child.type == 'dictionary_splat_pattern':
            # **kwargs
            for sub in child.children:
                if sub.type == 'identifier':
                    params.append(f"**{content[sub.start_byte:sub.end_byte]}")
                    break

    return params


# =============================================================================
# Configuration
# =============================================================================

def _get_python_exclude_patterns() -> list:
    """Get exclude patterns from central configuration."""
    from ..exclusions import ExclusionConfig
    return ExclusionConfig.get_patterns('python')


PYTHON_CONFIG = LanguageConfig(
    name="Python",
    tree_sitter_name="python",
    extensions={'.py'},
    symbol_queries=PYTHON_QUERIES,
    max_file_size=200_000,  # 200KB, matching original limit
    exclude_patterns=_get_python_exclude_patterns(),
    qualified_name_builder=python_qualified_name_builder,
    docstring_extractor=python_docstring_extractor,
    visibility_detector=python_visibility_detector,
)
