"""
Compliance RAG — three TF-IDF stores (NSE, BSE, SEBI) + meta-router.

Architecture:
  - One index per source → faster cold-start, independent refresh
  - TF-IDF vectorization (scikit-learn) — works fine for 50K+ chunks
  - Persistent caching in MongoDB: compliance_circulars + compliance_chunks
  - Query router decides which stores to hit based on filters or keyword heuristics

Chunking:
  - 800-character windows with 200-char overlap (simple, reliable)
  - Preserves circular_no + title + date in each chunk's metadata
  - No PDF stored — only extracted text chunks in Mongo
"""
import logging
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping windows."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + chunk_size, len(text))
        chunks.append(text[i:end])
        if end == len(text):
            break
        i += chunk_size - overlap
    return chunks


@dataclass
class ComplianceStore:
    """TF-IDF store for one compliance source (NSE / BSE / SEBI)."""
    source: str
    vectorizer: Optional[TfidfVectorizer] = None
    matrix: Optional[np.ndarray] = None
    chunks: List[dict] = None
    built_at: Optional[datetime] = None

    def is_ready(self) -> bool:
        return self.vectorizer is not None and self.matrix is not None and bool(self.chunks)

    async def build(self, db):
        """Load all chunks for this source from MongoDB and build the index.
        Builds into local vars first, then swaps all three attributes together
        under a lock so a concurrent search() never observes a half-initialised
        vectorizer (which would raise sklearn NotFittedError)."""
        import asyncio
        if not hasattr(self, "_swap_lock") or self._swap_lock is None:
            self._swap_lock = threading.Lock()

        cursor = db.compliance_chunks.find({"source": self.source}, {"_id": 0})
        chunks = await cursor.to_list(length=None)
        if not chunks:
            logger.warning(f"COMPLIANCE RAG [{self.source}]: no chunks — skipping build")
            with self._swap_lock:
                self.chunks = []
            return

        texts = [c["text_chunk"] for c in chunks]
        max_df = 0.95 if len(texts) >= 10 else 1.0
        new_vec = TfidfVectorizer(
            max_features=50000, ngram_range=(1, 2),
            stop_words="english", lowercase=True,
            min_df=1, max_df=max_df,
        )
        # fit_transform is CPU-bound — run in a worker thread so we don't block
        # the FastAPI event loop (critical for deploy health-probes to succeed
        # while the index is being built on startup).
        new_matrix = await asyncio.to_thread(new_vec.fit_transform, texts)

        with self._swap_lock:
            self.vectorizer = new_vec
            self.matrix = new_matrix
            self.chunks = chunks
            self.built_at = datetime.utcnow()
        logger.info(f"COMPLIANCE RAG [{self.source}]: built — {len(chunks)} chunks, vocab={len(new_vec.vocabulary_)}")

    def search(self, query: str, top_k: int = 10, year_filter: Optional[int] = None) -> List[dict]:
        # Snapshot the (vectorizer, matrix, chunks) triple under the same lock
        # used by build(), so we transform & score against a consistent view.
        lock = getattr(self, "_swap_lock", None)
        if lock is not None:
            with lock:
                vec, mat, chunks = self.vectorizer, self.matrix, self.chunks
        else:
            vec, mat, chunks = self.vectorizer, self.matrix, self.chunks
        if vec is None or mat is None or not chunks:
            return []
        try:
            q_vec = vec.transform([query])
        except Exception as e:
            logger.warning(f"COMPLIANCE RAG [{self.source}]: search transform failed ({e}) — returning empty")
            return []
        sims = cosine_similarity(q_vec, mat).flatten()
        # Get top-k indices
        top_indices = np.argsort(sims)[::-1][: top_k * 3]  # over-fetch for filtering
        results = []
        for idx in top_indices:
            if sims[idx] <= 0:
                continue
            c = chunks[idx]
            if year_filter and c.get("year") and c["year"] != year_filter:
                continue
            results.append({
                **c,
                "score": float(sims[idx]),
            })
            if len(results) >= top_k:
                break
        return results


class ComplianceRouter:
    """Multi-store router — queries one or more sources, merges + ranks results."""

    def __init__(self):
        self.stores = {
            "nse": ComplianceStore("nse"),
            "bse": ComplianceStore("bse"),
            "sebi": ComplianceStore("sebi"),
        }

    async def build_all(self, db):
        for store in self.stores.values():
            try:
                await store.build(db)
            except Exception as e:
                logger.error(f"COMPLIANCE RAG [{store.source}] build failed: {e}")

    def ready_sources(self) -> List[str]:
        return [s for s, store in self.stores.items() if store.is_ready()]

    def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        year_filter: Optional[int] = None,
        top_k: int = 10,
    ) -> List[dict]:
        """Search across selected sources and merge by score."""
        sources = sources or ["nse", "bse", "sebi"]
        merged = []
        for src in sources:
            store = self.stores.get(src.lower())
            if store and store.is_ready():
                results = store.search(query, top_k=top_k, year_filter=year_filter)
                merged.extend(results)
        # Dedupe by (source, circular_no, chunk_idx) and keep highest score
        dedupe = {}
        for r in merged:
            key = (r.get("source"), r.get("circular_no"), r.get("chunk_idx", 0))
            if key not in dedupe or r["score"] > dedupe[key]["score"]:
                dedupe[key] = r
        # Sort by score then recency
        sorted_results = sorted(
            dedupe.values(),
            key=lambda x: (x["score"], x.get("date_iso", "")),
            reverse=True,
        )
        return sorted_results[:top_k]

    def stats(self) -> dict:
        return {
            source: {
                "ready": store.is_ready(),
                "chunk_count": len(store.chunks or []),
                "built_at": store.built_at.isoformat() if store.built_at else None,
            }
            for source, store in self.stores.items()
        }


compliance_router = ComplianceRouter()
