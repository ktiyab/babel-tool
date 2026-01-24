# babel config — View and Set Configuration

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=167 limit=65
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [CFG-01] Intent | 33-69 | purpose, settings, LLM, provider | `offset=28 limit=46` |
| [CFG-02] Command Overview | 71-117 | syntax, --set, --user, parameters | `offset=66 limit=56` |
| [CFG-03] Configuration Options | 119-168 | llm, display, coherence, keys | `offset=114 limit=59` |
| [CFG-04] Output & Messages | 170-240 | view config, set success | `offset=165 limit=80` |
| [CFG-05] Use Cases | 242-301 | examples, workflows, scenarios | `offset=237 limit=69` |
| [CFG-06] AI Operator Guide | 303-354 | triggers, when to configure | `offset=298 limit=61` |
| [CFG-07] Integration | 356-400 | status, check, environment | `offset=351 limit=54` |
| [CFG-08] Quick Reference | 402-485 | cheatsheet, one-liners | `offset=397 limit=93` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[CFG-" manual/config.md    # Find all sections
grep -n "CFG-06" manual/config.md     # Find AI Operator Guide
```

---

## [CFG-01] Intent

`babel config` views and modifies **Babel configuration settings**, including LLM provider, display options, and coherence settings.

### The Problem It Solves

| Without Config | With Config |
|----------------|-------------|
| Hardcoded settings | Customizable per project |
| Same model everywhere | Different models for different projects |
| Can't check settings | Clear view of current configuration |
| Manual file editing | CLI-based configuration |

### Configuration Layers

| Layer | Location | Scope |
|-------|----------|-------|
| User | `~/.babel/config.yaml` | All projects |
| Project | `.babel/config.yaml` | Current project only |

Project config overrides user config.

### HC3: Offline-First

Configuration supports **offline-first explicit config** [OA-PH]:
- Settings work without network
- No automatic remote loading
- Explicit API key configuration

### Provider Priority

LLM provider selection follows this order [QO-AC]:
1. Remote API key (if configured)
2. Local LLM (Ollama)
3. Mock provider (testing)

---

## [CFG-02] Command Overview

```bash
babel config [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **View** | (no args) | Show current configuration |
| **Set** | `--set KEY=VALUE` | Set a config value |
| **Scope** | `--user` | Apply to user config (default: project) |

### View Configuration

```bash
babel config
```

Shows all current settings.

### Set Configuration

```bash
babel config --set KEY=VALUE
```

Sets a value in project config.

### Set User Configuration

```bash
babel config --set KEY=VALUE --user
```

Sets a value in user config (applies to all projects).

### Key Format

Use dot notation for nested keys:

```bash
babel config --set llm.provider=openai
babel config --set llm.model=gpt-4
babel config --set coherence.threshold=strict
```

---

## [CFG-03] Configuration Options

### LLM Settings

| Key | Values | Description |
|-----|--------|-------------|
| `llm.provider` | `claude`, `openai`, `ollama`, `mock` | LLM provider |
| `llm.model` | Model name | Specific model to use |
| `llm.api_key` | Key string | API key (use env var preferred) |

```bash
babel config --set llm.provider=claude
babel config --set llm.model=claude-opus-4-20250514
```

### Display Settings

| Key | Values | Description |
|-----|--------|-------------|
| `display.symbols` | `auto`, `unicode`, `ascii` | Symbol rendering |
| `display.format` | `auto`, `compact`, `detailed` | Output format |

```bash
babel config --set display.symbols=unicode
babel config --set display.format=compact
```

### Coherence Settings

| Key | Values | Description |
|-----|--------|-------------|
| `coherence.auto_check` | `true`, `false` | Auto-check on operations |
| `coherence.threshold` | `normal`, `strict`, `relaxed` | Alignment threshold |

```bash
babel config --set coherence.auto_check=true
babel config --set coherence.threshold=strict
```

### Environment Variables

Preferred for sensitive values:

| Env Variable | Purpose |
|--------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `BABEL_PROJECT_PATH` | Default project path |

---

## [CFG-04] Output & Messages

### View Configuration

```bash
babel config
```

```
Configuration:

LLM:
  Provider: claude
  Model: claude-opus-4-20250514
  API Key: ✓ Set

Display:
  Symbols: auto
  Format: auto

Coherence:
  Auto-check: True
  Threshold: normal

Config files:
  User: /root/.babel/config.yaml
  Project: /mnt/c/Users/.../tower/.babel/config.yaml

-> Next: babel status  (Verify configuration)
```

### Set Success

```bash
babel config --set llm.provider=openai
```

```
Set llm.provider = openai (project config)

-> Next: babel config  (Verify change)
```

### Set User Config

```bash
babel config --set display.symbols=unicode --user
```

```
Set display.symbols = unicode (user config)

-> Next: babel config  (Verify change)
```

### Invalid Key

```bash
babel config --set invalid.key=value
```

```
Unknown config key: invalid.key

Valid keys:
  llm.provider, llm.model, llm.api_key
  display.symbols, display.format
  coherence.auto_check, coherence.threshold
```

---

## [CFG-05] Use Cases

### Use Case 1: View Current Settings

```bash
babel config
```

### Use Case 2: Change LLM Provider

```bash
babel config --set llm.provider=openai
babel config --set llm.model=gpt-4
```

### Use Case 3: Configure Local LLM

```bash
babel config --set llm.provider=ollama
# Requires Ollama running locally
```

### Use Case 4: Set User Defaults

```bash
babel config --set display.symbols=unicode --user
babel config --set display.format=compact --user
```

### Use Case 5: Strict Coherence

```bash
babel config --set coherence.threshold=strict
babel config --set coherence.auto_check=true
```

### Use Case 6: Project-Specific Model

```bash
# For a project needing specific model
cd my-project
babel config --set llm.model=claude-opus-4-20250514
```

### Use Case 7: Testing Configuration

```bash
# Use mock provider for tests
babel config --set llm.provider=mock
```

### Use Case 8: Verify After Change

```bash
babel config --set llm.provider=claude
babel config    # Verify change
babel status    # Verify working
```

---

## [CFG-06] AI Operator Guide

### When AI Should Check Config

| Trigger | AI Action |
|---------|-----------|
| LLM errors | `babel config` to verify settings |
| User asks about settings | `babel config` to show current |
| Before changing provider | Show current, then set |

### When NOT to Change Config

| Context | Reason |
|---------|--------|
| Without user request | Config changes are user decisions |
| API keys | Never set keys via CLI (use env vars) |
| Unknown project | Don't assume settings |

### Config vs Status

```bash
babel config   # Detailed configuration view
babel status   # Quick health check (includes config summary)
```

### Context Compression Survival

After compression, remember:

1. **Config is settings** — not project state
2. **Two layers** — user (global) and project (local)
3. **Provider priority** — remote > local > mock

### AI-Safe Command

`babel config` is **non-interactive** — safe for AI operators:

```bash
babel config                          # View (safe)
babel config --set key=value          # Set (safe)
babel config --set key=value --user   # User scope (safe)
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "What's my config?" | `babel config` |
| "Change to OpenAI" | `babel config --set llm.provider=openai` |
| "Use strict coherence" | `babel config --set coherence.threshold=strict` |

---

## [CFG-07] Integration

### With status

```bash
babel config   # Detailed settings
babel status   # Includes config summary in health check
```

### With check

```bash
babel check    # Verifies config file exists and is valid
babel config   # View/modify settings
```

### With environment

```bash
# Set API key via environment (recommended)
export ANTHROPIC_API_KEY=sk-...

# Config will show it's set
babel config
# → API Key: ✓ Set
```

### Lifecycle Position

```
init (creates config)
    ↓
config ←── YOU ARE HERE (view/modify)
    ↓
status (includes config in health)
```

### Config Files

```
~/.babel/config.yaml          # User config (all projects)
.babel/config.yaml            # Project config (this project)
```

---

## [CFG-08] Quick Reference

### Basic Commands

```bash
# View configuration
babel config

# Set project config
babel config --set KEY=VALUE

# Set user config
babel config --set KEY=VALUE --user
```

### Common Settings

```bash
# LLM provider
babel config --set llm.provider=claude
babel config --set llm.provider=openai
babel config --set llm.provider=ollama

# Model
babel config --set llm.model=claude-opus-4-20250514
babel config --set llm.model=gpt-4

# Display
babel config --set display.symbols=unicode
babel config --set display.format=compact

# Coherence
babel config --set coherence.threshold=strict
babel config --set coherence.auto_check=true
```

### Config Layers

| Layer | Flag | Scope |
|-------|------|-------|
| Project | (default) | Current project |
| User | `--user` | All projects |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `BABEL_PROJECT_PATH` | Default project |

### Provider Priority

```
1. Remote API (if key set)
2. Local LLM (Ollama)
3. Mock (testing)
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `status` | Shows config in health check |
| `check` | Verifies config file |
| `init` | Creates initial config |

### Config Key Reference

| Key | Type | Values |
|-----|------|--------|
| `llm.provider` | string | claude, openai, ollama, mock |
| `llm.model` | string | Model name |
| `display.symbols` | string | auto, unicode, ascii |
| `display.format` | string | auto, compact, detailed |
| `coherence.threshold` | string | normal, strict, relaxed |
| `coherence.auto_check` | bool | true, false |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~485
Last updated: 2026-01-24
=============================================================================
-->
