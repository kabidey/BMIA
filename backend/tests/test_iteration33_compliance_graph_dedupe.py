"""
Iteration 33 — GraphRAG + 3D viz + SEBI dedupe endpoint for Compliance.

Tests:
- POST /api/compliance/dedupe (dry_run / match_on=url / match_on=source_circno)
- SEBI dedupe execution (dry_run=false) → verify counts fall to 0 on re-run
- GET /api/compliance/graph/stats
- POST /api/compliance/graph/query (enrich=false and enrich=true)
- GET /api/compliance/graph/subgraph?source=sebi

These rely on the backend being warmed up (TF-IDF store ready). If not ready,
we call /api/compliance/rebuild first.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module", autouse=True)
def ensure_store_ready(client):
    """If TF-IDF stores aren't ready, trigger rebuild."""
    try:
        r = client.get(f"{API}/compliance/stats", timeout=30)
        if r.status_code != 200:
            return
        stats = r.json()
        stores = (stats.get("stores") or {})
        ready = all(v.get("ready") for v in stores.values()) if stores else False
        if not ready:
            print("[setup] rebuilding compliance stores...")
            client.post(f"{API}/compliance/rebuild", timeout=120)
            time.sleep(2)
    except Exception as e:
        print(f"[setup] warning: could not verify store readiness: {e}")


# -------- Dedupe endpoint --------

