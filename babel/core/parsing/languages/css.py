"""
CSS language configuration for symbol extraction.

Defines CSS_CONFIG with tree-sitter queries for CSS files (.css).
Indexes architectural selectors that represent structure, not utilities.

Symbol types extracted:
- id: ID selectors (#sidebar, #main-nav)
- class: Component root classes (.modal, .card) - filtered
- variable: CSS custom properties (--color-primary)
- animation: @keyframes declarations

Filtering rules for class selectors:
- INCLUDE: Component roots (no __ or -- in name, length > 3)
- EXCLUDE: BEM elements (.card__header)
- EXCLUDE: BEM modifiers (.btn--large)
- EXCLUDE: Utility classes (.flex, .p-4, .text-sm)

This creates semantic coherence with HTML containers:
- HTML: <section id="pricing"> maps to CSS: #pricing { }
- HTML: <nav class="navbar"> maps to CSS: .navbar { }
"""

from pathlib import Path
from typing import List, Optional, Set, TYPE_CHECKING

from ..config import LanguageConfig, SymbolQuery

if TYPE_CHECKING:
    from tree_sitter import Node


# =============================================================================
# Known Utility Class Patterns (common frameworks)
# =============================================================================

# Short utility prefixes that indicate atomic/utility classes
UTILITY_PREFIXES = frozenset({
    # Spacing
    'm-', 'mx-', 'my-', 'mt-', 'mr-', 'mb-', 'ml-', 'ms-', 'me-',
    'p-', 'px-', 'py-', 'pt-', 'pr-', 'pb-', 'pl-', 'ps-', 'pe-',
    # Sizing
    'w-', 'h-', 'min-w-', 'min-h-', 'max-w-', 'max-h-',
    # Display/layout
    'd-', 'flex-', 'grid-', 'col-', 'row-', 'gap-',
    # Text
    'text-', 'font-', 'leading-', 'tracking-',
    # Colors
    'bg-', 'border-', 'ring-',
    # Position
    'top-', 'right-', 'bottom-', 'left-', 'inset-',
    # Other utilities
    'z-', 'opacity-', 'rounded-', 'shadow-', 'overflow-',
})

# Single-word utility classes
UTILITY_SINGLE_WORDS = frozenset({
    'flex', 'grid', 'block', 'inline', 'hidden', 'visible',
    'static', 'fixed', 'absolute', 'relative', 'sticky',
    'container', 'clearfix', 'sr-only', 'not-sr-only',
})


# =============================================================================
# Symbol Queries
# =============================================================================

CSS_QUERIES = [
    # ID selectors - always architectural
    SymbolQuery(
        node_type="id_selector",
        symbol_type="id",
        name_field=None,  # Custom extraction
        capture_signature=True,
        capture_docstring=False,
    ),
    # Class selectors - filtered in post-processor
    SymbolQuery(
        node_type="class_selector",
        symbol_type="class",
        name_field=None,  # Custom extraction
        capture_signature=True,
        capture_docstring=False,
    ),
    # Declarations - for custom properties (--*), filtered in name_extractor
    SymbolQuery(
        node_type="declaration",
        symbol_type="variable",
        name_field=None,  # Custom extraction (only --* properties)
        capture_signature=True,
        capture_docstring=False,
    ),
    # Keyframes - animation definitions
    SymbolQuery(
        node_type="keyframes_statement",
        symbol_type="animation",
        name_field=None,  # Custom extraction
        capture_signature=True,
        capture_docstring=False,
    ),
]


# =============================================================================
# Custom Hooks
# =============================================================================

def css_name_extractor(node: 'Node', content: str) -> Optional[str]:
    """
    Extract name from CSS selector or at-rule.

    Handles:
    - id_selector: extract id_name child
    - class_selector: extract class_name child
    - keyframes_statement: extract keyframes_name child
    - declaration: extract property_name if custom property
    """
    if node.type == 'id_selector':
        # Find id_name child
        for child in node.children:
            if child.type == 'id_name':
                return '#' + content[child.start_byte:child.end_byte]
        # Fallback: text after #
        text = content[node.start_byte:node.end_byte]
        if text.startswith('#'):
            return text.split()[0]  # Just the selector

    elif node.type == 'class_selector':
        # Find class_name child
        for child in node.children:
            if child.type == 'class_name':
                return '.' + content[child.start_byte:child.end_byte]
        # Fallback: text after .
        text = content[node.start_byte:node.end_byte]
        if text.startswith('.'):
            return text.split()[0]

    elif node.type == 'keyframes_statement':
        # Find keyframes_name child
        for child in node.children:
            if child.type == 'keyframes_name':
                return '@keyframes ' + content[child.start_byte:child.end_byte]
        # Fallback: extract name after @keyframes
        text = content[node.start_byte:node.end_byte]
        if '@keyframes' in text:
            parts = text.split()
            if len(parts) >= 2:
                return '@keyframes ' + parts[1]

    elif node.type == 'declaration':
        # Check if this is a custom property (--*)
        for child in node.children:
            if child.type == 'property_name':
                prop_name = content[child.start_byte:child.end_byte]
                if prop_name.startswith('--'):
                    return prop_name

    return None


