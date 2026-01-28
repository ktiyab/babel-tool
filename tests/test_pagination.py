"""
Tests for Paginator — Coherence Evidence for reusable pagination utility

These tests validate:
- Paginator core properties (total, offset, limit, indices)
- items() returns correct slice
- Navigation helpers (has_more, has_previous, is_truncated)
- summary() generates correct output with hints
- header() generates correct title
- Edge cases (empty lists, offset beyond total)
- add_pagination_args() mixin
"""

import argparse

from babel.utils.pagination import (
    Paginator,
    add_pagination_args,
    paginate_from_args,
)


class TestPaginatorBasics:
    """Basic Paginator functionality."""

    def test_default_limit(self):
        """Default limit is 10."""
        items = list(range(50))
        paginator = Paginator(items)
        assert paginator.limit == 10

    def test_default_offset(self):
        """Default offset is 0."""
        items = list(range(50))
        paginator = Paginator(items)
        assert paginator.offset == 0

    def test_total_count(self):
        """Total returns correct count."""
        items = list(range(25))
        paginator = Paginator(items)
        assert paginator.total == 25

    def test_items_returns_correct_slice(self):
        """items() returns correct slice for first page."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.items() == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_items_with_offset(self):
        """items() respects offset."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=10)
        assert paginator.items() == [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

    def test_items_with_custom_limit(self):
        """items() respects custom limit."""
        items = list(range(50))
        paginator = Paginator(items, limit=5, offset=0)
        assert paginator.items() == [0, 1, 2, 3, 4]


class TestPaginatorIndices:
    """Index calculations for display."""

    def test_start_index_first_page(self):
        """Start index is 1 for first page (1-based display)."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.start_index == 1

    def test_start_index_second_page(self):
        """Start index is 11 for second page."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=10)
        assert paginator.start_index == 11

    def test_end_index_first_page(self):
        """End index is 10 for first page of 50 items."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.end_index == 10

    def test_end_index_last_page_partial(self):
        """End index caps at total for partial last page."""
        items = list(range(25))
        paginator = Paginator(items, limit=10, offset=20)
        assert paginator.end_index == 25

    def test_start_index_empty_list(self):
        """Start index is 0 for empty list."""
        paginator = Paginator([])
        assert paginator.start_index == 0

    def test_end_index_empty_list(self):
        """End index is 0 for empty list."""
        paginator = Paginator([])
        assert paginator.end_index == 0


class TestPaginatorNavigation:
    """Navigation helper methods."""

    def test_has_more_true(self):
        """has_more() True when more items exist."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.has_more() is True

    def test_has_more_false_last_page(self):
        """has_more() False on last page."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=40)
        assert paginator.has_more() is False

    def test_has_more_false_exact_fit(self):
        """has_more() False when items exactly fit limit."""
        items = list(range(10))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.has_more() is False

    def test_has_previous_false_first_page(self):
        """has_previous() False on first page."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.has_previous() is False

    def test_has_previous_true_second_page(self):
        """has_previous() True on second page."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=10)
        assert paginator.has_previous() is True

    def test_is_truncated_true(self):
        """is_truncated() True when total exceeds limit."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.is_truncated() is True

    def test_is_truncated_false(self):
        """is_truncated() False when total fits in limit."""
        items = list(range(5))
        paginator = Paginator(items, limit=10, offset=0)
        assert paginator.is_truncated() is False


class TestPaginatorSummary:
    """Summary generation."""

    def test_summary_basic(self):
        """Summary shows correct range."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        summary = paginator.summary()
        assert "Showing 1-10 of 50" in summary

    def test_summary_with_offset(self):
        """Summary shows correct range with offset."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=20)
        summary = paginator.summary()
        assert "Showing 21-30 of 50" in summary

    def test_summary_with_next_hint(self):
        """Summary includes next hint when more items exist."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        summary = paginator.summary(command_hint="babel list")
        assert "-> Next: babel list --offset 10" in summary

    def test_summary_no_next_hint_last_page(self):
        """Summary excludes next hint on last page."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=40)
        summary = paginator.summary(command_hint="babel list")
        assert "-> Next:" not in summary

    def test_summary_with_prev_hint(self):
        """Summary includes prev hint when on later page."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=20)
        summary = paginator.summary(command_hint="babel list")
        assert "-> Prev: babel list --offset 10" in summary

    def test_summary_empty_list(self):
        """Summary handles empty list."""
        paginator = Paginator([])
        summary = paginator.summary()
        assert "No items found" in summary


class TestPaginatorHeader:
    """Header generation."""

    def test_header_basic(self):
        """Header shows title with count."""
        items = list(range(5))
        paginator = Paginator(items, limit=10, offset=0)
        header = paginator.header("Decisions")
        assert header == "Decisions (5):"

    def test_header_truncated(self):
        """Header shows range when truncated."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=0)
        header = paginator.header("Decisions")
        assert header == "Decisions (1-10 of 50):"

    def test_header_truncated_with_offset(self):
        """Header shows correct range with offset."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=20)
        header = paginator.header("Decisions")
        assert header == "Decisions (21-30 of 50):"

    def test_header_empty_list(self):
        """Header handles empty list."""
        paginator = Paginator([])
        header = paginator.header("Decisions")
        assert header == "Decisions: none"


class TestPaginatorEdgeCases:
    """Edge cases and boundary conditions."""

    def test_negative_offset_becomes_zero(self):
        """Negative offset is clamped to 0."""
        items = list(range(50))
        paginator = Paginator(items, limit=10, offset=-5)
        assert paginator.offset == 0

    def test_zero_limit_becomes_one(self):
        """Zero limit is clamped to 1."""
        items = list(range(50))
        paginator = Paginator(items, limit=0, offset=0)
        assert paginator.limit == 1

    def test_offset_beyond_total(self):
        """Offset beyond total returns empty items."""
        items = list(range(10))
        paginator = Paginator(items, limit=10, offset=20)
        assert paginator.items() == []
        assert paginator.start_index == 10  # Caps at total

    def test_accepts_generator(self):
        """Paginator accepts generators (converts to list)."""
        def gen():
            for i in range(25):
                yield i
        paginator = Paginator(gen(), limit=10, offset=0)
        assert paginator.total == 25
        assert paginator.items() == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_should_warn_all_true(self):
        """should_warn_all() True when total exceeds threshold."""
        items = list(range(100))
        paginator = Paginator(items, warn_threshold=50)
        assert paginator.should_warn_all() is True

    def test_should_warn_all_false(self):
        """should_warn_all() False when total under threshold."""
        items = list(range(30))
        paginator = Paginator(items, warn_threshold=50)
        assert paginator.should_warn_all() is False


class TestAddPaginationArgs:
    """Tests for add_pagination_args() mixin."""

    def test_adds_limit_argument(self):
        """Adds --limit argument with default 10."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args([])
        assert args.limit == 10

    def test_adds_offset_argument(self):
        """Adds --offset argument with default 0."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args([])
        assert args.offset == 0

    def test_adds_all_argument(self):
        """Adds --all argument with default False."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args([])
        assert args.show_all is False

    def test_custom_default_limit(self):
        """Respects custom default limit."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser, default_limit=20)
        args = parser.parse_args([])
        assert args.limit == 20

    def test_parses_limit(self):
        """Parses --limit value."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args(['--limit', '25'])
        assert args.limit == 25

    def test_parses_offset(self):
        """Parses --offset value."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args(['--offset', '30'])
        assert args.offset == 30

    def test_parses_all_flag(self):
        """Parses --all flag."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args(['--all'])
        assert args.show_all is True

    def test_short_flags(self):
        """Short flags work (-l, -o, -a)."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args(['-l', '15', '-o', '5', '-a'])
        assert args.limit == 15
        assert args.offset == 5
        assert args.show_all is True


class TestPaginateFromArgs:
    """Tests for paginate_from_args() helper."""

    def test_creates_paginator_from_args(self):
        """Creates Paginator with args values."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args(['--limit', '15', '--offset', '10'])

        items = list(range(50))
        paginator = paginate_from_args(items, args)

        assert paginator.limit == 15
        assert paginator.offset == 10

    def test_show_all_overrides_limit(self):
        """--all flag shows all items regardless of limit."""
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args(['--limit', '5', '--all'])

        items = list(range(50))
        paginator = paginate_from_args(items, args)

        assert len(paginator.items()) == 50
        assert paginator.offset == 0
