"""
Help text for Babel CLI.

Extracted from cli.py for separation of concerns.
"""

HELP_TEXT = """
Babel -- Intent Preservation Tool
================================

Captures reasoning. Answers 'why?'. Quiet until needed.


GETTING STARTED
---------------

  babel init "purpose"          Initialize project with stated purpose
                                Creates .babel/ directory and .system_prompt.md
                                Purpose is shared with team via git


CAPTURING REASONING
-------------------

  babel capture "text"          Capture a thought or decision (local by default)
      --share, -s               Share with team (git-tracked)
      --raw                     Skip AI extraction

  babel capture "We chose X because Y" --share
                                Capture and share with team immediately

  babel share <event_id>        Promote a local capture to shared
                                Use first 8 chars of event ID


QUERYING
--------

  babel why "topic"             Trace reasoning for a topic
                                Shows decisions, constraints, and connections

  babel status                  Show project overview
                                Events, artifacts, coherence, scope counts

  babel history                 Show recent activity
      -n <count>                Number of events (default: 10)
      --shared                  Show only team events
      --local                   Show only personal events


COHERENCE
---------

  babel coherence               Check alignment between purpose and decisions
      --full                    Force full check (ignore cache)
      --qa                      QA/QC mode with detailed report


COLLABORATION
-------------

  babel sync                    Synchronize after git pull
      -v, --verbose             Show details
                                Deduplicates events, rebuilds graph

  Scope markers:
    [S] shared                  Team sees it, git-tracked
    [L] local                   Only you, git-ignored


CONFIGURATION
-------------

  babel config                  View current configuration
      --set KEY=VALUE           Set config value
      --user                    Apply to user config (~/.babel/)

  Examples:
    babel config --set llm.provider=claude
    babel config --set display.symbols=ascii
    babel config --set coherence.auto_check=true


GIT INTEGRATION
---------------

  babel hooks install           Install post-commit hook for auto-capture
  babel hooks uninstall         Remove hooks
  babel hooks status            Check hook status

  babel capture-commit          Manually capture last commit
      --async                   Queue for later processing


LLM INTEGRATION
---------------

  babel prompt                  Output system prompt for LLM integration
                                Copy/paste into your LLM's system prompt

  cat .system_prompt.md         View the system prompt file directly


MEMOS (Persistent Preferences)
------------------------------

  babel memo "content"          Save a preference (reduces repetition)
      --context, -c TOPIC       Add context for targeted surfacing (repeatable)

  babel memo --list             List all saved memos
  babel memo --remove ID        Remove a memo by ID (prefix match ok)
  babel memo --update ID        Update memo content or contexts
  babel memo --relevant TOPIC   Show memos relevant to a topic/context

  babel memo --candidates       Show AI-detected patterns (pending review)
  babel memo --promote ID       Promote candidate to permanent memo
  babel memo --promote-all      Promote all pending candidates
  babel memo --dismiss ID       Dismiss candidate (won't suggest again)
  babel memo --suggest          Show candidates ready for promotion

  babel memo --stats            Show memo/candidate statistics

  Examples:
    babel memo "Always use python3" -c bash -c python
    babel memo --relevant bash
    babel memo --promote c_abc123


OTHER
-----

  babel process-queue           Process queued extractions (after offline)
      --batch                   Queue proposals for review (for AI assistants)
  babel help                    Show this help
  babel --help                  Show argument help


AI ASSISTANT WORKFLOWS
----------------------

  When invoked by AI assistants (Claude, GPT, etc.), use these options
  to avoid interactive prompts that cause EOF errors:

  babel capture "text" --batch  Queue proposals for later review
  babel process-queue --batch   Process queue without interactive confirm

  Human review with: babel review


DIRECTORY STRUCTURE
-------------------

  project/
  +-- .system_prompt.md         LLM instructions (git-tracked)
  +-- .babel/
      +-- shared/events.jsonl   Team events (git-tracked)
      +-- local/events.jsonl    Personal events (git-ignored)
      +-- config.yaml           Project config
      +-- graph.db              Derived cache (git-ignored)


PRINCIPLES
----------

  P1: Reasoning travels with artifacts
  P2: Evolution is traceable
  P3: Coherence is observable

  Low friction: Local by default, share when ready
"""