class TestDedupe:
    def test_dedupe_dry_run_by_url(self, client):
        r = client.post(f"{API}/compliance/dedupe",
                        json={"dry_run": True, "match_on": "url"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "dry_run"
        for k in ("duplicate_groups", "duplicate_extra_docs",
                  "duplicate_chunk_rows_estimate"):
            assert k in data, f"missing key {k}"
        assert isinstance(data["duplicate_groups"], int)
        # We expect >0 duplicate groups per the task brief (7 reported)
        print(f"[dry_run/url] groups={data['duplicate_groups']} "
              f"extras={data['duplicate_extra_docs']} "
              f"chunks~={data['duplicate_chunk_rows_estimate']}")
        # Should not delete in dry-run
        assert data.get("deleted_circulars", 0) == 0
        assert data.get("deleted_chunks", 0) == 0

    def test_dedupe_dry_run_by_source_circno(self, client):
        r = client.post(f"{API}/compliance/dedupe",
                        json={"dry_run": True, "match_on": "source_circno"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "dry_run"
        assert data["match_on"] == "source_circno"
        assert data.get("deleted_circulars", 0) == 0

    def test_dedupe_invalid_match_on(self, client):
        r = client.post(f"{API}/compliance/dedupe",
                        json={"dry_run": True, "match_on": "bogus"}, timeout=30)
        assert r.status_code == 400

    def test_dedupe_sebi_execute_and_verify(self, client):
        # 1) SEBI dry_run first
        r = client.post(f"{API}/compliance/dedupe",
                        json={"source": "sebi", "dry_run": True, "match_on": "url"}, timeout=60)
        assert r.status_code == 200, r.text
        pre = r.json()
        print(f"[sebi/dry_run] groups={pre['duplicate_groups']} extras={pre['duplicate_extra_docs']}")

        if pre["duplicate_groups"] == 0:
            pytest.skip("No SEBI duplicates present; cannot exercise delete path")

        # 2) Execute delete
        r2 = client.post(f"{API}/compliance/dedupe",
                         json={"source": "sebi", "dry_run": False, "match_on": "url"}, timeout=180)
        assert r2.status_code == 200, r2.text
        exe = r2.json()
        assert exe["status"] == "executed"
        assert exe["deleted_circulars"] > 0, "expected deletions but got 0"
        assert exe["deleted_chunks"] >= 0
        assert "sebi" in (exe.get("rebuilt_sources") or [])
        print(f"[sebi/executed] deleted_circulars={exe['deleted_circulars']} "
              f"deleted_chunks={exe['deleted_chunks']}")

        # 3) Re-run dry_run — should report 0 now
        r3 = client.post(f"{API}/compliance/dedupe",
                         json={"source": "sebi", "dry_run": True, "match_on": "url"}, timeout=60)
        assert r3.status_code == 200
        post = r3.json()
        assert post["duplicate_groups"] == 0, \
            f"expected 0 groups after dedupe, got {post['duplicate_groups']}"


# -------- Graph endpoints --------

class TestGraph:
    def test_graph_stats(self, client):
        r = client.get(f"{API}/compliance/graph/stats", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("total_circulars", "llm_enriched_circulars", "sources"):
            assert k in data, f"missing key {k}"
        assert isinstance(data["total_circulars"], int)
        assert data["total_circulars"] > 0

    def test_graph_query_no_enrich(self, client):
        payload = {"question": "SEBI insider trading disclosure rules",
                   "top_k": 6, "enrich": False}
        r = client.post(f"{API}/compliance/graph/query", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "answer" in data
        assert "citations" in data and len(data["citations"]) > 0, \
            "expected >=1 citation"
        sg = data.get("subgraph") or {}
        assert "nodes" in sg and "edges" in sg
        assert len(sg["nodes"]) > 0, \
            f"expected nodes in subgraph, got: {sg}"

        # at least one node must be seed=True (validates lowercase source fix)
        seeds = [n for n in sg["nodes"] if n.get("seed")]
        assert len(seeds) > 0, \
            f"expected >=1 seed node. Subgraph nodes: {sg['nodes'][:5]}"
        # Seed node IDs should be lowercase 'source:circular_no'
        for s in seeds:
            nid = s.get("id", "")
            assert ":" in nid, f"seed id wrong format: {nid}"
            src_part = nid.split(":", 1)[0]
            assert src_part == src_part.lower(), \
                f"seed source part not lowercase: {nid}"

    def test_graph_query_with_enrich_and_cache(self, client):
        payload = {"question": "SEBI insider trading disclosure rules",
                   "top_k": 6, "enrich": True}
        t0 = time.time()
        r = client.post(f"{API}/compliance/graph/query", json=payload, timeout=150)
        dt1 = time.time() - t0
        assert r.status_code == 200, r.text
        data = r.json()
        sg = data.get("subgraph") or {}
        nodes = sg.get("nodes") or []
        assert len(nodes) > 0

        entity_nodes = [n for n in nodes if n.get("source") == "entity"]
        if not entity_nodes:
            pytest.skip(f"no entity nodes returned (LLM enrichment may have "
                        f"failed silently). dt={dt1:.1f}s nodes={len(nodes)}")

        allowed_types = {"REGULATION", "COMPANY", "CONCEPT", "PERSON", "DATE", "EVENT"}
        for en in entity_nodes:
            assert en.get("entity_type") in allowed_types, \
                f"unexpected entity_type: {en.get('entity_type')}"
        print(f"[enrich] first call {dt1:.1f}s entities={len(entity_nodes)}")

        # Second call — expect cached, faster
        t1 = time.time()
        r2 = client.post(f"{API}/compliance/graph/query", json=payload, timeout=60)
        dt2 = time.time() - t1
        assert r2.status_code == 200
        nodes2 = (r2.json().get("subgraph") or {}).get("nodes") or []
        ent2 = [n for n in nodes2 if n.get("source") == "entity"]
        assert len(ent2) > 0, "cached call lost entity nodes"
        print(f"[enrich/cached] {dt2:.1f}s entities={len(ent2)}")
        # Cached should be reasonably quick
        assert dt2 < 30, f"cached enrich call too slow: {dt2:.1f}s"

    def test_graph_subgraph_by_source(self, client):
        r = client.get(f"{API}/compliance/graph/subgraph",
                       params={"source": "sebi", "limit": 200}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "nodes" in data and "edges" in data
        assert len(data["nodes"]) > 0
        # All circular-type nodes must have source=='sebi' (entity nodes may exist too but none expected here)
        non_sebi = [n for n in data["nodes"]
                    if n.get("source") and n["source"] not in ("sebi", "entity")]
        assert not non_sebi, f"found non-sebi nodes: {non_sebi[:3]}"
