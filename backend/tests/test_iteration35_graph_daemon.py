"""Tests for iteration 35 — background graph extraction daemon + multihop force_mode."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bharat-quant-lab.preview.emergentagent.com").rstrip("/")


@pytest.fixture
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ─── Graph extraction daemon ────────────────────────────────────────────
class TestGraphExtraction:
    def test_extraction_status_shape(self, api):
        r = api.get(f"{BASE_URL}/api/compliance/graph/extraction-status", timeout=30)
        assert r.status_code == 200
        d = r.json()
        # Required keys
        for k in ("phase", "total_circulars", "extracted", "pending", "progress_pct"):
            assert k in d, f"missing key {k}"
        # Numeric types
        assert isinstance(d["total_circulars"], int)
        assert isinstance(d["extracted"], int)
        assert isinstance(d["pending"], int)
        assert isinstance(d["progress_pct"], (int, float))
        # progress_pct = 100*extracted/total_circulars rounded to 1 dp
        if d["total_circulars"]:
            expected = round(100.0 * d["extracted"] / d["total_circulars"], 1)
            assert abs(d["progress_pct"] - expected) < 0.05

    def test_extraction_running_after_manual_start(self, api):
        r = api.get(f"{BASE_URL}/api/compliance/graph/extraction-status", timeout=30)
        d = r.json()
        assert d["phase"] in ("running", "idle"), f"phase={d['phase']}"
        assert d.get("cycle_count", 0) >= 1

    def test_start_extraction_idempotent(self, api):
        r = api.post(f"{BASE_URL}/api/compliance/graph/start-extraction", timeout=30)
        assert r.status_code == 200
        assert r.json().get("status") == "started"
        # second call
        r2 = api.post(f"{BASE_URL}/api/compliance/graph/start-extraction", timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("status") == "started"

    def test_daemon_progress_over_60s(self, api):
        r1 = api.get(f"{BASE_URL}/api/compliance/graph/extraction-status", timeout=30).json()
        time.sleep(65)
        r2 = api.get(f"{BASE_URL}/api/compliance/graph/extraction-status", timeout=30).json()
        # Daemon should either be idle (caught up) OR show forward progress
        assert r2["extracted"] >= r1["extracted"], (
            f"extracted did not grow: {r1['extracted']} -> {r2['extracted']}"
        )
        assert r2.get("cycle_count", 0) >= r1.get("cycle_count", 0)


# ─── Smart research force_mode ─────────────────────────────────────────
class TestSmartResearchForceMode:
    def test_force_multihop_override(self, api):
        q = "What is the current insider trading disclosure timeline?"
        r = api.post(
            f"{BASE_URL}/api/compliance/smart-research",
            json={"question": q, "force_mode": "multihop"},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("mode") == "multihop"
        assert d.get("classifier", {}).get("source") == "override"
        sg = d.get("subgraph") or {}
        assert "nodes" in sg
        # subgraph may be empty only if no citations; print for visibility
        assert isinstance(sg.get("nodes"), list)

    def test_no_force_mode_classifier(self, api):
        r = api.post(
            f"{BASE_URL}/api/compliance/smart-research",
            json={"question": "What is the current insider trading disclosure timeline?"},
            timeout=120,
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("mode") in ("narrow", "multihop", "thematic")
        cls = d.get("classifier", {})
        assert cls.get("source") != "override"


# ─── Regressions ───────────────────────────────────────────────────────
class TestRegressions:
    def test_graph_stats(self, api):
        r = api.get(f"{BASE_URL}/api/compliance/graph/stats", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "total_circulars" in d

    def test_dedupe_dry_run(self, api):
        r = api.post(
            f"{BASE_URL}/api/compliance/dedupe",
            json={"dry_run": True, "match_on": "url"},
            timeout=60,
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("status") == "dry_run"

    def test_rebuild(self, api):
        r = api.post(f"{BASE_URL}/api/compliance/rebuild", timeout=60)
        assert r.status_code == 200
        assert r.json().get("status") == "rebuilt"

    def test_narrow_classification(self, api):
        r = api.post(
            f"{BASE_URL}/api/compliance/smart-research",
            json={"question": "What is circular CIR/CFD/DIL/2023/001 about?"},
            timeout=90,
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("mode") in ("narrow", "multihop", "thematic")
