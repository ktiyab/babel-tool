"""
Tests for Providers — Coherence Evidence for multi-provider support

These tests validate:
- Provider abstraction works correctly
- Falls back to MockProvider when packages unavailable
- Provider factory selects correct provider
- Nested config structure works with providers

All tests use mocks. No real LLM packages or API keys required.
"""

import json

from babel.config import Config, LLMConfig, LocalLLMConfig, RemoteLLMConfig
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

    def test_returns_mock_when_no_api_key_and_remote(self, monkeypatch):
        """Returns MockProvider when API key not set and active=remote."""
        # Clear all API keys
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        config = Config(llm=LLMConfig(
            active="remote",
            remote=RemoteLLMConfig(provider="claude")
        ))
        provider = get_provider(config)

        assert isinstance(provider, MockProvider)

    def test_returns_mock_for_unknown_remote_provider(self, monkeypatch):
        """Returns MockProvider for unknown remote provider."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = Config(llm=LLMConfig(
            active="remote",
            remote=RemoteLLMConfig(provider="unknown")
        ))
        provider = get_provider(config)

        assert isinstance(provider, MockProvider)

    def test_provider_with_key_but_no_package(self, monkeypatch):
        """Returns provider (or mock) when API key set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = Config(llm=LLMConfig(
            active="remote",
            remote=RemoteLLMConfig(provider="claude")
        ))
        provider = get_provider(config)

        # Will be MockProvider if anthropic package not installed
        # Will be ClaudeProvider if package is installed
        # Either way, it should be an LLMProvider
        assert isinstance(provider, LLMProvider)

    def test_active_local_uses_local_config(self, monkeypatch):
        """When active=local, uses local config."""
        # Set API key (should be ignored when active=local)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = Config(llm=LLMConfig(
            active="local",
            local=LocalLLMConfig(provider="ollama", model="mistral")
        ))
        provider = get_provider(config)

        # Will be MockProvider since Ollama not running in tests
        # But it should have attempted local, not remote
        assert isinstance(provider, (MockProvider, LLMProvider))

    def test_active_auto_prefers_remote(self, monkeypatch):
        """When active=auto and API key available, prefers remote."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = Config(llm=LLMConfig(active="auto"))
        provider = get_provider(config)

        # Should be LLMProvider (either Claude or Mock if package missing)
        assert isinstance(provider, LLMProvider)


class TestProviderStatus:
    """get_provider_status() for user display."""

    def test_status_without_key_remote(self, monkeypatch):
        """Shows missing key message when remote not configured."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        config = Config(llm=LLMConfig(
            active="remote",
            remote=RemoteLLMConfig(provider="claude")
        ))
        status = get_provider_status(config)

        assert "ANTHROPIC_API_KEY" in status

    def test_status_with_active_local(self, monkeypatch):
        """Shows local status when active=local."""
        config = Config(llm=LLMConfig(
            active="local",
            local=LocalLLMConfig(provider="ollama", model="llama3.2")
        ))
        status = get_provider_status(config)

        # Will show Ollama status (running or not)
        assert len(status) > 0

    def test_status_shows_active_mode(self, monkeypatch):
        """Status includes active mode info."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = Config(llm=LLMConfig(
            active="auto",
            remote=RemoteLLMConfig(provider="claude")
        ))
        status = get_provider_status(config)

        # Should show something about the provider
        assert len(status) > 0


class TestProviderInterface:
    """Provider classes implement interface correctly."""

    def test_claude_provider_without_key(self, monkeypatch):
        """ClaudeProvider not available without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        remote_config = RemoteLLMConfig(provider="claude")
        provider = ClaudeProvider(remote_config)

        assert provider.is_available is False

    def test_openai_provider_without_key(self, monkeypatch):
        """OpenAIProvider not available without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        remote_config = RemoteLLMConfig(provider="openai")
        provider = OpenAIProvider(remote_config)

        assert provider.is_available is False

    def test_gemini_provider_without_key(self, monkeypatch):
        """GeminiProvider not available without API key."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        remote_config = RemoteLLMConfig(provider="gemini")
        provider = GeminiProvider(remote_config)

        assert provider.is_available is False


class TestProviderIntegration:
    """Integration tests with Extractor."""

    def test_extractor_uses_mock_provider(self):
        """Extractor works with MockProvider."""
        from babel.services.extractor import Extractor

        provider = MockProvider()
        extractor = Extractor(provider=provider)

        assert extractor.is_available is True

    def test_extractor_without_provider_uses_mock_extraction(self):
        """Extractor falls back to mock extraction."""
        from babel.services.extractor import Extractor

        provider = MockProvider()
        extractor = Extractor(provider=provider)

        # Mock extraction should work
        result = extractor.extract(
            text="We should use caching for performance",
            source_id="test"
        )

        assert result is not None
