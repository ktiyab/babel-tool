# babel questions — Surface Unknowns and Uncertainties (ORIENT Flow)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For question command section, read offset=85 limit=45
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [QUE-01] Intent | 32-60 | purpose, ORIENT flow, unknowns, P10 | `offset=27 limit=38` |
| [QUE-02] Command Overview | 61-99 | syntax, parameters, output | `offset=56 limit=48` |
| [QUE-03] Creating Questions | 100-136 | question command, capture uncertainty | `offset=95 limit=46` |
| [QUE-04] Resolving Questions | 137-171 | resolve-question, answer | `offset=132 limit=44` |
| [QUE-05] Use Cases | 172-221 | examples, scenarios, workflows | `offset=167 limit=59` |
| [QUE-06] AI Operator Guide | 222-266 | session start, detection, uncertain | `offset=217 limit=54` |
| [QUE-07] Quick Reference | 267-307 | cheatsheet, patterns | `offset=262 limit=50` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[QUE-" .babel/manual/questions.md    # Find all sections
grep -n "QUE-03" .babel/manual/questions.md     # Find creating questions section
```

---

## [QUE-01] Intent

`babel questions` surfaces **acknowledged unknowns** — things the team explicitly doesn't know yet.

### The Problem It Solves

| Without Questions | With Questions |
|-------------------|----------------|
| Unknowns hidden | Unknowns visible |
| Premature decisions | Explicit uncertainty |
| Assumptions unstated | Assumptions surfaced |
| "We should have asked" | Questions recorded |

### Core Principle (P10)

**Holding ambiguity explicitly.**

Questions acknowledge:
- What we don't know yet
- What needs research
- What requires user/stakeholder input
- What can't be decided now

### When to Use

**MANDATORY**: Run at every session start alongside `babel status` and `babel tensions`.

---

## [QUE-02] Command Overview

```bash
babel questions [options]
```

| Parameter | Purpose |
|-----------|---------|
| `--verbose`, `-v` | Show full details |
| `--full` | Show complete content without truncation |
| `--format` | Output format (json, table, list) |

### Output When No Questions

```
No open questions.
(This is fine -- or you haven't recorded your unknowns yet)

Resolved: 9 question(s) answered

-> Next: babel status  (All questions resolved)
```

### Output When Questions Exist

```
Open questions (2):

  [Q1] Should we use REST or GraphQL for the API?
       Created: 2026-01-20

  [Q2] What's the maximum acceptable response time?
       Created: 2026-01-22

-> Next: babel resolve-question <id>  (When answered)
```

---

## [QUE-03] Creating Questions

Use `babel question` (singular) to create a question.

```bash
babel question "What authentication method should we use?" --batch
```

**Output**:
```
Captured question (○ local):
  "What authentication method should we use?"

queued for review

-> Next: babel review  (Accept to activate)
```

### When to Create Questions

| User Says | Create Question? |
|-----------|------------------|
| "I'm not sure if..." | Yes |
| "We need to figure out..." | Yes |
| "Depends on what X decides" | Yes |
| "Maybe we should..." | Consider |

### Alternative: --uncertain Flag

For provisional decisions that might change:

```bash
babel capture "Using REST for now" --uncertain --uncertainty-reason "Need to validate with mobile team" --batch
```

---

## [QUE-04] Resolving Questions

When a question is answered, use `babel resolve-question`.

```bash
babel resolve-question Q1 "Decided: Use OAuth 2.0 with JWT tokens"
```

**Output**:
```
Resolved question [Q1]:
  Question: "What authentication method should we use?"
  Answer: "Decided: Use OAuth 2.0 with JWT tokens"

-> Next: babel capture  (Capture the decision)
```

### After Resolution

Capture the decision that emerged:

```bash
babel capture "Using OAuth 2.0 with JWT tokens for authentication. Chosen because mobile team has existing OAuth implementation." --batch
```

### Resolution Without Answer

If question becomes irrelevant:

```bash
babel resolve-question Q2 "No longer relevant - project scope changed"
```

---

## [QUE-05] Use Cases

### Use Case 1: Session Start (MANDATORY)

```bash
babel status
babel tensions
babel questions
```

Know your unknowns before working.

### Use Case 2: Capturing Uncertainty

```bash
# User says: "I'm not sure whether to use SQL or NoSQL"
babel question "Should we use SQL or NoSQL for user data?" --batch
```

### Use Case 3: Resolving After Discussion

```bash
# After stakeholder meeting
babel resolve-question Q1 "PostgreSQL chosen - team expertise in SQL"

# Capture the decision
babel capture "Using PostgreSQL for user data. Team has strong SQL expertise and we need ACID compliance." --batch
```

### Use Case 4: Questions During Planning

```bash
# During architecture discussion
babel question "How will we handle offline sync?" --batch
babel question "What's our backup strategy?" --batch
babel question "Who approves API changes?" --batch
```

### Use Case 5: Converting Uncertain Capture

```bash
# Earlier captured as uncertain
babel capture "Maybe use Redis" --uncertain --batch

# Later, question resolved
babel resolve-question <id> "Confirmed: Redis for caching"
```

---

## [QUE-06] AI Operator Guide

### Session Start (MANDATORY)

```bash
# Run these three at every session start
babel status
babel tensions
babel questions
```

### Detection Triggers

| User Says | Action |
|-----------|--------|
| "I'm not sure..." | `babel question "..." --batch` |
| "We need to decide..." | `babel question "..." --batch` |
| "I don't know if..." | `babel question "..." --batch` |
| "Let me think about..." | Consider capturing question |

### When NOT to Capture

Don't capture as question if:
- User is just thinking aloud
- Answer is immediately available
- It's a rhetorical question

### Surfacing to User

If open questions exist:
```
"There are N open questions that may affect this work:
- Should we use REST or GraphQL?
Consider resolving before proceeding."
```

### Uncertainty vs Question

| Use | When |
|-----|------|
| `babel question` | True unknown needing research |
| `capture --uncertain` | Tentative decision that might change |

---

## [QUE-07] Quick Reference

```bash
# Check questions (session start)
babel questions

# Full details
babel questions --full
babel questions --verbose

# JSON output
babel questions --format json

# Create question
babel question "What we don't know?" --batch

# Resolve question
babel resolve-question <id> "What we decided/learned"
```

### Session Start Sequence

```bash
babel status && babel tensions && babel questions
```

### Question Lifecycle

```
question --batch → [review --accept] → [research/discuss] → resolve-question → capture decision
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~295
Last updated: 2026-01-24
=============================================================================
-->
