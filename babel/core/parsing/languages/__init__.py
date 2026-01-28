"""
Language configurations for symbol extraction.

Each language has its own module defining:
- Symbol queries (what AST nodes to extract)
- Exclude patterns (what paths to skip)
- Custom hooks (naming, docstrings, visibility)

Supported languages:
- python.py: Python (.py)
- javascript.py: JavaScript (.js, .jsx)
- typescript.py: TypeScript (.ts, .tsx)
- html.py: HTML (.html, .htm) - container elements only
- css.py: CSS (.css) - architectural selectors only
- markdown.py: Markdown (.md) - regex-based, special case
"""

from .python import PYTHON_CONFIG
from .javascript import JAVASCRIPT_CONFIG
from .typescript import TYPESCRIPT_CONFIG
from .html import HTML_CONFIG
from .css import CSS_CONFIG

__all__ = [
    'PYTHON_CONFIG',
    'JAVASCRIPT_CONFIG',
    'TYPESCRIPT_CONFIG',
    'HTML_CONFIG',
    'CSS_CONFIG',
]
