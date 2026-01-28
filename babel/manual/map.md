# babel map — Code Symbol Index for Strategic Loading

<!--
=============================================================================
QUICK NAVIGATION FOR AI OPERATORS
=============================================================================
To use: Read this file with offset=<Start-5> limit=<Length+10>
Example: For --index-clear, read offset=193 limit=40
=============================================================================
-->

## Table of Contents

| Section | Lines | Keywords | Offset Command |
|---------|-------|----------|----------------|
| [MAP-01] Intent | 38-85 | purpose, token efficiency, **multi-language, semantic bridge** | `offset=33 limit=50` |
| [MAP-02] Command Overview | 87-105 | all parameters, quick table | `offset=82 limit=25` |
| [MAP-03] --index | 107-155 | build index, whitelist, **gitignore, multi-language** | `offset=102 limit=50` |
| [MAP-04] --index-incremental | 157-176 | git diff, changed files, update | `offset=152 limit=25` |
| [MAP-05] --query | 178-245 | find symbol, **HTML/CSS/TypeScript symbols** | `offset=173 limit=70` |
| [MAP-06] --index-stats | 247-290 | statistics, **HTML/CSS symbols** | `offset=242 limit=45` |
| [MAP-07] --index-clear | 292-322 | clear, cleanup, .venv, pattern | `offset=287 limit=35` |
| [MAP-08] --except | 324-349 | exclude, selective clear | `offset=319 limit=30` |
| [MAP-09] Use Cases | 351-500 | examples, **frontend indexing, semantic bridge** | `offset=346 limit=155` |
| [MAP-10] Leveraging Commands | 502-539 | gather --symbol, babel why | `offset=497 limit=45` |
| [MAP-11] AI Operator Guide | 541-610 | compression, **multi-language efficiency** | `offset=536 limit=75` |
| [MAP-12] Architecture | 598-633 | storage, events, graph edges, **tree-sitter, graceful degradation** | `offset=593 limit=45` |
| [MAP-13] Quick Reference | 636-675 | cheatsheet, one-liners | `offset=631 limit=45` |

### Grep Patterns for Section Markers
```bash
grep -n "^\[MAP-" .babel/manual/map.md    # Find all sections
grep -n "MAP-07" .babel/manual/map.md     # Find --index-clear section
```

---

## [MAP-01] Intent

`babel map` creates and manages a **symbol index** that enables strategic loading of code and documentation without reading entire files.

### The Problem It Solves

When an AI assistant needs to understand code or documentation:

| Approach | Token Cost | Relevance |
|----------|------------|-----------|
| Read entire file | 100% of file | ~10% useful |
| Read entire folder | 100% of folder | ~5% useful |
| Query symbol index | ~5% of file | ~95% useful |

**Result**: 90%+ token waste eliminated.

### What Gets Indexed

| File Type | Symbols Extracted |
|-----------|-------------------|
| Python (`.py`) | Classes, functions, methods |
| JavaScript (`.js`, `.jsx`) | Classes, functions, methods |
| TypeScript (`.ts`, `.tsx`) | Classes, functions, methods, interfaces, types, enums |
| HTML (`.html`, `.htm`) | Container elements only (~35 structural tags) |
| CSS (`.css`) | ID selectors, component classes, custom properties, keyframes |
| Markdown (`.md`) | H1 (document), H2 (section), H3 (subsection) |

**HTML indexing** focuses on structural containers (header, nav, section, article, form, dialog, etc.) — not every HTML element. Elements are named by: id → aria-label → first class → tag only.

**CSS indexing** extracts architectural selectors:
- ID selectors (`#sidebar`, `#main-nav`)
- Component root classes (`.modal`, `.card`) — filters out BEM elements/modifiers and utility classes
- CSS custom properties (`--color-primary`, `--spacing-lg`)
- @keyframes animations

This enables the **semantic bridge** — linking decisions (WHY) to code, markup, and styles (WHAT).

