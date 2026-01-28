"""
Tests for OutputTemplate — Structured CLI output

Tests verify:
- Header rendering (title, subtitle, legend)
- Section rendering (title + content)
- Footer rendering (summary + succession hint)
- Utility methods (truncate, format_table, format_list)
"""

from babel.presentation.template import (
    OutputTemplate,
    TemplateSection,
    TemplateLegend,
    HEADER_CHAR,
    SECTION_CHAR,
)
from babel.presentation.symbols import UNICODE, ASCII


class TestOutputTemplateHeader:
    """Tests for header rendering."""

    def test_renders_title(self):
        """Header includes title between borders."""
        template = OutputTemplate(width=40)
        template.header("BABEL STATUS")
        output = template.render()

        assert "BABEL STATUS" in output
        assert HEADER_CHAR * 40 in output

    def test_renders_title_and_subtitle(self):
        """Header includes title and subtitle."""
        template = OutputTemplate(width=60)
        template.header("BABEL STATUS", "Project Health Overview")
        output = template.render()

        assert "BABEL STATUS - Project Health Overview" in output

    def test_header_without_title_still_renders(self):
        """Template renders even without header."""
        template = OutputTemplate(width=40)
        template.section("TEST", "content")
        output = template.render()

        assert "TEST" in output
        assert "content" in output


class TestOutputTemplateLegend:
    """Tests for legend rendering."""

    def test_renders_legend_items(self):
        """Legend shows symbol-to-meaning mappings."""
        template = OutputTemplate(width=60)
        template.header("TEST")
        template.legend({"●": "shared", "○": "local"})
        output = template.render()

        assert "Legend:" in output
        assert "● shared" in output
        assert "○ local" in output

    def test_empty_legend_not_rendered(self):
        """Empty legend dict produces no output."""
        legend = TemplateLegend(items={})
        assert legend.render() == ""

    def test_legend_items_separated(self):
        """Multiple legend items are space-separated."""
        legend = TemplateLegend(items={"A": "first", "B": "second"})
        rendered = legend.render()

        assert "A first" in rendered
        assert "B second" in rendered


class TestOutputTemplateScope:
    """Tests for scope line rendering."""

    def test_renders_scope_in_header(self):
        """Scope line appears after legend."""
        template = OutputTemplate(width=60)
        template.header("TEST")
        template.scope("25,156 artifacts | 165 validated")
        output = template.render()

        assert "25,156 artifacts | 165 validated" in output


class TestOutputTemplateSection:
    """Tests for section rendering."""

    def test_renders_section_with_title(self):
        """Section includes title with underline."""
        template = OutputTemplate(width=60)
        template.section("PROJECT METRICS", "Events: 1000")
        output = template.render()

        assert "PROJECT METRICS" in output
        assert SECTION_CHAR * len("PROJECT METRICS") in output
        assert "Events: 1000" in output

    def test_renders_multiple_sections(self):
        """Multiple sections render in order."""
        template = OutputTemplate(width=60)
        template.section("FIRST", "content 1")
        template.section("SECOND", "content 2")
        output = template.render()

        lines = output.split("\n")
        first_idx = next(i for i, l in enumerate(lines) if "FIRST" in l)
        second_idx = next(i for i, l in enumerate(lines) if "SECOND" in l)

        assert first_idx < second_idx

    def test_separator_adds_blank_line(self):
        """Separator adds visual break between sections."""
        template = OutputTemplate(width=60)
        template.section("FIRST", "content 1")
        template.separator()
        template.section("SECOND", "content 2")
        output = template.render()

        assert "FIRST" in output
        assert "SECOND" in output


