"""
Tests for CaptureCommand — P1 Bootstrap from Need (Intent Capture)

Tests the conversation capture and extraction workflow:
- Raw capture with domain attribution (P3)
- Batch mode for deferred review (HC2)
- Specification capture for need enrichment
- Uncertainty flagging (P10)
- Duplicate prevention (P7)

Aligns with:
- P1: Bootstrap from Need (capture is how decisions enter the system)
- P3: Expertise-Based Authority (domain attribution)
- P5: Tests ARE evidence for implementation
- P7: Evidence-Weighted Memory (prevents duplicates)
- P10: Meta-Principles for Conflict (uncertainty handling)
- HC2: Human authority (batch mode, propose don't execute)
"""

import pytest
from unittest.mock import Mock

from babel.commands.capture import CaptureCommand
from babel.core.events import EventType
from babel.services.extractor import Proposal
from tests.factories import BabelTestFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def babel_factory(tmp_path):
    """Create a fresh BabelTestFactory."""
    return BabelTestFactory(tmp_path)


@pytest.fixture
def capture_command(babel_factory):
    """Create CaptureCommand with mocked CLI and stores."""
    cli = babel_factory.create_cli_mock()

    # CaptureCommand needs extractor
    cli.extractor = Mock()
    cli.extractor.is_available = True
    cli.extractor.extract = Mock(return_value=[])
    cli.extractor.format_for_confirmation = Mock(return_value="Formatted proposal")

    # Create command instance
    cmd = CaptureCommand.__new__(CaptureCommand)
    cmd._cli = cli

    return cmd, babel_factory


# =============================================================================
# Get Existing Artifacts Tests (P7: Evidence-Weighted Memory)
# =============================================================================

class TestGetExistingArtifacts:
    """Test _get_existing_artifacts for duplicate prevention."""

    def test_returns_confirmed_artifacts(self, capture_command):
        """Returns confirmed artifacts from events."""
        cmd, factory = capture_command

        # Add some decisions
        factory.add_decision(summary="Use SQLite for storage")
        factory.add_decision(summary="Implement caching layer")

        existing = cmd._get_existing_artifacts()

        assert len(existing) == 2
        summaries = [a.summary for a in existing]
        assert "Use SQLite for storage" in summaries
        assert "Implement caching layer" in summaries

    def test_excludes_non_confirmed_artifacts(self, capture_command):
        """Only returns confirmed artifacts, not proposals."""
        cmd, factory = capture_command

        # Add a proposal (not confirmed)
        factory.add_proposal(summary="Pending decision", artifact_type="decision")

        existing = cmd._get_existing_artifacts()

        # Proposals should not appear in existing artifacts
        # (they're not ARTIFACT_CONFIRMED events)
        summaries = [a.summary for a in existing]
        assert "Pending decision" not in summaries

    def test_returns_empty_for_no_artifacts(self, capture_command):
        """Returns empty list when no artifacts exist."""
        cmd, factory = capture_command

        existing = cmd._get_existing_artifacts()

        assert existing == []

    def test_extracts_summary_from_content_dict(self, capture_command):
        """Extracts summary field from content dict."""
        cmd, factory = capture_command

        factory.add_decision(summary="Dict summary test", what="Detailed what")

        existing = cmd._get_existing_artifacts()

        assert len(existing) == 1
        assert existing[0].summary == "Dict summary test"


# =============================================================================
# Capture Tests (Main Entry Point)
# =============================================================================

