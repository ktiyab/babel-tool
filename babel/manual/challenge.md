# babel challenge / evidence / resolve — Disagree With Prior Decisions (DISAGREE Flow)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For resolve section, read offset=135 limit=50
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [DIS-01] Intent | 31-54 | purpose, DISAGREE flow, P4 | `offset=26 limit=33` |
| [DIS-02] challenge | 55-93 | create tension, hypothesis | `offset=50 limit=48` |
| [DIS-03] evidence | 94-126 | add evidence, observation | `offset=89 limit=42` |
| [DIS-04] resolve | 127-174 | outcomes, confirmed, revised | `offset=122 limit=57` |
| [DIS-05] Complete Workflow | 175-214 | full example, lifecycle | `offset=170 limit=49` |
| [DIS-06] AI Operator Guide | 215-249 | when to challenge, non-interactive | `offset=210 limit=44` |
| [DIS-07] Quick Reference | 250-292 | cheatsheet | `offset=245 limit=52` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[DIS-" .babel/manual/challenge.md
```

---

## [DIS-01] Intent

The **DISAGREE flow** allows challenging prior decisions with evidence.

### Core Principle (P4)

**Disagreement is information, not conflict.**

Challenges:
- Surface problems with existing decisions
- Build evidence for or against
- Resolve with explicit outcome
- Create evolution chain (P8)

### The Three Commands

| Command | Purpose |
|---------|---------|
| `challenge` | Create tension against a decision |
| `evidence` | Add supporting evidence |
| `resolve` | Close with outcome |

---

## [DIS-02] challenge

**Purpose**: Challenge an existing decision.

```bash
babel challenge <target_id> "reason for disagreement"
```

### Basic Challenge

```bash
babel challenge GP-LF "This approach causes performance issues"
```

**Output**:
```
Challenge created [T_abc123]:
  Target: [GP-LF] Use Redis for caching
  Reason: This approach causes performance issues

-> Next: babel evidence T_abc123 "supporting data"
```

### With Hypothesis

```bash
babel challenge GP-LF "Performance issues" \
  --hypothesis "Local caching would be faster" \
  --test "Benchmark both approaches"
```

### With Domain

```bash
babel challenge GP-LF "Security concern" --domain security
```

---

## [DIS-03] evidence

**Purpose**: Add evidence to an open challenge.

```bash
babel evidence <challenge_id> "what you observed"
```

### Add Observation

```bash
babel evidence T_abc123 "Benchmark shows 500ms response time with Redis"
```

### Evidence Types

```bash
babel evidence T_abc123 "data" --type observation
babel evidence T_abc123 "data" --type benchmark
babel evidence T_abc123 "data" --type user_feedback
babel evidence T_abc123 "data" --type other
```

### Multiple Evidence

```bash
babel evidence T_abc123 "Redis adds 200ms network latency"
babel evidence T_abc123 "Local cache shows 50ms response"
babel evidence T_abc123 "User complaints about slow API"
```

---

## [DIS-04] resolve

**Purpose**: Close challenge with explicit outcome.

```bash
babel resolve <challenge_id> --outcome <outcome> --resolution "what was decided"
```

### Outcomes

| Outcome | Meaning | When to Use |
|---------|---------|-------------|
| `confirmed` | Original was correct | Challenge disproven |
| `revised` | New approach supersedes | Challenge proven |
| `synthesized` | Both partially right | Merged perspective |
| `uncertain` | Can't decide yet | Need more evidence |

### Confirm Original

```bash
babel resolve T_abc123 --outcome confirmed \
  --resolution "Redis is correct - issue was network config"
```

### Revise Decision

```bash
babel resolve T_abc123 --outcome revised \
  --resolution "Changed to local caching for performance"
```

**After revision**: Link the evolution chain:
```bash
babel link <new-decision-id> <old-decision-id>
```

### Non-Interactive (AI)

```bash
babel resolve T_abc123 --outcome revised \
  --resolution "explanation" \
  --force
```

The `--force` flag skips confirmation prompts.

---

## [DIS-05] Complete Workflow

### Step 1: Challenge

```bash
babel challenge GP-LF "Performance is unacceptable - 500ms response"
# → [T_abc123]
```

### Step 2: Build Evidence

```bash
babel evidence T_abc123 "Benchmark: Redis adds 200ms latency"
babel evidence T_abc123 "Local cache benchmark: 50ms response"
babel evidence T_abc123 "SLA requires < 200ms"
```

### Step 3: Capture Replacement (if revising)

```bash
babel capture "Use local in-memory cache instead of Redis for API responses. Benchmarks show 4x improvement." --batch
# User accepts → [XY-AB]
```

### Step 4: Resolve

```bash
babel resolve T_abc123 --outcome revised \
  --resolution "Replaced Redis with local cache (see XY-AB)" \
  --force
```

### Step 5: Link Evolution

```bash
babel link XY-AB GP-LF  # XY-AB evolves_from GP-LF
```

---

## [DIS-06] AI Operator Guide

### When to Challenge

| Observation | Action |
|-------------|--------|
| Prior decision seems wrong | `babel challenge <id>` |
| Evidence contradicts decision | Challenge + evidence |
| Performance/security issue | Challenge with domain |

### Non-Interactive Pattern

```bash
# All commands work non-interactively
babel challenge <id> "reason"
babel evidence <id> "data"
babel resolve <id> --outcome X --resolution "..." --force
```

### Building Strong Cases

1. Create challenge with clear reason
2. Add multiple pieces of evidence
3. Let evidence guide outcome
4. Resolve with summary

### After Revision

Always link the evolution chain:
```bash
babel link <new-id> <old-id>
```

---

## [DIS-07] Quick Reference

```bash
# Challenge
babel challenge <target_id> "reason"
babel challenge <id> "reason" --hypothesis "alternative" --test "how"
babel challenge <id> "reason" --domain security

# Evidence
babel evidence <challenge_id> "observation"
babel evidence <id> "data" --type benchmark

# Resolve
babel resolve <id> --outcome confirmed --resolution "..."
babel resolve <id> --outcome revised --resolution "..." --force
babel resolve <id> --outcome synthesized --resolution "..."
babel resolve <id> --outcome uncertain --resolution "..."
```

### Lifecycle

```
challenge → evidence (×N) → [capture replacement] → resolve → [link evolution]
```

### Outcomes Summary

| Outcome | Original | New |
|---------|----------|-----|
| confirmed | Kept | N/A |
| revised | Superseded | Created |
| synthesized | Merged | Created |
| uncertain | Pending | Pending |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~335
Last updated: 2026-01-24
=============================================================================
-->
