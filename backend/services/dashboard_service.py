"""
Dashboard Service — Market Intelligence Cockpit Data Layer
Provides all data for the 4-section cockpit dashboard:
  1. Macro View: Indices, VIX, FII/DII, Breadth
  2. Micro View: Sector Treemap, Volume Shockers, 52W Clusters
  3. Derivatives & Sentiment: PCR, OI Quadrant
  4. Corporate Actions & News: Block Deals, Earnings/Actions

Uses nselib + yfinance with background pre-fetch cache for instant responses.
"""
import logging
import time
import threading
import traceback
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)

# ── In-memory TTL Cache ──────────────────────────────────────────────────────
_cache = {}
CACHE_TTL = 60  # seconds


def _cached(key, ttl=CACHE_TTL):
    """Decorator-free TTL cache check."""
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < ttl:
        return entry["data"]
    return None


def _set_cache(key, data, ttl=CACHE_TTL):
    _cache[key] = {"data": data, "ts": time.time()}


# ── Background Pre-fetch Cache ───────────────────────────────────────────────
_prefetch_cache = {
    "cockpit": None,
    "cockpit_slow": None,
    "cockpit_ts": 0,
    "cockpit_slow_ts": 0,
    "ready": False,
}
_prefetch_lock = threading.Lock()


def get_cached_cockpit():
    """Return pre-fetched cockpit data instantly."""
    with _prefetch_lock:
        return _prefetch_cache.get("cockpit")


def get_cached_cockpit_slow():
    """Return pre-fetched slow cockpit data instantly."""
    with _prefetch_lock:
        return _prefetch_cache.get("cockpit_slow")


def _background_refresh_loop():
    """Daemon thread: refreshes cockpit data every 30s, slow modules every 120s."""
    logger.info("COCKPIT CACHE: Background refresh thread started")
    # Initial quiet period — don't compete for CPU/GIL during app startup on
    # resource-constrained deploy pods (helps the health probe pass fast).
    time.sleep(30)
    cycle = 0
    while True:
        try:
            # Always refresh main cockpit (fast modules)
            t0 = time.time()
            data = get_full_cockpit()
            elapsed = round(time.time() - t0, 1)
            with _prefetch_lock:
                _prefetch_cache["cockpit"] = data
                _prefetch_cache["cockpit_ts"] = time.time()
                _prefetch_cache["ready"] = True
            logger.info(f"COCKPIT CACHE: Main cockpit refreshed in {elapsed}s")

            # Refresh slow modules every 4th cycle (~120s)
            if cycle % 4 == 0:
                t0 = time.time()
                slow = get_slow_cockpit_modules()
                elapsed = round(time.time() - t0, 1)
                with _prefetch_lock:
                    _prefetch_cache["cockpit_slow"] = slow
                    _prefetch_cache["cockpit_slow_ts"] = time.time()
                logger.info(f"COCKPIT CACHE: Slow modules refreshed in {elapsed}s")
        except Exception as e:
            logger.error(f"COCKPIT CACHE: Refresh error: {e}")

        cycle += 1
        time.sleep(30)


def start_background_cache():
    """Start the background pre-fetch thread (call once on app startup)."""
    t = threading.Thread(target=_background_refresh_loop, daemon=True)
    t.start()
    logger.info("COCKPIT CACHE: Background thread launched")


def _safe_float(val, default=None):
    """Convert to float safely, handling numpy and pandas types."""
    if val is None:
        return default
    try:
        import numpy as np
        if isinstance(val, (np.integer,)):
            return int(val)
        if isinstance(val, (np.floating,)):
            v = float(val)
            return v if not np.isnan(v) else default
        if isinstance(val, (np.bool_,)):
            return bool(val)
        return float(val)
    except (TypeError, ValueError):
        try:
            # Handle strings like "1,234.56"
            cleaned = str(val).replace(",", "").replace(" ", "").replace("%", "").strip()
            if cleaned in ("-", "", "nan", "None", "NaN"):
                return default
            return float(cleaned)
        except (ValueError, TypeError):
            return default