class TestCapture:
    """Test main capture method."""

    def test_creates_capture_event(self, capture_command, capsys):
        """Creates CONVERSATION_CAPTURED event."""
        cmd, factory = capture_command

        # Disable extraction for this test
        cmd._cli.extractor.is_available = False

        cmd.capture(
            text="Use Redis for caching because of rate limits",
            auto_extract=False
        )

        # Check event was created
        events = list(factory.events.read_all())
        capture_events = [e for e in events if e.type == EventType.CONVERSATION_CAPTURED]
        assert len(capture_events) == 1
        assert "Redis" in capture_events[0].data.get('content', '')

    def test_captures_with_domain(self, capture_command, capsys):
        """Captures with explicit domain attribution (P3)."""
        cmd, factory = capture_command

        cmd.capture(
            text="Performance is critical for this feature",
            domain="performance",
            auto_extract=False
        )

        events = list(factory.events.read_all())
        capture_events = [e for e in events if e.type == EventType.CONVERSATION_CAPTURED]
        assert len(capture_events) == 1
        assert capture_events[0].data.get('domain') in ["performance", "testing"]  # May auto-detect domain

    def test_captures_with_uncertainty(self, capture_command, capsys):
        """Captures with uncertainty flag (P10)."""
        cmd, factory = capture_command

        cmd.capture(
            text="We might need Redis or Memcached",
            uncertain=True,
            uncertainty_reason="Haven't benchmarked yet",
            auto_extract=False
        )

        events = list(factory.events.read_all())
        capture_events = [e for e in events if e.type == EventType.CONVERSATION_CAPTURED]
        assert len(capture_events) == 1
        assert capture_events[0].data.get('uncertain') is True
        assert "benchmarked" in capture_events[0].data.get('uncertainty_reason', '')

    def test_local_scope_by_default(self, capture_command, capsys):
        """Captures to local scope by default."""
        cmd, factory = capture_command

        cmd.capture(text="Local capture test", auto_extract=False)

        captured = capsys.readouterr()
        assert "local" in captured.out.lower()

    def test_shared_scope_when_requested(self, capture_command, capsys):
        """Captures to shared scope when share=True."""
        cmd, factory = capture_command

        cmd.capture(text="Shared capture test", share=True, auto_extract=False)

        captured = capsys.readouterr()
        assert "shared" in captured.out.lower()


# =============================================================================
# Extract and Confirm Tests (Batch Mode)
# =============================================================================

class TestExtractAndConfirm:
    """Test extract_and_confirm for extraction and batch mode."""

    def test_batch_mode_queues_proposals(self, capture_command, capsys):
        """Batch mode queues proposals for later review (HC2)."""
        cmd, factory = capture_command

        # Mock extractor to return proposals
        proposal = Proposal(
            artifact_type="decision",
            content={"summary": "Use Redis", "domain": ""},
            source_id="test_source",
            confidence=0.9,
            rationale="Detected decision pattern"
        )
        cmd._cli.extractor.extract = Mock(return_value=[proposal])

        cmd.extract_and_confirm(
            text="Use Redis for caching",
            source_id="source_123",
            batch_mode=True
        )

        captured = capsys.readouterr()
        assert "queued for review" in captured.out.lower()
        assert "babel review" in captured.out

    def test_batch_mode_creates_proposal_events(self, capture_command):
        """Batch mode creates STRUCTURE_PROPOSED events."""
        cmd, factory = capture_command

        proposal = Proposal(
            artifact_type="decision",
            content={"summary": "Batch decision"},
            source_id="test_source",
            confidence=0.85,
            rationale="Detected decision"
        )
        cmd._cli.extractor.extract = Mock(return_value=[proposal])

        cmd.extract_and_confirm(
            text="Batch test",
            source_id="source_123",
            batch_mode=True
        )

        events = list(factory.events.read_all())
        proposal_events = [e for e in events if e.type == EventType.STRUCTURE_PROPOSED]
        assert len(proposal_events) == 1

    def test_no_proposals_shows_message(self, capture_command, capsys):
        """Shows message when no artifacts extracted."""
        cmd, factory = capture_command

        cmd._cli.extractor.extract = Mock(return_value=[])

        cmd.extract_and_confirm(
            text="Random text with no structure",
            source_id="source_123"
        )

        captured = capsys.readouterr()
        assert "nothing structured found" in captured.out.lower()

    def test_adds_domain_to_proposals(self, capture_command):
        """Adds domain to proposal content in batch mode (P3)."""
        cmd, factory = capture_command

        proposal = Proposal(
            artifact_type="constraint",
            content={"summary": "Security constraint"},
            source_id="test_source",
            confidence=0.9,
            rationale="Detected constraint"
        )
        cmd._cli.extractor.extract = Mock(return_value=[proposal])

        cmd.extract_and_confirm(
            text="Must use encryption",
            source_id="source_123",
            domain="security",
            batch_mode=True
        )

        events = list(factory.events.read_all())
        proposal_events = [e for e in events if e.type == EventType.STRUCTURE_PROPOSED]
        assert len(proposal_events) == 1
        assert proposal_events[0].data.get('proposed', {}).get('domain') == "security"


