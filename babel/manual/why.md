# babel why — Query Project Knowledge and Reasoning

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --commit section, read offset=95 limit=40
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [WHY-01] Intent | 34-67 | purpose, RECALL flow, knowledge retrieval | `offset=29 limit=43` |
| [WHY-02] Command Overview | 68-96 | syntax, parameters, output format | `offset=63 limit=38` |
| [WHY-03] Query Basics | 97-162 | **cross-convention**, **tokenization**, semantic bridge | `offset=92 limit=75` |
| [WHY-04] --commit | 164-228 | git, **linked symbols**, semantic bridge | `offset=159 limit=75` |
| [WHY-05] Output Anatomy | 230-282 | sources, **doc_symbols**, code_symbols | `offset=225 limit=62` |
| [WHY-06] Use Cases | 283-352 | examples, scenarios, workflows | `offset=278 limit=79` |
| [WHY-07] AI Operator Guide | 353-425 | mandatory, **cross-convention queries**, scoring | `offset=348 limit=82` |
| [WHY-08] Integration | 426-490 | **semantic bridge diagram**, circular flow | `offset=421 limit=72` |
| [WHY-09] Quick Reference | 492-532 | cheatsheet, patterns | `offset=487 limit=50` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[WHY-" .babel/manual/why.md    # Find all sections
grep -n "WHY-04" .babel/manual/why.md     # Find --commit section
```

---

## [WHY-01] Intent

`babel why` is the **RECALL** command — it retrieves captured decisions, reasoning, and constraints to inform your actions.

### The Problem It Solves

| Without Why | With Why |
|-------------|----------|
| AI guesses based on patterns | AI knows from captured decisions |
| Prior reasoning is lost | Reasoning persists and is queryable |
| "Why did we do X?" unanswered | Direct answer with sources |
| Same mistakes repeated | Constraints prevent violations |

### Core Principle

**Query before acting. Never assume.**

```
WRONG: "Based on typical patterns, this probably uses..."
RIGHT: babel why "topic" → "Babel shows: [ID] decision because..."
```

### When to Use

**MANDATORY**: Before ANY code modification

Also use when:
- Starting work on unfamiliar area
- User asks "why does this code do X?"
- After context compression (to re-orient)
- Before suggesting changes

---

## [WHY-02] Command Overview

```bash
babel why "query"           # Query by topic
babel why --commit <sha>    # Query why a commit was made
```

| Parameter | Purpose |
|-----------|---------|
| `"query"` | Topic, concept, or question to search |
| `--commit <sha>` | Get decisions linked to a specific commit |

### Output Format

```
[Topic] in this project:

  [Synthesis paragraph explaining the topic]

  [Implementation details and decisions]

  Sources: N purposes, N decisions, N code_symbols
  IDs: [ID-1] [ID-2] [ID-3]...

-> Next: [suggested follow-up command]
```

---

## [WHY-03] Query Basics

### How Queries Work

1. **Universal tokenization** — Query is split into semantic tokens (language-agnostic)
2. **Cross-convention matching** — Tokens match ANY naming convention equally
3. **Graph traversal** — Expands 1 hop to find related artifacts
4. **Semantic synthesis** — LLM synthesizes into coherent answer
5. **Source citation** — Shows IDs for all referenced artifacts

### Cross-Convention Matching

The query system uses **universal tokenization** to match symbols regardless of naming convention:

| Query | Matches Equally |
|-------|-----------------|
| `"user profile"` | `UserProfile`, `user_profile`, `user-profile`, `userProfile` |
| `"cache manager"` | `CacheManager`, `cache_manager`, `cache-manager` |
| `"get user"` | `getUser`, `get_user`, `GetUser` |

This works because all naming conventions encode the **same semantic tokens**:
- `getUserProfile` → `[get, user, profile]`
- `get_user_profile` → `[get, user, profile]`
- `get-user-profile` → `[get, user, profile]`

**Key insight**: Naming conventions are formatting, not content. The meaning is in the tokens.

### Query Examples

```bash
# Broad topic
babel why "caching"

# Specific concept
babel why "rate limiting implementation"

# Question form
babel why "why does login redirect to /dashboard"

# Code pattern
babel why "error handling in API"
```

### Query Tips

| Query Type | Example | Returns |
|------------|---------|---------|
| Feature | `"authentication"` | Auth decisions, constraints |
| Pattern | `"event sourcing"` | Architecture decisions |
| File | `"cli.py"` | Decisions about CLI structure |
| Constraint | `"performance limits"` | Performance constraints |
| Cross-convention | `"user service"` | `UserService`, `user_service`, etc. |
| CSS/HTML | `"main nav"` | `#main-nav`, `.main-navigation`, etc. |

### What Gets Searched

- Decisions and their reasoning
- Constraints and rules
- Purposes and goals
- Code symbols (classes, functions, methods — if indexed via `babel map`)
- Documentation symbols (document, section, subsection — from indexed markdown)
- Specifications (from `capture --spec`)

The **semantic bridge** connects all these: decisions (WHY) link to code AND documentation (WHAT).

---

## [WHY-04] --commit

**Purpose**: Understand why a specific commit was made by retrieving linked decisions and symbols.

```bash
babel why --commit c73a08f
```

**Output**:
```
Commit [c73a08f2]:
  "Fix cache invalidation in events.py for write operations"
  by ktiyab

Linked decisions (1):

  [CZ-ZG] PRINCIPLE
    "Cache operations should be transparent to users"
    Linked by: user

Linked symbols (3):
  [C] src.cache.CacheManager
  [M] src.cache.CacheManager.invalidate
  [F] src.cache.clear_all
```

### The Semantic Bridge

When decisions are linked to commits via `babel link --to-commit`, the system also auto-detects touched code symbols. This creates a complete traceability chain:

```
Decision (WHY) ←→ Commit (state) ←→ Symbols (WHAT)
```

### When to Use --commit

| Situation | Why Use |
|-----------|---------|
| Before refactoring | Understand original intent |
| Reviewing PR | Check if commit aligns with decisions |
| After git blame | Know WHY, not just WHO |
| Code archaeology | Trace reasoning to implementation |

### How Decisions Get Linked to Commits

```bash
# During implementation (auto-links to touched symbols)
babel link <decision-id> --to-commit HEAD

# Retroactively
babel suggest-links --from-recent 10
```

### When No Links Exist

```
Commit [abc1234]:
  "Some commit message"
  by author

No linked decisions found.

Tip: Link decisions with: babel link <decision-id> --to-commit abc1234
```

---

## [WHY-05] Output Anatomy

### Full Output Example

```
◌ Thinking...● Done  ↓1239 ↑315 ≡1554

Caching in this project:

  The caching strategy serves multiple purposes: improving
  performance [TW-CQ], providing semantic understanding [KN-CX],
  and enabling responsive UX [JP-KD].

  The implementation uses Redis for distributed caching [KN-JV].
  The babel map system implements incremental updates with
  mtime-based caching [OK-MF]. Documentation for the caching
  system is available in the manual [manual.cache.CACHE-03].

  Sources: 5 decisions, 3 principles, 2 purposes, 4 code_symbols, 2 doc_symbols
  IDs: [KN-JV] [OK-MF] [OA-PF] [ZY-AF] [OU-YH]

-> Next: babel gather --symbol "CacheManager"  (Load the code)
```

The output now includes both **code symbols** (classes, functions) and **documentation symbols** (manual sections) when indexed via `babel map`.

### Output Components

| Component | Purpose |
|-----------|---------|
| `◌ Thinking...● Done` | LLM processing indicator |
| `↓N ↑N ≡N` | Tokens: input, output, total |
| Inline `[ID]` | Artifact references in text |
| `Sources:` | Count by artifact type |
| `IDs:` | All artifact IDs (for follow-up) |
| `-> Next:` | Suggested next command |

### Using IDs for Follow-up

```bash
# Get full artifact details
babel list --from KN-JV

# Challenge a decision
babel challenge KN-JV "reason for disagreement"

# Endorse a decision
babel endorse KN-JV
```

---

## [WHY-06] Use Cases

### Use Case 1: Before Modifying Code (MANDATORY)

```bash
# User asks: "Let's refactor the caching"
babel why "caching"
babel why "cache invalidation"
# NOW you know existing decisions before changing anything
```

### Use Case 2: Understanding a File

```bash
# Need to modify cli.py
babel why "cli.py structure"
babel why "command registration"
# Now understand architectural decisions
```

### Use Case 3: After Context Compression

When your context is compressed:

```bash
# Re-orient quickly
babel status        # Project overview
babel why "current feature"  # Specific context
# Now you're back up to speed
```

### Use Case 4: Investigating a Bug

```bash
# Bug in rate limiting
babel why "rate limiting"
babel why --commit <commit-that-introduced-bug>
# Understand original intent to fix correctly
```

### Use Case 5: Before Proposing Alternative

```bash
# Want to suggest different approach
babel why "current approach"
# Check if there were reasons for current design
# THEN propose, informed by context
```

### Use Case 6: Answering User Questions

```bash
# User asks: "Why does the API use Redis?"
babel why "API Redis"
# Quote the answer: "Babel shows: [KN-JV] Using Redis because..."
```

### Use Case 7: Code Archaeology

```bash
# Commit message is unclear
git blame src/api.py | head -5
# → abc1234 (author 2026-01-10) def handler():

babel why --commit abc1234
# → Shows linked decisions explaining why
```

---

## [WHY-07] AI Operator Guide

### Mandatory Rule

**ALWAYS run `babel why` before modifying code.** Not optional.

```
WRONG: User asks → You implement
RIGHT: User asks → babel why "topic" → You implement informed
```

### Detection Pattern

| User Request | Your Response |
|--------------|---------------|
| "Fix the bug in X" | `babel why "X"` first |
| "Add feature Y" | `babel why "Y"` first |
| "Refactor Z" | `babel why "Z"` first |
| "Change how W works" | `babel why "W"` first |

### Verbatim Protocol

**Never invent what Babel didn't say.**

```
FROM BABEL (quote exactly):
  "Babel shows: [a1b2c3d4] Using SQLite because users need offline access"

MY INTERPRETATION (label clearly):
  "Based on this, caching should also be local-first"
```

### When Babel Returns Nothing

```
WRONG: "No decisions found, but typically projects use..."

RIGHT: "Babel has no captured decisions about X.
        This is a gap — should we capture a decision now?"
```

### Query Patterns for AI

```bash
# Before any code change
babel why "the area you're about to change"

# Multiple queries for complex changes
babel why "component A"
babel why "component B"
babel why "how A and B interact"
```

### Cross-Convention Queries

You don't need to guess the exact naming convention. The tokenizer normalizes all names:

```bash
# All these find the same symbols:
babel why "user profile"      # Finds UserProfile, user_profile, user-profile
babel why "cache service"     # Finds CacheService, cache_service, etc.
babel why "html parser"       # Finds HTMLParser, html_parser, etc.
```

**Scoring priority**:
1. Exact name match (highest)
2. Qualified name match
3. Token-based match (cross-convention)

Results are sorted by relevance, so exact matches appear first.

---

## [WHY-08] Integration

### Command Lifecycle

```
why → [understand] → capture --batch → review → link → why [circular]
```

Meaning flows in circles: `why` informs decisions, decisions become artifacts, artifacts link to code/docs, all discoverable via `why`.

### Related Commands

| Command | Relationship |
|---------|--------------|
| `babel capture` | Stores what `why` retrieves |
| `babel map` | Indexes code AND documentation symbols for `why` |
| `babel gather --symbol` | Loads code or doc sections found by `why` |
| `babel link` | Connects artifacts for `why` to find |
| `babel link --to-commit` | Creates semantic bridge (decision → commit → symbols) |

### The Semantic Bridge

`babel why` operates across the semantic bridge:

```
        babel why "topic"
              │
              ▼
┌─────────────────────────────────┐
│     DECISIONS (WHY)             │ ← Captured reasoning
├─────────────────────────────────┤
│     CODE SYMBOLS (WHAT)         │ ← Indexed via babel map
├─────────────────────────────────┤
│     DOCUMENTATION (HOW TO USE)  │ ← Indexed markdown sections
└─────────────────────────────────┘
```

All three layers are searchable and interconnected.

### Why + Map Integration

```bash
# Index codebase AND documentation
babel map --index src/ .babel/manual/

# Now why can find code AND doc symbols
babel why "UserService"
# → Returns decisions, code location, AND relevant manual sections
```

### Why + Gather Integration

```bash
# Why shows code location
babel why "cache invalidation"
# → "Implementation at babel/core/cache.py:45-80"
# → "Documentation at .babel/manual/cache.md [CACHE-03]"

# Gather loads just what you need
babel gather --symbol "invalidate_cache"
babel gather --symbol "manual.cache.CACHE-03"
```

---

## [WHY-09] Quick Reference

```bash
# Basic query
babel why "topic"

# Query about commit
babel why --commit <sha>

# Common queries
babel why "feature name"
babel why "file.py purpose"
babel why "error handling"
babel why "architecture decision"
```

### Query Checklist

- [ ] Queried before modifying code?
- [ ] Quoted Babel verbatim (not paraphrased)?
- [ ] Noted if Babel had no results?
- [ ] Used IDs for follow-up commands?

### Common Patterns

```bash
# Before code change (mandatory)
babel why "area to change"

# After context compression
babel status && babel why "current work"

# Understanding commit
babel why --commit HEAD~1

# Finding constraints
babel why "constraints on X"
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~540
Last updated: 2026-01-27
Change: Added universal tokenization and cross-convention matching documentation.
        Query now matches UserProfile, user_profile, user-profile equally via token-based matching.
=============================================================================
-->
