# babel scan — Context-Aware Technical Analysis

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=361 limit=72
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [SCN-01] Intent | 33-79 | purpose, technical scan, EAST framework | `offset=28 limit=55` |
| [SCN-02] Command Overview | 80-142 | syntax, type, deep, verbose, **--verify, --remove** | `offset=75 limit=70` |
| [SCN-03] Scan Types | 143-399 | health, architecture, security, performance, dependencies, clean, **automated workflow, hybrid parser** | `offset=138 limit=265` |
| [SCN-04] Output & Messages | 400-467 | findings, warnings, recommendations | `offset=395 limit=75` |
| [SCN-05] Use Cases | 468-531 | examples, workflows, scenarios | `offset=463 limit=70` |
| [SCN-06] AI Operator Guide | 532-595 | triggers, when to scan, detection | `offset=527 limit=70` |
| [SCN-07] Integration | 596-662 | coherence, check, capture, lifecycle | `offset=591 limit=75` |
| [SCN-08] Quick Reference | 668-787 | cheatsheet, **automated workflow**, manual workflow, requirements | `offset=663 limit=125` |
| [SCN-09] Troubleshooting | 788-1000 | errors, git checkpoint, common issues, **practical fixes** | `offset=783 limit=220` |

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
| `clean` | Code cleanup: unused imports, dead code (via ruff) |

---

## [SCN-02] Command Overview

```bash
babel scan [query] [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Optional** | `query` | Specific question to answer |
| **Type** | `--type` | Scan type: health, architecture, security, performance, dependencies, clean |
| **Depth** | `--deep` | Run comprehensive analysis |
| **Output** | `-v`, `--verbose` | Show all findings including info items |
| **Findings** | `--list` | List persisted findings from last scan |
| **Findings** | `--validate ID` | Mark finding as true positive |
| **Findings** | `--invalidate ID --reason "..."` | Mark as false positive (exclude) |
| **Findings** | `--resolve-finding ID` | Mark finding as resolved |
| **Findings** | `--exclusions` | Show excluded findings |
| **Automation** | `--verify` | Auto-verify findings using hybrid parser (clean scan only) |
| **Automation** | `--remove` | Remove verified imports with safety checkpoint (clean scan only) |

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

### clean (Code Cleanup)

Code cleanup using **ruff** (fast Python linter):

```bash
babel scan --type clean          # Find unused imports
babel scan --type clean --deep   # Find all cleanup issues
```

> **⚠️ HC2 Compliance: Human Authority Preserved**
>
> Babel scan maintains **human authority** through two workflows:
> - **Manual workflow**: AI reviews, human fixes manually
> - **Automated workflow**: AI verifies + removes, human reviews captures
>
> Both workflows ensure human oversight — the difference is **when**:
> - Manual: Human reviews BEFORE changes
> - Automated: Human reviews AFTER changes (with rollback available)

**Normal mode checks:**
- F401: Unused imports (most common after refactoring)

**Deep mode adds:**
- F841: Unused variables
- I001: Unsorted imports
- ERA001: Commented-out code
- PIE790: Unnecessary pass statements

**Installation:**
```bash
pip install ruff                  # Install ruff globally
pip install babel-tool[clean]     # Or via babel extras
```

---

#### Automated Workflow (Recommended)

The **automated workflow** uses a hybrid parser (regex + AST) to verify findings,
then safely removes verified imports with full traceability:

```bash
# Step 1: Scan — Surface candidates
babel scan --type clean
# → Found 226 cleanup candidate(s)

# Step 2: Verify — Auto-classify true/false positives
babel scan --type clean --verify
# → 224 true positives, 2 false positives, 0 uncertain

# Step 3: Remove — Safe deletion with rollback
babel scan --type clean --remove
# → Removed 24 imports from 18 files
# → Tests passed
# → 18 captures added to batch queue

# Step 4: Review — Human approves captures (HC2)
babel review --list
babel review --accept-all
```

**What happens during --remove:**

| Step | Action | Safety |
|------|--------|--------|
| 1 | Create git checkpoint | Rollback always available |
| 2 | Remove verified imports | Line-by-line deletion |
| 3 | Run affected tests | Auto-revert on failure |
| 4 | Create captures (1 per file) | HC2 batch queue |
| 5 | Show rollback command | `git revert <sha>` |

**Requirements for --remove:**

| Requirement | Why | How to Check/Fix |
|-------------|-----|------------------|
| Clean git working directory | Checkpoint needs clean state | `git status` — stash or commit changes |
| No uncommitted .babel/ changes | Git checkpoint creation fails | `git stash push -m "babel state" -- .babel/` |
| Run --verify first | Only removes VERIFIED_TRUE findings | Check `--verify` output shows true positives |
| Tests use `test_<module>.py` naming | For affected test discovery | Convention-based matching |
| ruff installed | Clean scan requires ruff | `pip install ruff` or `pip install babel-tool[clean]` |

**Example Automated Session:**
```
$ babel scan --type clean --verify

