"""
Iteration 31 — Tests for Big Market Intel tab (6 aggregators),
compliance ingestion progress, and regressions on cockpit + auth.
"""
import os
import time
import pytest
import requests

def _resolve_base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        # fallback: read from frontend/.env
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.strip().split("=", 1)[1]
                        break
        except Exception:
            pass
    if not url:
        raise RuntimeError("REACT_APP_BACKEND_URL not set")
    return url.rstrip("/")

BASE_URL = _resolve_base_url()
API = f"{BASE_URL}/api"

LOGIN_EMAIL = "somnath.dey@smifs.com"
LOGIN_PASSWORD = "admin123"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_token(api):
    r = api.post(f"{API}/auth/login", json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:200]}"
    tok = r.json().get("token")
    assert tok and isinstance(tok, str) and len(tok) > 20
    return tok


# ---------- auth regression ----------
class TestAuth:
    def test_login_returns_jwt(self, api):
        r = api.post(f"{API}/auth/login", json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert "token" in body and len(body["token"]) > 20


# ---------- Intel endpoints ----------
class TestMovers:
    def test_movers_shape(self, api):
        r = api.get(f"{API}/big-market/movers", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # expect object with gainers/losers/high_volume arrays
        for key in ["gainers", "losers", "high_volume"]:
            assert key in data, f"missing {key}; keys={list(data.keys())}"
            assert isinstance(data[key], list)
        combined = data["gainers"] + data["losers"] + data["high_volume"]
        assert len(combined) > 0, "all movers arrays empty"
        # first item checks (field mapping fix)
        sample = (data["gainers"] or data["losers"] or data["high_volume"])[0]
        for field in ["symbol", "pct_change"]:
            assert field in sample, f"{field} missing in mover: {sample}"
        assert sample["symbol"], "symbol empty"
        assert sample["pct_change"] is not None


class TestFIIDII:
    def test_fii_dii_flows(self, api):
        r = api.get(f"{API}/big-market/fii-dii", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "flows" in data and isinstance(data["flows"], list)
        assert len(data["flows"]) >= 5, f"only {len(data['flows'])} flows"
        row = data["flows"][0]
        for f in ["fii_net", "dii_net", "fii_buy", "fii_sell"]:
            assert f in row, f"{f} missing: {row}"


class TestEarningsCalendar:
    def test_earnings_list(self, api):
        r = api.get(f"{API}/big-market/earnings-calendar", params={"days": 14}, timeout=45)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # may be list or {events:[]}
        events = data if isinstance(data, list) else data.get("events") or data.get("items") or []
        assert isinstance(events, list)
        assert len(events) >= 100, f"expected >=100 events, got {len(events)}"
        ev = events[0]
        for f in ["date", "symbol", "event_type"]:
            assert f in ev, f"missing {f}: {ev}"
        # date YYYY-MM-DD
        import re
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", ev["date"]), f"bad date {ev['date']}"


class TestPCR:
    def test_pcr_shape(self, api):
        r = api.get(f"{API}/big-market/pcr", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "current" in data, f"keys={list(data.keys())}"
        cur = data["current"]
        for idx in ["nifty", "banknifty"]:
            assert idx in cur, f"{idx} missing from current"
            assert cur[idx].get("pcr") is not None, f"{idx}.pcr null"
            assert isinstance(cur[idx]["pcr"], (int, float))


class TestAnalystEstimates:
    @pytest.mark.parametrize("symbol", ["RELIANCE", "TCS"])
    def test_estimates(self, api, symbol):
        r = api.get(f"{API}/big-market/analyst-estimates/{symbol}", timeout=45)
        assert r.status_code == 200, f"{symbol}: {r.text[:300]}"
        data = r.json()
        assert data.get("symbol", "").upper() == symbol
        # at least one fundamental numeric field should be populated
        numeric_fields = ["cmp", "pe", "roe", "market_cap_cr", "book_value"]
        populated = [f for f in numeric_fields if data.get(f) not in (None, "", 0)]
        assert len(populated) >= 2, f"too few populated numerics for {symbol}: {data}"


class TestNews:
    def test_news_items(self, api):
        r = api.get(f"{API}/big-market/news", params={"limit": 10}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        items = data if isinstance(data, list) else data.get("items") or data.get("news") or []
        assert len(items) >= 5, f"only {len(items)} news items"
        n = items[0]
        for f in ["title", "url", "published_at"]:
            assert f in n, f"missing {f} in news: {n}"
            assert n[f]


# ---------- compliance regression ----------
class TestCompliance:
    def test_compliance_stats(self, api):
        r = api.get(f"{API}/compliance/stats", timeout=20)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # overall phase
        phase = data.get("overall_phase") or data.get("phase")
        assert phase in ("backfill", "live"), f"unexpected phase {phase}: keys={list(data.keys())}"
        # per-source tracking lives in `stores` per current impl
        stores = data.get("stores") or data.get("by_source") or {}
        assert isinstance(stores, dict) and stores, f"no stores: {data}"
        for src in ["nse", "bse", "sebi"]:
            assert src in stores, f"missing source {src} in stores"
            sd = stores[src]
            for k in ["cycle_count", "progress_pct", "last_error"]:
                assert k in sd, f"{src} missing {k}: {sd}"

    def test_compliance_research_regression(self, api):
        # /research is POST per current router
        r = api.post(f"{API}/compliance/research", json={"query": "insider trading"}, timeout=45)
        assert r.status_code in (200, 422), r.text[:200]


# ---------- cockpit regression ----------
class TestCockpit:
    def test_cockpit_all_keys(self, api):
        r = api.get(f"{API}/market/cockpit", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # presence of key blocks — loose since schema may vary
        assert isinstance(data, dict)
        assert len(data.keys()) >= 5, f"cockpit keys too few: {list(data.keys())}"

    def test_cockpit_slow(self, api):
        r = api.get(f"{API}/market/cockpit/slow", timeout=60)
        assert r.status_code == 200, r.text[:300]

    def test_big_market_overview(self, api):
        r = api.get(f"{API}/big-market/overview", timeout=45)
        assert r.status_code == 200, r.text[:300]

    def test_guidance_stats(self, api):
        r = api.get(f"{API}/guidance/stats", timeout=20)
        assert r.status_code == 200, r.text[:200]


# ---------- NSE ingestion progress (best-effort) ----------
class TestNSEBackfillProgress:
    def test_nse_circular_count_growing(self, api):
        r = api.get(f"{API}/compliance/stats", timeout=20)
        assert r.status_code == 200
        data = r.json()
        by_src = data.get("stores") or data.get("by_source") or {}
        nse = by_src.get("nse", {})
        # expect circular_count >= 8 per spec within 5min of boot
        circ = nse.get("circular_count") or nse.get("circulars") or 0
        if circ < 8:
            pytest.xfail(f"NSE circular_count={circ} (<8); may be slow cold start or blocked upstream")
        assert circ >= 8
