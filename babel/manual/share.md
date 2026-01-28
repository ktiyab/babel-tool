# babel share — Promote Local to Team Scope

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
| [SHR-01] Intent | 32-65 | purpose, scope, local to shared, P6, visibility | `offset=27 limit=43` |
| [SHR-02] Command Overview | 67-100 | syntax, event_id, parameters | `offset=62 limit=43` |
| [SHR-03] Output & Messages | 102-154 | success, already shared, not found | `offset=97 limit=62` |
| [SHR-04] Use Cases | 156-224 | examples, workflows, scenarios | `offset=151 limit=78` |
| [SHR-05] AI Operator Guide | 226-272 | triggers, context compression, when to share | `offset=221 limit=56` |
| [SHR-06] Integration | 274-338 | capture, review, sync, git, lifecycle | `offset=269 limit=74` |
| [SHR-07] Quick Reference | 340-404 | cheatsheet, one-liners | `offset=335 limit=74` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[SHR-" .babel/manual/share.md    # Find all sections
grep -n "SHR-05" manual/share.md     # Find AI Operator Guide
```

---

## [SHR-01] Intent

`babel share` promotes a **local artifact to shared (team) scope**, making it visible across sessions and to team members.

### The Problem It Solves

| Without Share | With Share |
|---------------|------------|
| Decisions stay in personal space | Decisions visible to team |
| Work lost if `.babel/local/` deleted | Work persists in git-tracked storage |
| Others repeat your experiments | Others learn from your discoveries |
| Knowledge siloed per person | Knowledge shared across team |

### Scope Difference

| Scope | Symbol | Git Status | Visibility |
|-------|--------|------------|------------|
| Local | `○` | `.gitignore` | Personal only |
| Shared | `●` | Tracked | Team visible |

### Core Principle (P6: Token Efficiency)

Share supports **reuse of important work across sessions** [TB-JA]. By promoting validated decisions to shared scope, they become available via `babel why` for all team members and future AI sessions.

### When to Share

| Trigger | Example |
|---------|---------|
| Experiment validated | Local caching approach worked in testing |
| Team decision made | After discussion, agreed on REST API |
| Architectural constraint | "No Redis in production" — team-wide |
| Convention established | "Use pytest for all testing" |

---

## [SHR-02] Command Overview

```bash
babel share <event_id>
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Required** | `event_id` | ID (or prefix) of local artifact to share |

### Event ID Resolution

The command uses **prefix matching** — you can use short IDs:

```bash
babel share GP-LF      # Matches GP-LF...
babel share GP-LFXYZ   # More specific if needed
```

### Output Indicators

| Symbol | Meaning |
|--------|---------|
| `○` | Currently local (before share) |
| `●` | Now shared (after share) |

### What Happens

1. Event found by ID prefix
2. Event promoted from local to shared scope
3. Event file moved from `.babel/local/` to `.babel/shared/`
4. Git tracking enabled (will sync with `git push`)

---

## [SHR-03] Output & Messages

### Success

```bash
babel share XY-AB
```

```
Shared: Capture: "Using Redis for caching because rate..."
  (Will sync with git push)
```

### Already Shared

```bash
babel share XY-AB
```

```
Already shared: XY-AB
```

### Event Not Found

```bash
babel share INVALID
```

```
Event not found: INVALID

Recent local events:
  [SM-SJ] Structure Proposed
  [WY-QR] Capture: "Test capture for manual..."
  [ME-QD] Capture: "Testing capture with domain..."
```

### Multiple Matches

```bash
babel share GP   # Too short
```

```
Multiple matches for 'GP':
  [GP-LF] Capture: "Using Redis for caching..."
  [GP-XY] Capture: "GraphQL decision..."

Be more specific.
```

---

## [SHR-04] Use Cases

### Use Case 1: After Review Acceptance

The most common workflow — accept a proposal, then share it:

```bash
# Step 1: Capture created the local artifact
babel capture "Using Redis for caching because rate limits" --batch
# → [XY-AB] ○ local

# Step 2: Review and accept
babel review --accept XY-AB

# Step 3: Share to team
babel share XY-AB
# → [XY-AB] ● shared

# Step 4: Connect to purpose
babel link XY-AB
```

### Use Case 2: Promote Validated Experiment

After local testing proved the approach works:

```bash
# Experiment was captured locally
babel capture "Local LRU cache with 1000 entries" --batch

# ... testing shows it works ...

# Accept and share
babel review --accept-all
babel share LR-CA
```

### Use Case 3: Skip Share — Capture Directly to Shared

For team decisions made collaboratively:

```bash
babel capture "Team agreed: Use REST over GraphQL" --share --batch
# → [XY-AB] ● shared (already in shared scope)
```

### Use Case 4: After Linking

Complete the full workflow:

```bash
# Accept → Link → Share
babel review --accept XY-AB
babel link XY-AB                # Connect to purpose
babel share XY-AB               # Make team-visible
babel sync                      # Push to remote (optional)
```

### Use Case 5: Batch Promotion

Share multiple artifacts after validation:

```bash
babel share AB-12
babel share CD-34
babel share EF-56
```

---

## [SHR-05] AI Operator Guide

### When AI Should Suggest Sharing

| Trigger | AI Action |
|---------|-----------|
| User says "team decision" | "Should we share this? `babel share <id>`" |
| Decision affects architecture | "This may need team visibility" |
| After successful testing | "Consider sharing this validated approach" |
| User reviews and accepts | "Want to share this? `babel share <id>`" |

### When NOT to Suggest Sharing

| Context | Reason |
|---------|--------|
| Exploratory work | Local experiments should stay local until validated |
| Personal preferences | User-specific settings don't need sharing |
| Work in progress | Half-finished decisions shouldn't be shared |
| Uncertain decisions | Use `--uncertain` flag, resolve before sharing |

### Context Compression Survival

After context compression, remember:

1. **Check artifact scope** via `babel history` (○ vs ●)
2. **Share is post-validation** — typically after `review --accept`
3. **Workflow order**: capture → review → link → share → sync

### AI-Safe Command

`babel share` is **non-interactive** — safe for AI operators:

```bash
babel share XY-AB    # No prompt, immediate execution
```

### Detection Patterns

When user says:

| User Statement | AI Response |
|----------------|-------------|
| "This works, let's use it" | After accepting: "Share with team? `babel share <id>`" |
| "Team should know about this" | "`babel share <id>` will make it visible" |
| "Make this the standard" | "Share as team decision: `babel share <id>`" |

---

## [SHR-06] Integration

### With capture

```bash
# Option A: Capture local, share later
babel capture "decision" --batch
# ... validate ...
babel share <id>

# Option B: Capture directly to shared
babel capture "decision" --share --batch
```

### With review

```bash
babel review --list              # See pending
babel review --accept XY-AB      # Accept
babel share XY-AB                # Then share
```

### With link

```bash
# Full workflow order
babel review --accept XY-AB
babel link XY-AB                 # Connect to purpose graph
babel share XY-AB                # Make team-visible
```

### With sync

```bash
# After sharing, sync to remote
babel share XY-AB
babel sync                       # Push shared events
```

### With git

Shared artifacts are git-tracked:

```bash
babel share XY-AB
git add .babel/shared/
git commit -m "Share caching decision"
git push
```

### Lifecycle

```
capture --batch
    ↓
review --accept
    ↓
link (connect to purpose)
    ↓
share (promote to team) ←── YOU ARE HERE
    ↓
sync (push to remote)
```

---

## [SHR-07] Quick Reference

### Basic Commands

```bash
# Share artifact
babel share <id>

# Capture + share in one
babel capture "text" --share --batch

# Check if already shared
babel history -n 10    # ○ local vs ● shared
```

### Full Workflow

```bash
# Capture → Review → Link → Share → Sync
babel capture "decision" --batch
babel review --accept <id>
babel link <id>
babel share <id>
babel sync
```

### Scope Indicators

| Symbol | Meaning |
|--------|---------|
| `○` | Local (git-ignored) |
| `●` | Shared (git-tracked) |

### Error Handling

| Error | Solution |
|-------|----------|
| "Event not found" | Check ID spelling, use suggestions shown |
| "Multiple matches" | Use longer/more specific ID prefix |
| "Already shared" | No action needed — already in shared scope |

### Related Commands

| Command | Relationship |
|---------|--------------|
| `capture --share` | Skip share step |
| `review --accept` | Precedes share |
| `link` | Often done before share |
| `sync` | Push shared to remote |
| `history` | Check scope (○ vs ●) |

### Decision Tree

```
Is this a team decision?
├─ Yes → babel capture --share --batch
└─ No → Local experiment?
         ├─ Yes → capture --batch (local first)
         │        ├─ Validated? → share
         │        └─ Failed? → Leave local
         └─ No → Personal preference?
                  └─ Keep local (don't share)
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~380
Last updated: 2026-01-24
=============================================================================
-->
