# babel coherence — Verify Project Alignment (MAINTAIN Flow)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --resolve section, read offset=120 limit=50
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [COH-01] Intent | 34-63 | purpose, MAINTAIN flow, drift detection | `offset=29 limit=39` |
| [COH-02] Command Overview | 64-110 | syntax, parameters, output | `offset=59 limit=56` |
| [COH-03] Basic Check | 111-136 | default check, cached, alignment | `offset=106 limit=35` |
| [COH-04] --force | 137-157 | bypass cache, fresh check | `offset=132 limit=30` |
| [COH-05] --resolve | 158-204 | interactive resolution, batch mode | `offset=153 limit=56` |
| [COH-06] --qa | 205-244 | QA mode, detailed report | `offset=200 limit=49` |
| [COH-07] Use Cases | 245-295 | examples, scenarios, workflows | `offset=240 limit=60` |
| [COH-08] AI Operator Guide | 296-345 | after changes, verify, detection | `offset=291 limit=59` |
| [COH-09] Quick Reference | 346-396 | cheatsheet, patterns | `offset=341 limit=60` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[COH-" manual/coherence.md    # Find all sections
grep -n "COH-05" manual/coherence.md     # Find --resolve section
```

---

## [COH-01] Intent

`babel coherence` verifies that **artifacts align with project purpose** — detecting drift before it compounds.

### The Problem It Solves

| Without Coherence | With Coherence |
|-------------------|----------------|
| Drift accumulates silently | Drift detected early |
| Artifacts contradict purpose | Misalignment surfaced |
| "Something feels off" | Concrete issues identified |
| Manual review only | Automated alignment check |

### Core Principle

**Verify AFTER changes. Drift is silent — you must detect it.**

```
Implement → babel coherence → Surface issues → Resolve
```

### When to Use

- After implementing changes
- After code modifications
- Periodically during long sessions
- When "something feels off"

---

## [COH-02] Command Overview

```bash
babel coherence [options]
```

| Parameter | Purpose |
|-----------|---------|
| `--force` | Bypass cache, force fresh check |
| `--full` | Show complete content without truncation |
| `--qa` | QA/QC mode with detailed report |
| `--resolve` | Interactive resolution mode |
| `--batch` | Non-interactive mode (for AI, use with --resolve) |

### Output When Coherent

```
◎ Purpose: Use Babel to build itself...

Coherence: ✓ just checked

Checked 10 artifact(s):
  ✓ 10 coherent

-> Next: babel capture "..." --batch
```

### Output When Issues Found

```
◎ Purpose: Use Babel to build itself...

Coherence: ⚠ issues found

Checked 10 artifact(s):
  ✓ 8 coherent
  ⚠ 2 low alignment

Low alignment:
  [GP-LF] DECISION: Add --list and --all options
    Alignment: 0.42 (expected > 0.6)

-> Next: babel coherence --resolve
```

---

## [COH-03] Basic Check

**Purpose**: Quick alignment check using cached data.

```bash
babel coherence
```

**What it checks**:
- Artifact alignment with purpose
- Semantic similarity scores
- Graph connectivity

**Caching**: Results are cached. Subsequent calls return cached result unless `--force` is used.

### Alignment Scoring

| Score | Meaning |
|-------|---------|
| > 0.8 | Strong alignment |
| 0.6 - 0.8 | Good alignment |
| 0.4 - 0.6 | Low alignment (flagged) |
| < 0.4 | Poor alignment (investigate) |

---

## [COH-04] --force

**Purpose**: Bypass cache and perform fresh coherence check.

```bash
babel coherence --force
```

**When to use**:
- After significant changes
- Cache seems stale
- Investigating specific issue
- Want latest analysis

**Output includes**:
```
Coherence: ✓ checked (fresh)
```

---

## [COH-05] --resolve

**Purpose**: Interactive resolution mode for identified issues.

### Interactive Mode (for humans)

```bash
babel coherence --resolve
```

Prompts for each issue:
```
Issue: [GP-LF] low alignment (0.42)

Options:
  1. Re-link to different purpose
  2. Challenge the artifact
  3. Skip for now

Choice:
```

### Non-Interactive Mode (for AI)

```bash
babel coherence --resolve --batch
```

**IMPORTANT for AI operators**: Always use `--batch` flag.

**Output**:
```
Coherence resolution (batch mode):

Issue 1: [GP-LF] low alignment
  Suggestion: Consider re-linking to purpose [PA-AO]
  Action: babel link GP-LF PA-AO

Issue 2: [XY-AB] contradicts constraint
  Suggestion: Challenge or revise
  Action: babel challenge XY-AB "reason"

-> Next: Review suggestions and apply
```

---

## [COH-06] --qa

**Purpose**: QA/QC mode with detailed diagnostic report.

```bash
babel coherence --qa
```

**Output includes**:
```
QA/QC Coherence Report
======================

Purpose Alignment
-----------------
  High (>0.8):    45 artifacts
  Good (0.6-0.8): 32 artifacts
  Low (0.4-0.6):  8 artifacts
  Poor (<0.4):    2 artifacts

Graph Connectivity
------------------
  Connected:      80 artifacts
  Orphaned:       7 artifacts

Recommendations
---------------
  1. Review 8 low-alignment artifacts
  2. Link 7 orphaned artifacts
  3. Challenge 2 poor-alignment artifacts
```

**When to use**:
- Periodic health checks
- Before major releases
- After significant refactoring
- Team reviews

---

## [COH-07] Use Cases

### Use Case 1: After Implementation

```bash
# Implemented a feature
babel coherence
# Check if changes align with purpose
```

### Use Case 2: Something Feels Off

```bash
babel coherence --force
# Fresh check when instinct says "drift"
```

### Use Case 3: Resolve Issues (AI)

```bash
babel coherence --resolve --batch
# Get suggestions without prompts
```

### Use Case 4: Team QA Review

```bash
babel coherence --qa --full
# Detailed report for team discussion
```

### Use Case 5: After Bulk Changes

```bash
# After merging branch or bulk edits
babel coherence --force --full
# Comprehensive check of all changes
```

### Use Case 6: Investigating Low Alignment

```bash
# Coherence shows low alignment for GP-LF
babel why "GP-LF purpose"
babel list --from GP-LF
# Understand why alignment is low
# Then either re-link or challenge
```

---

## [COH-08] AI Operator Guide

### When to Run Coherence

| Trigger | Action |
|---------|--------|
| After implementing decision | `babel coherence` |
| After multiple changes | `babel coherence --force` |
| User modifies code | Suggest coherence check |
| Session running long | Periodic check |
| "Something feels wrong" | `babel coherence --force` |

### Non-Interactive Pattern (MANDATORY)

```bash
# ALWAYS use --batch with --resolve for AI
babel coherence --resolve --batch

# NEVER use interactive mode
babel coherence --resolve  # WRONG - will prompt
```

### Handling Issues

| Issue Type | AI Action |
|------------|-----------|
| Low alignment | Suggest re-linking |
| Poor alignment | Suggest challenge |
| Contradicts constraint | Surface to user |
| Orphaned artifact | Suggest linking |

### Detection Pattern

```bash
# Check coherence
babel coherence

# If issues found, get batch suggestions
babel coherence --resolve --batch

# Present to user:
"Coherence check found 2 issues:
1. [GP-LF] has low alignment (0.42)
   Suggestion: Re-link to purpose [PA-AO]
2. [XY-AB] contradicts constraint [ZW-CD]
   Suggestion: Review and challenge if needed"
```

---

## [COH-09] Quick Reference

```bash
# Basic check (uses cache)
babel coherence

# Fresh check (bypass cache)
babel coherence --force

# Full details
babel coherence --full

# QA report
babel coherence --qa

# Resolve issues (interactive)
babel coherence --resolve

# Resolve issues (AI-safe)
babel coherence --resolve --batch
```

### Coherence Checklist

- [ ] Ran coherence after changes?
- [ ] Used --batch with --resolve?
- [ ] Investigated low-alignment artifacts?
- [ ] Surfaced issues to user?

### Common Patterns

```bash
# After implementation
babel coherence

# Investigation
babel coherence --force --full

# AI batch resolution
babel coherence --resolve --batch
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~380
Last updated: 2026-01-24
=============================================================================
-->
