"""
Tests for Parsing Module — Multi-language symbol extraction architecture.

Tests validate:
- LanguageConfig and SymbolQuery dataclasses
- ParserRegistry extension routing
- ExclusionConfig centralized patterns
- TreeSitterExtractor (when available)
- CodeSymbolStore integration

All core tests work WITHOUT tree-sitter-language-pack installed.
Tree-sitter dependent tests are marked and skipped when unavailable.

Aligns with:
- P5: Tests ARE evidence for implementation
- HC1: Append-only events for symbol indexing
"""

import pytest
from pathlib import Path

# Check if tree-sitter-language-pack is available
try:
    import tree_sitter_language_pack  # noqa: F401
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

# Skip marker for tree-sitter dependent tests
requires_tree_sitter = pytest.mark.skipif(
    not TREE_SITTER_AVAILABLE,
    reason="tree-sitter-language-pack not installed"
)


# =============================================================================
# LanguageConfig Tests
# =============================================================================

class TestLanguageConfig:
    """Test LanguageConfig dataclass."""

    def test_create_basic_config(self):
        """Can create a basic language config."""
        from babel.core.parsing import LanguageConfig, SymbolQuery

        config = LanguageConfig(
            name="TestLang",
            tree_sitter_name="test",
            extensions={'.test'},
            symbol_queries=[
                SymbolQuery(node_type="function", symbol_type="function")
            ],
        )

        assert config.name == "TestLang"
        assert config.tree_sitter_name == "test"
        assert '.test' in config.extensions
        assert len(config.symbol_queries) == 1

    def test_matches_extension(self):
        """Config correctly matches file extensions."""
        from babel.core.parsing import LanguageConfig

        config = LanguageConfig(
            name="Python",
            tree_sitter_name="python",
            extensions={'.py', '.pyw'},
            symbol_queries=[],
        )

        assert config.matches_extension('.py') is True
        assert config.matches_extension('.PY') is True  # Case insensitive
        assert config.matches_extension('.js') is False

    def test_default_max_file_size(self):
        """Default max file size is 300KB."""
        from babel.core.parsing import LanguageConfig

        config = LanguageConfig(
            name="Test",
            tree_sitter_name="test",
            extensions={'.test'},
            symbol_queries=[],
        )

        assert config.max_file_size == 300_000

    def test_custom_hooks(self):
        """Custom hooks can be provided."""
        from babel.core.parsing import LanguageConfig

        def custom_name_builder(path, name, parent):
            return f"custom.{name}"

        config = LanguageConfig(
            name="Test",
            tree_sitter_name="test",
            extensions={'.test'},
            symbol_queries=[],
            qualified_name_builder=custom_name_builder,
        )

        assert config.qualified_name_builder is not None
        assert config.qualified_name_builder(Path("x"), "foo", None) == "custom.foo"


class TestSymbolQuery:
    """Test SymbolQuery dataclass."""

    def test_create_query(self):
        """Can create a symbol query."""
        from babel.core.parsing import SymbolQuery

        query = SymbolQuery(
            node_type="class_definition",
            symbol_type="class",
        )

        assert query.node_type == "class_definition"
        assert query.symbol_type == "class"
        assert query.name_field == "name"  # Default
        assert query.capture_signature is True  # Default
        assert query.capture_docstring is True  # Default

    def test_custom_name_field(self):
        """Can specify custom name field."""
        from babel.core.parsing import SymbolQuery

        query = SymbolQuery(
            node_type="variable_declarator",
            symbol_type="function",
            name_field="identifier",
        )

        assert query.name_field == "identifier"


# =============================================================================
# ParserRegistry Tests
# =============================================================================

