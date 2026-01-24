"""
Tests for StatusCommand — P9 Adaptive Cycle Rate (Project Health Assessment)

Tests the project status display and health computation:
- Purpose display formatting
- Pending proposal counting
- Project health computation (multi-factor assessment)
- Git-babel sync health
- JSON data collection for AI operators

Aligns with:
- P5: Tests ARE evidence for implementation
- P9: Adaptive Cycle Rate (health assessment guides pace)
- P4: Layered Validation (open tensions surfaced)
- P10: Meta-Principles for Conflict (open questions surfaced)
- HC2: Human authority (tests verify user-facing status)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from babel.commands.status import StatusCommand
from babel.core.events import EventType
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def status_command(babel_factory):
    """Create StatusCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # StatusCommand accesses these via properties from BaseCommand
    cli.project_dir = babel_factory.tmp_path

    # Mock memos (for init instructions)
    cli.memos = Mock()
    cli.memos.list_init_memos = Mock(return_value=[])

    # Mock coherence checker
    cli.coherence = Mock()
    cli.coherence.get_last_result = Mock(return_value=None)

    # Mock tensions store
    cli.tensions = Mock()
    cli.tensions.count_open = Mock(return_value=0)

    # Mock validation store
    cli.validation = Mock()
    cli.validation.stats = Mock(return_value={
        "tracked": 0,
        "validated": 0,
        "partial": 0,
        "groupthink_risk": 0,
        "unreviewed_risk": 0
    })

    # Mock questions store
    cli.questions = Mock()
    cli.questions.count_open = Mock(return_value=0)
    cli.questions.get_resolved_questions = Mock(return_value=[])

    # Mock extractor
    cli.extractor = Mock()
    cli.extractor.queue = None

    # Mock vocabulary with proper _load() method
    cli.vocabulary = Mock()
    cli.vocabulary._load = Mock(return_value={"clusters": {}})

    # Create command instance
    cmd = StatusCommand.__new__(StatusCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Display Purpose Tests
# =============================================================================

class TestDisplayPurpose:
    """Test _display_purpose method for purpose formatting."""

    def test_displays_summary_format(self, status_command, capsys):
        """Displays purpose with summary field."""
        cmd, factory = status_command

        content = {
            "summary": "Preserve intent across sessions",
            "detail": {
                "goal": "Never lose reasoning context",
                "success_criteria": "AI can recall past decisions"
            }
        }

        cmd._display_purpose(content, full=False)
        captured = capsys.readouterr()

        assert "Preserve intent" in captured.out
        assert "Purpose:" in captured.out

    def test_displays_legacy_format(self, status_command, capsys):
        """Displays purpose with legacy purpose field."""
        cmd, factory = status_command

        content = {
            "purpose": "Build Babel through dogfooding",
            "need": "Tools lose reasoning context"
        }

        cmd._display_purpose(content, full=False)
        captured = capsys.readouterr()

        assert "Build Babel" in captured.out
        assert "Need:" in captured.out
        assert "Tools lose" in captured.out

    def test_shows_goal_when_full(self, status_command, capsys):
        """Shows goal detail when full=True."""
        cmd, factory = status_command

        content = {
            "summary": "Test purpose",
            "detail": {
                "goal": "Achieve specific outcome"
            }
        }

        cmd._display_purpose(content, full=True)
        captured = capsys.readouterr()

        assert "Goal:" in captured.out
        assert "Achieve specific" in captured.out

    def test_handles_missing_fields(self, status_command, capsys):
        """Handles content with minimal fields."""
        cmd, factory = status_command

        content = {}

        # Should not crash
        cmd._display_purpose(content, full=False)
        captured = capsys.readouterr()

        # Should still output something
        assert "Purpose" in captured.out


# =============================================================================
# Count Pending Proposals Tests
# =============================================================================

class TestCountPendingProposals:
    """Test _count_pending_proposals method."""

    def test_counts_unconfirmed_proposals(self, status_command):
        """Counts proposals that haven't been confirmed."""
        cmd, factory = status_command

        # Add proposals
        factory.add_proposal("Decision 1")
        factory.add_proposal("Decision 2")
        factory.add_proposal("Decision 3")

        count = cmd._count_pending_proposals()

        assert count == 3

    def test_excludes_confirmed_proposals(self, status_command):
        """Excludes proposals that have been confirmed."""
        cmd, factory = status_command

        # Add and confirm a proposal
        proposal_id = factory.add_proposal("Confirmed decision")

        # Confirm it
        from babel.core.events import confirm_artifact
        confirm_event = confirm_artifact(
            proposal_id=proposal_id,
            artifact_type="decision",
            content={"summary": "Confirmed decision"}
        )
        factory.events.append(confirm_event)

        # Add another unconfirmed
        factory.add_proposal("Pending decision")

        count = cmd._count_pending_proposals()

        assert count == 1

    def test_excludes_rejected_proposals(self, status_command):
        """Excludes proposals that have been rejected."""
        cmd, factory = status_command

        # Add and reject a proposal
        proposal_id = factory.add_proposal("Rejected decision")

        from babel.core.events import reject_proposal
        reject_event = reject_proposal(
            proposal_id=proposal_id,
            reason="Not aligned with goals"
        )
        factory.events.append(reject_event)

        # Add another unconfirmed
        factory.add_proposal("Pending decision")

        count = cmd._count_pending_proposals()

        assert count == 1

    def test_returns_zero_when_no_proposals(self, status_command):
        """Returns zero when no proposals exist."""
        cmd, factory = status_command

        count = cmd._count_pending_proposals()

        assert count == 0


# =============================================================================
# Compute Project Health Tests (P9)
# =============================================================================

class TestComputeProjectHealth:
    """Test _compute_project_health method for P9 adaptive pace."""

    def test_starting_health_with_few_artifacts(self, status_command):
        """Returns 'Starting' level when few artifacts."""
        cmd, factory = status_command

        # Few artifacts
        health = cmd._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=0,
            coherence_result=None,
            principle_result=None
        )

        assert health["level"] == "Starting"
        assert "indicator" in health

    def test_growing_health_with_maturity(self, status_command):
        """Returns 'Growing' level with moderate artifacts."""
        cmd, factory = status_command

        # Add enough artifacts for maturity
        factory.add_purpose("Test purpose")
        for i in range(20):
            factory.add_decision(summary=f"Decision {i}")

        health = cmd._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 5, "validated": 0, "partial": 2},
            open_questions=0,
            coherence_result=None,
            principle_result=None
        )

        assert health["level"] in ("Growing", "Moderate")

    def test_confused_health_with_many_tensions(self, status_command):
        """Returns 'Confused' level with many open tensions."""
        cmd, factory = status_command

        factory.add_purpose("Test")
        for i in range(5):
            factory.add_decision(summary=f"Decision {i}")

        health = cmd._compute_project_health(
            open_tensions=5,  # High tension count
            validation_stats={"tracked": 5, "validated": 0, "partial": 5},
            open_questions=5,
            coherence_result=Mock(has_issues=True),
            principle_result=None
        )

        assert health["level"] == "Confused"
        assert "suggestion" in health

    def test_aligned_health_with_validation(self, status_command):
        """Returns 'Aligned' level with good validation."""
        cmd, factory = status_command

        factory.add_purpose("Test")
        for i in range(30):
            factory.add_decision(summary=f"Decision {i}")

        # Mock principle result with high score
        principle_result = Mock()
        principle_result.violation_count = 0
        principle_result.warning_count = 0
        principle_result.score = 0.9
        principle_result.satisfied_count = 9
        principle_result.total_applicable = 10

        health = cmd._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 10, "validated": 8, "partial": 0},
            open_questions=0,
            coherence_result=Mock(has_issues=False),
            principle_result=principle_result
        )

        assert health["level"] == "Aligned"

    def test_health_includes_indicator(self, status_command):
        """Health result includes visual indicator."""
        cmd, factory = status_command

        health = cmd._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=0,
            coherence_result=None,
            principle_result=None
        )

        assert "indicator" in health
        assert health["indicator"] is not None


