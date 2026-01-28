# babel capture-commit — Capture Last Git Commit

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
| [CCM-01] Intent | 32-66 | purpose, git, commit, bridge | `offset=27 limit=44` |
| [CCM-02] Command Overview | 68-112 | syntax, --async, parameters | `offset=63 limit=54` |
| [CCM-03] Output & Messages | 114-174 | success, nothing found, analysis | `offset=109 limit=70` |
| [CCM-04] Use Cases | 176-240 | examples, workflows, scenarios | `offset=171 limit=74` |
| [CCM-05] AI Operator Guide | 242-294 | triggers, when to capture, post-commit | `offset=237 limit=62` |
| [CCM-06] Integration | 296-358 | link, gaps, suggest-links, why --commit | `offset=291 limit=72` |
| [CCM-07] Quick Reference | 360-420 | cheatsheet, one-liners | `offset=355 limit=70` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[CCM-" manual/capture-commit.md    # Find all sections
grep -n "CCM-05" manual/capture-commit.md     # Find AI Operator Guide
```

---

## [CCM-01] Intent

`babel capture-commit` captures the **last git commit** as a Babel event, creating a bridge between code changes and intent.

### The Problem It Solves

| Without Capture-Commit | With Capture-Commit |
|------------------------|---------------------|
| Commits disconnected from decisions | Commits linked to intent |
| "Why was this commit made?" | Commit context captured |
| Code history only | Code + reasoning history |
| Manual commit documentation | Automatic capture |

### Git-Babel Bridge

Part of the **minimal git-babel bridge** [ZC-NN] with bidirectional links:

```
Decision ←→ Commit
```

This enables:
- `babel why --commit <sha>` — Why was this commit made?
- `babel gaps` — What decisions lack commits? What commits lack decisions?
- `babel suggest-links` — AI-assisted linking

### When to Use

| Trigger | Action |
|---------|--------|
| After meaningful commit | `babel capture-commit` |
| After implementing decision | `babel capture-commit`, then `link` |
| Important code change | Capture for future reference |

---

## [CCM-02] Command Overview

```bash
babel capture-commit [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Processing** | `--async` | Queue extraction for later (offline-friendly) |

### Basic Capture

```bash
babel capture-commit
```

Captures the most recent git commit.

### Async Capture

```bash
babel capture-commit --async
```

Queues for later processing (useful offline or when LLM unavailable).

### What It Captures

| Data | Source |
|------|--------|
| Commit SHA | Git HEAD |
| Commit message | Git log |
| Files changed | Git diff stats |
| Author/Date | Git metadata |

### Analysis

The command attempts to extract structured information:
- Decision type
- Affected areas
- Related artifacts

If no structure found, raw capture is saved.

---

## [CCM-03] Output & Messages

### Success — Structured

```bash
babel capture-commit
```

```
Captured: a1b2c3d4 -- Add caching layer for API responses
  ~5 modified, +2 added
◌ Analyzing...● Done

Extracted:
  [DECISION] Implement local caching for API
  Related: [GP-LF] Use Redis for caching

-> Next: babel link <id> --to-commit a1b2c3d4
```

### Success — Raw

```bash
babel capture-commit
```

```
Captured: 8925a7cc -- Update
  ~3 modified, -2 deleted
◌ Analyzing...● Done
Nothing structured found. That's fine--raw capture is saved.

-> Next: babel status  (Continue working)
```

### Async Queued

```bash
babel capture-commit --async
```

```
Queued: 8925a7cc -- Update
  Will be processed by: babel process-queue

-> Next: babel process-queue  (When online)
```

### No Commits

```bash
babel capture-commit
```

```
No commits found in repository.

-> Next: babel init  (Is project initialized?)
```

---

## [CCM-04] Use Cases

### Use Case 1: After Implementing Decision

```bash
# Made commit implementing a decision
git add . && git commit -m "Add caching layer"

# Capture the commit
babel capture-commit

# Link to the original decision
babel link GP-LF --to-commit HEAD
```

### Use Case 2: Quick Capture

```bash
# Just made a commit
babel capture-commit
# Captured, proceed with work
```

### Use Case 3: Offline Work

```bash
# Working offline
git commit -m "Fix authentication bug"
babel capture-commit --async

# Later, when online
babel process-queue
```

### Use Case 4: After Multiple Commits

```bash
# After several commits
babel capture-commit    # Captures most recent

# For older commits, use direct link
babel link <decision> --to-commit <sha>
```

### Use Case 5: Review Gaps

```bash
# After several commits
babel gaps --commits
# Shows: 3 commits without linked decisions

# Capture and link each
babel capture-commit
babel link <decision> --to-commit HEAD
```

### Use Case 6: With AI Suggestions

```bash
babel capture-commit
babel suggest-links --from-recent 5
# AI suggests which decisions match recent commits
```

---

## [CCM-05] AI Operator Guide

### When AI Should Suggest Capture-Commit

| Trigger | AI Action |
|---------|-----------|
| After `git commit` | "Capture this commit: `babel capture-commit`" |
| After implementing decision | "Link to decision: `babel link <id> --to-commit HEAD`" |
| User asks "why commit" | "First capture: `babel capture-commit`" |

### When NOT to Capture

| Context | Reason |
|---------|--------|
| Trivial commits | Minor typos, formatting only |
| WIP commits | Incomplete work |
| Already captured | Don't duplicate |

### Post-Implementation Workflow

```bash
# After implementing
git add . && git commit -m "message"
babel capture-commit
babel link <decision> --to-commit HEAD
```

### Context Compression Survival

After compression, remember:

1. **Capture-commit is post-commit** — run after git commit
2. **Link is separate** — capture doesn't auto-link
3. **Async for offline** — use --async when LLM unavailable

### AI-Safe Command

`babel capture-commit` is **non-interactive** — safe for AI operators:

```bash
babel capture-commit          # Immediate capture
babel capture-commit --async  # Queue for later
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "I just committed" | "`babel capture-commit` to capture intent" |
| "Done implementing" | "Commit, then `babel capture-commit`" |
| "Working offline" | "`babel capture-commit --async`" |

---

## [CCM-06] Integration

### With link

```bash
babel capture-commit
babel link GP-LF --to-commit HEAD
```

### With gaps

```bash
babel gaps --commits
# Shows commits needing decisions

babel capture-commit
# Reduces gap count
```

### With suggest-links

```bash
babel capture-commit
babel suggest-links --from-recent 5
# AI suggests links for recent commits
```

### With why --commit

```bash
babel capture-commit
# Later...
babel why --commit a1b2c3d4
# Shows captured context
```

### With process-queue

```bash
# Offline
babel capture-commit --async

# Online
babel process-queue
```

### Lifecycle Position

```
decision captured
    ↓
[IMPLEMENTATION]
    ↓
git commit
    ↓
capture-commit ←── YOU ARE HERE
    ↓
link --to-commit
    ↓
gaps (verify linked)
```

---

## [CCM-07] Quick Reference

### Basic Commands

```bash
# Capture last commit
babel capture-commit

# Queue for later (offline)
babel capture-commit --async

# Process queued
babel process-queue
```

### Full Implementation Workflow

```bash
# Implement
git add .
git commit -m "Implement caching"

# Capture and link
babel capture-commit
babel link GP-LF --to-commit HEAD
```

### Verify Coverage

```bash
# Check for gaps
babel gaps

# Show unlinked commits
babel gaps --commits

# Get AI suggestions
babel suggest-links --from-recent 5
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `link --to-commit` | Links decision to commit |
| `gaps` | Shows unlinked commits/decisions |
| `suggest-links` | AI-assisted linking |
| `why --commit` | Query commit context |
| `process-queue` | Process async captures |

### When to Capture

| Commit Type | Action |
|-------------|--------|
| Implementing decision | Capture + Link |
| Bug fix | Capture |
| Feature work | Capture + Link |
| Trivial changes | Skip |

### Capture vs Link

| Command | Purpose |
|---------|---------|
| `capture-commit` | Record commit in Babel |
| `link --to-commit` | Connect decision to commit |

Both are typically used together for full traceability.

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~405
Last updated: 2026-01-24
=============================================================================
-->
