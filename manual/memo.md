# babel memo — Persistent User Preferences (PREFERENCE Flow)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --init section, read offset=110 limit=45
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [MEM-01] Intent | 34-59 | purpose, PREFERENCE flow, persistent | `offset=29 limit=35` |
| [MEM-02] Command Overview | 60-86 | syntax, parameters, all flags | `offset=55 limit=36` |
| [MEM-03] Creating Memos | 87-117 | basic memo, context | `offset=82 limit=40` |
| [MEM-04] --init | 118-166 | foundational, session start, critical | `offset=113 limit=58` |
| [MEM-05] Managing Memos | 167-222 | list, update, remove | `offset=162 limit=65` |
| [MEM-06] Candidates | 223-269 | AI detection, promote, dismiss | `offset=218 limit=56` |
| [MEM-07] Use Cases | 270-316 | examples, scenarios, workflows | `offset=265 limit=56` |
| [MEM-08] AI Operator Guide | 317-357 | detection, when to suggest | `offset=312 limit=50` |
| [MEM-09] Quick Reference | 358-412 | cheatsheet, patterns | `offset=353 limit=64` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[MEM-" manual/memo.md    # Find all sections
grep -n "MEM-04" manual/memo.md     # Find --init section
```

---

## [MEM-01] Intent

`babel memo` saves **persistent user preferences** that survive across sessions.

### The Problem It Solves

| Without Memos | With Memos |
|---------------|------------|
| User repeats preferences | Said once, remembered |
| AI forgets style rules | Preferences persist |
| Same corrections every session | Corrections saved |
| Context-less instructions | Context-aware surfacing |

### Core Principle

**Reduce repetition. Save preferences once.**

### Memo Types

| Type | When Surfaces | Use Case |
|------|---------------|----------|
| Regular | Context-aware | "Use pytest for testing" |
| Init | Every session start | "Never bypass babel to access DB" |

---

## [MEM-02] Command Overview

```bash
babel memo [content] [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Create** | `"content"` | Memo text to save |
| | `--context` | Context where it applies (repeatable) |
| | `--init` | Make foundational (surfaces in status) |
| **List** | `--list` | Show all memos |
| | `--list-init` | Show only init memos |
| | `--relevant CONTEXT` | Show memos for context |
| | `--stats` | Show memo statistics |
| **Manage** | `--update ID` | Update memo content |
| | `--remove ID` | Delete memo |
| | `--promote-init ID` | Promote regular → init |
| | `--demote-init ID` | Demote init → regular |
| **Candidates** | `--candidates` | Show AI-detected patterns |
| | `--promote ID` | Promote candidate to memo |
| | `--promote-all` | Promote all candidates |
| | `--dismiss ID` | Dismiss candidate |
| | `--suggest` | Show promotion suggestions |

---

## [MEM-03] Creating Memos

### Basic Memo

```bash
babel memo "Always use python3 not python"
```

**Output**:
```
Memo saved [m_abc123]:
  "Always use python3 not python"
```

### With Context

```bash
babel memo "Use pytest not unittest" --context testing
babel memo "Prefer async/await" --context python --context api
```

Context helps surface memos only when relevant.

### Multiple Contexts

```bash
babel memo "Always validate input" --context api --context security
```

---

## [MEM-04] --init

**Purpose**: Create foundational instruction that surfaces at every session start.

```bash
babel memo "NEVER read .babel/ files directly. Always use babel commands." --init
```

**Output**:
```
Init memo saved [m_xyz789]:
  "NEVER read .babel/ files directly..."
  ⚡ Foundational - surfaces in babel status
```

### When to Use --init

| Content Type | Use --init? |
|--------------|-------------|
| Critical safety rule | Yes |
| Project constraint | Yes |
| Workflow preference | No - use regular |
| Testing preference | No - use --context |

### Init Memos in Status

```bash
babel status
```

Shows:
```
◎ Init Instructions (read before work):
  → NEVER read .babel/ files directly...
  → Always run tests before committing...
```

### Managing Init Status

```bash
# Promote regular memo to init
babel memo --promote-init m_abc123

# Demote init memo to regular
babel memo --demote-init m_xyz789
```

---

## [MEM-05] Managing Memos

### List All Memos

```bash
babel memo --list
```

**Output**:
```
Memos (5):

  [m_abc123] "Always use python3 not python"
    Context: bash

  [m_xyz789] ⚡ "NEVER read .babel/ files directly"
    Init memo - surfaces in status

  [m_def456] "Use pytest not unittest"
    Context: testing
```

### List Init Memos Only

```bash
babel memo --list-init
```

### Update Memo

```bash
babel memo --update m_abc123 "Updated: Use python3.12 specifically"
```

### Remove Memo

```bash
babel memo --remove m_abc123
```

### Show Relevant Memos

```bash
babel memo --relevant testing
```

Shows memos with `testing` context.

### Statistics

```bash
babel memo --stats
```

---

## [MEM-06] Candidates

AI can detect repeated patterns and suggest them as memo candidates.

### View Candidates

```bash
babel memo --candidates
```

**Output**:
```
Memo candidates (3):

  [c_111] "use python3" (seen 4 times)
    Contexts: bash, scripts
    → babel memo --promote c_111

  [c_222] "prefer async" (seen 2 times)
    Contexts: api
    → babel memo --promote c_222
```

### Promote Candidate

```bash
babel memo --promote c_111
```

Converts candidate to permanent memo.

### Promote All

```bash
babel memo --promote-all
```

### Dismiss Candidate

```bash
babel memo --dismiss c_222
```

Won't be suggested again.

---

## [MEM-07] Use Cases

### Use Case 1: Repeated Correction

```bash
# User corrects you twice: "No, use python3"
babel memo "Always use python3 not python" --context bash
```

### Use Case 2: Critical Safety Rule

```bash
babel memo "NEVER bypass babel to access database directly" --init
```

### Use Case 3: Project Preference

```bash
babel memo "This project uses FastAPI not Flask" --context api
babel memo "Use TailwindCSS for styling" --context frontend
```

### Use Case 4: Testing Preferences

```bash
babel memo "Run pytest with -v flag" --context testing
babel memo "Always test edge cases" --context testing
```

### Use Case 5: Update Outdated Memo

```bash
babel memo --list
# Find outdated memo
babel memo --update m_abc123 "Updated instruction here"
```

### Use Case 6: Promote Detected Pattern

```bash
# AI detected you say "use async" often
babel memo --candidates
babel memo --promote c_111
```

---

## [MEM-08] AI Operator Guide

### Detection Triggers

| User Says | Action |
|-----------|--------|
| "I always want..." | Suggest memo |
| "Never do X" | Suggest memo (consider --init) |
| Corrects you 2+ times | Detect pattern, suggest memo |
| "Remember to always..." | Suggest memo |

### When to Suggest --init

| Pattern | Suggest --init? |
|---------|-----------------|
| Safety rule | Yes |
| Critical constraint | Yes |
| Style preference | No |
| Tool preference | No |

### Suggesting to User

```
"I notice you've corrected this twice. Save as preference?
  babel memo 'Always use python3' --context bash"
```

### Non-Interactive Commands

All memo commands are non-interactive — safe for AI:

```bash
babel memo "content"              # Add
babel memo "content" --init       # Add init
babel memo --promote c_abc123     # Promote
babel memo --list                 # List
babel memo --remove m_abc123      # Remove
```

---

## [MEM-09] Quick Reference

```bash
# Create memo
babel memo "instruction"
babel memo "instruction" --context ctx
babel memo "instruction" --init

# List memos
babel memo --list
babel memo --list-init
babel memo --relevant context
babel memo --stats

# Manage memos
babel memo --update <id> "new content"
babel memo --remove <id>
babel memo --promote-init <id>
babel memo --demote-init <id>

# Candidates
babel memo --candidates
babel memo --promote <id>
babel memo --promote-all
babel memo --dismiss <id>
```

### Memo Checklist

- [ ] Is this a critical rule? (use --init)
- [ ] Should it have context?
- [ ] Is user repeating this instruction?

### Common Patterns

```bash
# After repeated correction
babel memo "preference" --context ctx

# Critical safety rule
babel memo "safety rule" --init

# Promote detected pattern
babel memo --candidates && babel memo --promote <id>
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~425
Last updated: 2026-01-24
=============================================================================
-->
