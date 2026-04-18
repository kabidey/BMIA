"""Unit tests for market-hours guard."""
import sys
import os
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.market_hours import _check  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")


def make(y, m, d, h, mi):
    return datetime(y, m, d, h, mi, tzinfo=IST)


def test_weekend_blocked():
    # Saturday
    ok, r = _check(make(2026, 4, 18, 11, 0), set())
    assert not ok and "Saturday" in r, r
    # Sunday
    ok, r = _check(make(2026, 4, 19, 11, 0), set())
    assert not ok and "Sunday" in r, r


def test_holiday_blocked():
    holidays = {"2026-08-15"}  # Independence Day
    ok, r = _check(make(2026, 8, 15, 11, 0), holidays)  # actually Saturday, still blocked
    assert not ok


def test_before_open():
    # 08:00 IST on a weekday
    ok, r = _check(make(2026, 4, 16, 8, 0), set())  # Thursday
    assert not ok and "opens at 09:15" in r, r


def test_open_auction_window_blocked():
    # 09:20 IST — within 09:15-09:30 auction window
    ok, r = _check(make(2026, 4, 16, 9, 20), set())  # Thursday
    assert not ok and "open auction" in r, r


def test_exactly_at_safe_open_allowed():
    # 09:30 IST on a regular weekday
    ok, r = _check(make(2026, 4, 16, 9, 30), set())  # Thursday
    assert ok, r


def test_midday_allowed():
    ok, r = _check(make(2026, 4, 16, 12, 30), set())  # Thursday
    assert ok, r


def test_close_auction_blocked():
    # 15:20 IST — within 15:15-15:30 close auction
    ok, r = _check(make(2026, 4, 16, 15, 20), set())  # Thursday
    assert not ok and "close auction" in r, r


def test_after_close():
    # 16:00 IST
    ok, r = _check(make(2026, 4, 16, 16, 0), set())  # Thursday
    assert not ok and "Market closed at 15:30" in r, r


def test_just_before_safe_close_allowed():
    # 15:14 IST — last safe minute
    ok, r = _check(make(2026, 4, 16, 15, 14), set())  # Thursday
    assert ok, r


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
    print("\n✅ All market-hours tests passed")