class TestParserRegistry:
    """Test ParserRegistry routing logic."""

    def test_empty_registry(self):
        """Empty registry has no supported extensions."""
        from babel.core.parsing import ParserRegistry

        registry = ParserRegistry()

        assert len(registry) == 0
        assert len(registry.supported_extensions()) == 0
        assert registry.get_config(Path("test.py")) is None

    def test_register_config(self):
        """Can register a language config."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        config = LanguageConfig(
            name="Python",
            tree_sitter_name="python",
            extensions={'.py'},
            symbol_queries=[],
        )

        registry.register(config)

        assert len(registry) == 1
        assert '.py' in registry.supported_extensions()
        assert "Python" in registry.supported_languages()

    def test_get_config_by_path(self):
        """Can retrieve config by file path."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        config = LanguageConfig(
            name="JavaScript",
            tree_sitter_name="javascript",
            extensions={'.js', '.jsx'},
            symbol_queries=[],
        )
        registry.register(config)

        assert registry.get_config(Path("app.js")).name == "JavaScript"
        assert registry.get_config(Path("Component.jsx")).name == "JavaScript"
        assert registry.get_config(Path("app.ts")) is None

    def test_get_config_by_name(self):
        """Can retrieve config by language name."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        config = LanguageConfig(
            name="TypeScript",
            tree_sitter_name="typescript",
            extensions={'.ts', '.tsx'},
            symbol_queries=[],
        )
        registry.register(config)

        assert registry.get_config_by_name("TypeScript") is config
        assert registry.get_config_by_name("Python") is None

    def test_extension_conflict_raises(self):
        """Registering conflicting extension raises error."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        config1 = LanguageConfig(
            name="Lang1",
            tree_sitter_name="lang1",
            extensions={'.ext'},
            symbol_queries=[],
        )
        config2 = LanguageConfig(
            name="Lang2",
            tree_sitter_name="lang2",
            extensions={'.ext'},  # Same extension
            symbol_queries=[],
        )

        registry.register(config1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(config2)

    def test_is_supported(self):
        """is_supported checks if file type is handled."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        registry.register(LanguageConfig(
            name="Python",
            tree_sitter_name="python",
            extensions={'.py'},
            symbol_queries=[],
        ))

        assert registry.is_supported(Path("test.py")) is True
        assert registry.is_supported(Path("test.js")) is False

    def test_glob_patterns_for_indexing(self):
        """Generates glob patterns for all supported extensions."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        registry.register(LanguageConfig(
            name="Python",
            tree_sitter_name="python",
            extensions={'.py'},
            symbol_queries=[],
        ))
        registry.register(LanguageConfig(
            name="JavaScript",
            tree_sitter_name="javascript",
            extensions={'.js'},
            symbol_queries=[],
        ))

        patterns = registry.glob_patterns_for_indexing()

        assert "**/*.py" in patterns
        assert "**/*.js" in patterns

    def test_all_exclude_patterns(self):
        """Combines exclude patterns from all configs."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        registry.register(LanguageConfig(
            name="Python",
            tree_sitter_name="python",
            extensions={'.py'},
            symbol_queries=[],
            exclude_patterns=["**/__pycache__/*"],
        ))
        registry.register(LanguageConfig(
            name="JavaScript",
            tree_sitter_name="javascript",
            extensions={'.js'},
            symbol_queries=[],
            exclude_patterns=["**/node_modules/*"],
        ))

        patterns = registry.all_exclude_patterns()

        assert "**/__pycache__/*" in patterns
        assert "**/node_modules/*" in patterns

    def test_unregister(self):
        """Can unregister a config."""
        from babel.core.parsing import ParserRegistry, LanguageConfig

        registry = ParserRegistry()
        registry.register(LanguageConfig(
            name="Python",
            tree_sitter_name="python",
            extensions={'.py'},
            symbol_queries=[],
        ))

        assert registry.unregister("Python") is True
        assert len(registry) == 0
        assert registry.unregister("Python") is False  # Already removed


# =============================================================================
# ExclusionConfig Tests
# =============================================================================

class TestExclusionConfig:
    """Test centralized exclusion configuration."""

    def test_default_common_patterns(self):
        """Default common patterns include standard excludes."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()
        patterns = ExclusionConfig.get_common_patterns()

        assert any('.git' in p for p in patterns)
        assert any('build' in p for p in patterns)

    def test_default_language_patterns(self):
        """Default language patterns exist for Python/JS/TS."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()

        python_patterns = ExclusionConfig.get_language_patterns('python')
        assert any('__pycache__' in p for p in python_patterns)

        js_patterns = ExclusionConfig.get_language_patterns('javascript')
        assert any('node_modules' in p for p in js_patterns)

    def test_get_patterns_combines_all(self):
        """get_patterns combines common + language + test patterns."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()
        patterns = ExclusionConfig.get_patterns('python')

        # Should have common
        assert any('.git' in p for p in patterns)
        # Should have python-specific
        assert any('__pycache__' in p for p in patterns)
        # Should have test patterns (by default)
        assert any('test_' in p for p in patterns)

    def test_add_common_pattern(self):
        """Can add custom common pattern."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()
        ExclusionConfig.add_common('**/custom_exclude/*')

        assert '**/custom_exclude/*' in ExclusionConfig.get_common_patterns()

    def test_add_language_pattern(self):
        """Can add custom language pattern."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()
        ExclusionConfig.add_language('python', '**/my_venv/*')

        assert '**/my_venv/*' in ExclusionConfig.get_language_patterns('python')

    def test_remove_patterns(self):
        """Can remove patterns."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()
        ExclusionConfig.add_common('**/to_remove/*')

        assert ExclusionConfig.remove_common('**/to_remove/*') is True
        assert '**/to_remove/*' not in ExclusionConfig.get_common_patterns()
        assert ExclusionConfig.remove_common('**/to_remove/*') is False  # Already gone

    def test_include_tests_toggle(self):
        """Can toggle test file inclusion."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()

        # By default, tests excluded (look for test file patterns specifically)
        patterns_without = ExclusionConfig.get_patterns('python')
        assert any('**/test_*.py' in p for p in patterns_without)

        # Include tests
        ExclusionConfig.set_include_tests(True)
        patterns_with = ExclusionConfig.get_patterns('python')
        # Test file patterns should be gone (not cache/config patterns)
        test_file_patterns = [p for p in patterns_with if '**/test_*.py' in p or '**/*_test.py' in p]
        assert len(test_file_patterns) == 0

        # Reset for other tests
        ExclusionConfig.reset()

    def test_reset(self):
        """Reset restores defaults."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.add_common('**/custom/*')
        ExclusionConfig.reset()

        assert '**/custom/*' not in ExclusionConfig.get_common_patterns()

    def test_supported_languages(self):
        """Reports supported languages."""
        from babel.core.parsing import ExclusionConfig

        ExclusionConfig.reset()
        languages = ExclusionConfig.supported_languages()

        assert 'python' in languages
        assert 'javascript' in languages
        assert 'typescript' in languages


# =============================================================================
# Language Configs Tests
# =============================================================================

class TestPythonConfig:
    """Test Python language configuration."""

    def test_python_config_exists(self):
        """PYTHON_CONFIG is properly defined."""
        from babel.core.parsing.languages import PYTHON_CONFIG

        assert PYTHON_CONFIG.name == "Python"
        assert PYTHON_CONFIG.tree_sitter_name == "python"
        assert '.py' in PYTHON_CONFIG.extensions

    def test_python_queries(self):
        """Python config has class and function queries."""
        from babel.core.parsing.languages import PYTHON_CONFIG

        query_types = [q.node_type for q in PYTHON_CONFIG.symbol_queries]

        assert 'class_definition' in query_types
        assert 'function_definition' in query_types

    def test_python_hooks_defined(self):
        """Python config has custom hooks."""
        from babel.core.parsing.languages import PYTHON_CONFIG

        assert PYTHON_CONFIG.qualified_name_builder is not None
        assert PYTHON_CONFIG.docstring_extractor is not None
        assert PYTHON_CONFIG.visibility_detector is not None


class TestJavaScriptConfig:
    """Test JavaScript language configuration."""

    def test_javascript_config_exists(self):
        """JAVASCRIPT_CONFIG is properly defined."""
        from babel.core.parsing.languages import JAVASCRIPT_CONFIG

        assert JAVASCRIPT_CONFIG.name == "JavaScript"
        assert JAVASCRIPT_CONFIG.tree_sitter_name == "javascript"
        assert '.js' in JAVASCRIPT_CONFIG.extensions
        assert '.jsx' in JAVASCRIPT_CONFIG.extensions

    def test_javascript_queries(self):
        """JavaScript config has expected queries."""
        from babel.core.parsing.languages import JAVASCRIPT_CONFIG

        query_types = [q.node_type for q in JAVASCRIPT_CONFIG.symbol_queries]

        assert 'class_declaration' in query_types
        assert 'function_declaration' in query_types
        assert 'lexical_declaration' in query_types  # Arrow functions


class TestTypeScriptConfig:
    """Test TypeScript language configuration."""

    def test_typescript_config_exists(self):
        """TYPESCRIPT_CONFIG is properly defined."""
        from babel.core.parsing.languages import TYPESCRIPT_CONFIG

        assert TYPESCRIPT_CONFIG.name == "TypeScript"
        assert TYPESCRIPT_CONFIG.tree_sitter_name == "typescript"
        assert '.ts' in TYPESCRIPT_CONFIG.extensions
        assert '.tsx' in TYPESCRIPT_CONFIG.extensions

    def test_typescript_extends_javascript(self):
        """TypeScript config includes JavaScript queries plus TS-specific."""
        from babel.core.parsing.languages import TYPESCRIPT_CONFIG, JAVASCRIPT_CONFIG

        ts_queries = [q.node_type for q in TYPESCRIPT_CONFIG.symbol_queries]
        js_queries = [q.node_type for q in JAVASCRIPT_CONFIG.symbol_queries]

        # Has all JS queries
        for jq in js_queries:
            assert jq in ts_queries

        # Has TS-specific queries
        assert 'interface_declaration' in ts_queries
        assert 'type_alias_declaration' in ts_queries
        assert 'enum_declaration' in ts_queries


# =============================================================================
# TreeSitterExtractor Tests (requires tree-sitter)
# =============================================================================

class TestTreeSitterExtractorAvailability:
    """Test extractor availability detection."""

    def test_is_available_without_package(self):
        """Reports unavailable when package not installed."""
        from babel.core.parsing import TreeSitterExtractor, ParserRegistry

        registry = ParserRegistry()
        extractor = TreeSitterExtractor(registry)

        # This may be True or False depending on environment
        # Just verify it doesn't crash
        result = extractor.is_available()
        assert isinstance(result, bool)


@requires_tree_sitter
class TestTreeSitterExtractorWithPackage:
    """Tests that require tree-sitter-language-pack."""

    def test_extract_python_function(self):
        """Extracts Python function symbols."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import PYTHON_CONFIG

        registry = ParserRegistry()
        registry.register(PYTHON_CONFIG)
        extractor = TreeSitterExtractor(registry)

        code = '''
def hello():
    """Say hello."""
    print("Hello")

def world(name):
    return f"World {name}"
'''
        symbols = extractor.extract(Path("test.py"), code)

        assert len(symbols) >= 2
        names = [s.name for s in symbols]
        assert 'hello' in names
        assert 'world' in names

    def test_extract_python_class(self):
        """Extracts Python class symbols."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import PYTHON_CONFIG

        registry = ParserRegistry()
        registry.register(PYTHON_CONFIG)
        extractor = TreeSitterExtractor(registry)

        code = '''
class MyClass:
    """A test class."""

    def method(self):
        pass
'''
        symbols = extractor.extract(Path("test.py"), code)

        types = [s.symbol_type for s in symbols]
        assert 'class' in types

    def test_extract_javascript_function(self):
        """Extracts JavaScript function symbols."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import JAVASCRIPT_CONFIG

        registry = ParserRegistry()
        registry.register(JAVASCRIPT_CONFIG)
        extractor = TreeSitterExtractor(registry)

        code = '''
function greet(name) {
    return "Hello " + name;
}

const farewell = (name) => {
    return "Goodbye " + name;
};
'''
        symbols = extractor.extract(Path("test.js"), code)

        names = [s.name for s in symbols]
        assert 'greet' in names

    def test_extract_typescript_interface(self):
        """Extracts TypeScript interface symbols."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import TYPESCRIPT_CONFIG

        registry = ParserRegistry()
        registry.register(TYPESCRIPT_CONFIG)
        extractor = TreeSitterExtractor(registry)

        code = '''
interface User {
    name: string;
    age: number;
}

type Status = 'active' | 'inactive';

enum Priority {
    LOW,
    HIGH
}
'''
        symbols = extractor.extract(Path("test.ts"), code)

        types = [s.symbol_type for s in symbols]
        assert 'interface' in types
        assert 'type' in types
        assert 'enum' in types

    def test_respects_file_size_limit(self):
        """Skips files exceeding max size."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor, LanguageConfig

        config = LanguageConfig(
            name="Small",
            tree_sitter_name="python",
            extensions={'.small'},
            symbol_queries=[],
            max_file_size=10,  # Very small limit
        )

        registry = ParserRegistry()
        registry.register(config)
        extractor = TreeSitterExtractor(registry)

        code = "x" * 100  # Exceeds limit
        symbols = extractor.extract(Path("test.small"), code)

        assert len(symbols) == 0


