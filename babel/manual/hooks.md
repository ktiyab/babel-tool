# babel hooks — Manage Git Hooks

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For Use Cases section, read offset=147 limit=60
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [HOK-01] Intent | 30-56 | purpose, git hooks, automation | `offset=25 limit=37` |
| [HOK-02] Command Overview | 58-78 | install, uninstall, status | `offset=53 limit=31` |
| [HOK-03] Subcommands | 80-144 | install, uninstall, status details | `offset=75 limit=75` |
| [HOK-04] Use Cases | 146-185 | examples, workflows | `offset=141 limit=50` |
| [HOK-05] AI Operator Guide | 187-213 | triggers, when to use | `offset=182 limit=37` |
| [HOK-06] Quick Reference | 215-255 | cheatsheet | `offset=210 limit=51` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[HOK-" manual/hooks.md
```

---

## [HOK-01] Intent

`babel hooks` manages **git hooks** for automatic Babel integration with git workflows.

### The Problem It Solves

| Without Hooks | With Hooks |
|---------------|------------|
| Manual capture-commit | Automatic on commit |
| Forget to sync | Auto-sync on pull |
| Manual reminders | Automatic prompts |

### What Hooks Do

| Hook | Trigger | Action |
|------|---------|--------|
| `post-commit` | After git commit | Suggest capture-commit |
| `post-merge` | After git pull/merge | Suggest sync |
| `pre-push` | Before git push | Remind of pending reviews |

### When to Install

- After `babel init` for new projects
- When enabling git integration
- To automate workflow reminders

---

## [HOK-02] Command Overview

```bash
babel hooks <subcommand>
```

| Subcommand | Purpose |
|------------|---------|
| `install` | Install git hooks |
| `uninstall` | Remove git hooks |
| `status` | Show hooks status |

### Quick Usage

```bash
babel hooks install     # Install all hooks
babel hooks status      # Check installation
babel hooks uninstall   # Remove hooks
```

---

## [HOK-03] Subcommands

### install

```bash
babel hooks install
```

Installs git hooks to `.git/hooks/`:

```
Installing git hooks...
  ✓ post-commit hook installed
  ✓ post-merge hook installed
  ✓ pre-push hook installed

-> Next: git commit  (Hooks will trigger)
```

### uninstall

```bash
babel hooks uninstall
```

Removes Babel git hooks:

```
Removing git hooks...
  ✓ post-commit hook removed
  ✓ post-merge hook removed
  ✓ pre-push hook removed

-> Next: babel status  (Continue without hooks)
```

### status

```bash
babel hooks status
```

Shows current hook installation:

```
Git Hooks Status:
  post-commit:  ✓ Installed
  post-merge:   ✓ Installed
  pre-push:     ✓ Installed

All hooks installed.
```

Or if not installed:

```
Git Hooks Status:
  post-commit:  ✗ Not installed
  post-merge:   ✗ Not installed
  pre-push:     ✗ Not installed

-> Next: babel hooks install
```

---

## [HOK-04] Use Cases

### Use Case 1: New Project Setup

```bash
babel init "purpose"
babel hooks install
# Now hooks will trigger on git operations
```

### Use Case 2: Check Status

```bash
babel hooks status
# See which hooks are installed
```

### Use Case 3: Disable Hooks

```bash
babel hooks uninstall
# Work without automatic prompts
```

### Use Case 4: Reinstall After Issues

```bash
babel hooks uninstall
babel hooks install
```

### Use Case 5: Team Onboarding

```bash
git clone <repo>
babel hooks install
# New team member has hooks
```

---

## [HOK-05] AI Operator Guide

### When AI Should Suggest Hooks

| Trigger | AI Action |
|---------|-----------|
| After `babel init` | "Install hooks: `babel hooks install`" |
| User asks about git integration | Explain hooks, suggest install |
| Missing automation | Check `babel hooks status` |

### AI-Safe Commands

All hooks subcommands are **non-interactive**:

```bash
babel hooks install      # No prompt
babel hooks uninstall    # No prompt
babel hooks status       # No prompt
```

### Context Compression Survival

1. **Hooks are optional** — enhance workflow, not required
2. **Three hooks** — post-commit, post-merge, pre-push
3. **Install once** — persists in .git/hooks/

---

## [HOK-06] Quick Reference

### Commands

```bash
babel hooks install     # Install all hooks
babel hooks uninstall   # Remove all hooks
babel hooks status      # Show status
```

### Hook Actions

| Hook | When | Does |
|------|------|------|
| post-commit | After commit | Suggests capture-commit |
| post-merge | After pull/merge | Suggests sync |
| pre-push | Before push | Reminds of pending reviews |

### Workflow

```bash
# Setup
babel init "purpose"
babel hooks install

# Now automatic:
git commit    # → Suggests capture-commit
git pull      # → Suggests sync
git push      # → Reminds of pending reviews
```

### Related Commands

| Command | Relationship |
|---------|--------------|
| `capture-commit` | Triggered by post-commit |
| `sync` | Triggered by post-merge |
| `review` | Reminded by pre-push |

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~345
Last updated: 2026-01-24
=============================================================================
-->