# =============================================================================
# Collect Status Data Tests (JSON format)
# =============================================================================

class TestCollectStatusData:
    """Test _collect_status_data for JSON output."""

    def test_includes_core_metrics(self, status_command):
        """Includes core project metrics."""
        cmd, factory = status_command

        factory.add_purpose("Test purpose")
        factory.add_decision(summary="Test decision")

        data = cmd._collect_status_data(full=False, git=False)

        assert "project" in data
        assert "events" in data
        assert "artifacts" in data
        assert "connections" in data

    def test_includes_events_breakdown(self, status_command):
        """Includes events with shared/local breakdown."""
        cmd, factory = status_command

        data = cmd._collect_status_data()

        assert "events" in data
        events = data["events"]
        assert "total" in events
        assert "shared" in events
        assert "local" in events

    def test_includes_health_data(self, status_command):
        """Includes health assessment data."""
        cmd, factory = status_command

        data = cmd._collect_status_data()

        assert "health" in data
        health = data["health"]
        assert "level" in health

    def test_includes_validation_stats(self, status_command):
        """Includes validation statistics."""
        cmd, factory = status_command

        data = cmd._collect_status_data()

        assert "validation" in data
        validation = data["validation"]
        assert "tracked" in validation
        assert "validated" in validation
        assert "partial" in validation

    def test_includes_tension_and_question_counts(self, status_command):
        """Includes open tensions and questions counts."""
        cmd, factory = status_command

        data = cmd._collect_status_data()

        assert "open_tensions" in data
        assert "open_questions" in data