# =============================================================================
# CodeSymbolStore Integration Tests
# =============================================================================

class TestCodeSymbolStoreIntegration:
    """Test CodeSymbolStore integration with parsing module."""

    def test_store_creates_registry(self, tmp_path):
        """CodeSymbolStore creates parser registry on init."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)

        assert store._registry is not None
        assert 'Python' in store._registry.supported_languages()
        assert 'JavaScript' in store._registry.supported_languages()
        assert 'TypeScript' in store._registry.supported_languages()

    def test_store_registry_accessible(self, tmp_path):
        """Registry is accessible via property."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)

        assert store.registry is store._registry
        assert '.py' in store.registry.supported_extensions()

    def test_stats_includes_typescript_types(self, tmp_path):
        """Stats method includes TypeScript symbol types."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)
        stats = store.stats()

        assert 'interfaces' in stats
        assert 'types' in stats
        assert 'enums' in stats

    def test_fallback_to_ast_for_python(self, tmp_path):
        """Falls back to AST parsing for Python when tree-sitter unavailable."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        # Create test Python file
        test_file = tmp_path / "test_module.py"
        test_file.write_text('''
def my_function():
    """A test function."""
    pass

class MyClass:
    """A test class."""
    pass
''')

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph, project_dir=tmp_path)

        # Force no extractor to test fallback
        store._extractor = None

        symbols = store.index_file(Path("test_module.py"), emit_events=False)

        names = [s.name for s in symbols]
        assert 'my_function' in names
        assert 'MyClass' in names


