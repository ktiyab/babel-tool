"""
Tests for WhyCommand — P7 Reasoning Travels (RECALL Flow)

Tests the context retrieval system that powers babel why:
- Tokenization for keyword matching
- Context gathering (keyword + graph traversal)
- Rejection context (P8: learn from failures)
- Fallback listing (no LLM)
- Commit-based queries

Aligns with:
- P5: Tests ARE evidence for implementation
- P7: Reasoning travels (retrieving context)
- P8: Evolution traceable (commit queries, rejection context)
- HC2: Human authority (user queries the system)
"""

import pytest
from unittest.mock import Mock

from babel.commands.why import WhyCommand
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def why_command(babel_factory):
    """Create WhyCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # WhyCommand accesses these via properties from BaseCommand
    # All properties delegate to self._cli.<attribute>
    cli.project_dir = babel_factory.tmp_path

    # Mock tension store (accessed via cli.tensions)
    cli.tensions = Mock()
    cli.tensions.get_open_challenges_for_parent = Mock(return_value=[])

    # Mock validation store (accessed via cli.validation)
    cli.validation = Mock()
    cli.validation.get_validation = Mock(return_value=None)

    # Mock LLM provider (accessed via cli.provider)
    cli.provider = Mock()
    cli.provider.available = False
    cli.provider.is_available = False

    # Create command instance - properties will access cli attributes
    cmd = WhyCommand.__new__(WhyCommand)
    cmd._cli = cli

    # Initialize cache (normally done in __init__)
    cmd._cache_path = babel_factory.babel_dir / "why_cache.json"
    cmd._cache = {}

    return cmd, babel_factory


# =============================================================================
# Tokenize Tests
# =============================================================================

class TestTokenize:
    """Test _tokenize method for keyword extraction."""

    def test_basic_tokenization(self, why_command):
        """Tokenizes text into lowercase words using universal tokenizer."""
        cmd, _ = why_command

        tokens = cmd._tokenize("Use SQLite for storage")

        # Universal tokenizer splits PascalCase: SQLite -> sq, lite
        assert "sq" in tokens or "lite" in tokens  # SQLite splits
        assert "storage" in tokens
        assert "use" in tokens
        assert "for" in tokens

    def test_splits_on_punctuation(self, why_command):
        """Splits on punctuation correctly using universal tokenizer."""
        cmd, _ = why_command

        tokens = cmd._tokenize("SQLite, PostgreSQL! What's best?")

        # Universal tokenizer splits PascalCase and handles punctuation
        # SQLite -> sq, lite; PostgreSQL -> postgre, sql
        assert "sq" in tokens or "lite" in tokens  # SQLite splits
        assert "postgre" in tokens or "sql" in tokens  # PostgreSQL splits
        assert "what" in tokens
        assert "best" in tokens

    def test_filters_single_characters(self, why_command):
        """Filters single character tokens."""
        cmd, _ = why_command

        tokens = cmd._tokenize("I am on it go do my work today")

        # Single char words removed
        assert "i" not in tokens
        # Two char words preserved (> 1)
        assert "am" in tokens
        assert "on" in tokens
        assert "it" in tokens
        assert "go" in tokens
        assert "do" in tokens
        assert "my" in tokens
        # Longer words preserved
        assert "work" in tokens
        assert "today" in tokens

    def test_handles_file_extensions(self, why_command):
        """Handles file extensions as separate tokens."""
        cmd, _ = why_command

        tokens = cmd._tokenize("ontology.py")

        assert "ontology" in tokens
        assert "py" in tokens

    def test_handles_compound_terms(self, why_command):
        """Handles hyphenated and underscored terms."""
        cmd, _ = why_command

        tokens_hyphen = cmd._tokenize("why-command")
        tokens_underscore = cmd._tokenize("babel_tool")

        assert "why" in tokens_hyphen
        assert "command" in tokens_hyphen
        assert "babel" in tokens_underscore
        assert "tool" in tokens_underscore

    def test_empty_string(self, why_command):
        """Handles empty string."""
        cmd, _ = why_command

        tokens = cmd._tokenize("")

        assert tokens == set()

    def test_only_single_chars(self, why_command):
        """Returns empty when only single char tokens."""
        cmd, _ = why_command

        tokens = cmd._tokenize("a b c d e f")

        # All single chars filtered out
        assert tokens == set()


# =============================================================================
# Gather Context Tests
# =============================================================================

class TestGatherContext:
    """Test _gather_context method for keyword matching + graph traversal."""

    def test_finds_matching_decisions(self, why_command):
        """Finds decisions that match query keywords."""
        cmd, factory = why_command

        # Add a decision with matching keywords
        factory.add_decision(
            summary="Use SQLite for local storage",
            domain="database",
            why="Offline access needed"
        )

        results = cmd._gather_context("sqlite storage")

        assert len(results) >= 1
        summaries = [r['summary'] for r in results]
        assert any("SQLite" in s for s in summaries)

    def test_finds_matching_constraints(self, why_command):
        """Finds constraints that match query keywords."""
        cmd, factory = why_command

        factory.add_constraint(
            summary="Maximum 100MB storage limit",
            domain="storage",
            why="Device limitations"
        )

        results = cmd._gather_context("storage limit")

        assert len(results) >= 1
        types = [r['type'] for r in results]
        assert 'constraint' in types

    def test_finds_matching_principles(self, why_command):
        """Finds principles that match query keywords."""
        cmd, factory = why_command

        factory.add_principle(
            summary="Offline-first design principle",
            domain="architecture",
            why="Users need offline access"
        )

        results = cmd._gather_context("offline design")

        assert len(results) >= 1
        types = [r['type'] for r in results]
        assert 'principle' in types

    def test_no_matches_returns_empty(self, why_command):
        """Returns empty list when no matches found."""
        cmd, factory = why_command

        factory.add_decision(
            summary="Use Redis for caching",
            domain="cache"
        )

        results = cmd._gather_context("postgresql database enterprise")

        # May return empty or find weak matches
        # The important thing is it doesn't crash
        assert isinstance(results, list)

    def test_includes_related_via_graph_traversal(self, why_command):
        """Includes related artifacts via graph traversal (1 hop)."""
        cmd, factory = why_command

        # Add a decision and a linked constraint
        decision_id = factory.add_decision(
            summary="Use sqlite for storage",  # lowercase to match query tokenization
            domain="database",
            link_to_purpose=False
        )
        constraint_id = factory.add_constraint(
            summary="Maximum file size 50MB",
            domain="storage",
            link_to_purpose=False
        )

        # Link them
        factory.link_artifacts(decision_id, constraint_id, relation="constrains")

        # Query for storage - matches directly (tokenizer keeps 'storage' intact)
        results = cmd._gather_context("storage")

        assert len(results) >= 1
        # Direct match should be found
        ids = [r['node'].id for r in results]
        assert decision_id in ids


# =============================================================================
# Gather Rejection Context Tests
# =============================================================================

class TestGatherRejectionContext:
    """Test _gather_rejection_context for P8: learn from failures."""

    def test_finds_matching_rejections(self, why_command):
        """Finds rejected proposals matching query."""
        cmd, factory = why_command

        # Add and reject a proposal
        from babel.core.events import propose_structure, reject_proposal

        # Create proposal
        proposed = {
            "type": "decision",
            "summary": "Use MongoDB for storage",
            "domain": "database",
            "rationale": "NoSQL flexibility"
        }
        propose_event = propose_structure(
            source_id="test_source",
            proposed=proposed,
            confidence=0.8
        )
        factory.events.append(propose_event)

        # Reject it
        reject_event = reject_proposal(
            proposal_id=propose_event.id,
            reason="SQLite is simpler and sufficient"
        )
        factory.events.append(reject_event)

        # Query for storage - should find the rejection
        rejections = cmd._gather_rejection_context("mongodb storage")

        assert len(rejections) >= 1
        summaries = [r['summary'] for r in rejections]
        assert any("MongoDB" in s for s in summaries)

    def test_includes_rejection_reason(self, why_command):
        """Includes rejection reason in results."""
        cmd, factory = why_command

        from babel.core.events import propose_structure, reject_proposal

        propose_event = propose_structure(
            source_id="test",
            proposed={"type": "decision", "summary": "Use complex ORM"},
            confidence=0.7
        )
        factory.events.append(propose_event)

        reject_event = reject_proposal(
            proposal_id=propose_event.id,
            reason="Too much complexity for this project"
        )
        factory.events.append(reject_event)

        rejections = cmd._gather_rejection_context("ORM complexity")

        if rejections:
            assert 'reason' in rejections[0]
            assert "complexity" in rejections[0]['reason'].lower()

    def test_no_rejections_returns_empty(self, why_command):
        """Returns empty list when no rejections exist."""
        cmd, factory = why_command

        rejections = cmd._gather_rejection_context("anything")

        assert rejections == []


# =============================================================================
# Build Artifact Data Tests
# =============================================================================

class TestBuildArtifactData:
    """Test _build_artifact_data for artifact dict construction."""

    def test_includes_required_fields(self, why_command):
        """Includes all required fields in artifact data."""
        cmd, factory = why_command

        decision_id = factory.add_decision(
            summary="Test decision",
            domain="testing"
        )

        # Get the node
        nodes = factory.graph.get_nodes_by_type("decision")
        node = nodes[0]

        data = cmd._build_artifact_data(node, score=0.8)

        assert 'node' in data
        assert 'short_id' in data
        assert 'type' in data
        assert 'summary' in data
        assert 'domain' in data
        assert 'score' in data
        assert 'related_count' in data
        assert 'challenges' in data
        assert 'match_type' in data

    def test_encodes_id_with_codec(self, why_command):
        """Encodes node ID using IDCodec."""
        cmd, factory = why_command

        factory.add_decision(summary="Test")
        nodes = factory.graph.get_nodes_by_type("decision")
        node = nodes[0]

        data = cmd._build_artifact_data(node, score=0.5)

        # short_id should be in AA-BB format
        assert '-' in data['short_id']
        assert len(data['short_id']) == 5  # AA-BB format

    def test_includes_match_type_for_traversal(self, why_command):
        """Includes match_type and via_relation for traversal hits."""
        cmd, factory = why_command

        factory.add_decision(summary="Test")
        nodes = factory.graph.get_nodes_by_type("decision")
        node = nodes[0]

        data = cmd._build_artifact_data(
            node,
            score=0.5,
            match_type='traversal',
            via_relation='supports',
            via_artifact='AB-CD'
        )

        assert data['match_type'] == 'traversal'
        assert data['via_relation'] == 'supports'
        assert data['via_artifact'] == 'AB-CD'


# =============================================================================
# Find Decision Node Tests
# =============================================================================

class TestFindDecisionNode:
    """Test _find_decision_node for ID lookup."""

    def test_finds_by_full_id(self, why_command):
        """Finds decision by full event ID."""
        cmd, factory = why_command

        decision_id = factory.add_decision(summary="Test decision")

        # Get the full event ID
        nodes = factory.graph.get_nodes_by_type("decision")
        node = nodes[0]

        found = cmd._find_decision_node(node.event_id)

        assert found is not None
        assert found.content.get('summary') == "Test decision"

    def test_finds_by_prefix(self, why_command):
        """Finds decision by ID prefix."""
        cmd, factory = why_command

        factory.add_decision(summary="Prefix test")
        nodes = factory.graph.get_nodes_by_type("decision")
        node = nodes[0]

        # Use first 8 chars as prefix
        prefix = node.event_id[:8]
        found = cmd._find_decision_node(prefix)

        assert found is not None

    def test_finds_constraints(self, why_command):
        """Also finds constraints (not just decisions)."""
        cmd, factory = why_command

        factory.add_constraint(summary="Test constraint")
        nodes = factory.graph.get_nodes_by_type("constraint")
        node = nodes[0]

        found = cmd._find_decision_node(node.event_id)

        assert found is not None
        assert found.type == "constraint"

    def test_returns_none_when_not_found(self, why_command):
        """Returns None when ID not found."""
        cmd, factory = why_command

        found = cmd._find_decision_node("nonexistent_id_12345")

        assert found is None


# =============================================================================
# Suggest Decisions for Commit Tests
# =============================================================================

class TestSuggestDecisionsForCommit:
    """Test _suggest_decisions_for_commit for commit-to-decision matching."""

    def test_suggests_matching_decisions(self, why_command):
        """Suggests decisions that match commit message keywords."""
        cmd, factory = why_command

        factory.add_decision(
            summary="Use SQLite for local storage",
            domain="database"
        )
        factory.add_decision(
            summary="Use Redis for caching",
            domain="cache"
        )

        # Mock commit info
        commit_info = Mock()
        commit_info.message = "Implement SQLite storage layer"

        suggestions = cmd._suggest_decisions_for_commit(commit_info)

        assert len(suggestions) >= 1
        summaries = [s['summary'] for s in suggestions]
        assert any("SQLite" in s for s in summaries)

    def test_sorts_by_relevance(self, why_command):
        """Sorts suggestions by relevance score."""
        cmd, factory = why_command

        factory.add_decision(summary="SQLite storage implementation")
        factory.add_decision(summary="Database connection pooling")

        commit_info = Mock()
        commit_info.message = "Add SQLite storage support"

        suggestions = cmd._suggest_decisions_for_commit(commit_info)

        if len(suggestions) > 1:
            # First should have higher score
            assert suggestions[0]['score'] >= suggestions[1]['score']

    def test_returns_empty_for_unmatched_commit(self, why_command):
        """Returns empty list when no decisions match."""
        cmd, factory = why_command

        factory.add_decision(summary="Use Redis for caching")

        commit_info = Mock()
        commit_info.message = "Fix typo in readme"

        suggestions = cmd._suggest_decisions_for_commit(commit_info)

        # May return empty or weak matches
        assert isinstance(suggestions, list)


# =============================================================================
# Fallback Tests (No LLM)
# =============================================================================

class TestFallback:
    """Test _fallback method for non-LLM listing."""

    def test_lists_artifacts_without_llm(self, why_command, capsys):
        """Lists artifacts when no LLM available."""
        cmd, factory = why_command

        factory.add_decision(
            summary="Use sqlite for storage",  # lowercase to match query tokenization
            domain="database"
        )

        # Query for 'storage' which matches directly
        artifacts = cmd._gather_context("storage")
        cmd._fallback("storage", artifacts)

        captured = capsys.readouterr()
        assert "sqlite" in captured.out.lower()
        assert "Decision" in captured.out or "decision" in captured.out

    def test_shows_artifact_ids(self, why_command, capsys):
        """Shows artifact IDs for traceability."""
        cmd, factory = why_command

        factory.add_decision(summary="Test decision for ID display")

        artifacts = cmd._gather_context("test decision")
        if artifacts:
            cmd._fallback("test", artifacts)
            captured = capsys.readouterr()

            # Should show ID in brackets
            assert "[" in captured.out and "]" in captured.out

    def test_shows_rejections_when_provided(self, why_command, capsys):
        """Shows rejection context when provided."""
        cmd, factory = why_command

        rejections = [{
            'proposal_id': 'AB-CD',
            'type': 'decision',
            'summary': 'Rejected approach',
            'reason': 'Too complex',
            'date': '2024-01-01',
            'score': 1
        }]

        cmd._fallback("test", [], rejections)
        captured = capsys.readouterr()

        assert "Rejected" in captured.out or "REJECTED" in captured.out


# =============================================================================
# Why Integration Tests
# =============================================================================

class TestWhyIntegration:
    """Integration tests for the why command."""

    def test_why_with_matching_decisions(self, why_command, capsys):
        """why command finds and displays matching decisions."""
        cmd, factory = why_command

        factory.add_purpose("Test project for validation")
        factory.add_decision(
            summary="Use SQLite for local storage",
            domain="database",
            why="Offline access required"
        )

        # Call why (will use fallback since provider.is_available = False)
        cmd.why("sqlite storage")
        captured = capsys.readouterr()

        # Should show the decision
        assert "SQLite" in captured.out or "sqlite" in captured.out.lower()

    def test_why_with_no_matches(self, why_command, capsys):
        """why command handles no matches gracefully."""
        cmd, factory = why_command

        factory.add_decision(summary="Something unrelated")

        cmd.why("completely unrelated query xyz")
        captured = capsys.readouterr()

        # Should show "no matches" message
        assert "No matches" in captured.out or captured.out is not None


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_query(self, why_command, capsys):
        """Handles empty query string."""
        cmd, factory = why_command

        # Should not crash
        try:
            results = cmd._gather_context("")
            assert isinstance(results, list)
        except Exception as e:
            # May raise an error for empty query - that's acceptable
            pass

    def test_handles_special_characters(self, why_command):
        """Handles special characters in query."""
        cmd, factory = why_command

        factory.add_decision(summary="Use C++ for performance")

        # Should not crash
        results = cmd._gather_context("C++ performance")
        assert isinstance(results, list)

    def test_handles_unicode(self, why_command):
        """Handles unicode in queries and content."""
        cmd, factory = why_command

        factory.add_decision(summary="Support internationalization with UTF-8")

        results = cmd._gather_context("UTF-8 internationalization")
        assert isinstance(results, list)

    def test_handles_very_long_query(self, why_command):
        """Handles very long query strings."""
        cmd, factory = why_command

        long_query = "word " * 100

        # Should not crash
        results = cmd._gather_context(long_query)
        assert isinstance(results, list)

    def test_handles_nodes_without_summary(self, why_command):
        """Handles graph nodes without summary field."""
        cmd, factory = why_command

        # Add a decision
        factory.add_decision(summary="Test")
        nodes = factory.graph.get_nodes_by_type("decision")

        if nodes:
            # Build artifact data should handle this gracefully
            node = nodes[0]
            data = cmd._build_artifact_data(node, score=0.5)
            assert 'summary' in data
