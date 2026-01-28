"""
Configuration — Centralized settings management

Config hierarchy (highest to lowest priority):
  1. Project config (.babel/config.yaml)
  2. User config (~/.babel/config.yaml)
  3. Environment variables (including .env file)
  4. Defaults

API keys are NEVER stored in config files.
They must be provided via environment variables or .env file.

.env file loading:
  - Automatic if python-dotenv is installed (pip install python-dotenv)
  - Searches: current directory, project root, user home (~/.babel/.env)
  - See .env.example for available configuration options
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .presentation.symbols import get_symbols


def _find_project_root(start_dir: Path) -> Optional[Path]:
    """
    Walk up directory tree to find project root (directory containing .babel/).

    Args:
        start_dir: Directory to start searching from

    Returns:
        Path to project root if found, None otherwise
    """
    current = start_dir.resolve()
    while current != current.parent:  # Stop at filesystem root
        if (current / ".babel").exists():
            return current
        current = current.parent
    # Check root itself
    if (current / ".babel").exists():
        return current
    return None


def _load_dotenv():
    """
    Attempt to load .env files using python-dotenv.

    Searches for .env in (order of priority, later overrides earlier):
      1. User config directory (~/.babel/.env)
      2. Project root (found by walking up from CWD to find .babel/)
      3. Current working directory (highest priority)

    Gracefully does nothing if python-dotenv is not installed.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        # python-dotenv not installed - continue without .env loading
        return

    # Search paths for .env files (later paths override earlier)
    search_paths = []

    # User config directory (lowest priority)
    user_env = Path.home() / ".babel" / ".env"
    if user_env.exists():
        search_paths.append(user_env)

    # Project root (walk up directory tree to find .babel/)
    cwd = Path.cwd()
    project_root = _find_project_root(cwd)
    if project_root:
        project_env = project_root / ".env"
        if project_env.exists():
            search_paths.append(project_env)

    # Current directory (highest priority)
    cwd_env = cwd / ".env"
    if cwd_env.exists() and cwd_env not in search_paths:
        search_paths.append(cwd_env)

    # Load .env files (later files override earlier ones)
    for env_path in search_paths:
        load_dotenv(env_path, override=True)


# Auto-load .env files at module import
_load_dotenv()


# Supported providers and their defaults
# Categories: Large/Powerful | Balanced | Lightweight/Cost-Efficient
# Local providers have env_key=None and is_local=True
PROVIDERS = {
    "claude": {
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
        "models": [
            # Large / Powerful
            "claude-opus-4-5-20251101",
            "claude-opus-4-1-20250414",
            "claude-opus-4-20250514",
            # Balanced (default)
            "claude-sonnet-4-20250514",
            # Lightweight / Cost-Efficient
            "claude-3-7-sonnet-20250219",
            "claude-3-5-haiku-20241022"
        ],
        "is_local": False
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-5-mini",
        "models": [
            # Large / Powerful
            "gpt-5.2",
            "gpt-5.2-pro",
            "gpt-5.2-chat-latest",
            # Balanced (default)
            "gpt-5-mini",
            # Lightweight / Cost-Efficient
            "gpt-5-nano"
        ],
        "is_local": False
    },
    "gemini": {
        "env_key": "GOOGLE_API_KEY",
        "default_model": "gemini-2.5-flash",
        "models": [
            # Large / Powerful
            "gemini-2.5-pro",
            "gemini-3-flash-preview",
            # Balanced (default)
            "gemini-2.5-flash",
            # Lightweight / Cost-Efficient
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash-image"
        ],
        "is_local": False
    },
    "ollama": {
        "env_key": None,  # No API key needed for local LLM
        "default_model": "llama3.2",
        "default_base_url": "http://localhost:11434",
        "models": [],  # Dynamic - any installed model works
        "is_local": True
    }
}

DEFAULT_REMOTE_PROVIDER = "claude"
DEFAULT_LOCAL_PROVIDER = "ollama"
# Backward compatibility alias
DEFAULT_PROVIDER = DEFAULT_REMOTE_PROVIDER