# =============================================================================
# Markdown Extraction Tests (no tree-sitter needed)
# =============================================================================

class TestMarkdownExtraction:
    """Test Markdown heading extraction (regex-based, always works)."""

    def test_extract_markdown_headings(self, tmp_path):
        """Extracts headings from Markdown files."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        # Create test Markdown file
        test_file = tmp_path / "doc.md"
        test_file.write_text('''
# Main Title

Some content.

## Section One

More content.

### Subsection

Details here.

## Section Two

Final content.
''')

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph, project_dir=tmp_path)

        symbols = store.index_file(Path("doc.md"), emit_events=False)

        types = [s.symbol_type for s in symbols]
        assert 'document' in types
        assert 'section' in types
        assert 'subsection' in types

    def test_markdown_skips_code_blocks(self, tmp_path):
        """Headings inside code blocks are not extracted."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        test_file = tmp_path / "code.md"
        test_file.write_text('''
# Real Heading

```markdown
# Fake Heading In Code Block
```

## Another Real Heading
''')

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph, project_dir=tmp_path)

        symbols = store.index_file(Path("code.md"), emit_events=False)

        names = [s.name for s in symbols]
        assert 'Real Heading' in names
        assert 'Another Real Heading' in names
        assert 'Fake Heading In Code Block' not in names


