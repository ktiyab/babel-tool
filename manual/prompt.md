# babel prompt — Manage System Prompt for LLM Integration

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=142 limit=60
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [PRM-01] Intent | 30-55 | purpose, system prompt, LLM, IDE | `offset=25 limit=36` |
| [PRM-02] Command Overview | 57-97 | install, mini, auto, status | `offset=52 limit=51` |
| [PRM-03] Prompt Types | 99-137 | full, mini, auto-select | `offset=94 limit=49` |
| [PRM-04] Use Cases | 139-178 | examples, workflows | `offset=134 limit=50` |
| [PRM-05] AI Operator Guide | 180-205 | triggers, when to use | `offset=175 limit=36` |
| [PRM-06] Quick Reference | 207-260 | cheatsheet | `offset=202 limit=64` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[PRM-" manual/prompt.md
```

---

## [PRM-01] Intent

`babel prompt` manages the **system prompt** for LLM integration, installing it to IDE-specific locations.

### The Problem It Solves

| Without Prompt | With Prompt |
|----------------|-------------|
| AI doesn't know Babel | AI understands Babel commands |
| Manual workflow | Automatic babel integration |
| Generic AI behavior | Project-aware AI responses |

### What It Does

- Generates `.system_prompt.md` for your project
- Installs to IDE-specific locations (Claude, Cursor, etc.)
- Supports full or mini (lightweight) versions

### Prompt Types

| Type | Size | When |
|------|------|------|
| Full | ~large | Full Babel capabilities |
| Mini | ~small | When skills installed elsewhere |

---

## [PRM-02] Command Overview

```bash
babel prompt [options]
```

| Option | Purpose |
|--------|---------|
| `--install` | Install prompt to IDE location |
| `--mini` | Use lightweight prompt |
| `--auto` | Auto-select based on BABEL_SKILLS_INSTALLED |
| `--force` | Overwrite existing prompt |
| `--status` | Show installation status |

### View Status

```bash
babel prompt --status
```

### Install Full Prompt

```bash
babel prompt --install
```

### Install Mini Prompt

```bash
babel prompt --install --mini
```

### Auto-Select

```bash
babel prompt --install --auto
```

Uses `BABEL_SKILLS_INSTALLED` env var to choose.

---

## [PRM-03] Prompt Types

### Full Prompt

Complete Babel instructions for the AI:
- All commands documented
- Workflow guidance
- Principle explanations

```bash
babel prompt --install
```

### Mini Prompt

Lightweight version when skills are installed:
- Basic command reference
- Assumes skills provide details
- Smaller context footprint

```bash
babel prompt --install --mini
```

### Auto-Select

Let Babel choose based on environment:

```bash
export BABEL_SKILLS_INSTALLED=true
babel prompt --install --auto
# Installs mini

unset BABEL_SKILLS_INSTALLED
babel prompt --install --auto
# Installs full
```

---

## [PRM-04] Use Cases

### Use Case 1: Initial Setup

```bash
babel init "purpose"
babel prompt --install
# AI now understands Babel
```

### Use Case 2: Check Status

```bash
babel prompt --status
# Shows what's installed where
```

### Use Case 3: With Skills

```bash
babel skill export claude-code
babel prompt --install --mini
# Skills handle details, mini prompt sufficient
```

### Use Case 4: Force Update

```bash
babel prompt --install --force
# Overwrites existing prompt
```

### Use Case 5: IDE-Specific

Prompt installs to detected IDE:
- Claude Code: `.claude/`
- Cursor: `.cursor/`
- Generic: `.system_prompt.md`

---

## [PRM-05] AI Operator Guide

### When AI Should Suggest Prompt

| Trigger | AI Action |
|---------|-----------|
| After `babel init` | "Install prompt: `babel prompt --install`" |
| AI seems unaware of Babel | Check `babel prompt --status` |
| After skill export | "Use mini prompt: `babel prompt --install --mini`" |

### AI-Safe Commands

All prompt commands are **non-interactive**:

```bash
babel prompt --status     # No prompt
babel prompt --install    # No prompt
```

### Context Compression Survival

1. **Prompt teaches AI** — installs Babel knowledge
2. **Full vs Mini** — full for standalone, mini with skills
3. **IDE-aware** — installs to correct location

---

## [PRM-06] Quick Reference

### Commands

```bash
# Check status
babel prompt --status

# Install full prompt
babel prompt --install

# Install mini prompt
babel prompt --install --mini

# Auto-select
babel prompt --install --auto

# Force overwrite
babel prompt --install --force
```

### Prompt Locations

| IDE | Location |
|-----|----------|
| Claude Code | `.claude/` |
| Cursor | `.cursor/` |
| Generic | `.system_prompt.md` |

### Full vs Mini

| Type | Use When |
|------|----------|
| Full | Standalone Babel usage |
| Mini | Skills installed |

### Workflow

```bash
babel init "purpose"
babel prompt --install
# or with skills:
babel skill export claude-code
babel prompt --install --mini
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `skill export` | Works with mini prompt |
| `init` | Creates initial project |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~340
Last updated: 2026-01-24
=============================================================================
-->
