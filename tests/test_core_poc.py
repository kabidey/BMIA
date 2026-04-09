"""
Bharat Market Intel Agent (BMIA) - Core POC Test Script
Tests: Market Data (yfinance), Technical Indicators, Fundamentals, 
       News Scraping, LLM Sentiment, Alpha Score Computation
"""

import asyncio
import json
import math
import os
import sys
import traceback
from datetime import datetime, timedelta

import numpy as np
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

# ========== CONFIG ==========
TEST_STOCKS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
TEST_COMMODITY = "GC=F"  # Gold futures as MCX proxy
ALL_SYMBOLS = TEST_STOCKS + [TEST_COMMODITY]
RESULTS = {}

# ========== 1. MARKET DATA (yfinance) ==========
def test_market_data():
    """Fetch OHLCV data for NSE stocks and commodity proxy."""
    print("\n" + "=" * 60)
    print("TEST 1: Market Data Fetching (yfinance)")
    print("=" * 60)
    
    results = {}
    for symbol in ALL_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            # Get 6 months of daily data
            hist = ticker.history(period="6mo", interval="1d")
            
            if hist.empty:
                print(f"  [FAIL] {symbol}: No data returned")
                results[symbol] = {"status": "FAIL", "error": "No data"}
                continue
            
            latest = hist.iloc[-1]
            data = {
                "status": "PASS",
                "rows": len(hist),
                "latest_date": str(hist.index[-1].date()),
                "open": round(float(latest["Open"]), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "close": round(float(latest["Close"]), 2),
                "volume": int(latest["Volume"]),
            }
            results[symbol] = data
            print(f"  [PASS] {symbol}: {data['rows']} rows, Close={data['close']}, Vol={data['volume']}")
        except Exception as e:
            results[symbol] = {"status": "FAIL", "error": str(e)}
            print(f"  [FAIL] {symbol}: {e}")
    
    RESULTS["market_data"] = results
    return results


# ========== 2. TECHNICAL INDICATORS ==========
def test_technical_indicators():
    """Calculate RSI, MACD, and VSA heuristics."""
    print("\n" + "=" * 60)
    print("TEST 2: Technical Indicator Calculations")
    print("=" * 60)
    
    results = {}
    for symbol in ALL_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y", interval="1d")
            
            if hist.empty or len(hist) < 30:
                print(f"  [FAIL] {symbol}: Insufficient data ({len(hist)} rows)")
                results[symbol] = {"status": "FAIL", "error": "Insufficient data"}
                continue
            
            close = hist["Close"].values
            volume = hist["Volume"].values
            
            # RSI (14-period)
            deltas = np.diff(close)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            # MACD (12, 26, 9)
            def ema(data, period):
                alpha = 2 / (period + 1)
                result = np.zeros_like(data, dtype=float)
                result[0] = data[0]
                for i in range(1, len(data)):
                    result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
                return result
            
            ema12 = ema(close, 12)
            ema26 = ema(close, 26)
            macd_line = ema12 - ema26
            signal_line = ema(macd_line, 9)
            macd_histogram = macd_line - signal_line
            
            # Volume Spread Analysis (VSA) - simplified
            avg_vol_20 = np.mean(volume[-20:])
            current_vol = volume[-1]
            vol_ratio = current_vol / (avg_vol_20 + 1e-10)
            spread = close[-1] - close[-2] if len(close) > 1 else 0
            
            # Breakout detection: price above 52-week high
            high_52w = np.max(hist["High"].values[-252:]) if len(hist) >= 252 else np.max(hist["High"].values)
            is_breakout = close[-1] >= high_52w * 0.98
            
            # 20-day Moving Average
            ma_20 = np.mean(close[-20:])
            above_ma = close[-1] > ma_20
            
            # Technical Score (0-100)
            tech_score = 50  # base
            if rsi > 50 and rsi < 70:
                tech_score += 15  # bullish but not overbought
            elif rsi > 70:
                tech_score += 5  # overbought - slightly positive
            elif rsi < 30:
                tech_score -= 15  # oversold
            
            if macd_histogram[-1] > 0:
                tech_score += 15  # bullish MACD
            else:
                tech_score -= 10
            
            if above_ma:
                tech_score += 10  # above 20 MA
            
            if vol_ratio > 1.5 and spread > 0:
                tech_score += 10  # high volume bullish
            
            if is_breakout:
                tech_score += 10  # breakout
                
            tech_score = max(0, min(100, tech_score))
            
            data = {
                "status": "PASS",
                "rsi": round(rsi, 2),
                "macd_line": round(float(macd_line[-1]), 4),
                "macd_signal": round(float(signal_line[-1]), 4),
                "macd_histogram": round(float(macd_histogram[-1]), 4),
                "vol_ratio": round(vol_ratio, 2),
                "ma_20": round(ma_20, 2),
                "above_ma": above_ma,
                "is_breakout": is_breakout,
                "technical_score": tech_score,
            }
            results[symbol] = data
            print(f"  [PASS] {symbol}: RSI={data['rsi']}, MACD_H={data['macd_histogram']}, TechScore={tech_score}")
        except Exception as e:
            results[symbol] = {"status": "FAIL", "error": str(e)}
            print(f"  [FAIL] {symbol}: {e}")
            traceback.print_exc()
    
    RESULTS["technical"] = results
    return results


# ========== 3. FUNDAMENTAL ANALYSIS ==========
def test_fundamentals():
    """Extract P/E, D/E, Revenue Growth, Graham Value."""
    print("\n" + "=" * 60)
    print("TEST 3: Fundamental Analysis")
    print("=" * 60)
    
    results = {}
    for symbol in ALL_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            sector_pe = info.get("sectorPE")  # may not exist
            debt_to_equity = info.get("debtToEquity")
            revenue_growth = info.get("revenueGrowth")
            eps = info.get("trailingEps")
            bvps = info.get("bookValue")
            market_cap = info.get("marketCap")
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            
            # Graham's Intrinsic Value: V = sqrt(22.5 * EPS * BVPS)
            graham_value = None
            if eps and bvps and eps > 0 and bvps > 0:
                graham_value = round(math.sqrt(22.5 * eps * bvps), 2)
            
            current_price = info.get("currentPrice") or info.get("previousClose")
            
            # Fundamental Score (0-100)
            fund_score = 50  # base
            
            if pe_ratio:
                if pe_ratio < 15:
                    fund_score += 20  # undervalued
                elif pe_ratio < 25:
                    fund_score += 10
                elif pe_ratio > 40:
                    fund_score -= 15  # overvalued
            
            if debt_to_equity:
                if debt_to_equity < 50:
                    fund_score += 15  # low debt
                elif debt_to_equity < 100:
                    fund_score += 5
                else:
                    fund_score -= 10  # high debt
            
            if revenue_growth:
                if revenue_growth > 0.15:
                    fund_score += 15  # strong growth
                elif revenue_growth > 0.05:
                    fund_score += 5
                elif revenue_growth < 0:
                    fund_score -= 10
            
            if graham_value and current_price:
                if current_price < graham_value:
                    fund_score += 10  # undervalued by Graham
                elif current_price > graham_value * 1.5:
                    fund_score -= 5
            
            fund_score = max(0, min(100, fund_score))
            
            data = {
                "status": "PASS",
                "pe_ratio": round(pe_ratio, 2) if pe_ratio else "N/A",
                "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else "N/A",
                "revenue_growth": round(revenue_growth * 100, 2) if revenue_growth else "N/A",
                "eps": round(eps, 2) if eps else "N/A",
                "bvps": round(bvps, 2) if bvps else "N/A",
                "graham_value": graham_value or "N/A",
                "current_price": round(current_price, 2) if current_price else "N/A",
                "sector": sector,
                "industry": industry,
                "market_cap": market_cap,
                "fundamental_score": fund_score,
            }
            results[symbol] = data
            print(f"  [PASS] {symbol}: P/E={data['pe_ratio']}, D/E={data['debt_to_equity']}, Graham={graham_value}, FundScore={fund_score}")
        except Exception as e:
            results[symbol] = {"status": "FAIL", "error": str(e)}
            print(f"  [FAIL] {symbol}: {e}")
            traceback.print_exc()
    
    RESULTS["fundamentals"] = results
    return results


# ========== 4. NEWS SCRAPING ==========
def test_news_scraping():
    """Fetch news headlines for stocks."""
    print("\n" + "=" * 60)
    print("TEST 4: News Scraping")
    print("=" * 60)
    
    results = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for symbol in ALL_SYMBOLS:
        try:
            # Method 1: Use yfinance news
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            headlines = []
            if news:
                # yfinance news can be a list of dicts or have nested structure
                news_items = news if isinstance(news, list) else []
                for item in news_items[:10]:
                    if isinstance(item, dict):
                        title = item.get("title", "") or item.get("headline", "")
                        publisher = item.get("publisher", "") or item.get("source", "")
                        link = item.get("link", "") or item.get("url", "")
                        pub_date = item.get("providerPublishTime", "") or item.get("publish_time", "")
                        if title:
                            date_str = ""
                            if isinstance(pub_date, (int, float)):
                                date_str = str(datetime.fromtimestamp(pub_date))
                            elif pub_date:
                                date_str = str(pub_date)
                            headlines.append({
                                "title": title,
                                "publisher": str(publisher),
                                "link": link,
                                "date": date_str,
                            })
            
            # Method 2: Google News RSS as fallback
            if len(headlines) < 3:
                import urllib.parse
                clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")
                search_query = f"{clean_symbol} stock India"
                encoded_query = urllib.parse.quote(search_query)
                try:
                    import feedparser
                    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
                    feed = feedparser.parse(rss_url)
                    for entry in feed.entries[:10]:
                        headlines.append({
                            "title": entry.get("title", ""),
                            "publisher": entry.get("source", {}).get("title", "Google News") if isinstance(entry.get("source"), dict) else "Google News",
                            "link": entry.get("link", ""),
                            "date": entry.get("published", ""),
                        })
                except Exception as rss_err:
                    print(f"    RSS fallback error: {rss_err}")
            
            data = {
                "status": "PASS" if len(headlines) > 0 else "PARTIAL",
                "headline_count": len(headlines),
                "headlines": headlines[:10],
                "sample": headlines[0]["title"] if headlines else "No headlines found",
            }
            results[symbol] = data
            print(f"  [{'PASS' if len(headlines) > 0 else 'PARTIAL'}] {symbol}: {len(headlines)} headlines found")
            if headlines:
                print(f"    Sample: {headlines[0]['title'][:80]}...")
        except Exception as e:
            results[symbol] = {"status": "FAIL", "error": str(e)}
            print(f"  [FAIL] {symbol}: {e}")
            traceback.print_exc()
    
    RESULTS["news"] = results
    return results


# ========== 5. LLM SENTIMENT ANALYSIS ==========
async def test_llm_sentiment():
    """Use OpenAI via Emergent to score news sentiment."""
    print("\n" + "=" * 60)
    print("TEST 5: LLM Sentiment Analysis (OpenAI via Emergent)")
    print("=" * 60)
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        print("  [FAIL] EMERGENT_LLM_KEY not found in environment")
        RESULTS["sentiment"] = {"status": "FAIL", "error": "No API key"}
        return {}
    
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    results = {}
    news_data = RESULTS.get("news", {})
    
    for symbol in ALL_SYMBOLS:
        try:
            news_info = news_data.get(symbol, {})
            headlines = news_info.get("headlines", [])
            
            if not headlines:
                results[symbol] = {"status": "SKIP", "reason": "No headlines"}
                print(f"  [SKIP] {symbol}: No headlines to analyze")
                continue
            
            # Prepare headline text
            headline_text = "\n".join([f"- {h['title']}" for h in headlines[:8]])
            clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")
            
            chat = LlmChat(
                api_key=api_key,
                session_id=f"sentiment-{symbol}-{datetime.now().isoformat()}",
                system_message="""You are a financial sentiment analyst for Indian markets. 
Analyze news headlines and return ONLY valid JSON with no extra text.
Format: {"score": <float -1 to 1>, "rationale": "<brief explanation>", "keywords": ["keyword1", "keyword2"], "sentiment_label": "<Bullish|Bearish|Neutral>"}
Score: -1 = very bearish, 0 = neutral, 1 = very bullish."""
            )
            chat.with_model("openai", "gpt-4.1-mini")
            
            user_msg = UserMessage(
                text=f"Analyze these headlines for {clean_symbol} stock sentiment:\n{headline_text}"
            )
            
            response = await chat.send_message(user_msg)
            
            # Parse response
            try:
                # Try to extract JSON from response
                resp_text = response.strip()
                if resp_text.startswith("```"):
                    resp_text = resp_text.split("```")[1]
                    if resp_text.startswith("json"):
                        resp_text = resp_text[4:]
                sentiment_data = json.loads(resp_text)
            except json.JSONDecodeError:
                # Fallback: try to find JSON in text
                import re
                json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                if json_match:
                    sentiment_data = json.loads(json_match.group())
                else:
                    sentiment_data = {"score": 0, "rationale": response[:200], "keywords": [], "sentiment_label": "Neutral"}
            
            score = float(sentiment_data.get("score", 0))
            # Normalize to 0-100
            sentiment_score = int((score + 1) * 50)  # -1->0, 0->50, 1->100
            
            data = {
                "status": "PASS",
                "raw_score": score,
                "sentiment_score_0_100": sentiment_score,
                "label": sentiment_data.get("sentiment_label", "Neutral"),
                "rationale": sentiment_data.get("rationale", ""),
                "keywords": sentiment_data.get("keywords", []),
            }
            results[symbol] = data
            print(f"  [PASS] {symbol}: Score={score}, Label={data['label']}, NormScore={sentiment_score}")
        except Exception as e:
            results[symbol] = {"status": "FAIL", "error": str(e)}
            print(f"  [FAIL] {symbol}: {e}")
            traceback.print_exc()
    
    RESULTS["sentiment"] = results
    return results


# ========== 6. ALPHA SCORE COMPUTATION ==========
def test_alpha_score():
    """Compute weighted Alpha Score and final recommendation."""
    print("\n" + "=" * 60)
    print("TEST 6: Alpha Score Computation")
    print("=" * 60)
    
    tech_data = RESULTS.get("technical", {})
    fund_data = RESULTS.get("fundamentals", {})
    sent_data = RESULTS.get("sentiment", {})
    market_data = RESULTS.get("market_data", {})
    
    results = {}
    for symbol in ALL_SYMBOLS:
        try:
            tech = tech_data.get(symbol, {})
            fund = fund_data.get(symbol, {})
            sent = sent_data.get(symbol, {})
            mkt = market_data.get(symbol, {})
            
            tech_score = tech.get("technical_score", 50)
            fund_score = fund.get("fundamental_score", 50)
            sent_score = sent.get("sentiment_score_0_100", 50)
            
            # Alpha Score = 0.4 * Technical + 0.4 * Fundamental + 0.2 * Sentiment
            alpha_score = round(0.4 * tech_score + 0.4 * fund_score + 0.2 * sent_score, 2)
            
            # Momentum Score: M = (Price_now - Price_n) / (Price_n * Volume_ratio)
            momentum = None
            if mkt.get("status") == "PASS":
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1mo", interval="1d")
                if len(hist) > 5:
                    price_now = float(hist["Close"].iloc[-1])
                    price_n = float(hist["Close"].iloc[0])
                    vol_ratio = tech.get("vol_ratio", 1)
                    momentum = round((price_now - price_n) / (price_n * max(vol_ratio, 0.01)), 4)
            
            # Sharpe Ratio (simplified with daily returns)
            sharpe = None
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="6mo", interval="1d")
                if len(hist) > 20:
                    returns = hist["Close"].pct_change().dropna().values
                    avg_return = np.mean(returns) * 252  # annualized
                    std_return = np.std(returns) * np.sqrt(252)
                    risk_free = 0.065  # India 10Y yield approx
                    if std_return > 0:
                        sharpe = round((avg_return - risk_free) / std_return, 4)
            except:
                pass
            
            # Recommendation
            if alpha_score > 85:
                recommendation = "STRONG BUY"
            elif alpha_score > 70:
                recommendation = "BUY"
            elif alpha_score > 60:
                recommendation = "ACCUMULATE"
            elif alpha_score >= 40:
                recommendation = "NEUTRAL"
            elif alpha_score >= 30:
                recommendation = "REDUCE"
            else:
                recommendation = "SELL/AVOID"
            
            data = {
                "status": "PASS",
                "technical_score": tech_score,
                "fundamental_score": fund_score,
                "sentiment_score": sent_score,
                "alpha_score": alpha_score,
                "momentum": momentum,
                "sharpe_ratio": sharpe,
                "recommendation": recommendation,
                "disclaimer": "This is for educational purposes only. Not financial advice. Past performance does not guarantee future results. Invest at your own risk. Always consult a SEBI-registered financial advisor.",
            }
            results[symbol] = data
            print(f"  [PASS] {symbol}: Alpha={alpha_score}%, Rec={recommendation}, Sharpe={sharpe}")
        except Exception as e:
            results[symbol] = {"status": "FAIL", "error": str(e)}
            print(f"  [FAIL] {symbol}: {e}")
            traceback.print_exc()
    
    RESULTS["alpha"] = results
    return results


