# Babel — Intent Preservation for Code

> *AI-native knowledge system. Captures reasoning. Answers 'why?'. Works through your AI assistant.*

[![Alpha](https://img.shields.io/badge/status-alpha-orange)](https://github.com/ktiyab/babel-tool)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## Quick Install

```bash
# Clone and install
git clone https://github.com/ktiyab/babel-tool.git
cd babel-tool
./install.sh

# Verify
babel --help
```

**Requirements:** Python 3.9+

**Alternative methods:** See [Installation & Configuration](#installation--configuration) below.

---

## The Problem

You join a project. The code works. But **WHY** was it built this way?

- Why PostgreSQL instead of MongoDB?
- Why this particular caching pattern?
- Why can't we just refactor this module?

You check Git blame. It shows **WHO** and **WHEN**. Not **WHY**.

You search for documentation. It's outdated, incomplete, or missing entirely.

You ask around. The person who made the decision left six months ago. The Slack thread expired. The meeting was never recorded.

**The reasoning is gone.**

Every codebase accumulates these ghosts — decisions that made sense once, for reasons no one remembers. Teams waste hours reverse-engineering intent. Refactors break things because constraints were invisible. New members feel lost in code that works but doesn't explain itself.

**Babel captures the WHY before it's lost.**

---

## The Solution

Babel is a lightweight tool that preserves reasoning alongside code.

```
Code tells WHAT exists.
Git tells WHEN it changed.
Babel tells WHY it's there.
```

**Simple workflow:**

```bash
# Capture reasoning when you have it
babel capture "Chose SQLite for offline support — 
               PostgreSQL requires network, users need airplane mode"

# Query reasoning when you need it
babel why "database"
# → Returns the full context, not just "we use SQLite"
```

**Babel is:**
- A knowledge system designed for AI assistants
- A structured memory that grows with your project
- A way to answer "why?" months or years later
- Commands you can use directly, but usually won't need to

**Babel is not:**
- A replacement for Git (it complements Git)
- A documentation system (it captures decisions, not docs)
- Another tool to learn (your AI handles it)
- Intrusive (it stays quiet until you need it)

---

## AI-Native Design

**Babel is built for AI assistants to use on your behalf.**

You *can* run `babel` commands directly. But mostly, you won't need to. Your AI assistant reads Babel's knowledge and acts accordingly — suggesting captures, checking context, warning about conflicts.

```
┌─────────────────────────────────────────────────────────────┐
│                    YOU (Developer)                          │
│                         ↕                                   │
│            AI Assistant (Claude, GPT, etc.)                 │
│               ↙                    ↘                        │
│     Babel knowledge store      Your codebase                │
│        (.babel/)                   (code)                   │
│               ↘                    ↙                        │
│          Informed, contextual assistance                    │
└─────────────────────────────────────────────────────────────┘
```

**What the AI does automatically:**

| You do this | AI does this behind the scenes |
|-------------|--------------------------------|
| Explain a decision | Suggests capturing it in Babel |
| Ask "why is it this way?" | Queries `babel why` for context |
| Propose a refactor | Checks constraints, warns of conflicts |
| Discuss architecture | Offers to record the reasoning |
| Start new work | Loads relevant context from Babel |

**The result:** You focus on building. The AI handles knowledge management.

### Reducing Cognitive Overhead

**Without Babel + AI:**
```
You think: "I should document this decision"
You do:    Open docs → find right place → write ADR → 
           format it → commit → hope someone reads it
You feel:  "That took 20 minutes. I'll skip it next time."
```

**With Babel + AI:**
```
You say:   "Let's use Redis for caching because of the rate limits"
AI says:   "Good reasoning. Want me to capture that decision?"
You say:   "Yes"
AI does:   babel capture --share "Redis for caching..."
You feel:  "That took 5 seconds."
```

The AI makes doing the right thing effortless.

### The Two-LLM Architecture

**Babel works best with two AI layers working together.**

```
┌─────────────────────────────────────────────────────────────────────┐
│  YOUR CODING LLM (Local)                                            │
│  Claude Code, Cursor, Gemini CLI, Cody, etc.                        │
│                                                                     │
│  • Runs babel commands on your behalf                               │
│  • Writes and reviews code                                          │
│  • Makes decisions with you                                         │
│                         │                                           │
│                         ▼                                           │
│            ┌─────────────────────────┐                              │
│            │  babel why "caching"    │                              │
│            └─────────────────────────┘                              │
│                         │                                           │
└─────────────────────────│───────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BABEL'S INTERNAL LLM (Remote via API key)                          │
│  Anthropic, OpenAI, or Google API                                   │
│                                                                     │
│  • Summarizes large decision history                                │
│  • Structures context for your coding LLM                           │
│  • Extracts artifacts from conversations                            │
│  • Runs coherence analysis                                          │
│                         │                                           │
│                         ▼                                           │
│            ┌─────────────────────────┐                              │
│            │  Optimized, structured  │                              │
│            │  context returned       │                              │
│            └─────────────────────────┘                              │
│                         │                                           │
└─────────────────────────│───────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  YOUR CODING LLM receives summarized context                        │
│  → Can reason about project history without context overload        │
└─────────────────────────────────────────────────────────────────────┘
```

**Why two LLMs?**

| Single LLM (no API key) | Two LLMs (with API key) |
|-------------------------|-------------------------|
| Raw decision history sent to coding LLM | History summarized by Babel's LLM first |
| Context window fills up quickly | Context stays optimized |
| Works for small projects | Scales to large project history |
| Pattern matching for extraction | Intelligent semantic extraction |

**The tradeoff:**
- **Without API key:** Babel works offline. Core features function. But as your decision history grows, your coding LLM may struggle with context overload — too much raw history, not enough synthesis.
- **With API key:** Babel's internal LLM pre-processes history, summarizes patterns, and delivers structured context. Your coding LLM stays focused and effective even with hundreds of decisions.

**Recommendation:** Set up an API key early. The cost is minimal (pennies per query), and it prevents context degradation as your project grows.

---

## Babel + Git: Complementary Layers

Babel doesn't compete with Git. They solve different problems.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: BABEL    Intent — WHY it was built this way       │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: GIT      History — WHAT changed and WHEN          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: CODE     Implementation — WHAT exists now         │
└─────────────────────────────────────────────────────────────┘
```

**Side by side:**

| Question | Git | Babel |
|----------|-----|-------|
| What changed? | ✓ Diff shows exact changes | |
| When did it change? | ✓ Commit timestamp | |
| Who changed it? | ✓ Author attribution | |
| Why was it changed? | ~72 character message | ✓ Full reasoning with context |
| What constraints exist? | | ✓ Captured boundaries |
| What alternatives were considered? | | ✓ Decision trade-offs |
| Does this align with our goals? | | ✓ Coherence checking |

**Git commit message:**
```
fix: switch from Postgres to SQLite
```

**Babel capture:**
```
Switching from PostgreSQL to SQLite.

Reasons:
- Users need offline access (mobile app, airplane mode)
- Data volume is small (<100MB per user)  
- PostgreSQL requires network, adds deployment complexity

Trade-offs accepted:
- No concurrent write scaling (acceptable for single-user)
- Limited query capabilities (acceptable for our use case)

Revisit if: Multi-user sync becomes a requirement
```

**Use both.** Git for code history. Babel for intent history.

### Git-Babel Bridge

Beyond complementary storage, Babel actively bridges decisions to commits:

```bash
# After implementing a decision, link it to the commit
babel link abc123 --to-commit HEAD

# Before refactoring, understand why the commit exists
babel why --commit a1b2c3d4
# → Shows linked decisions: "Use Redis because of rate limits"

# Find implementation gaps
babel gaps
# → Decisions without commits (unimplemented intent)
# → Commits without decisions (undocumented changes)

# Get AI suggestions for linking
babel suggest-links
```

This bridges **intent** (Babel decisions) with **state** (Git commits), making reasoning truly travel with code.

---

## Quick Start

**Get running in 5 minutes.**

### 1. Install

```bash
# From PyPI
pip install babel-intent

# Or from source (for development/testing)
git clone https://github.com/ktiyab/babel-tool.git
cd babel && pip install -e ".[dev]"
```

### 2. Initialize your project

```bash
cd your-project
babel init "Build offline-first mobile app" \
    --need "Field workers lose data when connectivity drops"
```

This creates a `.babel/` directory with your project's need (the problem) and purpose (the solution).

### 3. Capture a decision

```bash
babel capture "Using React Native because:
- Team has React experience
- Need iOS + Android from single codebase
- Offline support via local storage works well"
```

### 4. Query later

```bash
babel why "React Native"
```

Returns the full reasoning you captured.

### 5. Check project health

```bash
babel status    # Quick overview
babel scan      # AI-powered analysis
```

### 6. (Optional) Connect your AI assistant

```bash
babel prompt    # Outputs system prompt for AI
```

Copy this to your AI assistant's custom instructions. Now your AI:
- Suggests capturing decisions when you explain them
- Checks Babel context before answering questions
- Warns you about constraint conflicts

**That's it.** You're using Babel.

Everything else is optional. Babel works quietly in the background — directly via commands, or through your AI assistant.

---

## When to Use What

**Quick reference for daily use:**

| Situation | Command | Why |
|-----------|---------|-----|
| Made a decision | `babel capture "..."` | Save reasoning while fresh |
| Team decided something | `babel capture "..." --share` | Share with team via Git |
| Uncertain about a decision | `babel capture "..." --uncertain` | Mark as provisional (P6) |
| Wondering why something exists | `babel why "topic"` | Query captured reasoning |
| Starting work on unfamiliar code | `babel status` | See project purpose and key decisions |
| Before refactoring | `babel why "module"` | Understand constraints before changing |
| Disagree with a decision | `babel challenge <id> "reason"` | Record disagreement as information |
| Have evidence for/against challenge | `babel evidence <id> "what you learned"` | Build toward resolution |
| Ready to resolve dispute | `babel resolve <id> --outcome ...` | Close with evidence-based outcome |
| Check open disputes | `babel tensions` | See what's contested vs. settled (sorted by severity) |
| View tension severity | `babel tensions --full` | See critical/warning/info levels |
| Agree with a decision | `babel endorse <id>` | Add your consensus (P5) |
| Have evidence for a decision | `babel evidence-decision <id> "..."` | Ground decision in reality (P5) |
| Check decision validation | `babel validation` | See groupthink/unreviewed risks |
| Don't know something important | `babel question "How should we..."` | Record open question (P6) |
| Check acknowledged unknowns | `babel questions` | See what we haven't decided yet |
| Answer an open question | `babel resolve-question <id> "..."` | Close when evidence is sufficient |
| Mark decision as outdated | `babel deprecate <id> "reason"` | De-prioritize without deleting (P7) |
| Check if following principles | `babel principles` | Self-check reference (P11) |
| Get extended help on topics | `babel help <topic>` | Detailed workflows and explanations |
| Verify project integrity | `babel check` | Diagnose issues, suggest recovery |
| Reviewing architecture | `babel scan --type architecture` | Get AI analysis of design |
| Security review | `babel scan --type security` | Context-aware vulnerability check |
| After `git pull` | `babel sync` | Merge teammates' reasoning |
| New team member onboarding | `babel status` + `babel scan` | Understand project quickly |
| After implementing a decision | `babel link <id> --to-commit <sha>` | Bridge intent to code (P7, P8) |
| Before refactoring code | `babel why --commit <sha>` | Understand why commit exists |
| Check implementation gaps | `babel gaps` | Find unlinked decisions/commits |
| Find unlinked decisions only | `babel gaps --decisions` | Intent without implementation |
| Find unlinked commits only | `babel gaps --commits` | Implementation without intent |
| AI link suggestions | `babel suggest-links` | Match decisions to commits |
| Analyze specific commit count | `babel suggest-links --from-recent N` | Focus on last N commits |
| List decision-commit links | `babel link --commits` | See all bridged artifacts |
| Git-babel sync health | `babel status --git` | Overview of bridge status |
| After reviewing proposals | `babel link <id>` | Connect artifact to purpose (P9) |
| See unlinked artifacts | `babel link --list` | Find orphans that can't inform `why` |
| Bulk fix unlinked | `babel link --all` | Link all orphans to active purpose |
| Browse artifacts by type | `babel list` | See counts, then drill down |
| Find specific artifact type | `babel list decisions` | List decisions (10 by default) |
| Search artifacts | `babel list decisions --filter "cache"` | Keyword filter |
| Explore artifact connections | `babel list --from <id>` | Graph traversal from artifact |
| Find disconnected artifacts | `babel list --orphans` | Artifacts with no connections |
| Page through artifacts | `babel list decisions --offset 10` | Skip first 10, show next page |
| Save preference | `babel memo "instruction"` | Persists across sessions |
| Save with context | `babel memo "..." --context testing` | Surfaces only in relevant contexts |
| Save init memo | `babel memo "..." --init` | Foundational instruction (surfaces in status) |
| List memos | `babel memo --list` | Show saved preferences |
| List init memos | `babel memo --list-init` | Show only foundational instructions |
| Promote to init | `babel memo --promote-init <id>` | Make memo foundational |
| AI-detected patterns | `babel memo --candidates` | Show repeated instruction patterns |
| Resolve coherence issues | `babel coherence --resolve` | Interactive AI-guided resolution |
| Resolve issues (AI mode) | `babel coherence --resolve --batch` | Non-interactive for AI operators |
| Review pending proposals | `babel review` | See AI-extracted insights for approval |
| Accept all proposals | `babel review --accept-all` | Batch accept (AI-safe) |
| Accept specific proposal | `babel review --accept <id>` | Accept one by ID |
| Generate project map | `babel map --refresh` | Create structure map for LLMs |
| Update project map | `babel map --update` | Incremental update (changed files) |
| Process offline queue | `babel process-queue` | Process queued extractions |
| Capture last commit | `babel capture-commit` | Extract reasoning from commit |
| Set up AI assistant | `babel prompt --install` | Install system prompt to IDE location |
| Check prompt status | `babel prompt --status` | See if prompt is installed/outdated |
| After upgrading babel | `babel prompt --install --force` | Update prompt with new features |

**Rule of thumb:** If you're explaining something verbally, capture it in Babel. Future you (and teammates) will thank you.

---

## Command Workflow

Babel has 35 commands. Understanding **how they flow together** is as important as knowing what each does individually.

### The Complete Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: FOUNDATION (once per project)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────┐            │
│  │   init   │───→│    config    │───→│  hooks install  │            │
│  │          │    │              │    │                 │            │
│  │ "Start   │    │ "Set LLM     │    │ "Auto-capture   │            │
│  │  with    │    │  provider,   │    │  git commits"   │            │
│  │  purpose"│    │  API keys"   │    │                 │            │
│  └──────────┘    └──────────────┘    └─────────────────┘            │
│                                                                     │
│  Framework Principle: HC3 (Offline-First) - config works locally    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2: KNOWLEDGE CREATION (iterative - the main loop)            │
├─────────────────────────────────────────────────────────────────────┤
│  why ──→ capture ──→ review ──→ link ──→ [IMPLEMENT]                │
│  "Check    "Propose"   "Confirm"  "Connect"  "Code"                 │
│   first"                                                            │
│                                                                     │
│  ⚠️  CRITICAL: link BEFORE implement, not after!                    │
│      Unlinked artifacts can't inform 'babel why' queries.           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3: VALIDATION                                                │
├─────────────────────────────────────────────────────────────────────┤
│  endorse ──→ evidence-decision ──→ validation                       │
│  "Consensus"   "Grounding"          "Check status"                  │
│                                                                     │
│  Both required: consensus alone = groupthink risk                   │
│                 evidence alone = unreviewed risk                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 4: HEALTH CHECK                                              │
├─────────────────────────────────────────────────────────────────────┤
│  status ──→ coherence ──→ history                                   │
│  "Overview"  "Alignment"   "Audit trail"                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                              ┌─────┴─────┐
                              │  REPEAT   │
                              └───────────┘
```

### Complementary Command Groups

Commands that work **together as a unit**. Using one without the others leaves the workflow incomplete.

#### Foundation Flow (Once per Project)
```
┌────────────────────────────────────────────────────────────────────────┐
│                           PROJECT SETUP                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────┐                                                      │
│  │     init     │  babel init "Purpose" --need "Problem"               │
│  │              │                                                      │
│  │ Creates:     │  Framework Principle: P1 (Bootstrap from Need)       │
│  │ - .babel/    │  Ground in real problems, not solutions              │
│  │ - Purpose    │                                                      │
│  └──────┬───────┘                                                      │
│         │                                                              │
│         ▼                                                              │
│  ┌──────────────┐                                                      │
│  │    config    │  babel config --set llm.provider=anthropic           │
│  │              │  babel config --set llm.api_key_env=ANTHROPIC_API_KEY│
│  │ Settings:    │                                                      │
│  │ - LLM setup  │  Framework Principle: HC3 (Offline-First)            │
│  │ - API keys   │  Config works without network                        │
│  │ - --user     │  --user for global, default for project              │
│  └──────┬───────┘                                                      │
│         │                                                              │
│         ▼                                                              │
│  ┌──────────────┐                                                      │
│  │    hooks     │  babel hooks install                                 │
│  │              │  babel hooks status                                  │
│  │ Automation:  │  babel hooks uninstall                               │
│  │ - Git hooks  │                                                      │
│  │ - Auto-      │  Framework Principle: P7 (Reasoning Travels)         │
│  │   capture    │  Commits auto-captured preserves reasoning           │
│  └──────────────┘                                                      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

#### Capture Flow (Sequential) - The Main Knowledge Loop
```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌───────────┐
│   why   │───→│ capture │───→│ review  │───→│  link   │───→│ IMPLEMENT │
│         │    │         │    │         │    │         │    │           │
│ "Query  │    │"Propose │    │"Human   │    │"Connect │    │  "Write   │
│ existing│    │ decision│    │ confirms│    │ to      │    │   code"   │
│ first"  │    │ --batch"│    │  (HC2)" │    │ purpose"│    │           │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └───────────┘
     │              │              │              │
     │              │              │              │
     │         P3: Bounded    HC2: Human     P1: Coherence
     │         Expertise      Authority      Observable
     │                             │
     └─────────────────────────────┘
       Query before proposing to avoid duplicates

Review Options:
  babel review --list              # See pending proposals
  babel review --accept <id>       # Accept specific proposal
  babel review --accept-all        # Accept all pending
```

#### Validation Flow (Parallel then Check)
```
                    ┌──────────┐
                    │ endorse  │──────┐
                    │          │      │
                    │"Consensus│      │
                    │   (P5)"  │      │     ┌────────────┐
                    └──────────┘      ├────→│ validation │
                                      │     │            │
┌───────────────────┐                 │     │  "Check    │
│ evidence-decision │─────────────────┘     │   both"    │
│                   │                       └────────────┘
│   "Grounding      │
│      (P5)"        │
└───────────────────┘

     Both required: Consensus alone = groupthink
                    Evidence alone = unreviewed
```

#### Challenge Flow (Disagreement Lifecycle)
```
┌───────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
│ challenge │───→│ evidence │───→│ resolve │───→│ tensions │
│           │    │          │    │         │    │          │
│  "Raise   │    │  "Add    │    │ "Close  │    │  "See    │
│   (P4)"   │    │ findings"│    │  with   │    │  open    │
│           │    │          │    │ outcome"│    │ (sorted) │
└───────────┘    └──────────┘    └─────────┘    └──────────┘
                      │               │               │
                      └───────────────┘               │
                   Can add multiple evidence          │
                   before resolving                   │
                                                      ▼
                                            Sorted by severity:
                                            🔴 critical → 🟡 warning → 🟢 info

On `resolve --outcome revised`:
  P8: System prompts to create evolves_from link
  babel link <new_artifact_id> <old_artifact_id>
```

#### Ambiguity Flow (Unknown Lifecycle)
```
┌──────────┐                      ┌──────────────────┐    ┌───────────┐
│ question │─────────────────────→│ resolve-question │───→│ questions │
│          │                      │                  │    │           │
│ "Raise   │                      │ "Close when      │    │ "See all  │
│ unknown  │                      │  evidence        │    │   open"   │
│  (P6)"   │                      │  sufficient"     │    │           │
└──────────┘                      └──────────────────┘    └───────────┘
     │                                    │
     │    ┌───────────────────────────────┘
     │    │  Don't force closure - hold
     │    │  uncertainty until ready (P6)
     └────┘
```

#### Scope Promotion (Local → Shared)
```
┌─────────────────┐              ┌─────────────────┐
│     capture     │              │      share      │
│                 │              │                 │
│  [L] Local      │─────────────→│  [S] Shared     │
│  (personal)     │   Promote    │  (team)         │
│                 │   when       │                 │
│  Safe to        │   confident  │  Git-tracked    │
│  experiment     │              │                 │
└─────────────────┘              └─────────────────┘
```

#### Git-Babel Bridge Flow (Intent ↔ State)
```
┌───────────┐    ┌───────────────┐    ┌───────────────┐
│   link    │    │ suggest-links │    │     gaps      │
│  --to-    │    │               │    │               │
│  commit   │    │ "AI-assisted  │    │ "Show what's  │
│           │◄───│  matching"    │◄───│  unlinked"    │
│ "Bridge   │    │               │    │               │
│  intent   │    │               │    │ decisions ↔   │
│  to code" │    │               │    │ commits       │
└─────┬─────┘    └───────────────┘    └───────────────┘
      │
      ▼
┌───────────────────────────────────────────────────────┐
│  why --commit <sha>     "Query why commit exists"     │
│  status --git           "Check sync health"           │
│  link --commits         "List all decision→commit"    │
└───────────────────────────────────────────────────────┘

     P7: Reasoning Travels — decisions connect to code
     P8: Evolution Traceable — implementation has context
```

#### Health Check Pair
```
┌────────────┐                    ┌────────────┐
│   status   │                    │   check    │
│            │                    │            │
│ "Overview" │   Complementary    │ "Integrity"│
│            │◄──────────────────►│            │
│ - Events   │                    │ - Files OK │
│ - Purposes │                    │ - Graph OK │
│ - Health   │                    │ - Repair   │
└────────────┘                    └────────────┘
```

#### Visibility Pair
```
┌────────────┐                    ┌────────────┐
│  tensions  │                    │ questions  │
│            │                    │            │
│ "What's    │   Complementary    │ "What's    │
│ contested" │◄──────────────────►│  unknown"  │
│            │                    │            │
│ Disputes   │                    │ Unknowns   │
│ awaiting   │                    │ awaiting   │
│ resolution │                    │ answer     │
└────────────┘                    └────────────┘
```

### Special Use Cases

Commands for **specific situations**, outside the normal flow:

```
                         NORMAL FLOW
    ┌─────────────────────────────────────────────────┐
    │  why → capture → review → link → [IMPLEMENT]   │
    └─────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   COLLABORATION │ │    ANALYSIS     │ │    RECOVERY     │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│                 │ │                 │ │                 │
│  sync           │ │  scan           │ │  check          │
│  (after pull)   │ │  (deep review)  │ │  (integrity)    │
│                 │ │                 │ │                 │
│  process-queue  │ │  prompt         │ │  principles     │
│  (after offline)│ │  (LLM setup)    │ │  (self-check)   │
│                 │ │                 │ │                 │
│  capture-commit │ │  deprecate      │ │                 │
│  (manual git)   │ │  (evolution)    │ │                 │
│                 │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

| Command | Category | When to Use |
|---------|----------|-------------|
| `sync` | Collaboration | After `git pull` - merge teammates' reasoning |
| `process-queue` | Collaboration | After offline work - process queued extractions |
| `capture-commit` | Collaboration | Manual git capture when hooks disabled |
| `scan` | Analysis | Architecture/security/performance review |
| `prompt` | Analysis | Generate system prompt for AI assistants |
| `deprecate` | Analysis | Mark artifact as outdated (evolution, not deletion) |
| `check` | Recovery | Diagnose and repair project integrity |
| `principles` | Recovery | Self-check against framework rules |
| `help` | Reference | Extended help on topics and workflows |
| `gaps` | Git-Babel Bridge | Show unlinked decisions/commits (intent ↔ state) |
| `suggest-links` | Git-Babel Bridge | AI-assisted decision→commit matching |
| `link --to-commit` | Git-Babel Bridge | Connect decision to specific commit |
| `why --commit` | Git-Babel Bridge | Query why a commit was made |
| `status --git` | Git-Babel Bridge | Check git-babel sync health |

### The Critical Insight: Link Before Implement

**The framework's most common mistake:**

```
WRONG:  why → capture → review → [IMPLEMENT] → ... link later ...
RIGHT:  why → capture → review → link → [IMPLEMENT]
```

| When Linking is Deferred | What Happens |
|--------------------------|--------------|
| Artifacts exist but disconnected | `babel why` can't find the knowledge |
| Linking becomes batch housekeeping | Reasoning context is lost |
| Coherence check shows "N unlinked" | Framework tolerates incoherence |

**Linking is part of knowledge CREATION, not documentation cleanup.**

When you confirm a proposal (`babel review`), immediately link it to purpose (`babel link <id>`). The reasoning for WHY it connects is fresh in context. Deferring loses that reasoning.

### Quick Command Reference by Phase

**Phase 1: Foundation**
```bash
babel init "Purpose" --need "Problem"    # Start project
babel config --set llm.provider=claude   # Configure
babel hooks install                      # Automate git capture
```

**Phase 2: Knowledge Creation (the main loop)**
```bash
babel why "topic"                        # 1. Check existing knowledge FIRST
babel capture "I propose X because Y"    # 2. Propose decision
babel review                             # 3. Confirm proposals (HC2)
babel link <id>                          # 4. Connect to purpose IMMEDIATELY
# [IMPLEMENT]                            # 5. Now write code
```

**Phase 3: Validation**
```bash
babel endorse <id>                       # Add consensus
babel evidence-decision <id> "proof"     # Add grounding
babel validation                         # Check: both required for validated
```

**Phase 4: Health Check**
```bash
babel status                             # Overview
babel coherence                          # Alignment with purpose
babel history                            # Audit trail
```

**Phase 5: Git-Babel Bridge (after implementation)**
```bash
babel link <id> --to-commit <sha>        # Connect decision to commit
babel link --commits                     # List all decision→commit links
babel why --commit <sha>                 # Query why a commit was made
babel gaps                               # Show implementation gaps
babel gaps --decisions                   # Only unlinked decisions
babel gaps --commits                     # Only unlinked commits
babel suggest-links                      # AI-assisted link suggestions
babel suggest-links --from-recent 10     # Analyze last 10 commits
babel status --git                       # Git-babel sync health
```

**Disagreement (when it arises)**
```bash
babel challenge <id> "reason"            # Raise disagreement (P4)
babel evidence <id> "finding"            # Add evidence
babel resolve <id> --outcome confirmed   # Close with outcome
babel resolve <id> --outcome revised     # Close + prompts evolves_from link (P8)
babel tensions                           # See what's contested (sorted by severity)
babel tensions --full                    # Full details with severity levels
```

**Uncertainty (when you don't know)**
```bash
babel question "How should we...?"       # Raise open question (P6)
babel questions                          # See acknowledged unknowns
babel resolve-question <id> "answer"     # Close when evidence sufficient
```

---

## Core Concepts

Babel is built on nine principles from research on how knowledge is lost in software projects.

### P1: Bootstrap from Need

**The problem:** Projects start with solutions ("let's build X") instead of problems ("users can't do Y"). Without grounding in reality, purpose drifts and decisions become arbitrary.

**Babel's solution:** Explicitly capture the NEED (what's broken) alongside PURPOSE (what we're building).

**In practice:**
```bash
babel init "Build offline-first mobile app" \
    --need "Field workers lose data when connectivity drops"

# Later, when someone proposes always-online features:
# AI checks: "This conflicts with the NEED (connectivity drops)"
```

### P2: Emergent Ontology

**The problem:** Fixed vocabularies impose external meaning. "Database" in a financial app might mean something different than in a gaming app. Teams need to define their own terms.

**Babel's solution:** Vocabulary emerges from use. Terms can be introduced, challenged, refined, or discarded. Project-level definitions take precedence over common patterns.

**In practice:**
```bash
# Common pattern: Redis → caching cluster
# But in YOUR project, Redis is the primary store

vocab.define("redis", "database", reason="We use Redis as primary store")
vocab.challenge("graphql", reason="We call our JSON-RPC 'graphql' internally")

# Now AI understands YOUR project's vocabulary
```

### P3: Expertise Governance

**The problem:** Not all opinions are equal. A security expert's decision about authentication carries more weight than a frontend developer's guess. But without attribution, all decisions look the same.

**Babel's solution:** Decisions can declare their domain. Domains link to scan types and vocabulary clusters. AI participates as pattern detector, synthesizer, and challenger — never arbiter.

**In practice:**
```bash
# Capture with domain attribution
babel capture "Use bcrypt with cost factor 12" --domain security

# Scanner weights by domain relevance
babel scan --type security
# → Security decisions from security-domain contributors weighted higher
# → Cross-domain security mentions flagged for review

# AI knows its role
# ✓ "Pattern detected: 3 decisions about caching"
# ✓ "Challenge: This may conflict with constraint X"
# ✗ "You must use PostgreSQL" (arbiter — not allowed)
```

### P4: Disagreement as Hypothesis

**The problem:** Disagreement is often suppressed or resolved by authority. Knowledge is lost when the losing side's reasoning disappears. Teams need a way to record productive tension.

**Babel's solution:** Disagreement is information, not friction. Tensions are auto-detected via coherence checks and graded by severity. Disputes are reframed as testable hypotheses. No one "wins" by authority alone — resolution requires evidence.

**In practice:**
```bash
# Tensions are auto-detected during coherence checks
babel coherence
# → Detects conflicts and emits TENSION_DETECTED events

# See a decision you disagree with
babel why "database"
# → Decision [d3f8a2]: Use PostgreSQL for JSON support

# Challenge it (doesn't override — adds context)
babel challenge d3f8a2 "Schema-less data might not fit relational model" \
    --hypothesis "MongoDB handles our access patterns better" \
    --test "Benchmark with real production queries"

# Add evidence as you learn
babel evidence d3f8a2 "Benchmark showed 2x faster with MongoDB"

# Resolve when evidence supports a conclusion
babel resolve d3f8a2 --outcome revised \
    -r "Switching to MongoDB based on benchmark results"
# → P8: System prompts to create evolves_from link

# Track open tensions (sorted by severity)
babel tensions
# → 🔴 1 critical tension (hard constraint violated)
# → 🟡 2 warning tensions (potential conflicts)
# → 🟢 1 info tension (minor)
```

### P5: Dual-Test Truth

**The problem:** Decisions get validated by either consensus alone (groupthink) or evidence alone (unreviewed). Neither is sufficient. Teams need both shared agreement AND external grounding.

**Babel's solution:** Decisions require dual validation: team consensus (endorsements) AND external grounding (evidence). Neither alone marks a decision as "validated."

**In practice:**
```bash
# See a decision
babel why "database"
# → Decision [d3f8a2]: Use PostgreSQL for JSON support
# → ◐ Consensus only — needs evidence (groupthink risk)

# Add your endorsement (consensus)
babel endorse d3f8a2
# → 2 endorsements now

# Add supporting evidence (grounding)
babel evidence-decision d3f8a2 "Benchmark: PostgreSQL 3x faster for our queries"
# → Decision is now VALIDATED (consensus + evidence)

# Check validation status
babel validation
# → ● Validated: 5 decisions
# → ◐ Partial: 2 (1 groupthink risk, 1 unreviewed)
```

### P6: Ambiguity Management

**The problem:** Teams force decisions when evidence is insufficient. Premature closure loses valuable uncertainty signals. "Anomalies accumulate before paradigms shift."

**Babel's solution:** Ambiguity is explicitly recorded, not forced into closure. Open questions are first-class artifacts. Holding uncertainty is epistemic maturity, not weakness.

**In practice:**
```bash
# Record an open question (acknowledged unknown)
babel question "How should we handle offline sync conflicts?" \
    --context "Multiple users may edit same data offline"
# → ? Open question raised [q1a2b3c4]
# → This is an acknowledged unknown — not a failure.

# List open questions
babel questions
# → ? Open Questions: 3
# → (Acknowledged unknowns — not failures)

# Mark a decision as uncertain
babel capture "Use Redis for caching" --uncertain \
    --uncertainty-reason "Not sure about scaling past 10K users"
# → Captured (○ local) [caching] ◑ UNCERTAIN

# Premature resolution warning (P10)
babel resolve c3d4e5 --outcome confirmed
# → ⚠ Only 1 evidence item. Resolution may be premature.
# → Options: 1. Continue anyway  2. Mark as uncertain  3. Cancel
```

### P7: Reasoning Travels With Artifacts

**The problem:** Code without context is a puzzle without the picture on the box.

**Babel's solution:** Decisions are captured and linked, so reasoning travels with the code.

**In practice:**
```bash
babel why "caching"
# Returns not just "we use Redis" but:
# - WHY Redis (performance requirements)
# - WHY caching at all (API rate limits)
# - WHAT constraints exist (must invalidate on user update)
```

### P8: Evolution is Traceable

**The problem:** Decisions don't exist in isolation. They connect, build on each other, and sometimes conflict. When decisions are revised, the supersession chain must be explicit.

**Babel's solution:** Every decision links back to need and purpose. When artifacts are revised, `evolves_from` links maintain the lineage. You can trace the chain.

**In practice:**
```
Need: "Field workers lose data when connectivity drops"
  └─→ Purpose: "Offline-first mobile app"
        └─→ Decision: "Use SQLite for local storage"
              └─→ Decision: "Implement sync queue"
                    └─→ Constraint: "Must handle conflict resolution"
```

**Evolution tracking:**
```bash
# When resolving a challenge with outcome=revised
babel resolve abc123 --outcome revised --resolution "Updated approach"
# System prompts: P8: Evolution link available from [parent_id]
#                 To link: babel link <new_artifact_id> parent_id

# Create the evolves_from link
babel link new_decision_id old_decision_id
# Now `babel history` shows the evolution chain
```

### P9: Coherence is Observable

**The problem:** As projects evolve, decisions can drift from original need. New choices might conflict with old constraints. No one notices until something breaks.

**Babel's solution:** Coherence checking surfaces tensions early, before they become problems.

**In practice:**
```bash
babel coherence
# "Your 'real-time sync' feature may conflict with 
#  'offline-first' purpose. Consider: queue-based sync"

babel scan
# AI-powered analysis using YOUR project's context
```

### Evidence-Weighted Memory

**The problem:** Accumulated memory can constrain future options. Exhaustive archives create rigidity traps. Not all artifacts are equally relevant.

**Babel's solution:** Living artifacts, not exhaustive archives. AI weights retrieval by validation status (P5), challenge resolution (P4), certainty (P6), and deprecation. What works is prioritized; what fails is metabolized.

**In practice:**
```bash
# Mark outdated decision as deprecated (not deleted — HC1 preserved)
babel deprecate d3f8a2 "Superseded by microservices migration" \
    --superseded-by e4f5g6

# Query shows weighted results
babel why "architecture"
# → Shows validated decisions first
# → Deprecated items marked: ⊘ DEPRECATED
# → AI de-prioritizes deprecated, uncertain, unvalidated
```

**AI weighting (uses existing signals):**
- P5 VALIDATED > CONSENSUS > EVIDENCED > PROPOSED
- P4 confirmed (stood up to challenge) > revised (learned from failure)
- P6 certain > uncertain
- Deprecated items shown but de-prioritized

### Failure Metabolism

**The problem:** Failed ideas are silently abandoned. Teams repeat mistakes because lessons weren't captured. Failure is not loss; unexamined failure is.

**Babel's solution:** Failures are mandatory learning inputs. When decisions are revised or deprecated, explanations are required. AI surfaces these lessons in context.

**In practice:**
```bash
# Resolving a challenge as "revised" requires lesson (P8)
babel resolve c3d4e5 --outcome revised
# → P8: What did we learn from this?
# → Lesson learned: _________________

# Deprecating requires explanation (no silent abandonment)
babel deprecate d3f8a2 ""
# → ⚠ P8: Reason required for deprecation
# → Why is this being deprecated? What did we learn?

# AI surfaces lessons in context
babel why "authentication"
# → "Lesson learned: We originally tried session-based auth but
#    mobile apps needed stateless tokens. Switched to JWT."
```

**Where lessons are captured:**
- P4 `--outcome revised` → resolution field = lesson learned
- P7 `deprecate` → reason field = why it failed
- P6 `--outcome dissolved` → resolution field = why question became irrelevant

### Adaptive Cycle Rate

**The problem:** Fixed cadences don't fit all situations. Moving too fast when confused creates fragility. Moving too slow when aligned causes stagnation.

**Babel's solution:** The system provides pace guidance based on coherence and tension signals. Tensions are auto-detected with graded severity (critical/warning/info) to enable calibrated response. No fixed cadence is imposed. AI interprets the signals to suggest appropriate pace.

**In practice:**
```bash
babel status
# ...existing output...
#
# ◔ Project Health: HIGH CONFUSION
#   Consider resolving tensions before new decisions (slower cycles)

# Or when things are good:
# ● Project Health: ALIGNED
#   Good position to move forward

babel tensions
# Shows tensions sorted by severity:
# 🔴 [abc123] Critical: Hard constraint violated
# 🟡 [def456] Warning: Potential conflict detected
# 🟢 [ghi789] Info: Minor tension, informational
```

**Health indicators (derived from existing signals):**
| State | Signals | Suggestion |
|-------|---------|------------|
| ◔ HIGH CONFUSION | Many tensions, unvalidated decisions, coherence issues | Slow down, clarify |
| ◐ MODERATE | Some open items | Address tensions |
| ● ALIGNED | Validated, no tensions, coherent | Move forward |
| ○ STARTING | New project | Capture as you go |

**Tension severity levels:**
| Severity | Icon | Meaning | Response |
|----------|------|---------|----------|
| Critical | 🔴 | Hard constraint violated, multiple conflicts | Accelerate resolution cycle |
| Warning | 🟡 | Potential conflict, needs attention | Maintain current pace |
| Info | 🟢 | Minor tension, informational | Continue normally |

**AI interprets these signals naturally** — when it sees high confusion or critical tensions, it suggests addressing existing issues before new decisions. No enforcement, just guidance.

### Cross-Domain Learning

**The problem:** Ideas borrowed from other domains can be powerful but also misleading. When analogies break down, we need to know where the idea came from to diagnose why.

**Babel's solution:** Cross-domain references are detected and surfaced. Source domains (internal or external like electrical engineering, biology) are noted. Misapplied transfer is treated as diagnostic information, not error.

**In practice:**
```bash
# Capture with cross-domain reference
babel capture "Use circuit breaker pattern for API resilience"

# Detected: [auto: reliability]
#   ↔ Cross-domain: from electrical
#   (Borrowing from: electrical)

# Multiple internal domains detected
babel capture "Add Redis caching with JWT authentication"
# Detected: [auto: performance]
#   ↔ Cross-domain: references security
```

**External domains tracked:**
| Domain | Example Concepts |
|--------|------------------|
| electrical | circuit breaker, load balancing, fuse |
| military | defense in depth, strategy, tactics |
| biology | evolution, mutation, adaptation, ecosystem |
| manufacturing | kanban, lean, just in time |
| economics | supply, demand, equilibrium |
| medicine | diagnosis, triage, treatment |

**AI uses cross-domain detection to:**
- Note when ideas are borrowed from other fields
- Suggest checking if the analogy holds in your context
- Frame misapplication as learning opportunity, not error

### Framework Self-Application (Reflexivity)

**The problem:** A framework that cannot govern itself is incomplete. Teams can violate their own principles without noticing.

**Babel's solution:** The framework applies to its own discussion. Principles are documented and accessible. AI can notice violations and suggest meta-discussion when coherence degrades.

**In practice:**
```bash
# Quick reference to all principles
babel principles

# Shows:
# - All 11 core principles with commands
# - Hard constraints (HC1-HC5)
# - Self-check questions

# Self-check questions included:
#   □ Am I starting from need, or jumping to solutions? (P1)
#   □ Am I attributing expertise domains? (P3)
#   □ Am I treating disagreement as information? (P4)
#   □ Do decisions have both endorsement AND evidence? (P5)
#   □ Am I acknowledging what I don't know? (P6)
#   □ Am I capturing lessons from failures? (P8)
#   □ Is my pace appropriate to current confusion? (P9)
#   □ Am I noting where borrowed ideas come from? (P10)
```

**P11 in action:**
- AI notices principle violations in user actions
- AI suggests meta-discussion when coherence degrades
- Users can ask "Am I using this correctly?"
- `babel principles` provides quick reference for self-check

---

## Framework: Principles → Features

Every Babel feature exists to serve a principle. Nothing is arbitrary.

**Core Principles (Babel Framework):**

| Principle | What It Means | Babel Features | AI Behavior |
|-----------|---------------|----------------|-------------|
| **P1: Bootstrap from Need** | Start from real problems, not solutions | `init --need`, need in context | Checks need before suggesting changes |
| **P2: Emergent Ontology** | Vocabulary emerges, not imposed | `define`, `challenge`, `refine`, `discard` | Respects project-level definitions |
| **P3: Expertise Governance** | Authority from domain expertise | `--domain`, domain registry | Weights by expertise, never arbitrates |
| **P4: Disagreement as Hypothesis** | Disagreement is information | `challenge`, `evidence`, `resolve`, `tensions` | Suggests hypotheses, tracks resolution |
| **P5: Dual-Test Truth** | Consensus AND evidence required | `endorse`, `evidence-decision`, `validation` | Warns about groupthink/unreviewed |
| **P6: Ambiguity Management** | Hold uncertainty, don't force closure | `question`, `questions`, `--uncertain` | Detects uncertainty, warns on premature resolution |
| **P7: Reasoning Travels** | Decisions stay connected to code | `capture`, `why`, event linking | Suggests captures when you explain decisions |
| **P8: Evolution Traceable** | You can follow decision chains | Graph, refs, `history` | Traces connections when you ask "why" |
| **P9: Coherence Observable** | Drift becomes visible early | `coherence`, `scan` | Alerts when new decisions conflict with old |
| **Evidence-Weighted Memory** | Living artifacts, not archives | `deprecate`, AI weighting | Prioritizes validated/confirmed; de-weights deprecated |
| **Failure Metabolism** | Failures are learning inputs | Validation on revised/deprecate | Surfaces lessons; requires explanation for failures |
| **Adaptive Cycle Rate** | Pace adapts to state | Health indicator in `status` | Suggests slowdown when confused, speed when aligned |
| **Cross-Domain Learning** | Track idea sources | Domain detection in captures | Notes borrowed concepts; frames misapplication as diagnostic |
| **Framework Self-Application** | Framework governs itself | `babel principles` | Notices violations; suggests meta-discussion when needed |

**Hard constraints** (non-negotiable implementation rules):

| Constraint | Why It Exists | How Babel Implements |
|------------|---------------|----------------------|
| **HC1: Immutable Events** | History must be trustworthy | Append-only store, no edits |
| **HC2: Human Authority** | AI proposes, human decides | All extractions require confirmation |
| **HC3: Offline-First** | Must work without network | Local storage, extraction queue |
| **HC4: Tool Agnostic** | Your choice of AI provider | Provider abstraction layer |
| **HC5: Graceful Sync** | Team collaboration must work | Shared/local scope, deduplication |
| **HC6: No Jargon** | Output must be human-readable | Plain language, visual symbols |

**Graph relations** (renegotiation-aligned ontology):

| Relation | Direction | Principle | Purpose |
|----------|-----------|-----------|---------|
| `tensions_with` | Bidirectional (via tension node) | P4, P5 | Links conflicting artifacts — both preserved, tension surfaced |
| `evolves_from` | New → Old | P8 | Tracks artifact lineage — new preferred, old remains for history |
| `requires_negotiation` | Artifact → Constraint | HC2 | Advisory warning — artifact touches constrained area, human decides |

These relations enable:
- **Auto-detection**: Tensions surfaced via coherence checks, not manual flagging
- **Graded severity**: Critical/warning/info levels calibrate response (P5: Adaptive Cycle Rate)
- **Evolution tracking**: Supersession chains explicit, not implicit (P8: Evolution Traceable)
- **Advisory warnings**: System warns but proceeds, preserving human authority (HC2)

**Meta-principle: Low Friction**

If capturing knowledge is hard, people won't do it. Babel is designed so that:
- Doing the right thing is easier than skipping it
- AI handles the overhead
- Commands are optional, not required

---

## AI Conversation Example

Here's how Babel + AI work together in practice:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You: I think we should switch from REST to GraphQL for the API.

AI:  Before we decide, let me check the existing context...
     
     [Queries: babel why "API"]
     
     I found relevant history:
     
     ┌─────────────────────────────────────────────────────────
     │ Decision (March 15): "REST chosen for API"
     │ 
     │ Reasons:
     │ • Team has no GraphQL experience  
     │ • Simpler tooling and debugging
     │ • Sufficient for current query patterns
     │
     │ Constraint: "Keep stack accessible to junior devs"
     └─────────────────────────────────────────────────────────
     
     The original decision prioritized team experience and 
     simplicity. Has something changed that would justify 
     the GraphQL complexity?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You: Good point. The team still doesn't know GraphQL. Let's 
     stick with REST but add better caching for the slow endpoints.

AI:  That aligns with the existing constraints. Should I capture 
     this decision?
     
     Proposed capture:
     ┌─────────────────────────────────────────────────────────
     │ "Evaluated GraphQL vs REST (Jan 2025). Staying with REST.
     │  Adding caching layer for performance instead.
     │  
     │  Reasoning: Team experience unchanged, GraphQL complexity
     │  not justified. Caching solves immediate performance need
     │  while maintaining stack simplicity."
     └─────────────────────────────────────────────────────────

You: Yes, capture that.

AI:  [Runs: babel capture --share "..."]
     
     ✓ Captured and shared with team.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**What happened:**
1. AI checked context *before* you made a decision
2. Surfaced relevant constraints you might have forgotten
3. Helped you make a better-informed choice
4. Captured the reasoning for future reference

**You didn't run any commands.** The AI handled Babel for you.

---

## The System Prompt

When you initialize Babel, it creates `.system_prompt.md` — instructions for AI assistants.

### What It Contains

```markdown
# Project: Your App Name
# Purpose: Build an offline-first mobile app for field workers

## Instructions for AI Assistant

When working on this project:
1. Check `babel why "topic"` before answering questions about 
   existing code — context may exist that explains decisions.
2. After important discussions, suggest `babel capture` to 
   preserve reasoning.
3. Before suggesting major changes, run `babel scan` to check 
   for constraint conflicts.
4. Respect existing decisions unless explicitly revisiting them.

## Current Context
- Purpose: [loaded from Babel]
- Key decisions: [loaded from Babel]  
- Active constraints: [loaded from Babel]
```

### How to Use It

**Option 1: AI with custom instructions**
```bash
babel prompt | pbcopy  # Copy to clipboard
# Paste into your AI assistant's custom instructions
```

**Option 2: AI with file access**
```bash
# AI reads .system_prompt.md directly from your project
```

**Option 3: Claude Projects / GPT Projects**
```bash
# Upload .system_prompt.md to your project knowledge
```

### What the AI Learns

With the system prompt, your AI assistant:

| Without Babel Context | With Babel Context |
|-----------------------|-------------------|
| "You should use PostgreSQL" | "Your project chose SQLite for offline support — PostgreSQL would conflict with that goal" |
| "Add TypeScript for safety" | "There's a constraint about keeping the stack simple for junior devs — consider JSDoc instead" |
| "Let me explain this code" | "According to the March decision, this caching pattern exists because of API rate limits" |

**The AI becomes a team member who knows the project's history.**

---

## Commands Reference

### `babel init "purpose"` [--need "problem"]

**What:** Initialize Babel for a project, grounded in a real problem.

**Why:** P1 requires grounding in reality. Need anchors purpose to actual problems.

```bash
# Full P1-compliant initialization (recommended)
babel init "Build offline-first mobile app" \
    --need "Field workers lose data when connectivity drops"

# Purpose only (works, but less grounded)
babel init "Build a privacy-focused note-taking app"
```

**The difference:**

| Purpose Only | Purpose + Need |
|-------------|----------------|
| "Build offline-first app" | Need: "Workers lose data on disconnection" |
| Abstract goal | → Purpose: "Build offline-first app" |
| Decisions can drift | Decisions anchored to real problem |

**When:** Once per project, at the start.

---

### `babel capture "text"`

**What:** Capture reasoning, decisions, or context.

**Why:** Saves the WHY while it's fresh in your mind.

```bash
# Personal note (local only)
babel capture "Thinking about using GraphQL here..."

# Team decision (shared via Git)
babel capture "Decided on REST for simplicity" --share
```

**Options:**
- `--share` — Share with team (tracked in Git)
- `--raw` — Skip AI extraction (just store as-is)
- `--spec <need_id>` — Add implementation specification to existing need (links OBJECTIVE/ADD/MODIFY/REMOVE/PRESERVE to artifact)
- `--batch` — Queue for review instead of interactive confirmation

```bash
# Add specification to an existing need
babel capture --spec a1b2c3d4 "OBJECTIVE: Add caching layer
ADD:
- Redis client wrapper
- Cache invalidation logic
MODIFY:
- API handlers to check cache first
PRESERVE:
- Existing response format" --batch
```

**When:** After any decision, discussion, or realization worth preserving. Use `--spec` when you have implementation details for an existing need.

---

### `babel why "query"` [--commit <sha>]

**What:** Query captured reasoning, or understand why a specific commit was made.

**Why:** Answer "why is it this way?" without archaeology. The `--commit` flag bridges from code changes back to decisions.

```bash
# Query by topic
babel why "database"
babel why "authentication approach"
babel why "that weird caching pattern"

# Query why a specific commit was made
babel why --commit a1b2c3d4
# → Shows decisions linked to this commit
# → "Use Redis for caching because of rate limits"

# Query HEAD (most recent commit)
babel why --commit HEAD
```

**Options:**
- `--commit <sha>` — Show decisions linked to a specific commit (P7, P8)

**When:** Before changing something. When confused. When onboarding. Before refactoring a specific commit.

---

### `babel status` [--full] [--git]

**What:** Show project overview and health.

**Why:** Quick orientation — purpose, key decisions, health. The `--git` flag shows decision-to-commit sync status.

```bash
babel status
# Project: /path/to/project
# Purpose: Build offline-first mobile app
# Events: 47 (● 32 shared, ○ 15 local)
# Coherence: ✓ aligned

# Show full details
babel status --full

# Show git-babel sync health
babel status --git
# → Decision-commit links: 23
# → ⚠ Unlinked decisions: 5
# → ⚠ Unlinked commits (last 20): 3
# → ✓ Intent and state are well connected. (or suggestions)
```

**Options:**
- `--full` — Show full content without truncation
- `--git` — Show git-babel sync health (decision↔commit links)

**When:** Starting a work session. Getting oriented. Reviewing implementation coverage.

---

### `babel scan`

**What:** Context-aware technical analysis.

**Why:** Generic scanners don't know your project. Babel scan uses YOUR purpose, decisions, and constraints to give relevant advice.

```bash
# Quick health check
babel scan

# Focused analysis
babel scan --type architecture
babel scan --type security
babel scan --type performance

# Specific question
babel scan "Is our auth approach secure given our constraints?"

# Deep comprehensive analysis
babel scan --deep
```

**What makes it different:**
- Generic scanner: *"SQL injection risk"*
- Babel scan: *"SQL injection risk — but you have a 'sanitize all input' constraint. Verify it's applied at entry points X, Y, Z."*

**When:** Before major changes. During code review. Security audits.

---

### `babel coherence`

**What:** Check alignment between decisions and purpose.

**Why:** Surfaces drift before it causes problems.

```bash
babel coherence
# ✓ Coherent: 12 decisions aligned with purpose

babel coherence --full
# Show full content without truncation

babel coherence --force
# Force fresh analysis (ignore cache)

babel coherence --resolve
# Interactive AI-guided resolution of issues

babel coherence --resolve --batch
# Non-interactive mode for AI operators (shows suggestions without prompts)
```

**Options:**
- `--full` — Show full content without truncation
- `--force` — Bypass cache, run fresh check
- `--resolve` — Enter interactive resolution mode for issues
- `--batch` — With `--resolve`, non-interactive mode (for AI operators)

**When:** Periodically. Before releases. When something feels off.

---

### `babel history`

**What:** Show recent captured events.

**Why:** See what's been happening in the project.

```bash
babel history           # Last 10 events
babel history -n 20     # Last 20 events
babel history --shared  # Only team decisions
babel history --local   # Only personal notes
```

---

### `babel share <id>`

**What:** Promote a local capture to shared (team) status.

**Why:** Start local (safe experimentation), share when confident.

```bash
# You captured something locally
babel capture "Maybe we should use Redis here..."

# Later, you're confident — share with team
babel share abc123
```

---

### `babel sync`

**What:** Synchronize after Git operations.

**Why:** Merges reasoning from teammates smoothly.

```bash
git pull
babel sync
# Synced: 3 new decisions from teammates
```

**When:** After `git pull`, `git merge`, `git rebase`.

---

### `babel prompt`

**What:** Output the system prompt for LLM integration.

**Why:** Use with AI assistants that support custom instructions.

```bash
babel prompt > /tmp/instructions.md
# Copy to your AI assistant
```

---

### `babel config`

**What:** View or modify configuration.

**Why:** Customize LLM provider, display preferences, etc.

```bash
babel config                            # View current config
babel config --set llm.provider=openai  # Change setting
```

---

### `babel hooks install`

**What:** Install Git hooks for automatic capture.

**Why:** Capture commit reasoning automatically.

```bash
babel hooks install
# Now post-commit hook captures commit context
```

---

### `babel link <id>` [--list] [--all] [--to-commit <sha>] [--commits]

**What:** Connect artifacts to purpose or to git commits (improves coherence and traceability).

**Why:** Unlinked artifacts can't inform `babel why` queries. Linking decisions to commits bridges intent with state (P7, P8).

```bash
# Link a specific artifact to active purpose
babel link abc123

# Link to a specific purpose
babel link abc123 def456

# List all unlinked artifacts
babel link --list
# → Shows artifacts grouped by type with IDs

# Bulk link all unlinked to active purpose
babel link --all
# → Links all orphans, skips purposes and cycles

# === Git-Babel Bridge ===

# Link a decision to a specific commit
babel link abc123 --to-commit a1b2c3d4
# → Bridges intent (decision) with state (commit)

# Link to HEAD (most recent commit)
babel link abc123 --to-commit HEAD

# List all decision-to-commit links
babel link --commits
# → Shows all bridged artifacts: decision → commit
```

**Options:**
- `--list` — Show all unlinked artifacts (can't inform `why` queries)
- `--all` — Link all unlinked artifacts to active purpose
- `--to-commit <sha>` — Link decision to a git commit (P7, P8)
- `--commits` — List all decision-to-commit links

**When:** Immediately after `babel review --accept`. After implementing a decision (`--to-commit`). When `babel status` shows unlinked artifacts.

---

### `babel gaps` [--decisions] [--commits]

**What:** Show implementation gaps between decisions and commits (P7, P8).

**Why:** Surfaces where intent and state are disconnected — unimplemented decisions or undocumented changes.

```bash
# Show all gaps
babel gaps
# → Decisions without commits: 5
# → (Intent captured but not implemented)
# →   [decision] [abc12345] Use Redis for caching
# →   [decision] [def67890] Add input validation
# → Commits without decisions: 3
# → (State changed but intent not documented)
# →   [a1b2c3d4] Add caching layer
# →   [e5f6g7h8] Refactor auth module

# Only show unlinked decisions
babel gaps --decisions

# Only show unlinked commits
babel gaps --commits

# Analyze more recent commits
babel gaps --from-recent 50
```

**Options:**
- `--decisions` — Only show decisions without linked commits
- `--commits` — Only show commits without linked decisions
- `--from-recent <n>` — Number of recent commits to check (default: 20)
- `--limit <n>` — Maximum items to show (default: 10)
- `--offset <n>` — Skip first N items for pagination

**When:** Reviewing implementation status. After merging PR. Before release.

---

### `babel suggest-links`

**What:** AI-assisted decision-to-commit link suggestions.

**Why:** Helps find which decisions match which commits based on keyword overlap and domain context.

```bash
# Analyze last 5 commits (default)
babel suggest-links
# → Commit [a1b2c3d4]: "Add caching layer"
# →   [###] [abc12345] decision: Use Redis for caching
# →        Reasons: shared terms: caching, redis
# → Strongest match:
# →   babel link abc12345 --to-commit a1b2c3d4

# Analyze more commits
babel suggest-links --from-recent 10

# Analyze a specific commit
babel suggest-links --commit a1b2c3d4

# Show all matches (even low-confidence)
babel suggest-links --all

# Set minimum confidence score
babel suggest-links --min-score 0.5
```

**Options:**
- `--from-recent <n>` — Number of recent commits to analyze (default: 5)
- `--commit <sha>` — Analyze a specific commit instead of recent
- `--min-score <n>` — Minimum confidence score to show (default: 0.3)
- `--all` — Show all suggestions, even low-confidence

**When:** After making several commits. Periodically reviewing implementation gaps.

---

### `babel list` [type] [--from <id>] [--orphans]

**What:** Graph-aware artifact discovery. Browse, filter, and explore artifact connections.

**Why:** Find artifacts without LLM — fast, offline, uses graph structure directly.

```bash
# Overview: counts by type
babel list
# → Artifacts: 442 total
# →   decisions:   93  → babel list decisions
# →   constraints: 22  → babel list constraints
# →   ...

# List artifacts by type (10 by default)
babel list decisions
babel list constraints
babel list principles

# Show all (no limit)
babel list decisions --all

# Filter by keyword
babel list decisions --filter "cache"

# Graph traversal: see what's connected to an artifact
babel list --from a1b2c3d4
# → [a1b2c3d4] Use SQLite for offline storage
# →   ← Supported by:
# →     [c5d6e7f8] Offline-first requirement
# →   → Informs:
# →     [k3l4m5n6] Cache invalidation strategy

# Find orphan artifacts (no connections)
babel list --orphans
# → Shows artifacts that can't inform 'why' queries
```

**Options:**
- `type` — Artifact type to list (decisions, constraints, principles)
- `--from <id>` — Show artifacts connected to this ID (graph traversal)
- `--orphans` — Show artifacts with no incoming connections
- `--all` — Show all items (no limit)
- `--filter <keyword>` — Filter by keyword (case-insensitive)
- `--limit <n>` — Maximum items to show (default: 10)
- `--offset <n>` — Skip first N items for pagination (default: 0)

**When:** Exploring the knowledge graph. Finding specific artifacts. Understanding connections. Discovering orphaned artifacts that need linking.

---

### `babel memo` — Persistent User Preferences

Save operational preferences that persist across sessions. Unlike decisions (which capture reasoning), memos are simple instructions that reduce repetition.

**Two types of memos:**

| Type | When it surfaces | Use case |
|------|------------------|----------|
| **Regular memo** | Context-aware (via `--context`) | "Use pytest for testing" |
| **Init memo** | Always at session start via `babel status` | "Never bypass babel to use database directly" |

```bash
# Save a regular preference
babel memo "Always use python3 not python"

# With context (surfaces only in relevant situations)
babel memo "Run tests with -v --tb=short" --context testing

# Save an init memo (foundational instruction — surfaces at session start)
babel memo "Tests must use babel commands, never bypass to database" --init

# List all memos
babel memo --list

# List only init memos
babel memo --list-init

# Remove a memo
babel memo --remove m_abc123

# Update a memo
babel memo --update m_abc123 "New instruction"
```

**Init Memo Management:**

```bash
# Promote regular memo to init (foundational)
babel memo --promote-init m_abc123

# Demote init memo back to regular
babel memo --demote-init m_abc123
```

**AI Detection Features:**

```bash
# Show AI-detected repeated patterns
babel memo --candidates

# Promote a candidate to memo
babel memo --promote c_abc123

# Dismiss (don't suggest again)
babel memo --dismiss c_abc123

# Show pending suggestions
babel memo --suggest

# View statistics
babel memo --stats
```

**Options:**
- `content` — The memo content to save
- `--context, -c` — Context where this applies (can repeat)
- `--init, -i` — Mark as foundational instruction (surfaces at session start)
- `--list, -l` — List all saved memos
- `--list-init` — List only init memos (foundational instructions)
- `--remove, -r <id>` — Remove memo by ID
- `--update, -u <id>` — Update memo by ID
- `--promote-init <id>` — Promote regular memo to init (foundational)
- `--demote-init <id>` — Demote init memo to regular
- `--candidates` — Show AI-detected patterns
- `--promote <id>` — Promote candidate to memo
- `--dismiss <id>` — Dismiss a candidate
- `--suggest` — Show pending promotion suggestions
- `--stats` — Show memo statistics

**When:** Saving operational shortcuts. Reducing repetition. Persisting preferences across context compression. Setting foundational rules that must surface at every session start. AI detecting repeated instructions.

---

### `babel challenge <id> "reason"` — Disagree with a Decision

**What:** Record disagreement with an existing decision as testable hypothesis (P4).

**Why:** Disagreement is information, not conflict. Capturing it enables evidence-based resolution.

```bash
# Challenge a decision
babel challenge abc123 "This approach won't scale beyond 1000 users"

# With testable hypothesis
babel challenge abc123 "Won't scale" --hypothesis "Redis will outperform SQLite at 1000+ users"

# With test plan
babel challenge abc123 "Won't scale" --test "Benchmark at 100, 1000, 10000 users"

# Attribute domain expertise
babel challenge abc123 "Security risk" --domain security
```

**Options:**
- `target_id` — Decision ID (or prefix) to challenge
- `reason` — Why you disagree
- `--hypothesis, -H` — Testable alternative claim
- `--test, -t` — How to test the hypothesis
- `--domain, -d` — Expertise domain (P3: security, performance, etc.)

**When:** You disagree with an existing decision. You have evidence something is wrong. You want to propose an alternative.

---

### `babel evidence <challenge_id> "content"` — Add Evidence to Challenge

**What:** Add supporting evidence to an open challenge.

**Why:** Build a case before resolution. Evidence-based decisions are more durable.

```bash
# Add observation
babel evidence abc123 "Tested with 1000 users - response time increased 10x"

# Specify evidence type
babel evidence abc123 "User reported timeout" --type user_feedback
babel evidence abc123 "p99 latency: 2s → 20s" --type benchmark
```

**Options:**
- `challenge_id` — Challenge ID (or prefix)
- `content` — The evidence
- `--type` — Evidence type: `observation`, `benchmark`, `user_feedback`, `other`

**When:** You have data supporting or refuting a challenge. Building case for resolution.

---

### `babel resolve <challenge_id> --outcome <outcome>` — Resolve a Challenge

**What:** Close a challenge with an evidence-based outcome.

**Why:** Moves from contested to settled. Documents why the resolution was chosen.

```bash
# Confirm original decision was correct
babel resolve abc123 --outcome confirmed --resolution "Benchmarks show acceptable performance"

# Revise decision based on evidence
babel resolve abc123 --outcome revised --resolution "Switch to Redis based on load testing"

# Synthesize both perspectives
babel resolve abc123 --outcome synthesized --resolution "Use SQLite for small, Redis for large"

# Hold ambiguity when evidence is insufficient
babel resolve abc123 --outcome uncertain --resolution "Need more data before deciding"
```

**Options:**
- `challenge_id` — Challenge ID (or prefix)
- `--outcome, -o` — Resolution: `confirmed`, `revised`, `synthesized`, `uncertain`
- `--resolution, -r` — What was decided
- `--evidence, -e` — Summary of evidence
- `--force, -f` — Skip premature resolution warning

**When:** Challenge has sufficient evidence. Ready to close the dispute.

---

### `babel tensions` — Show Open Tensions

**What:** Display all open challenges and tensions, sorted by severity.

**Why:** See what's contested vs. settled. Prioritize critical issues.

```bash
# Show open tensions
babel tensions
# → 🔴 [abc123] Won't scale beyond 1000 users (2 evidence)
# → 🟡 [def456] Should use TypeScript (1 evidence)
# → 🟢 [ghi789] Consider dark mode (0 evidence)

# Full details with severity
babel tensions --full

# Verbose mode
babel tensions -v
```

**Severity levels:**
- 🔴 **Critical** — Hard constraint violated, multiple conflicts
- 🟡 **Warning** — Potential conflict, needs attention
- 🟢 **Info** — Minor tension, informational

**Options:**
- `-v, --verbose` — Show full details
- `--full` — Show full content without truncation
- `--format` — Output format: `auto`, `table`, `list`, `json`

**When:** Starting a session. Before making related decisions. Reviewing project health.

---

### `babel endorse <id>` — Endorse a Decision

**What:** Add your consensus to a decision (P5: Dual-Test Truth).

**Why:** Decisions need both consensus AND evidence to be fully validated.

```bash
# Endorse a decision
babel endorse abc123

# With comment
babel endorse abc123 --comment "Tested this approach, works well"
```

**Options:**
- `decision_id` — Decision ID (or prefix) to endorse
- `--comment, -c` — Optional comment on why endorsing

**When:** You agree a decision is correct. After reviewing and validating.

---

### `babel evidence-decision <id> "content"` — Add Evidence to Decision

**What:** Add grounding evidence to a decision (P5: Dual-Test Truth).

**Why:** Evidence without consensus is unreviewed. Consensus without evidence is groupthink.

```bash
# Add evidence
babel evidence-decision abc123 "Tests pass with 10,000 concurrent users"

# Specify type
babel evidence-decision abc123 "Customer confirmed feature works" --type user_feedback
babel evidence-decision abc123 "p99 latency < 100ms" --type benchmark
```

**Options:**
- `decision_id` — Decision ID (or prefix)
- `content` — The evidence
- `--type` — Evidence type: `observation`, `benchmark`, `user_feedback`, `outcome`, `other`

**When:** You have proof a decision works. Tests pass. Metrics met. User confirmed.

---

### `babel validation` — Show Validation Status

**What:** Display which decisions have consensus, evidence, or both (P5).

**Why:** Identifies groupthink risks (consensus only) and unreviewed decisions (evidence only).

```bash
# Overview
babel validation
# → ● Validated (consensus + evidence): 23
# → ◐ Consensus only (groupthink risk): 5
# → ◑ Evidence only (needs review): 3
# → ○ Unvalidated: 12

# Check specific decision
babel validation abc123

# Full details
babel validation --full
```

**Validation states:**
- ● **Validated** — Both consensus AND evidence (solid)
- ◐ **Consensus only** — Endorsed but no evidence (groupthink risk)
- ◑ **Evidence only** — Evidence but no endorsement (needs review)
- ○ **Unvalidated** — Neither consensus nor evidence

**Options:**
- `decision_id` — Optional: check specific decision
- `-v, --verbose` — Show full details
- `--full` — Show full content without truncation
- `--format` — Output format: `auto`, `table`, `list`, `json`, `detail`

**When:** Reviewing decision quality. Before releases. Identifying risks.

---

### `babel question "content"` — Raise an Open Question

**What:** Record something you don't know yet (P6: Ambiguity Management).

**Why:** Uncertainty is information. Capturing unknowns prevents premature decisions.

```bash
# Raise a question
babel question "Should we use REST or GraphQL for the API?"

# With context
babel question "Auth strategy for mobile?" --context "Affects offline mode design"

# Attribute domain
babel question "How to handle PCI compliance?" --domain security
```

**Options:**
- `content` — The question
- `--context, -c` — Why this question matters
- `--domain, -d` — Related expertise domain

**When:** You're uncertain about something important. Decision can't be made yet. Need input from others.

---

### `babel questions` — Show Open Questions

**What:** Display acknowledged unknowns (P6).

**Why:** See what hasn't been decided yet. Surfaces at session start.

```bash
# Show open questions
babel questions
# → [abc123] Should we use REST or GraphQL?
# → [def456] How to handle offline sync?

# Full details
babel questions --full
```

**Options:**
- `-v, --verbose` — Show full details
- `--full` — Show full content without truncation
- `--format` — Output format: `auto`, `table`, `list`, `json`

**When:** Starting a session. Reviewing project state. Planning work.

---

### `babel resolve-question <id> "resolution"` — Resolve an Open Question

**What:** Close an open question with an answer (P6).

**Why:** Moves from unknown to known. Documents the conclusion.

```bash
# Answer a question
babel resolve-question abc123 "Chose REST for simpler caching on mobile"

# Mark as dissolved (no longer relevant)
babel resolve-question abc123 "Requirements changed, not needed" --outcome dissolved

# Mark as superseded
babel resolve-question abc123 "Replaced by broader API strategy" --outcome superseded
```

**Options:**
- `question_id` — Question ID (or prefix)
- `resolution` — The answer or conclusion
- `--outcome` — How resolved: `answered`, `dissolved`, `superseded`

**When:** Question has been answered. Requirements changed. Question superseded.

---

### `babel deprecate <id> "reason"` — Deprecate an Artifact

**What:** Mark an artifact as no longer valid (P7: Living Memory).

**Why:** De-prioritizes without deleting. Maintains history while indicating obsolescence.

```bash
# Deprecate a decision
babel deprecate abc123 "Superseded by new caching strategy"

# With link to replacement
babel deprecate abc123 "Replaced by Redis approach" --superseded-by def456
```

**Options:**
- `artifact_id` — Artifact ID (or prefix) to deprecate
- `reason` — Why it is being deprecated
- `--superseded-by` — ID of replacement artifact

**When:** Decision is outdated. Context has changed. Better approach exists.

---

### `babel review` — Review Pending Proposals

**What:** Review AI-extracted proposals for human approval (HC2: Human Authority).

**Why:** AI proposes, human decides. Ensures human oversight over knowledge capture.

```bash
# See pending proposals
babel review
# → 5 proposal(s) pending:
# → 1. [abc123] [DECISION] Use Redis for caching
# → 2. [def456] [CONSTRAINT] Max 100 concurrent users

# List without prompting (AI-safe)
babel review --list

# Accept specific proposal
babel review --accept abc123

# Accept all proposals
babel review --accept-all

# Reject specific proposal
babel review --reject abc123

# Synthesize into themes
babel review --synthesize
babel review --by-theme
```

**Options:**
- `--list` — List proposals without prompting (AI-safe)
- `--accept <id>` — Accept specific proposal by ID
- `--accept-all` — Accept all proposals (AI-safe)
- `--synthesize, -s` — Synthesize proposals into themes
- `--by-theme` — Review by theme (requires `--synthesize` first)
- `--accept-theme <theme>` — Accept all proposals in a theme
- `--list-themes` — List synthesized themes
- `--format` — Output format for `--list`

**When:** After AI captures decisions. Periodically during session. Before committing.

---

### `babel check` — Verify Project Integrity

**What:** Diagnose issues and suggest recovery actions.

**Why:** Ensures data consistency. Identifies problems before they compound.

```bash
# Run integrity check
babel check
# → ✓ .babel/ directory exists
# → ✓ Shared events: 234 events
# → ✓ Graph: 156 nodes, 312 edges
# → ✓ All checks passed

# Attempt automatic repair
babel check --repair
```

**Options:**
- `--repair` — Attempt automatic repair of issues

**When:** Something feels wrong. After recovery. Verifying project health.

---

### `babel map` — Generate Project Structure Map

**What:** Create a semantic map of the project for LLM understanding.

**Why:** Provides instant project structure understanding without reading entire codebase.

```bash
# Generate fresh map
babel map --refresh

# Incremental update (only changed files)
babel map --update

# Check map status
babel map --status
```

**Options:**
- `--refresh` — Regenerate map from scratch
- `--update` — Incremental update (changed files only)
- `--status` — Show map status

**When:** After major changes. Onboarding new AI assistant. Project restructuring.

---

### `babel help` — Extended Help

**What:** Show comprehensive help for workflows and concepts.

**Why:** Detailed explanations beyond command syntax.

```bash
babel help
```

**When:** Learning Babel. Understanding workflows. Need detailed guidance.

---

### `babel principles` — Show Babel Principles

**What:** Display framework principles for self-check (P11: Reflexivity).

**Why:** Reference the principles that guide Babel's design.

```bash
babel principles
# → P1: Bootstrap from Need
# → P2: Emergent Ontology
# → ...
```

**When:** Self-checking alignment. Understanding framework philosophy. Training.

---

### `babel process-queue` — Process Offline Queue

**What:** Process queued extractions after being offline.

**Why:** Handles captures made while LLM was unavailable.

```bash
# Process queue
babel process-queue

# Queue results for review (for AI operators)
babel process-queue --batch
```

**Options:**
- `--batch` — Queue proposals for review instead of interactive confirm

**When:** After coming back online. Processing deferred extractions.

---

### `babel capture-commit` — Capture Last Git Commit

**What:** Extract reasoning from the most recent git commit.

**Why:** Captures commit intent for the knowledge graph.

```bash
# Capture last commit
babel capture-commit

# Queue for later processing
babel capture-commit --async
```

**Options:**
- `--async` — Queue extraction for later

**When:** After committing. Manually capturing commit reasoning.

---

## How It Works

### Data Storage

```
your-project/
├── .git/                      # Git (unchanged)
├── .babel/
│   ├── shared/                # Team knowledge (Git-tracked)
│   │   ├── events.jsonl       # Decision history
│   │   └── vocabulary.json    # Learned terminology
│   ├── local/                 # Personal notes (Git-ignored)
│   │   └── events.jsonl       # Your scratch space
│   ├── refs/                  # Fast lookup index
│   │   ├── topics/            # Topic → events mapping
│   │   └── decisions/         # Decision indexes
│   └── graph.db               # Relationship cache
├── .system_prompt.md          # LLM instructions (Git-tracked)
└── .gitignore                 # Includes .babel/local/
```

**What Git tracks** (shared with team):
- `.babel/shared/` — Team decisions and vocabulary
- `.system_prompt.md` — AI assistant instructions

**What Git ignores** (stays local):
- `.babel/local/` — Personal experiments and notes

### The Event Model

Everything in Babel is an **event** — an immutable record of something that happened.

```python
Event:
  id: "evt_abc123..."           # Unique identifier
  type: "artifact_confirmed"    # What kind of event
  timestamp: "2025-01-14T..."   # When it happened
  data: { ... }                 # The content
  scope: "shared"               # Team or personal
```

Events are append-only. History is never rewritten. You can always trace back.

### Scope: Shared vs Local

| Scope | Symbol | Git | Use Case |
|-------|--------|-----|----------|
| Shared | ● | Tracked | Team decisions, confirmed choices |
| Local | ○ | Ignored | Personal notes, experiments, drafts |

**Default is local** — safe to experiment. Use `--share` or `babel share` when ready to commit to a decision.

### Vocabulary Learning

Babel learns your project's terminology:

```bash
# First time
babel capture "Using DynamoDB for user data"
# Babel learns: dynamodb → database cluster

# Later
babel why "database"
# Finds DynamoDB decision via semantic understanding

babel why "dynamo"  
# Also finds it (learned abbreviation)
```

The vocabulary grows automatically. No configuration needed.

### AI Integration

Babel uses LLMs for:
1. **Extraction** — Finding structure in captured text
2. **Scanning** — Providing context-aware advice
3. **Coherence** — Detecting drift and conflicts

**Works without AI too** — basic extraction uses pattern matching. AI makes it smarter, not dependent.

**Supported providers:** Claude (default), OpenAI, Gemini

**Single model approach:** Babel currently uses one model for all tasks. The default (Claude Sonnet) balances quality and cost. For detailed configuration options, see [Configure LLM](#configure-llm-optional-but-recommended).

---

## Smart Features

### Semantic Search

Babel understands meaning, not just keywords:

```bash
babel capture "We're using Postgres for the main database"

babel why "PostgreSQL"  # Finds it (canonical name)
babel why "database"    # Finds it (category)
babel why "pg"          # Finds it (abbreviation)
babel why "data store"  # Finds it (concept)
```

### Context-Aware Scanning

Unlike generic linters, `babel scan` knows your project:

```
Generic scanner:
  "Consider using TypeScript for type safety"
  
Babel scan:
  "Your constraint 'keep stack simple for junior devs' 
   suggests TypeScript might add unwanted complexity.
   Consider: JSDoc types as a lighter alternative."
```

The scan references YOUR decisions and constraints.

### Git Integration

Babel flows with Git naturally:

```bash
# Your workflow doesn't change
git add .
git commit -m "Add caching layer"
git push

# Babel data travels with code
# Teammates get your reasoning on git pull
```

Optional hooks capture commit context automatically.

---

## Installation & Configuration

### Install from PyPI

```bash
pip install babel-intent
```

### Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/ktiyab/babel-tool.git
cd babel

# Install in editable mode (recommended for testing/development)
pip install -e .

# With LLM provider support
pip install -e ".[claude]"      # Anthropic Claude
pip install -e ".[openai]"      # OpenAI GPT
pip install -e ".[gemini]"      # Google Gemini
pip install -e ".[all]"         # All providers

# With development dependencies (pytest)
pip install -e ".[dev]"
```

### Build Package

```bash
# Build distributable package
pip install build
python -m build

# Creates dist/babel_intent-0.1.0-py3-none-any.whl
pip install dist/babel_intent-0.1.0-py3-none-any.whl
```

### Run Without Installing

```bash
# Run directly from source directory
cd babel-tool
python -m babel.cli --help
python -m babel.cli init "Test project"
```

### Verify Installation

```bash
babel --help
babel init "Test project"
babel status
```

**Requirements:**
- Python 3.9+
- Git (for collaboration features)

### Configure LLM (Recommended for Scale)

Babel uses a [two-LLM architecture](#the-two-llm-architecture). Your coding LLM (Claude Code, Cursor, etc.) runs babel commands, while Babel's internal LLM summarizes and structures decision history.

**Without an API key:** Babel works offline using pattern matching. Fine for small projects, but your coding LLM may experience context overload as decision history grows.

**With an API key:** Babel's internal LLM pre-processes history, delivering optimized context to your coding LLM. Scales to hundreds of decisions without degradation.

#### Setting Up API Keys

Each provider uses an environment variable for authentication:

```bash
# Claude (Anthropic) — Default provider
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google Gemini
export GOOGLE_API_KEY="..."
```

Add to your shell profile (`~/.bashrc`, `~/.zshrc`) to persist across sessions.

#### Selecting a Provider

```bash
# View current configuration
babel config

# Switch to Claude (default)
babel config --set llm.provider=claude

# Switch to OpenAI
babel config --set llm.provider=openai

# Switch to Gemini
babel config --set llm.provider=gemini
```

#### Selecting a Model

Each provider has a default model, but you can override it:

```bash
# Use a powerful model for complex tasks
babel config --set llm.model=claude-opus-4-1-20250414
babel config --set llm.model=gpt-5.2-pro
babel config --set llm.model=gemini-2.5-pro

# Use a lightweight model for cost efficiency
babel config --set llm.model=claude-3-5-haiku-20241022
babel config --set llm.model=gpt-5-nano
babel config --set llm.model=gemini-2.5-flash-lite

# Clear model override (use provider default)
babel config --set llm.model=
```

**Available models by provider:**

| Provider | Category | Models |
|----------|----------|--------|
| `claude` | Large / Powerful | `claude-opus-4-1-20250414`, `claude-opus-4-20250514` |
| | **Balanced (default)** | `claude-sonnet-4-20250514` |
| | Lightweight | `claude-3-7-sonnet-20250219`, `claude-3-5-haiku-20241022` |
| `openai` | Large / Powerful | `gpt-5.2`, `gpt-5.2-pro`, `gpt-5.2-chat-latest` |
| | **Balanced (default)** | `gpt-5-mini` |
| | Lightweight | `gpt-5-nano` |
| `gemini` | Large / Powerful | `gemini-2.5-pro`, `gemini-3-flash-preview` |
| | **Balanced (default)** | `gemini-2.5-flash` |
| | Lightweight | `gemini-2.5-flash-lite`, `gemini-2.5-flash-image` |

**Default models** (balanced quality/cost):
- Claude: `claude-sonnet-4-20250514`
- OpenAI: `gpt-5-mini`  
- Gemini: `gemini-2.5-flash`

#### Per-Project vs User Configuration

```bash
# Project-level (stored in .babel/config.yaml, shared with team)
babel config --set llm.provider=claude

# User-level (stored in ~/.babel/config.yaml, personal preference)
babel config --set llm.provider=openai --user
```

User config overrides project config for local settings.

#### Environment Variable Override

For CI/CD or temporary overrides:

```bash
# Override provider for this session
export INTENT_LLM_PROVIDER=openai
export INTENT_LLM_MODEL=gpt-5-nano

babel scan  # Uses OpenAI with gpt-5-nano
```

#### What Uses the LLM?

| Feature | LLM Usage | Without LLM |
|---------|-----------|-------------|
| `babel capture` | Smart extraction of decisions/constraints | Pattern matching fallback |
| `babel scan` | Context-aware code analysis | Not available |
| `babel coherence` | AI-powered coherence checking | Basic consistency check |

#### Cost Considerations

Babel uses LLM sparingly:
- **Extraction:** ~500-1000 tokens per capture
- **Scanning:** ~2000-4000 tokens per scan
- **Coherence:** ~1000-2000 tokens per check

For cost-conscious usage:
```bash
# Use lightweight/cheaper models
babel config --set llm.model=gpt-5-nano             # OpenAI (cheapest)
babel config --set llm.model=gemini-2.5-flash-lite  # Gemini (cheapest)
babel config --set llm.model=claude-3-5-haiku-20241022  # Claude (cheapest)
```

#### Checking LLM Status

```bash
babel status
# Shows: Extraction: claude (claude-sonnet-4-20250514)
# Or:    Extraction: not configured (pattern matching)
```

#### Without LLM

Babel works fully offline without any API key:

```bash
# All core features work:
babel init "Build offline-first app"
babel capture "We chose SQLite for local storage"
babel why "database"
babel status
babel history

# These are enhanced by LLM but not required:
babel capture "..."  # Falls back to pattern matching
babel scan           # Requires LLM
```

### Display Options

```bash
# Use ASCII symbols (for terminals without Unicode)
babel config --set display.symbols=ascii
```

---

## Recovery & Onboarding

### New Team Member Onboarding

When joining an existing project with Babel:

```bash
# 1. Clone the repository (includes .babel/shared/)
git clone <repo-url>
cd <project>

# 2. Sync to rebuild local graph from shared events
babel sync

# 3. Check project status
babel status

# 4. Understand the project
babel why "architecture"    # Query specific topics
babel scan                  # Get AI overview

# 5. (Optional) Set up your LLM for smart features
export ANTHROPIC_API_KEY="your-key"
```

That's it. All shared reasoning is in `.babel/shared/` which git provides.

### Integrity Check

Verify project health anytime:

```bash
babel check

# Output:
# Babel Integrity Check
# ========================================
# ✓ .babel/ directory exists
# ✓ Shared events: 47 events
# ✓ Local events: 12 events
# ✓ Graph: 23 nodes, 45 edges
# ✓ Config: claude (claude-sonnet-4-20250514)
# ✓ Purpose defined: 1 purpose(s)
# ✓ Git repository detected
# ✓ Local data protected (.gitignore)
# ✓ Local data not tracked in git
# ----------------------------------------
# ✓ All checks passed. Project is healthy.
```

If issues are found:

```bash
babel check --repair    # Attempt automatic fixes (rebuilds graph, fixes .gitignore)
```

### Recovery Scenarios

| Scenario | Recovery |
|----------|----------|
| Graph corrupted/deleted | `babel sync` → rebuilds from events |
| `.babel/shared/` deleted | `git checkout .babel/shared/` |
| `.babel/` completely deleted | `git checkout .babel/` then `babel sync` |
| Local events lost | Cannot recover (by design — personal/unshared) |
| Config corrupted | `git checkout .babel/config.yaml` or `babel config --set` |

### Data Architecture (Recovery Perspective)

```
.babel/
├── shared/              ← Git-tracked (recoverable via git)
│   └── events.jsonl     ← Source of truth for team
├── local/               ← Git-ignored (personal, not recoverable)
│   └── events.jsonl     ← Your private notes
├── graph.db             ← Derived cache (rebuilt by `babel sync`)
├── config.yaml          ← Git-tracked (recoverable via git)
└── .gitignore           ← Protects local data from accidental commit
```

**Key insight:** Everything important is either:
1. In git (shared events, config) → recoverable
2. Derived from git data (graph) → rebuildable
3. Personal by design (local events) → your responsibility

### Local Data Protection

Babel automatically prevents local (personal) data from being committed to git:

**Automatic protection:**
```bash
# .babel/.gitignore (created automatically)
local/
graph.db
graph.db-journal
```

**Verification:**
```bash
babel check

# Shows:
# ✓ Local data protected (.gitignore)
# ✓ Local data not tracked in git
```

**If protection is missing:**
```bash
babel check --repair
# ✓ Fixed .babel/.gitignore (local data now protected)
```

**If local data was accidentally committed:**
```bash
# babel check will show:
# [CRITICAL] Local events ARE tracked in git!
#   Fix: Run: git rm --cached .babel/local/ && git commit

# To fix:
git rm --cached .babel/local/
git commit -m "Remove accidentally committed local data"
```

**Why this matters:**
- Local events may contain personal notes, experiments, or sensitive thoughts
- Team members shouldn't see each other's unshared work
- Accidental commits could leak private information

### Principles That Enable Recovery

| Principle | How It Helps |
|-----------|--------------|
| **HC1: Immutable Events** | History is append-only, never edited → can't be corrupted, only lost |
| **HC3: Offline-First** | Everything is local files → recovery is file recovery |
| **P7: Evidence-Weighted Memory** | Deprecate, not delete → reduces accidental data loss |
| **P11: Framework Self-Application** | `babel check` verifies own integrity |

### Backup Recommendations

For critical projects:

```bash
# Git already provides backup for shared data
git push origin main

# For local events (if you want to preserve them)
cp .babel/local/events.jsonl ~/babel-backup/$(date +%Y%m%d)-local.jsonl
```

---

## FAQ

### Do I need to learn Babel commands?

**Not really.** If you use an AI assistant with the system prompt, the AI handles most Babel operations for you. It suggests captures, queries context, and warns about conflicts. You can learn commands later if you want direct control.

### Do I need an LLM API key?

**For small projects:** No. Babel works without one. Core features (capture, query, share, sync) are fully functional offline.

**For growing projects:** Yes, strongly recommended. See [The Two-LLM Architecture](#the-two-llm-architecture) above.

Here's why: Your coding LLM (Claude Code, Cursor, etc.) runs babel commands. When you query `babel why "topic"`, the results go back to your coding LLM. Without an API key, raw decision history is returned — which can overwhelm your coding LLM's context window as history grows.

With an API key, Babel's internal LLM summarizes and structures that history *before* returning it to your coding LLM. This keeps your coding LLM effective even with hundreds of decisions.

**The tradeoff:**
- No API key = works offline, but context overload risk at scale
- With API key = optimized context, scales to large projects (pennies per query)

**Recommendation:** Set up an API key early. Claude Sonnet is the default and offers a good balance of quality and cost.

### How does my AI assistant know about Babel?

The `.system_prompt.md` file contains instructions for AI assistants. When you add it to your AI's context (custom instructions, project knowledge, etc.), the AI learns to use Babel automatically. Run `babel prompt` to see what it contains.

### Which AI assistants work with Babel?

Any AI that accepts custom instructions:
- **Claude** (Anthropic) — Projects, custom instructions
- **ChatGPT** (OpenAI) — Custom GPTs, custom instructions
- **Cursor** — Rules for AI
- **Cody** — Custom instructions
- **Any LLM** — Via the system prompt

### How is this different from code comments?

Comments describe WHAT code does. Babel captures WHY decisions were made. Comments live in code and rot. Babel captures live in a queryable, connected knowledge base that your AI can search.

### How is this different from ADRs (Architecture Decision Records)?

ADRs are great but heavyweight. Babel is lightweight capture that can *become* ADRs if needed. Capture first, formalize later. Plus, ADRs aren't queryable by AI — Babel is.

### Does this add overhead to my workflow?

Minimal, and mostly handled by AI. When you explain something to your AI assistant, it suggests capturing. When you ask "why", it queries Babel. You don't have to remember to use it.

### What if I capture something wrong?

Events are immutable, but you can capture corrections. Babel shows the evolution, including changed minds. That's valuable too — knowing WHY something changed matters as much as knowing what it is now.

### How does team collaboration work?

- Shared decisions (`.babel/shared/`) are Git-tracked
- When you push, teammates get your reasoning
- When you pull, you get theirs
- `babel sync` resolves any merge situations
- Everyone's AI assistant sees the same project context

### What's the performance impact?

Negligible. Babel stores data in efficient append-only files. Queries use indexed lookups. Most commands complete in milliseconds.

### Is my data private?

- Local captures (`.babel/local/`) never leave your machine
- Shared captures (`.babel/shared/`) go where your Git repo goes
- LLM features send data to your configured provider
- The system prompt contains project context — treat it like code

---

## The Name

The Tower of Babel scattered human understanding — people could no longer comprehend each other's intent.

This Babel does the opposite. It gathers understanding. It preserves intent. It helps teams speak the same language about their code.

*Inverting the Tower of Babel. Restoring shared understanding.*

---

## Project Status

**Tests:** 647 passing

**Modules:**
- `events.py` — Immutable event store (with TensionSeverity enum and ontology events)
- `scope.py` — Shared/local collaboration
- `refs.py` — O(1) semantic lookup
- `loader.py` — Token-efficient loading
- `vocabulary.py` — Learning terminology
- `scanner.py` — Context-aware analysis
- `graph.py` — Relationship tracking (with tensions_with, evolves_from, requires_negotiation edges)
- `coherence.py` — Drift detection (with auto-tension detection and severity grading)
- `extractor.py` — AI-powered extraction
- `providers.py` — LLM abstraction
- `domains.py` — P3 expertise governance
- `tensions.py` — P4 disagreement handling (with evolves_from linking on resolve)
- `validation.py` — P5 dual-test truth
- `ambiguity.py` — P6 open questions
- `config.py` — Configuration management
- `git.py` — Git integration
- `review.py` — Proposal review (with requires_negotiation detection)
- `commit_links.py` — Git-babel bridge storage (decision↔commit links)
- `commands/gaps.py` — Implementation gap detection (P7, P8)
- `commands/suggest_links.py` — AI-assisted decision→commit matching
- `cli.py` — Command interface

---

## Babel Installation Guide

**Package built successfully. 509 tests passing.**

### Quick Installation Methods

#### 1. Development Install (Recommended for Testing)

```bash
git clone https://github.com/ktiyab/babel-tool.git
cd babel

# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install in editable mode
pip install -e .

# Verify
babel --help
```

#### 2. With Optional Dependencies

```bash
pip install -e ".[dev]"      # + pytest for testing
pip install -e ".[claude]"   # + Anthropic SDK
pip install -e ".[openai]"   # + OpenAI SDK
pip install -e ".[gemini]"   # + Google SDK
pip install -e ".[all]"      # All providers
```

#### 3. Build & Install Package

```bash
# Build
pip install build
python -m build

# Install from wheel
pip install dist/babel_intent-0.1.0-py3-none-any.whl
```

#### 4. Run Without Installing

```bash
cd babel-tool
python -m babel.cli --help
python -m babel.cli init "Test project"
python -m babel.cli status
```

#### 5. Run Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

### Package Structure

```
babel-tool/
├── babel/                 # Source code
│   ├── cli.py            # Main CLI
│   ├── events.py         # Event store
│   ├── graph.py          # Knowledge graph
│   └── ...
├── tests/                # 509 tests
├── dist/                 # Built packages
│   ├── babel_intent-0.1.0-py3-none-any.whl
│   └── babel_intent-0.1.0.tar.gz
├── pyproject.toml        # Package config
└── README.md
```

### pyproject.toml Highlights

```toml
[project]
name = "babel-intent"
version = "0.1.0"
requires-python = ">=3.9"

dependencies = ["pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]
claude = ["anthropic>=0.18.0"]
openai = ["openai>=1.0.0"]
gemini = ["google-generativeai>=0.3.0"]

[project.scripts]
babel = "babel.cli:main"
```

### Verification Commands

```bash
# Check installation
babel --help

# Initialize test project
babel init "Test project" --need "Testing Babel"

# Run integrity check
babel check

# View principles
babel principles

# Run tests
pytest tests/ -q
```

---

## Contributing

Babel is built on the principle that **reasoning should travel with code**. Contributions that advance this mission are welcome.

---

## License

MIT

---

*Where the original Babel scattered understanding, this Babel gathers it.*
