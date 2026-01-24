# Babel Command Summary — Complete Reference

This document provides a detailed summary of all 32 Babel commands, organized by lifecycle phase.

---

## Overview

Babel is an **intent preservation system** that maintains coherence across AI sessions and team collaboration. It provides:

- **Persistent memory** for decisions, constraints, and reasoning
- **Semantic queries** via `babel why "topic"`
- **Evolution tracking** via challenge → resolve flow
- **Validation states** (proposed → consensus → validated)
- **Git-Babel bridge** connecting decisions to commits

---

## THE LIVING CYCLE

All commands map to phases in the Living Cycle:

```
ORIENT → RECALL → REMEMBER → VALIDATE → CONNECT → VERIFY → STRENGTHEN → REPEAT
```

| Phase | Purpose | Core Commands |
|-------|---------|---------------|
| ORIENT | Session orientation | status, tensions, questions |
| RECALL | Query before acting | why, list, history, gaps, suggest-links |
| REMEMBER | Capture knowledge | capture, question, capture-commit, share |
| VALIDATE | Human review | review, validation, endorse, evidence-decision |
| CHALLENGE | Disagree and revise | challenge, evidence, resolve, deprecate |
| CONNECT | Link artifacts | link, sync |
| VERIFY | Check alignment | coherence, scan, map |
| CONFIG | Setup and preferences | init, config, hooks, prompt, skill, memo, process-queue |
| REFERENCE | Help and principles | help, principles, gather |

---

## PHASE 1: ORIENT — Session Orientation

### status

**Intent:** Complete project overview for session orientation.

**What it shows:**
- Init memos (critical instructions)
- Event counts (shared vs local)
- Recent purposes (goals and context)
- Coherence state
- Validation status
- Pending proposals
- Project health score

**Key options:**
| Option | Purpose |
|--------|---------|
| `--full` | Show full content without truncation |
| `--git` | Show git-babel sync health |
| `--format` | Output format (json, table, list, summary) |

**When to use:** Every session start. Non-negotiable.

**Manual:** `manual/status.md`

---

### tensions

**Intent:** Surfaces open conflicts between artifacts — disagreements that need resolution.

**Core principle:** P4 — Disagreement is information, not conflict.

**What it shows:**
- Competing requirements
- Contradictory decisions
- Evolving understanding
- Unresolved debates
- Severity grading (critical, warning, info)

**Key options:**
| Option | Purpose |
|--------|---------|
| `--verbose`, `-v` | Show full details |
| `--full` | Show complete content without truncation |

**When to use:** Every session start alongside `status` and `questions`.

**Manual:** `manual/tensions.md`

---

### questions

**Intent:** Surfaces acknowledged unknowns — things explicitly not known yet.

**Core principle:** P10 — Holding ambiguity explicitly.

**What it shows:**
- What we don't know yet
- What needs research
- What requires user/stakeholder input
- What can't be decided now

**Key options:**
| Option | Purpose |
|--------|---------|
| `--verbose`, `-v` | Show full details |
| `--full` | Show complete content without truncation |

**When to use:** Every session start alongside `status` and `tensions`.

**Manual:** `manual/questions.md`

---

## PHASE 2: RECALL — Query Before Acting

### why

**Intent:** RECALL command — retrieves captured decisions, reasoning, and constraints to inform actions.

**Core principle:** Query before acting. Never assume.

**What it does:**
- Semantic query across knowledge graph
- Returns related decisions, constraints, reasoning
- Supports commit queries via `--commit SHA`

**Key options:**
| Option | Purpose |
|--------|---------|
| `"topic"` | Query by topic |
| `--commit SHA` | Query why a commit was made |

**When to use:** Before ANY code modification. Mandatory.

**Manual:** `manual/why.md`

---

### list

**Intent:** Browses and discovers artifacts in the knowledge graph.

**Key features:**
- No LLM required — fast, offline, direct graph access
- Token efficient — default limit 10, pagination via `--offset`
- Graph-aware — `--from` shows actual relationships

