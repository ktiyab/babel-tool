# babel skill — Export and Manage Skills for AI Platforms

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=152 limit=65
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [SKL-01] Intent | 33-70 | purpose, export, platforms, AI tools | `offset=28 limit=48` |
| [SKL-02] Command Overview | 72-107 | export, sync, remove, list, status | `offset=67 limit=46` |
| [SKL-03] Subcommands | 109-222 | export, sync, remove, list, status details | `offset=104 limit=124` |
| [SKL-04] Skill Categories | 224-292 | lifecycle, knowledge, validation, maintenance | `offset=219 limit=79` |
| [SKL-05] Use Cases | 294-361 | examples, workflows | `offset=289 limit=78` |
| [SKL-06] AI Operator Guide | 363-406 | triggers, when to export | `offset=358 limit=54` |
| [SKL-07] Integration | 408-457 | prompt, mini, platforms | `offset=403 limit=60` |
| [SKL-08] Quick Reference | 459-520 | cheatsheet | `offset=454 limit=72` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[SKL-" manual/skill.md    # Find all sections
grep -n "SKL-06" manual/skill.md     # Find AI Operator Guide
```

---

## [SKL-01] Intent

`babel skill` manages **skill export** to AI platforms, enabling Babel workflows across different tools.

### The Problem It Solves

| Without Skill Export | With Skill Export |
|---------------------|-------------------|
| AI doesn't know Babel workflows | AI has embedded Babel knowledge |
| Manual prompt management | Automatic platform integration |
| Skills tied to one tool | Skills travel across platforms [TY-WF] |
| Repeated context loading | Progressive disclosure [BS-BF] |

### What It Does

- Exports Babel skills to platform-specific locations
- Manages skill lifecycle (export, sync, remove)
- Tracks export status and checksums
- Supports multiple platforms (Claude Code, Cursor, Codex, Generic)

### Core Philosophy [TY-WF]

**Skills should travel across tools, not just time.**

Skills are designed to:
- Map to user workflows, not implementation details [PX-EY]
- Treat protocols as cross-cutting behaviors [IX-VI]
- Enable progressive disclosure [BS-BF]

### Skill vs Prompt

| Resource | Purpose |
|----------|---------|
| `babel skill export` | Exports individual skill commands |
| `babel prompt --install` | Installs full system prompt |
| `babel prompt --mini` | Lightweight prompt (with skills) |

---

## [SKL-02] Command Overview

```bash
babel skill <subcommand> [options]
```

| Subcommand | Purpose |
|------------|---------|
| `export` | Export skills to platform |
| `sync` | Re-export to previously exported platforms |
| `remove` | Remove exported skills from platform |
| `list` | List available skills |
| `status` | Show skill export status |

### Quick Usage

```bash
babel skill list               # See available skills
babel skill status             # Check export status
babel skill export             # Export to auto-detected platform
babel skill export --target claude-code  # Export to specific platform
babel skill sync               # Re-export after changes
babel skill remove --target X  # Remove from platform
```

### Platform Targets

| Target | Description |
|--------|-------------|
| `claude-code` | Claude Code CLI |
| `cursor` | Cursor IDE |
| `codex` | OpenAI Codex |
| `generic` | Generic Markdown output |
| `all` | All active platforms |

---

## [SKL-03] Subcommands

### export

```bash
babel skill export [--target TARGET] [--force] [--all]
```

Exports skills to platform-specific locations [PC-PQ].

| Option | Purpose |
|--------|---------|
| `--target, -t` | Target platform (default: auto-detect) |
| `--force, -f` | Overwrite existing files |
| `--all` | Export to all active platforms |

**Output:**
```
Exporting skills to claude-code...
  ✓ Lifecycle skills (4)
  ✓ Knowledge skills (5)
  ✓ Validation skills (5)
  ✓ Maintenance skills (3)
  ✓ Preference skills (2)
  ✓ Analyze skills (6)
  ✓ Protocols (6)

Exported 25 skills, 6 protocols to: .claude/skills/

-> Next: babel prompt --install --mini  (Mini prompt works with skills)
```

### sync

```bash
babel skill sync [--force]
```

Re-exports skills to all previously exported platforms.

| Option | Purpose |
|--------|---------|
| `--force, -f` | Overwrite existing files |

**Output:**
```
Syncing skills to previously exported platforms...
  ✓ claude-code: 25 skills updated

-> Next: babel skill status  (Verify sync)
```

### remove

```bash
babel skill remove [--target TARGET] [--force] [--all]
```

Removes exported skills from platform.

| Option | Purpose |
|--------|---------|
| `--target, -t` | Target platform |
| `--force, -f` | Required for --all |
| `--all` | Remove from all exported platforms |

**Output:**
```
Removing skills from claude-code...
  ✓ Removed 25 skills, 6 protocols

-> Next: babel skill status  (Verify removal)
```

### list

```bash
babel skill list [category]
```

Lists available skills organized by category.

**Categories:**
- Lifecycle (continue, orient, start-new, verify)
- Knowledge (connect, recall, remember, spec, uncertain)
- Validation (challenge, revise, strengthen, tension, validate)
- Maintenance (discover, git-babel, maintain)
- Preference (init-memo, preference)
- Analyze (architecture-review, dependency-audit, expert-query, health-check, performance-review, security-audit)
- Protocols (AI-SAFE, BATCH, CODE-MOD, DUAL-DISPLAY, OUTPUT-FORMAT, VERBATIM)

### status

```bash
babel skill status
```

Shows current skill export status with checksums.

**Output:**
```
# Babel Skills Export Status

Source checksum: `9740ed81149f`

## ⚠ Never Exported
- claude-code

| Platform | Status | Skills | Protocols | Last Export |
|----------|--------|--------|-----------|-------------|
| claude-code | ⚠ never_exported | - | - | - |
```

---

## [SKL-04] Skill Categories

### Lifecycle Skills (4)

| Skill | Purpose |
|-------|---------|
| `/continue` | Resume ongoing multi-step tasks |
| `/orient` | Initialize session with project context |
| `/start-new` | Begin new task with proper context |
| `/verify` | Verify alignment after changes |

### Knowledge Skills (5)

| Skill | Purpose |
|-------|---------|
| `/connect` | Link artifacts to purpose or evolution chain |
| `/recall` | Query existing knowledge before code change |
| `/remember` | Capture decisions with reasoning |
| `/spec` | Capture implementation specification |
| `/uncertain` | Capture uncertainty explicitly |

### Validation Skills (5)

| Skill | Purpose |
|-------|---------|
| `/challenge` | Disagree with prior decision |
| `/revise` | Supersede artifact with traceable evolution |
| `/strengthen` | Validate with dual-test (consensus + evidence) |
| `/tension` | Handle auto-detected conflicts |
| `/validate` | Process pending proposals |

### Maintenance Skills (3)

| Skill | Purpose |
|-------|---------|
| `/discover` | Explore knowledge graph |
| `/git-babel` | Bridge intent to code |
| `/maintain` | Keep system healthy |

### Preference Skills (2)

| Skill | Purpose |
|-------|---------|
| `/init-memo` | Save foundational instructions |
| `/preference` | Save persistent user preferences |

### Analyze Skills (6)

| Skill | Purpose |
|-------|---------|
| `/architecture-review` | Design pattern analysis |
| `/dependency-audit` | Dependency review with upgrade priority |
| `/expert-query` | Answer technical questions with decision references |
| `/health-check` | Quick project health overview |
| `/performance-review` | Bottleneck and efficiency analysis |
| `/security-audit` | Vulnerability assessment |

### Protocols (6)

| Protocol | Purpose |
|----------|---------|
| AI-SAFE | Non-interactive command patterns |
| BATCH | Queue proposals with --batch |
| CODE-MOD | Pre-flight checklist for modifications |
| DUAL-DISPLAY | Format as "[ID] readable summary" |
| OUTPUT-FORMAT | Tables with WHY column |
| VERBATIM | Quote Babel output exactly |

---

## [SKL-05] Use Cases

### Use Case 1: Initial Platform Setup

```bash
# Export skills to detected platform
babel skill export

# Or target specific platform
babel skill export --target claude-code

# Install mini prompt (works with skills)
babel prompt --install --mini
```

### Use Case 2: Check Available Skills

```bash
babel skill list                    # All skills
babel skill list Lifecycle          # Specific category
babel skill list Analyze            # Analysis skills
```

### Use Case 3: Check Export Status

```bash
babel skill status
# Shows: which platforms exported, checksums, last export time
```

### Use Case 4: Update After Changes

```bash
# Skills were updated, re-export to all platforms
babel skill sync

# Or force overwrite
babel skill sync --force
```

### Use Case 5: Export to All Platforms

```bash
babel skill export --all
# Exports to: claude-code, cursor, codex, generic
```

### Use Case 6: Remove from Platform

```bash
# Remove from specific platform
babel skill remove --target cursor

# Remove from all (requires --force)
babel skill remove --all --force
```

### Use Case 7: Team Onboarding

```bash
# New team member setup
git clone <repo>
babel skill export
babel prompt --install --mini
# Now AI has full Babel skill integration
```

---

## [SKL-06] AI Operator Guide

### When AI Should Suggest Skill Export

| Trigger | AI Action |
|---------|-----------|
| After `babel init` | "Export skills: `babel skill export`" |
| AI seems unaware of workflows | Check `babel skill status` |
| New platform setup | "Export to platform: `babel skill export --target X`" |
| Skills seem outdated | "Sync skills: `babel skill sync`" |

### AI-Safe Commands

All skill subcommands are **non-interactive**:

```bash
babel skill list        # No prompt
babel skill status      # No prompt
babel skill export      # No prompt
babel skill sync        # No prompt
babel skill remove      # No prompt (except --all needs --force)
```

### Context Compression Survival

After compression, remember:

1. **Skills travel** — export to platform for AI integration [TY-WF]
2. **Mini prompt** — use with skills for lighter context
3. **Sync after changes** — skills can update independently

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "AI doesn't know Babel" | "Export skills: `babel skill export`" |
| "Updated skills" | "Sync to platforms: `babel skill sync`" |
| "What skills exist?" | `babel skill list` |

### Skill Loading

Skills are loaded from YAML or Markdown files via `babel/skills/__init__.py`. Each skill maps to a user workflow, not implementation details [PX-EY].

---

## [SKL-07] Integration

### With Prompt

```bash
# Full prompt (standalone, no skills needed)
babel prompt --install

# Mini prompt (with skills)
babel skill export
babel prompt --install --mini

# Skills complement mini prompt
```

### With Init

```bash
# New project setup
babel init "purpose"
babel skill export
babel prompt --install --mini
# AI now has full Babel integration
```

### With Status

```bash
babel skill status     # Export status
babel prompt --status  # Prompt installation status
# Both needed for complete AI integration picture
```

### Platform Locations

| Platform | Skill Location |
|----------|----------------|
| claude-code | `.claude/skills/` |
| cursor | `.cursor/skills/` |
| codex | `.codex/skills/` |
| generic | `.babel/skills/` |

### Checksum Tracking

Skills use checksum tracking to detect changes:
- Source checksum identifies current skill version
- Export checksum tracks what was exported
- Mismatch suggests `babel skill sync` needed

---

## [SKL-08] Quick Reference

### Commands

```bash
# List and status
babel skill list                    # All skills
babel skill list <category>         # Category skills
babel skill status                  # Export status

# Export
babel skill export                  # Auto-detect platform
babel skill export --target X       # Specific platform
babel skill export --all            # All platforms
babel skill export --force          # Overwrite existing

# Sync and remove
babel skill sync                    # Re-export to exported platforms
babel skill sync --force            # Force overwrite
babel skill remove --target X       # Remove from platform
babel skill remove --all --force    # Remove from all
```

### Skill Categories

| Category | Count | Focus |
|----------|-------|-------|
| Lifecycle | 4 | Session flow |
| Knowledge | 5 | Capture/recall |
| Validation | 5 | Challenge/validate |
| Maintenance | 3 | Health/sync |
| Preference | 2 | User settings |
| Analyze | 6 | Technical analysis |
| Protocols | 6 | Cross-cutting behaviors |

### Workflow

```bash
# Initial setup
babel skill export
babel prompt --install --mini

# After skill updates
babel skill sync

# Check status
babel skill status
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `prompt --install` | Installs system prompt |
| `prompt --mini` | Lightweight prompt (with skills) |
| `init` | Creates initial project |

### Platform Detection

Babel auto-detects platform based on:
1. Environment variables
2. Directory structure (`.claude/`, `.cursor/`, etc.)
3. Default: `generic`

### Key Concepts

| Concept | Meaning |
|---------|---------|
| Skills | Reusable AI workflow commands |
| Protocols | Cross-cutting behavior patterns |
| Export | Copy skills to platform location |
| Sync | Re-export after changes |
| Checksum | Track skill version changes |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~545
Last updated: 2026-01-24
=============================================================================
-->
