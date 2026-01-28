# babel link — Connect Artifacts to Purpose (CONNECT Flow)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --to-commit section, read offset=175 limit=50
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [LNK-01] Intent | 36-66 | purpose, CONNECT flow, supports edge | `offset=31 limit=40` |
| [LNK-02] Command Overview | 67-94 | syntax, parameters, flags | `offset=62 limit=37` |
| [LNK-03] Basic Linking | 95-135 | artifact to purpose, default | `offset=90 limit=50` |
| [LNK-04] --list | 136-182 | unlinked artifacts, pagination | `offset=131 limit=56` |
| [LNK-05] --all | 183-215 | bulk linking, all unlinked | `offset=178 limit=42` |
| [LNK-06] --to-commit | 216-300 | git commit, decision bridge, **symbols, semantic bridge** | `offset=211 limit=95` |
| [LNK-07] --commits | 301-335 | list decision-commit links | `offset=296 limit=44` |
| [LNK-08] Use Cases | 336-400 | examples, scenarios, workflows | `offset=331 limit=74` |
| [LNK-09] AI Operator Guide | 401-452 | after accept, mandatory, orphans, **symbol auto-linking** | `offset=396 limit=60` |
| [LNK-10] Integration | 453-495 | review, why, gaps | `offset=448 limit=52` |
| [LNK-11] Quick Reference | 496-546 | cheatsheet, patterns | `offset=491 limit=60` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[LNK-" .babel/manual/link.md    # Find all sections
grep -n "LNK-06" .babel/manual/link.md     # Find --to-commit section
```

---

## [LNK-01] Intent

`babel link` is the **CONNECT** command — it creates edges between artifacts and purposes so they can inform `babel why` queries.

### The Problem It Solves

| Without Linking | With Linking |
|-----------------|--------------|
| Artifacts are orphans | Artifacts connected to purpose |
| `babel why` can't find them | `babel why` retrieves them |
| Knowledge graph fragmented | Knowledge graph connected |
| No traceability | Full traceability |

### Core Principle

**Linking is knowledge creation, not documentation cleanup.**

```
Artifact created → Link to purpose → Now discoverable via babel why
```

### The Supports Edge

```
[DECISION] Use Redis for caching
    │
    └── supports ──→ [PURPOSE] Improve API performance
```

---

## [LNK-02] Command Overview

```bash
babel link [artifact_id] [purpose_id] [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Position** | `artifact_id` | Artifact to link (or prefix) |
| | `purpose_id` | Target purpose (default: active) |
| **List** | `--list` | Show unlinked artifacts |
| | `--full` | Show complete content |
| | `--limit N` | Max items to show (default: 10) |
| | `--offset N` | Skip first N items |
| **Bulk** | `--all` | Link all unlinked to active purpose |
| **Git** | `--to-commit SHA` | Link decision to git commit |
| | `--commits` | List decision-commit links |

### ID Prefix Matching

You can use ID prefixes:
```bash
babel link GP-LF     # Full ID
babel link GP        # Prefix works too
```

---

## [LNK-03] Basic Linking

**Purpose**: Connect an artifact to a purpose.

### Link to Active Purpose (Default)

```bash
babel link GP-LF
```

Links artifact `GP-LF` to the currently active purpose.

### Link to Specific Purpose

```bash
babel link GP-LF PA-AO
```

Links artifact `GP-LF` to purpose `PA-AO`.

**Output**:
```
Linked [GP-LF] to purpose [PA-AO]
  DECISION: Add --list and --all options
  → Purpose: Preserve intent across sessions
```

### What Gets Linked

| Artifact Type | Can Link? |
|---------------|-----------|
| Decision | Yes |
| Constraint | Yes |
| Principle | Yes |
| Requirement | Yes |
| Proposal | No - must accept first |

**Important**: Proposals must be accepted via `babel review` before linking.

---

## [LNK-04] --list

**Purpose**: Show artifacts that aren't connected to any purpose.

```bash
babel link --list
```

**Output**:
```
Unlinked artifacts (1-10 of 2208):
(These can't inform 'babel why' queries)

[proposal] (10)
  [ZR-XT] {'source_id': 'a73fdeaba79a24e2'...
  [ZR-XT] {'source_id': '54a4316a0e3557f0'...

→ Next: babel link --list --offset 10
→ All: babel link --list --all

Link individually: babel link <id>
Link all at once:  babel link --all
```

### Pagination

```bash
# First 10
babel link --list

# Next 10
babel link --list --offset 10

# Show 20 at a time
babel link --list --limit 20
```

### Full Content

```bash
babel link --list --full
```

Shows complete artifact content instead of truncated.

---

## [LNK-05] --all

**Purpose**: Link all unlinked artifacts to active purpose in bulk.

```bash
babel link --all
```

**Output**:
```
Linking 2208 artifacts to active purpose...
✓ Linked 2208 artifacts

→ Next: babel why "topic"  (Artifacts now discoverable)
```

### When to Use --all

| Situation | Use --all? |
|-----------|------------|
| Many orphans, same purpose | Yes |
| Need selective linking | No - link individually |
| After bulk review acceptance | Yes |
| Cleanup session | Yes |

### Caution

Links everything to **active** purpose. Make sure:
1. Correct purpose is active
2. All orphans belong to that purpose

---

## [LNK-06] --to-commit

**Purpose**: Bridge decisions to their implementing git commits AND code symbols (P8: Evolution Traceable).

This command creates the **return path** in the semantic bridge:
- Links decision to commit (as before)
- **NEW**: Auto-detects and links to symbols touched by the commit

```bash
babel link GP-LF --to-commit HEAD
babel link GP-LF --to-commit c73a08f
```

**Output**:
```
✓ Linked decision to commit:

  Decision [GP-LF]:
    "Add caching to UserService"

  → Commit [c73a08f]:
    "Implement Redis caching layer"

  Relation: implements

This enables:
  babel why --commit c73a08f  (see why this commit was made)

→ Symbols touched by this commit:
  [C] src.services.user.UserService
  [M] src.services.user.UserService.get_user
  [M] src.services.user.UserService.cache_user

✓ Linked decision to 3 symbol(s)
```

### The Semantic Bridge

```
Decision (WHY)
    │
    ├── implements ──→ Commit (git state)
    │
    └── implemented_in ──→ Symbol (WHAT)
                           └── UserService.get_user
                           └── UserService.cache_user
```

This bidirectional linking enables:
- `babel why "UserService"` → surfaces the decision
- `babel list --from [decision]` → shows linked symbols

### Why Link to Commits

| Benefit | Description |
|---------|-------------|
| Traceability | Know WHY code was written |
| Archaeology | `babel why --commit` works |
| Symbol context | Know which functions implement a decision |
| Review | Connect intent to implementation |
| P8 compliance | Evolution is traceable |

### When to Link

```bash
# After implementing a decision
babel capture "Using Redis for caching" --batch
# ... user accepts ...
# ... implement code ...
git commit -m "Add Redis caching"
babel link GP-LF --to-commit HEAD
# → Links to commit AND auto-links to touched symbols
```

### Symbol Linking Requirements

For symbols to be auto-linked:
1. Code must be indexed: `babel map --index babel-tool/`
2. Commit must touch indexed files
3. Symbols exist in the graph

If no symbols found, only commit link is created (no error).

---

## [LNK-07] --commits

**Purpose**: List all decision-to-commit links.

```bash
babel link --commits
```

**Output**:
```
Decision → Commit Links (1-10 of 92):
(Bridges intent with state)

  [GP-LF] Add --list and --all options to babel li
    → commit [7ac2e6bb] (by user)

  [IB-OE] Add AI-Safe Command Reference section to
    → commit [3c0af881] (by user)
```

### Related Commands

```bash
# Find unlinked decisions
babel gaps --decisions

# Get suggestions for linking
babel suggest-links --from-recent 10

# Query why a commit was made
babel why --commit c73a08f
```

---

## [LNK-08] Use Cases

### Use Case 1: After Review Acceptance

```bash
# User accepts proposals
babel review --accept-all

# AI links immediately
babel link GP-LF
babel link XY-AB
```

### Use Case 2: Bulk Cleanup

```bash
# See unlinked count
babel status
# Shows: Unlinked: 2208

# Link all to active purpose
babel link --all
```

### Use Case 3: After Implementation

```bash
# Capture decision
babel capture "Using SQLite for offline" --batch
# → [ABC123]

# User accepts
babel review --accept ABC123

# Implement
# ... write code ...
git commit -m "Add SQLite storage"

# Link decision to commit
babel link ABC123 --to-commit HEAD
```

### Use Case 4: Selective Linking

```bash
# List unlinked
babel link --list

# Link specific ones
babel link GP-LF
babel link XY-AB PA-AO  # To specific purpose
```

### Use Case 5: Audit Decision Coverage

```bash
# How many decisions have commits?
babel link --commits | wc -l

# What's missing?
babel gaps --decisions
```

---

## [LNK-09] AI Operator Guide

### Mandatory After Acceptance

When user accepts proposals, **link immediately**:

```bash
# User runs:
babel review --accept GP-LF

# You run:
babel link GP-LF
```

### Why Linking Matters

Unlinked artifacts:
- Can't inform `babel why` queries
- Are orphans in the knowledge graph
- Represent lost knowledge

### Detection Pattern

| Event | Action |
|-------|--------|
| After `review --accept` | `babel link <id>` |
| After `review --accept-all` | `babel link --all` or link each |
| After implementation commit | `babel link <id> --to-commit HEAD` |
| High unlinked count in status | Suggest `babel link --all` |

### Symbol Auto-Linking

When you run `babel link <id> --to-commit HEAD`:
1. Decision links to commit (implements edge)
2. Touched files are detected from git diff
3. Symbols in those files are found via index
4. Decision links to each symbol (implemented_in edge)

**This completes the semantic bridge** — the decision now points to both:
- The git commit (state)
- The code symbols (implementation)

### Check Unlinked Count

```bash
babel status | grep "Unlinked"
# Unlinked: 2208 (isolated - can't inform 'why' queries)
```

If high, suggest linking session.

---

## [LNK-10] Integration

### Command Lifecycle

```
capture --batch → review --accept → link → [discoverable via why]
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `babel review` | Accept artifacts before linking |
| `babel why` | Linked artifacts inform queries |
| `babel gaps` | Shows unlinked decisions/commits |
| `babel suggest-links` | AI suggestions for commit links |
| `babel status` | Shows unlinked count |

### Link Flow

```bash
# 1. Capture decision
babel capture "decision" --batch

# 2. User accepts
babel review --accept XY-AB

# 3. Link to purpose
babel link XY-AB

# 4. Implement code
git commit -m "Implementation"

# 5. Link to commit
babel link XY-AB --to-commit HEAD

# 6. Now fully traceable
babel why --commit HEAD
# → Shows linked decision
```

---

## [LNK-11] Quick Reference

```bash
# Basic linking
babel link <artifact_id>              # To active purpose
babel link <artifact_id> <purpose_id> # To specific purpose

# List unlinked
babel link --list
babel link --list --full
babel link --list --offset 10 --limit 20

# Bulk linking
babel link --all

# Git commit linking
babel link <id> --to-commit HEAD
babel link <id> --to-commit <sha>
babel link --commits
```

### Link Checklist

- [ ] Artifact accepted via review?
- [ ] Linked to purpose after acceptance?
- [ ] Linked to commit after implementation?
- [ ] Checked unlinked count in status?

### Common Patterns

```bash
# After review
babel review --accept XY-AB && babel link XY-AB

# Bulk cleanup
babel link --all

# After implementation
babel link XY-AB --to-commit HEAD
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~546
Last updated: 2026-01-24
Change: Added symbol auto-linking documentation to --to-commit section
=============================================================================
-->
