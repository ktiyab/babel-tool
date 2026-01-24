# babel status — Project Overview and Health Dashboard

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --git section, read offset=135 limit=45
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [STA-01] Intent | 35-63 | purpose, ORIENT flow, session start | `offset=30 limit=38` |
| [STA-02] Command Overview | 64-90 | syntax, parameters, flags | `offset=59 limit=36` |
| [STA-03] Output Sections | 91-158 | init memos, events, purposes, health | `offset=86 limit=77` |
| [STA-04] --git | 159-205 | commit links, sync health, gaps | `offset=154 limit=56` |
| [STA-05] --full | 206-238 | truncation, complete content | `offset=201 limit=42` |
| [STA-06] --format | 239-272 | json, table, list, summary | `offset=234 limit=43` |
| [STA-07] Use Cases | 273-330 | examples, scenarios, workflows | `offset=268 limit=67` |
| [STA-08] AI Operator Guide | 331-372 | session start, mandatory, compression | `offset=326 limit=51` |
| [STA-09] Integration | 373-406 | tensions, questions, review | `offset=368 limit=43` |
| [STA-10] Quick Reference | 407-458 | cheatsheet, patterns | `offset=402 limit=61` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[STA-" manual/status.md    # Find all sections
grep -n "STA-04" manual/status.md     # Find --git section
```

---

## [STA-01] Intent

`babel status` is the **ORIENT** command — it provides a complete project overview for session orientation.

### The Problem It Solves

| Without Status | With Status |
|----------------|-------------|
| AI starts blind | AI knows project state |
| Init memos forgotten | Critical rules surfaced |
| Health unknown | Project health visible |
| Pending work hidden | Queued items shown |

### Core Principle

**Run `babel status` at every session start.** Non-negotiable.

### What It Shows

- Init memos (critical instructions)
- Event counts (shared vs local)
- Recent purposes (goals and context)
- Coherence state
- Validation status
- Pending proposals
- Project health score

---

## [STA-02] Command Overview

```bash
babel status [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Display** | `--full` | Show full content without truncation |
| | `--format` | Output format (json, table, list, summary) |
| | `--limit-purposes N` | Show N most recent purposes (default: 10) |
| **Sync** | `--git` | Show git-babel sync health |
| **Cache** | `--force` | Bypass cache, force fresh data |

### Output Indicators

| Symbol | Meaning |
|--------|---------|
| `◎` | Section header |
| `●` | Shared scope (git-tracked) |
| `○` | Local scope (git-ignored) |
| `◐` | Moderate health/partial |
| `✓` | Healthy/checked |
| `⚠` | Warning/needs attention |

---

## [STA-03] Output Sections

### Init Instructions

```
◎ Init Instructions (read before work):
  → Tests must directly use babel commands...
  → CRITICAL CONSTRAINT - Directory Protocol...
  → NEVER read .babel/ files directly...
```

**What it is**: Foundational memos saved with `babel memo "..." --init`. These are critical rules that AI must see before any work.

### Project Metrics

```
Project: /path/to/project
Events: 88457 (● 45252 shared, ○ 43205 local)
Artifacts: 4060
Connections: 3385
Unlinked: 2209 (isolated - can't inform 'why' queries)
```

| Metric | Meaning |
|--------|---------|
| Events | Total captured events |
| Artifacts | Decisions, constraints, purposes, etc. |
| Connections | Graph edges between artifacts |
| Unlinked | Orphan artifacts (need linking) |

### Purposes

```
◎ Purpose: Token efficiency as primary intent of babel map
    Goal: Token efficiency

Need: Tools lose reasoning context...
  └─ Purpose: Use Babel to build itself...

  (66 older purposes hidden)
  → babel list purposes --all
```

Shows recent purposes with goals and success criteria.

### Health Indicators

```
Coherence: ✓ just checked
Commits captured: 31
◐ Validation: 133 validated, 6 need review
  ⚠ 6 evidence-only (tested but not endorsed)
Decision-commit links: 92
Pending: 1 proposal(s)
Queued: 1 extraction(s)
◐ Project Health: Moderate (8/8 principles)
```

| Indicator | Action if Warning |
|-----------|-------------------|
| Coherence | Run `babel coherence` |
| Validation | Run `babel validation` |
| Pending | Run `babel review` |
| Queued | Run `babel process-queue` |
| Health | Check individual indicators |

---

## [STA-04] --git

**Purpose**: Show git-babel sync health — how well decisions connect to commits.

```bash
babel status --git
```

**Output**:
```
Decision-commit links: 92
  ⚠ Unlinked decisions: 5
  ⚠ Unlinked commits (last 20): 3
  → Run: babel gaps (see all gaps)
  → Run: babel suggest-links (AI suggestions)
```

### What It Shows

| Metric | Meaning |
|--------|---------|
| Decision-commit links | Decisions with commit references |
| Unlinked decisions | Decisions without implementation |
| Unlinked commits | Commits without decision context |

### When to Use --git

- After implementation sprints
- Before code reviews
- To audit decision coverage
- When `babel why --commit` returns empty

### Follow-up Commands

```bash
# See all gaps
babel gaps

# Get AI suggestions for linking
babel suggest-links --from-recent 10

# Link a decision to commit
babel link <decision-id> --to-commit HEAD
```

---

## [STA-05] --full

**Purpose**: Show complete content without truncation.

```bash
babel status --full
```

**Default behavior**: Long content is truncated for readability.

**With --full**: All content shown completely.

### When to Use --full

| Situation | Use --full? |
|-----------|-------------|
| Quick orientation | No |
| Debugging issue | Yes |
| Reading all init memos | Yes |
| Reviewing all purposes | Yes |

### Alternative for Purposes

```bash
# Show all purposes (better than --full)
babel status --limit-purposes 0

# Or list separately
babel list purposes --all
```

---

## [STA-06] --format

**Purpose**: Control output format for different use cases.

```bash
babel status --format json
babel status --format table
babel status --format summary
```

### Format Options

| Format | Use Case |
|--------|----------|
| `auto` | Default, adapts to terminal |
| `table` | Structured display |
| `list` | Linear output |
| `json` | Machine parsing, scripts |
| `summary` | Minimal overview |

### JSON Output Example

```bash
babel status --format json | jq '.health'
```

Useful for:
- CI/CD pipelines
- Monitoring dashboards
- Custom tooling
- Automated reporting

---

## [STA-07] Use Cases

### Use Case 1: Session Start (MANDATORY)

Every session begins with:

```bash
babel status
babel tensions
babel questions
```

**Result**: You know project purpose, health, conflicts, unknowns.

### Use Case 2: After Context Compression

When your context is compressed:

```bash
babel status    # Re-orient to project
babel why "current feature"  # Specific context
```

### Use Case 3: Health Check

```bash
babel status
# Check indicators:
# - Validation: are decisions validated?
# - Pending: are proposals waiting?
# - Coherence: is system coherent?
```

### Use Case 4: Before Code Review

```bash
babel status --git
# See: unlinked decisions and commits
# Follow up: babel gaps, babel suggest-links
```

### Use Case 5: Debug Project Issues

```bash
babel status --full
# See complete content without truncation
# Identify: missing memos, stale purposes
```

### Use Case 6: Monitoring in CI

```bash
babel status --format json | jq '.health'
# Use in automated checks
```

---

## [STA-08] AI Operator Guide

### Session Start Protocol (MANDATORY)

```bash
# ALWAYS run these three at session start
babel status      # Project overview
babel tensions    # Open conflicts
babel questions   # Acknowledged unknowns
```

**Skip = Work blind.** Non-negotiable.

### What to Look For

| Section | Action |
|---------|--------|
| Init Instructions | READ before any work |
| Unlinked count high | Consider linking artifacts |
| Pending > 0 | Remind user: `babel review` |
| Queued > 0 | May need `babel process-queue` |
| Health < 8/8 | Investigate weak principles |

### After Context Compression

```bash
# Quick re-orientation
babel status

# Then specific context
babel why "what you were working on"
```

### Periodic Reminders

If status shows pending proposals:
```
"You have pending proposals. Review with: babel review"
```

---

## [STA-09] Integration

### Session Start Flow

```
status → tensions → questions → [oriented] → begin work
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `babel tensions` | Complements status at session start |
| `babel questions` | Complements status at session start |
| `babel review` | Process pending shown in status |
| `babel validation` | Detail for validation indicator |
| `babel coherence` | Detail for coherence indicator |
| `babel gaps` | Detail for git sync health |

### Status + Other Commands

```bash
# Full orientation sequence
babel status && babel tensions && babel questions

# After status shows pending
babel review --list

# After status shows validation needs
babel validation
```

---

## [STA-10] Quick Reference

```bash
# Basic status
babel status

# Full content
babel status --full

# Git sync health
babel status --git

# JSON output
babel status --format json

# More purposes
babel status --limit-purposes 20

# Fresh data (bypass cache)
babel status --force
```

### Session Start Checklist

- [ ] Ran `babel status`?
- [ ] Read init instructions?
- [ ] Noted pending/queued items?
- [ ] Ran `babel tensions`?
- [ ] Ran `babel questions`?

### Common Patterns

```bash
# Full session orientation
babel status && babel tensions && babel questions

# Quick health check
babel status | grep -E "Health|Pending|Validation"

# CI/CD monitoring
babel status --format json | jq '.health'
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~450
Last updated: 2026-01-24
=============================================================================
-->
