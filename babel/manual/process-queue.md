# babel process-queue — Process Async Captured Events

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=122 limit=55
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [PQU-01] Intent | 32-68 | purpose, async, offline, queue | `offset=27 limit=47` |
| [PQU-02] Command Overview | 70-110 | syntax, --batch, processing | `offset=65 limit=51` |
| [PQU-03] Queue Mechanics | 112-181 | how queue works, stages | `offset=107 limit=80` |
| [PQU-04] Use Cases | 183-256 | examples, workflows, offline | `offset=178 limit=84` |
| [PQU-05] AI Operator Guide | 258-327 | triggers, when to process | `offset=253 limit=80` |
| [PQU-06] Integration | 329-403 | capture-commit, async capture | `offset=324 limit=85` |
| [PQU-07] Quick Reference | 405-470 | cheatsheet | `offset=400 limit=76` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[PQU-" manual/process-queue.md    # Find all sections
grep -n "PQU-05" manual/process-queue.md     # Find AI Operator Guide
```

---

## [PQU-01] Intent

`babel process-queue` processes **async captured events** that were queued for later extraction.

### The Problem It Solves

| Without Process-Queue | With Process-Queue |
|----------------------|-------------------|
| Offline work blocks analysis | Capture now, analyze later |
| LLM unavailable = stuck | Queue for when LLM is available |
| Lose context during offline | Context preserved in queue |
| All-or-nothing capture | Graceful async workflow |

### What It Does

- Processes events captured with `--async` flag
- Extracts structured information using LLM
- Links extracted artifacts to the knowledge graph
- Enables offline-first workflows [HC3]

### Why It Exists [LW-LW]

This command exists to enable **AI assistants as first-class Babel users**:
- AI assistants cannot handle interactive prompts [ER-DG]
- EOF errors occur with interactive confirmation [XD-OQ]
- The `--batch` flag enables automated workflows [NL-VK, XY-VZ]

### Offline-First Principle [HC3]

**Core functionality works without network.**

```
OFFLINE: babel capture-commit --async  (Queues locally)
ONLINE:  babel process-queue           (Analyzes with LLM)
```

---

## [PQU-02] Command Overview

```bash
babel process-queue [--batch]
```

| Option | Purpose |
|--------|---------|
| `--batch` | Queue proposals for review instead of interactive confirm |

### Basic Processing

```bash
babel process-queue
```

Processes all queued events, extracting structured information.

### AI-Safe Processing

```bash
babel process-queue --batch
```

Uses batch mode — no interactive prompts, safe for AI operators [XR-GL].

### What Gets Processed

| Source | Queue Trigger |
|--------|---------------|
| `capture-commit --async` | Commit captured for later analysis |
| `capture --async` | Decision captured without immediate extraction |
| Offline captures | Any capture made without LLM access |

### Processing Stages

```
Queue Entry → LLM Analysis → Artifact Extraction → Graph Linking
```

---

## [PQU-03] Queue Mechanics

### How Events Enter the Queue

Events are queued when:
1. `--async` flag is used (explicit deferral)
2. LLM is unavailable (automatic fallback)
3. Offline mode is active (network unavailable)

### Queue Storage

Queued events are stored in `.babel/queue/`:
```
.babel/queue/
  pending/
    event_a1b2c3d4.json
    event_e5f6g7h8.json
  processed/
    event_i9j0k1l2.json
```

### Processing Flow

```
1. Read pending event from queue
2. Send to LLM for structured extraction
3. Create artifacts from extraction
4. Link artifacts to knowledge graph
5. Move event to processed/
6. Report results
```

### Output Example

```
Processing queue...
  ○ event_a1b2c3d4: Commit 8925a7cc
    ◌ Analyzing...● Done
    Extracted:
      [DECISION] Add caching layer for API responses
      [CONSTRAINT] Must respect rate limits
    ✓ Processed

  ○ event_e5f6g7h8: Commit f95ecc0
    ◌ Analyzing...● Done
    Nothing structured found. Raw capture saved.
    ✓ Processed

Queue complete: 2 events processed

-> Next: babel review  (Review extracted proposals)
```

### Queue States

| State | Location | Meaning |
|-------|----------|---------|
| Pending | `queue/pending/` | Awaiting processing |
| Processed | `queue/processed/` | Successfully analyzed |
| Failed | `queue/failed/` | Processing error (retry later) |

### Error Handling

If processing fails:
- Event stays in `pending/` or moves to `failed/`
- Error is logged with context
- Retry with `babel process-queue` later
- Manual intervention via `babel check --repair` if needed

---

## [PQU-04] Use Cases

### Use Case 1: Process After Offline Work

```bash
# While offline
git commit -m "Fix authentication bug"
babel capture-commit --async

git commit -m "Add rate limiting"
babel capture-commit --async

# Later, when online
babel process-queue
# Processes both commits, extracts structured decisions
```

### Use Case 2: Batch Commits at End of Day

```bash
# During the day - quick captures
babel capture-commit --async
# ... work ...
babel capture-commit --async
# ... more work ...
babel capture-commit --async

# End of day - process all
babel process-queue
babel review
```

### Use Case 3: AI Operator Workflow

```bash
# AI safely processes queue
babel process-queue --batch

# Then reviews extracted proposals
babel review --accept-all
```

### Use Case 4: Check Queue Status

```bash
# See what's pending
ls .babel/queue/pending/

# Process if items exist
babel process-queue
```

### Use Case 5: After LLM Outage

```bash
# LLM was unavailable, captures queued automatically
# Once LLM is back:
babel process-queue

# Verify processing
ls .babel/queue/processed/
```

### Use Case 6: Team Sync

```bash
# After pulling team changes
babel sync

# Process any queued events from sync
babel process-queue
```

---

## [PQU-05] AI Operator Guide

### When AI Should Process Queue

| Trigger | AI Action |
|---------|-----------|
| After offline work session | `babel process-queue --batch` |
| After `--async` captures | "Process queue: `babel process-queue --batch`" |
| After `babel sync` | Check and process queue |
| LLM back online | Process accumulated queue |

### AI-Safe Command

`babel process-queue --batch` is **non-interactive** — safe for AI operators:

```bash
babel process-queue --batch   # No prompts, safe for automation
```

**Without `--batch`:**
- May prompt for confirmations
- Can cause EOF errors in AI context [XD-OQ]

**With `--batch`:**
- All proposals queued for review
- No interactive prompts [XR-GL]
- AI can proceed safely

### Context Compression Survival

After compression, remember:

1. **Process after async** — `--async` captures need processing
2. **Use --batch for AI** — avoids interactive prompts
3. **Queue is persistent** — survives session restarts

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "Was working offline" | "Process queue: `babel process-queue --batch`" |
| "Captured commits async" | "Extract now: `babel process-queue --batch`" |
| "LLM is back" | "Process accumulated: `babel process-queue --batch`" |

### Workflow Integration

```
OFFLINE WORKFLOW:
  capture-commit --async → [queue] → process-queue --batch → review

BATCH WORKFLOW:
  multiple captures → [queue] → process-queue --batch → review --accept-all

POST-SYNC WORKFLOW:
  sync → process-queue --batch → review
```

### Error Recovery

If processing fails:
```bash
# Check what failed
ls .babel/queue/failed/

# Repair and retry
babel check --repair
babel process-queue --batch
```

---

## [PQU-06] Integration

### With capture-commit

```bash
# Capture queues for later
babel capture-commit --async

# Process extracts structured data
babel process-queue --batch

# Review accepts proposals
babel review --accept-all
```

### With sync

```bash
# After git pull
babel sync

# Process any new queued events
babel process-queue --batch
```

### With review

```bash
# Processing creates proposals
babel process-queue --batch

# Proposals need review
babel review

# After review, link artifacts
babel link <artifact_id>
```

### With check

```bash
# If queue has issues
babel check --repair

# Then retry processing
babel process-queue --batch
```

### Lifecycle Position

```
capture --async
    ↓
[QUEUE]
    ↓
process-queue ←── YOU ARE HERE
    ↓
[PROPOSALS CREATED]
    ↓
review
    ↓
link
```

### HC3 Implementation

`process-queue` implements **Offline-First Principle [HC3]**:

| Offline | Online |
|---------|--------|
| Capture with `--async` | Process with LLM |
| Queue persists locally | Extracts structured data |
| No network required | Full analysis available |

---

## [PQU-07] Quick Reference

### Commands

```bash
# Process all pending
babel process-queue

# AI-safe processing
babel process-queue --batch

# Check queue status
ls .babel/queue/pending/
ls .babel/queue/processed/
```

### Queue Locations

| Location | Purpose |
|----------|---------|
| `.babel/queue/pending/` | Events awaiting processing |
| `.babel/queue/processed/` | Successfully processed |
| `.babel/queue/failed/` | Processing errors |

### Workflow

```bash
# Async capture (offline or deferred)
babel capture-commit --async

# Process when ready
babel process-queue --batch

# Review proposals
babel review --accept-all

# Link artifacts
babel link <artifact_id>
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `capture-commit --async` | Creates queue entries |
| `capture --async` | Creates queue entries |
| `review` | Reviews processed proposals |
| `sync` | May trigger queue processing |
| `check --repair` | Fixes queue issues |

### Flags

| Flag | Purpose | AI-Safe |
|------|---------|---------|
| `--batch` | Non-interactive mode | Yes |
| (none) | May prompt for confirmation | No |

### When to Process

| Situation | Action |
|-----------|--------|
| After offline work | `process-queue --batch` |
| After `--async` captures | `process-queue --batch` |
| After `babel sync` | Check and process |
| LLM back online | `process-queue --batch` |
| End of work session | `process-queue --batch` |

### Error Handling

```bash
# Check for failures
ls .babel/queue/failed/

# Repair issues
babel check --repair

# Retry processing
babel process-queue --batch
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~420
Last updated: 2026-01-24
=============================================================================
-->
