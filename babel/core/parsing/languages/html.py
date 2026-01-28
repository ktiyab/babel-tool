"""
HTML language configuration for symbol extraction.

Defines HTML_CONFIG with tree-sitter queries for HTML files (.html, .htm).
Indexes only structural container elements, not every HTML element.

Container elements indexed (~35 tags):
- Document: html, head, body
- Page sections: header, footer, main, nav, article, section, aside, hgroup
- Generic: div
- Table: table
- Lists: ul, ol, dl, menu
- Form: form, fieldset, datalist, select, optgroup
- Media: figure, picture, video, audio, canvas, svg, map
- Interactive: details, dialog, search
- Text block: blockquote, pre, address
- Embedded: iframe, object, embed
- Web Components: template, slot
- Output: output

Symbol naming priority:
1. id attribute (unique identifier)
2. aria-label attribute (accessibility name)
3. First class name (if meaningful)
4. Tag name only (fallback)
"""

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from ..config import LanguageConfig, SymbolQuery

if TYPE_CHECKING:
    from tree_sitter import Node


# =============================================================================
# Container Elements (structural elements worth indexing)
# =============================================================================

HTML_CONTAINER_ELEMENTS = frozenset({
    # Document
    'html', 'head', 'body',
    # Page sections
    'header', 'footer', 'main', 'nav', 'article', 'section', 'aside', 'hgroup',
    # Generic container
    'div',
    # Table
    'table',
    # Lists
    'ul', 'ol', 'dl', 'menu',
    # Form
    'form', 'fieldset', 'datalist', 'select', 'optgroup',
    # Media
    'figure', 'picture', 'video', 'audio', 'canvas', 'svg', 'map',
    # Interactive
    'details', 'dialog', 'search',
    # Text block
    'blockquote', 'pre', 'address',
    # Embedded
    'iframe', 'object', 'embed',
    # Web Components
    'template', 'slot',
    # Output
    'output',
})


# =============================================================================
# Symbol Queries
# =============================================================================

HTML_QUERIES = [
    # Query all elements, filter in post-processor
    SymbolQuery(
        node_type="element",
        symbol_type="container",
        name_field=None,  # Custom extraction via hooks
        capture_signature=True,
        capture_docstring=False,
    ),
]


# =============================================================================
# Custom Hooks
# =============================================================================

def html_name_extractor(node: 'Node', content: str) -> Optional[str]:
    """
    Extract meaningful name from HTML element.

    Priority:
    1. id attribute
    2. aria-label attribute
    3. First class name
    4. Tag name only

    Returns:
        Name string like "nav#main-nav" or "section.hero" or "header"
    """
    tag_name = None
    element_id = None
    aria_label = None
    first_class = None

    # Find start_tag child
    start_tag = None
    for child in node.children:
        if child.type == 'start_tag':
            start_tag = child
            break
        elif child.type == 'self_closing_tag':
            start_tag = child
            break

    if not start_tag:
        return None

    # Extract tag name and attributes
    for child in start_tag.children:
        if child.type == 'tag_name':
            tag_name = content[child.start_byte:child.end_byte].lower()
        elif child.type == 'attribute':
            attr_name = None
            attr_value = None
            for attr_child in child.children:
                if attr_child.type == 'attribute_name':
                    attr_name = content[attr_child.start_byte:attr_child.end_byte].lower()
                elif attr_child.type in ('quoted_attribute_value', 'attribute_value'):
                    # Remove quotes if present
                    val = content[attr_child.start_byte:attr_child.end_byte]
                    attr_value = val.strip('"\'')

            if attr_name == 'id' and attr_value:
                element_id = attr_value
            elif attr_name == 'aria-label' and attr_value:
                aria_label = attr_value
            elif attr_name == 'class' and attr_value and not first_class:
                # Take first class only
                first_class = attr_value.split()[0] if attr_value else None

    if not tag_name:
        return None

    # Build name with priority
    if element_id:
        return f"{tag_name}#{element_id}"
    elif aria_label:
        # Clean aria-label for use as identifier
        clean_label = aria_label.lower().replace(' ', '-')[:30]
        return f"{tag_name}[{clean_label}]"
    elif first_class:
        return f"{tag_name}.{first_class}"
    else:
        return tag_name