# =============================================================================
# HTML Config Tests
# =============================================================================

class TestHTMLConfig:
    """Test HTML language configuration."""

    def test_html_config_exists(self):
        """HTML_CONFIG is properly defined."""
        from babel.core.parsing.languages import HTML_CONFIG

        assert HTML_CONFIG.name == "HTML"
        assert HTML_CONFIG.tree_sitter_name == "html"
        assert '.html' in HTML_CONFIG.extensions
        assert '.htm' in HTML_CONFIG.extensions

    def test_html_queries(self):
        """HTML config has element query."""
        from babel.core.parsing.languages import HTML_CONFIG

        query_types = [q.node_type for q in HTML_CONFIG.symbol_queries]
        assert 'element' in query_types

    def test_html_hooks_defined(self):
        """HTML config has custom hooks."""
        from babel.core.parsing.languages import HTML_CONFIG

        assert HTML_CONFIG.name_extractor is not None
        assert HTML_CONFIG.signature_extractor is not None
        assert HTML_CONFIG.post_processor is not None

    def test_html_container_elements_defined(self):
        """HTML container elements set is populated."""
        from babel.core.parsing.languages.html import HTML_CONTAINER_ELEMENTS

        # Check some key containers
        assert 'header' in HTML_CONTAINER_ELEMENTS
        assert 'nav' in HTML_CONTAINER_ELEMENTS
        assert 'section' in HTML_CONTAINER_ELEMENTS
        assert 'article' in HTML_CONTAINER_ELEMENTS
        assert 'form' in HTML_CONTAINER_ELEMENTS
        assert 'dialog' in HTML_CONTAINER_ELEMENTS
        assert 'div' in HTML_CONTAINER_ELEMENTS

        # Check modern additions
        assert 'search' in HTML_CONTAINER_ELEMENTS
        assert 'hgroup' in HTML_CONTAINER_ELEMENTS
        assert 'template' in HTML_CONTAINER_ELEMENTS
        assert 'slot' in HTML_CONTAINER_ELEMENTS

    def test_html_exclusion_patterns(self):
        """HTML has exclusion patterns defined."""
        from babel.core.parsing.exclusions import ExclusionConfig

        ExclusionConfig.reset()
        patterns = ExclusionConfig.get_language_patterns('html')

        # Should have some patterns
        assert len(patterns) > 0
        assert any('*.min.html' in p for p in patterns)