**Key options:**
| Option | Purpose |
|--------|---------|
| `[type]` | Filter by type (decisions, constraints, purposes, principles) |
| `--from ID` | Show connected artifacts (graph traversal) |
| `--orphans` | Show disconnected artifacts |
| `--filter KEYWORD` | Keyword search |
| `--limit N` | Max items (default: 10) |
| `--offset N` | Skip first N items (pagination) |
| `--all` | Show all (no limit) |

**When to use:** Exploring graph, finding artifacts, checking connections.

**Manual:** `manual/list.md`

---

### history

**Intent:** Shows recent activity — captures, reviews, links, and other events.

**What it shows:**
- Captures and their types
- Reviews and acceptance
- Links created
- Coherence checks
- Task completions

**Key options:**
| Option | Purpose |
|--------|---------|
| `-n N` | Show N most recent events |
| `--shared` | Only shared (team) events |
| `--local` | Only local (personal) events |

**When to use:** Task continuity, audit trail, checking recent activity.

**Manual:** `manual/history.md`

---

### gaps

**Intent:** Shows implementation gaps — decisions without commits and commits without decisions.

**Core principles:** P7 (Reasoning Travels), P8 (Evolution Traceable)

**Gap types:**
| Gap | Problem |
|-----|---------|
| Decision without commit | Intent not implemented |
| Commit without decision | Code lacks documented why |

**Key options:**
| Option | Purpose |
|--------|---------|
| `--commits` | Only show unlinked commits |
| `--decisions` | Only show unlinked decisions |
| `--from-recent N` | Check last N commits (default: 20) |

**When to use:** After implementing decisions, checking completeness.

**Manual:** `manual/gaps.md`

---

### suggest-links

**Intent:** Uses AI to match decisions with commits automatically.

**How it works:**
1. Analyzes recent commit messages
2. Compares with unlinked decisions
3. Suggests matches with confidence scores
4. You confirm and link

**Key options:**
| Option | Purpose |
|--------|---------|
| `--from-recent N` | Analyze last N commits (default: 5) |
| `--commit SHA` | Analyze specific commit |
| `--min-score N` | Minimum confidence (0-1, default: 0.3) |

**When to use:** Closing gaps efficiently with AI assistance.

**Manual:** `manual/suggest-links.md`

---

## PHASE 3: REMEMBER — Capture Knowledge

### capture

**Intent:** REMEMBER command — preserves decisions, reasoning, and constraints so they survive context compression and team turnover.

**Core principle:** Capture WHAT + WHY, not just WHAT.

**What to capture:**
- User makes a decision
- User states a constraint
- User explains reasoning
- Implementation approach is chosen
- Something is explicitly rejected

**Key options:**
| Option | Purpose |
|--------|---------|
| `"text"` | What to capture (decision, reasoning, constraint) |
| `--batch`, `-b` | Queue for review (mandatory for AI) |
| `--spec <id>` | Add specification to existing need |
| `--share`, `-s` | Share with team (default: local) |
| `--uncertain`, `-u` | Mark as provisional (P10) |
| `--domain`, `-d` | Expertise domain (P3 compliance) |

**AI-safe pattern:** Always use `--batch`

**Manual:** `manual/capture.md`

---

### capture --spec

**Intent:** Adds implementation specification to existing need.

**What to include:**
```
OBJECTIVE: What problem this solves
ADD: What must be introduced
MODIFY: What existing code must change
REMOVE: What to eliminate
PRESERVE: What must NOT be touched
RELATED: Dependencies that inform this change
```

**Usage:**
```bash
babel capture --spec <need_id> "OBJECTIVE: ...
ADD: ...
MODIFY: ...
PRESERVE: ..." --batch
```

**Why it matters:** Without spec capture, the implementation plan evaporates when context compresses.

**Manual:** `manual/capture.md`

---

### capture-commit

**Intent:** Captures the last git commit as a Babel event, creating a bridge between code changes and intent.