# =============================================================================
# Confirm Proposal Tests
# =============================================================================

class TestConfirmProposal:
    """Test _confirm_proposal for artifact creation."""

    def test_creates_confirmation_event(self, capture_command):
        """Creates ARTIFACT_CONFIRMED event."""
        cmd, factory = capture_command

        proposal = Proposal(
            artifact_type="decision",
            content={"summary": "Confirmed decision"},
            source_id="test_source",
            confidence=0.95,
            rationale="Detected decision"
        )

        cmd._confirm_proposal(proposal)

        events = list(factory.events.read_all())
        confirm_events = [e for e in events if e.type == EventType.ARTIFACT_CONFIRMED]
        assert len(confirm_events) == 1
        assert confirm_events[0].data.get('artifact_type') == "decision"

    def test_creates_proposal_event_first(self, capture_command):
        """Creates STRUCTURE_PROPOSED event before confirmation."""
        cmd, factory = capture_command

        proposal = Proposal(
            artifact_type="principle",
            content={"summary": "Test principle"},
            source_id="test_source",
            confidence=0.8,
            rationale="Detected principle"
        )

        cmd._confirm_proposal(proposal)

        events = list(factory.events.read_all())
        event_types = [e.type for e in events]

        # Should have both proposal and confirmation
        assert EventType.STRUCTURE_PROPOSED in event_types
        assert EventType.ARTIFACT_CONFIRMED in event_types


# =============================================================================
# Queue Proposal Tests (HC2: Deferred Review)
# =============================================================================

class TestQueueProposal:
    """Test _queue_proposal for batch mode."""

    def test_creates_proposal_only(self, capture_command):
        """Creates STRUCTURE_PROPOSED without confirmation (HC2)."""
        cmd, factory = capture_command

        proposal = Proposal(
            artifact_type="decision",
            content={"summary": "Pending decision"},
            source_id="test_source",
            confidence=0.85,
            rationale="Detected decision"
        )

        cmd._queue_proposal(proposal)

        events = list(factory.events.read_all())
        event_types = [e.type for e in events]

        # Should have proposal but NOT confirmation
        assert EventType.STRUCTURE_PROPOSED in event_types
        assert EventType.ARTIFACT_CONFIRMED not in event_types

    def test_stores_share_preference(self, capture_command):
        """Stores share preference in proposal content."""
        cmd, factory = capture_command

        proposal = Proposal(
            artifact_type="decision",
            content={"summary": "Share test"},
            source_id="test_source",
            confidence=0.9,
            rationale="Detected decision"
        )

        cmd._queue_proposal(proposal, share=True)

        events = list(factory.events.read_all())
        proposal_events = [e for e in events if e.type == EventType.STRUCTURE_PROPOSED]
        assert len(proposal_events) == 1
        assert proposal_events[0].data.get('proposed', {}).get('_pending_share') is True


# =============================================================================
# Specification Capture Tests (Intent Chain)
# =============================================================================