### Core Principle

Symbols are **cache, not intent**. They're derived from Git-versioned source files and can be:
- Rebuilt from source at any time
- Cleared and re-indexed
- Treated as ephemeral lookup data

This is different from decisions, which are permanent intent records.

---

## [MAP-02] Command Overview

```bash
babel map [options]
```

| Category | Parameters | Purpose |
|----------|------------|---------|
| **Status** | `--status` | Show map status (default) |
| **Indexing** | `--index <path>...` | Build symbol index for paths |
| | `--index-incremental` | Update index for changed files |
| **Querying** | `--query <name>` | Find symbols by name |
| | `--index-stats` | Show index statistics |
| **Cleanup** | `--index-clear <pattern>...` | Clear symbols matching pattern |
| | `--except <pattern>` | Exclude pattern from clearing |
| **Map Generation** | `--refresh` | Regenerate project map |
| | `--update` | Incremental map update |

---

## [MAP-03] --index \<path\> [path...]

**Purpose**: Build symbol index for specified paths only.

**What gets indexed**:
- Python files (`*.py`) → classes, functions, methods
- JavaScript files (`*.js`, `*.jsx`) → classes, functions, methods
- TypeScript files (`*.ts`, `*.tsx`) → classes, functions, methods, interfaces, types, enums
- HTML files (`*.html`, `*.htm`) → structural container elements
- CSS files (`*.css`) → IDs, component classes, custom properties, keyframes
- Markdown files (`*.md`) → headings as document/section/subsection

**Gitignore respect**: By default, indexing respects `.gitignore` using `git ls-files`. Files ignored by git (node_modules, dist, etc.) are automatically excluded without explicit patterns.

**Why paths are required**: Whitelist principle — you specify what to index, not what to skip. Combined with gitignore respect, this ensures clean indexes.

```bash
# Index single path (indexes all supported file types)
babel map --index src/

# Index multiple paths
babel map --index babel-tool/ tests/

# Index frontend code (React/TypeScript)
babel map --index src/components/ src/styles/

# Index single file
babel map --index babel-tool/babel/cli.py

# Index documentation
babel map --index .babel/manual/
```

**Error when no path provided**:
```bash
$ babel map --index
Error: --index requires path(s) to index.

Usage: babel map --index <path> [<path>...]

Examples:
  babel map --index src/
  babel map --index babel-tool/ tests/
  babel map --index mypackage/core.py

Why: Indexing requires explicit paths to avoid accidentally
     indexing third-party code (.venv, node_modules, etc.)
```

---

## [MAP-04] --index-incremental

**Purpose**: Update index for files changed since last indexing (git diff based).

**When to use**: After modifying code, to update the index without full rebuild.

```bash
babel map --index-incremental
```

**Output**:
```
Indexing changed files (incremental)...

✓ Indexed 3 file(s), 15 symbol(s).
```

**Note**: This is safe by default — it only touches git-tracked files.

---

## [MAP-05] --query \<name\>

**Purpose**: Find symbols (classes, functions, methods, documentation sections) by name.

```bash
# Find a class
babel map --query "CodeSymbolStore"

# Find a function
babel map --query "clear_symbols"

# Partial match
babel map --query "Symbol"

# Find a documentation section
babel map --query "LNK-06"
```

**Output (code)**:
```
Found 1 symbol(s) matching "clear_symbols":

  [M] clear_symbols @ babel-tool/babel/core/symbols.py:122-158
      def clear_symbols(self, pattern, exclude)
      "Clear symbols matching a path pattern."

Load specific symbol: babel gather --file babel-tool/babel/core/symbols.py --limit 46
```

**Output (documentation)**:
```
Found 1 symbol(s) matching "LNK-06":

  [§] manual.link.LNK-06 @ .babel/manual/link.md:216-300
      ## [LNK-06] --to-commit
      "Bridge decisions to their implementing git commits AND code symbols"

Load section: babel gather --symbol "manual.link.LNK-06"
```

