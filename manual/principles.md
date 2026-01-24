# babel principles — Framework Self-Check (P11)

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Core Principles section, read offset=82 limit=120
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [PRI-01] Intent | 33-66 | purpose, P11, self-application, framework | `offset=28 limit=43` |
| [PRI-02] Command Overview | 68-105 | syntax, output | `offset=63 limit=47` |
| [PRI-03] Core Principles (P1-P6) | 107-178 | need, ontology, expertise, disagreement, truth, ambiguity | `offset=102 limit=81` |
| [PRI-04] System Principles (P7-P11) | 180-237 | memory, evolution, synthesis, adaptive, recursive | `offset=175 limit=67` |
| [PRI-05] Human Constraints (HC1-HC3) | 239-276 | immutable, authority, offline-first | `offset=234 limit=52` |
| [PRI-06] Use Cases | 278-327 | examples, self-check, verification | `offset=273 limit=59` |
| [PRI-07] AI Operator Guide | 329-375 | triggers, when to check principles | `offset=324 limit=56` |
| [PRI-08] Quick Reference | 377-460 | cheatsheet, principle summary | `offset=372 limit=93` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[PRI-" manual/principles.md    # Find all sections
grep -n "PRI-03" manual/principles.md     # Find Core Principles
```

---

## [PRI-01] Intent

`babel principles` displays the **Babel framework principles** for self-checking and grounding.

### The Problem It Solves

| Without Principles | With Principles |
|--------------------|-----------------|
| Forget why patterns exist | Principles explain the "why" |
| Inconsistent application | Consistent framework guidance |
| Lost in commands | Grounded in philosophy |
| "Why this workflow?" | Clear principle reference |

### Core Concept (P11: Recursive Application)

**A framework that cannot govern itself is incomplete.**

Principles are for:
- Self-checking your babel usage
- Understanding why workflows exist
- Grounding decisions in framework philosophy
- Teaching new team members

### When to Reference

| Situation | Principle |
|-----------|-----------|
| Starting a project | P1: Bootstrap from Need |
| Disagreeing with decision | P4: Disagreement as Hypothesis |
| Validating decisions | P5: Dual-Test Truth |
| Uncertain about something | P6: Ambiguity Management |
| Deprecating old decisions | P7: Living Memory |

---

## [PRI-02] Command Overview

```bash
babel principles
```

No options — displays all principles.

### Output Structure

```
Babel Principles -- Framework Self-Application (P11)
====================================================

CORE PRINCIPLES
---------------
P1: Bootstrap from Need
    ...

SYSTEM PRINCIPLES
-----------------
P7: Living Memory
    ...

HUMAN CONSTRAINTS
-----------------
HC1: Immutable Event Log
    ...
```

### Quick Reference

Each principle includes:
- Name and number
- Description
- Relevant babel commands

---

## [PRI-03] Core Principles (P1-P6)

### P1: Bootstrap from Need

**Start from real problems, not solutions.**

Every project begins with a stated need. Purpose is grounded in reality.

```bash
babel init --need "problem" --purpose "solution"
```

### P2: Emergent Ontology

**Vocabulary emerges, not imposed.**

Define terms as the project discovers them. Don't force terminology upfront.

```bash
babel define
babel challenge
babel refine
```

### P3: Expertise Governance

**Authority derives from domain expertise, not seniority.**

State which domain your claims apply to. AI participates as pattern detector, never arbiter.

```bash
babel capture "..." --domain architecture
babel capture "..." --domain security
```

### P4: Disagreement as Hypothesis

**Disagreement is information, not noise.**

Challenges require hypotheses and tests. Don't suppress disagreement — capture it.

```bash
babel challenge <id> "reason"
babel evidence <id> "observation"
babel resolve <id> --outcome X
```

### P5: Dual-Test Truth

**Decisions need both consensus AND evidence.**

- Consensus alone risks groupthink
- Evidence alone risks blind spots

```bash
babel endorse <id>
babel evidence-decision <id> "proof"
babel validation
```

### P6: Ambiguity Management

**Hold uncertainty rather than forcing premature closure.**

Capture unknowns explicitly. Resolve when evidence is sufficient.

```bash
babel question "unknown" --batch
babel resolve-question <id> "answer"
```

---

## [PRI-04] System Principles (P7-P11)

### P7: Living Memory

**Knowledge evolves rather than accumulates.**

Deprecate obsolete artifacts instead of deleting them. Evolution is traceable.

```bash
babel deprecate <id> "reason"
babel deprecate <id> "reason" --superseded-by <new>
```

### P8: Evolution Traceable

**Changes maintain explicit supersession chains.**

When decisions evolve, link old to new.

```bash
babel resolve <id> --outcome revised
babel deprecate <old> --superseded-by <new>
babel history <id>
```

### P9: Synthesis Over Victory

**Conflicts seek integration, not domination.**

When resolving tensions, look for synthesis that honors both sides.

```bash
babel resolve <id> --outcome synthesized
```

### P10: Adaptive Cycle Rate

**Response speed matches signal severity.**

Critical tensions get accelerated cycles. Minor tensions maintain normal pace.

```bash
babel tensions          # Sorted by severity
babel tensions --full   # See severity levels
```

### P11: Recursive Application

**Framework applies to itself.**

Use principles to check your own babel usage. A framework that cannot govern itself is incomplete.

```bash
babel principles        # Review for self-check
babel coherence         # Check alignment
```

---

## [PRI-05] Human Constraints (HC1-HC3)

### HC1: Immutable Event Log

**Events cannot be deleted or modified.**

Once captured, decisions persist. This ensures audit trail and prevents silent revision.

```bash
# Can't delete — can only deprecate
babel deprecate <id> "reason"
```

### HC2: Human Authority

**AI proposes, human disposes.**

AI never auto-confirms artifacts. Humans must review and accept.

```bash
babel capture "..." --batch   # Proposes, doesn't confirm
babel review                  # Human reviews
babel review --accept <id>    # Human confirms
```

### HC3: Offline-First

**Core functionality works without network.**

System must function offline. Network enhances but isn't required.

```bash
babel why "topic"        # Works offline (with fallback)
babel capture --batch    # Works offline
babel sync               # Syncs when online
```

---

## [PRI-06] Use Cases

### Use Case 1: Self-Check Before Major Decision

```bash
babel principles
# Review P4, P5 — am I following proper process?
```

### Use Case 2: Onboarding New Team Member

```bash
babel principles
# Walk through each principle
# Explain how they manifest in commands
```

### Use Case 3: Resolving Tension

```bash
# Stuck on how to resolve?
babel principles
# Review P4, P5, P9 for guidance
```

### Use Case 4: Questioning a Workflow

```bash
# "Why do we use --batch?"
babel principles
# See HC2: Human Authority
```

### Use Case 5: Deprecation Decision

```bash
# Should I delete or deprecate?
babel principles
# See P7, P8, HC1 — deprecate, never delete
```

### Use Case 6: Framework Coherence Check

```bash
babel principles         # Review the framework
babel coherence          # Check project alignment
babel scan --type health # Technical compliance
```

---

## [PRI-07] AI Operator Guide

### When AI Should Reference Principles

| Trigger | AI Action |
|---------|-----------|
| User asks "why this workflow?" | Reference relevant principle |
| Uncertainty about process | `babel principles` then explain |
| New user onboarding | Walk through principles |
| Tension resolution | Reference P4, P5, P9 |

### Principle Quick Reference for AI

| Situation | Principle | Command |
|-----------|-----------|---------|
| Starting project | P1 | `init --need` |
| Disagreement | P4 | `challenge`, `evidence` |
| Validation | P5 | `endorse`, `evidence-decision` |
| Uncertainty | P6 | `question` |
| Deprecation | P7, P8 | `deprecate --superseded-by` |
| AI proposing | HC2 | `--batch`, `review` |

### Context Compression Survival

After compression, remember:

1. **P11 is meta** — use principles to check principles
2. **HC2 is non-negotiable** — AI proposes, human disposes
3. **P4-P5-P6 flow** — disagreement → evidence → resolution OR hold uncertainty

### AI-Safe Command

`babel principles` is **non-interactive** — safe for AI operators:

```bash
babel principles    # View only, no prompts
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "Why use --batch?" | Reference HC2: Human Authority |
| "Should I delete this?" | Reference P7, HC1: Deprecate, don't delete |
| "How do I disagree?" | Reference P4: Challenge flow |

---

## [PRI-08] Quick Reference

### Command

```bash
babel principles    # View all principles
```

### Principle Summary

| ID | Name | Core Idea |
|----|------|-----------|
| P1 | Bootstrap from Need | Start from problems |
| P2 | Emergent Ontology | Vocabulary emerges |
| P3 | Expertise Governance | Domain authority |
| P4 | Disagreement as Hypothesis | Challenges are testable |
| P5 | Dual-Test Truth | Consensus + Evidence |
| P6 | Ambiguity Management | Hold uncertainty |
| P7 | Living Memory | Evolve, don't delete |
| P8 | Evolution Traceable | Supersession chains |
| P9 | Synthesis Over Victory | Integrate conflicts |
| P10 | Adaptive Cycle Rate | Match response to severity |
| P11 | Recursive Application | Framework governs itself |

### Human Constraints

| ID | Name | Core Idea |
|----|------|-----------|
| HC1 | Immutable Event Log | Events can't be deleted |
| HC2 | Human Authority | AI proposes, human disposes |
| HC3 | Offline-First | Works without network |

### Principle → Command Mapping

| Principle | Key Commands |
|-----------|--------------|
| P1 | `init --need --purpose` |
| P4 | `challenge`, `evidence`, `resolve` |
| P5 | `endorse`, `evidence-decision`, `validation` |
| P6 | `question`, `resolve-question` |
| P7-P8 | `deprecate --superseded-by`, `history` |
| HC2 | `--batch`, `review` |

### Related Commands

| Command | Relationship |
|---------|--------------|
| `coherence` | Checks alignment with purpose |
| `validation` | Implements P5 |
| `tensions` | Implements P4, P10 |
| `question` | Implements P6 |
| `deprecate` | Implements P7, P8 |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~535
Last updated: 2026-01-24
=============================================================================
-->
