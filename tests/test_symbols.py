"""
Tests for Symbols — Visual vocabulary validation

Tests Unicode/ASCII detection and symbol formatting.
"""

import os
from unittest.mock import patch

from babel.presentation.symbols import (
    get_symbols, supports_unicode, UNICODE, ASCII,
    symbol_for_type, symbol_for_status,
    format_artifact, format_status_line, format_trace,
    TableRenderer
)


class TestSymbolSets:
    """Test symbol set completeness."""

    def test_unicode_has_all_symbols(self):
        """Unicode set has all required symbols."""
        assert UNICODE.purpose
        assert UNICODE.decision
        assert UNICODE.constraint
        assert UNICODE.principle
        assert UNICODE.tension
        assert UNICODE.drift
        assert UNICODE.coherent
        assert UNICODE.ambiguous
        assert UNICODE.checkpoint
        assert UNICODE.trace

    def test_ascii_has_all_symbols(self):
        """ASCII set has all required symbols."""
        assert ASCII.purpose
        assert ASCII.decision
        assert ASCII.constraint
        assert ASCII.principle
        assert ASCII.tension
        assert ASCII.drift
        assert ASCII.coherent
        assert ASCII.ambiguous
        assert ASCII.checkpoint
        assert ASCII.trace

    def test_ascii_is_printable(self):
        """ASCII symbols are all printable ASCII."""
        for sym in [ASCII.purpose, ASCII.decision, ASCII.constraint,
                    ASCII.principle, ASCII.tension, ASCII.drift,
                    ASCII.coherent, ASCII.ambiguous, ASCII.checkpoint, ASCII.trace]:
            assert all(32 <= ord(c) <= 126 for c in sym), f"Non-printable ASCII in {sym}"


class TestSymbolSelection:
    """Test symbol set selection logic."""

    def test_explicit_unicode(self):
        """Explicit unicode preference returns unicode."""
        symbols = get_symbols("unicode")
        assert symbols is UNICODE

    def test_explicit_ascii(self):
        """Explicit ascii preference returns ascii."""
        symbols = get_symbols("ascii")
        assert symbols is ASCII

    def test_auto_respects_detection(self):
        """Auto mode uses detection result."""
        with patch('babel.presentation.symbols.supports_unicode', return_value=True):
            assert get_symbols("auto") is UNICODE
            assert get_symbols(None) is UNICODE

        with patch('babel.presentation.symbols.supports_unicode', return_value=False):
            assert get_symbols("auto") is ASCII
            assert get_symbols(None) is ASCII


class TestUnicodeDetection:
    """Test Unicode support detection."""

    def test_utf8_lang_enables_unicode(self):
        """UTF-8 in LANG enables unicode."""
        with patch.dict(os.environ, {'LANG': 'en_US.UTF-8'}, clear=False):
            # Clear other env vars that might affect detection
            with patch.dict(os.environ, {'BABEL_ASCII_ONLY': '', 'BABEL_UNICODE': ''}, clear=False):
                assert supports_unicode() is True

    def test_ascii_only_env_disables(self):
        """BABEL_ASCII_ONLY disables unicode."""
        with patch.dict(os.environ, {'BABEL_ASCII_ONLY': '1', 'LANG': 'en_US.UTF-8'}, clear=False):
            assert supports_unicode() is False

    def test_unicode_env_enables(self):
        """BABEL_UNICODE forces unicode."""
        with patch.dict(os.environ, {'BABEL_UNICODE': 'true', 'BABEL_ASCII_ONLY': ''}, clear=False):
            assert supports_unicode() is True

    def test_windows_terminal_detected(self):
        """Windows Terminal is detected."""
        with patch.dict(os.environ, {'WT_SESSION': 'some-guid', 'BABEL_ASCII_ONLY': '', 'BABEL_UNICODE': ''}, clear=False):
            assert supports_unicode() is True

    def test_vscode_detected(self):
        """VSCode terminal is detected."""
        with patch.dict(os.environ, {'TERM_PROGRAM': 'vscode', 'BABEL_ASCII_ONLY': '', 'BABEL_UNICODE': ''}, clear=False):
            assert supports_unicode() is True


class TestSymbolForType:
    """Test type-to-symbol mapping."""

    def test_known_types(self):
        """Known artifact types map correctly."""
        assert symbol_for_type(UNICODE, 'purpose') == UNICODE.purpose
        assert symbol_for_type(UNICODE, 'decision') == UNICODE.decision
        assert symbol_for_type(UNICODE, 'constraint') == UNICODE.constraint
        assert symbol_for_type(ASCII, 'purpose') == ASCII.purpose
        assert symbol_for_type(ASCII, 'decision') == ASCII.decision

    def test_unknown_type_defaults(self):
        """Unknown type defaults to decision."""
        assert symbol_for_type(UNICODE, 'unknown') == UNICODE.decision
        assert symbol_for_type(ASCII, 'unknown') == ASCII.decision


class TestSymbolForStatus:
    """Test status-to-symbol mapping."""

    def test_known_statuses(self):
        """Known statuses map correctly."""
        assert symbol_for_status(UNICODE, 'coherent') == UNICODE.coherent
        assert symbol_for_status(UNICODE, 'tension') == UNICODE.tension
        assert symbol_for_status(UNICODE, 'drift') == UNICODE.drift
        assert symbol_for_status(ASCII, 'coherent') == ASCII.coherent

    def test_unknown_status_defaults(self):
        """Unknown status defaults to ambiguous."""
        assert symbol_for_status(UNICODE, 'unknown') == UNICODE.ambiguous
        assert symbol_for_status(ASCII, 'unknown') == ASCII.ambiguous


