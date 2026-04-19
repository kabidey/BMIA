"""
Compliance ingestion daemon — crawls NSE, BSE, SEBI circulars, extracts text,
chunks + stores in MongoDB (no persistent PDF storage).

Ingestion sources (public endpoints):
  - SEBI: https://www.sebi.gov.in/sebi_data/attachdocs (direct PDF links from listing)
    Listing: https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=5&smid=0
  - NSE: https://www.nseindia.com/api/circulars (JSON API)
  - BSE: https://api.bseindia.com/BseIndiaAPI/api/NoticesAndCirculars/w

Strategy:
  - Slow, respectful crawling (~1 request per 2 seconds)
  - Most-recent-first; backfill year-by-year
  - Idempotent: skip circulars whose (source, circular_no) is already in Mongo
  - Run as background thread — does not block server startup

NOTE: This is a best-effort crawler. NSE/BSE/SEBI websites change APIs
frequently and occasionally return anti-bot pages. If a fetch fails,
we log and continue — next cycle retries.
"""
import asyncio
import io
import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

# Polite delay between requests
REQUEST_DELAY_SEC = 2.0
MAX_CIRCULARS_PER_CYCLE = 25  # per source

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, application/pdf, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ─── PDF text extraction (in-memory, no disk) ────────────────────────────────
def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfminer.six. No file written."""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(pdf_bytes)) or ""
    except Exception as e:
        logger.debug(f"PDF extraction failed: {e}")
        return ""


def _fetch_pdf_text(url: str, timeout: int = 30) -> str:
    """Download PDF, extract text, discard bytes."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "").lower()
        if "pdf" in ct or url.lower().endswith(".pdf"):
            return _extract_pdf_text(r.content)
        # HTML fallback: strip tags
        html = r.text
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()
    except Exception as e:
        logger.debug(f"Fetch failed for {url}: {e}")
        return ""


