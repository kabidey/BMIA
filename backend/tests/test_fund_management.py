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



# ─── 5. GET /api/funds/decisions — flat decision history ─────────────────
class TestDecisions:
    def test_decisions_returns_list_no_id_leak(self, api, started_run):
        # started_run already finished by the time TestRunCompletion ran
        r = api.get(f"{BASE_URL}/api/funds/decisions?limit=20", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "decisions" in body and isinstance(body["decisions"], list)
        assert len(body["decisions"]) >= 1, "Expected at least one decision"
        for d in body["decisions"]:
            assert "_id" not in d, "Mongo _id leaked into decisions"
            for f in ("symbol", "decision", "final_verdict", "confidence",
                      "headline", "ts"):
                assert f in d, f"decision row missing field {f}"
            assert d["decision"] in ("ACCEPT", "REJECT", "HOLD")
            assert d["final_verdict"] in (
                "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"
            )

    def test_decisions_filter_by_decision(self, api):
        r = api.get(f"{BASE_URL}/api/funds/decisions?decision=HOLD&limit=10",
                    timeout=10)
        assert r.status_code == 200
        for d in r.json().get("decisions", []):
            assert d["decision"] == "HOLD"

    def test_decisions_filter_source_daemon(self, api):
        # Daemon may take ~3 minutes after backend boot to log first decision.
        deadline = time.time() + 180
        last = []
        while time.time() < deadline:
            r = api.get(f"{BASE_URL}/api/funds/decisions?source=daemon&limit=20",
                        timeout=10)
            assert r.status_code == 200
            last = r.json().get("decisions", [])
            if last:
                break
            time.sleep(15)
        assert len(last) >= 1, "Expected at least one daemon-produced decision in 3 minutes"
        for d in last:
            assert d.get("source") == "daemon"


# ─── 6. /api/funds/daemon/* — daemon control & status ────────────────────
class TestDaemon:
    def test_daemon_status_shape(self, api):
        r = api.get(f"{BASE_URL}/api/funds/daemon/status", timeout=10)
        assert r.status_code == 200
        body = r.json()
        for k in ("state", "queued", "decisions_logged"):
            assert k in body, f"daemon status missing {k}"
        st = body["state"]
        for k in ("status", "current_symbol", "accepts", "rejects", "holds",
                  "cycle_count", "errors"):
            assert k in st, f"daemon state missing {k}"
        assert st["status"] in ("running", "paused", "stopped", "sleeping")
        assert isinstance(st["errors"], list)
        assert isinstance(body["queued"], int)

    def test_daemon_pause_then_start(self, api):
        # Pause
        r = api.post(f"{BASE_URL}/api/funds/daemon/control",
                     json={"action": "pause"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # Wait up to 60s for daemon thread to read kill switch from DB
        flipped = False
        for _ in range(12):
            time.sleep(5)
            st = api.get(f"{BASE_URL}/api/funds/daemon/status",
                         timeout=10).json()["state"]
            if st["status"] == "paused":
                flipped = True
                break
        assert flipped, "Daemon did not flip to paused within 60s"

        # Resume
        r2 = api.post(f"{BASE_URL}/api/funds/daemon/control",
                      json={"action": "start"}, timeout=10)
        assert r2.status_code == 200
        body = api.get(f"{BASE_URL}/api/funds/daemon/status", timeout=10).json()
        assert body["config"].get("paused") is False

    def test_daemon_invalid_action(self, api):
        r = api.post(f"{BASE_URL}/api/funds/daemon/control",
                     json={"action": "explode"}, timeout=10)
        assert r.status_code == 400


# ─── 7. recover_orphaned_runs() exists & is wired ────────────────────────
class TestOrphanRecoveryWiring:
    def test_recover_orphaned_runs_callable(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.fund_management import recover_orphaned_runs  # noqa: F401
        assert callable(recover_orphaned_runs)

    def test_recover_orphaned_runs_wired_in_server(self):
        with open("/app/backend/server.py") as fh:
            content = fh.read()
        assert "recover_orphaned_runs" in content, \
            "recover_orphaned_runs not referenced in server.py"
        assert "from routes.fund_management import recover_orphaned_runs" in content