def _safe_int(val, default=0):
    f = _safe_float(val, None)
    return int(f) if f is not None else default


# ── 1. MACRO VIEW ────────────────────────────────────────────────────────────

def get_indices_snapshot():
    """Get major indices with streaming data using nselib."""
    cached = _cached("indices_snapshot")
    if cached:
        return cached

    try:
        from nselib import capital_market
        df = capital_market.market_watch_all_indices()

        target_indices = {
            "NIFTY 50": "Nifty 50",
            "NIFTY BANK": "Bank Nifty",
            "NIFTY MIDCAP 100": "Midcap 100",
            "NIFTY SMALLCAP 100": "Smallcap 100",
            "NIFTY NEXT 50": "Nifty Next 50",
            "NIFTY IT": "Nifty IT",
            "NIFTY PHARMA": "Nifty Pharma",
            "NIFTY AUTO": "Nifty Auto",
            "NIFTY FIN SERVICE": "Fin Services",
            "NIFTY METAL": "Nifty Metal",
            "NIFTY ENERGY": "Nifty Energy",
            "NIFTY REALTY": "Nifty Realty",
            "NIFTY PSU BANK": "PSU Banks",
            "NIFTY MEDIA": "Nifty Media",
            "NIFTY FMCG": "FMCG",
            "NIFTY CONSUMPTION": "Consumption",
            "NIFTY INFRA": "Infrastructure",
            "NIFTY COMMODITIES": "Commodities",
            "NIFTY HEALTHCARE INDEX": "Healthcare",
            "NIFTY OIL AND GAS": "Oil & Gas",
            "NIFTY PRIVATE BANK": "Private Banks",
        }

        indices = []
        for _, row in df.iterrows():
            idx_name = str(row.get("index", "")).strip().upper()
            if idx_name in target_indices:
                indices.append({
                    "name": target_indices[idx_name],
                    "symbol": idx_name,
                    "last": _safe_float(row.get("last")),
                    "change": _safe_float(row.get("variation")),
                    "change_pct": _safe_float(row.get("percentChange")),
                    "open": _safe_float(row.get("open")),
                    "high": _safe_float(row.get("high")),
                    "low": _safe_float(row.get("low")),
                    "prev_close": _safe_float(row.get("previousClose")),
                    "year_high": _safe_float(row.get("yearHigh")),
                    "year_low": _safe_float(row.get("yearLow")),
                    "advances": _safe_int(row.get("advances")),
                    "declines": _safe_int(row.get("declines")),
                    "unchanged": _safe_int(row.get("unchanged")),
                })

        # Sort: primary indices first
        priority = ["Nifty 50", "Sensex", "Bank Nifty", "Midcap 100", "Smallcap 100"]
        indices.sort(key=lambda x: priority.index(x["name"]) if x["name"] in priority else 99)

        # Add BSE Sensex from yfinance (not available from nselib)
        try:
            sensex = yf.Ticker("^BSESN")
            hist = sensex.history(period="2d")
            if hist is not None and len(hist) >= 1:
                close = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else close
                change = round(close - prev, 2)
                change_pct = round((change / prev) * 100, 2) if prev else 0
                indices.insert(1, {
                    "name": "Sensex",
                    "symbol": "BSE SENSEX",
                    "last": round(close, 2),
                    "change": change,
                    "change_pct": change_pct,
                    "open": float(hist["Open"].iloc[-1]),
                    "high": float(hist["High"].iloc[-1]),
                    "low": float(hist["Low"].iloc[-1]),
                    "prev_close": round(prev, 2),
                    "year_high": None,
                    "year_low": None,
                    "advances": 0,
                    "declines": 0,
                    "unchanged": 0,
                })
        except Exception as e:
            logger.warning(f"Sensex yfinance fallback error: {e}")

        result = {"indices": indices, "updated_at": datetime.now(timezone.utc).isoformat()}
        _set_cache("indices_snapshot", result)
        return result
    except Exception as e:
        logger.error(f"Indices snapshot error: {e}")
        return {"indices": [], "error": str(e)}