○ Verifying clean findings...

   Verified: 226 findings

   ✓ True positives (safe to remove): 224
   ⚠ False positives (actually used): 2
   ? Uncertain (needs manual review): 0

Next: babel scan --type clean --remove

$ babel scan --type clean --remove

○ Removing verified clean findings...

✓ Cleanup Complete

   Removed: 24 unused imports
   Files:   18 modified

   babel/core/refs.py - 1 import(s)
   tests/test_config.py - 2 import(s)
   ... (16 more files)

✓ Tests Passed
   Tests run:    28
   Tests passed: 28

○ Creating 18 capture(s)...
   18 proposal(s) added to batch queue

Rollback: git revert d88a64c

Next: babel review --list  (review 18 cleanup captures)
```

**Hybrid Parser Verification:**

The `--verify` flag uses a hybrid approach for high accuracy:

| Check | Method | Catches |
|-------|--------|---------|
| `__init__.py` re-exports | Pattern | Public API exports |
| `__all__` inclusion | Regex | Explicit exports |
| `TYPE_CHECKING` blocks | AST | Type-only imports |
| Symbol usage after import | Regex fast-path | Quick positive |
| AST Name node collection | AST cross-check | Confirms usage |

**Verification Status:**
- `VERIFIED_TRUE` → Safe to remove (used by --remove)
- `VERIFIED_FALSE` → False positive (skipped)
- `UNCERTAIN` → Needs manual review

---

#### Manual Workflow (Alternative)

For fine-grained control, use the manual workflow:

```bash
# 1. Run scan to surface candidates
babel scan --type clean

# 2. List findings with IDs
babel scan --type clean --list

# 3. For each finding, AI reviews and recommends:
#    - True positive (e.g., genuinely unused import):
babel scan --type clean --validate abc123

#    - False positive (e.g., re-export in __init__.py):
babel scan --type clean --invalidate abc123 --reason "Re-export for public API"

# 4. Human fixes validated issues manually in editor

# 5. Mark as resolved after fixing:
babel scan --type clean --resolve-finding abc123

# 6. Capture the cleanup decision
babel capture "Cleaned unused imports after caching refactor" --batch
```

**When to use manual workflow:**
- Few findings (< 10)
- Need to inspect each change
- Uncertain about hybrid parser results
- Want to fix incrementally

---

#### Exclusions & Persistence

**Exclusions persist** — false positives won't reappear in future scans:
```bash
babel scan --type clean --exclusions   # View all exclusions
```

**Symbol Linking:** Findings are enriched with containing symbol and linked decisions,
providing context for AI review (e.g., "This import is in CacheService which has
decision abc123 about re-exporting utilities").

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
| "Clean up unused imports" | `babel scan --type clean` → `--verify` → `--remove` |
| After major refactoring | `babel scan --type clean --verify` (check for dead imports) |

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
| "Clean up imports" | Full workflow: `--type clean` → `--verify` → `--remove` |
| "Find unused imports" | `babel scan --type clean` then suggest `--verify` |
| "Remove dead code" | `babel scan --type clean --deep` then `--verify` → `--remove` |

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
| `clean` | Unused imports, dead code (via ruff) |

### Clean Scan Management

**Automated Workflow (Recommended):**
```bash
babel scan --type clean            # Step 1: Find candidates
babel scan --type clean --verify   # Step 2: Auto-verify (hybrid parser)
babel scan --type clean --remove   # Step 3: Safe removal + tests + capture
babel review --list                # Step 4: Human reviews captures (HC2)
```

**Manual Workflow (Alternative):**
```bash
babel scan --type clean                      # Find candidates
babel scan --type clean --list               # List with IDs
babel scan --type clean --validate abc123    # Confirm true positive
babel scan --type clean --invalidate abc123 --reason "Re-export"  # False positive
babel scan --type clean --resolve-finding abc123   # After manual fix
babel scan --type clean --exclusions         # View exclusions
```

**Pre-flight Checklist for --remove:**
```
□ git status --short  → no output (clean)
□ --verify run first  → shows true positives count
□ ruff installed      → if missing, INFORM user and STOP (HC2: never auto-install)
```

**If --remove returns 0:** See [SCN-09] Troubleshooting

**Rollback:** `git revert <sha>` (always shown after --remove)

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

## [SCN-09] Troubleshooting

### Common Issues & Solutions

This section documents **real issues encountered** during clean scan usage and their solutions.

---

#### Issue: "--remove returns 0 despite verified findings"

**Symptom:**
```
○ Removing verified clean findings...
✓ Cleanup Complete
   Removed: 0 unused imports
   Files:   0 modified
