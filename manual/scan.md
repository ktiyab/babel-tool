# babel scan — Context-Aware Technical Analysis

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=192 limit=70
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [SCN-01] Intent | 33-77 | purpose, technical scan, EAST framework | `offset=28 limit=54` |
| [SCN-02] Command Overview | 79-133 | syntax, type, deep, verbose | `offset=74 limit=64` |
| [SCN-03] Scan Types | 135-207 | health, architecture, security, performance, dependencies | `offset=130 limit=82` |
| [SCN-04] Output & Messages | 209-275 | findings, warnings, recommendations | `offset=204 limit=76` |
| [SCN-05] Use Cases | 277-339 | examples, workflows, scenarios | `offset=272 limit=72` |
| [SCN-06] AI Operator Guide | 341-403 | triggers, when to scan, detection | `offset=336 limit=72` |
| [SCN-07] Integration | 405-470 | coherence, check, capture, lifecycle | `offset=400 limit=75` |
| [SCN-08] Quick Reference | 472-545 | cheatsheet, one-liners | `offset=467 limit=83` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[SCN-" manual/scan.md    # Find all sections
grep -n "SCN-06" manual/scan.md     # Find AI Operator Guide
```

---

## [SCN-01] Intent

`babel scan` performs **context-aware technical analysis** of your project, identifying issues against the project's declared purpose and decisions.

### The Problem It Solves

| Without Scan | With Scan |
|--------------|-----------|
| Manual code review | Automated analysis |
| Miss architectural issues | Issues surfaced systematically |
| Generic linting | Context-aware findings |
| "What should I fix?" | Prioritized recommendations |

### Core Approach

Scan analyzes your project **against captured decisions and purpose**:

```
Scanning against: "Use Babel to build itself..."
Type: health

⚠ HC2/HC3 compliance risks with current automation decisions...
```

Findings are **contextualized** — not generic lint warnings, but issues relevant to YOUR project's intent.

### EAST Framework

Scan uses the **EAST Framework** [LT-VC] for standardized decision analysis:
- **E**valuate against purpose
- **A**nalyze constraints
- **S**urface conflicts
- **T**rack recommendations

### Types of Analysis

| Type | Focus |
|------|-------|
| `health` | Overall project health, HC compliance |
| `architecture` | Patterns, event-driven design, state machines |
| `security` | Credential handling, input validation |
| `performance` | Bottlenecks, caching, efficiency |
| `dependencies` | Outdated packages, conflicts |

---

## [SCN-02] Command Overview

```bash
babel scan [query] [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Optional** | `query` | Specific question to answer |
| **Type** | `--type` | Scan type: health, architecture, security, performance, dependencies |
| **Depth** | `--deep` | Run comprehensive analysis |
| **Output** | `-v`, `--verbose` | Show all findings including info items |

### Basic Scan

```bash
babel scan
```

Runs default health scan.

### Specific Type

```bash
babel scan --type architecture
babel scan --type security
babel scan --type performance
babel scan --type dependencies
```

### Deep Analysis

```bash
babel scan --deep
```

Runs comprehensive analysis across all areas.

### With Query

```bash
babel scan "Is our caching strategy correct?"
babel scan "Are there security vulnerabilities?"
```

### Verbose Output

```bash
babel scan --verbose
babel scan --type architecture -v
```

Shows all findings including info-level items.

---

## [SCN-03] Scan Types

### health (Default)

Checks overall project health and compliance:

```bash
babel scan --type health
```

**Checks for:**
- HC compliance (HC2, HC3)
- Constraint conflicts
- Decision alignment
- Purpose coherence

### architecture

Analyzes architectural patterns:

```bash
babel scan --type architecture
```

**Checks for:**
- Event-driven patterns
- State machine opportunities
- Workflow orchestration
- Cross-component consistency

### security

Security-focused analysis:

```bash
babel scan --type security
```

**Checks for:**
- Credential handling
- Input validation
- Authentication patterns
- API security

### performance

Performance bottleneck detection:

```bash
babel scan --type performance
```

**Checks for:**
- Caching effectiveness
- Query optimization
- Resource usage
- Efficiency patterns

### dependencies

Dependency health check:

```bash
babel scan --type dependencies
```

**Checks for:**
- Outdated packages
- Version conflicts
- Security vulnerabilities
- Unused dependencies

---

## [SCN-04] Output & Messages

### Standard Output

```bash
babel scan --type health
```

```
Scanning against: "Use Babel to build itself, enabling testing..."
Type: health

⚠ HC2/HC3 compliance risks with current automation decisions need attention

1. ⚠ Solo Project Cannot Meet 2-Endorsement Requirement
   The constraint 'Solo projects cannot reach 2-endorsement threshold'
   directly conflicts with HC2 compliance requirement...
   → Implement a documented exception process for solo projects

2. ⚠ Offline-First Compliance vs LLM Synthesis
   The decision to 'Use LLM synthesis for why command functionality'
   may conflict with HC3's offline-first requirement...
   → Implement a local fallback for the 'why' command

Run `babel scan --deep` for comprehensive analysis

-> Next: babel capture "..." --batch  (Capture findings)
```

### Severity Levels

| Symbol | Level | Meaning |
|--------|-------|---------|
| `⚠` | Warning | Needs attention |
| `ℹ` | Info | Informational (verbose only) |
| `✗` | Critical | Immediate action needed |
| `✓` | Pass | Check passed |

### Verbose Output

```bash
babel scan --type architecture --verbose
```

Shows additional info items hidden by default.

### Deep Scan

```bash
babel scan --deep
```

```
Comprehensive Scan
==================
Running: health, architecture, security, performance, dependencies

[Health] 3 findings...
[Architecture] 2 findings...
[Security] 1 finding...
[Performance] 0 findings
[Dependencies] 2 findings...

Total: 8 findings (3 warnings, 5 info)
```

---

## [SCN-05] Use Cases

### Use Case 1: Quick Health Check

```bash
babel scan
# Default health scan
```

### Use Case 2: Architecture Review

```bash
babel scan --type architecture
# Check patterns and structure
```

### Use Case 3: Security Audit

```bash
babel scan --type security
# Security-focused analysis
```

### Use Case 4: Comprehensive Analysis

```bash
babel scan --deep
# Full analysis across all types
```

### Use Case 5: Specific Question

```bash
babel scan "Is our caching strategy aligned with performance goals?"
```

### Use Case 6: Pre-Review Check

Before major changes:

```bash
babel scan --type health
babel scan --type architecture
# Address findings before proceeding
```

### Use Case 7: Capture Findings

```bash
babel scan --type security
# Review findings, then capture relevant ones:
babel capture "Security scan revealed: need input validation on API endpoints" --batch
```

### Use Case 8: Periodic Maintenance

```bash
# Weekly scan routine
babel scan --deep --verbose > scan-report.txt
babel capture "Weekly scan: 3 warnings, 5 info items" --batch
```

---

## [SCN-06] AI Operator Guide

### When AI Should Suggest Scan

| Trigger | AI Action |
|---------|-----------|
| User asks "is this healthy?" | `babel scan --type health` |
| Before major refactoring | `babel scan --type architecture` |
| Security concerns mentioned | `babel scan --type security` |
| Performance questions | `babel scan --type performance` |
| "What should I fix?" | `babel scan --deep` |

### When NOT to Scan

| Context | Reason |
|---------|--------|
| Simple file edits | Overhead not justified |
| Already scanned recently | Avoid redundant analysis |
| No decisions captured | Scan needs context to be useful |

### After Scan

When scan reveals issues:

```bash
# Option 1: Capture as finding
babel capture "Scan revealed: [issue description]" --batch

# Option 2: Create question for research
babel question "How to address [scan finding]?" --batch

# Option 3: Challenge existing decision
babel challenge <id> "Scan shows conflict with this approach"
```

### Context Compression Survival

After compression, remember:

1. **Scan is context-aware** — uses project purpose/decisions
2. **Types focus analysis** — use specific types for targeted checks
3. **Deep is comprehensive** — use for thorough review

### AI-Safe Command

`babel scan` is **non-interactive** — safe for AI operators:

```bash
babel scan                     # Quick health check
babel scan --type security     # Focused analysis
babel scan --deep              # Comprehensive
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "Is this project healthy?" | `babel scan --type health` |
| "Check the architecture" | `babel scan --type architecture` |
| "Any security issues?" | `babel scan --type security` |
| "Full analysis please" | `babel scan --deep --verbose` |

---

## [SCN-07] Integration

### With coherence

```bash
# Complementary checks
babel coherence   # Semantic alignment
babel scan        # Technical analysis
```

### With check

```bash
# Structural + technical
babel check       # Integrity verification
babel scan        # Technical analysis
```

### With capture

```bash
# Capture important findings
babel scan --type security
# Review output...
babel capture "Security scan: need to address credential handling" --batch
```

### With challenge

```bash
# Scan may reveal decision conflicts
babel scan --type architecture
# If finding conflicts with decision:
babel challenge <id> "Architecture scan shows pattern mismatch"
```

### With question

```bash
# Uncertain about finding resolution
babel scan --type performance
babel question "How to optimize caching based on scan findings?" --batch
```

### Lifecycle Position

```
check (integrity)
    ↓
scan ←── YOU ARE HERE (technical analysis)
    ↓
coherence (semantic alignment)
    ↓
capture/challenge (act on findings)
```

### Maintenance Flow

```
1. check     # Structural integrity
2. scan      # Technical analysis
3. coherence # Semantic alignment
4. tensions  # Open conflicts
```

---

## [SCN-08] Quick Reference

### Basic Commands

```bash
# Quick health check
babel scan

# Specific type
babel scan --type health
babel scan --type architecture
babel scan --type security
babel scan --type performance
babel scan --type dependencies

# Deep analysis
babel scan --deep

# Verbose output
babel scan --verbose
babel scan --type architecture -v

# Specific question
babel scan "Is caching strategy correct?"
```

### Scan Types

| Type | Focus |
|------|-------|
| `health` | HC compliance, constraints, alignment |
| `architecture` | Patterns, workflows, state machines |
| `security` | Credentials, validation, auth |
| `performance` | Caching, queries, efficiency |
| `dependencies` | Packages, versions, conflicts |

### Output Symbols

| Symbol | Meaning |
|--------|---------|
| `⚠` | Warning - needs attention |
| `ℹ` | Info - informational |
| `✗` | Critical - immediate action |
| `✓` | Pass - check passed |

### Workflow

```bash
# Periodic health check
babel scan

# Address findings
babel capture "Scan finding: ..." --batch
# or
babel challenge <id> "Scan revealed conflict"
# or
babel question "How to address scan finding?" --batch
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `check` | Structural integrity |
| `coherence` | Semantic alignment |
| `capture` | Record findings |
| `challenge` | Act on conflicts |

### Scan vs Check vs Coherence

| Command | Focus |
|---------|-------|
| `check` | Data integrity, file structure |
| `scan` | Technical patterns, compliance |
| `coherence` | Semantic alignment with purpose |

### When to Use Each

| Situation | Command |
|-----------|---------|
| "Is data valid?" | `babel check` |
| "Is code healthy?" | `babel scan` |
| "Is project aligned?" | `babel coherence` |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~510
Last updated: 2026-01-24
=============================================================================
-->