def get_market_breadth():
    """Get advance/decline data from Nifty 50 index row."""
    cached = _cached("market_breadth")
    if cached:
        return cached

    try:
        from nselib import capital_market
        df = capital_market.market_watch_all_indices()

        # Get Nifty 500 or broadest index for breadth
        breadth = {}
        for _, row in df.iterrows():
            idx = str(row.get("index", "")).strip().upper()
            if idx in ("NIFTY 500", "NIFTY 50"):
                adv = _safe_int(row.get("advances"))
                dec = _safe_int(row.get("declines"))
                unch = _safe_int(row.get("unchanged"))
                total = adv + dec + unch
                breadth[idx] = {
                    "advances": adv,
                    "declines": dec,
                    "unchanged": unch,
                    "total": total,
                    "ad_ratio": round(adv / max(dec, 1), 2),
                    "advance_pct": round(adv / max(total, 1) * 100, 1),
                    "decline_pct": round(dec / max(total, 1) * 100, 1),
                }

        # Prefer Nifty 500 for broad breadth
        result = breadth.get("NIFTY 500", breadth.get("NIFTY 50", {}))
        result["updated_at"] = datetime.now(timezone.utc).isoformat()
        _set_cache("market_breadth", result)
        return result
    except Exception as e:
        logger.error(f"Market breadth error: {e}")
        return {"advances": 0, "declines": 0, "unchanged": 0, "error": str(e)}


