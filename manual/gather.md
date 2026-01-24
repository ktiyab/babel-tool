# babel gather — Parallel Context Collection for AI Operations

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --symbol section, read offset=170 limit=50
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [GAT-01] Intent | 37-76 | purpose, parallel I/O, multi-source | `offset=32 limit=49` |
| [GAT-02] Command Overview | 77-108 | syntax, parameters, all flags | `offset=72 limit=41` |
| [GAT-03] --file | 109-139 | read file, multiple files | `offset=104 limit=40` |
| [GAT-04] --grep | 140-176 | search pattern, path filter | `offset=135 limit=46` |
| [GAT-05] --bash | 177-210 | command execution, safety | `offset=172 limit=43` |
| [GAT-06] --glob | 211-240 | file patterns, wildcards | `offset=206 limit=39` |
| [GAT-07] --symbol | 241-302 | **documentation symbols**, code, section | `offset=236 limit=70` |
| [GAT-08] Context Headers | 303-347 | operation, intent, manifest | `offset=298 limit=54` |
| [GAT-09] Output Options | 348-389 | format, output, limit, strategy | `offset=343 limit=51` |
| [GAT-10] Use Cases | 390-470 | **semantic bridge**, code+docs | `offset=385 limit=90` |
| [GAT-11] AI Operator Guide | 471-519 | when to use, when not, native tools | `offset=466 limit=58` |
| [GAT-12] Quick Reference | 520-573 | cheatsheet, patterns | `offset=515 limit=63` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[GAT-" manual/gather.md    # Find all sections
grep -n "GAT-07" manual/gather.md     # Find --symbol section
```

---

## [GAT-01] Intent

`babel gather` enables **parallel context collection** from multiple sources in a single operation.

### The Problem It Solves

| Without Gather | With Gather |
|----------------|-------------|
| Sequential file reads | Parallel collection |
| Multiple tool calls | Single command |
| No structured output | Manifest + corpus |
| Context scattered | Unified context block |

### Core Principle

**Batch multiple sources when you know what you need.**

```bash
# Instead of sequential:
Read file A → Read file B → Grep pattern → Run command

# Use parallel:
babel gather --file A --file B --grep "pattern" --bash "command"
```

### When to Use

**Decision Tree**:
```
Q1: Do I know what sources I need?
  NO  → Use native tools (Read, Grep, Bash)
  YES → Q2

Q2: How many independent sources?
  1-2 → Use native tools
  3+  → babel gather
```

---

## [GAT-02] Command Overview

```bash
babel gather [options]
```

| Category | Parameter | Purpose |
|----------|-----------|---------|
| **Sources** | `--file PATH` | Read file (repeatable) |
| | `--grep PATTERN[:PATH]` | Search pattern (repeatable) |
| | `--bash COMMAND` | Execute command (repeatable) |
| | `--glob PATTERN` | Find files by pattern (repeatable) |
| | `--symbol NAME` | Load code symbol (repeatable) |
| **Context** | `--operation NAME` | Operation name for header |
| | `--intent DESC` | Intent description for header |
| **Output** | `--format` | Output format (markdown, json) |
| | `--output FILE` | Write to file instead of stdout |
| **Limits** | `--limit KB` | Context size limit (default: 100KB) |
| | `--strategy` | Chunking strategy |

### Source Flags Are Repeatable

```bash
babel gather \
  --file src/api.py \
  --file src/cache.py \
  --grep "CacheError:src/" \
  --bash "git log -5"
```

---

## [GAT-03] --file

**Purpose**: Read one or more files.

```bash
# Single file
babel gather --file src/api.py

# Multiple files
babel gather --file src/api.py --file src/cache.py --file src/db.py
```

**Output**:
```
### [1/3] FILE: src/api.py
- Lines: 245 | Size: 8.2KB | Time: 5ms
```python
# file contents...
```

### When to Use --file vs Native Read

| Situation | Use |
|-----------|-----|
| Single file, small | Native Read tool |
| Single file, need context header | `--file` |
| Multiple files | `--file` (repeatable) |
| File + other sources | `--file` with other flags |

---

## [GAT-04] --grep

**Purpose**: Search for pattern, optionally limited to path.

### Basic Grep

```bash
babel gather --grep "class.*Error"
```

### Grep with Path Filter

```bash
# Format: "pattern:path"
babel gather --grep "def handle:babel-tool/babel/commands/"
```

**Output**:
```
### [1/1] GREP: def handle
- Lines: 23 | Size: 1.5KB | Time: 144ms
```
babel-tool/babel/commands/capture.py:502:def handle(cli, args):
babel-tool/babel/commands/check.py:217:def handle(cli, args):
...
```

### Multiple Greps

```bash
babel gather \
  --grep "class.*Exception:src/" \
  --grep "def handle_error:src/"
```

---

## [GAT-05] --bash

**Purpose**: Execute bash command and capture output.

```bash
babel gather --bash "git log -5 --oneline"
```

**Output**:
```
### [1/1] BASH: git log -5 --oneline
- Lines: 5 | Size: 0.3KB | Time: 45ms
```
8925a7c Update
c73a08f Fix cache invalidation
f95ecc0 Fix memo --list-init handler
...
```

### Safety

Commands are validated before execution. Dangerous commands are blocked.

### Multiple Commands

```bash
babel gather \
  --bash "git status" \
  --bash "git log -5" \
  --bash "ls -la src/"
```

---

## [GAT-06] --glob

**Purpose**: Find files matching pattern.

```bash
babel gather --glob "**/*.py"
```

**Output**: Lists matching files (not their contents).

### Glob + File

```bash
# Find files, then read specific ones
babel gather --glob "src/**/*.py"
# Review output, then:
babel gather --file src/api.py --file src/cache.py
```

### Common Patterns

| Pattern | Matches |
|---------|---------|
| `*.py` | Python files in current dir |
| `**/*.py` | Python files recursively |
| `src/*.ts` | TypeScript in src/ |
| `tests/test_*.py` | Test files |

---

## [GAT-07] --symbol

**Purpose**: Load code or documentation symbol by name.

```bash
# Load a class
babel gather --symbol "CodeSymbolStore"

# Load a method
babel gather --symbol "GraphStore.delete_nodes_by_type_pattern"

# Load multiple symbols
babel gather --symbol "Symbol" --symbol "CodeSymbolStore"

# Load a documentation section
babel gather --symbol "manual.link.LNK-06"
```

**Output (code)**:
```
### [1/2] SYMBOL: CodeSymbolStore
- Location: babel/core/symbols.py:45-180
- Type: class
```python
class CodeSymbolStore:
    """Store for code symbols..."""
    def __init__(self):
        ...
```

**Output (documentation)**:
```
### [1/1] SYMBOL: manual.link.LNK-06
- Location: manual/link.md:216-300
- Type: section
```markdown
## [LNK-06] --to-commit

**Purpose**: Bridge decisions to their implementing git commits...
```

### Prerequisite

Symbols must be indexed first:
```bash
# Index code AND documentation
babel map --index src/ manual/
```

### Symbol Types

| Type | Example | Source |
|------|---------|--------|
| Class | `"UserService"` | Python |
| Function | `"validate_input"` | Python |
| Method | `"UserService.authenticate"` | Python |
| Document | `"manual.link"` | Markdown H1 |
| Section | `"manual.link.LNK-06"` | Markdown H2 |
| Subsection | `"manual.link.LNK-06.example"` | Markdown H3 |

The **semantic bridge** enables loading both code implementations AND their related documentation in one gather operation.

---

## [GAT-08] Context Headers

**Purpose**: Add structured context to gather output.

### --operation

Names the operation:
```bash
babel gather --file api.py --operation "Fix API Bug"
```

**Output**:
```
════════════════════════════════════════════════════════════
CONTEXT GATHER: Fix API Bug
════════════════════════════════════════════════════════════
```

### --intent

Describes why you're gathering:
```bash
babel gather --file api.py --intent "Understand error handling flow"
```

**Output**:
```
## HEADER
- Intent: Understand error handling flow
- Total Size: 8.2 KB across 1 sources
- Gathered: 2026-01-24 02:31:22 UTC
```

### Full Header Example

```bash
babel gather \
  --file src/api.py \
  --file src/cache.py \
  --operation "Fix Caching Bug" \
  --intent "Trace cache invalidation path"
```

---

## [GAT-09] Output Options

### --format

```bash
# Markdown (default)
babel gather --file api.py --format markdown

# JSON (for parsing)
babel gather --file api.py --format json
```

### --output

Write to file instead of stdout:
```bash
babel gather --file api.py --output /tmp/context.md
```

### --limit

Set context size limit (default: 100KB):
```bash
babel gather --file large.py --limit 50
```

### --strategy

Chunking strategy when content exceeds limit:

| Strategy | Behavior |
|----------|----------|
| `size` | Simple size-based truncation |
| `coherence` | Keeps logical units together (default) |
| `priority` | Prioritizes by source importance |

```bash
babel gather --file large.py --limit 50 --strategy priority
```

---

## [GAT-10] Use Cases

### Use Case 1: Multi-File Context for Bug Fix

```bash
babel gather \
  --file src/api.py \
  --file src/cache.py \
  --file src/db.py \
  --grep "CacheError:src/" \
  --operation "Fix Cache Bug" \
  --intent "Understand cache invalidation flow"
```

### Use Case 2: Code Review Context

```bash
babel gather \
  --bash "git diff HEAD~5" \
  --bash "git log -5" \
  --file src/changed_file.py \
  --operation "Code Review" \
  --intent "Review recent changes"
```

### Use Case 3: Symbol Investigation

```bash
babel gather \
  --symbol "CacheService" \
  --symbol "CacheService.invalidate" \
  --grep "CacheService:tests/" \
  --operation "Understand CacheService"
```

### Use Case 4: Project Overview

```bash
babel gather \
  --glob "src/**/*.py" \
  --bash "wc -l src/**/*.py" \
  --operation "Project Structure"
```

### Use Case 5: Code + Documentation (Semantic Bridge)

Load implementation AND its documentation together:

```bash
babel gather \
  --symbol "LinkCommand" \
  --symbol "LinkCommand.link_to_commit" \
  --symbol "manual.link.LNK-06" \
  --operation "Understand link --to-commit" \
  --intent "See both implementation and docs"
```

This leverages the **semantic bridge** — gathering WHY (from decisions via `babel why`), WHAT (code symbols), and HOW TO USE (documentation sections) in one operation.

### Decision Tree: When to Use Gather

```
Need to read files?
├── 1-2 files → Use Read tool
└── 3+ files → babel gather --file

Need to search code?
├── Single search → Use Grep tool
└── Multiple searches or with files → babel gather --grep

Need command output?
├── Single command → Use Bash tool
└── Multiple commands or with files → babel gather --bash

Know exact sources needed?
├── Yes, 3+ sources → babel gather
└── No, exploring → Use native tools
```

---

## [GAT-11] AI Operator Guide

### When to Use babel gather

| Situation | Use Gather? |
|-----------|-------------|
| 3+ independent sources | Yes |
| Multi-source with context header | Yes |
| Need structured manifest | Yes |
| Single file read | No - use Read |
| Exploring unknown codebase | No - use native tools |
| Sequential dependency | No - use native tools |

### When NOT to Use

```bash
# DON'T: Single file
babel gather --file api.py  # Use Read tool instead

# DON'T: Exploring
babel gather --grep "something"  # Use Grep tool to explore first

# DON'T: Sequential dependency
babel gather --bash "command that depends on previous"  # Use sequential Bash
```

### Optimal Pattern

```bash
# GOOD: Known multi-source with context
babel gather \
  --file src/api.py \
  --file src/cache.py \
  --grep "Error:src/" \
  --operation "Fix Bug" \
  --intent "Trace error flow"
```

### Integration with Workflow

```
1. babel why "topic"           # Understand context
2. babel gather --file/--grep  # Collect code
3. [implement fix]
4. babel capture --batch       # Document decision
```

---

## [GAT-12] Quick Reference

```bash
# Multiple files
babel gather --file A --file B --file C

# Files + grep
babel gather --file api.py --grep "Error:src/"

# With context header
babel gather --file api.py --operation "Fix Bug" --intent "Trace flow"

# Symbol loading
babel gather --symbol "ClassName" --symbol "ClassName.method"

# Output to file
babel gather --file api.py --output /tmp/context.md

# JSON format
babel gather --file api.py --format json

# With size limit
babel gather --file large.py --limit 50
```

### Source Checklist

- [ ] 3+ independent sources?
- [ ] Added --operation name?
- [ ] Added --intent description?
- [ ] Sources don't depend on each other?

### Common Patterns

```bash
# Bug fix context
babel gather --file X --file Y --grep "error" --operation "Fix"

# Code review
babel gather --bash "git diff" --file changed.py

# Symbol investigation
babel gather --symbol "Class" --grep "Class:tests/"

# Code + documentation (semantic bridge)
babel gather --symbol "ClassName" --symbol "manual.cmd.CMD-05"
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~575
Last updated: 2026-01-24
Change: Added documentation symbol support (markdown sections loadable via --symbol)
=============================================================================
-->
