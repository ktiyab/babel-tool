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
    
    Args:
        config: Application configuration
        
    Returns:
        Configured provider, or MockProvider if none available
    """
    llm = config.llm
    
    providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider
    }
    
    provider_class = providers.get(llm.provider)
    
    if provider_class:
        provider = provider_class(llm)
        if provider.is_available:
            return provider
    
    # Fall back to mock if no provider available
    return MockProvider()


def get_provider_status(config: Config) -> str:
    """Get human-readable provider status."""
    llm = config.llm

    if not llm.api_key:
        return f"LLM not configured (set {llm.api_key_env} environment variable)"

    # Check if provider package is installed
    package_map = {
        "claude": ("anthropic", "pip install anthropic"),
        "openai": ("openai", "pip install openai"),
        "gemini": ("google.generativeai", "pip install google-generativeai")
    }

    if llm.provider in package_map:
        module_name, install_cmd = package_map[llm.provider]
        try:
            __import__(module_name.split('.')[0])
        except ImportError:
            return f"LLM package missing: {install_cmd}"

    provider = get_provider(config)

    if isinstance(provider, MockProvider):
        # Fallback - shouldn't reach here normally
        return "LLM unavailable (check configuration)"

    return f"{llm.provider.title()}: {llm.effective_model}"