def get_vix_regime():
    """Get India VIX data for gauge display."""
    cached = _cached("vix_regime")
    if cached:
        return cached

    try:
        from nselib import capital_market
        vix_df = capital_market.india_vix_data(period="1M")

        if vix_df is not None and len(vix_df) > 0:
            latest = vix_df.iloc[-1]
            current = _safe_float(latest.get("CLOSE_INDEX_VAL"))
            if current is None:
                current = _safe_float(latest.get("CURRENT"))
            if current is None:
                current = _safe_float(latest.get("EOD_CLOSE_INDEX_VAL"))

            # Determine regime
            if current and current < 13:
                regime = "calm"
                regime_label = "Calm"
            elif current and current < 18:
                regime = "watch"
                regime_label = "Elevated"
            elif current and current < 25:
                regime = "risk"
                regime_label = "High Risk"
            else:
                regime = "extreme"
                regime_label = "Extreme Fear"

            # Build history
            history = []
            for _, r in vix_df.iterrows():
                val = _safe_float(r.get("CLOSE_INDEX_VAL")) or _safe_float(r.get("EOD_CLOSE_INDEX_VAL"))
                ts = str(r.get("TIMESTAMP", ""))
                if val:
                    history.append({"date": ts, "value": val})

            result = {
                "current": current,
                "change": _safe_float(latest.get("VIX_PTS_CHG")) or _safe_float(latest.get("CHG")),
                "change_pct": _safe_float(latest.get("VIX_PERC_CHG")) or _safe_float(latest.get("PER_CHG")),
                "high": _safe_float(latest.get("HIGH_INDEX_VAL")) or _safe_float(latest.get("EOD_HIGH_INDEX_VAL")),
                "low": _safe_float(latest.get("LOW_INDEX_VAL")) or _safe_float(latest.get("EOD_LOW_INDEX_VAL")),
                "prev_close": _safe_float(latest.get("PREV_CLOSE")),
                "regime": regime,
                "regime_label": regime_label,
                "history": history[-20:],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            _set_cache("vix_regime", result)
            return result
    except Exception as e:
        logger.error(f"VIX regime error: {e}")

    return {"current": None, "regime": "unknown", "error": "VIX data unavailable"}


def get_fii_dii_flows():
    """Get FII/DII daily flows from derivatives statistics."""
    cached = _cached("fii_dii_flows")
    if cached:
        return cached

    try:
        from nselib import derivatives

        flows = []
        # Try last 10 trading days
        for days_back in range(0, 15):
            d = date.today() - timedelta(days=days_back)
            trade_date = d.strftime("%d-%m-%Y")
            try:
                df = derivatives.fii_derivatives_statistics(trade_date)
                if df is not None and len(df) > 0:
                    # Sum up total buy/sell values
                    total_buy = df["buy_value_in_Cr"].sum()
                    total_sell = df["sell_value_in_Cr"].sum()
                    net = _safe_float(total_buy) - _safe_float(total_sell)
                    flows.append({
                        "date": d.strftime("%Y-%m-%d"),
                        "display_date": d.strftime("%d %b"),
                        "fii_buy": _safe_float(total_buy),
                        "fii_sell": _safe_float(total_sell),
                        "fii_net": round(net, 2) if net else 0,
                    })
                    if len(flows) >= 10:
                        break
            except Exception:
                continue

        # Try to get DII data from participant wise OI
        try:
            yesterday = date.today() - timedelta(days=1)
            for days_back in range(0, 5):
                d = yesterday - timedelta(days=days_back)
                trade_date = d.strftime("%d-%m-%Y")
                try:
                    oi_df = derivatives.participant_wise_open_interest(trade_date)
                    if oi_df is not None and len(oi_df) > 0:
                        for _, row in oi_df.iterrows():
                            ct = str(row.get("Client Type", "")).strip()
                            if ct == "DII":
                                dii_long = _safe_float(row.get("Total Long Contracts      ")) or 0
                                dii_short = _safe_float(row.get("Total Short Contracts")) or 0
                                for f in flows:
                                    f["dii_long"] = dii_long
                                    f["dii_short"] = dii_short
                                    f["dii_net"] = dii_long - dii_short
                            elif ct == "FII":
                                fii_long = _safe_float(row.get("Total Long Contracts      ")) or 0
                                fii_short = _safe_float(row.get("Total Short Contracts")) or 0
                                for f in flows:
                                    f["fii_long_contracts"] = fii_long
                                    f["fii_short_contracts"] = fii_short
                        break
                except Exception:
                    continue
        except Exception:
            pass

        flows.reverse()
        result = {"flows": flows, "updated_at": datetime.now(timezone.utc).isoformat()}
        _set_cache("fii_dii_flows", result)
        return result
    except Exception as e:
        logger.error(f"FII/DII flows error: {e}")
        return {"flows": [], "error": str(e)}


# ── 2. MICRO VIEW ────────────────────────────────────────────────────────────

def get_sector_rotation():
    """Get sector performance data for treemap visualization."""
    cached = _cached("sector_rotation")
    if cached:
        return cached

    try:
        from nselib import capital_market
        df = capital_market.market_watch_all_indices()

        sector_indices = {
            "NIFTY IT": "IT",
            "NIFTY BANK": "Banking",
            "NIFTY PHARMA": "Pharma",
            "NIFTY AUTO": "Auto",
            "NIFTY FIN SERVICE": "Financial Services",
            "NIFTY METAL": "Metals",
            "NIFTY ENERGY": "Energy",
            "NIFTY REALTY": "Realty",
            "NIFTY PSU BANK": "PSU Banks",
            "NIFTY MEDIA": "Media",
            "NIFTY FMCG": "FMCG",
            "NIFTY CONSUMPTION": "Consumption",
            "NIFTY INFRA": "Infrastructure",
            "NIFTY COMMODITIES": "Commodities",
            "NIFTY MNC": "MNCs",
            "NIFTY HEALTHCARE INDEX": "Healthcare",
            "NIFTY OIL AND GAS": "Oil & Gas",
            "NIFTY PRIVATE BANK": "Private Banks",
        }

        # Approximate market cap weights for treemap sizing
        sector_weights = {
            "Banking": 25, "IT": 14, "Financial Services": 12, "Energy": 10,
            "FMCG": 8, "Auto": 7, "Pharma": 6, "Metals": 5, "Oil & Gas": 5,
            "Infrastructure": 4, "PSU Banks": 4, "Realty": 3, "Private Banks": 8,
            "Healthcare": 4, "Media": 2, "Consumption": 3, "MNCs": 3, "Commodities": 3,
        }

        sectors = []
        for _, row in df.iterrows():
            idx = str(row.get("index", "")).strip().upper()
            if idx in sector_indices:
                name = sector_indices[idx]
                change_pct = _safe_float(row.get("percentChange"), 0)
                sectors.append({
                    "name": name,
                    "index_symbol": idx,
                    "change_pct": change_pct,
                    "last": _safe_float(row.get("last")),
                    "weight": sector_weights.get(name, 3),
                    "advances": _safe_int(row.get("advances")),
                    "declines": _safe_int(row.get("declines")),
                })

        result = {"sectors": sectors, "updated_at": datetime.now(timezone.utc).isoformat()}
        _set_cache("sector_rotation", result)
        return result
    except Exception as e:
        logger.error(f"Sector rotation error: {e}")
        return {"sectors": [], "error": str(e)}


def get_volume_shockers():
    """Get stocks with 3x-5x average volume (volume breakouts)."""
    cached = _cached("volume_shockers", ttl=120)
    if cached:
        return cached

    try:
        from symbols import NIFTY_50, ALL_SYMBOLS
        symbols_to_check = [s["symbol"] for s in (NIFTY_50 + ALL_SYMBOLS[:30])]
        # Deduplicate
        seen = set()
        unique = []
        for s in symbols_to_check:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        symbols_to_check = unique[:50]

        shockers = []
        for sym in symbols_to_check:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="1mo")
                if hist is None or len(hist) < 11:
                    continue

                current_vol = float(hist["Volume"].iloc[-1])
                avg_vol_10d = float(hist["Volume"].iloc[-11:-1].mean())

                if avg_vol_10d <= 0:
                    continue

                vol_ratio = round(current_vol / avg_vol_10d, 1)
                if vol_ratio < 2.5:
                    continue

                close = float(hist["Close"].iloc[-1])
                prev_close = float(hist["Close"].iloc[-2])
                change_pct = round((close - prev_close) / prev_close * 100, 2)

                # Check for breakout (near 20d high)
                high_20d = float(hist["High"].iloc[-20:].max())
                is_breakout = close >= high_20d * 0.98

                clean_sym = sym.replace(".NS", "").replace(".BO", "")
                shockers.append({
                    "symbol": sym,
                    "display_name": clean_sym,
                    "price": round(close, 2),
                    "change_pct": change_pct,
                    "volume": int(current_vol),
                    "avg_volume": int(avg_vol_10d),
                    "vol_ratio": vol_ratio,
                    "is_breakout": is_breakout,
                    "trigger": "breakout" if is_breakout else "volume_spike",
                })
            except Exception:
                continue

        shockers.sort(key=lambda x: x["vol_ratio"], reverse=True)
        result = {"shockers": shockers[:20], "updated_at": datetime.now(timezone.utc).isoformat()}
        _set_cache("volume_shockers", result, ttl=120)
        return result
    except Exception as e:
        logger.error(f"Volume shockers error: {e}")
        return {"shockers": [], "error": str(e)}


