# babel review — Human Authority Over Proposals (HC2)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --accept section, read offset=115 limit=50
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [REV-01] Intent | 36-65 | purpose, HC2, human authority, VALIDATE flow | `offset=31 limit=39` |
| [REV-02] Command Overview | 66-96 | syntax, parameters, flags | `offset=61 limit=40` |
| [REV-03] --list | 97-130 | list proposals, AI-safe, pending | `offset=92 limit=43` |
| [REV-04] --accept | 131-172 | accept proposal, accept-all, specific | `offset=126 limit=51` |
| [REV-05] --reject | 173-203 | reject proposal, reason, learning | `offset=168 limit=40` |
| [REV-06] --rejected | 204-235 | rejected history, P8, learn from | `offset=199 limit=41` |
| [REV-07] Theme Review | 236-279 | synthesize, by-theme, bulk review | `offset=231 limit=53` |
| [REV-08] Use Cases | 280-338 | examples, scenarios, workflows | `offset=275 limit=68` |
| [REV-09] AI Operator Guide | 339-385 | mandatory flags, reminder, non-interactive | `offset=334 limit=56` |
| [REV-10] Integration | 386-420 | capture, link, lifecycle | `offset=381 limit=44` |
| [REV-11] Quick Reference | 421-476 | cheatsheet, patterns | `offset=416 limit=65` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[REV-" .babel/manual/review.md    # Find all sections
grep -n "REV-04" .babel/manual/review.md     # Find --accept section
```

---

## [REV-01] Intent

`babel review` is the **VALIDATE** command — it enforces human authority (HC2) over what enters the knowledge graph.

### The Problem It Solves

| Without Review | With Review |
|----------------|-------------|
| AI auto-captures decisions | Human validates before entry |
| Noise enters knowledge graph | Quality control via review |
| HC2 violated | Human authority maintained |
| No audit trail | Rejections tracked (P8) |

### Core Principle

**Humans decide what enters the system.**

```
AI captures → Proposal queued → Human reviews → Accepted/Rejected
```

### HC2: Human Authority

This command enforces HC2 (Human Authority Over All Changes):
- AI proposes using `--batch`
- Human accepts/rejects using `review`
- Nothing auto-enters the knowledge graph

---

## [REV-02] Command Overview

```bash
babel review [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Display** | `--list` | List proposals without prompting (AI-safe) |
| | `--format` | Output format (json, table, list) |
| **Accept** | `--accept <id>` | Accept specific proposal |
| | `--accept-all` | Accept all pending proposals |
| **Reject** | `--reject <id>` | Reject specific proposal |
| | `--reason "..."` | Reason for rejection |
| | `--rejected` | Show rejection history |
| **Theme** | `--synthesize` | Group proposals by theme |
| | `--by-theme` | Review grouped by theme |
| | `--accept-theme` | Accept all in a theme |
| | `--list-themes` | List themes without reviewing |

### AI-Safe Commands (Non-Interactive)

```bash
babel review --list         # List proposals
babel review --accept <id>  # Accept specific
babel review --accept-all   # Accept all
babel review --reject <id>  # Reject specific
```

---

## [REV-03] --list

**Purpose**: List pending proposals without prompting (AI-safe).

```bash
babel review --list
```

**Output**:
```
1 proposal(s) pending:

1. [SM-SJ] [REQUIREMENT] Manuals must have AI-readable navigation

Accept with:
  babel review --accept <id>        # Accept specific proposal
  babel review --accept-all         # Accept all proposals
  babel review                      # Interactive review

Reject with:
  babel review --reject <id>        # Reject specific proposal
  babel review --reject <id> --reason "..."  # Reject with custom reason
```

### When to Use --list

| Situation | Action |
|-----------|--------|
| Check pending proposals | `babel review --list` |
| Before suggesting acceptance | `babel review --list` first |
| After multiple captures | See what's queued |

---

## [REV-04] --accept

**Purpose**: Accept proposals to enter the knowledge graph.

### Accept Specific

```bash
babel review --accept SM-SJ
```

**Output**:
```
Accepted: [SM-SJ] [REQUIREMENT] Manuals must have AI-readable navigation
  → Run: babel link SM-SJ  (Connect to purpose)
```

### Accept All

```bash
babel review --accept-all
```

**Output**:
```
Accepted 3 proposal(s):
  [SM-SJ] [REQUIREMENT] Manuals must have AI-readable navigation
  [XY-AB] [DECISION] Use Redis for caching
  [ZW-CD] [CONSTRAINT] API response < 200ms

→ Run: babel link <id>  (Connect accepted artifacts to purpose)
```

### After Acceptance

Accepted proposals become artifacts. **Link them immediately**:

```bash
babel link SM-SJ
```

---

## [REV-05] --reject

**Purpose**: Reject proposals with reason (P8: Learn from Rejections).

```bash
babel review --reject SM-SJ --reason "Not accurate for our use case"
```

**Output**:
```
Rejected: [SM-SJ] [REQUIREMENT] Manuals must have AI-readable navigation
  Reason: Not accurate for our use case
```

### Why Reasons Matter (P8)

Rejections are information:
- Future sessions can learn from past rejections
- `--rejected` shows rejection history
- Prevents same proposals being made again

### Reject Without Reason

```bash
babel review --reject SM-SJ
```

Works, but provides less learning value.

---

## [REV-06] --rejected

**Purpose**: Show rejection history for learning (P8: Evolution Traceable).

```bash
babel review --rejected
```

**Output**:
```
16 rejected proposal(s):

❌ [SE-LW] [REQUIREMENT] IDs from orphans list must be valid
   REASON: Not a bug - babel link is for artifacts, not proposals.
   DATE: 2026-01-21

❌ [DU-OC] [CONSTRAINT] Code tests cannot validate LLM skill
   REASON: Captured without user validation - violated HC2
   DATE: 2026-01-21
```

### Learning from Rejections

| Rejection Reason | Learning |
|------------------|----------|
| "Violated HC2" | Don't auto-capture |
| "Not a bug" | User error, not system issue |
| "Duplicate" | Check before capturing |
| "Wrong scope" | Clarify before proposing |

---

## [REV-07] Theme Review

**Purpose**: Group proposals by theme for efficient bulk review.

### Step 1: Synthesize Themes

```bash
babel review --synthesize
```

Groups proposals by semantic similarity.

### Step 2: List Themes

```bash
babel review --list-themes
```

**Output**:
```
Themes:
  1. [caching] 3 proposals about caching strategy
  2. [auth] 2 proposals about authentication
  3. [api] 4 proposals about API design
```

### Step 3: Accept by Theme

```bash
babel review --accept-theme caching
```

Accepts all proposals in the "caching" theme.

### When to Use Theme Review

| Situation | Approach |
|-----------|----------|
| Few proposals (1-5) | Use `--accept` or `--accept-all` |
| Many proposals (5+) | Use `--synthesize` + `--by-theme` |
| Mixed topics | Use `--accept-theme` selectively |

---

## [REV-08] Use Cases

### Use Case 1: AI Shows Pending to User

```bash
# AI lists proposals
babel review --list

# AI tells user:
# "You have 3 pending proposals. Review with: babel review"
```

### Use Case 2: User Accepts All

```bash
babel review --accept-all
```

Quick approval for trusted AI captures.

### Use Case 3: User Rejects with Reason

```bash
babel review --reject XY-AB --reason "This contradicts existing decision [ZW-CD]"
```

Reason helps AI learn from rejection.

### Use Case 4: Theme-Based Bulk Review

```bash
# Synthesize themes
babel review --synthesize

# Accept all caching-related
babel review --accept-theme caching

# Reject all auth-related with reason
babel review --reject-theme auth --reason "Need to discuss auth approach first"
```

### Use Case 5: Review Rejection History

```bash
# What got rejected before?
babel review --rejected

# Learn: don't repeat rejected patterns
```

### Use Case 6: AI Reminder Pattern

When `babel status` shows pending:
```
"You have 3 pending proposals. Review with: babel review"
```

---

## [REV-09] AI Operator Guide

### Non-Interactive Commands (MANDATORY)

```bash
# ALWAYS use these flags for AI operations
babel review --list          # Check pending
babel review --accept <id>   # Accept specific
babel review --accept-all    # Accept all
babel review --reject <id>   # Reject specific

# NEVER use interactive mode
babel review                 # WRONG - prompts for input
```

### Workflow Pattern

```
1. AI captures with --batch    → Queued
2. AI shows user: review --list
3. User runs: review --accept-all
4. AI links: babel link <id>
```

### Periodic Reminders

If proposals are pending:
```
"You have N pending proposals. Review with: babel review"
```

Check with:
```bash
babel status | grep "Pending"
```

### After User Accepts

**Link immediately**:
```bash
babel link <accepted-id>
```

Unlinked artifacts can't inform `babel why`.

---

## [REV-10] Integration

### Command Lifecycle

```
capture --batch → review --accept → link → [artifact in graph]
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `babel capture --batch` | Creates proposals for review |
| `babel link` | Links accepted artifacts to purpose |
| `babel status` | Shows pending proposal count |
| `babel why` | Retrieves accepted artifacts |

### Review Flow

```bash
# 1. AI captures
babel capture "decision" --batch

# 2. AI reminds
"Review pending: babel review"

# 3. User accepts
babel review --accept XY-AB

# 4. AI links
babel link XY-AB
```

---

## [REV-11] Quick Reference

```bash
# List pending (AI-safe)
babel review --list

# Accept specific
babel review --accept <id>

# Accept all
babel review --accept-all

# Reject with reason
babel review --reject <id> --reason "..."

# Show rejections
babel review --rejected

# Theme review
babel review --synthesize
babel review --list-themes
babel review --accept-theme <theme>
```

### Review Checklist

- [ ] Listed pending with `--list`?
- [ ] Used non-interactive flags?
- [ ] Linked accepted artifacts?
- [ ] Reminded user of pending?

### Common Patterns

```bash
# AI workflow (non-interactive)
babel review --list
babel review --accept-all
babel link <id>

# User workflow (can be interactive)
babel review

# Theme-based bulk review
babel review --synthesize
babel review --accept-theme <theme>
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~485
Last updated: 2026-01-24
=============================================================================
-->