def css_qualified_name_builder(
    file_path: Path,
    name: str,
    parent_symbol: Optional[str]
) -> str:
    """Build qualified name for CSS symbol."""
    module = str(file_path.with_suffix('')).replace('/', '.').replace('\\', '.')
    # Clean name for qualified path
    clean_name = name.replace('#', 'id_').replace('.', 'class_').replace('@keyframes ', 'keyframes_')
    clean_name = clean_name.replace('--', 'var_')
    return f"{module}.{clean_name}"


def css_signature_extractor(node: 'Node', content: str) -> str:
    """Extract CSS rule signature."""
    # For selectors, find the parent rule_set and get its selector
    if node.type in ('id_selector', 'class_selector'):
        # Walk up to find rule_set
        parent = node.parent
        while parent and parent.type != 'rule_set':
            parent = parent.parent
        if parent and parent.type == 'rule_set':
            # Get first line of rule
            text = content[parent.start_byte:parent.end_byte]
            first_line = text.split('{')[0].strip()
            return first_line[:150]

    # For keyframes, get the full @keyframes line
    elif node.type == 'keyframes_statement':
        text = content[node.start_byte:node.end_byte]
        first_line = text.split('{')[0].strip()
        return first_line[:150]

    # For declarations (custom properties), get property: value
    elif node.type == 'declaration':
        text = content[node.start_byte:node.end_byte]
        return text.strip()[:150]

    # Fallback
    text = content[node.start_byte:node.end_byte]
    return text.split('\n')[0][:150]


def is_architectural_class(class_name: str) -> bool:
    """
    Determine if a class selector is architectural (component root) vs utility.

    Architectural classes:
    - Component roots: .modal, .card, .navbar, .hero
    - No BEM element separator (__)
    - No BEM modifier separator (--)
    - Not a known utility pattern

    Args:
        class_name: Class name without the dot (e.g., "modal" not ".modal")

    Returns:
        True if this is an architectural/component class
    """
    # BEM element - skip
    if '__' in class_name:
        return False

    # BEM modifier - skip (but be careful not to match CSS vars)
    # BEM uses single -- as modifier separator
    if '--' in class_name and not class_name.startswith('--'):
        return False

    # Very short classes are usually utilities
    if len(class_name) <= 2:
        return False

    # Check utility prefixes
    for prefix in UTILITY_PREFIXES:
        if class_name.startswith(prefix):
            return False

    # Check single-word utilities
    if class_name in UTILITY_SINGLE_WORDS:
        return False

    # Looks like a component class
    return True


def css_post_processor(
    symbols: List['Symbol'],
    file_path: Path,
    content: str
) -> List['Symbol']:
    """
    Filter CSS symbols to architectural selectors only.

    Removes:
    - BEM elements (.card__header)
    - BEM modifiers (.btn--large)
    - Utility classes (.flex, .p-4)
    """
    filtered = []
    seen_names: Set[str] = set()  # Deduplicate

    for sym in symbols:
        # Skip duplicates (same selector can appear multiple times)
        if sym.name in seen_names:
            continue

        # ID selectors - always keep
        if sym.name.startswith('#'):
            seen_names.add(sym.name)
            filtered.append(sym)
            continue

        # Keyframes - always keep
        if sym.name.startswith('@keyframes'):
            seen_names.add(sym.name)
            filtered.append(sym)
            continue

        # Custom properties - always keep
        if sym.name.startswith('--'):
            seen_names.add(sym.name)
            filtered.append(sym)
            continue

        # Class selectors - filter
        if sym.name.startswith('.'):
            class_name = sym.name[1:]  # Remove dot
            if is_architectural_class(class_name):
                seen_names.add(sym.name)
                filtered.append(sym)

    return filtered


# =============================================================================
# Configuration
# =============================================================================

def _get_css_exclude_patterns() -> list:
    """Get exclude patterns from central configuration."""
    from ..exclusions import ExclusionConfig
    return ExclusionConfig.get_patterns('css')


CSS_CONFIG = LanguageConfig(
    name="CSS",
    tree_sitter_name="css",
    extensions={'.css'},
    symbol_queries=CSS_QUERIES,
    max_file_size=500_000,  # 500KB
    exclude_patterns=_get_css_exclude_patterns(),
    name_extractor=css_name_extractor,
    qualified_name_builder=css_qualified_name_builder,
    docstring_extractor=None,  # CSS doesn't have docstrings
    visibility_detector=None,  # All CSS is "public"
    signature_extractor=css_signature_extractor,
    post_processor=css_post_processor,
)
