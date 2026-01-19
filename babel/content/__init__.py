"""
Content — Static text content for CLI display

Separates presentation text from logic (Single Responsibility).
Text is data, not code embedded in methods.
"""

from .help_text import HELP_TEXT
from .principles_text import PRINCIPLES_TEXT
from .prompts import MINIMAL_SYSTEM_PROMPT, BABEL_LLM_INSTRUCTIONS

__all__ = ['HELP_TEXT', 'PRINCIPLES_TEXT', 'MINIMAL_SYSTEM_PROMPT', 'BABEL_LLM_INSTRUCTIONS']
