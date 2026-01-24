# babel deprecate — Mark Artifacts as Obsolete

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=157 limit=70
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [DEP-01] Intent | 32-76 | purpose, obsolete, P7, evolution, living memory | `offset=27 limit=54` |
| [DEP-02] Command Overview | 78-121 | syntax, superseded-by, parameters | `offset=73 limit=53` |
| [DEP-03] Output & Messages | 123-176 | success, not found, already deprecated | `offset=118 limit=63` |
| [DEP-04] Use Cases | 178-257 | examples, workflows, scenarios | `offset=173 limit=89` |
| [DEP-05] AI Operator Guide | 259-320 | triggers, when to deprecate, detection | `offset=254 limit=71` |
| [DEP-06] Integration | 322-387 | challenge, resolve, capture, lifecycle | `offset=317 limit=75` |
| [DEP-07] Quick Reference | 389-463 | cheatsheet, one-liners | `offset=384 limit=84` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[DEP-" manual/deprecate.md    # Find all sections
grep -n "DEP-05" manual/deprecate.md     # Find AI Operator Guide
```

---

## [DEP-01] Intent

`babel deprecate` marks an artifact as **no longer valid**, preserving its history while indicating it's been superseded.

### The Problem It Solves

| Without Deprecate | With Deprecate |
|-------------------|----------------|
| Old decisions clutter queries | Old decisions marked obsolete |
| Delete loses history | History preserved, context maintained |
| Evolution invisible | Clear supersession chain |
| "Why not X?" unanswered | "Why not X" documented |

### Core Principle (P7: Living Memory)

Deprecation supports the principle that **knowledge evolves rather than accumulates** [ZM-JO]:

```
WRONG:  Delete old decision
        → History lost, "why not X" unknown

RIGHT:  Deprecate old decision with reason + supersession
        → History preserved, evolution traceable
```

### Why Deprecate (Not Delete)

| Delete | Deprecate |
|--------|-----------|
| Loses history | Preserves history |
| No context | Reason recorded |
| Evolution broken | Supersession explicit |
| Learning lost | Learning preserved |

### When to Deprecate

| Trigger | Example |
|---------|---------|
| Decision superseded | New approach replaces old |
| Context changed | Original reasoning no longer applies |
| After revision challenge | `resolve --outcome revised` leads to deprecation |
| Technology migration | Moving from old stack to new |
| Scope change | Feature removed, decision irrelevant |

---

## [DEP-02] Command Overview

```bash
babel deprecate <artifact_id> "reason" [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Required** | `artifact_id` | ID (or prefix) to deprecate |
| **Required** | `reason` | Why it's obsolete |
| **Optional** | `--superseded-by` | ID of replacement artifact |

### Basic Deprecation

```bash
babel deprecate GP-LF "Replaced by local caching approach"
```

### With Supersession Link

```bash
babel deprecate GP-LF "Performance issues" --superseded-by XY-AB
```

Creates explicit link: GP-LF → superseded by → XY-AB

### Artifact ID Resolution

Uses prefix matching:

```bash
babel deprecate GP-LF      # Matches GP-LF...
babel deprecate GP-LFX     # More specific if needed
```

### What Happens

1. Artifact found by ID prefix
2. Deprecated event created
3. Reason recorded
4. Supersession link created (if --superseded-by used)
5. Artifact marked obsolete in graph

---

## [DEP-03] Output & Messages

### Success — Basic

```bash
babel deprecate GP-LF "Replaced by local caching approach"
```

```
Deprecated [GP-LF]:
  DECISION: Use Redis for caching
  Reason: Replaced by local caching approach
```

### Success — With Supersession

```bash
babel deprecate GP-LF "Performance issues" --superseded-by XY-AB
```

```
Deprecated [GP-LF]:
  DECISION: Use Redis for caching
  Reason: Performance issues
  Superseded by: [XY-AB] Use local caching
```

### Artifact Not Found

```bash
babel deprecate INVALID "reason"
```

```
Artifact not found: INVALID

Recent artifacts:
  [GP-LF] DECISION: Use Redis for caching
  [XY-AB] DECISION: Use local caching
```

### Already Deprecated

```bash
babel deprecate GP-LF "different reason"
```

```
Already deprecated: GP-LF
Deprecated on: 2026-01-24
Original reason: Performance issues
```

---

## [DEP-04] Use Cases

### Use Case 1: After Challenge Resolution

The most common workflow — after a revision challenge:

```bash
# Challenge resolved with revised outcome
babel resolve T_abc123 --outcome revised \
  --resolution "Updated approach based on testing" --force

# New decision was created: XY-AB
# Deprecate old decision
babel deprecate GP-LF "Superseded by XY-AB after revision" \
  --superseded-by XY-AB
```

### Use Case 2: Context Changed

When original reasoning no longer applies:

```bash
babel deprecate GP-LF "Project scope changed - no longer need caching"
```

### Use Case 3: Technology Migration

```bash
babel deprecate GP-LF "Migrating from Redis to PostgreSQL" \
  --superseded-by PG-CA
```

### Use Case 4: Cleanup Duplicates

```bash
babel deprecate OLD-ID "Duplicate of XY-AB" --superseded-by XY-AB
```

### Use Case 5: Purpose Evolution

When project purpose evolves:

```bash
# Old narrow purpose
babel deprecate OLD-PUR "Purpose too narrow for current scope" \
  --superseded-by NEW-PUR
```

### Use Case 6: Constraint Relaxed

```bash
babel deprecate CONSTR-1 "Constraint no longer applies - team expanded" \
  --superseded-by CONSTR-2
```

### Use Case 7: Full Revision Workflow (P4, P8)

```bash
# 1. Challenge existing artifact
babel challenge GP-LF "Performance issues in production"

# 2. Build evidence
babel evidence T_abc "Response times 500ms, target is 100ms"

# 3. Capture replacement
babel capture "Use local LRU cache for hot data" --batch
# User accepts → [XY-AB]

# 4. Resolve challenge
babel resolve T_abc --outcome revised \
  --resolution "Replaced with local caching" --force

# 5. Deprecate old (P8: evolution traceable)
babel deprecate GP-LF "Performance issues" --superseded-by XY-AB

# 6. Link new decision
babel link XY-AB
```

---

## [DEP-05] AI Operator Guide

### When AI Should Suggest Deprecation

| Trigger | AI Action |
|---------|-----------|
| After `resolve --outcome revised` | "Deprecate old decision: `babel deprecate <id> 'reason' --superseded-by <new>`" |
| User says "that's outdated" | "Mark as deprecated? `babel deprecate <id> 'reason'`" |
| Duplicate detected | "Deprecate duplicate: `babel deprecate <id> 'duplicate' --superseded-by <original>`" |
| Technology change | "Deprecate old approach: `babel deprecate <id> 'migrating to X'`" |

### When NOT to Deprecate

| Context | Use Instead |
|---------|-------------|
| Disagreement with decision | `challenge` (test the hypothesis first) |
| Uncertainty about validity | `question` (research before deprecating) |
| Minor update needed | `capture` new decision, may not need deprecation |

### Deprecate vs Challenge

| Command | When |
|---------|------|
| `challenge` | You disagree, want to test hypothesis |
| `deprecate` | Decision is confirmed obsolete |

```
WRONG:  User: "I don't think we should use Redis"
        AI: babel deprecate GP-LF "User disagrees"
        (Skipped the challenge/evidence process)

RIGHT:  User: "I don't think we should use Redis"
        AI: babel challenge GP-LF "Performance concerns"
        (Start the proper revision flow)
```

### Context Compression Survival

After compression, remember:

1. **Deprecate is post-decision** — use after revision confirmed
2. **Always include reason** — explains "why not X"
3. **Use --superseded-by** when replacement exists — P8 traceability

### AI-Safe Command

`babel deprecate` is **non-interactive** — safe for AI operators:

```bash
babel deprecate GP-LF "reason"                      # Basic
babel deprecate GP-LF "reason" --superseded-by XY   # With link
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "That decision is outdated" | "Deprecate it: `babel deprecate <id> 'reason'`" |
| "We're not doing that anymore" | Check if replacement exists, suggest deprecate |
| "Replace X with Y" | Capture Y, then deprecate X with --superseded-by |

---

## [DEP-06] Integration

### With challenge/resolve

```bash
# Full revision flow
babel challenge <id> "reason"
babel evidence <challenge> "data"
babel resolve <challenge> --outcome revised --force --resolution "..."
babel deprecate <id> "Superseded" --superseded-by <new>
```

### With capture

```bash
# Capture replacement first
babel capture "new approach" --batch
# User accepts → [XY-AB]

# Then deprecate old
babel deprecate GP-LF "Replaced" --superseded-by XY-AB
```

### With why

After deprecation, `why` queries will show:

```bash
babel why "caching"
# Shows: [GP-LF] (DEPRECATED) Use Redis for caching
#        Superseded by: [XY-AB] Use local caching
```

### With coherence

```bash
# Coherence may suggest deprecations
babel coherence
# Shows: Low alignment artifacts - consider deprecation
```

### Lifecycle Position

```
challenge → evidence → resolve --outcome revised
    ↓
capture (replacement)
    ↓
deprecate ←── YOU ARE HERE
    ↓
link (new decision to purpose)
```

### REVISE Flow (P4, P8)

```
coherence → challenge → evidence → capture replacement
    ↓
resolve --outcome revised
    ↓
deprecate --superseded-by
    ↓
link new artifacts
```

---

## [DEP-07] Quick Reference

### Basic Commands

```bash
# Basic deprecation
babel deprecate <id> "reason"

# With replacement link
babel deprecate <id> "reason" --superseded-by <new-id>
```

### Full Revision Workflow

```bash
# Challenge → Evidence → Capture → Resolve → Deprecate
babel challenge <id> "why wrong"
babel evidence <challenge> "proof"
babel capture "replacement" --batch
# Accept...
babel resolve <challenge> --outcome revised --force --resolution "..."
babel deprecate <id> "Superseded" --superseded-by <new>
babel link <new>
```

### Deprecation vs Challenge

| Action | Use Case |
|--------|----------|
| Challenge | Disagree, want to test |
| Deprecate | Confirmed obsolete |

### When to Include --superseded-by

| Situation | Include? |
|-----------|----------|
| Replacement exists | Yes |
| Just obsolete (no replacement) | No |
| Duplicate of another | Yes (point to original) |

### Related Commands

| Command | Relationship |
|---------|--------------|
| `challenge` | Precedes deprecation (tests hypothesis) |
| `resolve --outcome revised` | Triggers deprecation |
| `capture` | Creates replacement |
| `coherence` | May suggest deprecations |
| `why` | Shows deprecated artifacts as superseded |

### Error Handling

| Error | Solution |
|-------|----------|
| Not found | Check ID spelling, use suggestions |
| Already deprecated | No action needed |
| Wrong artifact | Use more specific ID prefix |

### Symbols After Deprecation

| In Output | Meaning |
|-----------|---------|
| `(DEPRECATED)` | Artifact obsolete |
| `Superseded by: [XY]` | Replacement exists |

### Deprecation Reasons

| Reason Type | Example |
|-------------|---------|
| Replaced | "Superseded by local caching approach" |
| Obsolete | "No longer relevant - scope changed" |
| Duplicate | "Duplicate of [XY-AB]" |
| Migration | "Migrating from Redis to PostgreSQL" |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~440
Last updated: 2026-01-24
=============================================================================
-->
