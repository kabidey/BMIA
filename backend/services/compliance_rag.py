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
        """Load all chunks for this source from MongoDB and build the index."""
        cursor = db.compliance_chunks.find({"source": self.source}, {"_id": 0})
        chunks = await cursor.to_list(length=None)
        if not chunks:
            logger.warning(f"COMPLIANCE RAG [{self.source}]: no chunks — skipping build")
            self.chunks = []
            return

        texts = [c["text_chunk"] for c in chunks]
        self.vectorizer = TfidfVectorizer(
            max_features=50000, ngram_range=(1, 2),
            stop_words="english", lowercase=True,
            min_df=2, max_df=0.95,
        )
        self.matrix = self.vectorizer.fit_transform(texts)
        self.chunks = chunks
        self.built_at = datetime.utcnow()
        logger.info(f"COMPLIANCE RAG [{self.source}]: built — {len(chunks)} chunks, vocab={len(self.vectorizer.vocabulary_)}")

    def search(self, query: str, top_k: int = 10, year_filter: Optional[int] = None) -> List[dict]:
        if not self.is_ready():
            return []
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix).flatten()
        # Get top-k indices
        top_indices = np.argsort(sims)[::-1][: top_k * 3]  # over-fetch for filtering
        results = []
        for idx in top_indices:
            if sims[idx] <= 0:
                continue
            c = self.chunks[idx]
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
