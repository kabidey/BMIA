"""
Performance Service - Track record metrics, equity curves, streaks.
"""
import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


async def get_track_record(db):
    """Compute comprehensive track record metrics."""
    try:
        all_signals = await db.signals.find({}).sort("created_at", 1).to_list(length=500)

        if not all_signals:
            return {
                "total_signals": 0,
                "open_signals": 0,
                "closed_signals": 0,
                "metrics": {},
                "equity_curve": [],
                "monthly_returns": [],
                "by_action": {},
                "by_sector": {},
                "by_timeframe": {},
                "by_confidence": {},
                "streaks": {},
            }

        open_signals = [s for s in all_signals if s.get("status") == "OPEN"]
        closed_signals = [s for s in all_signals if s.get("status") != "OPEN"]

        # Core metrics
        wins = [s for s in closed_signals if s.get("return_pct", 0) > 0]
        losses = [s for s in closed_signals if s.get("return_pct", 0) <= 0]
        returns = [s.get("return_pct", 0) for s in closed_signals]

        win_rate = round(len(wins) / max(len(closed_signals), 1) * 100, 1)
        avg_return = round(sum(returns) / max(len(returns), 1), 2)
        avg_win = round(sum(s.get("return_pct", 0) for s in wins) / max(len(wins), 1), 2)
        avg_loss = round(sum(s.get("return_pct", 0) for s in losses) / max(len(losses), 1), 2)
        max_win = max(returns) if returns else 0
        max_loss = min(returns) if returns else 0

        # Expectancy = (Win% * AvgWin) - (Loss% * |AvgLoss|)
        win_pct = len(wins) / max(len(closed_signals), 1)
        loss_pct = len(losses) / max(len(closed_signals), 1)
        expectancy = round(win_pct * avg_win - loss_pct * abs(avg_loss), 2)

        # Profit factor = gross wins / gross losses
        gross_wins = sum(s.get("return_pct", 0) for s in wins)
        gross_losses = abs(sum(s.get("return_pct", 0) for s in losses))
        profit_factor = round(gross_wins / max(gross_losses, 0.01), 2)

        # Streaks
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        streak = 0
        streak_type = None
        for s in closed_signals:
            ret = s.get("return_pct", 0)
            if ret > 0:
                if streak_type == "win":
                    streak += 1
                else:
                    streak = 1
                    streak_type = "win"
                max_win_streak = max(max_win_streak, streak)
            else:
                if streak_type == "loss":
                    streak += 1
                else:
                    streak = 1
                    streak_type = "loss"
                max_loss_streak = max(max_loss_streak, streak)
        current_streak = streak
        current_streak_type = streak_type or "none"

        # Equity curve (cumulative return)
        equity_curve = []
        cumulative = 0
        for s in closed_signals:
            ret = s.get("return_pct", 0)
            cumulative += ret
            created = s.get("created_at")
            date_str = created.isoformat() if isinstance(created, datetime) else str(created)
            equity_curve.append({
                "date": date_str,
                "return": ret,
                "cumulative": round(cumulative, 2),
                "symbol": s.get("symbol", ""),
                "action": s.get("action", ""),
            })

        # By action
        by_action = {}
        for action in ["BUY", "SELL", "HOLD", "AVOID"]:
            action_signals = [s for s in closed_signals if s.get("action") == action]
            if action_signals:
                action_returns = [s.get("return_pct", 0) for s in action_signals]
                action_wins = [r for r in action_returns if r > 0]
                by_action[action] = {
                    "count": len(action_signals),
                    "win_rate": round(len(action_wins) / len(action_signals) * 100, 1),
                    "avg_return": round(sum(action_returns) / len(action_returns), 2),
                }

        # By sector
        by_sector = defaultdict(lambda: {"count": 0, "wins": 0, "total_return": 0})
        from symbols import get_symbol_info
        for s in closed_signals:
            info = get_symbol_info(s.get("symbol", ""))
            sector = info.get("sector", "Unknown")
            by_sector[sector]["count"] += 1
            if s.get("return_pct", 0) > 0:
                by_sector[sector]["wins"] += 1
            by_sector[sector]["total_return"] += s.get("return_pct", 0)

        by_sector_clean = {}
        for sector, stats in by_sector.items():
            by_sector_clean[sector] = {
                "count": stats["count"],
                "win_rate": round(stats["wins"] / max(stats["count"], 1) * 100, 1),
                "avg_return": round(stats["total_return"] / max(stats["count"], 1), 2),
            }

        # By confidence band
        by_confidence = {}
        for band_name, lo, hi in [("Low (0-40)", 0, 40), ("Medium (40-70)", 40, 70), ("High (70-100)", 70, 101)]:
            band_signals = [s for s in closed_signals if lo <= s.get("confidence", 0) < hi]
            if band_signals:
                band_returns = [s.get("return_pct", 0) for s in band_signals]
                by_confidence[band_name] = {
                    "count": len(band_signals),
                    "win_rate": round(len([r for r in band_returns if r > 0]) / len(band_returns) * 100, 1),
                    "avg_return": round(sum(band_returns) / len(band_returns), 2),
                }

        return {
            "total_signals": len(all_signals),
            "open_signals": len(open_signals),
            "closed_signals": len(closed_signals),
            "metrics": {
                "win_rate": win_rate,
                "avg_return": avg_return,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "max_win": round(max_win, 2),
                "max_loss": round(max_loss, 2),
                "expectancy": expectancy,
                "profit_factor": profit_factor,
                "total_return": round(sum(returns), 2),
            },
            "streaks": {
                "current": current_streak,
                "current_type": current_streak_type,
                "max_win_streak": max_win_streak,
                "max_loss_streak": max_loss_streak,
            },
            "equity_curve": equity_curve,
            "by_action": dict(by_action),
            "by_sector": by_sector_clean,
            "by_confidence": by_confidence,
        }

    except Exception as e:
        logger.error(f"Track record error: {e}")
        return {"error": str(e), "total_signals": 0}