def get_52w_clusters():
    """Get 52-week high/low cluster data."""
    cached = _cached("52w_clusters")
    if cached:
        return cached

    try:
        from nselib import capital_market
        today = date.today()

        # Try today, then recent dates
        df = None
        for days_back in range(0, 5):
            d = today - timedelta(days=days_back)
            try:
                df = capital_market.week_52_high_low_report(d.strftime("%d-%m-%Y"))
                if df is not None and len(df) > 0:
                    break
            except Exception:
                continue

        if df is None or len(df) == 0:
            return {"highs": [], "lows": [], "high_count": 0, "low_count": 0, "error": "No data"}

        # Process 52W data
        highs = []
        lows = []
        for _, row in df.iterrows():
            sym = str(row.get("SYMBOL", "")).strip()
            high_52w = _safe_float(row.get("Adjusted_52_Week_High"))
            low_52w = _safe_float(row.get("Adjusted_52_Week_Low"))
            high_date = str(row.get("52_Week_High_Date", ""))
            low_date = str(row.get("52_Week_Low_DT", ""))

            # Check if recent high (within 5 days)
            try:
                hd = datetime.strptime(high_date.strip(), "%d-%b-%Y").date()
                if (today - hd).days <= 5:
                    highs.append({"symbol": sym, "price": high_52w, "date": high_date})
            except Exception:
                pass

            # Check if recent low (within 5 days)
            try:
                ld = datetime.strptime(low_date.strip(), "%d-%b-%Y").date()
                if (today - ld).days <= 5:
                    lows.append({"symbol": sym, "price": low_52w, "date": low_date})
            except Exception:
                pass

        result = {
            "highs": highs[:30],
            "lows": lows[:30],
            "high_count": len(highs),
            "low_count": len(lows),
            "total_stocks": len(df),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _set_cache("52w_clusters", result)
        return result
    except Exception as e:
        logger.error(f"52W clusters error: {e}")
        return {"highs": [], "lows": [], "high_count": 0, "low_count": 0, "error": str(e)}


# ── 3. DERIVATIVES & SENTIMENT ───────────────────────────────────────────────

def get_pcr():
    """Compute Put-Call Ratio for Nifty and Bank Nifty from option chain."""
    cached = _cached("pcr")
    if cached:
        return cached

    result = {"nifty": None, "banknifty": None}

    for symbol, key in [("NIFTY", "nifty"), ("BANKNIFTY", "banknifty")]:
        try:
            from nselib import derivatives

            # Get expiry dates first
            expiry_data = derivatives.expiry_dates_option_index()
            expiry_dates = expiry_data.get(symbol, [])
            if not expiry_dates:
                continue

            # Get nearest expiry in DD-MM-YYYY format
            nearest_expiry = expiry_dates[0]
            # Convert from DD-Mon-YYYY to DD-MM-YYYY if needed
            try:
                from datetime import datetime as dt
                parsed = dt.strptime(nearest_expiry, "%d-%b-%Y")
                nearest_expiry_fmt = parsed.strftime("%d-%m-%Y")
            except Exception:
                nearest_expiry_fmt = nearest_expiry

            oc = derivatives.nse_live_option_chain(symbol, expiry_date=nearest_expiry_fmt)
            if oc is not None and hasattr(oc, "columns") and len(oc) > 0:
                put_oi = _safe_float(oc["PUTS_OI"].sum(), 0)
                call_oi = _safe_float(oc["CALLS_OI"].sum(), 0)

                pcr_val = round(put_oi / max(call_oi, 1), 2) if call_oi > 0 else None

                if pcr_val is not None:
                    if pcr_val > 1.3:
                        sentiment = "put_heavy"
                        label = "Bullish (Put Heavy)"
                    elif pcr_val > 1.0:
                        sentiment = "mildly_bullish"
                        label = "Mildly Bullish"
                    elif pcr_val > 0.7:
                        sentiment = "neutral"
                        label = "Neutral"
                    else:
                        sentiment = "call_heavy"
                        label = "Bearish (Call Heavy)"

                    result[key] = {
                        "pcr": pcr_val,
                        "put_oi": int(put_oi),
                        "call_oi": int(call_oi),
                        "sentiment": sentiment,
                        "label": label,
                        "expiry": nearest_expiry,
                    }
        except Exception as e:
            logger.error(f"PCR error for {symbol}: {e}")
            result[key] = {"pcr": None, "error": str(e)}

    result["updated_at"] = datetime.now(timezone.utc).isoformat()
    _set_cache("pcr", result)
    return result


def get_oi_quadrant():
    """Classify F&O stocks into OI buildup quadrants."""
    cached = _cached("oi_quadrant", ttl=120)
    if cached:
        return cached

    try:
        from symbols import NIFTY_50
        # Use top F&O stocks
        fno_symbols = [s["symbol"] for s in NIFTY_50[:30]]

        quadrants = {
            "long_buildup": [],
            "short_covering": [],
            "short_buildup": [],
            "long_unwinding": [],
        }

        for sym in fno_symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="5d")
                if hist is None or len(hist) < 2:
                    continue

                close_today = float(hist["Close"].iloc[-1])
                close_prev = float(hist["Close"].iloc[-2])
                vol_today = float(hist["Volume"].iloc[-1])
                vol_prev = float(hist["Volume"].iloc[-2])

                price_change = round((close_today - close_prev) / close_prev * 100, 2)
                vol_change = round((vol_today - vol_prev) / max(vol_prev, 1) * 100, 2)

                clean_sym = sym.replace(".NS", "").replace(".BO", "")

                entry = {
                    "symbol": sym,
                    "display_name": clean_sym,
                    "price": round(close_today, 2),
                    "price_change": price_change,
                    "volume_change": vol_change,
                }

                # Classify into quadrants
                # Using volume change as proxy for OI change (since real OI requires NSE F&O data)
                if price_change > 0 and vol_change > 0:
                    quadrants["long_buildup"].append(entry)
                elif price_change > 0 and vol_change < 0:
                    quadrants["short_covering"].append(entry)
                elif price_change < 0 and vol_change > 0:
                    quadrants["short_buildup"].append(entry)
                else:
                    quadrants["long_unwinding"].append(entry)
            except Exception:
                continue

        # Sort each quadrant by absolute price change
        for q in quadrants.values():
            q.sort(key=lambda x: abs(x["price_change"]), reverse=True)

        result = {
            "quadrants": quadrants,
            "total_stocks": sum(len(v) for v in quadrants.values()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _set_cache("oi_quadrant", result, ttl=120)
        return result
    except Exception as e:
        logger.error(f"OI quadrant error: {e}")
        return {"quadrants": {}, "error": str(e)}


# ── 4. CORPORATE ACTIONS & NEWS ──────────────────────────────────────────────

def get_block_deals():
    """Get recent block/bulk deals."""
    cached = _cached("block_deals")
    if cached:
        return cached

    try:
        from nselib import capital_market
        df = capital_market.block_deals_data(period="1M")

        deals = []
        if df is not None and len(df) > 0:
            for _, row in df.iterrows():
                qty_str = str(row.get("QuantityTraded", "0")).replace(",", "")
                price_str = str(row.get("TradePrice/Wght.Avg.Price", "0")).replace(",", "")
                qty = _safe_float(qty_str, 0)
                price = _safe_float(price_str, 0)
                value_cr = round(qty * price / 1e7, 2) if qty and price else 0

                deals.append({
                    "date": str(row.get("Date", "")),
                    "symbol": str(row.get("Symbol", "")),
                    "name": str(row.get("SecurityName", "")),
                    "client": str(row.get("ClientName", "")),
                    "side": str(row.get("Buy/Sell", "")),
                    "quantity": int(qty) if qty else 0,
                    "price": round(price, 2) if price else 0,
                    "value_cr": value_cr,
                })

        # Sort by date descending, value descending
        deals.sort(key=lambda x: (x["date"], x["value_cr"]), reverse=True)

        result = {"deals": deals[:30], "total": len(deals), "updated_at": datetime.now(timezone.utc).isoformat()}
        _set_cache("block_deals", result)
        return result
    except Exception as e:
        logger.error(f"Block deals error: {e}")
        return {"deals": [], "error": str(e)}


def get_corporate_actions():
    """Get upcoming corporate actions (dividends, splits, earnings)."""
    cached = _cached("corporate_actions")
    if cached:
        return cached

    try:
        from nselib import capital_market

        # Get last 2 weeks of actions
        today = date.today()
        from_date = (today - timedelta(days=7)).strftime("%d-%m-%Y")
        to_date = (today + timedelta(days=14)).strftime("%d-%m-%Y")

        df = capital_market.corporate_actions_for_equity(from_date=from_date, to_date=to_date)

        actions = []
        if df is not None and len(df) > 0:
            for _, row in df.iterrows():
                subject = str(row.get("subject", ""))
                ex_date = str(row.get("exDate", ""))

                # Categorize
                category = "other"
                if "dividend" in subject.lower():
                    category = "dividend"
                elif "split" in subject.lower():
                    category = "split"
                elif "bonus" in subject.lower():
                    category = "bonus"
                elif "rights" in subject.lower():
                    category = "rights"
                elif "agm" in subject.lower() or "egm" in subject.lower():
                    category = "meeting"

                actions.append({
                    "symbol": str(row.get("symbol", "")),
                    "subject": subject,
                    "ex_date": ex_date,
                    "record_date": str(row.get("recDate", "")),
                    "category": category,
                })

        # Sort by ex_date
        actions.sort(key=lambda x: x["ex_date"], reverse=True)

        result = {"actions": actions[:30], "total": len(actions), "updated_at": datetime.now(timezone.utc).isoformat()}
        _set_cache("corporate_actions", result)
        return result
    except Exception as e:
        logger.error(f"Corporate actions error: {e}")
        return {"actions": [], "error": str(e)}


# ── CONSOLIDATED COCKPIT ENDPOINT ────────────────────────────────────────────

def get_full_cockpit():
    """
    Consolidated endpoint that gathers all dashboard data.
    Each module is independent - if one fails, others still return.
    """
    modules = {}

    # Macro View
    try:
        modules["indices"] = get_indices_snapshot()
    except Exception as e:
        modules["indices"] = {"error": str(e)}

    try:
        modules["breadth"] = get_market_breadth()
    except Exception as e:
        modules["breadth"] = {"error": str(e)}

    try:
        modules["vix"] = get_vix_regime()
    except Exception as e:
        modules["vix"] = {"error": str(e)}

    try:
        modules["flows"] = get_fii_dii_flows()
    except Exception as e:
        modules["flows"] = {"error": str(e)}

    # Micro View
    try:
        modules["sectors"] = get_sector_rotation()
    except Exception as e:
        modules["sectors"] = {"error": str(e)}

    try:
        modules["clusters_52w"] = get_52w_clusters()
    except Exception as e:
        modules["clusters_52w"] = {"error": str(e)}

    # Derivatives
    try:
        modules["pcr"] = get_pcr()
    except Exception as e:
        modules["pcr"] = {"error": str(e)}

    # Corporate Actions
    try:
        modules["block_deals"] = get_block_deals()
    except Exception as e:
        modules["block_deals"] = {"error": str(e)}

    try:
        modules["corporate_actions"] = get_corporate_actions()
    except Exception as e:
        modules["corporate_actions"] = {"error": str(e)}

    modules["updated_at"] = datetime.now(timezone.utc).isoformat()
    return modules


def get_slow_cockpit_modules():
    """
    Modules that take longer (volume shockers, OI quadrant).
    Called separately so the main cockpit loads fast.
    """
    modules = {}

    try:
        modules["volume_shockers"] = get_volume_shockers()
    except Exception as e:
        modules["volume_shockers"] = {"error": str(e)}

    try:
        modules["oi_quadrant"] = get_oi_quadrant()
    except Exception as e:
        modules["oi_quadrant"] = {"error": str(e)}

    modules["updated_at"] = datetime.now(timezone.utc).isoformat()
    return modules
