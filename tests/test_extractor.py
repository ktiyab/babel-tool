"""
Tests for Extractor — Coherence Evidence for P-FRICTION, TD4

These tests validate:
- P-FRICTION: Low friction capture, system proposes structure
- TD4: Local-first, queue when offline
- HC2: AI proposes, never commits without human

All tests use MockProvider or mock extraction.
No real LLM calls — tests work without API keys or packages.
"""

import pytest
import json
from pathlib import Path

from babel.services.extractor import Extractor, Proposal, ExtractionQueue
from babel.services.providers import MockProvider


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_extractor():
    """Extractor with no provider (uses mock keyword extraction)."""
    return Extractor(provider=None)


@pytest.fixture
def provider_extractor():
    """Extractor with MockProvider (simulates real provider)."""
    return Extractor(provider=MockProvider())


# ============================================================================
# MOCK EXTRACTION TESTS
# ============================================================================

class TestMockExtraction:
    """P-FRICTION: System proposes structure from natural language."""
    
    def test_detects_decision(self, mock_extractor):
        """Decisions are detected from keywords."""
        proposals = mock_extractor.extract(
            "We decided to use Python because it's fastest for prototyping.",
            source_id="test_123"
        )
        
        assert len(proposals) >= 1
        assert any(p.artifact_type == "decision" for p in proposals)
    
    def test_detects_purpose(self, mock_extractor):
        """Purposes are detected from keywords."""
        proposals = mock_extractor.extract(
            "Our goal is to build a tool that preserves babel.",
            source_id="test_123"
        )
        
        assert len(proposals) >= 1
        assert any(p.artifact_type == "purpose" for p in proposals)
    
    def test_detects_constraint(self, mock_extractor):
        """Constraints are detected from keywords."""
        proposals = mock_extractor.extract(
            "The system must work offline. We cannot require internet.",
            source_id="test_123"
        )
        
        assert len(proposals) >= 1
        assert any(p.artifact_type == "constraint" for p in proposals)
    
    def test_detects_principle(self, mock_extractor):
        """Principles are detected from keywords."""
        proposals = mock_extractor.extract(
            "We learned that you should always write tests first.",
            source_id="test_123"
        )
        
        assert len(proposals) >= 1
        assert any(p.artifact_type == "principle" for p in proposals)
    
    def test_detects_tension(self, mock_extractor):
        """Tensions are detected from keywords."""
        proposals = mock_extractor.extract(
            "There's a tradeoff between simplicity vs completeness.",
            source_id="test_123"
        )
        
        assert len(proposals) >= 1
        assert any(p.artifact_type == "tension" for p in proposals)
    
    def test_no_extraction_on_neutral_text(self, mock_extractor):
        """Neutral text produces no proposals."""
        proposals = mock_extractor.extract(
            "The weather is nice today.",
            source_id="test_123"
        )
        
        assert len(proposals) == 0
    
    def test_multiple_artifacts_in_single_text(self, mock_extractor):
        """Multiple artifact types can be extracted from rich text."""
        proposals = mock_extractor.extract(
            "We decided to use SQLite. Our goal is offline support. "
            "The system must never lose data. We learned that simplicity wins.",
            source_id="test_123"
        )
        
        types = {p.artifact_type for p in proposals}
        assert len(types) >= 3  # Should detect multiple types


# ============================================================================
# PROPOSAL FORMAT TESTS
# ============================================================================

class TestProposalFormat:
    """HC6: User-facing language is jargon-free."""
    
    def test_confidence_to_human_language(self, mock_extractor):
        """Confidence scores become readable words."""
        high = Proposal("src", "decision", {"summary": "X"}, 0.95, "test")
        medium = Proposal("src", "decision", {"summary": "X"}, 0.75, "test")
        low = Proposal("src", "decision", {"summary": "X"}, 0.45, "test")
        
        high_text = mock_extractor.format_for_confirmation(high)
        medium_text = mock_extractor.format_for_confirmation(medium)
        low_text = mock_extractor.format_for_confirmation(low)
        
        assert "clearly" in high_text
        assert "likely" in medium_text
        assert "might be" in low_text
    
    def test_artifact_type_to_human_language(self, mock_extractor):
        """Artifact types become readable descriptions."""
        proposal = Proposal("src", "constraint", {"summary": "Must work offline"}, 0.8, "test")
        text = mock_extractor.format_for_confirmation(proposal)
        
        assert "constraint or requirement" in text
        assert "Must work offline" in text


# ============================================================================
# EXTRACTION QUEUE TESTS
# ============================================================================