**What it enables:**
- `babel why --commit <sha>` — Why was this commit made?
- `babel gaps` — What decisions lack commits? What commits lack decisions?
- `babel suggest-links` — AI-assisted linking

**Key options:**
| Option | Purpose |
|--------|---------|
| `--async` | Queue for later processing (offline-first) |
| `--message "text"` | Custom description |

**When to use:** After meaningful commit, after implementing decision.

**Manual:** `manual/capture-commit.md`

---

### question

**Intent:** Captures acknowledged unknowns — things explicitly not known yet.

**Core principle:** P10 — Don't force decisions when uncertainty exists.

**Question vs Uncertain:**
| Command | When to Use |
|---------|-------------|
| `babel question` | True unknown needing research |
| `capture --uncertain` | Tentative decision that might change |

**Key options:**
| Option | Purpose |
|--------|---------|
| `"text"` | The question/unknown |
| `--batch` | Queue for review (mandatory for AI) |

**AI-safe pattern:** Always use `--batch`

**Manual:** `manual/question.md`

---

### share

**Intent:** Promotes a local artifact to shared (team) scope, making it visible across sessions and to team members.

**Scope difference:**
| Scope | Symbol | Git Status | Visibility |
|-------|--------|------------|------------|
| Local | `○` | `.gitignore` | Personal only |
| Shared | `●` | Tracked | Team visible |

**When to share:**
- Experiment validated
- Team decision made
- Architectural constraint
- Convention established

**Usage:**
```bash
babel share <event_id>
```

**Manual:** `manual/share.md`

---

## PHASE 4: VALIDATE — Human Review

### review

**Intent:** VALIDATE command — enforces human authority (HC2) over what enters the knowledge graph.

**Core principle:** HC2 — Humans decide what enters the system.

**Flow:**
```
AI captures → Proposal queued → Human reviews → Accepted/Rejected
```

**Key options:**
| Option | Purpose |
|--------|---------|
| `--list` | List proposals without prompting (AI-safe) |
| `--accept-all` | Accept all proposals |
| `--accept <id>` | Accept specific proposal |
| `--reject <id>` | Reject specific proposal |

**AI-safe pattern:** Use `--accept ID` or `--accept-all`, not bare `review`

**Manual:** `manual/review.md`

---

### validation

**Intent:** Checks validation status of decisions (P9: Dual-Test Truth).

**Validation states:**
| Symbol | State | Meaning |
|--------|-------|---------|
| `○` | Proposed | Captured, not reviewed |
| `◐` | Consensus only | Endorsed, no evidence |
| `◑` | Evidence only | Tested, not endorsed |
| `●` | Validated | BOTH consensus AND evidence |

**Usage:**
```bash
babel validation           # Check all
babel validation <id>      # Check specific
```

**Manual:** `manual/validation.md`

---

### endorse

**Intent:** Adds consensus to a decision — you or user agrees it's correct.

**Core principle:** P9 — Decisions need both consensus AND evidence.

**Usage:**
```bash
babel endorse <decision_id>
```

**When to use:** After reviewing decision and agreeing it's correct.

**Manual:** `manual/validation.md`

---

### evidence-decision

**Intent:** Adds evidence to a decision — proof it works.

**Core principle:** P9 — Decisions need both consensus AND evidence.

**Usage:**
```bash
babel evidence-decision <decision_id> "proof it works"
```

**When to use:** After tests pass, performance confirmed, user validated.

**Manual:** `manual/validation.md`

---

## PHASE 5: CHALLENGE — Disagree and Revise

### challenge

**Intent:** Creates tension against a decision — formally disagree with prior decision.

**Core principle:** P4 — Disagreement is information, not conflict.

**What challenges do:**
- Surface problems with existing decisions
- Build evidence for or against
- Resolve with explicit outcome
- Create evolution chain (P8)

**Key options:**
| Option | Purpose |
|--------|---------|
| `<target_id>` | Decision to challenge |
| `"reason"` | Why you disagree |
| `--hypothesis` | Proposed alternative |
| `--test` | How to test the hypothesis |

