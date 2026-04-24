"""Compliance query router — classifies a user question into one of:
  - "narrow"     → flat RAG (cheap, fast, exact-quote answers)
  - "multihop"   → GraphRAG local (entity/relation expansion over citations)
  - "thematic"   → GraphRAG local with deeper enrichment (community summaries
                   would live here once built; for now we fall back to local
                   GraphRAG with higher top_k).

Uses Claude Sonnet 4.5 for the classifier. Adds ~0.5-1s latency per query,
saves 30-60s on questions that don't need the graph.
"""
import json
import logging
import os
import re
from typing import Literal

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

Mode = Literal["narrow", "multihop", "thematic"]

CLASSIFIER_SYSTEM = """You classify Indian capital-markets compliance research questions into ONE of three modes:

1. "narrow"    — A single factual lookup about one specific rule, circular, or disclosure. Expected answer is a direct quote from one or two circulars.
   Examples: "What is the current insider trading disclosure timeline?", "What does LODR Reg 30 say about material events?", "Latest SEBI circular on T+0 settlement"

2. "multihop"  — The question requires connecting two or more entities (regulation + company type, rule + amendment, one circular + the circulars it references). Answer needs relational reasoning across multiple circulars.
   Examples: "Which circulars amend the 2015 PIT regulations?", "What rules apply to a PMS doing algo trading for FPI clients?", "How do LODR disclosure timelines interact with SAST trigger thresholds?"

3. "thematic"  — A broad, evolution-style or cross-cutting question that needs a synthesis across many circulars over time.
   Examples: "How has SEBI's stance on ESG reporting evolved?", "Summarise all algo-trading circulars since 2018", "What are the recurring themes in FPI regulations over the past decade?"

Return ONLY valid JSON:
{"mode": "narrow|multihop|thematic", "reason": "<one short sentence>"}

No markdown, no prose outside the JSON.
"""

_HEURISTIC_THEMATIC = re.compile(
    r"\b(evolve|evolut|history|over time|over the years|since \d{4}|trend|summaris|summariz|all circulars|theme|decade)\b",
    re.IGNORECASE,
)
_HEURISTIC_MULTIHOP = re.compile(
    r"\b(amend|supersede|superseed|interact|relat(ed|ion)|applies to|both|and|between|which circulars|cross-refer)\b",
    re.IGNORECASE,
)


def _heuristic_classify(q: str) -> Mode:
    """Cheap, deterministic fallback when LLM classifier fails or budget is low."""
    if _HEURISTIC_THEMATIC.search(q):
        return "thematic"
    if _HEURISTIC_MULTIHOP.search(q) and len(q.split()) > 6:
        return "multihop"
    return "narrow"


async def classify_query(question: str) -> dict:
    """Return {mode, reason, source: 'llm'|'heuristic'}."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        mode = _heuristic_classify(question)
        return {"mode": mode, "reason": "heuristic fallback (no LLM key)", "source": "heuristic"}

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"compliance-router-{hash(question) & 0xFFFFFF}",
            system_message=CLASSIFIER_SYSTEM,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=f"Classify: {question.strip()}"))
        raw = resp.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
        data = json.loads(raw)
        mode = data.get("mode")
        if mode not in ("narrow", "multihop", "thematic"):
            raise ValueError(f"invalid mode {mode!r}")
        return {"mode": mode, "reason": data.get("reason", "")[:240], "source": "llm"}
    except Exception as e:
        logger.warning(f"Query classifier failed, falling back to heuristic: {e}")
        mode = _heuristic_classify(question)
        return {"mode": mode, "reason": f"heuristic fallback ({e.__class__.__name__})", "source": "heuristic"}