@dataclass
class LocalLLMConfig:
    """Local LLM configuration (e.g., Ollama)."""
    provider: str = DEFAULT_LOCAL_PROVIDER
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"

    @property
    def effective_model(self) -> str:
        """Get model (local models are user-specified, no provider default)."""
        return self.model

    @property
    def effective_base_url(self) -> str:
        """Get base URL."""
        return self.base_url

    def validate(self) -> Optional[str]:
        """Validate local config."""
        # Local providers are dynamic - just check provider is known as local
        provider_info = PROVIDERS.get(self.provider, {})
        if not provider_info.get("is_local", False):
            local_providers = [k for k, v in PROVIDERS.items() if v.get("is_local")]
            return f"Provider '{self.provider}' is not a local provider. Valid: {', '.join(local_providers)}"
        return None


@dataclass
class RemoteLLMConfig:
    """Remote LLM configuration (Claude, OpenAI, Gemini)."""
    provider: str = DEFAULT_REMOTE_PROVIDER
    model: Optional[str] = None  # None = use provider default

    @property
    def effective_model(self) -> str:
        """Get model, falling back to provider default."""
        if self.model:
            return self.model
        return PROVIDERS.get(self.provider, {}).get("default_model", "")

    @property
    def api_key_env(self) -> str:
        """Get environment variable name for API key."""
        return PROVIDERS.get(self.provider, {}).get("env_key") or ""

    @property
    def api_key(self) -> Optional[str]:
        """Get API key from environment. Never stored."""
        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env)

    @property
    def is_available(self) -> bool:
        """Check if provider is configured (has API key)."""
        return bool(self.api_key)

    def validate(self) -> Optional[str]:
        """Validate remote config."""
        provider_info = PROVIDERS.get(self.provider, {})
        if provider_info.get("is_local", False):
            remote_providers = [k for k, v in PROVIDERS.items() if not v.get("is_local")]
            return f"Provider '{self.provider}' is not a remote provider. Valid: {', '.join(remote_providers)}"

        if self.provider not in PROVIDERS:
            valid = ", ".join(PROVIDERS.keys())
            return f"Unknown provider '{self.provider}'. Valid: {valid}"

        # Validate model if specified
        if self.model:
            valid_models = PROVIDERS[self.provider].get("models", [])
            if valid_models and self.model not in valid_models:
                return f"Unknown model '{self.model}' for {self.provider}. Valid: {', '.join(valid_models)}"

        return None


@dataclass
class LLMConfig:
    """
    LLM configuration with separate local and remote configs.

    Structure:
        llm:
            active: local | remote | auto
            local:
                provider: ollama
                model: llama3.2
                base_url: http://localhost:11434
            remote:
                provider: claude
                model: claude-opus-4-5-20251101
    """
    active: str = "auto"  # "local" | "remote" | "auto"
    local: LocalLLMConfig = field(default_factory=LocalLLMConfig)
    remote: RemoteLLMConfig = field(default_factory=RemoteLLMConfig)

    def get_active_config(self) -> tuple:
        """
        Get the active configuration based on 'active' setting.

        Returns:
            Tuple of (config, is_local) where config is LocalLLMConfig or RemoteLLMConfig
        """
        if self.active == "local":
            return (self.local, True)
        elif self.active == "remote":
            return (self.remote, False)
        else:  # auto: prefer remote if available, else local
            if self.remote.is_available:
                return (self.remote, False)
            return (self.local, True)

    def validate(self) -> Optional[str]:
        """Validate config. Returns error message or None if valid."""
        # Validate active mode
        valid_modes = ("local", "remote", "auto")
        if self.active not in valid_modes:
            return f"Unknown active mode '{self.active}'. Valid: {', '.join(valid_modes)}"

        # Validate nested configs
        error = self.local.validate()
        if error:
            return f"Local config: {error}"

        error = self.remote.validate()
        if error:
            return f"Remote config: {error}"

        return None


@dataclass
class DisplayConfig:
    """Display preferences."""
    symbols: str = "auto"  # "unicode" | "ascii" | "auto"
    format: str = "auto"   # "auto" | "table" | "list" | "detail" | "summary" | "json"

    def validate(self) -> Optional[str]:
        """Validate config. Returns error message or None if valid."""
        valid_symbols = ("unicode", "ascii", "auto")
        if self.symbols not in valid_symbols:
            return f"Unknown symbols setting '{self.symbols}'. Valid: {', '.join(valid_symbols)}"

        valid_formats = ("auto", "table", "list", "detail", "summary", "json")
        if self.format not in valid_formats:
            return f"Unknown format '{self.format}'. Valid: {', '.join(valid_formats)}"
        return None