**Symbol type indicators**:

| Indicator | Type | Source |
|-----------|------|--------|
| `[C]` | Class | Python, JavaScript, TypeScript |
| `[F]` | Function | Python, JavaScript, TypeScript |
| `[M]` | Method | Python, JavaScript, TypeScript |
| `[mod]` | Module | Python |
| `[I]` | Interface | TypeScript |
| `[T]` | Type | TypeScript |
| `[E]` | Enum | TypeScript |
| `[H]` | Container | HTML structural elements |
| `[#]` | ID selector | CSS `#id` |
| `[V]` | Variable | CSS custom properties `--*` |
| `[A]` | Animation | CSS `@keyframes` |
| `[D]` | Document | Markdown H1 |
| `[S]` | Section | Markdown H2 |
| `[s]` | Subsection | Markdown H3 |

---

## [MAP-06] --index-stats

**Purpose**: Show current index statistics.

```bash
babel map --index-stats
```

**Output**:
```
Symbol Index Statistics
========================================
Status:  ✓ 3842 symbols indexed

Code Symbols:
  Classes:     158
  Functions:   232
  Methods:     891

TypeScript Symbols:
  Interfaces:  45
  Types:       23
  Enums:       12

HTML Symbols:
  Containers:  87

CSS Symbols:
  IDs:         34
  Variables:   56
  Animations:  8

Documentation Symbols:
  Documents:   41
  Sections:    312

Files:      156
```

The statistics are grouped by language/type. HTML containers include only structural elements (header, nav, section, etc.). CSS shows architectural selectors only (BEM elements and utilities are filtered out).

---

## [MAP-07] --index-clear \<pattern\> [pattern...]

**Purpose**: Clear symbols matching path patterns. Code symbols are cache, so clearing is safe.

```bash
# Clear .venv symbols
babel map --index-clear .venv

# Clear multiple patterns
babel map --index-clear .venv node_modules __pycache__

# Clear everything (use with caution)
babel map --index-clear .
```

**Output**:
```
Clearing symbols matching: .venv
  Cache: 0 symbols cleared
  Graph: 38119 nodes deleted

✓ Total cleared: 0 from cache, 38119 from graph

Remaining symbols:
  Classes:   157
  Functions: 227
  Methods:   868
  Files:     76
```

---

## [MAP-08] --except \<pattern\>

**Purpose**: Exclude a pattern when using `--index-clear`.

```bash
# Clear all symbols except those in babel-tool/babel/core
babel map --index-clear babel-tool --except babel-tool/babel/core
```

**Output**:
```
Clearing symbols matching: babel-tool
  (excluding: babel-tool/babel/core)
  Cache: 1006 symbols cleared
  Graph: 1278 nodes deleted

✓ Total cleared: 1006 from cache, 1278 from graph

Remaining symbols:
  Classes:   31
  Functions: 57
  Methods:   165
  Files:     11
```

---

## [MAP-09] Use Cases

### Use Case 1: Initial Setup (Starting from Zero)

When starting work on a project, index the codebase:

```bash
# Check if index exists
babel map --index-stats

# If empty, index project code (not .venv!)
babel map --index src/
babel map --index lib/

# Verify
babel map --index-stats
```

### Use Case 2: Finding Code Location

When you need to find where a class or function is defined:

```bash
# Find the class
babel map --query "GraphStore"

# Output shows: @ babel-tool/babel/core/graph.py:37-419

# Load just that code
babel gather --symbol "GraphStore"
```

### Use Case 3: After Context Compression

When AI context is compressed and you need to re-orient:

```bash
# Quick check - is the index available?
babel map --index-stats

# Find what you need
babel map --query "the_function_name"

# Load specific code
babel gather --symbol "ClassName.method_name"
```

### Use Case 4: Cleanup After Accidental Indexing