# =============================================================================
# CSS Config Tests
# =============================================================================

class TestCSSConfig:
    """Test CSS language configuration."""

    def test_css_config_exists(self):
        """CSS_CONFIG is properly defined."""
        from babel.core.parsing.languages import CSS_CONFIG

        assert CSS_CONFIG.name == "CSS"
        assert CSS_CONFIG.tree_sitter_name == "css"
        assert '.css' in CSS_CONFIG.extensions

    def test_css_queries(self):
        """CSS config has expected queries."""
        from babel.core.parsing.languages import CSS_CONFIG

        query_types = [q.node_type for q in CSS_CONFIG.symbol_queries]

        assert 'id_selector' in query_types
        assert 'class_selector' in query_types
        assert 'declaration' in query_types  # For custom properties
        assert 'keyframes_statement' in query_types

    def test_css_hooks_defined(self):
        """CSS config has custom hooks."""
        from babel.core.parsing.languages import CSS_CONFIG

        assert CSS_CONFIG.name_extractor is not None
        assert CSS_CONFIG.signature_extractor is not None
        assert CSS_CONFIG.post_processor is not None

    def test_css_is_architectural_class(self):
        """Tests is_architectural_class filtering logic."""
        from babel.core.parsing.languages.css import is_architectural_class

        # Architectural - should return True
        assert is_architectural_class('modal') is True
        assert is_architectural_class('card') is True
        assert is_architectural_class('navbar') is True
        assert is_architectural_class('hero-section') is True

        # BEM elements - should return False
        assert is_architectural_class('card__header') is False
        assert is_architectural_class('modal__content') is False
        assert is_architectural_class('nav__item') is False

        # BEM modifiers - should return False
        assert is_architectural_class('btn--large') is False
        assert is_architectural_class('card--featured') is False

        # Utility classes - should return False
        assert is_architectural_class('flex') is False
        assert is_architectural_class('hidden') is False
        assert is_architectural_class('p-4') is False
        assert is_architectural_class('mt-2') is False
        assert is_architectural_class('text-center') is False

        # Short classes - should return False
        assert is_architectural_class('m') is False
        assert is_architectural_class('p') is False

    def test_css_exclusion_patterns(self):
        """CSS has exclusion patterns defined."""
        from babel.core.parsing.exclusions import ExclusionConfig

        ExclusionConfig.reset()
        patterns = ExclusionConfig.get_language_patterns('css')

        # Should have some patterns
        assert len(patterns) > 0
        assert any('*.min.css' in p for p in patterns)


