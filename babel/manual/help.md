# babel help — Comprehensive Command Reference

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=117 limit=55
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [HLP-01] Intent | 31-59 | purpose, reference, all commands | `offset=26 limit=38` |
| [HLP-02] Command Overview | 61-105 | syntax, output format | `offset=56 limit=54` |
| [HLP-03] Help Categories | 107-174 | getting started, capturing, querying, coherence | `offset=102 limit=77` |
| [HLP-04] Use Cases | 176-225 | examples, when to use help | `offset=171 limit=59` |
| [HLP-05] AI Operator Guide | 227-270 | triggers, help vs manual | `offset=222 limit=53` |
| [HLP-06] Quick Reference | 272-330 | cheatsheet, navigation | `offset=267 limit=68` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[HLP-" manual/help.md    # Find all sections
grep -n "HLP-05" manual/help.md     # Find AI Operator Guide
```

---

## [HLP-01] Intent

`babel help` displays **comprehensive command reference** for all Babel commands.

### The Problem It Solves

| Without Help | With Help |
|--------------|-----------|
| Read individual --help | One comprehensive reference |
| Miss related commands | See commands by category |
| Forget command exists | Full command list |
| No quick examples | Examples for each command |

### When to Use

| Situation | Action |
|-----------|--------|
| "What commands exist?" | `babel help` |
| "How do I do X?" | `babel help`, then find section |
| New to Babel | Start with `babel help` |

### Help vs --help

| Command | Shows |
|---------|-------|
| `babel help` | All commands, organized by category |
| `babel <cmd> --help` | Detailed options for one command |

---

## [HLP-02] Command Overview

```bash
babel help
```

No options — displays full reference.

### Output Structure

```
Babel -- Intent Preservation Tool
================================

GETTING STARTED
---------------
  babel init "purpose"    Initialize project...

CAPTURING REASONING
-------------------
  babel capture "text"    Capture a thought...

QUERYING
--------
  babel why "topic"       Trace reasoning...

COHERENCE
---------
  babel coherence         Check alignment...
```

### Categories Covered

1. Getting Started
2. Capturing Reasoning
3. Querying
4. Coherence
5. Validation
6. Challenges
7. Questions
8. Maintenance
9. Preferences
10. Git Integration

---

## [HLP-03] Help Categories

### Getting Started

```
babel init "purpose"      Initialize project
babel status              Show project overview
babel check               Verify integrity
```

### Capturing Reasoning

```
babel capture "text"      Capture thought/decision
babel capture --share     Capture and share
babel share <id>          Promote local to shared
```

### Querying

```
babel why "topic"         Trace reasoning
babel status              Project overview
babel history             Recent activity
babel list                List artifacts
```

### Coherence

```
babel coherence           Check alignment
babel scan                Technical analysis
```

### Validation (P5)

```
babel validation          Show validation status
babel endorse <id>        Add consensus
babel evidence-decision   Add evidence
```

### Challenges (P4)

```
babel challenge <id>      Challenge decision
babel evidence <id>       Add evidence
babel resolve <id>        Resolve challenge
babel tensions            Show open tensions
```

### Questions (P6)

```
babel question "text"     Raise question
babel resolve-question    Resolve question
babel questions           Show open questions
```

### Maintenance

```
babel sync                Sync after git pull
babel deprecate <id>      Mark obsolete
babel check --repair      Fix issues
```

---

## [HLP-04] Use Cases

### Use Case 1: New User Orientation

```bash
babel help
# Read through all categories
# Understand command landscape
```

### Use Case 2: Find Related Commands

```bash
babel help
# Search for "validation" or "coherence"
# Find related commands
```

### Use Case 3: Quick Reference

```bash
babel help | grep capture
# Find capture-related commands
```

### Use Case 4: Category Deep Dive

```bash
babel help
# Find "CHALLENGES" section
# See challenge/evidence/resolve flow
```

### Use Case 5: Before Starting Project

```bash
babel help
# Review "GETTING STARTED"
# Understand init flow
```

### Use Case 6: Teaching Babel

```bash
babel help
# Walk through each category
# Show command examples
```

---

## [HLP-05] AI Operator Guide

### When AI Should Use Help

| Trigger | AI Action |
|---------|-----------|
| User asks "what commands?" | `babel help` |
| Looking for command | `babel help \| grep "keyword"` |
| Explaining workflow | Reference help categories |

### Help vs Manual

| Resource | When to Use |
|----------|-------------|
| `babel help` | Quick command list |
| `babel <cmd> --help` | Specific command options |
| `manual/<cmd>.md` | Full documentation |

### Context Compression Survival

After compression, remember:

1. **Help is quick reference** — not detailed docs
2. **Categories organize commands** — find by workflow
3. **Examples included** — for quick understanding

### AI-Safe Command

`babel help` is **non-interactive** — safe for AI operators:

```bash
babel help              # Full reference
babel help | grep X     # Filter for topic
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "What commands does Babel have?" | `babel help` |
| "How do I do X in Babel?" | `babel help`, find section |
| "Show me all options" | `babel help` for overview |

---

## [HLP-06] Quick Reference

### Basic Command

```bash
# Show all commands
babel help

# Filter for topic
babel help | grep capture
babel help | grep coherence
```

### Navigation

```
GETTING STARTED     → init, status, check
CAPTURING           → capture, share
QUERYING            → why, status, history, list
COHERENCE           → coherence, scan
VALIDATION          → validation, endorse, evidence-decision
CHALLENGES          → challenge, evidence, resolve, tensions
QUESTIONS           → question, resolve-question, questions
MAINTENANCE         → sync, deprecate, check
```

### Help Resources

| Resource | Command | Detail Level |
|----------|---------|--------------|
| All commands | `babel help` | Overview |
| One command | `babel <cmd> --help` | Options |
| Full docs | `manual/<cmd>.md` | Complete |
| Principles | `babel principles` | Framework |

### Related Commands

| Command | Relationship |
|---------|--------------|
| `--help` | Per-command options |
| `principles` | Framework philosophy |
| `status` | Current state |

### When to Use Each

| Need | Use |
|------|-----|
| "What commands exist?" | `babel help` |
| "What options for X?" | `babel X --help` |
| "Why does X work this way?" | `babel principles` |
| "Full X documentation" | `manual/X.md` |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~325
Last updated: 2026-01-24
=============================================================================
-->
