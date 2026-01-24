# babel check — Verify Project Integrity

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=147 limit=65
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [CHK-01] Intent | 33-71 | purpose, integrity, health, verification | `offset=28 limit=48` |
| [CHK-02] Command Overview | 73-116 | syntax, --repair, parameters | `offset=68 limit=53` |
| [CHK-03] Output & Messages | 118-213 | success, issues, repair output | `offset=113 limit=105` |
| [CHK-04] What It Checks | 215-269 | events, graph, git, config | `offset=210 limit=64` |
| [CHK-05] Use Cases | 271-330 | examples, workflows, troubleshooting | `offset=266 limit=69` |
| [CHK-06] AI Operator Guide | 332-392 | triggers, when to check, diagnosis | `offset=327 limit=70` |
| [CHK-07] Integration | 394-452 | init, sync, status, lifecycle | `offset=389 limit=68` |
| [CHK-08] Quick Reference | 454-528 | cheatsheet, one-liners | `offset=449 limit=84` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[CHK-" manual/check.md    # Find all sections
grep -n "CHK-06" manual/check.md     # Find AI Operator Guide
```

---

## [CHK-01] Intent

`babel check` verifies **project integrity** and reports the health of all Babel components.

### The Problem It Solves

| Without Check | With Check |
|---------------|------------|
| Silent corruption | Issues detected and reported |
| Mysterious failures | Clear diagnostic output |
| Manual inspection | Automated verification |
| Drift undetected | Health baseline established |

### What It Verifies

| Component | Verification |
|-----------|--------------|
| **Directory** | `.babel/` exists with proper structure |
| **Events** | Shared and local event stores readable |
| **Graph** | Database integrity, node/edge counts |
| **Config** | Configuration file valid |
| **Purpose** | Project has declared purpose(s) |
| **Git** | Repository detected, local data protected |

### When to Use

| Trigger | Reason |
|---------|--------|
| After `git pull` conflicts | Verify `.babel/` integrity |
| Unusual errors | Diagnose root cause |
| After manual file edits | Confirm no corruption |
| Periodic maintenance | Health check baseline |
| New team member | Verify setup correct |

### HC1 Compliance

Check was added following **HC1 principle** [JP-MI] for faster understanding of command workflows — it provides immediate visibility into project state.

---

## [CHK-02] Command Overview

```bash
babel check [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Repair** | `--repair` | Attempt automatic repair of issues |

### Basic Check

```bash
babel check
```

Runs all integrity checks and reports results.

### Check with Repair

```bash
babel check --repair
```

Runs checks AND attempts to fix any issues found.

### What Repair Can Fix

| Issue | Repair Action |
|-------|---------------|
| Missing directories | Creates them |
| Orphaned events | Reconnects to graph |
| Index inconsistencies | Rebuilds indices |
| Config issues | Resets to defaults |

### What Repair Cannot Fix

| Issue | Manual Action Needed |
|-------|---------------------|
| Deleted events | Restore from backup/git |
| Corrupted graph | May need reinit |
| Bad event data | Manual inspection |

---

## [CHK-03] Output & Messages

### All Checks Passed

```bash
babel check
```

```
Babel Integrity Check
========================================
✓ .babel/ directory exists
✓ Shared events: 45254 events
✓ Local events: 43205 events
✓ Graph: 43462 nodes, 3419 edges
✓ Config: claude (claude-opus-4-20250514)
✓ Purpose defined: 76 purpose(s)
✓ Git repository detected
✓ Local data protected (.gitignore)
✓ Local data not tracked in git

----------------------------------------

✓ All checks passed. Project is healthy.

-> Next: babel status  (Review overall state)
```

### Issues Found

```bash
babel check
```

```
Babel Integrity Check
========================================
✓ .babel/ directory exists
✓ Shared events: 45254 events
✓ Local events: 43205 events
⚠ Graph: 3 orphaned nodes detected
✓ Config: claude (claude-opus-4-20250514)
✓ Purpose defined: 76 purpose(s)
✓ Git repository detected
✓ Local data protected (.gitignore)
✓ Local data not tracked in git

----------------------------------------

⚠ Issues found. Run: babel check --repair

-> Next: babel check --repair  (Attempt automatic repair)
```

### Repair Output

```bash
babel check --repair
```

```
Babel Integrity Check
========================================
✓ .babel/ directory exists
✓ Shared events: 45254 events
✓ Local events: 43205 events
⚠ Graph: 3 orphaned nodes detected
  → Repairing: Reconnecting orphaned nodes...
  ✓ Repaired: 3 nodes reconnected
✓ Config: claude (claude-opus-4-20250514)
...

----------------------------------------

✓ Repairs completed. Project is now healthy.

-> Next: babel status  (Review overall state)
```

### Critical Failure

```bash
babel check
```

```
Babel Integrity Check
========================================
✗ .babel/ directory missing

----------------------------------------

✗ Critical failure. Run: babel init "purpose"
```

---

## [CHK-04] What It Checks

### Directory Structure

| Check | Purpose |
|-------|---------|
| `.babel/` exists | Root directory present |
| `.babel/shared/` | Team events directory |
| `.babel/local/` | Personal events directory |
| Proper permissions | Can read/write |

### Event Stores

| Check | Purpose |
|-------|---------|
| Shared event count | Reports total shared events |
| Local event count | Reports total local events |
| Event file format | Valid YAML/JSON structure |
| Event consistency | No duplicate IDs |

### Graph Database

| Check | Purpose |
|-------|---------|
| Database opens | SQLite/graph accessible |
| Node count | Total artifacts in graph |
| Edge count | Total relationships |
| Orphaned nodes | Disconnected artifacts |
| Referential integrity | All edges point to valid nodes |

### Configuration

| Check | Purpose |
|-------|---------|
| Config file exists | `config.yaml` present |
| Valid syntax | YAML parses correctly |
| Model specified | LLM provider configured |
| Required fields | All necessary fields present |

### Git Integration

| Check | Purpose |
|-------|---------|
| Repository detected | `.git/` exists |
| `.gitignore` includes local | `.babel/local/` protected |
| Local not tracked | Personal data stays personal |

### Purpose

| Check | Purpose |
|-------|---------|
| Purpose declared | At least one purpose exists |
| Purpose count | Reports total purposes |

---

## [CHK-05] Use Cases

### Use Case 1: Quick Health Check

```bash
babel check
# Shows all check results
```

### Use Case 2: After Git Merge Conflicts

```bash
# Resolved merge conflicts in .babel/
git add .babel/
git commit -m "Resolve babel conflicts"
babel check --repair    # Verify and fix if needed
```

### Use Case 3: Troubleshooting Errors

```bash
# babel commands failing unexpectedly
babel check             # Diagnose issues
babel check --repair    # Attempt to fix
```

### Use Case 4: After Manual File Edits

```bash
# Edited .babel/ files directly (not recommended)
babel check --repair    # Verify and fix
```

### Use Case 5: New Team Member Setup

```bash
git clone <repo>
cd <repo>
babel check             # Verify setup correct
babel status            # Understand project
```

### Use Case 6: Periodic Maintenance

```bash
# Weekly health check
babel check
babel coherence         # Also check semantic alignment
```

### Use Case 7: Before Major Changes

```bash
# About to make significant changes
babel check             # Baseline health
# ... make changes ...
babel check             # Verify still healthy
```

---

## [CHK-06] AI Operator Guide

### When AI Should Run Check

| Trigger | AI Action |
|---------|-----------|
| Unusual babel errors | "Let me check integrity: `babel check`" |
| After git operations | Run check if conflicts occurred |
| User reports problems | Diagnose with check first |
| Start of session (if suspicious) | Quick health verification |

### When NOT to Check

| Context | Reason |
|---------|--------|
| Normal operation | Status is sufficient |
| Every session | Overhead not needed |
| No issues observed | Check when problems arise |

### Diagnostic Workflow

```bash
# Step 1: Diagnose
babel check

# Step 2a: If healthy
babel status    # Proceed normally

# Step 2b: If issues
babel check --repair    # Attempt fix

# Step 3: If repair fails
# Report to user, may need manual intervention
```

### Context Compression Survival

After compression, remember:

1. **Check is diagnostic** — use when problems suspected
2. **Repair is conservative** — won't delete data
3. **Status is lighter** — use for routine health

### AI-Safe Command

`babel check` is **non-interactive** — safe for AI operators:

```bash
babel check           # No prompt, immediate check
babel check --repair  # No prompt, immediate repair attempt
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "Babel isn't working" | "`babel check` to diagnose" |
| "Something's wrong with my project" | Run `babel check` first |
| "I edited the .babel folder" | "`babel check --repair` to verify" |

---

## [CHK-07] Integration

### With init

```bash
# If check shows no project
babel check
# → ✗ .babel/ directory missing
babel init "purpose"
```

### With sync

```bash
git pull
babel sync
babel check     # Verify sync didn't corrupt
```

### With status

```bash
# Status for routine health
babel status

# Check for diagnostics
babel check
```

### With coherence

```bash
# Full health check
babel check       # Structural integrity
babel coherence   # Semantic alignment
```

### Lifecycle Position

```
init (creates structure)
    ↓
check ←── YOU ARE HERE (verify integrity)
    ↓
status (project overview)
    ↓
normal operations
```

### Maintenance Flow

```
1. check     # Structural integrity
2. coherence # Semantic alignment
3. tensions  # Open conflicts
4. questions # Unresolved unknowns
```

---

## [CHK-08] Quick Reference

### Basic Commands

```bash
# Quick health check
babel check

# Check and repair
babel check --repair
```

### Diagnostic Workflow

```bash
# When things seem wrong
babel check             # Diagnose
babel check --repair    # Fix if needed
babel status            # Verify health
```

### Check vs Status

| Command | Purpose |
|---------|---------|
| `check` | Deep integrity verification |
| `status` | Quick health overview |

Use `check` for diagnostics, `status` for routine.

### Output Symbols

| Symbol | Meaning |
|--------|---------|
| `✓` | Check passed |
| `⚠` | Issue found (repairable) |
| `✗` | Critical failure |

### Related Commands

| Command | Relationship |
|---------|--------------|
| `init` | Creates what check verifies |
| `status` | Lighter health check |
| `sync` | May need check after |
| `coherence` | Semantic (vs structural) check |

### Error Handling

| Error | Solution |
|-------|----------|
| Missing `.babel/` | Run `babel init` |
| Orphaned nodes | `babel check --repair` |
| Corrupted graph | Try repair, else reinit |
| Config invalid | `babel check --repair` |

### When to Use Each

| Situation | Command |
|-----------|---------|
| Normal session start | `babel status` |
| Something seems wrong | `babel check` |
| After git conflicts | `babel check --repair` |
| Periodic maintenance | `babel check` |

### Repair Scope

| Can Repair | Cannot Repair |
|------------|---------------|
| Missing directories | Deleted events |
| Orphaned nodes | Corrupted data |
| Index issues | Lost history |
| Config defaults | Custom config |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~445
Last updated: 2026-01-24
=============================================================================
-->
