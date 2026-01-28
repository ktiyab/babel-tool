"""
Tests for ReviewCommand — HC2 Human Authority over proposals

Tests the core workflow for proposal review:
- Listing pending proposals (--list)
- Accepting specific proposals (--accept)
- Accepting all proposals (--accept-all)
- Rejecting proposals (--reject)

Aligns with:
- HC2: Human authority over all changes
- P5: Tests ARE evidence for implementation
- P7: Reasoning travels (proposals → confirmed artifacts)
"""

import pytest

from babel.commands.review import ReviewCommand
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
def review_command(babel_factory):
    """Create ReviewCommand with mocked CLI."""
    cli = babel_factory.create_cli_mock()

    # Add resolve_id method (used by _accept_by_ids)
    def resolve_id(query, candidates, context):
        """Resolve ID by prefix or codec alias."""
        # Try exact match first
        if query in candidates:
            return query
        # Try prefix match
        for cid in candidates:
            if cid.startswith(query):
                return cid
        # Try codec alias match
        for cid in candidates:
            if cli.codec.encode(cid) == query:
                return cid
        return None

    cli.resolve_id = resolve_id

    cmd = ReviewCommand.__new__(ReviewCommand)
    cmd._cli = cli
    return cmd, babel_factory


# =============================================================================
# Get Pending Proposals Tests
# =============================================================================

class TestGetPendingProposals:
    """Test _get_pending_proposals method."""

    def test_returns_empty_when_no_proposals(self, review_command):
        """Returns empty list when no proposals exist."""
        cmd, factory = review_command

        pending = cmd._get_pending_proposals()

        assert pending == []

    def test_returns_pending_proposals(self, review_command):
        """Returns proposals that haven't been confirmed or rejected."""
        cmd, factory = review_command

        # Add proposals
        factory.add_proposal("Use SQLite for storage", artifact_type="decision")
        factory.add_proposal("Max 100MB limit", artifact_type="constraint")

        pending = cmd._get_pending_proposals()

        assert len(pending) == 2

    def test_excludes_confirmed_proposals(self, review_command):
        """Excludes proposals that have been confirmed."""
        cmd, factory = review_command

        # Add and confirm a proposal
        proposal_id = factory.add_proposal("Test decision")

        # Confirm it (simulating what _confirm_pending_proposal does)
        from babel.core.events import confirm_artifact
        confirm_event = confirm_artifact(
            proposal_id=proposal_id,
            artifact_type="decision",
            content={"summary": "Test decision"}
        )
        factory.events.append(confirm_event)

        pending = cmd._get_pending_proposals()

        assert len(pending) == 0

    def test_excludes_rejected_proposals(self, review_command):
        """Excludes proposals that have been rejected."""
        cmd, factory = review_command

        # Add a proposal
        proposal_id = factory.add_proposal("Test decision")

        # Reject it
        from babel.core.events import reject_proposal
        reject_event = reject_proposal(
            proposal_id=proposal_id,
            reason="Test rejection"
        )
        factory.events.append(reject_event)

        pending = cmd._get_pending_proposals()

        assert len(pending) == 0


# =============================================================================
# List Proposals Tests
# =============================================================================

class TestListProposals:
    """Test _list_proposals method (--list mode)."""

    def test_lists_all_pending_proposals(self, review_command, capsys):
        """Lists all pending proposals with IDs."""
        cmd, factory = review_command

        factory.add_proposal("Use SQLite", artifact_type="decision")
        factory.add_proposal("Max 100MB", artifact_type="constraint")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._list_proposals(pending, symbols)
        captured = capsys.readouterr()

        assert "PROPOSALS (2 pending)" in captured.out
        assert "Use SQLite" in captured.out
        assert "Max 100MB" in captured.out
        assert "DECISION" in captured.out
        assert "CONSTRAINT" in captured.out

    def test_shows_proposal_rationale(self, review_command, capsys):
        """Shows rationale for each proposal."""
        cmd, factory = review_command

        factory.add_proposal(
            "Use Redis for caching",
            rationale="API rate limits require local cache"
        )

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._list_proposals(pending, symbols)
        captured = capsys.readouterr()

        assert "API rate limits" in captured.out

    def test_shows_accept_hints(self, review_command, capsys):
        """Shows hints for accepting proposals."""
        cmd, factory = review_command

        factory.add_proposal("Test decision")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._list_proposals(pending, symbols)
        captured = capsys.readouterr()

        assert "babel review --accept" in captured.out
        assert "babel review --accept-all" in captured.out