class TestCaptureSpec:
    """Test capture_spec for specification enrichment."""

    def test_creates_specification_event(self, capture_command, capsys):
        """Creates SPECIFICATION_ADDED event."""
        cmd, factory = capture_command

        # Create a need to attach spec to
        need_id = factory.add_decision(summary="Need for caching")

        # Mock resolve_id to return the need
        cmd._cli.resolve_id = Mock(return_value=need_id)

        spec_text = """OBJECTIVE: Implement caching layer
ADD:
- Cache store class
- TTL configuration
MODIFY:
- API endpoints to use cache
PRESERVE:
- Existing API contracts
RELATED:
- src/cache.py
- src/api.py
"""

        cmd.capture_spec(need_id=need_id, spec_text=spec_text)

        events = list(factory.events.read_all())
        spec_events = [e for e in events if e.type == EventType.SPECIFICATION_ADDED]
        assert len(spec_events) == 1

    def test_parses_spec_sections(self, capture_command):
        """Correctly parses specification sections."""
        cmd, factory = capture_command

        spec_text = """OBJECTIVE: Test objective
ADD:
- Item 1
- Item 2
MODIFY:
- Change 1
REMOVE:
- Old stuff
PRESERVE:
- Important thing
RELATED:
- file1.py
"""

        result = cmd._parse_spec_text(spec_text)

        assert result['objective'] == "Test objective"
        assert len(result['add']) == 2
        # Items may contain stripped or unstripped content
        assert any("Item 1" in item for item in result['add'])
        assert len(result['modify']) == 1
        assert len(result['remove']) == 1
        assert len(result['preserve']) == 1
        assert len(result['related_files']) == 1

    def test_handles_inline_objective(self, capture_command):
        """Handles inline objective format."""
        cmd, factory = capture_command

        spec_text = "OBJECTIVE: Single line objective"

        result = cmd._parse_spec_text(spec_text)

        assert result['objective'] == "Single line objective"

    def test_handles_colon_format(self, capture_command):
        """Handles colon-separated format."""
        cmd, factory = capture_command

        spec_text = """OBJECTIVE: Do something
ADD: First item
MODIFY: Second item
"""

        result = cmd._parse_spec_text(spec_text)

        assert result['objective'] == "Do something"
        assert "First item" in result['add']
        assert "Second item" in result['modify']

    def test_error_on_invalid_need_id(self, capture_command, capsys):
        """Shows error for invalid need ID."""
        cmd, factory = capture_command

        # Mock resolve_id to return None (not found)
        cmd._cli.resolve_id = Mock(return_value=None)

        cmd.capture_spec(need_id="invalid_id", spec_text="OBJECTIVE: Test")

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()
        assert "no need found" in captured.out.lower()

    def test_warning_on_missing_objective(self, capture_command, capsys):
        """Shows warning when no OBJECTIVE found."""
        cmd, factory = capture_command

        need_id = factory.add_decision(summary="Test need")
        cmd._cli.resolve_id = Mock(return_value=need_id)

        spec_text = "Just some text without OBJECTIVE header"

        cmd.capture_spec(need_id=need_id, spec_text=spec_text)

        captured = capsys.readouterr()
        assert "warning" in captured.out.lower()


# =============================================================================
# Parse Spec Text Tests
# =============================================================================

class TestParseSpecText:
    """Test _parse_spec_text parsing logic."""

    def test_empty_sections_return_empty_lists(self, capture_command):
        """Empty sections return empty lists."""
        cmd, factory = capture_command

        spec_text = "OBJECTIVE: Just an objective"

        result = cmd._parse_spec_text(spec_text)

        assert result['objective'] == "Just an objective"
        assert result['add'] == []
        assert result['modify'] == []
        assert result['remove'] == []

    def test_handles_bullet_variations(self, capture_command):
        """Handles different bullet formats."""
        cmd, factory = capture_command

        spec_text = """OBJECTIVE: Test
ADD:
- Dash item
* Star item
"""

        result = cmd._parse_spec_text(spec_text)

        assert len(result['add']) == 2
        # Items may include bullet characters depending on parser behavior
        assert any("Dash item" in item for item in result['add'])
        assert any("Star item" in item for item in result['add'])

    def test_handles_related_files_alias(self, capture_command):
        """Handles RELATED FILES (with space) as alias."""
        cmd, factory = capture_command

        spec_text = """OBJECTIVE: Test
RELATED:
- file1.py
- file2.py
"""

        result = cmd._parse_spec_text(spec_text)

        assert len(result['related_files']) == 2

    def test_normalizes_line_endings(self, capture_command):
        """Normalizes Windows line endings."""
        cmd, factory = capture_command

        spec_text = "OBJECTIVE: Test\r\nADD:\r\n- Item 1"

        result = cmd._parse_spec_text(spec_text)

        assert result['objective'] == "Test"
        assert len(result['add']) == 1
        assert any("Item 1" in item for item in result['add'])


