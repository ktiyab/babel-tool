"""
TreeSitterExtractor — Unified symbol extraction using tree-sitter AST.

Extracts symbols from any language based on LanguageConfig queries.
Uses tree-sitter-language-pack for parsing multiple languages.

Design principle: Language-agnostic extraction driven by configuration.

Usage:
    from babel.core.parsing import ParserRegistry, TreeSitterExtractor
    from babel.core.parsing.languages.python import PYTHON_CONFIG

    registry = ParserRegistry()
    registry.register(PYTHON_CONFIG)

    extractor = TreeSitterExtractor(registry)
    symbols = extractor.extract(Path("app.py"), content)
"""

from pathlib import Path
from typing import List, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Parser, Node

# Lazy import for tree-sitter to allow graceful degradation
_tree_sitter_available = None
_language_pack_available = None


def _check_tree_sitter() -> bool:
    """Check if tree-sitter is available."""
    global _tree_sitter_available
    if _tree_sitter_available is None:
        try:
            import tree_sitter  # noqa: F401
            _tree_sitter_available = True
        except ImportError:
            _tree_sitter_available = False
    return _tree_sitter_available


def _check_language_pack() -> bool:
    """Check if tree-sitter-language-pack is available."""
    global _language_pack_available
    if _language_pack_available is None:
        try:
            import tree_sitter_language_pack  # noqa: F401
            _language_pack_available = True
        except ImportError:
            _language_pack_available = False
    return _language_pack_available