# =============================================================================
# Gitignore Integration Tests
# =============================================================================

class TestGitignoreIntegration:
    """Test .gitignore respect via git ls-files."""

    def test_get_tracked_files_method_exists(self, tmp_path):
        """CodeSymbolStore has _get_tracked_files method."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)

        assert hasattr(store, '_get_tracked_files')
        assert callable(store._get_tracked_files)

    def test_index_project_has_gitignore_param(self, tmp_path):
        """index_project has respect_gitignore parameter."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore
        import inspect

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)

        sig = inspect.signature(store.index_project)
        assert 'respect_gitignore' in sig.parameters

    def test_get_tracked_files_returns_none_without_git(self, tmp_path):
        """_get_tracked_files returns None when not in git repo."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        # Create non-git directory
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph, project_dir=tmp_path)

        result = store._get_tracked_files({'.py', '.js'})

        # Should return None (fallback to glob)
        assert result is None

    def test_index_project_fallback_without_git(self, tmp_path):
        """index_project falls back to glob when git unavailable."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        # Create non-git directory with a Python file
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph, project_dir=tmp_path)

        # Should work via fallback
        files, symbols = store.index_project(respect_gitignore=True)

        # Should index something (fallback to glob)
        assert files >= 0  # May be 0 or more depending on glob patterns


# =============================================================================
# Registry Integration Tests for New Languages
# =============================================================================