class TestExtractionQueue:
    """TD4: Local-first, queue when offline."""
    
    def test_queue_persists(self, tmp_path):
        """Queued items survive restart."""
        queue_path = tmp_path / "queue.jsonl"
        
        queue1 = ExtractionQueue(queue_path)
        queue1.add("Test text", "source_1")
        queue1.add("More text", "source_2")
        
        # Recreate queue (simulates restart)
        queue2 = ExtractionQueue(queue_path)
        items = queue2.get_all()
        
        assert len(items) == 2
        assert items[0].text == "Test text"
        assert items[1].source_id == "source_2"
    
    def test_queue_clears(self, tmp_path):
        """Queue can be cleared after processing."""
        queue = ExtractionQueue(tmp_path / "queue.jsonl")
        
        queue.add("Text 1", "src_1")
        queue.add("Text 2", "src_2")
        assert queue.count() == 2
        
        queue.clear()
        assert queue.count() == 0
    
    def test_queue_count(self, tmp_path):
        """Queue tracks item count."""
        queue = ExtractionQueue(tmp_path / "queue.jsonl")
        
        assert queue.count() == 0
        queue.add("Text", "src")
        assert queue.count() == 1
    
    def test_extractor_queues_when_offline(self, tmp_path):
        """Extractor queues requests when provider unavailable."""
        queue_path = tmp_path / "queue.jsonl"
        extractor = Extractor(provider=None, queue_path=queue_path)
        
        # Extract without mock fallback - should queue
        proposals = extractor.extract(
            "Test text to queue",
            source_id="test_1",
            allow_mock=False
        )
        
        assert proposals == []  # Nothing extracted
        assert extractor.queue.count() == 1  # But queued for later


# ============================================================================
# EXTRACTOR AVAILABILITY TESTS
# ============================================================================

class TestExtractorAvailability:
    """Extractor handles missing LLM gracefully."""
    
    def test_not_available_without_provider(self):
        """Reports unavailable when no provider."""
        extractor = Extractor(provider=None)
        assert extractor.is_available is False
    
    def test_available_with_mock_provider(self):
        """Reports available with mock provider."""
        extractor = Extractor(provider=MockProvider())
        assert extractor.is_available is True
    
    def test_falls_back_to_mock(self, mock_extractor):
        """Falls back to mock extraction when no provider."""
        proposals = mock_extractor.extract(
            "We decided to use mock mode.",
            source_id="test"
        )
        
        # Should still extract using mock
        assert len(proposals) >= 1


# ============================================================================
# RESPONSE PARSING TESTS
# ============================================================================

class TestResponseParsing:
    """LLM response parsing handles edge cases."""
    
    def test_parses_clean_json(self, mock_extractor):
        """Parses well-formed JSON response."""
        response = json.dumps({
            "artifacts": [{
                "type": "decision",
                "summary": "Use Python",
                "content": {"what": "Language choice"},
                "confidence": 0.9,
                "rationale": "Explicit statement"
            }],
            "meta": {"extractable": True}
        })
        
        proposals = mock_extractor._parse_response(response, "src_123")
        
        assert len(proposals) == 1
        assert proposals[0].artifact_type == "decision"
        assert proposals[0].confidence == 0.9
    
    def test_handles_markdown_wrapped_json(self, mock_extractor):
        """Strips markdown code fences from response."""
        response = """```json
{
    "artifacts": [{
        "type": "purpose",
        "summary": "Build great things",
        "confidence": 0.85,
        "rationale": "Clear goal"
    }]
}
```"""
        
        proposals = mock_extractor._parse_response(response, "src_123")
        
        assert len(proposals) == 1
        assert proposals[0].artifact_type == "purpose"
    
    def test_handles_malformed_json(self, mock_extractor):
        """Returns empty list on parse failure."""
        response = "This is not JSON at all"
        
        proposals = mock_extractor._parse_response(response, "src_123")
        
        assert proposals == []
    
    def test_handles_empty_artifacts(self, mock_extractor):
        """Handles response with no artifacts."""
        response = json.dumps({
            "artifacts": [],
            "meta": {"extractable": False, "reason": "No structure found"}
        })
        
        proposals = mock_extractor._parse_response(response, "src_123")
        
        assert proposals == []


# ============================================================================
# MOCK PROVIDER TESTS
# ============================================================================

class TestMockProvider:
    """Mock provider for testing."""
    
    def test_mock_is_available(self):
        """Mock provider reports available."""
        provider = MockProvider()
        assert provider.is_available is True
    
    def test_mock_returns_empty_extraction(self):
        """Mock provider returns valid empty response."""
        provider = MockProvider()
        response = provider.complete("system", "user")

        data = json.loads(response.text)
        assert "artifacts" in data
        assert data["artifacts"] == []


# ============================================================================
# PROVIDER EXTRACTION TESTS
# ============================================================================

class TestProviderExtraction:
    """Extraction using provider abstraction."""
    
    def test_uses_provider_when_available(self, provider_extractor):
        """Uses provider's complete() when available."""
        # MockProvider returns empty artifacts
        proposals = provider_extractor.extract(
            "We decided to test the provider.",
            source_id="test",
            allow_mock=False  # Force provider, no mock fallback
        )
        
        # MockProvider returns empty, so no proposals
        assert proposals == []
    
    def test_extractor_is_available_with_provider(self, provider_extractor):
        """Extractor reports available when provider is set."""
        assert provider_extractor.is_available is True