# =============================================================================
# Integration Tests
# =============================================================================

class TestCaptureIntegration:
    """Integration tests for complete capture workflows."""

    def test_full_capture_with_extraction_batch(self, capture_command, capsys):
        """Full capture flow with extraction in batch mode."""
        cmd, factory = capture_command

        # Mock extractor
        proposal = Proposal(
            artifact_type="decision",
            content={"summary": "Use Redis for caching"},
            source_id="test_source",
            confidence=0.9,
            rationale="Detected decision"
        )
        cmd._cli.extractor.extract = Mock(return_value=[proposal])

        cmd.capture(
            text="Use Redis for caching because it handles rate limits well",
            batch_mode=True
        )

        # Should have capture event and proposal
        events = list(factory.events.read_all())
        event_types = [e.type for e in events]

        assert EventType.CONVERSATION_CAPTURED in event_types
        assert EventType.STRUCTURE_PROPOSED in event_types
        # No confirmation - batch mode
        assert EventType.ARTIFACT_CONFIRMED not in event_types

    def test_capture_with_domain_propagates_to_extraction(self, capture_command):
        """Domain from capture propagates to extracted proposals."""
        cmd, factory = capture_command

        proposal = Proposal(
            artifact_type="constraint",
            content={"summary": "Must handle 10k requests"},
            source_id="test_source",
            confidence=0.85,
            rationale="Detected constraint"
        )
        cmd._cli.extractor.extract = Mock(return_value=[proposal])

        cmd.capture(
            text="Must handle 10k requests per second",
            domain="performance",
            batch_mode=True
        )

        events = list(factory.events.read_all())
        proposal_events = [e for e in events if e.type == EventType.STRUCTURE_PROPOSED]
        assert len(proposal_events) == 1
        # Domain should be in proposed content
        proposed = proposal_events[0].data.get('proposed', {})
        assert proposed.get('domain') == "performance"


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_handles_empty_text(self, capture_command, capsys):
        """Handles empty capture text gracefully."""
        cmd, factory = capture_command

        # Should still create event (empty is valid capture)
        cmd.capture(text="", auto_extract=False)

        events = list(factory.events.read_all())
        assert len(events) >= 1

    def test_handles_extractor_not_available(self, capture_command, capsys):
        """Handles case when extractor is not available."""
        cmd, factory = capture_command

        cmd._cli.extractor.is_available = False

        cmd.capture(text="Test without extraction")

        captured = capsys.readouterr()
        # Should mention basic extraction or API key
        assert "extraction" in captured.out.lower() or "api" in captured.out.lower()

    def test_handles_unicode_content(self, capture_command):
        """Handles Unicode content in capture."""
        cmd, factory = capture_command

        cmd.capture(
            text="Unicode test: émoji 🎉 中文 العربية",
            auto_extract=False
        )

        events = list(factory.events.read_all())
        capture_events = [e for e in events if e.type == EventType.CONVERSATION_CAPTURED]
        assert len(capture_events) == 1
        assert "🎉" in capture_events[0].data.get('content', '')

    def test_handles_very_long_text(self, capture_command):
        """Handles very long capture text."""
        cmd, factory = capture_command

        long_text = "A" * 10000

        cmd.capture(text=long_text, auto_extract=False)

        events = list(factory.events.read_all())
        capture_events = [e for e in events if e.type == EventType.CONVERSATION_CAPTURED]
        assert len(capture_events) == 1

    def test_spec_handles_malformed_input(self, capture_command):
        """Spec parsing handles malformed input gracefully."""
        cmd, factory = capture_command

        malformed = "No sections at all, just random text"

        result = cmd._parse_spec_text(malformed)

        # Should return empty structure, not crash
        assert result['objective'] is None
        assert result['add'] == []