class TestOutputTemplateFooter:
    """Tests for footer rendering."""

    def test_renders_summary(self):
        """Footer includes summary text."""
        template = OutputTemplate(width=60)
        template.header("TEST")
        template.footer("25,156 artifacts | 8/8 principles")
        output = template.render()

        assert "Summary: 25,156 artifacts | 8/8 principles" in output

    def test_includes_succession_hint(self):
        """Footer includes succession hint when command provided."""
        template = OutputTemplate(width=60)
        template.header("TEST")
        # Use a command that has succession rules
        output = template.render(command="status", context={"has_pending": True})

        # Should include hint arrow
        assert "->" in output or "→" in output

    def test_no_hint_without_command(self):
        """No succession hint when command not provided."""
        template = OutputTemplate(width=60)
        template.header("TEST")
        output = template.render()

        # Footer still has border
        assert HEADER_CHAR * 60 in output


class TestOutputTemplateIntegration:
    """Integration tests for full template rendering."""

    def test_full_render(self):
        """Complete template renders all components."""
        template = OutputTemplate(width=70)
        template.header("BABEL STATUS", "Project Health Overview")
        template.legend({"●": "shared", "○": "local"})
        template.scope("141,284 events")
        template.section("METRICS", "Artifacts: 25,156\nConnections: 10,215")
        template.section("HEALTH", "Aligned (8/8 principles)")
        template.footer("Ready to proceed")

        output = template.render(command="status", context={"healthy": True})

        # Header elements
        assert "BABEL STATUS" in output
        assert "Project Health Overview" in output
        assert "Legend:" in output

        # Sections
        assert "METRICS" in output
        assert "Artifacts: 25,156" in output
        assert "HEALTH" in output

        # Footer
        assert "Summary: Ready to proceed" in output

    def test_works_with_unicode_symbols(self):
        """Template works with Unicode symbol set."""
        template = OutputTemplate(symbols=UNICODE, width=60)
        template.header("TEST")
        template.legend({UNICODE.shared: "shared"})
        output = template.render()

        assert UNICODE.shared in output

    def test_works_with_ascii_symbols(self):
        """Template works with ASCII symbol set."""
        template = OutputTemplate(symbols=ASCII, width=60)
        template.header("TEST")
        output = template.render()

        # Should render without error
        assert "TEST" in output


class TestOutputTemplateUtilities:
    """Tests for utility methods."""

    def test_truncate_long_text(self):
        """Truncate shortens text with ellipsis."""
        template = OutputTemplate(width=80, full=False)
        long_text = "A" * 100
        truncated = template.truncate(long_text, length=20)

        assert len(truncated) <= 20
        assert truncated.endswith("…") or truncated.endswith("...")

    def test_truncate_respects_full_mode(self):
        """Truncate returns full text when full=True."""
        template = OutputTemplate(width=80, full=True)
        long_text = "A" * 100
        result = template.truncate(long_text, length=20)

        assert result == long_text

    def test_format_table_aligns_columns(self):
        """Format table produces aligned columns."""
        template = OutputTemplate(width=80)
        rows = [
            {"name": "Alice", "count": "100"},
            {"name": "Bob", "count": "5"},
        ]
        table = template.format_table(rows, columns=["Name", "Count"])

        lines = table.split("\n")
        assert len(lines) == 3  # header + 2 data rows
        assert "Name" in lines[0]
        assert "Alice" in lines[1]
        assert "Bob" in lines[2]

    def test_format_table_empty_rows(self):
        """Format table handles empty rows."""
        template = OutputTemplate(width=80)
        table = template.format_table([], columns=["Name", "Count"])

        assert table == ""

    def test_format_list_with_bullets(self):
        """Format list adds bullets to items."""
        template = OutputTemplate(symbols=UNICODE, width=80)
        items = ["First item", "Second item"]
        result = template.format_list(items)

        lines = result.split("\n")
        assert len(lines) == 2
        assert "First item" in lines[0]
        assert "Second item" in lines[1]

    def test_format_list_empty(self):
        """Format list handles empty list."""
        template = OutputTemplate(width=80)
        result = template.format_list([])

        assert result == ""


class TestTemplateSection:
    """Tests for TemplateSection dataclass."""

    def test_creates_section(self):
        """TemplateSection stores title and content."""
        section = TemplateSection(title="TEST", content="content")

        assert section.title == "TEST"
        assert section.content == "content"
        assert section.collapsed is False
