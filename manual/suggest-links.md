# babel suggest-links — AI-Assisted Link Suggestions

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [SUG-01] Intent | 27-47 | purpose, AI suggestions, matching | `offset=22 limit=30` |
| [SUG-02] Command Overview | 48-76 | syntax, parameters | `offset=43 limit=38` |
| [SUG-03] Use Cases | 77-125 | examples, scenarios | `offset=72 limit=58` |
| [SUG-04] Quick Reference | 126-159 | cheatsheet | `offset=121 limit=43` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[SUG-" manual/suggest-links.md
```

---

## [SUG-01] Intent

`babel suggest-links` uses AI to **match decisions with commits** automatically.

### The Problem It Solves

| Without Suggestions | With Suggestions |
|---------------------|------------------|
| Manual matching | AI analyzes and suggests |
| Tedious review | Confidence scores |
| May miss connections | Semantic matching |

### How It Works

1. Analyzes recent commit messages
2. Compares with unlinked decisions
3. Suggests matches with confidence scores
4. You confirm and link

---

## [SUG-02] Command Overview

```bash
babel suggest-links [options]
```

| Parameter | Purpose |
|-----------|---------|
| `--from-recent N` | Analyze last N commits (default: 5) |
| `--commit SHA` | Analyze specific commit |
| `--min-score N` | Minimum confidence (0-1, default: 0.3) |
| `--all` | Show all, including low-confidence |

### Output

```
Analyzing last 5 commits...

Commit [abc123] "Add Redis caching layer"
  Suggested decision: [XY-AB] "Use Redis for caching"
  Confidence: 0.85
  → babel link XY-AB --to-commit abc123

Commit [def456] "Fix login redirect"
  No strong matches (below 0.3 threshold)
```

---

## [SUG-03] Use Cases

### Use Case 1: After Implementation Sprint

```bash
babel suggest-links --from-recent 20
# Get suggestions for last 20 commits
```

### Use Case 2: Specific Commit

```bash
babel suggest-links --commit abc123
# Analyze just this commit
```

### Use Case 3: See All Suggestions

```bash
babel suggest-links --all
# Include low-confidence matches
```

### Use Case 4: Higher Confidence Only

```bash
babel suggest-links --min-score 0.7
# Only show strong matches
```

### Use Case 5: Complete Workflow

```bash
# 1. Find gaps
babel gaps

# 2. Get suggestions
babel suggest-links --from-recent 10

# 3. Review and link
babel link XY-AB --to-commit abc123
babel link ZW-CD --to-commit def456

# 4. Verify
babel status --git
```

---

## [SUG-04] Quick Reference

```bash
# Default (last 5 commits)
babel suggest-links

# More commits
babel suggest-links --from-recent 20

# Specific commit
babel suggest-links --commit <sha>

# All suggestions
babel suggest-links --all

# High confidence only
babel suggest-links --min-score 0.7
```

### Workflow

```bash
babel gaps → suggest-links → link --to-commit → status --git
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~165
Last updated: 2026-01-24
=============================================================================
-->
