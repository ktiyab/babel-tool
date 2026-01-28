# babel sync — Merge Team Changes After Git Pull

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=142 limit=65
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [SYN-01] Intent | 32-65 | purpose, git pull, team, velocity mismatch, P7 | `offset=27 limit=43` |
| [SYN-02] Command Overview | 67-101 | syntax, verbose, parameters | `offset=62 limit=44` |
| [SYN-03] Output & Messages | 103-170 | success, no changes, conflicts | `offset=98 limit=77` |
| [SYN-04] Use Cases | 172-239 | examples, workflows, team collaboration | `offset=167 limit=77` |
| [SYN-05] AI Operator Guide | 241-295 | triggers, session start, when to sync | `offset=236 limit=64` |
| [SYN-06] Integration | 297-362 | git, share, tensions, status | `offset=292 limit=75` |
| [SYN-07] Quick Reference | 364-434 | cheatsheet, one-liners | `offset=359 limit=80` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[SYN-" manual/sync.md    # Find all sections
grep -n "SYN-05" manual/sync.md     # Find AI Operator Guide
```

---

## [SYN-01] Intent

`babel sync` merges **team's reasoning changes after git pull**, ensuring your local Babel view integrates shared decisions from teammates.

### The Problem It Solves

| Without Sync | With Sync |
|--------------|-----------|
| Team decisions invisible after pull | All shared events integrated |
| Work on stale context | Current team knowledge available |
| Miss constraints from teammates | Constraints surface in `babel why` |
| Conflicts discovered late | Tensions detected immediately |

### Core Principle (P7: Reasoning Travels)

Sync supports the principle that **reasoning must travel with artifacts** [PA-AO]. When teammates make decisions, their reasoning (not just code) needs to reach you.

### Velocity Mismatch Problem

The core problem sync solves is **velocity mismatch** [WZ-LP]:
- Teams work at different speeds
- AI sessions restart, losing context
- Critical reasoning needs to persist across both

### When to Sync

| Trigger | Reason |
|---------|--------|
| After `git pull` | New shared events from team |
| Start of work session | Ensure current with team |
| Before major decisions | Check for relevant team context |
| After merge conflicts | Reintegrate Babel state |

---

## [SYN-02] Command Overview

```bash
babel sync [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Display** | `--verbose`, `-v` | Show details of each integrated event |

### What Happens

1. Scans `.babel/shared/` for events from git
2. Integrates new events into local view
3. Updates graph database with new nodes/edges
4. Reports count of integrated events
5. Suggests checking tensions

### Default Behavior

- Syncs to **coherence** target (maintenance cycle alignment) [OQ-RU]
- Preserves `.git/` directory during any rsync operations [DX-WE] [FN-HA]
- Non-destructive — only adds, never removes local events

### Implementation Path

```
CLI (babel/cli.py:791-793)
    ↓
HistoryCommand (babel/commands/history.py:187-222)
    ↓
EventStore (babel/core/events.py:430-456)
```

---

## [SYN-03] Output & Messages

### Success — New Events

```bash
babel sync
```

```
Syncing after git pull...
  Found: 12 new shared events
  Integrated: 12 events

-> Next: babel tensions  (Check for new conflicts)
```

### Success — No New Events

```bash
babel sync
```

```
Syncing after git pull...
  Found: 0 new shared events
  Already up to date.

-> Next: babel status  (Check project health)
```

### Verbose Output

```bash
babel sync --verbose
```

```
Syncing after git pull...
  Found: 3 new shared events

  Integrating:
    [AB-CD] DECISION: Use Redis for caching
    [EF-GH] CONSTRAINT: Max 100 connections
    [IJ-KL] PURPOSE: Optimize API response time

  Integrated: 3 events

-> Next: babel tensions  (Check for new conflicts)
```

### After Git Merge Conflicts

If `.babel/` had merge conflicts:

```bash
babel sync
```

```
Syncing after git pull...
  Warning: Some events may need manual review
  Found: 5 new shared events
  Integrated: 5 events

-> Next: babel check --repair  (Verify integrity)
```

---

## [SYN-04] Use Cases

### Use Case 1: After Git Pull (Most Common)

```bash
# Standard workflow
git pull
babel sync
babel tensions    # Check for new conflicts
```

### Use Case 2: Start of Work Session

```bash
# Full orientation after pulling latest
git pull
babel sync
babel status      # Project health
babel tensions    # Open conflicts
babel questions   # Unresolved unknowns
```

### Use Case 3: Verbose Sync for Audit

```bash
# See exactly what was integrated
babel sync --verbose
```

### Use Case 4: After Merge Conflicts

```bash
# After resolving git conflicts in .babel/
git add .babel/
git commit -m "Resolve babel conflicts"
babel sync
babel check --repair    # Verify integrity
```

### Use Case 5: Before Major Decision

```bash
# Ensure you have latest team context
git pull
babel sync
babel why "topic"       # Now includes team knowledge
babel capture "decision" --batch
```

### Use Case 6: Team Collaboration Workflow

```bash
# Morning routine
git pull
babel sync
babel status
# See: 3 new decisions from Alice, 1 constraint from Bob

# Work during day...

# Evening: share your work
babel share <id>
git add .babel/shared/
git commit -m "Share caching decision"
git push
```

---

## [SYN-05] AI Operator Guide

### When AI Should Run Sync

| Trigger | AI Action |
|---------|-----------|
| User says "git pull" | Run `babel sync` immediately after |
| Session starts | Include in ORIENT phase if team project |
| User mentions "team" or "others" | Suggest sync to get latest |
| Before querying `babel why` | Ensure context includes team knowledge |

### Session Start Protocol (Team Projects)

```bash
# ORIENT phase for team projects
babel status       # Purpose + health
babel sync         # Integrate team changes (if git pull done)
babel tensions     # Including team conflicts
babel questions    # Including team unknowns
```

### When NOT to Sync

| Context | Reason |
|---------|--------|
| Solo project | No team events to integrate |
| No git pull | Nothing new to sync |
| Offline work | Can't pull, can't sync |

### Context Compression Survival

After compression, remember:

1. **Sync is post-pull** — always after `git pull`
2. **Sync is read-only** — doesn't modify remote
3. **Check tensions after** — new conflicts may have arrived

### AI-Safe Command

`babel sync` is **non-interactive** — safe for AI operators:

```bash
babel sync           # No prompt, integrates immediately
babel sync -v        # Verbose, still non-interactive
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "I just pulled" | "`babel sync` to integrate team changes" |
| "Let me get latest" | After pull: "Run `babel sync`" |
| "What did the team decide?" | "`babel sync` first, then `babel why 'topic'`" |

---

## [SYN-06] Integration

### With git

```bash
# Standard flow
git pull
babel sync

# After push (others need to sync)
babel share <id>
git add .babel/shared/
git commit -m "Share decision"
git push
# Others: git pull && babel sync
```

### With share

```bash
# Your changes become visible to others via:
babel share <id>          # Promote to shared
git push                  # Others can pull
# Others run: babel sync  # Integrates your shared events
```

### With tensions

```bash
# Always check tensions after sync
babel sync
babel tensions            # May have new conflicts from team
```

### With status

```bash
# Full health check
babel sync
babel status --git        # Git-babel sync health
```

### With check

```bash
# After merge conflicts
babel sync
babel check               # Verify integrity
babel check --repair      # If issues found
```

### Lifecycle Position

```
git pull
    ↓
sync ←── YOU ARE HERE
    ↓
tensions (check for conflicts)
    ↓
status (overall health)
    ↓
why (query with team context)
```

---

## [SYN-07] Quick Reference

### Basic Commands

```bash
# Sync after pull
babel sync

# Verbose sync
babel sync --verbose

# Full workflow
git pull && babel sync && babel tensions
```

### Team Workflow

```bash
# Morning: get team changes
git pull
babel sync
babel status

# Evening: share your changes
babel share <id>
git add .babel/shared/
git commit -m "Share decisions"
git push
```

### When to Sync

| Trigger | Command |
|---------|---------|
| After `git pull` | `babel sync` |
| Start of collaboration | `git pull && babel sync` |
| Before major decisions | Ensure synced first |
| After merge conflicts | `babel sync && babel check` |

### Related Commands

| Command | Relationship |
|---------|--------------|
| `share` | Creates events for others to sync |
| `tensions` | Check after sync for conflicts |
| `status --git` | Git-babel sync health |
| `check` | Verify integrity after sync |
| `why` | Query now includes team context |

### Sync vs Share

| Command | Direction | Purpose |
|---------|-----------|---------|
| `share` | Local → Shared | Make your work visible |
| `sync` | Shared → Local | Get team's work |

### Error Handling

| Issue | Solution |
|-------|----------|
| Nothing to sync | Normal if already up to date |
| Integrity warning | Run `babel check --repair` |
| Merge conflicts | Resolve in git, then sync |

### Implementation Notes

- Uses rsync filters to protect `.git/` [FN-HA]
- Uses bash arrays for rsync filters [RY-LF]
- Default target is coherence [OQ-RU]

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~375
Last updated: 2026-01-24
=============================================================================
-->
