# Babel

**Augment your Coding LLM with persistent meaning, owned by you.**

[![Alpha](https://img.shields.io/badge/status-alpha-orange)](https://github.com/ktiyab/babel-tool)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## Quick Install

```bash
# Install
git clone https://github.com/ktiyab/babel-tool.git
cd babel-tool && ./install.sh

# Configure LLM (choose one)
export ANTHROPIC_API_KEY="sk-ant-..."   # Cloud: Claude (recommended)
# OR use local LLM: export BABEL_LLM_PROVIDER=ollama
```

> **Security:** `babel init` automatically adds `.env` to `.gitignore` to prevent credential leakage.

**Then, only 4 commands to start:**

```bash
babel prompt --install              # Once: teach your AI about Babel
babel init "Detailed information about your project purpose" \
 --need "Detailed information on the need/friction that led to the project" # Once: initialize your project
babel review                        # Periodically: validate AI proposals
```

That's it. Your AI assistant handles the 35+ commands; you just review.

> **Other AIs?** `babel prompt --install` and `babel skill export` auto-configure Claude Code and Cursor. For others, use `babel prompt > /path/to/ai/instructions.md` and `babel skill export --target generic` to export to a monolithic reference file.

**Requirements:** Python 3.10+ • **LLM options:** [Cloud API](#setting-up-api-keys) or [Local Ollama](#local-llm-ollama) • **Full config:** [LLM Configuration](#llm-configuration)

---

## What Babel Is

Babel is a CLI tool designed for Coding LLMs. It gives AI assistants capabilities they don't have natively: persistent memory across sessions, semantic retrieval that bridges decisions and code, coherence detection that catches drift before it compounds.

You don't need to learn 35 commands and their parameters. The system prompt, loaded into your coding assistant, encodes when to capture decisions, when to query meaning, when to check coherence, and how to use the manual when needed. The AI handles the mechanics. You just work.

What you own is the output: meaning artifacts that accumulate as you collaborate, stored in your repository, portable across any model, independent of any provider.

## The Shift

When meaning gets captured in reusable artifact forms instead of vanishing when a session ends, something fundamental changes.

Meaning becomes portable, it travels, and any LLM, any human, can pick it up and run with it. You're no longer trapped in that exhausting loop of re-explaining the same context for the fifth time to the fifth different model, watching your intent dissolve a little more with each retelling.

Reasoning leaves a trail you can actually follow. You see how thinking evolved, what paths were tried and abandoned, what was rejected and why it mattered. The journey becomes visible, not just the destination, and that visibility changes how you navigate.

You're not locked in anymore. Your meaning isn't hostage to one provider's logs or one model's context window. It belongs to you, it lives in your repository, and it goes wherever you go.

## The Key Insight

You are the continuous thread. The LLM doesn't remember; it re-orients.

Good meaning artifacts make that re-orientation so fast and frictionless that the seam between sessions disappears entirely. From where you sit, the work simply continues, as if the interruption never happened.

This is what distinguishes meaning artifacts from conventional deliverables. A finished report closes a chapter; you file it and move on. A meaning artifact keeps one open, deliberately, because it's designed to bring a future collaborator, whether human or LLM, into the problem space you've been building, so the thinking can pick up exactly where it left off rather than stumbling back to the beginning.

## How It Works

The system prompt encodes best practices directly into your coding assistant's behavior:

- Before modifying code, the AI queries existing decisions with `babel why`
- When you validate a decision, the AI captures it with `babel capture`
- After implementation, the AI checks alignment with `babel coherence`
- When linking reasoning to code, the AI connects them with `babel link`
- To make code searchable, the AI indexes symbols with `babel map`
- To load specific code without reading entire files, the AI uses `babel gather --symbol`

You don't issue these commands. The AI does, guided by the system prompt, following the manual when it needs details. The manual itself is written for AI operators, with sections like "AI Operator Guide" designed for machine reading.

The result is that best practices happen automatically. Instead of teaching humans "always check prior decisions before making changes," the discipline is encoded into the AI's behavior. You get the benefits without the cognitive overhead.

### The Semantic Bridge

Babel connects two worlds: meaning artifacts (decisions, purposes, constraints) and physical artifacts (code, documentation, stylesheets). The bridge works through indexing, shared tokens, and git integration.

**Indexing code symbols** with `babel map --index <path>` extracts searchable symbols:

| File Type | What Gets Indexed |
|-----------|-------------------|
| Python, JavaScript, TypeScript | Classes, functions, methods, interfaces, types |
| HTML | Structural containers (header, nav, section, form, dialog) |
| CSS | ID selectors, component classes, custom properties, keyframes |
| Markdown | Document structure (H1, H2, H3 headings) |

Once indexed, these symbols become searchable through `babel why`. When you query "user profile," you get back decisions about user profiles AND the code symbols like `UserProfileService` that share those semantic tokens. The AI can then load the specific code with `babel gather --symbol UserProfileService` without reading the entire file.

**Connecting decisions to commits** with `babel link --to-commit` creates full traceability:

```
Decision (WHY)
    │
    ├── implements ──→ Commit (git state)
    │
    └── implemented_in ──→ Symbols (WHAT)
                           └── UserService.get_user
                           └── UserService.cache_user
```

When the AI links a decision to a commit, Babel auto-detects which code symbols were touched by that commit and links them too. This enables bidirectional navigation:

- `babel why "caching"` → finds decisions AND the code that implements them
- `babel why --commit <sha>` → shows why a specific commit was made
- `babel list --from <decision>` → shows all linked commits and symbols

This eliminates token waste and guesswork. Instead of reading entire files or inferring intent from code, the AI queries the semantic bridge and gets exactly what it needs with full context.

## How Naming Bridges Thought and Code

When a developer writes `getUserProfile`, they're encoding a concept into a symbol. The same concept appears as `get_user_profile` in Python, `GetUserProfile` in Go, and `.user-profile` in CSS. These aren't three different things; they're one thing wearing three different costumes.

Babel's universal tokenizer strips away the costume and extracts the semantic tokens underneath:

```
getUserProfile      → [get, user, profile]
get_user_profile    → [get, user, profile]
GetUserProfile      → [get, user, profile]
.user-profile       → [user, profile]
```

The same tokenizer works on decision text written in natural language. When your decision says "cache user profiles for performance" and your code contains `UserProfileCache`, they share tokens. The connection isn't constructed by some linking mechanism; it's uncovered, because it was always there, embedded in the naming itself.

This is why querying "caching" returns decisions, code symbols, and documentation together. They share the same conceptual fingerprint, and the query finds all of them at once.

## What The AI Can Do

The system prompt gives your coding assistant these capabilities:

| Capability | What Happens |
|------------|--------------|
| Orient at session start | AI queries project status, open tensions, acknowledged unknowns |
| Recall before code changes | AI retrieves prior decisions relevant to what you're modifying |
| Capture when validated | AI preserves decisions with reasoning so they survive the session |
| Link to implementation | AI connects decisions to commits and code symbols |
| Detect drift | AI checks whether current code aligns with captured intent |
| Track evolution | AI records what was challenged, revised, or deprecated and why |

These aren't things you do manually. They're behaviors encoded in the system prompt that the AI executes as part of normal collaboration.

## What You Own

Everything Babel produces belongs to you:

**Meaning artifacts** live in your repository as `events.jsonl`, an append-only log that any tool can read. The knowledge graph is rebuilt from this source of truth, so your history is always auditable and recoverable.

**The artifacts are typed**: decisions, constraints, purposes, questions, tensions. Each type has distinct semantics, and they connect to each other and to code symbols, forming a navigable graph of project understanding.

**Portability is built in.** Switch models, switch providers, switch coding assistants. Your meaning artifacts stay in your repository, and any future collaborator, human or AI, can load them and continue where you left off.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      YOU                                    │
│              (the continuous thread)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │ work naturally
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   CODING LLM                                │
│           (with Babel system prompt loaded)                 │
│                                                             │
│   Reads manual when needed · Executes commands · Follows    │
│   encoded best practices · Handles mechanics transparently  │
└─────────────────────────┬───────────────────────────────────┘
                          │ babel commands
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 MEANING ARTIFACTS                           │
│                                                             │
│   Decisions · Constraints · Purposes · Questions · Tensions │
│                                                             │
│   Context snapshots you own, stored in your repository,     │
│   portable across any model or provider                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 UNIVERSAL TOKENIZER                         │
│                                                             │
│   Natural language  ──┐                                     │
│   Python symbols    ──┼──►  Semantic tokens  ──►  Unified   │
│   TypeScript symbols──┤                          index      │
│   CSS selectors     ──┤                                     │
│   Any naming format ──┘                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   KNOWLEDGE GRAPH                           │
│                                                             │
│   events.jsonl (append-only source of truth you own)        │
│   graph.db (query index, rebuildable from events)           │
│   Semantic links between artifacts and code symbols         │
└─────────────────────────────────────────────────────────────┘
```

## Principles

Babel is built on eleven principles that form a complete epistemology:

| Principle | What It Means |
|-----------|---------------|
| Bootstrap from Need | Start from problems, not solutions, and let the problem shape everything that follows |
| Emergent Ontology | Vocabulary emerges through use rather than being imposed upfront |
| Expertise Governance | Authority derives from domain knowledge, not title or seniority |
| Disagreement as Hypothesis | Conflict is information to be tested, not noise to be suppressed |
| Dual-Test Truth | Decisions need both consensus and evidence; either alone is fragile |
| Ambiguity Management | Hold uncertainty rather than forcing premature closure that you'll regret |
| Evidence-Weighted Memory | Living artifacts that evolve, not exhaustive archives that gather dust |
| Failure Metabolism | Failures are mandatory learning inputs, not embarrassments to hide |
| Adaptive Cycle Rate | Pace adapts to coherence level; slow down when confused, accelerate when aligned |
| Cross-Domain Learning | Track where ideas originate so borrowed concepts can be evaluated properly |
| Framework Self-Application | These principles apply to Babel itself; the tool must follow its own rules |

---

## Data Storage

Babel stores everything in your repository, giving you full ownership and version control:

```
your-project/
├── .git/                      # Git (unchanged)
├── .babel/
│   ├── shared/                # Team knowledge (Git-tracked)
│   │   └── events.jsonl       # Decision history, source of truth
│   ├── local/                 # Personal notes (Git-ignored)
│   │   └── events.jsonl       # Your scratch space
│   ├── refs/                  # Fast lookup indexes
│   │   ├── topics/            # Topic → artifact mapping
│   │   └── decisions/         # Decision indexes
│   ├── manual/                # Command reference (AI reads this)
│   └── graph.db               # Relationship cache (rebuildable)
└── .gitignore                 # Includes .babel/local/
```

**What travels with git** (shared with team):
- `.babel/shared/` contains team decisions and vocabulary
- The system prompt contains AI instructions

**What stays local** (git-ignored):
- `.babel/local/` holds personal experiments and drafts

### The Event Model

Everything in Babel is an immutable event, a record of something that happened:

```
Event:
  id: "AB-CD"                    # Short, human-readable ID
  type: "artifact_confirmed"     # What kind of event
  timestamp: "2025-01-14T..."    # When it happened
  data: { ... }                  # The content
  scope: "shared"                # Team or personal
```

Events are append-only. History is never rewritten. You can always trace back to understand how decisions evolved, what was tried, and why approaches were rejected.

### Scope: Shared vs Local

| Scope | Symbol | Git | Use Case |
|-------|--------|-----|----------|
| Shared | ● | Tracked | Team decisions, confirmed choices |
| Local | ○ | Ignored | Personal notes, experiments, drafts |

Default is local, which keeps experimentation safe. Use `--share` or `babel share` when you're ready to commit to a decision and share it with the team.

---

## LLM Configuration

Babel uses LLMs for semantic extraction, context-aware scanning, and coherence detection. The configuration supports both cloud and local providers, with settings that persist independently so you can switch without losing either setup.

### Nested LLM Structure

Babel maintains separate configurations for local and remote LLMs:

```yaml
llm:
  active: local | remote | auto   # Which to use
  local:                          # Persists independently
    provider: ollama
    model: llama3.2
    base_url: http://localhost:11434
  remote:                         # Persists independently
    provider: claude
    model: claude-sonnet-4-20250514
```

| Setting | Behavior |
|---------|----------|
| `local` | Use local LLM (Ollama or compatible) |
| `remote` | Use cloud provider (requires API key) |
| `auto` | Remote if API key available, else local |

Default is `auto` for backward compatibility.

### Setting Up API Keys

```bash
# Claude (Anthropic) — Default provider
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google Gemini
export GOOGLE_API_KEY="..."
```

Add to your shell profile (`~/.bashrc`, `~/.zshrc`) to persist across sessions.

### Local LLM (Ollama)

Run Babel entirely offline with a local LLM, keeping all data on your machine:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model and start
ollama pull llama3.2
ollama serve

# Configure Babel
export BABEL_LLM_PROVIDER=ollama
export BABEL_LLM_MODEL=llama3.2
```

Compatible servers include [Ollama](https://ollama.com), [LM Studio](https://lmstudio.ai), and [LocalAI](https://localai.io).

### Switching Providers

```bash
# View current configuration
babel config

# Switch between local and remote
babel config --set llm.active=local
babel config --set llm.active=remote

# Configure remote provider
babel config --set llm.remote.provider=claude
babel config --set llm.remote.model=claude-sonnet-4-20250514

# Configure local provider
babel config --set llm.local.provider=ollama
babel config --set llm.local.model=llama3.2
```

### What Uses the LLM

| Feature | With LLM | Without LLM |
|---------|----------|-------------|
| `babel capture` | Smart extraction of decisions and constraints | Pattern matching fallback |
| `babel why` | Semantic synthesis across artifacts | Keyword-based retrieval |
| `babel scan` | Context-aware code analysis | Not available |
| `babel coherence` | AI-powered drift detection | Basic consistency check |

Core features work without an API key. LLM enhances extraction quality and enables semantic features, but Babel remains functional offline.

---

## Smart Features

### Semantic Search

`babel why` understands meaning, not just keywords:

```bash
babel capture "We're using Postgres for the main database"

babel why "PostgreSQL"  # Finds it (canonical name)
babel why "database"    # Finds it (category)
babel why "pg"          # Finds it (abbreviation)
babel why "data store"  # Finds it (concept)
```

The universal tokenizer extracts semantic tokens from both your query and all artifacts, finding matches across naming conventions and natural language.

### Context-Aware Scanning

Unlike generic linters, `babel scan` knows your project's decisions and constraints:

```
Generic linter:
  "Consider using TypeScript for type safety"

babel scan:
  "Your constraint 'keep stack simple for junior devs'
   suggests TypeScript might add complexity.
   Consider: JSDoc types as a lighter alternative."
```

Scan types include `health`, `architecture`, `security`, `performance`, `dependencies`, and `clean` (for unused imports via ruff).

### Git Integration

Babel flows with git naturally. The `babel link --to-commit` command connects decisions to specific commits, enabling bidirectional navigation between reasoning and implementation. Optional hooks can capture commit context automatically.

---

## Team Collaboration

### New Team Member Onboarding

When joining an existing project:

```bash
# Clone the repository (includes .babel/shared/)
git clone <repo-url>
cd <project>

# Rebuild local graph from shared events
babel sync

# Orient yourself
babel status              # Project overview
babel why "architecture"  # Query specific topics
```

All shared reasoning travels with git. New team members inherit the full decision history.

### Sync After Pull

After pulling changes from teammates:

```bash
babel sync
```

This integrates new shared events into your local view. Constraints from teammates surface in `babel why`, and potential conflicts are detected as tensions.

### Integrity Check

Verify project health anytime:

```bash
babel check

# Output:
# ✓ .babel/ directory exists
# ✓ Shared events: 47 events
# ✓ Local events: 12 events
# ✓ Graph: 23 nodes, 45 edges
# ✓ Purpose defined
# ✓ Local data protected (.gitignore)
# All checks passed.
```

If issues are found, `babel check --repair` attempts automatic fixes by rebuilding the graph and ensuring proper gitignore configuration.

### Recovery

| Scenario | Recovery |
|----------|----------|
| Graph corrupted | `babel sync` rebuilds from events |
| Shared data deleted | `git checkout .babel/shared/` |
| Config corrupted | `babel config --set` or git checkout |
| Local events lost | By design (personal, unshared) |

The principle is simple: shared events are the source of truth and live in git. Everything else is either derived (rebuildable) or personal (your responsibility).

---

## FAQ

### Do I need to learn Babel commands?

Not really. If you use an AI assistant with the system prompt loaded, the AI handles most Babel operations for you. It suggests captures, queries context, and warns about conflicts. You can learn commands later if you want direct control.

### Do I need an LLM API key?

For small projects, no. Core features work offline using pattern matching. For growing projects, an API key is strongly recommended because it enables semantic extraction and synthesis. Your coding LLM (Claude Code, Cursor, etc.) runs babel commands, and with an API key, Babel's internal LLM pre-processes history before returning it, keeping your coding LLM effective even with hundreds of decisions.

For fully private operation, use [Ollama](#local-llm-ollama) to run a local LLM.

### How does my AI assistant know about Babel?

The system prompt contains instructions for AI assistants. When you load it via `babel prompt --install` or add it to your AI's custom instructions, the AI learns to use Babel automatically. The manual is structured for machine reading, so the AI can consult specific sections when it needs details about a command.

### Which AI assistants work with Babel?

Any AI that accepts custom instructions: Claude (Anthropic), ChatGPT (OpenAI), Cursor, Cody, and others. The `babel skill export` command auto-detects your platform and installs the appropriate configuration.

### How is this different from code comments?

Comments describe what code does. Babel captures why decisions were made. Comments live in code and can rot as context changes. Babel captures live in a queryable knowledge graph that your AI can search semantically.

### How is this different from ADRs?

Architecture Decision Records are valuable but heavyweight. Babel is lightweight capture that can become ADRs if needed. Capture first, formalize later. ADRs also aren't queryable by AI in real-time during coding sessions; Babel is.

### Does this add overhead to my workflow?

Minimal, and mostly handled by AI. When you explain something to your AI assistant, it suggests capturing. When you ask "why," it queries Babel. You don't have to remember to use it.

### What if I capture something wrong?

Events are immutable, but you can capture corrections and deprecate outdated decisions. Babel shows the evolution, including changed minds. Knowing why something changed matters as much as knowing what it is now.

### How does team collaboration work?

Shared decisions in `.babel/shared/` are git-tracked. When you push, teammates get your reasoning. When you pull, you get theirs. `babel sync` integrates new events. Everyone's AI assistant sees the same project context.

### Is my data private?

Local captures (`.babel/local/`) never leave your machine. Shared captures go where your git repo goes. LLM features send data to your configured provider unless you use a local LLM like Ollama.

---

## Documentation

[Manual](./manual/): Command reference for AI operators. The manual is structured for machine reading, with sections like [CMD-05] AI Operator Guide designed for your coding assistant to consult when executing commands.

[System Prompt](./manual/babel_system_prompt.md): The encoded best practices that teach your AI when and how to use Babel commands.
