"""Backend tests for Compliance (NSE/BSE/SEBI RAG) endpoints."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: read from /app/frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api/compliance"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Stats endpoint ---
class TestStats:
    def test_stats_shape(self, session):
        r = session.get(f"{API}/stats", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "stores" in data and "sources" in data
        for src in ("nse", "bse", "sebi"):
            assert src in data["stores"]
            s = data["stores"][src]
            for k in ("ready", "chunk_count", "circular_count", "total_chunks_in_db"):
                assert k in s, f"{src} missing {k}"


# --- Rebuild (ensures stores are built before further tests) ---
class TestRebuild:
    def test_rebuild(self, session):
        r = session.post(f"{API}/rebuild", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "rebuilt"
        assert "stats" in data
        # At least one store should be ready (we have 4 seeded circulars)
        any_ready = any(s.get("ready") for s in data["stats"].values())
        assert any_ready, f"No store became ready after rebuild: {data['stats']}"


# --- Circulars list ---
class TestCirculars:
    def test_list_default(self, session):
        r = session.get(f"{API}/circulars", timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("total", "page", "limit", "items"):
            assert k in data
        assert isinstance(data["items"], list)
        # should have at least 4 seeded
        assert data["total"] >= 4, f"Expected >=4 seeded, got {data['total']}"
        # items should not include mongodb _id
        for it in data["items"]:
            assert "_id" not in it

    def test_filter_by_source_sebi(self, session):
        r = session.get(f"{API}/circulars", params={"source": "sebi"}, timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it.get("source") == "sebi"

    def test_filter_by_source_nse(self, session):
        r = session.get(f"{API}/circulars", params={"source": "nse"}, timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it.get("source") == "nse"

    def test_search_filter(self, session):
        r = session.get(f"{API}/circulars", params={"search": "insider"}, timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        # at least the SEBI insider-trading seed should match
        assert len(items) >= 1
        assert any("insider" in (it.get("title") or "").lower() for it in items)

    def test_pagination(self, session):
        r = session.get(f"{API}/circulars", params={"page": 1, "limit": 2}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["limit"] == 2
        assert len(data["items"]) <= 2


# --- Research endpoint ---
class TestResearch:
    def test_short_question_rejected(self, session):
        r = session.post(f"{API}/research", json={"question": "hi"}, timeout=30)
        assert r.status_code == 400

    def test_empty_question_rejected(self, session):
        r = session.post(f"{API}/research", json={"question": "   "}, timeout=30)
        assert r.status_code == 400

    def test_research_sebi_insider_trading(self, session):
        payload = {"question": "insider trading disclosure rules", "sources": ["sebi"], "top_k": 5}
        r = session.post(f"{API}/research", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "answer" in data
        assert "citations" in data
        assert isinstance(data["citations"], list)
        assert "sources_searched" in data
        assert data["sources_searched"] == ["sebi"]
        # Should have retrieved at least one citation from the seeded SEBI circular
        if data["citations"]:
            c = data["citations"][0]
            for k in ("id", "source", "circular_no", "title", "date", "category", "url", "score"):
                assert k in c, f"citation missing {k}"
            # source filter honoured
            assert all(ci["source"].lower() == "sebi" for ci in data["citations"])

    def test_research_nse_algo_trading(self, session):
        payload = {"question": "algorithmic trading risk management", "sources": ["nse"], "top_k": 5}
        r = session.post(f"{API}/research", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        if data.get("citations"):
            assert all(ci["source"].lower() == "nse" for ci in data["citations"])

    def test_research_bse_lodr(self, session):
        payload = {"question": "LODR corporate governance", "sources": ["bse"], "top_k": 5}
        r = session.post(f"{API}/research", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        if data.get("citations"):
            assert all(ci["source"].lower() == "bse" for ci in data["citations"])

    def test_research_all_sources(self, session):
        payload = {"question": "compliance requirements for listed companies", "top_k": 8}
        r = session.post(f"{API}/research", json=payload, timeout=120)
        assert r.status_code == 200
        data = r.json()
        assert set(data.get("sources_searched", [])) == {"nse", "bse", "sebi"}

    def test_research_year_filter(self, session):
        # Filter to a year unlikely to have seeds -> expect empty citations (not error)
        payload = {"question": "insider trading", "sources": ["sebi"], "year_filter": 1999, "top_k": 5}
        r = session.post(f"{API}/research", json=payload, timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert data.get("citations") == [] or len(data["citations"]) == 0


# --- Ingest-now ---
class TestIngestNow:
    def test_ingest_now_returns_started(self, session):
        r = session.post(f"{API}/ingest-now", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "started"