# ─── Source-specific listing fetchers ────────────────────────────────────────
def _fetch_sebi_circulars(limit: int = MAX_CIRCULARS_PER_CYCLE) -> List[dict]:
    """Fetch most-recent SEBI circulars via HTML listing page."""
    url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=5&smid=0"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        html = r.text
        # Extract circular rows: date | title | link
        pattern = re.compile(
            r'<tr[^>]*>.*?(\d{1,2}\s+\w+,?\s+\d{4})[^<]*</td>.*?'
            r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        results = []
        for m in list(pattern.finditer(html))[:limit]:
            date_str, link, title = m.group(1), m.group(2), m.group(3).strip()
            if not link.startswith("http"):
                link = f"https://www.sebi.gov.in{link}"
            results.append({
                "source": "sebi",
                "title": re.sub(r"\s+", " ", title)[:500],
                "url": link,
                "date_str": date_str,
            })
        return results
    except Exception as e:
        logger.error(f"SEBI fetch failed: {e}")
        return []


def _fetch_nse_circulars(limit: int = MAX_CIRCULARS_PER_CYCLE) -> List[dict]:
    """Fetch most-recent NSE circulars via JSON API."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        # Warm-up: get cookies from main page
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(1.0)
        api_url = "https://www.nseindia.com/api/circulars?type=circulars"
        r = session.get(api_url, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
        rows = data.get("data", [])[:limit]
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


def _fetch_bse_circulars(limit: int = MAX_CIRCULARS_PER_CYCLE) -> List[dict]:
    """Fetch most-recent BSE circulars via JSON API."""
    try:
        today = datetime.now()
        api_url = (
            "https://api.bseindia.com/BseIndiaAPI/api/NoticesAndCirculars/w?"
            f"strCat=-1&strPrevDate=&strScrip=&strSearch=P&strToDate={today:%Y%m%d}&strType=C"
        )
        r = requests.get(api_url, headers={**HEADERS, "Referer": "https://www.bseindia.com/"}, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
        rows = data.get("Table", [])[:limit]
        results = []
        for row in rows:
            circ_no = row.get("CIRCULARNO") or row.get("NEWSID") or ""
            title = row.get("HEADLINE") or row.get("NEWSSUB") or ""
            date = row.get("CIRDATE") or row.get("NEWSDATE") or ""
            attach = row.get("ATTACHMENTNAME") or ""
            pdf_url = f"https://www.bseindia.com/xml-data/corpfiling/CircAttachmentLive/{attach}" if attach else ""
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


# ─── Parsing helpers ─────────────────────────────────────────────────────────
def _parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(date_str.strip().replace(",", ""), fmt)
        except Exception:
            continue
    return None


# ─── Ingestion worker ────────────────────────────────────────────────────────
def _ingest_one(db_sync, meta: dict) -> bool:
    """Download + extract + chunk + store one circular. Returns True if stored."""
    source = meta["source"]
    circ_no = meta.get("circular_no") or meta.get("url", "")[-100:]
    title = meta.get("title", "")
    url = meta.get("url", "")

    # Skip if already ingested
    if db_sync.compliance_circulars.find_one({"source": source, "circular_no": circ_no}):
        return False

    if not url:
        return False

    text = _fetch_pdf_text(url)
    if not text or len(text) < 100:
        return False

    dt = _parse_date(meta.get("date_str", ""))
    date_iso = dt.date().isoformat() if dt else ""
    year = dt.year if dt else None

    # Insert circular master record
    doc = {
        "source": source,
        "circular_no": circ_no,
        "title": title,
        "url": url,
        "date_iso": date_iso,
        "year": year,
        "category": meta.get("category", "General"),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "text_length": len(text),
    }
    db_sync.compliance_circulars.insert_one(doc)

    # Chunk + vectorize-ready rows
    from services.compliance_rag import chunk_text
    chunks = chunk_text(text)
    chunk_docs = []
    for i, c in enumerate(chunks):
        chunk_docs.append({
            "source": source,
            "circular_no": circ_no,
            "title": title,
            "url": url,
            "date_iso": date_iso,
            "year": year,
            "category": meta.get("category", "General"),
            "chunk_idx": i,
            "text_chunk": c,
        })
    if chunk_docs:
        db_sync.compliance_chunks.insert_many(chunk_docs)

    logger.info(f"COMPLIANCE INGEST [{source}]: {circ_no} — {len(chunks)} chunks")
    return True


def _run_cycle(db_sync):
    """One ingestion cycle over all 3 sources."""
    fetchers = {"sebi": _fetch_sebi_circulars, "nse": _fetch_nse_circulars, "bse": _fetch_bse_circulars}
    total_new = 0
    for source, fetcher in fetchers.items():
        try:
            circulars = fetcher()
            for meta in circulars:
                try:
                    if _ingest_one(db_sync, meta):
                        total_new += 1
                except Exception as e:
                    logger.debug(f"COMPLIANCE INGEST [{source}] item failed: {e}")
                time.sleep(REQUEST_DELAY_SEC)
        except Exception as e:
            logger.error(f"COMPLIANCE INGEST [{source}] cycle failed: {e}")

    if total_new > 0:
        logger.info(f"COMPLIANCE INGEST: cycle done — {total_new} new circulars indexed")
        # Trigger vector store rebuild
        try:
            from services.compliance_rag import compliance_router
            import asyncio
            # Build using sync DB-compatible calls: iterate sync cursor
            for store in compliance_router.stores.values():
                rows = list(db_sync.compliance_chunks.find({"source": store.source}, {"_id": 0}))
                if not rows:
                    continue
                from sklearn.feature_extraction.text import TfidfVectorizer
                store.vectorizer = TfidfVectorizer(
                    max_features=50000, ngram_range=(1, 2),
                    stop_words="english", lowercase=True,
                    min_df=1, max_df=0.95 if len(rows) >= 10 else 1.0,
                )
                store.matrix = store.vectorizer.fit_transform([r["text_chunk"] for r in rows])
                store.chunks = rows
                store.built_at = datetime.utcnow()
            logger.info("COMPLIANCE RAG: rebuilt all stores post-ingest")
        except Exception as e:
            logger.error(f"COMPLIANCE RAG rebuild failed: {e}")

    return total_new


def _daemon_loop(mongo_url, db_name, interval_sec=900):
    """Background loop — runs forever, ingests at `interval_sec` cadence."""
    import pymongo
    client = pymongo.MongoClient(mongo_url)
    db = client[db_name]
    logger.info(f"COMPLIANCE DAEMON: started (interval={interval_sec}s)")
    while True:
        try:
            _run_cycle(db)
        except Exception as e:
            logger.error(f"COMPLIANCE DAEMON cycle error: {e}")
        time.sleep(interval_sec)


def start_compliance_daemon(mongo_url: str, db_name: str):
    """Spawn the ingestion daemon in a background thread."""
    t = threading.Thread(
        target=_daemon_loop, args=(mongo_url, db_name), daemon=True, name="compliance-daemon"
    )
    t.start()
    logger.info("COMPLIANCE DAEMON: thread launched")
