"""Semantic embedding reranker for compliance retrieval.

Sits on top of the HashingTF-IDF first-pass: takes the top-K candidates
(typically 50) and rescores them by cosine similarity in a 384-dim
sentence-transformer space.

Why local sentence-transformers and not OpenAI embeddings?
  • Emergent LLM Key proxy doesn't expose embedding models.
  • Going to OpenAI directly would need the user's own key and add a network
    hop per query.
  • `all-MiniLM-L6-v2` is 80MB on disk, ~200MB RAM resident, and encodes
    50 texts in ~200ms on CPU — perfect for a query-time reranker.

The model is loaded LAZILY on first use so the FastAPI startup probe
doesn't pay the cost. After warm, every reranker call is sub-300ms.
"""
from __future__ import annotations

import logging
import threading
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_LOCK = threading.Lock()
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_embedder():
    """Returns the singleton SentenceTransformer model. Lazy-loaded under a
    lock so concurrent first-callers don't race.

    Returns False (cached) if sentence-transformers is not installed (e.g.
    on the resource-constrained production pod where the package is omitted
    from requirements.txt). Callers must treat None/False as 'reranker
    unavailable, fall back to lexical ranking'."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            try:
                # Local import — sentence-transformers is an OPTIONAL runtime
                # dependency. On 250m CPU / 1Gi pods we don't ship it; the
                # reranker silently degrades to lex-only ordering.
                from sentence_transformers import SentenceTransformer  # noqa: WPS433
                logger.info(f"COMPLIANCE EMBED: loading {_MODEL_NAME} (first use)")
                _MODEL = SentenceTransformer(_MODEL_NAME)
                logger.info("COMPLIANCE EMBED: model ready")
            except ImportError:
                logger.info(
                    "COMPLIANCE EMBED: sentence-transformers not installed — "
                    "embedding reranker disabled, falling back to lexical ranking"
                )
                _MODEL = False  # cache the absence
            except Exception as e:
                logger.error(f"COMPLIANCE EMBED: model load failed — {e}")
                _MODEL = False
    return _MODEL


def is_available() -> bool:
    m = get_embedder()
    return m is not None and m is not False


def rerank(query: str, candidates: List[dict], top_k: int = 10,
           text_field: str = "text_chunk", weight: float = 0.6) -> List[dict]:
    """Rerank candidates by combined score:
        final_score = (1-weight) * lex_score  +  weight * semantic_cosine
    where lex_score is whatever the caller already computed (TF-IDF + boosts)
    and semantic_cosine is the embedding-space cosine similarity of the
    candidate's text against the query.

    `weight=0.6` puts most of the trust on semantic similarity but keeps the
    lexical/title/recency signals as a tiebreaker so very-recent or
    title-matching circulars don't get drowned by semantic near-misses."""
    if not candidates:
        return []
    model = get_embedder()
    if not model or model is False:
        # Embedder unavailable — return candidates unchanged (truncated)
        return candidates[:top_k]

    try:
        # Encode query + all candidate texts in one batch (parallelised internally)
        texts = [(c.get(text_field) or c.get("title", ""))[:512] for c in candidates]
        all_embs = model.encode(
            [query] + texts,
            convert_to_numpy=True,
            normalize_embeddings=True,   # so dot-product == cosine similarity
            show_progress_bar=False,
        )
        q_emb = all_embs[0]
        cand_embs = all_embs[1:]
        sem_scores = (cand_embs @ q_emb).astype(float)  # cosine since normalized

        # Find max lex_score so we can normalise — lex scores are typically
        # 0..0.3 so we scale to 0..1 for fair blending.
        lex_max = max((c.get("score", 0.0) for c in candidates), default=1.0) or 1.0

        out = []
        for c, sem in zip(candidates, sem_scores):
            lex_norm = (c.get("score", 0.0) / lex_max) if lex_max else 0.0
            blended = (1.0 - weight) * lex_norm + weight * float(sem)
            out.append({
                **c,
                "score": blended,
                "score_lex_norm": lex_norm,
                "score_semantic": float(sem),
            })
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:top_k]
    except Exception as e:
        logger.warning(f"COMPLIANCE EMBED: rerank failed ({e}) — falling back to lex order")
        return candidates[:top_k]


async def warmup_async():
    """Call from FastAPI lifespan to pre-load the model in a worker thread.
    Doesn't block startup if the model takes a few seconds to load."""
    import asyncio
    try:
        await asyncio.to_thread(get_embedder)
    except Exception as e:
        logger.warning(f"COMPLIANCE EMBED: warmup failed (non-fatal) — {e}")
