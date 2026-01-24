"""
Test Data Factory — CI-compatible test data creation for Babel commands

Provides declarative test data creation without external database dependencies.
Uses tmp_path fixtures with temp SQLite stores for isolation.

Aligns with:
- P5: Tests ARE evidence for implementation
- P11: Self-application (dogfooding Babel's own systems)
- HC2: Human authority (tests verify user-facing commands)

Usage:
    @pytest.fixture
    def babel_env(tmp_path):
        factory = BabelTestFactory(tmp_path)
        factory.add_purpose("Test purpose")
        factory.add_decision("Use SQLite", domain="database")
        return factory

    def test_something(babel_env):
        cli = babel_env.create_cli_mock()
        cmd = babel_env.create_command(SomeCommand)
        # ... test command behavior
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from unittest.mock import Mock

from babel.core.events import (
    EventStore,
    DualEventStore,
    declare_purpose,
    confirm_artifact,
    propose_structure,
    raise_question,
    resolve_question,
    raise_challenge,
)
from babel.core.graph import GraphStore, Edge
from babel.config import Config
from babel.presentation.codec import IDCodec
from babel.presentation.symbols import get_symbols


class BabelTestFactory:
    """
    Factory for creating test Babel environments.

    Creates isolated .babel/ directory structure with real EventStore
    and GraphStore backed by temp files. Provides helper methods for
    adding test data and creating command instances.

    All data is isolated per test via pytest's tmp_path fixture.
    Works in CI environments (GitHub Actions) without external dependencies.
    """

    def __init__(self, tmp_path: Path):
        """
        Initialize factory with temporary directory.

        Args:
            tmp_path: pytest tmp_path fixture for isolated temp directory
        """
        self.tmp_path = tmp_path
        self.babel_dir = tmp_path / ".babel"
        self.babel_dir.mkdir(parents=True, exist_ok=True)
        (self.babel_dir / "shared").mkdir(exist_ok=True)
        (self.babel_dir / "local").mkdir(exist_ok=True)

        # Initialize real stores (temp files, not mocks)
        # Use DualEventStore for scope support (shared/local)
        self.events = DualEventStore(self.tmp_path)
        self.graph = GraphStore(self.babel_dir / "graph.db")
        self.config = Config()
        self.codec = IDCodec()
        self.symbols = get_symbols()

        # Track created artifacts for later reference
        self._artifacts: Dict[str, Any] = {}
        self._purpose_id: Optional[str] = None

    # =========================================================================
    # Artifact Creation Methods
    # =========================================================================

    def add_purpose(self, purpose: str, need: str = "Test need") -> str:
        """
        Add a purpose to the project.

        Args:
            purpose: The purpose statement
            need: The need this purpose addresses

        Returns:
            The purpose node ID
        """
        event = declare_purpose(purpose, need=need)
        self.events.append(event)
        self.graph._project_event(event)

        # Get the created node ID
        purposes = self.graph.get_nodes_by_type("purpose")
        if purposes:
            self._purpose_id = purposes[-1].id
            return self._purpose_id
        return event.id

    def add_decision(
        self,
        summary: str,
        domain: str = "",
        what: Optional[str] = None,
        why: str = "Test reason",
        link_to_purpose: bool = True
    ) -> str:
        """
        Add a decision artifact.

        Args:
            summary: Decision summary
            domain: Domain/area this applies to
            what: Detailed what (defaults to summary)
            why: Reasoning for the decision
            link_to_purpose: Whether to link to purpose (if exists)

        Returns:
            The decision node ID
        """
        return self._add_artifact(
            artifact_type="decision",
            summary=summary,
            domain=domain,
            what=what or summary,
            why=why,
            link_to_purpose=link_to_purpose
        )

    def add_constraint(
        self,
        summary: str,
        domain: str = "",
        what: Optional[str] = None,
        why: str = "Test constraint reason",
        link_to_purpose: bool = True
    ) -> str:
        """
        Add a constraint artifact.

        Args:
            summary: Constraint summary
            domain: Domain/area this applies to
            what: Detailed what (defaults to summary)
            why: Reasoning for the constraint
            link_to_purpose: Whether to link to purpose (if exists)

        Returns:
            The constraint node ID
        """
        return self._add_artifact(
            artifact_type="constraint",
            summary=summary,
            domain=domain,
            what=what or summary,
            why=why,
            link_to_purpose=link_to_purpose
        )

    def add_principle(
        self,
        summary: str,
        domain: str = "",
        what: Optional[str] = None,
        why: str = "Test principle reason",
        link_to_purpose: bool = True
    ) -> str:
        """
        Add a principle artifact.

        Args:
            summary: Principle summary
            domain: Domain/area this applies to
            what: Detailed what (defaults to summary)
            why: Reasoning for the principle
            link_to_purpose: Whether to link to purpose (if exists)

        Returns:
            The principle node ID
        """
        return self._add_artifact(
            artifact_type="principle",
            summary=summary,
            domain=domain,
            what=what or summary,
            why=why,
            link_to_purpose=link_to_purpose
        )

    def add_proposal(
        self,
        summary: str,
        artifact_type: str = "decision",
        domain: str = "",
        rationale: str = "Test rationale",
        confidence: float = 0.9
    ) -> str:
        """
        Add a pending proposal (STRUCTURE_PROPOSED event).

        Proposals are pending artifacts that need review before becoming
        confirmed artifacts. Used for testing the review command.

        Args:
            summary: Proposal summary
            artifact_type: Type of artifact (decision, constraint, principle)
            domain: Domain/area this applies to
            rationale: Why this proposal was made
            confidence: Extraction confidence (0.0-1.0)

        Returns:
            The proposal event ID
        """
        proposed = {
            "type": artifact_type,
            "summary": summary,
            "domain": domain,
            "rationale": rationale
        }

        event = propose_structure(
            source_id=f"source_{hash(summary) & 0xFFFFFF:06x}",
            proposed=proposed,
            confidence=confidence
        )
        self.events.append(event)
        self.graph._project_event(event)

        return event.id

    def add_question(
        self,
        question: str,
        domain: str = "",
        resolved: bool = False,
        resolution: Optional[str] = None
    ) -> str:
        """
        Add a question (uncertainty).

        Args:
            question: The question text
            domain: Domain/area this applies to
            resolved: Whether to also resolve the question
            resolution: Resolution text (if resolved=True)

        Returns:
            The question event ID
        """
        event = raise_question(question, domain=domain)
        self.events.append(event)
        self.graph._project_event(event)

        question_id = event.id

        if resolved and resolution:
            resolve_event = resolve_question(question_id, resolution)
            self.events.append(resolve_event)
            self.graph._project_event(resolve_event)

        return question_id

    def add_tension(
        self,
        target_id: str,
        reason: str,
        domain: str = ""
    ) -> str:
        """
        Add a tension (challenge) against an existing artifact.

        Args:
            target_id: ID of artifact to challenge
            reason: Reason for the challenge
            domain: Domain expertise

        Returns:
            The tension event ID
        """
        event = raise_challenge(
            target_id=target_id,
            reason=reason,
            challenger="test",
            domain=domain
        )
        self.events.append(event)
        self.graph._project_event(event)

        return event.id

    def _add_artifact(
        self,
        artifact_type: str,
        summary: str,
        domain: str,
        what: str,
        why: str,
        link_to_purpose: bool
    ) -> str:
        """Internal helper to add any artifact type."""
        # Generate unique proposal ID based on content hash
        proposal_id = f"prop_{hash(summary) & 0xFFFFFF:06x}"

        content = {
            "summary": summary,
            "domain": domain,
            "detail": {"what": what, "why": why}
        }

        event = confirm_artifact(
            proposal_id=proposal_id,
            artifact_type=artifact_type,
            content=content
        )
        self.events.append(event)
        self.graph._project_event(event)

        # Get the created node
        nodes = self.graph.get_nodes_by_type(artifact_type)
        node_id = nodes[-1].id if nodes else event.id

        # Track artifact
        self._artifacts[node_id] = {
            "type": artifact_type,
            "summary": summary,
            "event": event
        }

        # Link to purpose if requested and purpose exists
        if link_to_purpose and self._purpose_id:
            self.link_artifacts(self._purpose_id, node_id)

        return node_id

    def link_artifacts(self, source_id: str, target_id: str, relation: str = "informs") -> None:
        """
        Create a link between two artifacts.

        Args:
            source_id: Source artifact ID
            target_id: Target artifact ID
            relation: Relationship type (default: "informs")
        """
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            event_id=f"link_{hash(source_id + target_id) & 0xFFFFFF:06x}"
        )
        self.graph.add_edge(edge)

    # =========================================================================
    # CLI Mock Creation
    # =========================================================================

    def create_cli_mock(self) -> Mock:
        """
        Create a mock CLI with real stores.

        Returns a Mock object configured with:
        - Real graph and event stores (from tmp_path)
        - Real IDCodec and Symbols
        - Proper format_id() method
        - Mock resolver

        Returns:
            Configured Mock CLI instance
        """
        cli = Mock()
        cli.babel_dir = self.babel_dir
        cli.project_dir = self.tmp_path
        cli.graph = self.graph
        cli.events = self.events
        cli.config = self.config
        cli.codec = self.codec
        cli.symbols = self.symbols

        # Real format_id method
        cli.format_id = lambda node_id: f"[{self.codec.encode(node_id)}]"

        # Mock resolver (can be overridden per test)
        cli.resolver = Mock()

        # Mock _is_deprecated (returns None = not deprecated)
        cli._is_deprecated = Mock(return_value=None)

        # Mock _get_active_purpose (returns None = no auto-linking)
        cli._get_active_purpose = Mock(return_value=None)

        # Mock refs with index_event (does nothing in tests)
        cli.refs = Mock()
        cli.refs.index_event = Mock()

        # Mock vocabulary (used by refs)
        cli.vocabulary = Mock()

        # Mock validation with register_decision (does nothing in tests)
        cli.validation = Mock()
        cli.validation.register_decision = Mock()

        return cli

    def create_command(self, command_class, cli: Optional[Mock] = None):
        """
        Create a command instance with proper initialization.

        Args:
            command_class: The command class to instantiate
            cli: Optional pre-configured CLI mock (creates one if not provided)

        Returns:
            Configured command instance
        """
        if cli is None:
            cli = self.create_cli_mock()

        # Create command using __new__ to bypass __init__
        cmd = command_class.__new__(command_class)
        cmd._cli = cli

        return cmd

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def create_sample_project(
        self,
        purpose: str = "Test project for CI validation",
        decisions: int = 3,
        constraints: int = 2,
        principles: int = 1
    ) -> None:
        """
        Create a sample project with typical artifacts.

        Useful for quickly setting up test environments.

        Args:
            purpose: Project purpose statement
            decisions: Number of decisions to create
            constraints: Number of constraints to create
            principles: Number of principles to create
        """
        self.add_purpose(purpose)

        for i in range(decisions):
            self.add_decision(
                summary=f"Decision {i}: Test decision for validation",
                domain=f"domain_{i % 3}",
                why=f"Reason {i} for testing"
            )

        for i in range(constraints):
            self.add_constraint(
                summary=f"Constraint {i}: Test constraint",
                domain=f"domain_{i % 2}",
                why=f"Constraint reason {i}"
            )

        for i in range(principles):
            self.add_principle(
                summary=f"Principle {i}: Guiding test principle",
                domain="testing",
                why=f"Principle reason {i}"
            )

    def get_artifact_ids(self, artifact_type: Optional[str] = None) -> List[str]:
        """
        Get IDs of created artifacts.

        Args:
            artifact_type: Optional filter by type (decision, constraint, etc.)

        Returns:
            List of artifact IDs
        """
        if artifact_type:
            return [
                aid for aid, info in self._artifacts.items()
                if info["type"] == artifact_type
            ]
        return list(self._artifacts.keys())

    @property
    def purpose_id(self) -> Optional[str]:
        """Get the project purpose ID (if created)."""
        return self._purpose_id


# =============================================================================
# Pytest Fixtures (for conftest.py import)
# =============================================================================

def create_babel_factory(tmp_path: Path) -> BabelTestFactory:
    """
    Factory function for creating BabelTestFactory.

    Can be used in conftest.py:
        from tests.factories import create_babel_factory

        @pytest.fixture
        def babel_env(tmp_path):
            return create_babel_factory(tmp_path)
    """
    return BabelTestFactory(tmp_path)


def create_sample_project(tmp_path: Path) -> BabelTestFactory:
    """
    Create a factory with sample project data pre-populated.

    Can be used in conftest.py:
        from tests.factories import create_sample_project

        @pytest.fixture
        def populated_project(tmp_path):
            return create_sample_project(tmp_path)
    """
    factory = BabelTestFactory(tmp_path)
    factory.create_sample_project()
    return factory
