# babel gaps — Find Implementation Gaps (GIT-BABEL Bridge)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --decisions section, read offset=90 limit=40
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [GAP-01] Intent | 30-53 | purpose, unlinked, bridge | `offset=25 limit=33` |
| [GAP-02] Command Overview | 54-77 | syntax, parameters | `offset=49 limit=33` |
| [GAP-03] --commits | 78-106 | unlinked commits | `offset=73 limit=38` |
| [GAP-04] --decisions | 107-135 | unlinked decisions | `offset=102 limit=38` |
| [GAP-05] Use Cases | 136-184 | examples, scenarios | `offset=131 limit=58` |
| [GAP-06] Quick Reference | 185-228 | cheatsheet, patterns | `offset=180 limit=53` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[GAP-" .babel/manual/gaps.md    # Find all sections
```

---

## [GAP-01] Intent

`babel gaps` shows **implementation gaps** — decisions without commits and commits without decisions.

### The Problem It Solves

| Gap Type | Problem |
|----------|---------|
| Decision without commit | Intent not implemented |
| Commit without decision | Code lacks documented why |

### Git-Babel Bridge (P7, P8)

Decisions should connect to their implementing commits:
- **P7**: Reasoning travels with code
- **P8**: Evolution is traceable

```
Decision → implements → Commit
Commit ← implements ← Decision
```

---

## [GAP-02] Command Overview

```bash
babel gaps [options]
```

| Parameter | Purpose |
|-----------|---------|
| `--commits` | Only show unlinked commits |
| `--decisions` | Only show unlinked decisions |
| `--from-recent N` | Check last N commits (default: 20) |
| `--limit N` | Max items per section (default: 10) |
| `--offset N` | Skip first N items |

### Default Output

```bash
babel gaps
```

Shows both unlinked decisions and commits.

---

## [GAP-03] --commits

**Purpose**: Show commits without linked decisions.

```bash
babel gaps --commits
```

**Output**:
```
Unlinked commits (last 20):

  [abc123] "Add caching layer"
    No linked decisions
    → babel link <decision-id> --to-commit abc123

  [def456] "Fix login bug"
    No linked decisions
```

### Why This Matters

Commits without decisions:
- Lack documented reasoning
- Can't be found via `babel why --commit`
- Have no traceability

---

## [GAP-04] --decisions

**Purpose**: Show decisions without linked commits.

```bash
babel gaps --decisions
```

**Output**:
```
Unlinked decisions:

  [GP-LF] "Add --list and --all options"
    No linked commits
    → babel link GP-LF --to-commit <sha>

  [XY-AB] "Use Redis for caching"
    No linked commits
```

### Why This Matters

Decisions without commits:
- May be unimplemented
- Or implemented but not linked
- Need closure

---

## [GAP-05] Use Cases

### Use Case 1: Audit Coverage

```bash
babel gaps
# See: How many decisions have implementations?
# See: How many commits have reasoning?
```

### Use Case 2: After Sprint

```bash
babel gaps --from-recent 50
# Check last 50 commits for gaps
```

### Use Case 3: Link Missing Decisions

```bash
babel gaps --commits
# For each:
babel link <decision-id> --to-commit <sha>
```

### Use Case 4: Find Unimplemented Decisions

```bash
babel gaps --decisions
# Review: Are these implemented? Link or deprecate.
```

### Use Case 5: Before Code Review

```bash
babel gaps --from-recent 10
# Ensure PRs have documented decisions
```

### Use Case 6: Get AI Suggestions

```bash
babel gaps
babel suggest-links --from-recent 10
# AI analyzes commits and suggests matches
```

---

## [GAP-06] Quick Reference

```bash
# Show all gaps
babel gaps

# Only commits
babel gaps --commits

# Only decisions
babel gaps --decisions

# Check more commits
babel gaps --from-recent 50

# Pagination
babel gaps --limit 20 --offset 10
```

### Workflow

```bash
# 1. Find gaps
babel gaps

# 2. Get AI suggestions
babel suggest-links

# 3. Link them
babel link <decision> --to-commit <sha>

# 4. Verify
babel status --git
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~235
Last updated: 2026-01-24
=============================================================================
-->
