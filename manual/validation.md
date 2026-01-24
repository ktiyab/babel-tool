# babel validation / endorse / evidence-decision — Strengthen Decisions (P9)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [VAL-01] Intent | 28-55 | purpose, P9, dual-test truth | `offset=23 limit=37` |
| [VAL-02] validation | 57-95 | check status, states | `offset=52 limit=48` |
| [VAL-03] endorse | 97-130 | consensus, agreement | `offset=92 limit=43` |
| [VAL-04] evidence-decision | 132-170 | proof, grounding | `offset=127 limit=48` |
| [VAL-05] Use Cases | 172-215 | examples, workflows | `offset=167 limit=53` |
| [VAL-06] Quick Reference | 217-255 | cheatsheet | `offset=212 limit=48` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[VAL-" manual/validation.md
```

---

## [VAL-01] Intent

The **STRENGTHEN flow** validates decisions through consensus AND evidence (P9: Dual-Test Truth).

### Validation States

| Symbol | State | Meaning |
|--------|-------|---------|
| `○` | Proposed | Captured, not reviewed |
| `◐` | Consensus only | Endorsed, no evidence |
| `◑` | Evidence only | Tested, not endorsed |
| `●` | Validated | BOTH consensus AND evidence |

### P9: Dual-Test Truth

Decisions need BOTH:
- **Consensus** — People agree (via `endorse`)
- **Evidence** — Proof it works (via `evidence-decision`)

### The Three Commands

| Command | Purpose |
|---------|---------|
| `validation` | Check validation status |
| `endorse` | Add consensus |
| `evidence-decision` | Add evidence |

---

## [VAL-02] validation

**Purpose**: Check validation status of decisions.

```bash
babel validation [decision_id]
```

### Check All

```bash
babel validation
```

**Output**:
```
Validation Status (P9: Dual-Test Truth)

  ● Validated (133):
    Both consensus AND evidence

  ◐ Consensus only (3):
    [GP-LF] Use Redis for caching

  ◑ Evidence only (6):
    [XY-AB] Local cache implementation

→ Next: babel endorse <id>  (Add consensus)
→ Next: babel evidence-decision <id> "proof"  (Add evidence)
```

### Check Specific

```bash
babel validation GP-LF
```

Shows validation details for one decision.

---

## [VAL-03] endorse

**Purpose**: Add consensus (agreement) to a decision.

```bash
babel endorse <decision_id>
```

### Basic Endorsement

```bash
babel endorse GP-LF
```

**Output**:
```
Endorsed [GP-LF]:
  DECISION: Use Redis for caching
  Status: ◐ consensus (needs evidence for validation)
```

### With Comment

```bash
babel endorse GP-LF --comment "Confirmed this approach works well"
```

### When to Endorse

- After reviewing and agreeing with decision
- Team consensus achieved
- User confirms approach is correct

---

## [VAL-04] evidence-decision

**Purpose**: Add evidence (proof) to a decision.

```bash
babel evidence-decision <decision_id> "evidence"
```

### Add Observation

```bash
babel evidence-decision GP-LF "API response times improved from 500ms to 50ms"
```

### Evidence Types

```bash
babel evidence-decision GP-LF "data" --type observation
babel evidence-decision GP-LF "data" --type benchmark
babel evidence-decision GP-LF "data" --type user_feedback
babel evidence-decision GP-LF "data" --type outcome
```

### When to Add Evidence

- Tests pass
- Performance metrics met
- User confirmed working
- Observed outcome matches intent

---

## [VAL-05] Use Cases

### Use Case 1: Full Validation

```bash
# Decision exists: GP-LF
# Add consensus
babel endorse GP-LF

# Add evidence
babel evidence-decision GP-LF "Tests pass, performance meets SLA"

# Check status
babel validation GP-LF
# → ● Validated
```

### Use Case 2: After Implementation

```bash
# Implemented and tested
babel evidence-decision GP-LF "All tests pass, 50ms response time"

# Team agrees
babel endorse GP-LF
```

### Use Case 3: Check What Needs Work

```bash
babel validation
# See: which decisions need endorsement or evidence
```

### Use Case 4: Periodic Health Check

```bash
babel status
# Shows: ◐ Validation: 133 validated, 6 need review
babel validation
# Details on what needs attention
```

---

## [VAL-06] Quick Reference

```bash
# Check validation status
babel validation
babel validation <id>

# Add consensus
babel endorse <id>
babel endorse <id> --comment "reason"

# Add evidence
babel evidence-decision <id> "proof"
babel evidence-decision <id> "proof" --type benchmark
```

### Validation States

| State | Needs |
|-------|-------|
| `◐` Consensus only | Add evidence |
| `◑` Evidence only | Add endorsement |
| `●` Validated | Complete |

### Full Validation Flow

```bash
babel endorse <id>
babel evidence-decision <id> "proof"
# → ● Validated
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~260
Last updated: 2026-01-24
=============================================================================
-->