If you accidentally indexed third-party code:

```bash
# See current stats
babel map --index-stats

# Clear the noise
babel map --index-clear .venv node_modules

# Re-index only project code
babel map --index src/
```

### Use Case 5: Incremental Updates During Development

After modifying code, update the index:

```bash
# Update only changed files (fast)
babel map --index-incremental

# Or re-index specific path
babel map --index babel-tool/babel/commands/
```

### Use Case 6: Selective Cleanup

Keep core symbols, clear everything else:

```bash
# Clear all babel-tool EXCEPT core
babel map --index-clear babel-tool --except babel-tool/babel/core

# Then re-index what you need
babel map --index babel-tool/babel/commands/
```

### Use Case 7: Documentation Indexing

Index manuals to enable section-level navigation:

```bash
# Index manual documentation
babel map --index .babel/manual/

# Find a specific section
babel map --query "LNK-06"
# Output: [§] manual.link.LNK-06 @ .babel/manual/link.md:216-300

# Load just that section
babel gather --symbol "manual.link.LNK-06"
```

**Why this matters**:
- Navigate to specific manual sections without reading entire files
- Documentation becomes queryable alongside code
- Completes the semantic bridge: decisions link to BOTH code AND docs

### Use Case 8: Frontend/React Project Indexing

Index a full-stack application including frontend code:

```bash
# Index React/TypeScript frontend
babel map --index src/components/ src/hooks/ src/styles/

# Find a component
babel map --query "Modal"
# Output: [C] Modal @ src/components/Modal.tsx:15-89

# Find CSS for that component
babel map --query "modal"
# Output: [#] #modal-backdrop, .modal @ src/styles/components.css

# Find design tokens
babel map --query "--color"
# Output: [V] --color-primary, --color-secondary @ src/styles/tokens.css
```

**What gets indexed from frontend**:
- TypeScript: Components (classes/functions), interfaces, types, enums
- HTML: Structural containers (header, nav, section, form, dialog)
- CSS: ID selectors, component classes, custom properties, animations

**What's filtered out**:
- BEM elements (`.card__header`) and modifiers (`.btn--large`)
- Utility classes (`.flex`, `.p-4`, `.text-center`)
- Non-structural HTML elements (`<p>`, `<span>`, `<a>`)

### Use Case 9: Full Semantic Bridge Setup

Index everything for complete traceability:

```bash
# Index code, frontend, and documentation together
babel map --index babel-tool/ src/ .babel/manual/

# Now queries work across all:
babel map --query "link"
# Returns: CodeSymbolStore methods AND manual sections AND CSS link styles
```

---

## [MAP-10] Commands That Leverage babel map

### babel gather --symbol

Uses the map index to load specific code symbols without reading entire files.

```bash
# Load a specific class
babel gather --symbol "CodeSymbolStore"

# Load a specific method
babel gather --symbol "GraphStore.delete_nodes_by_type_pattern"

# Load multiple symbols
babel gather --symbol "Symbol" --symbol "CodeSymbolStore"
```

**How it works**:
1. `babel map` pre-indexes symbols with file:line locations
2. `babel gather --symbol X` queries the index
3. Returns only the relevant code section, not the whole file

### babel why

Uses code symbols to provide implementation context in answers.

```bash
babel why "symbol clearing"
```

**Output includes**:
```
The implementation lives in babel/core/symbols.py:34-54 for the Symbol class...
```

Code symbols appear in `babel why` results when they're semantically relevant to the query. This provides the "WHERE" to complement the "WHY" from decisions.

---

## [MAP-11] For AI Operators

### When to Use babel map

| Situation | Action |
|-----------|--------|
| Starting new session | `babel map --index-stats` — check if symbols exist |
| Need to find code | `babel map --query "name"` — locate without reading |
| Need manual section | `babel map --query "CMD-05"` — find specific section |
| After code changes | `babel map --index-incremental` — update index |
| Context compressed | Query symbols instead of re-reading files |
| Noise in index | `babel map --index-clear <pattern>` — cleanup |

