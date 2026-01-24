# babel list — Browse and Discover Artifacts (DISCOVER Flow)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --from section, read offset=115 limit=45
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [LST-01] Intent | 34-54 | purpose, DISCOVER flow, browse | `offset=29 limit=30` |
| [LST-02] Command Overview | 55-75 | syntax, parameters, types | `offset=50 limit=30` |
| [LST-03] List by Type | 76-122 | decisions, constraints, purposes | `offset=71 limit=56` |
| [LST-04] --from | 123-149 | graph traversal, connected | `offset=118 limit=36` |
| [LST-05] --orphans | 150-176 | disconnected, no edges | `offset=145 limit=36` |
| [LST-06] --filter | 177-201 | keyword, search | `offset=172 limit=34` |
| [LST-07] Pagination | 202-234 | limit, offset, all | `offset=197 limit=42` |
| [LST-08] Use Cases | 235-278 | examples, scenarios | `offset=230 limit=53` |
| [LST-09] Quick Reference | 279-328 | cheatsheet, patterns | `offset=274 limit=59` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[LST-" manual/list.md    # Find all sections
grep -n "LST-04" manual/list.md     # Find --from section
```

---

## [LST-01] Intent

`babel list` browses and discovers artifacts in the knowledge graph.

### The Problem It Solves

| Without List | With List |
|--------------|-----------|
| Can't browse artifacts | Browse by type |
| No graph exploration | `--from` traversal |
| Finding orphans hard | `--orphans` flag |
| No keyword search | `--filter` search |

### Key Features

- **No LLM required** — fast, offline, direct graph access
- **Token efficient** — default limit 10, pagination via `--offset`
- **Graph-aware** — `--from` shows actual relationships

---

## [LST-02] Command Overview

```bash
babel list [type] [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Type** | `decisions` | List decisions |
| | `constraints` | List constraints |
| | `purposes` | List purposes |
| | `principles` | List principles |
| **Graph** | `--from ID` | Show connected artifacts |
| | `--orphans` | Show disconnected artifacts |
| **Filter** | `--filter KEYWORD` | Keyword search |
| **Pagination** | `--limit N` | Max items (default: 10) |
| | `--offset N` | Skip first N items |
| | `--all` | Show all (no limit) |

---

## [LST-03] List by Type

### List Decisions

```bash
babel list decisions
```

**Output**:
```
Decisions (1-10 of 89):
  [GP-LF] Add --list and --all options to babel link
  [XY-AB] Use Redis for caching
  ...

→ Next: babel list decisions --offset 10
```

### List Constraints

```bash
babel list constraints
```

### List Purposes

```bash
babel list purposes
```

### Overview (No Type)

```bash
babel list
```

Shows counts by type:
```
Artifacts:
  Decisions:   89
  Constraints: 23
  Purposes:    15
  Principles:  8
```

---

## [LST-04] --from

**Purpose**: Graph traversal — show artifacts connected to an ID.

```bash
babel list --from GP-LF
```

**Output**:
```
Connected to [GP-LF]:

  supports → [PA-AO] PURPOSE: Preserve intent across sessions
  tensions_with → [XY-AB] DECISION: Old approach
  evidence → [E1] EVIDENCE: Performance improvement
```

### Why Use --from

| Situation | Command |
|-----------|---------|
| Understand artifact context | `babel list --from <id>` |
| Find related decisions | `babel list --from <id>` |
| Trace connections | `babel list --from <id>` |

---

## [LST-05] --orphans

**Purpose**: Find artifacts with no connections.

```bash
babel list --orphans
```

**Output**:
```
Orphaned artifacts (7):
  [XY-AB] DECISION: Old decision without links
  [ZW-CD] CONSTRAINT: Disconnected constraint
  ...

→ Next: babel link <id>  (Connect orphans)
```

### Why Orphans Matter

Orphaned artifacts:
- Can't inform `babel why` queries
- Represent lost knowledge
- Should be linked or deprecated

---

## [LST-06] --filter

**Purpose**: Keyword search (case-insensitive).

```bash
babel list decisions --filter "cache"
```

**Output**:
```
Decisions matching 'cache' (2):
  [XY-AB] Use Redis for caching
  [ZW-CD] Cache invalidation strategy
```

### Filter Examples

```bash
babel list decisions --filter "api"
babel list constraints --filter "performance"
babel list --filter "security"  # All types
```

---

## [LST-07] Pagination

### Default Limit (10)

```bash
babel list decisions
# Shows first 10
```

### Custom Limit

```bash
babel list decisions --limit 20
```

### Pagination with Offset

```bash
babel list decisions              # Items 1-10
babel list decisions --offset 10  # Items 11-20
babel list decisions --offset 20  # Items 21-30
```

### Show All

```bash
babel list decisions --all
```

**Caution**: May be large. Use pagination for token efficiency.

---

## [LST-08] Use Cases

### Use Case 1: Browse Decisions

```bash
babel list decisions
babel list decisions --offset 10  # Next page
```

### Use Case 2: Find Related Artifacts

```bash
babel list --from GP-LF
# Shows: what supports, tensions, evidence
```

### Use Case 3: Find Orphans to Link

```bash
babel list --orphans
# Link each: babel link <id>
```

### Use Case 4: Search by Keyword

```bash
babel list decisions --filter "authentication"
```

### Use Case 5: Check Artifact Counts

```bash
babel list
# Shows counts by type
```

### Use Case 6: Export All for Review

```bash
babel list decisions --all > decisions.txt
```

---

## [LST-09] Quick Reference

```bash
# Overview (counts)
babel list

# By type
babel list decisions
babel list constraints
babel list purposes
babel list principles

# Graph traversal
babel list --from <id>
babel list --orphans

# Search
babel list decisions --filter "keyword"

# Pagination
babel list decisions --limit 20
babel list decisions --offset 10
babel list decisions --all
```

### Common Patterns

```bash
# Browse and paginate
babel list decisions
babel list decisions --offset 10

# Find and explore
babel list decisions --filter "cache"
babel list --from <found-id>

# Clean up orphans
babel list --orphans
babel link <id>  # For each
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~350
Last updated: 2026-01-24
=============================================================================
-->
