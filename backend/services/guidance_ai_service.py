"""
Guidance AI Service — RAG Pipeline for BSE Corporate Filings Intelligence.

Pipeline:
1. Parse question → extract stock names, categories, intent
2. Vector-search relevant filings + PDF chunks via TF-IDF cosine similarity (3-month window)
3. Build context window from top-K results
4. Send to LLM (GPT-4.1) with crafted prompt
5. Return structured answer with source citations
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
RETENTION_DAYS = 90  # 3-month window

GUIDANCE_SYSTEM_PROMPT = """You are the Bharat Market Intel Agent (BMIA) — Guidance Intelligence Module.
You are an expert analyst specializing in Indian equity markets. You have access to real BSE corporate filings, 
announcements, board meeting outcomes, insider trading disclosures, and regulatory updates.

YOUR ROLE:
- Answer questions precisely using ONLY the provided filing data as evidence
- Cross-reference multiple filings to identify patterns, risks, and opportunities  
- Flag critical events: insider selling, board resignations, regulatory actions, unusual corporate actions
- Provide actionable intelligence, not just summaries
- Cite specific filings by [Stock Symbol, Date, Category] so the user can verify

ANALYSIS STYLE:
- Be direct and specific. No generic statements.
- Quantify when possible (e.g., "3 insider sales in 7 days totaling X shares")
- Highlight contradictions between filings (e.g., company says growth but insiders selling)
- Compare across companies when relevant
- Flag what's MISSING (e.g., "No result filing from X despite board meeting on Y date")

FORMAT:
- Use clear sections with headers when answering complex questions
- Include a "Key Takeaways" section at the end for quick scanning
- Reference source filings as [SYMBOL | Date | Category] 

IMPORTANT:
- If data is insufficient to answer, say so clearly — don't fabricate
- Distinguish between facts (from filings) and your analytical inference
- Consider Indian market context (SEBI regulations, NSE/BSE norms, Indian corporate governance)
"""

GEMINI_REWRITE_PROMPT = """You are a senior financial editor at a top Indian brokerage. Your job is to take raw analyst notes and transform them into a polished, professional intelligence report.

