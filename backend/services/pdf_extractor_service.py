"""
PDF Extractor Service — Downloads BSE PDFs, extracts text, stores inline with guidance docs.
No persistent PDF storage — PDFs are downloaded, text extracted, then flushed.
Download links always point to bseindia.com.
"""
import io
import logging
import time
import threading
from datetime import datetime, timedelta, timezone

import requests
import pdfplumber

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
MAX_PDF_SIZE_MB = 10
PDF_DOWNLOAD_TIMEOUT = 20

BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/pdf",
    "Referer": "https://www.bseindia.com",
}


def download_and_extract_pdf(pdf_url: str) -> str:
    """Download PDF from BSE, extract text, flush PDF bytes immediately."""
    try:
        resp = requests.get(pdf_url, headers=BSE_HEADERS, timeout=PDF_DOWNLOAD_TIMEOUT, stream=True)
        resp.raise_for_status()

        content_length = int(resp.headers.get("content-length", 0))
        if content_length > MAX_PDF_SIZE_MB * 1024 * 1024:
            return ""

        pdf_bytes = resp.content
        if len(pdf_bytes) < 100:
            return ""

        text = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages[:30]:
                t = page.extract_text()
                if t:
                    pages_text.append(t.strip())
            text = "\n\n".join(pages_text)

        # PDF bytes are NOT stored — flushed after extraction
        del pdf_bytes
        return text

    except requests.exceptions.Timeout:
        return ""
    except Exception as e:
        logger.debug(f"PDF extraction failed: {e}")
        return ""


def chunk_text(text: str) -> list:
    """Split text into overlapping chunks for RAG."""
    if not text or len(text) < 50:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]

        if end < len(text):
            last_period = chunk.rfind('. ')
            last_newline = chunk.rfind('\n')
            break_at = max(last_period, last_newline)
            if break_at > CHUNK_SIZE * 0.5:
                chunk = chunk[:break_at + 1]
                end = start + break_at + 1

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - CHUNK_OVERLAP if end < len(text) else len(text)

    return chunks


async def process_unprocessed_pdfs(db, limit: int = 30):
    """Process PDFs for guidance docs that haven't been text-extracted yet.
    Stores extracted text chunks INLINE with the guidance document."""
    filings = await db.guidance.find(
        {
            "pdf_url": {"$ne": None, "$exists": True},
            "pdf_extracted": {"$ne": True},
        },
        {"_id": 0, "news_id": 1, "pdf_url": 1, "stock_symbol": 1, "headline": 1}
    ).sort("news_date", -1).limit(limit).to_list(length=limit)

    if not filings:
        return {"processed": 0, "chunks_created": 0}

    total_chunks = 0
    processed = 0

    for f in filings:
        pdf_url = f.get("pdf_url")
        news_id = f.get("news_id")
        if not pdf_url or not news_id:
            continue

        text = download_and_extract_pdf(pdf_url)
        chunks = chunk_text(text) if text else []

        # Store text chunks inline with the guidance document
        await db.guidance.update_one(
            {"news_id": news_id},
            {"$set": {
                "pdf_text_chunks": chunks,
                "pdf_text_length": len(text) if text else 0,
                "pdf_extracted": True,
                "pdf_extracted_at": datetime.now(IST).isoformat(),
            }}
        )

        if chunks:
            total_chunks += len(chunks)
            processed += 1

        time.sleep(1)  # Rate limit

    logger.info(f"PDF EXTRACTOR: Processed {processed}/{len(filings)} PDFs, {total_chunks} chunks")
    return {"processed": processed, "chunks_created": total_chunks, "total_attempted": len(filings)}


async def get_pdf_chunks_for_query(db, stock_symbols=None, categories=None, keywords=None, max_chunks=15):
    """Retrieve relevant PDF text chunks from guidance docs for RAG."""
    query = {"pdf_extracted": True, "pdf_text_chunks": {"$exists": True, "$ne": []}}

    if stock_symbols:
        query["stock_symbol"] = {"$in": stock_symbols}
    if categories:
        cat_regex = "|".join(categories)
        query["category"] = {"$regex": cat_regex, "$options": "i"}

    docs = await db.guidance.find(
        query, {"_id": 0, "stock_symbol": 1, "headline": 1, "category": 1, "news_date": 1, "pdf_url": 1, "pdf_text_chunks": 1}
    ).sort("news_date", -1).limit(max_chunks).to_list(length=max_chunks)

    results = []
    for doc in docs:
        chunks = doc.get("pdf_text_chunks", [])
        if keywords and chunks:
            scored = [(sum(1 for kw in keywords if kw.lower() in c.lower()), c) for c in chunks]
            scored.sort(reverse=True)
            best = [c for s, c in scored[:2] if s > 0]
            if not best:
                best = chunks[:1]
        else:
            best = chunks[:1]

        for chunk in best:
            results.append({
                "stock_symbol": doc.get("stock_symbol", ""),
                "headline": doc.get("headline", ""),
                "category": doc.get("category", ""),
                "news_date": doc.get("news_date", ""),
                "pdf_url": doc.get("pdf_url", ""),
                "text": chunk,
            })

    return results[:max_chunks]


async def get_pdf_extraction_stats(db):
    """Get PDF extraction stats."""
    total_with_pdf = await db.guidance.count_documents({"pdf_url": {"$ne": None, "$exists": True}})
    total_extracted = await db.guidance.count_documents({"pdf_extracted": True})
    total_with_text = await db.guidance.count_documents({"pdf_text_chunks": {"$exists": True, "$ne": []}})

    return {
        "total_filings_with_pdf": total_with_pdf,
        "pdfs_processed": total_extracted,
        "pdfs_with_text": total_with_text,
        "pdfs_pending": total_with_pdf - total_extracted,
    }


def start_pdf_extraction_daemon(mongo_url: str, db_name: str):
    """Background daemon — processes PDFs and stores text inline."""
    import asyncio as _aio
    from motor.motor_asyncio import AsyncIOMotorClient

    def _loop():
        logger.info("PDF EXTRACTION DAEMON: Started")
        time.sleep(30)

        while True:
            try:
                loop = _aio.new_event_loop()
                _aio.set_event_loop(loop)
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]

                result = loop.run_until_complete(process_unprocessed_pdfs(db, limit=20))
                if result["processed"] > 0:
                    logger.info(f"PDF DAEMON: {result['processed']} PDFs → {result['chunks_created']} chunks")

                client.close()
                loop.close()
            except Exception as e:
                logger.error(f"PDF DAEMON: Error: {e}")

            time.sleep(300)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info("PDF EXTRACTION DAEMON: Thread launched")
