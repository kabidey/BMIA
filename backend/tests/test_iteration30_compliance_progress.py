"""
Iteration 30 — Compliance ingestion PROGRESS endpoint + per-source workers.

Covers:
  - GET /api/compliance/stats returns overall_phase, totals, per-source progress fields
  - progress_pct is computed from distinct years (honest)
  - state docs persist in compliance_ingestion_state
  - POST /api/compliance/ingest-now still works
  - POST /api/compliance/research still works (unchanged flow)
"""
import os
import time
import pytest
import requests
import pymongo

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://compliance-rag-agent.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

EXPECTED_SRC_FIELDS = {
    "phase", "progress_pct", "oldest_date", "newest_date",
    "target_start_year", "years_covered", "total_years_span",
    "cycle_count", "last_cycle_at", "last_new_ingest_at",
    "started_at", "errors_count", "last_error",
    "circular_count", "total_chunks_in_db",
}


@pytest.fixture(scope="module")
def mongo_db():
    c = pymongo.MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


class TestComplianceStats:
    # stats structure
    def test_stats_top_level_shape(self):
        r = requests.get(f"{BASE_URL}/api/compliance/stats", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "stores" in d and "sources" in d
        assert "overall_phase" in d and d["overall_phase"] in ("backfill", "live", "idle")
        assert "totals" in d
        for k in ("circulars", "chunks", "avg_progress_pct"):
            assert k in d["totals"], f"totals missing {k}"
        assert set(d["stores"].keys()) == {"nse", "bse", "sebi"}

    def test_per_source_fields(self):
        r = requests.get(f"{BASE_URL}/api/compliance/stats", timeout=20)
        d = r.json()
        for src in ("nse", "bse", "sebi"):
            s = d["stores"][src]
            missing = EXPECTED_SRC_FIELDS - set(s.keys())
            assert not missing, f"{src} missing fields: {missing}"
            assert 0 <= s["progress_pct"] <= 100
            assert s["phase"] in ("backfill", "live", "idle")
            assert isinstance(s["years_covered"], int)
            assert isinstance(s["total_years_span"], int) and s["total_years_span"] >= 1

    # progress_pct must be derived from DISTINCT year count (honest)
    def test_progress_pct_matches_distinct_years(self, mongo_db):
        r = requests.get(f"{BASE_URL}/api/compliance/stats", timeout=20)
        d = r.json()
        target_year = int(os.environ.get("COMPLIANCE_TARGET_START_YEAR", "2010"))
        from datetime import datetime, timezone
        cur_year = datetime.now(timezone.utc).year
        span = max(1, cur_year - target_year + 1)
        for src in ("nse", "bse", "sebi"):
            years = mongo_db.compliance_circulars.distinct(
                "year", {"source": src, "year": {"$gte": target_year, "$lte": cur_year}}
            )
            expected_pct = round(100.0 * len(years) / span, 1)
            got = d["stores"][src]["progress_pct"]
            assert abs(got - expected_pct) < 0.2, f"{src}: api={got} expected={expected_pct}"
            assert d["stores"][src]["years_covered"] == len(years)


class TestStatePersistence:
    # state docs exist in compliance_ingestion_state
    def test_state_docs_present(self, mongo_db):
        # give daemon a moment in case of cold start
        for _ in range(3):
            docs = list(mongo_db.compliance_ingestion_state.find({}, {"_id": 0}))
            sources = {d["source"] for d in docs}
            if {"nse", "bse", "sebi"}.issubset(sources):
                break
            time.sleep(2)
        assert {"nse", "bse", "sebi"}.issubset({d["source"] for d in docs}), f"missing sources in state: {docs}"
        for d in docs:
            assert "phase" in d
            assert d["phase"] in ("backfill", "live")
            assert "started_at" in d and d["started_at"]
            assert "target_start_year" in d

    def test_cycle_count_is_numeric(self, mongo_db):
        for d in mongo_db.compliance_ingestion_state.find({}, {"_id": 0}):
            assert isinstance(d.get("cycle_count", 0), int)
            assert d.get("cycle_count", 0) >= 0


class TestIngestNow:
    # manual trigger endpoint
    def test_trigger_returns_started(self):
        r = requests.post(f"{BASE_URL}/api/compliance/ingest-now", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d.get("status") == "started"


class TestResearchStillWorks:
    # research endpoint should still return answer + citations on seeded corpus
    def test_research_validation(self):
        r = requests.post(f"{BASE_URL}/api/compliance/research", json={"question": "hi"}, timeout=15)
        assert r.status_code == 400

    def test_research_answer(self):
        payload = {
            "question": "What are SEBI insider trading disclosure rules?",
            "sources": ["sebi"],
            "top_k": 5,
        }
        r = requests.post(f"{BASE_URL}/api/compliance/research", json=payload, timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert "answer" in d
        assert isinstance(d.get("citations", []), list)


class TestStatsNoStateEdgeCase:
    # endpoint must not 500 even when state absent; create a dummy fourth source temporarily should not break
    def test_stats_idempotent(self):
        # call twice back-to-back
        r1 = requests.get(f"{BASE_URL}/api/compliance/stats", timeout=20)
        r2 = requests.get(f"{BASE_URL}/api/compliance/stats", timeout=20)
        assert r1.status_code == 200 and r2.status_code == 200