class TestFormatting:
    """Test output formatting functions."""

    def test_format_artifact_with_status(self):
        """Formats artifact with status symbol."""
        result = format_artifact(UNICODE, 'decision', 'Use SQLite', 'coherent')
        assert UNICODE.decision in result
        assert 'Use SQLite' in result
        assert UNICODE.coherent in result

    def test_format_artifact_without_status(self):
        """Formats artifact without status symbol."""
        result = format_artifact(UNICODE, 'purpose', 'Build a tool')
        assert UNICODE.purpose in result
        assert 'Build a tool' in result

    def test_format_status_line(self):
        """Formats coherence status line."""
        result = format_status_line(UNICODE, 'coherent', 'checked 2h ago')
        assert 'Coherence:' in result
        assert UNICODE.coherent in result
        assert '2h ago' in result

    def test_format_trace_normal(self):
        """Formats normal trace."""
        result = format_trace(UNICODE, 'decision', 'constraint', 'offline-first', is_conflict=False)
        assert UNICODE.trace in result
        assert 'links to' in result
        assert UNICODE.constraint in result

    def test_format_trace_conflict(self):
        """Formats conflict trace."""
        result = format_trace(UNICODE, 'decision', 'constraint', 'offline-first', is_conflict=True)
        assert UNICODE.trace_conflict in result
        assert 'conflicts with' in result


class TestASCIIFallback:
    """Test ASCII mode works correctly."""

    def test_ascii_format_artifact(self):
        """ASCII formatting works."""
        result = format_artifact(ASCII, 'decision', 'Use SQLite', 'coherent')
        assert '[>]' in result
        assert '[+]' in result
        assert 'Use SQLite' in result

    def test_ascii_format_status(self):
        """ASCII status line works."""
        result = format_status_line(ASCII, 'tension', 'just checked')
        assert '[!]' in result
        assert 'Coherence:' in result


class TestTableBorders:
    """Test table border symbols."""

    def test_unicode_has_all_borders(self):
        """Unicode set has all table border symbols."""
        assert UNICODE.box_h
        assert UNICODE.box_v
        assert UNICODE.box_tl
        assert UNICODE.box_tr
        assert UNICODE.box_bl
        assert UNICODE.box_br
        assert UNICODE.box_cross
        assert UNICODE.box_t_down
        assert UNICODE.box_t_up
        assert UNICODE.box_t_right
        assert UNICODE.box_t_left

    def test_ascii_has_all_borders(self):
        """ASCII set has all table border symbols."""
        assert ASCII.box_h
        assert ASCII.box_v
        assert ASCII.box_tl
        assert ASCII.box_tr
        assert ASCII.box_bl
        assert ASCII.box_br
        assert ASCII.box_cross
        assert ASCII.box_t_down
        assert ASCII.box_t_up
        assert ASCII.box_t_right
        assert ASCII.box_t_left

    def test_ascii_borders_are_printable(self):
        """ASCII border symbols are printable ASCII."""
        borders = [ASCII.box_h, ASCII.box_v, ASCII.box_tl, ASCII.box_tr,
                   ASCII.box_bl, ASCII.box_br, ASCII.box_cross,
                   ASCII.box_t_down, ASCII.box_t_up, ASCII.box_t_right, ASCII.box_t_left]
        for sym in borders:
            assert all(32 <= ord(c) <= 126 for c in sym), f"Non-printable ASCII in border {sym}"


class TestTableRenderer:
    """Test TableRenderer class."""

    def test_render_themes_empty(self):
        """Empty themes returns message."""
        renderer = TableRenderer(UNICODE, width=80)
        result = renderer.render_themes([])
        assert "No themes" in result

    def test_render_themes_unicode(self):
        """Renders themes with Unicode borders."""
        renderer = TableRenderer(UNICODE, width=100)
        themes = [{
            'letter': 'A',
            'name': 'Test Theme',
            'risk': 'low',
            'recommendation': 'Accept',
            'description': 'Test impact',
            'rationale': 'Test rationale',
            'proposals': [1, 2]
        }]
        result = renderer.render_themes(themes)
        assert '┌' in result  # Unicode top-left
        assert '│' in result  # Unicode vertical
        assert 'Test Theme' in result
        assert 'IMPACT:' in result
        assert 'WHY:' in result

    def test_render_themes_ascii(self):
        """Renders themes with ASCII borders."""
        renderer = TableRenderer(ASCII, width=100)
        themes = [{
            'letter': 'B',
            'name': 'ASCII Theme',
            'risk': 'medium',
            'recommendation': 'Review',
            'description': 'ASCII impact',
            'rationale': 'ASCII rationale',
            'proposals': [1]
        }]
        result = renderer.render_themes(themes)
        assert '+' in result  # ASCII corner
        assert '|' in result  # ASCII vertical
        assert 'ASCII Theme' in result

    def test_render_themes_truncates(self):
        """Long content is truncated when full=False."""
        renderer = TableRenderer(UNICODE, width=60, full=False)
        themes = [{
            'letter': 'C',
            'name': 'Theme',
            'risk': 'low',
            'recommendation': 'Accept',
            'description': 'A' * 200,  # Very long
            'rationale': 'B' * 200,
            'proposals': []
        }]
        result = renderer.render_themes(themes)
        assert '…' in result  # Truncation indicator

    def test_render_themes_full_mode(self):
        """Full mode doesn't truncate."""
        renderer = TableRenderer(UNICODE, width=300, full=True)
        long_text = 'X' * 100
        themes = [{
            'letter': 'D',
            'name': 'Theme',
            'risk': 'low',
            'recommendation': 'Accept',
            'description': long_text,
            'rationale': 'Short',
            'proposals': []
        }]
        result = renderer.render_themes(themes)
        assert long_text in result