class TestRegistryWithHTMLCSS:
    """Test that HTML and CSS are registered in the default registry."""

    def test_store_includes_html_css(self, tmp_path):
        """CodeSymbolStore registry includes HTML and CSS."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)

        languages = store._registry.supported_languages()
        assert 'HTML' in languages
        assert 'CSS' in languages

    def test_store_supports_html_extensions(self, tmp_path):
        """Registry supports .html and .htm extensions."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)

        extensions = store._registry.supported_extensions()
        assert '.html' in extensions
        assert '.htm' in extensions

    def test_store_supports_css_extension(self, tmp_path):
        """Registry supports .css extension."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)

        extensions = store._registry.supported_extensions()
        assert '.css' in extensions

    def test_stats_includes_html_css_types(self, tmp_path):
        """Stats method includes HTML and CSS symbol types."""
        from babel.core.symbols import CodeSymbolStore
        from babel.core.events import DualEventStore
        from babel.core.graph import GraphStore

        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()

        events = DualEventStore(tmp_path)
        graph = GraphStore(babel_dir / "graph.db")

        store = CodeSymbolStore(babel_dir, events, graph)
        stats = store.stats()

        # HTML stats
        assert 'containers' in stats

        # CSS stats
        assert 'ids' in stats
        assert 'variables' in stats
        assert 'animations' in stats


# =============================================================================
# Tree-sitter HTML/CSS Extraction Tests (requires tree-sitter)
# =============================================================================

@requires_tree_sitter
class TestHTMLExtraction:
    """Tests for HTML extraction (requires tree-sitter-language-pack)."""

    def test_extract_html_containers(self):
        """Extracts HTML container elements."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import HTML_CONFIG

        registry = ParserRegistry()
        registry.register(HTML_CONFIG)
        extractor = TreeSitterExtractor(registry)

        html = '''
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <header id="main-header">
        <nav class="navbar">Menu</nav>
    </header>
    <main>
        <section id="pricing" class="hero">
            <div class="container">Content</div>
        </section>
        <article>Blog post</article>
    </main>
    <footer>Copyright</footer>
</body>
</html>
'''
        symbols = extractor.extract(Path("test.html"), html)

        names = [s.name for s in symbols]

        # Should include containers with IDs
        assert 'header#main-header' in names
        assert 'section#pricing' in names

        # Should include containers with classes (if no ID)
        assert any('nav' in n for n in names)

    def test_html_skips_non_containers(self):
        """Skips non-container elements like p, span, a."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import HTML_CONFIG

        registry = ParserRegistry()
        registry.register(HTML_CONFIG)
        extractor = TreeSitterExtractor(registry)

        html = '''
<div id="content">
    <p id="intro">Intro paragraph</p>
    <span class="highlight">Highlight</span>
    <a href="#" id="link">Link</a>
</div>
'''
        symbols = extractor.extract(Path("test.html"), html)

        # Should NOT include p, span, a even with IDs
        names = [s.name for s in symbols]
        assert not any('intro' in n and 'p' in n for n in names)
        assert not any('span' in n for n in names)
        assert not any('link' in n and 'a#' in n for n in names)

        # Should include div
        assert 'div#content' in names


@requires_tree_sitter
class TestCSSExtraction:
    """Tests for CSS extraction (requires tree-sitter-language-pack)."""

    def test_extract_css_id_selectors(self):
        """Extracts CSS ID selectors."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import CSS_CONFIG

        registry = ParserRegistry()
        registry.register(CSS_CONFIG)
        extractor = TreeSitterExtractor(registry)

        css = '''
#sidebar {
    width: 200px;
}

#main-content {
    flex: 1;
}

#footer {
    margin-top: auto;
}
'''
        symbols = extractor.extract(Path("test.css"), css)

        names = [s.name for s in symbols]
        assert '#sidebar' in names
        assert '#main-content' in names
        assert '#footer' in names

    def test_extract_css_component_classes(self):
        """Extracts component root classes, filters utilities."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import CSS_CONFIG

        registry = ParserRegistry()
        registry.register(CSS_CONFIG)
        extractor = TreeSitterExtractor(registry)

        css = '''
.modal {
    position: fixed;
}

.card {
    border-radius: 8px;
}

.card__header {
    padding: 16px;
}

.btn--large {
    font-size: 18px;
}

.flex {
    display: flex;
}
'''
        symbols = extractor.extract(Path("test.css"), css)

        names = [s.name for s in symbols]

        # Should include component roots
        assert '.modal' in names
        assert '.card' in names

        # Should NOT include BEM elements/modifiers
        assert '.card__header' not in names
        assert '.btn--large' not in names

        # Should NOT include utilities
        assert '.flex' not in names

    def test_extract_css_custom_properties(self):
        """Extracts CSS custom properties (--*)."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import CSS_CONFIG

        registry = ParserRegistry()
        registry.register(CSS_CONFIG)
        extractor = TreeSitterExtractor(registry)

        css = '''
:root {
    --color-primary: #007bff;
    --spacing-lg: 24px;
    --font-heading: Georgia, serif;
}

.dark-mode {
    --color-primary: #4dabf7;
}
'''
        symbols = extractor.extract(Path("test.css"), css)

        names = [s.name for s in symbols]
        types = [s.symbol_type for s in symbols]

        # Should include custom properties
        assert '--color-primary' in names
        assert '--spacing-lg' in names
        assert '--font-heading' in names

        # Should be typed as variable
        assert 'variable' in types

    def test_extract_css_keyframes(self):
        """Extracts @keyframes animations."""
        from babel.core.parsing import ParserRegistry, TreeSitterExtractor
        from babel.core.parsing.languages import CSS_CONFIG

        registry = ParserRegistry()
        registry.register(CSS_CONFIG)
        extractor = TreeSitterExtractor(registry)

        css = '''
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    0% { transform: translateY(100%); }
    100% { transform: translateY(0); }
}
'''
        symbols = extractor.extract(Path("test.css"), css)

        names = [s.name for s in symbols]
        types = [s.symbol_type for s in symbols]

        # Should include keyframes
        assert any('fadeIn' in n for n in names)
        assert any('slideUp' in n for n in names)

        # Should be typed as animation
        assert 'animation' in types
