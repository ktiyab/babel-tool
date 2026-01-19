"""
Paginator — Reusable pagination for list-producing commands

Design principles:
- P6: Token efficiency (default limit prevents dumps)
- HC2: Human authority (user controls via flags)
- HC3: Offline-first (stateless offset, no session)
- HC6: No jargon (simple "Showing X-Y of Z" format)

Usage:
    items = get_all_items()
    paginator = Paginator(items, limit=10, offset=0)

    for item in paginator.items():
        print(format_item(item))

    print(paginator.summary(command_hint="babel list decisions"))
"""

from typing import List, Any, Optional, Iterable
import argparse


# Default pagination settings
DEFAULT_LIMIT = 10
WARN_THRESHOLD = 50  # Warn when --all would show more than this


class Paginator:
    """
    Stateless pagination utility for list output.

    Handles offset-based pagination with consistent summary generation.
    Works for both AI (token efficiency) and human (cognitive load) consumers.
    """

    def __init__(
        self,
        items: Iterable[Any],
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        warn_threshold: int = WARN_THRESHOLD
    ):
        """
        Initialize paginator with items and pagination parameters.

        Args:
            items: Iterable of items to paginate
            limit: Maximum items per page (default 10)
            offset: Number of items to skip (default 0)
            warn_threshold: Warn if total exceeds this when using --all
        """
        self._all_items = list(items)
        self._limit = max(1, limit)  # Minimum 1 item
        self._offset = max(0, offset)  # No negative offset
        self._warn_threshold = warn_threshold

    @property
    def total(self) -> int:
        """Total number of items."""
        return len(self._all_items)

    @property
    def offset(self) -> int:
        """Current offset."""
        return self._offset

    @property
    def limit(self) -> int:
        """Current limit."""
        return self._limit

    @property
    def start_index(self) -> int:
        """1-based start index for display (e.g., "Showing 1-10")."""
        if self.total == 0:
            return 0
        return min(self._offset + 1, self.total)

    @property
    def end_index(self) -> int:
        """1-based end index for display (e.g., "Showing 1-10")."""
        return min(self._offset + self._limit, self.total)

    def items(self) -> List[Any]:
        """Get items for current page."""
        return self._all_items[self._offset:self._offset + self._limit]

    def has_more(self) -> bool:
        """Check if there are more items after current page."""
        return self._offset + self._limit < self.total

    def has_previous(self) -> bool:
        """Check if there are items before current page."""
        return self._offset > 0

    def is_truncated(self) -> bool:
        """Check if output is truncated (not showing all items)."""
        return self.total > self._limit

    def should_warn_all(self) -> bool:
        """Check if --all should show a warning (large dataset)."""
        return self.total > self._warn_threshold

    def summary(self, command_hint: Optional[str] = None) -> str:
        """
        Generate summary line with optional navigation hints.

        Args:
            command_hint: Base command for hint (e.g., "babel list decisions")

        Returns:
            Summary string like "Showing 1-10 of 85\n-> Next: babel list --offset 10"
        """
        if self.total == 0:
            return "No items found."

        lines = []

        # Main summary line
        lines.append(f"Showing {self.start_index}-{self.end_index} of {self.total}")

        # Navigation hints
        if command_hint and self.has_more():
            next_offset = self._offset + self._limit
            lines.append(f"-> Next: {command_hint} --offset {next_offset}")

        if command_hint and self.has_previous():
            prev_offset = max(0, self._offset - self._limit)
            lines.append(f"-> Prev: {command_hint} --offset {prev_offset}")

        return "\n".join(lines)

    def header(self, title: str) -> str:
        """
        Generate header with count info.

        Args:
            title: Base title (e.g., "Decisions")

        Returns:
            Header string like "Decisions (showing 1-10 of 85):"
        """
        if self.total == 0:
            return f"{title}: none"

        if not self.is_truncated():
            return f"{title} ({self.total}):"

        return f"{title} ({self.start_index}-{self.end_index} of {self.total}):"


def add_pagination_args(parser: argparse.ArgumentParser, default_limit: int = DEFAULT_LIMIT):
    """
    Add standard pagination arguments to an argument parser.

    Provides consistent --limit, --offset, --all flags across commands.

    Args:
        parser: ArgumentParser to add arguments to
        default_limit: Default limit value (default 10)

    Usage:
        parser = argparse.ArgumentParser()
        add_pagination_args(parser)
        args = parser.parse_args()

        paginator = Paginator(items, limit=args.limit, offset=args.offset)
        if args.all:
            paginator = Paginator(items, limit=len(items), offset=0)
    """
    group = parser.add_argument_group('pagination')

    group.add_argument(
        '--limit', '-l',
        type=int,
        default=default_limit,
        metavar='N',
        help=f'Maximum items to show (default: {default_limit})'
    )

    group.add_argument(
        '--offset', '-o',
        type=int,
        default=0,
        metavar='N',
        help='Skip first N items (default: 0)'
    )

    group.add_argument(
        '--all', '-a',
        action='store_true',
        dest='show_all',
        help='Show all items (ignores --limit, warns if >50)'
    )


def paginate_from_args(items: Iterable[Any], args) -> 'Paginator':
    """
    Create Paginator from parsed arguments.

    Convenience function that handles --all flag logic.

    Args:
        items: Items to paginate
        args: Parsed arguments (must have limit, offset, show_all attributes)

    Returns:
        Configured Paginator instance
    """
    items_list = list(items)

    if getattr(args, 'show_all', False):
        return Paginator(items_list, limit=len(items_list) or 1, offset=0)

    return Paginator(
        items_list,
        limit=getattr(args, 'limit', DEFAULT_LIMIT),
        offset=getattr(args, 'offset', 0)
    )
