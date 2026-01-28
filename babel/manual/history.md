# babel history — View Recent Activity

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For scope filters section, read offset=85 limit=40
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [HIS-01] Intent | 30-51 | purpose, activity, events | `offset=25 limit=31` |
| [HIS-02] Command Overview | 52-80 | syntax, parameters | `offset=47 limit=38` |
| [HIS-03] Limiting Results | 81-107 | -n, count | `offset=76 limit=36` |
| [HIS-04] Scope Filters | 108-134 | shared, local | `offset=103 limit=36` |
| [HIS-05] Use Cases | 135-180 | examples, scenarios | `offset=130 limit=55` |
| [HIS-06] Quick Reference | 181-220 | cheatsheet, patterns | `offset=176 limit=49` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[HIS-" .babel/manual/history.md    # Find all sections
```

---

## [HIS-01] Intent

`babel history` shows **recent activity** in the project — captures, reviews, links, and other events.

### The Problem It Solves

| Without History | With History |
|-----------------|--------------|
| What happened? | Recent events visible |
| Who did what? | Activity audit trail |
| What changed? | Chronological view |

### What It Shows

- Captures and their types
- Reviews and acceptance
- Links created
- Coherence checks
- Task completions

---

## [HIS-02] Command Overview

```bash
babel history [options]
```

| Parameter | Purpose |
|-----------|---------|
| `-n N` | Show N most recent events |
| `--shared` | Only shared (team) events |
| `--local` | Only local (personal) events |
| `--format` | Output format (json, table, list) |

### Default Output

```bash
babel history
```

Shows recent events:
```
Recent events:
  ● [abc123] CAPTURED: Using Redis for caching
  ○ [def456] REVIEWED: Accepted proposal
  ● [ghi789] LINKED: Decision to purpose
```

---

## [HIS-03] Limiting Results

### Default (20)

```bash
babel history
# Shows 20 most recent
```

### Custom Count

```bash
babel history -n 50    # Last 50 events
babel history -n 10    # Last 10 events
babel history -n 100   # Last 100 events
```

### Finding Task Progress

```bash
babel history -n 30 | grep -E "TASK|COMPLETE"
```

Shows task-related events for continuation.

---

## [HIS-04] Scope Filters

### Shared Only

```bash
babel history --shared
```

Shows only team-visible events (git-tracked).

### Local Only

```bash
babel history --local
```

Shows only personal events (git-ignored).

### Scope Indicators

| Symbol | Meaning |
|--------|---------|
| `●` | Shared (team) |
| `○` | Local (personal) |

---

## [HIS-05] Use Cases

### Use Case 1: What Happened Recently

```bash
babel history
# Quick view of recent activity
```

### Use Case 2: Task Continuation

```bash
babel history -n 30 | grep -E "TASK|COMPLETE"
# Find: TASK A.2 COMPLETE, TASK B.1 in progress
# Resume from where left off
```

### Use Case 3: Team Activity

```bash
babel history --shared
# See what team has captured
```

### Use Case 4: Personal Notes

```bash
babel history --local
# See personal captures and experiments
```

### Use Case 5: After Context Compression

```bash
babel history -n 20
# Reconstruct what was happening
```

### Use Case 6: JSON Export

```bash
babel history --format json > activity.json
```

---

## [HIS-06] Quick Reference

```bash
# Recent events
babel history
babel history -n 30

# By scope
babel history --shared
babel history --local

# Task tracking
babel history -n 30 | grep -E "TASK|COMPLETE"

# JSON output
babel history --format json
```

### Common Patterns

```bash
# Session orientation
babel status && babel history -n 10

# Task continuation
babel history -n 30 | grep TASK

# Team review
babel history --shared -n 50
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~240
Last updated: 2026-01-24
=============================================================================
-->