RULES:
- Preserve every factual claim, stock symbol, date, number, and citation from the raw notes
- Never invent new facts or stocks not mentioned in the raw notes
- Structure the response with clear markdown headers (##), bullet points, and bold emphasis on key findings
- Start with a brief Executive Summary (2-3 lines)
- Group related findings under logical section headers
- End with a 'Key Takeaways' section as a bulleted list
- Use Indian market terminology naturally (SEBI, NSE, BSE, scrip, etc.)
- Keep the tone professional but direct — traders read this before market open
- If the raw notes mention data gaps or insufficient evidence, preserve that transparency
- Format numbers in Indian style (lakhs, crores) where appropriate
"""


def _extract_query_context(question: str):
    """Parse the user question to extract stocks, categories, and intent."""
    q = question.upper()

    # Common stock name patterns
    stock_patterns = re.findall(r'\b([A-Z]{2,15})\b', q)
    # Filter out common English words
    noise = {'THE', 'AND', 'FOR', 'ARE', 'WAS', 'HAS', 'HAVE', 'WITH', 'FROM', 'THIS',
             'THAT', 'WHAT', 'WHICH', 'WHO', 'HOW', 'WHY', 'WHEN', 'WHERE', 'ANY',
             'ALL', 'ABOUT', 'INTO', 'BETWEEN', 'THEIR', 'BEEN', 'WILL', 'WOULD',
             'SHOULD', 'COULD', 'MOST', 'SOME', 'THAN', 'THEM', 'THESE', 'THOSE',
             'SHOW', 'TELL', 'GIVE', 'LIST', 'FIND', 'GET', 'RECENT', 'LATEST',
             'LAST', 'NEXT', 'NEW', 'OLD', 'TOP', 'BEST', 'WORST', 'MORE', 'LESS',
             'RED', 'FLAG', 'FLAGS', 'COMPARE', 'ANALYSIS', 'ANALYZE', 'SUMMARY',
             'SUMMARIZE', 'PATTERN', 'PATTERNS', 'COMPANY', 'COMPANIES', 'STOCK',
             'STOCKS', 'MARKET', 'FILING', 'FILINGS', 'BOARD', 'MEETING', 'MEETINGS',
             'INSIDER', 'TRADING', 'CORPORATE', 'ACTION', 'ACTIONS', 'DIVIDEND',
             'RESULT', 'RESULTS', 'ANNUAL', 'QUARTERLY', 'REPORT', 'REPORTS',
             'GROUP', 'SECTOR', 'DAYS', 'WEEK', 'MONTH', 'YEAR', 'TODAY', 'YESTERDAY',
             'BSE', 'NSE', 'SEBI', 'NIFTY', 'INDEX', 'PDF', 'NEWS', 'UPDATE', 'UPDATES'}
    extracted_stocks = [s for s in stock_patterns if s not in noise and len(s) >= 3]

    # Category detection
    categories = []
    cat_map = {
        'board meeting': 'Board Meeting',
        'insider': 'Insider Trading / SAST',
        'sast': 'Insider Trading / SAST',
        'agm': 'AGM/EGM',
        'egm': 'AGM/EGM',
        'dividend': 'Corp. Action',
        'corporate action': 'Corp. Action',
        'result': 'Result',
        'quarterly': 'Result',
        'annual': 'Result',
        'mutual fund': 'Mutual Fund',
    }
    ql = question.lower()
    for key, cat in cat_map.items():
        if key in ql and cat not in categories:
            categories.append(cat)

    # Time range detection
    days_back = 30
    if 'today' in ql or 'latest' in ql:
        days_back = 1
    elif 'yesterday' in ql:
        days_back = 2
    elif 'this week' in ql or 'last 7' in ql or '7 day' in ql:
        days_back = 7
    elif 'this month' in ql or 'last 30' in ql or '30 day' in ql:
        days_back = 30
    elif 'last 3 month' in ql or '90 day' in ql or 'quarter' in ql:
        days_back = 90

    return {
        "stocks": extracted_stocks[:5],
        "categories": categories,
        "days_back": days_back,
    }


async def _retrieve_relevant_filings(db, question: str, context: dict, max_results: int = 60):
    """Retrieve relevant filings using vector store (TF-IDF cosine similarity).
    Falls back to keyword search if vector store is not ready."""
    from services.vector_store import guidance_vector_store

    if guidance_vector_store.is_ready:
        # First pass: search with category filter only (TF-IDF handles text relevance)
        # Don't filter by extracted "stocks" — they're often noise words from the question
        results = guidance_vector_store.search(
            query=question,
            top_k=max_results,
            category_filter=context.get("categories") or None,
            min_score=0.03,
        )

        # If we got specific stock names that look real (>= 3 chars, known patterns),
        # do a secondary focused search and merge
        real_stocks = [s for s in context.get("stocks", []) if len(s) >= 3]
        if real_stocks and len(results) < max_results:
            stock_results = guidance_vector_store.search(
                query=question,
                top_k=max_results // 2,
                stock_filter=real_stocks,
                min_score=0.02,
            )
            seen_ids = {r.get("news_id") for r in results}
            for sr in stock_results:
                if sr.get("news_id") not in seen_ids:
                    results.append(sr)
                    seen_ids.add(sr.get("news_id"))

        if results:
            logger.info(f"GUIDANCE AI: Vector search returned {len(results)} results (top score: {results[0].get('score', 0):.4f})")
            return results

    # Fallback: keyword-based retrieval from MongoDB
    logger.info("GUIDANCE AI: Vector store not ready or empty, using keyword fallback")
    cutoff = (datetime.now(IST) - timedelta(days=RETENTION_DAYS)).isoformat()
    query_parts = [{"scraped_at": {"$gte": cutoff}}]

    if context["stocks"]:
        stock_regex = "|".join(context["stocks"])
        query_parts.append({
            "$or": [
                {"stock_symbol": {"$regex": stock_regex, "$options": "i"}},
                {"stock_name": {"$regex": stock_regex, "$options": "i"}},
            ]
        })

    if context["categories"]:
        cat_regex = "|".join(re.escape(c) for c in context["categories"])
        query_parts.append({"category": {"$regex": cat_regex, "$options": "i"}})

    query = {"$and": query_parts} if len(query_parts) > 1 else query_parts[0]

    filings = await db.guidance.find(
        query, {"_id": 0}
    ).sort("news_date", -1).limit(max_results).to_list(length=max_results)

    return filings


async def _retrieve_pdf_chunks(db, context: dict, question: str, max_chunks: int = 15):
    """Retrieve relevant PDF text chunks via vector store for deeper RAG context."""
    from services.vector_store import guidance_vector_store

    if guidance_vector_store.is_ready:
        results = guidance_vector_store.search(
            query=question,
            top_k=max_chunks,
            category_filter=context.get("categories") or None,
            doc_type="pdf_chunk",
            min_score=0.03,
        )
        if results:
            logger.info(f"GUIDANCE AI: Vector search returned {len(results)} PDF chunks")
            return results

    # Fallback to old method
    try:
        from services.pdf_extractor_service import get_pdf_chunks_for_query
        keywords = [w for w in question.lower().split() if len(w) > 3]
        chunks = await get_pdf_chunks_for_query(
            db,
            stock_symbols=context.get("stocks"),
            categories=context.get("categories"),
            keywords=keywords,
            max_chunks=max_chunks,
        )
        return chunks
    except Exception as e:
        logger.debug(f"PDF chunk retrieval failed: {e}")
        return []


def _build_context_text(filings: list, max_chars: int = 30000) -> str:
    """Convert filings/vector results to structured text for LLM context."""
    if not filings:
        return "No relevant filings found in the database."

    lines = []
    total_chars = 0

    for i, f in enumerate(filings):
        score_str = f" | Relevance: {f['score']:.3f}" if "score" in f else ""
        entry = (
            f"[{i+1}] {f.get('stock_symbol', '?')} | "
            f"{(f.get('news_date', '?') or '?')[:10]} | "
            f"{f.get('category', 'General')}{score_str} | "
            f"Critical: {'YES' if f.get('critical') else 'No'}\n"
            f"  Company: {f.get('stock_name', '?')}\n"
            f"  Headline: {f.get('headline', 'N/A')}\n"
        )

        more = f.get('more_text', '')
        if more:
            entry += f"  Details: {more[:300]}\n"

        if f.get('pdf_url'):
            entry += f"  PDF: {f['pdf_url']}\n"

        entry += "\n"

        if total_chars + len(entry) > max_chars:
            lines.append(f"... [{len(filings) - i} more filings truncated for context limit]")
            break

        lines.append(entry)
        total_chars += len(entry)

    header = (
        f"=== BSE CORPORATE FILINGS DATABASE (3-MONTH WINDOW) ===\n"
        f"Total filings retrieved: {len(filings)}\n"
        f"Stocks covered: {len(set(f.get('stock_symbol','') for f in filings))}\n"
        f"Date range: {(filings[-1].get('news_date','?') or '?')[:10] if filings else '?'} to "
        f"{(filings[0].get('news_date','?') or '?')[:10] if filings else '?'}\n"
        f"Retrieval: TF-IDF Vector Similarity\n"
        f"{'='*50}\n\n"
    )

    return header + "".join(lines)


def _build_source_citations(filings: list) -> list:
    """Build structured source citations for the frontend."""
    sources = []
    seen = set()
    for f in filings[:20]:
        key = f.get("news_id", "")
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "symbol": f.get("stock_symbol", "?"),
            "name": f.get("stock_name", ""),
            "date": f.get("news_date", "")[:10] if f.get("news_date") else "",
            "category": f.get("category", "General"),
            "headline": f.get("headline", "")[:120],
            "pdf_url": f.get("pdf_url"),
            "critical": f.get("critical", False),
        })
    return sources


async def ask_guidance_ai(db, question: str, conversation_history: list = None):
    """
    Main RAG pipeline: Question → Retrieve → Contextualize → LLM → Answer.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "LLM key not configured", "answer": None}

    logger.info(f"GUIDANCE AI: Processing question: {question[:100]}")

    # Step 1: Parse question
    context = _extract_query_context(question)
    logger.info(f"GUIDANCE AI: Extracted context — stocks={context['stocks']}, categories={context['categories']}")

    # Step 2: Retrieve relevant filings
    filings = await _retrieve_relevant_filings(db, question, context)
    logger.info(f"GUIDANCE AI: Retrieved {len(filings)} relevant filings")

    # Step 2b: Retrieve PDF text chunks for deeper analysis
    pdf_chunks = await _retrieve_pdf_chunks(db, context, question)
    logger.info(f"GUIDANCE AI: Retrieved {len(pdf_chunks)} PDF text chunks")

    # Step 3: Build context text
    context_text = _build_context_text(filings)

    # Append PDF text chunks
    if pdf_chunks:
        pdf_context = "\n\n=== EXTRACTED PDF CONTENT (Vectorized Chunks) ===\n"
        for i, chunk in enumerate(pdf_chunks):
            score_str = f" | Score: {chunk['score']:.3f}" if "score" in chunk else ""
            chunk_text = chunk.get('text', '')
            pdf_context += (
                f"\n[PDF-{i+1}] {chunk.get('stock_symbol','')} | {(chunk.get('headline','') or '')[:80]}{score_str}\n"
                f"  {chunk_text[:600]}\n"
            )
        context_text += pdf_context

    # Step 4: Build the prompt
    user_prompt = (
        f"USER QUESTION: {question}\n\n"
        f"RETRIEVED FILINGS DATA:\n{context_text}\n\n"
        f"Instructions:\n"
        f"- Answer the question using the filings data above as your primary evidence\n"
        f"- Cite filings by their reference number [N] and include [Stock | Date | Category]\n"
        f"- If the data doesn't contain enough info to fully answer, state what's available and what's missing\n"
        f"- Provide actionable intelligence, not just a data dump\n"
        f"- End with 'Key Takeaways' bullet points\n"
    )

    # Include conversation history for follow-ups
    if conversation_history:
        history_text = "\n".join([
            f"{'User' if m['role'] == 'user' else 'AI'}: {m['content'][:200]}"
            for m in conversation_history[-4:]
        ])
        user_prompt = f"PREVIOUS CONVERSATION:\n{history_text}\n\n{user_prompt}"

    # Step 5: Two-stage LLM pipeline — GPT analyzes, Gemini structures
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        # Stage 1: GPT-4.1 — raw analysis from filings data
        gpt_chat = LlmChat(
            api_key=api_key,
            session_id=f"guidance-gpt-{datetime.now(IST).isoformat()}",
            system_message=GUIDANCE_SYSTEM_PROMPT,
        )
        gpt_chat.with_model("openai", "gpt-4.1")
        raw_analysis = await gpt_chat.send_message(UserMessage(text=user_prompt))

        logger.info(f"GUIDANCE AI: GPT raw analysis done ({len(raw_analysis)} chars)")

        # Stage 2: Gemini — rewrite into a polished, structured response
        gemini_chat = LlmChat(
            api_key=api_key,
            session_id=f"guidance-gemini-{datetime.now(IST).isoformat()}",
            system_message=GEMINI_REWRITE_PROMPT,
        )
        gemini_chat.with_model("gemini", "gemini-2.5-flash")

        rewrite_prompt = (
            f"ORIGINAL USER QUESTION:\n{question}\n\n"
            f"RAW ANALYST NOTES (from GPT):\n{raw_analysis}\n\n"
            f"Rewrite the above into a clear, well-structured intelligence report. "
            f"Preserve all factual claims, stock names, dates, and citations. "
            f"Improve flow, add proper section headers, and make it readable."
        )
        final_response = await gemini_chat.send_message(UserMessage(text=rewrite_prompt))

        logger.info(f"GUIDANCE AI: Gemini structured response done ({len(final_response)} chars)")

        # Step 6: Build source citations
        sources = _build_source_citations(filings)

        return {
            "answer": final_response.strip(),
            "sources": sources,
            "filings_retrieved": len(filings),
            "stocks_in_context": list(set(f.get("stock_symbol", "") for f in filings)),
            "query_context": context,
            "timestamp": datetime.now(IST).isoformat(),
            "pipeline": "gpt-4.1 → gemini-2.5-flash",
        }

    except Exception as e:
        logger.error(f"GUIDANCE AI: LLM error: {e}")
        return {
            "error": f"AI analysis failed: {str(e)}",
            "answer": None,
            "sources": _build_source_citations(filings),
            "filings_retrieved": len(filings),
        }


async def get_suggested_questions(db):
    """Generate suggested questions based on current filing data."""
    # Get recent critical filings
    critical = await db.guidance.find(
        {"critical": True}, {"_id": 0, "stock_symbol": 1, "headline": 1, "category": 1}
    ).sort("news_date", -1).limit(5).to_list(length=5)

    # Get top active stocks
    pipeline = [
        {"$group": {"_id": "$stock_symbol", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_stocks = await db.guidance.aggregate(pipeline).to_list(length=5)

    suggestions = [
        "What are the most significant board meeting outcomes this week?",
        "Show me all insider trading activity in the last 7 days. Any red flags?",
        "Which companies have upcoming AGMs/EGMs and what's on the agenda?",
    ]

    if critical:
        sym = critical[0].get("stock_symbol", "")
        suggestions.insert(0, f"Analyze the critical filing for {sym} — what does it mean for investors?")

    if top_stocks:
        syms = [s["_id"] for s in top_stocks[:3] if s["_id"]]
        if len(syms) >= 2:
            suggestions.append(f"Compare recent filings of {syms[0]} vs {syms[1]} — which looks stronger?")

    suggestions.append("Summarize all corporate actions announced this month. Any dividend opportunities?")

    return suggestions[:6]
