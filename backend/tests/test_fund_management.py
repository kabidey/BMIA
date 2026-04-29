"""Fund Management (BMIA) — backend endpoint tests.

Covers:
  - POST /api/funds/analyze
  - GET /api/funds/runs/{id}  (polling completion)
  - GET /api/funds/runs       (list, no _id leak)
  - GET /api/funds/stream/{id} (SSE streaming)
"""
import os
import time
import json
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bharat-quant-lab.preview.emergentagent.com").rstrip("/")
TIMEOUT = 180  # allow up to 3 minutes for the 6-agent pipeline (observed ~100-120s)


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def started_run(api):
    """Kick off one RELIANCE run that all tests below piggy-back on."""
    r = api.post(
        f"{BASE_URL}/api/funds/analyze",
        json={"symbol": "RELIANCE", "horizon_hint": "swing"},
        timeout=60,
    )
    assert r.status_code == 200, f"analyze failed: {r.status_code} {r.text[:300]}"
    j = r.json()
    assert "run_id" in j and len(j["run_id"]) >= 8
    assert j["status"] == "running"
    return j["run_id"]


# ─── 1. POST /api/funds/analyze ─────────────────────────────────────────
class TestAnalyzeEndpoint:
    def test_analyze_returns_run_id(self, started_run):
        assert isinstance(started_run, str)
        assert len(started_run) >= 8

    def test_analyze_rejects_empty_symbol(self, api):
        r = api.post(f"{BASE_URL}/api/funds/analyze", json={"symbol": ""}, timeout=60)
        assert r.status_code in (400, 422)


# ─── 2. GET /api/funds/runs/{run_id} — completion ───────────────────────
class TestRunCompletion:
    def test_run_eventually_completes(self, api, started_run):
        deadline = time.time() + TIMEOUT
        last_status = None
        run = None
        while time.time() < deadline:
            r = api.get(f"{BASE_URL}/api/funds/runs/{started_run}", timeout=60)
            assert r.status_code == 200
            run = r.json()
            last_status = run.get("status")
            if last_status in ("completed", "error"):
                break
            time.sleep(5)
        assert last_status == "completed", f"did not complete in {TIMEOUT}s (last={last_status}, err={run.get('error') if run else None})"
        # _id should not leak
        assert "_id" not in run
        # final_verdict populated
        fv = run.get("final_verdict") or {}
        assert isinstance(fv, dict) and fv, "final_verdict missing/empty"
        # typical fields
        assert "final_verdict" in fv or "headline" in fv or "rationale" in fv
        # stages progressed through all 6 keys
        stages = run.get("stages") or {}
        expected = {"data_gathering", "analysts", "debate", "trader", "risk", "fund_manager"}
        missing = expected - set(stages.keys())
        assert not missing, f"missing stages: {missing}"


# ─── 3. GET /api/funds/runs — list, no _id leak ─────────────────────────
class TestListRuns:
    def test_list_runs_no_id_leak(self, api, started_run):
        r = api.get(f"{BASE_URL}/api/funds/runs?limit=8", timeout=60)
        assert r.status_code == 200
        j = r.json()
        assert "runs" in j and isinstance(j["runs"], list)
        # our recently-started run should appear
        ids = [x.get("run_id") for x in j["runs"]]
        assert started_run in ids
        for row in j["runs"]:
            assert "_id" not in row
            # events excluded in list projection
            assert "events" not in row


# ─── 4. GET /api/funds/stream/{run_id} — SSE ────────────────────────────
class TestSseStream:
    def test_sse_emits_stage_and_done(self, api):
        """Start a *separate* run and tail the SSE stream until 'done'."""
        r = api.post(
            f"{BASE_URL}/api/funds/analyze",
            json={"symbol": "RELIANCE", "horizon_hint": "swing"},
            timeout=60,
        )
        assert r.status_code == 200
        rid = r.json()["run_id"]

        stages_seen = set()
        done_seen = False
        # 2 minutes max
        with requests.get(
            f"{BASE_URL}/api/funds/stream/{rid}",
            stream=True,
            timeout=(10, TIMEOUT),
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("Content-Type", "")
            event = None
            start = time.time()
            for raw in resp.iter_lines(decode_unicode=True):
                if time.time() - start > TIMEOUT:
                    break
                if raw is None:
                    continue
                line = raw.strip()
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    payload = line.split(":", 1)[1].strip()
                    if event == "stage":
                        try:
                            data = json.loads(payload)
                            if data.get("stage"):
                                stages_seen.add(data["stage"])
                        except Exception:
                            pass
                    elif event == "done":
                        done_seen = True
                        break
                    elif event == "error":
                        pytest.fail(f"SSE emitted error: {payload}")
        assert done_seen, f"no 'done' event (stages_seen={stages_seen})"
        # Pipeline must have progressed through all 6 stages in the events
        expected = {"data_gathering", "analysts", "debate", "trader", "risk", "fund_manager"}
        missing = expected - stages_seen
        assert not missing, f"missing SSE stages: {missing} (seen={stages_seen})"
