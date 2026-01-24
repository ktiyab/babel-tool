# babel init — Start a New Project

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=142 limit=65
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [INI-01] Intent | 32-82 | purpose, need, P1, grounded in reality | `offset=27 limit=60` |
| [INI-02] Command Overview | 84-127 | syntax, parameters, --need | `offset=79 limit=53` |
| [INI-03] Output & Messages | 129-187 | success, already exists, directory structure | `offset=124 limit=68` |
| [INI-04] Use Cases | 189-253 | examples, workflows, new project | `offset=184 limit=74` |
| [INI-05] AI Operator Guide | 255-308 | triggers, when to init, frictionless | `offset=250 limit=63` |
| [INI-06] Integration | 310-365 | status, capture, check, lifecycle | `offset=305 limit=65` |
| [INI-07] Quick Reference | 367-450 | cheatsheet, one-liners | `offset=362 limit=93` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[INI-" manual/init.md    # Find all sections
grep -n "INI-05" manual/init.md     # Find AI Operator Guide
```

---

## [INI-01] Intent

`babel init` starts a new Babel project with a **purpose grounded in need** (P1).

### The Problem It Solves

| Without Init | With Init |
|--------------|-----------|
| No persistent memory | `.babel/` directory created |
| Decisions scattered | Centralized decision graph |
| Purpose unclear | Explicit purpose + need captured |
| AI forgets between sessions | `babel why` retrieves context |

### Core Principle (P1: Purpose Grounded in Need)

Every project needs TWO things:

| Element | Question | Example |
|---------|----------|---------|
| **Need** | What problem are you solving? | "Teams struggle to coordinate work across timezones" |
| **Purpose** | What are you building? | "Build a task management app" |

```
WEAK:  "Build a task app"
       (No need — why does this matter?)

STRONG: "Build a task app"
        NEED: "Teams struggle to coordinate across timezones"
        (Purpose grounded in reality)
```

### Frictionless Onboarding

Init enables **frictionless user onboarding** [MK-IZ] — starting a project should be one command:

```bash
babel init "Build a REST API"
# Done. Project initialized.
```

### What It Creates

| Directory/File | Purpose |
|----------------|---------|
| `.babel/` | Root babel directory |
| `.babel/shared/` | Git-tracked team events |
| `.babel/local/` | Git-ignored personal events |
| `.babel/graph.db` | Knowledge graph database |
| Purpose event | First artifact in graph |

---

## [INI-02] Command Overview

```bash
babel init "purpose" [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Required** | `"purpose"` | What are you building? |
| **Recommended** | `--need`, `-n` | What problem are you solving? (P1) |

### Basic Init

```bash
babel init "Build a task management app"
```

### With Need (Recommended)

```bash
babel init "Build a task management app" \
  --need "Teams struggle to coordinate work across timezones"
```

### Parameter Details

**Purpose (Required)**
- First positional argument
- Describes what you're building
- Becomes the root artifact in the graph

**Need (Optional but Recommended)**
- Grounds purpose in reality (P1)
- Explains WHY this project matters
- Makes `babel why` queries more meaningful

### Directory Behavior

| If `.babel/` | Behavior |
|--------------|----------|
| Doesn't exist | Creates full structure |
| Exists | Shows message, suggests `check --repair` |

---

## [INI-03] Output & Messages

### Success — New Project

```bash
babel init "Build a REST API for user management" \
  --need "Need centralized user auth across services"
```

```
Initialized Babel project:
  Purpose: Build a REST API for user management
  Need: Need centralized user auth across services
  Location: .babel/

-> Next: babel capture "first decision" --batch
```

### Success — Minimal Init

```bash
babel init "Experiment with caching"
```

```
Initialized Babel project:
  Purpose: Experiment with caching
  Location: .babel/

-> Next: babel capture "first decision" --batch
```

### Already Exists

```bash
babel init "Another project"
```

```
Babel project already exists at .babel/

To verify integrity:
  babel check

To repair if needed:
  babel check --repair
```

### Directory Structure Created

```
.babel/
├── shared/          # Git-tracked team events
├── local/           # Git-ignored personal events
├── graph.db         # Knowledge graph
└── config.yaml      # Project configuration
```

---

## [INI-04] Use Cases

### Use Case 1: New Project with Full Context

```bash
cd my-project
babel init "REST API for user management" \
  --need "Need centralized user auth across services"
```

Best practice: Always include `--need` to ground purpose.

### Use Case 2: Minimal Exploration

```bash
babel init "Experiment with caching"
```

For quick experiments where need isn't clear yet.

### Use Case 3: After Cloning Existing Project

```bash
git clone <repo>
cd <repo>
# If .babel/ exists but needs verification:
babel check --repair
```

### Use Case 4: Team Project Setup

```bash
# Create project
babel init "E-commerce platform" \
  --need "Company needs modern online sales channel"

# Make first decisions
babel capture "Use Next.js for frontend" --batch --share

# Commit babel structure
git add .babel/
git commit -m "Initialize babel project"
```

### Use Case 5: Adding Babel to Existing Codebase

```bash
cd existing-project
babel init "Modernize legacy system" \
  --need "Current system can't scale to new requirements"

# Start capturing existing decisions
babel capture "Using PostgreSQL because data is relational" --batch
```

### Use Case 6: Reinitializing After Issues

```bash
# If .babel/ is corrupted
rm -rf .babel/
babel init "Same purpose" --need "Same need"
# Note: This loses all history - use only as last resort
```

---

## [INI-05] AI Operator Guide

### When AI Should Suggest Init

| Trigger | AI Action |
|---------|-----------|
| User says "new project" | "Let's start with `babel init`" |
| No `.babel/` directory | "Initialize babel first: `babel init 'purpose'`" |
| User describes project purpose | "Want to capture that? `babel init 'purpose' --need 'need'`" |
| `babel status` shows no project | Suggest init |

### When NOT to Init

| Context | Reason |
|---------|--------|
| `.babel/` already exists | Use `check --repair` instead |
| Cloned repo with `.babel/` | Already initialized |
| Temporary exploration | Maybe not worth initializing |

### Frictionless Experience

Init supports the **3-command simplicity** principle [LS-JO]:

```bash
babel init "purpose"           # Start
babel capture "decision" --batch  # Record
babel why "topic"              # Query
```

### Context Compression Survival

After compression, remember:

1. **Init is once per project** — only at the beginning
2. **Check for existing `.babel/`** before suggesting init
3. **Always recommend `--need`** — grounds purpose in reality

### AI-Safe Command

`babel init` is **non-interactive** — safe for AI operators:

```bash
babel init "purpose" --need "need"    # No prompt, immediate execution
```

### Detection Patterns

| User Statement | AI Response |
|----------------|-------------|
| "Let's start a new project" | "`babel init 'purpose' --need 'need'`" |
| "I want to build X because Y" | Extract purpose (X) and need (Y) for init |
| "Why doesn't babel work?" | Check if init was run |

---

## [INI-06] Integration

### With status

```bash
babel init "purpose"
babel status                  # Shows initialized project
```

### With capture

```bash
babel init "purpose"
babel capture "first decision" --batch  # Start capturing
```

### With check

```bash
# If init fails or .babel/ seems corrupted
babel check
babel check --repair
```

### With git

```bash
babel init "purpose"
git add .babel/
git commit -m "Initialize babel project"
```

### Lifecycle Position

```
init ←── YOU ARE HERE (First command ever)
    ↓
status (verify project)
    ↓
capture (start recording)
    ↓
why (query knowledge)
```

### Foundation Flow

Init is part of the **Foundation Flow** [FW-ON]:

```
1. init          # Create project
2. status        # Verify health
3. capture       # Begin recording
4. link          # Connect artifacts
```

---

## [INI-07] Quick Reference

### Basic Commands

```bash
# Minimal init
babel init "purpose"

# With need (recommended)
babel init "purpose" --need "problem"

# Check existing project
babel check
babel check --repair
```

### Full Start Workflow

```bash
# Initialize
babel init "Build REST API" --need "Need user management"

# Verify
babel status

# First capture
babel capture "Using FastAPI because team knows Python" --batch

# Review and share
babel review --accept-all
babel share <id>
```

### Init vs Check

| Command | When |
|---------|------|
| `init` | New project, no `.babel/` exists |
| `check` | Verify existing project |
| `check --repair` | Fix corrupted project |

### P1: Purpose Grounded in Need

| Element | Flag | Required |
|---------|------|----------|
| Purpose | (positional) | Yes |
| Need | `--need`, `-n` | No, but recommended |

### Directory Structure

```
.babel/
├── shared/          # ● Git-tracked
├── local/           # ○ Git-ignored
├── graph.db         # Knowledge graph
└── config.yaml      # Configuration
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `status` | Verify after init |
| `capture` | Start recording decisions |
| `check` | Verify/repair project |
| `why` | Query captured knowledge |

### Error Handling

| Error | Solution |
|-------|----------|
| "Already exists" | Use `check --repair` if needed |
| Permission denied | Check directory permissions |
| Corrupted | `rm -rf .babel/` then reinit (loses history) |

### When to Reinitialize

| Situation | Action |
|-----------|--------|
| Normal project | Never reinit — use `check` |
| Corrupted graph | Try `check --repair` first |
| Complete reset | `rm -rf .babel/` then `init` (loses history) |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~385
Last updated: 2026-01-24
=============================================================================
-->