**Usage:**
```bash
babel challenge <id> "This approach causes performance issues"
```

**Manual:** `manual/challenge.md`

---

### evidence

**Intent:** Adds supporting evidence to a challenge — build the case.

**Usage:**
```bash
babel evidence <challenge_id> "supporting observation"
```

**When to use:** After challenge, to build case with facts.

**Manual:** `manual/challenge.md`

---

### resolve

**Intent:** Closes a challenge with an outcome.

**Outcomes:**
| Outcome | Meaning | When to use |
|---------|---------|-------------|
| `confirmed` | Original was correct | Challenge disproven by evidence |
| `revised` | Original superseded | New artifact replaces old |
| `synthesized` | Both partially right | Merged into new understanding |
| `uncertain` | Can't decide yet | Hold ambiguity (P6) |

**AI-safe pattern:**
```bash
babel resolve <id> --outcome revised --force --resolution "what replaces it"
```

**Manual:** `manual/challenge.md`

---

### deprecate

**Intent:** Marks an artifact as no longer valid, preserving its history while indicating it's been superseded.

**Core principle:** P7 — Knowledge evolves rather than accumulates.

**Why deprecate (not delete):**
| Delete | Deprecate |
|--------|-----------|
| Loses history | Preserves history |
| No context | Reason recorded |
| Evolution broken | Supersession explicit |

**Usage:**
```bash
babel deprecate <id> "reason for deprecation"
```

**When to use:** Decision superseded, context changed, technology migration.

**Manual:** `manual/deprecate.md`

---

## PHASE 6: VERIFY — Check Alignment

### coherence

**Intent:** Verifies that artifacts align with project purpose — detecting drift before it compounds.

**Core principle:** Verify AFTER changes. Drift is silent — you must detect it.

**Key options:**
| Option | Purpose |
|--------|---------|
| `--force` | Bypass cache, force fresh check |
| `--full` | Show complete content without truncation |
| `--qa` | QA/QC mode with detailed report |
| `--resolve` | Interactive resolution mode |
| `--batch` | Non-interactive mode (for AI, use with --resolve) |

**AI-safe pattern:** `babel coherence --resolve --batch`

**When to use:** After implementing changes, periodically during long sessions.

**Manual:** `manual/coherence.md`

---

### scan

**Intent:** Performs context-aware technical analysis of your project, identifying issues against the project's declared purpose and decisions.

**EAST Framework:**
- **E**valuate against purpose
- **A**nalyze constraints
- **S**urface conflicts
- **T**rack recommendations

**Types of analysis:**
| Type | Focus |
|------|-------|
| `health` | Overall project health, HC compliance |
| `architecture` | Patterns, event-driven design, state machines |
| `security` | Credential handling, input validation |
| `performance` | Bottlenecks, caching, efficiency |

**Usage:**
```bash
babel scan                  # Default: health
babel scan --type security  # Specific type
```

**When to use:** Deep technical review needed.

**Manual:** `manual/scan.md`

---

### map

**Intent:** Creates and manages a code symbol index that enables strategic loading of code without reading entire files.

**Token efficiency:**
| Approach | Token Cost | Relevance |
|----------|------------|-----------|
| Read entire file | 100% of file | ~10% useful |
| Read entire folder | 100% of folder | ~5% useful |
| Query symbol index | ~5% of file | ~95% useful |

**Key options:**
| Option | Purpose |
|--------|---------|
| `--status` | Show map status (default) |
| `--index <path>` | Build symbol index for paths |
| `--query <symbol>` | Query specific symbol |
| `--index-clear` | Clear symbol index |

**Core principle:** Code symbols are cache, not intent. They're derived from Git-versioned source files.

**Manual:** `manual/map.md`

---

## PHASE 7: CONNECT — Link Artifacts

### link

**Intent:** CONNECT command — creates edges between artifacts and purposes so they can inform `babel why` queries.

**Core principle:** Linking is knowledge creation, not documentation cleanup.

**What linking does:**
```
Artifact created → Link to purpose → Now discoverable via babel why
```

