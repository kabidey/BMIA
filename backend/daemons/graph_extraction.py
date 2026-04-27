"""Compliance Graph Extraction Daemon — precomputes LLM entity/relation
extractions for every circular so the GraphRAG 3D viewer opens instantly
without on-demand LLM calls.

Design (mirrors the compliance_ingestion daemon pattern):
  • Single background thread started from server.py lifespan
  • Each cycle:
      1. Query compliance_circulars for N docs that don't yet have an entry
         in compliance_graph_entities (missing = un-extracted)
      2. Extract entities in parallel via asyncio.gather
      3. Persist results in compliance_graph_entities (idempotent upsert)
      4. Update compliance_graph_extraction_state progress
      5. Sleep COMPLIANCE_GRAPH_EXTRACTION_DELAY_SEC before next cycle
  • Budget-aware: tunable batch size + delay; gracefully no-ops if
    EMERGENT_LLM_KEY is missing or budget is exhausted
  • Safe to restart — picks up wherever it left off by reading
    compliance_graph_entities.circular_id as the resume cursor
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import List

import pymongo

logger = logging.getLogger(__name__)

# ─── Tunables ────────────────────────────────────────────────────────────
BATCH_SIZE = int(os.environ.get("COMPLIANCE_GRAPH_EXTRACTION_BATCH_SIZE", "4"))
DELAY_SEC = int(os.environ.get("COMPLIANCE_GRAPH_EXTRACTION_DELAY_SEC", "20"))
MAX_CHUNKS_PER_CIRC = int(os.environ.get("COMPLIANCE_GRAPH_EXTRACTION_MAX_CHUNKS", "6"))
EMPTY_IDLE_SEC = int(os.environ.get("COMPLIANCE_GRAPH_EXTRACTION_IDLE_SEC", "300"))  # 5 min when caught up

_STATE_KEY = "graph_extraction"
_STATE_COLL = "compliance_graph_extraction_state"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _patch_state(db, **fields):
    db[_STATE_COLL].update_one(
        {"_id": _STATE_KEY},
        {"$set": {**fields, "updated_at": _now()}},
        upsert=True,
    )


def _find_pending(db, limit: int) -> List[dict]:
    """Find regulator-issued circulars that don't yet have an entry in
    compliance_graph_entities. Company filings (BSE corporate announcements,
    AGM/EGM, Corp Action) are skipped — extracting entities from them would
    burn LLM budget on noise."""
    from services.compliance_filters import regulatory_categories

    # Build the set of already-extracted IDs (fast single distinct query)
    done_ids = set(db.compliance_graph_entities.distinct("circular_id"))
    pending: List[dict] = []
    # Sort newest-first so recent circulars get their entities extracted before
    # older history — matches how users tend to query.
    or_clauses = []
    for src in ("nse", "bse", "sebi"):
        cats = regulatory_categories(src)
        if cats:
            or_clauses.append({"source": src, "category": {"$in": cats}})
    or_clauses.append({"category": {"$regex": "^bulk_upload"}})
    cursor = (
        db.compliance_circulars
        .find({"$or": or_clauses}, {"_id": 0, "source": 1, "circular_no": 1, "title": 1})
        .sort("date_iso", -1)
    )
    for doc in cursor:
        cid = f"{doc['source']}:{doc.get('circular_no', '')}"
        if cid in done_ids:
            continue
        pending.append({**doc, "circular_id": cid})
        if len(pending) >= limit:
            break
    return pending


async def _extract_one(db, api_key: str, circ: dict):
    """Extract entities for a single circular and upsert into the cache."""
    from services.compliance_graph import extract_entities_llm

    src = circ["source"]
    circ_no = circ["circular_no"]
    circular_id = circ["circular_id"]

    # Double-check not already done (race with concurrent query-time enrichment)
    if db.compliance_graph_entities.find_one({"circular_id": circular_id}, {"_id": 1}):
        return {"circular_id": circular_id, "status": "already_cached"}

    chunks = list(db.compliance_chunks.find(
        {"source": src, "circular_no": circ_no},
        {"_id": 0, "text_chunk": 1},
    ).limit(MAX_CHUNKS_PER_CIRC))
    if not chunks:
        # No chunks — mark as extracted-with-nothing to avoid re-visiting
        db.compliance_graph_entities.update_one(
            {"circular_id": circular_id},
            {"$set": {
                "circular_id": circular_id,
                "entities": [],
                "relations": [],
                "extracted_at": _now(),
                "note": "no_chunks",
            }},
            upsert=True,
        )
        return {"circular_id": circular_id, "status": "no_chunks"}

    full_text = (circ.get("title") or "") + "\n\n" + "\n".join(
        c.get("text_chunk", "") for c in chunks
    )
    try:
        extracted = await extract_entities_llm(full_text, circ_no, api_key)
        db.compliance_graph_entities.update_one(
            {"circular_id": circular_id},
            {"$set": {
                "circular_id": circular_id,
                "entities": extracted["entities"],
                "relations": extracted["relations"],
                "extracted_at": _now(),
                "source": "background_daemon",
            }},
            upsert=True,
        )
        return {"circular_id": circular_id, "status": "ok",
                "n_entities": len(extracted["entities"]),
                "n_relations": len(extracted["relations"])}
    except Exception as e:
        return {"circular_id": circular_id, "status": "error", "error": str(e)[:200]}


async def _run_cycle_async(db, api_key: str) -> dict:
    pending = _find_pending(db, BATCH_SIZE)
    if not pending:
        return {"processed": 0, "pending": 0, "idle": True}

    results = await asyncio.gather(
        *[_extract_one(db, api_key, c) for c in pending],
        return_exceptions=True,
    )

    ok = err = skipped = 0
    for r in results:
        if isinstance(r, Exception):
            err += 1
            continue
        if r.get("status") == "ok":
            ok += 1
        elif r.get("status") == "error":
            err += 1
        else:
            skipped += 1

    return {"processed": len(results), "ok": ok, "err": err, "skipped": skipped,
            "idle": False}


def _worker_loop(mongo_url: str, db_name: str):
    logger.info("COMPLIANCE GRAPH EXTRACTION DAEMON: Started — batch=%d delay=%ds",
                BATCH_SIZE, DELAY_SEC)
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("COMPLIANCE GRAPH EXTRACTION DAEMON: EMERGENT_LLM_KEY missing — daemon idle")
        return

    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]
    _patch_state(db, phase="running", started_at=_now(),
                 batch_size=BATCH_SIZE, delay_sec=DELAY_SEC,
                 cycle_count=0, total_extracted=0, total_errors=0,
                 last_error=None)

    cycle = 0
    total_extracted = 0
    total_errors = 0
    while True:
        cycle += 1
        cycle_start = time.time()
        try:
            res = asyncio.run(_run_cycle_async(db, api_key))
            total_extracted += res.get("ok", 0)
            total_errors += res.get("err", 0)
            pending_count = db.compliance_circulars.estimated_document_count() - \
                db.compliance_graph_entities.estimated_document_count()
            _patch_state(
                db,
                phase="idle" if res.get("idle") else "running",
                cycle_count=cycle,
                last_cycle_at=_now(),
                last_cycle_duration_sec=round(time.time() - cycle_start, 1),
                last_cycle_result=res,
                total_extracted=total_extracted,
                total_errors=total_errors,
                approx_pending=max(0, pending_count),
            )
            if res.get("idle"):
                # Nothing to do right now — sleep longer to avoid burning DB.
                # New circulars will show up after the next ingestion cycle.
                time.sleep(EMPTY_IDLE_SEC)
                continue
        except Exception as e:
            total_errors += 1
            _patch_state(db, phase="error", last_error=str(e)[:300],
                         last_cycle_at=_now(), total_errors=total_errors)
            logger.error(f"COMPLIANCE GRAPH EXTRACTION DAEMON: cycle {cycle} crashed: {e}")

        time.sleep(DELAY_SEC)


_DAEMON_THREAD: threading.Thread | None = None
_DAEMON_LOCK = threading.Lock()


def start_graph_extraction_daemon(mongo_url: str, db_name: str) -> threading.Thread:
    """Idempotent — returns the existing worker thread if one is already alive,
    so repeated API calls to /graph/start-extraction don't leak threads."""
    global _DAEMON_THREAD
    with _DAEMON_LOCK:
        if _DAEMON_THREAD is not None and _DAEMON_THREAD.is_alive():
            logger.info("COMPLIANCE GRAPH EXTRACTION DAEMON: already running — reusing thread")
            return _DAEMON_THREAD
        _DAEMON_THREAD = threading.Thread(
            target=_worker_loop, args=(mongo_url, db_name),
            daemon=True, name="compliance-graph-extraction",
        )
        _DAEMON_THREAD.start()
        logger.info("COMPLIANCE GRAPH EXTRACTION DAEMON: Thread launched")
        return _DAEMON_THREAD
