# babel capture — Preserve Decisions and Reasoning

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --spec section, read offset=95 limit=45
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [CAP-01] Intent | 37-69 | purpose, why capture, REMEMBER flow | `offset=32 limit=42` |
| [CAP-02] Command Overview | 70-97 | all parameters, quick table, syntax | `offset=65 limit=37` |
| [CAP-03] --batch | 98-136 | queue, review, AI-safe, non-interactive | `offset=93 limit=48` |
| [CAP-04] --spec | 137-191 | specification, need, implementation plan | `offset=132 limit=64` |
| [CAP-05] --share | 192-225 | scope, local, team, git-tracked | `offset=187 limit=43` |
| [CAP-06] --domain | 226-259 | expertise, P3, attribution, security | `offset=221 limit=43` |
| [CAP-07] --uncertain | 260-293 | provisional, P10, ambiguity, reason | `offset=255 limit=43` |
| [CAP-08] --raw | 294-321 | skip extraction, fast, no LLM | `offset=289 limit=37` |
| [CAP-09] Use Cases | 322-398 | examples, scenarios, workflows | `offset=317 limit=86` |
| [CAP-10] AI Operator Guide | 399-445 | compression, triggers, when to capture | `offset=394 limit=56` |
| [CAP-11] Integration | 446-493 | review, link, why, lifecycle | `offset=441 limit=57` |
| [CAP-12] Quick Reference | 494-551 | cheatsheet, one-liners | `offset=489 limit=67` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[CAP-" .babel/manual/capture.md    # Find all sections
grep -n "CAP-04" .babel/manual/capture.md     # Find --spec section
```

---

## [CAP-01] Intent

`babel capture` is the **REMEMBER** command — it preserves decisions, reasoning, and constraints so they survive context compression and team turnover.

### The Problem It Solves

| Without Capture | With Capture |
|-----------------|--------------|
| Decisions exist only in chat | Decisions persist in graph |
| AI forgets after session ends | `babel why` retrieves reasoning |
| Team members repeat mistakes | Constraints prevent violations |
| "Why did we do X?" unanswered | Captured reasoning answers |

### Core Principle

**Capture WHAT + WHY, not just WHAT.**

```
BAD:  "Using SQLite"
GOOD: "Using SQLite for local storage because users need offline access and data stays under 100MB"
```

### When to Capture

Capture when:
- User makes a decision
- User states a constraint
- User explains reasoning
- Implementation approach is chosen
- Something is explicitly rejected

---

## [CAP-02] Command Overview

```bash
babel capture "text" [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Required** | `"text"` | What to capture (decision, reasoning, constraint) |
| **Workflow** | `--batch`, `-b` | Queue for review (mandatory for AI) |
| | `--spec <id>` | Add specification to existing need |
| **Scope** | `--share`, `-s` | Share with team (default: local) |
| **Attribution** | `--domain`, `-d` | Expertise domain (P3 compliance) |
| **Uncertainty** | `--uncertain`, `-u` | Mark as provisional (P10) |
| | `--uncertainty-reason` | Why it's uncertain |
| **Processing** | `--raw` | Skip LLM extraction |

### Output Indicators

| Symbol | Meaning |
|--------|---------|
| `○` | Local scope (git-ignored) |
| `●` | Shared scope (git-tracked) |
| `◑ UNCERTAIN` | Provisional capture |
| `[domain]` | Expertise attribution |

---

## [CAP-03] --batch

**Purpose**: Queue capture for user review instead of immediate confirmation.

**Why mandatory for AI**: Interactive prompts cause EOF errors. `--batch` is non-interactive.

```bash
# AI-SAFE: Queue for later review
babel capture "decision text" --batch

# WRONG: Will hang waiting for input
babel capture "decision text"
```

**Workflow**:
```
AI captures → Queued in review → User runs babel review → Accepted/Rejected
```

**Output**:
```
Captured (○ local) [auto: reliability].
  Share with: babel share XY-AB
◌ Analyzing...● Done

I found 1 potential artifact(s):
--- 1. DECISION ---
  "Using Redis for caching"
  Why: Explicitly stated...

queued for review

Queued 1 proposal(s). Review with: babel review
```

**Key point**: Proposals stay queued until user runs `babel review --accept <id>` or `--accept-all`.

---

## [CAP-04] --spec

**Purpose**: Add implementation specification to an existing need or decision.

**Why it matters**: Needs answer "why do we want this?" — specs answer "how do we intend to achieve it?"

```bash
# Step 1: Capture the need
babel capture "Need: Add caching to reduce API calls" --batch
# → [abc12345]

# Step 2: After user validates, add specification
babel capture --spec abc12345 "OBJECTIVE: Reduce API response time
ADD:
- Redis cache layer
- Cache invalidation on write
MODIFY:
- api.py to check cache first
REMOVE:
- None
PRESERVE:
- Existing API contracts
RELATED:
- src/api.py
- src/cache.py" --batch
```

**Specification format**:
```
OBJECTIVE: What this achieves
ADD: What must be introduced
MODIFY: What existing code changes
REMOVE: What to eliminate
PRESERVE: What must NOT change
RELATED: Files involved
```

**Output**:
```
Specification added to [abc12345] (● shared).
  OBJECTIVE: Reduce API response time...
  ADD: 2 item(s)
  MODIFY: 1 item(s)
  REMOVE: 1 item(s)
  PRESERVE: 1 item(s)
  RELATED: 2 file(s)
```

**Why specs matter for AI**:
- Implementation plans evaporate on context compression
- Specs captured in Babel persist across sessions
- `babel why "topic"` retrieves specs when needed

---

## [CAP-05] --share

**Purpose**: Control whether capture is local-only or shared with team.

**Default**: Local (git-ignored, personal working notes)

```bash
# Local capture (default)
babel capture "exploring this approach" --batch
# → Captured (○ local)

# Shared capture (team-visible)
babel capture "team decision on API design" --share --batch
# → Captured (● shared)

# Promote local to shared later
babel share XY-AB
```

**Scope comparison**:

| Scope | Symbol | Git | Use Case |
|-------|--------|-----|----------|
| Local | `○` | Ignored | Personal notes, experiments |
| Shared | `●` | Tracked | Team decisions, constraints |

**When to share**:
- Team-wide decisions
- Architectural constraints
- Standards and conventions
- After validating local experiments

---

## [CAP-06] --domain

**Purpose**: Attribute capture to expertise domain (P3: Expertise Preservation).

**Why it matters**: Decisions need domain context for proper cross-referencing.

```bash
# Security-related capture
babel capture "Input must be sanitized before DB query" --domain security --batch

# Performance-related capture
babel capture "Cache TTL set to 5 minutes based on load testing" --domain performance --batch

# Architecture-related capture
babel capture "Using event sourcing for audit trail" --domain architecture --batch
```

**Common domains**:
- `security` — Input validation, auth, encryption
- `performance` — Caching, optimization, load
- `architecture` — Patterns, structure, design
- `reliability` — Error handling, recovery
- `usability` — UX, API design

**Output**:
```
Captured (○ local) [security].
  Share with: babel share ME-QD
```

**Auto-detection**: If `--domain` is omitted, Babel auto-detects from text (shown as `[auto: domain]`).

---

## [CAP-07] --uncertain

**Purpose**: Mark capture as provisional (P10: Holding Ambiguity).

**When to use**: Decision made but not fully validated, exploring options, tentative approach.

```bash
# Uncertain capture with reason
babel capture "Thinking GraphQL might be better than REST" \
  --uncertain \
  --uncertainty-reason "Need to validate with mobile team" \
  --batch
```

**Output**:
```
Captured (○ local) [auto: architecture] ◑ UNCERTAIN.
  Uncertainty: Need to validate with mobile team
  Share with: babel share EB-MZ
```

**Why uncertainty matters**:
- Prevents treating provisional decisions as final
- Surfaces for review in `babel questions`
- Can be resolved later when clarity emerges

**Resolution**:
```bash
# When decision becomes certain
babel resolve-question <id> "Validated: GraphQL confirmed by mobile team"
```

---

## [CAP-08] --raw

**Purpose**: Skip LLM extraction, save capture directly.

**When to use**:
- Quick notes that don't need artifact extraction
- API key not available
- Speed priority over structure

```bash
# Skip extraction (fast)
babel capture "quick note about config" --raw

# Normal (with extraction)
babel capture "decision with reasoning" --batch
```

**Output comparison**:

| Mode | Output |
|------|--------|
| Normal | `◌ Analyzing...● Done` + proposals |
| `--raw` | Immediate save, no analysis |

**Trade-off**: Raw captures won't generate structured proposals (decisions, constraints, etc.) but are still searchable via `babel why`.

---

## [CAP-09] Use Cases

### Use Case 1: Capturing a Decision

When user states a decision:

```bash
babel capture "Using SQLite instead of PostgreSQL because users need offline access and data volume stays under 100MB" --batch
```

**Key**: Include WHAT (SQLite) + WHY (offline access, data volume).

### Use Case 2: Capturing a Constraint

When user states a rule that must be followed:

```bash
babel capture "CONSTRAINT: API responses must complete within 200ms. Business requirement from SLA." --batch
```

### Use Case 3: Capturing After Implementation Planning

After discussing implementation approach:

```bash
# First: Capture the need
babel capture "Need: Add rate limiting to protect API" --batch
# → [abc123]

# After planning: Add specification
babel capture --spec abc123 "OBJECTIVE: Prevent API abuse
ADD:
- Rate limiter middleware
- Redis counter per IP
MODIFY:
- app.py to include middleware
REMOVE:
- None
PRESERVE:
- Existing auth middleware order
RELATED:
- src/middleware/
- src/app.py" --batch
```

### Use Case 4: Capturing Rejected Alternative

Why NOT doing something is valuable:

```bash
babel capture "REJECTED: MongoDB for user data. Reason: Team expertise is in SQL, MongoDB would require training. SQLite chosen instead." --batch
```

### Use Case 5: Uncertain Decision

When exploring but not committed:

```bash
babel capture "Considering microservices but unsure about operational complexity" \
  --uncertain \
  --uncertainty-reason "Need ops team input" \
  --batch
```

### Use Case 6: Domain-Specific Capture

Security-sensitive decision:

```bash
babel capture "All user passwords must use bcrypt with cost factor 12" \
  --domain security \
  --share \
  --batch
```

---

## [CAP-10] AI Operator Guide

### When to Capture (Detection Triggers)

| User Says | Capture Type |
|-----------|--------------|
| "Let's use X because..." | Decision |
| "We must always/never..." | Constraint |
| "I'm not sure if..." | Question (use `babel question`) |
| "We decided against X because..." | Rejected alternative |
| "The requirement is..." | Requirement |

### Capture Format Template

```
[WHAT] was decided/constrained
[WHY] the reasoning
[CONTEXT] if relevant constraints apply
```

### After Context Compression

When your context is compressed:

1. You lose captured decisions
2. Use `babel why "topic"` to retrieve
3. Captures survive compression — your memory doesn't

### Non-Interactive Pattern (Mandatory)

```bash
# ALWAYS use --batch for AI operations
babel capture "text" --batch

# NEVER omit --batch (causes EOF error)
babel capture "text"  # WRONG
```

### Periodic Reminders

Remind user periodically:
```
"You have pending proposals. Review with: babel review"
```

---

## [CAP-11] Integration

### Command Lifecycle

```
capture --batch → review --accept → link → endorse → evidence-decision
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `babel review` | Review queued captures |
| `babel link` | Connect accepted artifacts to purpose |
| `babel why` | Retrieve captured reasoning |
| `babel share` | Promote local to shared |
| `babel question` | Capture uncertainty (alternative to --uncertain) |

### Capture → Review → Link Flow

```bash
# 1. AI captures
babel capture "decision" --batch

# 2. User reviews
babel review --accept XY-AB

# 3. AI links to purpose
babel link XY-AB
```

### Integration with Specs

```bash
# Capture need
babel capture "Need: Feature X" --batch
# → [need-id]

# Add specification
babel capture --spec need-id "OBJECTIVE: ..." --batch

# Query later
babel why "Feature X"
# → Returns need + spec
```

---

## [CAP-12] Quick Reference

```bash
# Basic capture (AI-safe)
babel capture "text" --batch

# With specification
babel capture --spec <id> "OBJECTIVE:..." --batch

# Shared with team
babel capture "text" --share --batch

# With domain
babel capture "text" --domain security --batch

# Uncertain
babel capture "text" --uncertain --uncertainty-reason "why" --batch

# Skip extraction
babel capture "text" --raw

# Promote local to shared
babel share <id>
```

### Capture Checklist

- [ ] WHAT + WHY included?
- [ ] `--batch` flag present? (mandatory for AI)
- [ ] Domain relevant? (use `--domain`)
- [ ] Uncertain? (use `--uncertain`)
- [ ] Team decision? (use `--share`)

### Common Patterns

```bash
# Decision with reasoning
babel capture "Using X because Y" --batch

# Constraint
babel capture "CONSTRAINT: Must do X" --batch

# Rejected alternative
babel capture "REJECTED: X because Y" --batch

# Specification to need
babel capture --spec <id> "OBJECTIVE:..." --batch
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~551
Last updated: 2026-01-24
=============================================================================
-->
