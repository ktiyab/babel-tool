"""
BaseCommand — Shared foundation for all CLI commands

Provides access to CLI resources via composition.
Commands receive the CLI instance and access its resources through properties.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cli import IntentCLI


class BaseCommand:
    """
    Base class for CLI commands with access to shared resources.

    Design principle: Composition over inheritance.
    Commands don't reinitialize resources — they access them via the CLI instance.
    """

    def __init__(self, cli: 'IntentCLI'):
        """
        Initialize command with CLI instance.

        Args:
            cli: The main IntentCLI instance holding all resources
        """
        self._cli = cli

    # -------------------------------------------------------------------------
    # Core resources (convenience properties)
    # -------------------------------------------------------------------------

    @property
    def project_dir(self):
        """Project root directory."""
        return self._cli.project_dir

    @property
    def babel_dir(self):
        """Babel data directory (.babel/)."""
        return self._cli.babel_dir

    @property
    def events(self):
        """Event store (DualEventStore)."""
        return self._cli.events

    @property
    def graph(self):
        """Graph store for artifacts and connections."""
        return self._cli.graph

    @property
    def refs(self):
        """Reference store for O(1) lookup."""
        return self._cli.refs

    @property
    def config(self):
        """Application configuration."""
        return self._cli.config

    @property
    def symbols(self):
        """Symbol set for display (Unicode/ASCII)."""
        return self._cli.symbols

    # -------------------------------------------------------------------------
    # Services (convenience properties)
    # -------------------------------------------------------------------------

    @property
    def provider(self):
        """LLM provider for AI operations."""
        return self._cli.provider

    @property
    def extractor(self):
        """Extractor for intent extraction."""
        return self._cli.extractor

    @property
    def loader(self):
        """Lazy loader for token-efficient context."""
        return self._cli.loader

    @property
    def vocabulary(self):
        """Vocabulary for semantic understanding."""
        return self._cli.vocabulary

    @property
    def coherence(self):
        """Coherence checker."""
        return self._cli.coherence

    @property
    def scanner(self):
        """Scanner for technical advice."""
        return self._cli.scanner

    @property
    def tensions(self):
        """Tension tracker for disagreements (P4)."""
        return self._cli.tensions

    @property
    def validation(self):
        """Validation tracker for dual-test truth (P9)."""
        return self._cli.validation

    @property
    def questions(self):
        """Question tracker for ambiguity (P10)."""
        return self._cli.questions

    @property
    def resolver(self):
        """ID resolver for fuzzy artifact lookup."""
        return self._cli.resolver

    @property
    def memos(self):
        """Memo manager for user preferences (P6)."""
        return self._cli.memos