def html_qualified_name_builder(
    file_path: Path,
    name: str,
    parent_symbol: Optional[str]
) -> str:
    """Build qualified name for HTML symbol."""
    # Convert path to module notation
    module = str(file_path.with_suffix('')).replace('/', '.').replace('\\', '.')
    return f"{module}.{name}"


def html_signature_extractor(node: 'Node', content: str) -> str:
    """
    Extract HTML element signature (opening tag).
    """
    # Find start_tag
    for child in node.children:
        if child.type in ('start_tag', 'self_closing_tag'):
            tag_text = content[child.start_byte:child.end_byte]
            # Limit length and clean up
            return tag_text[:150].replace('\n', ' ').strip()
    return ""


def html_post_processor(
    symbols: List['Symbol'],
    file_path: Path,
    content: str
) -> List['Symbol']:
    """
    Filter HTML symbols to only container elements.

    Removes non-container elements (p, span, a, etc.)
    """
    from ...symbols import Symbol

    filtered = []
    for sym in symbols:
        # Extract tag name from symbol name
        # Name format: "tag#id" or "tag.class" or "tag[label]" or "tag"
        name = sym.name
        if '#' in name:
            tag = name.split('#')[0]
        elif '.' in name:
            tag = name.split('.')[0]
        elif '[' in name:
            tag = name.split('[')[0]
        else:
            tag = name

        # Only keep container elements
        if tag.lower() in HTML_CONTAINER_ELEMENTS:
            filtered.append(sym)

    return filtered


# =============================================================================
# Custom Extractor for HTML (element node type needs special handling)
# =============================================================================

def html_element_extractor(
    node: 'Node',
    content: str,
    file_path: Path,
    git_hash: str
) -> Optional['Symbol']:
    """
    Extract symbol from HTML element node.

    Called by TreeSitterExtractor when processing HTML files.
    """
    from ...symbols import Symbol

    name = html_name_extractor(node, content)
    if not name:
        return None

    # Extract tag for filtering
    if '#' in name:
        tag = name.split('#')[0]
    elif '.' in name:
        tag = name.split('.')[0]
    elif '[' in name:
        tag = name.split('[')[0]
    else:
        tag = name

    # Only process container elements
    if tag.lower() not in HTML_CONTAINER_ELEMENTS:
        return None

    qualified_name = html_qualified_name_builder(file_path, name, None)
    signature = html_signature_extractor(node, content)

    return Symbol(
        symbol_type="container",
        name=name,
        qualified_name=qualified_name,
        file_path=str(file_path),
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        signature=signature,
        docstring="",
        parent_symbol="",
        visibility="public",
        git_hash=git_hash,
    )


# =============================================================================
# Configuration
# =============================================================================

def _get_html_exclude_patterns() -> list:
    """Get exclude patterns from central configuration."""
    from ..exclusions import ExclusionConfig
    return ExclusionConfig.get_patterns('html')


HTML_CONFIG = LanguageConfig(
    name="HTML",
    tree_sitter_name="html",
    extensions={'.html', '.htm'},
    symbol_queries=HTML_QUERIES,
    max_file_size=500_000,  # 500KB
    exclude_patterns=_get_html_exclude_patterns(),
    name_extractor=html_name_extractor,
    qualified_name_builder=html_qualified_name_builder,
    docstring_extractor=None,  # HTML doesn't have docstrings
    visibility_detector=None,  # All HTML elements are "public"
    signature_extractor=html_signature_extractor,
    post_processor=html_post_processor,
)
