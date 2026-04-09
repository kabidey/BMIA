"""
Learning Service - Builds learning context from past signal outcomes.
Fed back into the intelligence engine to improve future signals.
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def build_learning_context(db):
    """Aggregate past signal outcomes into a learning context for the AI."""
    try:
        # Get all closed signals
        closed = await db.signals.find(
            {"status": {"$in": ["HIT_TARGET", "HIT_STOP", "EXPIRED", "INVALIDATED"]}}
        ).sort("closed_at", -1).to_list(length=200)

        if not closed:
            return {
                "total_signals": 0,
                "win_rate": None,
                "avg_return": None,
                "lessons": ["No historical signals yet. This is the first analysis."],
                "recent_mistakes": [],
                "patterns": {},
                "updated_at": datetime.now().isoformat(),
            }

        total = len(closed)
        wins = [s for s in closed if s.get("return_pct", 0) > 0]
        losses = [s for s in closed if s.get("return_pct", 0) <= 0]
        win_rate = round(len(wins) / total * 100, 1) if total > 0 else 0

        returns = [s.get("return_pct", 0) for s in closed]
        avg_return = round(sum(returns) / len(returns), 2) if returns else 0
        max_win = max(returns) if returns else 0
        max_loss = min(returns) if returns else 0

        # Analyze by action type
        buy_signals = [s for s in closed if s.get("action") == "BUY"]
        sell_signals = [s for s in closed if s.get("action") == "SELL"]
        buy_win_rate = round(len([s for s in buy_signals if s.get("return_pct", 0) > 0]) / max(len(buy_signals), 1) * 100, 1)
        sell_win_rate = round(len([s for s in sell_signals if s.get("return_pct", 0) > 0]) / max(len(sell_signals), 1) * 100, 1)

        # Analyze by timeframe
        timeframe_stats = {}
        for tf in ["INTRADAY", "SWING", "POSITIONAL"]:
            tf_signals = [s for s in closed if s.get("timeframe") == tf]
            if tf_signals:
                tf_returns = [s.get("return_pct", 0) for s in tf_signals]
                timeframe_stats[tf] = {
                    "count": len(tf_signals),
                    "win_rate": round(len([r for r in tf_returns if r > 0]) / len(tf_returns) * 100, 1),
                    "avg_return": round(sum(tf_returns) / len(tf_returns), 2),
                }

        # Analyze by sector
        sector_stats = {}
        for s in closed:
            sector = "Unknown"
            # Try to extract sector from symbol info
            from symbols import get_symbol_info
            info = get_symbol_info(s.get("symbol", ""))
            sector = info.get("sector", "Unknown")
            if sector not in sector_stats:
                sector_stats[sector] = {"wins": 0, "losses": 0, "total_return": 0}
            if s.get("return_pct", 0) > 0:
                sector_stats[sector]["wins"] += 1
            else:
                sector_stats[sector]["losses"] += 1
            sector_stats[sector]["total_return"] += s.get("return_pct", 0)

        # Generate lessons
        lessons = []

        if win_rate < 50:
            lessons.append(f"Overall win rate is low ({win_rate}%). Be more selective with entries and require stronger confirmation signals.")
        elif win_rate > 70:
            lessons.append(f"Win rate is strong ({win_rate}%). Current approach is working well - maintain discipline.")

        if buy_win_rate < sell_win_rate and buy_signals:
            lessons.append(f"BUY signals ({buy_win_rate}% win rate) underperform SELL signals ({sell_win_rate}%). Consider tighter entry criteria for BUY signals.")

        if avg_return < 0:
            lessons.append(f"Average return is negative ({avg_return}%). Focus on improving risk/reward by setting tighter stop losses and realistic targets.")

        # Check for common failure patterns
        recent_losses = sorted(losses, key=lambda x: x.get("closed_at", datetime.min), reverse=True)[:10]
        for loss in recent_losses[:3]:
            symbol = loss.get("symbol", "?")
            ret = loss.get("return_pct", 0)
            action = loss.get("action", "?")
            notes = loss.get("evaluation_notes", "")
            lessons.append(f"Recent loss on {symbol} ({action}): {ret}% - {notes}")

        # Best performing patterns
        recent_wins = sorted(wins, key=lambda x: x.get("return_pct", 0), reverse=True)[:3]
        for win in recent_wins:
            symbol = win.get("symbol", "?")
            ret = win.get("return_pct", 0)
            action = win.get("action", "?")
            lessons.append(f"Successful {action} on {symbol}: +{ret}% - pattern to replicate.")

        # Confidence calibration
        high_conf_signals = [s for s in closed if s.get("confidence", 0) >= 70]
        low_conf_signals = [s for s in closed if s.get("confidence", 0) < 50]
        if high_conf_signals:
            high_conf_wr = round(len([s for s in high_conf_signals if s.get("return_pct", 0) > 0]) / len(high_conf_signals) * 100, 1)
            if high_conf_wr < 60:
                lessons.append(f"High-confidence signals ({high_conf_wr}% win rate) are overconfident. Calibrate confidence levels down.")

        # Recent mistakes
        recent_mistakes = []
        for loss in recent_losses[:5]:
            mistake = f"{loss.get('symbol', '?')} {loss.get('action', '?')}: Lost {loss.get('return_pct', 0)}%. "
            if loss.get("evaluation_notes"):
                mistake += loss["evaluation_notes"]
            recent_mistakes.append(mistake)

        context = {
            "total_signals": total,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "max_win": max_win,
            "max_loss": max_loss,
            "buy_win_rate": buy_win_rate,
            "sell_win_rate": sell_win_rate,
            "timeframe_stats": timeframe_stats,
            "sector_stats": {k: v for k, v in list(sector_stats.items())[:10]},
            "lessons": lessons[:10],
            "recent_mistakes": recent_mistakes[:5],
            "updated_at": datetime.now().isoformat(),
        }

        # Store in DB
        await db.learning_context.replace_one(
            {"type": "global"},
            {"type": "global", **context},
            upsert=True
        )

        return context

    except Exception as e:
        logger.error(f"Learning context error: {e}")
        return {
            "total_signals": 0,
            "lessons": [f"Error building context: {str(e)}"],
            "recent_mistakes": [],
            "updated_at": datetime.now().isoformat(),
        }


async def get_cached_learning_context(db):
    """Get the cached learning context, or build fresh if stale."""
    try:
        cached = await db.learning_context.find_one({"type": "global"})
        if cached:
            cached.pop("_id", None)
            return cached
    except Exception:
        pass
    return await build_learning_context(db)
