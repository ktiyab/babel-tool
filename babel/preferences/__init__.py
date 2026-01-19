"""
Preferences — User preference layer for Babel CLI

Contains user preference systems:
- Memo: Persistent operational shortcuts (mutable, no WHY required)
  - Regular memos: Context-aware preferences
  - Init memos: Foundational instructions (surface at session start)
  - Candidates: AI-detected patterns awaiting confirmation

Design:
- Mutable (unlike HC1 decisions)
- Survives context compression
- Graph-integrated for contextual surfacing
"""

from .memo import Memo, Candidate, MemoManager

__all__ = [
    # Memo
    "Memo", "Candidate", "MemoManager",
]
