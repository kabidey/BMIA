"""
News Scraping Service
"""
import urllib.parse
import feedparser
import yfinance as yf
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def fetch_news(symbol: str, max_headlines: int = 10):
    headlines = []
    
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        if news and isinstance(news, list):
            for item in news[:max_headlines]:
                if isinstance(item, dict):
                    title = item.get("title", "") or item.get("headline", "")
                    if title:
                        pub_date = item.get("providerPublishTime", "") or item.get("publish_time", "")
                        date_str = ""
                        if isinstance(pub_date, (int, float)):
                            date_str = datetime.fromtimestamp(pub_date).isoformat()
                        elif pub_date:
                            date_str = str(pub_date)
                        
                        headlines.append({
                            "title": title,
                            "publisher": str(item.get("publisher", "") or item.get("source", "")),
                            "link": item.get("link", "") or item.get("url", ""),
                            "date": date_str,
                            "source": "yfinance",
                        })
    except Exception as e:
        logger.warning(f"yfinance news error for {symbol}: {e}")
    
    if len(headlines) < 3:
        try:
            clean_symbol = symbol.replace(".NS", "").replace(".BO", "").replace("=F", "")
            search_query = f"{clean_symbol} stock India"
            encoded_query = urllib.parse.quote(search_query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:max_headlines]:
                title = entry.get("title", "")
                if title:
                    headlines.append({
                        "title": title,
                        "publisher": entry.get("source", {}).get("title", "Google News") if isinstance(entry.get("source"), dict) else "Google News",
                        "link": entry.get("link", ""),
                        "date": entry.get("published", ""),
                        "source": "google_news",
                    })
        except Exception as e:
            logger.warning(f"RSS fallback error for {symbol}: {e}")
    
    seen = set()
    unique = []
    for h in headlines:
        if h["title"] not in seen:
            seen.add(h["title"])
            unique.append(h)
    
    return unique[:max_headlines]
