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
import math
import os
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

CHUNK_SIZE = int(os.environ.get("COMPLIANCE_CHUNK_SIZE", "1600"))
CHUNK_OVERLAP = int(os.environ.get("COMPLIANCE_CHUNK_OVERLAP", "200"))


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
    """Hashing-TF-IDF store for one compliance source (NSE / BSE / SEBI).

    Uses HashingVectorizer + TfidfTransformer so memory is constant regardless
    of corpus size — critical because NSE alone has 490k+ chunks and a
    growing-vocab TfidfVectorizer was OOM-killing the 1GB pod during fit."""
    source: str
    vectorizer: Optional[object] = None       # the Hashing+Tfidf pipeline
    matrix: Optional[np.ndarray] = None
    chunks: List[dict] = None
    built_at: Optional[datetime] = None

    def is_ready(self) -> bool:
        return self.vectorizer is not None and self.matrix is not None and bool(self.chunks)

    async def build(self, db):
        """Load all chunks for this source from MongoDB and build the index.
        Builds into local vars first, then swaps all three attributes together
        under a lock so a concurrent search() never observes a half-initialised
        store (which would raise sklearn NotFittedError).

        Only loads chunks belonging to REGULATOR-ISSUED circulars. Company
        filings (BSE Announcements, AGM/EGM, Corp Action…) are excluded so the
        index isn't polluted with company-specific noise that drowns out
        genuine regulatory language."""
        import asyncio
        from services.compliance_filters import regulatory_categories

        if not hasattr(self, "_swap_lock") or self._swap_lock is None:
            self._swap_lock = threading.Lock()

        cats = regulatory_categories(self.source)
        query: dict = {"source": self.source}
        if cats:
            query["$or"] = [
                {"category": {"$in": cats}},
                {"category": {"$regex": "^bulk_upload"}},
            ]

        cursor = db.compliance_chunks.find(query, {"_id": 0})
        chunks = await cursor.to_list(length=None)
        if not chunks:
            logger.warning(f"COMPLIANCE RAG [{self.source}]: no regulatory chunks — skipping build")
            with self._swap_lock:
                self.chunks = []
            return

        texts = [c["text_chunk"] for c in chunks]
        # Hashing-TF-IDF pipeline:
        #  • HashingVectorizer hashes tokens directly into 2^18 = 262,144 buckets
        #    → constant memory, no growing vocab dict (the previous OOM cause).
        #  • Bigrams included; trigrams skipped to keep transform CPU low.
        #  • TfidfTransformer applies BM25-style sublinear_tf weighting on top.
        #  • Stop-words are sklearn's English list; lowercase=True; binary=False.
        n_features = 1 << 18  # 262,144
        hv = HashingVectorizer(
            n_features=n_features,
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True,
            alternate_sign=False,   # always non-negative (TF-IDF expects this)
            norm=None,              # let TfidfTransformer normalise
        )
        tfidf = TfidfTransformer(sublinear_tf=True, norm="l2")

        # Build in a worker thread so we don't block the FastAPI event loop.
        def _fit() -> tuple:
            counts = hv.transform(texts)            # streaming, memory-bounded
            tfidf.fit(counts)
            mat = tfidf.transform(counts)
            return mat, hv, tfidf

        new_matrix, hv, tfidf = await asyncio.to_thread(_fit)
        # Wrap as a tiny pipeline object exposing .transform() the same way
        # downstream code expected from TfidfVectorizer.
        class _HashingTfidfPipeline:
            def __init__(self, hv, tfidf):
                self.hv = hv
                self.tfidf = tfidf
            def transform(self, raw_docs):
                return self.tfidf.transform(self.hv.transform(raw_docs))
        new_vec = _HashingTfidfPipeline(hv, tfidf)

        with self._swap_lock:
            self.vectorizer = new_vec
            self.matrix = new_matrix
            self.chunks = chunks
            self.built_at = datetime.utcnow()
        logger.info(f"COMPLIANCE RAG [{self.source}]: built — {len(chunks)} chunks, n_features={n_features}")

    def search(self, query: str, top_k: int = 10, year_filter: Optional[int] = None,
               use_embeddings: bool = False) -> List[dict]:
        """Two-stage retrieval (per-store):
          1) HashingTF-IDF cosine similarity — fast first-pass over all chunks.
          2) Feature-engineered reranker that boosts:
             • Title-token overlap with the query.
             • Recency (4-year decay).
             • Source diversity (post-rerank within this single source).
        The semantic embedding rerank (stage 3) is NOT done here — the
        ComplianceRouter does it AFTER merging across all sources, so the
        cross-source cosine ordering is consistent.

        `use_embeddings` is kept as a back-compat flag for direct callers, but
        defaults False because the router now owns this stage."""
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

        # Stage 1 — over-fetch top-50 for the reranker (more headroom than the
        # previous top_k*3, gives the reranker something to actually rerank).
        first_pass_n = max(50, top_k * 5)
        candidate_idxs = np.argsort(sims)[::-1][:first_pass_n]

        # Pre-process query for the title boost
        q_tokens = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
        today = datetime.utcnow()

        scored: List[tuple] = []
        for idx in candidate_idxs:
            base = float(sims[idx])
            if base <= 0:
                continue
            c = chunks[idx]
            if year_filter and c.get("year") and c["year"] != year_filter:
                continue

            # ── Title-match boost ──
            title = (c.get("title") or "").lower()
            if q_tokens:
                t_tokens = set(re.findall(r"[a-z0-9]+", title))
                overlap = len(q_tokens & t_tokens) / len(q_tokens)
                title_boost = 1.0 + 0.6 * overlap  # max +60% if every query term is in title
            else:
                title_boost = 1.0

            # ── Recency boost (4-year half-life) ──
            try:
                d_iso = c.get("date_iso") or ""
                if d_iso:
                    d = datetime.fromisoformat(d_iso[:10])
                    days_old = max(0, (today - d).days)
                    recency_boost = 1.0 + 0.25 * math.exp(-days_old / 1460.0)  # 4yr decay
                else:
                    recency_boost = 1.0
            except Exception:
                recency_boost = 1.0

            final_score = base * title_boost * recency_boost
            scored.append((idx, final_score, base, title_boost, recency_boost))

        # Sort by reranked score
        scored.sort(key=lambda x: x[1], reverse=True)

        # ── Source-diversity penalty (post-rerank) ──
        # Apply at the result-set level: each consecutive hit from the same
        # source after the first 2 takes a 5% penalty per duplicate. This
        # gently dampens monoculture without hard-capping any one source.
        per_source_seen = defaultdict(int)
        diverse: List[tuple] = []
        for idx, fs, b, tb, rb in scored:
            src = chunks[idx].get("source", "")
            seen = per_source_seen[src]
            penalty = 1.0 if seen < 2 else max(0.5, 1.0 - 0.05 * (seen - 1))
            diverse.append((idx, fs * penalty, b, tb, rb, penalty))
            per_source_seen[src] += 1
        diverse.sort(key=lambda x: x[1], reverse=True)

        # Build the intermediate result objects (stage-2 ranked)
        stage2: List[dict] = []
        for idx, final_score, base, tb, rb, pen in diverse[: max(top_k, 50)]:
            c = chunks[idx]
            stage2.append({
                **c,
                "score": final_score,
                "score_base": base,
                "score_title_boost": tb,
                "score_recency_boost": rb,
                "score_diversity_penalty": pen,
            })

        # ── Stage 3: semantic embedding rerank (optional) ──
        if use_embeddings and len(stage2) > 1:
            try:
                from services.compliance_embed import rerank as embed_rerank
                stage2 = embed_rerank(query, stage2, top_k=top_k, weight=0.6)
            except Exception as e:
                logger.warning(f"COMPLIANCE RAG [{self.source}]: embed rerank skipped ({e})")
                stage2 = stage2[:top_k]
        else:
            stage2 = stage2[:top_k]
        return stage2


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
        use_embeddings: bool = True,
    ) -> List[dict]:
        """Search across selected sources, merge, then run a single
        cross-source semantic embedding rerank as the final stage. This makes
        the cosine ordering consistent — a SEBI chunk with sem=0.6 will beat
        a BSE chunk with sem=0.3 regardless of how the per-source lex scores
        were normalised."""
        sources = sources or ["nse", "bse", "sebi"]
        # Over-fetch from each source so the global rerank has real choice
        per_source_k = max(top_k * 2, 20)
        merged = []
        for src in sources:
            store = self.stores.get(src.lower())
            if store and store.is_ready():
                results = store.search(
                    query, top_k=per_source_k, year_filter=year_filter,
                    use_embeddings=False,  # rerank globally below
                )
                merged.extend(results)

        # Dedupe by (source, circular_no, chunk_idx)
        dedupe = {}
        for r in merged:
            key = (r.get("source"), r.get("circular_no"), r.get("chunk_idx", 0))
            if key not in dedupe or r["score"] > dedupe[key]["score"]:
                dedupe[key] = r
        candidates = list(dedupe.values())
        # First-pass sort by lexical+features score (stable ordering)
        candidates.sort(key=lambda x: (x.get("score", 0), x.get("date_iso", "")), reverse=True)

        if use_embeddings and len(candidates) > 1:
            try:
                from services.compliance_embed import rerank as embed_rerank
                # Pass the top 60 to the embedder (sweet spot for quality vs
                # latency). Returns the final top_k blended-and-sorted.
                return embed_rerank(query, candidates[:60], top_k=top_k, weight=0.65)
            except Exception as e:
                logger.warning(f"COMPLIANCE ROUTER: embed rerank skipped ({e})")
        return candidates[:top_k]

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
