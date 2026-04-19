"""
Compliance ingestion daemon — one background thread per source (NSE, BSE, SEBI).

Design
------
Each source runs an independent loop with two cursors:
  - `newest_date`: live cursor; on every cycle we refetch circulars
    published after this date and move it forward (incremental updates).
  - `oldest_date`: backfill cursor; while it hasn't reached the TARGET_START_YEAR,
    we fetch one older batch per cycle and move it backward.

State is persisted in MongoDB collection `compliance_ingestion_state`
(one doc per source) so progress survives restarts and is readable by the UI.

Polite pacing
-------------
  - ~3 s between HTTP requests (configurable via COMPLIANCE_REQUEST_DELAY_SEC).
  - ~10 min between cycles once backfill is done (live mode).
  - ~2 min between cycles during backfill so we cover ~10-20 years in 3-5 days
    without hammering the source.

PDF text is extracted in-memory (pdfminer.six) and the raw PDF bytes are
discarded — only chunked text is persisted in `compliance_chunks`.
"""
import io
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

# ─── Tunables ────────────────────────────────────────────────────────────────
REQUEST_DELAY_SEC = float(os.environ.get("COMPLIANCE_REQUEST_DELAY_SEC", "3.0"))
BACKFILL_CYCLE_SLEEP_SEC = int(os.environ.get("COMPLIANCE_BACKFILL_SLEEP", "120"))   # 2 min
LIVE_CYCLE_SLEEP_SEC = int(os.environ.get("COMPLIANCE_LIVE_SLEEP", "900"))           # 15 min
BATCH_SIZE = int(os.environ.get("COMPLIANCE_BATCH_SIZE", "15"))                      # items per batch call
PER_CYCLE_MAX_PDFS = int(os.environ.get("COMPLIANCE_MAX_PDFS_PER_CYCLE", "10"))      # hard cap on PDF fetches per worker cycle
PDF_READ_TIMEOUT = int(os.environ.get("COMPLIANCE_PDF_READ_TIMEOUT", "10"))          # seconds
TARGET_START_YEAR = int(os.environ.get("COMPLIANCE_TARGET_START_YEAR", "2010"))
REBUILD_AFTER_N_CHUNKS = int(os.environ.get("COMPLIANCE_REBUILD_AFTER_N_CHUNKS", "50"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, application/pdf, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ─── PDF/HTML text extraction (in-memory) ────────────────────────────────────
def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(pdf_bytes)) or ""
    except Exception as e:
        logger.debug(f"PDF extraction failed: {e}")
        return ""


def _fetch_doc_text(url: str, timeout: int = PDF_READ_TIMEOUT) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=(5, timeout))
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "").lower()
        if "pdf" in ct or url.lower().endswith(".pdf"):
            return _extract_pdf_text(r.content)
        html = r.text
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()
    except Exception as e:
        logger.debug(f"Fetch failed for {url}: {e}")
        return ""