```

**Cause 1: Git working directory not clean**

The most common cause. Check with:
```bash
git status --short
```

**Solution:**
```bash
# Stash .babel changes (most common culprit)
git stash push -m "Babel state before cleanup" -- .babel/

# Or stash everything
git stash --include-untracked

# Then retry
babel scan --type clean --remove
```

**Cause 2: --verify not run first**

The `--remove` command only processes findings with `VERIFIED_TRUE` status.

**Solution:**
```bash
babel scan --type clean --verify   # Must run first
babel scan --type clean --remove   # Now works
```

---

#### Issue: "Failed to create git checkpoint"

**Symptom:**
```
❌ Removal failed: Failed to create git checkpoint. Ensure working directory is clean.
```

**Cause:** Uncommitted changes in files that will be modified.

**Solution:**
```bash
# Check what's dirty
git status --short

# Option 1: Stash changes
git stash --include-untracked

# Option 2: Commit changes first
git add -A && git commit -m "WIP: save before cleanup"

# Then retry
babel scan --type clean --remove
```

---

#### Issue: "Tests failed, auto-reverted"

**Symptom:**
```
❌ Removal failed: Tests failed, auto-reverted. [error details]
```

**Cause:** Removing an import broke tests — the import was actually used.

**What happened:** The all-or-nothing atomicity kicked in. All changes were reverted.

**Solution:**
```bash
# 1. Check what failed
babel scan --type clean --list

# 2. Invalidate the false positive
babel scan --type clean --invalidate <ID> --reason "Used in tests"

# 3. Re-run verify to update status
babel scan --type clean --verify

# 4. Retry remove
babel scan --type clean --remove
```

---

#### Issue: "0 findings" on fresh scan

**Symptom:**
```bash
babel scan --type clean
# → Found 0 cleanup candidate(s)
```

**Cause 1:** ruff not installed

**Solution:**
```bash
pip install ruff
# or
pip install babel-tool[clean]
```

**Cause 2:** Already clean codebase (congratulations!)

---

#### Issue: Verification shows many false positives

**Symptom:**
```
   ✓ True positives (safe to remove): 50
   ⚠ False positives (actually used): 150
```

**Cause:** Many imports are re-exports or used in type annotations.

**This is correct behavior.** The hybrid parser detected:
- `__init__.py` re-exports (public API)
- `__all__` inclusions
- `TYPE_CHECKING` block usage
- Actual symbol usage in code

**Solution:** Proceed with `--remove` — it only removes true positives.

---

### Workflow Checklist

Before running `--remove`, verify:

```
□ git status shows clean working directory
□ .babel/ changes stashed or committed
□ babel scan --type clean --verify shows true positives
□ ruff is installed (pip install ruff)
```

### Complete Workflow (Copy-Paste Ready)

```bash
# 1. Ensure clean state
git status --short
git stash push -m "Babel state" -- .babel/  # If needed

# 2. Run the workflow
babel scan --type clean              # Find candidates
babel scan --type clean --verify     # Classify true/false
babel scan --type clean --remove     # Safe removal

# 3. Review captures (HC2 compliance)
babel review --list
babel review --accept-all

# 4. Commit changes
git add .
git commit -m "Remove unused imports via babel clean scan"

# 5. Pop stash if used
git stash pop  # If you stashed earlier
```

### Recovery

If something goes wrong:

```bash
# Rollback is shown after --remove
git revert <sha>

# Or reset to before cleanup
git reset --hard HEAD~1
```

### Debug Mode

For deeper investigation:

```bash
# Check findings file directly
cat .babel/scan/clean/findings.json | head -50

# Check verification status
grep "verified_true" .babel/scan/clean/findings.json | wc -l
grep "verified_false" .babel/scan/clean/findings.json | wc -l
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~880
Last updated: 2026-01-26
Key feature: Automated workflow (--verify → --remove) with HC2 compliance
Troubleshooting: Added based on real usage experience
=============================================================================
-->