### Token Efficiency Pattern

```bash
# WRONG: Read entire file to find one function
babel gather --file src/big_file.py    # 2000 lines, 50KB

# RIGHT: Query index, load only what's needed
babel map --query "my_function"         # Shows: line 450-480
babel gather --symbol "my_function"     # 30 lines, 1KB
```

**Token savings**: ~98%

### Documentation Efficiency Pattern

```bash
# WRONG: Read entire manual to find one section
babel gather --file .babel/manual/link.md      # 550 lines

# RIGHT: Query index, load only the section
babel map --query "LNK-06"              # Shows: manual.link.LNK-06
babel gather --symbol "manual.link.LNK-06"  # ~85 lines
```

**Benefits**:
- Navigate manuals without memorizing TOC offsets
- Documentation and code treated uniformly
- Enables `babel why` to surface relevant docs

### Recovery After Compression

When context is lost:

```bash
# 1. Orient with babel
babel status
babel tensions
babel questions

# 2. Find relevant code OR docs efficiently
babel map --query "relevant_class"
babel gather --symbol "relevant_class.relevant_method"

# 3. Find relevant manual sections
babel map --query "relevant_command"
babel gather --symbol "manual.cmd.CMD-05"

# 4. Continue work with minimal token usage
```

---

## [MAP-12] Architectural Notes

### Symbol Storage

Symbols are stored in two places:

1. **Cache** (`symbol_cache.json`) — Fast lookup, in-memory
2. **Graph** (SQLite) — Persistent, queryable via `babel why`

Both are cleared by `--index-clear` and rebuilt by `--index`.

### Event Sourcing

Each indexed symbol emits a `SYMBOL_INDEXED` event (HC1: append-only). The graph projects these into `code_symbol` nodes for queries.

### No Graph Edges to Decisions

Code symbols do NOT have explicit edges to decisions. They're matched dynamically via semantic/keyword similarity in `babel why` queries. This is why clearing symbols doesn't break decision links.

### Parser Architecture (Graceful Degradation)

The system uses **tree-sitter** when available, with **built-in fallbacks**:

| Parser | Languages | Fallback |
|--------|-----------|----------|
| tree-sitter | All (`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.html`, `.css`) | — |
| Built-in AST | Python (`.py`) | Always available |
| Built-in regex | Markdown (`.md`) | Always available |

**Without tree-sitter installed**: Python and Markdown indexing works. JS/TS/HTML/CSS silently skipped.

**To enable all languages**:
```bash
pip install tree-sitter tree-sitter-language-pack
```

---

## [MAP-13] Quick Reference

```bash
# Index
babel map --index <path>          # Build index for path(s)
babel map --index-incremental     # Update changed files only

# Query
babel map --query <name>          # Find symbol by name
babel map --index-stats           # Show statistics

# Cleanup
babel map --index-clear <pattern> # Clear matching symbols
babel map --index-clear <p> --except <e>  # Clear with exclusion

# Status
babel map --status                # Show map status (default)
babel map --refresh               # Full map regeneration
babel map --update                # Incremental map update
```

---

<!--
=============================================================================
END OF DOCUMENT
Total lines: ~680
Last updated: 2026-01-27
Changes:
- Added multi-language support: JavaScript, TypeScript, HTML, CSS
- Added gitignore respect via git ls-files
- Updated symbol type indicators for all languages
- Added TypeScript symbols: interface, type, enum
- Added HTML symbols: container (structural elements only)
- Added CSS symbols: ID selectors, component classes, custom properties, keyframes
- Added Use Case 8: Frontend/React Project Indexing
- CSS filtering: excludes BEM elements/modifiers and utility classes
- HTML filtering: indexes only ~35 structural container elements
- Added Parser Architecture section: tree-sitter graceful degradation
=============================================================================
-->