class TreeSitterExtractor:
    """
    Extracts symbols from source code using tree-sitter AST parsing.

    Uses LanguageConfig to determine what AST nodes to extract.
    Produces Symbol objects compatible with CodeSymbolStore.
    """

    def __init__(self, registry: 'ParserRegistry'):
        """
        Initialize extractor with parser registry.

        Args:
            registry: ParserRegistry providing language configs
        """
        from .registry import ParserRegistry
        self.registry: ParserRegistry = registry
        self._parsers: Dict[str, 'Parser'] = {}  # Lazy-loaded parsers

    def _get_parser(self, tree_sitter_name: str) -> Optional['Parser']:
        """
        Get tree-sitter parser for a language (lazy-loaded).

        Args:
            tree_sitter_name: Grammar name (e.g., "python", "typescript")

        Returns:
            Parser instance or None if not available
        """
        if tree_sitter_name in self._parsers:
            return self._parsers[tree_sitter_name]

        if not _check_language_pack():
            return None

        try:
            from tree_sitter_language_pack import get_parser
            parser = get_parser(tree_sitter_name)
            self._parsers[tree_sitter_name] = parser
            return parser
        except Exception:
            return None

    def extract(
        self,
        file_path: Path,
        content: str,
        git_hash: str = ""
    ) -> List['Symbol']:
        """
        Extract symbols from file content.

        Args:
            file_path: Path to file (for qualified name building)
            content: File content to parse
            git_hash: Current git commit hash (optional)

        Returns:
            List of extracted Symbol objects
        """
        from ..symbols import Symbol
        from .config import LanguageConfig

        config = self.registry.get_config(file_path)
        if config is None:
            return []

        # Check file size limit
        if len(content) > config.max_file_size:
            return []

        # Special case: Markdown uses regex, not tree-sitter
        if config.tree_sitter_name == 'markdown':
            return self._extract_markdown(file_path, content, config, git_hash)

        # Get tree-sitter parser
        parser = self._get_parser(config.tree_sitter_name)
        if parser is None:
            # Fall back to no extraction if tree-sitter unavailable
            return []

        # Parse content
        try:
            tree = parser.parse(content.encode('utf-8'))
        except Exception:
            return []

        # Extract symbols by walking AST
        symbols: List[Symbol] = []
        self._walk_tree(
            node=tree.root_node,
            config=config,
            file_path=file_path,
            content=content,
            git_hash=git_hash,
            symbols=symbols,
            parent_symbol=None,
        )

        # Apply post-processor if configured
        if config.post_processor:
            symbols = config.post_processor(symbols, file_path, content)

        return symbols

    def _walk_tree(
        self,
        node: 'Node',
        config: 'LanguageConfig',
        file_path: Path,
        content: str,
        git_hash: str,
        symbols: List['Symbol'],
        parent_symbol: Optional[str],
    ) -> None:
        """
        Recursively walk AST and extract symbols.

        Args:
            node: Current AST node
            config: Language configuration
            file_path: Source file path
            content: File content (for text extraction)
            git_hash: Git commit hash
            symbols: List to append extracted symbols
            parent_symbol: Qualified name of parent (for methods)
        """
        from .config import SymbolQuery

        # Check if this node matches any symbol query
        for query in config.symbol_queries:
            if node.type == query.node_type:
                symbol = self._extract_symbol(
                    node=node,
                    query=query,
                    config=config,
                    file_path=file_path,
                    content=content,
                    git_hash=git_hash,
                    parent_symbol=parent_symbol,
                )
                if symbol:
                    symbols.append(symbol)
                    # For classes, recurse with this symbol as parent
                    if symbol.symbol_type == 'class':
                        for child in node.children:
                            self._walk_tree(
                                node=child,
                                config=config,
                                file_path=file_path,
                                content=content,
                                git_hash=git_hash,
                                symbols=symbols,
                                parent_symbol=symbol.qualified_name,
                            )
                        return  # Don't recurse again below

        # Recurse into children
        for child in node.children:
            self._walk_tree(
                node=child,
                config=config,
                file_path=file_path,
                content=content,
                git_hash=git_hash,
                symbols=symbols,
                parent_symbol=parent_symbol,
            )

    def _extract_symbol(
        self,
        node: 'Node',
        query: 'SymbolQuery',
        config: 'LanguageConfig',
        file_path: Path,
        content: str,
        git_hash: str,
        parent_symbol: Optional[str],
    ) -> Optional['Symbol']:
        """
        Extract a single symbol from an AST node.

        Args:
            node: AST node to extract from
            query: SymbolQuery defining extraction rules
            config: Language configuration
            file_path: Source file path
            content: File content
            git_hash: Git commit hash
            parent_symbol: Parent symbol qualified name

        Returns:
            Symbol object or None if extraction fails
        """
        from ..symbols import Symbol

        # Get name - try custom extractor first, then field-based
        name = None
        if config.name_extractor:
            name = config.name_extractor(node, content)
        if not name and query.name_field:
            name = self._get_node_field_text(node, query.name_field, content)
        if not name and query.name_field:
            # Try direct child with type matching name_field
            name = self._get_child_by_type_text(node, query.name_field, content)
        if not name:
            return None

        # Build qualified name
        if config.qualified_name_builder:
            qualified_name = config.qualified_name_builder(
                file_path, name, parent_symbol
            )
        else:
            qualified_name = self._default_qualified_name(
                file_path, name, parent_symbol
            )

        # Extract signature - try custom extractor first
        signature = ""
        if query.capture_signature:
            if config.signature_extractor:
                signature = config.signature_extractor(node, content)
            else:
                signature = self._extract_signature(node, content, config)

        # Extract docstring
        docstring = ""
        if query.capture_docstring and config.docstring_extractor:
            docstring = config.docstring_extractor(node, content)
        elif query.capture_docstring:
            docstring = self._default_docstring_extractor(node, content)

        # Determine visibility
        visibility = "public"
        if config.visibility_detector:
            visibility = config.visibility_detector(node, name, content)
        else:
            # Default: underscore prefix = private
            visibility = "private" if name.startswith('_') else "public"

        # Determine symbol type (may be refined, e.g., function -> method)
        symbol_type = query.symbol_type
        if parent_symbol and symbol_type == 'function':
            symbol_type = 'method'

        return Symbol(
            symbol_type=symbol_type,
            name=name,
            qualified_name=qualified_name,
            file_path=str(file_path),
            line_start=node.start_point[0] + 1,  # tree-sitter is 0-indexed
            line_end=node.end_point[0] + 1,
            signature=signature,
            docstring=docstring[:200] if docstring else "",
            parent_symbol=parent_symbol or "",
            visibility=visibility,
            git_hash=git_hash,
        )

    def _get_node_field_text(
        self,
        node: 'Node',
        field_name: str,
        content: str
    ) -> Optional[str]:
        """Get text of a named field in the node."""
        child = node.child_by_field_name(field_name)
        if child:
            return content[child.start_byte:child.end_byte]
        return None

    def _get_child_by_type_text(
        self,
        node: 'Node',
        type_name: str,
        content: str
    ) -> Optional[str]:
        """Get text of first child with matching type."""
        for child in node.children:
            if child.type == type_name:
                return content[child.start_byte:child.end_byte]
            # Check one level deeper for identifiers
            if child.type == 'identifier':
                return content[child.start_byte:child.end_byte]
        return None

    def _default_qualified_name(
        self,
        file_path: Path,
        name: str,
        parent_symbol: Optional[str],
    ) -> str:
        """Build default qualified name: path.to.module.SymbolName"""
        # Convert path to module notation
        module = str(file_path.with_suffix('')).replace('/', '.').replace('\\', '.')

        if parent_symbol:
            return f"{parent_symbol}.{name}"
        return f"{module}.{name}"

    def _extract_signature(
        self,
        node: 'Node',
        content: str,
        config: 'LanguageConfig'
    ) -> str:
        """
        Extract signature from node.

        Default: first line of node text, trimmed.
        """
        text = content[node.start_byte:node.end_byte]
        first_line = text.split('\n')[0].strip()
        # Limit length
        return first_line[:200] if len(first_line) > 200 else first_line

    def _default_docstring_extractor(
        self,
        node: 'Node',
        content: str
    ) -> str:
        """
        Default docstring extraction.

        Looks for string literal as first statement in body.
        """
        # Look for a 'body' or 'block' child
        for child in node.children:
            if child.type in ('block', 'body', 'statement_block'):
                # First child might be a string/docstring
                if child.children:
                    first = child.children[0]
                    if first.type in ('expression_statement', 'string'):
                        text = content[first.start_byte:first.end_byte]
                        # Clean up quotes
                        text = text.strip().strip('"\'').strip()
                        return text.split('\n')[0][:200]
        return ""

    def _extract_markdown(
        self,
        file_path: Path,
        content: str,
        config: 'LanguageConfig',
        git_hash: str
    ) -> List['Symbol']:
        """
        Extract symbols from Markdown using regex (special case).

        Markdown doesn't use tree-sitter; it uses heading regex.
        This preserves compatibility with existing markdown extraction.
        """
        import re
        from ..symbols import Symbol

        symbols = []

        # Build qualified name prefix from file path
        parts = list(file_path.with_suffix('').parts)
        doc_name = '.'.join(parts)

        lines = content.split('\n')
        heading_pattern = re.compile(r'^(#{1,3})\s+(.+)$')

        in_code_block = False
        for line_num, line in enumerate(lines, start=1):
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            match = heading_pattern.match(line)
            if not match:
                continue

            level = len(match.group(1))
            heading_text = match.group(2).strip().rstrip('#').strip()

            # Determine symbol type
            if level == 1:
                symbol_type = "document"
            elif level == 2:
                symbol_type = "section"
            elif level == 3:
                symbol_type = "subsection"
            else:
                continue

            # Build qualified name with section marker if present
            marker_match = re.search(r'\[([A-Z]+-\d+)\]', heading_text)
            if marker_match:
                section_id = marker_match.group(1)
            else:
                # Create slug
                slug = re.sub(r'[^\w\s-]', '', heading_text.lower())
                slug = re.sub(r'[\s-]+', '_', slug)
                section_id = slug[:50]

            qualified_name = f"{doc_name}.{section_id}"

            # Find end line
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
                git_hash=git_hash,
            ))

        return symbols

    def is_available(self) -> bool:
        """Check if tree-sitter extraction is available."""
        return _check_tree_sitter() and _check_language_pack()

    def available_languages(self) -> List[str]:
        """
        Get list of languages available via tree-sitter-language-pack.

        Returns:
            List of language names, or empty if package not available
        """
        if not _check_language_pack():
            return []

        # Common languages known to be in the pack
        return [
            'python', 'javascript', 'typescript', 'tsx',
            'go', 'rust', 'java', 'c', 'cpp', 'c_sharp',
            'ruby', 'php', 'swift', 'kotlin', 'scala',
            'html', 'css', 'json', 'yaml', 'toml',
            'bash', 'sql', 'lua', 'haskell', 'elixir',
        ]
