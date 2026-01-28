"""
LLM Providers — Abstraction for multiple AI providers

Supports: Claude, OpenAI, Gemini
All providers implement same interface for extraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from ..config import Config, LLMConfig


@dataclass
class LLMResponse:
    """Response from LLM including token usage."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def format_tokens(self, symbols=None) -> str:
        """Format token usage for display."""
        if symbols:
            return f"{symbols.tokens_in}{self.input_tokens} {symbols.tokens_out}{self.output_tokens} {symbols.tokens_total}{self.total_tokens}"
        return f"in:{self.input_tokens} out:{self.output_tokens} total:{self.total_tokens}"


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        """
        Get completion from LLM.

        Args:
            system: System prompt
            user: User message
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with text and token usage
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and ready."""
        pass


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
        self._init_client()
    
    def _init_client(self):
        if not self.config.api_key:
            return
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
        except ImportError:
            pass
    
    @property
    def is_available(self) -> bool:
        return self._client is not None
    
    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        if not self._client:
            raise RuntimeError("Claude client not initialized")

        message = self._client.messages.create(
            model=self.config.effective_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )

        # Extract token usage from response
        input_tokens = getattr(message.usage, 'input_tokens', 0)
        output_tokens = getattr(message.usage, 'output_tokens', 0)

        return LLMResponse(
            text=message.content[0].text,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
        self._init_client()
    
    def _init_client(self):
        if not self.config.api_key:
            return
        try:
            import openai
            self._client = openai.OpenAI(api_key=self.config.api_key)
        except ImportError:
            pass
    
    @property
    def is_available(self) -> bool:
        return self._client is not None
    
    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")

        response = self._client.chat.completions.create(
            model=self.config.effective_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )

        # Extract token usage from response
        usage = getattr(response, 'usage', None)
        input_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
        output_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0

        return LLMResponse(
            text=response.choices[0].message.content,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
        self._init_client()
    
    def _init_client(self):
        if not self.config.api_key:
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            self._client = genai.GenerativeModel(self.config.effective_model)
        except ImportError:
            pass
    
    @property
    def is_available(self) -> bool:
        return self._client is not None
    
    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        if not self._client:
            raise RuntimeError("Gemini client not initialized")

        # Gemini combines system and user in prompt
        full_prompt = f"{system}\n\n---\n\n{user}"

        response = self._client.generate_content(
            full_prompt,
            generation_config={"max_output_tokens": max_tokens}
        )

        # Extract token usage from response metadata
        usage_metadata = getattr(response, 'usage_metadata', None)
        input_tokens = getattr(usage_metadata, 'prompt_token_count', 0) if usage_metadata else 0
        output_tokens = getattr(usage_metadata, 'candidates_token_count', 0) if usage_metadata else 0

        return LLMResponse(
            text=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider.

    Uses OpenAI-compatible API at localhost:11434/v1/chat/completions.
    No external package required - uses stdlib urllib.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._available: Optional[bool] = None  # Cached availability

    @property
    def base_url(self) -> str:
        """Get base URL for Ollama API."""
        return self.config.effective_base_url or "http://localhost:11434"

    def _check_ollama_running(self) -> bool:
        """Check if Ollama is running by querying the API."""
        import urllib.request
        import urllib.error

        try:
            # Try to reach Ollama's tags endpoint (lists models)
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            return False

    @property
    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        if self._available is None:
            self._available = self._check_ollama_running()
        return self._available

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        """
        Get completion from Ollama using OpenAI-compatible API.

        Uses urllib (stdlib) to avoid external dependencies.
        """
        import urllib.request
        import urllib.error
        import json

        if not self.is_available:
            raise RuntimeError(
                f"Ollama not running at {self.base_url}. "
                "Start with: ollama serve"
            )

        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.config.effective_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": max_tokens,
            "stream": False
        }

        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
        }

        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))

                # Extract response text
                text = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                # Extract token usage (Ollama provides this in OpenAI format)
                usage = result.get('usage', {})
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)

                return LLMResponse(
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError(
                    f"Model '{self.config.effective_model}' not found. "
                    f"Pull with: ollama pull {self.config.effective_model}"
                )
            raise RuntimeError(f"Ollama API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: ollama serve"
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid response from Ollama: {e}")


class MockProvider(LLMProvider):
    """Mock provider for testing."""
    
    def __init__(self):
        self._available = True
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        # Return empty extraction for mock (no tokens consumed)
        return LLMResponse(
            text='{"artifacts": [], "meta": {"extractable": false, "reason": "Mock provider"}}',
            input_tokens=0,
            output_tokens=0
        )


def get_provider(config: Config) -> LLMProvider:
    """
    Get LLM provider based on configuration.

    Uses nested config structure:
      - llm.active controls which config to use ("local", "remote", "auto")
      - llm.local contains local LLM settings (Ollama)
      - llm.remote contains remote LLM settings (Claude, OpenAI, Gemini)

    Selection logic:
      - "local": Use llm.local config with local provider
      - "remote": Use llm.remote config with remote provider
      - "auto": Use remote if API key available, else local

    Args:
        config: Application configuration

    Returns:
        Configured provider, or MockProvider if none available
    """
    llm = config.llm

    # Provider class mappings
    remote_providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider
    }

    local_providers = {
        "ollama": OllamaProvider
    }

    # Get active config and whether it's local
    active_config, is_local = llm.get_active_config()

    if is_local:
        # Use local provider with local config
        provider_name = active_config.provider
        if provider_name in local_providers:
            provider_class = local_providers[provider_name]
            provider = provider_class(active_config)
            if provider.is_available:
                return provider
        # Fallback: try any local provider
        for provider_class in local_providers.values():
            provider = provider_class(active_config)
            if provider.is_available:
                return provider
    else:
        # Use remote provider with remote config
        provider_name = active_config.provider
        if provider_name in remote_providers:
            provider_class = remote_providers[provider_name]
            provider = provider_class(active_config)
            if provider.is_available:
                return provider

    # Fall back to mock if no provider available
    return MockProvider()


def get_provider_status(config: Config) -> str:
    """Get human-readable provider status."""
    llm = config.llm

    # Get active config and whether it's local
    active_config, is_local = llm.get_active_config()

    if is_local:
        # Local provider status
        provider = get_provider(config)

        if isinstance(provider, MockProvider):
            # Ollama not running
            base_url = active_config.effective_base_url
            return f"Ollama not running at {base_url}. Start with: ollama serve"

        if isinstance(provider, OllamaProvider):
            return f"Ollama: {active_config.effective_model} (local, active={llm.active})"

        return f"{active_config.provider.title()}: {active_config.effective_model} (local)"

    # Remote provider status
    if not active_config.api_key:
        return f"LLM not configured (set {active_config.api_key_env} environment variable)"

    # Check if provider package is installed
    package_map = {
        "claude": ("anthropic", "pip install anthropic"),
        "openai": ("openai", "pip install openai"),
        "gemini": ("google.generativeai", "pip install google-generativeai")
    }

    if active_config.provider in package_map:
        module_name, install_cmd = package_map[active_config.provider]
        try:
            __import__(module_name.split('.')[0])
        except ImportError:
            return f"LLM package missing: {install_cmd}"

    provider = get_provider(config)

    if isinstance(provider, MockProvider):
        # Fallback - shouldn't reach here normally
        return "LLM unavailable (check configuration)"

    return f"{active_config.provider.title()}: {active_config.effective_model} (active={llm.active})"