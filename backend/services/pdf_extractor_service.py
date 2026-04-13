"""
PDF Extractor Service — Downloads and extracts text from BSE corporate filing PDFs.
Chunks text for RAG analysis and stores in MongoDB.
"""
import os
import io
import logging
import time
import threading
import tempfile
from datetime import datetime, timedelta, timezone

import requests
import pdfplumber

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

CHUNK_SIZE = 1200  # chars per chunk
CHUNK_OVERLAP = 200  # overlap between chunks
MAX_PDF_SIZE_MB = 10  # skip PDFs larger than this
PDF_DOWNLOAD_TIMEOUT = 20  # seconds

BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/pdf",
    "Referer": "https://www.bseindia.com",
}


def download_and_extract_pdf(pdf_url: str) -> str:
    """Download a PDF from BSE and extract text using pdfplumber."""
    try:
        resp = requests.get(pdf_url, headers=BSE_HEADERS, timeout=PDF_DOWNLOAD_TIMEOUT, stream=True)
        resp.raise_for_status()

        content_length = int(resp.headers.get("content-length", 0))
        if content_length > MAX_PDF_SIZE_MB * 1024 * 1024:
            logger.warning(f"PDF too large ({content_length/1024/1024:.1f}MB): {pdf_url}")
            return ""

        pdf_bytes = resp.content
        if len(pdf_bytes) < 100:
            return ""

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            all_text = []
            for page in pdf.pages[:30]:  # Limit to 30 pages
                text = page.extract_text()
                if text:
                    all_text.append(text.strip())
            return "\n\n".join(all_text)

    except requests.exceptions.Timeout:
        logger.debug(f"PDF download timeout: {pdf_url}")
        return ""
    except Exception as e:
        logger.debug(f"PDF extraction failed for {pdf_url}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Split text into overlapping chunks for RAG."""
    if not text or len(text) < 50:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('. ')
            last_newline = chunk.rfind('\n')
            break_at = max(last_period, last_newline)
            if break_at > chunk_size * 0.5:
                chunk = chunk[:break_at + 1]
                end = start + break_at + 1

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap if end < len(text) else len(text)

    return chunks


async def process_filing_pdf(db, filing: dict) -> int:
    """Process a single filing's PDF: download, extract, chunk, store."""
    pdf_url = filing.get("pdf_url")
    news_id = filing.get("news_id")
    if not pdf_url or not news_id:
        return 0

    # Check if already processed
    existing = await db.guidance_pdf_chunks.find_one({"news_id": news_id})
    if existing:
        return 0

    text = download_and_extract_pdf(pdf_url)
    if not text:
        # Mark as attempted but empty
        await db.guidance_pdf_chunks.update_one(
            {"news_id": news_id},
            {"$set": {
                "news_id": news_id,
                "stock_symbol": filing.get("stock_symbol", ""),
                "stock_name": filing.get("stock_name", ""),
                "category": filing.get("category", ""),
                "headline": filing.get("headline", ""),
                "pdf_url": pdf_url,
                "chunks": [],
                "full_text_length": 0,
                "processed_at": datetime.now(IST).isoformat(),
                "status": "empty",
            }},
            upsert=True,
        )
        return 0

    chunks = chunk_text(text)

    await db.guidance_pdf_chunks.update_one(
        {"news_id": news_id},
        {"$set": {
            "news_id": news_id,
            "stock_symbol": filing.get("stock_symbol", ""),
            "stock_name": filing.get("stock_name", ""),
            "category": filing.get("category", ""),
            "headline": filing.get("headline", ""),
            "news_date": filing.get("news_date", ""),
            "pdf_url": pdf_url,
            "chunks": chunks,
            "full_text_length": len(text),
            "chunk_count": len(chunks),
            "processed_at": datetime.now(IST).isoformat(),
            "status": "processed",
        }},
        upsert=True,
    )

    return len(chunks)


async def process_unprocessed_pdfs(db, limit: int = 50):
    """Process PDFs that haven't been extracted yet."""
    # Get filings with PDFs that haven't been processed
    processed_ids = set()
    cursor = db.guidance_pdf_chunks.find({}, {"news_id": 1, "_id": 0})
    async for doc in cursor:
        processed_ids.add(doc.get("news_id"))

    # Get unprocessed filings with PDFs
    filings = await db.guidance.find(
        {"pdf_url": {"$ne": None, "$exists": True}},
        {"_id": 0}
    ).sort("news_date", -1).limit(limit * 3).to_list(length=limit * 3)

    unprocessed = [f for f in filings if f.get("news_id") not in processed_ids][:limit]

    if not unprocessed:
        return {"processed": 0, "chunks_created": 0}

    total_chunks = 0
    processed_count = 0

    for filing in unprocessed:
        chunks = await process_filing_pdf(db, filing)
        total_chunks += chunks
        if chunks > 0:
            processed_count += 1
        time.sleep(1)  # Rate limit BSE downloads

    logger.info(f"PDF EXTRACTOR: Processed {processed_count} PDFs, {total_chunks} chunks created")
    return {"processed": processed_count, "chunks_created": total_chunks, "total_attempted": len(unprocessed)}


async def get_pdf_chunks_for_query(db, stock_symbols: list = None, categories: list = None,
                                    keywords: list = None, max_chunks: int = 20) -> list:
    """Retrieve relevant PDF text chunks for RAG context."""
    query = {"status": "processed", "chunk_count": {"$gt": 0}}

    if stock_symbols:
        query["stock_symbol"] = {"$in": stock_symbols}
    if categories:
        cat_regex = "|".join(categories)
        query["category"] = {"$regex": cat_regex, "$options": "i"}

    docs = await db.guidance_pdf_chunks.find(
        query, {"_id": 0}
    ).sort("news_date", -1).limit(max_chunks).to_list(length=max_chunks)

    results = []
    for doc in docs:
        chunks = doc.get("chunks", [])
        if keywords and chunks:
            # Score chunks by keyword relevance
            scored = []
            for chunk in chunks:
                score = sum(1 for kw in keywords if kw.lower() in chunk.lower())
                scored.append((score, chunk))
            scored.sort(reverse=True)
            best_chunks = [c for s, c in scored[:3] if s > 0]
            if not best_chunks:
                best_chunks = chunks[:2]
        else:
            best_chunks = chunks[:2]

        for chunk in best_chunks:
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
    """Get PDF extraction pipeline stats."""
    total_filings_with_pdf = await db.guidance.count_documents({"pdf_url": {"$ne": None, "$exists": True}})
    total_processed = await db.guidance_pdf_chunks.count_documents({})
    total_with_text = await db.guidance_pdf_chunks.count_documents({"status": "processed", "chunk_count": {"$gt": 0}})

    pipeline = [
        {"$match": {"status": "processed"}},
        {"$group": {"_id": None, "total_chunks": {"$sum": "$chunk_count"}, "total_text": {"$sum": "$full_text_length"}}}
    ]
    agg = await db.guidance_pdf_chunks.aggregate(pipeline).to_list(length=1)
    chunk_stats = agg[0] if agg else {"total_chunks": 0, "total_text": 0}

    return {
        "total_filings_with_pdf": total_filings_with_pdf,
        "pdfs_processed": total_processed,
        "pdfs_with_text": total_with_text,
        "pdfs_pending": total_filings_with_pdf - total_processed,
        "total_chunks": chunk_stats.get("total_chunks", 0),
        "total_text_chars": chunk_stats.get("total_text", 0),
    }


def start_pdf_extraction_daemon(mongo_url: str, db_name: str):
    """Background daemon that processes PDFs periodically."""
    import asyncio as _aio
    from motor.motor_asyncio import AsyncIOMotorClient

    def _daemon_loop():
        logger.info("PDF EXTRACTION DAEMON: Started")
        time.sleep(30)  # Wait for initial scrape

        while True:
            try:
                loop = _aio.new_event_loop()
                _aio.set_event_loop(loop)
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]

                result = loop.run_until_complete(process_unprocessed_pdfs(db, limit=30))
                if result["processed"] > 0:
                    logger.info(f"PDF DAEMON: {result['processed']} PDFs processed, {result['chunks_created']} chunks")

                client.close()
                loop.close()
            except Exception as e:
                logger.error(f"PDF DAEMON: Error: {e}")

            time.sleep(300)  # Run every 5 minutes

    t = threading.Thread(target=_daemon_loop, daemon=True)
    t.start()
    logger.info("PDF EXTRACTION DAEMON: Thread launched")
