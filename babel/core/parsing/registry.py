"""
Parser Registry — Routes files to language-specific configurations.

Central registry that maps file extensions to LanguageConfig instances.
Enables adding new language support without modifying core code.

Usage:
    registry = ParserRegistry()
    registry.register(PYTHON_CONFIG)
    registry.register(TYPESCRIPT_CONFIG)

    config = registry.get_config(Path("src/app.tsx"))
    # Returns TYPESCRIPT_CONFIG
"""

from pathlib import Path
from typing import Dict, Optional, Set, List

from .config import LanguageConfig


class ParserRegistry:
    """
    Registry of language configurations.

    Maps file extensions to LanguageConfig instances for routing.
    Provides unified access to supported extensions and exclude patterns.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._configs: Dict[str, LanguageConfig] = {}  # name -> config
        self._extension_map: Dict[str, str] = {}  # ext -> config name

    def register(self, config: LanguageConfig) -> None:
        """
        Register a language configuration.

        Args:
            config: LanguageConfig to register

        Raises:
            ValueError: If extension already registered to different config
        """
        # Check for extension conflicts
        for ext in config.extensions:
            ext_lower = ext.lower()
            if ext_lower in self._extension_map:
                existing = self._extension_map[ext_lower]
                if existing != config.name:
                    raise ValueError(
                        f"Extension {ext} already registered to {existing}, "
                        f"cannot register to {config.name}"
                    )

        # Register config
        self._configs[config.name] = config
        for ext in config.extensions:
            self._extension_map[ext.lower()] = config.name

    def unregister(self, name: str) -> bool:
        """
        Unregister a language configuration by name.

        Args:
            name: Config name to unregister

        Returns:
            True if unregistered, False if not found
        """
        if name not in self._configs:
            return False

        config = self._configs[name]

        # Remove extension mappings
        for ext in config.extensions:
            ext_lower = ext.lower()
            if self._extension_map.get(ext_lower) == name:
                del self._extension_map[ext_lower]

        del self._configs[name]
        return True

    def get_config(self, file_path: Path) -> Optional[LanguageConfig]:
        """
        Get language config for a file based on extension.

        Args:
            file_path: Path to file

        Returns:
            LanguageConfig if extension is supported, None otherwise
        """
        ext = file_path.suffix.lower()
        config_name = self._extension_map.get(ext)
        return self._configs.get(config_name) if config_name else None

    def get_config_by_name(self, name: str) -> Optional[LanguageConfig]:
        """
        Get language config by name.

        Args:
            name: Config name (e.g., "Python", "TypeScript")

        Returns:
            LanguageConfig if found, None otherwise
        """
        return self._configs.get(name)

    def supported_extensions(self) -> Set[str]:
        """
        Get all supported file extensions.

        Returns:
            Set of extensions (e.g., {'.py', '.ts', '.tsx'})
        """
        return set(self._extension_map.keys())

    def supported_languages(self) -> List[str]:
        """
        Get list of registered language names.

        Returns:
            List of language names (e.g., ["Python", "TypeScript"])
        """
        return list(self._configs.keys())

    def all_exclude_patterns(self) -> List[str]:
        """
        Get combined exclude patterns from all registered configs.

        Returns:
            Deduplicated list of exclude patterns
        """
        patterns = set()
        for config in self._configs.values():
            patterns.update(config.exclude_patterns)
        return list(patterns)

    def glob_patterns_for_indexing(self) -> List[str]:
        """
        Get glob patterns for all supported file types.

        Returns:
            List of glob patterns (e.g., ["**/*.py", "**/*.ts", "**/*.tsx"])
        """
        return [f"**/*{ext}" for ext in self.supported_extensions()]

    def is_supported(self, file_path: Path) -> bool:
        """
        Check if a file type is supported.

        Args:
            file_path: Path to check

        Returns:
            True if extension is registered
        """
        return file_path.suffix.lower() in self._extension_map

    def __len__(self) -> int:
        """Return number of registered configs."""
        return len(self._configs)

    def __contains__(self, name: str) -> bool:
        """Check if a config name is registered."""
        return name in self._configs
