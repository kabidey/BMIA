"""Compliance Re-Chunking Daemon — consolidates over-granular chunks into
larger semantic units to halve the row count and improve retrieval quality.

Background:
  • Older ingests used CHUNK_SIZE=800 / OVERLAP=200 → stride 600 chars.
    A 100k-char NSE circular produced ~167 chunks. Across 1,773 NSE circulars
    we accumulated 492k chunks (avg 277/circular). Embeddings, TF-IDF
    fit_transform and cosine-similarity all scale with chunk count.
  • New default is CHUNK_SIZE=1600 / OVERLAP=200 → stride 1400 → ~71 chunks per
    100k-char doc. ~58% reduction in chunk count, larger semantic windows
    that contain whole sections (better for compliance language matching).

This daemon walks every (source, circular_no) group, reconstructs the original
text by stitching chunks together with overlap-dedupe, then re-splits using
the new params and replaces the rows. Idempotent: skips circulars whose
chunk_count is already ≤ expected_count_for_NEW_size.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Iterable, List

import pymongo

logger = logging.getLogger(__name__)

# Tunables (env)
RECHUNK_BATCH = int(os.environ.get("COMPLIANCE_RECHUNK_BATCH", "20"))
RECHUNK_DELAY_SEC = int(os.environ.get("COMPLIANCE_RECHUNK_DELAY_SEC", "2"))
RECHUNK_IDLE_SEC = int(os.environ.get("COMPLIANCE_RECHUNK_IDLE_SEC", "1800"))  # 30 min
_STATE_KEY = "rechunk"
_STATE_COLL = "compliance_rechunk_state"

_DAEMON_THREAD: threading.Thread | None = None
_DAEMON_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _patch_state(db, **fields):
    db[_STATE_COLL].update_one(
        {"_id": _STATE_KEY},
        {"$set": {**fields, "updated_at": _now()}},
        upsert=True,
    )


def _stitch_text(chunks_in_order: List[dict], overlap: int = 200) -> str:
    """Reconstruct full circular text from its existing chunks. Adjacent
    chunks have an `overlap`-char overlap; trim it from chunk[i+1] to avoid
    duplicating the prefix. Falls back to concat-with-newline if the
    overlap doesn't actually match (which can happen because the original
    chunker breaks at sentence boundaries)."""
    if not chunks_in_order:
        return ""
    out = chunks_in_order[0].get("text_chunk", "")
    for c in chunks_in_order[1:]:
        nxt = c.get("text_chunk", "")
        if not nxt:
            continue
        # Try to detect overlap: does the tail of `out` match the head of `nxt`?
        max_check = min(overlap + 50, len(out), len(nxt))
        match = 0
        for k in range(max_check, 20, -1):  # try long matches first
            if out[-k:] == nxt[:k]:
                match = k
                break
        if match:
            out += nxt[match:]
        else:
            out += "\n" + nxt
    return out


def _rechunk_one(db, source: str, circular_no: str) -> dict:
    """Re-chunk a single circular's chunks. Idempotent — if the new chunk
    count would equal/exceed the existing count, we skip writing."""
    from services.compliance_rag import CHUNK_SIZE, CHUNK_OVERLAP, chunk_text

    rows = list(db.compliance_chunks.find(
        {"source": source, "circular_no": circular_no},
        {"_id": 0},
    ).sort("chunk_idx", 1))
    if len(rows) <= 1:
        return {"status": "skip_too_small", "n": len(rows)}

    text = _stitch_text(rows, overlap=CHUNK_OVERLAP)
    if len(text) < 200:
        return {"status": "skip_tiny", "n": len(rows)}

    new_chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if len(new_chunks) >= len(rows):
        # Already at-or-better granularity; nothing to do.
        return {"status": "skip_no_improvement", "old": len(rows), "new": len(new_chunks)}

    template = rows[0]
    common = {k: template.get(k) for k in (
        "source", "circular_no", "title", "url", "category",
        "year", "date_iso", "ingested_at",
    ) if k in template}

    new_docs = []
    for i, ch in enumerate(new_chunks):
        new_docs.append({
            **common,
            "chunk_idx": i,
            "text_chunk": ch,
            "rechunked_at": _now(),
        })

    # Replace atomically (delete then insert). Brief inconsistency window
    # accepted — search still degrades gracefully.
    db.compliance_chunks.delete_many({"source": source, "circular_no": circular_no})
    if new_docs:
        db.compliance_chunks.insert_many(new_docs)

    return {"status": "ok", "old": len(rows), "new": len(new_chunks)}


def _find_pending(db, limit: int) -> Iterable[dict]:
    """Find (source, circular_no) groups with > expected chunks for the NEW
    chunk size. Uses an aggregation to count chunks per circular."""
    from services.compliance_rag import CHUNK_SIZE, CHUNK_OVERLAP

    # Threshold: a circular with > THRESH chunks is "over-granular" relative
    # to the new chunk size. THRESH is tuned conservatively at 30 — anything
    # above that probably came from the old (CHUNK_SIZE=800) pipeline.
    threshold = max(30, int(CHUNK_SIZE / max(1, CHUNK_SIZE - CHUNK_OVERLAP)) * 2)

    pipeline = [
        # Skip already-rechunked groups
        {"$match": {"rechunked_at": {"$exists": False}}},
        {"$group": {
            "_id": {"source": "$source", "circular_no": "$circular_no"},
            "n": {"$sum": 1},
        }},
        {"$match": {"n": {"$gt": threshold}}},
        {"$sort": {"n": -1}},   # tackle biggest offenders first
        {"$limit": limit},
    ]
    for r in db.compliance_chunks.aggregate(pipeline, allowDiskUse=True):
        yield {
            "source": r["_id"]["source"],
            "circular_no": r["_id"]["circular_no"],
            "current_chunks": r["n"],
        }


def _run_cycle(db) -> dict:
    pending = list(_find_pending(db, RECHUNK_BATCH))
    if not pending:
        return {"processed": 0, "idle": True}

    ok = err = skipped = old_total = new_total = 0
    for p in pending:
        try:
            res = _rechunk_one(db, p["source"], p["circular_no"])
            if res.get("status") == "ok":
                ok += 1
                old_total += res.get("old", 0)
                new_total += res.get("new", 0)
            else:
                skipped += 1
        except Exception as e:
            err += 1
            logger.warning(f"COMPLIANCE RECHUNK: {p['source']}:{p['circular_no']} failed: {e}")
    return {
        "processed": len(pending),
        "ok": ok,
        "err": err,
        "skipped": skipped,
        "old_total": old_total,
        "new_total": new_total,
        "idle": False,
    }


def _worker_loop(mongo_url: str, db_name: str):
    logger.info(f"COMPLIANCE RECHUNK DAEMON: started — batch={RECHUNK_BATCH}")
    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]
    _patch_state(db, phase="running", started_at=_now(),
                 cycle_count=0, total_old=0, total_new=0)
    cycle = 0
    total_old = 0
    total_new = 0
    while True:
        cycle += 1
        cycle_start = time.time()
        try:
            res = _run_cycle(db)
            total_old += res.get("old_total", 0)
            total_new += res.get("new_total", 0)
            chunks_now = db.compliance_chunks.estimated_document_count()
            _patch_state(
                db,
                phase="idle" if res.get("idle") else "running",
                cycle_count=cycle,
                last_cycle_at=_now(),
                last_cycle_duration_sec=round(time.time() - cycle_start, 1),
                last_cycle_result=res,
                total_old=total_old, total_new=total_new,
                chunks_total=chunks_now,
            )
            if res.get("idle"):
                time.sleep(RECHUNK_IDLE_SEC)
                continue
        except Exception as e:
            _patch_state(db, phase="error", last_error=str(e)[:300])
            logger.error(f"COMPLIANCE RECHUNK: cycle {cycle} crashed: {e}")
        time.sleep(RECHUNK_DELAY_SEC)


def start_rechunk_daemon(mongo_url: str, db_name: str) -> threading.Thread:
    global _DAEMON_THREAD
    with _DAEMON_LOCK:
        if _DAEMON_THREAD is not None and _DAEMON_THREAD.is_alive():
            logger.info("COMPLIANCE RECHUNK DAEMON: already running — reusing thread")
            return _DAEMON_THREAD
        _DAEMON_THREAD = threading.Thread(
            target=_worker_loop, args=(mongo_url, db_name),
            daemon=True, name="compliance-rechunk",
        )
        _DAEMON_THREAD.start()
        logger.info("COMPLIANCE RECHUNK DAEMON: thread launched")
        return _DAEMON_THREAD