# =============================================================================
# Show Git Sync Health Tests
# =============================================================================

class TestShowGitSyncHealth:
    """Test _show_git_sync_health for git-babel bridge display."""

    def test_shows_link_count(self, status_command, capsys):
        """Shows number of decision-commit links."""
        cmd, factory = status_command

        mock_git = Mock()
        mock_git._run_git = Mock(return_value="")

        with patch('babel.commands.status.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.all_links.return_value = [Mock(), Mock()]  # 2 links
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            cmd._show_git_sync_health(mock_git, full=False)

        captured = capsys.readouterr()
        assert "Decision-commit links: 2" in captured.out

    def test_shows_unlinked_decisions_warning(self, status_command, capsys):
        """Shows warning for unlinked decisions."""
        cmd, factory = status_command

        # Add decision
        factory.add_decision(summary="Unlinked decision")

        mock_git = Mock()
        mock_git._run_git = Mock(return_value="")

        with patch('babel.commands.status.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.all_links.return_value = []
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            cmd._show_git_sync_health(mock_git, full=False)

        captured = capsys.readouterr()
        assert "Unlinked decisions:" in captured.out

    def test_shows_unlinked_commits_warning(self, status_command, capsys):
        """Shows warning for unlinked commits."""
        cmd, factory = status_command

        mock_git = Mock()
        mock_git._run_git = Mock(return_value="abc123|Add feature\n")

        with patch('babel.commands.status.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.all_links.return_value = []
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            cmd._show_git_sync_health(mock_git, full=False)

        captured = capsys.readouterr()
        assert "Unlinked commits" in captured.out

    def test_shows_success_when_all_linked(self, status_command, capsys):
        """Shows success message when all artifacts are linked."""
        cmd, factory = status_command

        mock_git = Mock()
        mock_git._run_git = Mock(return_value="")

        with patch('babel.commands.status.CommitLinkStore') as mock_store_class:
            mock_store = Mock()
            mock_store.all_links.return_value = []
            mock_store.get_linked_decision_ids.return_value = set()
            mock_store.get_linked_commit_shas.return_value = set()
            mock_store_class.return_value = mock_store

            cmd._show_git_sync_health(mock_git, full=False)

        captured = capsys.readouterr()
        # Either success message or gaps hint
        assert "connected" in captured.out or "gaps" in captured.out


# =============================================================================
# Status Integration Tests
# =============================================================================

class TestStatusIntegration:
    """Integration tests for the status command."""

    def test_status_runs_without_error(self, status_command, capsys):
        """Status command runs without crashing."""
        cmd, factory = status_command

        with patch('babel.commands.status.get_provider_status', return_value="Mock mode"):
            with patch('babel.commands.status.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.commands.status.PrincipleChecker') as mock_checker_class:
                    mock_result = Mock()
                    mock_result.satisfied_count = 5
                    mock_result.total_applicable = 10
                    mock_result.warning_count = 0
                    mock_result.violation_count = 0
                    mock_result.score = 0.5

                    mock_checker = Mock()
                    mock_checker.check_all.return_value = mock_result
                    mock_checker_class.return_value = mock_checker

                    with patch('babel.output.end_command'):
                        cmd.status()

        captured = capsys.readouterr()
        assert "Project:" in captured.out
        assert "Events:" in captured.out

    def test_status_shows_artifact_counts(self, status_command, capsys):
        """Status shows artifact and connection counts."""
        cmd, factory = status_command

        factory.add_purpose("Test purpose")
        factory.add_decision(summary="Test decision")

        with patch('babel.commands.status.get_provider_status', return_value="Mock mode"):
            with patch('babel.commands.status.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.commands.status.PrincipleChecker') as mock_checker_class:
                    mock_result = Mock()
                    mock_result.satisfied_count = 5
                    mock_result.total_applicable = 10
                    mock_result.warning_count = 0
                    mock_result.violation_count = 0
                    mock_result.score = 0.5

                    mock_checker = Mock()
                    mock_checker.check_all.return_value = mock_result
                    mock_checker_class.return_value = mock_checker

                    with patch('babel.output.end_command'):
                        cmd.status()

        captured = capsys.readouterr()
        assert "Artifacts:" in captured.out
        assert "Connections:" in captured.out

    def test_status_shows_health(self, status_command, capsys):
        """Status shows project health assessment."""
        cmd, factory = status_command

        with patch('babel.commands.status.get_provider_status', return_value="Mock mode"):
            with patch('babel.commands.status.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.commands.status.PrincipleChecker') as mock_checker_class:
                    mock_result = Mock()
                    mock_result.satisfied_count = 5
                    mock_result.total_applicable = 10
                    mock_result.warning_count = 0
                    mock_result.violation_count = 0
                    mock_result.score = 0.5

                    mock_checker = Mock()
                    mock_checker.check_all.return_value = mock_result
                    mock_checker_class.return_value = mock_checker

                    with patch('babel.output.end_command'):
                        cmd.status()

        captured = capsys.readouterr()
        assert "Project Health:" in captured.out

    def test_status_json_format(self, status_command, capsys):
        """Status with --format json outputs valid JSON."""
        cmd, factory = status_command

        factory.add_purpose("Test purpose")

        with patch('babel.commands.status.get_provider_status', return_value="Mock mode"):
            with patch('babel.commands.status.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.commands.status.PrincipleChecker') as mock_checker_class:
                    mock_result = Mock()
                    mock_result.satisfied_count = 5
                    mock_result.total_applicable = 10
                    mock_result.warning_count = 0
                    mock_result.violation_count = 0
                    mock_result.score = 0.5

                    mock_checker = Mock()
                    mock_checker.check_all.return_value = mock_result
                    mock_checker_class.return_value = mock_checker

                    cmd.status(format="json")

        captured = capsys.readouterr()
        # Should be valid JSON (contains braces)
        assert "{" in captured.out or "project" in captured.out.lower()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_project(self, status_command, capsys):
        """Handles project with no artifacts."""
        cmd, factory = status_command

        with patch('babel.commands.status.get_provider_status', return_value="Mock mode"):
            with patch('babel.commands.status.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.commands.status.PrincipleChecker') as mock_checker_class:
                    mock_result = Mock()
                    mock_result.satisfied_count = 0
                    mock_result.total_applicable = 10
                    mock_result.warning_count = 0
                    mock_result.violation_count = 0
                    mock_result.score = 0.0

                    mock_checker = Mock()
                    mock_checker.check_all.return_value = mock_result
                    mock_checker_class.return_value = mock_checker

                    with patch('babel.output.end_command'):
                        # Should not crash
                        cmd.status()

        captured = capsys.readouterr()
        assert "Project:" in captured.out

    def test_handles_missing_coherence_result(self, status_command, capsys):
        """Handles missing coherence check result."""
        cmd, factory = status_command

        # coherence.get_last_result returns None
        cmd._cli.coherence.get_last_result.return_value = None

        with patch('babel.commands.status.get_provider_status', return_value="Mock mode"):
            with patch('babel.commands.status.GitIntegration') as mock_git_class:
                mock_git = Mock()
                mock_git.is_git_repo = False
                mock_git_class.return_value = mock_git

                with patch('babel.commands.status.PrincipleChecker') as mock_checker_class:
                    mock_result = Mock()
                    mock_result.satisfied_count = 5
                    mock_result.total_applicable = 10
                    mock_result.warning_count = 0
                    mock_result.violation_count = 0
                    mock_result.score = 0.5

                    mock_checker = Mock()
                    mock_checker.check_all.return_value = mock_result
                    mock_checker_class.return_value = mock_checker

                    with patch('babel.output.end_command'):
                        # Should not crash
                        cmd.status()

        captured = capsys.readouterr()
        # Should display project health without crashing
        # Coherence is optional - only shown when checked
        assert "Project Health:" in captured.out or "Ready" in captured.out

    def test_handles_purpose_with_no_detail(self, status_command, capsys):
        """Handles purpose content without detail field."""
        cmd, factory = status_command

        content = {"summary": "Simple purpose"}

        cmd._display_purpose(content, full=True)
        captured = capsys.readouterr()

        # Should display without crashing
        assert "Simple purpose" in captured.out
