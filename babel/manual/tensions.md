# babel tensions — Surface Conflicts and Disagreements (ORIENT Flow)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For severity section, read offset=105 limit=45
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [TEN-01] Intent | 32-60 | purpose, ORIENT flow, conflicts, P4 | `offset=27 limit=38` |
| [TEN-02] Command Overview | 61-100 | syntax, parameters, output | `offset=56 limit=49` |
| [TEN-03] Severity Levels | 101-128 | critical, warning, info, severity | `offset=96 limit=37` |
| [TEN-04] Resolution | 129-169 | challenge, evidence, resolve, outcomes | `offset=124 limit=50` |
| [TEN-05] Use Cases | 170-215 | examples, scenarios, workflows | `offset=165 limit=55` |
| [TEN-06] AI Operator Guide | 216-254 | session start, mandatory, detection | `offset=211 limit=48` |
| [TEN-07] Quick Reference | 255-299 | cheatsheet, patterns | `offset=250 limit=54` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[TEN-" .babel/manual/tensions.md    # Find all sections
grep -n "TEN-03" .babel/manual/tensions.md     # Find severity section
```

---

## [TEN-01] Intent

`babel tensions` surfaces **open conflicts** between artifacts — disagreements that need resolution.

### The Problem It Solves

| Without Tensions | With Tensions |
|------------------|---------------|
| Conflicts hidden | Conflicts visible |
| Contradictions accumulate | Contradictions surfaced |
| Silent drift | Explicit disagreement |
| Groupthink risk | P4: Disagreement as information |

### Core Principle (P4)

**Disagreement is information, not conflict.**

Tensions reveal important project dynamics:
- Competing requirements
- Contradictory decisions
- Evolving understanding
- Unresolved debates

### When to Use

**MANDATORY**: Run at every session start alongside `babel status` and `babel questions`.

---

## [TEN-02] Command Overview

```bash
babel tensions [options]
```

| Parameter | Purpose |
|-----------|---------|
| `--verbose`, `-v` | Show full details |
| `--full` | Show complete content without truncation |
| `--format` | Output format (json, table, list) |

### Output When No Tensions

```
No open tensions.

Resolved: 7 (confirmed: 4, revised: 3, synthesized: 0)

-> Next: babel status  (All tensions resolved)
```

### Output When Tensions Exist

```
Open tensions (2):

🔴 [T1] [CRITICAL] Decision A conflicts with Constraint B
   Created: 2026-01-20
   Evidence: 2 items

🟡 [T2] [WARNING] Purpose X may contradict Purpose Y
   Created: 2026-01-22
   Evidence: 0 items

-> Next: babel challenge <id>  (Add disagreement)
```

---

## [TEN-03] Severity Levels

Tensions are auto-classified by severity.

| Severity | Icon | Meaning | Response |
|----------|------|---------|----------|
| Critical | 🔴 | Hard constraint violated, multiple conflicts | Accelerate resolution |
| Warning | 🟡 | Potential conflict, needs attention | Maintain pace |
| Info | 🟢 | Minor tension, informational | Continue normally |

### Severity Factors

| Factor | Impact |
|--------|--------|
| Constraint involved | Higher severity |
| Multiple artifacts | Higher severity |
| Recent creation | Higher urgency |
| Evidence count | More data = clearer picture |

### Resolution Priority (P5)

**P5: Adaptive Cycle Rate** — Calibrate response speed to severity:
- Critical: Resolve before proceeding
- Warning: Resolve soon
- Info: Resolve when convenient

---

## [TEN-04] Resolution

Tensions are created via `babel challenge` and resolved via `babel resolve`.

### Creating a Tension

```bash
# Challenge an existing decision
babel challenge GP-LF "This conflicts with our performance constraint"

# Add evidence
babel evidence <tension-id> "Benchmark shows 500ms response time"
babel evidence <tension-id> "SLA requires < 200ms"
```

### Resolving a Tension

```bash
babel resolve <tension-id> --outcome confirmed --resolution "Original was correct"
babel resolve <tension-id> --outcome revised --resolution "Updated approach needed"
babel resolve <tension-id> --outcome synthesized --resolution "Merged both perspectives"
```

### Resolution Outcomes

| Outcome | Meaning |
|---------|---------|
| `confirmed` | Original artifact was correct |
| `revised` | New artifact supersedes old |
| `synthesized` | Both partially right, merged |
| `uncertain` | Can't decide yet (P6: Hold ambiguity) |

### After Revision

When outcome is `revised`, link the evolution chain:
```bash
babel link <new-artifact-id> <old-artifact-id>  # evolves_from edge
```

---

## [TEN-05] Use Cases

### Use Case 1: Session Start (MANDATORY)

```bash
babel status
babel tensions
babel questions
```

Know your conflicts before working.

### Use Case 2: Discovering Conflict

```bash
# You notice: Decision A contradicts Constraint B
babel challenge A "Conflicts with constraint B - requires negotiation"
```

### Use Case 3: Building Evidence

```bash
# Tension exists, gather evidence
babel evidence T1 "Performance test shows 400ms"
babel evidence T1 "SLA document specifies 200ms max"
```

### Use Case 4: Resolving Tension

```bash
# After discussion with user
babel resolve T1 --outcome revised --resolution "Changed to Redis for performance"

# Link evolution chain
babel link <new-decision-id> <old-decision-id>
```

### Use Case 5: Checking Resolution History

```bash
babel tensions --full
# Shows: Resolved: 7 (confirmed: 4, revised: 3, synthesized: 0)
```

---

## [TEN-06] AI Operator Guide

### Session Start (MANDATORY)

```bash
# Run these three at every session start
babel status
babel tensions
babel questions
```

### What to Look For

| Tensions Output | Action |
|-----------------|--------|
| "No open tensions" | Good, proceed |
| Critical (🔴) | Surface to user immediately |
| Warning (🟡) | Note for later discussion |
| Info (🟢) | Low priority |

### When to Create Tensions

| Observation | Action |
|-------------|--------|
| Decision contradicts constraint | `babel challenge <id>` |
| Two decisions conflict | `babel challenge <id>` |
| Evidence against prior decision | `babel challenge <id>` + `babel evidence` |

### Surfacing to User

If tensions exist:
```
"There are N open tensions that may affect this work:
- [T1] Decision A conflicts with Constraint B
Consider resolving before proceeding."
```

---

## [TEN-07] Quick Reference

```bash
# Check tensions (session start)
babel tensions

# Full details
babel tensions --full
babel tensions --verbose

# JSON output
babel tensions --format json

# Create tension
babel challenge <artifact-id> "reason"

# Add evidence
babel evidence <tension-id> "observation"

# Resolve
babel resolve <id> --outcome confirmed --resolution "..."
babel resolve <id> --outcome revised --resolution "..."
```

### Session Start Sequence

```bash
babel status && babel tensions && babel questions
```

### Tension Lifecycle

```
challenge → evidence → resolve --outcome X → [if revised: link evolves_from]
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~310
Last updated: 2026-01-24
=============================================================================
-->
