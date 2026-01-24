"""
Shared pytest fixtures for Babel test suite.

Provides common fixtures using the BabelTestFactory pattern for
CI-compatible testing without external database dependencies.

Usage in tests:
    def test_something(babel_factory):
        babel_factory.add_decision("Test decision")
        cli = babel_factory.create_cli_mock()
        # ... test with real stores

    def test_with_data(babel_env):
        # babel_env comes pre-populated with sample data
        cli = babel_env.create_cli_mock()
        # ... test with existing artifacts
"""

import pytest
from tests.factories import BabelTestFactory


@pytest.fixture
def babel_factory(tmp_path):
    """
    Create an empty BabelTestFactory instance.

    Use this when you need fine-grained control over test data.
    The factory provides real EventStore and GraphStore backed
    by temp files that are cleaned up after each test.

    Example:
        def test_decision_creation(babel_factory):
            babel_factory.add_purpose("Test purpose")
            decision_id = babel_factory.add_decision("Use SQLite")
            cli = babel_factory.create_cli_mock()
            # ... test with the decision
    """
    return BabelTestFactory(tmp_path)


@pytest.fixture
def babel_env(tmp_path):
    """
    Create a BabelTestFactory with sample project data.

    Pre-populated with:
    - 1 purpose
    - 3 decisions
    - 2 constraints
    - 1 principle

    All artifacts are linked to the purpose.

    Example:
        def test_list_decisions(babel_env):
            cli = babel_env.create_cli_mock()
            decisions = cli.graph.get_nodes_by_type("decision")
            assert len(decisions) == 3
    """
    factory = BabelTestFactory(tmp_path)
    factory.create_sample_project()
    return factory


@pytest.fixture
def mock_cli(babel_factory):
    """
    Create a mock CLI instance with empty stores.

    Convenience fixture for tests that just need a CLI mock
    without pre-populating data.

    Example:
        def test_empty_project(mock_cli):
            decisions = mock_cli.graph.get_nodes_by_type("decision")
            assert len(decisions) == 0
    """
    return babel_factory.create_cli_mock()