@dataclass
class CoherenceConfig:
    """Coherence checking preferences."""
    auto_check: bool = True  # Check on commits automatically
    threshold: str = "normal"  # "strict" | "normal" | "relaxed"
    
    def validate(self) -> Optional[str]:
        """Validate config. Returns error message or None if valid."""
        valid_thresholds = ("strict", "normal", "relaxed")
        if self.threshold not in valid_thresholds:
            return f"Unknown threshold '{self.threshold}'. Valid: {', '.join(valid_thresholds)}"
        return None


@dataclass 
class Config:
    """Application configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    coherence: CoherenceConfig = field(default_factory=CoherenceConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        llm_dict: Dict[str, Any] = {
            "active": self.llm.active,
            "local": {
                "provider": self.llm.local.provider,
                "model": self.llm.local.model,
                "base_url": self.llm.local.base_url
            },
            "remote": {
                "provider": self.llm.remote.provider,
            }
        }
        # Only include remote model if explicitly set
        if self.llm.remote.model:
            llm_dict["remote"]["model"] = self.llm.remote.model

        return {
            "llm": llm_dict,
            "display": {
                "symbols": self.display.symbols,
                "format": self.display.format
            },
            "coherence": {
                "auto_check": self.coherence.auto_check,
                "threshold": self.coherence.threshold
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """
        Create from dictionary.

        Handles migration from old flat format:
            Old: llm: {provider, model, base_url, mode}
            New: llm: {active, local: {...}, remote: {...}}
        """
        llm_data = data.get("llm", {})
        display_data = data.get("display", {})
        coherence_data = data.get("coherence", {})

        # Check if this is old flat format (has 'provider' at top level, no 'local'/'remote')
        is_old_format = "provider" in llm_data and "local" not in llm_data

        if is_old_format:
            # Migration: convert old flat format to nested
            old_provider = llm_data.get("provider", DEFAULT_REMOTE_PROVIDER)
            old_model = llm_data.get("model")
            old_base_url = llm_data.get("base_url")
            old_mode = llm_data.get("mode", "auto")

            # Determine if old config was local or remote
            provider_info = PROVIDERS.get(old_provider, {})
            was_local = provider_info.get("is_local", False)

            if was_local:
                # Old config was for local provider
                local_config = LocalLLMConfig(
                    provider=old_provider,
                    model=old_model or "llama3.2",
                    base_url=old_base_url or "http://localhost:11434"
                )
                remote_config = RemoteLLMConfig()  # defaults
            else:
                # Old config was for remote provider
                local_config = LocalLLMConfig()  # defaults
                remote_config = RemoteLLMConfig(
                    provider=old_provider,
                    model=old_model
                )

            llm_config = LLMConfig(
                active=old_mode,
                local=local_config,
                remote=remote_config
            )
        else:
            # New nested format
            local_data = llm_data.get("local", {})
            remote_data = llm_data.get("remote", {})

            llm_config = LLMConfig(
                active=llm_data.get("active", "auto"),
                local=LocalLLMConfig(
                    provider=local_data.get("provider", DEFAULT_LOCAL_PROVIDER),
                    model=local_data.get("model", "llama3.2"),
                    base_url=local_data.get("base_url", "http://localhost:11434")
                ),
                remote=RemoteLLMConfig(
                    provider=remote_data.get("provider", DEFAULT_REMOTE_PROVIDER),
                    model=remote_data.get("model")
                )
            )

        return cls(
            llm=llm_config,
            display=DisplayConfig(
                symbols=display_data.get("symbols", "auto"),
                format=display_data.get("format", "auto")
            ),
            coherence=CoherenceConfig(
                auto_check=coherence_data.get("auto_check", True),
                threshold=coherence_data.get("threshold", "normal")
            )
        )


class ConfigManager:
    """
    Manages configuration loading and persistence.
    
    Hierarchy:
      1. Project config (.babel/config.yaml)
      2. User config (~/.babel/config.yaml)  
      3. Defaults
    """
    
    USER_CONFIG_DIR = Path.home() / ".babel"
    USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yaml"
    PROJECT_CONFIG_DIR = ".babel"
    PROJECT_CONFIG_FILE = "config.yaml"
    
    # Legacy paths for migration
    LEGACY_USER_CONFIG_DIR = Path.home() / ".intent"
    LEGACY_PROJECT_CONFIG_DIR = ".intent"
    
    def __init__(self, project_dir: Optional[Path] = None):
        # Priority: explicit param > BABEL_PROJECT_PATH env var > CWD
        if project_dir is not None:
            self.project_dir = Path(project_dir)
        else:
            env_path = os.environ.get("BABEL_PROJECT_PATH")
            self.project_dir = Path(env_path) if env_path else Path.cwd()
        self._config: Optional[Config] = None

        # Auto-migrate from .intent to .babel
        self._migrate_if_needed()
    
    def _migrate_if_needed(self):
        """Migrate from legacy .intent directory to .babel."""
        import shutil
        
        # Migrate project config
        legacy_project = self.project_dir / self.LEGACY_PROJECT_CONFIG_DIR
        new_project = self.project_dir / self.PROJECT_CONFIG_DIR
        
        if legacy_project.exists() and not new_project.exists():
            try:
                shutil.move(str(legacy_project), str(new_project))
                print(f"Migrated {legacy_project} -> {new_project}")
            except Exception as e:
                print(f"Warning: Could not migrate {legacy_project}: {e}")
        
        # Migrate user config
        if self.LEGACY_USER_CONFIG_DIR.exists() and not self.USER_CONFIG_DIR.exists():
            try:
                shutil.move(str(self.LEGACY_USER_CONFIG_DIR), str(self.USER_CONFIG_DIR))
                print(f"Migrated {self.LEGACY_USER_CONFIG_DIR} -> {self.USER_CONFIG_DIR}")
            except Exception as e:
                print(f"Warning: Could not migrate user config: {e}")
    
    @property
    def project_config_path(self) -> Path:
        return self.project_dir / self.PROJECT_CONFIG_DIR / self.PROJECT_CONFIG_FILE
    
    @property
    def user_config_path(self) -> Path:
        return self.USER_CONFIG_FILE
    
    def load(self) -> Config:
        """Load configuration from all sources."""
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config_data: Dict[str, Any] = {}
        
        # Layer 1: User config
        if self.user_config_path.exists():
            try:
                with open(self.user_config_path) as f:
                    user_data = yaml.safe_load(f) or {}
                    config_data = self._merge(config_data, user_data)
            except Exception:
                pass  # Ignore malformed user config
        
        # Layer 2: Project config (higher priority)
        if self.project_config_path.exists():
            try:
                with open(self.project_config_path) as f:
                    project_data = yaml.safe_load(f) or {}
                    config_data = self._merge(config_data, project_data)
            except Exception:
                pass  # Ignore malformed project config
        
        # Layer 3: Environment overrides (nested structure)
        # Active mode
        if os.environ.get("BABEL_LLM_ACTIVE"):
            config_data.setdefault("llm", {})["active"] = os.environ["BABEL_LLM_ACTIVE"]

        # Local LLM config
        if os.environ.get("BABEL_LLM_LOCAL_PROVIDER"):
            config_data.setdefault("llm", {}).setdefault("local", {})["provider"] = os.environ["BABEL_LLM_LOCAL_PROVIDER"]
        if os.environ.get("BABEL_LLM_LOCAL_MODEL"):
            config_data.setdefault("llm", {}).setdefault("local", {})["model"] = os.environ["BABEL_LLM_LOCAL_MODEL"]
        if os.environ.get("BABEL_LLM_LOCAL_BASE_URL"):
            config_data.setdefault("llm", {}).setdefault("local", {})["base_url"] = os.environ["BABEL_LLM_LOCAL_BASE_URL"]

        # Remote LLM config
        if os.environ.get("BABEL_LLM_REMOTE_PROVIDER"):
            config_data.setdefault("llm", {}).setdefault("remote", {})["provider"] = os.environ["BABEL_LLM_REMOTE_PROVIDER"]
        if os.environ.get("BABEL_LLM_REMOTE_MODEL"):
            config_data.setdefault("llm", {}).setdefault("remote", {})["model"] = os.environ["BABEL_LLM_REMOTE_MODEL"]

        self._config = Config.from_dict(config_data)
        return self._config
    
    def save_project(self, config: Config):
        """Save configuration to project config file."""
        self.project_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.project_config_path, 'w') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False)
        
        self._config = config
    
    def save_user(self, config: Config):
        """Save configuration to user config file."""
        self.USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(self.user_config_path, 'w') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False)
        
        self._config = config
    
    def set(self, key: str, value: str, scope: str = "project") -> Optional[str]:
        """
        Set a configuration value.

        Args:
            key: Dot-separated key (e.g., "llm.active", "llm.local.model")
            value: Value to set
            scope: "project" or "user"

        Returns:
            Error message or None if successful
        """
        config = self.load()

        parts = key.split(".")
        if len(parts) < 2 or len(parts) > 3:
            return f"Invalid key format: {key}. Use 'section.setting' or 'llm.local.setting'"

        section = parts[0]

        if section == "llm":
            if len(parts) == 2:
                # llm.active
                setting = parts[1]
                if setting == "active":
                    config.llm.active = value
                else:
                    return f"Unknown LLM setting: {setting}. Valid: active, local.*, remote.*"
            elif len(parts) == 3:
                # llm.local.* or llm.remote.*
                subsection, setting = parts[1], parts[2]
                if subsection == "local":
                    if setting == "provider":
                        config.llm.local.provider = value
                    elif setting == "model":
                        config.llm.local.model = value
                    elif setting == "base_url":
                        config.llm.local.base_url = value
                    else:
                        return f"Unknown local LLM setting: {setting}. Valid: provider, model, base_url"
                elif subsection == "remote":
                    if setting == "provider":
                        config.llm.remote.provider = value
                    elif setting == "model":
                        config.llm.remote.model = value
                    else:
                        return f"Unknown remote LLM setting: {setting}. Valid: provider, model"
                else:
                    return f"Unknown LLM subsection: {subsection}. Valid: local, remote"
            # Validate LLM config
            error = config.llm.validate()
            if error:
                return error

        elif section == "display":
            if len(parts) != 2:
                return f"Invalid display key: {key}. Use 'display.setting'"
            setting = parts[1]
            if setting == "symbols":
                config.display.symbols = value
            elif setting == "format":
                config.display.format = value
            else:
                return f"Unknown display setting: {setting}. Valid: symbols, format"
            error = config.display.validate()
            if error:
                return error

        elif section == "coherence":
            if len(parts) != 2:
                return f"Invalid coherence key: {key}. Use 'coherence.setting'"
            setting = parts[1]
            if setting == "auto_check":
                config.coherence.auto_check = value.lower() in ('true', '1', 'yes')
            elif setting == "threshold":
                config.coherence.threshold = value
            else:
                return f"Unknown coherence setting: {setting}. Valid: auto_check, threshold"
            error = config.coherence.validate()
            if error:
                return error
        else:
            return f"Unknown section: {section}. Valid: llm, display, coherence"

        if scope == "project":
            self.save_project(config)
        else:
            self.save_user(config)

        return None
    
    def get(self, key: str) -> Optional[str]:
        """Get a configuration value."""
        config = self.load()

        parts = key.split(".")
        if len(parts) < 2 or len(parts) > 3:
            return None

        section = parts[0]

        if section == "llm":
            if len(parts) == 2:
                # llm.active
                setting = parts[1]
                if setting == "active":
                    return config.llm.active
            elif len(parts) == 3:
                # llm.local.* or llm.remote.*
                subsection, setting = parts[1], parts[2]
                if subsection == "local":
                    if setting == "provider":
                        return config.llm.local.provider
                    elif setting == "model":
                        return config.llm.local.effective_model
                    elif setting == "base_url":
                        return config.llm.local.effective_base_url
                elif subsection == "remote":
                    if setting == "provider":
                        return config.llm.remote.provider
                    elif setting == "model":
                        return config.llm.remote.effective_model

        elif section == "display":
            if len(parts) == 2:
                setting = parts[1]
                if setting == "symbols":
                    return config.display.symbols
                elif setting == "format":
                    return config.display.format

        elif section == "coherence":
            if len(parts) == 2:
                setting = parts[1]
                if setting == "auto_check":
                    return str(config.coherence.auto_check).lower()
                elif setting == "threshold":
                    return config.coherence.threshold

        return None
    
    def _merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dicts, override wins."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def display(self) -> str:
        """Format config for display."""
        config = self.load()
        symbols = get_symbols()

        # Determine which config is active
        active_config, is_local = config.llm.get_active_config()
        active_marker = lambda mode: f" {symbols.check_pass}" if config.llm.active == mode else ""

        lines = [
            "Configuration:",
            "",
            f"LLM (active: {config.llm.active}):",
            "",
            f"  Local:{active_marker('local')}",
            f"    Provider: {config.llm.local.provider}",
            f"    Model: {config.llm.local.model}",
            f"    Base URL: {config.llm.local.base_url}",
            "",
            f"  Remote:{active_marker('remote')}",
            f"    Provider: {config.llm.remote.provider}",
            f"    Model: {config.llm.remote.effective_model}",
        ]

        # Show API key status for remote
        api_key_status = f"{symbols.check_pass} Set" if config.llm.remote.api_key else f"{symbols.check_fail} Missing"
        lines.append(f"    API Key: {api_key_status}")
        if not config.llm.remote.api_key:
            lines.append(f"    (Set {config.llm.remote.api_key_env} environment variable)")

        # Show effective config when auto
        if config.llm.active == "auto":
            effective = "remote" if config.llm.remote.is_available else "local"
            lines.append(f"")
            lines.append(f"  Effective: {effective} (auto-selected)")

        lines.extend([
            "",
            "Display:",
            f"  Symbols: {config.display.symbols}",
            f"  Format: {config.display.format}",
            "",
            "Coherence:",
            f"  Auto-check: {config.coherence.auto_check}",
            f"  Threshold: {config.coherence.threshold}",
            "",
            "Config files:",
            f"  User: {self.user_config_path}",
            f"  Project: {self.project_config_path}",
        ])

        return "\n".join(lines)


# Convenience function
def get_config(project_dir: Optional[Path] = None) -> Config:
    """Load configuration for a project."""
    return ConfigManager(project_dir).load()


# =============================================================================
# Environment File Utilities
# =============================================================================

def update_env_file(
    project_dir: Path,
    variables: Dict[str, str],
    section_name: str,
    section_comment: str = ""
) -> tuple:
    """
    Update .env file with new variables, preserving existing content.

    Extracted from init_cmd._configure_parallelization() for reuse across
    commands that need to update .env (skill export, prompt install, etc.).

    Pattern:
      1. Read existing .env content
      2. Parse existing keys (handles 'export KEY=val' and 'KEY=val')
      3. Find keys not already configured
      4. Append section with header comment

    Args:
        project_dir: Project root directory containing .env
        variables: Dict of KEY=value pairs to set
        section_name: Name for the section header (e.g., "Parallelization")
        section_comment: Optional comment after section name

    Returns:
        Tuple of (variables_added: dict, message: str)
    """
    env_path = project_dir / ".env"

    # Read existing content and parse keys
    existing_content = ""
    existing_keys = set()
    if env_path.exists():
        existing_content = env_path.read_text()
        for line in existing_content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                # Handle both 'export KEY=val' and 'KEY=val'
                key_part = line.split("=")[0].replace("export ", "").strip()
                existing_keys.add(key_part)

    # Find keys not yet configured
    missing_keys = {k: v for k, v in variables.items() if k not in existing_keys}

    if not missing_keys:
        return {}, f"{section_name} already configured"

    # Build section to append
    comment_suffix = f" ({section_comment})" if section_comment else ""
    section = "\n# -----------------------------------------------------------------------------\n"
    section += f"# {section_name}{comment_suffix}\n"
    section += "# -----------------------------------------------------------------------------\n"
    for key, value in missing_keys.items():
        section += f"export {key}={value}\n"

    # Append to .env
    with open(env_path, "a") as f:
        if existing_content and not existing_content.endswith("\n"):
            f.write("\n")
        f.write(section)

    keys_list = ", ".join(f"{k}={v}" for k, v in missing_keys.items())
    return missing_keys, f"{section_name}: {keys_list}"


def get_env_variable(project_dir: Path, key: str) -> Optional[str]:
    """
    Read a specific variable from project .env file.

    Args:
        project_dir: Project root directory
        key: Variable name to read

    Returns:
        Variable value or None if not found
    """
    env_path = project_dir / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            # Handle both 'export KEY=val' and 'KEY=val'
            parts = line.split("=", 1)
            found_key = parts[0].replace("export ", "").strip()
            if found_key == key and len(parts) > 1:
                return parts[1].strip()

    return None