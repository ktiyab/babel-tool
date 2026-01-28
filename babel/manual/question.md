# babel question / resolve-question — Hold Ambiguity (P10)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=202 limit=75
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [QST-01] Intent | 33-87 | purpose, P10, uncertainty, ambiguity, hold | `offset=28 limit=64` |
| [QST-02] question Command | 89-146 | create question, batch, context, domain | `offset=84 limit=67` |
| [QST-03] resolve-question Command | 148-208 | answer, resolution, outcome | `offset=143 limit=70` |
| [QST-04] questions Command | 210-259 | list, open questions, overview | `offset=205 limit=59` |
| [QST-05] Use Cases | 261-337 | examples, scenarios, workflows | `offset=256 limit=86` |
| [QST-06] AI Operator Guide | 339-416 | triggers, detection, when to question | `offset=334 limit=87` |
| [QST-07] Integration | 418-492 | capture, why, tensions, lifecycle | `offset=413 limit=84` |
| [QST-08] Quick Reference | 494-592 | cheatsheet, one-liners | `offset=489 limit=108` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[QST-" manual/question.md    # Find all sections
grep -n "QST-06" manual/question.md     # Find AI Operator Guide
```

---

## [QST-01] Intent

`babel question` captures **acknowledged unknowns** — things you explicitly don't know yet.

### The Problem It Solves

| Without Questions | With Questions |
|-------------------|----------------|
| Unknowns forgotten | Unknowns tracked explicitly |
| Premature decisions | Decisions deferred until clarity |
| "We figured that out... somewhere" | Questions searchable in graph |
| Uncertainty hidden | Uncertainty surfaced in status |

### Core Principle (P10: Holding Ambiguity)

**Don't force decisions when uncertainty exists.**

```
WRONG:  User: "I'm not sure if we should use REST or GraphQL"
        AI: "Let's use REST because it's simpler"
        (Forced decision without evidence)

RIGHT:  User: "I'm not sure if we should use REST or GraphQL"
        AI: babel question "REST vs GraphQL for API" --batch
        (Captured uncertainty, decision deferred)
```

### Question vs Uncertain Capture

| Command | When to Use |
|---------|-------------|
| `babel question` | True unknown needing research |
| `capture --uncertain` | Tentative decision that might change |

```bash
# Question: We don't know the answer
babel question "What auth method should we use?" --batch

# Uncertain capture: We made a decision but might revise
babel capture "Using JWT for now" --uncertain --batch
```

### Question Lifecycle

```
question --batch
    ↓
[research/discussion/testing]
    ↓
resolve-question (when answered)
    ↓
capture (the resulting decision)
```

---

## [QST-02] question Command

**Purpose**: Create an open question to track uncertainty.

```bash
babel question "what we don't know" [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Required** | `content` | The question text |
| **Context** | `--context`, `-c` | Why this question matters |
| **Attribution** | `--domain`, `-d` | Related expertise domain |
| **Workflow** | `--batch`, `-b` | Queue for review (AI-safe) |

### Basic Question

```bash
babel question "Should we use REST or GraphQL?" --batch
```

**Output:**
```
Captured question (○ local):
  "Should we use REST or GraphQL?"

queued for review
```

### With Context

```bash
babel question "What authentication method?" \
  --context "Multiple options available, team has varying experience" \
  --batch
```

### With Domain

```bash
babel question "How to handle rate limiting?" \
  --domain security \
  --batch
```

### AI-Safe Mode

Always use `--batch` for AI operators:

```bash
# CORRECT - Non-interactive
babel question "What database to use?" --batch

# WRONG - May prompt for confirmation
babel question "What database to use?"
```

---

## [QST-03] resolve-question Command

**Purpose**: Close a question when it's been answered.

```bash
babel resolve-question <question_id> "resolution" [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Required** | `question_id` | ID (or prefix) of the question |
| **Required** | `resolution` | The answer or conclusion |
| **Outcome** | `--outcome` | How resolved: answered, dissolved, superseded |

### Outcomes

| Outcome | When to Use |
|---------|-------------|
| `answered` | Question was researched and answered (default) |
| `dissolved` | Question became irrelevant |
| `superseded` | A different question replaced this one |

### Resolve with Answer

```bash
babel resolve-question Q1 "Chose REST for simplicity and team familiarity"
```

**Output:**
```
Resolved question [Q1]:
  Question: "Should we use REST or GraphQL?"
  Resolution: "Chose REST for simplicity and team familiarity"
  Outcome: answered
```

### Resolve as Dissolved

```bash
babel resolve-question Q2 "Scope changed, no longer need this feature" \
  --outcome dissolved
```

### Resolve as Superseded

```bash
babel resolve-question Q3 "Replaced by more specific question about JWT vs OAuth" \
  --outcome superseded
```

### After Resolution — Capture the Decision

```bash
# Question resolved
babel resolve-question Q1 "Chose REST for simplicity"

# Capture the resulting decision
babel capture "Using REST API because team familiar, simpler caching" --batch
```

---

## [QST-04] questions Command

**Purpose**: List open (unresolved) questions.

```bash
babel questions
```

### Output — With Open Questions

```
Open Questions (P10: Hold Ambiguity):

  [Q1] Should we use REST or GraphQL?
       Context: Multiple options available
       Created: 2026-01-24

  [Q2] What authentication method?
       Domain: security
       Created: 2026-01-23

2 open question(s)

Resolved: 9 question(s) answered

-> Next: babel resolve-question <id> "answer"
```

### Output — No Open Questions

```
No open questions.
(This is fine -- or you haven't recorded your unknowns yet)

Resolved: 9 question(s) answered

-> Next: babel status  (All questions resolved)
```

### Session Start

Include in ORIENT phase:

```bash
babel status      # Purpose + health
babel tensions    # Open conflicts
babel questions   # ← Open unknowns
```

---

## [QST-05] Use Cases

### Use Case 1: Capture Uncertainty

User expresses uncertainty:

```bash
# User: "I'm not sure about the auth approach"
babel question "What authentication method should we use?" \
  --context "Multiple options: JWT, OAuth, API keys" \
  --batch
```

### Use Case 2: Resolve After Research

```bash
# After research and discussion
babel resolve-question Q1 "OAuth 2.0 - team has existing implementation"

# Capture the resulting decision
babel capture "Using OAuth 2.0 for authentication - existing team experience" --batch
```

### Use Case 3: Check Open Questions

```bash
babel questions
# Shows all open questions awaiting answers
```

### Use Case 4: Question Becomes Irrelevant

```bash
babel resolve-question Q1 "No longer relevant - scope changed" \
  --outcome dissolved
```

### Use Case 5: Question Replaced

```bash
babel resolve-question Q1 "Replaced by more specific questions" \
  --outcome superseded

# Create the more specific questions
babel question "JWT token lifetime?" --batch
babel question "Refresh token strategy?" --batch
```

### Use Case 6: Security Domain Question

```bash
babel question "How to handle credential storage?" \
  --domain security \
  --context "Need to store API keys for external services" \
  --batch
```

### Use Case 7: Full Workflow

```bash
# 1. Capture the uncertainty
babel question "Database choice for analytics" --batch

# 2. Research and discuss...
# ... time passes, investigation happens ...

# 3. Resolve when decided
babel resolve-question Q1 "PostgreSQL - good for OLAP queries, team knows it"

# 4. Capture the decision
babel capture "Using PostgreSQL for analytics. JSONB for flexible schemas, good aggregation performance." --batch

# 5. Link to purpose
babel link <id>
```

---

## [QST-06] AI Operator Guide

### Detection Triggers

When user says:

| User Statement | AI Action |
|----------------|-----------|
| "I'm not sure..." | `babel question "..." --batch` |
| "We need to figure out..." | `babel question "..." --batch` |
| "I don't know if..." | `babel question "..." --batch` |
| "Maybe we should... or maybe..." | `babel question "..." --batch` |
| "That's a good question" | `babel question "..." --batch` |

### When to Suggest Questions

| Context | AI Action |
|---------|-----------|
| Explicit uncertainty | Capture immediately |
| Multiple valid options | Ask if user wants to decide now or capture question |
| Missing information | Capture as question, research later |
| User defers decision | Capture to track |

### When NOT to Capture Question

| Context | Reason |
|---------|--------|
| User made decision | Use `capture`, not `question` |
| Rhetorical question | Not a real unknown |
| Already captured | Check `babel questions` first |

### Context Compression Survival

After compression, remember:

1. **Questions track unknowns** — not tentative decisions
2. **Always use --batch** — non-interactive for AI
3. **Resolve → Capture** — question resolution leads to decision capture

### AI-Safe Commands

Both commands have non-interactive modes:

```bash
# Non-interactive question capture
babel question "text" --batch

# Non-interactive resolution
babel resolve-question <id> "answer"
```

### Session Start Protocol

Include questions in ORIENT:

```bash
babel status      # Purpose + health
babel tensions    # Open conflicts
babel questions   # Open unknowns ← INCLUDE THIS
```

### Building Evidence Before Resolution

Don't resolve questions prematurely. Build evidence:

```bash
# Question exists
babel questions
# [Q1] What database to use?

# Gather evidence (P10: sufficient evidence before resolving)
# ... research, testing, discussion ...

# Then resolve with evidence
babel resolve-question Q1 "PostgreSQL - benchmarks show best for our query patterns"
```

---

## [QST-07] Integration

### With capture

```bash
# After resolving question, capture the decision
babel resolve-question Q1 "Chose REST"
babel capture "Using REST API - team familiarity, simple caching" --batch
```

### With capture --uncertain

```bash
# Question: We don't know at all
babel question "What framework?" --batch

# Uncertain capture: We chose but might change
babel capture "Trying FastAPI for now" --uncertain --batch
```

### With why

```bash
# Check if question already exists
babel why "database choice"
# If shows question: don't duplicate
# If shows decision: question already answered
```

### With tensions

```bash
# Questions and tensions are both uncertainties
babel tensions    # Conflicts (disagreements)
babel questions   # Unknowns (lack of information)
```

### With status

```bash
babel status
# Shows: Questions: 2 open, 9 resolved
```

### Lifecycle Position

```
uncertainty detected
    ↓
question --batch ←── YOU ARE HERE
    ↓
[research/discussion]
    ↓
resolve-question
    ↓
capture (resulting decision)
    ↓
link
```

### Full UNCERTAIN Flow

```
question --batch
    ↓
questions (review open)
    ↓
[gather evidence]
    ↓
resolve-question (with answer)
    ↓
capture (the decision)
```

---

## [QST-08] Quick Reference

### Basic Commands

```bash
# Create question
babel question "What we don't know" --batch

# With context
babel question "What we don't know" --context "why it matters" --batch

# With domain
babel question "What we don't know" --domain security --batch

# List open questions
babel questions

# Resolve question
babel resolve-question <id> "answer"

# Resolve with specific outcome
babel resolve-question <id> "answer" --outcome dissolved
```

### Resolution Outcomes

| Outcome | When |
|---------|------|
| `answered` | Research provided answer (default) |
| `dissolved` | Question no longer relevant |
| `superseded` | Replaced by different question |

### Question vs Uncertain

| Command | Meaning |
|---------|---------|
| `question` | We don't know the answer |
| `capture --uncertain` | We decided but might change |

### Detection Patterns

| User Says | Capture As |
|-----------|------------|
| "I'm not sure..." | Question |
| "We need to figure out..." | Question |
| "Let's try X for now" | Uncertain capture |
| "We decided to use X" | Regular capture |

### Full Workflow

```bash
# Capture uncertainty
babel question "API design" --batch

# Review pending
babel review --accept <id>

# Later, resolve
babel resolve-question <id> "REST with versioning"

# Capture resulting decision
babel capture "Using REST API with URL versioning" --batch
```

### Session Start

```bash
babel status
babel tensions
babel questions    # ← Check open unknowns
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `questions` | List open questions |
| `capture --uncertain` | Alternative for tentative decisions |
| `tensions` | Conflicts (vs unknowns) |
| `status` | Shows question counts |

### Symbols

| Symbol | Meaning |
|--------|---------|
| `○` | Local question |
| `●` | Shared question |
| Open | Not yet resolved |
| Resolved | Has answer |

### Error Handling

| Error | Solution |
|-------|----------|
| Question not found | Use prefix matching or check ID |
| Already resolved | Cannot re-resolve |
| No open questions | Normal state — or capture more unknowns |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~515
Last updated: 2026-01-24
=============================================================================
-->