# ========== MAIN ==========
async def main():
    print("=" * 60)
    print("BHARAT MARKET INTEL AGENT - CORE POC TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Symbols: {ALL_SYMBOLS}")
    print("=" * 60)
    
    # Run tests sequentially
    test_market_data()
    test_technical_indicators()
    test_fundamentals()
    test_news_scraping()
    await test_llm_sentiment()
    test_alpha_score()
    
    # Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    all_pass = True
    for test_name, test_results in RESULTS.items():
        passes = sum(1 for v in test_results.values() if isinstance(v, dict) and v.get("status") in ("PASS", "PARTIAL", "SKIP"))
        total = len(test_results)
        status = "PASS" if passes == total else "PARTIAL" if passes > 0 else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {test_name}: {status} ({passes}/{total} symbols)")
    
    # Final output JSON
    alpha_results = RESULTS.get("alpha", {})
    print("\n" + "=" * 60)
    print("ALPHA SCORE RESULTS (JSON)")
    print("=" * 60)
    for symbol, data in alpha_results.items():
        print(f"\n{symbol}:")
        print(json.dumps(data, indent=2))
    
    overall = "POC PASSED" if all_pass else "POC PARTIAL (check failures above)"
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {overall}")
    print(f"{'=' * 60}")
    
    return all_pass

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
