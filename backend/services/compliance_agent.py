"""
Compliance AI Agent — NotebookLM-style research over NSE/BSE/SEBI circulars.

Uses Claude Sonnet 4.5 via Emergent LLM key.
Two-stage:
  1. Retrieve top-K relevant chunks via compliance_router
  2. Feed chunks as context to Claude with strict citation format instructions
"""
import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

from services.compliance_rag import compliance_router

load_dotenv()
logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

SYSTEM_PROMPT = """You are a senior compliance research analyst specializing in Indian capital markets regulation.
You help users understand NSE, BSE, and SEBI circulars from 2010 to present.

STRICT RULES:
1. Answer ONLY from the provided CONTEXT sections below. Never invent citations or facts.
2. Every factual claim must cite its source using [CIT-N] markers where N is the citation number.
3. If context is insufficient, say "The provided circulars do not directly address this" — never guess.
4. Use clear, professional compliance language. Structure long answers with headings.
5. When asked about a regulation's evolution, cite circulars in chronological order.
6. Always end with a "## Sources" section listing each [CIT-N] and the source metadata.

OUTPUT FORMAT:
- Direct, concise answer first (2-4 sentences)
- Then detailed explanation with [CIT-N] inline references
- End with ## Sources listing:
  [CIT-1] SEBI Circular SEBI/HO/CFD/CMD2/CIR/P/2023/142 | 25-Sep-2023 | Category
  [CIT-2] NSE Circular NSE/CML/2024/15 | 03-Jan-2024 | Category"""


def _format_context(chunks: List[dict]) -> tuple[str, List[dict]]:
    """Build numbered context block + return citation metadata list."""
    ctx_parts = []
    citations = []
    for i, chunk in enumerate(chunks, 1):
        src = (chunk.get("source") or "").upper()
        circ_no = chunk.get("circular_no") or "N/A"
        title = chunk.get("title") or "Untitled"
        date = chunk.get("date_iso") or chunk.get("date") or "N/A"
        category = chunk.get("category") or "General"
        text = chunk.get("text_chunk") or ""

        ctx_parts.append(
            f"[CIT-{i}] SOURCE: {src} | CIRCULAR: {circ_no} | DATE: {date} | TITLE: {title}\n"
            f"CONTEXT:\n{text}\n"
        )
        citations.append({
            "id": f"CIT-{i}",
            "source": src,
            "circular_no": circ_no,
            "title": title,
            "date": date,
            "category": category,
            "url": chunk.get("url", ""),
            "score": round(chunk.get("score", 0), 3),
            "score_semantic": round(chunk["score_semantic"], 3) if "score_semantic" in chunk else None,
        })
    return "\n---\n".join(ctx_parts), citations


async def research(
    question: str,
    sources: Optional[List[str]] = None,
    year_filter: Optional[int] = None,
    session_id: Optional[str] = None,
    top_k: int = 10,
) -> dict:
    """Main entry: retrieve + reason + return answer with citations."""
    if not EMERGENT_LLM_KEY:
        return {
            "answer": "Compliance AI is not configured — EMERGENT_LLM_KEY missing.",
            "citations": [],
            "error": "missing_key",
        }

    # 1. Retrieve
    chunks = compliance_router.search(
        question, sources=sources, year_filter=year_filter, top_k=top_k
    )
    if not chunks:
        return {
            "answer": (
                "No relevant circulars found in the indexed sources. "
                "The ingestion may still be in progress, or your query may be too "
                "broad — try including a specific topic (e.g., 'insider trading', "
                "'ESG reporting', 'ICDR', 'listing obligations')."
            ),
            "citations": [],
            "sources_searched": sources or ["nse", "bse", "sebi"],
        }

    context, citations = _format_context(chunks)

    # 2. Reason with Claude
    sid = session_id or f"compliance_{hash(question) & 0xFFFFFF}"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=sid,
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    user_prompt = f"""## QUESTION
{question}

## CONTEXT (from indexed circulars)
{context}

Answer the question strictly from the CONTEXT above using [CIT-N] citations.
"""
    try:
        response = await chat.send_message(UserMessage(text=user_prompt))
    except Exception as e:
        logger.error(f"COMPLIANCE AGENT: Claude call failed: {e}")
        return {
            "answer": f"AI reasoning temporarily unavailable: {e}",
            "citations": citations,
            "error": "llm_call_failed",
        }

    return {
        "answer": response,
        "citations": citations,
        "sources_searched": sources or ["nse", "bse", "sebi"],
        "session_id": sid,
        "context_chunks_used": len(chunks),
    }
