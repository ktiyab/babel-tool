"""
Tests for Config — Coherence Evidence for centralized configuration

These tests validate:
- Config hierarchy (project > user > env > defaults)
- Provider configuration
- API key security (never in files)

All tests use mocks. No real LLM packages required.
"""

import pytest
import os
from pathlib import Path

from babel.config import Config, LLMConfig, ConfigManager, PROVIDERS, DEFAULT_PROVIDER


class TestLLMConfig:
    """LLM configuration validation."""
    
    def test_default_provider(self):
        """Default provider is claude."""
        config = LLMConfig()
        assert config.provider == "claude"
    
    def test_effective_model_uses_default(self):
        """Uses provider's default model when not specified."""
        config = LLMConfig(provider="claude", model=None)
        assert config.effective_model == PROVIDERS["claude"]["default_model"]
    
    def test_effective_model_uses_specified(self):
        """Uses specified model when provided."""
        config = LLMConfig(provider="claude", model="claude-opus-4-20250514")
        assert config.effective_model == "claude-opus-4-20250514"
    
    def test_api_key_from_environment(self, monkeypatch):
        """API key comes from environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
        config = LLMConfig(provider="claude")
        assert config.api_key == "test-key-123"
    
    def test_api_key_missing(self, monkeypatch):
        """API key is None when not in environment."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = LLMConfig(provider="claude")
        assert config.api_key is None
    
    def test_is_available_with_key(self, monkeypatch):
        """is_available True when API key present."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig(provider="claude")
        assert config.is_available is True
    
    def test_is_available_without_key(self, monkeypatch):
        """is_available False when API key missing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = LLMConfig(provider="claude")
        assert config.is_available is False
    
    def test_validate_unknown_provider(self):
        """Validation fails for unknown provider."""
        config = LLMConfig(provider="unknown")
        error = config.validate()
        assert error is not None
        assert "Unknown provider" in error
    
    def test_validate_unknown_model(self):
        """Validation fails for unknown model."""
        config = LLMConfig(provider="claude", model="claude-nonexistent")
        error = config.validate()
        assert error is not None
        assert "Unknown model" in error
    
    def test_validate_valid_config(self):
        """Validation passes for valid config."""
        config = LLMConfig(provider="claude", model="claude-sonnet-4-20250514")
        error = config.validate()
        assert error is None


class TestConfigManager:
    """Configuration loading and saving."""
    
    def test_load_defaults(self, tmp_path):
        """Loads defaults when no config files exist."""
        manager = ConfigManager(tmp_path)
        config = manager.load()
        
        assert config.llm.provider == DEFAULT_PROVIDER
    
    def test_save_and_load_project(self, tmp_path):
        """Saves and loads project config."""
        manager = ConfigManager(tmp_path)
        
        config = Config(llm=LLMConfig(provider="openai", model="gpt-4o"))
        manager.save_project(config)
        
        # Reload
        manager2 = ConfigManager(tmp_path)
        loaded = manager2.load()
        
        assert loaded.llm.provider == "openai"
        assert loaded.llm.model == "gpt-4o"
    
    def test_project_overrides_user(self, tmp_path, monkeypatch):
        """Project config takes priority over user config."""
        # Create user config
        user_dir = tmp_path / "home" / ".intent"
        user_dir.mkdir(parents=True)
        user_config = user_dir / "config.yaml"
        user_config.write_text("llm:\n  provider: gemini\n")
        
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        proj_config_dir = project_dir / ".intent"
        proj_config_dir.mkdir()
        proj_config = proj_config_dir / "config.yaml"
        proj_config.write_text("llm:\n  provider: openai\n")
        
        # Patch user config path
        manager = ConfigManager(project_dir)
        manager.USER_CONFIG_FILE = user_config
        
        config = manager.load()
        
        # Project wins
        assert config.llm.provider == "openai"
    
    def test_environment_overrides_files(self, tmp_path, monkeypatch):
        """Environment variables override config files."""
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        proj_config_dir = project_dir / ".intent"
        proj_config_dir.mkdir()
        proj_config = proj_config_dir / "config.yaml"
        proj_config.write_text("llm:\n  provider: gemini\n")
        
        # Set environment
        monkeypatch.setenv("BABEL_LLM_PROVIDER", "claude")
        
        manager = ConfigManager(project_dir)
        config = manager.load()
        
        # Environment wins
        assert config.llm.provider == "claude"
    
    def test_set_valid_config(self, tmp_path):
        """Can set valid configuration values."""
        manager = ConfigManager(tmp_path)
        
        error = manager.set("llm.provider", "openai")
        assert error is None
        
        config = manager.load()
        assert config.llm.provider == "openai"
    
    def test_set_invalid_provider(self, tmp_path):
        """Set returns error for invalid provider."""
        manager = ConfigManager(tmp_path)
        
        error = manager.set("llm.provider", "invalid")
        assert error is not None
        assert "Unknown provider" in error
    
    def test_set_invalid_key_format(self, tmp_path):
        """Set returns error for invalid key format."""
        manager = ConfigManager(tmp_path)
        
        error = manager.set("invalid", "value")
        assert error is not None
        assert "Invalid key format" in error
    
    def test_get_config_value(self, tmp_path):
        """Can get configuration values."""
        manager = ConfigManager(tmp_path)
        manager.set("llm.provider", "gemini")
        
        value = manager.get("llm.provider")
        assert value == "gemini"


class TestProviders:
    """Provider configuration."""
    
    def test_all_providers_have_required_fields(self):
        """All providers have required configuration."""
        for name, config in PROVIDERS.items():
            assert "env_key" in config
            assert "default_model" in config
            assert "models" in config
            assert len(config["models"]) > 0
    
    def test_claude_config(self):
        """Claude provider is correctly configured."""
        assert PROVIDERS["claude"]["env_key"] == "ANTHROPIC_API_KEY"
    
    def test_openai_config(self):
        """OpenAI provider is correctly configured."""
        assert PROVIDERS["openai"]["env_key"] == "OPENAI_API_KEY"
    
    def test_gemini_config(self):
        """Gemini provider is correctly configured."""
        assert PROVIDERS["gemini"]["env_key"] == "GOOGLE_API_KEY"