# ─── Source-specific fetchers (date-ranged) ──────────────────────────────────
def _fetch_sebi(from_date: datetime, to_date: datetime, limit: int = BATCH_SIZE) -> List[dict]:
    """SEBI circulars listing. Paginates until date window covered."""
    url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=5&smid=0"
    try:
        r = requests.get(url, headers=HEADERS, timeout=(5, 15))
        if r.status_code != 200:
            return []
        html = r.text
        pattern = re.compile(
            r'<tr[^>]*>.*?(\d{1,2}\s+\w+,?\s+\d{4})[^<]*</td>.*?'
            r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        results: List[dict] = []
        for m in pattern.finditer(html):
            date_str, link, title = m.group(1), m.group(2), m.group(3).strip()
            dt = _parse_date(date_str)
            if not dt:
                continue
            if dt < from_date or dt > to_date:
                continue
            if not link.startswith("http"):
                link = f"https://www.sebi.gov.in{link}"
            circ_no = link.split("/")[-1].split(".")[0][:120]  # derive from URL
            results.append({
                "source": "sebi",
                "circular_no": circ_no,
                "title": re.sub(r"\s+", " ", title)[:500],
                "url": link,
                "date_str": date_str,
                "category": "General",
            })
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        logger.error(f"SEBI fetch failed: {e}")
        return []


def _fetch_nse(from_date: datetime, to_date: datetime, limit: int = BATCH_SIZE) -> List[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        # (connect, read) timeout tuple — avoids indefinite hang on DNS/TCP
        session.get("https://www.nseindia.com", timeout=(5, 10))
        time.sleep(1.0)
        api_url = (
            "https://www.nseindia.com/api/circulars"
            f"?from_date={from_date:%d-%m-%Y}&to_date={to_date:%d-%m-%Y}"
        )
        r = session.get(api_url, timeout=(5, 15))
        if r.status_code != 200:
            return []
        data = r.json()
        rows = data.get("data", data if isinstance(data, list) else [])[:limit]
        results = []
        for row in rows:
            circ_no = row.get("circNumber") or row.get("cirNumber") or ""
            title = row.get("cirSubject") or row.get("subject") or ""
            date = row.get("cirDisplayDate") or row.get("circularDate") or ""
            pdf_url = row.get("cirDetails") or row.get("attachmentFile") or ""
            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = f"https://archives.nseindia.com{pdf_url}"
            results.append({
                "source": "nse",
                "circular_no": circ_no,
                "title": title[:500],
                "url": pdf_url,
                "date_str": date,
                "category": row.get("cirDepartment") or "General",
            })
        return results
    except Exception as e:
        logger.error(f"NSE fetch failed: {e}")
        return []
    finally:
        try:
            session.close()
        except Exception:
            pass


def _fetch_bse(from_date: datetime, to_date: datetime, limit: int = BATCH_SIZE) -> List[dict]:
    try:
        api_url = (
            "https://api.bseindia.com/BseIndiaAPI/api/NoticesAndCirculars/w?"
            f"strCat=-1&strPrevDate={from_date:%Y%m%d}&strScrip=&strSearch=P"
            f"&strToDate={to_date:%Y%m%d}&strType=C"
        )
        r = requests.get(
            api_url,
            headers={**HEADERS, "Referer": "https://www.bseindia.com/"},
            timeout=(5, 15),
        )
        if r.status_code != 200:
            return []
        try:
            data = r.json()
        except ValueError:
            # BSE frequently serves HTML bot-guard pages instead of JSON from
            # cloud IPs — log at debug, not error, so it doesn't flood prod logs.
            logger.debug("BSE returned non-JSON (likely bot-guard page); skipping cycle")
            return []
        rows = data.get("Table", [])[:limit]
        results = []
        for row in rows:
            circ_no = row.get("CIRCULARNO") or row.get("NEWSID") or ""
            title = row.get("HEADLINE") or row.get("NEWSSUB") or ""
            date = row.get("CIRDATE") or row.get("NEWSDATE") or ""
            attach = row.get("ATTACHMENTNAME") or ""
            pdf_url = (
                f"https://www.bseindia.com/xml-data/corpfiling/CircAttachmentLive/{attach}"
                if attach else ""
            )
            results.append({
                "source": "bse",
                "circular_no": circ_no,
                "title": title[:500],
                "url": pdf_url,
                "date_str": date,
                "category": row.get("CATEGORYNAME") or "General",
            })
        return results
    except Exception as e:
        logger.error(f"BSE fetch failed: {e}")
        return []


FETCHERS = {"sebi": _fetch_sebi, "nse": _fetch_nse, "bse": _fetch_bse}


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%m-%Y",
                "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%d-%b-%y"):
        try:
            return datetime.strptime(date_str.strip().replace(",", ""), fmt)
        except Exception:
            continue
    return None


def _get_state(db_sync, source: str) -> dict:
    now = datetime.now(timezone.utc)
    existing = db_sync.compliance_ingestion_state.find_one({"source": source}, {"_id": 0})
    if existing:
        return existing
    doc = {
        "source": source,
        "phase": "backfill",            # "backfill" | "live"
        "target_start_year": TARGET_START_YEAR,
        "newest_date_iso": None,        # most recent circular ingested
        "oldest_date_iso": None,        # oldest circular ingested (backfill cursor)
        "total_circulars": 0,
        "total_chunks": 0,
        "cycle_count": 0,
        "last_cycle_at": None,
        "last_error": None,
        "errors_count": 0,
        "started_at": now.isoformat(),
        "last_new_ingest_at": None,
    }
    db_sync.compliance_ingestion_state.insert_one(dict(doc))
    return doc


def _save_state(db_sync, source: str, patch: dict):
    db_sync.compliance_ingestion_state.update_one(
        {"source": source}, {"$set": patch}, upsert=True
    )


def _ingest_circular(db_sync, meta: dict) -> Optional[dict]:
    """Download + extract + chunk + store one circular. Returns stored doc or None."""
    source = meta["source"]
    circ_no = meta.get("circular_no") or meta.get("url", "")[-100:]
    url = meta.get("url", "")
    if not url or not circ_no:
        return None

    # Idempotency
    if db_sync.compliance_circulars.find_one(
        {"source": source, "circular_no": circ_no}, {"_id": 1}
    ):
        return None

    text = _fetch_doc_text(url)
    if not text or len(text) < 100:
        return None

    dt = _parse_date(meta.get("date_str", ""))
    date_iso = dt.date().isoformat() if dt else ""
    year = dt.year if dt else None

    doc = {
        "source": source,
        "circular_no": circ_no,
        "title": meta.get("title", ""),
        "url": url,
        "date_iso": date_iso,
        "year": year,
        "category": meta.get("category", "General"),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "text_length": len(text),
    }
    db_sync.compliance_circulars.insert_one(dict(doc))

    from services.compliance_rag import chunk_text
    chunks = chunk_text(text)
    if chunks:
        db_sync.compliance_chunks.insert_many([
            {**doc, "chunk_idx": i, "text_chunk": c} for i, c in enumerate(chunks)
        ])
    logger.info(f"COMPLIANCE INGEST [{source}]: {circ_no} — {len(chunks)} chunks")
    return {**doc, "chunk_count": len(chunks)}


def _rebuild_store(db_sync, source: str):
    """Rebuild TF-IDF store for one source from MongoDB chunks."""
    try:
        from services.compliance_rag import compliance_router
        from sklearn.feature_extraction.text import TfidfVectorizer

        rows = list(db_sync.compliance_chunks.find({"source": source}, {"_id": 0}))
        if not rows:
            return
        store = compliance_router.stores[source]
        store.vectorizer = TfidfVectorizer(
            max_features=50000, ngram_range=(1, 2),
            stop_words="english", lowercase=True,
            min_df=1, max_df=0.95 if len(rows) >= 10 else 1.0,
        )
        store.matrix = store.vectorizer.fit_transform([r["text_chunk"] for r in rows])
        store.chunks = rows
        store.built_at = datetime.utcnow()
        logger.info(f"COMPLIANCE RAG [{source}]: rebuilt ({len(rows)} chunks)")
    except Exception as e:
        logger.error(f"COMPLIANCE RAG [{source}] rebuild failed: {e}")


# ─── Per-source worker ───────────────────────────────────────────────────────
def _source_worker(mongo_url: str, db_name: str, source: str):
    import pymongo
    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]
    logger.info(f"COMPLIANCE WORKER [{source}]: started")
    fetcher = FETCHERS[source]

    while True:
        try:
            state = _get_state(db, source)
            now = datetime.now(timezone.utc)
            new_since_rebuild = 0
            total_new = 0

            # ─ 1. Live catch-up: fetch last 30 days (always) ─
            live_from = (
                _parse_date(state["newest_date_iso"]) or (now - timedelta(days=30))
            )
            live_to = now.replace(tzinfo=None)
            live_batch_size = 0
            pdfs_fetched = 0
            try:
                live_batch = fetcher(live_from, live_to)
                live_batch_size = len(live_batch)
                for meta in live_batch:
                    if pdfs_fetched >= PER_CYCLE_MAX_PDFS:
                        break
                    stored = _ingest_circular(db, meta)
                    pdfs_fetched += 1
                    if stored:
                        total_new += 1
                        new_since_rebuild += 1
                        d = stored.get("date_iso")
                        if d and (not state.get("newest_date_iso") or d > state["newest_date_iso"]):
                            state["newest_date_iso"] = d
                    time.sleep(REQUEST_DELAY_SEC)
            except Exception as e:
                state["last_error"] = f"live: {e}"
                state["errors_count"] = state.get("errors_count", 0) + 1

            # ─ 2. Backfill step: fetch one batch older than oldest_date ─
            if state["phase"] == "backfill":
                oldest = _parse_date(state["oldest_date_iso"]) or now.replace(tzinfo=None)
                back_to = oldest - timedelta(days=1)
                back_from = back_to - timedelta(days=365)
                if back_from.year < state["target_start_year"]:
                    back_from = datetime(state["target_start_year"], 1, 1)
                try:
                    back_batch = fetcher(back_from, back_to)
                    for meta in back_batch:
                        if pdfs_fetched >= PER_CYCLE_MAX_PDFS:
                            break
                        stored = _ingest_circular(db, meta)
                        pdfs_fetched += 1
                        if stored:
                            total_new += 1
                            new_since_rebuild += 1
                            d = stored.get("date_iso")
                            if d and (not state.get("oldest_date_iso") or d < state["oldest_date_iso"]):
                                state["oldest_date_iso"] = d
                        time.sleep(REQUEST_DELAY_SEC)

                    # Only advance cursor when we ingested items. If the batch
                    # was empty it likely means the source blocked us or didn't
                    # return historical data via this endpoint — retry next cycle
                    # rather than fake progress. The UI's progress % is computed
                    # from actual ingested data, so "stuck" is visible truthfully.

                    # Transition to live mode if we've collected enough history.
                    if state.get("oldest_date_iso") and state["oldest_date_iso"] <= f"{state['target_start_year']}-01-01":
                        state["phase"] = "live"
                        logger.info(f"COMPLIANCE WORKER [{source}]: backfill COMPLETE → live mode")
                except Exception as e:
                    state["last_error"] = f"backfill: {e}"
                    state["errors_count"] = state.get("errors_count", 0) + 1

            # ─ Update state totals ─
            state["total_circulars"] = db.compliance_circulars.count_documents({"source": source})
            state["total_chunks"] = db.compliance_chunks.count_documents({"source": source})
            state["cycle_count"] = state.get("cycle_count", 0) + 1
            state["last_cycle_at"] = now.isoformat()
            if total_new > 0:
                state["last_new_ingest_at"] = now.isoformat()

            # ─ Observability: mark silent no-ops as errors so UI shows them ─
            # A cycle with zero ingests AND zero fetched items is almost always
            # the source blocking/rate-limiting us. Surface it in the UI.
            if total_new == 0 and live_batch_size == 0:
                state["errors_count"] = state.get("errors_count", 0) + 1
                state["last_error"] = (
                    state.get("last_error")
                    or f"no_data: fetcher returned 0 items for {source} "
                       f"(likely blocked/rate-limited upstream)"
                )
            elif total_new > 0:
                # Clear stale error once we start getting data again
                state["last_error"] = None

            _save_state(db, source, state)

            # ─ Rebuild TF-IDF if enough new chunks ─
            if new_since_rebuild >= REBUILD_AFTER_N_CHUNKS or (total_new > 0 and state["cycle_count"] <= 2):
                _rebuild_store(db, source)

            # ─ Sleep ─
            sleep_for = BACKFILL_CYCLE_SLEEP_SEC if state["phase"] == "backfill" else LIVE_CYCLE_SLEEP_SEC
            logger.info(
                f"COMPLIANCE WORKER [{source}]: cycle done phase={state['phase']} "
                f"new={total_new} total={state['total_circulars']} "
                f"oldest={state.get('oldest_date_iso')} newest={state.get('newest_date_iso')} "
                f"sleep={sleep_for}s"
            )
            time.sleep(sleep_for)
        except Exception as e:
            logger.error(f"COMPLIANCE WORKER [{source}] fatal in cycle: {e}")
            time.sleep(60)


def start_compliance_daemon(mongo_url: str, db_name: str):
    """Spawn one background thread per source."""
    for source in FETCHERS.keys():
        t = threading.Thread(
            target=_source_worker, args=(mongo_url, db_name, source),
            daemon=True, name=f"compliance-worker-{source}",
        )
        t.start()
    logger.info("COMPLIANCE DAEMON: 3 source workers launched (sebi, nse, bse)")


# ─── Legacy helper used by /ingest-now route ─────────────────────────────────
def _run_cycle(db_sync):
    """Fires one quick live-only fetch across all sources (used by manual trigger)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    from_date = now - timedelta(days=30)
    total_new = 0
    for source, fetcher in FETCHERS.items():
        try:
            for meta in fetcher(from_date, now):
                if _ingest_circular(db_sync, meta):
                    total_new += 1
                time.sleep(REQUEST_DELAY_SEC)
            _rebuild_store(db_sync, source)
        except Exception as e:
            logger.error(f"COMPLIANCE manual ingest [{source}] failed: {e}")
    return total_new