**Key options:**
| Option | Purpose |
|--------|---------|
| `<artifact_id>` | Artifact to link |
| `<purpose_id>` | Target purpose (default: active) |
| `--to-commit SHA` | Link decision to git commit |
| `--list` | Show unlinked artifacts |
| `--all` | Link all unlinked to active purpose |
| `--commits` | List decision-commit links |

**When to use:** Immediately after `review --accept`.

**Manual:** `manual/link.md`

---

### sync

**Intent:** Merges team's reasoning changes after git pull, ensuring your local Babel view integrates shared decisions from teammates.

**Core principle:** P7 — Reasoning must travel with artifacts.

**What sync does:**
- Integrates shared events from team
- Detects tensions immediately
- Makes team constraints available in `babel why`

**When to use:**
| Trigger | Reason |
|---------|--------|
| After `git pull` | New shared events from team |
| Start of work session | Ensure current with team |
| Before major decisions | Check for relevant team context |

**Manual:** `manual/sync.md`

---

## CONFIG — Setup and Preferences

### init

**Intent:** Starts a new Babel project with a purpose grounded in need (P1).

**Core principle:** P1 — Every project needs NEED + PURPOSE.

**What it creates:**
- `.babel/` directory structure
- Initial purpose artifact
- Configuration files

**Usage:**
```bash
babel init "Build a REST API"
babel init "Build a REST API" --need "Teams need unified data access"
```

**Manual:** `manual/init.md`

---

### config

**Intent:** Views and modifies Babel configuration settings.

**Configuration layers:**
| Layer | Location | Scope |
|-------|----------|-------|
| User | `~/.babel/config.yaml` | All projects |
| Project | `.babel/config.yaml` | Current project only |

**Key options:**
| Option | Purpose |
|--------|---------|
| `--show` | Show current configuration |
| `--set KEY VALUE` | Set configuration value |
| `--provider` | Set LLM provider |

**Manual:** `manual/config.md`

---

### hooks

**Intent:** Manages git hooks for automatic Babel integration with git workflows.

**Hooks installed:**
| Hook | Trigger | Action |
|------|---------|--------|
| `post-commit` | After git commit | Suggest capture-commit |
| `post-merge` | After git pull/merge | Suggest sync |
| `pre-push` | Before git push | Remind of pending reviews |

**Subcommands:**
```bash
babel hooks install     # Install all hooks
babel hooks uninstall   # Remove all hooks
babel hooks status      # Show status
```

**Manual:** `manual/hooks.md`

---

### prompt

**Intent:** Manages the system prompt for LLM integration, installing it to IDE-specific locations.

**Prompt types:**
| Type | Size | When |
|------|------|------|
| Full | Large | Full Babel capabilities |
| Mini | Small | When skills installed elsewhere |

**Key options:**
| Option | Purpose |
|--------|---------|
| `--install` | Install prompt to IDE location |
| `--mini` | Use lightweight prompt |
| `--status` | Show installation status |

**Manual:** `manual/prompt.md`

---

### skill

**Intent:** Manages skill export to AI platforms, enabling Babel workflows across different tools.

**Subcommands:**
| Subcommand | Purpose |
|------------|---------|
| `export` | Export skills to platform |
| `sync` | Re-export to previously exported platforms |
| `remove` | Remove exported skills from platform |
| `list` | List available skills |
| `status` | Show skill export status |

**Platform targets:**
- `claude-code` — Claude Code CLI
- `cursor` — Cursor IDE
- `codex` — OpenAI Codex
- `generic` — Generic Markdown output

**Manual:** `manual/skill.md`

---

### memo

**Intent:** Saves persistent user preferences that survive across sessions.

**Memo types:**
| Type | When Surfaces | Use Case |
|------|---------------|----------|
| Regular | Context-aware | "Use pytest for testing" |
| Init | Every session start | "Never bypass babel to access DB" |

