"""
Centralized exclusion patterns for symbol indexing.

Single source of truth for all exclude patterns across languages.
Extensible and accessible for configuration.

Usage:
    from babel.core.parsing.exclusions import ExclusionConfig

    # Get all patterns for a language
    patterns = ExclusionConfig.get_patterns('python')

    # Add custom patterns
    ExclusionConfig.add_common('**/custom_exclude/*')
    ExclusionConfig.add_language('python', '**/my_tests/*')

    # Reset to defaults
    ExclusionConfig.reset()
"""

from typing import Dict, List, Set


class ExclusionConfig:
    """
    Central configuration for exclude patterns.

    Manages:
    - Common patterns applied to all languages
    - Language-specific patterns
    - Runtime additions for customization
    """

    # =========================================================================
    # Default Patterns (can be extended at runtime)
    # =========================================================================

    # Patterns applied to ALL languages
    _DEFAULT_COMMON: List[str] = [
        # Version control
        '**/.git/*',
        '**/.svn/*',
        '**/.hg/*',

        # IDE/Editor
        '**/.idea/*',
        '**/.vscode/*',
        '**/*.swp',
        '**/*.swo',

        # Build artifacts
        '**/build/*',
        '**/dist/*',
        '**/out/*',

        # Documentation build
        '**/docs/_build/*',
        '**/_site/*',

        # Coverage/reports
        '**/coverage/*',
        '**/htmlcov/*',
        '**/.coverage',

        # Logs
        '**/logs/*',
        '**/*.log',

        # Temporary files
        '**/tmp/*',
        '**/temp/*',
        '**/*.tmp',
    ]

    # Language-specific default patterns
    _DEFAULT_LANGUAGE: Dict[str, List[str]] = {
        'python': [
            '**/__pycache__/*',
            '**/*.pyc',
            '**/*.pyo',
            '**/.venv/*',
            '**/venv/*',
            '**/env/*',
            '**/.env/*',
            '**/site-packages/*',
            '**/migrations/*',
            '**/.tox/*',
            '**/.nox/*',
            '**/.pytest_cache/*',
            '**/.mypy_cache/*',
            '**/.ruff_cache/*',
            '**/eggs/*',
            '**/*.egg-info/*',
        ],
        'javascript': [
            '**/node_modules/*',
            '**/bower_components/*',
            '**/.npm/*',
            '**/*.min.js',
            '**/*.bundle.js',
            '**/vendor/*',
        ],
        'typescript': [
            '**/node_modules/*',
            '**/.next/*',
            '**/out/*',
            '**/*.d.ts',  # Declaration files (optional, can be removed)
            '**/.turbo/*',
            '**/.vercel/*',
        ],
        'markdown': [
            # Usually no exclusions for markdown
        ],
        'html': [
            # Minified/generated HTML
            '**/*.min.html',
            '**/vendor/*',
            # Build outputs
            '**/dist/*',
            '**/build/*',
            # Template caches
            '**/__templates__/*',
            '**/template_cache/*',
        ],
        'css': [
            # Minified CSS
            '**/*.min.css',
            # Vendor/external
            '**/vendor/*',
            '**/node_modules/*',
            # Build outputs
            '**/dist/*',
            '**/build/*',
            # Generated CSS
            '**/*.generated.css',
            '**/css-modules/*',
        ],
    }

    # Test patterns (separate for easy toggling)
    _DEFAULT_TEST_PATTERNS: Dict[str, List[str]] = {
        'python': [
            '**/test_*.py',
            '**/*_test.py',
            '**/tests/*',
            '**/testing/*',
            '**/conftest.py',
        ],
        'javascript': [
            '**/*.test.js',
            '**/*.spec.js',
            '**/__tests__/*',
            '**/test/*',
        ],
        'typescript': [
            '**/*.test.ts',
            '**/*.test.tsx',
            '**/*.spec.ts',
            '**/*.spec.tsx',
            '**/__tests__/*',
            '**/test/*',
        ],
    }

    # =========================================================================
    # Runtime State (mutable)
    # =========================================================================

    _common_patterns: List[str] = []
    _language_patterns: Dict[str, List[str]] = {}
    _include_tests: bool = False  # Whether to index test files
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Initialize with defaults if not already done."""
        if not cls._initialized:
            cls.reset()

    @classmethod
    def reset(cls) -> None:
        """Reset to default patterns."""
        cls._common_patterns = list(cls._DEFAULT_COMMON)
        cls._language_patterns = {
            lang: list(patterns)
            for lang, patterns in cls._DEFAULT_LANGUAGE.items()
        }
        cls._include_tests = False
        cls._initialized = True

    # =========================================================================
    # Query Methods
    # =========================================================================

    @classmethod
    def get_common_patterns(cls) -> List[str]:
        """Get patterns applied to all languages."""
        cls._ensure_initialized()
        return list(cls._common_patterns)

    @classmethod
    def get_language_patterns(cls, language: str) -> List[str]:
        """Get patterns specific to a language."""
        cls._ensure_initialized()
        return list(cls._language_patterns.get(language, []))

    @classmethod
    def get_test_patterns(cls, language: str) -> List[str]:
        """Get test file patterns for a language."""
        return list(cls._DEFAULT_TEST_PATTERNS.get(language, []))

    @classmethod
    def get_patterns(cls, language: str, include_tests: bool = None) -> List[str]:
        """
        Get all exclude patterns for a language.

        Args:
            language: Language name (e.g., 'python', 'typescript')
            include_tests: Override for whether to exclude tests.
                          If None, uses class-level setting.

        Returns:
            Combined list of exclude patterns
        """
        cls._ensure_initialized()

        patterns: Set[str] = set()

        # Add common patterns
        patterns.update(cls._common_patterns)

        # Add language-specific patterns
        patterns.update(cls._language_patterns.get(language, []))

        # Add test patterns unless explicitly including tests
        should_exclude_tests = not (
            include_tests if include_tests is not None else cls._include_tests
        )
        if should_exclude_tests:
            patterns.update(cls._DEFAULT_TEST_PATTERNS.get(language, []))

        return sorted(patterns)

    @classmethod
    def get_all_patterns(cls) -> List[str]:
        """Get all patterns across all languages (deduplicated)."""
        cls._ensure_initialized()

        patterns: Set[str] = set()
        patterns.update(cls._common_patterns)

        for lang_patterns in cls._language_patterns.values():
            patterns.update(lang_patterns)

        if not cls._include_tests:
            for test_patterns in cls._DEFAULT_TEST_PATTERNS.values():
                patterns.update(test_patterns)

        return sorted(patterns)

    # =========================================================================
    # Modification Methods
    # =========================================================================

    @classmethod
    def add_common(cls, pattern: str) -> None:
        """Add a pattern to common exclusions."""
        cls._ensure_initialized()
        if pattern not in cls._common_patterns:
            cls._common_patterns.append(pattern)

    @classmethod
    def add_language(cls, language: str, pattern: str) -> None:
        """Add a pattern to language-specific exclusions."""
        cls._ensure_initialized()
        if language not in cls._language_patterns:
            cls._language_patterns[language] = []
        if pattern not in cls._language_patterns[language]:
            cls._language_patterns[language].append(pattern)

    @classmethod
    def remove_common(cls, pattern: str) -> bool:
        """Remove a pattern from common exclusions. Returns True if removed."""
        cls._ensure_initialized()
        if pattern in cls._common_patterns:
            cls._common_patterns.remove(pattern)
            return True
        return False

    @classmethod
    def remove_language(cls, language: str, pattern: str) -> bool:
        """Remove a pattern from language-specific exclusions. Returns True if removed."""
        cls._ensure_initialized()
        if language in cls._language_patterns and pattern in cls._language_patterns[language]:
            cls._language_patterns[language].remove(pattern)
            return True
        return False

    @classmethod
    def set_include_tests(cls, include: bool) -> None:
        """Set whether test files should be indexed."""
        cls._ensure_initialized()
        cls._include_tests = include

    @classmethod
    def include_tests_enabled(cls) -> bool:
        """Check if test files are being indexed."""
        cls._ensure_initialized()
        return cls._include_tests

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    @classmethod
    def add_common_bulk(cls, patterns: List[str]) -> None:
        """Add multiple patterns to common exclusions."""
        for pattern in patterns:
            cls.add_common(pattern)

    @classmethod
    def add_language_bulk(cls, language: str, patterns: List[str]) -> None:
        """Add multiple patterns to language-specific exclusions."""
        for pattern in patterns:
            cls.add_language(language, pattern)

    @classmethod
    def set_language_patterns(cls, language: str, patterns: List[str]) -> None:
        """Replace all patterns for a language."""
        cls._ensure_initialized()
        cls._language_patterns[language] = list(patterns)

    # =========================================================================
    # Inspection
    # =========================================================================

    @classmethod
    def supported_languages(cls) -> List[str]:
        """Get list of languages with configured patterns."""
        cls._ensure_initialized()
        return sorted(set(cls._language_patterns.keys()) | set(cls._DEFAULT_TEST_PATTERNS.keys()))

    @classmethod
    def summary(cls) -> Dict[str, any]:
        """Get summary of current configuration."""
        cls._ensure_initialized()
        return {
            'common_count': len(cls._common_patterns),
            'languages': {
                lang: len(patterns)
                for lang, patterns in cls._language_patterns.items()
            },
            'include_tests': cls._include_tests,
        }
