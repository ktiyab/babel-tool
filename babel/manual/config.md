# babel config — View and Set Configuration

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=240 limit=100
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [CFG-01] Intent | 33-85 | purpose, settings, LLM, nested, active | `offset=28 limit=62` |
| [CFG-02] Command Overview | 87-155 | syntax, --set, --user, --benchmark | `offset=82 limit=78` |
| [CFG-03] Configuration Options | 157-255 | llm.active, llm.local, llm.remote, keys | `offset=152 limit=108` |
| [CFG-04] Output & Messages | 257-330 | view config, set success, nested display | `offset=252 limit=83` |
| [CFG-05] Use Cases | 332-430 | examples, workflows, switch local/remote | `offset=327 limit=108` |
| [CFG-06] AI Operator Guide | 432-510 | triggers, when to configure, patterns | `offset=427 limit=88` |
| [CFG-07] Integration | 512-560 | status, check, environment | `offset=507 limit=58` |
| [CFG-08] Benchmark | 562-680 | --benchmark, local vs remote, quality | `offset=557 limit=128` |
| [CFG-09] Quick Reference | 682-800 | cheatsheet, one-liners, nested paths, benchmark | `offset=677 limit=128` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[CFG-" manual/config.md    # Find all sections
grep -n "CFG-06" manual/config.md     # Find AI Operator Guide
```

---

## [CFG-01] Intent

`babel config` views and modifies **Babel configuration settings**, including LLM provider, display options, and coherence settings.

### The Problem It Solves

| Without Nested Config | With Nested Config |
|-----------------------|-------------------|
| Single provider config | Local AND remote configs persist |
| Lose settings when switching | Switch with simple toggle |
| Unset env vars to use local | Both configs coexist |
| API key forces remote | Explicit choice via `llm.active` |

### Configuration Layers

| Layer | Location | Scope |
|-------|----------|-------|
| User | `~/.babel/config.yaml` | All projects |
| Project | `.babel/config.yaml` | Current project only |
| Environment | `BABEL_LLM_*` variables | Runtime override |

Priority: Environment > Project > User > Defaults

### HC3: Offline-First

Configuration supports **offline-first explicit config** [OA-PH]:
- Settings work without network
- No automatic remote loading
- Explicit API key configuration

### Nested LLM Structure [JB-KT]

LLM configuration uses **nested structure** enabling both local and remote configs to coexist:

```yaml
llm:
  active: local | remote | auto   # Toggle which to use
  local:                          # Persists independently
    provider: ollama
    model: llama3.2
    base_url: http://localhost:11434
  remote:                         # Persists independently
    provider: claude
    model: claude-opus-4-5-20251101
```

### Provider Selection Logic

| `llm.active` | Behavior |
|--------------|----------|
| `local` | Use `llm.local` config (Ollama) |
| `remote` | Use `llm.remote` config (requires API key) |
| `auto` | Remote if API key available, else local |

Default is `auto` for backward compatibility.

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
| **Benchmark** | `--benchmark` | Run LLM benchmark (local vs remote) |
| | `--local-only` | Benchmark local LLM only |
| | `--remote-only` | Benchmark remote LLM only |

### View Configuration

```bash
babel config
```

Shows all current settings including both local and remote LLM configs.

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

### Run Benchmark

```bash
babel config --benchmark
```

Compares local vs remote LLM extraction quality with calibrated test cases.

```bash
babel config --benchmark --local-only   # Test local only
babel config --benchmark --remote-only  # Test remote only
```

See [CFG-08] Benchmark for detailed output and interpretation.

### Key Format

Use dot notation for nested keys:

```bash
# Toggle active LLM
babel config --set llm.active=local

# Configure local LLM
babel config --set llm.local.model=mistral

# Configure remote LLM
babel config --set llm.remote.provider=openai

# Other settings
babel config --set coherence.threshold=strict
```

---

## [CFG-03] Configuration Options

### LLM Settings (Nested Structure)

LLM configuration uses a nested structure with separate local and remote configs:

```yaml
llm:
  active: local | remote | auto   # Which config to use
  local:                          # Local LLM settings (Ollama)
    provider: ollama
    model: llama3.2
    base_url: http://localhost:11434
  remote:                         # Remote LLM settings (Claude, OpenAI, etc.)
    provider: claude
    model: claude-opus-4-5-20251101
```

#### Toggle Active LLM

| Key | Values | Description |
|-----|--------|-------------|
| `llm.active` | `local`, `remote`, `auto` | Which LLM to use |

```bash
babel config --set llm.active=local    # Force local LLM even with API key set
babel config --set llm.active=remote   # Force remote LLM
babel config --set llm.active=auto     # Auto-select (default: remote if available)
```

#### Local LLM Settings

| Key | Values | Description |
|-----|--------|-------------|
| `llm.local.provider` | `ollama` | Local provider |
| `llm.local.model` | Model name | Local model (e.g., llama3.2, mistral, codellama) |
| `llm.local.base_url` | URL | Ollama endpoint (default: http://localhost:11434) |

```bash
babel config --set llm.local.model=mistral
babel config --set llm.local.base_url=http://localhost:11434
```

#### Remote LLM Settings

| Key | Values | Description |
|-----|--------|-------------|
| `llm.remote.provider` | `claude`, `openai`, `gemini` | Remote provider |
| `llm.remote.model` | Model name | Remote model (uses provider default if unset) |

```bash
babel config --set llm.remote.provider=openai
babel config --set llm.remote.model=gpt-4o
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

Preferred for sensitive values and runtime overrides:

| Env Variable | Purpose |
|--------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Gemini API key |
| `BABEL_LLM_ACTIVE` | Override active mode (`local`, `remote`, `auto`) |
| `BABEL_LLM_LOCAL_PROVIDER` | Override local provider |
| `BABEL_LLM_LOCAL_MODEL` | Override local model |
| `BABEL_LLM_LOCAL_BASE_URL` | Override local LLM endpoint |
| `BABEL_LLM_REMOTE_PROVIDER` | Override remote provider |
| `BABEL_LLM_REMOTE_MODEL` | Override remote model |

---

## [CFG-04] Output & Messages

### View Configuration (Nested Display)

```bash
babel config
```

```
Configuration:

LLM (active: local):

  Local: ✓
    Provider: ollama
    Model: llama3.2
    Base URL: http://localhost:11434

  Remote:
    Provider: claude
    Model: claude-opus-4-5-20251101
    API Key: ✓ Set

Display:
  Symbols: auto
  Format: auto

Coherence:
  Auto-check: True
  Threshold: normal

Config files:
  User: /root/.babel/config.yaml
  Project: /path/to/project/.babel/config.yaml

-> Next: babel status  (Verify configuration)
```

The `✓` marker shows which config is currently active.

### Set Active Mode

```bash
babel config --set llm.active=remote
```

```
Set llm.active = remote
Saved to: /path/to/project/.babel/config.yaml

-> Next: babel config  (Verify change)
```

### Set Nested Value

```bash
babel config --set llm.local.model=codellama
```

```
Set llm.local.model = codellama
Saved to: /path/to/project/.babel/config.yaml

-> Next: babel config  (Verify change)
```

### Invalid Key Error

```bash
babel config --set llm.invalid=value
```

```
Unknown LLM setting: invalid. Valid: active, local.*, remote.*

-> Next: babel config  (View valid keys)
```

### Invalid Active Mode

```bash
babel config --set llm.active=invalid
```

```
Unknown active mode 'invalid'. Valid: local, remote, auto
```

---

## [CFG-05] Use Cases

### Use Case 1: View Current Settings

```bash
babel config
```

Shows both local and remote configs, with marker on active one.

### Use Case 2: Switch to Local LLM

```bash
# Switch to local without losing remote config
babel config --set llm.active=local
```

Remote config preserved, just not used.

### Use Case 3: Switch to Remote LLM

```bash
# Switch to remote without losing local config
babel config --set llm.active=remote
```

Local config preserved, just not used.

### Use Case 4: Configure Local Ollama Model

```bash
babel config --set llm.local.model=codellama
babel config --set llm.local.base_url=http://localhost:11434
babel config --set llm.active=local
```

### Use Case 5: Configure Remote Provider

```bash
babel config --set llm.remote.provider=openai
babel config --set llm.remote.model=gpt-4o
babel config --set llm.active=remote
```

### Use Case 6: Use Auto Mode (Default)

```bash
babel config --set llm.active=auto
# → Uses remote if API key available, else local
```

### Use Case 7: Quick Toggle for Testing

```bash
# Testing with local (free, fast)
babel config --set llm.active=local
# ... test ...

# Back to remote (production quality)
babel config --set llm.active=remote
```

Both configs persist — no reconfiguration needed.

### Use Case 8: Set User Defaults

```bash
# Default local model for all projects
babel config --set llm.local.model=llama3.2 --user

# Default remote provider for all projects
babel config --set llm.remote.provider=claude --user
```

### Use Case 9: Project-Specific Override

```bash
# This project uses different models
cd my-project
babel config --set llm.local.model=codellama
babel config --set llm.remote.model=gpt-4-turbo
```

### Use Case 10: Environment Override

```bash
# Temporarily use local for this session
export BABEL_LLM_ACTIVE=local
babel status  # Uses local config
```

---

## [CFG-06] AI Operator Guide

### When AI Should Check Config

| Trigger | AI Action |
|---------|-----------|
| LLM errors | `babel config` to verify settings |
| User asks about settings | `babel config` to show current |
| Before switching LLM | Show current, explain nested structure |
| "Use local/remote" | `babel config --set llm.active=local|remote` |
| "Compare LLMs" / "Is local good enough?" | `babel config --benchmark` |
| "Test my LLM setup" | `babel config --benchmark` |

### When NOT to Change Config

| Context | Reason |
|---------|--------|
| Without user request | Config changes are user decisions |
| API keys | Never set keys via CLI (use env vars) |
| Unknown project | Don't assume settings |

### Key Concept: Nested Structure

```
llm.active     → Toggle (local/remote/auto)
llm.local.*    → Local config (persists independently)
llm.remote.*   → Remote config (persists independently)
```

Both configs **always persist**. Switching `llm.active` doesn't lose settings.

### Config vs Status

```bash
babel config   # Detailed configuration view (shows both configs)
babel status   # Quick health check (shows active config only)
```

### Context Compression Survival

After compression, remember:

1. **Nested structure** — local and remote configs coexist
2. **llm.active** — toggle between them
3. **Both persist** — switching doesn't lose settings
4. **auto mode** — remote if API key, else local

### AI-Safe Commands

`babel config` is **non-interactive** — safe for AI operators:

```bash
babel config                              # View (safe)
babel config --set llm.active=local       # Toggle (safe)
babel config --set llm.local.model=X      # Set local (safe)
babel config --set llm.remote.provider=Y  # Set remote (safe)
babel config --benchmark                  # Benchmark (safe, may take time)
babel config --benchmark --local-only     # Local only benchmark (safe)
babel config --benchmark --remote-only    # Remote only benchmark (safe)
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "What's my config?" | `babel config` |
| "Use local LLM" | `babel config --set llm.active=local` |
| "Use remote LLM" | `babel config --set llm.active=remote` |
| "Switch to Ollama" | `babel config --set llm.active=local` |
| "Change local model" | `babel config --set llm.local.model=X` |
| "Use OpenAI" | `babel config --set llm.remote.provider=openai` then `--set llm.active=remote` |

---

## [CFG-07] Integration

### With status

```bash
babel config   # Detailed settings (both configs)
babel status   # Health check (active config summary)
```

### With environment

```bash
# API keys via environment (recommended)
export ANTHROPIC_API_KEY=sk-...
export OPENAI_API_KEY=sk-...

# Runtime override of active mode
export BABEL_LLM_ACTIVE=local
babel status  # Uses local despite API key being set
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

### YAML Structure

```yaml
llm:
  active: auto
  local:
    provider: ollama
    model: llama3.2
    base_url: http://localhost:11434
  remote:
    provider: claude
    model: claude-opus-4-5-20251101
display:
  symbols: auto
  format: auto
coherence:
  auto_check: true
  threshold: normal
```

---

## [CFG-08] Benchmark

`babel config --benchmark` runs calibrated test cases to compare local vs remote LLM extraction quality.

### Why Benchmark?

| Question | Benchmark Answers |
|----------|-------------------|
| Is my local LLM good enough? | See actual extraction output side-by-side |
| What's the quality trade-off? | Compare accuracy across difficulty levels |
| What's the speed trade-off? | See timing for each test case |
| Should I use local or remote? | Evaluate based on YOUR hardware and needs |

### Test Levels

| Level | Tests | What It Measures |
|-------|-------|------------------|
| **SIMPLE** | 3 | Basic extraction: explicit statements, obvious types |
| **MEDIUM** | 3 | Real-world complexity: multiple artifacts, technical terms |
| **HIGH** | 3 | Nuanced understanding: implicit meaning, ambiguity |

### Running Benchmarks

```bash
# Full benchmark (local + remote)
babel config --benchmark

# Local only (no API costs)
babel config --benchmark --local-only

# Remote only (faster)
babel config --benchmark --remote-only
```

### Output Structure

```
══════════════════════════════════════════════════════════════════════════════
                        BABEL LLM BENCHMARK
══════════════════════════════════════════════════════════════════════════════
Local:  ✓ ollama/llama3.2
Remote: ✓ claude/claude-opus-4-5-20251101
══════════════════════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                           SIMPLE LEVEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─ S1: Explicit Decision ───────────────────────────────────────────────────┐
│ INPUT: We decided to use PostgreSQL because we need ACID transactions.   │
│ EXPECTED: Single decision with database choice and rationale             │
│ HINT: Should capture PostgreSQL choice AND the ACID rationale            │
└────────────────────────────────────────────────────────────────────────────┘

        LOCAL                                REMOTE
        ───────────────────────────────────  ───────────────────────────────────
Time:   12,340 ms                            3,892 ms
Status: ✓ Parsed                             ✓ Parsed
Found:  1 artifact(s)                        2 artifact(s)

[1] decision (conf: 0.95)                [1] decision (conf: 0.95)
      "Choose PostgreSQL for                   "Use PostgreSQL for database"
       financial data"
```

### Interpreting Results

| Indicator | Meaning |
|-----------|---------|
| `✓ Parsed` | LLM returned valid JSON |
| `✗ Parsed` | LLM failed to return valid JSON |
| `conf: 0.95` | LLM's confidence in extraction |
| Artifact count | How many items extracted from input |
| Time | Latency for that test case |

### Summary Section

```
                         LOCAL                 REMOTE
                         ────────────────────  ────────────────────
SIMPLE       (3 tests)   3/3 ✓      avg 12,001ms  3/3 ✓      avg 4,487ms
MEDIUM       (3 tests)   2/3 ✓      avg 29,664ms  3/3 ✓      avg 8,192ms
HIGH         (3 tests)   1/3 ✓      avg 19,525ms  3/3 ✓      avg 7,417ms
```

### Decision Guide

| Your Situation | Recommendation |
|----------------|----------------|
| Local passes all SIMPLE | Good for basic captures |
| Local struggles with MEDIUM | Use remote for complex decisions |
| Local fails HIGH | Use remote for meeting notes, discussions |
| Remote 3-4x faster | Consider remote for time-sensitive work |
| Privacy concerns | Use local despite lower accuracy |
| No API budget | Use local, accept limitations |

### Typical Results

| Model Type | SIMPLE | MEDIUM | HIGH | Notes |
|------------|--------|--------|------|-------|
| Small local (7B) | ✓✓✓ | ✓✓○ | ✓○○ | Good for explicit text |
| Medium local (13-30B) | ✓✓✓ | ✓✓✓ | ✓✓○ | Handles most cases |
| Large local (70B+) | ✓✓✓ | ✓✓✓ | ✓✓✓ | Near-remote quality |
| Remote (Claude/GPT) | ✓✓✓ | ✓✓✓ | ✓✓✓ | Best quality, has cost |

---

## [CFG-09] Quick Reference

### Basic Commands

```bash
# View configuration
babel config

# Set project config
babel config --set KEY=VALUE

# Set user config
babel config --set KEY=VALUE --user
```

### Toggle Active LLM

```bash
babel config --set llm.active=local    # Use local LLM
babel config --set llm.active=remote   # Use remote LLM
babel config --set llm.active=auto     # Auto-select (default)
```

### Configure Local LLM

```bash
babel config --set llm.local.provider=ollama
babel config --set llm.local.model=llama3.2
babel config --set llm.local.model=mistral
babel config --set llm.local.model=codellama
babel config --set llm.local.base_url=http://localhost:11434
```

### Configure Remote LLM

```bash
babel config --set llm.remote.provider=claude
babel config --set llm.remote.provider=openai
babel config --set llm.remote.provider=gemini
babel config --set llm.remote.model=claude-opus-4-5-20251101
babel config --set llm.remote.model=gpt-4o
```

### Display Settings

```bash
babel config --set display.symbols=unicode
babel config --set display.symbols=ascii
babel config --set display.format=compact
babel config --set display.format=detailed
```

### Coherence Settings

```bash
babel config --set coherence.threshold=strict
babel config --set coherence.threshold=normal
babel config --set coherence.threshold=relaxed
babel config --set coherence.auto_check=true
babel config --set coherence.auto_check=false
```

### Config Layers

| Layer | Flag | Scope | Priority |
|-------|------|-------|----------|
| Environment | N/A | Runtime | Highest |
| Project | (default) | Current project | High |
| User | `--user` | All projects | Low |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Gemini API key |
| `BABEL_LLM_ACTIVE` | Override active mode |
| `BABEL_LLM_LOCAL_MODEL` | Override local model |
| `BABEL_LLM_REMOTE_PROVIDER` | Override remote provider |

### Common Workflows

```bash
# Switch to local for testing
babel config --set llm.active=local

# Switch back to remote
babel config --set llm.active=remote

# Configure then switch
babel config --set llm.local.model=codellama
babel config --set llm.active=local
```

### Benchmark Commands

```bash
# Full benchmark (local + remote)
babel config --benchmark

# Local only (no API costs, offline)
babel config --benchmark --local-only

# Remote only (faster completion)
babel config --benchmark --remote-only
```

| Flag | Use Case |
|------|----------|
| `--benchmark` | Compare both LLMs side-by-side |
| `--local-only` | Test local without API costs |
| `--remote-only` | Quick remote quality check |