**Key options:**
| Option | Purpose |
|--------|---------|
| `"content"` | Memo text to save |
| `--context` | Context where it applies |
| `--init` | Make foundational (surfaces in status) |
| `--list` | Show all memos |
| `--list-init` | Show only init memos |
| `--update ID` | Update memo content |
| `--remove ID` | Delete memo |
| `--promote-init ID` | Promote regular → init |
| `--demote-init ID` | Demote init → regular |

**Manual:** `manual/memo.md`

---

### process-queue

**Intent:** Processes async captured events that were queued for later extraction.

**Core principle:** HC3 — Offline-first. Core functionality works without network.

**What gets processed:**
- `capture-commit --async` — Commit captured for later analysis
- `capture --async` — Decision captured without immediate extraction
- Offline captures — Any capture made without LLM access

**Key options:**
| Option | Purpose |
|--------|---------|
| `--batch` | Non-interactive mode (mandatory for AI) |

**When to use:** After offline work, after `--async` captures, when LLM back online.

**Manual:** `manual/process-queue.md`

---

## REFERENCE — Help and Principles

### help

**Intent:** Displays comprehensive command reference for all Babel commands.

**Usage:**
```bash
babel help              # All commands, organized by category
babel <cmd> --help      # Detailed options for one command
```

**Manual:** `manual/help.md`

---

### principles

**Intent:** Displays the Babel framework principles for self-checking and grounding.

**Core principle:** P11 — A framework that cannot govern itself is incomplete.

**Principle categories:**
- Core Principles (P1-P6)
- System Principles (P7-P11)
- Human Constraints (HC1-HC6)

**Usage:**
```bash
babel principles
```

**Manual:** `manual/principles.md`

---

### gather

**Intent:** Enables parallel context collection from multiple sources in a single operation.

**Core principle:** Batch multiple sources when you know what you need.

**Decision tree:**
```
Q1: Do I know what sources I need?
  NO  → Use native tools (Read, Grep, Bash)
  YES → Q2

Q2: How many independent sources?
  1-2 → Use native tools
  3+  → babel gather
```

**Key options:**
| Option | Purpose |
|--------|---------|
| `--file <path>` | Add file to gather (repeatable) |
| `--grep "pattern:path"` | Grep with path |
| `--bash "command"` | Bash command |
| `--glob "pattern"` | Glob pattern |
| `--symbol <name>` | Query symbol from map |
| `--operation "desc"` | Task description |
| `--intent "why"` | Why gathering this context |

**Usage:**
```bash
babel gather \
  --file src/cache.py \
  --file src/api.py \
  --grep "CacheError:src/" \
  --operation "Fix caching bug" \
  --intent "Understand cache flow"
```

**Manual:** `manual/gather.md`

---

## AI-SAFE PATTERNS

Commands that need special flags for non-interactive use:

| Command | AI-Safe Pattern |
|---------|-----------------|
| capture | `--batch` required |
| capture --spec | `--batch` required |
| question | `--batch` required |
| coherence --resolve | `--batch` required |
| resolve | `--outcome X --force --resolution "text"` |
| review | `--accept ID` or `--accept-all` |
| deprecate | Reason as argument required |
| process-queue | `--batch` required |

---

## QUICK REFERENCE

### Session Start
```bash
babel status && babel tensions && babel questions
```

### Before Code Change
```bash
babel why "topic"
```

### Capture Decision
```bash
babel capture "WHAT because WHY" --batch
```

### Capture Spec
```bash
babel capture --spec <id> "OBJECTIVE: ... ADD: ... MODIFY: ... PRESERVE: ..." --batch
```

### After Review Accept
```bash
babel link <id>
```

### After Implementation
```bash
babel coherence
```

### Challenge Flow
```bash
babel challenge <id> "reason"
babel evidence <challenge_id> "data"
babel capture "replacement" --batch
babel resolve <challenge_id> --outcome revised --force --resolution "superseded"
babel deprecate <old_id> "superseded by new"
```

### Git-Babel Bridge
```bash
babel link <id> --to-commit HEAD
babel gaps
babel suggest-links
```

---
