"""
Regression test for the proceeds-double-booking bug in
`services.auto_reinvest.reinvest_proceeds`.

Pre-fix behaviour: the function read `cash_balance` (already credited with
proceeds by `_enforce_stops`) and ADDED `proceeds` again, then deducted the
`deployed` amount. That inflated cash, current_value and total_pnl by exactly
`proceeds` for every successful stop-out + reinvest pair.

Post-fix: only the `deployed` amount is deducted from the on-disk cash, since
the caller has already banked the proceeds.
"""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import auto_reinvest


class _FakeUpdateResult:
    def __init__(self): self.matched_count = 1


class _FakeCollection:
    """Minimal fake of `db.portfolios` supporting find_one / update_one."""

    def __init__(self, doc): self._doc = doc

    def find_one(self, q): return self._doc

    def update_one(self, q, update):
        self._doc.update(update.get("$set", {}))
        return _FakeUpdateResult()


class _FakeDB:
    def __init__(self, doc): self.portfolios = _FakeCollection(doc)


def test_reinvest_does_not_double_book_proceeds():
    """If `_enforce_stops` already banked ₹100k of proceeds into cash_balance,
    `reinvest_proceeds` should only subtract the deployed amount (₹95k),
    leaving cash at ₹5k — NOT add another ₹100k on top."""
    portfolio = {
        "type": "momentum",
        "initial_capital": 5_000_000,
        "cash_balance": 100_000.0,         # `_enforce_stops` already banked proceeds here
        "realized_pnl": -3_500.0,
        "holdings": [
            {"symbol": "TCS.NS", "entry_price": 4000.0, "quantity": 100,
             "current_price": 4050.0, "weight": 10},
        ],
    }
    db = _FakeDB(portfolio)

    fake_pick = {
        "symbol": "INFY.NS",
        "name": "Infosys",
        "sector": "IT",
        "current_price": 1900.0,
        "quantity": 50,                     # deployed = 95_000
        "deployed": 95_000.0,
        "score": 42.0,
        "ret_1m_pct": 1.0, "ret_3m_pct": 5.0, "ret_6m_pct": 8.0,
        "rsi": 55.0, "strategy_fit": "momentum", "market_cap": 5e12,
    }

    with patch("utils.market_hours.is_market_safe_sync",
               return_value=(True, "open")), \
         patch.object(auto_reinvest, "pick_replacement_stock",
                      return_value=fake_pick):
        result = auto_reinvest.reinvest_proceeds(
            db, "momentum",
            proceeds=100_000.0,
            source_exit={"symbol": "RELIANCE.NS", "weight": 10},
        )

    assert result is not None, "reinvest_proceeds should succeed in test path"
    # POST-FIX invariant: cash = old_cash - deployed = 100_000 - 95_000 = 5_000
    assert portfolio["cash_balance"] == pytest.approx(5_000.0), (
        f"cash_balance was {portfolio['cash_balance']:.2f} — proceeds got "
        f"double-booked (pre-fix bug)"
    )
    # Holdings has the new buy appended
    syms = [h["symbol"] for h in portfolio["holdings"]]
    assert "INFY.NS" in syms


def test_reinvest_handles_zero_existing_cash():
    """Sanity check: cash starts at proceeds (just banked) and ends at the
    truncation residue."""
    portfolio = {
        "type": "swing", "initial_capital": 5_000_000,
        "cash_balance": 50_000.0, "realized_pnl": 0,
        "holdings": [],
    }
    fake_pick = {
        "symbol": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Banks",
        "current_price": 1600.0, "quantity": 30, "deployed": 48_000.0,
        "score": 30.0, "ret_1m_pct": 0, "ret_3m_pct": 0, "ret_6m_pct": 0,
        "rsi": 55.0, "strategy_fit": "oversold", "market_cap": 1e13,
    }
    db = _FakeDB(portfolio)
    with patch("utils.market_hours.is_market_safe_sync",
               return_value=(True, "open")), \
         patch.object(auto_reinvest, "pick_replacement_stock",
                      return_value=fake_pick):
        auto_reinvest.reinvest_proceeds(
            db, "swing", proceeds=50_000.0,
            source_exit={"symbol": "X.NS", "weight": 10},
        )
    # 50k banked - 48k deployed = 2k truncation
    assert portfolio["cash_balance"] == pytest.approx(2_000.0)
