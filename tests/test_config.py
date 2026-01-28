"""
Tests for Config — Coherence Evidence for centralized configuration

These tests validate:
- Config hierarchy (project > user > env > defaults)
- Provider configuration
- API key security (never in files)
- Nested LLM config structure (local/remote)

All tests use mocks. No real LLM packages required.
"""


from babel.config import (
    Config, LLMConfig, LocalLLMConfig, RemoteLLMConfig,
    ConfigManager, PROVIDERS, DEFAULT_PROVIDER,
    DEFAULT_LOCAL_PROVIDER, DEFAULT_REMOTE_PROVIDER
)


class TestLocalLLMConfig:
    """Local LLM configuration validation."""

    def test_default_provider(self):
        """Default local provider is ollama."""
        config = LocalLLMConfig()
        assert config.provider == "ollama"

    def test_default_model(self):
        """Default local model is llama3.2."""
        config = LocalLLMConfig()
        assert config.model == "llama3.2"

    def test_default_base_url(self):
        """Default base URL is localhost:11434."""
        config = LocalLLMConfig()
        assert config.base_url == "http://localhost:11434"

    def test_effective_model(self):
        """Effective model returns the model directly."""
        config = LocalLLMConfig(model="mistral")
        assert config.effective_model == "mistral"

    def test_validate_valid_config(self):
        """Validation passes for valid local config."""
        config = LocalLLMConfig(provider="ollama")
        error = config.validate()
        assert error is None

    def test_validate_remote_provider_fails(self):
        """Validation fails if provider is not local."""
        config = LocalLLMConfig(provider="claude")
        error = config.validate()
        assert error is not None
        assert "not a local provider" in error


class TestRemoteLLMConfig:
    """Remote LLM configuration validation."""

    def test_default_provider(self):
        """Default remote provider is claude."""
        config = RemoteLLMConfig()
        assert config.provider == "claude"

    def test_effective_model_uses_default(self):
        """Uses provider's default model when not specified."""
        config = RemoteLLMConfig(provider="claude", model=None)
        assert config.effective_model == PROVIDERS["claude"]["default_model"]

    def test_effective_model_uses_specified(self):
        """Uses specified model when provided."""
        config = RemoteLLMConfig(provider="claude", model="claude-opus-4-20250514")
        assert config.effective_model == "claude-opus-4-20250514"

    def test_api_key_from_environment(self, monkeypatch):
        """API key comes from environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
        config = RemoteLLMConfig(provider="claude")
        assert config.api_key == "test-key-123"

    def test_api_key_missing(self, monkeypatch):
        """API key is None when not in environment."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = RemoteLLMConfig(provider="claude")
        assert config.api_key is None

    def test_is_available_with_key(self, monkeypatch):
        """is_available True when API key present."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = RemoteLLMConfig(provider="claude")
        assert config.is_available is True

    def test_is_available_without_key(self, monkeypatch):
        """is_available False when API key missing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = RemoteLLMConfig(provider="claude")
        assert config.is_available is False

    def test_validate_unknown_provider(self):
        """Validation fails for unknown provider."""
        config = RemoteLLMConfig(provider="unknown")
        error = config.validate()
        assert error is not None
        assert "Unknown provider" in error

    def test_validate_unknown_model(self):
        """Validation fails for unknown model."""
        config = RemoteLLMConfig(provider="claude", model="claude-nonexistent")
        error = config.validate()
        assert error is not None
        assert "Unknown model" in error

    def test_validate_valid_config(self):
        """Validation passes for valid config."""
        config = RemoteLLMConfig(provider="claude", model="claude-sonnet-4-20250514")
        error = config.validate()
        assert error is None

    def test_validate_local_provider_fails(self):
        """Validation fails if provider is local."""
        config = RemoteLLMConfig(provider="ollama")
        error = config.validate()
        assert error is not None
        assert "not a remote provider" in error


class TestLLMConfig:
    """Nested LLM configuration."""

    def test_default_active(self):
        """Default active mode is auto."""
        config = LLMConfig()
        assert config.active == "auto"

    def test_has_local_config(self):
        """Has nested local config."""
        config = LLMConfig()
        assert isinstance(config.local, LocalLLMConfig)
        assert config.local.provider == "ollama"

    def test_has_remote_config(self):
        """Has nested remote config."""
        config = LLMConfig()
        assert isinstance(config.remote, RemoteLLMConfig)
        assert config.remote.provider == "claude"

    def test_get_active_config_local(self):
        """get_active_config returns local when active=local."""
        config = LLMConfig(active="local")
        active_config, is_local = config.get_active_config()
        assert is_local is True
        assert isinstance(active_config, LocalLLMConfig)

    def test_get_active_config_remote(self):
        """get_active_config returns remote when active=remote."""
        config = LLMConfig(active="remote")
        active_config, is_local = config.get_active_config()
        assert is_local is False
        assert isinstance(active_config, RemoteLLMConfig)

    def test_get_active_config_auto_prefers_remote(self, monkeypatch):
        """get_active_config prefers remote when API key available."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = LLMConfig(active="auto")
        active_config, is_local = config.get_active_config()
        assert is_local is False

    def test_get_active_config_auto_falls_back_to_local(self, monkeypatch):
        """get_active_config falls back to local when no API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        config = LLMConfig(active="auto")
        active_config, is_local = config.get_active_config()
        assert is_local is True

    def test_validate_invalid_active(self):
        """Validation fails for invalid active mode."""
        config = LLMConfig(active="invalid")
        error = config.validate()
        assert error is not None
        assert "Unknown active mode" in error

    def test_validate_propagates_local_errors(self):
        """Validation reports local config errors."""
        config = LLMConfig(local=LocalLLMConfig(provider="claude"))
        error = config.validate()
        assert error is not None
        assert "Local config" in error

    def test_validate_propagates_remote_errors(self):
        """Validation reports remote config errors."""
        config = LLMConfig(remote=RemoteLLMConfig(provider="unknown"))
        error = config.validate()
        assert error is not None
        assert "Remote config" in error