# =============================================================================
# Accept By IDs Tests
# =============================================================================

class TestAcceptByIds:
    """Test _accept_by_ids method (--accept mode)."""

    def test_accepts_proposal_by_full_id(self, review_command, capsys):
        """Accepts proposal when given full ID."""
        cmd, factory = review_command

        proposal_id = factory.add_proposal("Use SQLite for storage")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_by_ids(pending, [proposal_id], symbols)
        captured = capsys.readouterr()

        assert "ACCEPTED" in captured.out
        assert "Use SQLite" in captured.out

        # Verify proposal is now confirmed
        remaining = cmd._get_pending_proposals()
        assert len(remaining) == 0

    def test_accepts_proposal_by_prefix(self, review_command, capsys):
        """Accepts proposal when given ID prefix."""
        cmd, factory = review_command

        proposal_id = factory.add_proposal("Test decision")
        prefix = proposal_id[:12]  # First 12 chars

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_by_ids(pending, [prefix], symbols)
        captured = capsys.readouterr()

        assert "ACCEPTED" in captured.out

    def test_accepts_proposal_by_codec_alias(self, review_command, capsys):
        """Accepts proposal when given AA-BB codec alias."""
        cmd, factory = review_command

        proposal_id = factory.add_proposal("Test decision")
        alias = factory.codec.encode(proposal_id)  # e.g., "AB-CD"

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_by_ids(pending, [alias], symbols)
        captured = capsys.readouterr()

        assert "ACCEPTED" in captured.out

    def test_accepts_multiple_proposals(self, review_command, capsys):
        """Accepts multiple proposals in one call."""
        cmd, factory = review_command

        id1 = factory.add_proposal("Decision 1")
        id2 = factory.add_proposal("Decision 2")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_by_ids(pending, [id1, id2], symbols)
        captured = capsys.readouterr()

        assert "ACCEPTED (2)" in captured.out

        remaining = cmd._get_pending_proposals()
        assert len(remaining) == 0

    def test_reports_not_found(self, review_command, capsys):
        """Reports when proposal ID is not found."""
        cmd, factory = review_command

        factory.add_proposal("Test decision")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_by_ids(pending, ["nonexistent_id"], symbols)
        captured = capsys.readouterr()

        assert "Not found" in captured.out
        assert "nonexistent_id" in captured.out


# =============================================================================
# Accept All Tests
# =============================================================================

class TestAcceptAll:
    """Test _accept_all_proposals method (--accept-all mode)."""

    def test_accepts_all_proposals(self, review_command, capsys):
        """Accepts all pending proposals."""
        cmd, factory = review_command

        factory.add_proposal("Decision 1")
        factory.add_proposal("Decision 2")
        factory.add_proposal("Constraint 1", artifact_type="constraint")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_all_proposals(pending, symbols)
        captured = capsys.readouterr()

        assert "All 3 proposal(s) accepted" in captured.out

        remaining = cmd._get_pending_proposals()
        assert len(remaining) == 0

    def test_shows_each_accepted_proposal(self, review_command, capsys):
        """Shows summary of each accepted proposal."""
        cmd, factory = review_command

        factory.add_proposal("Use SQLite", artifact_type="decision")
        factory.add_proposal("Max 100MB", artifact_type="constraint")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_all_proposals(pending, symbols)
        captured = capsys.readouterr()

        assert "[DECISION]" in captured.out
        assert "[CONSTRAINT]" in captured.out
        assert "Use SQLite" in captured.out
        assert "Max 100MB" in captured.out


