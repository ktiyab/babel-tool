"""
JavaScript language configuration for symbol extraction.

Defines JAVASCRIPT_CONFIG with tree-sitter queries and custom hooks
for extracting symbols from JavaScript files (.js, .jsx).

Symbol types extracted:
- class: Class declarations
- function: Function declarations and arrow functions
- method: Functions inside classes
"""

from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

from ..config import LanguageConfig, SymbolQuery

if TYPE_CHECKING:
    from tree_sitter import Node


# =============================================================================
# Symbol Queries
# =============================================================================

JAVASCRIPT_QUERIES = [
    # Class declarations: class Foo {}
    SymbolQuery(
        node_type="class_declaration",
        symbol_type="class",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Function declarations: function foo() {}
    SymbolQuery(
        node_type="function_declaration",
        symbol_type="function",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Arrow functions and function expressions assigned to const/let/var
    # const foo = () => {} or const foo = function() {}
    SymbolQuery(
        node_type="lexical_declaration",
        symbol_type="function",
        name_field="name",  # Will be extracted from variable_declarator
        capture_signature=True,
        capture_docstring=True,
    ),
    # Variable declarations: var foo = () => {}
    SymbolQuery(
        node_type="variable_declaration",
        symbol_type="function",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Method definitions inside classes
    SymbolQuery(
        node_type="method_definition",
        symbol_type="method",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
    # Generator functions: function* foo() {}
    SymbolQuery(
        node_type="generator_function_declaration",
        symbol_type="function",
        name_field="name",
        capture_signature=True,
        capture_docstring=True,
    ),
]


# =============================================================================
# Custom Hooks
# =============================================================================

def javascript_qualified_name_builder(
    file_path: Path,
    name: str,
    parent_symbol: Optional[str]
) -> str:
    """
    Build JavaScript-style qualified name.

    Examples:
        src/hooks/useAuth.js + useAuth -> src.hooks.useAuth.useAuth
        src/components/Button.jsx + Button -> src.components.Button.Button
    """
    # Convert path to module notation
    module = str(file_path.with_suffix('')).replace('/', '.').replace('\\', '.')

    if parent_symbol:
        return f"{parent_symbol}.{name}"
    return f"{module}.{name}"


def javascript_docstring_extractor(node: 'Node', content: str) -> str:
    """
    Extract JSDoc comment preceding the node.

    Looks for /** ... */ comment immediately before the declaration.
    Returns first line of JSDoc (before @tags), truncated to 200 chars.
    """
    # Look for comment sibling before this node
    if node.prev_named_sibling and node.prev_named_sibling.type == 'comment':
        comment_text = content[node.prev_named_sibling.start_byte:node.prev_named_sibling.end_byte]

        # Check if it's a JSDoc comment
        if comment_text.startswith('/**'):
            # Extract content between /** and */
            text = comment_text[3:]
            if text.endswith('*/'):
                text = text[:-2]

            # Clean up and get first meaningful line
            lines = text.strip().split('\n')
            for line in lines:
                # Remove leading * and whitespace
                line = line.strip().lstrip('*').strip()
                # Skip empty lines and @tags
                if line and not line.startswith('@'):
                    return line[:200]

    return ""


def javascript_visibility_detector(node: 'Node', name: str, content: str) -> str:
    """
    Determine JavaScript symbol visibility.

    - Exported symbols (export keyword) = public
    - Non-exported symbols = private
    - Underscore prefix also indicates private
    """
    if name.startswith('_'):
        return "private"

    # Check if this node or its parent is an export statement
    parent = node.parent
    while parent:
        if parent.type in ('export_statement', 'export_default_declaration'):
            return "public"
        parent = parent.parent

    # Check if node text starts with export
    node_text = content[node.start_byte:min(node.start_byte + 20, node.end_byte)]
    if node_text.strip().startswith('export'):
        return "public"

    return "private"


def javascript_signature_extractor(node: 'Node', content: str) -> str:
    """
    Extract JavaScript function/class signature.

    For functions: function foo(arg1, arg2) or const foo = (arg1) => ...
    For classes: class Foo extends Base
    """
    if node.type == 'class_declaration':
        return _extract_js_class_signature(node, content)
    elif node.type in ('function_declaration', 'generator_function_declaration'):
        return _extract_js_function_signature(node, content)
    elif node.type in ('lexical_declaration', 'variable_declaration'):
        return _extract_js_variable_function_signature(node, content)
    elif node.type == 'method_definition':
        return _extract_js_method_signature(node, content)
    else:
        # Fallback: first line
        text = content[node.start_byte:node.end_byte]
        return text.split('\n')[0].strip()[:200]


def _extract_js_class_signature(node: 'Node', content: str) -> str:
    """Extract class signature with extends."""
    name = None
    extends = None

    for child in node.children:
        if child.type == 'identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'class_heritage':
            # Get the extended class name
            for sub in child.children:
                if sub.type == 'identifier':
                    extends = content[sub.start_byte:sub.end_byte]
                    break

    if not name:
        return ""

    if extends:
        return f"class {name} extends {extends}"
    return f"class {name}"


def _extract_js_function_signature(node: 'Node', content: str) -> str:
    """Extract function signature with parameters."""
    name = None
    params = []
    is_async = False
    is_generator = node.type == 'generator_function_declaration'

    for child in node.children:
        if child.type == 'identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'formal_parameters':
            params = _extract_js_parameters(child, content)

    # Check for async
    node_text = content[node.start_byte:node.start_byte + 15]
    if 'async' in node_text:
        is_async = True

    if not name:
        return ""

    prefix = ""
    if is_async:
        prefix = "async "
    if is_generator:
        prefix += "function* "
    else:
        prefix += "function "

    return f"{prefix}{name}({', '.join(params)})"[:200]


def _extract_js_variable_function_signature(node: 'Node', content: str) -> str:
    """Extract signature for const/let/var function assignments."""
    # Find the variable_declarator
    for child in node.children:
        if child.type == 'variable_declarator':
            name = None
            is_arrow = False
            is_async = False
            params = []

            for sub in child.children:
                if sub.type == 'identifier':
                    name = content[sub.start_byte:sub.end_byte]
                elif sub.type == 'arrow_function':
                    is_arrow = True
                    # Check for async
                    arrow_text = content[sub.start_byte:sub.start_byte + 10]
                    if 'async' in arrow_text:
                        is_async = True
                    # Get parameters
                    for arrow_child in sub.children:
                        if arrow_child.type == 'formal_parameters':
                            params = _extract_js_parameters(arrow_child, content)
                        elif arrow_child.type == 'identifier':
                            # Single param without parens
                            params = [content[arrow_child.start_byte:arrow_child.end_byte]]
                elif sub.type == 'function':
                    # const foo = function() {}
                    for func_child in sub.children:
                        if func_child.type == 'formal_parameters':
                            params = _extract_js_parameters(func_child, content)

            if name:
                prefix = "async " if is_async else ""
                if is_arrow:
                    return f"const {name} = {prefix}({', '.join(params)}) =>"[:200]
                else:
                    return f"const {name} = {prefix}function({', '.join(params)})"[:200]

    return ""


def _extract_js_method_signature(node: 'Node', content: str) -> str:
    """Extract method signature."""
    name = None
    params = []
    is_async = False
    is_static = False
    is_getter = False
    is_setter = False

    for child in node.children:
        if child.type == 'property_identifier':
            name = content[child.start_byte:child.end_byte]
        elif child.type == 'formal_parameters':
            params = _extract_js_parameters(child, content)

    # Check modifiers from node text
    method_text = content[node.start_byte:node.start_byte + 30]
    if 'async' in method_text:
        is_async = True
    if 'static' in method_text:
        is_static = True
    if method_text.strip().startswith('get '):
        is_getter = True
    if method_text.strip().startswith('set '):
        is_setter = True

    if not name:
        return ""

    prefix = ""
    if is_static:
        prefix += "static "
    if is_async:
        prefix += "async "
    if is_getter:
        prefix += "get "
    if is_setter:
        prefix += "set "

    return f"{prefix}{name}({', '.join(params)})"[:200]


def _extract_js_parameters(params_node: 'Node', content: str) -> List[str]:
    """Extract parameter names from formal_parameters node."""
    params = []

    for child in params_node.children:
        if child.type == 'identifier':
            params.append(content[child.start_byte:child.end_byte])
        elif child.type == 'assignment_pattern':
            # Default parameter: param = value
            for sub in child.children:
                if sub.type == 'identifier':
                    params.append(content[sub.start_byte:sub.end_byte])
                    break
        elif child.type == 'rest_pattern':
            # Rest parameter: ...args
            for sub in child.children:
                if sub.type == 'identifier':
                    params.append(f"...{content[sub.start_byte:sub.end_byte]}")
                    break
        elif child.type == 'object_pattern':
            # Destructured parameter: { a, b }
            params.append(content[child.start_byte:child.end_byte])
        elif child.type == 'array_pattern':
            # Destructured array: [a, b]
            params.append(content[child.start_byte:child.end_byte])

    return params


def javascript_post_processor(
    symbols: List['Symbol'],
    file_path: Path,
    content: str
) -> List['Symbol']:
    """
    Post-process extracted symbols.

    - Filter out lexical_declaration that aren't functions
    - Classify React components and hooks
    """

    filtered = []
    for sym in symbols:
        # Skip non-function variable declarations
        if sym.signature and 'const' in sym.signature:
            # Only keep if it's actually a function (has => or function)
            if '=>' not in sym.signature and 'function' not in sym.signature:
                continue

        # Classify React hooks (useXxx pattern)
        if (sym.symbol_type == 'function' and
            sym.name.startswith('use') and
            len(sym.name) > 3 and
            sym.name[3].isupper()):
            # Keep as function but could add metadata
            pass

        # Classify React components (PascalCase in components directory)
        if (sym.symbol_type == 'function' and
            sym.name[0].isupper() and
            ('components' in str(file_path) or 'pages' in str(file_path))):
            # Keep as function but could add metadata
            pass

        filtered.append(sym)

    return filtered


# =============================================================================
# Configuration
# =============================================================================

def _get_javascript_exclude_patterns() -> list:
    """Get exclude patterns from central configuration."""
    from ..exclusions import ExclusionConfig
    return ExclusionConfig.get_patterns('javascript')


JAVASCRIPT_CONFIG = LanguageConfig(
    name="JavaScript",
    tree_sitter_name="javascript",
    extensions={'.js', '.jsx'},
    symbol_queries=JAVASCRIPT_QUERIES,
    max_file_size=300_000,  # 300KB
    exclude_patterns=_get_javascript_exclude_patterns(),
    qualified_name_builder=javascript_qualified_name_builder,
    docstring_extractor=javascript_docstring_extractor,
    visibility_detector=javascript_visibility_detector,
    post_processor=javascript_post_processor,
)
