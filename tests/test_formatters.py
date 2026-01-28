"""
Tests for presentation formatters — P12 Temporal Attribution

Tests format_timestamp() and format_age_indicator() which enforce
P12: Time is always shown, no parameters, no flags.
"""

from datetime import datetime, timezone, timedelta

from babel.presentation.formatters import format_timestamp, format_age_indicator


class TestFormatTimestamp:
    """Tests for format_timestamp() — P12: time always shown."""

    def test_just_now_for_very_recent(self):
        """Very recent timestamps show 'just now'."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(seconds=30)
        result = format_timestamp(ts.isoformat())
        assert result == "just now"

    def test_minutes_ago_format(self):
        """Timestamps within an hour show minutes ago."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(minutes=15)
        result = format_timestamp(ts.isoformat())
        assert result == "15m ago"

    def test_hours_ago_format(self):
        """Timestamps within a day show hours ago."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(hours=5)
        result = format_timestamp(ts.isoformat())
        assert result == "5h ago"

    def test_days_ago_format(self):
        """Timestamps within a week show days ago."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=3)
        result = format_timestamp(ts.isoformat())
        assert result == "3d ago"

    def test_absolute_date_for_old_timestamps(self):
        """Timestamps older than 7 days show absolute date (e.g., 'Jan 15')."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=10)
        result = format_timestamp(ts.isoformat())
        # Should be "Mon DD" format
        expected = ts.strftime("%b %d")
        assert result == expected

    def test_seven_day_threshold(self):
        """Exactly 7 days uses absolute format (P12 threshold)."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=7)
        result = format_timestamp(ts.isoformat())
        # At exactly 7 days, should be absolute
        expected = ts.strftime("%b %d")
        assert result == expected

    def test_six_days_uses_relative(self):
        """6 days still uses relative format."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=6)
        result = format_timestamp(ts.isoformat())
        assert result == "6d ago"

    def test_empty_string_returns_unknown(self):
        """Empty input returns 'unknown'."""
        assert format_timestamp("") == "unknown"

    def test_none_returns_unknown(self):
        """None input returns 'unknown'."""
        assert format_timestamp(None) == "unknown"

    def test_invalid_string_returns_unknown(self):
        """Invalid timestamp string returns 'unknown'."""
        assert format_timestamp("not-a-date") == "unknown"
        assert format_timestamp("2026/01/15") == "unknown"  # Wrong format

    def test_future_timestamp_returns_just_now(self):
        """Future timestamps (clock skew) return 'just now'."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        result = format_timestamp(future.isoformat())
        assert result == "just now"

    def test_handles_z_suffix(self):
        """Handles Z suffix (common in JSON)."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(minutes=30)
        iso_with_z = ts.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        result = format_timestamp(iso_with_z)
        assert result == "30m ago"

    def test_handles_naive_timestamp(self):
        """Handles naive timestamps (assumes UTC)."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(hours=2)
        # Create naive timestamp (no timezone info)
        naive_iso = ts.strftime("%Y-%m-%dT%H:%M:%S")
        result = format_timestamp(naive_iso)
        assert result == "2h ago"


class TestFormatAgeIndicator:
    """Tests for format_age_indicator() — semantic age categories."""

    def test_recent_for_under_one_hour(self):
        """Timestamps under 1 hour are 'recent'."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(minutes=30)
        result = format_age_indicator(ts.isoformat())
        assert result == "recent"

    def test_today_for_same_day(self):
        """Timestamps 1-24 hours ago are 'today'."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(hours=5)
        result = format_age_indicator(ts.isoformat())
        assert result == "today"

    def test_this_week_for_under_seven_days(self):
        """Timestamps 1-7 days ago are 'this_week'."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=3)
        result = format_age_indicator(ts.isoformat())
        assert result == "this_week"

    def test_older_for_over_seven_days(self):
        """Timestamps over 7 days are 'older'."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=10)
        result = format_age_indicator(ts.isoformat())
        assert result == "older"

    def test_empty_returns_unknown(self):
        """Empty input returns 'unknown'."""
        assert format_age_indicator("") == "unknown"

    def test_invalid_returns_unknown(self):
        """Invalid input returns 'unknown'."""
        assert format_age_indicator("not-a-date") == "unknown"

    def test_future_returns_recent(self):
        """Future timestamps return 'recent'."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        result = format_age_indicator(future.isoformat())
        assert result == "recent"


class TestFormatTimestampEdgeCases:
    """Edge case tests for robustness."""

    def test_exactly_one_hour_threshold(self):
        """Test exactly 1 hour boundary."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(hours=1)
        result = format_timestamp(ts.isoformat())
        assert result == "1h ago"

    def test_exactly_one_day_threshold(self):
        """Test exactly 1 day boundary."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=1)
        result = format_timestamp(ts.isoformat())
        assert result == "1d ago"

    def test_very_old_timestamp(self):
        """Test very old timestamps (months/years)."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(days=365)
        result = format_timestamp(ts.isoformat())
        # Should still be absolute date format
        expected = ts.strftime("%b %d")
        assert result == expected

    def test_microseconds_ignored(self):
        """Microseconds in timestamp are handled correctly."""
        now = datetime.now(timezone.utc)
        ts = now - timedelta(minutes=5, microseconds=123456)
        result = format_timestamp(ts.isoformat())
        assert result == "5m ago"