# =============================================================================
# Reject Tests
# =============================================================================

class TestRejectByIds:
    """Test _reject_by_ids method (--reject mode)."""

    def test_rejects_proposal(self, review_command, capsys):
        """Rejects proposal by ID."""
        cmd, factory = review_command

        proposal_id = factory.add_proposal("Bad idea")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._reject_by_ids(pending, [proposal_id], "Not aligned with goals", symbols)
        captured = capsys.readouterr()

        assert "Rejected" in captured.out or "rejected" in captured.out.lower()

        # Verify proposal is no longer pending
        remaining = cmd._get_pending_proposals()
        assert len(remaining) == 0

    def test_uses_custom_rejection_reason(self, review_command, capsys):
        """Records custom rejection reason."""
        cmd, factory = review_command

        proposal_id = factory.add_proposal("Test")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._reject_by_ids(pending, [proposal_id], "Conflicts with existing constraint", symbols)
        captured = capsys.readouterr()

        # Rejection should be recorded
        rejected_events = factory.events.read_by_type(EventType.PROPOSAL_REJECTED)
        assert len(rejected_events) == 1
        assert "Conflicts with existing constraint" in rejected_events[0].data.get("reason", "")


# =============================================================================
# Review Command Integration Tests
# =============================================================================

class TestReviewIntegration:
    """Integration tests for the review command."""

    def test_review_with_no_proposals_shows_message(self, review_command, capsys):
        """Shows helpful message when no proposals pending."""
        cmd, factory = review_command

        cmd.review(list_only=True)
        captured = capsys.readouterr()

        assert "No pending proposals" in captured.out
        assert "babel capture" in captured.out

    def test_review_list_shows_proposals(self, review_command, capsys):
        """review --list shows pending proposals."""
        cmd, factory = review_command

        factory.add_proposal("Test decision")

        cmd.review(list_only=True)
        captured = capsys.readouterr()

        assert "PROPOSALS (1 pending)" in captured.out
        assert "Test decision" in captured.out

    def test_review_accept_all_confirms_all(self, review_command, capsys):
        """review --accept-all confirms all proposals."""
        cmd, factory = review_command

        factory.add_proposal("Decision 1")
        factory.add_proposal("Decision 2")

        cmd.review(accept_all=True)
        captured = capsys.readouterr()

        assert "All 2 proposal(s) accepted" in captured.out

        # Verify all confirmed
        remaining = cmd._get_pending_proposals()
        assert len(remaining) == 0

    def test_review_accept_specific_id(self, review_command, capsys):
        """review --accept <id> accepts specific proposal."""
        cmd, factory = review_command

        id1 = factory.add_proposal("Keep this")
        id2 = factory.add_proposal("Also keep this")

        cmd.review(accept_ids=[id1])
        captured = capsys.readouterr()

        assert "ACCEPTED" in captured.out
        assert "Keep this" in captured.out

        # One should remain
        remaining = cmd._get_pending_proposals()
        assert len(remaining) == 1


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_proposal_content(self, review_command, capsys):
        """Handles proposals with minimal content."""
        cmd, factory = review_command

        # Add proposal with empty summary
        factory.add_proposal("", artifact_type="decision")

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        # Should not crash
        cmd._list_proposals(pending, symbols)
        captured = capsys.readouterr()

        assert "PROPOSALS (1 pending)" in captured.out

    def test_handles_long_summary(self, review_command, capsys):
        """Truncates very long summaries appropriately."""
        cmd, factory = review_command

        long_summary = "A" * 200
        factory.add_proposal(long_summary)

        pending = cmd._get_pending_proposals()
        symbols = factory.symbols

        cmd._accept_all_proposals(pending, symbols)
        captured = capsys.readouterr()

        # Should truncate and not break output
        assert "..." in captured.out or "AAAA" in captured.out
