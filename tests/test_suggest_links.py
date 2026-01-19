"""
Tests for SuggestLinksCommand — AI-assisted decision-to-commit linking

Tests the suggestion engine that helps bridge decisions (Babel)
with commits (Git) while respecting human authority (HC2).

Aligns with:
- P5: Tests ARE evidence for implementation
- P7: Reasoning travels (bridging intent with state)
- P8: Evolution traceable (completing the chain)
- HC2: Human authority (suggestions, not auto-link)
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import asdict

from babel.commands.suggest_links import SuggestLinksCommand, LinkSuggestion


@pytest.fixture
def mock_babel_dir(tmp_path):
    """Create a minimal .babel directory structure."""
    babel_dir = tmp_path / ".babel"
    babel_dir.mkdir()
    (babel_dir / "shared").mkdir()
    (babel_dir / "local").mkdir()
    return babel_dir


@pytest.fixture
def mock_graph():
    """Create a mock graph with no nodes by default."""
    graph = Mock()
    graph.get_nodes_by_type = Mock(return_value=[])
    return graph


@pytest.fixture
def mock_symbols():
    """Create mock symbols for output."""
    symbols = Mock()
    symbols.check_pass = "[PASS]"
    symbols.llm_thinking = "[AI]"
    symbols.arrow = "->"
    return symbols


@pytest.fixture
def mock_cli(mock_babel_dir, tmp_path, mock_graph, mock_symbols):
    """Create a mock CLI with required attributes."""
    cli = Mock()
    cli.babel_dir = mock_babel_dir
    cli.project_dir = tmp_path
    cli.graph = mock_graph
    cli.symbols = mock_symbols
    return cli


@pytest.fixture
def suggest_command(mock_cli):
    """Create SuggestLinksCommand with mocked dependencies."""
    cmd = SuggestLinksCommand.__new__(SuggestLinksCommand)
    cmd._cli = mock_cli
    return cmd


# =============================================================================
# LinkSuggestion Dataclass Tests
# =============================================================================

class TestLinkSuggestion:
    """Test LinkSuggestion dataclass."""

    def test_create_suggestion(self):
        """LinkSuggestion can be created with required fields."""
        suggestion = LinkSuggestion(
            decision_id="dec12345",
            decision_summary="Use SQLite for storage",
            decision_type="decision",
            commit_sha="abc67890",
            commit_message="Implement SQLite storage",
            score=0.8,
            reasons=["shared terms: sqlite, storage"]
        )

        assert suggestion.decision_id == "dec12345"
        assert suggestion.commit_sha == "abc67890"
        assert suggestion.score == 0.8
        assert len(suggestion.reasons) == 1

    def test_suggestion_to_dict(self):
        """LinkSuggestion can be converted to dict."""
        suggestion = LinkSuggestion(
            decision_id="dec12345",
            decision_summary="Test",
            decision_type="decision",
            commit_sha="abc67890",
            commit_message="Test commit",
            score=0.5,
            reasons=[]
        )

        d = asdict(suggestion)
        assert d["decision_id"] == "dec12345"
        assert d["score"] == 0.5


# =============================================================================
# Word Extraction Tests
# =============================================================================

class TestExtractWords:
    """Test _extract_words method (stop word filtering)."""

    def test_extract_basic_words(self, suggest_command):
        """Extracts meaningful words from text."""
        words = suggest_command._extract_words("Implement SQLite database storage")

        assert "sqlite" in words
        assert "database" in words
        assert "storage" in words

    def test_filters_stop_words(self, suggest_command):
        """Filters out common stop words."""
        words = suggest_command._extract_words("add the new file to fix the issue")

        # Stop words should be filtered
        assert "the" not in words
        assert "add" not in words
        assert "fix" not in words
        assert "new" not in words
        assert "file" not in words

        # But meaningful words remain
        assert "issue" in words

    def test_filters_short_words(self, suggest_command):
        """Filters words shorter than 3 characters."""
        words = suggest_command._extract_words("to do it in a db")

        # Short words filtered
        assert "to" not in words
        assert "do" not in words
        assert "it" not in words
        assert "in" not in words
        assert "a" not in words
        assert "db" not in words  # 2 chars

    def test_lowercases_words(self, suggest_command):
        """Words are lowercased for matching."""
        words = suggest_command._extract_words("SQLite Database STORAGE")

        assert "sqlite" in words
        assert "database" in words
        assert "storage" in words
        # Original case not present
        assert "SQLite" not in words
        assert "STORAGE" not in words

    def test_empty_text_returns_empty_set(self, suggest_command):
        """Empty text returns empty set."""
        words = suggest_command._extract_words("")
        assert words == set()


# =============================================================================
# Score Calculation Tests
# =============================================================================

class TestCalculateMatchScore:
    """Test _calculate_match_score method."""

    def test_no_overlap_returns_zero(self, suggest_command):
        """No word overlap results in zero score."""
        commit = {
            'message': 'Fix typo in readme',
            'words': {'typo', 'readme'}
        }
        decision = {
            'id': 'dec123',
            'summary': 'Use PostgreSQL database',
            'words': {'postgresql', 'database'},
            'type': 'decision',
            'domain': ''
        }

        score, reasons = suggest_command._calculate_match_score(commit, decision)

        assert score == 0.0
        assert reasons == []

    def test_word_overlap_increases_score(self, suggest_command):
        """Word overlap increases the match score."""
        commit = {
            'message': 'Implement SQLite storage',
            'words': {'sqlite', 'storage', 'implement'}
        }
        decision = {
            'id': 'dec123',
            'summary': 'Use SQLite for storage',
            'words': {'sqlite', 'storage'},
            'type': 'decision',
            'domain': ''
        }

        score, reasons = suggest_command._calculate_match_score(commit, decision)

        assert score > 0.0
        assert any('shared terms' in r for r in reasons)

    def test_domain_match_adds_score(self, suggest_command):
        """Domain match adds to the score."""
        commit = {
            'message': 'Add caching feature',
            'words': {'caching', 'feature'}
        }
        decision = {
            'id': 'dec123',
            'summary': 'Implement cache layer',
            'words': {'cache', 'layer'},
            'type': 'decision',
            'domain': 'caching'
        }

        score, reasons = suggest_command._calculate_match_score(commit, decision)

        assert score >= 0.2  # Domain match adds 0.2
        assert any('domain match' in r for r in reasons)

    def test_constraint_type_boost(self, suggest_command):
        """Constraint type gets boost for constraint-related commits."""
        commit = {
            'message': 'Enforce maximum file size',
            'words': {'enforce', 'maximum', 'size'}
        }
        decision = {
            'id': 'con123',
            'summary': 'Maximum file size constraint',
            'words': {'maximum', 'size', 'constraint'},
            'type': 'constraint',
            'domain': ''
        }

        score, reasons = suggest_command._calculate_match_score(commit, decision)

        # Has word overlap + constraint boost
        assert any('constraint-related' in r for r in reasons)

    def test_decision_type_boost(self, suggest_command):
        """Decision type gets boost for implementation commits."""
        commit = {
            'message': 'Implement authentication flow',
            'words': {'authentication', 'flow'}
        }
        decision = {
            'id': 'dec123',
            'summary': 'Use JWT authentication',
            'words': {'jwt', 'authentication'},
            'type': 'decision',
            'domain': ''
        }

        score, reasons = suggest_command._calculate_match_score(commit, decision)

        # Has word overlap + implementation boost
        assert any('implementation commit' in r for r in reasons)

    def test_score_capped_at_one(self, suggest_command):
        """Score is capped at 1.0 even with many matches."""
        commit = {
            'message': 'implement enforce require sqlite database storage caching',
            'words': {'sqlite', 'database', 'storage', 'caching', 'layer', 'implement'}
        }
        decision = {
            'id': 'dec123',
            'summary': 'Use SQLite database for storage and caching layer',
            'words': {'sqlite', 'database', 'storage', 'caching', 'layer'},
            'type': 'decision',
            'domain': 'caching'
        }

        score, reasons = suggest_command._calculate_match_score(commit, decision)

        assert score <= 1.0


# =============================================================================
# Find Matches Tests
# =============================================================================

class TestFindMatches:
    """Test _find_matches method."""

    def test_finds_matching_decisions(self, suggest_command):
        """Finds decisions that match a commit."""
        commit = {
            'sha': 'abc123',
            'message': 'Implement SQLite storage',
            'words': {'sqlite', 'storage'}
        }
        decisions = [
            {
                'id': 'dec1',
                'summary': 'Use SQLite for storage',
                'words': {'sqlite', 'storage'},
                'type': 'decision',
                'domain': ''
            },
            {
                'id': 'dec2',
                'summary': 'Use PostgreSQL database',
                'words': {'postgresql', 'database'},
                'type': 'decision',
                'domain': ''
            }
        ]

        suggestions = suggest_command._find_matches(commit, decisions, min_score=0.3)

        # Should find the SQLite decision
        assert len(suggestions) >= 1
        matching_ids = [s.decision_id for s in suggestions]
        assert 'dec1' in matching_ids

    def test_respects_min_score(self, suggest_command):
        """Only returns suggestions above min_score."""
        commit = {
            'sha': 'abc123',
            'message': 'Minor typo fix',
            'words': {'minor', 'typo'}
        }
        decisions = [
            {
                'id': 'dec1',
                'summary': 'Major architecture decision',
                'words': {'major', 'architecture'},
                'type': 'decision',
                'domain': ''
            }
        ]

        # High min_score should filter out weak matches
        suggestions = suggest_command._find_matches(commit, decisions, min_score=0.5)

        assert len(suggestions) == 0

    def test_returns_link_suggestion_objects(self, suggest_command):
        """Returns proper LinkSuggestion objects."""
        commit = {
            'sha': 'abc123',
            'message': 'Add caching layer',
            'words': {'caching', 'layer'}
        }
        decisions = [
            {
                'id': 'dec1',
                'summary': 'Implement caching',
                'words': {'caching', 'implement'},
                'type': 'decision',
                'domain': ''
            }
        ]

        suggestions = suggest_command._find_matches(commit, decisions, min_score=0.1)

        if suggestions:
            s = suggestions[0]
            assert isinstance(s, LinkSuggestion)
            assert s.commit_sha == 'abc123'
            assert s.decision_id == 'dec1'
            assert s.score > 0


# =============================================================================
# Get Linkable Decisions Tests
# =============================================================================

class TestGetLinkableDecisions:
    """Test _get_linkable_decisions method."""

    def test_collects_multiple_types(self, suggest_command, mock_cli):
        """Collects decisions, constraints, principles, and proposals."""
        decision = Mock(
            event_id="dec123",
            id="decision_dec123",
            content={"summary": "Test decision"}
        )
        constraint = Mock(
            event_id="con123",
            id="constraint_con123",
            content={"summary": "Test constraint"}
        )

        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [decision]
            elif node_type == "constraint":
                return [constraint]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        decisions = suggest_command._get_linkable_decisions()

        # Should have both
        assert len(decisions) == 2
        types = {d['type'] for d in decisions}
        assert 'decision' in types
        assert 'constraint' in types

    def test_extracts_words_from_summary(self, suggest_command, mock_cli):
        """Extracts words from decision summary for matching."""
        node = Mock(
            event_id="dec123",
            id="decision_dec123",
            content={"summary": "Use SQLite database storage"}
        )

        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        decisions = suggest_command._get_linkable_decisions()

        assert len(decisions) == 1
        assert 'words' in decisions[0]
        assert 'sqlite' in decisions[0]['words']

    def test_handles_missing_summary(self, suggest_command, mock_cli):
        """Handles decisions without summary gracefully."""
        node = Mock(
            event_id="dec123",
            id="decision_dec123",
            content={"detail": "Some detail but no summary"}
        )

        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        decisions = suggest_command._get_linkable_decisions()

        assert len(decisions) == 1
        # Should still have some summary (from content stringification)
        assert 'summary' in decisions[0]


# =============================================================================
# Score Bar Tests
# =============================================================================

class TestScoreBar:
    """Test _score_bar visual representation."""

    def test_high_confidence(self, suggest_command):
        """High confidence (>= 0.7) shows full bar."""
        assert suggest_command._score_bar(0.8) == "[###]"
        assert suggest_command._score_bar(0.7) == "[###]"

    def test_medium_confidence(self, suggest_command):
        """Medium confidence (0.5-0.7) shows partial bar."""
        assert suggest_command._score_bar(0.6) == "[## ]"
        assert suggest_command._score_bar(0.5) == "[## ]"

    def test_low_confidence(self, suggest_command):
        """Low confidence (0.3-0.5) shows minimal bar."""
        assert suggest_command._score_bar(0.4) == "[#  ]"
        assert suggest_command._score_bar(0.3) == "[#  ]"

    def test_very_low_confidence(self, suggest_command):
        """Very low confidence (< 0.3) shows empty bar."""
        assert suggest_command._score_bar(0.2) == "[   ]"
        assert suggest_command._score_bar(0.1) == "[   ]"


# =============================================================================
# Human Authority (HC2) Semantics Tests
# =============================================================================

class TestHumanAuthority:
    """Test that suggestions respect human authority (HC2)."""

    def test_suggestions_are_proposals_not_actions(self, suggest_command, mock_cli, capsys):
        """Command suggests but does not auto-link (HC2)."""
        # Setup a matching scenario
        node = Mock(
            event_id="dec123",
            id="decision_dec123",
            content={"summary": "Use SQLite storage"}
        )

        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        with patch('babel.commands.suggest_links.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_commit_shas.return_value = set()
            # Importantly: add() should NOT be called
            mock_store_class.return_value = mock_store

            with patch('babel.commands.suggest_links.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git._run_git.return_value = "abc123|Implement SQLite storage\n"
                mock_git_class.return_value = mock_git

                with patch('babel.output.end_command'):
                    suggest_command.suggest_links()

            # Verify that add() was NEVER called (suggestions only)
            mock_store.add.assert_not_called()

    def test_output_includes_manual_link_command(self, suggest_command, mock_cli, capsys):
        """Output includes command for manual linking."""
        node = Mock(
            event_id="dec123",
            id="decision_dec123",
            content={"summary": "Use SQLite storage"}
        )

        def mock_get_nodes(node_type):
            if node_type == "decision":
                return [node]
            return []

        mock_cli.graph.get_nodes_by_type.side_effect = mock_get_nodes

        with patch('babel.commands.suggest_links.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            with patch('babel.commands.suggest_links.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git._run_git.return_value = "abc123|Implement SQLite storage\n"
                mock_git_class.return_value = mock_git

                with patch('babel.output.end_command'):
                    suggest_command.suggest_links()

        captured = capsys.readouterr()
        # Output should include the command for human to manually link
        assert "babel link" in captured.out
        assert "--to-commit" in captured.out


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_not_git_repo(self, suggest_command, capsys):
        """Handles non-git repositories."""
        with patch('babel.commands.suggest_links.GitIntegration') as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repo = False
            mock_git_class.return_value = mock_git

            suggest_command.suggest_links()

        captured = capsys.readouterr()
        assert "Not a git repository" in captured.out

    def test_no_commits(self, suggest_command, capsys):
        """Handles no commits found."""
        with patch('babel.commands.suggest_links.CommitLinkStore'):
            with patch('babel.commands.suggest_links.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git._run_git.return_value = ""
                mock_git_class.return_value = mock_git

                suggest_command.suggest_links()

        captured = capsys.readouterr()
        assert "No commits found" in captured.out

    def test_no_decisions(self, suggest_command, mock_cli, capsys):
        """Handles no decisions in graph."""
        mock_cli.graph.get_nodes_by_type.return_value = []

        with patch('babel.commands.suggest_links.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            with patch('babel.commands.suggest_links.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git._run_git.return_value = "abc123|Some commit\n"
                mock_git_class.return_value = mock_git

                suggest_command.suggest_links()

        captured = capsys.readouterr()
        assert "No decisions found" in captured.out

    def test_all_commits_already_linked(self, suggest_command, capsys):
        """Handles all commits already having links."""
        with patch('babel.commands.suggest_links.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            # The commit is already linked
            mock_store.get_linked_commit_shas.return_value = {"abc123"}
            mock_store_class.return_value = mock_store

            with patch('babel.commands.suggest_links.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = True
                mock_git._run_git.return_value = "abc123|Already linked commit\n"
                mock_git_class.return_value = mock_git

                suggest_command.suggest_links()

        captured = capsys.readouterr()
        assert "already have decision links" in captured.out
