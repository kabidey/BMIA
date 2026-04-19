"""
Guidance Vector Store — TF-IDF Vectorization + Cosine Similarity for RAG.

Maintains an in-memory TF-IDF index of all guidance chunks from the last 3 months.
Rebuilds automatically after each scrape or every 2 hours.
"""
import logging
import time
import threading
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

RETENTION_DAYS = 90  # 3-month rolling window


class GuidanceVectorStore:
    """In-memory TF-IDF vector store for guidance RAG retrieval."""

    def __init__(self):
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._documents: list = []  # Parallel list of doc metadata
        self._build_time: Optional[float] = None
        self._lock = threading.Lock()
        self._doc_count = 0
        logger.info("VECTOR STORE: Initialized (empty, awaiting build)")

    @property
    def is_ready(self) -> bool:
        return self._vectorizer is not None and self._tfidf_matrix is not None

    @property
    def doc_count(self) -> int:
        return self._doc_count

    @property
    def age_seconds(self) -> float:
        if self._build_time is None:
            return float("inf")
        return time.time() - self._build_time

    def _prepare_doc_text(self, doc: dict) -> str:
        """Combine all text fields of a guidance doc into a single searchable string."""
        parts = []
        if doc.get("stock_symbol"):
            parts.append(doc["stock_symbol"])
        if doc.get("stock_name"):
            parts.append(doc["stock_name"])
        if doc.get("category"):
            parts.append(doc["category"])
        if doc.get("headline"):
            parts.append(doc["headline"])
        if doc.get("more_text"):
            parts.append(doc["more_text"])
        return " ".join(parts)

    def _prepare_chunk_text(self, doc: dict, chunk: str) -> str:
        """Combine chunk text with parent doc metadata for richer context."""
        parts = []
        if doc.get("stock_symbol"):
            parts.append(doc["stock_symbol"])
        if doc.get("stock_name"):
            parts.append(doc["stock_name"])
        if doc.get("category"):
            parts.append(doc["category"])
        parts.append(chunk)
        return " ".join(parts)

    async def build(self, db):
        """Build/rebuild the TF-IDF index from MongoDB guidance collection."""
        start = time.time()
        cutoff = (datetime.now(IST) - timedelta(days=RETENTION_DAYS)).isoformat()

        try:
            # Fetch all guidance docs from last 3 months
            docs_cursor = db.guidance.find(
                {"scraped_at": {"$gte": cutoff}},
                {
                    "_id": 0, "news_id": 1, "scrip_code": 1,
                    "stock_symbol": 1, "stock_name": 1,
                    "headline": 1, "category": 1, "news_date": 1,
                    "more_text": 1, "pdf_url": 1, "critical": 1,
                    "pdf_text_chunks": 1, "scraped_at": 1,
                }
            ).sort("news_date", -1)
            raw_docs = await docs_cursor.to_list(length=100000)

            if not raw_docs:
                logger.warning("VECTOR STORE: No docs in 3-month window, index empty")
                with self._lock:
                    self._vectorizer = None
                    self._tfidf_matrix = None
                    self._documents = []
                    self._doc_count = 0
                    self._build_time = time.time()
                return

            texts = []
            metadata = []

            for doc in raw_docs:
                # Index the announcement itself (headline + more_text)
                doc_text = self._prepare_doc_text(doc)
                if doc_text.strip():
                    texts.append(doc_text)
                    metadata.append({
                        "type": "announcement",
                        "news_id": doc.get("news_id", ""),
                        "scrip_code": doc.get("scrip_code", ""),
                        "stock_symbol": doc.get("stock_symbol", ""),
                        "stock_name": doc.get("stock_name", ""),
                        "headline": doc.get("headline", ""),
                        "category": doc.get("category", ""),
                        "news_date": doc.get("news_date", ""),
                        "pdf_url": doc.get("pdf_url"),
                        "critical": doc.get("critical", False),
                        "more_text": (doc.get("more_text", "") or "")[:500],
                    })

                # Index each PDF chunk as a separate vector
                chunks = doc.get("pdf_text_chunks") or []
                for i, chunk in enumerate(chunks):
                    chunk_text = self._prepare_chunk_text(doc, chunk)
                    if chunk_text.strip():
                        texts.append(chunk_text)
                        metadata.append({
                            "type": "pdf_chunk",
                            "chunk_index": i,
                            "news_id": doc.get("news_id", ""),
                            "scrip_code": doc.get("scrip_code", ""),
                            "stock_symbol": doc.get("stock_symbol", ""),
                            "stock_name": doc.get("stock_name", ""),
                            "headline": doc.get("headline", ""),
                            "category": doc.get("category", ""),
                            "news_date": doc.get("news_date", ""),
                            "pdf_url": doc.get("pdf_url"),
                            "critical": doc.get("critical", False),
                            "text": chunk[:1200],
                        })

            if not texts:
                logger.warning("VECTOR STORE: No indexable text found")
                with self._lock:
                    self._vectorizer = None
                    self._tfidf_matrix = None
                    self._documents = []
                    self._doc_count = 0
                    self._build_time = time.time()
                return

            # Build TF-IDF matrix — fit_transform is CPU-bound and blocks the
            # event loop for tens of seconds on large corpora. Run it in a
            # worker thread so FastAPI can keep serving /api/health + other
            # requests during deploy health-probe windows.
            vectorizer = TfidfVectorizer(
                max_features=20000,
                stop_words="english",
                ngram_range=(1, 2),
                min_df=2 if len(texts) > 100 else 1,
                max_df=0.95,
                sublinear_tf=True,
            )
            import asyncio as _asyncio
            tfidf_matrix = await _asyncio.to_thread(vectorizer.fit_transform, texts)

            with self._lock:
                self._vectorizer = vectorizer
                self._tfidf_matrix = tfidf_matrix
                self._documents = metadata
                self._doc_count = len(texts)
                self._build_time = time.time()

            elapsed = time.time() - start
            logger.info(
                f"VECTOR STORE: Built index — {len(texts)} vectors "
                f"({len(raw_docs)} announcements + PDF chunks) in {elapsed:.2f}s"
            )

        except Exception as e:
            logger.error(f"VECTOR STORE: Build failed: {e}")

    def search(
        self,
        query: str,
        top_k: int = 30,
        stock_filter: list = None,
        category_filter: list = None,
        doc_type: str = None,
        min_score: float = 0.05,
    ) -> list:
        """Search the vector store using cosine similarity.

        Returns list of dicts with 'score' and all metadata fields.
        """
        with self._lock:
            if not self.is_ready:
                return []

            try:
                query_vec = self._vectorizer.transform([query])
                scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

                # Apply filters and threshold
                results = []
                for idx in np.argsort(scores)[::-1]:
                    score = float(scores[idx])
                    if score < min_score:
                        break

                    doc = self._documents[idx]

                    # Apply filters
                    if stock_filter:
                        sym = (doc.get("stock_symbol") or "").upper()
                        name = (doc.get("stock_name") or "").upper()
                        if not any(
                            sf.upper() in sym or sf.upper() in name
                            for sf in stock_filter
                        ):
                            continue

                    if category_filter:
                        cat = (doc.get("category") or "").lower()
                        if not any(cf.lower() in cat for cf in category_filter):
                            continue

                    if doc_type and doc.get("type") != doc_type:
                        continue

                    results.append({**doc, "score": round(score, 4)})
                    if len(results) >= top_k:
                        break

                return results

            except Exception as e:
                logger.error(f"VECTOR STORE: Search error: {e}")
                return []

    def get_stats(self) -> dict:
        """Return store statistics."""
        with self._lock:
            announcement_count = sum(
                1 for d in self._documents if d.get("type") == "announcement"
            )
            chunk_count = sum(
                1 for d in self._documents if d.get("type") == "pdf_chunk"
            )
            return {
                "ready": self.is_ready,
                "total_vectors": self._doc_count,
                "announcements": announcement_count,
                "pdf_chunks": chunk_count,
                "age_seconds": round(self.age_seconds, 1) if self._build_time else None,
                "last_built": (
                    datetime.fromtimestamp(self._build_time, IST).isoformat()
                    if self._build_time
                    else None
                ),
                "retention_days": RETENTION_DAYS,
            }


# Singleton instance
guidance_vector_store = GuidanceVectorStore()