class TestConfigManager:
    """Configuration loading and saving."""

    def test_load_defaults(self, tmp_path):
        """Loads defaults when no config files exist."""
        manager = ConfigManager(tmp_path)
        config = manager.load()

        assert config.llm.active == "auto"
        assert config.llm.remote.provider == DEFAULT_REMOTE_PROVIDER
        assert config.llm.local.provider == DEFAULT_LOCAL_PROVIDER

    def test_save_and_load_project(self, tmp_path):
        """Saves and loads project config."""
        manager = ConfigManager(tmp_path)

        config = Config(llm=LLMConfig(
            active="local",
            remote=RemoteLLMConfig(provider="openai", model="gpt-5-mini")
        ))
        manager.save_project(config)

        # Reload
        manager2 = ConfigManager(tmp_path)
        loaded = manager2.load()

        assert loaded.llm.active == "local"
        assert loaded.llm.remote.provider == "openai"

    def test_project_overrides_user(self, tmp_path, monkeypatch):
        """Project config takes priority over user config."""
        # Create user config (new nested format)
        user_dir = tmp_path / "home" / ".babel"
        user_dir.mkdir(parents=True)
        user_config = user_dir / "config.yaml"
        user_config.write_text("llm:\n  active: remote\n  remote:\n    provider: gemini\n")

        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        proj_config_dir = project_dir / ".babel"
        proj_config_dir.mkdir()
        proj_config = proj_config_dir / "config.yaml"
        proj_config.write_text("llm:\n  active: local\n  remote:\n    provider: openai\n")

        # Patch user config path
        manager = ConfigManager(project_dir)
        manager.USER_CONFIG_FILE = user_config

        config = manager.load()

        # Project wins
        assert config.llm.active == "local"
        assert config.llm.remote.provider == "openai"

    def test_environment_overrides_files(self, tmp_path, monkeypatch):
        """Environment variables override config files."""
        # Create project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        proj_config_dir = project_dir / ".babel"
        proj_config_dir.mkdir()
        proj_config = proj_config_dir / "config.yaml"
        proj_config.write_text("llm:\n  active: remote\n")

        # Set environment
        monkeypatch.setenv("BABEL_LLM_ACTIVE", "local")

        manager = ConfigManager(project_dir)
        config = manager.load()

        # Environment wins
        assert config.llm.active == "local"

    def test_set_llm_active(self, tmp_path):
        """Can set llm.active value."""
        manager = ConfigManager(tmp_path)

        error = manager.set("llm.active", "local")
        assert error is None

        config = manager.load()
        assert config.llm.active == "local"

    def test_set_llm_local_model(self, tmp_path):
        """Can set llm.local.model value."""
        manager = ConfigManager(tmp_path)

        error = manager.set("llm.local.model", "mistral")
        assert error is None

        config = manager.load()
        assert config.llm.local.model == "mistral"

    def test_set_llm_remote_provider(self, tmp_path):
        """Can set llm.remote.provider value."""
        manager = ConfigManager(tmp_path)

        error = manager.set("llm.remote.provider", "openai")
        assert error is None

        config = manager.load()
        assert config.llm.remote.provider == "openai"

    def test_set_invalid_active(self, tmp_path):
        """Set returns error for invalid active mode."""
        manager = ConfigManager(tmp_path)

        error = manager.set("llm.active", "invalid")
        assert error is not None
        assert "Unknown active mode" in error

    def test_set_invalid_key_format(self, tmp_path):
        """Set returns error for invalid key format."""
        manager = ConfigManager(tmp_path)

        error = manager.set("invalid", "value")
        assert error is not None
        assert "Invalid key format" in error

    def test_get_llm_active(self, tmp_path):
        """Can get llm.active value."""
        manager = ConfigManager(tmp_path)
        manager.set("llm.active", "local")

        value = manager.get("llm.active")
        assert value == "local"

    def test_get_llm_local_model(self, tmp_path):
        """Can get llm.local.model value."""
        manager = ConfigManager(tmp_path)
        manager.set("llm.local.model", "mistral")

        value = manager.get("llm.local.model")
        assert value == "mistral"

    def test_migration_from_old_format(self, tmp_path):
        """Migrates old flat format to new nested format."""
        # Create project config in OLD format
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        proj_config_dir = project_dir / ".babel"
        proj_config_dir.mkdir()
        proj_config = proj_config_dir / "config.yaml"
        proj_config.write_text("llm:\n  provider: openai\n  model: gpt-5-mini\n  mode: local\n")

        manager = ConfigManager(project_dir)
        config = manager.load()

        # Should migrate to nested format
        assert config.llm.active == "local"
        assert config.llm.remote.provider == "openai"
        assert config.llm.remote.model == "gpt-5-mini"


class TestProviders:
    """Provider configuration."""

    def test_all_providers_have_required_fields(self):
        """All providers have required configuration."""
        for name, config in PROVIDERS.items():
            assert "env_key" in config
            assert "default_model" in config
            assert "models" in config
            # Local providers (like ollama) have empty models list
            # since models are locally installed and vary by user
            if not config.get("is_local", False):
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

    def test_ollama_config(self):
        """Ollama provider is correctly configured as local."""
        assert PROVIDERS["ollama"]["is_local"] is True
        assert PROVIDERS["ollama"]["env_key"] is None
