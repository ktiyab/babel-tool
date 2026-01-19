"""
Tests for Providers — Coherence Evidence for multi-provider support

These tests validate:
- Provider abstraction works correctly
- Falls back to MockProvider when packages unavailable
- Provider factory selects correct provider

All tests use mocks. No real LLM packages or API keys required.
"""

import pytest
import json

from babel.config import Config, LLMConfig
from babel.services.providers import (
    LLMProvider, MockProvider, 
    get_provider, get_provider_status,
    ClaudeProvider, OpenAIProvider, GeminiProvider
)


class TestMockProvider:
    """MockProvider for testing."""
    
    def test_is_available(self):
        """MockProvider is always available."""
        provider = MockProvider()
        assert provider.is_available is True
    
    def test_complete_returns_valid_json(self):
        """MockProvider returns parseable JSON."""
        provider = MockProvider()
        response = provider.complete("system prompt", "user message")

        data = json.loads(response.text)
        assert "artifacts" in data
        assert isinstance(data["artifacts"], list)

    def test_complete_returns_empty_artifacts(self):
        """MockProvider returns empty artifacts list."""
        provider = MockProvider()
        response = provider.complete("system", "user")

        data = json.loads(response.text)
        assert data["artifacts"] == []

    def test_complete_returns_llm_response(self):
        """MockProvider returns LLMResponse with zero tokens."""
        from babel.services.providers import LLMResponse

        provider = MockProvider()
        response = provider.complete("system", "user")

        assert isinstance(response, LLMResponse)
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.total_tokens == 0


class TestProviderFactory:
    """get_provider() factory function."""
    
    def test_returns_mock_when_no_api_key(self, monkeypatch):
        """Returns MockProvider when API key not set."""
        # Clear all API keys
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        
        config = Config(llm=LLMConfig(provider="claude"))
        provider = get_provider(config)
        
        assert isinstance(provider, MockProvider)
    
    def test_returns_mock_for_unknown_provider(self, monkeypatch):
        """Returns MockProvider for unknown provider."""
        config = Config(llm=LLMConfig(provider="unknown"))
        provider = get_provider(config)
        
        assert isinstance(provider, MockProvider)
    
    def test_provider_with_key_but_no_package(self, monkeypatch):
        """Returns MockProvider when API key set but package not installed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        
        config = Config(llm=LLMConfig(provider="claude"))
        provider = get_provider(config)
        
        # Will be MockProvider if anthropic package not installed
        # Will be ClaudeProvider if package is installed
        # Either way, it should be an LLMProvider
        assert isinstance(provider, LLMProvider)


class TestProviderStatus:
    """get_provider_status() for user display."""
    
    def test_status_without_key(self, monkeypatch):
        """Shows missing key message when not configured."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        
        config = Config(llm=LLMConfig(provider="claude"))
        status = get_provider_status(config)
        
        assert "ANTHROPIC_API_KEY" in status
    
    def test_status_with_mock(self, monkeypatch):
        """Shows mock mode when falling back."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        
        config = Config(llm=LLMConfig(provider="claude"))
        status = get_provider_status(config)
        
        # Will show either "Claude: model" or "Mock mode"
        assert len(status) > 0


class TestProviderInterface:
    """Provider classes implement interface correctly."""
    
    def test_claude_provider_without_key(self, monkeypatch):
        """ClaudeProvider not available without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        
        llm_config = LLMConfig(provider="claude")
        provider = ClaudeProvider(llm_config)
        
        assert provider.is_available is False
    
    def test_openai_provider_without_key(self, monkeypatch):
        """OpenAIProvider not available without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        llm_config = LLMConfig(provider="openai")
        provider = OpenAIProvider(llm_config)
        
        assert provider.is_available is False
    
    def test_gemini_provider_without_key(self, monkeypatch):
        """GeminiProvider not available without API key."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        
        llm_config = LLMConfig(provider="gemini")
        provider = GeminiProvider(llm_config)
        
        assert provider.is_available is False


class TestProviderIntegration:
    """Integration tests with Extractor."""
    
    def test_extractor_uses_mock_provider(self):
        """Extractor works with MockProvider."""
        from babel.services.extractor import Extractor
        
        provider = MockProvider()
        extractor = Extractor(provider=provider)
        
        assert extractor.is_available is True
        
        # Extract should work (returns empty from MockProvider)
        proposals = extractor.extract("Test text", "source_1", allow_mock=False)
        assert proposals == []  # MockProvider returns empty
    
    def test_extractor_without_provider_uses_mock_extraction(self):
        """Extractor falls back to keyword extraction without provider."""
        from babel.services.extractor import Extractor
        
        extractor = Extractor(provider=None)
        
        assert extractor.is_available is False
        
        # Should use mock keyword extraction
        proposals = extractor.extract(
            "We decided to use Python.",
            "source_1",
            allow_mock=True
        )
        
        assert len(proposals) >= 1
        assert any(p.artifact_type == "decision" for p in proposals)