"""
Guidance AI Service — RAG Pipeline for BSE Corporate Filings Intelligence.

Pipeline:
1. Parse question → extract stock names, categories, intent
2. Retrieve relevant filings from MongoDB (smart text matching + filters)
3. Build context window from top-K filings
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
    """Retrieve relevant filings from MongoDB using smart querying."""
    query_parts = []

    # Stock filter
    if context["stocks"]:
        stock_regex = "|".join(context["stocks"])
        query_parts.append({
            "$or": [
                {"stock_symbol": {"$regex": stock_regex, "$options": "i"}},
                {"stock_name": {"$regex": stock_regex, "$options": "i"}},
            ]
        })

    # Category filter
    if context["categories"]:
        cat_regex = "|".join(re.escape(c) for c in context["categories"])
        query_parts.append({"category": {"$regex": cat_regex, "$options": "i"}})

    # Build final query
    if query_parts:
        query = {"$and": query_parts} if len(query_parts) > 1 else query_parts[0]
    else:
        # No specific filters — do keyword search on headline
        keywords = [w for w in question.lower().split() if len(w) > 3 and w not in
                    ('what', 'which', 'show', 'tell', 'give', 'list', 'find',
                     'about', 'from', 'with', 'that', 'this', 'have', 'been',
                     'their', 'they', 'some', 'most', 'more', 'than')]
        if keywords:
            kw_regex = "|".join(re.escape(k) for k in keywords[:6])
            query = {"$or": [
                {"headline": {"$regex": kw_regex, "$options": "i"}},
                {"stock_name": {"$regex": kw_regex, "$options": "i"}},
                {"more_text": {"$regex": kw_regex, "$options": "i"}},
                {"category": {"$regex": kw_regex, "$options": "i"}},
            ]}
        else:
            query = {}

    # Fetch with date sort (most recent first)
    filings = await db.guidance.find(
        query, {"_id": 0}
    ).sort("news_date", -1).limit(max_results).to_list(length=max_results)

    # If we got too few results from specific query, broaden search
    if len(filings) < 10 and context["stocks"]:
        broad_filings = await db.guidance.find(
            {}, {"_id": 0}
        ).sort("news_date", -1).limit(30).to_list(length=30)
        # Add unique filings
        existing_ids = {f.get("news_id") for f in filings}
        for bf in broad_filings:
            if bf.get("news_id") not in existing_ids:
                filings.append(bf)
                if len(filings) >= max_results:
                    break

    return filings


def _build_context_text(filings: list, max_chars: int = 30000) -> str:
    """Convert filings to structured text for LLM context."""
    if not filings:
        return "No relevant filings found in the database."

    lines = []
    total_chars = 0

    for i, f in enumerate(filings):
        entry = (
            f"[{i+1}] {f.get('stock_symbol', '?')} | "
            f"{f.get('news_date', '?')[:10]} | "
            f"{f.get('category', 'General')} | "
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
        f"=== BSE CORPORATE FILINGS DATABASE ===\n"
        f"Total filings retrieved: {len(filings)}\n"
        f"Stocks covered: {len(set(f.get('stock_symbol','') for f in filings))}\n"
        f"Date range: {filings[-1].get('news_date','?')[:10] if filings else '?'} to "
        f"{filings[0].get('news_date','?')[:10] if filings else '?'}\n"
        f"{'='*40}\n\n"
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

    # Step 3: Build context text
    context_text = _build_context_text(filings)

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

    # Step 5: Call LLM
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=api_key,
            session_id=f"guidance-ai-{datetime.now(IST).isoformat()}",
            system_message=GUIDANCE_SYSTEM_PROMPT,
        )
        chat.with_model("openai", "gpt-4.1")
        response = await chat.send_message(UserMessage(text=user_prompt))

        # Step 6: Build source citations
        sources = _build_source_citations(filings)

        return {
            "answer": response.strip(),
            "sources": sources,
            "filings_retrieved": len(filings),
            "stocks_in_context": list(set(f.get("stock_symbol", "") for f in filings)),
            "query_context": context,
            "timestamp": datetime.now(IST).isoformat(),
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
